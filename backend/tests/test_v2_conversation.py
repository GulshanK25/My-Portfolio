"""V2 regression tests. No network/API key required."""
from __future__ import annotations

import asyncio
import json

from fastapi.testclient import TestClient

from backend.agent import PortfolioAssistant
from backend.main import app


def test_greeting_takes_chat_route_not_facts_lookup(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("Hey")
    assert result["mode"] == "offline"
    assert "Gulshan AI" in result["answer"]
    assert result["sources"] == []


def test_misspelled_rags_project_retrieves_rag_not_unrelated(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = PortfolioAssistant().ask("What is architecture of Gulshan's rags project?")
    assert [doc["id"] for doc in result["sources"]] == ["project:rag"]
    assert "Website RAG Assistant" in result["answer"]


def test_followup_keeps_project_topic(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = PortfolioAssistant().ask("What were its challenges?", [
        {"role": "user", "content": "Tell me about Gulshan's Website RAG Assistant."},
        {"role": "assistant", "content": "It retrieves passages from websites."},
    ])
    assert [d["id"] for d in result["sources"]] == ["project:rag", "profile:project_learnings"]


def test_no_inference_from_project_featured_status(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = PortfolioAssistant().ask("Which projects are Gulshan currently working on?")
    assert result["sources"] == [{
        "id": "profile:current_projects", "title": "Active development projects (dated status)",
        "url": "/profile-facts.json",
    }]
    assert "2026-11-23" in result["answer"]


def test_model_messages_have_persona_and_context_but_not_user_chat_evidence(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    assistant = PortfolioAssistant()
    prepared = {"question": "What did you build?", "history": [
        {"role": "user", "content": "Tell me about the RAG project"},
        {"role": "assistant", "content": "It crawls websites."},
    ]}
    prepared.update(assistant._contextualize(prepared))
    prepared.update(assistant._retrieve(prepared))
    messages = assistant._messages(prepared)
    assert "AI representative" in messages[0]["content"]
    assert "Conversation history provides" in messages[0]["content"]
    assert messages[-1]["role"] == "user"
    assert "VERIFIED EVIDENCE" in messages[-1]["content"]
    assert "Website RAG Assistant" in messages[-1]["content"]


def test_stream_endpoint_returns_chunks_and_sources_without_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with TestClient(app) as client:
        response = client.post("/api/chat/stream", json={"question": "What is Gulshan studying at BTH?"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "event: meta" in response.text
        assert "event: delta" in response.text
        assert "event: done" in response.text
        assert "Education: Blekinge Institute of Technology" in response.text


def test_stream_sends_groq_deltas_instead_of_retrieval_bullets(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-stream-key")
    assistant = PortfolioAssistant()
    class FakeResponse:
        def raise_for_status(self):
            pass
        async def aiter_lines(self):
            yield 'data: ' + json.dumps({"choices":[{"delta":{"content":"I'm studying "}}]})
            yield 'data: ' + json.dumps({"choices":[{"delta":{"content":"Software Engineering at BTH."}}]})
            yield 'data: [DONE]'
    class FakeStream:
        async def __aenter__(self): return FakeResponse()
        async def __aexit__(self, *args): return False
    class FakeClient:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        def stream(self, method, url, **kwargs):
            assert method == "POST"
            assert kwargs["json"]["stream"] is True
            assert kwargs["headers"]["Authorization"] == "Bearer test-stream-key"
            return FakeStream()

    monkeypatch.setattr("backend.agent.httpx.AsyncClient", FakeClient)
    async def collect():
        return [event async for event in assistant.ask_stream("What are you studying at BTH?")]
    events = asyncio.run(collect())
    assert [e["type"] for e in events] == ["meta", "delta", "delta", "done"]
    assert "Software Engineering at BTH." in "".join(e.get("text", "") for e in events)
    assert events[0]["sources"][0]["id"] == "education:bth"


def test_llm_query_does_not_include_api_key_in_messages(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "my-top-secret-api-key")
    assistant = PortfolioAssistant()
    state = {"question": "What is the RAG assistant?", "history": []}
    state.update(assistant._contextualize(state))
    state.update(assistant._retrieve(state))
    assert "my-top-secret-api-key" not in json.dumps(assistant._messages(state))
