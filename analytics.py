# analytics.py
# ------------------------------------------------------------
# Aggregation / reporting logic. Runs SQL through db.py and
# returns plain Python values ready for the UI layer to render.
# ------------------------------------------------------------
from datetime import date, timedelta

import db
from db import OPEN_HOUR, CLOSE_HOUR


def _run(*args, **kwargs):
    return db._run(*args, **kwargs)


def _pct(part, whole):
    try:
        if not whole or whole <= 0:
            return 0.0
        return round((part / whole) * 100, 1)
    except (TypeError, ZeroDivisionError):
        return 0.0


def _clamp(value, default, low, high):
    """Keep a caller-supplied number inside a sensible range."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(low, min(value, high))


def kpis(days=30):
    """Headline figures for the last `days` days."""
    days = _clamp(days, 30, 1, 3650)
    frm = date.today() - timedelta(days=days)
    to = date.today()
    row = _run(
        """SELECT COUNT(*) AS total,
                  COUNT(*) FILTER (WHERE s.code = 'cancelled') AS cancelled,
                  COUNT(*) FILTER (WHERE s.code = 'no_show')   AS no_show,
                  COALESCE(SUM(EXTRACT(EPOCH FROM (b.end_time - b.start_time)) / 3600)
                           FILTER (WHERE s.code <> 'cancelled'), 0) AS hours
           FROM bookings b JOIN booking_statuses s ON s.status_id = b.status_id
           WHERE b.booking_date BETWEEN %s AND %s""",
        (frm, to), fetch="one",
    )
    n_res = _run("SELECT COUNT(*) AS n FROM resources WHERE is_active", fetch="one")["n"] or 1

    total = row["total"]
    booked_hours = float(row["hours"])
    capacity_hours = n_res * max(CLOSE_HOUR - OPEN_HOUR, 1) * days

    return {
        "total_bookings": total,
        "booked_hours": round(booked_hours, 1),
        "utilisation_rate": _pct(booked_hours, capacity_hours),
        "cancelled_bookings": row["cancelled"],
        "cancellation_rate": _pct(row["cancelled"], total),
        "no_show_bookings": row["no_show"],
        "no_show_rate": _pct(row["no_show"], total),
        "period_from": frm.isoformat(),
        "period_to": to.isoformat(),
    }


def bookings_by_type():
    return _run(
        """SELECT t.name AS label, COUNT(*) AS value
           FROM bookings b
           JOIN resources r        ON r.resource_id = b.resource_id
           JOIN resource_types t   ON t.type_id = r.type_id
           JOIN booking_statuses s ON s.status_id = b.status_id
           WHERE s.code <> 'cancelled'
           GROUP BY t.name ORDER BY value DESC""",
        fetch="all",
    )


def weekly_trend(weeks=8):
    """Bookings per week (Monday to Sunday) for the last `weeks` weeks,
    including weeks with none."""
    weeks = _clamp(weeks, 8, 1, 104)
    this_monday = date.today() - timedelta(days=date.today().weekday())
    first_monday = this_monday - timedelta(weeks=weeks - 1)
    rows = _run(
        """SELECT date_trunc('week', b.booking_date)::date AS week_start, COUNT(*) AS n
           FROM bookings b JOIN booking_statuses s ON s.status_id = b.status_id
           WHERE s.code <> 'cancelled' AND b.booking_date BETWEEN %s AND %s
           GROUP BY 1""",
        (first_monday, this_monday + timedelta(days=6)), fetch="all",
    )
    counts = {r["week_start"]: r["n"] for r in rows}
    out = []
    for i in range(weeks):
        start = first_monday + timedelta(weeks=i)
        out.append({"label": start.strftime("%d %b"), "value": counts.get(start, 0)})
    return out


def most_booked(n=3):
    n = _clamp(n, 3, 1, 100)
    rows = _run(
        """SELECT r.resource_name, r.building, r.room_code, t.name AS resource_type, t.icon,
                  COUNT(*) AS bookings,
                  COALESCE(SUM(EXTRACT(EPOCH FROM (b.end_time - b.start_time)) / 3600), 0) AS hours
           FROM bookings b
           JOIN resources r        ON r.resource_id = b.resource_id
           JOIN resource_types t   ON t.type_id = r.type_id
           JOIN booking_statuses s ON s.status_id = b.status_id
           WHERE s.code <> 'cancelled'
           GROUP BY r.resource_id, t.name, t.icon
           ORDER BY bookings DESC, r.resource_name LIMIT %s""",
        (n,), fetch="all",
    )
    for r in rows:
        r["hours"] = float(r["hours"])
    return rows


def by_building():
    return _run(
        """SELECT r.building AS label, COUNT(*) AS value,
                  COUNT(*) FILTER (WHERE s.code = 'cancelled') AS cancelled
           FROM bookings b
           JOIN resources r        ON r.resource_id = b.resource_id
           JOIN booking_statuses s ON s.status_id = b.status_id
           GROUP BY r.building ORDER BY value DESC""",
        fetch="all",
    )
