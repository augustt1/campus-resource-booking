"""Shared set-up for the test suite.

Three kinds of test live in this folder:

* test_validation.py     - pure input rules. No database, no network.
* test_access.py         - sign-in and permissions. The database and the
                           sign-in service are replaced with stand-ins.
* test_booking_rules.py  - the real SQL against the real database. Every
                           test runs inside a transaction that is rolled
                           back afterwards, so nothing a test creates is
                           ever saved. Skipped when DATABASE_URL is not set.

Run everything with:  pytest -v
"""
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(ROOT, ".env"))
os.environ.setdefault("SESSION_SECRET", "test-only-secret")

import db  # noqa: E402


@pytest.fixture(scope="session")
def _connection():
    """One database connection shared by the whole test run."""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL is not set, so database tests are skipped.")
    try:
        con = psycopg2.connect(url, cursor_factory=RealDictCursor, connect_timeout=15)
    except psycopg2.OperationalError:
        pytest.skip("The database could not be reached, so database tests are skipped.")
    yield con
    con.close()


@pytest.fixture
def temp_db(_connection, monkeypatch):
    """Send every query db.py makes through one transaction, then undo it.

    Each statement gets its own savepoint, so a statement the database
    rejects (a double booking, say) fails on its own without breaking
    the rest of the test, exactly as it would in the running app.
    """
    con = _connection

    def run(sql, params=None, fetch=None):
        with con.cursor() as cur:
            cur.execute("SAVEPOINT one_statement")
            try:
                cur.execute(sql, params or ())
                if fetch == "all":
                    result = cur.fetchall()
                elif fetch == "one":
                    result = cur.fetchone()
                else:
                    result = cur.rowcount
            except Exception:
                cur.execute("ROLLBACK TO SAVEPOINT one_statement")
                raise
            cur.execute("RELEASE SAVEPOINT one_statement")
            return result

    monkeypatch.setattr(db, "_run", run)
    yield
    con.rollback()


@pytest.fixture
def student_id(temp_db):
    """The id of an existing student account to make bookings as."""
    row = db._run("SELECT user_id::text AS user_id FROM profiles WHERE role = 'student' "
                  "ORDER BY created_at LIMIT 1", fetch="one")
    if not row:
        pytest.skip("No student profile exists. Run db/seed.py first.")
    return row["user_id"]


@pytest.fixture
def room(temp_db):
    """A brand-new resource that only exists for the length of one test."""
    db.create_resource("Pytest Room", "Study Room", "Test Building", "T-001", 4, "temporary")
    return [r for r in db.list_resources() if r["resource_name"] == "Pytest Room"][0]
