"""Read-only GitHub -> local RAG source cache.

Only public repository metadata and narrowly selected documentation are indexed.
No repository mutations, GitHub webhooks, or API credentials are stored.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import httpx

logger = logging.getLogger(__name__)
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / 'public' / 'knowledge-sources.json'
CACHE_DIR = Path(os.getenv('GULSHAN_AI_CACHE_DIR', str(Path.home() / '.gulshan-ai')))
GITHUB_CACHE = CACHE_DIR / 'github_knowledge.json'
LINKEDIN_CACHE = CACHE_DIR / 'linkedin_knowledge.json'
MAX_REPOS = 45
MAX_README_BYTES = 130_000
MAX_README_CHARS = 11_000
API = 'https://api.github.com'
GITHUB_ID = re.compile(r'^[A-Za-z0-9-]{1,39}/[A-Za-z0-9._-]{1,100}$')
SECRET_LINE = re.compile(r'(?i)(?:api[_-]?key|secret|password|token|private[_-]?key)\s*[:=]\s*[^\s]{8,}')


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.sync-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            json.dump(payload, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    with path.open('r', encoding='utf-8') as stream:
        result = json.load(stream)
    return result if isinstance(result, dict) else {}


def scrub_public_markdown(value: str) -> str:
    """Exclude code samples, emails, likely credentials, and HTML from quoted README text."""
    value = re.sub(r'```[\s\S]*?```', '[code example omitted]', value)
    value = re.sub(r'<[^>]*>', ' ', value)
    value = re.sub(r'!\[[^]]*\]\([^)]*\)', '', value)
    value = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', '[email omitted]', value)
    value = re.sub(r'\+?\d[\d\s()\-]{9,}\d', '[phone omitted]', value)
    lines = []
    for line in value.splitlines():
        if SECRET_LINE.search(line) or re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----', line):
            continue
        lines.append(line)
    return '\n'.join(lines)[:MAX_README_CHARS]


def _doc(repo: str, part: str, title: str, text: str, url: str, priority: float) -> dict:
    return {
        'id': f'github:{repo}:{part}', 'kind': 'github', 'title': title,
        'text': text, 'url': url, 'priority': priority,
    }


class GitHubKnowledgeSync:
    """Pull a bounded public repo snapshot and store citeable source documents.

    The read-only API calls work without a token for public repos. To increase
    the rate limit, set GITHUB_READ_TOKEN locally (never place it in React).
    """

    def __init__(self, config_path: Path = DEFAULT_CONFIG, cache_path: Path = GITHUB_CACHE,
                 client: httpx.Client | None = None):
        self.config_path = Path(config_path)
        self.cache_path = Path(cache_path)
        self.client = client
        self._discovery_complete = False

    @staticmethod
    def _headers() -> dict[str, str]:
        h = {'Accept': 'application/vnd.github+json',
             'User-Agent': 'GulshanAI-public-profile-indexer',
             'X-GitHub-Api-Version': '2022-11-28'}
        token = os.getenv('GITHUB_READ_TOKEN', '').strip()
        if token:
            h['Authorization'] = f'Bearer {token}'
        return h

    def _get(self, client: httpx.Client, path: str, *, params: dict | None = None) -> Any:
        resp = client.get(f'{API}{path}', params=params)
        if resp.status_code in (404, 410):
            return None
        resp.raise_for_status()
        return resp.json()

    def _list_public_repos(self, client: httpx.Client, owners: list[str]) -> dict[str, dict]:
        """Inventory every visible *public* repo, including forks and archived repos.

        Forks/archived projects are listed with their status, but intentionally
        excluded from portfolio README ingestion below. If the bounded listing
        cannot prove completeness, the catalog must not claim to be exhaustive.
        """
        found: dict[str, dict] = {}
        complete = bool(owners) and len(owners) <= 3
        for owner in owners[:3]:
            if not re.fullmatch(r'[A-Za-z0-9-]{1,39}', owner):
                complete = False
                continue
            # Bound polling to two pages for now and explicitly report truncation.
            for page in (1, 2):
                repos = self._get(client, f'/users/{owner}/repos', params={
                    'per_page': 100, 'page': page, 'sort': 'updated', 'type': 'owner',
                })
                if not isinstance(repos, list):
                    complete = False
                    break
                for item in repos:
                    if isinstance(item, dict) and item.get('private') is False \
                            and GITHUB_ID.fullmatch(item.get('full_name') or ''):
                        found[item['full_name']] = item
                if len(repos) < 100:
                    break
                if page == 2:
                    complete = False
        self._discovery_complete = complete
        return found

    @staticmethod
    def _catalog_entry(meta: dict) -> dict | None:
        """Constrain the public repository facts exposed in chatbot responses."""
        full_name = str(meta.get('full_name') or '')
        if meta.get('private') is not False or not GITHUB_ID.fullmatch(full_name):
            return None
        return {
            'full_name': full_name, 'visibility': 'public',
            'name': full_name.split('/', 1)[1],
            'url': f'https://github.com/{full_name}',
            'description': str(meta.get('description') or '').strip()[:350],
            'topics': [str(t)[:60] for t in meta.get('topics', [])[:25] if isinstance(t, str)]
                      if isinstance(meta.get('topics'), list) else [],
            'language': str(meta.get('language') or '').strip()[:80],
            'pushed_at': str(meta.get('pushed_at') or '')[:25],
            'fork': bool(meta.get('fork')),
            'archived': bool(meta.get('archived')),
        }

    def _repository_docs(self, client: httpx.Client, full_name: str,
                         previous: dict[str, Any] | None = None,
                         discovered_meta: dict[str, Any] | None = None) -> tuple[dict, list[dict]] | None:
        meta = discovered_meta or self._get(client, f'/repos/{full_name}')
        if not isinstance(meta, dict) or meta.get('private') is not False \
                or meta.get('fork') or meta.get('archived'):
            return None
        actual = str(meta.get('full_name') or full_name)
        if not GITHUB_ID.fullmatch(actual):
            return None
        url = f'https://github.com/{actual}'
        description = str(meta.get('description') or '').strip()[:1000]
        topics = [str(x)[:60] for x in meta.get('topics', []) if isinstance(x, str)][:25]
        lang = str(meta.get('language') or '').strip()[:100]
        updated_at = str(meta.get('pushed_at') or '')[:25]
        commit_hint = str(meta.get('default_branch') or 'main')
        # Publication dates and descriptions do not prove active employment or project status.
        summary = (f'Public GitHub repository {actual}. Description: {description or "Not provided"}. '
                   f'Primary language: {lang or "Not specified"}. Topics: {", ".join(topics) or "None"}. '
                   f'Last pushed at (GitHub metadata): {updated_at or "Unknown"}. '
                   'A recent push is not proof that this project is still actively developed, '
                   'that any claimed feature is complete, or that Gulshan personally authored every commit.')
        records = [_doc(actual, 'metadata', f'GitHub project: {actual.split("/")[-1]}',
                        summary, url, 1.1)]
        previous = previous or {}
        # Reuse unchanged README. Treat repo pushes as a cheap invalidation hint.
        # Metadata is rebuilt on every sync even when documentation is unchanged.
        old_sha = previous.get('pushed_at')
        old_docs = previous.get('documents', [])
        if old_sha == updated_at and previous.get('default_branch') == commit_hint and old_docs:
            records.extend([d for d in old_docs if d.get('id', '').endswith(':readme')])
        else:
            readme = self._get(client, f'/repos/{actual}/readme')
            if isinstance(readme, dict) and readme.get('encoding') == 'base64':
                try:
                    raw = base64.b64decode(str(readme.get('content', '')),
                                           validate=False)
                    if len(raw) <= MAX_README_BYTES:
                        body = scrub_public_markdown(raw.decode('utf-8', errors='replace'))
                        if body.strip():
                            path = str(readme.get('path') or 'README.md')
                            # Restrict citeable links to this repository.
                            if not re.fullmatch(r'[\w./-]{1,200}', path) or '..' in path:
                                path = 'README.md'
                            doc_url = f'{url}/blob/{commit_hint}/{path}'
                            records.append(_doc(actual, 'readme', f'GitHub README: {actual}',
                                                f'Public repository documentation for {actual} '\
                                                '(project claims, not independently verified):\n' + body,
                                                doc_url, .95))
                except (ValueError, TypeError) as exc:
                    logger.warning('Skipping invalid README from %s (%s)', actual, type(exc).__name__)
        return {'pushed_at': updated_at, 'default_branch': commit_hint, 'documents': records}, records

    def sync(self) -> dict:
        config = load_json(self.config_path).get('github') or {}
        if not config.get('enabled', False):
            return {'status': 'disabled', 'repositories': 0}
        owners = [x for x in config.get('owners', []) if isinstance(x, str)]
        pinned = [x for x in config.get('repositories', [])
                  if isinstance(x, str) and GITHUB_ID.fullmatch(x)]
        max_repos = min(max(int(config.get('max_repos', 30)), 1), MAX_REPOS)
        old = load_json(self.cache_path)
        previous = old.get('repositories', {}) if isinstance(old.get('repositories'), dict) else {}
        client = self.client or httpx.Client(timeout=12.0, headers=self._headers(), trust_env=True)
        owns_client = self.client is None
        changed = 0
        errors: list[str] = []
        try:
            discovered = self._list_public_repos(client, owners) if config.get('discover_public', False) else {}
            indexable = [ref for ref, meta in discovered.items()
                         if not meta.get('fork') and not meta.get('archived')]
            refs = list(dict.fromkeys(pinned + indexable))[:max_repos]
            if not refs:
                # A transient discovery failure should never erase previously indexed sources.
                return {'status': 'no_repositories', 'repositories': 0}
            entries = {}
            for ref in refs:
                try:
                    record = self._repository_docs(client, ref, previous.get(ref), discovered.get(ref))
                    if record:
                        entries[ref] = record[0]
                        if record[0] != previous.get(ref):
                            changed += 1
                except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                    logger.warning('GitHub knowledge sync failed for %s (%s)', ref, type(exc).__name__)
                    errors.append(ref)
                    if ref in previous:
                        entries[ref] = previous[ref]  # preserve old, verified public snapshot
            # The catalog is NOT the 5-document RAG shortlist. It retains the
            # entire public owner inventory even if only a bounded subset has
            # downloaded README docs. Never include private repos or mistake
            # a pinned collaborator repo for an owned repository.
            inventory = [item for meta in discovered.values()
                         if (item := self._catalog_entry(meta)) is not None]
            inventory.sort(key=lambda item: (item['pushed_at'], item['full_name']), reverse=True)
            inventory_complete = bool(config.get('discover_public') and self._discovery_complete)
            payload = {
                'schema': 2, 'provider': 'github', 'synced_at': utc_now(),
                'repositories': entries,
                'documents': [d for entry in entries.values() for d in entry.get('documents', [])],
                'inventory': inventory, 'inventory_complete': inventory_complete,
                'inventory_owners': owners[:3],
                'readme_limit_reached': len(dict.fromkeys(pinned + indexable)) > max_repos,
            }
            if entries or inventory:
                atomic_json(self.cache_path, payload)
            return {'status': 'partial' if errors else 'ok', 'repositories': len(entries),
                    'inventory_repositories': len(inventory),
                    'inventory_complete': inventory_complete,
                    'changed': changed, 'failed': len(errors), 'synced_at': payload['synced_at']}
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            logger.warning('GitHub discovery failed (%s); keeping previous snapshot', type(exc).__name__)
            return {'status': 'failed', 'error_type': type(exc).__name__,
                    'repositories': len(previous)}
        finally:
            if owns_client:
                client.close()


if __name__ == '__main__':
    print(json.dumps(GitHubKnowledgeSync().sync(), indent=2))
