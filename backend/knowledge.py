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
import logging
from typing import Any

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_JSON = ROOT / "src" / "data" / "portfolioKnowledge.json"
CV_PATH = ROOT / "public" / "Gulshan Kumar CV.pdf"
PUBLIC_FACTS_PATH = ROOT / "public" / "profile-facts.json"
from .source_sync import GITHUB_CACHE, LINKEDIN_CACHE, load_json

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
        "projects": "project", "rags": "rag", "skills": "skill", "technologies": "technology",
        "languages": "language", "langauges": "language", "langauge": "language",
        "agents": "agent", "models": "model", "systems": "system", "degrees": "degree",
        "experiences": "experience", "repositories": "repository", "jobs": "job",
        # Natural ways a visitor may ask about someone's professional direction.
        "goals": "goal", "ambitions": "goal", "ambition": "goal",
        "aspirations": "goal", "aspiration": "goal", "aims": "goal", "aim": "goal",
        "objectives": "goal", "objective": "goal", "achieve": "goal",
        "future": "goal", "wants": "goal", "want": "goal",
        "interests": "interest", "interested": "interest",
        "motivations": "motivation", "motivates": "motivation", "motivated": "motivation",
        "lessons": "lesson", "learned": "lesson", "learnt": "lesson",
        "certifications": "certification", "certificates": "certification",
        "certified": "certification", "credentials": "certification",
        "commits": "commit", "committed": "commit",
        "speak": "spoken", "speaks": "spoken",
        "based": "location", "city": "location", "address": "location",
        "currently": "current", "ongoing": "current", "active": "current",
        "nowadays": "current", "certificates": "certification",
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


def _spoken_languages_in_cv(text: str) -> list[str]:
    """Extract only the spoken-language section, not 'Programming Languages'."""
    match = re.search(
        r"(?m)^\s*Languages\s*$\n(?P<body>.*?)(?=^\s*(?:References|Education|Projects|Thesis|Work Experience)\s*$|\Z)",
        text,
        flags=re.S | re.M,
    )
    if not match:
        return []
    languages: list[str] = []
    for line in match.group("body").splitlines():
        clean = line.strip().lstrip("•·\uf0b7- ").strip()
        entry = re.match(r"^([A-Za-z][A-Za-z ]{1,32})\s*[–—-]\s*(.{3,75})$", clean)
        if entry:
            languages.append(f"{entry.group(1).strip()} ({entry.group(2).strip()})")
    return languages[:10]


def _language_values_from_doc(doc: SourceDocument) -> list[str]:
    value = doc.text.split(":", 1)[-1].strip().rstrip(".")
    return [part.strip() for part in value.split(";") if part.strip()]


# Section recognition describes the CV *format*, not predetermined answers.
# All sections receive the same indexing treatment.
CV_HEADINGS = {
    "professional summary", "summary", "profile", "about me", "contact",
    "technical skills", "skills", "programming languages", "frameworks & technologies",
    "work experience", "professional experience", "experience", "employment",
    "education", "academic background", "thesis", "bachelor thesis",
    "bachelor's thesis", "bachelor’s thesis", "master thesis", "master's thesis",
    "projects", "projects & achievements", "projects and achievements",
    "certification", "certifications", "certificates", "courses", "training",
    "licenses & certifications", "licenses and certifications", "languages",
    "awards", "achievements", "volunteer experience", "publications",
    "interests", "references", "research", "research experience",
}


def _cv_heading(line: str) -> str | None:
    heading = re.sub(r"\s+", " ", line.strip().strip(":").strip()).lower()
    return heading if heading in CV_HEADINGS else None


