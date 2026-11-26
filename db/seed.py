# db/seed.py
# ------------------------------------------------------------
# Fills an empty database with demo data so the app has something
# to show: two sign-in accounts, ten resources and sample bookings.
#
#   python db/seed.py
#
# Safe to run more than once: anything that already exists is left
# alone. Run db/schema.sql first.
#
# The demo accounts' password is read from DEMO_PASSWORD in .env,
# so it is never written in the code or committed to git.
# ------------------------------------------------------------
import os
import sys
from datetime import date, timedelta

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# (email, first name, last name, role, university ID, department, course)
DEMO_USERS = [
    ("student@example.com", "Alex", "Chen", "student", "U2100001",
     "Computer Science", "MSc Applied Artificial Intelligence"),
    ("staff@example.com", "Sam", "Okafor", "staff", "S1000001",
     "Library and Learning Resources", None),
]

# (name, type, owning department, building, room code, capacity, notes)
RESOURCES = [
    ("Study Room A", "Study Room", "Library and Learning Resources", "Library", "LIB-101", 8, "Quiet study room"),
    ("Silent Pod 1", "Study Room", "Library and Learning Resources", "Library", "LIB-G04", 1, "Single-occupant pod"),
    ("Group Room 1", "Group-Work Space", "Library and Learning Resources", "Library", "LIB-102", 6, "Whiteboard and screen"),
    ("Collaboration Hub", "Group-Work Space", "Business School", "Business School", "BUS-015", 12, "Movable tables"),
    ("AI Lab", "Computer Lab", "Computer Science", "Engineering", "ENG-204", 30, "GPU workstations"),
    ("Robotics Lab", "Computer Lab", "Engineering", "Engineering", "ENG-118", 24, "Project workbenches"),
    ("Camera Kit 1", "Specialist Equipment", "Media and Communication", "Media Centre", "MC-KIT1", 1, "DSLR and tripod"),
    ("Projector Set", "Specialist Equipment", "Media and Communication", "Media Centre", "MC-PRJ2", 1, "Portable, HDMI and USB-C"),
    ("Academic Writing Clinic", "Academic Support Session", "Library and Learning Resources", "Library", "LIB-210", 1, "One-to-one writing support"),
    ("Maths and Stats Drop-in", "Academic Support Session", "Library and Learning Resources", "Library", "LIB-212", 4, "Small-group support"),
]

# (resource, who, days from today, start, end, purpose, status)
# Negative days are in the past. Upcoming bookings are all "confirmed"
# and do not overlap each other.
BOOKINGS = [
    ("Study Room A", "student", 1, "09:00", "11:00", "Group study", "confirmed"),
    ("AI Lab", "student", 2, "13:00", "16:00", "Model training", "confirmed"),
    ("Academic Writing Clinic", "student", 5, "10:00", "11:00", "Dissertation draft review", "confirmed"),
    ("Group Room 1", "staff", 3, "14:00", "15:30", "Induction planning", "confirmed"),
    ("Projector Set", "staff", 6, "09:30", "12:00", "Open day set-up", "confirmed"),
    ("Group Room 1", "student", -2, "09:00", "10:00", "Revision", "completed"),
    ("AI Lab", "student", -3, "11:00", "13:00", "Coursework", "completed"),
    ("Robotics Lab", "student", -5, "11:00", "13:00", "Project demo", "completed"),
    ("Study Room A", "student", -7, "15:00", "16:00", "Quiet study", "completed"),
    ("Maths and Stats Drop-in", "student", -8, "14:00", "15:00", "Statistics help", "completed"),
    ("Collaboration Hub", "staff", -9, "18:00", "20:00", "Team workshop", "no_show"),
    ("AI Lab", "student", -12, "09:00", "12:00", "Workshop", "completed"),
    ("Camera Kit 1", "student", -14, "14:00", "17:00", "Filming", "completed"),
    ("Study Room A", "staff", -15, "13:00", "15:00", "Seminar prep", "cancelled"),
    ("Group Room 1", "student", -17, "10:00", "12:00", "Group project", "completed"),
    ("Robotics Lab", "staff", -20, "09:00", "11:00", "Lab session", "completed"),
    ("Silent Pod 1", "student", -24, "10:00", "11:00", "Focus work", "completed"),
    ("AI Lab", "staff", -27, "13:00", "17:00", "Staff training", "completed"),
    ("Academic Writing Clinic", "student", -30, "11:00", "12:00", "Essay feedback", "completed"),
    ("Study Room A", "student", -33, "09:00", "11:00", "Exam revision", "completed"),
    ("Group Room 1", "student", -36, "15:00", "17:00", "Presentation practice", "cancelled"),
    ("AI Lab", "student", -41, "10:00", "12:00", "Coursework", "completed"),
    ("Collaboration Hub", "student", -44, "13:00", "15:00", "Society meeting", "completed"),
    ("Study Room A", "staff", -48, "09:00", "10:00", "Planning", "completed"),
]


