"""Regression checks for verified categories, ambiguous wording, and project status."""
import json
from pathlib import Path

from backend.agent import PortfolioAssistant
from backend.knowledge import KnowledgeStore


def test_explicit_programming_languages_are_not_confused_with_spoken(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = PortfolioAssistant().ask("Which programming languages does Gulshan know?")
    assert response["mode"] == "retrieval_only"
    assert [source["id"] for source in response["sources"]] == ["profile:programming_languages"]
    for language in ("Python", "Java", "Kotlin", "JavaScript", "TypeScript"):
        assert language in response["answer"]
    assert "Swedish" not in response["answer"]


def test_spoken_languages_come_from_spoken_record(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = PortfolioAssistant().ask("Which langauges does Gulshan speaks?")
    assert [source["id"] for source in response["sources"]] == ["profile:languages"]
    assert "English" in response["answer"] and "Swedish" in response["answer"]
    assert "JavaScript" not in response["answer"]


def test_ambiguous_language_question_includes_both_with_distinct_sources(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = PortfolioAssistant().ask("Okay which langauges does Gulshan know?")
    assert {source["id"] for source in response["sources"]} == {
        "profile:programming_languages", "profile:languages"
    }
    assert "Python" in response["answer"]
    assert "English" in response["answer"]


def test_ongoing_projects_require_explicit_dated_status(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    response = PortfolioAssistant().ask("What projects is Gulshan currently working on?")
    assert [source["id"] for source in response["sources"]] == ["profile:current_projects"]
    assert "Ask Gulshan AI" in response["answer"]
    assert "2026-11-23" in response["answer"]
    assert "Home Assistant Software Evolution" not in response["answer"]
    assert "PermitTo" not in response["answer"]


def test_no_active_status_does_not_invent_current_work(tmp_path, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "src/data/portfolioKnowledge.json").read_text(encoding="utf8"))
    profile = tmp_path / "portfolio.json"
    profile.write_text(json.dumps(data), encoding="utf8")
    # No dated status record: existing project list is not evidence of current activity.
    store = KnowledgeStore(json_path=profile, cv_path=tmp_path / "missing.pdf")
    result = PortfolioAssistant(store=store).ask("What projects is he currently working on?")
    assert result["mode"] == "no_evidence"
    assert result["sources"] == []


def test_groq_receives_verified_language_and_current_status_sources(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "not-a-real-key")
    submitted = []

    class FakeResponse:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": "Gulshan knows Python, Java and TypeScript. [SOURCE 1]"}}]}

    class FakeClient:
        def __init__(self, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def post(self, url, **kwargs):
            submitted.append(kwargs["json"])
            return FakeResponse()

    monkeypatch.setattr("backend.agent.httpx.Client", FakeClient)
    answer = PortfolioAssistant().ask("What programming languages does Gulshan know?")
    assert answer["mode"] == "groq"
    assert answer["sources"][0]["id"] == "profile:programming_languages"
    assert "Programming languages" in str(submitted[0]["messages"])
    assert "Swedish" not in str(submitted[0]["messages"])
