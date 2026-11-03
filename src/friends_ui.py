"""Profile-bound Friends window. Networking never holds Anki's collection lock.

Only explicit attachments can auto-publish. Downloads always use Anki's native
import confirmation. This module does not patch another add-on or the scheduler.
"""
from __future__ import annotations

import copy
import json
import secrets
import tempfile
from pathlib import Path

from aqt.operations import QueryOp
from aqt.qt import QDialog, QTimer, QVBoxLayout
from aqt.webview import AnkiWebView
from .core import ValidationError, fresh_catalog, json_for_html, profile_settings
from .friends_client import FriendsClient, FriendsError
from .social_models import sharing_settings, service_settings

ROOT = Path(__file__).parent


class FriendsWindow(QDialog):
    def __init__(self, controller, mw, tab):
        super().__init__(mw)
        self.controller = controller
        self.setWindowTitle('Atelier · Friends & companion journey')
        self.resize(1080, 790)
        self.setMinimumSize(560, 450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.web = AnkiWebView(title='Atelier Friends')
        layout.addWidget(self.web)
        self.nonce = secrets.token_hex(20)
        self.web.set_bridge_command(self.receive, self)
        cfg = controller.owner.get_config()
        from .review_model import PALETTES
        # Theme only our document. With visuals off use Anki's light/dark neutral.
        from aqt.theme import theme_manager
        p = PALETTES[cfg['theme']] if cfg['visual_owner'] == 'atelier' and cfg['mode'] != 'native' else None
        tokens = ''.join(f'--social-{k}:{v};' for k, v in (p or {}).items())
        boot = {'nonce': self.nonce, 'tab': tab, 'assets': '/_addons/' + controller.owner.package + '/sprout/web/pip',
                'dark': theme_manager.night_mode, 'motion': cfg.get('motion', True)}
        css = (ROOT / 'web/social.css').read_text(encoding='utf-8')
        js = (ROOT / 'web/social.js').read_text(encoding='utf-8')
        self.web.stdHtml('<main id="atelier-social"></main><script>window.AtelierSocialBoot=' + json_for_html(boot)
                         + ';</script><script>' + js + '</script>', js=[], default_css=False,
                         head='<style>' + css + '</style><style>#atelier-social[data-dark=true],#atelier-social[data-dark=false]{' + tokens + '}</style>', context=self)

    def receive(self, message):
        if not self.controller.valid() or not isinstance(message, str) or len(message) > 32768:
            return
        try:
            value = json.loads(message)
            if value.get('nonce') != self.nonce or not isinstance(value.get('data', {}), dict):
                return
            self.controller.command(value.get('op'), value.get('data', {}))
        except OSError:
            self.deliver({'error': 'A file could not be saved. Existing Anki data was kept; check available space and try again.'})
        except (ValueError, TypeError, ValidationError) as exc:
            self.deliver({'error': str(exc)[:240]})

    def deliver(self, data):
        try:
            self.web.eval('window.AtelierSocial?.receive(' + json_for_html(data) + ');')
        except (RuntimeError, AttributeError):
            pass


class FriendsController:
    def __init__(self, owner, mw):
        self.owner, self.mw = owner, mw
        self.col, self.store = mw.col, owner.store
        self.client = FriendsClient(owner.get_config())
        self.window = None
        self.busy = False
        self.stopped = False
        self.home = {}
        self.notice = ''
        self.suspended = set()
        self.timer = QTimer(mw)
        self.timer.setSingleShot(True)
        self.timer.setInterval(15000)
        self.timer.timeout.connect(self.scan_auto)

    def valid(self):
        return not self.stopped and self.mw.col is self.col and self.owner.store is self.store

    def open(self, tab='shared'):
        if not self.valid():
            return
        if self.window is None:
            self.window = FriendsWindow(self, self.mw, tab)
        else:
            self.window.deliver({'tab': tab})
            self.refresh()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def shutdown(self):
        self.stopped = True
        self.timer.stop()
        self.timer.deleteLater()
        self.client.close()
        self.home = {}
        if self.window:
            self.window.close()
            self.window.web.cleanup()
            self.window.deleteLater()
            self.window = None

    def changed(self, *_):
        if self.valid() and self.client.account:
            self.timer.start()

    def send(self, data):
        if self.valid() and self.window:
            self.window.deliver(data)

    def save(self, key, value):
        if not self.valid():
            raise ValidationError('This profile has closed. Open Friends again.')
        updated = profile_settings(dict(self.owner.profile, **{key: value}))
        self.store.write(updated)
        self.owner.profile = updated

    def refresh(self):
        if not self.valid():
            return
        profile = copy.deepcopy(self.owner.profile)
        def local(col):
            from .companion_journey import status
            cat = fresh_catalog(col)
            return {'journey': status(col, profile), 'decks': [
                {'id': k, 'name': v['name']} for k, v in list(cat.items())[:10000]],
                'focus': [s['name'] for s in profile.get('studies', []) if s.get('active')][:24]}
        def done(result):
            if self.valid():
                result.update(self.client.public_state(), home=self.home, sharing=sharing_settings(self.owner.profile.get('sharing')),
                              account=self.client.account, origin=self.client.origin_hash, busy=self.busy,
                              notice=self.notice, suspended=list(self.suspended))
                self.send({'state': result})
        QueryOp(parent=self.mw, op=local, success=done).failure(self.failed).run_in_background()

    def failed(self, error):
        if not self.valid():
            return
        self.busy = False
        self.notice = str(error)[:240] if isinstance(error, ValidationError) else 'This action could not finish. Your local decks are unchanged.'
        if not self.client.account: self.home = {}
        self.send({'error': self.notice, 'busy': False, 'signed_out': not bool(self.client.account)})

    def network(self, work, success=None):
        if not self.valid():
            return
        self.busy = True
        self.send({'busy': True})
        def done(future):
            try:
                value = future.result()
                if not self.valid():
                    return
                self.busy = False
                if success:
                    success(value)
                self.refresh()
            except Exception as exc:
                self.failed(exc)
        self.mw.taskman.run_in_background(work, done, uses_collection=False)

    def bound(self, course):
        return course['account'] == self.client.account and course['origin'] == self.client.origin_hash

    def local_course(self, key):
        courses = sharing_settings(self.owner.profile.get('sharing'))['courses']
        c = next((x for x in courses if x['id'] == key and self.bound(x)), None)
        if not c:
            raise FriendsError('Attach folders for this account before publishing this course.')
        return c

    def command(self, op, data):
        if not self.valid():
            return
        if op == 'ready':
            self.refresh(); return
        if self.busy:
            raise FriendsError('Wait for the current action to finish.')
        if op == 'refresh':
            if self.client.account:
                self.network(lambda: self.client.rpc('home'), self.set_home)
            else:
                self.refresh()
        elif op == 'configure':
            cfg = service_settings({'friends_url': data.get('url'), 'friends_public_key': data.get('key')})
            raw = self.mw.addonManager.getConfig(self.owner.module) or {}
            raw.update(cfg)
            self.mw.addonManager.writeConfig(self.owner.module, raw)
            self.client.close()
            self.client = FriendsClient(cfg)
            self.home = {}
            self.notice = 'Service settings saved. Sign in with your invited email.'
            self.refresh()
        elif op == 'send_code':
            self.network(lambda: self.client.send_code(data.get('email')), lambda _: self.send({'code_sent': True}))
        elif op == 'verify_code':
            self.network(lambda: self.client.verify_code(data.get('email'), data.get('code')), self.set_home)
        elif op == 'logout':
            self.network(self.client.logout, lambda _: self.set_home({}))
        elif op in ('profile', 'invite_create', 'invite_preview', 'invite_accept', 'friend_remove', 'course_update', 'snapshot_cancel', 'course_revoke'):
            client = self.client
            def work():
                value = client.rpc(op, data)
                return value, client.rpc('home')
            def completed(value):
                out, home = value
                self.set_home(home)
                if op == 'invite_create': self.send({'invite': out})
                elif op == 'invite_preview': self.send({'inviter': out})
                elif op == 'course_revoke':
                    saved = sharing_settings(self.owner.profile.get('sharing'))
                    for c in saved['courses']:
                        if c['id'] == data.get('id'): c['auto'] = False
                    self.save('sharing', saved)
                self.notice = 'Saved.' if op not in ('invite_create', 'invite_preview') else ''
            self.network(work, completed)
        elif op == 'attach':
            roots = data.get('deck_ids')
            # Validate the real hierarchy before creating remote metadata.
            self.busy = True
            def checked(_):
                client = self.client
                def create():
                    out = client.rpc('course_create', {'title': data.get('title'), 'recipients': data.get('recipients')})
                    return out, client.rpc('home')
                def attached(value):
                    out, home = value
                    saved = sharing_settings(self.owner.profile.get('sharing'))
                    saved['courses'].append({'id': out['id'], 'title': data.get('title'), 'deck_ids': roots,
                        'account': client.account, 'origin': client.origin_hash, 'auto': data.get('auto') is True,
                        'digest': '', 'version': 0})
                    self.save('sharing', saved)
                    self.set_home(home)
                    self.notice = 'Folders attached. Automatic publishing will start shortly.' if data.get('auto') is True else 'Folders attached. Publish the first version when you are ready.'
                self.network(create, attached)
            from .folder_sharing import inspect_scope
            QueryOp(parent=self.mw, op=lambda c: inspect_scope(c, roots), success=checked).failure(self.failed).run_in_background()
        elif op == 'automatic':
            course = self.local_course(data.get('id'))
            if type(data.get('enabled')) is not bool: raise FriendsError('Choose an update preference.')
            saved = sharing_settings(self.owner.profile.get('sharing'))
            for c in saved['courses']:
                if c['id'] == course['id']: c['auto'] = data['enabled']
            self.save('sharing', saved)
            self.suspended.discard(course['id'])
            self.notice = 'Automatic publishing enabled while Friends is signed in.' if data['enabled'] else 'Automatic publishing paused.'
            self.changed(); self.refresh()
        elif op == 'publish':
            course = self.local_course(data.get('id'))
            self.suspended.discard(course['id'])
            self.publish(course)
        elif op == 'download':
            self.download(data.get('id'))
        elif op == 'journey_claim':
            key = data.get('id')
            from .companion_journey import claim
            profile = copy.deepcopy(self.owner.profile)
            self.busy = True
            def claimed(saved):
                try:
                    if self.valid():
                        # Merge this one earned key into the current preference file.
                        from .social_models import journey_settings
                        current = journey_settings(self.owner.profile.get('journey'))
                        current['earned'].update(saved['earned'])
                        self.save('journey', current)
                        self.busy = False
                        self.notice = 'Keepsake collected. It stays yours.'
                        self.refresh()
                except Exception as exc: self.failed(exc)
            QueryOp(parent=self.mw, op=lambda col: claim(col, profile, key), success=claimed).failure(self.failed).run_in_background()
        elif op in ('journey_equip', 'journey_reflection'):
            from .companion_journey import change
            self.save('journey', change(self.owner.profile, 'equip' if op.endswith('equip') else 'reflection', data.get('value')))
            self.owner.sprout_link.refresh()
            self.notice = 'Scene chosen.' if op.endswith('equip') else 'Reflection saved on this device.'
            self.refresh()
        elif op == 'focus_open':
            self.owner.open()
        elif op == 'export_local':
            from .study_progress import export_deck
            self.owner._export_dialog = export_deck(self.mw, data.get('id'))
        else:
            raise FriendsError('Choose a Friends or companion action.')

    def set_home(self, value):
        self.home = value
        self.notice = ''
        if self.client.account:
            self.changed()

    def scan_auto(self):
        if not self.valid() or not self.client.account:
            return
        if self.busy or self.mw.state != 'deckBrowser':
            self.timer.start(30000); return
        courses = [x for x in sharing_settings(self.owner.profile.get('sharing'))['courses']
                   if self.bound(x) and x['auto'] and x['id'] not in self.suspended]
        if not courses:
            return
        self.busy = True
        self.send({'busy': True})
        from .folder_sharing import inspect_scope
        def inspect(col):
            return next((c for c in courses if inspect_scope(col, c['deck_ids'])['digest'] != c['digest']), None)
        def checked(course):
            if not self.valid(): return
            self.busy = False
            if course: self.publish(course, automatic=True)
        QueryOp(parent=self.mw, op=inspect, success=checked).failure(self.failed).run_in_background()

    def publish(self, course, automatic=False):
        if not self.valid(): return
        self.busy = True
        self.send({'busy': True})
        stage = tempfile.TemporaryDirectory(prefix='atelier-share-')
        target = Path(stage.name) / 'course.apkg'
        from .folder_sharing import export_scope
        client = self.client
        def exported(meta):
            if not self.valid(): stage.cleanup(); return
            def transfer():
                try:
                    home = client.rpc('home')
                    remote = next((x for x in home.get('courses', []) if x['id'] == course['id'] and x['enabled']), None)
                    if not remote: raise FriendsError('This course is no longer shared.')
                    if remote.get('pending_id'): raise FriendsError('Cancel the unfinished upload before publishing again.')
                    ticket = client.rpc('snapshot_begin', {'course_id': course['id'], 'previous_version': remote['version'],
                                                         'bytes': meta['bytes'], 'sha256': meta['sha256']})
                    result = client.upload(ticket['id'], target)
                    return result, client.rpc('home')
                finally:
                    stage.cleanup()
            def completed(value):
                result, home = value
                saved = sharing_settings(self.owner.profile.get('sharing'))
                for c in saved['courses']:
                    if c['id'] == course['id'] and self.bound(c):
                        c.update(digest=meta['digest'], version=result['version'])
                self.save('sharing', saved)
                self.home = home
                self.notice = 'Version ' + str(result['version']) + ' is ready for your friends to import.'
                self.changed()
            # Failure suspends this course until an explicit retry or preference change.
            self.suspended.add(course['id'])
            def success(value):
                completed(value)
                self.suspended.discard(course['id'])
            self.network(transfer, success)
        def failed(error):
            stage.cleanup()
            self.suspended.add(course['id'])
            self.failed(error)
        QueryOp(parent=self.mw, op=lambda col: export_scope(col, course['deck_ids'], target), success=exported).failure(failed).run_in_background()

    def download(self, key):
        row = next((x for x in self.home.get('inbox', []) if x['id'] == key), None)
        if not row: raise FriendsError('Refresh Friends and choose an available shared course.')
        from aqt.qt import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self.window, 'Save shared Anki package', 'Shared course.apkg', 'Anki deck package (*.apkg)')
        if not path: return
        client = self.client
        def completed(value):
            self.notice = 'Package verified and saved. Anki will ask how to import it.'
            saved = sharing_settings(self.owner.profile.get('sharing'))
            saved['received'][row['id']] = row['version']
            self.save('sharing', saved)
            # This is the native importer with its normal update/conflict controls.
            from aqt.importing import importFile
            importFile(self.mw, value['path'])
        self.network(lambda: client.download(row['latest_id'], path, row['bytes'], row['sha256']), completed)


def open_friends(owner, mw, tab='shared'):
    if not mw.col:
        from aqt.utils import showInfo
        showInfo('Open an Anki profile first.'); return
    owner.ensure_store()
    if not getattr(owner, 'friends', None): owner.friends = FriendsController(owner, mw)
    owner.friends.open(tab)
