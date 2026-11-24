"""FastAPI entry point for Gulshan AI v2."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
import logging
from threading import Event, Thread
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .agent import PortfolioAssistant
from .source_sync import GitHubKnowledgeSync, GITHUB_CACHE, LINKEDIN_CACHE, load_json

assistant = PortfolioAssistant()
_sync_stop = Event()
_sync_worker: Thread | None = None
_logger = logging.getLogger(__name__)


def _sync_loop():
    # Poll public GitHub metadata and README files; never write to GitHub.
    interval = max(300, min(int(os.getenv('GITHUB_SYNC_INTERVAL_SECONDS', '21600')), 86400))
    while not _sync_stop.is_set():
        try:
            report = GitHubKnowledgeSync().sync()
            _logger.info('Read-only GitHub knowledge sync: %s', report)
        except Exception as exc:  # Never stop chat service due to external sources.
            _logger.warning('GitHub sync unavailable (%s)', type(exc).__name__)
        _sync_stop.wait(interval)


def _start_sync():
    global _sync_worker
    if os.getenv('GITHUB_AUTO_SYNC', '0') != '1':
        return
    if _sync_worker and _sync_worker.is_alive():
        return
    _sync_stop.clear()
    _sync_worker = Thread(target=_sync_loop, name='github-readonly-sync', daemon=True)
    _sync_worker.start()


def _stop_sync():
    _sync_stop.set()
    if _sync_worker and _sync_worker.is_alive():
        _sync_worker.join(timeout=2.0)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Start optional GitHub syncing when the API starts; stop on shutdown."""
    _start_sync()
    try:
        yield
    finally:
        _stop_sync()


app = FastAPI(title="Gulshan AI API", version="2.0.0", lifespan=lifespan)
allowed_origins = [x.strip() for x in os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
).split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1200)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    history: list[HistoryItem] = Field(default_factory=list, max_length=12)


@app.get("/api/health")
def health():
    semantic_requested = os.getenv("ENABLE_SEMANTIC", "0") == "1"
    github_cache = load_json(GITHUB_CACHE)
    return {"status": "ok", "langgraph": assistant.graph is not None,
            "semantic": semantic_requested and assistant.store.semantic_ready,
            "semantic_requested": semantic_requested,
            "semantic_status": (
                "disabled" if not semantic_requested else
                "unavailable" if assistant.store.semantic_error else
                "ready" if assistant.store.semantic_ready else "not_initialized"
            ),
            "provider": "groq",
            "groq_configured": bool(os.getenv("GROQ_API_KEY", "").strip()),
            "groq_model": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            "streaming": True,
            "version": "2.1.0",
            "github_sync": {
                "enabled": os.getenv('GITHUB_AUTO_SYNC', '0') == '1',
                "synced_at": github_cache.get('synced_at'),
                "repositories": len(github_cache.get('repositories', {})),
                "inventory_repositories": len(github_cache.get('inventory', [])),
                "inventory_complete": github_cache.get('inventory_complete') is True,
            },
            "linkedin_sync": {
                "mode": "owner_export_only",
                "imported_at": load_json(LINKEDIN_CACHE).get('imported_at'),
            }}


@app.post("/api/chat")
def chat(request: ChatRequest):
    """Non-streaming endpoint retained for tests and older clients."""
    return assistant.ask(request.question.strip(),
                         [item.model_dump() for item in request.history])


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """SSE response over POST. Each event contains exactly one JSON payload."""
    async def events():
        async for event in assistant.ask_stream(
            request.question.strip(), [item.model_dump() for item in request.history]
        ):
            yield f"event: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache, no-transform",
                                      "X-Accel-Buffering": "no"})
