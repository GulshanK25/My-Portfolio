"""No-network semantic search tests with deterministic fake embeddings."""
from __future__ import annotations

import json
from pathlib import Path

from backend.knowledge import KnowledgeStore, SourceDocument
from backend.semantic import LocalSemanticIndex


class FakeEmbedding:
    def __init__(self):
        self.seen: list[list[str]] = []

    def embed(self, texts):
        texts = list(texts)
        self.seen.append(texts)
        for text in texts:
            normalized = text.lower()
            # Simulates a meaning match, not literal keyword overlap.
            if 'android' in normalized or 'handheld' in normalized or 'phone' in normalized:
                yield [1.0, 0.0, 0.0]
            elif 'database' in normalized or 'data storage' in normalized:
                yield [0.0, 1.0, 0.0]
            else:
                yield [0.0, 0.0, 1.0]


def test_local_dense_index_matches_paraphrase_and_filters():
    model = FakeEmbedding()
    index = LocalSemanticIndex(model=model)
    docs = [
        SourceDocument('mobile', 'Android application', 'Kotlin interface for Android devices', '/mobile', 'portfolio'),
        SourceDocument('database', 'Database migration', 'PostgreSQL schema migration', '/db', 'portfolio'),
    ]
    index.build(docs)
    found = index.search('What did you develop for handheld devices?')
    assert found[0].document_id == 'mobile'
    assert found[0].similarity > 0.99
    assert [x.document_id for x in index.search('handheld device', {'database'})] == []


def test_embed_cache_reuses_unchanged_docs_and_removes_deleted_docs():
    embedder = FakeEmbedding()
    index = LocalSemanticIndex(model=embedder)
    doc = SourceDocument('mobile', 'Android app', 'Kotlin for Android', '/mobile', 'portfolio')
    other = SourceDocument('data', 'Database', 'Data storage using PostgreSQL', '/db', 'portfolio')
    index.build([doc, other])
    assert len(embedder.seen) == 1 and len(embedder.seen[0]) == 2
    index.build([doc, other])
    assert len(embedder.seen) == 1, 'Unchanged docs should not be embedded twice'
    changed = SourceDocument('mobile', 'Android app', 'New Android feature', '/mobile', 'portfolio')
    index.build([changed])
    assert len(embedder.seen) == 2 and len(embedder.seen[1]) == 1
    assert set(index.vectors) == {'mobile'}


def _portfolio_file(tmp_path: Path) -> Path:
    data = {
        'profile': {'name':'Example','headline':'Developer', 'intro':'Full stack developer',
                    'about':[], 'email':'example@example.org',
                    'github':'https://github.com/example', 'linkedin':'https://example.org'},
        'education': [], 'experience': [], 'extraSkills': [],
        'projects': [
            {'id':'android','name':'Android Activities','category':'Mobile','description':'A native Kotlin Android app',
             'tech':['Kotlin'], 'githubLink':'https://example.org/android'},
            {'id':'db','name':'Database Migration','category':'Data','description':'PostgreSQL schema conversion',
             'tech':['SQL'],'githubLink':'https://example.org/db'},
        ],
    }
    path = tmp_path / 'portfolio.json'
    path.write_text(json.dumps(data), encoding='utf-8')
    return path


def test_hybrid_finds_semantic_match_without_shared_keywords(tmp_path, monkeypatch):
    import backend.semantic as semantic
    model = FakeEmbedding()
    monkeypatch.setattr(semantic, 'LocalSemanticIndex',
                        lambda model_name: LocalSemanticIndex(model_name, model=model))
    monkeypatch.setenv('ENABLE_SEMANTIC', '1')
    store = KnowledgeStore(_portfolio_file(tmp_path), cv_path=tmp_path / 'none.pdf')
    results = store.search('What did I make for handheld devices?', limit=3)
    assert store.semantic_ready
    assert results[0].id == 'project:android'
    assert all(item.kind == 'portfolio' for item in store.search('handheld devices', kind='portfolio'))


def test_missing_embedding_dependency_falls_back_to_bm25(tmp_path, monkeypatch):
    import backend.semantic as semantic
    monkeypatch.setenv('ENABLE_SEMANTIC', '1')

    def unavailable(*args, **kwargs):
        raise ImportError('fastembed is not installed')

    monkeypatch.setattr(semantic, 'LocalSemanticIndex', unavailable)
    store = KnowledgeStore(_portfolio_file(tmp_path), cv_path=tmp_path / 'none.pdf')
    result = store.search('PostgreSQL database')
    assert any(item.id == 'project:db' for item in result)
    assert store.semantic_ready is False
    assert store.semantic_error == 'ImportError'
    assert store.search('PostgreSQL database'), 'Repeated searches must keep working'


def test_semantic_toggle_without_restart_after_lexical_refresh(tmp_path, monkeypatch):
    import backend.semantic as semantic
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    store = KnowledgeStore(_portfolio_file(tmp_path), cv_path=tmp_path / 'none.pdf')
    store.search('Android')
    assert store.semantic_ready is False
    monkeypatch.setattr(semantic, 'LocalSemanticIndex',
                        lambda model_name: LocalSemanticIndex(model_name, model=FakeEmbedding()))
    monkeypatch.setenv('ENABLE_SEMANTIC', '1')
    assert store.search('handheld device')[0].id == 'project:android'
    assert store.semantic_ready


def test_health_reports_actual_readiness_not_env_flag(monkeypatch):
    from backend.main import app, assistant
    from fastapi.testclient import TestClient
    monkeypatch.setenv('ENABLE_SEMANTIC', '1')
    # The app may not have loaded its embedding index yet. A flag alone is not
    # enough to claim semantic search is ready.
    with TestClient(app) as client:
        health = client.get('/api/health').json()
    assert health['semantic_requested'] is True
    assert health['semantic'] == assistant.store.semantic_ready
    if not assistant.store.semantic_ready:
        assert health['semantic_status'] in {'not_initialized','unavailable'}


def test_hybrid_retrieves_multiple_mobile_projects_for_broad_question(tmp_path, monkeypatch):
    import backend.semantic as semantic
    monkeypatch.setenv('ENABLE_SEMANTIC', '1')
    path = _portfolio_file(tmp_path)
    data = json.loads(path.read_text(encoding='utf-8'))
    data['projects'].insert(1, {
        'id': 'lunchmate', 'name':'Lunchmate', 'category':'Mobile',
        'description':'A Kotlin Android social application', 'tech':['Kotlin', 'Firebase'],
        'githubLink':'https://example.org/lunchmate',
    })
    data['experience'] = [{
        'id':'unrelated', 'organization':'Accounting firm', 'role':'Analyst',
        'period':'2023', 'details':'Professional experience with audits and reporting.',
    }]
    path.write_text(json.dumps(data), encoding='utf-8')
    monkeypatch.setattr(semantic, 'LocalSemanticIndex',
                        lambda model_name: LocalSemanticIndex(model_name, model=FakeEmbedding()))
    store = KnowledgeStore(path, cv_path=tmp_path / 'none.pdf')
    result = store.search('How much experience building things for handheld devices?', limit=4)
    ids = [item.id for item in result]
    assert 'project:android' in ids[:3]
    assert 'project:lunchmate' in ids[:3]
    assert ids.index('project:android') < ids.index('experience:unrelated') if 'experience:unrelated' in ids else True
