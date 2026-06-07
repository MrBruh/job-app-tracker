# Job Application Tracker — Spec / Plan

A personal desktop app to track job applications: your **answers to application
questions** (the main point: reuse and improve them) plus the **status** of each
application. Single user, local-only, built to keep records for years.

Status: DRAFT (pending sign-off). Last updated: 2026-06-07.

---

## Context

Right now you track applications and your answers entirely in your head, so your
answers drift between applications and you can't improve on them. This app is a
persistent, searchable record of your application Q&A, plus lightweight status
tracking of where each application stands. Built for one person, runs locally,
designed to survive an intense active search now and to hold records over years.

## Goals (priority order)

1. **Reuse + improve answers.** Capture every application question and your
   answer, and search across all of them to find and adapt a past answer.
2. **See an application at a glance.** Company, role, current status, and a
   clickable link to the job posting.
3. **Track the pipeline.** Move each application through editable stages, and
   record each stage change so a drop-off chart is possible later.

## Tech (Python + PySide6)

- **Python 3.11+**.
- **PySide6 (Qt for Python)** for the UI. `pip install PySide6`. Native, polished
  widgets and a real layout system. The official Qt binding (LGPL, free to use).
- **sqlite3** for storage. Built into Python. One database file. The data layer
  stays plain `sqlite3`, decoupled from Qt, so the DB code does not depend on the
  UI and could be reused or tested on its own.
- **webbrowser** (stdlib) to open job-posting links in the real browser.
- **shutil** + Qt's `QFileDialog` for the backup/export feature.
- Dev-only optional: **PyInstaller** to build a double-click `.exe`
  (`--windowed`; PySide6 builds are large and may need `--collect-all PySide6`).

The database file lives outside the code folder so it survives edits and is easy
to back up: `~/.job-app-tracker/jobtracker.db` (on Windows that is
`C:\Users\<you>\.job-app-tracker\jobtracker.db`).

## Data Model (SQLite)

```sql
-- Editable pipeline stages, seeded with research-backed defaults
CREATE TABLE stage (
  id          INTEGER PRIMARY KEY,
  name        TEXT    NOT NULL,
  sort_order  INTEGER NOT NULL,
  kind        TEXT    NOT NULL CHECK (kind IN ('active','terminal_positive','terminal_negative'))
);

-- One row per job application
CREATE TABLE application (
  id               INTEGER PRIMARY KEY,
  company          TEXT    NOT NULL,
  role             TEXT    NOT NULL,
  job_url          TEXT,
  location         TEXT,
  source           TEXT,                       -- LinkedIn, referral, company site, etc.
  current_stage_id INTEGER NOT NULL REFERENCES stage(id),
  date_applied     TEXT,                        -- ISO 8601 (YYYY-MM-DD)
  notes            TEXT,
  created_at       TEXT    NOT NULL,
  updated_at       TEXT    NOT NULL
);

-- Every stage change, so a drop-off / Sankey chart is possible later
CREATE TABLE stage_event (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  stage_id       INTEGER NOT NULL REFERENCES stage(id),
  changed_at     TEXT    NOT NULL,
  note           TEXT
);

-- Q&A entries, owned by an application
CREATE TABLE qa_entry (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  question       TEXT    NOT NULL,
  answer         TEXT,
  created_at     TEXT    NOT NULL,
  updated_at     TEXT    NOT NULL
);
```

**Search** is a plain query, no extra tables:

```sql
SELECT q.*, a.company, a.role
FROM qa_entry q JOIN application a ON a.id = q.application_id
WHERE q.question LIKE :term OR q.answer LIKE :term
ORDER BY q.updated_at DESC;     -- :term is '%text%'
```

**Seeded stages** (all editable later): Saved, Applied, Online Assessment,
Phone/Recruiter Screen, Interview, Final/Onsite, Offer (kind=active), Accepted
(terminal_positive), Rejected, Withdrawn, Ghosted/No-response
(terminal_negative). Recording `stage_event` from day one is cheap and is what
makes the future drop-off chart possible; without it that history is lost.

## Screens

1. **Applications list** (home): every application as a row showing company,
   role, status, date applied. Filter by stage, sort by date. "Add application"
   button. Click a row to open detail.
2. **Application detail / editor**: fields for company, role, job URL, location,
   source, stage (dropdown), date applied, notes. An "Open posting" button opens
   the job URL in the browser. Below: the Q&A entries for this application, each
   add / edit / delete.
