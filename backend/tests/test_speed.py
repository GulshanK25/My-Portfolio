"""Groq failure must not block offline retrieval or repeated requests."""
from backend.agent import PortfolioAssistant


def test_no_key_never_calls_network(monkeypatch):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    def fail(*args, **kwargs):
        raise AssertionError('Network should not be called without an API key')
    monkeypatch.setattr('backend.agent.httpx.Client', fail)
    result = PortfolioAssistant().ask('Tell me about Dun & Bradstreet')
    assert result['mode'] == 'retrieval_only'
    assert 'Dun & Bradstreet' in result['answer']


def test_failure_activates_short_cooldown(monkeypatch):
    import httpx
    monkeypatch.setenv('GROQ_API_KEY', 'dummy')
    calls = []

    class FakeClient:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            calls.append(1)
            raise httpx.ReadTimeout('simulated')

    monkeypatch.setattr('backend.agent.httpx.Client', FakeClient)
    bot = PortfolioAssistant()
    a = bot.ask('Describe the Website RAG Assistant')
    b = bot.ask('Describe the Website RAG Assistant')
    assert a['mode'] == b['mode'] == 'retrieval_only'
    assert len(calls) == 1
