"""Menu-access boundary tests; native QAction execution is verified separately."""
from fixtures import *
from types import SimpleNamespace as NS
import pytest
tools=importlib.import_module('atelier_testing.addon_tools')

class Action:
    def __init__(self,text,menu=None,enabled=True,visible=True):
        self.title=text;self.child=menu;self.enabled=enabled;self.visible=visible
    def text(self):return self.title
    def menu(self):return self.child
    def isSeparator(self):return not self.title
    def isVisible(self):return self.visible
    def isEnabled(self):return self.enabled

class Menu:
    def __init__(self,title,*actions):self.name=title;self.items=list(actions)
    def title(self):return self.name
    def actions(self):return self.items

def host(*menus):
    file=Menu('File',Action('Delete profile'));core=Menu('Tools',Action('Anki add-ons'))
    bar=Menu('',Action('File',file),Action('Tools',core),*(Action(m.title(),m) for m in menus))
    return NS(form=NS(menuFile=file,menuTools=core),menuBar=lambda:bar),core

def test_original_qactions_are_retained_and_no_foreign_signal_is_emitted():
    command=Action('Open companion');menu=Menu('Study rewards',command);mw,_=host(menu)
    rows,truncated=tools.collect(mw)
    assert not truncated and next(r for r in rows if r['title']=='Open companion')['action'] is command
    assert not any(r['title']=='Delete profile' for r in rows)

def test_nested_disabled_parent_is_respected_even_when_child_is_enabled():
    command=Action('Open');mw,core=host();parent=Action('Extra',Menu('Extra',command),enabled=False);core.items.append(parent)
    row=next(r for r in tools.collect(mw)[0] if r['title']=='Open')
    assert not tools.usable(row);parent.enabled=True;assert tools.usable(row)
    command.visible=False;assert not tools.usable(row)

def test_original_settings_menu_is_not_recursively_indexed():
    own=Menu('Atelier',Action('Add-on tools'));mw,core=host();core.items.append(Action('Atelier',own))
    rows,_=tools.collect(mw,NS(menu=own));assert not any(r['title']=='Add-on tools' for r in rows)

def test_refresh_discovers_late_commands_and_deduplicates_shared_action():
    command=Action('Late command');mw,core=host(Menu('Other',command));core.items.extend([command,Action('',None),Action('Hidden',visible=False)])
    assert len([r for r in tools.collect(mw)[0] if r['action'] is command])==1
    core.items.append(Action('Just added'));assert any(r['title']=='Just added' for r in tools.collect(mw)[0])

def test_menu_cycles_and_large_lists_are_bounded():
    menu=Menu('Cycle');menu.items.append(Action('Again',menu));mw,core=host(menu)
    core.items.extend(Action(f'Command {i}') for i in range(600));rows,truncated=tools.collect(mw)
    assert len(rows)==500 and truncated

def test_qobject_deleted_after_listing_is_never_usable():
    class Deleted(Action):
        def isEnabled(self):raise RuntimeError('wrapped C++ object deleted')
    assert not tools.usable({'action':Deleted('Removed'),'ancestors':()})

@pytest.mark.parametrize('text,expected',[('&Settings','Settings'),('A && B','A & B'),('Open\tCtrl+O','Open')])
def test_mnemonics_are_cleaned_without_removing_literal_ampersands(text,expected):
    assert tools.label(text)==expected

def test_menu_widget_controls_are_left_in_their_original_menu():
    control=Action('Volume');control.defaultWidget=lambda:object();mw,core=host();core.items.append(control)
    assert not any(r['action'] is control for r in tools.collect(mw)[0])
