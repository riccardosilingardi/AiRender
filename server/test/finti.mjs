// Doppi per i test: un database in memoria che imita le funzioni SQL (la
// loro logica vera e' provata su Postgres in crediti.test.mjs), e un fetch
// che risponde da una tabella.

import { createHmac } from "node:crypto";

export function dbFinto() {
  const stato = { licenze: [], lotti: [], render: [], fatture: [], chiamate: [], caricati: [], link_accesso: [], chiavi_accesso: [] };
  let n = 0;
  const id = () => `id-${++n}`;
  const saldo = (lic) => {
    const lotti = stato.lotti.filter((l) => l.licenza_id === lic).reduce((s, l) => s + l.residuo, 0);
    const attesa = stato.render.filter((r) => r.licenza_id === lic && r.stato === "riservato").reduce((s, r) => s + r.peso, 0);
    return { disponibile: lotti - attesa, in_attesa: attesa, prossima_scadenza: null };
  };
  const rpc = {
    airender_licenza: ({ p_hash }) => {
      const chiave = stato.chiavi_accesso.find((c) => c.hash_codice === p_hash && !c.revocata_il);
      const l = stato.licenze.find((x) => x.hash_codice === p_hash || (chiave && x.id === chiave.licenza_id));
      return l ? { ...l, postazioni_usate: 0, saldo: saldo(l.id) } : null;
    },
    airender_crea_licenza: (a) => {
      const esistente = stato.licenze.find((l) => (a.p_riferimento && l.riferimento_creazione === a.p_riferimento)
        || (a.p_stripe_abbonamento && l.stripe_abbonamento === a.p_stripe_abbonamento));
      if (esistente) return { id: esistente.id, nuova: false };
      const l = { id: id(), hash_codice: a.p_hash, ultime_cifre: a.p_ultime_cifre, email: a.p_email, piano: a.p_piano,
        stato: "attiva", origine: a.p_origine, postazioni_max: a.p_postazioni_max, riferimento_creazione: a.p_riferimento,
        stripe_cliente: a.p_stripe_cliente, stripe_abbonamento: a.p_stripe_abbonamento, rivenditore: a.p_rivenditore,
        dati_fiscali: a.p_dati_fiscali, email_inviata_il: null };
      stato.licenze.push(l);
      return { id: l.id, nuova: true };
    },
    airender_accredita: (a) => {
      if (stato.lotti.some((l) => l.riferimento === a.p_riferimento)) return { accreditato: false };
      stato.lotti.push({ licenza_id: a.p_licenza, origine: a.p_origine, residuo: a.p_quantita, scade_il: a.p_scade_il, riferimento: a.p_riferimento });
      return { accreditato: true };
    },
    airender_riserva: (a) => {
      const esistente = stato.render.find((r) => r.licenza_id === a.p_licenza && r.chiave === a.p_chiave);
      if (esistente) return { esito: "ok", render: esistente.id, ripetuto: true };
      const s = saldo(a.p_licenza);
      if (s.disponibile < a.p_peso) return { esito: "saldo", disponibile: s.disponibile, peso: a.p_peso };
      const r = { id: id(), licenza_id: a.p_licenza, chiave: a.p_chiave, peso: a.p_peso, stato: "riservato",
        modello: a.p_modello, dimensione: a.p_dimensione, canale: a.p_canale };
      stato.render.push(r);
      return { esito: "ok", render: r.id, ripetuto: false };
    },
    airender_avvia: ({ p_render, p_richiesta }) => { stato.render.find((r) => r.id === p_render).richiesta_comfy = p_richiesta; return null; },
    airender_annulla: ({ p_render }) => { const r = stato.render.find((x) => x.id === p_render); if (r.stato === "riservato") r.stato = "annullato"; return null; },
    airender_chiudi_senza_immagine: ({ p_render, p_tetto }) => {
      const r = stato.render.find((x) => x.id === p_render);
      if (r.stato === "annullato") return { esito: "ok", rimborsato: true, ripetuto: true, saldo: saldo(r.licenza_id) };
      if (r.stato === "addebitato") return { rimborsato: false, ...rpc.airender_addebita({ p_render }) };
      const rimborsati = stato.render.filter((x) => x.licenza_id === r.licenza_id && x.senza_immagine && x.stato === "annullato").length;
      r.senza_immagine = true;
      if (rimborsati < p_tetto) {
        r.stato = "annullato";
        return { esito: "ok", rimborsato: true, ripetuto: false, rimborsati_24h: rimborsati + 1, saldo: saldo(r.licenza_id) };
      }
      return { rimborsato: false, rimborsati_24h: rimborsati, ...rpc.airender_addebita({ p_render }) };
    },
    airender_render_di: ({ p_licenza, p_richiesta }) => stato.render.find((r) => r.licenza_id === p_licenza && r.richiesta_comfy === p_richiesta) || null,
    airender_addebita: ({ p_render }) => {
      const r = stato.render.find((x) => x.id === p_render);
      if (r.stato === "addebitato") return { esito: "ok", ripetuto: true, saldo: saldo(r.licenza_id) };
      r.stato = "addebitato";
      let resta = r.peso;
      for (const l of stato.lotti.filter((x) => x.licenza_id === r.licenza_id)) {
        const preso = Math.min(l.residuo, resta); l.residuo -= preso; resta -= preso;
      }
      return { esito: "ok", ripetuto: false, saldo: saldo(r.licenza_id) };
    },
    airender_saldo: ({ p_licenza }) => saldo(p_licenza),
    airender_evento_nuovo: () => true,
    airender_licenze_di: ({ p_email }) => stato.licenze
      .filter((l) => l.email.toLowerCase() === p_email.trim().toLowerCase() && l.stato === "attiva")
      .map((l) => ({ id: l.id, piano: l.piano, ultime_cifre: l.ultime_cifre,
        link_recenti: stato.link_accesso.filter((a) => a.licenza_id === l.id).length })),
    airender_crea_link: ({ p_hash_gettone, p_licenza, p_minuti }) => {
      stato.link_accesso.push({ hash_gettone: p_hash_gettone, licenza_id: p_licenza, scade: Date.now() + p_minuti * 60000, usato: false });
      return null;
    },
    airender_usa_link: ({ p_hash_gettone, p_hash_chiave, p_ultime_cifre }) => {
      const a = stato.link_accesso.find((x) => x.hash_gettone === p_hash_gettone && !x.usato && x.scade > Date.now());
      if (!a) return null;
      a.usato = true;
      stato.chiavi_accesso.push({ hash_codice: p_hash_chiave, licenza_id: a.licenza_id, ultime_cifre: p_ultime_cifre });
      return rpc.airender_licenza({ p_hash: p_hash_chiave });
    },
  };
  const filtra = (tabella, query) => {
    const p = new URLSearchParams(query);
    return stato[tabella].filter((riga) => [...p].every(([k, v]) => {
      if (k === "select") return true;
      const [op, valore] = [v.slice(0, v.indexOf(".")), decodeURIComponent(v.slice(v.indexOf(".") + 1))];
      if (op === "eq") return String(riga[k]) === valore;
      if (op === "ilike") return String(riga[k]).toLowerCase() === valore.toLowerCase();
      return false;
    }));
  };
  return {
    stato,
    async rpc(nome, a) { stato.chiamate.push(nome); return structuredClone(rpc[nome](a)); },
    async select(tabella, query) { return structuredClone(filtra(tabella, query)); },
    async aggiorna(tabella, query, valori) { for (const r of filtra(tabella, query)) Object.assign(r, valori); },
    async inserisci(tabella, valori) { stato[tabella].push({ ...valori }); },
    async caricaRisultato(percorso, byte, tipo) { stato.caricati.push({ percorso, byte, tipo }); return `https://storage.finto/${percorso}?token=x`; },
  };
}

// fetch finto: una lista di [prova(url, opzioni) -> bool, risposta]. Ogni
// chiamata resta in .chiamate.
export function fetchFinto(regole) {
  const chiamate = [];
  const f = async (url, opzioni = {}) => {
    chiamate.push({ url: String(url), ...opzioni });
    for (const [prova, risposta] of regole) {
      if (prova(String(url), opzioni)) {
        const r = typeof risposta === "function" ? risposta(String(url), opzioni) : risposta;
        return new Response(r.corpo === undefined ? null : JSON.stringify(r.corpo), { status: r.stato || 200, headers: r.intestazioni || {} });
      }
    }
    throw new Error(`fetch finto: nessuna regola per ${url}`);
  };
  f.chiamate = chiamate;
  return f;
}

export function firmaStripe(corpo, segreto, t = Math.floor(Date.now() / 1000)) {
  return `t=${t},v1=${createHmac("sha256", segreto).update(`${t}.${corpo}`).digest("hex")}`;
}
