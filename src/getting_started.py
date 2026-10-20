"""Task-based reference alongside the short orientation tour. No collection writes."""
from aqt.qt import QDialog,QDialogButtonBox,QPushButton,QTextBrowser,QVBoxLayout
from .review_model import PALETTES

GUIDE='''<h1>Start with what you want to do.</h1>
<p>The guided tour shows where things live. These steps are here whenever you need a reminder.</p>
<h2>1. Bring in cards you already have</h2>
<p>For an <b>.apkg deck package</b>, open <b>Anki tools → Import file</b> or Anki’s File menu. This uses Anki’s importer. For shared decks, use Anki’s shared-deck browser from Anki tools. Only share material you have permission to distribute.</p>
<h2>2. Organize a class</h2>
<p>Open <b>Library &amp; study scope</b>. Keep a parent folder for the course, with lecture decks inside it. Use a folder’s menu to rename, move, export or study it. Star a folder for quick access. A saved study focus selects material without merging your decks.</p>
<h2>3. Choose exactly what to study</h2>
<p>On Study desk, choose <b>Study scope → Choose folders</b> (or Edit). Select any parent folders or individual decks. Parents include their subdecks; overlapping branches count once. Save the study, then use its study action. Continue lecture opens normal Anki review.</p>
<p>For whole-folder study, choose its <b>Shuffle between lectures</b> option when you want eligible cards mixed across lectures. This changes native ordering and is undoable. Anki’s limits, learning timing and sibling rules still apply; ratings in normal review affect scheduling.</p>
<h2>4. Turn a slideset into cards</h2>
<p>Open <b>Card Studio → Import a source</b>. Import a PDF, presentation, image, document or text into a source project. Use the page rail to keep slides in order. Work beside the source, save drafts, check the proposed cards and destination, then approve adding them to Anki. Keep separate backups of source projects and drafts; Anki Sync does not back up all local project data.</p>
<h2>5. Make image-occlusion and specialized cards</h2>
<p>For an imported diagram in Card Studio, choose <b>Mask figure</b>, draw or adjust masks over the original image, then review the resulting draft before publishing. Original source images remain separate from masks. Cloze and image cards are available too.</p>
<p><b>Add cards</b> opens Anki’s native editor. Use it for installed note types, the stock Image Occlusion workflow and specialized tools from your other editor add-ons. <b>Browse</b> finds and edits existing notes. Atelier does not replace every third-party editor workflow.</p>
<h2>6. Put several folders in one exam</h2>
<p>Open <b>Exam Studio</b>, create a plan and select every parent folder or deck belonging to it—even two separate courses. Choose the exam date and the available preparation options. The original decks stay separate. Use <b>Practice &amp; mocks</b> for that exam’s practice sessions; review its grading/scheduling description before starting. Save &amp; close to resume practice later.</p>
<h2>7. Study with Pip or time a session</h2>
<p>Set the study focus first, then use <b>Study with Pip</b> on Study desk to carry that selection into Pip Study. It is optional.</p>
<p>The <b>clock button</b> on the home toolbar or <b>Tools → Atelier → Study clock</b> opens a small native window. Choose Countdown and a length, or Stopwatch. Start, pause/resume and reset it yourself. It stays available while reviewing or editing; closing its window keeps timing, and quitting Anki pauses it. Reopening Anki restores the saved elapsed time paused. Reset before changing clock mode or countdown length. The clock does not grade cards, change schedules or add time to Anki’s study statistics.</p>
<h2>8. Make the workspace yours</h2>
<p>Use <b>Worlds and appearance</b> to choose a world, density, motion or appearance owner. <b>Widgets</b> manages home widgets. Optional Onigiri rewards reveal their real restaurant and controls through Show rewards when that separate add-on is enabled. Other add-ons retain their own menus and windows.</p>
<h2>9. Share and protect your work</h2>
<p>Export a chosen deck from its menu or Anki tools to create an <b>.apkg</b> file. Source projects, masks, exam plans and local preferences need separate backups; they are not all included in a deck export or Anki Sync. Read the included USER-GUIDE for the exact folders before moving to a new computer.</p>
<h2>10. Return to familiar Anki controls</h2>
<p><b>Tools → Atelier → Use original Anki home</b> restores the original home. The same menu has reviewer and shortcut recovery controls. For a compatibility problem, save your work, disable Atelier in Tools → Add-ons and restart. Disable instead of deleting it to keep local data. Never delete or reset your collection to troubleshoot a theme.</p>'''

def open_guide(owner,parent):
    old=getattr(owner,'_help_window',None)
    if old:old.show();old.raise_();old.activateWindow();return
    window=QDialog(parent);window.setWindowTitle('Atelier · Getting started')
    available=window.screen().availableGeometry();window.resize(min(700,available.width()-24),min(650,available.height()-32))
    box=QVBoxLayout(window);text=QTextBrowser();text.setHtml(GUIDE);text.setOpenExternalLinks(False);box.addWidget(text)
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Close);tour=QPushButton('Show me around');buttons.addButton(tour,QDialogButtonBox.ButtonRole.ActionRole);box.addWidget(buttons)
    buttons.rejected.connect(window.close)
    def replay():window.close();owner.open_tour()
    tour.clicked.connect(replay)
    cfg=owner.get_config()
    if cfg.get('visual_owner')=='atelier':
        p=PALETTES[cfg['theme']];window.setStyleSheet('QDialog,QTextBrowser{background:'+p['bg']+';color:'+p['text']+';font-family:Segoe UI;} QTextBrowser{border:0;padding:16px;font-size:14px;} QPushButton{background:'+p['raised']+';color:'+p['text']+';border:1px solid '+p['line']+';padding:9px 14px;border-radius:8px;font-family:Segoe UI;font-size:14px;}')
    owner._help_window=window;window.finished.connect(lambda *_:setattr(owner,'_help_window',None));window.show()