def _cv_section_documents(page_text: str, page_number: int) -> list[SourceDocument]:
    """Extract complete CV sections with original page citations.

    A new heading starts a new record. Headers and experience remain searchable,
    and no field such as 'thesis' or 'certifications' receives special answers.
    """
    lines = [line.strip() for line in page_text.splitlines() if line.strip()]
    sections: list[tuple[str, list[str]]] = []
    current_heading = "identity and location"
    current_lines: list[str] = []
    for line in lines:
        heading = _cv_heading(line)
        if heading:
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading, current_lines = heading, []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))
    result: list[SourceDocument] = []
    counts: dict[str, int] = {}
    for heading, body in sections:
        text = " ".join(body).strip()
        if not text:
            continue
        # Filter sensitive contact details before they enter RAG or the LLM.
        text = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email omitted]", text)
        text = re.sub(r"(?:\+\d{1,3}[ -]?)?(?:\d[ -]?){9,14}", "[phone omitted]", text)
        slug = re.sub(r"[^a-z0-9]+", "_", heading).strip("_")
        counts[slug] = counts.get(slug, 0) + 1
        if heading == "languages":
            doc_id = "cv:languages" if counts[slug] == 1 else f"cv:languages:p{page_number}:{counts[slug]}"
            label = "CV: Spoken languages"
        elif "thesis" in heading:
            doc_id = f"cv:thesis:p{page_number}"
            label = "CV: Thesis"
        else:
            doc_id = f"cv:section:{slug}:p{page_number}:{counts[slug]}"
            label = "CV: " + heading.title()
        result.append(SourceDocument(
            doc_id, label, f"CV section {heading.title()}: {text[:1900]}",
            f"/Gulshan%20Kumar%20CV.pdf#page={page_number}", "cv",
            1.35 if heading != "identity and location" else 0.9,
        ))
    return result


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
            f"project:{entry['id']}", f"Project: {entry['name']} ({entry['category']})",
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

    # Index every recognizable CV section, with page-level fallback for layouts
    # that do not expose headings cleanly. There are no field-specific answers.
    if cv_path and cv_path.exists():
        from pypdf import PdfReader
        reader = PdfReader(str(cv_path))
        for page_number, page in enumerate(reader.pages, 1):
            raw = page.extract_text() or ""
            docs.extend(_cv_section_documents(raw, page_number))
            raw = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "[email omitted]", raw)
            raw = re.sub(r"(?:\+\d{1,3}[ -]?)?(?:\d[ -]?){9,14}", "[phone omitted]", raw)
            text = " ".join(raw.split())
            # Full-page fallback, lower-weight so section evidence wins.
            if text:
                for n, pos in enumerate(range(0, len(text), 1300)):
                    segment = text[pos:pos + 1450]
                    if segment:
                        docs.append(SourceDocument(
                            f"cv:p{page_number}:{n}", f"CV page {page_number}",
                            "Published CV page content: " + segment,
                            f"/Gulshan%20Kumar%20CV.pdf#page={page_number}", "cv", .35,
                        ))
    return docs


