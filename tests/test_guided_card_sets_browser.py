"""Focused browser receipt for the guided card-set and study-scope interfaces.

Uses local synthetic records and the real production renderers. It does not open
native Anki windows or claim a human usability study.
"""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from card_studio_harness import UnifiedHost, ROOT
from test_complete_home_browser import fixture as home_fixture

OUT = ROOT / 'verification' / 'guided-card-sets'
SHOTS = ROOT / 'screenshots' / 'card-set-upgrade'
OUT.mkdir(parents=True, exist_ok=True)
SHOTS.mkdir(parents=True, exist_ok=True)


def main():
    checks, errors = [], []

    def check(name, value):
        assert value, name
        checks.append(name)
        print('PASS', name, flush=True)

    host = UnifiedHost()
    slide_source = host.store.add_source(
        host.primary_project,
        'Cardiology lecture 04',
        'pptx',
        [
            {'text': 'Slide one: rhythm overview'},
            {'text': 'Slide two: atrial fibrillation'},
            {'text': 'Slide three: treatment decisions'},
            {'text': 'Slide four: review'},
        ],
    )['source']['id']
    before = host.col.note_count()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 960})
        page.set_default_timeout(8000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.expose_function('nativeBridge', host.dispatch)
        try:
            page.set_content(host.html())
            page.locator('.shelf-grid').wait_for()
            page.locator('[data-view="import"]').click()
            page.locator('.import-roadmap').wait_for()
            check('Import starts with four plain-language steps', page.locator('.roadmap-step').count() == 4)
            check('Import accepts slides PDFs images notes and text', all(word in page.locator('#ws-page').inner_text() for word in ('PowerPoint', 'PDF', 'images', 'notes', 'text')))
            check('Image occlusion is explained at import', 'Image occlusion is built in' in page.locator('#ws-page').inner_text())
            check('Card set explains its relationship to Anki decks', 'does not move or rename an Anki deck' in page.locator('#ws-page').inner_text())
            page.screenshot(path=str(SHOTS / 'import-card-set-1440x960.png'), animations='disabled')

            page.locator('[data-view="studio"]').click()
            page.locator('[data-change="studio-project"]').select_option(host.primary_project)
            page.locator('[data-change="studio-source"]').select_option(slide_source)
            page.locator('.source-page-rail').wait_for()
            check('Imported slide order is visible', page.locator('.source-page-rail .page-chip').all_inner_texts() == ['1', '2', '3', '4'])
            page.locator('[data-action="jump-page"][data-page="3"]').click()
            check('Exact slide selection updates page control', page.locator('[data-change="page-number"]').input_value() == '3')
            check('Card workflow keeps four stages visible', page.locator('.creator-step').count() == 4)
            page.locator('.creator-guide [data-action="card-style"][data-value="cloze"]').click()
            check('Guide card choices use the original draft engine', page.locator('[data-action="card-style"][data-value="cloze"]').last.get_attribute('aria-pressed') == 'true')
            check('Browsing and choosing card style creates no Anki notes', host.col.note_count() == before)
            page.screenshot(path=str(SHOTS / 'slide-workflow-1440x960.png'), animations='disabled')
            page.set_viewport_size({'width': 390, 'height': 720})
            page.wait_for_timeout(180)
            check('Compact Card Studio has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
            check('Compact workflow retains all four stages', page.locator('.creator-step').count() == 4)
            page.screenshot(path=str(SHOTS / 'slide-workflow-390x720.png'), animations='disabled')

            page.set_viewport_size({'width': 1440, 'height': 960})
            page.set_content(home_fixture())
            page.locator('.side-scope-card').wait_for()
            check('Home sidebar exposes current study scope', 'STUDY SCOPE' in page.locator('.side-scope-card').inner_text())
            check('Scope names selected folders and live counts', all(word in page.locator('.side-scope-card').inner_text() for word in ('selected folders', 'review', 'learning')))
            check('Study scope can be edited and studied directly', page.locator('.side-scope-card [data-action="studies"]').count() == 1 and page.locator('.side-scope-card [data-action="quick-session"]').count() == 1)
            check('Sidebar groups learning creation and management', all(word in page.locator('.sidebar').inner_text() for word in ('LEARN', 'CREATE & PREPARE', 'TRACK & MANAGE')))
            check('Home has no horizontal overflow', page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'))
            page.screenshot(path=str(SHOTS / 'study-scope-sidebar-1440x960.png'), animations='disabled')
            check('No browser errors', not errors)
        except Exception:
            page.screenshot(path=str(SHOTS / 'failure.png'), animations='disabled')
            raise
        finally:
            (OUT / 'results.json').write_text(json.dumps({'count': len(checks), 'cases': checks, 'errors': errors, 'native_windows': False}, indent=2) + '\n', encoding='utf8')
            browser.close()
    print('TOTAL', len(checks))


if __name__ == '__main__':
    main()
