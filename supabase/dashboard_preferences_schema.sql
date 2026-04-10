create extension if not exists pgcrypto;

create table if not exists public.dashboard_preferences (
  id uuid primary key default gen_random_uuid(),
  profile_id text not null unique default 'default',
  visible_cards jsonb not null default '["quotes","weather","feed","flight","trump","guestbook"]'::jsonb,
  card_order jsonb not null default '["quotes","weather","feed","flight","trump","guestbook"]'::jsonb,
  collapsed_cards jsonb not null default '["weather"]'::jsonb,
  theme text,
  flight_origin text not null default 'TPE',
  flight_regions jsonb not null default '["日本","韓國","東南亞"]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.dashboard_preferences enable row level security;

create policy "dashboard_preferences_select_all"
on public.dashboard_preferences
for select
using (true);

create policy "dashboard_preferences_insert_all"
on public.dashboard_preferences
for insert
with check (true);

create policy "dashboard_preferences_update_all"
on public.dashboard_preferences
for update
using (true)
with check (true);

insert into public.dashboard_preferences (profile_id)
values ('default')
on conflict (profile_id) do nothing;
