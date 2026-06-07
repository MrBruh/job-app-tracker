"""Entry point: open the database (creating the data dir on first run) and show
the main window."""

import sys

from PySide6.QtWidgets import QApplication

import db
from ui.main_window import MainWindow


def main():
    conn = db.connect(db.DEFAULT_DB_PATH)   # creates ~/.job-app-tracker on first run
    app = QApplication(sys.argv)
    app.setApplicationName("Job Application Tracker")
    window = MainWindow(conn, str(db.DEFAULT_DB_PATH))
    window.show()
    exit_code = app.exec()
    conn.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
