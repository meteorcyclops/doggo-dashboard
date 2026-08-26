alter table public.guestbook_notes
  drop constraint if exists guestbook_notes_nickname_length_check;

alter table public.guestbook_notes
  add constraint guestbook_notes_nickname_length_check
  check (char_length(btrim(nickname)) between 1 and 24);

drop policy if exists "guestbook_insert_all" on public.guestbook_notes;

create table if not exists public.guestbook_rate_limits (
  client_hash text not null,
  action text not null check (action in ('submit', 'delete')),
  window_start timestamptz not null,
  created_at timestamptz not null default now(),
  primary key (client_hash, action, window_start)
);

alter table public.guestbook_rate_limits enable row level security;
revoke all on table public.guestbook_rate_limits from anon, authenticated;

create index if not exists guestbook_rate_limits_created_at_idx
  on public.guestbook_rate_limits (created_at);
