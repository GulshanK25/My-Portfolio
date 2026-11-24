"""Regression checks for multi-turn project conversations, without Groq calls."""
from backend.agent import PortfolioAssistant


ANDROID_HISTORY = [
    {"role": "user", "content": "How experienced is Gulshan in mobile application development?"},
    {"role": "assistant", "content": "He built Android apps and worked on Android security."},
    {"role": "user", "content": "Which Android projects has he built?"},
    {"role": "assistant", "content": "Smart House App and Lunchmate for Softhouse."},
    {"role": "user", "content": "What technologies did he use?"},
    {"role": "assistant", "content": "Smart House App uses Kotlin and Jetpack Compose, while Lunchmate for Softhouse uses Kotlin and Firebase."},
]


def test_which_was_harder_follows_android_pair(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("Which project was more technically challenging?", ANDROID_HISTORY)
    assert {s["id"] for s in result["sources"]} == {"project:lunchmate", "project:smart"}
    assert "can't reliably say" in result["answer"]
    assert "Developer Portfolio" not in result["answer"]


def test_retrieval_uses_older_topic_when_last_followup_has_no_names(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("Which project was more technically challenging?", ANDROID_HISTORY[:-1])
    assert {s["id"] for s in result["sources"]} == {"project:lunchmate", "project:smart"}


def test_comparison_without_context_asks_instead_of_guessing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("Which project was more technically challenging?")
    assert result["sources"] == []
    assert result["mode"] == "clarification"
    assert "Which two projects" in result["answer"]


def test_named_comparison_works_without_history(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("Between the RAG project and Smart House App, which was harder?")
    assert {s["id"] for s in result["sources"]} == {"project:rag", "project:smart"}


def test_android_experience_retrieves_multiple_apps_not_mindmed(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assistant = PortfolioAssistant()
    result = assistant.ask("How much experience does Gulshan have developing Android mobile applications?")
    ids = {s["id"] for s in result["sources"]}
    assert {"project:lunchmate", "project:smart"}.issubset(ids)
    assert "project:mindmed" not in ids


def test_groq_prompt_receives_explicit_comparison_scope(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "testing-only")
    assistant = PortfolioAssistant()
    state = {"question": "Which project was more technically challenging?", "history": ANDROID_HISTORY}
    state.update(assistant._contextualize(state))
    state.update(assistant._retrieve(state))
    messages = assistant._messages(state)
    assert [d.id for d in state["documents"]] == ["project:lunchmate", "project:smart"]
    assert "these two projects" in messages[-1]["content"]
    assert "without ranking them" in messages[-1]["content"]
    assert "Project: Developer Portfolio" not in messages[-1]["content"]
