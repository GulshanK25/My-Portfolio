"""Multi-turn context and source-scoped follow-ups."""
from backend.agent_legacy import PortfolioAssistant


def test_open_question_includes_current_profile(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    result = PortfolioAssistant().ask('Who is Gulshan?')
    assert result['sources'][0]['id'] == 'profile'
    assert 'Blekinge' in result['answer']


def test_cv_followup_is_scoped_to_cv(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    history = [{'role':'user','content':'Tell me about his work experience'}]
    result = PortfolioAssistant().ask('Check in his CV', history)
    assert all(source['id'].startswith('cv:') for source in result['sources'])
    assert result['sources']
