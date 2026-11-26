# main.py
# ------------------------------------------------------------
# Application entry point and route handlers.
#
# Access control: everyone must sign in (Supabase Auth, see auth.py).
# Each account is a "student" or "staff" (stored in the `profiles`
# table). Students manage their own bookings; staff can also manage
# every booking, manage resources and see reports.
# ------------------------------------------------------------
import logging
import os
from datetime import date, datetime
from urllib.parse import quote_plus

from dotenv import load_dotenv
from fasthtml.common import *

import auth
from validation import parse_date, parse_int, safe_kind, booking_error, resource_error, MAX_CAPACITY
from db import (
    OPEN_HOUR, CLOSE_HOUR, STATUSES, type_names, get_profile,
    list_resources, get_resource, create_resource, update_resource, delete_resource,
    list_bookings, get_booking, has_clash, create_booking, set_booking_status, slots_for,
)
from analytics import kpis, bookings_by_type, weekly_trend, most_booked, by_building
from ui import (
    Page, Alert, Card, StatItem, StatsRow, StatusBadge, Cell, DataTable, DetailList,
    Field, SelectField, TextArea_, ListingCard, BarChart, LineChart,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pages that can be opened without signing in.
PUBLIC_PATHS = [r"/signin", r"/favicon\.ico"]


def require_sign_in(req, sess):
    """Runs before every page: visitors who are not signed in are sent
    to the sign-in page, and brought back afterwards."""
    if not sess.get("user"):
        nxt = quote_plus(req.url.path)
        return RedirectResponse(f"/signin?next={nxt}", status_code=303)


def error_page(req, exc):
    """Shown instead of a bare "Internal Server Error" when a page fails,
    for example because the database cannot be reached. The details go
    to the server log, never to the person's screen."""
    logger.error("Unhandled error on %s %s", req.method, req.url.path, exc_info=exc)
    user = req.scope.get("session", {}).get("user")
    page = Page(
        "Something went wrong",
        Alert("We could not load this page right now. Nothing you entered has been lost "
              "elsewhere; please try again in a moment.", "error"),
        A("Back to dashboard", href="/", cls="btn btn-ghost"),
        active="", user=user,
    )
    return HTMLResponse("<!doctype html>" + to_xml(page), status_code=500)


app, rt = fast_app(
    hdrs=(),
    before=Beforeware(require_sign_in, skip=PUBLIC_PATHS),
    secret_key=os.environ.get("SESSION_SECRET"),
    exception_handlers={Exception: error_page},
)


# ---------------- helpers ----------------
def current_user(session):
    return session.get("user")


def is_staff(session):
    user = session.get("user")
    return bool(user) and user["role"] == "staff"


def staff_only(session, redirect_to="/"):
    if not is_staff(session):
        return go(redirect_to, "Staff access only.", "error")
    return None


def go(path, msg="", kind="ok"):
    """Redirect, optionally carrying a message to show on the next page."""
    if msg:
        path += ("&" if "?" in path else "?") + f"msg={quote_plus(msg)}&kind={safe_kind(kind)}"
    return RedirectResponse(path, status_code=303)


def _hours(s, e):
    try:
        t0 = datetime.strptime(s, "%H:%M")
        t1 = datetime.strptime(e, "%H:%M")
        return max((t1 - t0).total_seconds() / 3600, 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_next(path):
    """Only follow 'next' links that stay inside this site."""
    ok = isinstance(path, str) and path.startswith("/") and not path.startswith("//")
    return path if ok else "/"


def _pretty_date(iso, fmt="%a %d %b %Y"):
    try:
        return datetime.fromisoformat(iso).strftime(fmt)
    except (TypeError, ValueError):
        return str(iso)


# ---------------- Sign in / sign out ----------------
@rt("/signin")
def get(session, msg: str = "", kind: str = "error", next: str = "/"):
    if current_user(session):
        return go(_safe_next(next))
    form = Form(
        Div(
            Field("email", type="email", autocomplete="username", required=True, autofocus=True),
            Field("password", type="password", autocomplete="current-password", required=True),
            cls="form-grid",
        ),
        Hidden(name="next", value=next),
        Button("Sign in", cls="btn btn-primary"),
        method="post", action="/signin",
    )
    return Page(
        "Sign in",
        Div(
            Alert(msg, kind) if msg else None,
            Card("Welcome back", form),
            P("Accounts are issued by the university. Contact Learning Resources if you cannot sign in.",
              cls="auth-note"),
            cls="auth-wrap",
        ),
        subtitle="Use your university email and password.",
        active="",
    )


@rt("/signin")
def post(session, email: str = "", password: str = "", next: str = "/"):
    email = email.strip().lower()
    back = f"/signin?next={quote_plus(next)}"
    if not email or not password:
        return go(back, "Enter your email and password.", "error")
    try:
        result = auth.sign_in(email, password)
    except auth.AuthUnavailable:
        return go(back, "Sign-in is unavailable right now. Please try again shortly.", "error")

    profile = get_profile(result["user_id"]) if result else None
    if not profile:
        # One message for every failure, so nobody can discover which emails have accounts.
        return go(back, "Email or password is incorrect.", "error")

    session["user"] = {
        "user_id": profile["user_id"],
        "first_name": profile["first_name"],
        "last_name": profile["last_name"],
        "email": email,
        "role": profile["role"],
    }
    return go(_safe_next(next))


@rt("/signout")
def post(session):
    session.clear()
    return go("/signin", "You have signed out.", "info")


# ---------------- Account ----------------
@rt("/account")
def get(session, msg: str = "", kind: str = "info"):
    user = current_user(session)
    profile = get_profile(user["user_id"])
    details = DetailList([
        ("Name", f'{profile["first_name"]} {profile["last_name"]}'),
        ("Email", user["email"]),
        ("University ID", profile["university_id"]),
        ("Role", profile["role"].title()),
        ("Department", profile["department"]),
        ("Course", profile["course"] if profile["role"] == "student" else "Not applicable"),
    ])
    return Page(
        "Account",
        Alert(msg, kind) if msg else None,
        Card("Your details", details, hint="Managed by the university"),
        Card("Security",
             P("Change the password you use to sign in.", cls="muted", style="margin-bottom:14px"),
             A("Change password", href="/account/password", cls="btn btn-ghost")),
        subtitle="Your profile and sign-in settings.",
        active="", user=user,
    )


@rt("/account/password")
def get(session, msg: str = "", kind: str = "error"):
    user = current_user(session)
    form = Form(
        Div(
            Field("current_password", type="password", autocomplete="current-password", required=True),
            Field("new_password", type="password", autocomplete="new-password", required=True),
            Field("confirm_password", type="password", autocomplete="new-password", required=True,
                  label="Confirm new password"),
            cls="form-grid",
        ),
        P("Your new password needs:", cls="muted", style="margin:16px 0 0;font-size:13px"),
        Ul(*[Li(rule) for rule in auth.PASSWORD_RULES], cls="rules"),
        Button("Update password", cls="btn btn-primary"),
        method="post", action="/account/password",
    )
    return Page(
        "Change password",
        Div(Alert(msg, kind) if msg else None, Card("Choose a new password", form), cls="auth-wrap"),
        active="", user=user,
    )


@rt("/account/password")
def post(session, current_password: str = "", new_password: str = "", confirm_password: str = ""):
    user = current_user(session)
    back = "/account/password"
    if not current_password or not new_password:
        return go(back, "Fill in every field.", "error")
    if new_password != confirm_password:
        return go(back, "The two new passwords do not match.", "error")
    if new_password == current_password:
        return go(back, "Your new password must be different from the current one.", "error")
    problems = auth.password_problems(new_password)
    if problems:
        return go(back, "Your new password still needs: " + ", ".join(p.lower() for p in problems) + ".", "error")
    try:
        # Prove it really is the account owner by checking the current password first.
        result = auth.sign_in(user["email"], current_password)
        if not result:
            return go(back, "Your current password is incorrect.", "error")
        if not auth.change_password(result["access_token"], new_password):
            return go(back, "The password could not be changed. Please try again.", "error")
    except auth.AuthUnavailable:
        return go(back, "The sign-in service is unavailable right now. Please try again shortly.", "error")
    return go("/account", "Your password has been changed.", "ok")


# ---------------- Dashboard ----------------
@rt("/")
def get(session, msg: str = "", kind: str = "info"):
    user = current_user(session)
    upcoming = list_bookings(upcoming=True, user_id=user["user_id"], limit=6)
    rows = [
        Tr(Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
           Td(_pretty_date(b["booking_date"])),
           Td(f'{b["start_time"]}–{b["end_time"]}'),
           Td(b["purpose"] or "—"))
        for b in upcoming
    ]
    popular_cards = [
        ListingCard(
            icon=r["icon"],
            title=r["resource_name"],
            meta=f'{r["building"]} {r["room_code"]}',
            body=f'{r["hours"]:g} hours booked recently',
            action=A("Check availability", href=f'/availability?rtype={quote_plus(r["resource_type"])}',
                     cls="btn btn-ghost btn-sm"),
        )
        for r in most_booked(3)
    ]

    blocks = [Alert(msg, kind)] if msg else []

    if is_staff(session):
        k = kpis()
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
                        DataTable(["Resource", "Date", "Time", "Purpose"], rows,
                                   empty_msg="You have no upcoming bookings."), flush=True))
    blocks.append(Card("Most in-demand resources",
                        Div(*popular_cards, cls="listing-grid") if popular_cards
                        else P("No bookings have been made yet.", cls="muted")))

    return Page(
        f'Welcome, {user["first_name"]}', *blocks,
        subtitle="Your bookings and what is in demand across campus.",
        active="/", user=user,
        actions=[A("+ New booking", href="/bookings/new", cls="btn btn-primary"),
                 A("Check availability", href="/availability", cls="btn btn-ghost")],
    )


