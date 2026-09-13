"""rc5 question navigation retained inside the incoming quiet Tools popup.

One set of original controls; no second reviewer, altered answer lock, clock,
scheduling or question state. Navigation always uses the runner's guarded path.
"""
from .session_model import question_page, next_question, FILTERS

class QuestionNavigation:
    def __init__(self, runner, parent, layout):
        from aqt.qt import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QPushButton
        self.runner = runner
        self.view = 'all'
        self.page = 0
        self.rows = []
        self.widget = QWidget(parent)
        box = QVBoxLayout(self.widget); box.setContentsMargins(0,8,0,8); box.setSpacing(8)
        quick = QHBoxLayout()
        self.next_unanswered = QPushButton('Next unanswered', self.widget)
        self.next_flagged = QPushButton('Next flagged', self.widget)
        self.next_unanswered.clicked.connect(lambda _=False:self.next('unanswered'))
        self.next_flagged.clicked.connect(lambda _=False:self.next('flagged'))
        quick.addWidget(self.next_unanswered);quick.addWidget(self.next_flagged);box.addLayout(quick)
        label = QLabel('Question map · answers remain hidden',self.widget);label.setWordWrap(True);box.addWidget(label)
        self.filter = QComboBox(self.widget)
        for name in ('All questions','Unanswered','Flagged'):self.filter.addItem(name)
        self.filter.setAccessibleName('Filter the question map')
        self.filter.activated.connect(self.change_filter);box.addWidget(self.filter)
        grid = QGridLayout();grid.setSpacing(5)
        self.buttons=[]
        for i in range(24):
            b=QPushButton('',self.widget);b.setMinimumHeight(30)
            b.clicked.connect(lambda _=False,i=i:self.choose(i))
            grid.addWidget(b,i//6,i%6);self.buttons.append(b)
        box.addLayout(grid)
        pagebar=QHBoxLayout();self.previous=QPushButton('Previous page',self.widget);self.more=QPushButton('Next page',self.widget)
        self.previous.clicked.connect(lambda _=False:self.turn(-1));self.more.clicked.connect(lambda _=False:self.turn(1))
        pagebar.addWidget(self.previous);pagebar.addWidget(self.more);box.addLayout(pagebar)
        self.status=QLabel(self.widget);self.status.setWordWrap(True);box.addWidget(self.status)
        layout.addWidget(self.widget)
        self.refresh()

    def allowed(self):
        r=self.runner
        return (r.session.phase=='answering' and not hasattr(r,'saved_answers')
                and not getattr(r,'finished_once',False) and not getattr(r,'_learning_busy',False))

    def refresh(self):
        allowed=self.allowed();self.widget.setVisible(allowed)
        if not allowed:return
        result=question_page(self.runner.session,self.view,self.page)
        self.page=result['page'];self.rows=result['rows']
        for i,b in enumerate(self.buttons):
            b.setVisible(i<len(self.rows))
            if i<len(self.rows):
                row=self.rows[i];b.setText(str(row['number'])+(' •' if row['flagged'] else ' ✓' if row['answered'] else ''))
                b.setAccessibleName(row['label']);b.setToolTip(row['label']);b.setProperty('current',row['current'])
        self.previous.setEnabled(self.page>0);self.more.setEnabled(self.page+1<result['pages']);self.status.setText(result['label'])
        self.next_unanswered.setEnabled(next_question(self.runner.session,'unanswered') is not None)
        self.next_flagged.setEnabled(next_question(self.runner.session,'flagged') is not None)

    def change_filter(self,index):
        if not self.allowed() or type(index) is not int or not 0<=index<len(FILTERS):return
        self.view=FILTERS[index];self.page=0;self.refresh()

    def turn(self,delta):
        if not self.allowed():return
        self.page=max(0,self.page+delta);self.refresh()

    def choose(self,index):
        if self.allowed() and type(index) is int and 0<=index<len(self.rows):
            self.runner._jump_from_tools(self.rows[index]['index'])

    def next(self,view):
        if not self.allowed():return
        index=next_question(self.runner.session,view)
        if index is not None:self.runner._jump_from_tools(index)
