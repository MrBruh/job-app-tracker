"""Unit tests for the db layer. Run with `pytest`. Uses the in-memory `conn`
fixture from conftest.py, so no real data is ever touched."""

import db


def _stage_id(conn, name):
    return conn.execute("SELECT id FROM stage WHERE name=?", (name,)).fetchone()["id"]


# ── schema / migration / seed ────────────────────────────────────────────

def test_migration_sets_user_version(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_foreign_keys_enabled(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_seed_creates_eleven_stages(conn):
    assert conn.execute("SELECT COUNT(*) FROM stage").fetchone()[0] == 11


def test_seed_is_idempotent(conn):
    db.seed_stages(conn)
    db.seed_stages(conn)
    assert conn.execute("SELECT COUNT(*) FROM stage").fetchone()[0] == 11


def test_list_stages_in_pipeline_order(conn):
    stages = db.list_stages(conn)
    orders = [s["sort_order"] for s in stages]
    assert orders == sorted(orders)
    assert stages[0]["name"] == "Saved"


# ── applications ──────────────────────────────────────────────────────────

def test_add_application_records_initial_stage_event(conn):
    sid = _stage_id(conn, "Applied")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=sid,
                               date_applied="2026-06-01")
    app = db.get_application(conn, app_id)
    assert app["company"] == "Acme"
    assert app["current_stage_id"] == sid
    events = db.list_stage_events(conn, app_id)
    assert len(events) == 1
    assert events[0]["stage_id"] == sid


def test_update_application_does_not_change_stage(conn):
    applied = _stage_id(conn, "Applied")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=applied)
    db.update_application(conn, app_id, company="Acme Corp", role="Backend Eng")
    app = db.get_application(conn, app_id)
    assert app["company"] == "Acme Corp"
    assert app["current_stage_id"] == applied            # stage untouched
    assert len(db.list_stage_events(conn, app_id)) == 1  # no spurious event


def test_set_stage_updates_and_logs_atomically(conn):
    applied = _stage_id(conn, "Applied")
    interview = _stage_id(conn, "Interview")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=applied)
    db.set_stage(conn, app_id, interview, note="passed screen")
    app = db.get_application(conn, app_id)
    assert app["current_stage_id"] == interview
    events = db.list_stage_events(conn, app_id)
    assert [e["stage_id"] for e in events] == [applied, interview]
    assert events[-1]["note"] == "passed screen"


def test_delete_application_cascades(conn):
    sid = _stage_id(conn, "Applied")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=sid)
    db.add_qa(conn, app_id, "Why us?", "Because...")
    db.set_stage(conn, app_id, _stage_id(conn, "Interview"))
    db.delete_application(conn, app_id)
    assert db.get_application(conn, app_id) is None
    assert conn.execute("SELECT COUNT(*) FROM qa_entry WHERE application_id=?",
                        (app_id,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM stage_event WHERE application_id=?",
                        (app_id,)).fetchone()[0] == 0


def test_date_applied_null_roundtrip(conn):
    saved = _stage_id(conn, "Saved")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=saved,
                               date_applied=None)
    assert db.get_application(conn, app_id)["date_applied"] is None


def test_list_applications_filter_and_join(conn):
    applied = _stage_id(conn, "Applied")
    interview = _stage_id(conn, "Interview")
    db.add_application(conn, company="Acme", role="Eng", stage_id=applied)
    db.add_application(conn, company="Globex", role="Sci", stage_id=interview)
    everything = db.list_applications(conn)
    assert len(everything) == 2
    assert "stage_name" in everything[0].keys()
    only_applied = db.list_applications(conn, stage_id=applied)
    assert len(only_applied) == 1
    assert only_applied[0]["company"] == "Acme"


# ── Q&A ───────────────────────────────────────────────────────────────────

def test_qa_crud(conn):
    sid = _stage_id(conn, "Applied")
    app_id = db.add_application(conn, company="Acme", role="Eng", stage_id=sid)
    qa_id = db.add_qa(conn, app_id, "Why us?", "First answer")
    rows = db.list_qa(conn, app_id)
    assert len(rows) == 1 and rows[0]["answer"] == "First answer"
    db.update_qa(conn, qa_id, "Why us?", "Better answer")
    assert db.list_qa(conn, app_id)[0]["answer"] == "Better answer"
    db.delete_qa(conn, qa_id)
    assert db.list_qa(conn, app_id) == []


# ── search ────────────────────────────────────────────────────────────────

def test_search_matches_question_and_answer_with_source(conn):
    a1 = db.add_application(conn, company="Acme", role="Backend Eng",
                            stage_id=_stage_id(conn, "Applied"))
    a2 = db.add_application(conn, company="Globex", role="Data Sci",
                            stage_id=_stage_id(conn, "Applied"))
    db.add_qa(conn, a1, "Why do you want to work here?", "I love your mission")
    db.add_qa(conn, a2, "Greatest weakness?", "I work too hard")
    res = db.search_qa(conn, "work")          # matches q1 question + a2 answer
    assert len(res) == 2
    assert {r["company"] for r in res} == {"Acme", "Globex"}


def test_search_empty_term_returns_nothing(conn):
    app_id = db.add_application(conn, company="A", role="R",
                               stage_id=_stage_id(conn, "Applied"))
    db.add_qa(conn, app_id, "Q", "A")
    assert db.search_qa(conn, "") == []
    assert db.search_qa(conn, "   ") == []


def test_search_no_results(conn):
    app_id = db.add_application(conn, company="A", role="R",
                               stage_id=_stage_id(conn, "Applied"))
    db.add_qa(conn, app_id, "Question text", "Answer text")
    assert db.search_qa(conn, "zzzznomatch") == []
