-- AIRENDER: tetto ai rimborsi dei render senza immagine.
--
-- Un render che torna dal Router senza immagine (Gemini rifiuta, risponde
-- solo testo) non si paga: la riserva si annulla. Ma Comfy quel lavoro lo
-- puo' far pagare a Riccardo lo stesso, e chi lo scopre potrebbe mandare
-- apposta richieste che finiscono vuote. Quindi il rimborso vale fino a un
-- tetto per licenza nelle ultime 24 ore (p_tetto, dal listino: core/config.py,
-- LISTINO["rimborsi_senza_immagine_24h"]); oltre, il render vuoto si addebita
-- come uno riuscito.
--
-- Contano solo i render chiusi senza immagine (senza_immagine = true): un
-- invio che il Router rifiuta, o il lavoro fermato dal cliente, restano
-- rimborsati sempre e non consumano il tetto.

alter table render add column if not exists senza_immagine boolean not null default false;
create index if not exists render_senza_immagine on render (licenza_id, chiuso_il) where senza_immagine;

create or replace function airender_chiudi_senza_immagine(p_render uuid, p_tetto int, p_crediti_comfy numeric default null)
returns jsonb
language plpgsql
set search_path = public
as $$
declare
  v_render render%rowtype;
  v_rimborsati int;
  v jsonb;
begin
  select * into v_render from render where id = p_render;
  if not found then
    return jsonb_build_object('esito', 'render_sconosciuto');
  end if;
  -- Lo stesso ordine di airender_addebita: prima la licenza, poi il render,
  -- cosi' due letture insieme non superano il tetto.
  perform 1 from licenze where id = v_render.licenza_id for update;
  select * into v_render from render where id = p_render for update;

  if v_render.stato = 'annullato' then
    return jsonb_build_object('esito', 'ok', 'rimborsato', true, 'ripetuto', true,
                              'saldo', airender_saldo(v_render.licenza_id));
  end if;
  if v_render.stato = 'addebitato' then
    return jsonb_build_object('rimborsato', false) || airender_addebita(p_render, p_crediti_comfy);
  end if;

  select count(*) into v_rimborsati from render
   where licenza_id = v_render.licenza_id and senza_immagine and stato = 'annullato'
     and chiuso_il > now() - interval '24 hours';

  if v_rimborsati < p_tetto then
    update render set stato = 'annullato', senza_immagine = true, chiuso_il = now(),
                      crediti_comfy = p_crediti_comfy
     where id = p_render;
    return jsonb_build_object('esito', 'ok', 'rimborsato', true, 'ripetuto', false,
                              'rimborsati_24h', v_rimborsati + 1,
                              'saldo', airender_saldo(v_render.licenza_id));
  end if;

  update render set senza_immagine = true where id = p_render;
  v := airender_addebita(p_render, p_crediti_comfy);
  return jsonb_build_object('rimborsato', false, 'rimborsati_24h', v_rimborsati) || v;
end
$$;

do $$
declare
  f text := 'airender_chiudi_senza_immagine(uuid, int, numeric)';
begin
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
end
$$;
