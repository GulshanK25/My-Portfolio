"""Read-only, source-aware tools for Gulshan AI's LLM-controlled agent.

Tool names describe capabilities, never visitor question templates. External
content is evidence rather than an instruction, and visitors cannot write facts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from .github_commits import GitHubCommitReader
from .knowledge import KnowledgeStore, SourceDocument, _terms
from .project_catalog import ai_repository_evidence
from .source_sync import load_json


TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_professional_overview",
        "description": (
            "Read Gulshan's verified professional introduction, education, experience, "
            "featured projects and career interests. Use for broad questions about who "
            "Gulshan is, his background, or what you know about him. "
            "Use this before asserting a personal biography."
        ),
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "search_professional_knowledge",
        "description": (
            "Search owner-approved portfolio data, CV, project descriptions and synced "
            "public sources. Use for Gulshan-specific facts including study, projects, "
            "skills, job history, thesis, certifications, interests and follow-ups. "
            "Search using the meaning of the visitor's question and conversation context. "
            "Do not use for ordinary general-knowledge questions or casual chat."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Meaningful natural-language search query including any resolved subject."},
        }, "required": ["query"], "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "inspect_professional_work_and_projects",
        "description": (
            "Inspect the COMPLETE owner-approved portfolio catalog of work roles and "
            "software projects, including non-featured and mobile projects. Use when "
            "evaluating the breadth of Gulshan's experience, comparing employment "
            "with personal/academic/collaborative projects, or determining whether "
            "a kind of app or project is represented. A portfolio project or GitHub "
            "repository does NOT by itself establish employment, a paid client, "
            "a lead role, or completed/production-ready features."
        ),
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "Optional topic to prioritize source links; full catalog is always returned."},
        }, "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "list_public_repositories",
        "description": (
            "Get the synchronized public GitHub repository inventory with exact names, "
            "links and last-push metadata. Use for account-wide lists, recently pushed "
            "repositories, or identifying AI-related repositories. A push is not a "
            "commit or proof of ongoing work. Private repositories are excluded."
        ),
        "parameters": {"type": "object", "properties": {
            "focus": {"type": "string", "enum": ["all", "ai"], "description": "Optional AI evidence filter."},
            "sort": {"type": "string", "enum": ["recent", "name"], "description": "Order, default recent."},
        }, "additionalProperties": False},
    }},
    {"type": "function", "function": {
        "name": "get_latest_public_commit",
        "description": (
            "Fetch the latest commit on a specific public GitHub repository's default "
            "branch, including exact date, message and changed files. This performs a "
            "read-only live GitHub API request. If no repository is known, ask which one."
        ),
        "parameters": {"type": "object", "properties": {
            "repository": {"type": "string", "description": "Public repository name or owner/repo (e.g. Scrapper-chatbox)."},
        }, "required": ["repository"], "additionalProperties": False},
    }},
]


@dataclass
class ToolResult:
    value: dict[str, Any]
    sources: list[dict[str, str]] = field(default_factory=list)

    def content(self) -> str:
        return json.dumps(self.value, ensure_ascii=False, separators=(",", ":"))


class ReadOnlyTools:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.commits = GitHubCommitReader(cache_path=store.github_path) if store.github_path else None

    @staticmethod
    def _pack(doc: SourceDocument, max_chars: int = 1250) -> dict:
        return {"title": doc.title, "type": doc.kind, "source_id": doc.id,
                "url": doc.url, "evidence": doc.text[:max_chars]}

    @staticmethod
    def _sources(documents: list[SourceDocument]) -> list[dict[str, str]]:
        return [doc.link() for doc in documents]

    def _overview(self) -> ToolResult:
        self.store.refresh()
        docs = self.store.documents
        # This collection is based on source roles/records, not question phrasing.
        profile = [doc for doc in docs if doc.id == "profile"]
        education = [doc for doc in docs if doc.id.startswith("education:")]
        work = [doc for doc in docs if doc.id.startswith("experience:")]
        interests = [doc for doc in docs if doc.id in {
            "profile:career_goals", "profile:professional_interests", "profile:current_projects"}]
        projects = [doc for doc in docs if doc.id.startswith("project:")]
        # Show a representative selection based on the portfolio's presentation order.
        selected = (profile[:1] + education[:3] + work[:3] + interests[:3] + projects[:3])
        return ToolResult({
            "type": "professional_overview",
            "note": "Owner-approved profile and published materials, not a complete biography. Dates may be historical.",
            "records": [self._pack(doc, 550 if doc.id.startswith("project:") else 750) for doc in selected],
        }, self._sources(selected))

    def _search(self, args: dict) -> ToolResult:
        query = args.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return ToolResult({"error": "A nonempty search query is required."})
        # Keep tool outputs compact; cap untrusted query size.
        query = query.strip()[:380]
        docs = self.store.search(query, limit=10)
        # Category/facet coverage is based on published project metadata, not
        # particular visitor phrases or prewritten project answers. Similarity
        # top-k alone can omit half the projects in a category (e.g. mobile).
        terms = _terms(query)
        category_matches = []
        for project in self.store.data.get("projects", []):
            if not isinstance(project, dict):
                continue
            project_id = project.get("id")
            doc = self.store.by_id.get("project:" + str(project_id))
            if doc is None:
                continue
            facets = [str(project.get("category", ""))] + [
                str(f) for f in project.get("filterCategories", []) if isinstance(f, str)
            ]
            if any(_terms(facet) and _terms(facet) <= terms for facet in facets):
                category_matches.append(doc)
        merged = list(category_matches)
        merged.extend(d for d in docs if d.id not in {m.id for m in merged})
        selected = merged[:6]
        return ToolResult({
            "query": query[:200],
            "record_count": len(selected),
            "category_matches": len(category_matches),
            "records": [self._pack(d, 850) for d in selected],
            "note": "Search results are potential evidence and not a complete project inventory. Never infer that a project does not exist just because it isn't in the results."
        }, self._sources(selected))

    def _work_and_projects(self, args: dict) -> ToolResult:
        """Return a bounded but complete catalog without using search top-k.

        Portfolio projects and verified employment are kept separate: sharing
        a technology, company word, or GitHub URL does not establish a job.
        """
        self.store.refresh()
        data = self.store.data
        jobs = []
        projects = []
        source_docs: list[SourceDocument] = []
        by_experience_id = {str(item.get("id")): item for item in data.get("experience", [])
                            if isinstance(item, dict) and item.get("id")}
        for item in data.get("experience", []):
            if not isinstance(item, dict):
                continue
            doc = self.store.by_id.get("experience:" + str(item.get("id")))
            if not doc:
                continue
            jobs.append({"organization": item.get("organization"), "role": item.get("role"),
                         "period": item.get("period"), "documented_work": item.get("details"),
                         "source_id": doc.id})
            source_docs.append(doc)
        for item in data.get("projects", []):
            if not isinstance(item, dict):
                continue
            doc = self.store.by_id.get("project:" + str(item.get("id")))
            if not doc:
                continue
            job = by_experience_id.get(str(item.get("id")))
            projects.append({"name": item.get("name"),
                             "portfolio_category": item.get("category"),
                             "portfolio_filters": item.get("filterCategories", []),
                             "documented_project": item.get("description"),
                             "technologies": item.get("tech", []),
                             "repository_or_link": item.get("githubLink"),
                             "associated_documented_work_role": (
                                 {"organization": job.get("organization"), "role": job.get("role")}
                                 if job else None),
                             "source_id": doc.id})
            source_docs.append(doc)
        q = args.get("query", "")
        if isinstance(q, str) and q.strip():
            ranked = self.store.search(q.strip()[:300], limit=20)
            rank_ids = [d.id for d in ranked]
            requested_terms = _terms(q)
            category_ids = set()
            for project in data.get("projects", []):
                if not isinstance(project, dict):
                    continue
                facets = [str(project.get("category", ""))] + [
                    str(x) for x in project.get("filterCategories", []) if isinstance(x, str)
                ]
                if any(_terms(f) and _terms(f) <= requested_terms for f in facets):
                    category_ids.add("project:" + str(project.get("id")))
            source_docs.sort(key=lambda d: (
                0 if d.id in category_ids else 1,
                rank_ids.index(d.id) if d.id in rank_ids else 1000,
            ))
        return ToolResult({
            "catalog_scope": "Every published, indexed portfolio project and professional work record; includes non-featured projects.",
            "work_experience": jobs,
            "portfolio_projects": projects,
            "counts": {"work_records": len(jobs), "project_records": len(projects)},
            "interpretation": (
                "Work experience is documented separately from portfolio projects. "
                "Only a documented work role establishes an employment/client relationship. "
                "A project can be personal, university-based or collaborative. "
                "Do not infer features, status, seniority or employers from repository names. "
                "Use the complete list before making claims that a type of app is absent."
            )
        }, self._sources(source_docs))

    def _repositories(self, args: dict) -> ToolResult:
        if not self.store.github_path:
            return ToolResult({"error": "GitHub synchronization is not configured."})
        data = load_json(self.store.github_path)
        inventory = data.get("inventory", [])
        if not isinstance(inventory, list) or not inventory:
            return ToolResult({"error": "GitHub repository inventory not available yet. Synchronization may still be running."})
        owners = {str(owner).lower() for owner in data.get("inventory_owners", [])}
        rows = [r for r in inventory if isinstance(r, dict) and r.get("visibility") == "public"
                and re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}", str(r.get("full_name", "")))
                and (not owners or str(r["full_name"]).split("/", 1)[0].lower() in owners)]
        focus = args.get("focus", "all")
        if focus == "ai":
            self.store.refresh()
            facts = load_json(self.store.facts_path) if self.store.facts_path else {}
            verified = ai_repository_evidence(rows, self.store.data, facts)
            rows = [r for r in rows if str(r["full_name"]).lower() in verified]
        if args.get("sort") == "name":
            rows.sort(key=lambda x: str(x.get("full_name", "")).lower())
        else:
            rows.sort(key=lambda x: str(x.get("pushed_at") or ""), reverse=True)
        links = [{"id": "github:repo:" + str(r["full_name"]),
                  "title": "Public GitHub repository: " + str(r["full_name"]),
                  "url": str(r.get("url") or "https://github.com/" + str(r["full_name"]))}
                 for r in rows]
        return ToolResult({
            "inventory_complete": data.get("inventory_complete") is True,
            "last_synced": data.get("synced_at"),
            "filter": focus,
            "total_returned": len(rows),
            "repositories": [{"name": r.get("full_name"), "description": r.get("description"),
                              "topics": r.get("topics", []), "last_push": r.get("pushed_at"),
                              "url": r.get("url"), "fork": r.get("fork"), "archived": r.get("archived")}
                             for r in rows[:90]],
            "note": "All entries are public. Last push is not the latest commit date or proof of authorship/activity."
        }, links[:8])

    def _latest_commit(self, args: dict) -> ToolResult:
        repository = args.get("repository", "")
        if not isinstance(repository, str) or not repository.strip() or not self.commits:
            return ToolResult({"error": "Specify a known public repository."})
        resolved = self.commits.resolve(repository[:130], [])
        if not resolved:
            return ToolResult({"error": "That repository could not be uniquely resolved in the public inventory. Ask for the specific repository."})
        try:
            doc = self.commits.latest(resolved)
        except Exception as exc:
            # The agent should never report an unverified commit date on network failure.
            return ToolResult({"error": "Live GitHub commit lookup failed.", "reason_type": type(exc).__name__})
        if not doc:
            return ToolResult({"error": "No live commit data was returned for that public repository."})
        return ToolResult({"repository": resolved, "record": self._pack(doc, 3600)}, [doc.link()])

    def execute(self, name: str, arguments: dict | None) -> ToolResult:
        args = arguments if isinstance(arguments, dict) else {}
        if name == "get_professional_overview":
            return self._overview()
        if name == "search_professional_knowledge":
            return self._search(args)
        if name == "inspect_professional_work_and_projects":
            return self._work_and_projects(args)
        if name == "list_public_repositories":
            return self._repositories(args)
        if name == "get_latest_public_commit":
            return self._latest_commit(args)
        return ToolResult({"error": "Unknown tool. No action taken."})
