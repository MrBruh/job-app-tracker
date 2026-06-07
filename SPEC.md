# Job Application Tracker — Spec / Plan

A personal desktop app to track job applications: your **answers to application
questions** (the main point: reuse and improve them) plus the **status** of each
application. Single user, local-only, built to keep records for years.

Status: PLAN LOCKED — eng-reviewed, outside-voice challenged, design-reviewed
2026-06-07. Ready to build.

---

## Context

Right now you track applications and your answers entirely in your head, so your
answers drift between applications and you can't improve on them. This app is a
persistent, searchable record of your application Q&A, plus lightweight status
tracking of where each application stands. Built for one person, runs locally,
designed to survive an intense active search now and to hold records over years.

Honest framing (per the outside-voice challenge): a spreadsheet would cover most
of the reuse goal faster. This app is chosen for the durable local record you own
and as a worthwhile PySide6 build, not as the absolute fastest path. That tradeoff
is accepted.

## Goals (priority order)

1. **Reuse + improve answers.** Capture every application question and your
   answer, and search across all of them to find and adapt a past answer.
2. **See an application at a glance.** Company, role, current status, and a
   clickable link to the job posting.
3. **Track the pipeline.** Move each application through editable stages, and
   record each stage change so a drop-off chart is possible later.

## Tech (Python + PySide6)

- **Python 3.11+.** 3.12.10 is installed and confirmed via the `py` launcher
  (`py -3.12`). The bare `python` on PATH is an old 3.8 that PySide6 will not
  install on, so always build/run through `py -3.12`.
- **PySide6 (Qt for Python)** for the UI. `pip install PySide6`. The official Qt
  binding (LGPL, free to use).
- **sqlite3** for storage. Built into Python. One database file. The data layer
  stays plain `sqlite3`, decoupled from Qt, so the DB code can be unit-tested on
  its own.
- **webbrowser** (stdlib) to open job-posting links in the real browser.
- **shutil** + Qt's `QFileDialog` for the backup/export feature.
- Dev-only: **pytest** (tests), optional **PyInstaller** to build an `.exe`.

The database file lives outside the code folder so it survives edits and is easy
to back up: `~/.job-app-tracker/jobtracker.db` (Windows:
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
  date_applied     TEXT,                        -- ISO 8601 date (YYYY-MM-DD), NULL until applied
  notes            TEXT,
  created_at       TEXT    NOT NULL,            -- UTC ISO 8601, set by db.py
  updated_at       TEXT    NOT NULL             -- UTC ISO 8601, set by db.py
);

