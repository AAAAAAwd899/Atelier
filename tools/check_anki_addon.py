"""Bounded, read-only validation of the distributable Anki desktop add-on.

Technical packaging evidence, not AnkiWeb approval or a legal certification.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]

def inspect(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist();assert names and len(names)==len(set(names)), 'Duplicate package entries'
        assert not z.testzip(), 'ZIP integrity failure'
        required={'__init__.py','manifest.json','config.json','config.schema.json','LICENSE','NOTICE','PRIVACY.md',
                  'sprout/LICENSE','workshop/LICENSE','workshop/vendor/pypdf/LICENSE'}
        assert required<=set(names),'Missing runtime/manifest/license notice'
        for name in names:
            p=PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in name, 'Unsafe archive path'
            assert '__pycache__' not in p.parts and p.suffix not in ('.pyc','.pyo'), 'Python cache included'
            assert p.name!='meta.json' and not p.name.startswith('.env'), 'User or secret configuration included'
            assert p.suffix.lower() not in ('.anki2','.db','.sqlite','.sqlite3','.pem','.key','.ttf','.otf','.woff','.woff2'), 'Private or excluded payload'
            assert 'user_files' not in p.parts or name=='user_files/README.txt','Saved work included'
            info=z.getinfo(name);assert not info.flag_bits&1,'Encrypted member'
            assert (info.external_attr>>16)&0o170000!=0o120000,'Symlink member'
        manifest=json.loads(z.read('manifest.json'))
        assert manifest['package']=='daedalus_atelier' and manifest['name']=='Atelier'
        assert manifest['human_version'] in ('1.0.5','1.0.6','1.0.7') and manifest['min_point_version']==250905
        assert isinstance(manifest.get('conflicts'),list) and set(manifest['conflicts'])=={'exam_sprout','daedalus_workshop'}
        assert all(b'Permission is hereby granted' in z.read(n) for n in ['LICENSE','sprout/LICENSE','workshop/LICENSE'])
        assert b'Redistribution and use' in z.read('workshop/vendor/pypdf/LICENSE')
        return {'version':manifest['human_version'],'format':'Anki desktop .ankiaddon ZIP','package':manifest['package'],
                'minimum_anki':'25.09.5','members':len(names),'root_entrypoint':True,'manifest_valid':True,'zip_integrity':True,
                'unsafe_or_private_entries':0,'license_notices_present':True,'ankiweb_listing_verified':False,
                'installer_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('installer',type=Path);ap.add_argument('--report',type=Path)
    args=ap.parse_args();report=inspect(args.installer)
    if args.report:args.report.parent.mkdir(parents=True,exist_ok=True);args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))
