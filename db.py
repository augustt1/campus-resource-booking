# db.py
# ------------------------------------------------------------
# Database layer: connection handling and every SQL query the
# app runs. No HTML, no routing — just Postgres (Supabase) access.
#
# The schema lives in db/schema.sql. Sign-in is handled by
# Supabase Auth (see auth.py); this file only reads and writes
# our own tables.
# ------------------------------------------------------------
import logging
import os
import threading
from datetime import date

import psycopg2
from psycopg2 import errors
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

STATUSES = ("confirmed", "completed", "cancelled", "no_show")
OPEN_HOUR, CLOSE_HOUR = 8, 20


# ---------------- connection handling ----------------
# A small pool keeps a few connections open, so each page does not
# pay the cost of a fresh network handshake with Supabase.
_pool = None
_pool_lock = threading.Lock()


def _get_pool():
    global _pool
    with _pool_lock:
        if _pool is None:
            url = os.environ.get("DATABASE_URL")
            if not url:
                raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
            try:
                _pool = ThreadedConnectionPool(
                    1, 5, dsn=url, cursor_factory=RealDictCursor, connect_timeout=15,
                    keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3,
                )
            except psycopg2.Error:
                # Log that it failed, but never the connection string (it holds the password).
                logger.error("Could not connect to the database. Check DATABASE_URL in .env.")
                raise
        return _pool


def _run(sql, params=None, fetch=None):
    """Run one statement in its own transaction.

    fetch: "all" -> list of rows, "one" -> a single row or None,
           None  -> number of rows affected.
    Rows are dictionaries keyed by column name.
    If Supabase has closed an idle connection we throw it away and
    retry once on a fresh one.
    """
    pool = _get_pool()
    for attempt in (1, 2):
        con = pool.getconn()
        try:
            with con:                       # commits, or rolls back on error
                with con.cursor() as cur:
                    cur.execute(sql, params or ())
                    if fetch == "all":
                        return cur.fetchall()
                    if fetch == "one":
                        return cur.fetchone()
                    return cur.rowcount
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            pool.putconn(con, close=True)
            con = None
            if attempt == 2:
                raise
        finally:
            if con is not None:
                pool.putconn(con)


# ---------------- lookups ----------------
def list_types():
    return _run("SELECT type_id, name, icon FROM resource_types ORDER BY name", fetch="all")


def type_names():
    return [t["name"] for t in list_types()]


def list_departments():
    return _run("SELECT department_id, name FROM departments ORDER BY name", fetch="all")


# ---------------- people ----------------
def get_profile(user_id):
    return _run(
        """SELECT p.user_id::text AS user_id, p.university_id, p.first_name, p.last_name,
                  p.role, p.course, d.name AS department
           FROM profiles p LEFT JOIN departments d ON d.department_id = p.department_id
           WHERE p.user_id = %s""",
        (user_id,), fetch="one",
    )


# ---------------- resources ----------------
_RESOURCE_SELECT = """
    SELECT r.resource_id, r.resource_name, r.type_id, t.name AS resource_type, t.icon,
           r.department_id, r.building, r.room_code, r.capacity, r.notes, r.is_active
    FROM resources r JOIN resource_types t ON t.type_id = r.type_id
"""


def list_resources(active_only=False, rtype=""):
    q = _RESOURCE_SELECT + " WHERE TRUE"
    p = []
    if active_only:
        q += " AND r.is_active"
    if rtype:
        q += " AND t.name = %s"
        p.append(rtype)
    q += " ORDER BY r.resource_name"
    return _run(q, p, fetch="all")


def get_resource(rid):
    return _run(_RESOURCE_SELECT + " WHERE r.resource_id = %s", (rid,), fetch="one")


def create_resource(resource_name, resource_type, building, room_code, capacity, notes, is_active=True):
    _run(
        """INSERT INTO resources (resource_name, type_id, building, room_code, capacity, notes, is_active)
           VALUES (%s, (SELECT type_id FROM resource_types WHERE name = %s), %s, %s, %s, %s, %s)""",
        (resource_name, resource_type, building, room_code, capacity, notes, bool(is_active)),
    )


