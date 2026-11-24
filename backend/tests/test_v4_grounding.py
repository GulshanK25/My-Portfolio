"""Data-driven source coverage tests for portfolio breadth and role accuracy.

These verify the evidence given to the model, not the quality of a live model
completion. Live Groq evaluation is needed before claiming hallucinations fixed.
"""
from __future__ import annotations

import json

from backend.agent import PortfolioAssistant, SYSTEM_PROMPT
from backend.agent_tools import ReadOnlyTools, TOOL_SCHEMAS
from backend.knowledge import KnowledgeStore


def test_full_project_catalog_distinguishes_work_from_projects(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    tools = ReadOnlyTools(KnowledgeStore())
    result = tools.execute('inspect_professional_work_and_projects', {'query':'mobile Android applications'})
    items = {item['name']: item for item in result.value['portfolio_projects']}
    assert result.value['counts']['project_records'] == len(items)
    assert 'Smart House App' in items
    assert 'Lunchmate for Softhouse' in items
    assert items['Smart House App']['associated_documented_work_role'] is None
    assert items['Lunchmate for Softhouse']['associated_documented_work_role'] is None
    assert items['PermitTo Consultancy']['associated_documented_work_role']['role'] == 'Freelance Web Developer'
    assert result.value['work_experience']
    assert all(item['role'] != 'Android intern' for item in result.value['work_experience'])
    assert 'project:smart' in [item['id'] for item in result.sources[:5]]
    assert 'project:lunchmate' in [item['id'] for item in result.sources[:5]]
    assert len(result.content()) < 10000


def test_android_and_mobile_search_expand_category_completely(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    tools = ReadOnlyTools(KnowledgeStore())
    for query in ['Android development experience', 'mobile applications']:
        response = tools.execute('search_professional_knowledge', {'query':query})
        ids = {s['id'] for s in response.sources}
        assert {'project:smart', 'project:lunchmate'} <= ids
        assert response.value['record_count'] <= 6


def test_category_coverage_not_specific_to_android(tmp_path, monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    sample = {
        'profile': {'name': 'Example', 'headline': 'Engineer', 'intro': 'Hello', 'about': [],
                    'email': 'example@example.org', 'github': 'https://github.com/example',
                    'linkedin': 'https://linkedin.com/in/example'},
        'projects': [
            {'id':'a', 'name':'Project Alpha', 'category':'Quantum Visualization',
             'description':'Plots simulations', 'tech': ['Python']},
            {'id':'b', 'name':'Project Beta', 'category':'Quantum Visualization',
             'description':'Shows measurements', 'tech': ['Python']},
        ]
    }
    path = tmp_path / 'portfolio.json'
    path.write_text(json.dumps(sample), encoding='utf-8')
    tools = ReadOnlyTools(KnowledgeStore(json_path=path,cv_path=tmp_path / "missing_cv.pdf"))
    ids = {s['id'] for s in tools.execute('search_professional_knowledge',
                {'query':'quantum visualization experience'}).sources}
    assert {'project:a','project:b'} <= ids


def test_model_gets_complete_catalog_on_tool_call(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    assistant = PortfolioAssistant()
    args = {'query':'Does Gulshan have mobile or web applications?'}
    result = assistant.tools.execute('inspect_professional_work_and_projects', args)
    assert result.value['counts']['project_records'] > 5
    assert 'Lunchmate for Softhouse' in result.content()
    assert 'Smart House App' in result.content()
    tool_names = [s['function']['name'] for s in TOOL_SCHEMAS]
    assert 'inspect_professional_work_and_projects' in tool_names
    assert 'search_professional_knowledge' in tool_names
    assert 'Never infer that an entire kind of project is absent' in SYSTEM_PROMPT
    assert 'prefer short paragraphs or bullet lists over Markdown tables' in SYSTEM_PROMPT
