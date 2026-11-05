// Supabase: le funzioni SQL di supabase/migrations/001_crediti.sql chiamate
// via PostgREST con la chiave di servizio, e lo Storage per i risultati
// troppo pesanti. La chiave di servizio vive solo nelle variabili d'ambiente
// di Netlify.

import { serve } from "./ambiente.mjs";

export function creaDb(ambiente = process.env, chiama = fetch) {
  const base = () => serve("SUPABASE_URL", ambiente).replace(/\/$/, "");
  const chiave = () => serve("SUPABASE_SERVICE_ROLE_KEY", ambiente);
  const intestazioni = () => ({ apikey: chiave(), authorization: `Bearer ${chiave()}` });

  async function rpc(nome, argomenti = {}) {
    const r = await chiama(`${base()}/rest/v1/rpc/${nome}`, {
      method: "POST",
      headers: { ...intestazioni(), "content-type": "application/json" },
      body: JSON.stringify(argomenti),
    });
    const testo = await r.text();
    if (!r.ok) throw new Error(`Supabase ${nome}: ${r.status} ${testo.slice(0, 300)}`);
    return testo ? JSON.parse(testo) : null;
  }

  async function select(tabella, query) {
    const r = await chiama(`${base()}/rest/v1/${tabella}?${query}`, { headers: intestazioni() });
    if (!r.ok) throw new Error(`Supabase ${tabella}: ${r.status} ${(await r.text()).slice(0, 300)}`);
    return r.json();
  }

  async function aggiorna(tabella, query, valori) {
    const r = await chiama(`${base()}/rest/v1/${tabella}?${query}`, {
      method: "PATCH",
      headers: { ...intestazioni(), "content-type": "application/json", prefer: "return=minimal" },
      body: JSON.stringify(valori),
    });
    if (!r.ok) throw new Error(`Supabase ${tabella}: ${r.status} ${(await r.text()).slice(0, 300)}`);
  }

  async function inserisci(tabella, valori, suConflitto = "") {
    const q = suConflitto ? `?on_conflict=${suConflitto}` : "";
    const r = await chiama(`${base()}/rest/v1/${tabella}${q}`, {
      method: "POST",
      headers: {
        ...intestazioni(), "content-type": "application/json",
        prefer: suConflitto ? "resolution=merge-duplicates,return=minimal" : "return=minimal",
      },
      body: JSON.stringify(valori),
    });
    if (!r.ok) throw new Error(`Supabase ${tabella}: ${r.status} ${(await r.text()).slice(0, 300)}`);
  }

  // Carica un file nel bucket privato "risultati" e ne restituisce un link
  // firmato che scade.
  async function caricaRisultato(percorso, byte, tipo, secondi) {
    const su = await chiama(`${base()}/storage/v1/object/risultati/${percorso}`, {
      method: "POST",
      headers: { ...intestazioni(), "content-type": tipo, "x-upsert": "true" },
      body: byte,
    });
    if (!su.ok) throw new Error(`Supabase Storage: ${su.status} ${(await su.text()).slice(0, 300)}`);
    const firma = await chiama(`${base()}/storage/v1/object/sign/risultati/${percorso}`, {
      method: "POST",
      headers: { ...intestazioni(), "content-type": "application/json" },
      body: JSON.stringify({ expiresIn: secondi }),
    });
    if (!firma.ok) throw new Error(`Supabase Storage: ${firma.status} ${(await firma.text()).slice(0, 300)}`);
    const { signedURL } = await firma.json();
    return `${base()}/storage/v1${signedURL}`;
  }

  // Cancella dal bucket "risultati" i file indicati (al massimo 1000 per
  // chiamata, il limite dell'API dello Storage).
  async function rimuoviRisultati(nomi) {
    if (!nomi.length) return;
    const r = await chiama(`${base()}/storage/v1/object/risultati`, {
      method: "DELETE",
      headers: { ...intestazioni(), "content-type": "application/json" },
      body: JSON.stringify({ prefixes: nomi }),
    });
    if (!r.ok) throw new Error(`Supabase Storage: ${r.status} ${(await r.text()).slice(0, 300)}`);
  }

  return { rpc, select, aggiorna, inserisci, caricaRisultato, rimuoviRisultati };
}
