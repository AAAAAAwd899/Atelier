"""Small explicit Qt control/layout double. NOT a Qt renderer or DPI test."""
from types import SimpleNamespace,ModuleType

class Signal:
 def __init__(self):self.handlers=[]
 def connect(self,f):self.handlers.append(f)
 def emit(self,*args):
  for f in self.handlers:f(*args)

class Widget:
 def __init__(self,*args):
  self.parent=next((x for x in reversed(args) if isinstance(x,Widget)),None)
  self.text=next((x for x in args if isinstance(x,str)), '')
  self.name='';self.hidden=False;self.enabled=True;self.checked=False;self._width=1180;self._height=820;self.styles='';self._layout=None
  self.clicked=Signal();self.activated=Signal();self.timeout=Signal();self.textChanged=Signal();self.items=[];self.current=0;self.focus=False
 def setObjectName(self,v):self.name=v
 def setText(self,v):self.text=v
 def setTextFormat(self,v):pass
 def setWordWrap(self,v):self.word_wrap=v
 def setStyleSheet(self,v):self.styles=v
 def setMinimumHeight(self,v):self.minheight=v
 def setMaximumHeight(self,v):self.maxheight=v
 def setMinimumWidth(self,v):self.minwidth=v
 def setMaximumWidth(self,v):self.maxwidth=v
 def setAutoDefault(self,v):pass
 def setCheckable(self,v):self.checkable=v
 def setChecked(self,v):self.checked=v
 def isChecked(self):return self.checked
 def setEnabled(self,v):self.enabled=v
 def setVisible(self,v):self.hidden=not v
 def isHidden(self):return self.hidden
 def show(self):self.hidden=False
 def hide(self):self.hidden=True
 def setAccessibleName(self,v):self.accessible=v
 def setToolTip(self,v):self.tip=v
 def setBuddy(self,w):self.buddy=w
 def setPlainText(self,v):self.text=v
 def toPlainText(self):return self.text
 def isReadOnly(self):return getattr(self,'read_only',False)
 def setReadOnly(self,v):self.read_only=v
 def setFocus(self):self.focus=True
 def addItem(self,label,data=None):self.items.append((label,data))
 def itemData(self,index):return self.items[index][1]
 def setCurrentIndex(self,v):self.current=v
 def setRange(self,a,b):pass
 def setValue(self,v):self.value=v
 def installEventFilter(self,f):self.filter=f
 def width(self):return self._width
 def height(self):return self._height
 def setOrientation(self,v):self.orientation=v
 def setSizes(self,v):self.sizes=v
 def setSingleShot(self,v):pass
 def start(self,*args):pass
 def click(self):
  if self.enabled:
   if getattr(self,'checkable',False):self.checked=not self.checked
   self.clicked.emit()

class Item:
 def __init__(self,v):self.v=v
 def widget(self):return self.v if isinstance(self.v,Widget) else None

class Layout:
 def __init__(self,parent=None):self.parent=parent;self.items=[]
 def count(self):return len(self.items)
 def itemAt(self,index):return self.items[index]
 def takeAt(self,index):
  x=self.items.pop(index)
  if isinstance(x.v,Widget):x.v._layout=None
  return x
 def addWidget(self,w,*args):
  if w._layout and w._layout is not self:w._layout.removeWidget(w)
  w._layout=self;self.items.append(Item(w));w.parent=self.parent
 def insertWidget(self,i,w):
  self.addWidget(w);item=self.items.pop();self.items.insert(i,item)
 def removeWidget(self,w):self.items=[i for i in self.items if i.v is not w];w._layout=None
 def addLayout(self,l):self.items.append(Item(l))
 def addStretch(self,n=1):self.items.append(Item(None))
 def setContentsMargins(self,*args):pass
 def setSpacing(self,v):pass
 def setColumnStretch(self,*args):pass

Qt=SimpleNamespace(TextFormat=SimpleNamespace(PlainText=1),Orientation=SimpleNamespace(Horizontal=1,Vertical=2))
QEvent=SimpleNamespace(Type=SimpleNamespace(Resize=1))
def install(monkeypatch):
 aqt=ModuleType('aqt');qt=ModuleType('aqt.qt')
 for n in ('QObject','QWidget','QLabel','QFrame','QPushButton','QComboBox','QTimer'):setattr(qt,n,Widget)
 for n in ('QVBoxLayout','QHBoxLayout','QGridLayout'):setattr(qt,n,Layout)
 qt.Qt=Qt;qt.QEvent=QEvent
 theme=ModuleType('aqt.theme');theme.theme_manager=SimpleNamespace(night_mode=True)
 monkeypatch.setitem(__import__('sys').modules,'aqt',aqt);monkeypatch.setitem(__import__('sys').modules,'aqt.qt',qt);monkeypatch.setitem(__import__('sys').modules,'aqt.theme',theme)
 return qt
