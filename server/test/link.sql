-- Il link di accesso (migrazione 004) su Postgres vero: lo lancia crediti.test.mjs dopo la 001.
do $$
declare v_lic uuid; v jsonb;
begin
  v_lic := (airender_crea_licenza('hash-acquisto', '3333', 'Studio@Esempio.it', 'pro', 'manuale', 2, 'rif-link')->>'id')::uuid;
  v := airender_licenze_di(' studio@ESEMPIO.it');
  assert jsonb_array_length(v) = 1 and (v->0->>'link_recenti')::int = 0, v::text;
  perform airender_crea_link('g1', v_lic, 15);
  perform airender_crea_link('vecchio', v_lic, -1);
  v := airender_licenze_di('studio@esempio.it');
  assert (v->0->>'link_recenti')::int = 2, v::text;
  assert airender_usa_link('vecchio', 'h-x', 'XXXX') is null, 'scaduto accettato';
  v := airender_usa_link('g1', 'hash-chiave', 'ABCD');
  assert (v->>'id')::uuid = v_lic, coalesce(v::text, 'null');
  assert airender_usa_link('g1', 'hash-chiave2', 'EFGH') is null, 'usato due volte';
  assert (airender_licenza('hash-chiave')->>'id')::uuid = v_lic, 'chiave non apre';
  update chiavi_accesso set revocata_il = now() where hash_codice = 'hash-chiave';
  assert airender_licenza('hash-chiave') is null, 'chiave revocata apre';
  assert (airender_licenza('hash-acquisto')->>'id')::uuid = v_lic, 'codice acquisto rotto';
  raise notice 'link ok';
end $$;
