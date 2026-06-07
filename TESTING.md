# Manual Testing Guide

A step-by-step pass for manually testing the app. Each item lists what to do and
what you should see. Together they cover every acceptance criterion in
[SPEC.md](SPEC.md). The automated `db.py` tests (`pytest`) cover the data layer;
this guide covers the UI and end-to-end behavior.

> Checkboxes reset for items that changed in the latest round of fixes (default
> stage, inline validation, inline Q&A editing, stage-history view, Saved removed).
> Re-run those; items still marked `[y]` were unaffected.

## Run the app

From the project folder, inside the venv:

```powershell
venv\Scripts\python.exe main.py
```

Your data is created at `C:\Users\<you>\.job-app-tracker\jobtracker.db` (outside
the repo). To start from a clean slate, close the app and delete that file.

---

## 1. First launch
- [y] Window opens (~1000x700) with two tabs: **Applications** and **Search**.
- [y] Applications shows the **empty state**: "No applications yet" plus a
      prominent "+ Add your first application" button (not a blank grid).

## 2. Add an application
- [ ] Click **+ Add**. The detail form opens, defaulting to the **Applied** stage
      with **today's date** checked.
- [ ] Click **Save** with Company/Role blank → an **inline red message** appears
      ("Company and role are required") — no pop-up dialog. It clears on a valid
      save.
- [y] Fill Company + Role → **Save** → the status bar shows "Saved".
- [y] Click **← Applications** (or press **Esc**) → back to the list; your row is
      there.

## 3. Add Q&A during entry
- [y] Click **+ Add**, fill Company + Role, then click **+ Add question** right
      away (before a separate Save). It should save the application and open the
      Q&A dialog in one step (no disabled button).
- [ ] Add a question + answer → it appears in the Q&A table. The metadata form
      and **Stage history** sit above it; the Q&A table no longer swallows the
      whole screen.
- [ ] **Edit in place:** double-click the **Question** or **Answer** cell (or
      select a row and click **Edit** / press F2) → type → click away or press
      Enter → the change is saved immediately (status "Question updated"), no
      pop-up. Clearing the question reverts it (status "Question can't be empty").

## 4. Job posting link
- [y] Set Job URL to `linkedin.com/jobs/123` (no `https://`), **Save**.
- [y] **Open posting** opens your browser with `https://` prepended.
- [y] Clear the URL → the **Open posting** button disables.

## 5. Stage changes and history
- [y] Add a second application. Change its **Stage** dropdown to "Interview",
      **Save** → status "Saved", and the list reflects the new stage.
- [ ] The **Stage history** list under the form shows the change with a timestamp
      (newest first), e.g. `2026-06-07 14:30 → Interview` above the initial
      `→ Applied`.

## 6. List sort and filter
- [y] Click the **Stage** column header → rows sort by pipeline order
      (Applied -> Online Assessment -> Interview -> ...), not alphabetically.
- [y] Click the **Applied** column header → rows sort by date.
- [y] Use the **Stage** filter dropdown → only matching applications show.
- [y] After sorting/filtering, double-click a row → it opens the **correct**
      application (not a wrong one).

## 7. Global Q&A search (the reuse engine)
- [y] Open the **Search** tab → the box is focused and shows the hint
      ("Search every answer you've written...").
- [y] Type a word from an answer (e.g. "work") → matching Q&A appear, each
      showing its source application (Company - Role).
- [y] Select a result → **Copy answer** → button flips to "Copied ✓"; paste
      elsewhere to confirm the clipboard.
- [y] Type gibberish → "No answers match '...'."
- [ ] Open an application, edit an answer in place (Q&A cell), then return to
      **Search** and search for it → the result reflects the edit (no stale
      results). Search has no detail view of its own — editing happens in the
      application's detail screen.

## 8. Delete
- [y] Open an application → **Delete** → a confirmation dialog appears.
- [y] Confirm → the application is gone, and its Q&A and stage history go with it.

## 9. Export / backup
- [y] **File -> Export database...** → choose a location → status "Exported to ...".
- [y] Confirm the `.db` file exists at that path.

## 10. Persistence
- [y] Close the app completely and reopen → all your data is still there.
- [ ] The stage dropdown lists the **10** default stages (Applied through
      Ghosted/No-response) — "Saved" is gone. If your DB predates this change, any
      application that was on "Saved" now shows as "Applied".

---

If anything does not match, note the step number and what you saw. Bugs get fixed
on a branch and land via a pull request to `main`
