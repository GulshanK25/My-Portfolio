"""The GitHub repository inventory must never be derived from RAG top-k."""
from __future__ import annotations

import base64
import json
from pathlib import Path

import httpx

from backend.agent_legacy import PortfolioAssistant
from backend.knowledge import KNOWLEDGE_JSON, KnowledgeStore
from backend.source_sync import GitHubKnowledgeSync, load_json


def _github_fixture(tmp_path: Path):
    config = tmp_path / 'sources.json'
    config.write_text(json.dumps({'github': {
        'enabled': True, 'owners': ['GulshanK25'], 'discover_public': True,
        'max_repos': 2,
        'repositories': ['8bitscode/nordic-consultancy'],
    }}), encoding='utf8')
    cache = tmp_path / 'github.json'
    public = [
        {'full_name': 'GulshanK25/My-Portfolio', 'private': False,
         'fork': False, 'archived': False, 'pushed_at': '2026-11-20T11:00:00Z',
         'language': 'JavaScript', 'description': 'Personal portfolio', 'default_branch': 'main'},
        {'full_name': 'GulshanK25/Scrapper-chatbox', 'private': False,
         'fork': False, 'archived': False, 'pushed_at': '2026-11-21T11:00:00Z',
         'language': 'Python', 'description': 'Web scraper and RAG', 'default_branch': 'main'},
        {'full_name': 'GulshanK25/LunchMAte', 'private': False,
         'fork': False, 'archived': False, 'pushed_at': '2025-05-01T00:00:00Z',
         'language': 'Kotlin', 'description': '', 'default_branch': 'main'},
        {'full_name': 'GulshanK25/ArchivedDemo', 'private': False,
         'fork': False, 'archived': True, 'pushed_at': '2023-12-01T00:00:00Z',
         'language': 'Java', 'default_branch': 'main'},
        {'full_name': 'GulshanK25/ForkedWork', 'private': False,
         'fork': True, 'archived': False, 'pushed_at': '2024-02-01T00:00:00Z',
         'language': 'Python', 'default_branch': 'main'},
        {'full_name': 'GulshanK25/SecretThesis', 'private': True,
         'fork': False, 'archived': False, 'pushed_at': '2026-11-23T00:00:00Z'},
    ]

    def route(request: httpx.Request):
        if request.url.path == '/users/GulshanK25/repos':
            return httpx.Response(200, json=public if request.url.params.get('page') == '1' else [])
        name = request.url.path.removeprefix('/repos/')
        if name == '8bitscode/nordic-consultancy':
            return httpx.Response(200, json={'full_name': name, 'private': False,
                'fork': False, 'archived': False, 'pushed_at': '2026-11-22T10:00:00Z',
                'language': 'TypeScript', 'description': 'Client consultancy site', 'default_branch': 'main'})
        if request.url.path.endswith('/readme'):
            return httpx.Response(200, json={'encoding': 'base64', 'path': 'README.md',
                'content': base64.b64encode(b'Project introduction').decode()})
        return httpx.Response(404)

    with httpx.Client(transport=httpx.MockTransport(route)) as client:
        report = GitHubKnowledgeSync(config, cache, client).sync()
    return cache, report


def _assistant(cache: Path) -> PortfolioAssistant:
    store = KnowledgeStore(json_path=KNOWLEDGE_JSON, github_path=cache,
                           linkedin_path=cache.with_name('missing_linkedin.json'))
    return PortfolioAssistant(store=store)


def test_full_catalog_includes_non_indexed_repos_but_never_private_or_external(tmp_path):
    cache, report = _github_fixture(tmp_path)
    assert report['status'] == 'ok'
    assert report['repositories'] <= 2  # README indexing is bounded
    assert report['inventory_repositories'] == 5  # Complete account inventory
    assert report['inventory_complete'] is True
    payload = load_json(cache)
    assert len(payload['inventory']) == 5
    assert 'SecretThesis' not in json.dumps(payload)
    assert '8bitscode/nordic-consultancy' not in json.dumps(payload['inventory'])

    ai = _assistant(cache)
    reply = ai.ask('so tell me all the projects you find on his github')
    assert reply['mode'] == 'github_catalog'
    assert '5 public repositories' in reply['answer']
    assert 'Scrapper-chatbox' in reply['answer']
    assert 'LunchMAte' in reply['answer']
    assert 'ArchivedDemo' in reply['answer']
    assert 'ForkedWork' in reply['answer']
    assert 'SecretThesis' not in reply['answer']
    assert 'nordic-consultancy' not in reply['answer']
    assert 'complete' in reply['answer']
    assert 'https://github.com/GulshanK25/Scrapper-chatbox' in reply['answer']


