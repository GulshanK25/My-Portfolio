"""V4 live-provider resilience tests with mock responses, no real API calls."""
import asyncio
import json
import time

import httpx
import pytest

from backend.agent import (
    MAX_TOOL_ROUNDS, PortfolioAssistant, ProviderError, _provider_error,
    _retry_after_seconds, _wait_message,
)
from backend.agent_tools import ReadOnlyTools
from backend.knowledge import KnowledgeStore


def test_retry_after_parses_numeric_date_and_bad_headers():
    assert _retry_after_seconds('125') == 125
    assert _retry_after_seconds('0.2') == 1
    assert _retry_after_seconds('Wed, 21 Oct 2015 07:28:00 GMT') == 1
    assert _retry_after_seconds('not a date') is None
    assert _retry_after_seconds(None) is None
    assert '3 minute' in _wait_message(125)


def test_429_cooldown_prevents_followup_provider_requests(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-v4-key')
    assistant = PortfolioAssistant()
    calls = 0

    def exhausted(messages, rounds):
        nonlocal calls
        calls += 1
        request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')
        resp = httpx.Response(429, request=request, headers={'Retry-After': '91'})
        raise _provider_error(httpx.HTTPStatusError('too many', request=request, response=resp))

    monkeypatch.setattr(assistant, '_post', exhausted)
    first = assistant.ask('Tell me about Gulshan')
    assert first['mode'] == 'error'
    assert '2 minute' in first['answer']
    second = assistant.ask('How are you?')
    assert second['mode'] == 'unavailable'
    assert '2 minute' in second['answer']
    assert calls == 1


def test_normal_gpt_oss_requests_use_low_reasoning_and_bounded_context(monkeypatch):
    monkeypatch.setenv('GROQ_MODEL', 'openai/gpt-oss-20b')
    assistant = PortfolioAssistant()
    history = [{'role':'user', 'content':'a'*1200} for _ in range(25)]
    messages = assistant._messages('hello', history)
    assert len(messages) == 10 # system, 8 history, current message
    assert all(len(m.get('content', '')) <= 700 for m in messages[1:-1])
    payload = assistant._payload(messages, rounds=0, stream=True)
    assert payload['reasoning_effort'] == 'low'
    assert payload['reasoning_format'] == 'hidden'
    assert payload['max_completion_tokens'] == 1600
    assert payload['parallel_tool_calls'] is False
    assert MAX_TOOL_ROUNDS == 2
    final_payload = assistant._payload(messages, rounds=MAX_TOOL_ROUNDS, stream=True)
    assert 'tools' not in final_payload


def test_other_model_does_not_receive_unsupported_gpt_oss_settings(monkeypatch):
    monkeypatch.setenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    payload = PortfolioAssistant()._payload([], rounds=0, stream=False)
    assert 'reasoning_effort' not in payload
    assert 'reasoning_format' not in payload


def test_tool_payloads_are_compact_but_retain_primary_evidence(monkeypatch):
    monkeypatch.delenv('ENABLE_SEMANTIC', raising=False)
    tools = ReadOnlyTools(KnowledgeStore())
    overview = tools.execute('get_professional_overview', {})
    assert 'Blekinge' in overview.content()
    assert 'Dun & Bradstreet' in overview.content()
    assert len(overview.content()) < 12500
    search = tools.execute('search_professional_knowledge', {'query':'Android development'})
    assert search.value['record_count'] <= 6
    assert any('Android' in r['evidence'] for r in search.value['records'])


def test_streaming_429_sends_a_single_clear_error_without_leaking_content(monkeypatch):
    monkeypatch.setenv('GROQ_API_KEY', 'fake-v4-key')
    assistant = PortfolioAssistant()
    request = httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions')

    class Response:
        def raise_for_status(self):
            response = httpx.Response(429, request=request, headers={'Retry-After':'77'})
            raise httpx.HTTPStatusError('slow down', request=request, response=response)
    class Stream:
        async def __aenter__(self): return Response()
        async def __aexit__(self, *args): return False
    class Client:
        def __init__(self, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): return False
        def stream(self, method, url, headers, json): return Stream()
    monkeypatch.setattr('backend.agent.httpx.AsyncClient', Client)
    async def collect():
        return [e async for e in assistant.ask_stream('Can you tell me about his projects?')]
    events = asyncio.run(collect())
    assert [e['type'] for e in events] == ['meta','delta','done']
    assert events[0]['mode'] == 'error'
    assert '2 minute' in events[1]['text']
    assert assistant._cooling_down()
