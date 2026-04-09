create extension if not exists pgcrypto;

create table if not exists public.guestbook_notes (
  id uuid primary key default gen_random_uuid(),
  nickname text not null default '匿名訪客',
  message text not null check (char_length(message) between 1 and 220),
  created_at timestamptz not null default now()
);

alter table public.guestbook_notes enable row level security;

create policy "guestbook_select_all"
on public.guestbook_notes
for select
using (true);

create policy "guestbook_insert_all"
on public.guestbook_notes
for insert
with check (char_length(message) between 1 and 220);
