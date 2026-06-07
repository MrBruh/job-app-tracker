# Job Application Tracker

A small personal desktop app to track job applications and reuse your answers to
application questions. Single user, local-only. Built with Python + PySide6, data
in a local SQLite file.

See [SPEC.md](SPEC.md) for the full plan, data model, and design.

## Requirements

- Python 3.11+ (built/tested on 3.12). On Windows use the `py` launcher: `py -3.12`.

## Setup

```
py -3.12 -m venv venv
venv\Scripts\activate          # Windows (PowerShell: venv\Scripts\Activate.ps1)
pip install -r requirements.txt
```

## Run

```
python main.py
```

Your data lives in a single file outside the repo:
`~/.job-app-tracker/jobtracker.db` (Windows:
`C:\Users\<you>\.job-app-tracker\jobtracker.db`). Back it up by copying that file,
or use **Export database…** in the app.

## Tests

```
pip install -r requirements-dev.txt
pytest
```

## Packaging (optional)

```
pip install pyinstaller
pyinstaller --windowed main.py        # add --collect-all PySide6 if needed
```

`--windowed` hides the console (no tracebacks); use a plain `pyinstaller main.py`
build when debugging a packaged crash.
