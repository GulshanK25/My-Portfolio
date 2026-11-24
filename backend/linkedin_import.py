"""Import *owner-selected* LinkedIn professional export CSVs, never private messages.

This is an opt-in local import, not LinkedIn scraping or a live LinkedIn API.
Only specifically permitted professional fields from specific filenames are used.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import re
from zipfile import ZipFile, BadZipFile

from .source_sync import LINKEDIN_CACHE, atomic_json, scrub_public_markdown

ALLOWED = {
    'profile.csv': {'first name', 'last name', 'headline', 'summary', 'industry', 'about'},
    'positions.csv': {'company name', 'title', 'description', 'started on', 'finished on', 'location', 'employment type'},
    'education.csv': {'school name', 'degree name', 'field of study', 'start date', 'end date', 'notes'},
    'skills.csv': {'name', 'skill', 'skill name'},
    'certifications.csv': {'name', 'organization', 'authority', 'date'},
    'projects.csv': {'name', 'description', 'start date', 'end date'},
}
SKIP = {'connections.csv', 'messages.csv', 'invitations.csv', 'email addresses.csv',
        'account status history.csv', 'ad targeting.csv'}
MAX_SOURCE_BYTES = 2_000_000
MAX_ROWS = 250


def _csv_docs(name: str, body: str, profile_url: str) -> list[dict]:
    if name not in ALLOWED:
        return []
    reader = csv.DictReader(StringIO(body.lstrip('\ufeff')))
    if not reader.fieldnames:
        return []
    permitted = ALLOWED[name]
    documents = []
    for i, row in enumerate(reader):
        if i >= MAX_ROWS:
            break
        # Use an explicit whitelist, not everything in the export.
        fields = [(str(k).strip(), str(v).strip()) for k, v in row.items()
                  if k and isinstance(v, str) and k.strip().lower() in permitted and v.strip()]
        if not fields:
            continue
        text = '; '.join(f'{key}: {scrub_public_markdown(value)[:700]}' for key, value in fields)
        if not text:
            continue
        documents.append({
            'id': f'linkedin:{name}:{i}', 'kind': 'linkedin',
            'title': f'LinkedIn professional profile: {name.removesuffix(".csv").title()} {i + 1}',
            'text': ('User-authorized LinkedIn professional export; snapshot only, '
                     'not proof of current employment status. ' + text)[:2500],
            'url': profile_url, 'priority': 1.05,
        })
    return documents


def import_export(source: Path, output: Path = LINKEDIN_CACHE,
                  profile_url: str = '') -> dict:
    """Only explicit call from portfolio owner reads a LinkedIn export ZIP/folder.

    Private files are ignored. The original export is never copied to the cache.
    """
    source = Path(source)
    if not re.fullmatch(r'https://(?:www\.)?linkedin\.com/in/[A-Za-z0-9%_\-]+/?', profile_url):
        profile_url = ''
    files: dict[str, str] = {}
    if source.is_dir():
        for path in source.rglob('*.csv'):
            name = path.name.lower()
            if name in ALLOWED and path.stat().st_size <= MAX_SOURCE_BYTES:
                files[name] = path.read_text(encoding='utf-8-sig', errors='replace')
    elif source.is_file() and source.suffix.lower() == '.zip':
        with ZipFile(source) as archive:
            for item in archive.infolist():
                name = Path(item.filename).name.lower()
                if name in ALLOWED and item.file_size <= MAX_SOURCE_BYTES:
                    files[name] = archive.read(item).decode('utf-8-sig', errors='replace')
    else:
        raise ValueError('Expected a LinkedIn export .zip or extracted directory')
    docs = [doc for name, raw in files.items() for doc in _csv_docs(name, raw, profile_url)]
    if not docs:
        raise ValueError('No supported professional profile CSV files found')
    payload = {'schema': 1, 'provider': 'linkedin-owner-export',
               'imported_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'documents': docs}
    atomic_json(output, payload)
    return {'status': 'ok', 'imported_documents': len(docs), 'source_files': sorted(files)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Import only selected professional LinkedIn CSV files')
    parser.add_argument('path', type=Path)
    parser.add_argument('--profile-url', default='')
    args = parser.parse_args()
    print(json.dumps(import_export(args.path, profile_url=args.profile_url), indent=2))
