# CLAUDE.md

Guidance for Claude Code working in this repository.

## Local files

Before proceeding, check for and read any local, untracked CLAUDE files in this
project (for example `CLAUDE.local.md`). They hold developer- or machine-specific
instructions that are not committed and take precedence over this file.

## Project

Job Application Tracker: a personal desktop app to record job-application Q&A
(the main point is reusing and improving answers) and track the status of each
application. Single user, local-only, built to keep records for years.

**`docs/SPEC.md` is the source of truth** for scope, data model, screens, and
acceptance criteria. Read it before making changes.

Status: greenfield / scaffolding. Code is built to match docs/SPEC.md.

## Stack

- **Python 3.11+**
- **PySide6** (Qt for Python) for the UI
- **sqlite3** (stdlib) for storage; the data layer stays decoupled from Qt
- stdlib **webbrowser** (open job links), **shutil** + Qt `QFileDialog` (DB export)
- Dev-only optional: **PyInstaller** for packaging

## Layout (per docs/SPEC.md)

```
main.py                  entry point: QApplication, open DB, show main window
db.py                    sqlite connection, schema, stage seed, all queries
ui/
  main_window.py         QMainWindow + QStackedWidget navigation
  application_list.py     home list view
  application_detail.py   detail/editor + Q&A (inline edit) + stage history
  search_view.py         global Q&A search
docs/
  SPEC.md                source of truth (spec/plan)
  TESTING.md             manual testing guide
```

Data file (NOT in the repo): `~/.job-app-tracker/jobtracker.db`.

## Setup & run

```
python -m venv venv
venv\Scripts\activate            # Windows; PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt  # PySide6
python main.py
```

## Conventions

- All SQL lives in `db.py`. UI modules call `db` functions; no SQL inside widgets.
- Queries return `sqlite3.Row` (dict-like access). No ORM.
- Timestamps (`created_at`, `updated_at`, `changed_at`): ISO 8601 strings.
  Dates (`date_applied`): `YYYY-MM-DD`.
- Stages are data (seeded rows in the `stage` table), never hardcoded enums.
- Write a `stage_event` row on every stage change. This history powers the
  future drop-off chart and cannot be backfilled, so never skip it.
- Keep the DB layer importable and testable without starting the GUI.
- Follow PEP 8, four-space indentation.

## Database

Tables: `stage`, `application`, `stage_event`, `qa_entry` (full schema in
docs/SPEC.md). Back up by copying the single `jobtracker.db` file before any schema
change; that copy is the rollback.

## Out of scope (v1)

Charts, reminders, document storage, contact tracking, cloud sync, answer-bank
versioning, and an in-app stage editor. See docs/SPEC.md "Out of Scope" before adding
any of these.
