"""FastAPI Web UI —— SSE 实时推送 Agent 事件与信号.

用法:
    uvicorn investment_agent.web.app:app --reload --port 8000
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator
from investment_agent.sensors.akshare_sensor import AKShareDataSensor
from investment_agent.sensors.news_sensor import NewsSensor
from investment_agent.skills.news_skill import NewsAnalysisSkill
from investment_agent.skills.portfolio_skill import PortfolioAdvisorSkill

logger = logging.getLogger("web")
logging.basicConfig(level=logging.INFO)

# 全局状态
_state: dict[str, Any] = {
    "events": [],
    "signals": [],
    "running": False,
}


def _get_orchestrator() -> AgentOrchestrator:
    """构建默认 orchestrator（可替换为从配置加载）."""
    orch = AgentOrchestrator()
    orch.register_sensor(AKShareDataSensor(symbols=["300750.SZ", "600519.SH"], limit=3))
    orch.register_sensor(NewsSensor(limit=3))
    orch.register_skill(NewsAnalysisSkill(priority=100))
    orch.register_advisor(PortfolioAdvisorSkill(priority=50))
    return orch


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    _state["orchestrator"] = _get_orchestrator()
    _state["running"] = True
    yield
    _state["running"] = False


app = FastAPI(title="Investment Agent", lifespan=lifespan)

# 静态文件
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """返回前端页面."""
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    return "<h1>Investment Agent Web UI</h1><p>index.html not found</p>"


@app.post("/api/run")
async def run_cycle() -> dict[str, Any]:
    """手动触发一次 Agent cycle."""
    orch: AgentOrchestrator = _state["orchestrator"]
    signals = orch.run_cycle()
    result = {
        "signals": [
            {
                "symbol": s.symbol,
                "direction": s.direction.value,
                "quantity": s.quantity,
                "price": s.price,
                "confidence": s.confidence,
                "reason": s.reason,
                "timestamp": s.timestamp.isoformat(),
            }
            for s in signals
        ],
        "event_count": len(orch._event_history),
    }
    _state["signals"].extend(result["signals"])
    return result


@app.get("/api/events")
async def get_events(limit: int = 20) -> dict[str, Any]:
    """获取最近事件."""
    orch: AgentOrchestrator = _state["orchestrator"]
    events = orch._event_history[-limit:]
    return {
        "events": [
            {
                "type": e.event_type.value,
                "title": e.title,
                "symbol": e.symbol,
                "source": e.source,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in events
        ]
    }


@app.get("/api/sse")
async def sse_stream() -> StreamingResponse:
    """SSE 实时推送."""

    async def event_generator() -> AsyncGenerator[str, None]:
        last_event_len = 0
        last_signal_len = 0
        while _state["running"]:
            orch: AgentOrchestrator = _state["orchestrator"]
            changed = False

            # 检查新事件
            events = orch._event_history
            if len(events) > last_event_len:
                for e in events[last_event_len:]:
                    data = json.dumps(
                        {
                            "type": "event",
                            "event_type": e.event_type.value,
                            "title": e.title,
                            "symbol": e.symbol,
                            "source": e.source,
                            "timestamp": e.timestamp.isoformat(),
                        },
                        ensure_ascii=False,
                    )
                    yield f"event: agent\ndata: {data}\n\n"
                last_event_len = len(events)
                changed = True

            # 检查新信号
            signals = _state.get("signals", [])
            if len(signals) > last_signal_len:
                for s in signals[last_signal_len:]:
                    data = json.dumps({"type": "signal", **s}, ensure_ascii=False)
                    yield f"event: agent\ndata: {data}\n\n"
                last_signal_len = len(signals)
                changed = True

            if not changed:
                await asyncio.sleep(1.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now().isoformat()}
