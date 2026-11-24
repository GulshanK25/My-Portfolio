"""Data-driven classification and identity matching for public GitHub projects.

Repository inventory, portfolio project categories and owner-approved local
project associations are separate evidence sources.  A local AI integration
must never be presented as a feature already pushed to a remote repository.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re
from urllib.parse import urlsplit

GITHUB_REPO = re.compile(r"^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$")
AI_TERMS = re.compile(
    r"\b(?:ai|artificial intelligence|machine learning|deep learning|llm|llms|"
    r"rag|retrieval augmented generation|generative ai|neural network|"
    r"computer vision|language model|agentic)\b", re.I,
)


def repository_slug(value: str) -> str | None:
    """Normalize a GitHub repository URL or owner/repo identifier."""
    value = str(value or "").strip()
    if value.startswith("https://github.com/"):
        p = urlsplit(value)
        if p.netloc != "github.com":
            return None
        parts = [x for x in p.path.split("/") if x]
        if len(parts) < 2:
            return None
        value = f"{parts[0]}/{parts[1]}"
    return value.lower() if GITHUB_REPO.fullmatch(value) else None


def ai_repository_evidence(inventory: list[dict], portfolio_data: dict,
                           facts: dict) -> dict[str, dict]:
    """Classify repositories from explicit metadata, not from coding language.

    These are discovery labels, not claims about completed functionality.
    Metadata from user-approved local work is labeled separately from GitHub.
    """
    catalog = {}
    for repo in inventory:
        if not isinstance(repo, dict) or repo.get("visibility") != "public":
            continue
        slug = repository_slug(repo.get("full_name", ""))
        if slug is None:
            continue
        labels = []
        text = " ".join([str(repo.get("description", ""))] +
                        [str(x) for x in repo.get("topics", []) if isinstance(x, str)])
        if AI_TERMS.search(text):
            labels.append("GitHub description/topics")
        catalog[slug] = {"repo": repo, "evidence": labels,
                         "local_work": [], "portfolio_projects": []}

    for project in portfolio_data.get("projects", []):
        if not isinstance(project, dict):
            continue
        slug = repository_slug(project.get("githubLink", ""))
        if slug not in catalog:
            continue
        filters = [str(x).lower() for x in project.get("filterCategories", [])]
        category = str(project.get("category", ""))
        if "ai" in filters or AI_TERMS.search(category):
            catalog[slug]["evidence"].append("portfolio AI project classification")
            catalog[slug]["portfolio_projects"].append(str(project.get("name", "")))

    for project in facts.get("currentProjects", []):
        if not isinstance(project, dict):
            continue
        slug = repository_slug(project.get("repository") or project.get("url", ""))
        if slug not in catalog:
            continue
        categories = [str(x).lower() for x in project.get("categories", [])]
        if "ai" not in categories:
            continue
        catalog[slug]["evidence"].append("owner-approved local AI project")
        catalog[slug]["local_work"].append({
            "name": str(project.get("name", "")),
            "status": str(project.get("status", "")),
            "as_of": str(project.get("asOf", "")),
            "relationship": str(project.get("relationship", "")),
            "publication_note": str(project.get("publicationNote", "")),
        })
    return {slug: data for slug, data in catalog.items() if data["evidence"]}


def referenced_repository(question: str, inventory: list[dict]) -> dict | None:
    """Match a repository mentioned by a visitor, tolerating small typos.

    Don't select a repo when the query lacks a sufficiently distinctive term.
    """
    words = re.findall(r"[a-z0-9]+", question.lower())
    ignored = {"what", "about", "your", "his", "her", "isnt", "is", "also", "that",
               "this", "and", "but", "project", "projects", "github", "repo",
               "repository", "which", "there", "why", "not", "are", "you", "the",
               "githbub", "including", "include", "all", "list"}
    words = [word for word in words if len(word) >= 5 and word not in ignored]
    best = (0., None)
    for item in inventory:
        name = str(item.get("name") or str(item.get("full_name", "")).split("/")[-1])
        tokens = [x for x in re.findall(r"[a-z0-9]+", name.lower()) if len(x) >= 5]
        if not tokens:
            continue
        similarity = max((SequenceMatcher(None, a, b).ratio()
                          for a in words for b in tokens), default=0)
        if similarity >= .79 and similarity > best[0]:
            best = (similarity, item)
    return best[1]
