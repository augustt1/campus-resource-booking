# db.py
# ------------------------------------------------------------
# Database layer: schema, seed data, and all raw queries.
# No HTML, no routing — just SQLite access.
# ------------------------------------------------------------
import sqlite3
import os
from datetime import date, timedelta

DB_PATH = "campus.db"

TYPES = ["Study Room", "Lab", "Hall", "Equipment", "Sports Facility"]
TYPE_ICON = {
    "Study Room": "📖",
    "Lab": "🔬",
    "Hall": "🏛️",
    "Equipment": "🎥",
    "Sports Facility": "🏀",
}
STATUSES = ("confirmed", "completed", "cancelled", "no_show")
OPEN_HOUR, CLOSE_HOUR = 8, 20

SEED_RESOURCES = [
    ("Study Room A", "Study Room", "Library", "LIB-101", 8, "Quiet study room"),
    ("Group Room 1", "Study Room", "Library", "LIB-102", 6, "Whiteboard included"),
    ("Silent Room 1", "Study Room", "Library", "LIB-G04", 1, "Single-occupant pod"),
    ("AI Lab", "Lab", "Engineering", "ENG-204", 30, "40 workstations, GPU bench"),
    ("Robotics Lab", "Lab", "Engineering", "ENG-118", 24, "Project workbenches"),
    ("Main Hall", "Hall", "Main Building", "MB-001", 180, "Lecture hall"),
    ("Seminar Hall 3", "Hall", "Main Building", "MB-203", 40, "Flexible seating"),
    ("Camera Kit #1", "Equipment", "Media Centre", "MC-KIT1", 1, "DSLR + tripod"),
    ("Projector Set", "Equipment", "Media Centre", "MC-PRJ2", 1, "Portable, HDMI/USB-C"),
    ("Sports Court 1", "Sports Facility", "Sports Centre", "SC-C1", 20, "Indoor court"),
]


