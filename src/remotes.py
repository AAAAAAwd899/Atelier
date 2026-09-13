"""Opt-in keyboard/HID remotes. No Bluetooth driver, global hotkeys or telemetry.

Default behavior is native Anki. Custom mappings run only in the foreground
scheduled reviewer, and recheck card identity and editing state before dispatch.
Practice, Card Studio and every other app retain their existing controls.
"""
from __future__ import annotations
import json, secrets
from pathlib import Path
from .remote_model import ACTIONS, PressGate, settings
from .core import json_for_html

ROOT=Path(__file__).parent

class RemoteControls:
    def __init__(self, owner):
        self.owner=owner; self.token=''; self.input_allowed=False
        self.pending=False; self.gate=PressGate(); self.window=None; self.filter=None
    def config(self):
        return settings(self.owner.get_config().get('remote'))
    def install(self, registration, app):
        from aqt import gui_hooks
        from aqt.qt import QApplication, QObject, QEvent
        owner=self
        class Filter(QObject):
            def eventFilter(self, watched, event):
                try:
                    kind=event.type()
                    if kind not in (QEvent.Type.ShortcutOverride,QEvent.Type.KeyPress,QEvent.Type.KeyRelease):
                        if kind in (QEvent.Type.ApplicationDeactivate,QEvent.Type.WindowDeactivate): owner.gate.reset()
                        return False
                    return owner.key_event(watched,event,kind)
                except (RuntimeError,AttributeError,TypeError):
                    return False
        self.filter=Filter()
        if app:
            app.installEventFilter(self.filter)
            registration.cleanup(lambda:app.removeEventFilter(self.filter))
        registration.hook(gui_hooks.webview_will_set_content,self.add_content)
        registration.hook(gui_hooks.webview_did_receive_js_message,self.receive)
        registration.hook(gui_hooks.state_did_change,self.state_changed)
        registration.hook(gui_hooks.profile_will_close,self.reset)
        registration.cleanup(self.reset)
    def reset(self,*args):
        self.token='';self.input_allowed=False;self.pending=False;self.gate.reset()
        w=self.window;self.window=None
        if w:
            try:w.close()
            except RuntimeError:pass
    def state_changed(self,new,old):
        if new!='review': self.token='';self.input_allowed=False;self.pending=False;self.gate.reset()
    def add_content(self,content,context):
        from aqt.reviewer import Reviewer
        if not isinstance(context,Reviewer) or not self.config()['enabled']: return
        self.token=secrets.token_urlsafe(18);self.input_allowed=False
        content.head+='<script>window.AtelierRemoteToken='+json_for_html(self.token)+';</script>'
        content.js.append(f'/_addons/{self.owner.package}/web/remote-input.js?v=1.0.1')
    def receive(self,handled,message,context):
        if handled[0] or not message.startswith('atelier-remote-focus:'):return handled
        from aqt import mw
        from aqt.reviewer import Reviewer
        if not isinstance(context,Reviewer) or context is not getattr(mw,'reviewer',None):return (True,None)
        bits=message.split(':')
        if len(bits)==3 and self.token and secrets.compare_digest(bits[1],self.token):
            self.input_allowed=bits[2]=='ready' and mw.state=='review'
        return (True,None)
    def focused_web(self):
        from aqt import mw
        from aqt.qt import QApplication
        focus=QApplication.focusWidget()
        if focus is None:return None
        for name in ('web','bottomWeb'):
            web=getattr(mw,name,None)
            if web and (focus is web or web.isAncestorOf(focus)):return web
        return None
    def footer_focus(self):
        from aqt import mw
        web=getattr(mw,'bottomWeb',None)
        return web is not None and self.focused_web() is web
    def active(self,watched=None):
        from aqt import mw
        from aqt.qt import QApplication
        if not getattr(mw,'col',None) or mw.state!='review' or not mw.isActiveWindow():return False
        if QApplication.activeModalWidget() or QApplication.activePopupWidget():return False
        web=self.focused_web()
        if web is None:return False
        if watched is not None and not (watched is web or web.isAncestorOf(watched)):return False
        return True
    def key_event(self,watched,event,kind):
        from aqt.qt import QEvent, Qt
        cfg=self.config();key=int(event.key())
        if not cfg['enabled'] or not self.active(watched):return False
        action=next((a for a,k in cfg['bindings'].items() if k==key),None)
        if action is None:return False
        # KeypadModifier does not change a remote's numeric key meaning.
        mods=event.modifiers()
        if mods & (Qt.KeyboardModifier.ControlModifier|Qt.KeyboardModifier.MetaModifier|Qt.KeyboardModifier.AltModifier|Qt.KeyboardModifier.ShiftModifier):return False
        if kind==QEvent.Type.KeyRelease:
            owned=key in self.gate.down;self.gate.release(key,event.isAutoRepeat());return owned
        if not self.input_allowed and not self.footer_focus():return False
        if kind==QEvent.Type.ShortcutOverride:
            event.accept();return True
        if kind==QEvent.Type.KeyPress:
            if self.gate.press(key,event.isAutoRepeat()):self.request(action)
            event.accept();return True
        return False
    def request(self,action):
        from aqt import mw
        if self.pending or not self.config()['enabled'] or not (self.input_allowed or self.footer_focus()) or not self.active():return
        reviewer=getattr(mw,'reviewer',None);card=getattr(reviewer,'card',None)
        if card is None:return
        token=self.token;col=mw.col;cid=card.id;stage=getattr(reviewer,'state',None);source=self.focused_web();footer=self.footer_focus()
        self.pending=True
        def done(state):
            if token!=self.token:return
            self.pending=False
            if (not isinstance(state,dict) or state.get('token')!=token or not state.get('ready')
                or not self.config()['enabled'] or not self.active() or mw.col is not col
                or mw.reviewer is not reviewer or getattr(reviewer,'card',None) is not card
                or card.id!=cid or reviewer.state!=stage or self.focused_web() is not source):return
            self.dispatch(reviewer,action,stage)
        try:mw.web.evalWithCallback('window.AtelierRemoteInput?.check('+('true' if footer else 'false')+') || null',done)
        except (RuntimeError,AttributeError):self.pending=False
    def dispatch(self,reviewer,action,stage):
        # Real native commands only. Never reveal-and-rate with one custom action.
        if action=='reveal' and stage=='question':reviewer._getTypedAnswer()
        elif action in ('again','hard','good','easy') and stage=='answer':
            ease={'again':1,'hard':2,'good':3,'easy':4}[action]
            available={i for i,_ in reviewer._answerButtonList()}
            if ease in available:reviewer._answerCard(ease)
        elif action=='replay':reviewer.replayAudio()
        elif action in ('scroll_up','scroll_down'):
            direction=-1 if action=='scroll_up' else 1
            reviewer.web.eval('window.scrollBy({top:Math.max(100,innerHeight*.65)*'+str(direction)+',behavior:"auto"})')
    def save(self,value):
        from .remote_model import validate_settings
        clean=validate_settings(value)
        self.owner.save_config({'remote':clean})
        self.input_allowed=False;self.gate.reset()
        # A fresh reviewer document gets the bridge; do not reload/advance a card.
        from aqt import mw
        if mw.state=='review' and clean['enabled']:
            self.token=secrets.token_urlsafe(18)
            mw.web.eval('window.AtelierRemoteToken='+json_for_html(self.token)+';'+(ROOT/'web/remote-input.js').read_text())
        elif not clean['enabled']:
            self.token=''
            if mw.state=='review':mw.web.eval('window.AtelierRemoteInput?.dispose()')
    def open(self):
        from aqt import mw
        if not getattr(mw,'col',None):return
        if self.window:
            try:self.window.show();self.window.raise_();self.window.activateWindow();return
            except RuntimeError:self.window=None
        from .remote_ui import create_dialog
        self.window=create_dialog(self,mw)
        self.window.show();self.window.raise_();self.window.activateWindow()