def test_recent_repo_queries_sort_by_last_push_not_readme_rank(tmp_path):
    cache, _ = _github_fixture(tmp_path)
    ai = _assistant(cache)
    reply = ai.ask('what are gulshan recents projects on github')
    assert reply['mode'] == 'github_catalog'
    assert 'last push' in reply['answer'].lower()
    assert reply['answer'].index('Scrapper-chatbox') < reply['answer'].index('My-Portfolio')
    assert '2026-11-21' in reply['answer']
    assert 'SecretThesis' not in reply['answer']


def test_followup_about_inactivity_avoids_unjustified_continuity(tmp_path):
    cache, _ = _github_fixture(tmp_path)
    ai = _assistant(cache)
    first = ai.ask('What are Gulshan recent projects on GitHub?')
    second = ai.ask('so you are trying to say gulshan hasnt worked between 2026 and 2024', [
        {'role': 'user', 'content': 'What are Gulshan recent projects on GitHub?'},
        {'role': 'assistant', 'content': first['answer']},
    ])
    assert second['mode'] == 'github_catalog'
    assert 'cannot establish' in second['answer']
    assert 'last-push' in second['answer']
    assert 'steady stream' not in second['answer']


def test_correction_admits_limitations_not_fabricated_absence(tmp_path):
    cache, _ = _github_fixture(tmp_path)
    ai = _assistant(cache)
    reply = ai.ask("so why didnt you say it before?", [
        {'role': 'assistant', 'content': 'You can see Scrapper-chatbox in GitHub.'},
    ])
    assert reply['mode'] == 'github_catalog'
    assert 'retrieved' in reply['answer']
    assert 'did not mean it was absent' in reply['answer']


def test_old_cache_requires_refresh_instead_of_false_full_list(tmp_path):
    cache = tmp_path / 'github_old.json'
    cache.write_text(json.dumps({'schema': 1, 'repositories': {
        'GulshanK25/Scrapper-chatbox': {'documents': []},
    }}))
    ai = _assistant(cache)
    reply = ai.ask('list all projects on GitHub')
    assert 'refresh GitHub synchronization' in reply['answer']
    assert 'complete' in reply['answer']


def test_partial_discovery_does_not_claim_complete(tmp_path):
    cache, _ = _github_fixture(tmp_path)
    payload = load_json(cache)
    payload['inventory_complete'] = False
    cache.write_text(json.dumps(payload))
    ai = _assistant(cache)
    reply = ai.ask('show all GitHub repos')
    assert 'may be incomplete' in reply['answer']
    assert 'complete snapshot' not in reply['answer']


def test_direct_project_question_still_uses_rag(tmp_path):
    cache, _ = _github_fixture(tmp_path)
    ai = _assistant(cache)
    assert ai._github_catalog_request('Explain the RAG architecture in Scrapper-chatbox', []) is None
    assert ai._github_catalog_request('What about web scrapper?', []) is None


def test_catalog_works_in_streaming_api_without_groq(tmp_path, monkeypatch):
    """The React SSE path must show inventory data, not invoke the LLM."""
    import asyncio
    cache, _ = _github_fixture(tmp_path)
    ai = _assistant(cache)
    monkeypatch.delenv('GROQ_API_KEY', raising=False)

    async def collect():
        return [event async for event in ai.ask_stream('List all his GitHub repositories')]

    events = asyncio.run(collect())
    assert [event['type'] for event in events] == ['meta', 'delta', 'done']
    assert events[0]['mode'] == 'github_catalog'
    assert 'Scrapper-chatbox' in events[1]['text']
    assert '5 public repositories' in events[1]['text']