def ensure_user(cur, password, email, first, last, role, university_id, department, course):
    """Create the Supabase Auth account and its profile if they are missing."""
    cur.execute("SELECT id FROM auth.users WHERE email = %s", (email,))
    row = cur.fetchone()
    if row:
        user_id = row[0]
    else:
        # The password is stored only as a bcrypt hash, made by the database itself.
        cur.execute(
            """INSERT INTO auth.users (
                   instance_id, id, aud, role, email, encrypted_password, email_confirmed_at,
                   raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
                   confirmation_token, recovery_token, email_change, email_change_token_new)
               VALUES (
                   '00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated',
                   'authenticated', %s, extensions.crypt(%s, extensions.gen_salt('bf')), now(),
                   '{"provider":"email","providers":["email"]}', '{}', now(), now(),
                   '', '', '', '')
               RETURNING id""",
            (email, password),
        )
        user_id = cur.fetchone()[0]
        cur.execute(
            """INSERT INTO auth.identities (
                   user_id, provider_id, provider, identity_data, last_sign_in_at, created_at, updated_at)
               VALUES (%s, %s, 'email',
                       jsonb_build_object('sub', %s::text, 'email', %s::text,
                                          'email_verified', true, 'phone_verified', false),
                       now(), now(), now())""",
            (user_id, user_id, user_id, email),
        )
        print(f"  created account {email}")

    cur.execute(
        """INSERT INTO profiles (user_id, university_id, first_name, last_name, role, department_id, course)
           VALUES (%s, %s, %s, %s, %s, (SELECT department_id FROM departments WHERE name = %s), %s)
           ON CONFLICT (user_id) DO NOTHING""",
        (user_id, university_id, first, last, role, department, course),
    )
    return user_id


def main():
    url = os.environ.get("DATABASE_URL")
    password = os.environ.get("DEMO_PASSWORD")
    if not url or not password:
        sys.exit("Set DATABASE_URL and DEMO_PASSWORD in .env first.")

    con = psycopg2.connect(url, connect_timeout=15)
    try:
        with con, con.cursor() as cur:
            print("Accounts")
            ids = {}
            for email, first, last, role, uni_id, dept, course in DEMO_USERS:
                ids[role] = ensure_user(cur, password, email, first, last, role, uni_id, dept, course)

            cur.execute("SELECT COUNT(*) FROM resources")
            if cur.fetchone()[0] == 0:
                for name, rtype, dept, building, room, capacity, notes in RESOURCES:
                    cur.execute(
                        """INSERT INTO resources (resource_name, type_id, department_id, building,
                                                  room_code, capacity, notes)
                           VALUES (%s, (SELECT type_id FROM resource_types WHERE name = %s),
                                   (SELECT department_id FROM departments WHERE name = %s), %s, %s, %s, %s)""",
                        (name, rtype, dept, building, room, capacity, notes),
                    )
                print(f"Resources: added {len(RESOURCES)}")
            else:
                print("Resources: already present, left alone")

            cur.execute("SELECT COUNT(*) FROM bookings")
            if cur.fetchone()[0] == 0:
                today = date.today()
                for resource, who, offset, start, end, purpose, status in BOOKINGS:
                    cur.execute(
                        """INSERT INTO bookings (resource_id, user_id, booking_date, start_time,
                                                 end_time, purpose, status_id)
                           VALUES ((SELECT resource_id FROM resources WHERE resource_name = %s), %s, %s, %s, %s, %s,
                                   (SELECT status_id FROM booking_statuses WHERE code = %s))""",
                        (resource, ids[who], today + timedelta(days=offset), start, end, purpose, status),
                    )
                print(f"Bookings: added {len(BOOKINGS)}")
            else:
                print("Bookings: already present, left alone")
    finally:
        con.close()
    print("Done.")


if __name__ == "__main__":
    main()
