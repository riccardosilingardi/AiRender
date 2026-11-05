-- AIRENDER: pulizia dei risultati salvati nello Storage.
--
-- Un risultato piu' pesante di 4,5 MB non sta nella risposta di una funzione
-- Netlify: il router lo carica nel bucket privato "risultati" e da' al plugin
-- un link firmato che vale 24 ore. Dopo, il file non serve a nessuno e non
-- deve restare: e' l'immagine di un progetto del cliente (GDPR,
-- minimizzazione). La funzione programmata netlify/functions/pulizia.mjs
-- chiede qui i nomi dei file piu' vecchi e li cancella con l'API dello
-- Storage (cancellare le righe di storage.objects a mano lascerebbe il file).

create or replace function airender_risultati_vecchi(p_ore int default 24, p_quanti int default 500)
returns setof text
language sql security definer set search_path = public, storage as $$
  select name from storage.objects
   where bucket_id = 'risultati' and created_at < now() - make_interval(hours => p_ore)
   order by created_at
   limit p_quanti
$$;

revoke all on function airender_risultati_vecchi(int, int) from public, anon, authenticated;
