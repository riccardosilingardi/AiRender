-- AIRENDER: licenze, crediti a lotti, render, movimenti.
--
-- Una licenza e' l'account del cliente: un'email e un codice. Lo stesso
-- codice apre il plugin di Allplan e, quando ci sara', la web app dello
-- Studio: i crediti sono gli stessi, i canali li decide il piano
-- (listino.json, campo "canali").
--
-- I crediti stanno in LOTTI: ogni accredito (benvenuto, piano del mese,
-- prova, ricarica, accredito manuale) e' un lotto con la sua scadenza. Un
-- render consuma dal lotto che scade prima. Il saldo e' la somma dei residui
-- non scaduti meno i render riservati e non ancora chiusi.
--
-- Un render si RISERVA all'invio e si ADDEBITA solo quando il risultato
-- torna con un'immagine. Se il servizio fallisce si ANNULLA. Una riserva mai
-- chiusa smette di contare dopo 24 ore, quanto il Comfy Router tiene un
-- risultato.
--
-- Le tabelle si leggono solo con la chiave di servizio (funzioni Netlify):
-- RLS accesa e nessuna policy, quindi la chiave pubblica non vede niente.
-- Il codice licenza non e' mai salvato in chiaro: solo il suo SHA-256.

create extension if not exists pgcrypto;

create table if not exists licenze (
  id uuid primary key default gen_random_uuid(),
  hash_codice text not null unique,
  ultime_cifre text not null,
  email text not null,
  piano text not null check (piano in ('prova', 'base', 'pro', 'studio', 'nessuno')),
  stato text not null default 'attiva' check (stato in ('attiva', 'sospesa', 'chiusa')),
  origine text not null check (origine in ('stripe', 'manuale')),
  rivenditore text,
  codice_sconto text,
  stripe_cliente text,
  stripe_abbonamento text unique,
  -- La sessione di Checkout (o il riferimento manuale) che l'ha creata: rende
  -- idempotente la creazione quando Stripe ripete lo stesso evento.
  riferimento_creazione text unique,
  postazioni_max int not null default 1 check (postazioni_max >= 1),
  dati_fiscali jsonb not null default '{}'::jsonb,
  email_inviata_il timestamptz,
  creata_il timestamptz not null default now()
);
create index if not exists licenze_email on licenze (lower(email));

create table if not exists postazioni (
  licenza_id uuid not null references licenze (id) on delete cascade,
  postazione text not null,
  canale text not null default 'plugin',
  prima_volta timestamptz not null default now(),
  ultima_volta timestamptz not null default now(),
  primary key (licenza_id, postazione)
);

create table if not exists lotti (
  id bigserial primary key,
  licenza_id uuid not null references licenze (id) on delete cascade,
  origine text not null check (origine in ('benvenuto', 'piano', 'prova', 'ricarica', 'manuale')),
  quantita int not null check (quantita > 0),
  residuo int not null check (residuo >= 0),
  scade_il timestamptz not null,
  riferimento text unique,
  creato_il timestamptz not null default now()
);
create index if not exists lotti_licenza on lotti (licenza_id, scade_il);

create table if not exists render (
  id uuid primary key default gen_random_uuid(),
  licenza_id uuid not null references licenze (id) on delete cascade,
  chiave_idempotenza text not null,
  postazione text,
  canale text not null default 'plugin',
  modello text not null,
  dimensione text not null,
  peso int not null check (peso > 0),
  stato text not null default 'riservato' check (stato in ('riservato', 'addebitato', 'annullato')),
  richiesta_comfy text unique,
  crediti_comfy numeric,
  scoperto int not null default 0,
  creato_il timestamptz not null default now(),
  chiuso_il timestamptz,
  unique (licenza_id, chiave_idempotenza)
);
create index if not exists render_riservati on render (licenza_id) where stato = 'riservato';

create table if not exists movimenti (
  id bigserial primary key,
  licenza_id uuid not null references licenze (id) on delete cascade,
  lotto_id bigint references lotti (id),
  render_id uuid references render (id),
  quantita int not null,
  causale text not null,
  creato_il timestamptz not null default now()
);
create index if not exists movimenti_licenza on movimenti (licenza_id, creato_il);

create table if not exists eventi_stripe (
  id text primary key,
  tipo text not null,
  ricevuto_il timestamptz not null default now()
);

create table if not exists fatture (
  riferimento text primary key,
  licenza_id uuid references licenze (id),
  fic_documento text,
  stato text not null default 'da_creare' check (stato in ('da_creare', 'creata', 'inviata', 'errore')),
  errore text,
  creata_il timestamptz not null default now(),
  aggiornata_il timestamptz not null default now()
);

alter table licenze enable row level security;
alter table postazioni enable row level security;
alter table lotti enable row level security;
alter table render enable row level security;
alter table movimenti enable row level security;
alter table eventi_stripe enable row level security;
alter table fatture enable row level security;

-- Quanto una riserva resta valida: il Router tiene il risultato 24 ore.
create or replace function airender_riserva_valida() returns interval
language sql immutable as $$ select interval '24 hours' $$;

