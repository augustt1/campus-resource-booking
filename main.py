# main.py
# ------------------------------------------------------------
# Routes only. Data access -> db.py, aggregation -> analytics.py,
# presentation -> ui.py.
# Run: python main.py  ->  http://localhost:8080
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
from analytics import kpis, bookings_by_type, weekly_trend, most_booked, by_building, _hours
from ui import (
    Page, Card, Alert, Empty, StatsRow, StatItem, StatusBadge, Cell, DataTable,
    Field, SelectField, TextArea_, ListingCard, BarChart, LineChart,
)

init_db()
app, rt = fast_app(hdrs=())


# ---------------- Dashboard ----------------
@rt("/")
def get(msg: str = "", kind: str = "info"):
    k = kpis()
    up = list_bookings(upcoming=True, limit=6)
    rows = [
        Tr(Cell(b["resource_name"], f'{b["building"]} · {b["room_code"]}'),
           Td(datetime.fromisoformat(b["booking_date"]).strftime("%a %d %b %Y")),
           Td(f'{b["start_time"]}–{b["end_time"]}'),
           Td(b["user_name"]))
        for b in up
    ]
    popular = [
        ListingCard(
            TYPE_ICON.get(r["resource_type"], "📦"), r["resource_name"],
            f'{r["building"]} · {r["room_code"]} · {r["capacity"]} capacity',
            r["notes"] or "No additional notes recorded.",
            f'{r["hours"]:g} hours booked',
            actions=[A("View availability", href=f'/availability?rtype={r["resource_type"]}', cls="btn btn-ghost btn-sm")],
        )
        for r in most_booked(3)
    ]
    return Page(
        "Dashboard", "Service-wide reservation overview.",
        Alert(msg, kind),
        StatsRow(
            StatItem("📅", k["total_bookings"], label="Total bookings", note=f'{k["period_from"]} → {k["period_to"]}'),
            StatItem("📈", k["utilisation_rate"], "%", "Utilisation", f'{k["booked_hours"]:g} hrs booked', tone="ok"),
            StatItem("⚠️", k["cancellation_rate"], "%", "Cancellations", f'{k["cancelled_bookings"]} bookings',
                     tone="warn" if k["cancellation_rate"] > 12 else ""),
            StatItem("🚫", k["no_show_rate"], "%", "No-shows", f'{k["no_show_bookings"]} bookings',
                     tone="risk" if k["no_show_rate"] > 8 else ""),
        ),
        Card("Weekly booking trend", LineChart(weekly_trend(8)), hint="Last 8 weeks"),
        Card("Upcoming bookings", DataTable(["Resource", "Date", "Time", "Booked by"], rows,
                                             "No upcoming bookings. Create one from the Bookings page."), flush=True),
        Card("Most in-demand resources", Div(*popular, cls="listing-grid") if popular else Empty("No data yet")),
        active="/",
        actions=[A("＋ New booking", href="/bookings/new", cls="btn btn-primary"),
                 A("Check availability", href="/availability", cls="btn btn-ghost")],
    )


# ---------------- Resources ----------------
@rt("/resources")
def get(msg: str = "", kind: str = "info", rtype: str = ""):
    rows = [
        Tr(Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', r["building"] or "—"),
           Td(r["resource_type"]), Td(r["room_code"]), Td(r["capacity"]),
           Td(StatusBadge("confirmed") if r["is_active"] else StatusBadge("inactive")),
           Td(A("Edit", href=f'/resources/{r["resource_id"]}/edit', cls="btn btn-ghost btn-sm"),
              Form(Button("Delete", cls="btn btn-danger btn-sm"),
                   method="post", action=f'/resources/{r["resource_id"]}/delete', style="display:inline")))
        for r in list_resources(rtype=rtype)
    ]
    return Page(
        "Resources", "Manage bookable campus resources.",
        Alert(msg, kind),
        Card("Filter", Form(SelectField("rtype", TYPES, "Type", value=rtype, blank="All types"),
                             Button("Apply", cls="btn btn-ghost"), method="get", action="/resources")),
        Card("All resources", DataTable(["Name", "Type", "Room", "Capacity", "Status", ""], rows,
                                         "No resources match this filter.")),
        active="/resources",
        actions=[A("＋ New resource", href="/resources/new", cls="btn btn-primary")],
    )


