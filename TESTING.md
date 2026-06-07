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
- [y] Window opens (~1000x700) with two tabs: **Applications** and **Search**.
- [y] Applications shows the **empty state**: "No applications yet" plus a
      prominent "+ Add your first application" button (not a blank grid).

## 2. Add an application
- [n] Click **+ Add**. The detail form opens, defaulting to the **Applied** stage
      with **today's date** checked. [defaults to saved, saved should not exist]
- [n] Click **Save** with Company/Role blank → it warns they are required. [There should not be a pop-up, instead have some text somewhere in the map app indicating this]
- [y] Fill Company + Role → **Save** → the status bar shows "Saved".
- [y] Click **← Applications** (or press **Esc**) → back to the list; your row is
      there.

## 3. Add Q&A during entry
- [y] Click **+ Add**, fill Company + Role, then click **+ Add question** right
      away (before a separate Save). It should save the application and open the
      Q&A dialog in one step (no disabled button).
- [n] Add a question + answer → **Save** → it appears in the Q&A list, which takes
      up most of the screen. [Takes up too much of the screen, Question can be a little shorter and Application should be a bit wider to make it more clear]
- [n] Select it → **Edit** (or double-click) → change the answer → **Save** →
      updated. [Editting should be done in place rather than in a new popup]

## 4. Job posting link
- [y] Set Job URL to `linkedin.com/jobs/123` (no `https://`), **Save**.
- [y] **Open posting** opens your browser with `https://` prepended.
- [y] Clear the URL → the **Open posting** button disables.

## 5. Stage changes and history
- [y] Add a second application. Change its **Stage** dropdown to "Interview",
      **Save** → status "Saved", and the list reflects the new stage.
- [n] (Each stage change is recorded as history for the future drop-off chart.) [It probably is, but I don't have a way to check in-app]

## 6. List sort and filter
- [y] Click the **Stage** column header → rows sort by pipeline order
      (Saved -> Applied -> Interview -> ...), not alphabetically.
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
- [n] Edit an answer in the detail view, return to Search, search for it → the
      result reflects the edit (no stale results). [There is no detail view]

## 8. Delete
- [y] Open an application → **Delete** → a confirmation dialog appears.
- [y] Confirm → the application is gone, and its Q&A and stage history go with it.

## 9. Export / backup
- [y] **File -> Export database...** → choose a location → status "Exported to ...".
- [y] Confirm the `.db` file exists at that path.

## 10. Persistence
- [y] Close the app completely and reopen → all your data is still there.
- [y] The stage dropdown lists the 11 default stages (Saved through
      Ghosted/No-response).

---

If anything does not match, note the step number and what you saw. Bugs get fixed
on a branch and land via a pull request to `main`
