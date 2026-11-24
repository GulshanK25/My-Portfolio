"""Read-only GitHub commit evidence for an existing public repository inventory.

Commit records are retrieved on demand because a README snapshot cannot say
what changed in the latest commit. This module never writes to GitHub.
"""
from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher
import os
import re
import time
from threading import RLock

import httpx

from .knowledge import SourceDocument
from .source_sync import API, GITHUB_CACHE, load_json


def _words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.lower())


def _repo_similarity(name: str, text: str) -> float:
    repo = name.rsplit('/', 1)[-1]
    words = _words(repo)
    words_in_text = _words(text)
    if not words or not words_in_text:
        return 0
    joined = " ".join(words)
    haystack = " ".join(words_in_text)
    if re.search(rf"(?<!\w){re.escape(joined)}(?!\w)", haystack):
        return 1.0
    # The tokenizer handles hyphens/underscores/spacing in repository names.
    meaningful = [w for w in words if len(w) > 2]
    if meaningful and all(w in words_in_text for w in meaningful):
        return .93
    # Fuzzy matching tolerates casual typos, but requires a distinctive name.
    n = len(words)
    return max((SequenceMatcher(None, joined, " ".join(words_in_text[i:i+n])).ratio()
                for i in range(max(0,len(words_in_text)-n+1))), default=0.0)


class GitHubCommitReader:
    def __init__(self, cache_path=GITHUB_CACHE, client: httpx.Client | None = None,
                 cache_seconds: int = 300):
        self.cache_path = cache_path
        self.client = client
        self.cache_seconds = cache_seconds
        self._entries: dict[str, tuple[float, SourceDocument]] = {}
        self._lock = RLock()

    def _inventory(self) -> list[dict]:
        payload = load_json(self.cache_path)
        owners = {str(x).lower() for x in payload.get('inventory_owners', [])}
        return [item for item in payload.get('inventory', [])
                if isinstance(item, dict)
                and item.get('visibility') == 'public'
                and isinstance(item.get('full_name'), str)
                and (not owners or item['full_name'].split('/', 1)[0].lower() in owners)]

    def resolve(self, question: str, history: list[dict[str, str]] | None = None) -> str | None:
        inventory = self._inventory()
        if not inventory:
            return None
        # Prefer exact/current question. Only use recent history when the question
        # references an earlier repository. Conversation is context, never evidence.
        for text in [question] + [str(t.get('content', '')) for t in reversed((history or [])[-8:])
                                  if t.get('role') == 'user']:
            ranked = sorted(((_repo_similarity(i['full_name'], text), i['full_name']) for i in inventory),
                            reverse=True)
            if not ranked or ranked[0][0] < .82:
                continue
            if len(ranked) > 1 and ranked[1][0] >= ranked[0][0] - .055:
                continue  # Ambiguous: never guess which repository.
            return ranked[0][1]
        return None

    @staticmethod
    def _headers() -> dict:
        headers = {'Accept': 'application/vnd.github+json',
                   'X-GitHub-Api-Version': '2022-11-28',
                   'User-Agent': 'GulshanAI-readonly-commit-lookup'}
        token = os.getenv('GITHUB_READ_TOKEN', '').strip()
        if token:
            headers['Authorization'] = 'Bearer ' + token
        return headers

    def latest(self, repository: str) -> SourceDocument | None:
        # Check current public inventory again to enforce the privacy boundary.
        if repository not in {i['full_name'] for i in self._inventory()}:
            return None
        now = time.monotonic()
        with self._lock:
            cached = self._entries.get(repository)
            if cached and now - cached[0] < self.cache_seconds:
                return cached[1]
        owns = self.client is None
        client = self.client or httpx.Client(timeout=httpx.Timeout(10, connect=4),
                                             headers=self._headers())
        try:
            response = client.get(f'{API}/repos/{repository}/commits', params={'per_page': 1})
            response.raise_for_status()
            commits = response.json()
            if not isinstance(commits, list) or not commits:
                return None
            summary = commits[0]
            sha = str(summary.get('sha') or '')
            if not re.fullmatch(r'[0-9a-f]{40}', sha):
                return None
            details_resp = client.get(f'{API}/repos/{repository}/commits/{sha}')
            details_resp.raise_for_status()
            details = details_resp.json()
            info = details.get('commit', {})
            when = (info.get('committer') or {}).get('date') or (info.get('author') or {}).get('date')
            message = str(info.get('message') or '').strip()[:900]
            timestamp = str(when or 'not specified')
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%B %d, %Y at %H:%M UTC')
            except (ValueError, TypeError):
                pass
            files = details.get('files', [])
            file_names = [str(f.get('filename') or '') for f in files[:35]
                          if isinstance(f, dict) and f.get('filename')]
            changes = [f"{f.get('filename')}: {f.get('status', 'changed')}"
                       for f in files[:20] if isinstance(f, dict) and f.get('filename')]
            url = f'https://github.com/{repository}/commit/{sha}'
            text = (f"Latest commit on the default branch of the public GitHub repository {repository}. "
                    f"Commit date: {timestamp}. Commit SHA: {sha}. "
                    f"Commit message: {message}. "
                    f"Changed files ({len(files)} returned): {', '.join(changes) or 'not available'}. "
                    f"File paths: {', '.join(file_names)}. "
                    "Describe only changes supported by the commit message and changed-file list; "
                    "do not claim unverified runtime outcomes. This is a commit, not necessarily the repository's last push.")
            doc = SourceDocument(f'github:commit:{repository}:{sha}',
                                 f'Latest GitHub commit: {repository}', text, url, 'github', 2.0)
            with self._lock:
                self._entries[repository] = (now, doc)
            return doc
        finally:
            if owns:
                client.close()
