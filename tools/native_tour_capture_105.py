"""Manual foreground review of real Anki/Qt in an isolated unsynced profile.

Use computer-use to capture the visible window. No synthetic browser fixture.
Automatically closes gracefully after five minutes if the reviewer leaves it open.
"""
from pathlib import Path
import os,sys,time,zipfile
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'output/native-onboarding-105'/('manual-capture-'+str(time.time_ns()));BASE.mkdir(parents=True)
target=BASE/'addons21/daedalus_atelier';target.mkdir(parents=True)
with zipfile.ZipFile(ROOT/'dist/Atelier-1.0.5.ankiaddon') as z:z.extractall(target)
os.environ.update(QT_QPA_PLATFORM='windows',QTWEBENGINE_CHROMIUM_FLAGS='--disable-gpu --no-sandbox --disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling',ANKI_SOFTWAREOPENGL='1',QTWEBENGINE_DISABLE_SANDBOX='1')
import anki.lang
anki.lang.set_lang('en_US')
from aqt.profiles import ProfileManager
pm=ProfileManager(str(BASE));pm.setupMeta();pm.create('Tour Capture QA');pm.load('Tour Capture QA')
pm.meta.update(firstRun=False,defaultLang='en_US',check_for_updates=False);pm.profile['autoSync']=False;pm.save();pm.db.close()
import aqt
from aqt.qt import QTimer
aqt.AnkiApp.secondInstance=lambda self:False
app=aqt._run(['anki','-b',str(BASE),'-p','Tour Capture QA','-l','en_US'],exec=False)
QTimer.singleShot(1000,lambda:aqt.mw.resize(1100,650))
QTimer.singleShot(300000,lambda:aqt.mw.unloadProfileAndExit())
app.exec()
