# analytics.py
# ------------------------------------------------------------
# Aggregation / reporting logic. Reads from db.py, returns
# plain Python values ready for the UI layer to render.
# ------------------------------------------------------------
import logging
import sqlite3
from datetime import date, timedelta, datetime
from db import get_db, OPEN_HOUR, CLOSE_HOUR

logger = logging.getLogger(__name__)


def _hours(s, e):
    try:
        t0 = datetime.strptime(s, "%H:%M")
        t1 = datetime.strptime(e, "%H:%M")
        return max((t1 - t0).total_seconds() / 3600, 0)
    except (TypeError, ValueError):
        return 0.0


def _pct(part, whole):
    try:
        if not whole or whole <= 0:
            return 0.0
        return round((part / whole) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0.0


def kpis(days=30):
    days = max(1, min(int(days) if days is not None else 30, 3650))
    frm = (date.today() - timedelta(days=days)).isoformat()
    to = date.today().isoformat()

    con = get_db()
    try:
        rows = con.execute(
            "SELECT * FROM bookings WHERE booking_date BETWEEN ? AND ?", (frm, to)
        ).fetchall()
        n_res = con.execute("SELECT COUNT(*) FROM resources WHERE is_active=1").fetchone()[0] or 1
    except sqlite3.Error as exc:
        logger.exception("Failed to query KPIs: %s", exc)
        raise
    finally:
        con.close()

    total = len(rows)
    cancelled = sum(1 for r in rows if r["status"] == "cancelled")
    noshow = sum(1 for r in rows if r["status"] == "no_show")
    booked_hours = sum(_hours(r["start_time"], r["end_time"]) for r in rows if r["status"] != "cancelled")
    daily_hours = max(CLOSE_HOUR - OPEN_HOUR, 1)
    capacity_hours = n_res * daily_hours * days

    return {
        "total_bookings": total,
        "booked_hours": round(booked_hours, 1),
        "utilisation_rate": _pct(booked_hours, capacity_hours),
        "cancelled_bookings": cancelled,
        "cancellation_rate": _pct(cancelled, total),
        "no_show_bookings": noshow,
        "no_show_rate": _pct(noshow, total),
        "period_from": frm,
        "period_to": to,
    }


def bookings_by_type():
    con = get_db()
    try:
        rows = con.execute(
            """SELECT r.resource_type AS label, COUNT(*) AS value
               FROM bookings b JOIN resources r USING (resource_id)
               WHERE b.status != 'cancelled'
               GROUP BY r.resource_type ORDER BY value DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error as exc:
        logger.exception("Failed to query bookings by type: %s", exc)
        raise
    finally:
        con.close()


def weekly_trend(weeks=8):
    weeks = max(1, min(int(weeks) if weeks is not None else 8, 104))
    today = date.today()
    out = []
    con = get_db()
    try:
        for i in range(weeks - 1, -1, -1):
            start = today - timedelta(days=today.weekday() + i * 7)
            end = start + timedelta(days=6)
            n = con.execute(
                """SELECT COUNT(*) FROM bookings
                   WHERE booking_date BETWEEN ? AND ? AND status != 'cancelled'""",
                (start.isoformat(), end.isoformat()),
            ).fetchone()[0]
            out.append({"label": start.strftime("%d %b"), "value": n})
        return out
    except sqlite3.Error as exc:
        logger.exception("Failed to query weekly trend: %s", exc)
        raise
    finally:
        con.close()


def most_booked(n=3):
    n = max(1, min(int(n) if n is not None else 3, 100))
    con = get_db()
    try:
        return con.execute(
            """SELECT r.*, COUNT(*) AS bookings,
                      COALESCE(SUM((julianday('2000-01-01 '||b.end_time)
- julianday('2000-01-01 '||b.start_time))*24), 0) AS hours
               FROM bookings b JOIN resources r USING (resource_id)
               WHERE b.status != 'cancelled'
               GROUP BY r.resource_id ORDER BY bookings DESC LIMIT ?""",
            (n,),
        ).fetchall()
    except sqlite3.Error as exc:
        logger.exception("Failed to query most booked resources: %s", exc)
        raise
    finally:
        con.close()


def by_building():
    con = get_db()
    try:
        return con.execute(
            """SELECT r.building AS label, COUNT(*) AS value,
                      SUM(CASE WHEN b.status='cancelled' THEN 1 ELSE 0 END) AS cancelled
               FROM bookings b JOIN resources r USING (resource_id)
               GROUP BY r.building ORDER BY value DESC"""
        ).fetchall()
    except sqlite3.Error as exc:
        logger.exception("Failed to query bookings by building: %s", exc)
        raise
    finally:
        con.close()