3. **Global Q&A search**: one search box that matches across every question and
   answer you have entered. Each result shows the question, the answer, and which
   application it came from, with a **Copy answer** button. This is the reuse
   engine.

## UI building blocks (PySide6)

- App shell: `QMainWindow` with a `QStackedWidget` to switch between the list,
  detail, and search views (a toolbar or top buttons switch views).
- Applications list: `QTableWidget` (columns: Company, Role, Stage, Date
  applied). A `QComboBox` filters by stage; clicking a column header sorts;
  double-clicking a row opens detail.
- Detail / editor: `QLineEdit` (company, role, job URL, location, source),
  `QComboBox` (stage), `QDateEdit` (date applied), `QPlainTextEdit` (notes), and
  a `QPushButton` "Open posting" that calls `webbrowser.open`. Q&A entries sit
  below in a `QTableWidget`; add/edit opens a small `QDialog` with a question
  `QLineEdit` and an answer `QPlainTextEdit`.
- Global search: a `QLineEdit` search box, results in a `QTableWidget`
  (Question, Answer, Company / Role). "Copy answer" uses
  `QApplication.clipboard().setText(...)`.
- Stage badges: color the stage cell (or a small `QLabel`) by `stage.kind`
  (active / terminal_positive / terminal_negative).

## Acceptance Criteria (MVP)

1. I can create an application with company, role, job URL, stage, and date
   applied; it appears in the list immediately.
2. Opening an application shows its details and an "Open posting" button that
   opens the job URL in my default browser.
3. On an application I can add, edit, and delete Q&A entries, and they persist
   after the app restarts.
4. The global search box returns matching Q&A across all applications, shows the
   source application, and a Copy button puts the answer on my clipboard.
5. Changing an application's stage updates the list and writes a `stage_event`
   row with a timestamp.
6. All data persists in `jobtracker.db`; closing and reopening loses nothing.
7. The 11 default stages exist on first launch.

## Included but light

- **Backup / export**: a button or menu item "Export database…" that copies
  `jobtracker.db` to a location you choose (data safety for the multi-year goal).
- **stage_event recording** on every stage change (the chart that uses it is out
  of scope for v1).

## Out of Scope (v1)

- The drop-off / Sankey chart itself (data is recorded for it; chart is later).
- Reminders / follow-up notifications.
- Resume or document storage / attachments.
- Recruiter / contact tracking.
- Cloud sync, multi-device, accounts.
- A canonical "answer bank" with versioning (per-app + search has a clean
  upgrade path to this).
- An in-app stage editor UI (you start on the 11 seeded stages; editing stages
  is v1.1).

## Project Structure

```
job-app-tracker/
  main.py                       # entry point: create QApplication, open DB, show window
  db.py                         # connect, create schema, seed stages, all queries
  ui/
    __init__.py
    main_window.py              # QMainWindow + QStackedWidget navigation
    application_list.py         # list view (home)
    application_detail.py       # detail/editor + Q&A section + Q&A edit dialog
    search_view.py              # global Q&A search
  README.md                     # how to run
  requirements.txt              # PySide6 (+ optional pyinstaller for packaging)
  SPEC.md                       # this file
```

Queries return `sqlite3.Row` (dict-like access), so no separate model classes are
needed. Light dataclasses can be added later if the code grows.

## How it runs

- Setup: `python -m venv venv`, then `venv\Scripts\activate` (Windows), then
  `pip install PySide6`.
- Develop / run: `python main.py`.
- Optional packaged `.exe` later: `pyinstaller --windowed main.py`
  (PySide6 may need `--collect-all PySide6`; one-file builds are large).

## Effort (rough build time)

DB layer + schema + seed ~0.75h · QMainWindow + navigation ~0.75h · List view
(QTableWidget) + filter/sort ~1h · Detail/editor + Q&A add/edit/delete dialog
~1.25h · Global search + clipboard copy ~0.75h · Export + polish ~0.5h.
**Total ~5h of build.**

## Rollback

Greenfield, nothing to roll back. The database is a single file; copying it
before any schema change makes a future migration reversible by restoring the
copy.

## Open questions (to confirm before build)

1. MVP scope: keep global search in v1? (Your stated bar was the list + job
   link, but reuse is your #1 goal, so search is in v1 here.)
2. Any extra per-application fields? e.g. salary range, application deadline,
   referral name.