create or replace function airender_saldo(p_licenza uuid) returns jsonb
language sql stable as $$
  select jsonb_build_object(
    'disponibile',
      coalesce((select sum(residuo) from lotti
                where licenza_id = p_licenza and scade_il > now()), 0)
      - coalesce((select sum(peso) from render
                  where licenza_id = p_licenza and stato = 'riservato'
                    and creato_il > now() - airender_riserva_valida()), 0),
    'in_attesa',
      coalesce((select sum(peso) from render
                where licenza_id = p_licenza and stato = 'riservato'
                  and creato_il > now() - airender_riserva_valida()), 0),
    'prossima_scadenza',
      (select jsonb_build_object('quantita', residuo, 'il', scade_il)
       from lotti where licenza_id = p_licenza and scade_il > now() and residuo > 0
       order by scade_il limit 1)
  )
$$;

-- La licenza dal suo codice (gia' ridotto a hash dalla funzione Netlify).
create or replace function airender_licenza(p_hash text) returns jsonb
language sql stable as $$
  select jsonb_build_object(
    'id', l.id, 'email', l.email, 'piano', l.piano, 'stato', l.stato,
    'origine', l.origine, 'rivenditore', l.rivenditore,
    'ultime_cifre', l.ultime_cifre, 'postazioni_max', l.postazioni_max,
    'postazioni_usate', (select count(*) from postazioni p where p.licenza_id = l.id),
    'stripe_cliente', l.stripe_cliente, 'stripe_abbonamento', l.stripe_abbonamento,
    'saldo', airender_saldo(l.id)
  )
  from licenze l where l.hash_codice = p_hash
$$;

create or replace function airender_crea_licenza(
  p_hash text, p_ultime_cifre text, p_email text, p_piano text, p_origine text,
  p_postazioni_max int, p_riferimento text, p_stripe_cliente text default null,
  p_stripe_abbonamento text default null, p_rivenditore text default null,
  p_codice_sconto text default null, p_dati_fiscali jsonb default '{}'::jsonb
) returns jsonb
language plpgsql as $$
declare
  v_id uuid;
begin
  select id into v_id from licenze
   where (p_riferimento is not null and riferimento_creazione = p_riferimento)
      or (p_stripe_abbonamento is not null and stripe_abbonamento = p_stripe_abbonamento);
  if v_id is not null then
    return jsonb_build_object('id', v_id, 'nuova', false);
  end if;
  insert into licenze (hash_codice, ultime_cifre, email, piano, origine, postazioni_max,
                       riferimento_creazione, stripe_cliente, stripe_abbonamento,
                       rivenditore, codice_sconto, dati_fiscali)
  values (p_hash, p_ultime_cifre, p_email, p_piano, p_origine, p_postazioni_max,
          p_riferimento, p_stripe_cliente, p_stripe_abbonamento,
          p_rivenditore, p_codice_sconto, coalesce(p_dati_fiscali, '{}'::jsonb))
  returning id into v_id;
  return jsonb_build_object('id', v_id, 'nuova', true);
end
$$;

-- Accredita un lotto. Lo stesso riferimento (fattura Stripe, sessione,
-- accredito manuale) non accredita due volte.
create or replace function airender_accredita(
  p_licenza uuid, p_origine text, p_quantita int, p_scade_il timestamptz, p_riferimento text
) returns jsonb
language plpgsql as $$
declare
  v_lotto bigint;
begin
  if p_quantita <= 0 then
    raise exception 'quantita deve essere positiva';
  end if;
  insert into lotti (licenza_id, origine, quantita, residuo, scade_il, riferimento)
  values (p_licenza, p_origine, p_quantita, p_quantita, p_scade_il, p_riferimento)
  on conflict (riferimento) do nothing
  returning id into v_lotto;
  if v_lotto is null then
    return jsonb_build_object('accreditato', false);
  end if;
  insert into movimenti (licenza_id, lotto_id, quantita, causale)
  values (p_licenza, v_lotto, p_quantita, p_origine);
  return jsonb_build_object('accreditato', true, 'lotto', v_lotto);
end
$$;

-- Riserva un render. Controlla stato, postazioni e saldo sotto lo stesso
-- blocco della licenza: due invii insieme non spendono lo stesso credito.
create or replace function airender_riserva(
  p_licenza uuid, p_postazione text, p_canale text, p_chiave text,
  p_modello text, p_dimensione text, p_peso int
) returns jsonb
language plpgsql as $$
declare
  v_lic licenze%rowtype;
  v_render render%rowtype;
  v_usate int;
  v_disponibile int;
begin
  select * into v_lic from licenze where id = p_licenza for update;
  if not found then
    return jsonb_build_object('esito', 'licenza_sconosciuta');
  end if;
  if v_lic.stato <> 'attiva' then
    return jsonb_build_object('esito', 'licenza_' || v_lic.stato);
  end if;

  -- Lo stesso invio ripetuto (stessa Idempotency-Key) non riserva due volte.
  select * into v_render from render where licenza_id = p_licenza and chiave_idempotenza = p_chiave;
  if found then
    return jsonb_build_object('esito', 'ok', 'render', v_render.id, 'ripetuto', true,
                              'richiesta_comfy', v_render.richiesta_comfy, 'stato', v_render.stato);
  end if;

  if p_postazione is not null and p_postazione <> '' then
    if not exists (select 1 from postazioni where licenza_id = p_licenza and postazione = p_postazione) then
      select count(*) into v_usate from postazioni where licenza_id = p_licenza;
      if v_usate >= v_lic.postazioni_max then
        return jsonb_build_object('esito', 'postazioni', 'usate', v_usate, 'massimo', v_lic.postazioni_max);
      end if;
      insert into postazioni (licenza_id, postazione, canale) values (p_licenza, p_postazione, p_canale);
    else
      update postazioni set ultima_volta = now() where licenza_id = p_licenza and postazione = p_postazione;
    end if;
  end if;

  v_disponibile := (airender_saldo(p_licenza) ->> 'disponibile')::int;
  if v_disponibile < p_peso then
    return jsonb_build_object('esito', 'saldo', 'disponibile', v_disponibile, 'peso', p_peso);
  end if;

  insert into render (licenza_id, chiave_idempotenza, postazione, canale, modello, dimensione, peso)
  values (p_licenza, p_chiave, p_postazione, p_canale, p_modello, p_dimensione, p_peso)
  returning * into v_render;
  return jsonb_build_object('esito', 'ok', 'render', v_render.id, 'ripetuto', false,
                            'disponibile', v_disponibile - p_peso);
end
$$;

create or replace function airender_avvia(p_render uuid, p_richiesta text) returns void
language sql as $$
  update render set richiesta_comfy = p_richiesta where id = p_render and richiesta_comfy is null
$$;

create or replace function airender_annulla(p_render uuid) returns void
language sql as $$
  update render set stato = 'annullato', chiuso_il = now() where id = p_render and stato = 'riservato'
$$;

-- Il render della licenza a cui appartiene la richiesta del Router: chi
-- legge stato e risultato deve essere chi l'ha mandata.
create or replace function airender_render_di(p_licenza uuid, p_richiesta text) returns jsonb
language sql stable as $$
  select to_jsonb(r) from render r where r.licenza_id = p_licenza and r.richiesta_comfy = p_richiesta
$$;

-- Addebita un render riuscito, consumando dai lotti che scadono prima.
-- Idempotente: un render gia' addebitato non si paga due volte. Se un lotto
-- e' scaduto fra la riserva e il risultato e il credito non basta, il render
-- si chiude lo stesso e la differenza resta scritta in "scoperto".
create or replace function airender_addebita(p_render uuid, p_crediti_comfy numeric default null) returns jsonb
language plpgsql as $$
declare
  v_render render%rowtype;
  v_lotto record;
  v_resta int;
  v_preso int;
begin
  select * into v_render from render where id = p_render;
  if not found then
    return jsonb_build_object('esito', 'render_sconosciuto');
  end if;
  perform 1 from licenze where id = v_render.licenza_id for update;
  select * into v_render from render where id = p_render for update;
  if v_render.stato = 'addebitato' then
    return jsonb_build_object('esito', 'ok', 'ripetuto', true,
                              'saldo', airender_saldo(v_render.licenza_id));
  end if;

  v_resta := v_render.peso;
  for v_lotto in
    select id, residuo from lotti
     where licenza_id = v_render.licenza_id and scade_il > now() and residuo > 0
     order by scade_il, id
     for update
  loop
    exit when v_resta = 0;
    v_preso := least(v_lotto.residuo, v_resta);
    update lotti set residuo = residuo - v_preso where id = v_lotto.id;
    insert into movimenti (licenza_id, lotto_id, render_id, quantita, causale)
    values (v_render.licenza_id, v_lotto.id, p_render, -v_preso, 'render');
    v_resta := v_resta - v_preso;
  end loop;

  update render set stato = 'addebitato', chiuso_il = now(), crediti_comfy = p_crediti_comfy,
                    scoperto = v_resta
   where id = p_render;
  return jsonb_build_object('esito', 'ok', 'ripetuto', false, 'scoperto', v_resta,
                            'saldo', airender_saldo(v_render.licenza_id));
end
$$;

-- Un evento Stripe gia' visto si salta: Stripe ripete gli eventi.
create or replace function airender_evento_nuovo(p_id text, p_tipo text) returns boolean
language plpgsql as $$
begin
  insert into eventi_stripe (id, tipo) values (p_id, p_tipo);
  return true;
exception when unique_violation then
  return false;
end
$$;

-- Bucket per i risultati troppo pesanti per la risposta di una funzione
-- Netlify (6 MB): l'immagine si carica qui e il plugin la scarica da un link
-- firmato. Privato. Su un Postgres senza Supabase lo schema storage manca e
-- il blocco non fa niente.
do $$
begin
  if exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    insert into storage.buckets (id, name, public) values ('risultati', 'risultati', false)
    on conflict (id) do nothing;
  end if;
end
$$;
