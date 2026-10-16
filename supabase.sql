-- Roadster: open world ranking for the self-hosted version.
-- Run once in your Supabase project (SQL Editor -> New query -> paste -> Run),
-- then paste the project URL and anon key into SUPABASE_URL / SUPABASE_KEY in index.html.

create extension if not exists pgcrypto with schema extensions;

create table if not exists public.scores (
  name        text primary key check (name ~ '^[A-Z0-9ÁÉÍÓÚÜÑ _.\-]{1,14}$'),
  token_hash  text not null,                     -- sha256 of the device token that owns the name
  total       integer not null default 0,
  passed      integer not null default 0,
  bests       jsonb not null default '{}'::jsonb,
  updated_at  timestamptz not null default now()
);

-- Everyone reads the ranking; nobody writes the table directly (only through submit_score).
alter table public.scores enable row level security;
drop policy if exists "ranking is public" on public.scores;
create policy "ranking is public" on public.scores for select using (true);
revoke all on public.scores from anon, authenticated;
grant select (name, total, passed, updated_at) on public.scores to anon, authenticated;

-- One place per name: the first device to submit a name owns it; later scores only go up.
create or replace function public.submit_score(p_name text, p_token text, p_total integer, p_passed integer, p_bests jsonb)
returns text
language plpgsql
security definer
set search_path = public, extensions
as $$
declare
  h   text := encode(digest(coalesce(p_token, ''), 'sha256'), 'hex');
  cur public.scores;
begin
  if p_name !~ '^[A-Z0-9ÁÉÍÓÚÜÑ _.\-]{1,14}$' or char_length(coalesce(p_token, '')) < 16 then return 'invalid'; end if;
  if p_total < 0 or p_total > 14000 or p_passed < 0 or p_passed > 8 then return 'invalid'; end if;

  select * into cur from public.scores where name = p_name;
  if not found then
    insert into public.scores (name, token_hash, total, passed, bests)
    values (p_name, h, p_total, p_passed, coalesce(p_bests, '{}'::jsonb));
    return 'ok';
  end if;

  if cur.token_hash <> h then return 'taken'; end if;

  update public.scores
     set total = greatest(total, p_total),
         passed = greatest(passed, p_passed),
         bests = case when p_total >= total then coalesce(p_bests, bests) else bests end,
         updated_at = now()
   where name = p_name;
  return 'ok';
end;
$$;

revoke all on function public.submit_score(text, text, integer, integer, jsonb) from public;
grant execute on function public.submit_score(text, text, integer, integer, jsonb) to anon, authenticated;

-- House record to beat. Its token is random, so nobody can overwrite it from the game.
insert into public.scores (name, token_hash, total, passed, bests)
values ('ZANI', encode(digest(gen_random_uuid()::text, 'sha256'), 'hex'), 10988, 8,
        '{"0":1436,"1":1418,"2":1362,"3":1395,"4":1371,"5":1344,"6":1359,"7":1303}')
on conflict (name) do nothing;
