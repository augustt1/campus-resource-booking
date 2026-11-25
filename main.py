# main.py
# ------------------------------------------------------------
# Application entry point and route handlers.
# Role-based access control: "student" (default) vs "staff".
# No real login/password — role is chosen via a simple switcher
# stored in the session (documented as a design trade-off).
# ------------------------------------------------------------
import os
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

init_db()
app, rt = fast_app(hdrs=())


def _hours(s, e):
    t0 = datetime.strptime(s, "%H:%M")
    t1 = datetime.strptime(e, "%H:%M")
    return max((t1 - t0).total_seconds() / 3600, 0)


def staff_only(session, redirect_to="/"):
    if not is_staff(session):
        msg = quote_plus("Staff access only.")
        return RedirectResponse(f"{redirect_to}?msg={msg}&kind=error", status_code=303)
    return None


# ---------------- Role switcher ----------------
@rt("/role/{role}")
def get(role: str, session, next: str = "/"):
    if role in ("student", "staff"):
        session["role"] = role
    return RedirectResponse(next or "/", status_code=303)


# ---------------- Dashboard ----------------
@rt("/")
def get(session, msg: str = "", kind: str = "info"):
    role = session.get("role", "student")
    k = kpis()
    upcoming = list_bookings(upcoming=True, limit=6)
    rows = [
        Tr(Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
           Td(datetime.fromisoformat(b["booking_date"]).strftime("%a %d %b %Y")),
           Td(f'{b["start_time"]}–{b["end_time"]}'),
           Td(b["user_name"]))
        for b in upcoming
    ]
    popular_cards = [
        ListingCard(
            icon=TYPE_ICON.get(r["resource_type"], "📦"),
            title=r["resource_name"],
            meta=f'{r["building"]} {r["room_code"]}',
            body=f'{r["hours"]:g} hours booked recently',
            action=A("Check availability", href=f'/availability?rtype={r["resource_type"]}', cls="btn btn-ghost btn-sm"),
        )
        for r in most_booked(3)
    ]

    blocks = [Alert(msg, kind)] if msg else []

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
        blocks.append(Card("Weekly booking trend", LineChart(weekly_trend(8)), hint="Last 8 weeks"))

    blocks.append(Card("My upcoming bookings",
                        DataTable(["Resource", "Date", "Time", "Booked by"], rows,
                                   empty_msg="No upcoming bookings yet."), flush=True))
    blocks.append(Card("Most in-demand resources", Div(*popular_cards, cls="listing-grid")))

    return Page(
        "Dashboard", *blocks,
        subtitle="Service-wide overview and your bookings, all on one page.",
        active="/", role=role,
        actions=[A("+ New booking", href="/bookings/new", cls="btn btn-primary"),
                 A("Check availability", href="/availability", cls="btn btn-ghost")],
    )


# ---------------- Resources ----------------
@rt("/resources")
def get(session, msg: str = "", kind: str = "info", rtype: str = ""):
    role = session.get("role", "student")
    staff = is_staff(session)
    resources = list_resources(rtype=rtype)

    def row(r):
        cells = [
            Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', r["notes"] or ""),
            Td(r["resource_type"]), Td(r["room_code"]), Td(r["capacity"]),
            Td(StatusBadge("confirmed" if r["is_active"] else "inactive")),
        ]
        if staff:
            cells.append(Td(
                A("Edit", href=f'/resources/{r["resource_id"]}/edit', cls="btn btn-ghost btn-sm"),
                Form(Button("Delete", cls="btn btn-danger btn-sm"),
                     method="post", action=f'/resources/{r["resource_id"]}/delete', style="display:inline"),
            ))
        return Tr(*cells)

    headers = ["Resource", "Type", "Room", "Capacity", "Status"] + (["Actions"] if staff else [])
    rows = [row(r) for r in resources]

    blocks = [Alert(msg, kind)] if msg else []
    blocks.append(Form(SelectField("rtype", TYPES, value=rtype, blank="All types"),
                        Button("Filter", cls="btn btn-ghost"),
                        cls="filters", method="get", action="/resources"))
    blocks.append(Card("All resources", DataTable(headers, rows, empty_msg="No resources match that filter."), flush=True))

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


