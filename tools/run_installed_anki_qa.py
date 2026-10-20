"""Run a repository QA script against the installed MSI's Anki/Qt packages.

Invoke using the pre-existing compatible CPython 3.13 interpreter. This does not
install dependencies or modify the MSI. The official launcher is checked separately.
"""
from pathlib import Path
import os,runpy,site,sys
ROOT=Path(__file__).resolve().parents[1]
APP=Path.home()/'AppData/Local/Programs/Anki'
PACKAGES=APP/'app_packages'
assert sys.version_info[:2]==(3,13)
assert PACKAGES.is_dir()
sys.path.insert(0,str(PACKAGES))
site.addsitedir(str(PACKAGES))
os.environ['PATH']=str(APP)+os.pathsep+os.environ['PATH']
script=(ROOT/sys.argv[1]).resolve()
assert script.is_relative_to(ROOT) and script.suffix=='.py'
sys.argv=[str(script),*sys.argv[2:]]
runpy.run_path(str(script),run_name='__main__')
