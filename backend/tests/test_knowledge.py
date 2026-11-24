"""Knowledge extraction, provenance and current portfolio prioritization."""
import json
from pathlib import Path
from fastapi.testclient import TestClient
from backend.knowledge import KnowledgeStore, build_documents, _spoken_languages_in_cv
from backend.main import app


def test_document_construction_and_curated_public_facts():
    root = Path(__file__).resolve().parents[2]
    data = json.loads((root / 'src/data/portfolioKnowledge.json').read_text(encoding='utf8'))
    docs = build_documents(data, cv_path=None)
    assert any('Blekinge' in d.text for d in docs)
    assert any('AI Code Review' in d.text for d in docs)
    assert not any('Pig Game' in d.text for d in docs)
    matches = KnowledgeStore().search('Which languages does Gulshan speak?')
    assert matches[0].id == 'profile:languages'


def test_current_education_and_named_projects_rank_high():
    store = KnowledgeStore()
    assert store.search('Which university does Gulshan currently attend?')[0].id == 'education:bth'
    assert store.search('Explain the RAG architecture')[0].id == 'project:rag'


def test_input_validation():
    with TestClient(app) as client:
        assert client.post('/api/chat', json={'question':'x'}).status_code == 422


def test_languages_parser_does_not_confuse_programming_languages():
    text = 'Programming Languages: Java, Python\nLanguages\n• English – Professional Proficiency\n• Swedish – Basic Proficiency\nReferences'
    assert _spoken_languages_in_cv(text) == ['English (Professional Proficiency)', 'Swedish (Basic Proficiency)']
