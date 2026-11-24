"""Regression coverage for AI portfolio vs GitHub inventory identity."""
import json
from pathlib import Path

from backend.agent_legacy import PortfolioAssistant
from backend.knowledge import KNOWLEDGE_JSON, KnowledgeStore
from backend.project_catalog import ai_repository_evidence, referenced_repository


def make_assistant(tmp_path: Path):
    cache = tmp_path / 'github_knowledge.json'
    inventory = [
        {'full_name': 'GulshanK25/My-Portfolio', 'visibility': 'public',
         'name': 'My-Portfolio', 'description': 'React developer portfolio',
         'pushed_at': '2026-11-20T08:00:00Z', 'topics': [],
         'fork': False, 'archived': False},
        {'full_name': 'GulshanK25/github-code-review', 'visibility': 'public',
         'name': 'github-code-review', 'description': 'Code review assistant',
         'pushed_at': '2026-11-19T08:00:00Z', 'topics': [],
         'fork': False, 'archived': False},
        {'full_name': 'GulshanK25/Scrapper-chatbox', 'visibility': 'public',
         'name': 'Scrapper-chatbox', 'description': 'Web scraping RAG',
         'pushed_at': '2026-11-12T08:00:00Z', 'topics': [],
         'fork': False, 'archived': False},
        {'full_name': 'GulshanK25/Book_shop', 'visibility': 'public',
         'name': 'Book_shop', 'description': 'Java database application',
         'pushed_at': '2024-03-20T08:00:00Z', 'topics': [],
         'fork': False, 'archived': False},
        {'full_name': 'GulshanK25/Private-AI', 'visibility': 'private',
         'name': 'Private-AI', 'description': 'Private LLM',
         'pushed_at': '2026-11-22T08:00:00Z', 'topics': []},
    ]
    cache.write_text(json.dumps({
        'schema': 2, 'provider': 'github', 'inventory': inventory,
        'inventory_owners': ['GulshanK25'], 'inventory_complete': True,
        'synced_at': '2026-11-23T00:00:00Z', 'documents': [],
    }), encoding='utf-8')
    store = KnowledgeStore(json_path=KNOWLEDGE_JSON, github_path=cache,
                           linkedin_path=tmp_path / 'no_linkedin.json')
    return PortfolioAssistant(store), inventory


def test_ai_repo_list_combines_portfolio_and_local_feature_without_implying_pushed(tmp_path):
    assistant, _ = make_assistant(tmp_path)
    result = assistant.ask('tell me ai projects on your githbub')
    assert result['mode'] == 'github_catalog'
    assert 'My-Portfolio' in result['answer']
    assert 'Scrapper-chatbox' in result['answer']
    assert 'github-code-review' in result['answer']
    assert 'Book_shop' not in result['answer']
    assert 'Private-AI' not in result['answer']
    assert 'Local AI feature' in result['answer']
    assert 'may not yet contain' in result['answer']
    assert '3 AI-related' in result['answer']


def test_followup_corrects_portfolio_identity_with_typo(tmp_path):
    assistant, _ = make_assistant(tmp_path)
    question = 'and what about your portifolio? isnt that also ai project'
    history = [
        {'role': 'user', 'content': 'tell me ai projects on your githbub'},
        {'role': 'assistant', 'content': 'Here are the AI projects in GitHub.'},
    ]
    result = assistant.ask(question, history)
    assert result['mode'] == 'github_catalog'
    assert 'Yes' in result['answer']
    assert 'My-Portfolio' in result['answer']
    assert 'same' in result['answer'].lower() or 'existing' in result['answer'].lower()
    assert 'not a separate' in result['answer']
    assert 'public GitHub' in result['answer']


def test_current_portfolio_link_is_searchable_without_canned_answer(tmp_path):
    assistant, _ = make_assistant(tmp_path)
    assistant.store.refresh()
    doc = assistant.store.by_id['profile:repo_relation:gulshank25/my-portfolio']
    assert 'My-Portfolio' in doc.text
    assert 'not verify' in doc.text
    # Direct questions about the named portfolio can retrieve *both* the
    # older frontend project description and the approved local AI addition.
    state = {'question': 'Is his developer portfolio an AI project?',
             'effective_question': 'Is his developer portfolio an AI project?',
             'intent': 'knowledge', 'cv_only': False, 'broad': False}
    retrieved = assistant._retrieve(state)
    ids = {d.id for d in retrieved['documents']}
    assert 'project:portfolio' in ids
    assert 'profile:repo_relation:gulshank25/my-portfolio' in ids


def test_fuzzy_repo_matching_does_not_invent_repositories(tmp_path):
    assistant, inventory = make_assistant(tmp_path)
    assert referenced_repository('what about your portifolio?', inventory)['name'] == 'My-Portfolio'
    assert referenced_repository('what about this?', inventory) is None
    assistant.store.refresh()
    from backend.source_sync import load_json
    from backend.project_catalog import ai_repository_evidence
    facts = load_json(assistant.store.facts_path)
    classified = ai_repository_evidence(inventory, assistant.store.data, facts)
    assert 'gulshank25/private-ai' not in classified
    assert 'gulshank25/book_shop' not in classified
