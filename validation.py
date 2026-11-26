# validation.py
# ------------------------------------------------------------
# Input checks for forms. Pure functions: no database, no HTML,
# no web framework, so every rule can be unit tested directly
# (see tests/test_validation.py).
#
# Each *_error function returns a message to show the person,
# or None when the input is fine.
# ------------------------------------------------------------
import re
from datetime import date

TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

MAX_NAME = 120
MAX_PURPOSE = 300
MAX_CAPACITY = 10_000
ALERT_KINDS = ("info", "ok", "warn", "error")


def parse_date(raw, fallback=None):
    """'2026-11-25' -> date. Anything else -> fallback."""
    if not raw or not isinstance(raw, str):
        return fallback
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return fallback


def parse_time(raw):
    """'09:30' -> '09:30'. Anything that is not a real HH:MM time -> None."""
    if not raw or not isinstance(raw, str):
        return None
    value = raw.strip()
    return value if TIME_RE.match(value) else None


def parse_int(raw, default=None, min_val=1, max_val=100_000):
    """A whole number between min_val and max_val, otherwise default."""
    if raw is None or raw == "":
        return default
    try:
        num = int(str(raw).strip())
    except (TypeError, ValueError):
        return default
    return num if min_val <= num <= max_val else default


def safe_kind(kind, default="info"):
    """Only allow the alert styles the pages know about."""
    return kind if kind in ALERT_KINDS else default


def booking_error(booking_date, start_time, end_time, purpose="",
                  today=None, open_hour=8, close_hour=20):
    """Check the date, times and purpose of a proposed booking."""
    today = today or date.today()
    day = parse_date(booking_date)
    start = parse_time(start_time)
    end = parse_time(end_time)

    if day is None:
        return "Choose a valid booking date."
    if start is None or end is None:
        return "Choose valid start and end times."
    if day < today:
        return "Booking date cannot be in the past."
    if end <= start:
        return "End time must be after start time."
    if not (f"{open_hour:02d}:00" <= start and end <= f"{close_hour:02d}:00"):
        return f"Bookings must fall within campus hours ({open_hour:02d}:00–{close_hour:02d}:00)."
    if len((purpose or "").strip()) > MAX_PURPOSE:
        return f"Purpose must be {MAX_PURPOSE} characters or fewer."
    return None


def resource_error(resource_name, resource_type, capacity, is_active, valid_types):
    """Check the fields of the add/edit resource form."""
    name = (resource_name or "").strip()
    if not name:
        return "Resource name is required."
    if len(name) > MAX_NAME:
        return f"Resource name must be {MAX_NAME} characters or fewer."
    if resource_type not in valid_types:
        return "Choose a valid resource type."
    if parse_int(capacity, max_val=MAX_CAPACITY) is None:
        return f"Capacity must be a whole number between 1 and {MAX_CAPACITY:,}."
    if str(is_active) not in ("0", "1"):
        return "Choose a valid status."
    return None
