"""Input rules (validation.py and auth.password_problems). No database needed."""
from datetime import date, timedelta

import pytest

import auth
from validation import (
    booking_error, resource_error, parse_date, parse_time, parse_int, safe_kind,
)

TODAY = date(2026, 11, 25)
TOMORROW = (TODAY + timedelta(days=1)).isoformat()
TYPES = ["Study Room", "Computer Lab"]


def check(booking_date=TOMORROW, start="10:00", end="12:00", purpose=""):
    return booking_error(booking_date, start, end, purpose, today=TODAY)


# ---------------- booking rules ----------------
def test_valid_booking_is_accepted():
    assert check() is None


def test_booking_today_is_accepted():
    assert check(booking_date=TODAY.isoformat()) is None


def test_booking_in_the_past_is_rejected():
    yesterday = (TODAY - timedelta(days=1)).isoformat()
    assert "past" in check(booking_date=yesterday)


def test_end_must_be_after_start():
    assert "after start" in check(start="12:00", end="10:00")
    assert "after start" in check(start="10:00", end="10:00")


@pytest.mark.parametrize("start,end", [("07:30", "09:00"), ("19:00", "20:30"), ("06:00", "07:00")])
def test_booking_outside_campus_hours_is_rejected(start, end):
    assert "campus hours" in check(start=start, end=end)


def test_booking_can_fill_the_whole_day():
    assert check(start="08:00", end="20:00") is None


@pytest.mark.parametrize("bad", ["", "tomorrow", "2026-13-01", "25/11/2026", None])
def test_invalid_date_is_rejected(bad):
    assert "valid booking date" in check(booking_date=bad)


@pytest.mark.parametrize("bad", ["", "9:00", "25:00", "10:60", "ten", "10:00:00", None])
def test_invalid_time_is_rejected(bad):
    assert "valid start and end times" in check(start=bad)


def test_overlong_purpose_is_rejected():
    assert "300 characters" in check(purpose="x" * 301)
    assert check(purpose="x" * 300) is None


# ---------------- resource form ----------------
def test_valid_resource_is_accepted():
    assert resource_error("Study Room Z", "Study Room", "8", "1", TYPES) is None


def test_resource_name_is_required():
    assert "required" in resource_error("   ", "Study Room", "8", "1", TYPES)


def test_resource_name_length_is_limited():
    assert "120 characters" in resource_error("x" * 121, "Study Room", "8", "1", TYPES)


def test_resource_type_must_exist():
    assert "valid resource type" in resource_error("Room", "Sports Hall", "8", "1", TYPES)


@pytest.mark.parametrize("capacity", ["0", "-3", "abc", "", "10001", "2.5"])
def test_resource_capacity_must_be_a_sensible_whole_number(capacity):
    assert "Capacity" in resource_error("Room", "Study Room", capacity, "1", TYPES)


def test_resource_status_must_be_active_or_inactive():
    assert "valid status" in resource_error("Room", "Study Room", "8", "maybe", TYPES)


# ---------------- small helpers ----------------
def test_parse_helpers():
    assert parse_date("2026-11-25") == TODAY
    assert parse_date("nonsense", fallback=TODAY) == TODAY
    assert parse_time(" 09:30 ") == "09:30"
    assert parse_time("24:00") is None
    assert parse_int("42") == 42
    assert parse_int("0") is None
    assert parse_int("99999", default=8080, max_val=65535) == 8080


def test_alert_style_cannot_be_injected():
    assert safe_kind("error") == "error"
    assert safe_kind('x" onclick="alert(1)') == "info"


# ---------------- password rules ----------------
def test_strong_password_has_no_problems():
    assert auth.password_problems("Correct-Horse-42") == []


@pytest.mark.parametrize("password,missing", [
    ("Short-1a", "At least 12 characters"),
    ("alllowercase-123", "An uppercase letter"),
    ("ALLUPPERCASE-123", "A lowercase letter"),
    ("NoNumbersHere-!", "A number"),
    ("NoSpecialChar123", "A special character"),
    ("Aa1-" + "x" * 130, "No more than 128 characters"),
])
def test_weak_password_reports_the_missing_rule(password, missing):
    assert missing in auth.password_problems(password)
