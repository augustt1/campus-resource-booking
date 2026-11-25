# main.py
# ------------------------------------------------------------
# Application entry point and route handlers.
# Role-based access control: "student" (default) vs "staff".
# No real login/password — role is chosen via a simple switcher
# stored in the session (documented as a design trade-off).
# ------------------------------------------------------------
import logging
import os
import re
from datetime import date, datetime
from urllib.parse import quote_plus

from fasthtml.common import *

from db import (
    init_db, TYPES, OPEN_HOUR, CLOSE_HOUR, STATUSES, TYPE_ICON,
    list_resources, get_resource, create_resource, update_resource, delete_resource,
    list_bookings, get_booking, has_clash, create_booking, set_booking_status, slots_for,
)
from analytics import kpis, bookings_by_type, weekly_trend, most_booked, by_building
from ui import (
    Page, Alert, Empty, Card, StatItem, StatsRow, StatusBadge, Cell, DataTable,
    Field, SelectField, TextArea_, ListingCard, BarChart, LineChart, is_staff,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialise database/storage safely at startup
try:
    init_db()
except Exception as exc:
    logger.exception("Failed to initialise database on startup: %s", exc)

app, rt = fast_app(hdrs=())

TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def _redirect_msg(path: str, msg: str, kind: str = "error") -> RedirectResponse:
    sep = "&" if "?" in path else "?"
    return RedirectResponse(f"{path}{sep}msg={quote_plus(msg)}&kind={quote_plus(kind)}", status_code=303)


def _parse_iso_date(raw: str, fallback: date | None = None) -> date | None:
    if not raw or not isinstance(raw, str):
        return fallback
    try:
        return date.fromisoformat(raw.strip())
    except ValueError:
        return fallback


def _parse_hhmm(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    val = raw.strip()
    if not TIME_RE.match(val):
        return None
    return val


def _parse_positive_int(raw, default: int | None = None, min_val: int = 1, max_val: int = 100_000) -> int | None:
    if raw is None or raw == "":
        return default
    try:
        num = int(raw)
    except (TypeError, ValueError):
        return default
    if num < min_val or num > max_val:
        return default
    return num


def _hours(s, e):
    try:
        t0 = datetime.strptime(s, "%H:%M")
        t1 = datetime.strptime(e, "%H:%M")
        return max((t1 - t0).total_seconds() / 3600, 0)
    except Exception:
        return 0.0


def _format_display_date(iso_str: str, fmt: str = "%a %d %b %Y") -> str:
    try:
        return datetime.fromisoformat(iso_str).strftime(fmt)
    except Exception:
        return str(iso_str)


def staff_only(session, redirect_to="/"):
    if not is_staff(session):
        return _redirect_msg(redirect_to, "Staff access only.", "error")
    return None


# ---------------- Role switcher ----------------
@rt("/role/{role}")
def get(role: str, session, next: str = "/"):
    if role in ("student", "staff"):
        session["role"] = role
    # Prevent open redirects by ensuring `next` is a relative local path
    safe_next = next if (isinstance(next, str) and next.startswith("/") and not next.startswith("//")) else "/"
    return RedirectResponse(safe_next, status_code=303)


# ---------------- Dashboard ----------------
@rt("/")
def get(session, msg: str = "", kind: str = "info"):
    role = session.get("role", "student")
    safe_kind = kind if kind in ("info", "ok", "warn", "error") else "info"

    try:
        k = kpis()
        upcoming = list_bookings(upcoming=True, limit=6)
        popular = most_booked(3)
        trend = weekly_trend(8)
    except Exception as exc:
        logger.exception("Dashboard data load failed: %s", exc)
        return Page(
            "Dashboard",
            Alert("Unable to load dashboard data right now. Please try again later.", "error"),
            subtitle="Service-wide overview and your bookings, all on one page.",
            active="/", role=role,
        )

    rows = [
        Tr(
            Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
            Td(_format_display_date(b["booking_date"])),
            Td(f'{b["start_time"]}–{b["end_time"]}'),
            Td(b["user_name"]),
        )
        for b in upcoming
    ]
    popular_cards = [
        ListingCard(
            icon=TYPE_ICON.get(r["resource_type"], "📦"),
            title=r["resource_name"],
            meta=f'{r["building"]} {r["room_code"]}',
            body=f'{r["hours"]:g} hours booked recently',
            action=A("Check availability", href=f'/availability?rtype={quote_plus(r["resource_type"])}', cls="btn btn-ghost btn-sm"),
        )
        for r in popular
    ]

    blocks = [Alert(msg, safe_kind)] if msg else []

    if is_staff(session):
        blocks.append(Card(
            "Service overview",
            StatsRow(
                StatItem("📅", k["total_bookings"], label="Total bookings",
                         note=f'{k["period_from"]} – {k["period_to"]}'),
                StatItem("📈", k["utilisation_rate"], unit="%", label="Utilisation",
                         note=f'{k["booked_hours"]:g} hours'),
                StatItem("↩️", k["cancellation_rate"], unit="%", label="Cancellation rate",
                         note=f'{k["cancelled_bookings"]} cancelled',
                         tone="warn" if k["cancellation_rate"] > 12 else ""),
                StatItem("❓", k["no_show_rate"], unit="%", label="No-show rate",
                         note=f'{k["no_show_bookings"]} not attended',
                         tone="warn" if k["no_show_rate"] > 8 else ""),
            ),
            hint="Last 30 days",
        ))
        blocks.append(Card("Weekly booking trend", LineChart(trend), hint="Last 8 weeks"))

    blocks.append(Card("My upcoming bookings",
                       DataTable(["Resource", "Date", "Time", "Booked by"], rows,
                                 empty_msg="No upcoming bookings yet."), flush=True))
    blocks.append(Card("Most in-demand resources", Div(*popular_cards, cls="listing-grid")))

    return Page(
        "Dashboard", *blocks,
        subtitle="Service-wide overview and your bookings, all on one page.",
        active="/", role=role,
        actions=[
            A("+ New booking", href="/bookings/new", cls="btn btn-primary"),
            A("Check availability", href="/availability", cls="btn btn-ghost"),
        ],
    )


# ---------------- Resources ----------------
@rt("/resources")
def get(session, msg: str = "", kind: str = "info", rtype: str = ""):
    role = session.get("role", "student")
    staff = is_staff(session)
    safe_kind = kind if kind in ("info", "ok", "warn", "error") else "info"
    valid_types = {t[0] if isinstance(t, (tuple, list)) else t for t in TYPES}
    clean_rtype = rtype if rtype in valid_types else ""

    try:
        resources = list_resources(rtype=clean_rtype)
    except Exception as exc:
        logger.exception("Failed to list resources: %s", exc)
        return Page(
            "Resources",
            Alert("Could not load resources due to a storage error.", "error"),
            subtitle="Browse all bookable resources on campus.",
            active="/resources", role=role,
        )

    def row(r):
        cells = [
            Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', r["notes"] or ""),
            Td(r["resource_type"]), Td(r["room_code"]), Td(r["capacity"]),
            Td(StatusBadge("confirmed" if r["is_active"] else "inactive")),
        ]
        if staff:
            cells.append(Td(
                A("Edit", href=f'/resources/{r["resource_id"]}/edit', cls="btn btn-ghost btn-sm"),
                Form(
                    Button("Delete", cls="btn btn-danger btn-sm"),
                    method="post", action=f'/resources/{r["resource_id"]}/delete',
                    style="display:inline",
                ),
            ))
        return Tr(*cells)

    headers = ["Resource", "Type", "Room", "Capacity", "Status"] + (["Actions"] if staff else [])
    rows = [row(r) for r in resources]

    blocks = [Alert(msg, safe_kind)] if msg else []
    if rtype and not clean_rtype:
        blocks.append(Alert("Unknown resource type filter ignored; showing all types.", "warn"))

    blocks.append(Form(
        SelectField("rtype", TYPES, value=clean_rtype, blank="All types"),
        Button("Filter", cls="btn btn-ghost"),
        cls="filters", method="get", action="/resources",
    ))
    blocks.append(Card(
        "All resources",
        DataTable(headers, rows, empty_msg="No resources match that filter."),
        flush=True,
    ))

    return Page(
        "Resources", *blocks,
        subtitle="Browse all bookable resources on campus.",
        active="/resources", role=role,
        actions=[A("+ Add resource", href="/resources/new", cls="btn btn-primary")] if staff else None,
    )


def _resource_form(r=None, action="/resources/new"):
    g = (lambda k, d="": r[k]) if r else (lambda k, d="": d)
    return Form(
        Div(
            Field("resource_name", value=g("resource_name")),
            SelectField("resource_type", TYPES, value=g("resource_type")),
            Field("building", value=g("building")),
            Field("room_code", value=g("room_code")),
            Field("capacity", value=g("capacity", 1)),
            SelectField("is_active", [("1", "Active"), ("0", "Inactive")], value=str(g("is_active", 1))),
            TextArea_("notes", value=g("notes")),
            cls="form-grid",
        ),
        Button("Save", cls="btn btn-primary", style="margin-top:18px"),
        A("Cancel", href="/resources", cls="btn btn-ghost", style="margin-top:18px;margin-left:8px"),
        method="post", action=action,
    )


def _validate_resource_payload(resource_name: str, resource_type: str, capacity, is_active: str):
    valid_types = {t[0] if isinstance(t, (tuple, list)) else t for t in TYPES}
    cap = _parse_positive_int(capacity, default=None, min_val=1, max_val=10_000)
    if not resource_name or not resource_name.strip():
        return "Resource name is required."
    if len(resource_name.strip()) > 120:
        return "Resource name must be 120 characters or fewer."
    if resource_type not in valid_types:
        return "Invalid resource type selected."
    if cap is None:
        return "Capacity must be a positive whole number (1–10,000)."
    if str(is_active) not in ("0", "1"):
        return "Invalid active status."
    return None


@rt("/resources/new")
def get(session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    return Page("New resource", Card("Add a new bookable item", _resource_form()), active="/resources", role="staff")


@rt("/resources/new")
def post(session, resource_name: str = "", resource_type: str = "", capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard

    err = _validate_resource_payload(resource_name, resource_type, capacity, is_active)
    if err:
        return _redirect_msg("/resources", err, "error")

    try:
        create_resource(
            resource_name.strip(), resource_type, building.strip(), room_code.strip(),
            int(capacity), notes.strip(), int(is_active),
        )
    except Exception as exc:
        logger.exception("Failed to create resource: %s", exc)
        return _redirect_msg("/resources", "Could not save new resource due to a storage error.", "error")

    return _redirect_msg("/resources", "Resource created", "ok")


@rt("/resources/{rid}/edit")
def get(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if rid <= 0:
        return _redirect_msg("/resources", "Invalid resource ID.", "error")

    try:
        r = get_resource(rid)
    except Exception as exc:
        logger.exception("Failed to fetch resource %s: %s", rid, exc)
        return _redirect_msg("/resources", "Could not load resource due to a storage error.", "error")

    if not r:
        return _redirect_msg("/resources", "Resource not found", "error")

    return Page(
        f'Edit "{r["resource_name"]}"',
        Card("Update details", _resource_form(r, f"/resources/{rid}/edit")),
        active="/resources", role="staff",
    )


@rt("/resources/{rid}/edit")
def post(rid: int, session, resource_name: str = "", resource_type: str = "", capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if rid <= 0:
        return _redirect_msg("/resources", "Invalid resource ID.", "error")

    err = _validate_resource_payload(resource_name, resource_type, capacity, is_active)
    if err:
        return _redirect_msg("/resources", err, "error")

    try:
        update_resource(
            rid, resource_name.strip(), resource_type, building.strip(), room_code.strip(),
            int(capacity), notes.strip(), int(is_active),
        )
    except Exception as exc:
        logger.exception("Failed to update resource %s: %s", rid, exc)
        return _redirect_msg("/resources", "Could not update resource due to a storage error.", "error")

    return _redirect_msg("/resources", "Resource updated", "ok")


@rt("/resources/{rid}/delete")
def post(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if rid <= 0:
        return _redirect_msg("/resources", "Invalid resource ID.", "error")

    try:
        delete_resource(rid)
    except Exception as exc:
        logger.exception("Failed to delete resource %s: %s", rid, exc)
        return _redirect_msg("/resources", "Could not delete resource (it may have linked bookings).", "error")

    return _redirect_msg("/resources", "Resource deleted", "ok")


# ---------------- Bookings ----------------
@rt("/bookings")
def get(session, msg: str = "", kind: str = "info"):
    role = session.get("role", "student")
    staff = is_staff(session)
    safe_kind = kind if kind in ("info", "ok", "warn", "error") else "info"

    try:
        upcoming = list_bookings(upcoming=True)
        history = list_bookings(upcoming=False, limit=15)
    except Exception as exc:
        logger.exception("Failed to load bookings: %s", exc)
        return Page(
            "Bookings",
            Alert("Unable to load bookings right now due to a storage error.", "error"),
            subtitle="All reservations across the campus estate.",
            active="/bookings", role=role,
        )

    def row(b, show_actions):
        cells = [
            Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
            Td(_format_display_date(b["booking_date"])),
            Td(f'{b["start_time"]}–{b["end_time"]}'),
            Cell(b["user_name"], b["purpose"] or ""),
            Td(StatusBadge(b["status"])),
        ]
        if show_actions and staff:
            if b["status"] == "confirmed":
                cells.append(Td(
                    Form(
                        Button("Cancel", cls="btn btn-danger btn-sm"),
                        method="post", action=f'/bookings/{b["booking_id"]}/status?to=cancelled',
                        style="display:inline",
                    ),
                    Form(
                        Button("Complete", cls="btn btn-ghost btn-sm"),
                        method="post", action=f'/bookings/{b["booking_id"]}/status?to=completed',
                        style="display:inline",
                    ),
                ))
            else:
                cells.append(Td(""))
        return Tr(*cells)

    up_headers = ["Resource", "Date", "Time", "Booked by", "Status"] + (["Actions"] if staff else [])
    hist_headers = ["Resource", "Date", "Time", "Booked by", "Status"]

    blocks = [Alert(msg, safe_kind)] if msg else []
    blocks.append(Card(
        "Upcoming bookings",
        DataTable(up_headers, [row(b, True) for b in upcoming], empty_msg="No upcoming bookings."),
        flush=True,
    ))
    blocks.append(Card(
        "Recent history",
        DataTable(hist_headers, [row(b, False) for b in history], empty_msg="No past bookings yet."),
        hint="Last 15", flush=True,
    ))

    return Page(
        "Bookings", *blocks,
        subtitle="All reservations across the campus estate.",
        active="/bookings", role=role,
        actions=[A("+ New booking", href="/bookings/new", cls="btn btn-primary")],
    )


@rt("/bookings/new")
def get(session, msg: str = "", kind: str = "error", resource_id: str = ""):
    role = session.get("role", "student")
    safe_kind = kind if kind in ("info", "ok", "warn", "error") else "error"

    try:
        active_resources = list_resources(active_only=True)
    except Exception as exc:
        logger.exception("Failed to load active resources for booking form: %s", exc)
        return Page(
            "New booking",
            Alert("Unable to load bookable resources right now.", "error"),
            active="/bookings", role=role,
        )

    options = [
        (r["resource_id"], f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]} ({r["room_code"]})')
        for r in active_resources
    ]
    parsed_rid = _parse_positive_int(resource_id, default="")
    form = Form(
        Div(
            SelectField("resource_id", options, value=str(parsed_rid) if parsed_rid != "" else ""),
            Field("user_name", help_text="Your name or username"),
            Field("booking_date", value=date.today().isoformat()),
            Field("start_time", value="09:00", help_text=f"Campus open {OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00"),
            Field("end_time", value="11:00"),
            TextArea_("purpose"),
            cls="form-grid",
        ),
        Button("Confirm booking", cls="btn btn-primary", style="margin-top:18px"),
        A("Cancel", href="/bookings", cls="btn btn-ghost", style="margin-top:18px;margin-left:8px"),
        method="post", action="/bookings/new",
    )
    blocks = [Alert(msg, safe_kind)] if msg else []
    blocks.append(Card("Book an item", form))
    return Page("New booking", *blocks, active="/bookings", role=role)


@rt("/bookings/new")
def post(session, resource_id: int, user_name: str = "", booking_date: str = "",
         start_time: str = "", end_time: str = "", purpose: str = ""):
    parsed_rid = _parse_positive_int(resource_id, default=None)
    parsed_date = _parse_iso_date(booking_date)
    parsed_start = _parse_hhmm(start_time)
    parsed_end = _parse_hhmm(end_time)

    err = None
    if parsed_rid is None:
        err = "Please select a valid resource."
    elif not user_name or not user_name.strip():
        err = "Your name is required."
    elif len(user_name.strip()) > 100:
        err = "Name must be 100 characters or fewer."
    elif parsed_date is None:
        err = "Please enter a valid booking date (YYYY-MM-DD)."
    elif parsed_date.isoformat() < date.today().isoformat():
        err = "Booking date cannot be in the past."
    elif parsed_start is None or parsed_end is None:
        err = "Start and end times must be in valid HH:MM format."
    elif parsed_end <= parsed_start:
        err = "End time must be after start time."
    elif not (f"{OPEN_HOUR:02d}:00" <= parsed_start and parsed_end <= f"{CLOSE_HOUR:02d}:00"):
        err = f"Bookings must fall within campus hours ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)."
    elif len(purpose.strip()) > 300:
        err = "Purpose must be 300 characters or fewer."

    if err:
        return _redirect_msg("/bookings/new", err, "error")

    try:
        if has_clash(parsed_rid, parsed_date.isoformat(), parsed_start, parsed_end):
            return _redirect_msg("/bookings/new", "That resource is already booked for this time slot.", "error")
        create_booking(
            parsed_rid, user_name.strip(), parsed_date.isoformat(),
            parsed_start, parsed_end, purpose.strip(),
        )
    except Exception as exc:
        logger.exception("Failed to create booking: %s", exc)
        return _redirect_msg("/bookings/new", "Could not complete booking due to a storage error.", "error")

    return _redirect_msg("/bookings", "Booking confirmed", "ok")


@rt("/bookings/{bid}/status")
def post(bid: int, session, to: str = "cancelled"):
    guard = staff_only(session, "/bookings")
    if guard:
        return guard
    if bid <= 0:
        return _redirect_msg("/bookings", "Invalid booking ID.", "error")
    if to not in STATUSES:
        return _redirect_msg("/bookings", "Invalid booking status requested.", "error")

    try:
        set_booking_status(bid, to)
    except Exception as exc:
        logger.exception("Failed to update booking %s status to %s: %s", bid, to, exc)
        return _redirect_msg("/bookings", "Could not update booking status due to a storage error.", "error")

    return _redirect_msg("/bookings", f"Booking marked {to}", "ok")


# ---------------- Availability ----------------
@rt("/availability")
def get(session, d: str = "", rtype: str = ""):
    role = session.get("role", "student")
    parsed_d = _parse_iso_date(d, fallback=date.today())
    iso_d = parsed_d.isoformat()

    valid_types = {t[0] if isinstance(t, (tuple, list)) else t for t in TYPES}
    clean_rtype = rtype if rtype in valid_types else ""

    rows = []
    try:
        resources = list_resources(active_only=True, rtype=clean_rtype)
        for r in resources:
            slots = slots_for(r["resource_id"], iso_d)
            used = sum(_hours(s["start_time"], s["end_time"]) for s in slots)
            slot_spans = [Span(f'{s["start_time"]}–{s["end_time"]} {s["user_name"]}', cls="slot") for s in slots]
            if not slot_spans:
                slot_spans = [Span(f"Free all day ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)", cls="slot free")]
            rows.append(Tr(
                Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', f'{r["building"]} {r["room_code"]}'),
                Td(*slot_spans),
                Td(f'{max((CLOSE_HOUR - OPEN_HOUR) - used, 0):g} hrs free'),
                Td(A("Book", href=f'/bookings/new?resource_id={r["resource_id"]}', cls="btn btn-primary btn-sm")),
            ))
    except Exception as exc:
        logger.exception("Failed to load availability for %s: %s", iso_d, exc)
        return Page(
            "Availability",
            Alert("Unable to load slot availability due to a storage error.", "error"),
            subtitle="Check free and booked slots by date.",
            active="/availability", role=role,
        )

    form = Form(
        Field("d", value=iso_d),
        SelectField("rtype", TYPES, value=clean_rtype, blank="All types"),
        Button("Search", cls="btn btn-primary", style="align-self:flex-end"),
        cls="filters", method="get", action="/availability",
    )
    pretty = _format_display_date(iso_d, "%A %d %B %Y")
    notices = []
    if d and _parse_iso_date(d) is None:
        notices.append(Alert(f"Invalid date '{d}'; showing today ({pretty}).", "warn"))

    return Page(
        "Availability", *notices,
        Card("Filters", form),
        Card(
            f"Resources on {pretty}",
            DataTable(["Resource", "Booked slots", "Free hours", ""], rows,
                      empty_msg="No active resources match that filter."),
        ),
        subtitle="Check free and booked slots by date.",
        active="/availability", role=role,
    )


# ---------------- Reports (staff only) ----------------
@rt("/reports")
def get(session):
    guard = staff_only(session, "/")
    if guard:
        return guard

    try:
        k = kpis()
        bld_data = by_building()
        type_data = bookings_by_type()
        trend_data = weekly_trend(8)
    except Exception as exc:
        logger.exception("Failed to generate staff reports: %s", exc)
        return Page(
            "Reports",
            Alert("Unable to generate reports due to a data/storage error.", "error"),
            subtitle="Service-level analytics for the last 30 days.",
            active="/reports", role="staff",
        )

    bld_rows = [
        Tr(
            Td(b["building"]),
            Td(b["n"]),
            Td(b["cancelled"]),
            Td(f'{round((b["cancelled"] / b["n"]) * 100) if b["n"] else 0}%'),
        )
        for b in bld_data
    ]
    return Page(
        "Reports",
        Card(
            "Service-level KPIs",
            StatsRow(
                StatItem("📅", k["total_bookings"], label="Total bookings",
                         note=f'{k["period_from"]} – {k["period_to"]}'),
                StatItem("⏱️", k["booked_hours"], label="Booked hours"),
                StatItem("📈", k["utilisation_rate"], unit="%", label="Utilisation"),
                StatItem("❓", k["no_show_rate"], unit="%", label="No-show rate",
                         note=f'{k["no_show_bookings"]} not attended'),
            ),
            hint="Last 30 days",
        ),
        Card("Bookings by resource type", BarChart(type_data)),
        Card("Weekly trend", LineChart(trend_data), hint="Last 8 weeks"),
        Card(
            "By building",
            DataTable(["Building", "Bookings", "Cancelled", "Cancel %"], bld_rows,
                      empty_msg="No data yet."),
            flush=True,
        ),
        subtitle="Service-level analytics for the last 30 days.",
        active="/reports", role="staff",
    )


# ---------------- Entry point ----------------
if __name__ == "__main__":
    raw_port = os.environ.get("PORT", "8080")
    port = _parse_positive_int(raw_port, default=8080, min_val=1, max_val=65535)
    is_cloud = "PORT" in os.environ
    try:
        serve(host="0.0.0.0", port=port, reload=not is_cloud)
    except Exception as exc:
        logger.exception("Application server failed to start on port %s: %s", port, exc)
        raise