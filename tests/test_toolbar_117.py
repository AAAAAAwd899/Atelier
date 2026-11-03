"""Toolbar recovery policy without importing Qt or touching an owner profile."""
import ast
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.mark.parametrize('state,owner,mode,enabled,fullscreen,hidden,shows',[
 ('deckBrowser','atelier','workspace',True,False,True,1),
 ('deckBrowser','atelier','workspace',True,False,False,0),
 ('deckBrowser','atelier','workspace',False,False,True,0),
 ('deckBrowser','onigiri','workspace',True,False,True,0),
 ('deckBrowser','atelier','native',True,False,True,0),
 ('review','atelier','workspace',True,False,True,0),
 ('overview','atelier','workspace',True,False,True,0),
 ('deckBrowser','atelier','workspace',True,True,True,0),
])
def test_native_toolbar_recovery_scope(state,owner,mode,enabled,fullscreen,hidden,shows):
 tree=ast.parse((ROOT/'src/integration.py').read_text())
 fn=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='restore_native_toolbar')
 calls=[];web=SimpleNamespace(isHidden=lambda:hidden,setVisible=lambda value:calls.append(value))
 mw=SimpleNamespace(state=state,fullscreen=fullscreen,toolbarWeb=web)
 cfg={'visual_owner':owner,'mode':mode,'native_toolbar':enabled}
 namespace={'mw':mw};exec(compile(ast.Module(body=[fn],type_ignores=[]),'toolbar-policy','exec'),namespace)
 namespace['restore_native_toolbar'](SimpleNamespace(get_config=lambda:cfg))
 assert len(calls)==shows
 assert cfg=={'visual_owner':owner,'mode':mode,'native_toolbar':enabled}
