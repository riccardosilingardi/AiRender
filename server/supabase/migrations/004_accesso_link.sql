-- AIRENDER: accesso alla web app con un link via email.
--
-- Il codice licenza nel database c'e' solo come SHA-256: il server non puo'
-- rimandarlo. Chi entra col link riceve allora una chiave sua, nella stessa
-- forma AIR-XXXX-XXXX-XXXX-XXXX, legata alla stessa licenza: il plugin e lo
-- Studio la usano come il codice (stesso saldo, stesse postazioni), e la si
-- puo' revocare da sola senza toccare il codice dell'acquisto.
--
-- Il link porta un gettone casuale; qui ne sta solo lo SHA-256. Vale una
-- volta sola e per pochi minuti (LINK_ACCESSO_MINUTI in core/config.py, nel
-- listino come accesso.link_minuti).

create table if not exists link_accesso (
  hash_gettone text primary key,
  licenza_id uuid not null references licenze (id) on delete cascade,
  creato_il timestamptz not null default now(),
  scade_il timestamptz not null,
  usato_il timestamptz
);
create index if not exists link_accesso_licenza on link_accesso (licenza_id, creato_il);

create table if not exists chiavi_accesso (
  hash_codice text primary key,
  licenza_id uuid not null references licenze (id) on delete cascade,
  ultime_cifre text not null,
  creata_il timestamptz not null default now(),
  revocata_il timestamptz
);
create index if not exists chiavi_accesso_licenza on chiavi_accesso (licenza_id);

alter table link_accesso enable row level security;
alter table chiavi_accesso enable row level security;

-- La licenza dal codice dell'acquisto o da una chiave di accesso non revocata.
create or replace function airender_licenza(p_hash text) returns jsonb
language sql stable set search_path = public as $$
  select jsonb_build_object(
    'id', l.id, 'email', l.email, 'piano', l.piano, 'stato', l.stato,
    'origine', l.origine, 'rivenditore', l.rivenditore,
    'ultime_cifre', l.ultime_cifre, 'postazioni_max', l.postazioni_max,
    'postazioni_usate', (select count(*) from postazioni p where p.licenza_id = l.id),
    'stripe_cliente', l.stripe_cliente, 'stripe_abbonamento', l.stripe_abbonamento,
    'saldo', airender_saldo(l.id)
  )
  from licenze l
  where l.hash_codice = p_hash
     or l.id = (select c.licenza_id from chiavi_accesso c
                 where c.hash_codice = p_hash and c.revocata_il is null)
  limit 1
$$;

-- Le licenze attive di un'email (senza distinguere maiuscole), per il link.
create or replace function airender_licenze_di(p_email text) returns jsonb
language sql stable set search_path = public as $$
  select coalesce(jsonb_agg(jsonb_build_object(
    'id', l.id, 'piano', l.piano, 'ultime_cifre', l.ultime_cifre,
    'link_recenti', (select count(*) from link_accesso a
                      where a.licenza_id = l.id and a.creato_il > now() - interval '1 hour')
  ) order by l.creata_il desc), '[]'::jsonb)
  from licenze l
  where lower(l.email) = lower(trim(p_email)) and l.stato = 'attiva'
$$;

create or replace function airender_crea_link(p_hash_gettone text, p_licenza uuid, p_minuti int) returns void
language sql set search_path = public as $$
  insert into link_accesso (hash_gettone, licenza_id, scade_il)
  values (p_hash_gettone, p_licenza, now() + make_interval(mins => p_minuti))
$$;

-- Usa il link (una volta sola, se non e' scaduto) e crea la chiave del
-- browser. Torna la licenza come airender_licenza, o null.
create or replace function airender_usa_link(p_hash_gettone text, p_hash_chiave text, p_ultime_cifre text)
returns jsonb language plpgsql set search_path = public as $$
declare
  v_licenza uuid;
begin
  update link_accesso set usato_il = now()
   where hash_gettone = p_hash_gettone and usato_il is null and scade_il > now()
  returning licenza_id into v_licenza;
  if v_licenza is null then
    return null;
  end if;
  insert into chiavi_accesso (hash_codice, licenza_id, ultime_cifre)
  values (p_hash_chiave, v_licenza, p_ultime_cifre);
  return airender_licenza(p_hash_chiave);
end
$$;

do $$
declare
  f text;
begin
  foreach f in array array[
    'airender_licenza(text)', 'airender_licenze_di(text)',
    'airender_crea_link(text, uuid, int)', 'airender_usa_link(text, text, text)'
  ] loop
    execute format('revoke all on function %s from public', f);
    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on function %s from anon', f);
    end if;
    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute format('revoke all on function %s from authenticated', f);
    end if;
    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant execute on function %s to service_role', f);
    end if;
  end loop;
end
$$;