def _resource_form(r=None, action="/resources/new"):
    g = (lambda k, d="": r[k] if r else d)
    return Form(
        Div(
            Field("resource_name", "Name", value=g("resource_name")),
            SelectField("resource_type", TYPES, "Type", value=g("resource_type")),
            Field("building", "Building", value=g("building")),
            Field("room_code", "Room / code", value=g("room_code")),
            Field("capacity", "Capacity", type="number", value=g("capacity", 1), min="1"),
            SelectField("is_active", [("1", "Active"), ("0", "Inactive")], "Status", value=str(g("is_active", 1))),
            TextArea_("notes", "Notes", value=g("notes")),
            cls="form-grid",
        ),
        Button("Save", cls="btn btn-primary", style="margin-top:18px"),
        A("Cancel", href="/resources", cls="btn btn-ghost", style="margin-top:18px;margin-left:8px"),
        method="post", action=action,
    )


@rt("/resources/new")
def get():
    return Page("New resource", "Add a bookable item.", Card("Resource details", _resource_form()), active="/resources")


@rt("/resources/new")
def post(resource_name: str, resource_type: str, capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    if not resource_name.strip():
        return RedirectResponse("/resources?msg=Resource+name+is+required&kind=error", status_code=303)
    create_resource(resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     max(capacity, 1), notes.strip(), int(is_active))
    return RedirectResponse("/resources?msg=Resource+created&kind=ok", status_code=303)


@rt("/resources/{rid}/edit")
def get(rid: int):
    r = get_resource(rid)
    if not r:
        return RedirectResponse("/resources?msg=Resource+not+found&kind=error", status_code=303)
    return Page(f'Edit "{r["resource_name"]}"', "Update resource details.",
                Card("Resource details", _resource_form(r, f"/resources/{rid}/edit")), active="/resources")


@rt("/resources/{rid}/edit")
def post(rid: int, resource_name: str, resource_type: str, capacity: int = 1,
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    update_resource(rid, resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     max(capacity, 1), notes.strip(), int(is_active))
    return RedirectResponse("/resources?msg=Resource+updated&kind=ok", status_code=303)


@rt("/resources/{rid}/delete")
def post(rid: int):
    delete_resource(rid)
    return RedirectResponse("/resources?msg=Resource+deleted&kind=ok", status_code=303)


# ---------------- Bookings ----------------
@rt("/bookings")
def get(msg: str = "", kind: str = "info"):
    up = list_bookings(upcoming=True)
    past = list_bookings(upcoming=False, limit=15)

    def row(b, show_actions=True):
        actions = []
        if show_actions and b["status"] == "confirmed":
            actions = [
                Form(Button("Cancel", cls="btn btn-danger btn-sm"), method="post",
                     action=f'/bookings/{b["booking_id"]}/status?to=cancelled', style="display:inline"),
                Form(Button("Complete", cls="btn btn-ghost btn-sm"), method="post",
                     action=f'/bookings/{b["booking_id"]}/status?to=completed', style="display:inline"),
            ]
        return Tr(Cell(b["resource_name"], f'{b["building"]} · {b["room_code"]}'),
                  Td(datetime.fromisoformat(b["booking_date"]).strftime("%a %d %b %Y")),
                  Td(f'{b["start_time"]}–{b["end_time"]}'),
                  Cell(b["user_name"], b["purpose"]),
                  Td(StatusBadge(b["status"])),
                  Td(*actions))

    return Page(
        "Bookings", "All reservations across the estate.",
        Alert(msg, kind),
        Card("Upcoming", DataTable(["Resource", "Date", "Time", "Booked by", "Status", ""],
                                    [row(b) for b in up], "No upcoming bookings yet.")),
        Card("Recent history", DataTable(["Resource", "Date", "Time", "Booked by", "Status", ""],
                                          [row(b, show_actions=False) for b in past],
                                          "No past bookings."), hint="Last 15", flush=True),
        active="/bookings",
        actions=[A("＋ New booking", href="/bookings/new", cls="btn btn-primary")],
    )


@rt("/bookings/new")
def get(msg: str = "", kind: str = "info", resource_id: str = ""):
    options = [(r["resource_id"], f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]} ({r["room_code"]})')
               for r in list_resources(active_only=True)]
    form = Form(
        Div(
            SelectField("resource_id", options, "Resource", value=resource_id),
            Field("user_name", "Your name"),
            Field("booking_date", "Date", type="date", value=date.today().isoformat()),
            Field("start_time", "Start time", type="time", value="09:00",
                  help_text=f"Campus hours {OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00"),
            Field("end_time", "End time", type="time", value="11:00"),
            TextArea_("purpose", "Purpose"),
            cls="form-grid",
        ),
        Button("Confirm booking", cls="btn btn-primary", style="margin-top:18px"),
        A("Cancel", href="/bookings", cls="btn btn-ghost", style="margin-top:18px;margin-left:8px"),
        method="post", action="/bookings/new",
    )
    return Page("New booking", "Reserve a room, lab, or item.", Alert(msg, kind), Card("Booking details", form),
                active="/bookings")


@rt("/bookings/new")
def post(resource_id: int, user_name: str, booking_date: str,
         start_time: str, end_time: str, purpose: str = ""):
    err = None
    if not user_name.strip():
        err = "Your name is required."
    elif end_time <= start_time:
        err = "End time must be after start time."
    elif not (f"{OPEN_HOUR:02d}:00" <= start_time and end_time <= f"{CLOSE_HOUR:02d}:00"):
        err = f"Booking must be within campus hours ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)."
    elif booking_date < date.today().isoformat():
        err = "Booking date cannot be in the past."
    elif has_clash(resource_id, booking_date, start_time, end_time):
        err = "This resource is already booked for that time slot."

    if err:
        return RedirectResponse(f"/bookings/new?msg={quote_plus(err)}&kind=error", status_code=303)

    create_booking(resource_id, user_name.strip(), booking_date, start_time, end_time, purpose.strip())
    return RedirectResponse("/bookings?msg=Booking+confirmed&kind=ok", status_code=303)


@rt("/bookings/{bid}/status")
def post(bid: int, to: str = "cancelled"):
    if to in STATUSES:
        set_booking_status(bid, to)
    return RedirectResponse(f"/bookings?msg=Booking+marked+{to}&kind=ok", status_code=303)


# ---------------- Availability ----------------
@rt("/availability")
def get(d: str = "", rtype: str = ""):
    d = d or date.today().isoformat()
    rows = []
    for r in list_resources(active_only=True, rtype=rtype):
        slots = slots_for(r["resource_id"], d)
        used = sum(_hours(s["start_time"], s["end_time"]) for s in slots)
        badges = [Span(f'{s["start_time"]}–{s["end_time"]} · {s["user_name"]}', cls="slot") for s in slots] or \
                 [Span(f"Free all day ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)", cls="slot free")]
        rows.append(Tr(
            Cell(f'{TYPE_ICON.get(r["resource_type"], "📦")} {r["resource_name"]}', f'{r["building"]} · {r["room_code"]}'),
            Td(*badges),
            Td(f'{(CLOSE_HOUR - OPEN_HOUR) - used:g} hrs free'),
            Td(A("Book", href=f'/bookings/new?resource_id={r["resource_id"]}', cls="btn btn-primary btn-sm")),
        ))
    pretty = datetime.fromisoformat(d).strftime("%A %d %B %Y")
    return Page(
        "Availability", f"Live availability for {pretty}.",
        Card("Filter", Form(
            Field("d", "Date", type="date", value=d),
            SelectField("rtype", TYPES, "Type", value=rtype, blank="All types"),
            Div(Button("Search", cls="btn btn-primary"), style="align-self:flex-end"),
            method="get", action="/availability", cls="filters",
        )),
        Card("Resources", DataTable(["Resource", "Booked slots", "Free hours", ""], rows,
                                     "No resources match this filter.")),
        active="/availability",
    )


# ---------------- Reports ----------------
@rt("/reports")
def get():
    k = kpis()
    bld_rows = [
        Tr(Td(b["label"] or "—"), Td(b["value"]), Td(b["cancelled"]),
           Td(f'{round((b["cancelled"] / b["value"]) * 100) if b["value"] else 0}%'))
        for b in by_building()
    ]
    return Page(
        "Reports", "Service-level analytics for the last 30 days.",
        StatsRow(
            StatItem("📅", k["total_bookings"], label="Total bookings", note=f'{k["period_from"]} → {k["period_to"]}'),
            StatItem("⏱️", k["booked_hours"], label="Hours booked"),
            StatItem("📈", k["utilisation_rate"], "%", "Utilisation"),
            StatItem("🚫", k["no_show_rate"], "%", "No-show rate", f'{k["no_show_bookings"]} bookings'),
        ),
        Card("Bookings by resource type", BarChart(bookings_by_type())),
        Card("Weekly booking trend", LineChart(weekly_trend(8)), hint="Last 8 weeks"),
        Card("By building", DataTable(["Building", "Bookings", "Cancelled", "Cancel %"], bld_rows,
                                       "No booking data yet.")),
        active="/reports",
    )


# ---------------- Entry point ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    is_cloud = "PORT" in os.environ
    serve(host="0.0.0.0", port=port, reload=not is_cloud)