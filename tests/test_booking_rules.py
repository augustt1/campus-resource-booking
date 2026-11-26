"""Database rules for campus-resource-booking: the SQL in db.py and
analytics.py, run against the real Supabase (Postgres) database.

Nothing these tests create is kept: each test runs inside a transaction
that is rolled back at the end (see the temp_db fixture in conftest.py).
They are skipped automatically when DATABASE_URL is not set.

Run with:
    pytest tests/test_booking_rules.py -v
"""
from datetime import date, timedelta

import pytest

import analytics
import db

TOMORROW = (date.today() + timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------
# Resource CRUD
# ---------------------------------------------------------------------

def test_create_resource_appears_in_list(temp_db):
    db.create_resource("Study Room Z", "Study Room", "Library", "LIB-999", 6, "")
    names = [r["resource_name"] for r in db.list_resources()]
    assert "Study Room Z" in names


def test_update_resource_changes_fields(room):
    db.update_resource(room["resource_id"], "Lab Renamed", "Computer Lab", "Engineering",
                       "ENG-998", 12, "moved", is_active=False)
    updated = db.get_resource(room["resource_id"])
    assert updated["resource_name"] == "Lab Renamed"
    assert updated["resource_type"] == "Computer Lab"
    assert updated["room_code"] == "ENG-998"
    assert updated["capacity"] == 12
    assert updated["is_active"] is False


def test_inactive_resource_is_hidden_from_bookable_list(room):
    db.update_resource(room["resource_id"], room["resource_name"], room["resource_type"],
                       room["building"], room["room_code"], room["capacity"], room["notes"], is_active=False)
    bookable = [r["resource_id"] for r in db.list_resources(active_only=True)]
    assert room["resource_id"] not in bookable


def test_delete_resource_removes_it(room):
    assert db.delete_resource(room["resource_id"]) is True
    remaining_ids = [r["resource_id"] for r in db.list_resources()]
    assert room["resource_id"] not in remaining_ids


def test_resource_with_bookings_cannot_be_deleted(room, student_id):
    """Booking history must survive, so the database refuses the delete."""
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Project work")
    assert db.delete_resource(room["resource_id"]) is False
    assert db.get_resource(room["resource_id"]) is not None


def test_database_rejects_zero_capacity(temp_db):
    import psycopg2
    with pytest.raises(psycopg2.errors.CheckViolation):
        db.create_resource("Broken Room", "Study Room", "Library", "LIB-000", 0, "")


# ---------------------------------------------------------------------
# Booking clash detection (core business rule)
# ---------------------------------------------------------------------

def test_has_clash_detects_overlapping_booking(room, student_id):
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Project work")
    # 11:00-13:00 overlaps the 10:00-12:00 booking
    assert db.has_clash(room["resource_id"], TOMORROW, "11:00", "13:00") is True


def test_has_clash_allows_non_overlapping_booking(room, student_id):
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Project work")
    # Back-to-back is fine
    assert db.has_clash(room["resource_id"], TOMORROW, "12:00", "13:00") is False
    assert db.has_clash(room["resource_id"], TOMORROW, "08:00", "10:00") is False


def test_has_clash_is_per_resource_and_per_day(room, student_id):
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Project work")
    day_after = (date.today() + timedelta(days=2)).isoformat()
    assert db.has_clash(room["resource_id"], day_after, "10:00", "12:00") is False

    db.create_resource("Pytest Room 2", "Study Room", "Test Building", "T-002", 4, "")
    other = [r for r in db.list_resources() if r["resource_name"] == "Pytest Room 2"][0]
    assert db.has_clash(other["resource_id"], TOMORROW, "10:00", "12:00") is False


def test_has_clash_ignores_cancelled_bookings(room, student_id):
    """A cancelled booking should free up the slot for a new booking."""
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Project work")
    created = [b for b in db.list_bookings(upcoming=True) if b["resource_id"] == room["resource_id"]][0]

    db.set_booking_status(created["booking_id"], "cancelled")

    assert db.has_clash(room["resource_id"], TOMORROW, "10:00", "12:00") is False
    assert db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Rebooked") is True


def test_database_itself_blocks_a_double_booking(room, student_id):
    """Safety net: even if the app's own check is skipped (two people
    submitting at the same moment), the database refuses the overlap."""
    assert db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "First") is True
    assert db.create_booking(room["resource_id"], student_id, TOMORROW, "11:00", "13:00", "Second") is False

    confirmed = [b for b in db.list_bookings(upcoming=True) if b["resource_id"] == room["resource_id"]]
    assert len(confirmed) == 1


