"""Global Q&A search: the reuse engine. Matches across every answer, shows the
source application, and copies an answer to the clipboard. Has an initial hint and
a no-results state."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import db

_HINT = ('Search every answer you\'ve written.\n'
         'Try "why this company" or "biggest weakness".')


class SearchView(QWidget):
    def __init__(self, conn, status):
        super().__init__()
        self.conn = conn
        self.status = status
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        self.box = QLineEdit()
        self.box.setClearButtonEnabled(True)
        self.box.setPlaceholderText("Search every answer you've written…")
        self.box.textChanged.connect(self._search)
        layout.addWidget(self.box)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Question", "Answer", "Application"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # Wrap long questions/answers; let each row grow to fit the wrapped text.
        self.table.setWordWrap(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.cellActivated.connect(lambda _r, _c: self._copy())
        self.stack.addWidget(self.table)

        self.msg = QLabel()
        self.msg.setAlignment(Qt.AlignCenter)
        self.msg.setWordWrap(True)
        self.stack.addWidget(self.msg)

        bar = QHBoxLayout()
        bar.addStretch(1)
        self.copy_btn = QPushButton("Copy answer")
        self.copy_btn.clicked.connect(self._copy)
        bar.addWidget(self.copy_btn)
        layout.addLayout(bar)

        self._show_initial()

    def on_shown(self):
        """Called when the Search tab becomes visible: focus + re-run the query
        so edits made elsewhere are reflected (no stale cache)."""
        self.box.setFocus()
        self._search(self.box.text())

    def _show_initial(self):
        self.msg.setText(_HINT)
        self.stack.setCurrentIndex(1)
        self.copy_btn.setEnabled(False)

    def _search(self, text):
        term = text.strip()
        if not term:
            self._show_initial()
            return
        rows = db.search_qa(self.conn, term)
        if not rows:
            self.msg.setText(f'No answers match "{term}".')
            self.stack.setCurrentIndex(1)
            self.copy_btn.setEnabled(False)
            return
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            q = QTableWidgetItem(r["question"])
            q.setData(Qt.UserRole, r["answer"] or "")     # stash full answer for copy
            self.table.setItem(i, 0, q)
            self.table.setItem(i, 1, QTableWidgetItem(r["answer"] or ""))
            self.table.setItem(i, 2, QTableWidgetItem(f'{r["company"]} · {r["role"]}'))
        self.stack.setCurrentIndex(0)
        self.copy_btn.setEnabled(True)
        self.status(f"{len(rows)} match(es)")

    def _copy(self):
        row = self.table.currentRow()
        if row < 0:
            self.status("Select a result to copy its answer")
            return
        item = self.table.item(row, 0)
        answer = item.data(Qt.UserRole) if item else ""
        if not answer:
            self.status("No answer to copy")
            return
        QApplication.clipboard().setText(answer)
        self.status("Answer copied")
        self.copy_btn.setText("Copied ✓")
        QTimer.singleShot(1500, lambda: self.copy_btn.setText("Copy answer"))
