"""Regression checks for conversational retrieval and Groq generation (no network)."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.agent_legacy import PortfolioAssistant
from backend.agent_tools import ReadOnlyTools
from backend.knowledge import KnowledgeStore, build_documents
from backend.main import app


def ask(question, history=None):
    with TestClient(app) as client:
        response = client.post('/api/chat', json={'question': question, 'history': history or []})
    assert response.status_code == 200, response.text
    return response.json()


# The historical agent remains available to regression-test existing retrieval.
# The active v4 /api/chat endpoint deliberately no longer uses its offline
# document-dumping fallback. These tests exercise source tools directly.

def test_local_search_covers_new_ai_projects(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    store = KnowledgeStore()
    docs = store.search('AI projects code review website RAG', limit=12)
    assert any(doc.id == 'project:review' for doc in docs)
    assert any(doc.id == 'project:rag' for doc in docs)


def test_profile_and_cv_are_distinct_sources(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    store = KnowledgeStore()
    result = ReadOnlyTools(store).execute('search_professional_knowledge', {'query':'spoken languages'})
    assert any(s['id'] == 'profile:languages' for s in result.sources)
    cv = store.search('spoken languages English Swedish', limit=10, kind='cv')
    assert cv and all(doc.kind == 'cv' for doc in cv)


def test_open_ended_question_covers_multiple_sources(monkeypatch):
    tool = ReadOnlyTools(KnowledgeStore())
    response = tool.execute('get_professional_overview', {})
    assert response.sources[0]['id'] == 'profile'
    assert any(s['id'].startswith('education:') for s in response.sources)
    assert any(s['id'].startswith('experience:') for s in response.sources)


def test_followup_can_search_resolved_topic(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    tool = ReadOnlyTools(KnowledgeStore())
    response = tool.execute('search_professional_knowledge',
                            {'query':'Website RAG Assistant technologies'})
    assert any(s['id'] == 'project:rag' for s in response.sources)


def test_master_thesis_title_not_automatically_fabricated(monkeypatch):
    store = KnowledgeStore()
    store.refresh()
    assert not any(doc.id.startswith('cv:thesis:') and
                   'master' in doc.title.lower() for doc in store.documents)
    # The model must inspect evidence rather than use a prefilled answer.
    assert any('Only professional-source tool outputs' in msg['content']
               for msg in __import__('backend.agent', fromlist=['PortfolioAssistant'])
               .PortfolioAssistant._messages('What is his master thesis title?', []))


def test_no_key_offline_failure_is_truthful(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    response = ask('check in his CV')
    assert response['mode'] == 'unavailable'
    assert response['sources'] == []
    assert 'The AI service' in response['answer']


def test_groq_uses_only_server_side_environment_and_verified_sources(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'test-not-a-real-key')
    monkeypatch.setenv('GROQ_MODEL', 'openai/gpt-oss-20b')
    calls = []

    class MockResponse:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return {'choices': [{'message': {'content': 'He built a website RAG assistant using LangGraph and ChromaDB. [SOURCE 1]'}}]}

    class FakeHTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            calls.append((url, kwargs))
            return MockResponse()

    monkeypatch.setattr('backend.agent_legacy.httpx.Client', FakeHTTP)
    response = PortfolioAssistant().ask('Explain Gulshan’s RAG assistant')
    assert response['mode'] == 'groq'
    assert 'LangGraph' in response['answer']
    assert calls[0][0] == 'https://api.groq.com/openai/v1/chat/completions'
    assert calls[0][1]['json']['model'] == 'openai/gpt-oss-20b'
    assert calls[0][1]['headers']['Authorization'] == 'Bearer test-not-a-real-key'
    assert any(s['id'] == 'project:rag' for s in response['sources'])


def test_live_provider_health_does_not_leak_secret(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'hidden-example-key')
    with TestClient(app) as client:
        data = client.get('/api/health').json()
    assert data['provider'] == 'groq'
    assert data['groq_configured'] is True
    assert 'hidden-example-key' not in json.dumps(data)


def test_changes_to_profile_data_are_reloadable(tmp_path, monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    minimal = {
      'profile': {'name':'Example', 'headline':'Engineer', 'intro':'Software engineer', 'about':[],
                  'email':'a@b.example', 'linkedin':'https://example.org', 'github':'https://github.com/example'},
      'education':[], 'experience':[], 'projects':[], 'extraSkills':[],
    }
    local = tmp_path / 'profile.json'
    local.write_text(json.dumps(minimal), encoding='utf8')
    store = KnowledgeStore(json_path=local, cv_path=tmp_path/'missing.pdf')
    assert store.search('Kotlin') == []
    minimal['profile']['about'] = ['Experienced in Kotlin mobile development.']
    local.write_text(json.dumps(minimal, indent=2), encoding='utf8')
    assert any('Kotlin' in d.text for d in store.search('Kotlin'))


def test_named_project_is_not_mixed_with_unrelated_sources(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    result = PortfolioAssistant().ask('Explain the architecture of his RAG assistant')
    assert result['mode'] == 'retrieval_only'
    assert result['sources']
    assert [source['id'] for source in result['sources']] == ['project:rag']
    assert 'Home Assistant' not in result['answer']


def test_groq_http_error_logs_status_and_redacts_api_key(monkeypatch, caplog):
    import httpx
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_thisisasecretkey123456')
    monkeypatch.setenv('GROQ_MODEL', 'openai/gpt-oss-20b')

    class FakeHTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            return httpx.Response(
                status_code=401,
                json={'error': {
                    'type': 'invalid_request_error',
                    'code': 'invalid_api_key',
                    'message': 'Bad key gsk_thisisasecretkey123456',
                }},
                request=httpx.Request('POST', url),
            )

    monkeypatch.setattr('backend.agent_legacy.httpx.Client', FakeHTTP)
    with caplog.at_level('WARNING'):
        result = PortfolioAssistant().ask('Explain the architecture of his RAG assistant')
    assert result['mode'] == 'retrieval_only'
    assert [source['id'] for source in result['sources']] == ['project:rag']
    assert 'HTTP 401' in caplog.text
    assert 'invalid_api_key' in caplog.text
    assert 'gsk_thisisasecretkey123456' not in caplog.text
    assert '[REDACTED]' in caplog.text


def test_groq_retries_400_with_minimal_single_user_message(monkeypatch, caplog):
    import httpx
    monkeypatch.setenv('GROQ_API_KEY', 'test-secret-123')
    responses = []
    class FakeHTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            responses.append(kwargs['json'])
            if len(responses) == 1:
                return httpx.Response(400, json={'message': 'Unsupported message format'},
                                      request=httpx.Request('POST', url))
            return httpx.Response(200, json={'choices':[{'message':{'content':'Gulshan is studying Software Engineering at BTH.'}}]},
                                  request=httpx.Request('POST',url))
    monkeypatch.setattr('backend.agent_legacy.httpx.Client', FakeHTTP)
    with caplog.at_level('WARNING'):
        result=PortfolioAssistant().ask('What is Gulshan studying at BTH?')
    assert result['mode'] == 'groq'
    assert len(responses) == 2
    assert set(responses[0]) == {'model','messages'}
    assert len(responses[1]['messages']) == 1
    assert responses[1]['messages'][0]['role'] == 'user'
    assert 'Unsupported message format' in caplog.text
    assert 'test-secret-123' not in caplog.text


def test_groq_nonstandard_errors_are_logged_and_secrets_redacted(monkeypatch, caplog):
    import httpx
    monkeypatch.setenv('GROQ_API_KEY', 'gsk_SUPERSECRET123456789')
    calls=[]
    class FakeHTTP:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            calls.append(kwargs['json'])
            return httpx.Response(400, json={'detail':'Body rejected gsk_SUPERSECRET123456789'},
                                  headers={'x-request-id': 'req-abc-123'},
                                  request=httpx.Request('POST',url))
    monkeypatch.setattr('backend.agent_legacy.httpx.Client', FakeHTTP)
    with caplog.at_level('WARNING'):
        result=PortfolioAssistant().ask('What is he studying at BTH?')
    assert result['mode'] == 'retrieval_only'
    assert len(calls) == 2
    assert 'HTTP 400' in caplog.text
    assert 'req-abc-123' in caplog.text
    assert 'gsk_SUPERSECRET123456789' not in caplog.text
    assert '[REDACTED]' in caplog.text