def update_resource(rid, resource_name, resource_type, building, room_code, capacity, notes, is_active=True):
    _run(
        """UPDATE resources SET resource_name = %s,
                  type_id = (SELECT type_id FROM resource_types WHERE name = %s),
                  building = %s, room_code = %s, capacity = %s, notes = %s, is_active = %s
           WHERE resource_id = %s""",
        (resource_name, resource_type, building, room_code, capacity, notes, bool(is_active), rid),
    )


def delete_resource(rid):
    """Delete a resource. Returns False if it still has bookings: the
    database refuses, so booking history is never wiped by accident."""
    try:
        _run("DELETE FROM resources WHERE resource_id = %s", (rid,))
        return True
    except errors.ForeignKeyViolation:
        return False


# ---------------- bookings ----------------
# Dates and times are returned as text ('2026-11-25', '09:00') so the
# pages can show and compare them without further conversion.
_BOOKING_SELECT = """
    SELECT b.booking_id, b.resource_id, b.user_id::text AS user_id,
           b.booking_date::text AS booking_date,
           to_char(b.start_time, 'HH24:MI') AS start_time,
           to_char(b.end_time, 'HH24:MI') AS end_time,
           b.purpose, s.code AS status,
           r.resource_name, r.building, r.room_code, t.name AS resource_type, t.icon,
           p.first_name || ' ' || p.last_name AS user_name, p.university_id
    FROM bookings b
    JOIN resources r        ON r.resource_id = b.resource_id
    JOIN resource_types t   ON t.type_id = r.type_id
    JOIN booking_statuses s ON s.status_id = b.status_id
    JOIN profiles p         ON p.user_id = b.user_id
"""


def list_bookings(upcoming=None, user_id=None, limit=None):
    """upcoming=True: confirmed bookings from today on. upcoming=False:
    everything else (history). user_id narrows it to one person."""
    q = _BOOKING_SELECT + " WHERE TRUE"
    p = []
    if upcoming is True:
        q += " AND b.booking_date >= %s AND s.code = 'confirmed'"
        p.append(date.today())
    elif upcoming is False:
        q += " AND NOT (b.booking_date >= %s AND s.code = 'confirmed')"
        p.append(date.today())
    if user_id:
        q += " AND b.user_id = %s"
        p.append(user_id)
    q += " ORDER BY b.booking_date " + ("ASC" if upcoming else "DESC") + ", b.start_time ASC"
    if limit is not None:
        q += " LIMIT %s"
        p.append(limit)
    return _run(q, p, fetch="all")


def get_booking(bid):
    return _run(_BOOKING_SELECT + " WHERE b.booking_id = %s", (bid,), fetch="one")


def has_clash(resource_id, booking_date, start_time, end_time, exclude_id=None):
    """True if a confirmed booking for this resource overlaps the slot."""
    q = """SELECT COUNT(*) AS n FROM bookings
           WHERE resource_id = %s AND booking_date = %s AND status_id = 1
             AND NOT (end_time <= %s OR start_time >= %s)"""
    p = [resource_id, booking_date, start_time, end_time]
    if exclude_id is not None:
        q += " AND booking_id <> %s"
        p.append(exclude_id)
    return _run(q, p, fetch="one")["n"] > 0


def create_booking(resource_id, user_id, booking_date, start_time, end_time, purpose):
    """Create a confirmed booking. Returns False if the database's
    no-overlap rule rejects it (someone took the slot a moment earlier)."""
    try:
        _run(
            """INSERT INTO bookings (resource_id, user_id, booking_date, start_time, end_time, purpose)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (resource_id, user_id, booking_date, start_time, end_time, purpose),
        )
        return True
    except errors.ExclusionViolation:
        return False


def set_booking_status(bid, status):
    if status not in STATUSES:
        raise ValueError(f"Invalid booking status: {status!r}")
    _run(
        "UPDATE bookings SET status_id = (SELECT status_id FROM booking_statuses WHERE code = %s) WHERE booking_id = %s",
        (status, bid),
    )


def slots_for(resource_id, d):
    return _run(
        """SELECT to_char(b.start_time, 'HH24:MI') AS start_time,
                  to_char(b.end_time, 'HH24:MI') AS end_time,
                  p.first_name || ' ' || p.last_name AS user_name
           FROM bookings b JOIN profiles p ON p.user_id = b.user_id
           WHERE b.resource_id = %s AND b.booking_date = %s AND b.status_id = 1
           ORDER BY b.start_time""",
        (resource_id, d), fetch="all",
    )
