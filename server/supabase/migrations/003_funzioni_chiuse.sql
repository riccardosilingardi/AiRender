-- AIRENDER: le funzioni dei crediti le chiama solo il server.
--
-- Supabase espone ogni funzione dello schema public anche alla chiave
-- pubblica (ruoli anon e authenticated). Le tabelle hanno RLS senza policy,
-- quindi una chiamata dalla chiave pubblica non leggerebbe ne' scriverebbe
-- niente; ma una funzione del registro dei crediti non deve essere
-- raggiungibile da fuori per nessuna ragione. Qui si toglie l'esecuzione a
-- tutti tranne service_role (le funzioni Netlify) e si fissa search_path,
-- come chiede il controllo di sicurezza di Supabase (lint 0011).

do $$
declare
  f record;
  ruoli text;
begin
  select string_agg(quote_ident(r), ', ') into ruoli
    from unnest(array['anon', 'authenticated']) r
   where exists (select 1 from pg_roles where rolname = r);
  for f in
    select p.oid::regprocedure as firma, p.proconfig as config
      from pg_proc p join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public' and p.proname like 'airender\_%'
  loop
    if f.config is null then
      execute format('alter function %s set search_path = public', f.firma);
    end if;
    execute format('revoke all on function %s from public', f.firma);
    if ruoli is not null then
      execute format('revoke all on function %s from %s', f.firma, ruoli);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f.firma);
    end if;
  end loop;
end
$$;
