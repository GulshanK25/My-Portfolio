import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.knowledge import KnowledgeStore, build_documents
from backend.main import app


def test_build_includes_master_and_ai_projects():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / "src/data/portfolioKnowledge.json").read_text(encoding="utf-8"))
    docs = build_documents(data, None)
    assert any("Blekinge" in d.text for d in docs)
    assert any("AI Code Review" in d.text for d in docs)
    assert not any("Pig Game" in d.text for d in docs)


def test_search_prefers_current_portfolio():
    store = KnowledgeStore()
    matches = store.search("What degree is Gulshan studying at BTH?")
    assert matches and matches[0].kind == "portfolio"
    assert any("Master's" in d.text for d in matches)


def test_chat_api_without_ollama(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "0")
    with TestClient(app) as client:
        res = client.post("/api/chat", json={"question": "Tell me about the RAG assistant"})
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "retrieval_only"
    assert body["sources"]
    assert "Website RAG Assistant" in body["answer"]


def test_input_validation():
    with TestClient(app) as client:
        res = client.post("/api/chat", json={"question": "x"})
    assert res.status_code == 422


def test_unknown_master_thesis_is_not_invented(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "0")
    client = TestClient(app)
    response = client.post("/api/chat", json={"question": "What is his master's thesis title?"})
    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "couldn't find verified information" in response.json()["answer"]


def test_store_detects_content_changes(tmp_path):
    initial = {
        "profile": {"name": "Test Person", "headline": "Engineer", "intro": "I work in software",
                    "about": ["I develop software"], "github": "https://github.com/example",
                    "linkedin": "https://linkedin.com/example", "email": "test@example.com"},
        "education": [], "experience": [], "projects": [], "extraSkills": [],
    }
    json_path = tmp_path / "profile.json"
    json_path.write_text(json.dumps(initial), encoding="utf-8")
    store = KnowledgeStore(json_path=json_path, cv_path=tmp_path / "no-cv.pdf")
    assert store.search("Python") == []
    initial["profile"]["intro"] = "I develop professional Python applications"
    json_path.write_text(json.dumps(initial, indent=2), encoding="utf-8")
    assert any("Python" in doc.text for doc in store.search("Python"))


def test_open_ended_questions_return_actual_profile_summary(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "0")
    client = TestClient(app)
    for question in ["What else do you know about Gulshan?", "Who is Gulshan?", "Give me an overview of Gulshan"]:
        res = client.post("/api/chat", json={"question": question})
        assert res.status_code == 200
        data = res.json()
        assert data["mode"] == "profile_summary"
        assert "Blekinge" in data["answer"]
        assert "Dun & Bradstreet" in data["answer"]
        assert "AI Code Review" in data["answer"]
        assert data["sources"]


def test_languages_are_not_guessed_when_not_approved(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "0")
    client = TestClient(app)
    res = client.post("/api/chat", json={"question": "Which languages does Gulshan speak?"})
    assert res.status_code == 200
    assert res.json()["mode"] == "profile_fact"
    assert "doesn't list" in res.json()["answer"]
    assert res.json()["sources"] == []


def test_languages_only_if_published(tmp_path, monkeypatch):
    from backend.agent import PortfolioAssistant
    monkeypatch.setenv("USE_OLLAMA", "0")
    data = json.loads((Path(__file__).resolve().parents[2] / "src/data/portfolioKnowledge.json").read_text())
    data["profile"]["languages"] = ["Language A", "Language B (beginner)"]
    path = tmp_path / "knowledge.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assistant = PortfolioAssistant(KnowledgeStore(path, tmp_path / "no-cv.pdf"))
    reply = assistant.ask("What languages does Gulshan speak?")
    assert "Language A" in reply["answer"]
    assert "Language B (beginner)" in reply["answer"]
    assert reply["sources"][0]["id"] == "profile"


def test_common_recruiter_questions_have_useful_offline_answers(monkeypatch):
    monkeypatch.setenv("USE_OLLAMA", "0")
    client = TestClient(app)
    checks = [
        ("Tell me about his work experience", "Dun & Bradstreet"),
        ("What is he studying at BTH?", "Master's"),
        ("What AI projects has Gulshan built?", "AI Code Review"),
        ("What technologies and skills does Gulshan have?", "LangGraph"),
    ]
    for question, expected in checks:
        result = client.post("/api/chat", json={"question": question})
        assert result.status_code == 200
        answer = result.json()
        assert answer["mode"] == "profile_summary"
        assert expected in answer["answer"]
        assert answer["sources"]
