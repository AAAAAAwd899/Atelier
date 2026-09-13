from fixtures import *
from preview_071 import home071
from playwright.sync_api import sync_playwright
import html
D=ROOT/'dist';D.mkdir(exist_ok=True)
# The screenshot and preview embed the actual release reviewer/footer assets.
main=card('obsidian','basic').replace('<p>What makes an effective study session?</p><p id="answer" hidden>One clear objective. A manageable set of questions.</p>', '<p>What two hormones are released by the posterior pituitary?</p>')
main=main.replace('"Sample collection", "Study skills", "Lecture 1"','"Pharmacy School", "Endocrinology", "Hypothalamic–pituitary axis"')
bar=footer('obsidian','question','old',True)
top='''<html><head><style>html,body{margin:0;background:#10131e;font:13px "Segoe UI",Arial;color:#c2c6d5}nav{height:54px;display:flex;justify-content:center;align-items:center;gap:9px}button{font:inherit;border:1px solid #35394b;background:#1b2032;border-radius:9px;padding:8px 14px;color:inherit}</style></head><body><nav><button>Decks</button><button>Add</button><button>Browse</button><button>Stats</button><button>Sync</button></nav></body></html>'''
page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Atelier 0.7.1 reviewer layout fixture</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#10131e}.app{display:grid;grid-template-rows:54px minmax(0,1fr) 116px;height:100dvh}iframe{width:100%;height:100%;min-height:0;border:0;display:block}.note{position:fixed;top:18px;left:20px;color:#a8afc8;font:10px system-ui;letter-spacing:1px;pointer-events:none}</style></head><body><div class="app"><iframe title="Sample navigation" srcdoc="'''+html.escape(top,quote=True)+'''"></iframe><iframe title="Shipped card styling" srcdoc="'''+html.escape(main,quote=True)+'''"></iframe><iframe title="Shipped footer styling" srcdoc="'''+html.escape(bar,quote=True)+'''"></iframe></div><div class="note">ATELIER 0.7.1 / BROWSER FIXTURE</div></body></html>'''
(D/'Atelier-0.7.1-Reviewer-Preview.html').write_text(page)
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 p=b.new_page(viewport={'width':1440,'height':850},device_scale_factor=1);p.set_content(page);p.wait_for_timeout(500)
 p.screenshot(path=str(D/'Atelier-0.7.1-Reviewer.png'))
 p.set_content(home071('ask'));p.wait_for_timeout(200);p.screenshot(path=str(D/'Atelier-0.7.1-Owner-Choice.png'))
 b.close()
