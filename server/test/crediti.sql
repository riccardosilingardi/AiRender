-- Prova delle funzioni SQL su un Postgres vero (senza Supabase). Si lancia
-- da test/crediti.test.mjs dentro una transazione che alla fine si annulla.
\set ON_ERROR_STOP on
begin;

do $$
declare
  v jsonb;
  v_lic uuid;
  v_r1 uuid;
  v_r2 uuid;
begin
  -- licenza nuova e ripetuta sullo stesso riferimento
  v := airender_crea_licenza('h1', 'ABCD', 'a@b.it', 'pro', 'stripe', 1, 'cs_1');
  assert (v->>'nuova')::boolean, 'la prima creazione e'' nuova';
  v_lic := (v->>'id')::uuid;
  v := airender_crea_licenza('h2', 'EFGH', 'a@b.it', 'pro', 'stripe', 1, 'cs_1');
  assert not (v->>'nuova')::boolean and (v->>'id')::uuid = v_lic, 'stesso riferimento, stessa licenza';

  -- accredito idempotente
  v := airender_accredita(v_lic, 'benvenuto', 10, now() + interval '12 months', 'benvenuto:x');
  assert (v->>'accreditato')::boolean;
  v := airender_accredita(v_lic, 'benvenuto', 10, now() + interval '12 months', 'benvenuto:x');
  assert not (v->>'accreditato')::boolean, 'stesso riferimento non accredita due volte';
  assert (airender_saldo(v_lic)->>'disponibile')::int = 10;

  -- un lotto scaduto non conta
  perform airender_accredita(v_lic, 'piano', 5, now() - interval '1 day', 'vecchio');
  assert (airender_saldo(v_lic)->>'disponibile')::int = 10, 'il lotto scaduto non conta';
  -- un lotto che scade prima si consuma per primo
  perform airender_accredita(v_lic, 'piano', 3, now() + interval '5 days', 'mese');

  -- riserva: il peso esce dal disponibile ma non dai lotti
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k1', 'm', '1K', 2);
  assert v->>'esito' = 'ok', v::text;
  v_r1 := (v->>'render')::uuid;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 11;
  assert (airender_saldo(v_lic)->>'in_attesa')::int = 2;

  -- stessa Idempotency-Key: nessuna seconda riserva
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k1', 'm', '1K', 2);
  assert (v->>'ripetuto')::boolean and (v->>'render')::uuid = v_r1;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 11;

  -- seconda postazione oltre il massimo (1)
  v := airender_riserva(v_lic, 'pc-2', 'plugin', 'k2', 'm', '1K', 1);
  assert v->>'esito' = 'postazioni', v::text;

  -- addebito: consuma dal lotto che scade prima (3 -> 1), idempotente
  perform airender_avvia(v_r1, 'req-1');
  assert (airender_render_di(v_lic, 'req-1')->>'id')::uuid = v_r1;
  v := airender_addebita(v_r1, 17.17);
  assert v->>'esito' = 'ok' and not (v->>'ripetuto')::boolean;
  assert (select residuo from lotti where riferimento = 'mese') = 1, 'consumato prima il lotto che scade prima';
  v := airender_addebita(v_r1, 17.17);
  assert (v->>'ripetuto')::boolean, 'secondo addebito ignorato';
  assert (airender_saldo(v_lic)->>'disponibile')::int = 11;
  assert (airender_saldo(v_lic)->>'in_attesa')::int = 0;
  assert (select sum(quantita) from movimenti where render_id = v_r1) = -2;

  -- annullo: la riserva torna disponibile
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k3', 'm', '4K', 3);
  v_r2 := (v->>'render')::uuid;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 8;
  perform airender_annulla(v_r2);
  assert (airender_saldo(v_lic)->>'disponibile')::int = 11;
  -- un render annullato non si addebita... ma airender_addebita non lo
  -- impedisce: il router chiama addebita solo con un'immagine in mano.

  -- saldo insufficiente
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k4', 'm', '4K', 50);
  assert v->>'esito' = 'saldo' and (v->>'disponibile')::int = 11, v::text;

  -- una riserva vecchia di piu' di 24 ore non trattiene piu' credito
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k5', 'm', '1K', 4);
  update render set creato_il = now() - interval '25 hours' where id = (v->>'render')::uuid;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 11;

  -- licenza sospesa
  update licenze set stato = 'sospesa' where id = v_lic;
  v := airender_riserva(v_lic, 'pc-1', 'plugin', 'k6', 'm', '1K', 1);
  assert v->>'esito' = 'licenza_sospesa', v::text;

  -- la licenza letta dall'hash
  v := airender_licenza('h1');
  assert v->>'piano' = 'pro' and (v->>'postazioni_usate')::int = 1;
  assert airender_licenza('niente') is null;

  -- evento Stripe ripetuto
  assert airender_evento_nuovo('evt_1', 'invoice.paid');
  assert not airender_evento_nuovo('evt_1', 'invoice.paid');

  raise notice 'crediti.sql: tutto a posto';
end
$$;

rollback;
