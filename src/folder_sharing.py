"""Read/export one bounded union of native decks; never move or reschedule cards."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote

from .core import ValidationError, deck_id, fresh_catalog
from .friends_client import validate_package

MAX_CARDS = 50000
MAX_SOURCE_BYTES = 64 * 1024 * 1024


def inspect_scope(col, roots):
    if not isinstance(roots, list) or not 1 <= len(roots) <= 20:
        raise ValidationError('Choose 1–20 folders or decks to share.')
    roots = list(dict.fromkeys(deck_id(x) for x in roots))
    catalog = fresh_catalog(col)
    if any(x not in catalog for x in roots):
        raise ValidationError('An attached folder is no longer available. Attach it again.')
    paths = [catalog[x]['name'] for x in roots]
    decks = {k: v['name'] for k, v in catalog.items()
             if any(v['name'] == p or v['name'].startswith(p + '::') for p in paths)}
    ids = ','.join(str(int(x)) for x in decks)
    size = col.db.scalar('select coalesce(sum(length(cast(n.flds as blob))+length(cast(n.tags as blob))),0) from notes n where n.id in (select c.nid from cards c where (case when c.odid>0 then c.odid else c.did end) in (' + ids + '))')
    if size > MAX_SOURCE_BYTES:
        raise ValidationError('This course is too large for the private sharing pilot.')
    rows = col.db.all(
        'select c.id,c.nid,case when c.odid>0 then c.odid else c.did end,c.ord,'
        'n.mid,n.flds,n.tags,n.guid from cards c join notes n on c.nid=n.id '
        f'where (case when c.odid>0 then c.odid else c.did end) in ({ids}) '
        f'order by c.id limit {MAX_CARDS + 1}')
    if not rows:
        raise ValidationError('Add some cards to these folders before sharing.')
    if len(rows) > MAX_CARDS:
        raise ValidationError('Share a smaller folder: the private pilot supports 50,000 cards per course.')
    h = hashlib.sha256()
    total = 0
    media = set()
    models = set()
    for row in rows:
        raw = json.dumps(row, ensure_ascii=False, separators=(',', ':')).encode()
        total += len(raw)
        if total > MAX_SOURCE_BYTES:
            raise ValidationError('This course is too large for the private sharing pilot.')
        h.update(raw)
        models.add(row[4])
        # Parse references without rendering LaTeX or fetching remote resources.
        for match in re.finditer(r'''(?:src\s*=\s*["']([^"']+)["']|\[sound:([^\]]+)\])''', row[5], re.I):
            media.add(unquote(html.unescape(match[1] or match[2])))
    for mid in sorted(models):
        model = col.models.get(mid)
        if not model:
            raise ValidationError('A note type is unavailable. Check this course in Anki first.')
        raw = json.dumps(model, sort_keys=True, ensure_ascii=False).encode()
        total += len(raw)
        h.update(raw)
        media.update(col.media.extract_static_media_files(mid))
    media_root = Path(col.media.dir()).resolve()
    for name in sorted(media):
        if not isinstance(name, str) or len(name) > 1024:
            continue
        target = (media_root / name).resolve()
        if target.parent != media_root:
            continue  # No remote, absolute or nested file acquisition.
        try:
            stat = target.stat()
        except FileNotFoundError:
            h.update(('missing:' + name).encode())
            continue
        total += stat.st_size
        if total > MAX_SOURCE_BYTES:
            raise ValidationError('The course and its media exceed the private pilot’s 64 MiB source limit.')
        h.update(json.dumps([name, stat.st_size, stat.st_mtime_ns]).encode())
    if total > MAX_SOURCE_BYTES:
        raise ValidationError('This course is too large for the private sharing pilot.')
    h.update(json.dumps(decks, sort_keys=True).encode())
    return {'digest': h.hexdigest(), 'card_ids': [r[0] for r in rows],
            'deck_count': len(decks), 'card_count': len(rows)}


def export_scope(col, roots, target):
    from anki.collection import CardIdsLimit, ExportAnkiPackageOptions
    scope = inspect_scope(col, roots)
    col.export_anki_package(
        out_path=str(target), limit=CardIdsLimit(scope['card_ids']),
        options=ExportAnkiPackageOptions(with_scheduling=False, with_media=True,
                                       with_deck_configs=False, legacy=False))
    meta = validate_package(target)
    if inspect_scope(col, roots)['digest'] != scope['digest']:
        raise ValidationError('This course changed during export. Publish it again.')
    return {**scope, **meta}
