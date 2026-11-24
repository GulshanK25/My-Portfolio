import base64
import csv
from io import StringIO
import json
from pathlib import Path
import zipfile

import httpx
import pytest

from backend.source_sync import GitHubKnowledgeSync, scrub_public_markdown, load_json
from backend.linkedin_import import import_export
from backend.knowledge import KnowledgeStore


def _mock_github(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == '/users/GulshanK25/repos':
        return httpx.Response(200, json=[{'full_name': 'GulshanK25/test-rag', 'private': False,
                                          'fork': False, 'archived': False}])
    if path == '/repos/GulshanK25/test-rag':
        return httpx.Response(200, json={
            'full_name': 'GulshanK25/test-rag', 'private': False, 'archived': False,
            'fork': False, 'pushed_at': '2026-11-23T12:00:00Z', 'description': 'A semantic CV assistant',
            'language': 'Python', 'topics': ['rag', 'ai'], 'default_branch': 'main',
        })
    if path == '/repos/GulshanK25/test-rag/readme':
        return httpx.Response(200, json={
            'encoding': 'base64', 'path': 'README.md',
            'content': base64.b64encode(b'# RAG assistant\nAnswers based on CV with hybrid search.').decode(),
        })
    return httpx.Response(404, json={'message': 'Not Found'})


def _setup(tmp_path):
    config = tmp_path / 'knowledge-sources.json'
    config.write_text(json.dumps({'github': {'enabled': True, 'owners': ['GulshanK25'],
                                                    'discover_public': True, 'repositories': [],
                                                    'max_repos': 5}}))
    cache = tmp_path / 'github.json'
    transport = httpx.MockTransport(_mock_github)
    client = httpx.Client(transport=transport)
    return config, cache, client


def test_github_sync_creates_public_docs_and_source_links(tmp_path):
    cfg, cache, client = _setup(tmp_path)
    with client:
        result = GitHubKnowledgeSync(cfg, cache, client).sync()
    assert result['status'] == 'ok'
    assert result['repositories'] == 1
    documents = load_json(cache)['documents']
    assert len(documents) == 2
    assert documents[0]['kind'] == 'github'
    assert documents[1]['url'] == 'https://github.com/GulshanK25/test-rag/blob/main/README.md'
    assert 'hybrid search' in documents[1]['text']


def test_github_sync_reuses_readme_when_not_changed(tmp_path):
    cfg, cache, client = _setup(tmp_path)
    counter = {'readme': 0}
    def route(request):
        if request.url.path.endswith('/readme'):
            counter['readme'] += 1
        return _mock_github(request)
    with httpx.Client(transport=httpx.MockTransport(route)) as client:
        sync = GitHubKnowledgeSync(cfg, cache, client)
        sync.sync()
        sync.sync()
    assert counter['readme'] == 1


def test_github_network_error_keeps_previous_snapshot(tmp_path):
    cfg, cache, client = _setup(tmp_path)
    with client:
        GitHubKnowledgeSync(cfg, cache, client).sync()
    old = load_json(cache)
    def failure(request):
        return httpx.Response(502, json={'error': 'temporary'})
    with httpx.Client(transport=httpx.MockTransport(failure)) as failed:
        result = GitHubKnowledgeSync(cfg, cache, failed).sync()
    assert result['status'] == 'failed'
    assert load_json(cache) == old


def test_private_repos_are_never_indexed(tmp_path):
    cfg = tmp_path / 'config.json'
    cfg.write_text(json.dumps({'github': {'enabled': True,
        'owners': [], 'discover_public': False, 'repositories': ['Other/Private']}}))
    cache = tmp_path / 'github.json'
    def endpoint(request):
        return httpx.Response(200, json={'full_name': 'Other/Private', 'private': True, 'fork': False})
    with httpx.Client(transport=httpx.MockTransport(endpoint)) as client:
        result = GitHubKnowledgeSync(cfg, cache, client).sync()
    assert result['repositories'] == 0
    assert not cache.exists()


def test_cache_documents_enter_knowledge_store_without_replacing_verified_facts(tmp_path):
    cfg, cache, client = _setup(tmp_path)
    with client:
        GitHubKnowledgeSync(cfg, cache, client).sync()
    from backend.knowledge import KNOWLEDGE_JSON
    # The test store uses the real portfolio data, but our controlled cache.
    store = KnowledgeStore(json_path=KNOWLEDGE_JSON, github_path=cache,
                           linkedin_path=tmp_path/'missing.json')
    store.refresh()
    assert 'github:GulshanK25/test-rag:readme' in store.by_id
    assert 'profile' in store.by_id
    assert any('RAG assistant' in d.text for d in store.search('hybrid CV semantic', limit=12))


def test_linkedin_export_explicit_fields_and_privacy(tmp_path):
    package = tmp_path / 'LinkedInData.zip'
    with zipfile.ZipFile(package, 'w') as z:
        z.writestr('Basic_Profile/Positions.csv', 'Company Name,Title,Description,Private Notes\nExample Inc,Developer,Worked with backend,personal id 1234\n')
        z.writestr('Messages.csv', 'From,Message\nSomeone,Private content\n')
    output = tmp_path / 'linkedin.json'
    result = import_export(package, output=output,
                           profile_url='https://www.linkedin.com/in/test-professional')
    assert result['source_files'] == ['positions.csv']
    docs = load_json(output)['documents']
    assert 'Example Inc' in docs[0]['text']
    assert 'Private Notes' not in docs[0]['text']
    assert 'Private content' not in json.dumps(docs)
    assert docs[0]['kind'] == 'linkedin'


def test_scrub_does_not_index_credentials():
    text = 'Hello\nAPI_KEY=abcdefghi12345\nemail a@b.com\n```python\npassword="oops"\n```'
    result = scrub_public_markdown(text)
    assert 'abcdefghi' not in result
    assert 'a@b.com' not in result
    assert 'password=' not in result
