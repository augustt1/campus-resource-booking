"""
Starter test suite for campus-resource-booking.

These tests exercise the data-layer logic in db.py (and, where noted,
analytics.py) in isolation from the real campus.db file. Each test run
creates a fresh temporary SQLite database so tests never pollute or
depend on seed data.

Run with:
    pytest tests/test_booking_rules.py -v
"""
import os
import sys
from datetime import date, timedelta

import pytest

# Allow tests to import the project modules from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import db  # noqa: E402


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """Point db.DB_PATH at a throwaway file for the duration of one test."""
    test_db_path = tmp_path / "test_campus.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db_path))
    db.init_db()
    yield
    # tmp_path is cleaned up automatically by pytest


# ---------------------------------------------------------------------
# Resource CRUD
# ---------------------------------------------------------------------

def test_create_resource_appears_in_list(temp_db):
    db.create_resource("Study Room Z", "Room", "LIB-999", is_active=1)
    resources = db.list_resources()
    names = [r["resource_name"] for r in resources]
    assert "Study Room Z" in names


def test_update_resource_changes_fields(temp_db):
    db.create_resource("Lab Temp", "Lab", "ENG-999", is_active=1)
    created = [r for r in db.list_resources() if r["resource_name"] == "Lab Temp"][0]

    db.update_resource(
        created["resource_id"],
        resource_name="Lab Renamed",
        resource_type="Lab",
        room_code="ENG-998",
        is_active=0,
    )
    updated = db.get_resource(created["resource_id"])
    assert updated["resource_name"] == "Lab Renamed"
    assert updated["room_code"] == "ENG-998"
    assert updated["is_active"] == 0


def test_delete_resource_removes_it(temp_db):
    db.create_resource("Temp Hall", "Hall", "MB-999", is_active=1)
    created = [r for r in db.list_resources() if r["resource_name"] == "Temp Hall"][0]

    db.delete_resource(created["resource_id"])
    remaining_ids = [r["resource_id"] for r in db.list_resources()]
    assert created["resource_id"] not in remaining_ids


# ---------------------------------------------------------------------
# Booking clash detection (core business rule)
# ---------------------------------------------------------------------

def test_has_clash_detects_overlapping_booking(temp_db):
    resources = db.list_resources(active_only=True)
    resource_id = resources[0]["resource_id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    db.create_booking(resource_id, "alice", tomorrow, "10:00", "12:00", "Project work")

    # Overlapping window (11:00-13:00 overlaps the 10:00-12:00 booking)
    clash = db.has_clash(resource_id, tomorrow, "11:00", "13:00")
    assert clash is True


def test_has_clash_allows_non_overlapping_booking(temp_db):
    resources = db.list_resources(active_only=True)
    resource_id = resources[0]["resource_id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    db.create_booking(resource_id, "alice", tomorrow, "10:00", "12:00", "Project work")

    # Back-to-back, non-overlapping window
    clash = db.has_clash(resource_id, tomorrow, "12:00", "13:00")
    assert clash is False


def test_has_clash_ignores_cancelled_bookings(temp_db):
    """A cancelled booking should free up the slot for a new booking."""
    resources = db.list_resources(active_only=True)
    resource_id = resources[0]["resource_id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    db.create_booking(resource_id, "alice", tomorrow, "10:00", "12:00", "Project work")
    bookings = db.list_bookings(upcoming=False)
    created = [b for b in bookings if b["user_name"] == "alice"][0]

    db.set_booking_status(created["booking_id"], "cancelled")

    clash = db.has_clash(resource_id, tomorrow, "10:00", "12:00")
    assert clash is False


# ---------------------------------------------------------------------
# Booking status transitions (covers the history-visibility bug fix)
# ---------------------------------------------------------------------

def test_cancelled_booking_appears_in_history(temp_db):
    """
    Regression test for the bug where cancelling/completing a future
    booking made it vanish from both the upcoming and history views.
    """
    resources = db.list_resources(active_only=True)
    resource_id = resources[0]["resource_id"]
    future_date = (date.today() + timedelta(days=3)).isoformat()

    db.create_booking(resource_id, "bob", future_date, "09:00", "10:00", "Meeting")
    created = [b for b in db.list_bookings(upcoming=False) if b["user_name"] == "bob"][0]

    db.set_booking_status(created["booking_id"], "cancelled")

    history = db.list_bookings(upcoming=False)
    history_ids = [b["booking_id"] for b in history]
    assert created["booking_id"] in history_ids, (
        "Cancelled future booking should still be visible in booking history"
    )


# ---------------------------------------------------------------------
# Validation rules that live in main.py route handlers today.
#
# NOTE: these are currently enforced in main.py's /bookings/new POST
# handler rather than in db.py. As a future improvement, consider moving
# validation (opening hours, past-date check) into a pure function in
# db.py or a new validation.py so it can be unit tested directly, without
# needing to simulate an HTTP request.
# ---------------------------------------------------------------------

def test_booking_in_the_past_is_rejected_by_business_rule():
    """
    Placeholder test documenting an untested rule: bookings dated before
    today should be rejected. Once this validation is extracted into a
    standalone function (e.g. validate_booking_date), replace this stub
    with a real assertion against that function.
    """
    pytest.skip("Validation currently lives in main.py route handler; "
                "extract to a testable function as a follow-up.")