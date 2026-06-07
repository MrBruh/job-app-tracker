"""Main window: persistent QTabWidget (Applications | Search). The Applications
tab holds a QStackedWidget swapping list <-> detail; the status bar shows transient
confirmations; the File menu exports the database."""

import shutil

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QFileDialog, QMainWindow, QMessageBox, QStackedWidget, QTabWidget,
)

from ui.application_detail import ApplicationDetailView
from ui.application_list import ApplicationListView
from ui.search_view import SearchView


class MainWindow(QMainWindow):
    def __init__(self, conn, db_path):
        super().__init__()
        self.conn = conn
        self.db_path = db_path
        self.setWindowTitle("Job Application Tracker")
        self.resize(1000, 700)
        self.setMinimumSize(800, 500)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Applications tab: list <-> detail.
        self.app_stack = QStackedWidget()
        self.list_view = ApplicationListView(self.conn, self.status_message)
        self.detail_view = ApplicationDetailView(self.conn, self.status_message)
        self.app_stack.addWidget(self.list_view)
        self.app_stack.addWidget(self.detail_view)
        self.tabs.addTab(self.app_stack, "Applications")

        # Search tab.
        self.search_view = SearchView(self.conn, self.status_message)
        self.tabs.addTab(self.search_view, "Search")

        # Wiring.
        self.list_view.open_application.connect(self._open_detail)
        self.list_view.add_application.connect(self._add_new)
        self.detail_view.back.connect(self._show_list)
        self.detail_view.deleted.connect(self._show_list)
        self.tabs.currentChanged.connect(self._tab_changed)

        self._build_menu()
        self.statusBar().showMessage("Ready")
        self.list_view.refresh()

    def status_message(self, text, msecs=3000):
        self.statusBar().showMessage(text, msecs)

    def _build_menu(self):
        file_menu = self.menuBar().addMenu("&File")
        export = QAction("Export database…", self)
        export.triggered.connect(self._export)
        file_menu.addAction(export)
        file_menu.addSeparator()
        quit_act = QAction("Exit", self)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

    def _open_detail(self, app_id):
        self.detail_view.load(app_id)
        self.app_stack.setCurrentWidget(self.detail_view)

    def _add_new(self):
        self.detail_view.load(None)
        self.app_stack.setCurrentWidget(self.detail_view)

    def _show_list(self):
        self.list_view.refresh()
        self.app_stack.setCurrentWidget(self.list_view)

    def _tab_changed(self, index):
        if self.tabs.widget(index) is self.search_view:
            self.search_view.on_shown()
        elif self.tabs.widget(index) is self.app_stack:
            self.list_view.refresh()

    def _export(self):
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export database", "jobtracker-backup.db", "SQLite DB (*.db)"
        )
        if not dest:
            return
        try:
            self.conn.commit()
            shutil.copy(self.db_path, dest)
            self.status_message(f"Exported to {dest}")
        except Exception as exc:  # noqa: BLE001 - surface any copy error to the user
            QMessageBox.warning(self, "Export failed", str(exc))
