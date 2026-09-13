"""Build a complete local installer, source ZIP and clearly separate AnkiWeb handoff.

No upload is performed. The UPLOAD_ONLY variant is not a local installer: its
conflict metadata is intended for AnkiWeb's numeric-ID installation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from addon.core import VERSION

DOCS = ['LIVE_ANKI_CHECKLIST.md', 'ARCHITECTURE.md', 'TEST_REPORT.md', 'CHANGELOG.md',
        'READINESS_METHOD.md', 'PRIVACY.md', 'ANKIWEB_PUBLISHING.md', 'WINDOWS_UPDATE_RECOVERY.md']
SKIP = {'__pycache__', '.pytest_cache', '.git', 'dist', 'verification-work'}


def include(path: Path) -> bool:
    return not any(part in SKIP for part in path.relative_to(ROOT).parts) and path.suffix not in ('.pyc', '.pyo')


def entry(z: zipfile.ZipFile, name: str, content: bytes) -> None:
    info = zipfile.ZipInfo(name, date_time=(2026, 9, 11, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, content)


def build(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    installer = out / f'Exam_Sprout_{VERSION}.ankiaddon'
    with zipfile.ZipFile(installer, 'w') as z:
        for path in sorted((ROOT / 'addon').rglob('*')):
            if path.is_file() and include(path):
                entry(z, path.relative_to(ROOT / 'addon').as_posix(), path.read_bytes())
        for name in ('README.md', 'LICENSE'):
            entry(z, name, (ROOT / name).read_bytes())
        for name in DOCS:
            entry(z, 'docs/' + name, (ROOT / 'docs' / name).read_bytes())
    with zipfile.ZipFile(installer) as z:
        assert z.testzip() is None
        assert '__init__.py' in z.namelist() and 'manifest.json' in z.namelist()
        manifest = json.loads(z.read('manifest.json'))
        assert manifest['package'] == 'exam_sprout' and manifest['conflicts'] == []
        for name in z.namelist():
            assert not name.startswith('addon/') and '__pycache__' not in name
            if name.endswith('.py'):
                compile(z.read(name), name, 'exec')

    source = out / f'Exam_Sprout_Source_{VERSION}.zip'
    with zipfile.ZipFile(source, 'w') as z:
        for path in sorted(ROOT.rglob('*')):
            if path.is_file() and include(path) and out not in path.parents and path.suffix not in ('.ankiaddon', '.zip'):
                entry(z, 'Exam Sprout/' + path.relative_to(ROOT).as_posix(), path.read_bytes())

    publication = out / 'AnkiWeb_Publication'
    if publication.exists():
        shutil.rmtree(publication)
    publication.mkdir()
    upload = publication / f'UPLOAD_ONLY_Exam_Sprout_{VERSION}.ankiaddon'
    with zipfile.ZipFile(installer) as local, zipfile.ZipFile(upload, 'w') as remote:
        for name in local.namelist():
            content = local.read(name)
            if name == 'manifest.json':
                data = json.loads(content)
                data['conflicts'] = ['exam_sprout']
                content = (json.dumps(data, indent=2) + '\n').encode()
            entry(remote, name, content)
    shutil.copy2(ROOT / 'LICENSE', publication / 'LICENSE')
    shutil.copy2(ROOT / 'docs/ANKIWEB_PUBLISHING.md', publication / 'READ_THIS_FIRST.md')
    for name in ('PRIVACY.md', 'READINESS_METHOD.md', 'LIVE_ANKI_CHECKLIST.md', 'TEST_REPORT.md', 'WINDOWS_UPDATE_RECOVERY.md'):
        shutil.copy2(ROOT / 'docs' / name, publication / name)
    for name in ('Exam_Sprout_Readiness.png', 'Exam_Sprout_Exam_Builder.png', 'Exam_Sprout_Result.png'):
        path = ROOT / 'docs/readiness-0100' / name
        if path.exists():
            shutil.copy2(path, publication / name)
            shutil.copy2(path, out / name)
    listing = f'''Exam Sprout — Exam Readiness, Mock Exams & Pip Study

{VERSION} RELEASE CANDIDATE. Native Windows/Anki acceptance is still required before
this listing is published as a stable release. Target: Anki 25.09.5 / Qt 6.

Windows update repair: native animations now play from memory rather than
locked files. Existing old installations must first be closed and updated in
safe mode. See WINDOWS_UPDATE_RECOVERY.md.

A small countdown on your deck screen, a focused exam plan, and a living Pip
companion. Choose your exam decks and emphasis, then rehearse material rather
than just repeat the cards you already know.

• Experimental F− through A+ / S readiness tiers, topic coverage, delayed recall,
  evidence strength and a visible no-guarantee notice. This is NOT a promised
  grade, calibrated exam-score prediction or probability of passing.
• Pip effort grows separately from readiness. One graded note per UTC day earns
  effort; wrong answers count and petting does not inflate it.
• 1–500 unique-question exams, relative deck weights, fixed representative mocks
  or targeted rehearsal, optional cold-only draws and up to 720-minute timing.
• Flags, question navigation, confidence before reveal, self-marking and mistake
  categories. Review original misses or all questions alongside retained answers.
• Explicit save/resume for one unfinished session. Timed mocks keep counting
  while closed. Completed written-answer saving is off by default.
• Pip Study targets unresolved/confident mistakes and delayed checks; recently
  correct learned cards are deprioritized. Prompts encourage uncued explanation,
  comparison and application; they do not generate case or multiple-choice items.
• Explicit new-card learning can submit real Anki Again/Hard/Good/Easy ratings
  for revalidated active NEW cards only. This changes their Anki progress. Remaining
  learning steps occur in normal review. Learned rehearsal and mocks never grade
  Anki's scheduler. Back up first; this path requires native acceptance testing.
• Tiny 46px reviewer companion; no sidebar or card overlay. Local 3D art and
  fallback assets; original templates render through Anki's Previewer in practice.
• Preset/inherited palettes and support for the supplied Atelier home interface.

Privacy: local profile storage. No account, AI subscription, telemetry or remote
renderer. Explicit Save & close stores an unfinished draft including written text;
that consent is separate from optional completed-session answer retention. Exported
result JSON contains outcomes, not written prose.

Limitations: desktop add-on, not an AnkiWeb-browser or mobile extension. Self-marked
flashcards cannot certify syllabus coverage or case competence. Native third-party
review-only hooks may differ in independent practice. Actual Windows Anki/FSRS,
image-occlusion/audio/template combinations and numeric AnkiWeb installation need
acceptance testing. Server upload-size/publication acceptance has not been tested.
Screenshots show actual packaged UI with synthetic sample data.

Author/brand: Daedalus Works. Website: https://daedalusworks.net/
License: MIT for the original Exam Sprout files. Source archive accompanies this
release. Owner must confirm a monitored support contact and tested version range
before publication. No AnkiWeb install code has been allocated in this handoff.
'''
    (publication / 'LISTING.txt').write_text(listing, encoding='utf-8')
    (publication / 'SCREENSHOT_CAPTIONS.txt').write_text(
        'Readiness: actual production planner with synthetic sample evidence (not a validated exam prediction).\n'
        'Exam builder: actual production 500-question settings with synthetic sample decks.\n'
        'Result: actual production self-marked outcome screen with synthetic sample results.\n', encoding='utf-8')
    bundle = out / f'Exam_Sprout_AnkiWeb_Publication_{VERSION}.zip'
    with zipfile.ZipFile(bundle, 'w') as z:
        for path in sorted(publication.rglob('*')):
            if path.is_file():
                entry(z, path.relative_to(publication).as_posix(), path.read_bytes())
    shutil.copy2(ROOT / 'docs/TEST_REPORT.md', out / f'Exam_Sprout_{VERSION}_Test_Report.md')
    shutil.copy2(ROOT / 'docs/READINESS_METHOD.md', out / 'Exam_Sprout_Readiness_Method.md')
    shutil.copy2(ROOT / 'docs/ANKIWEB_PUBLISHING.md', out / 'AnkiWeb_Publication_Guide.md')
    shutil.copy2(ROOT / 'docs/WINDOWS_UPDATE_RECOVERY.md', out / 'Exam_Sprout_Windows_Update_Recovery.md')
    artifacts = [installer, source, bundle]
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts}
    (out / 'SHA256SUMS.txt').write_text(''.join(f'{value}  {key}\n' for key, value in hashes.items()))
    print(json.dumps({'files': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': hashes[p.name]} for p in artifacts]}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=ROOT / 'dist')
    build(parser.parse_args().output.resolve())
