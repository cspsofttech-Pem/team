-- Run this once in Supabase: SQL Editor → New query → paste → Run.
-- It creates the shared "tasks" table the app uses.

create table if not exists public.tasks (
    id            text primary key,
    title         text not null,
    description   text,
    priority      text not null default 'Medium',
    due           text,          -- YYYY-MM-DD
    assignee      text,
    status        text not null default 'To Do',
    created_at    text,
    created_by    text,
    updated_at    text,
    updated_by    text,
    completed_at  text
);

-- Keep the table locked to the public internet. The app connects with the
-- secret (service_role) key, which is only stored in Streamlit's Secrets.
alter table public.tasks enable row level security;

-- Employees who register in the app
create table if not exists public.users (
    name_key    text primary key,   -- lowercase name, so "Arun" and "arun" are the same person
    name        text not null,
    pin_hash    text not null,      -- the PIN is stored scrambled, never as plain text
    created_at  text,
    last_seen   text                -- used for the 🔔 "new" notifications
);

alter table public.users enable row level security;
