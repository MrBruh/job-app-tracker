"""Applications list (home view): a sortable/filterable table, or a friendly
empty state on first run. Emits signals; navigation is wired by MainWindow."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLabel, QPushButton, QStackedWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import db

# Stage badge colors by kind.
STAGE_COLORS = {
    "active": "#2d6cdf",
    "terminal_positive": "#2e9e5b",
    "terminal_negative": "#b03a3a",
}


class _Item(QTableWidgetItem):
    """Table item that sorts by an explicit key (e.g. stage pipeline order)
    rather than its display text."""

    def __init__(self, text, sort_key=None):
        super().__init__(text)
        self._sort = sort_key if sort_key is not None else text

    def __lt__(self, other):
        try:
            return self._sort < other._sort
        except (AttributeError, TypeError):
            return super().__lt__(other)


class ApplicationListView(QWidget):
    open_application = Signal(int)
    add_application = Signal()

    def __init__(self, conn, status):
        super().__init__()
        self.conn = conn
        self.status = status
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Stage:"))
        self.filter = QComboBox()
        top.addWidget(self.filter)
        top.addStretch(1)
        self.add_btn = QPushButton("+ Add")
        self.add_btn.clicked.connect(self.add_application.emit)
        top.addWidget(self.add_btn)
        layout.addLayout(top)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        # 0: table
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Company", "Role", "Stage", "Applied"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setSortingEnabled(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.cellActivated.connect(self._activated)  # Enter or double-click
        self.stack.addWidget(self.table)

        # 1: empty / first-run state
        empty = QWidget()
        ev = QVBoxLayout(empty)
        ev.addStretch(1)
        title = QLabel("No applications yet")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        sub = QLabel("Track your first one and start reusing answers.")
        sub.setAlignment(Qt.AlignCenter)
        first_btn = QPushButton("+ Add your first application")
        first_btn.clicked.connect(self.add_application.emit)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(first_btn)
        btn_row.addStretch(1)
        ev.addWidget(title)
        ev.addWidget(sub)
        ev.addLayout(btn_row)
        ev.addStretch(1)
        self.stack.addWidget(empty)

        self._reload_filter()
        self.filter.currentIndexChanged.connect(self.refresh)

    def _reload_filter(self):
        self.filter.blockSignals(True)
        self.filter.clear()
        self.filter.addItem("All", None)
        for s in db.list_stages(self.conn):
            self.filter.addItem(s["name"], s["id"])
        self.filter.blockSignals(False)

    def refresh(self, *_):
        stage_id = self.filter.currentData()
        rows = db.list_applications(self.conn, stage_id=stage_id)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for r in rows:
            i = self.table.rowCount()
            self.table.insertRow(i)
            company = _Item(r["company"])
            company.setData(Qt.UserRole, r["id"])
            self.table.setItem(i, 0, company)
            self.table.setItem(i, 1, _Item(r["role"]))
            stage = _Item(r["stage_name"], r["stage_sort"])
            color = STAGE_COLORS.get(r["stage_kind"])
            if color:
                stage.setForeground(QBrush(QColor(color)))
            self.table.setItem(i, 2, stage)
            self.table.setItem(i, 3, _Item(r["date_applied"] or ""))
        self.table.setSortingEnabled(True)

        # Empty/first-run page only when there is genuinely nothing (no filter).
        if not rows and stage_id is None:
            self.stack.setCurrentIndex(1)
            self.status("No applications yet")
        else:
            self.stack.setCurrentIndex(0)
            self.status(f"{len(rows)} application(s)")

    def _activated(self, row, _col):
        item = self.table.item(row, 0)
        if item is not None:
            self.open_application.emit(item.data(Qt.UserRole))