-- Every stage change, so a drop-off / Sankey chart is possible later
CREATE TABLE stage_event (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
  stage_id       INTEGER NOT NULL REFERENCES stage(id),
  changed_at     TEXT    NOT NULL,             -- UTC ISO 8601
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

## DB layer rules (db.py) — correctness requirements

- **Connection model: one injected connection.** `connect(path)` opens the DB,
  runs `PRAGMA foreign_keys = ON`, sets `row_factory = sqlite3.Row`, and returns
  the connection. Every query function takes that `conn` as its first argument.
  `main.py` opens one connection for the app's lifetime (single-threaded GUI).
  Tests create their own connection against `:memory:` or a `tmp_path` file and
  pass it in. (FK pragma is connection-scoped and OFF by default; without it the
  `ON DELETE CASCADE` rules do nothing and orphan rows.)
- **First-run directory:** before connecting, expand and create the data dir —
  `Path.home() / ".job-app-tracker"`, `mkdir(parents=True, exist_ok=True)`.
  sqlite3 does NOT create missing parent dirs and does NOT expand `~`; skipping
  this is a guaranteed first-run crash.
- **Idempotent seed:** insert the 11 default stages only when the `stage` table is
  empty, so they are not duplicated on later launches.
- **Atomic stage change:** a single `set_stage(conn, application_id, stage_id)`
  updates `application.current_stage_id` AND inserts a `stage_event` in one
  transaction. Stage changes go through this function ONLY — the generic
  application-update path must never write `current_stage_id` directly, or it
  drops the history that the drop-off chart depends on.
- **Schema versioning:** track the schema with `PRAGMA user_version`. On launch,
  db.py applies pending migrations in order (v1 = create the schema). Future field
  adds (salary, deadline, ...) become one ordered migration step.
- **Timestamps:** `created_at` / `updated_at` / `changed_at` are Python-side UTC
  ISO 8601 strings set in db.py (one source of truth, consistent over years).
- Connections return `sqlite3.Row` (dict-like). No ORM.

## Screens

Persistent navigation: a top `QTabWidget` with two areas, **Applications** and
**Search**. The Applications tab swaps between the list and a single application's
detail; the detail view has a "← Applications" back affordance.

1. **Applications list** (home): every application as a row showing company,
   role, status, date applied. Filter by stage, sort by column. Prominent
   "+ Add" action. Open a row (double-click or Enter) to its detail.
2. **Application detail / editor**: a compact metadata header (company, role, job
   URL, location, source, stage, date applied, notes) above a **dominant Q&A
   section** — Q&A is the reuse engine and gets the space. "Open posting" opens
   the URL in the browser. Q&A entries add / edit / delete.
3. **Global Q&A search**: one search box matching across every question and
   answer. Each result shows the question, answer, and source application, with a
   **Copy answer** button. This is the reuse engine.

## UI building blocks (PySide6)

- App shell: `QMainWindow` with a top `QTabWidget` for **Applications** and
  **Search** (persistent nav — always answers "where am I"). The Applications tab
  holds a `QStackedWidget` (list <-> detail); the detail page has a
  "← Applications" back button. `QMainWindow.statusBar()` shows transient
  confirmations.
- Applications list: `QTableWidget` (columns: Company, Role, Stage, Date
  applied). A `QComboBox` filters by stage; double-click or Enter opens detail.
  - **Store the application id on each row** via `item.setData(Qt.UserRole, id)`;
    never map visible row index to id (sort/filter reorder and hide rows).
  - The Stage column sorts by pipeline order (`stage.sort_order`), not
    alphabetically — sort on a hidden sort-key column or a custom sort role.
- Detail / editor: `QLineEdit` (company, role, job URL, location, source),
  `QComboBox` (stage), `QDateEdit` (date applied), `QPlainTextEdit` (notes).
  - **Hierarchy:** the metadata is a compact header; the Q&A section takes the
    majority of the vertical space (reuse is goal #1).
  - **"Have applied" checkbox gates the `QDateEdit`.** Unchecked → `date_applied`
    is stored NULL (QDateEdit can't represent "no date"; "Saved" apps have none).
  - Changing the stage routes through `set_stage` (not the blanket field save), so
    a `stage_event` is always written.
  - "Open posting" `QPushButton` calls `webbrowser.open`; **disabled when job_url
    is empty**, and prepends `https://` when the URL has no scheme.
  - Q&A entries in a `QTableWidget`; add/edit opens a small `QDialog` (question
    `QLineEdit` + answer `QPlainTextEdit`).
- Delete: a `QMessageBox` confirm before `delete_application` (it cascades and
  removes the Q&A, which is goal-#1 data).
- Global search: a `QLineEdit` box, results in a `QTableWidget` (Question, Answer,
  Company / Role). "Copy answer" uses `QApplication.clipboard().setText(...)`.
  **Re-query when the view is shown** so edits made elsewhere aren't stale.
- Stage badges: color the stage cell (or a small `QLabel`) by `stage.kind`.

## States, feedback & keyboard

- **Empty / first-run (list):** with no applications, replace the table with
  "No applications yet — track your first one and start reusing answers." and a
  prominent "+ Add your first application" button. Never show a blank grid.
- **Q&A empty (detail):** "No questions saved yet." + "+ Add the first question".
- **Search initial (no query):** hint, e.g. "Search every answer you've written.
  Try 'why this company'."
- **Search no-results:** "No answers match '<term>'."
- **Action feedback** via `statusBar()`: "Saved", "Answer copied",
  "Stage → Interview". The Copy button also flips to "Copied ✓" for ~1.5s. Silent
  success reads as broken; every action confirms.
- **Keyboard:** Enter (or double-click) opens the selected list row; switching to
  the Search tab focuses the search box; Esc returns from detail to the list.
- **Window:** default ~1000x700, minimum 800x500, resizable; the Q&A list and the
  search results expand to fill, the metadata form stays compact.
- **Visual language:** lean on Qt's native theme (follows OS light/dark). Do not
  invent a custom visual system for v1.

## Acceptance Criteria (MVP)

1. I can create an application with company, role, job URL, stage, and date
   applied; it appears in the list immediately.
2. Opening an application shows its details and an "Open posting" button that
   opens the job URL in my default browser (disabled when there is no URL).
3. On an application I can add, edit, and delete Q&A entries, and they persist
   after the app restarts.
4. The global search box returns matching Q&A across all applications, shows the
   source application, and a Copy button puts the answer on my clipboard.
5. Changing a stage updates the list and writes a `stage_event` row (via
   `set_stage`); editing other fields never silently changes the stage.
6. All data persists in `jobtracker.db`; closing and reopening loses nothing.
7. The 11 default stages exist on first launch and are not duplicated later.
8. A "Saved" application with no applied date round-trips a NULL date correctly.
9. Deleting an application asks for confirmation; confirming removes its Q&A and
   stage history too.
10. After sorting or filtering the list, opening a row opens the correct
    application (id-based, not row-based).
11. `db.py` unit tests pass (`pytest`), covering the paths in the Testing section.
12. On first launch with no data, the list shows a friendly empty state with a
    prominent "Add your first application" action (not a blank grid). Search and
    the Q&A section show their own empty / no-results states.
13. Copying an answer, saving, and changing a stage each show a visible
    confirmation (status bar and/or button state); no action succeeds silently.
14. I can move list → detail → back and reach Search via persistent tabs without
    losing my place.

## Testing

pytest unit tests for `db.py`, run against a `:memory:` connection (works because
of the single-injected-connection model) or a `tmp_path` file, so they never touch
real data. Cover every db path:

- schema init + `user_version` migration applies cleanly on a fresh DB
- `seed_stages` is idempotent (running twice yields 11 stages, not 22)
- application CRUD; creating one writes an initial `stage_event`
- `delete_application` cascades (qa_entry + stage_event removed) — proves
  `PRAGMA foreign_keys = ON` is in effect
- `set_stage` updates `current_stage_id` AND appends a `stage_event` atomically
- a generic application update does NOT change `current_stage_id` or add a
  stage_event (stage routing is honored)
- `date_applied` NULL round-trips (save NULL, read back NULL)
- Q&A add / edit / delete
- `search_qa`: matching term, empty term, no-results, and correct source app

UI wiring (PySide6) is verified manually for v1; pytest-qt smoke tests are a later
add.

## Included but light

- **Backup / export**: "Export database…" copies `jobtracker.db` to a location you
  choose (data safety for the multi-year goal).
- **stage_event recording** on every stage change (the chart that uses it is out
  of scope for v1).

## Out of Scope (v1)

- The drop-off / Sankey chart itself (data is recorded for it; chart is later).
- Reminders / follow-up notifications.
- Resume or document storage / attachments.
- Recruiter / contact tracking.
- Cloud sync, multi-device, accounts.
- A canonical "answer bank" with versioning (per-app + search upgrades to this).
- An in-app stage editor UI (start on the 11 seeded stages; editing is v1.1).
- pytest-qt UI smoke tests (db.py unit tests only for v1).
- Extra fields (salary, deadline, referral) — deferred; a one-line migration each.
- A custom visual theme — v1 uses Qt's native look.

## Project Structure

```
job-app-tracker/
  main.py                       # create data dir, connect (one conn), QApplication, show window
  db.py                         # connect(path), migrate (user_version), seed, all queries
  ui/
    __init__.py
    main_window.py              # QMainWindow + QTabWidget (Applications | Search) + statusBar
    application_list.py         # list view + empty state
    application_detail.py       # detail/editor (compact form + dominant Q&A) + Q&A dialog + back
    search_view.py              # global Q&A search + initial/no-results states
  tests/
    test_db.py                  # pytest unit tests for the db layer
  README.md                     # how to run
  requirements.txt              # PySide6 (+ optional pyinstaller for packaging)
  requirements-dev.txt          # pytest
  SPEC.md                       # this file
```

Queries return `sqlite3.Row` (dict-like). No separate model classes for v1.

## How it runs

- Setup (use the 3.12 interpreter; the bare `python` is an old 3.8):
  `py -3.12 -m venv venv`, then `venv\Scripts\activate` (Windows), then
  `pip install -r requirements.txt`.
- Develop / run: `python main.py` (inside the venv).
- Run tests: `pip install -r requirements-dev.txt` then `pytest`.
- Optional packaged `.exe`: `pyinstaller --windowed main.py` (may need
  `--collect-all PySide6`). Note: `--windowed` hides the console, so tracebacks
  vanish — keep a plain `pyinstaller main.py` console build around for debugging.

## Effort (rough build time)

DB layer (connect + migrations + seed + set_stage) ~1.25h · db.py pytest suite
~1h · QMainWindow + tabs + nav ~1h · List view (id-mapping, stage-order sort,
filter, empty state) ~1.75h · Detail/editor (Q&A-dominant layout, date checkbox,
stage routing, Q&A dialog, empty state) ~2.25h · Global search (states + clipboard
+ refresh) ~1.25h · Export + delete-confirm + statusBar feedback + polish ~1.25h.
**Total ~10-12h of build.**

## Rollback

Greenfield, nothing to roll back. Schema changes go through ordered `user_version`
migrations; copying the single `jobtracker.db` file before a migration is the
belt-and-suspenders restore point.

## Decisions locked

- Global Q&A search: **in v1** (reuse is goal #1).
- Extra per-application fields: **none for v1** (current set; add later via migration).
- Connection model: **single injected connection** (FK pragma once; testable).
- Schema migrations: **`user_version` ladder** from v1.
- Tests: **db.py pytest suite** (UI manual for v1).
- Interpreter: **`py -3.12`**.
- Navigation: **`QTabWidget` (Applications | Search)** + back affordance in detail.
- Detail hierarchy: **Q&A dominates** the compact metadata header.
- Feedback: **statusBar + "Copied ✓"**; every action confirms.

## Wireframes (appendix)

Applications list (with data) and its empty / first-run state:

```
┌─ Job Application Tracker ──────────────────────────────────────┐
│ [ Applications ] [ Search ]                          [ + Add ]  │
├────────────────────────────────────────────────────────────────┤
│ Stage: [ All ▾ ]                                Sort: [ Date ▾ ]│
│ Company        Role             Stage         Applied           │
│ ────────────────────────────────────────────────────────────── │
│ Acme Corp      Backend Eng      ● Interview    2026-05-30       │
│ Globex         Data Scientist   ● Applied      2026-06-01       │
│ Initech        ML Engineer      ○ Rejected     2026-05-20       │
├────────────────────────────────────────────────────────────────┤
│ 12 applications                                       (status)  │
└────────────────────────────────────────────────────────────────┘

Empty / first run:
│                     No applications yet                         │
│           Track your first one and start reusing answers.       │
│                [  + Add your first application  ]               │
```

Application detail (Q&A dominant) and Q&A empty state:

```
┌────────────────────────────────────────────────────────────────┐
│ ← Applications               [ Open posting ]  [ Save ] [Delete]│
├────────────────────────────────────────────────────────────────┤
│ Company [Acme Corp      ]  Role [Backend Eng         ]          │
│ Stage   [Interview ▾]      ☑ Applied [2026-05-30]              │
│ URL     [https://…      ]  Source [LinkedIn ]   Notes […]      │
├────────────────────────────────────────────────────────────────┤
│ Questions & Answers                            [ + Add question]│
│ ────────────────────────────────────────────────────────────── │
│ Why do you want to work here?                    [Edit] [Copy]  │
│   "I'm drawn to Acme's work on…"                                │
│ Describe a hard technical problem…               [Edit] [Copy]  │
└────────────────────────────────────────────────────────────────┘

Q&A empty:  No questions saved yet.  [ + Add the first question ]
```

Global Q&A search (results, initial hint, no-results):

```
┌────────────────────────────────────────────────────────────────┐
│ [ Applications ] [ Search ]                                     │
│ 🔍 [ why this company                                        ]  │
│ ────────────────────────────────────────────────────────────── │
│ Why do you want to work here?                          [Copy]   │
│   "I'm drawn to Acme's work on…"                                │
│   Acme Corp · Backend Eng                                       │
│ What attracts you to this role?                        [Copy]   │
│   "The mix of research and…"                                    │
│   Globex · Data Scientist                                       │
└────────────────────────────────────────────────────────────────┘

Initial (no query):  Search every answer you've written. Try "why this company".
No results:          No answers match "xyzzy".
```

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | not run |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | clean | 6 findings + 1 env blocker; all resolved |
| Outside Voice | Claude subagent | Independent challenge | 1 | issues_found | 3 P1 + 6 P2/P3; all folded in or decided |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | clean | 5/10 → 8.5/10; 9 UX fixes folded in |

- **Eng review resolved:** FK pragma + idempotent seed + atomic `set_stage` (D1);
  db.py pytest suite (D2); `user_version` migration ladder (D3, kept at D7);
  Python 3.12 confirmed (D4).
- **Outside voice resolved:** single injected connection model fixing the
  in-memory test conflict (D5); QDateEdit null-date checkbox, stage-change
  routing, Qt.UserRole id mapping, first-run mkdir, delete-confirm, URL guard,
  UTC timestamps, search refresh, effort revised to 10-12h (D6); migration ladder
  kept after cross-model tension (D7).
- **Design review resolved:** QTabWidget nav + back affordance, Q&A-dominant
  detail hierarchy, empty/first-run + search states, statusBar/Copy feedback,
  keyboard affordances, window sizing; wireframes added as an appendix (D8/D9).
- **UNRESOLVED:** none.
- **VERDICT:** ENG + DESIGN CLEARED, outside-voice challenged — ready to implement.
