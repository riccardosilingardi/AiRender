-- Il tetto ai rimborsi dei render senza immagine (migrazione 005) su Postgres
-- vero: lo lancia crediti.test.mjs dopo la 001, dentro una transazione che
-- alla fine si annulla.
begin;

do $$
declare v_lic uuid; v_r uuid; v jsonb; i int;
begin
  v_lic := (airender_crea_licenza('hash-tetto', '4444', 'tetto@esempio.it', 'pro', 'manuale', 1, 'rif-tetto')->>'id')::uuid;
  perform airender_accredita(v_lic, 'manuale', 20, now() + interval '30 days', 'lotto-tetto');

  -- un invio rifiutato dal Router si annulla e non consuma il tetto
  v_r := (airender_riserva(v_lic, 'pc', 'plugin', 'rifiutato', 'm', '1K', 1)->>'render')::uuid;
  perform airender_annulla(v_r);

  -- tetto 2: i primi due vuoti si rimborsano, il terzo si paga
  for i in 1..3 loop
    v_r := (airender_riserva(v_lic, 'pc', 'plugin', 'vuoto-' || i, 'm', '1K', 1)->>'render')::uuid;
    v := airender_chiudi_senza_immagine(v_r, 2);
    if i <= 2 then
      assert (v->>'rimborsato')::boolean and (v->>'rimborsati_24h')::int = i, v::text;
    else
      assert not (v->>'rimborsato')::boolean and v->>'esito' = 'ok' and not (v->>'ripetuto')::boolean, v::text;
    end if;
  end loop;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 19, (airender_saldo(v_lic))::text;

  -- la stessa lettura ripetuta non paga due volte
  v := airender_chiudi_senza_immagine(v_r, 2);
  assert (v->>'ripetuto')::boolean and not (v->>'rimborsato')::boolean, v::text;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 19;

  -- dopo 24 ore il tetto si libera
  update render set chiuso_il = now() - interval '25 hours' where licenza_id = v_lic and senza_immagine;
  v_r := (airender_riserva(v_lic, 'pc', 'plugin', 'vuoto-dopo', 'm', '1K', 1)->>'render')::uuid;
  v := airender_chiudi_senza_immagine(v_r, 2);
  assert (v->>'rimborsato')::boolean and (v->>'rimborsati_24h')::int = 1, v::text;
  assert (airender_saldo(v_lic)->>'disponibile')::int = 19;
  raise notice 'tetto rimborsi ok';
end $$;

rollback;
