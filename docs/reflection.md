# Project Reflection — Campus Resource Booking

**Module:** Programming for Artificial Intelligence (WM9QF-15)
**Team members:** [Name 1, Name 2, Name 3, ...]
**Date:** [submission date]

## 1. Development Lifecycle Methodology

We adopted an **Iterative (incremental) development approach** rather than
Waterfall. We chose this because the scenario brief left several design
decisions open (e.g. exact resource types, booking rules, role separation),
and we expected our understanding of requirements to improve as we built
and tested working pieces of the system.

Each iteration followed roughly the same small cycle:
1. Pick one user-facing capability (e.g. "staff can view KPIs", "students
   can book a resource without double-booking").
2. Implement the minimal database + logic + page needed.
3. Manually exercise it, write/extend tests, fix defects found.
4. Commit to Git with a descriptive message before moving to the next slice.

We rejected Waterfall because our team had not built a FastHTML/SQLite
application before; locking in a complete upfront design would have meant
discovering fundamental problems (e.g. our original folder-per-layer
structure causing import errors — see Section 4) too late to recover
cheaply. We also rejected a full Scrum process as disproportionate for a
team of [N] working over [X weeks] — we kept its spirit (short cycles,
retrospective fixes) without the ceremony (no formal sprints/stand-ups).

## 2. Requirements Gathering and Planning

Requirements were derived from the scenario brief (a campus resource
booking system) and refined through internal discussion rather than a
formal external stakeholder. Our interpretation:

**Functional requirements:**
- Manage a set of bookable resources (study rooms, labs, halls, equipment)
  grouped by type and building.
- Allow a user to create a booking for a resource within a defined date
  and time window, preventing double-booking of the same resource.
- Allow upcoming bookings to be cancelled or marked completed.
- Provide staff-only analytics: utilisation rate, cancellation rate,
  no-show rate, weekly booking trend, most in-demand resources.
- Separate what students and staff can see/do (students browse and book;
  staff manage resources and view service-wide reports).

**Non-functional requirements:**
- Data must persist between runs (SQLite rather than in-memory state).
- The system should prevent invalid bookings at the data layer, not just
  hide buttons in the UI (defence in depth).
- The codebase should be split by responsibility (data access / analytics
  / presentation / routing) so it remains readable as it grows.

Tasks were divided as follows: [e.g. "Person A: database schema and
queries; Person B: booking validation and clash detection; Person C: UI
components and page composition; Person D: analytics and reporting"].
Progress was tracked via [GitHub Issues / a shared document / a Trello
board — state what you actually used].

## 3. Software Architecture and Design Decisions

The application is split into four modules by responsibility:

| Module         | Responsibility                                            |
|-----------------|------------------------------------------------------------|
| `db.py`         | Schema, seed data, and all SQL queries                    |
| `analytics.py`  | KPI and reporting calculations, built on top of `db.py`    |
| `ui.py`         | Reusable CSS/HTML components and page shell                |
| `main.py`       | Routes only — composes `db`, `analytics`, and `ui` together |

**Design decisions and trade-offs:**

- **SQLite over a heavier database.** Chosen for simplicity and zero setup
  cost, appropriate for a coursework-scale application. We accept this
  would not scale to concurrent multi-user production use.
- **No password-based authentication.** We considered implementing full
  user accounts with hashed passwords and sessions, but decided this was
  out of scope for the assessed learning outcomes and would introduce a
  large new area for bugs without demonstrable benefit. Instead we
  implemented a lightweight session-based **role switch** (student/staff)
  to demonstrate the *concept* of role-based access control — staff see
  analytics and resource management; students see booking and
  availability only — while being transparent that this is not real
  authentication. **Future work:** a `users` table with hashed
  passwords and proper login would be the natural next iteration.
- **Clash detection enforced in the database layer (`has_clash`), not
  just the UI.** This was a deliberate choice so that even a direct
  form submission bypassing the UI cannot create an overlapping booking.
- **Server-rendered, dependency-free charts (CSS bars / inline SVG lines)**
  instead of a JavaScript charting library, to avoid external dependencies
  and keep the application runnable offline.

## 4. Challenges Encountered and How We Responded

- **Initial over-modularisation.** Early in the project we split the
  application into an `app/routes`, `app/pages`, `app/ui` package
  structure. This produced a cascade of `ModuleNotFoundError` and
  `ImportError` failures, because files were referenced before they were
  fully implemented (e.g. `app.pages.dashboard_page`, then
  `BarChart`/`StatCard` missing from `app.ui.components`). We treated this
  as a signal that the structure's complexity had outpaced the project's
  actual size. We refactored down to four flat modules
  (`main.py`, `db.py`, `analytics.py`, `ui.py`), which eliminated the
  import errors and made the codebase easier to reason about and test.
  This was a genuine design pivot based on evidence, not a cosmetic choice.
- **Silent logic bug in booking history.** We discovered that cancelling
  or completing an upcoming booking made it disappear from *both* the
  "Upcoming" and "Recent History" views. Investigation showed
  `list_bookings(upcoming=False)` filtered strictly by `booking_date <
  today`, while `upcoming=True` filtered by `status='confirmed'` — a
  booking changed to `cancelled`/`completed` on a future date satisfied
  neither condition. We fixed this by redefining "history" as "anything
  that is not an active, upcoming, confirmed booking" rather than purely
  by date. This taught us to be more careful about how implicit state
  transitions (status changes) interact with filters defined in terms of
  a different field (date).
- **Git authentication.** We initially hit `Authentication failed` /
  "Password authentication is not supported" errors when pushing to
  GitHub, because GitHub removed password-based Git authentication in
  2021. We resolved this by generating a Personal Access Token and using
  it in place of the account password.

## 5. Testing Approach

We adopted test-driven practices for core logic functions, particularly
booking validation (`has_clash`) and analytics calculations (`kpis`,
`weekly_trend`), using `pytest`. Tests run against a temporary SQLite
database created per test run so they never touch the real `campus.db`
seed data. See `tests/test_booking_rules.py` for CRUD and clash-detection
coverage, and [`tests/test_analytics.py`, if added] for KPI coverage.

## 6. Privacy, Ethics, and Usability Considerations

- No real personal data is collected; `user_name` is a free-text field for
  demonstration purposes rather than a verified identity.
- Because there is no real authentication, the system should not be
  treated as production-ready; this limitation is stated explicitly
  rather than hidden.
- Opening hours and past-date validation are enforced server-side to
  prevent nonsensical bookings regardless of client input.

## 7. Limitations and Future Improvements

- Replace the role-switch with real authenticated accounts and a
  `users`/`departments` table, as originally scoped in the brief.
- Add department-level reporting once a `departments` table exists.
- Add pagination for large booking histories.
- Add automated CI (e.g. GitHub Actions) to run the test suite on push.
- Expand test coverage to all route-level validation paths, not just the
  underlying data functions.

## 8. Version Control Practice

The project is hosted on GitHub at [repository URL]. We committed
incrementally with descriptive messages (e.g. "Fix booking history filter
bug", "Add role-based access control") rather than a single final commit,
so that the project history itself evidences the iterative process
described in Section 1.