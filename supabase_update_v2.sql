-- Update for version 2 (employee registration + notifications).
-- Run once in Supabase: SQL Editor → New query → paste → Run.
-- Your existing tasks are not touched.

create table if not exists public.users (
    name_key    text primary key,   -- lowercase name, so "Arun" and "arun" are the same person
    name        text not null,
    pin_hash    text not null,      -- the PIN is stored scrambled, never as plain text
    created_at  text,
    last_seen   text                -- used for the 🔔 "new" notifications
);

alter table public.users enable row level security;
