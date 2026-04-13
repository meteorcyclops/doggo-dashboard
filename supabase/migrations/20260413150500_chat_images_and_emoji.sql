alter table public.chat_messages
  add column if not exists image_url text,
  add column if not exists image_path text;

alter table public.chat_messages
  drop constraint if exists chat_messages_content_check;

alter table public.chat_messages
  alter column body set default '';

alter table public.chat_messages
  add constraint chat_messages_content_check check (
    char_length(body) between 1 and 400
    or image_url is not null
  );

alter table public.chat_messages
  drop constraint if exists chat_messages_body_check;

create policy if not exists "chat_messages_insert_all"
on public.chat_messages
for insert
with check (
  (char_length(body) between 1 and 400)
  or image_url is not null
);