def get_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS resources (
    resource_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_name TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    building      TEXT NOT NULL DEFAULT '',
    room_code     TEXT NOT NULL DEFAULT '',
    capacity      INTEGER NOT NULL DEFAULT 1,
    notes         TEXT NOT NULL DEFAULT '',
    is_active     INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS bookings (
    booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_id  INTEGER NOT NULL REFERENCES resources(resource_id) ON DELETE CASCADE,
    user_name    TEXT NOT NULL,
    booking_date TEXT NOT NULL,
    start_time   TEXT NOT NULL,
    end_time     TEXT NOT NULL,
    purpose      TEXT NOT NULL DEFAULT '',
    status       TEXT NOT NULL DEFAULT 'confirmed',
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_book_res_date ON bookings(resource_id, booking_date);
"""


def init_db():
    fresh = not os.path.exists(DB_PATH)
    con = get_db()
    con.executescript(SCHEMA)

    if con.execute("SELECT COUNT(*) FROM resources").fetchone()[0] == 0:
        con.executemany(
            """INSERT INTO resources
               (resource_name, resource_type, building, room_code, capacity, notes)
               VALUES (?,?,?,?,?,?)""",
            SEED_RESOURCES,
        )

    if con.execute("SELECT COUNT(*) FROM bookings").fetchone()[0] == 0:
        today = date.today()
        demo = [
            (1, "a.chen", today + timedelta(days=1), "09:00", "11:00", "Group study", "confirmed"),
            (4, "a.chen", today + timedelta(days=2), "13:00", "16:00", "ML training", "confirmed"),
            (6, "j.okafor", today + timedelta(days=3), "10:00", "12:00", "Robot build", "confirmed"),
            (8, "m.rossi", today + timedelta(days=4), "14:00", "17:00", "Filming", "confirmed"),
            (2, "s.patel", today - timedelta(days=2), "09:00", "10:00", "Revision", "completed"),
            (5, "s.patel", today - timedelta(days=5), "11:00", "13:00", "Project demo", "completed"),
            (1, "l.nguyen", today - timedelta(days=7), "15:00", "16:00", "Quiet study", "completed"),
            (10, "t.brown", today - timedelta(days=9), "18:00", "20:00", "Team practice", "no_show"),
            (4, "a.chen", today - timedelta(days=12), "09:00", "12:00", "Workshop", "completed"),
            (7, "j.okafor", today - timedelta(days=15), "13:00", "15:00", "Seminar", "cancelled"),
            (6, "m.rossi", today - timedelta(days=20), "09:00", "11:00", "Lab session", "completed"),
            (3, "l.nguyen", today - timedelta(days=24), "10:00", "11:00", "Focus work", "completed"),
        ]
        con.executemany(
            """INSERT INTO bookings
               (resource_id,user_name,booking_date,start_time,end_time,purpose,status)
               VALUES (?,?,?,?,?,?,?)""",
            [(r, u, d.isoformat(), s, e, p, st) for r, u, d, s, e, p, st in demo],
        )
    con.commit()
    con.close()
    if fresh:
        print(f"Created fresh database at {DB_PATH}")


# ---------------- resources ----------------
def list_resources(active_only=False, rtype=""):
    con = get_db()
    q = "SELECT * FROM resources WHERE 1=1"
    p = []
    if active_only:
        q += " AND is_active = 1"
    if rtype:
        q += " AND resource_type = ?"
        p.append(rtype)
    q += " ORDER BY resource_name"
    rows = con.execute(q, p).fetchall()
    con.close()
    return rows


def get_resource(rid):
    con = get_db()
    row = con.execute("SELECT * FROM resources WHERE resource_id=?", (rid,)).fetchone()
    con.close()
    return row


def create_resource(resource_name, resource_type, building, room_code, capacity, notes, is_active=1):
    con = get_db()
    con.execute(
        """INSERT INTO resources
           (resource_name, resource_type, building, room_code, capacity, notes, is_active)
           VALUES (?,?,?,?,?,?,?)""",
        (resource_name, resource_type, building, room_code, capacity, notes, is_active),
    )
    con.commit()
    con.close()


def update_resource(rid, resource_name, resource_type, building, room_code, capacity, notes, is_active=1):
    con = get_db()
    con.execute(
        """UPDATE resources SET resource_name=?, resource_type=?, building=?,
           room_code=?, capacity=?, notes=?, is_active=? WHERE resource_id=?""",
        (resource_name, resource_type, building, room_code, capacity, notes, is_active, rid),
    )
    con.commit()
    con.close()


def delete_resource(rid):
    con = get_db()
    con.execute("DELETE FROM resources WHERE resource_id=?", (rid,))
    con.commit()
    con.close()


# ---------------- bookings ----------------
def list_bookings(upcoming=None, user="", limit=None):
    q = """SELECT b.*, r.resource_name, r.building, r.room_code, r.resource_type
           FROM bookings b JOIN resources r USING (resource_id) WHERE 1=1"""
    p = []
    if upcoming is True:
        q += " AND b.booking_date >= ? AND b.status='confirmed'"
        p.append(date.today().isoformat())
    elif upcoming is False:
        q += " AND NOT (b.booking_date >= ? AND b.status='confirmed')"
        p.append(date.today().isoformat())
    if user:
        q += " AND b.user_name = ?"
        p.append(user)
    q += " ORDER BY b.booking_date " + ("ASC" if upcoming else "DESC") + ", b.start_time ASC"
    if limit:
        q += " LIMIT ?"
        p.append(limit)
    con = get_db()
    rows = con.execute(q, p).fetchall()
    con.close()
    return rows


def get_booking(bid):
    con = get_db()
    row = con.execute(
        """SELECT b.*, r.resource_name, r.building, r.room_code
           FROM bookings b JOIN resources r USING (resource_id)
           WHERE b.booking_id=?""",
        (bid,),
    ).fetchone()
    con.close()
    return row


def has_clash(resource_id, booking_date, start_time, end_time, exclude_id=None):
    q = """SELECT COUNT(*) FROM bookings
           WHERE resource_id=? AND booking_date=? AND status='confirmed'
           AND NOT (end_time <= ? OR start_time >= ?)"""
    p = [resource_id, booking_date, start_time, end_time]
    if exclude_id:
        q += " AND booking_id != ?"
        p.append(exclude_id)
    con = get_db()
    n = con.execute(q, p).fetchone()[0]
    con.close()
    return n > 0


def create_booking(resource_id, user_name, booking_date, start_time, end_time, purpose):
    con = get_db()
    con.execute(
        """INSERT INTO bookings
           (resource_id,user_name,booking_date,start_time,end_time,purpose,status)
           VALUES (?,?,?,?,?,?, 'confirmed')""",
        (resource_id, user_name, booking_date, start_time, end_time, purpose),
    )
    con.commit()
    con.close()


def set_booking_status(bid, status):
    con = get_db()
    con.execute("UPDATE bookings SET status=? WHERE booking_id=?", (status, bid))
    con.commit()
    con.close()


def slots_for(resource_id, d):
    con = get_db()
    rows = con.execute(
        """SELECT start_time, end_time, user_name FROM bookings
           WHERE resource_id=? AND booking_date=? AND status='confirmed'
           ORDER BY start_time""",
        (resource_id, d),
    ).fetchall()
    con.close()
    return rows