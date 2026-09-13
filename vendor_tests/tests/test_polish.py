"""0.9.1: presentation/upgrade regression tests; no native Anki claims."""
from copy import deepcopy
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
import json
import pytest
from addon.core import THEMES
from addon.storage import Store, settings_from
from addon.widget import countdown_html

class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags=[]; self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag,dict(attrs)))


def make_exam(store, **changes):
    e={'id':'exam','name':'Physiology & pharmacology','due':'2099-09-20T09:00','scopes':[{'deck_id':1,'name':'Course::Exam 3'}]}
    e.update(changes); store.save_exam(e)

@pytest.mark.parametrize('theme',THEMES)
def test_all_themes_roundtrip_without_affecting_exam_data(tmp_path,theme):
    store=Store(tmp_path); make_exam(store); previous=deepcopy(store.state['exams'])
    store.save_settings({**store.state['settings'],'theme':theme})
    restored=Store(tmp_path)
    assert restored.state['settings']['theme']==theme
    assert restored.state['exams']==previous
    assert f'data-theme="{theme}"' in countdown_html(restored)


def test_hidden_widget_can_be_previewed_without_saving_or_enabling(tmp_path):
    store=Store(tmp_path); make_exam(store)
    store.save_settings({**store.state['settings'],'show_countdown':False})
    before=store.path.read_bytes()
    assert countdown_html(store)==''
    preview=countdown_html(store,preview=True)
    assert 'data-preview="true"' in preview
    assert any(tag=='section' and 'inert' in attrs for tag,attrs in Tags(preview).tags)
    assert store.path.read_bytes()==before


def test_production_countdown_is_interactive_not_inert(tmp_path):
    store=Store(tmp_path);make_exam(store)
    markup=countdown_html(store)
    assert any(tag=='button' and attrs.get('data-exam-id')=='exam' for tag,attrs in Tags(markup).tags)
    assert all('inert' not in attrs for _,attrs in Tags(markup).tags)


def test_empty_past_and_archived_do_not_add_fictional_countdowns(tmp_path):
    store=Store(tmp_path)
    make_exam(store,due=(datetime.now()-timedelta(days=2)).isoformat(timespec='minutes'))
    make_exam(store,id='archived',archived=True)
    html=countdown_html(store)
    assert 'data-deadline' not in html
    assert 'data-exam-id=""' in html
    assert 'Add your first exam countdown' in html


def test_name_escaping_also_applies_to_attribute_and_preview(tmp_path):
    store=Store(tmp_path);make_exam(store,name='Exam " onfocus="alert(1) <script> & quiz')
    for preview in (True,False):
        html=countdown_html(store,preview=preview)
        assert '<script>' not in html
        assert 'onfocus' not in next(attrs for tag,attrs in Tags(html).tags if tag=='button')
        assert '&amp;' in html


def test_widget_count_limit_and_compact_state_preserved(tmp_path):
    store=Store(tmp_path)
    for i in range(3): make_exam(store,id=f'exam_{i}')
    store.save_settings({**store.state['settings'],'max_countdowns':1,'compact':False})
    html=countdown_html(store)
    assert html.count('data-deadline=')==1
    assert '+2 more' in html and 'data-compact="false"' in html


def test_no_remote_fonts_or_automatic_external_fetches_in_ui():
    web=Path(__file__).resolve().parents[1]/'addon/web'
    for path in web.iterdir():
        if path.suffix in ('.js','.css'):
            data=path.read_text()
            assert 'fetch(' not in data
            assert '@import' not in data
            assert 'XMLHttpRequest' not in data
            assert 'fonts.googleapis' not in data
