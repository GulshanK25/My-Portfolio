"""Academic CV sections must remain complete and outrank unrelated matches."""
from __future__ import annotations

from backend.agent_legacy import PortfolioAssistant
from backend.knowledge import KnowledgeStore, _thesis_section_in_cv
from backend.semantic import SemanticMatch


def test_pdf_thesis_section_preserves_full_explanation():
    store = KnowledgeStore()
    store.refresh()
    matches = [doc for doc in store.documents if doc.id.startswith("cv:thesis:p")]
    assert matches, "Expected an indexed thesis record from the published CV"
    excerpt = matches[0].text.lower()
    assert "intent security" in excerpt
    assert "intent hijacking" in excerpt
    assert "tensor flow lite" in excerpt
    assert matches[0].url.endswith("CV.pdf#page=2")


def test_parser_never_creates_a_thesis_when_section_lacks_evidence():
    assert _thesis_section_in_cv("Thesis\n\nLanguages\nEnglish") is None
    assert _thesis_section_in_cv("Education\nBachelor's in Engineering\nLanguages\nEnglish") is None


def test_first_question_includes_actual_cv_evidence_without_prompting(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ENABLE_SEMANTIC", raising=False)
    store = KnowledgeStore()
    ids = [doc.id for doc in store.search("What was his bachelor thesis?")]
    assert ids[:2] == ["cv:thesis:p2", "education:hkr"]
    answer = PortfolioAssistant(store).ask("What was his bachelor thesis?")
    assert answer["sources"][0]["id"] == "cv:thesis:p2"
    assert "intent" in answer["answer"].lower()


def test_semantic_ranking_cannot_hide_relevant_thesis_evidence(monkeypatch):
    monkeypatch.setenv("ENABLE_SEMANTIC", "1")
    store = KnowledgeStore()
    monkeypatch.setattr(store, "_prepare_semantic", lambda: None)
    store.refresh()

    class MisleadingDenseIndex:
        vectors = {"profile": (1.0,), "project:portfolio": (1.0,)}
        def search(self, question, eligible_ids=None, limit=15):
            return [SemanticMatch("profile", .95), SemanticMatch("project:portfolio", .80)]
    store.semantic = MisleadingDenseIndex()
    hits = store.search("What was Gulshan's bachelor's thesis about?")
    assert [doc.id for doc in hits[:2]] == ["cv:thesis:p2", "education:hkr"]


def test_cv_followup_uses_current_cv_not_unrelated_profile(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ENABLE_SEMANTIC", raising=False)
    result = PortfolioAssistant().ask(
        "look into his cv",
        history=[{"role": "user", "content": "what was his bachelor thesis?"}],
    )
    assert result["sources"]
    assert result["sources"][0]["id"] == "cv:thesis:p2"
    assert all(item["id"].startswith("cv:") for item in result["sources"])
    assert "intent security" in result["answer"].lower()


def test_unknown_masters_thesis_still_not_invented(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = PortfolioAssistant().ask("What is Gulshan's master's thesis title?")
    assert result["sources"] == []
