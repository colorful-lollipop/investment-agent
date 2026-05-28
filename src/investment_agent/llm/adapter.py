"""LLM 适配器 —— 统一接口支持 OpenAI / DeepSeek / Ollama / 本地模型.

基于 OpenAI SDK 兼容接口，通过切换 base_url 和 api_key 实现多模型支持.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any, cast


@dataclass
class LLMMessage:
    """LLM 消息结构."""

    role: str  # system / user / assistant / tool
    content: str = ""
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = self.tool_calls
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        return msg


@dataclass
class LLMResponse:
    """LLM 响应结构."""

    content: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    raw: Any = None

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMAdapter:
    """LLM 适配器 —— 金融量化分析专用.

    支持:
    - OpenAI (GPT-4o / o3-mini)
    - DeepSeek (deepseek-chat / deepseek-reasoner)
    - Ollama 本地模型 (qwen3, llama3.1 等)
    - 任意 OpenAI 兼容接口
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model or os.getenv("LLM_MODEL", "mimo-v2.5-pro")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL", None)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = 60.0
        self._client: Any = None

    def _get_client(self) -> Any:
        """懒加载 OpenAI 客户端."""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise ImportError("openai SDK not installed. Run: pip install openai") from exc

            kwargs: dict[str, Any] = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        """发送对话请求到 LLM.

        Args:
            messages: 消息列表
            tools: Function calling 工具定义 (OpenAI 格式)
            tool_choice: "auto" | "none" | {"type": "function", "function": {"name": "xxx"}}

        Returns:
            LLMResponse: 包含文本回复和工具调用请求
        """
        client = self._get_client()
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_dict() for m in messages],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        completion = client.chat.completions.create(**payload, timeout=self.timeout)
        msg = completion.choices[0].message

        tool_calls = []
        if msg.tool_calls:
            tool_calls = [
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                }
                for tc in msg.tool_calls
            ]

        return LLMResponse(
            content=msg.content or "",
            tool_calls=tool_calls,
            raw=completion,
        )

    def analyze_news(
        self,
        news_text: str,
        symbol: str | None = None,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """金融新闻快速分析 —— 返回结构化 JSON.

        返回字段:
        - sentiment: "positive" | "negative" | "neutral"
        - sentiment_score: -1.0 ~ 1.0
        - impact_level: "high" | "medium" | "low"
        - affected_sectors: list[str]
        - summary: str
        - trading_signal: "buy" | "sell" | "hold" | "watch"
        - confidence: 0.0 ~ 1.0
        """
        from .prompts import SYSTEM_PROMPT_FINANCIAL_ANALYST

        sys_prompt = system_prompt or SYSTEM_PROMPT_FINANCIAL_ANALYST
        user_prompt = self._build_news_prompt(news_text, symbol)

        messages = [
            LLMMessage(role="system", content=sys_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]
        resp = self.chat(messages)
        return self._parse_json_response(resp.content)

    def _build_news_prompt(self, news_text: str, symbol: str | None) -> str:
        symbol_line = f"相关标的: {symbol}\n" if symbol else ""
        return (
            f"请分析以下金融新闻，并以 JSON 格式输出分析结果。\n\n"
            f"{symbol_line}"
            f"新闻内容:\n{news_text}\n\n"
            f"请输出以下格式的 JSON (不要包含 markdown 代码块):\n"
            f"{{\n"
            f'  "sentiment": "positive|negative|neutral",\n'
            f'  "sentiment_score": 0.0,\n'
            f'  "impact_level": "high|medium|low",\n'
            f'  "affected_sectors": ["行业1", "行业2"],\n'
            f'  "summary": "一句话摘要",\n'
            f'  "trading_signal": "buy|sell|hold|watch",\n'
            f'  "confidence": 0.0\n'
            f"}}"
        )

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        text = text.strip()
        """从 LLM 回复中提取 JSON."""
        import json

        text = text.strip()
        # 去除 markdown 代码块
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines)

        try:
            return cast(dict[str, Any], json.loads(text))
        except json.JSONDecodeError:
            # 尝试从文本中提取 JSON 子串
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                try:
                    return cast(dict[str, Any], json.loads(text[start : end + 1]))
                except json.JSONDecodeError:
                    pass
            return {
                "sentiment": "neutral",
                "sentiment_score": 0.0,
                "impact_level": "low",
                "affected_sectors": [],
                "summary": text[:200],
                "trading_signal": "hold",
                "confidence": 0.0,
                "_parse_error": True,
            }
