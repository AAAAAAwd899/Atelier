"""Index existing Qt menu actions. No add-on imports, settings or command bridge."""
from __future__ import annotations

LIMIT = 500


def label(text):
    return str(text).replace('&&', '\0').replace('&', '').replace('\0', '&').split('\t', 1)[0].strip()


def collect(mw, owner=None):
    """Read Tools plus additional top-level menus, without emitting menu signals.

    Commands stay as their original QActions, never serialized identifiers.
    Do not invoke aboutToShow: a third party may perform I/O in that signal.
    """
    form = getattr(mw, 'form', None)
    tools = getattr(form, 'menuTools', None)
    excluded = [getattr(form, n, None) for n in ('menuFile', 'menuEdit', 'menuView', 'menuHelp')]
    own = getattr(owner, 'menu', None)
    roots=[];rows=[];seen=set();visited=set();truncated=False
    for action in mw.menuBar().actions():
        menu=action.menu()
        if menu is not None and menu is not own and (menu is tools or menu not in excluded):
            roots.append((menu, (action,)))

    def walk(menu, trail, ancestors, depth):
        nonlocal truncated
        if depth>8 or id(menu) in visited:return
        visited.add(id(menu))
        for action in menu.actions():
            if len(rows)>=LIMIT:truncated=True;return
            if action.isSeparator() or not action.isVisible():continue
            title=label(action.text())
            if not title:continue
            child=action.menu()
            if child is not None:
                if child is not own:walk(child,trail+(title,),ancestors+(action,),depth+1)
            elif id(action) not in seen:
                # Sliders/custom widgets remain in the original menu, not a fake command.
                widget=getattr(action,'defaultWidget',None)
                if callable(widget) and widget() is not None:continue
                seen.add(id(action));rows.append({'title':title,'path':' › '.join(trail),'action':action,'ancestors':ancestors})
    for menu,ancestors in roots:
        if ancestors[0].isVisible():walk(menu,(label(menu.title()),),ancestors,0)
    return sorted(rows,key=lambda r:(r['path'].casefold(),r['title'].casefold())),truncated


def usable(row):
    try:return all(a.isEnabled() and a.isVisible() for a in (*row['ancestors'],row['action']))
    except RuntimeError:return False


def open_tools(mw, owner):
    from aqt.qt import (QDialog,QDialogButtonBox,QLabel,QLineEdit,QPushButton,
                        QTreeWidget,QTreeWidgetItem,QVBoxLayout,Qt,QTimer)
    from aqt.utils import showInfo
    if not mw.col:
        showInfo('Open an Anki profile first.');return
    old=getattr(owner,'_addon_tools_window',None)
    if old:old.reload();old.show();old.raise_();old.activateWindow();return

    class ToolsWindow(QDialog):
        def __init__(self):
            super().__init__(mw);self.collection=mw.col;self.rows=[]
            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.setWindowTitle('Atelier · Add-on tools')
            available=self.screen().availableGeometry();self.resize(min(620,available.width()-24),min(580,available.height()-32))
            layout=QVBoxLayout(self)
            heading=QLabel('Your add-ons, within reach');heading.setStyleSheet('font-size:20px;font-weight:600;');layout.addWidget(heading)
            hint=QLabel('Search commands from Tools and added top-level menus. Editor buttons and reviewer widgets stay in their own windows.')
            hint.setWordWrap(True);layout.addWidget(hint)
            self.search=QLineEdit();self.search.setPlaceholderText('Find an add-on, setting or command…');self.search.setAccessibleName('Search add-on menu commands');self.search.setClearButtonEnabled(True);layout.addWidget(self.search)
            self.tree=QTreeWidget();self.tree.setHeaderLabels(['Command','Menu','Shortcut']);self.tree.setRootIsDecorated(False);self.tree.setAlternatingRowColors(True);self.tree.setAccessibleName('Original Anki and add-on menu commands');layout.addWidget(self.tree)
            self.status=QLabel();self.status.setWordWrap(True);layout.addWidget(self.status)
            self.buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            self.open_button=QPushButton('Open selected');self.open_button.setAutoDefault(False)
            refresh=QPushButton('Refresh');refresh.setAutoDefault(False)
            self.buttons.addButton(self.open_button,QDialogButtonBox.ButtonRole.ActionRole);self.buttons.addButton(refresh,QDialogButtonBox.ButtonRole.ActionRole);layout.addWidget(self.buttons)
            self.buttons.rejected.connect(self.close);refresh.clicked.connect(self.reload)
            self.open_button.clicked.connect(self.open_selected);self.tree.itemActivated.connect(lambda *_:self.open_selected())
            self.tree.itemSelectionChanged.connect(self.selection);self.search.textChanged.connect(self.filter)
            self.timer=QTimer(self);self.timer.setInterval(500);self.timer.timeout.connect(self.selection);self.timer.start()
            self.reload();self.search.setFocus()

        def reload(self):
            self.rows,self.truncated=collect(mw,owner);self.filter()

        def filter(self,*_):
            query=self.search.text().casefold().split();self.tree.clear();count=0
            for i,row in enumerate(self.rows):
                if not all(word in (row['title']+' '+row['path']).casefold() for word in query):continue
                try:
                    action=row['action'];title=('✓ ' if action.isCheckable() and action.isChecked() else '')+row['title']
                    item=QTreeWidgetItem([title,row['path'],action.shortcut().toString()]);item.setData(0,Qt.ItemDataRole.UserRole,i);item.setIcon(0,action.icon());self.tree.addTopLevelItem(item);count+=1
                except RuntimeError:continue
            for column in (0,1):self.tree.resizeColumnToContents(column)
            self.status.setText((f'{count} commands shown. ' if count else 'No matching commands. ')+('First 500 indexed; use the original menus for more. ' if self.truncated else '')+'Not listed? Open its original menu once, then Refresh. Commands unavailable in this screen cannot be opened here.')
            self.selection()

        def selection(self):
            item=self.tree.currentItem();row=self.rows[item.data(0,Qt.ItemDataRole.UserRole)] if item else None
            self.open_button.setEnabled(bool(row and mw.col is self.collection and usable(row)))

        def open_selected(self):
            item=self.tree.currentItem()
            if not item:return
            row=self.rows[item.data(0,Qt.ItemDataRole.UserRole)]
            if mw.col is not self.collection or not usable(row):
                self.selection();showInfo('This command is unavailable in the current screen. Use its original menu after finishing the current operation.',parent=self);return
            # Recheck after closing: focus/close handlers can disable an action.
            self.close()
            def trigger():
                if mw.col is self.collection and usable(row):row['action'].trigger()
            QTimer.singleShot(0,trigger)

        def closeEvent(self,event):
            self.timer.stop();super().closeEvent(event)

    window=ToolsWindow();owner._addon_tools_window=window
    surface=getattr(owner,'native_surfaces',None)
    if surface:surface.apply(window)
    window.finished.connect(lambda *_:setattr(owner,'_addon_tools_window',None))
    window.show()