@rt("/resources/new")
def get(session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    return Page("New resource", Card("Add a new bookable item", _resource_form()), active="/resources", role="staff")


@rt("/resources/new")
def post(session, resource_name: str, resource_type: str, capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if not resource_name.strip():
        return RedirectResponse("/resources?msg=Resource+name+is+required&kind=error", status_code=303)
    create_resource(resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     capacity, notes.strip(), int(is_active))
    return RedirectResponse("/resources?msg=Resource+created&kind=ok", status_code=303)


@rt("/resources/{rid}/edit")
def get(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    r = get_resource(rid)
    if not r:
        return RedirectResponse("/resources?msg=Resource+not+found&kind=error", status_code=303)
    return Page(f'Edit "{r["resource_name"]}"', Card("Update details", _resource_form(r, f"/resources/{rid}/edit")),
                active="/resources", role="staff")


@rt("/resources/{rid}/edit")
def post(rid: int, session, resource_name: str, resource_type: str, capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    update_resource(rid, resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     capacity, notes.strip(), int(is_active))
    return RedirectResponse("/resources?msg=Resource+updated&kind=ok", status_code=303)


@rt("/resources/{rid}/delete")
def post(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    delete_resource(rid)
    return RedirectResponse("/resources?msg=Resource+deleted&kind=ok", status_code=303)


# ---------------- Bookings ----------------
@rt("/bookings")
def get(session, msg: str = "", kind: str = "info"):
    role = session.get("role", "student")
    staff = is_staff(session)
    upcoming = list_bookings(upcoming=True)
    history = list_bookings(upcoming=False, limit=15)

    def row(b, show_actions):
        cells = [
            Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
            Td(datetime.fromisoformat(b["booking_date"]).strftime("%a %d %b %Y")),
            Td(f'{b["start_time"]}–{b["end_time"]}'),
            Cell(b["user_name"], b["purpose"] or ""),
            Td(StatusBadge(b["status"])),
        ]
        if show_actions and staff:
            if b["status"] == "confirmed":
                cells.append(Td(
                    Form(Button("Cancel", cls="btn btn-danger btn-sm"), method="post",
                         action=f'/bookings/{b["booking_id"]}/status?to=cancelled', style="display:inline"),
                    Form(Button("Complete", cls="btn btn-ghost btn-sm"), method="post",
                         action=f'/bookings/{b["booking_id"]}/status?to=completed', style="display:inline"),
                ))
            else:
                cells.append(Td(""))
        return Tr(*cells)

    up_headers = ["Resource", "Date", "Time", "Booked by", "Status"] + (["Actions"] if staff else [])
    hist_headers = ["Resource", "Date", "Time", "Booked by", "Status"]

    blocks = [Alert(msg, kind)] if msg else []
    blocks.append(Card("Upcoming bookings",
                        DataTable(up_headers, [row(b, True) for b in upcoming], empty_msg="No upcoming bookings."),
                        flush=True))
    blocks.append(Card("Recent history",
                        DataTable(hist_headers, [row(b, False) for b in history], empty_msg="No past bookings yet."),
                        hint="Last 15", flush=True))

    return Page("Bookings", *blocks, subtitle="All reservations across the campus estate.",
                active="/bookings", role=role,
                actions=[A("+ New booking", href="/bookings/new", cls="btn btn-primary")])


@rt("/bookings/new")
def get(session, msg: str = "", kind: str = "error", resource_id: str = ""):
    role = session.get("role", "student")
    options = [(r["resource_id"], f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]} ({r["room_code"]})')
               for r in list_resources(active_only=True)]
    form = Form(
        Div(
            SelectField("resource_id", options, value=resource_id),
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
    blocks = [Alert(msg, kind)] if msg else []
    blocks.append(Card("Book an item", form))
    return Page("New booking", *blocks, active="/bookings", role=role)


@rt("/bookings/new")
def post(session, resource_id: int, user_name: str, booking_date: str,
         start_time: str, end_time: str, purpose: str = ""):
    err = None
    if not user_name.strip():
        err = "Your name is required."
    elif end_time <= start_time:
        err = "End time must be after start time."
    elif not (f"{OPEN_HOUR:02d}:00" <= start_time and end_time <= f"{CLOSE_HOUR:02d}:00"):
        err = f"Bookings must fall within campus hours ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)."
    elif booking_date < date.today().isoformat():
        err = "Booking date cannot be in the past."
    elif has_clash(resource_id, booking_date, start_time, end_time):
        err = "That resource is already booked for this time slot."

    if err:
        return RedirectResponse(f"/bookings/new?msg={quote_plus(err)}&kind=error", status_code=303)

    create_booking(resource_id, user_name.strip(), booking_date, start_time, end_time, purpose.strip())
    return RedirectResponse("/bookings?msg=Booking+confirmed&kind=ok", status_code=303)


@rt("/bookings/{bid}/status")
def post(bid: int, session, to: str = "cancelled"):
    guard = staff_only(session, "/bookings")
    if guard:
        return guard
    if to not in STATUSES:
        to = "cancelled"
    set_booking_status(bid, to)
    return RedirectResponse(f"/bookings?msg=Booking+marked+{to}&kind=ok", status_code=303)


# ---------------- Availability ----------------
@rt("/availability")
def get(session, d: str = "", rtype: str = ""):
    role = session.get("role", "student")
    d = d or date.today().isoformat()
    rows = []
    for r in list_resources(active_only=True, rtype=rtype):
        slots = slots_for(r["resource_id"], d)
        used = sum(_hours(s["start_time"], s["end_time"]) for s in slots)
        slot_spans = [Span(f'{s["start_time"]}–{s["end_time"]} {s["user_name"]}', cls="slot") for s in slots]
        if not slot_spans:
            slot_spans = [Span(f"Free all day ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)", cls="slot free")]
        rows.append(Tr(
            Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', f'{r["building"]} {r["room_code"]}'),
            Td(*slot_spans),
            Td(f'{(CLOSE_HOUR - OPEN_HOUR) - used:g} hrs free'),
            Td(A("Book", href=f'/bookings/new?resource_id={r["resource_id"]}', cls="btn btn-primary btn-sm")),
        ))

    form = Form(
        Field("d", value=d),
        SelectField("rtype", TYPES, value=rtype, blank="All types"),
        Button("Search", cls="btn btn-primary", style="align-self:flex-end"),
        cls="filters", method="get", action="/availability",
    )
    pretty = datetime.fromisoformat(d).strftime("%A %d %B %Y")
    return Page(
        "Availability", Card("Filters", form),
        Card(f"Resources on {pretty}", DataTable(["Resource", "Booked slots", "Free hours", ""], rows,
                                                    empty_msg="No active resources match that filter.")),
        subtitle="Check free and booked slots by date.",
        active="/availability", role=role,
    )


# ---------------- Reports (staff only) ----------------
@rt("/reports")
def get(session):
    guard = staff_only(session, "/")
    if guard:
        return guard
    k = kpis()
    bld_rows = [
        Tr(Td(b["building"]), Td(b["n"]), Td(b["cancelled"]),
           Td(f'{round((b["cancelled"] / b["n"]) * 100) if b["n"] else 0}%'))
        for b in by_building()
    ]
    return Page(
        "Reports",
        Card("Service-level KPIs",
             StatsRow(
                 StatItem("📅", k["total_bookings"], label="Total bookings",
                           note=f'{k["period_from"]} – {k["period_to"]}'),
                 StatItem("⏱️", k["booked_hours"], label="Booked hours"),
                 StatItem("📈", k["utilisation_rate"], unit="%", label="Utilisation"),
                 StatItem("❓", k["no_show_rate"], unit="%", label="No-show rate",
                           note=f'{k["no_show_bookings"]} not attended'),
             ), hint="Last 30 days"),
        Card("Bookings by resource type", BarChart(bookings_by_type())),
        Card("Weekly trend", LineChart(weekly_trend(8)), hint="Last 8 weeks"),
        Card("By building", DataTable(["Building", "Bookings", "Cancelled", "Cancel %"], bld_rows,
                                        empty_msg="No data yet."), flush=True),
        subtitle="Service-level analytics for the last 30 days.",
        active="/reports", role="staff",
    )


# ---------------- Entry point ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    is_cloud = "PORT" in os.environ
    serve(host="0.0.0.0", port=port, reload=not is_cloud)