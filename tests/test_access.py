"""Sign-in and permissions, tested through the real routes.

The database and the Supabase sign-in service are replaced with small
stand-ins, so these tests need no network and change no data.
"""
from datetime import date, timedelta
from urllib.parse import unquote_plus

import pytest
from starlette.testclient import TestClient

import main

STUDENT = {"user_id": "student-1", "university_id": "U1", "first_name": "Alex", "last_name": "Chen",
           "role": "student", "department": "Computer Science", "course": "MSc"}
STAFF = {"user_id": "staff-1", "university_id": "S1", "first_name": "Sam", "last_name": "Okafor",
         "role": "staff", "department": "Library", "course": None}
TOMORROW = (date.today() + timedelta(days=1)).isoformat()


@pytest.fixture
def client():
    return TestClient(main.app, follow_redirects=False, raise_server_exceptions=False)


@pytest.fixture
def sign_in_as(client, monkeypatch):
    def _sign_in(profile):
        monkeypatch.setattr(main.auth, "sign_in", lambda email, password: {"user_id": profile["user_id"],
                                                                           "access_token": "token"})
        monkeypatch.setattr(main, "get_profile", lambda user_id: profile)
        r = client.post("/signin", data={"email": "someone@example.com", "password": "pw"})
        assert r.status_code == 303 and r.headers["location"] == "/"
    return _sign_in


def where(response):
    """The redirect target, with the message decoded so it can be read."""
    assert response.status_code == 303
    return unquote_plus(response.headers["location"])


class Recorder:
    """Stands in for a database function and remembers how it was called."""
    def __init__(self, result=None):
        self.calls, self.result = [], result

    def __call__(self, *args, **kwargs):
        self.calls.append(args)
        return self.result


# ---------------- signing in ----------------
@pytest.mark.parametrize("path", ["/", "/bookings", "/resources", "/availability", "/reports", "/account"])
def test_signed_out_visitor_is_sent_to_sign_in(client, path):
    assert where(client.get(path)).startswith("/signin?next=")


def test_wrong_password_and_unknown_email_give_the_same_message(client, monkeypatch):
    # Wrong password: Supabase says no.
    monkeypatch.setattr(main.auth, "sign_in", lambda e, p: None)
    wrong_password = where(client.post("/signin", data={"email": "a@example.com", "password": "x"}))
    # Password accepted, but there is no profile for this person.
    monkeypatch.setattr(main.auth, "sign_in", lambda e, p: {"user_id": "ghost", "access_token": "t"})
    monkeypatch.setattr(main, "get_profile", lambda user_id: None)
    no_profile = where(client.post("/signin", data={"email": "a@example.com", "password": "x"}))

    assert "Email or password is incorrect." in wrong_password
    assert wrong_password == no_profile


def test_sign_in_never_redirects_to_another_site(client, monkeypatch):
    monkeypatch.setattr(main.auth, "sign_in", lambda e, p: {"user_id": "student-1", "access_token": "t"})
    monkeypatch.setattr(main, "get_profile", lambda user_id: STUDENT)
    r = client.post("/signin", data={"email": "a@example.com", "password": "x", "next": "//evil.example"})
    assert where(r) == "/"


def test_sign_in_service_down_shows_a_friendly_message(client, monkeypatch):
    def down(email, password):
        raise main.auth.AuthUnavailable("offline")
    monkeypatch.setattr(main.auth, "sign_in", down)
    assert "unavailable" in where(client.post("/signin", data={"email": "a@example.com", "password": "x"}))


def test_sign_out_ends_the_session(client, sign_in_as):
    sign_in_as(STUDENT)
    client.post("/signout")
    assert where(client.get("/bookings")).startswith("/signin")


# ---------------- students are kept out of staff pages ----------------
def test_student_cannot_open_reports(client, sign_in_as):
    sign_in_as(STUDENT)
    assert "Staff access only." in where(client.get("/reports"))


def test_student_cannot_create_edit_or_delete_resources(client, sign_in_as, monkeypatch):
    sign_in_as(STUDENT)
    created, updated, deleted = Recorder(), Recorder(), Recorder(True)
    monkeypatch.setattr(main, "create_resource", created)
    monkeypatch.setattr(main, "update_resource", updated)
    monkeypatch.setattr(main, "delete_resource", deleted)
    form = {"resource_name": "Sneaky Room", "resource_type": "Study Room", "capacity": "4"}

    assert "Staff access only." in where(client.get("/resources/new"))
    assert "Staff access only." in where(client.post("/resources/new", data=form))
    assert "Staff access only." in where(client.post("/resources/1/edit", data=form))
    assert "Staff access only." in where(client.post("/resources/1/delete"))
    assert created.calls == updated.calls == deleted.calls == []


# ---------------- changing a booking's status ----------------
def booking(owner, status="confirmed"):
    return {"booking_id": 7, "user_id": owner, "status": status}


