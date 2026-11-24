"""Regression tests for general evidence search and exact GitHub commit lookup."""
import json
from pathlib import Path

import httpx

from backend.agent_legacy import PortfolioAssistant
from backend.github_commits import GitHubCommitReader
from backend.knowledge import KnowledgeStore, _cv_section_documents


def test_cv_sections_all_indexed_by_same_parser():
    sample = """Gulshan Kumar
Kristianstad, Sweden
Education
Master's in Software Engineering
Certifications
AWS Certified Cloud Practitioner (2025)
AI Fluency: Framework & Foundations
Thesis
Intent Security in Android
Languages
English – Professional Proficiency
"""
    docs = _cv_section_documents(sample, 1)
    names = [doc.title for doc in docs]
    assert 'CV: Certifications' in names
    assert 'CV: Thesis' in names
    assert 'CV: Education' in names
    assert 'CV: Spoken languages' in names
    assert any('Kristianstad, Sweden' in d.text for d in docs)
    assert any('AWS Certified Cloud Practitioner' in d.text for d in docs)


def test_general_retrieval_finds_android_apps_without_mobile_answer_rules(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    store = KnowledgeStore()
    names = [x.id for x in store.search('How much Android experience does Gulshan have?', limit=3)]
    assert {'project:smart', 'project:lunchmate'} <= set(names)


def test_general_retrieval_finds_thesis_on_first_attempt(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    response = PortfolioAssistant().ask('What was Gulshan\'s bachelor thesis?')
    assert response['sources'][0]['id'].startswith('cv:thesis:')
    assert 'intent security' in response['answer'].lower()


def test_exact_masters_title_not_misassigned_from_bachelors(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    response = PortfolioAssistant().ask("What is Gulshan's master's thesis title?")
    assert not response['sources']


def test_cv_followup_reuses_question_context(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    answer = PortfolioAssistant().ask('Check in his CV.', [{'role':'user','content':'What was his bachelor thesis?'}])
    assert answer['sources'][0]['id'].startswith('cv:thesis:')
    assert all(item['id'].startswith('cv:') for item in answer['sources'])


def test_unknown_certification_does_not_return_unrelated_experience(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    answer = PortfolioAssistant().ask('What certifications has Gulshan completed?')
    # The older CV in this repository does not have a Certifications section.
    # If a newer CV is supplied locally, its actual evidence should be returned.
    if any('certification' in str(s['title']).lower() for s in answer['sources']):
        assert answer['sources']
    else:
        assert answer['sources'] == []


def test_comparison_follows_two_names_in_conversation(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    history = [{'role':'assistant','content':'Smart House App and Lunchmate for Softhouse were Android projects.'}]
    response = PortfolioAssistant().ask('Which project was more technically challenging?', history)
    assert {s['id'] for s in response['sources']} == {'project:smart','project:lunchmate'}


def test_ambiguous_comparison_requests_clarification():
    response = PortfolioAssistant().ask('Which project was more technically challenging?')
    assert response['mode'] == 'clarification'


def _mock_github_client():
    sha = 'a' * 40
    def handler(request):
        if request.url.path.endswith('/commits'):
            return httpx.Response(200, json=[{'sha':sha}])
        if request.url.path.endswith('/commits/'+sha):
            return httpx.Response(200, json={
                'sha': sha, 'commit': {'message':'Improve retrieval quality',
                                       'committer':{'date':'2026-11-12T18:35:52Z'}},
                'files':[{'filename':'RAG/graph.py','status':'modified'},
                         {'filename':'app.py','status':'modified'}]})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_latest_commit_is_live_structured_evidence(tmp_path):
    path = tmp_path / 'github.json'
    path.write_text(json.dumps({'inventory_owners':['GulshanK25'], 'inventory':[
        {'full_name':'GulshanK25/Scrapper-chatbox','visibility':'public'},
        {'full_name':'GulshanK25/private-test','visibility':'private'}]}))
    client = _mock_github_client()
    reader = GitHubCommitReader(cache_path=path, client=client)
    repo = reader.resolve('When was last committed on scrapper chatbox?', [])
    assert repo == 'GulshanK25/Scrapper-chatbox'
    doc = reader.latest(repo)
    assert 'November 12, 2026' in doc.text
    assert 'Improve retrieval quality' in doc.text
    assert 'RAG/graph.py' in doc.text
    assert doc.url.endswith('a'*40)
    assert reader.latest('GulshanK25/private-test') is None
    client.close()


def test_private_repositories_never_resolve(tmp_path):
    path=tmp_path/'gh.json'
    path.write_text(json.dumps({'inventory_owners':['GulshanK25'], 'inventory':[
        {'full_name':'GulshanK25/private-test','visibility':'private'}]}))
    reader=GitHubCommitReader(cache_path=path)
    assert reader.resolve('last commit on private-test') is None
