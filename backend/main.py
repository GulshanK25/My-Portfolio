"""FastAPI entry point for the local portfolio assistant."""

from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal
from .agent import PortfolioAssistant

app = FastAPI(title="Gulshan AI API", version="0.1.0")
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
assistant = PortfolioAssistant()


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=500)


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=500)
    history: list[HistoryItem] = Field(default_factory=list, max_length=6)


@app.get("/api/health")
def health():
    return {"status": "ok", "langgraph": assistant.graph is not None,
            "semantic": os.getenv("ENABLE_SEMANTIC", "0") == "1",
            "ollama_enabled": os.getenv("USE_OLLAMA", "1") == "1",
            "ollama_model": os.getenv("OLLAMA_MODEL", "llama3")}


@app.post("/api/chat")
def chat(request: ChatRequest):
    return assistant.ask(request.question.strip(),
                         [item.model_dump() for item in request.history])
