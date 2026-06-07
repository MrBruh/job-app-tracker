"""Application detail / editor: a compact metadata header above a dominant Q&A
section (reuse is goal #1). Stage changes route through db.set_stage so history is
always recorded; the date field is gated by a 'Applied' checkbox so 'Saved' apps
keep a NULL date."""

import webbrowser

from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

import db


class QADialog(QDialog):
    """Add/edit a single question + answer."""

    def __init__(self, parent=None, question="", answer=""):
        super().__init__(parent)
        self.setWindowTitle("Question & Answer")
        self.resize(520, 340)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Question"))
        self.question = QLineEdit(question)
        layout.addWidget(self.question)
        layout.addWidget(QLabel("Answer"))
        self.answer = QPlainTextEdit(answer)
        layout.addWidget(self.answer, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept(self):
        if not self.question.text().strip():
            QMessageBox.warning(self, "Question required", "Enter a question.")
            return
        self.accept()

    def values(self):
        return self.question.text().strip(), self.answer.toPlainText().strip()


class ApplicationDetailView(QWidget):
    back = Signal()
    deleted = Signal()

    def __init__(self, conn, status):
        super().__init__()
        self.conn = conn
        self.status = status
        self.app_id = None          # None == creating a new application
        self._loaded_stage_id = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        self.back_btn = QPushButton("← Applications")
        self.back_btn.clicked.connect(self.back.emit)
        top.addWidget(self.back_btn)
        top.addStretch(1)
        self.open_btn = QPushButton("Open posting")
        self.open_btn.clicked.connect(self._open_posting)
        top.addWidget(self.open_btn)
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save)
        top.addWidget(self.save_btn)
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete)
        top.addWidget(self.delete_btn)
        layout.addLayout(top)

        # Compact metadata form.
        form = QFormLayout()
        self.company = QLineEdit()
        self.role = QLineEdit()
        self.stage = QComboBox()
        for s in db.list_stages(self.conn):
            self.stage.addItem(s["name"], s["id"])
        self.job_url = QLineEdit()
        self.job_url.textChanged.connect(self._update_open_btn)
        self.location = QLineEdit()
        self.source = QLineEdit()
        self.notes = QPlainTextEdit()
        self.notes.setFixedHeight(54)

        date_row = QHBoxLayout()
        self.applied_check = QCheckBox("Applied")
        self.applied_check.toggled.connect(self.date_enabled)
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("yyyy-MM-dd")
        date_row.addWidget(self.applied_check)
        date_row.addWidget(self.date)
        date_row.addStretch(1)

        form.addRow("Company", self.company)
        form.addRow("Role", self.role)
        form.addRow("Stage", self.stage)
        form.addRow("Date applied", date_row)
        form.addRow("Job URL", self.job_url)
        form.addRow("Location", self.location)
        form.addRow("Source", self.source)
        form.addRow("Notes", self.notes)
        layout.addLayout(form)

        # Q&A section (dominant — gets the stretch).
        qa_header = QHBoxLayout()
        qa_title = QLabel("Questions & Answers")
        qa_title.setStyleSheet("font-weight: bold;")
        qa_header.addWidget(qa_title)
        qa_header.addStretch(1)
        self.add_qa_btn = QPushButton("+ Add question")
        self.add_qa_btn.clicked.connect(self._add_qa)
        qa_header.addWidget(self.add_qa_btn)
        layout.addLayout(qa_header)

        self.qa_stack = QStackedWidget()
        layout.addWidget(self.qa_stack, 1)

        self.qa_table = QTableWidget(0, 2)
        self.qa_table.setHorizontalHeaderLabels(["Question", "Answer"])
        self.qa_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.qa_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.qa_table.setSelectionMode(QTableWidget.SingleSelection)
        self.qa_table.verticalHeader().setVisible(False)
        self.qa_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.qa_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.qa_table.cellActivated.connect(lambda r, _c: self._edit_qa(r))
        self.qa_stack.addWidget(self.qa_table)

        qa_empty = QWidget()
        qev = QVBoxLayout(qa_empty)
        qev.addStretch(1)
        lbl = QLabel("No questions saved yet.")
        lbl.setAlignment(Qt.AlignCenter)
        self.first_qa_btn = QPushButton("+ Add the first question")
        self.first_qa_btn.clicked.connect(self._add_qa)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.first_qa_btn)
        row.addStretch(1)
        qev.addWidget(lbl)
        qev.addLayout(row)
        qev.addStretch(1)
        self.qa_stack.addWidget(qa_empty)

        qa_actions = QHBoxLayout()
        qa_actions.addStretch(1)
        self.edit_qa_btn = QPushButton("Edit")
        self.copy_qa_btn = QPushButton("Copy answer")
        self.del_qa_btn = QPushButton("Delete")
        self.edit_qa_btn.clicked.connect(lambda: self._edit_qa())
        self.copy_qa_btn.clicked.connect(self._copy_qa)
        self.del_qa_btn.clicked.connect(self._delete_qa)
        for b in (self.edit_qa_btn, self.copy_qa_btn, self.del_qa_btn):
            qa_actions.addWidget(b)
        layout.addLayout(qa_actions)

    # ── loading ──────────────────────────────────────────────────────────

    def load(self, app_id):
        """Populate for an existing application, or reset for a new one (None)."""
        self.app_id = app_id
        if app_id is None:
            self.company.clear()
            self.role.clear()
            self.job_url.clear()
            self.location.clear()
            self.source.clear()
            self.notes.clear()
            # Default to "Applied" + today: the common case is tracking an
            # application you've already submitted, not a pre-apply "Saved" one.
            applied_idx = self.stage.findText("Applied")
            self.stage.setCurrentIndex(applied_idx if applied_idx >= 0 else 0)
            self._loaded_stage_id = self.stage.currentData()
            self.applied_check.setChecked(True)
            self.date.setDate(QDate.currentDate())
            self.delete_btn.setEnabled(False)
        else:
            a = db.get_application(self.conn, app_id)
            self.company.setText(a["company"])
            self.role.setText(a["role"])
            self.job_url.setText(a["job_url"] or "")
            self.location.setText(a["location"] or "")
            self.source.setText(a["source"] or "")
            self.notes.setPlainText(a["notes"] or "")
            idx = self.stage.findData(a["current_stage_id"])
            self.stage.setCurrentIndex(idx if idx >= 0 else 0)
            self._loaded_stage_id = a["current_stage_id"]
            if a["date_applied"]:
                self.applied_check.setChecked(True)
                self.date.setDate(QDate.fromString(a["date_applied"], "yyyy-MM-dd"))
            else:
                self.applied_check.setChecked(False)
                self.date.setDate(QDate.currentDate())
            self.delete_btn.setEnabled(True)

        self.date_enabled(self.applied_check.isChecked())
        self._update_open_btn()
        self._refresh_qa()

    def date_enabled(self, on):
        self.date.setEnabled(on)

    # ── save / delete / posting ──────────────────────────────────────────

    def _save(self):
        company = self.company.text().strip()
        role = self.role.text().strip()
        if not company or not role:
            QMessageBox.warning(self, "Required", "Company and role are required.")
            return
        stage_id = self.stage.currentData()
        date_applied = (
            self.date.date().toString("yyyy-MM-dd")
            if self.applied_check.isChecked() else None
        )
        job_url = self.job_url.text().strip() or None
        location = self.location.text().strip() or None
        source = self.source.text().strip() or None
        notes = self.notes.toPlainText().strip() or None

        if self.app_id is None:
            self.app_id = db.add_application(
                self.conn, company=company, role=role, stage_id=stage_id,
                job_url=job_url, location=location, source=source,
                date_applied=date_applied, notes=notes,
            )
            self._loaded_stage_id = stage_id
            self.delete_btn.setEnabled(True)
            self._refresh_qa()
        else:
            db.update_application(
                self.conn, self.app_id, company=company, role=role,
                job_url=job_url, location=location, source=source,
                date_applied=date_applied, notes=notes,
            )
            if stage_id != self._loaded_stage_id:
                db.set_stage(self.conn, self.app_id, stage_id)
                self._loaded_stage_id = stage_id
        self.status("Saved")

    def _delete(self):
        if self.app_id is None:
            return
        res = QMessageBox.question(
            self, "Delete application",
            "Delete this application and all its Q&A and stage history? "
            "This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            db.delete_application(self.conn, self.app_id)
            self.status("Application deleted")
            self.deleted.emit()

    def _update_open_btn(self):
        self.open_btn.setEnabled(bool(self.job_url.text().strip()))

    def _open_posting(self):
        url = self.job_url.text().strip()
        if not url:
            return
        if "://" not in url:
            url = "https://" + url
        webbrowser.open(url)
        self.status("Opened posting in browser")

    # ── Q&A ──────────────────────────────────────────────────────────────

    def _refresh_qa(self):
        if self.app_id is None:
            self.qa_stack.setCurrentIndex(1)
            return
        rows = db.list_qa(self.conn, self.app_id)
        self.qa_table.setRowCount(0)
        for r in rows:
            i = self.qa_table.rowCount()
            self.qa_table.insertRow(i)
            q = QTableWidgetItem(r["question"])
            q.setData(Qt.UserRole, r["id"])
            self.qa_table.setItem(i, 0, q)
            preview = (r["answer"] or "").replace("\n", " ")
            self.qa_table.setItem(i, 1, QTableWidgetItem(preview))
        self.qa_stack.setCurrentIndex(0 if rows else 1)

    def _selected_qa_id(self):
        row = self.qa_table.currentRow()
        if row < 0:
            return None
        item = self.qa_table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def _qa_record(self, qa_id):
        for r in db.list_qa(self.conn, self.app_id):
            if r["id"] == qa_id:
                return r
        return None

    def _add_qa(self):
        if self.app_id is None:
            # Auto-create the application from the form so Q&A can be added during
            # initial entry. _save() warns and leaves app_id None if company/role
            # are still blank.
            self._save()
            if self.app_id is None:
                return
        dlg = QADialog(self)
        if dlg.exec() == QDialog.Accepted:
            q, a = dlg.values()
            db.add_qa(self.conn, self.app_id, q, a)
            self.status("Question added")
            self._refresh_qa()

    def _edit_qa(self, row=None):
        if row is not None:
            item = self.qa_table.item(row, 0)
            qa_id = item.data(Qt.UserRole) if item else None
        else:
            qa_id = self._selected_qa_id()
        if qa_id is None:
            self.status("Select a question to edit")
            return
        rec = self._qa_record(qa_id)
        if rec is None:
            return
        dlg = QADialog(self, rec["question"], rec["answer"] or "")
        if dlg.exec() == QDialog.Accepted:
            q, a = dlg.values()
            db.update_qa(self.conn, qa_id, q, a)
            self.status("Question updated")
            self._refresh_qa()

    def _copy_qa(self):
        qa_id = self._selected_qa_id()
        if qa_id is None:
            self.status("Select a question to copy its answer")
            return
        rec = self._qa_record(qa_id)
        if rec and rec["answer"]:
            QApplication.clipboard().setText(rec["answer"])
            self.status("Answer copied")
        else:
            self.status("No answer to copy")

    def _delete_qa(self):
        qa_id = self._selected_qa_id()
        if qa_id is None:
            self.status("Select a question to delete")
            return
        res = QMessageBox.question(
            self, "Delete question", "Delete this Q&A entry?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if res == QMessageBox.Yes:
            db.delete_qa(self.conn, qa_id)
            self.status("Question deleted")
            self._refresh_qa()

    # ── keyboard ─────────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.back.emit()
        else:
            super().keyPressEvent(event)
