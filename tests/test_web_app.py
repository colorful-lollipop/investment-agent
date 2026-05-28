"""Web API 测试."""

from fastapi.testclient import TestClient

from investment_agent.web.app import _state, app

client = TestClient(app)


class TestWebApp:
    def setup_method(self):
        from investment_agent.orchestrator.agent_orchestrator import AgentOrchestrator

        _state["orchestrator"] = AgentOrchestrator()

    def test_health(self) -> None:
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_index(self) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert "Investment Agent" in r.text

    def test_events_api(self) -> None:
        r = client.get("/api/events?limit=5")
        assert r.status_code == 200
        assert "events" in r.json()

    def test_run_cycle(self) -> None:
        r = client.post("/api/run")
        assert r.status_code == 200
        assert "signals" in r.json()
