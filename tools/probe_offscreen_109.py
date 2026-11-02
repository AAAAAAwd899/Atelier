"""Confirm the installed Qt can test without creating a Windows desktop window."""
import os,json
os.environ['QT_QPA_PLATFORM']='offscreen'
from aqt.qt import QApplication
app=QApplication([])
assert app.platformName()=='offscreen'
print(json.dumps({'platform':app.platformName(),'desktop_windows_created':False}))
