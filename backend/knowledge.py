"""Read verified portfolio information and the published PDF resume.

The portfolio JSON is the primary source of truth. The PDF CV is an older,
secondary source: when facts conflict the portfolio JSON wins.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_JSON = ROOT / "src" / "data" / "portfolioKnowledge.json"
CV_PATH = ROOT / "public" / "Gulshan Kumar CV.pdf"

STOPWORDS = {
    "a", "about", "am", "an", "and", "are", "at", "be", "can", "could", "do", "does",
    "for", "from", "give", "gulshan", "has", "have", "he", "his", "how", "i", "in",
    "is", "it", "kumar", "me", "more", "my", "of", "on", "or", "please", "show", "tell",
    "that", "the", "their", "there", "these", "this", "to", "was", "what", "when", "where",
    "which", "who", "why", "with", "worked", "work", "you", "your", "him", "any",
}


def _terms(text: str) -> set[str]:
    # Keep programming terms like C++, C#, Node.js and Next.js intact.
    tokens = re.findall(r"[a-z0-9]+(?:[.+#-][a-z0-9+#]+)*", text.lower())
    synonyms = {
        "projects": "project", "skills": "skill", "technologies": "technology",
        "agents": "agent", "models": "model", "systems": "system", "degrees": "degree",
        "experiences": "experience", "repositories": "repository", "jobs": "job",
    }
    return {synonyms.get(t, t) for t in tokens if t not in STOPWORDS and len(t) > 1}


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    text: str
    url: str
    kind: str
    priority: float = 1.0

    def link(self) -> dict[str, str]:
        return {"id": self.id, "title": self.title, "url": self.url}


def build_documents(data: dict[str, Any], cv_path: Path | None = CV_PATH) -> list[SourceDocument]:
    docs: list[SourceDocument] = []
    profile = data["profile"]
    docs.append(SourceDocument(
        "profile", "Professional profile", "\n".join([
            f"Name: {profile['name']}",
            f"Headline: {profile['headline']}",
            f"Introduction: {profile['intro']}",
            f"Contact email: {profile['email']}",
            f"GitHub: {profile['github']}",
            f"LinkedIn: {profile['linkedin']}",
            *profile["about"],
            *(["Spoken languages: " + ", ".join(profile["languages"])] if profile.get("languages") else []),
        ]), "/#about", "portfolio", 1.5,
    ))

    for entry in data.get("education", []):
        docs.append(SourceDocument(
            f"education:{entry['id']}", f"Education: {entry['institution']}",
            f"Education at {entry['institution']}. {entry['degree']}. Dates: {entry['years']}. {entry.get('detail', '')}",
            "/#education", "portfolio", 1.6,
        ))

    for entry in data.get("experience", []):
        docs.append(SourceDocument(
            f"experience:{entry['id']}", f"Experience: {entry['organization']}",
            f"Professional work experience at {entry['organization']}. Role: {entry['role']}. Period: {entry['period']}. {entry['details']}",
            entry.get("link", "/#workexperience"), "portfolio", 1.5,
        ))

    for entry in data.get("projects", []):
        if entry.get("id") in {"pig", "timer"}:
            continue
        tech = ", ".join(entry.get("tech", []))
        docs.append(SourceDocument(
            f"project:{entry['id']}", f"Project: {entry['name']}",
            f"Project {entry['name']}. Category: {entry['category']}. {entry['description']} Technologies: {tech}. "
            f"GitHub repository: {entry.get('githubLink', 'not published')}. "
            + (f"Live demo: {entry['liveLink']}" if entry.get("liveLink") else ""),
            entry.get("githubLink", "/#projects"), "portfolio", 1.5,
        ))

    for idx, skills in enumerate(data.get("extraSkills", [])):
        docs.append(SourceDocument(
            f"skills:{idx}", f"Technical skills: {skills['category']}",
            f"Technical skills in {skills['category']}: {', '.join(skills['items'])}.",
            "/#skillset", "portfolio", 1.4,
        ))

    # The published PDF includes older content; keep it supplemental and lower-priority.
    if cv_path and cv_path.exists():
        from pypdf import PdfReader
        reader = PdfReader(str(cv_path))
        for page_number, page in enumerate(reader.pages, 1):
            raw = page.extract_text() or ""
            # Avoid inadvertently repeating a personal phone number in responses.
            raw = re.sub(r"\+46\s*(?:\d[\s-]*){7,12}", "[phone omitted]", raw)
            text = " ".join(raw.split())
            if not text:
                continue
            # Overlap is intentionally limited for this small resume.
            for n, start in enumerate(range(0, len(text), 750)):
                part = text[start:start + 900]
                if part:
                    docs.append(SourceDocument(
                        f"cv:p{page_number}:{n}", f"CV (older copy), page {page_number}",
                        "Older CV content, potentially superseded by current portfolio: " + part,
                        "/Gulshan%20Kumar%20CV.pdf", "cv", 0.35,
                    ))
    return docs


class KnowledgeStore:
    """Reload changed files automatically; optional semantic retrieval via ChromaDB."""

    def __init__(self, json_path: Path = KNOWLEDGE_JSON, cv_path: Path = CV_PATH):
        self.json_path = json_path
        self.cv_path = cv_path
        self._lock = RLock()
        self._fingerprint: tuple | None = None
        self.documents: list[SourceDocument] = []
        self.by_id: dict[str, SourceDocument] = {}
        self.data: dict[str, Any] = {}
        self.semantic = None
        self._embedding_model = None

    def _stat_key(self) -> tuple:
        def st(path: Path) -> tuple:
            if not path.exists():
                return (False, 0, 0)
            x = path.stat()
            return (True, x.st_size, x.st_mtime_ns)
        return st(self.json_path), st(self.cv_path)

    def refresh(self) -> None:
        with self._lock:
            fingerprint = self._stat_key()
            if fingerprint == self._fingerprint:
                return
            with self.json_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            new_docs = build_documents(data, self.cv_path)
            self.data = data
            self.documents = new_docs
            self.by_id = {d.id: d for d in new_docs}
            self._fingerprint = fingerprint
            if os.getenv("ENABLE_SEMANTIC", "0") == "1":
                self._prepare_semantic()

    def _prepare_semantic(self) -> None:
        # Optional enhancement: set ENABLE_SEMANTIC=1 after installing
        # requirements-semantic.txt. The lexical index works without it.
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "ENABLE_SEMANTIC=1 requires: pip install -r backend/requirements-semantic.txt"
            ) from exc
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        client = chromadb.PersistentClient(path=str(ROOT / "backend" / ".chromadb"))
        collection = client.get_or_create_collection("portfolio_knowledge")
        # The content set is small: rebuild it to remove stale or deleted entries.
        existing = collection.get().get("ids", [])
        if existing:
            collection.delete(ids=existing)
        if self.documents:
            embeds = self._embedding_model.encode(
                [d.text for d in self.documents], normalize_embeddings=True
            ).tolist()
            collection.upsert(
                ids=[d.id for d in self.documents],
                documents=[d.text for d in self.documents],
                embeddings=embeds,
                metadatas=[{"title": d.title, "kind": d.kind} for d in self.documents],
            )
        self.semantic = collection

    def curated_overview(self) -> tuple[str, list[SourceDocument]]:
        """Compose a factual introduction from structured portfolio data, without an LLM."""
        self.refresh()
        with self._lock:
            data = self.data
            profile = data["profile"]
            degrees = data.get("education", [])
            jobs = data.get("experience", [])
            featured = [item for item in data.get("projects", []) if item.get("featured")]
            lines = [profile.get("intro", "").strip()]
            if degrees:
                primary = degrees[0]
                lines.append(f"Education: {primary['degree']} at {primary['institution']} ({primary['years']}).")
                if len(degrees) > 1:
                    previous = degrees[1]
                    lines.append(f"He also completed {previous['degree']} at {previous['institution']} ({previous['years']}).")
            if jobs:
                featured_jobs = [job for job in jobs if job.get("id") in {"dnb", "permitto"}] or jobs[:2]
                lines.append("Experience includes " + "; ".join(
                    f"{job['role']} at {job['organization']}" for job in featured_jobs[:3]
                ) + ".")
            if featured:
                lines.append("Featured projects include " + ", ".join(
                    project["name"] for project in featured[:4]
                ) + ".")
            lines.append("You can ask me about any of these areas, or request a specific project or technology.")
            ids = ["profile"]
            ids.extend(f"education:{item['id']}" for item in degrees[:2])
            ids.extend(f"experience:{item['id']}" for item in jobs if item.get("id") in {"dnb", "permitto"})
            ids.extend(f"project:{item['id']}" for item in featured[:2])
            docs = [self.by_id[item_id] for item_id in ids if item_id in self.by_id]
            return "\n\n".join(filter(None, lines)), docs

    def curated_category(self, category: str) -> tuple[str, list[SourceDocument]]:
        """Provide compact, evidence-backed answers to common recruiter questions offline."""
        self.refresh()
        with self._lock:
            data = self.data
            ids: list[str] = []
            lines: list[str] = []
            if category == "experience":
                lines.append("Gulshan's published professional experience includes:")
                for job in data.get("experience", []):
                    lines.append(f"• {job['role']} at {job['organization']} ({job['period']}). {job['details']}")
                    ids.append(f"experience:{job['id']}")
            elif category == "education":
                lines.append("Gulshan's education:")
                for item in data.get("education", []):
                    lines.append(f"• {item['degree']} at {item['institution']} ({item['years']}). {item.get('detail', '')}")
                    ids.append(f"education:{item['id']}")
            elif category == "projects":
                lines.append("Some of Gulshan's featured projects are:")
                for item in data.get("projects", []):
                    if item.get("featured") and item.get("id") not in {"pig", "timer"}:
                        tech = ", ".join(item.get("tech", []))
                        lines.append(f"• {item['name']}: {item['description']} Tech: {tech}.")
                        ids.append(f"project:{item['id']}")
            elif category == "skills":
                lines.append("Gulshan's published technical skills include:")
                for i, skill in enumerate(data.get("extraSkills", [])):
                    lines.append(f"• {skill['category']}: {', '.join(skill['items'])}.")
                    ids.append(f"skills:{i}")
            docs = [self.by_id[item_id] for item_id in ids if item_id in self.by_id]
            return "\n\n".join(lines), docs

    def approved_languages(self) -> list[str]:
        """Spoken languages must be explicitly entered into public profile data."""
        self.refresh()
        with self._lock:
            return list(self.data.get("profile", {}).get("languages") or [])

    def search(self, question: str, limit: int = 5) -> list[SourceDocument]:
        self.refresh()
        words = _terms(question)
        with self._lock:
            # If the question is very general, lead with the verified profile.
            if not words:
                return [self.by_id["profile"]]
            # Don't invent a Master's thesis title from a Bachelor's thesis entry.
            if {"master", "thesis"}.issubset(words) and not any(
                ("master's thesis" in d.text.lower() or "master thesis" in d.text.lower())
                for d in self.documents
            ):
                return []
            scores: dict[str, float] = {}
            about_projects = "project" in words
            about_education = "education" in words or "degree" in words
            about_experience = "experience" in words or "internship" in words

            for d in self.documents:
                title_words = _terms(d.title)
                doc_words = _terms(d.text)
                common = words & doc_words
                if not common:
                    continue
                if (about_projects and "ai" in words and d.id.startswith("project:")
                        and "ai" not in doc_words and "rag" not in doc_words):
                    continue
                title_hits = len(words & title_words)
                relevance_boost = 1.0
                if about_projects and d.id.startswith("project:"):
                    relevance_boost = 2.0
                elif about_education and d.id.startswith("education:"):
                    relevance_boost = 1.8
                elif about_experience and d.id.startswith("experience:"):
                    relevance_boost = 1.8
                scores[d.id] = (len(common) + title_hits * 1.8) * d.priority * relevance_boost

            if self.semantic is not None and self._embedding_model is not None:
                embedding = self._embedding_model.encode(
                    [question], normalize_embeddings=True
                ).tolist()
                result = self.semantic.query(query_embeddings=embedding, n_results=min(8, len(self.documents)))
                for rank, doc_id in enumerate(result.get("ids", [[]])[0]):
                    doc = self.by_id.get(doc_id)
                    if doc and doc.kind == "portfolio":
                        scores[doc_id] = scores.get(doc_id, 0) + (2.4 / (rank + 1))
            ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
            return [self.by_id[doc_id] for doc_id, _ in ranked[:limit]]
