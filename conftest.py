"""Pytest config: putting this at the repo root adds the root to sys.path so the
tests can ``import db`` without installing the project. Also provides a fresh
in-memory database connection for each test.
"""

import pytest

import db


@pytest.fixture
def conn():
    """A fresh, fully-migrated, seeded in-memory database for one test."""
    c = db.connect(":memory:")
    yield c
    c.close()
