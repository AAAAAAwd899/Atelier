"""Original-card preview, deliberately separate from scheduled review."""
from aqt.browser.previewer import Previewer
from aqt.qt import QPushButton,QDialogButtonBox,QComboBox
from .core import ValidationError

class CardPreview(Previewer):
    def __init__(self,controller,ids):
        self.controller=controller;self.ids=list(ids);self.index=0;self.last_id=None
        self.collection=controller.mw.col;self.epoch=controller.epoch
        super().__init__(parent=None,mw=controller.mw,on_close=self._finished)
    def card(self):
        if self.mw.col is not self.collection or self.epoch!=self.controller.epoch:return None
        try:return self.collection.get_card(self.ids[self.index])
        except Exception:return None
    def card_changed(self):
        current=self.ids[self.index];changed=current!=self.last_id;self.last_id=current;return changed
    def _create_gui(self):
        super()._create_gui()
        self.setWindowTitle('Workshop · Original card preview')
        self.selector=QComboBox(self)
        for i in range(len(self.ids)):self.selector.addItem(f'Card {i+1} of {len(self.ids)}')
        self.selector.activated.connect(self._select);self.vbox.insertWidget(0,self.selector)
        flip=self.bbox.addButton('Reveal / hide answer',QDialogButtonBox.ButtonRole.ActionRole)
        flip.clicked.connect(self._flip)
        close=self.bbox.addButton('Close',QDialogButtonBox.ButtonRole.RejectRole);close.clicked.connect(self.close)
    def _flip(self):
        if not self.card():self.close();return
        self._show_both_sides=False
        self._state='answer' if self._state=='question' else 'question';self.render_card()
    def _select(self,index):
        self.index=max(0,min(len(self.ids)-1,index));self._state='question';self.render_card()
    def _finished(self):
        previews=getattr(self.controller,'previews',[])
        if self in previews:previews.remove(self)
