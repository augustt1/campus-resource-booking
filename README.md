# Campus Resource Booking System

A prototype web application for booking and managing shared campus learning
resources (study rooms, computer labs, specialist equipment, academic support
sessions and group-work spaces). Built with Python, FastHTML and a Supabase
(Postgres) database.

## Features

- **Sign in** with a university account (Supabase Auth). Each account is a
  student or a member of staff.
- **Profile menu** — account details, change password, sign out.
- **Dashboard** — your upcoming bookings and the most in-demand resources;
  staff also see utilisation, cancellation and no-show rates and a weekly trend.
- **Resources** — browse and filter; staff can add, edit and delete.
- **Bookings** — create a booking with clash detection, opening-hours checks
  and past-date prevention. Students see and cancel their own bookings; staff
  see everyone's and can mark them completed or cancelled.
- **Availability** — free and booked slots per resource for any date. Only
  staff see who made a booking.
- **Reports** (staff) — 30-day KPIs, bookings by resource type, weekly trend
  and bookings by building.

## Project structure

```
campus-resource-booking/
├── main.py           # App entry point and all routes
├── auth.py           # Sign-in and password changes (Supabase Auth)
├── db.py             # Database connection and SQL queries
├── analytics.py      # KPI and reporting queries
├── ui.py             # Shared CSS, pickers and reusable UI components
├── db/
│   ├── schema.sql    # Tables, constraints and reference data
│   └── seed.py       # Demo accounts, resources and bookings
├── .env.example      # Template for local settings
└── requirements.txt
```

## Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in the Supabase values
   (dashboard → Connect, and Project Settings → API). `.env` holds
   passwords and must never be committed.

4. First time only, on a new Supabase project: run `db/schema.sql` in the
   Supabase SQL Editor, add a `DEMO_PASSWORD` line to `.env`, then load the
   demo data:
   ```bash
   python db/seed.py
   ```

5. Run the application and open http://localhost:8080
   ```bash
   python main.py
   ```

## Demo accounts

Created by `db/seed.py`. Both use the `DEMO_PASSWORD` set in `.env`.

| Email                 | Role    |
|-----------------------|---------|
| student@example.com   | Student |
| staff@example.com     | Staff   |

## Design notes

- Passwords are handled entirely by Supabase Auth. Our own tables hold no
  passwords, only each person's university details.
- Double-booking is prevented twice: the app checks before saving, and the
  database has its own rule that rejects overlapping confirmed bookings.
- A resource that has bookings cannot be deleted, so history is kept for
  reporting; it is set to Inactive instead.
- Every table has row-level security switched on with no public policies, so
  the data can only be reached through this application's server.
- The campus is assumed open 08:00–20:00.
- The date and time pickers and the profile menu use a small amount of
  JavaScript; without it the browser's built-in controls are used.

## Licence

This project is for educational purposes.