# ---------------------------------------------------------------------
# Booking status and visibility
# ---------------------------------------------------------------------

def test_cancelled_booking_appears_in_history(room, student_id):
    """Regression test for the bug where cancelling/completing a future
    booking made it vanish from both the upcoming and history views."""
    future_date = (date.today() + timedelta(days=3)).isoformat()
    db.create_booking(room["resource_id"], student_id, future_date, "09:00", "10:00", "Meeting")
    created = [b for b in db.list_bookings(upcoming=True) if b["resource_id"] == room["resource_id"]][0]

    db.set_booking_status(created["booking_id"], "cancelled")

    upcoming_ids = [b["booking_id"] for b in db.list_bookings(upcoming=True)]
    history_ids = [b["booking_id"] for b in db.list_bookings(upcoming=False)]
    assert created["booking_id"] not in upcoming_ids
    assert created["booking_id"] in history_ids, (
        "Cancelled future booking should still be visible in booking history"
    )


def test_invalid_status_is_refused():
    with pytest.raises(ValueError):
        db.set_booking_status(1, "deleted")


def test_students_only_see_their_own_bookings(room, student_id):
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Mine")
    mine = db.list_bookings(upcoming=True, user_id=student_id)
    assert mine and all(b["user_id"] == student_id for b in mine)

    nobody = "00000000-0000-0000-0000-000000000000"
    assert db.list_bookings(upcoming=True, user_id=nobody) == []


def test_availability_slots_show_confirmed_bookings_only(room, student_id):
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "Keep")
    db.create_booking(room["resource_id"], student_id, TOMORROW, "14:00", "15:00", "Drop")
    drop = [b for b in db.list_bookings(upcoming=True)
            if b["resource_id"] == room["resource_id"] and b["start_time"] == "14:00"][0]
    db.set_booking_status(drop["booking_id"], "cancelled")

    slots = db.slots_for(room["resource_id"], TOMORROW)
    assert [(s["start_time"], s["end_time"]) for s in slots] == [("10:00", "12:00")]


# ---------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------

def test_kpis_count_a_new_booking(room, student_id):
    before = analytics.kpis()
    db.create_booking(room["resource_id"], student_id, date.today().isoformat(), "10:00", "12:00", "Counted")
    after = analytics.kpis()
    assert after["total_bookings"] == before["total_bookings"] + 1
    assert after["booked_hours"] == pytest.approx(before["booked_hours"] + 2, abs=0.11)
    assert 0 <= after["utilisation_rate"] <= 100


def test_by_building_has_the_columns_the_reports_page_reads(room, student_id):
    """Regression test for the Reports page crash (it read columns that
    the query did not return)."""
    db.create_booking(room["resource_id"], student_id, TOMORROW, "10:00", "12:00", "One")
    rows = analytics.by_building()
    test_row = [r for r in rows if r["label"] == "Test Building"][0]
    assert test_row["value"] == 1 and test_row["cancelled"] == 0


def test_weekly_trend_always_returns_every_week(temp_db):
    trend = analytics.weekly_trend(8)
    assert len(trend) == 8
    assert all(set(week) == {"label", "value"} for week in trend)


def test_most_booked_is_limited_and_sorted(temp_db):
    top = analytics.most_booked(3)
    assert len(top) <= 3
    counts = [r["bookings"] for r in top]
    assert counts == sorted(counts, reverse=True)
