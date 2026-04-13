create extension if not exists pgcrypto;

create table if not exists public.chat_rooms (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  description text not null default '',
  created_at timestamptz not null default now()
);

create table if not exists public.chat_invites (
  id uuid primary key default gen_random_uuid(),
  token text not null unique,
  room_id uuid not null references public.chat_rooms(id) on delete cascade,
  label text,
  max_uses integer,
  use_count integer not null default 0,
  expires_at timestamptz,
  revoked boolean not null default false,
  created_at timestamptz not null default now(),
  constraint chat_invites_max_uses_check check (max_uses is null or max_uses > 0)
);

create index if not exists idx_chat_invites_room_id on public.chat_invites(room_id);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  room_id uuid not null references public.chat_rooms(id) on delete cascade,
  nickname text not null,
  body text not null default '' check (char_length(body) <= 400),
  image_url text,
  image_path text,
  created_at timestamptz not null default now(),
  deleted boolean not null default false,
  constraint chat_messages_content_check check (
    char_length(body) between 1 and 400
    or image_url is not null
  )
);

create index if not exists idx_chat_messages_room_created_at on public.chat_messages(room_id, created_at desc);

create table if not exists public.chat_rate_limits (
  session_id text primary key,
  last_post_at timestamptz not null default now()
);

alter table public.chat_rooms enable row level security;
alter table public.chat_invites enable row level security;
alter table public.chat_messages enable row level security;
alter table public.chat_rate_limits enable row level security;

create policy "chat_rooms_select_all"
on public.chat_rooms
for select
using (true);

create policy "chat_invites_select_all"
on public.chat_invites
for select
using (true);

create policy "chat_messages_select_all"
on public.chat_messages
for select
using (true);

create policy "chat_messages_insert_all"
on public.chat_messages
for insert
with check (
  (char_length(body) between 1 and 400)
  or image_url is not null
);

create policy "chat_rate_limits_select_all"
on public.chat_rate_limits
for select
using (true);

create policy "chat_rate_limits_insert_all"
on public.chat_rate_limits
for insert
with check (true);

create policy "chat_rate_limits_update_all"
on public.chat_rate_limits
for update
using (true)
with check (true);

insert into public.chat_rooms (slug, title, description)
values ('lobby', '匿名小圈圈聊天室', '用邀請連結進入，匿名但不裸奔。')
on conflict (slug) do nothing;
