# Manual Testing Guide

A step-by-step pass for manually testing the app. Each item lists what to do and
what you should see. Together they cover every acceptance criterion in
[SPEC.md](SPEC.md). The automated `db.py` tests (`pytest`) cover the data layer;
this guide covers the UI and end-to-end behavior.

## Run the app

From the project folder, inside the venv:

```powershell
venv\Scripts\python.exe main.py
```

Your data is created at `C:\Users\<you>\.job-app-tracker\jobtracker.db` (outside
the repo). To start from a clean slate, close the app and delete that file.

---

## 1. First launch
- [ ] Window opens (~1000x700) with two tabs: **Applications** and **Search**.
- [ ] Applications shows the **empty state**: "No applications yet" plus a
      prominent "+ Add your first application" button (not a blank grid).

## 2. Add an application
- [ ] Click **+ Add**. The detail form opens, defaulting to the **Applied** stage
      with **today's date** checked.
- [ ] Click **Save** with Company/Role blank → it warns they are required.
- [ ] Fill Company + Role → **Save** → the status bar shows "Saved".
- [ ] Click **← Applications** (or press **Esc**) → back to the list; your row is
      there.

## 3. Add Q&A during entry
- [ ] Click **+ Add**, fill Company + Role, then click **+ Add question** right
      away (before a separate Save). It should save the application and open the
      Q&A dialog in one step (no disabled button).
- [ ] Add a question + answer → **Save** → it appears in the Q&A list, which takes
      up most of the screen.
- [ ] Select it → **Edit** (or double-click) → change the answer → **Save** →
      updated.

## 4. Job posting link
- [ ] Set Job URL to `linkedin.com/jobs/123` (no `https://`), **Save**.
- [ ] **Open posting** opens your browser with `https://` prepended.
- [ ] Clear the URL → the **Open posting** button disables.

## 5. Stage changes and history
- [ ] Add a second application. Change its **Stage** dropdown to "Interview",
      **Save** → status "Saved", and the list reflects the new stage.
- [ ] (Each stage change is recorded as history for the future drop-off chart.)

## 6. List sort and filter
- [ ] Click the **Stage** column header → rows sort by pipeline order
      (Saved -> Applied -> Interview -> ...), not alphabetically.
- [ ] Click the **Applied** column header → rows sort by date.
- [ ] Use the **Stage** filter dropdown → only matching applications show.
- [ ] After sorting/filtering, double-click a row → it opens the **correct**
      application (not a wrong one).

## 7. Global Q&A search (the reuse engine)
- [ ] Open the **Search** tab → the box is focused and shows the hint
      ("Search every answer you've written...").
- [ ] Type a word from an answer (e.g. "work") → matching Q&A appear, each
      showing its source application (Company - Role).
- [ ] Select a result → **Copy answer** → button flips to "Copied ✓"; paste
      elsewhere to confirm the clipboard.
- [ ] Type gibberish → "No answers match '...'."
- [ ] Edit an answer in the detail view, return to Search, search for it → the
      result reflects the edit (no stale results).

## 8. Delete
- [ ] Open an application → **Delete** → a confirmation dialog appears.
- [ ] Confirm → the application is gone, and its Q&A and stage history go with it.

## 9. Export / backup
- [ ] **File -> Export database...** → choose a location → status "Exported to ...".
- [ ] Confirm the `.db` file exists at that path.

## 10. Persistence
- [ ] Close the app completely and reopen → all your data is still there.
- [ ] The stage dropdown lists the 11 default stages (Saved through
      Ghosted/No-response).

---

If anything does not match, note the step number and what you saw. Bugs get fixed
on a branch and land via a pull request to `main` (see `CLAUDE.local.md`).
