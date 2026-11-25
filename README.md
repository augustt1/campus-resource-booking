```markdown
# Campus Resource Booking System

A lightweight web application for booking and managing shared campus resources
(study rooms, labs, equipment, halls) built with Python, FastHTML, and SQLite.

## Features

- **Dashboard** — service-wide KPIs (utilisation rate, cancellation rate,
  no-show rate), weekly booking trend chart, and most in-demand resources.
- **Resources** — full CRUD (create, read, update, delete) for bookable
  resources, with active/inactive status filtering.
- **Bookings** — create new bookings with clash detection, opening-hours
  validation, and past-date prevention. Mark bookings as completed or
  cancelled.
- **Availability** — view free/booked time slots per resource for any date.
- **Reports** — 30-day KPI summary, bookings by resource type, weekly trend,
  and bookings/cancellations by building.
- Dependency-free charts (bar and line) rendered as plain CSS/SVG — no
  JavaScript libraries or CDN required.

## Project Structure

```
campus-resource-booking/
├── main.py          # App entry point and all routes
├── db.py            # Database schema, connection, and queries
├── analytics.py      # KPI and reporting calculations
├── ui.py            # Shared CSS and reusable UI components
├── campus.db          # SQLite database (auto-created on first run)
├── requirements.txt  # Python dependencies
└── README.md
```

## Requirements

- Python 3.10+
- See `requirements.txt` for packages (FastHTML)

## Setup & Running

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/campus-resource-booking.git
   cd campus-resource-booking
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python main.py
   ```

5. Open your browser at [http://localhost:8080](http://localhost:8080)

> On first run, `campus.db` is automatically created with sample seed data
> (resources and bookings). Delete `campus.db` to reset to a fresh state.

## Notes

- The campus is assumed open 08:00–20:00; bookings outside this window are
  rejected.
- Double-booking is prevented via time-overlap checks at the database query
  level.
- Charts are rendered server-side with no external JS/CSS dependencies.

## License

This project is for educational purposes.
```
