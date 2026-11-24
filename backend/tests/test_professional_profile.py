"""Career goals and first-hand reflections should be grounded, not guessed."""
from __future__ import annotations

import json

from backend.agent_legacy import PortfolioAssistant
from backend.knowledge import KnowledgeStore


def test_professional_direction_is_public_reviewed_evidence():
    store = KnowledgeStore()
    store.refresh()
    for doc_id in (
        'profile:career_goals', 'profile:professional_interests',
        'profile:motivation', 'profile:project_learnings',
    ):
        doc = store.by_id[doc_id]
        assert doc.url == '/profile-facts.json'
        assert '2026-11-23' in doc.text
    assert 'AI engineering' in store.by_id['profile:career_goals'].text


def test_natural_career_goal_questions_find_goals(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    for question in (
        "What is Gulshan's goal?",
        "What are Gulshan's ambitions?",
        "What does Gulshan want to do after graduation?",
        "What is his career aspiration?",
    ):
        response = PortfolioAssistant().ask(question)
        assert response['sources'][0]['id'] == 'profile:career_goals', question
        assert 'software engineering' in response['answer'].lower(), question


def test_motivation_questions_do_not_trigger_unrelated_code_review_project(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    for question in ("Why is Gulshan interested in AI?", "What motivates Gulshan to build AI tools?"):
        response = PortfolioAssistant().ask(question)
        assert response['sources'][0]['id'] in {'profile:professional_interests', 'profile:motivation'}, question


def test_rag_challenges_include_firsthand_reflection(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    result = PortfolioAssistant().ask('What did Gulshan learn from his RAG project?')
    assert [source['id'] for source in result['sources']] == [
        'project:rag', 'profile:project_learnings',
    ]
    assert 'retrieval' in result['answer'].lower()


def test_broad_intro_includes_personal_direction(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    result = PortfolioAssistant().ask('Who is Gulshan?')
    assert result['sources'][0]['id'] == 'profile'
    assert any(item['id'] == 'profile:career_goals' for item in result['sources'])


def test_dated_goals_not_in_custom_unapproved_store(tmp_path, monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    root = __import__('pathlib').Path(__file__).resolve().parents[2]
    base_data = json.loads((root / 'src/data/portfolioKnowledge.json').read_text(encoding='utf8'))
    other = tmp_path / 'other.json'
    other.write_text(json.dumps(base_data), encoding='utf8')
    store = KnowledgeStore(json_path=other, cv_path=tmp_path / 'absent.pdf')
    store.refresh()
    assert 'profile:career_goals' not in store.by_id
    assert 'profile:project_learnings' not in store.by_id


def test_model_receives_goals_as_verified_evidence(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-key-for-test')
    sent = []

    class FakeResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {'choices': [{'message': {'content': 'I aim to build useful AI-powered software. '}}]}

    class FakeHTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            sent.append(kwargs['json'])
            return FakeResponse()

    monkeypatch.setattr('backend.agent_legacy.httpx.Client', FakeHTTP)
    result = PortfolioAssistant().ask("What's Gulshan's career goal?")
    assert result['mode'] == 'groq'
    assert result['sources'][0]['id'] == 'profile:career_goals'
    assert 'career goal' in json.dumps(sent[0]['messages']).lower()
    assert 'fixed timeline' in sent[0]['messages'][0]['content']
