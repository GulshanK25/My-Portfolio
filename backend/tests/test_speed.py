"""Regression checks for the fast portfolio assistant path."""
import time
import httpx
from fastapi.testclient import TestClient
from backend.agent import PortfolioAssistant
from backend.main import app


def test_common_questions_skip_ollama(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "1")
    monkeypatch.setenv("OLLAMA_FOR_SUMMARIES", "0")

    def should_never_call(*_args, **_kwargs):
        raise AssertionError("Common profile questions must not contact Ollama")

    monkeypatch.setattr(PortfolioAssistant, "_ollama", should_never_call)
    with TestClient(app) as client:
        for q in ("Tell me about his work experience", "Who is Gulshan?", "What technologies and skills does Gulshan have?"):
            res = client.post("/api/chat", json={"question": q})
            assert res.status_code == 200
            assert res.json()["mode"] == "profile_summary"


def test_timeout_cooldown_avoids_repeated_llm_calls(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "1")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "2")
    monkeypatch.setenv("OLLAMA_RETRY_COOLDOWN_SECONDS", "60")
    calls = []

    class FakeClient:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def post(self, *_args, **_kwargs):
            calls.append(time.monotonic())
            raise httpx.ReadTimeout("Simulated Ollama timeout")

    monkeypatch.setattr(httpx, "Client", FakeClient)
    assistant = PortfolioAssistant()
    first = assistant.ask("Explain the architecture of the Website RAG Assistant")
    second = assistant.ask("Explain the architecture of the Website RAG Assistant")
    assert len(calls) == 1
    assert first["mode"] == "retrieval_only"
    assert second["mode"] == "retrieval_only"
    assert first["sources"]
