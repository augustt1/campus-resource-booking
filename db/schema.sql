-- ============================================================
-- Campus Resource Booking — database schema (Supabase / Postgres)
--
-- How to apply: Supabase dashboard -> SQL Editor -> paste -> Run.
-- Safe to run more than once: every statement is "if not exists"
-- or "on conflict do nothing".
--
-- Sign-in is handled by Supabase Auth (the built-in auth.users
-- table). Passwords are never stored in our own tables; `profiles`
-- holds the university details for each signed-in person.
-- ============================================================

-- Needed for the "no double-booking" rule on bookings below.
create extension if not exists btree_gist;


-- ---------------- Lookup tables ----------------

create table if not exists departments (
    department_id  integer generated always as identity primary key,
    name           text not null unique
);

create table if not exists resource_types (
    type_id  integer generated always as identity primary key,
    name     text not null unique,
    icon     text not null default '📦'
);

create table if not exists booking_statuses (
    status_id  smallint primary key,
    code       text not null unique,     -- used in code: 'confirmed', 'cancelled', ...
    label      text not null             -- shown to people: 'Confirmed', 'No show', ...
);


-- ---------------- People ----------------

-- One row per account. user_id is the Supabase Auth user's id, so
-- deleting the account in Auth removes the profile with it.
create table if not exists profiles (
    user_id        uuid primary key references auth.users (id) on delete cascade,
    university_id  text not null unique,                 -- student or staff number
    first_name     text not null,
    last_name      text not null,
    role           text not null default 'student'
                   check (role in ('student', 'staff')),
    department_id  integer references departments (department_id),
    course         text,                                 -- students only; null for staff
    created_at     timestamptz not null default now()
);


-- ---------------- Resources ----------------

create table if not exists resources (
    resource_id    integer generated always as identity primary key,
    resource_name  text not null,
    type_id        integer not null references resource_types (type_id),
    department_id  integer references departments (department_id),   -- owning department
    building       text not null default '',
    room_code      text not null default '',
    capacity       integer not null default 1 check (capacity > 0),
    notes          text not null default '',
    is_active      boolean not null default true
);


-- ---------------- Bookings ----------------

create table if not exists bookings (
    booking_id    bigint generated always as identity primary key,
    -- "restrict": a resource with bookings cannot be deleted, so history
    -- (and the analytics built on it) is never wiped by accident.
    -- Retire a resource by setting is_active = false instead.
    resource_id   integer not null references resources (resource_id) on delete restrict,
    user_id       uuid not null references profiles (user_id) on delete cascade,
    booking_date  date not null,
    start_time    time not null,
    end_time      time not null,
    purpose       text not null default '',
    status_id     smallint not null default 1 references booking_statuses (status_id),
    created_at    timestamptz not null default now(),

    constraint bookings_end_after_start check (end_time > start_time),

    -- No double-booking, enforced by the database itself: two CONFIRMED
    -- bookings for the same resource may not overlap in time. The app
    -- also checks first so it can show a friendly message; this is the
    -- safety net if two people submit at the same moment.
    constraint bookings_no_overlap exclude using gist (
        resource_id with =,
        tsrange(booking_date + start_time, booking_date + end_time) with &&
    ) where (status_id = 1)
);

create index if not exists idx_bookings_resource_date on bookings (resource_id, booking_date);
create index if not exists idx_bookings_user          on bookings (user_id);
create index if not exists idx_bookings_date          on bookings (booking_date);


-- ---------------- Privacy: lock the tables down ----------------
-- Row Level Security with no policies means nobody can read or write
-- these tables through Supabase's public API key. Only our Python
-- server, which connects with the database password, can reach them.

alter table departments      enable row level security;
alter table resource_types   enable row level security;
alter table booking_statuses enable row level security;
alter table profiles         enable row level security;
alter table resources        enable row level security;
alter table bookings         enable row level security;


-- ---------------- Fixed reference data ----------------

insert into booking_statuses (status_id, code, label) values
    (1, 'confirmed', 'Confirmed'),
    (2, 'completed', 'Completed'),
    (3, 'cancelled', 'Cancelled'),
    (4, 'no_show',   'No show')
on conflict (status_id) do nothing;

-- The five kinds of resource named in the assessment scenario.
insert into resource_types (name, icon) values
    ('Study Room',               '📖'),
    ('Computer Lab',             '💻'),
    ('Specialist Equipment',     '🎥'),
    ('Academic Support Session', '🎓'),
    ('Group-Work Space',         '👥')
on conflict (name) do nothing;

insert into departments (name) values
    ('Library and Learning Resources'),
    ('Engineering'),
    ('Computer Science'),
    ('Business School'),
    ('Media and Communication')
on conflict (name) do nothing;


-- ============================================================
-- OPTIONAL — remove the table left over from the old project.
-- This permanently deletes its rows and cannot be undone.
-- Remove the two dashes below and run this line on its own.
-- ============================================================
-- drop table if exists "User Accounts";
