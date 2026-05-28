"""TDD: LLM 适配器测试."""

from investment_agent.llm.adapter import LLMAdapter, LLMMessage, LLMResponse


class TestLLMMessage:
    def test_to_dict(self):
        msg = LLMMessage(role="user", content="hello")
        assert msg.to_dict() == {"role": "user", "content": "hello"}

    def test_to_dict_with_tool_calls(self):
        msg = LLMMessage(role="assistant", content="", tool_calls=[{"id": "1"}], tool_call_id="1")
        d = msg.to_dict()
        assert d["tool_calls"] == [{"id": "1"}]
        assert d["tool_call_id"] == "1"


class TestLLMResponse:
    def test_has_tool_calls(self):
        resp = LLMResponse(content="hi", tool_calls=[{"name": "get_price"}])
        assert resp.has_tool_calls is True

    def test_no_tool_calls(self):
        resp = LLMResponse(content="hi")
        assert resp.has_tool_calls is False


class TestLLMAdapter:
    def test_init_defaults(self):
        adapter = LLMAdapter()
        assert adapter.model == "mimo-v2.5-pro"
        assert adapter.temperature == 0.2

    def test_parse_json_response_clean(self):
        adapter = LLMAdapter()
        result = adapter._parse_json_response('{"sentiment": "positive", "score": 0.8}')
        assert result["sentiment"] == "positive"
        assert result["score"] == 0.8

    def test_parse_json_response_with_markdown(self):
        adapter = LLMAdapter()
        text = '```json\n{"sentiment": "negative"}\n```'
        result = adapter._parse_json_response(text)
        assert result["sentiment"] == "negative"

    def test_parse_json_response_invalid(self):
        adapter = LLMAdapter()
        result = adapter._parse_json_response("not json at all")
        assert "_parse_error" in result
        assert result["trading_signal"] == "hold"