class KnowledgeStore:
    """Reload verified files and optionally combine BM25 with local dense search."""

    def __init__(self, json_path: Path = KNOWLEDGE_JSON, cv_path: Path = CV_PATH,
                 facts_path: Path | None = None, github_path: Path | None = None,
                 linkedin_path: Path | None = None):
        self.json_path = json_path
        self.cv_path = cv_path
        # Custom stores used by tests or external consumers do not inherit this
        # portfolio's public facts unless they opt into a facts_path explicitly.
        self.facts_path = (PUBLIC_FACTS_PATH if json_path == KNOWLEDGE_JSON else None) if facts_path is None else facts_path
        self.github_path = (GITHUB_CACHE if json_path == KNOWLEDGE_JSON else None) if github_path is None else github_path
        self.linkedin_path = (LINKEDIN_CACHE if json_path == KNOWLEDGE_JSON else None) if linkedin_path is None else linkedin_path
        self._lock = RLock()
        self._fingerprint: tuple | None = None
        self.documents: list[SourceDocument] = []
        self.by_id: dict[str, SourceDocument] = {}
        self.data: dict[str, Any] = {}
        self.semantic = None
        self.semantic_error: str | None = None
        self._semantic_model_name: str | None = None

    def _stat_key(self) -> tuple:
        def st(path: Path) -> tuple:
            if not path.exists():
                return (False, 0, 0)
            x = path.stat()
            return (True, x.st_size, x.st_mtime_ns)
        return (st(self.json_path), st(self.cv_path),
                (st(self.facts_path) if self.facts_path else None),
                (st(self.github_path) if self.github_path else None),
                (st(self.linkedin_path) if self.linkedin_path else None))

    def refresh(self) -> None:
        with self._lock:
            fingerprint = self._stat_key()
            if fingerprint == self._fingerprint:
                if os.getenv("ENABLE_SEMANTIC", "0") == "1" and self.semantic is None and not self.semantic_error:
                    self._prepare_semantic()
                return
            with self.json_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            new_docs = build_documents(data, self.cv_path)
            if self.facts_path and self.facts_path.is_file():
                with self.facts_path.open("r", encoding="utf-8") as facts_file:
                    facts = json.load(facts_file)
                approved = []
                for item in facts.get("spokenLanguages", []):
                    if isinstance(item, dict):
                        name = str(item.get("language", "")).strip()
                        proficiency = str(item.get("proficiency", "")).strip()
                        if name and proficiency:
                            approved.append(f"{name} ({proficiency})")
                if approved:
                    new_docs.append(SourceDocument(
                        "profile:languages", "Verified spoken languages",
                        "Spoken languages in Gulshan's public profile: " + "; ".join(approved) + ".",
                        "/profile-facts.json", "portfolio", 1.5,
                    ))
                # Source facts remain separate from frameworks and libraries.
                # These are programming languages explicitly represented by
                # the skill cards, not inferred from a mention of a framework.
                programming = [str(item).strip() for item in facts.get("programmingLanguages", [])
                               if isinstance(item, str) and item.strip()]
                if programming:
                    new_docs.append(SourceDocument(
                        "profile:programming_languages", "Verified programming languages",
                        "Programming languages Gulshan has used: " + ", ".join(programming) + ". "
                        "These are programming languages, distinct from spoken languages and from tools/frameworks.",
                        "/profile-facts.json", "portfolio", 1.7,
                    ))
                current = []
                for item in facts.get("currentProjects", []):
                    if not isinstance(item, dict) or item.get("status") != "in_progress":
                        continue
                    name = str(item.get("name", "")).strip()
                    description = str(item.get("description", "")).strip()
                    as_of = str(item.get("asOf", "")).strip()
                    if name and description and re.fullmatch(r"\d{4}-\d{2}-\d{2}", as_of):
                        current.append((name, description, as_of))
                if current:
                    new_docs.append(SourceDocument(
                        "profile:current_projects", "Active development projects (dated status)",
                        "Current projects: Project status explicitly marked in progress, as of the stated date (not live GitHub status):\n"
                        + "\n".join(f"{name}. As of {as_of}: {description}" for name, description, as_of in current)
                        + "\nOther featured or completed projects are NOT necessarily ongoing.",
                        "/profile-facts.json", "portfolio", 2.0,
                    ))
                # Link locally developed AI features to their actual GitHub
                # repositories without claiming those changes have been pushed.
                for project in facts.get("currentProjects", []):
                    if not isinstance(project, dict):
                        continue
                    repo = str(project.get("repository", "")).strip()
                    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", repo):
                        continue
                    name = str(project.get("name", "")).strip()
                    relationship = str(project.get("relationship", "")).strip()
                    publication = str(project.get("publicationNote", "")).strip()
                    date = str(project.get("asOf", "")).strip()
                    if not (name and relationship and publication):
                        continue
                    new_docs.append(SourceDocument(
                        f"profile:repo_relation:{repo.lower()}",
                        f"Verified project/repository relationship: {name}",
                        f"Local project: {name}. GitHub repository: https://github.com/{repo}. "
                        f"As of {date}: {relationship} {publication}",
                        "/profile-facts.json", "portfolio", 2.1,
                    ))
                # Professional direction is explicitly endorsed by Gulshan.
                # Keep goals, interests, motivation and lessons separate, so a
                # broad chat question retrieves the relevant personal evidence.
                direction = facts.get("professionalDirection", {})
                if isinstance(direction, dict) and direction.get("status") == "user_endorsed_professional_direction":
                    reviewed_on = str(direction.get("reviewedOn", "")).strip()
                    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", reviewed_on):
                        sections = (
                            ("careerGoals", "profile:career_goals", "Career goal and professional ambitions",
                             "Career goal and professional ambitions endorsed by Gulshan"),
                            ("professionalInterests", "profile:professional_interests", "Professional interests and focus areas",
                             "Professional interest and focus areas"),
                            ("motivation", "profile:motivation", "Motivation for building AI tools",
                             "Motivation and curiosity behind Gulshan's software and AI work"),
                            ("projectLearnings", "profile:project_learnings", "Website RAG Assistant lessons and challenges",
                             "Lessons learned and challenges encountered in Gulshan's Website RAG Assistant"),
                        )
                        for field, doc_id, title, lead in sections:
                            entries = [str(item).strip() for item in direction.get(field, [])
                                       if isinstance(item, str) and item.strip()]
                            if entries:
                                new_docs.append(SourceDocument(
                                    doc_id, title,
                                    f"{lead} (reviewed {reviewed_on}): " + " ".join(entries)
                                    + " These facts describe professional direction or past experience, not guaranteed future outcomes.",
                                    "/profile-facts.json", "portfolio",
                                    1.25 if field == "projectLearnings" else 2.15,
                                ))
            # Read-only third-party source snapshots are always *evidence*, not
            # instructions and not user-verified claims of employment or status.
            for cache_path, provider, max_documents in (
                (self.github_path, 'github', 180),
                (self.linkedin_path, 'linkedin', 350),
            ):
                if not cache_path or not cache_path.is_file():
                    continue
                try:
                    raw_cache = load_json(cache_path)
                    for source in raw_cache.get('documents', [])[:max_documents]:
                        if not isinstance(source, dict) or source.get('kind') != provider:
                            continue
                        title = str(source.get('title', ''))[:180]
                        text = str(source.get('text', ''))[:13000]
                        uri = str(source.get('url', ''))[:350]
                        source_id = str(source.get('id', ''))[:200]
                        if not title or not text or not source_id or not source_id.startswith(provider + ':'):
                            continue
                        if provider == 'github' and not uri.startswith('https://github.com/'):
                            continue
                        if provider == 'linkedin' and uri and not uri.startswith('https://www.linkedin.com/in/'):
                            continue
                        new_docs.append(SourceDocument(source_id, title, text, uri,
                                                       provider, min(float(source.get('priority', 1)), 1.1)))
                except (OSError, ValueError, TypeError, KeyError) as exc:
                    logger.warning('Unable to load %s snapshot (%s)', provider, type(exc).__name__)
            self.data = data
            self.documents = new_docs
            self.by_id = {d.id: d for d in new_docs}
            self._fingerprint = fingerprint
            if os.getenv("ENABLE_SEMANTIC", "0") == "1":
                self._prepare_semantic()

    @property
    def semantic_ready(self) -> bool:
        return self.semantic is not None and bool(self.semantic.vectors)

    def _prepare_semantic(self) -> None:
        """Initialize embeddings lazily on first search, then refresh changed docs.

        Embedding setup must not bring down the API or Groq conversation when
        dependencies or model downloads are unavailable.
        """
        if self.semantic_error:
            return
        try:
            from .semantic import DEFAULT_MODEL, LocalSemanticIndex
            model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL
            if self.semantic is None or self._semantic_model_name != model_name:
                self.semantic = LocalSemanticIndex(model_name=model_name)
                self._semantic_model_name = model_name
            self.semantic.build(self.documents)
        except Exception as exc:
            self.semantic = None
            self._semantic_model_name = None
            self.semantic_error = type(exc).__name__
            logger.warning("Local semantic search unavailable (%s); using lexical search", type(exc).__name__)

    def languages_with_source(self, prefer_cv: bool = False) -> tuple[list[str], SourceDocument | None, str]:
        """Return spoken-language facts and distinguish current CV vs saved profile."""
        self.refresh()
        with self._lock:
            cv_document = self.by_id.get("cv:languages")
            verified_document = self.by_id.get("profile:languages")
            inline_profile = list(self.data.get("profile", {}).get("languages") or [])
            if cv_document:
                # Direct evidence from the current PDF takes priority for this fact.
                return _language_values_from_doc(cv_document), cv_document, "CV"
            if verified_document:
                return _language_values_from_doc(verified_document), verified_document, "saved public profile"
            if inline_profile:
                return inline_profile, self.by_id.get("profile"), "public profile"
            return [], None, "none"

    def approved_languages(self) -> list[str]:
        # Compatibility for existing callers: only published, evidenced facts.
        return self.languages_with_source()[0]

    def search(self, question: str, limit: int = 6, kind: str | None = None) -> list[SourceDocument]:
        """Hybrid ranker: BM25 + optional FastEmbed dense-vector retrieval.

        ENABLE_SEMANTIC=1 loads a local ONNX embedding model. When disabled or
        unavailable, the previous BM25 behavior is preserved.
        """
        from collections import Counter
        import math

        self.refresh()
        words = _terms(question)
        # Normalize everyday spoken-language questions to the published field.
        aliases = {
            "speak": "spoken", "speaks": "spoken", "spoken": "spoken",
            "fluent": "language", "languages": "language", "intern": "internship",
            "developer": "development", "built": "project", "build": "project",
            "studying": "education", "university": "education",
        }
        words = {aliases.get(word, word) for word in words}
        # Generic question framing should not overwhelm the actual subject.
        # This is domain-neutral weighting, not a rule for Android or any other
        # individual answer. Keep generic words if there is no specific subject.
        broad_terms = {'experience', 'project', 'skill', 'work', 'developer',
                       'development', 'technology', 'knowledge', 'background',
                       'level', 'much', 'many', 'detail', 'details', 'information',
                       'completed', 'complete', 'currently', 'nowadays', 'recently'}
        substantive = words - broad_terms
        if substantive:
            words = substantive
        if not words:
            return [self.by_id["profile"]] if "profile" in self.by_id else []
        with self._lock:
            eligible = [doc for doc in self.documents if kind is None or doc.kind == kind]

            corpus = []
            for doc in eligible:
                text = _terms(doc.text + " " + doc.title + " " + doc.title)
                normalized = [aliases.get(t, t) for t in text]
                corpus.append(Counter(normalized))
            n = len(corpus)
            if not n:
                return []
            lengths = [sum(counts.values()) for counts in corpus]
            avg_length = sum(lengths) / n or 1
            doc_freq = Counter(term for counts in corpus for term in counts)
            scores = {}
            for doc, count, length in zip(eligible, corpus, lengths):
                total = 0.0
                for term in words:
                    frequency = count.get(term, 0)
                    if not frequency:
                        continue
                    idf = math.log1p((n - doc_freq[term] + 0.5) / (doc_freq[term] + 0.5))
                    total += idf * (frequency * 2.2) / (frequency + 1.2 * (0.25 + 0.75 * length / avg_length))
                if total > 0:
                    # A named match in a title is more informative than a
                    # generic word buried in an unrelated section.
                    title_words = {aliases.get(t, t) for t in _terms(doc.title)}
                    title_matches = len(words & title_words)
                    boost = (1.15 if doc.kind == "portfolio" else 1.0) * (1 + 1.3 * title_matches)
                    if re.search(r"\b(current|currently|now|attend|attending)\b", question.lower()) and "present" in doc.text.lower():
                        boost *= 1.5
                    scores[doc.id] = total * doc.priority * boost

            lexical_order = sorted(scores, key=lambda doc_id: (-scores[doc_id], doc_id))
            if os.getenv("ENABLE_SEMANTIC", "0") != "1" or not self.semantic_ready:
                return [self.by_id[doc_id] for doc_id in lexical_order[:limit]]

            # Reciprocal Rank Fusion. Semantic and BM25 scores have unrelated
            # units, so fuse their rankings instead of adding raw numbers.
            # Dense retrieval can surface evidence even when there are no
            # exact word matches (e.g. 'phone apps' vs 'Android development').
            try:
                dense_matches = self.semantic.search(
                    question, eligible_ids={doc.id for doc in eligible}, limit=min(15, n)
                )
            except Exception as exc:
                logger.warning("Semantic query failed (%s); using lexical search", type(exc).__name__)
                return [self.by_id[doc_id] for doc_id in lexical_order[:limit]]

            if not dense_matches:
                return [self.by_id[doc_id] for doc_id in lexical_order[:limit]]

            combined: dict[str, float] = {}
            for rank, doc_id in enumerate(lexical_order, start=1):
                combined[doc_id] = combined.get(doc_id, 0.0) + 1.0 / (25 + rank)
            for rank, match in enumerate(dense_matches, start=1):
                combined[match.document_id] = (
                    combined.get(match.document_id, 0.0) + 0.9 / (25 + rank)
                )
            # Ground relevance in the source title as well as dense similarity.
            # The semantic model should not hide a precise CV section under
            # unrelated generic profile text.
            for doc_id in combined:
                overlap = len(words & _terms(self.by_id[doc_id].title))
                combined[doc_id] *= (1 + 0.6 * overlap)
            # Curated/current facts are stronger evidence than old CV chunks.
            for doc_id in combined:
                priority = self.by_id[doc_id].priority
                combined[doc_id] *= 0.65 + min(priority, 2.0) * 0.35
            ordered = sorted(combined, key=lambda doc_id: (-combined[doc_id], doc_id))
            # For a sufficiently specific query, a single document that
            # supports all the substantive concepts is stronger evidence than
            # an unrelated high-similarity passage. No field-specific rules.
            if len(words) >= 2:
                grounded = [doc_id for doc_id in ordered
                            if words <= _terms(self.by_id[doc_id].title + ' ' + self.by_id[doc_id].text)]
                anchored = [doc_id for doc_id in grounded
                            if words & _terms(self.by_id[doc_id].title)]
                if anchored:
                    ordered = anchored + [doc_id for doc_id in grounded if doc_id not in anchored] + [doc_id for doc_id in ordered if doc_id not in grounded]
            return [self.by_id[doc_id] for doc_id in ordered[:limit]]


def _thesis_section_in_cv(page_text: str) -> str | None:
    """Backward-compatible helper; runtime indexing uses generic CV sections."""
    for doc in _cv_section_documents(page_text, 1):
        if doc.id.startswith('cv:thesis'):
            return doc.text.split(': ', 1)[-1]
    return None