# ---------------- Resources ----------------
@rt("/resources")
def get(session, msg: str = "", kind: str = "info", rtype: str = ""):
    user = current_user(session)
    staff = is_staff(session)
    types = type_names()
    unknown_type = bool(rtype) and rtype not in types
    if unknown_type:
        rtype = ""
    resources = list_resources(rtype=rtype)

    def row(r):
        cells = [
            Cell(f'{r["icon"]} {r["resource_name"]}', r["notes"] or ""),
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
    if unknown_type:
        blocks.append(Alert("Unknown resource type ignored; showing all types.", "warn"))
    blocks.append(Form(SelectField("rtype", types, value=rtype, blank="All types", label="Resource type"),
                        Button("Filter", cls="btn btn-ghost"),
                        cls="filters", method="get", action="/resources"))
    blocks.append(Card("All resources", DataTable(headers, rows, empty_msg="No resources match that filter."), flush=True))

    return Page(
        "Resources", *blocks,
        subtitle="Browse all bookable resources on campus.",
        active="/resources", user=user,
        actions=[A("+ Add resource", href="/resources/new", cls="btn btn-primary")] if staff else None,
    )


def _resource_form(r=None, action="/resources/new"):
    g = (lambda k, d="": r[k]) if r else (lambda k, d="": d)
    return Form(
        Div(
            Field("resource_name", value=g("resource_name")),
            SelectField("resource_type", type_names(), value=g("resource_type")),
            Field("building", value=g("building")),
            Field("room_code", value=g("room_code")),
            Field("capacity", value=g("capacity", 1), type="number", min=1, max=MAX_CAPACITY),
            SelectField("is_active", [("1", "Active"), ("0", "Inactive")],
                        value="1" if g("is_active", True) else "0", label="Status"),
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
    return Page("New resource", Card("Add a new bookable item", _resource_form()),
                active="/resources", user=current_user(session))


@rt("/resources/new")
def post(session, resource_name: str = "", resource_type: str = "", capacity: str = "1",
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    err = resource_error(resource_name, resource_type, capacity, is_active, type_names())
    if err:
        return go("/resources", err, "error")
    create_resource(resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     int(capacity), notes.strip(), is_active == "1")
    return go("/resources", "Resource created.")


@rt("/resources/{rid}/edit")
def get(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    r = get_resource(rid)
    if not r:
        return go("/resources", "Resource not found.", "error")
    return Page(f'Edit "{r["resource_name"]}"', Card("Update details", _resource_form(r, f"/resources/{rid}/edit")),
                active="/resources", user=current_user(session))


@rt("/resources/{rid}/edit")
def post(rid: int, session, resource_name: str = "", resource_type: str = "", capacity: str = "1",
         building: str = "", room_code: str = "", notes: str = "", is_active: str = "1"):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if not get_resource(rid):
        return go("/resources", "Resource not found.", "error")
    err = resource_error(resource_name, resource_type, capacity, is_active, type_names())
    if err:
        return go("/resources", err, "error")
    update_resource(rid, resource_name.strip(), resource_type, building.strip(), room_code.strip(),
                     int(capacity), notes.strip(), is_active == "1")
    return go("/resources", "Resource updated.")


@rt("/resources/{rid}/delete")
def post(rid: int, session):
    guard = staff_only(session, "/resources")
    if guard:
        return guard
    if not get_resource(rid):
        return go("/resources", "Resource not found.", "error")
    if not delete_resource(rid):
        return go("/resources",
                  "This resource has bookings, so it cannot be deleted. Edit it and set it to Inactive instead.",
                  "error")
    return go("/resources", "Resource deleted.")


# ---------------- Bookings ----------------
@rt("/bookings")
def get(session, msg: str = "", kind: str = "info"):
    user = current_user(session)
    staff = is_staff(session)
    # Staff see every booking; students see only their own.
    only_user = None if staff else user["user_id"]
    upcoming = list_bookings(upcoming=True, user_id=only_user)
    history = list_bookings(upcoming=False, user_id=only_user, limit=15)

    def row(b, show_actions):
        cells = [
            Cell(b["resource_name"], f'{b["building"]} {b["room_code"]}'),
            Td(_pretty_date(b["booking_date"])),
            Td(f'{b["start_time"]}–{b["end_time"]}'),
        ]
        if staff:
            cells.append(Cell(b["user_name"], b["university_id"]))
        cells += [Td(b["purpose"] or "—"), Td(StatusBadge(b["status"]))]
        if show_actions:
            buttons = [Form(Button("Cancel", cls="btn btn-danger btn-sm"), method="post",
                            action=f'/bookings/{b["booking_id"]}/status?to=cancelled', style="display:inline")]
            if staff:
                buttons.append(Form(Button("Complete", cls="btn btn-ghost btn-sm"), method="post",
                                    action=f'/bookings/{b["booking_id"]}/status?to=completed',
                                    style="display:inline"))
            cells.append(Td(*buttons))
        return Tr(*cells)

    base = ["Resource", "Date", "Time"] + (["Booked by"] if staff else []) + ["Purpose", "Status"]

    blocks = [Alert(msg, kind)] if msg else []
    blocks.append(Card("Upcoming bookings",
                        DataTable(base + ["Actions"], [row(b, True) for b in upcoming],
                                   empty_msg="No upcoming bookings."),
                        flush=True))
    blocks.append(Card("Recent history",
                        DataTable(base, [row(b, False) for b in history], empty_msg="No past bookings yet."),
                        hint="Last 15", flush=True))

    return Page("Bookings" if staff else "My bookings", *blocks,
                subtitle="All reservations across the campus estate." if staff
                else "Your upcoming and past reservations.",
                active="/bookings", user=user,
                actions=[A("+ New booking", href="/bookings/new", cls="btn btn-primary")])


@rt("/bookings/new")
def get(session, msg: str = "", kind: str = "error", resource_id: str = ""):
    user = current_user(session)
    resource_id = str(parse_int(resource_id, default=""))
    options = [(r["resource_id"], f'{r["icon"]} {r["resource_name"]} ({r["room_code"]})')
               for r in list_resources(active_only=True)]
    form = Form(
        Div(
            SelectField("resource_id", options, value=resource_id, label="Resource"),
            Field("booking_date", value=date.today().isoformat(), type="date",
                  min=date.today().isoformat()),
            Field("start_time", value="09:00", type="time", step=1800,
                  min=f"{OPEN_HOUR:02d}:00", max=f"{CLOSE_HOUR - 1:02d}:30",
                  help_text=f"Campus open {OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00"),
            Field("end_time", value="11:00", type="time", step=1800,
                  min=f"{OPEN_HOUR:02d}:30", max=f"{CLOSE_HOUR:02d}:00",
                  data_after="start_time"),
            TextArea_("purpose"),
            cls="form-grid",
        ),
        Button("Confirm booking", cls="btn btn-primary", style="margin-top:18px"),
        A("Cancel", href="/bookings", cls="btn btn-ghost", style="margin-top:18px;margin-left:8px"),
        method="post", action="/bookings/new",
    )
    blocks = [Alert(msg, kind)] if msg else []
    blocks.append(Card("Book an item", form, hint=f'Booking as {user["first_name"]} {user["last_name"]}'))
    return Page("New booking", *blocks, active="/bookings", user=user)


@rt("/bookings/new")
def post(session, resource_id: str = "", booking_date: str = "", start_time: str = "",
         end_time: str = "", purpose: str = ""):
    user = current_user(session)
    start_time, end_time = start_time.strip(), end_time.strip()
    rid = parse_int(resource_id)
    resource = get_resource(rid) if rid else None

    if not resource or not resource["is_active"]:
        err = "That resource is not available to book."
    else:
        err = booking_error(booking_date, start_time, end_time, purpose,
                            open_hour=OPEN_HOUR, close_hour=CLOSE_HOUR)
    if not err and has_clash(rid, booking_date, start_time, end_time):
        err = "That resource is already booked for this time slot."

    if not err and not create_booking(rid, user["user_id"], booking_date.strip(),
                                      start_time, end_time, purpose.strip()):
        # The database's own no-overlap rule caught a booking made a moment earlier.
        err = "That resource has just been booked for this time slot."

    if err:
        return go(f"/bookings/new?resource_id={rid}" if rid else "/bookings/new", err, "error")
    return go("/bookings", "Booking confirmed.")


@rt("/bookings/{bid}/status")
def post(bid: int, session, to: str = "cancelled"):
    user = current_user(session)
    booking = get_booking(bid)
    if not booking:
        return go("/bookings", "Booking not found.", "error")
    if to not in STATUSES:
        return go("/bookings", "That is not a valid booking status.", "error")
    if not is_staff(session):
        # Students may only cancel their own upcoming bookings.
        if booking["user_id"] != user["user_id"] or to != "cancelled" or booking["status"] != "confirmed":
            return go("/bookings", "You can only cancel your own upcoming bookings.", "error")
    set_booking_status(bid, to)
    return go("/bookings", f'Booking marked {to.replace("_", " ")}.')


# ---------------- Availability ----------------
@rt("/availability")
def get(session, d: str = "", rtype: str = ""):
    user = current_user(session)
    staff = is_staff(session)
    notices = []
    day = parse_date(d)
    if d and day is None:
        notices.append(Alert("That date was not valid, so today is shown instead.", "warn"))
    d = (day or date.today()).isoformat()
    types = type_names()
    if rtype and rtype not in types:
        notices.append(Alert("Unknown resource type ignored; showing all types.", "warn"))
        rtype = ""
    rows = []
    for r in list_resources(active_only=True, rtype=rtype):
        slots = slots_for(r["resource_id"], d)
        used = sum(_hours(s["start_time"], s["end_time"]) for s in slots)
        # Privacy: only staff see who made a booking. Students just see the slot is taken.
        slot_spans = [Span(f'{s["start_time"]}–{s["end_time"]} ' + (s["user_name"] if staff else "Booked"),
                           cls="slot") for s in slots]
        if not slot_spans:
            slot_spans = [Span(f"Free all day ({OPEN_HOUR:02d}:00–{CLOSE_HOUR:02d}:00)", cls="slot free")]
        rows.append(Tr(
            Cell(f'{r["icon"]} {r["resource_name"]}', f'{r["building"]} {r["room_code"]}'),
            Td(*slot_spans),
            Td(f'{max((CLOSE_HOUR - OPEN_HOUR) - used, 0):g} hrs free'),
            Td(A("Book", href=f'/bookings/new?resource_id={r["resource_id"]}', cls="btn btn-primary btn-sm")),
        ))

    form = Form(
        Field("d", value=d, type="date", label="Date"),
        SelectField("rtype", types, value=rtype, blank="All types", label="Resource type"),
        Button("Search", cls="btn btn-primary", style="align-self:flex-end"),
        cls="filters", method="get", action="/availability",
    )
    pretty = _pretty_date(d, "%A %d %B %Y")
    return Page(
        "Availability", *notices, Card("Filters", form),
        Card(f"Resources on {pretty}", DataTable(["Resource", "Booked slots", "Free hours", ""], rows,
                                                    empty_msg="No active resources match that filter.")),
        subtitle="Check free and booked slots by date.",
        active="/availability", user=user,
    )


# ---------------- Reports (staff only) ----------------
@rt("/reports")
def get(session):
    guard = staff_only(session, "/")
    if guard:
        return guard
    k = kpis()
    bld_rows = [
        Tr(Td(b["label"]), Td(b["value"]), Td(b["cancelled"]),
           Td(f'{round((b["cancelled"] / b["value"]) * 100) if b["value"] else 0}%'))
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
        active="/reports", user=current_user(session),
    )


# ---------------- Entry point ----------------
if __name__ == "__main__":
    port = parse_int(os.environ.get("PORT") or os.environ.get("APP_PORT"), default=8080, max_val=65535)
    is_cloud = "PORT" in os.environ
    serve(host="0.0.0.0", port=port, reload=not is_cloud)
