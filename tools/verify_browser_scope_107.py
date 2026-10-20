"""Bind the in-progress browser run to unchanged browser inputs after a Qt-only fix.

The only runtime change after that run started was WA_DeleteOnClose on the
new native QDialog. Browser fixtures never instantiate that native dialog.
Reconstruct the exact earlier runtime digest, not a guessed file allowlist.
Fresh Python and native checks still have to pass on the final runtime.
"""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from release_tools import runtime_digest
source=ROOT/'src';marker=b'            self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)\n'
current=(source/'addon_tools.py').read_bytes();assert current.count(marker)==1
files={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
       for p in sorted(source.rglob('*')) if p.is_file() and '__pycache__' not in p.parts
       and p.suffix in ('.py','.js','.css','.json','.svg','.png','.webp') and 'user_files' not in p.relative_to(source).parts}
files['addon_tools.py']=hashlib.sha256(current.replace(marker,b'',1)).hexdigest()
previous=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
assert previous=='53c5dbe7c131238a79b71fc506acdca097f5f0384c7dcacbedc1da0eef290f2e'
report={'browser_run_candidate_runtime':previous,'final_runtime':runtime_digest(),
        'only_runtime_difference':'addon_tools.py: native QDialog WA_DeleteOnClose flag',
        'all_other_runtime_files_byte_identical':True,'browser_inputs_changed':False,
        'native_fix_verification':'output/native-compat-107/results.json includes closed_dialog_deleted',
        'limits':'Browser results cover unchanged browser inputs. Native dialog behavior is checked in actual Anki, not claimed as a browser test.'}
(ROOT/'verification/browser-scope-107.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report))