def test_student_can_cancel_their_own_booking(client, sign_in_as, monkeypatch):
    sign_in_as(STUDENT)
    changed = Recorder()
    monkeypatch.setattr(main, "get_booking", lambda bid: booking("student-1"))
    monkeypatch.setattr(main, "set_booking_status", changed)
    assert "Booking marked cancelled." in where(client.post("/bookings/7/status?to=cancelled"))
    assert changed.calls == [(7, "cancelled")]


def test_student_cannot_cancel_someone_elses_booking(client, sign_in_as, monkeypatch):
    sign_in_as(STUDENT)
    changed = Recorder()
    monkeypatch.setattr(main, "get_booking", lambda bid: booking("someone-else"))
    monkeypatch.setattr(main, "set_booking_status", changed)
    assert "only cancel your own" in where(client.post("/bookings/7/status?to=cancelled"))
    assert changed.calls == []


def test_student_cannot_mark_a_booking_completed(client, sign_in_as, monkeypatch):
    sign_in_as(STUDENT)
    changed = Recorder()
    monkeypatch.setattr(main, "get_booking", lambda bid: booking("student-1"))
    monkeypatch.setattr(main, "set_booking_status", changed)
    assert "only cancel your own" in where(client.post("/bookings/7/status?to=completed"))
    assert changed.calls == []


def test_staff_can_complete_any_booking(client, sign_in_as, monkeypatch):
    sign_in_as(STAFF)
    changed = Recorder()
    monkeypatch.setattr(main, "get_booking", lambda bid: booking("student-1"))
    monkeypatch.setattr(main, "set_booking_status", changed)
    assert "Booking marked completed." in where(client.post("/bookings/7/status?to=completed"))
    assert changed.calls == [(7, "completed")]


def test_unknown_status_is_refused(client, sign_in_as, monkeypatch):
    sign_in_as(STAFF)
    changed = Recorder()
    monkeypatch.setattr(main, "get_booking", lambda bid: booking("student-1"))
    monkeypatch.setattr(main, "set_booking_status", changed)
    assert "not a valid booking status" in where(client.post("/bookings/7/status?to=deleted"))
    assert changed.calls == []


# ---------------- making a booking ----------------
@pytest.fixture
def booking_form(sign_in_as, monkeypatch):
    """Signed in as a student, with one bookable resource and nothing booked."""
    sign_in_as(STUDENT)
    created = Recorder(True)
    monkeypatch.setattr(main, "get_resource", lambda rid: {"resource_id": rid, "is_active": True})
    monkeypatch.setattr(main, "has_clash", lambda *a: False)
    monkeypatch.setattr(main, "create_booking", created)
    return created


def test_booking_is_saved_under_the_signed_in_person(client, booking_form):
    r = client.post("/bookings/new", data={"resource_id": "3", "booking_date": TOMORROW,
                                           "start_time": "10:00", "end_time": "12:00", "purpose": "Study"})
    assert "Booking confirmed." in where(r)
    assert booking_form.calls == [(3, "student-1", TOMORROW, "10:00", "12:00", "Study")]


def test_booking_in_the_past_is_not_saved(client, booking_form):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    r = client.post("/bookings/new", data={"resource_id": "3", "booking_date": yesterday,
                                           "start_time": "10:00", "end_time": "12:00"})
    assert "cannot be in the past" in where(r)
    assert booking_form.calls == []


def test_clashing_booking_is_not_saved(client, booking_form, monkeypatch):
    monkeypatch.setattr(main, "has_clash", lambda *a: True)
    r = client.post("/bookings/new", data={"resource_id": "3", "booking_date": TOMORROW,
                                           "start_time": "10:00", "end_time": "12:00"})
    assert "already booked" in where(r)
    assert booking_form.calls == []


def test_inactive_resource_cannot_be_booked(client, booking_form, monkeypatch):
    monkeypatch.setattr(main, "get_resource", lambda rid: {"resource_id": rid, "is_active": False})
    r = client.post("/bookings/new", data={"resource_id": "3", "booking_date": TOMORROW,
                                           "start_time": "10:00", "end_time": "12:00"})
    assert "not available to book" in where(r)
    assert booking_form.calls == []


def test_nonsense_form_values_do_not_crash(client, booking_form):
    r = client.post("/bookings/new", data={"resource_id": "abc", "booking_date": "soon",
                                           "start_time": "late", "end_time": ""})
    assert "not available to book" in where(r)
    assert booking_form.calls == []


# ---------------- when the database is down ----------------
def test_database_failure_shows_an_error_page_not_a_crash(client, sign_in_as, monkeypatch):
    sign_in_as(STUDENT)

    def broken(*args, **kwargs):
        raise RuntimeError("connection refused: secret-host")
    monkeypatch.setattr(main, "list_bookings", broken)

    r = client.get("/bookings")
    assert r.status_code == 500
    assert "Something went wrong" in r.text
    assert "secret-host" not in r.text      # technical details stay in the server log
