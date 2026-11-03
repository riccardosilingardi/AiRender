// Stripe senza SDK: firma del webhook verificata a mano e chiamate REST con
// corpo form-encoded. Documentazione letta il 2026-11-02; MAI ESEGUITO con
// un account vero.

import { createHmac, timingSafeEqual } from "node:crypto";
import { serve } from "./ambiente.mjs";

export const TOLLERANZA_FIRMA_SECONDI = 300;

// Stripe-Signature: t=<secondi>,v1=<hmac hex>[,v1=...]. Il payload firmato e'
// "<t>.<corpo grezzo>".
export function firmaValida(corpoGrezzo, intestazione, segreto, adesso = Date.now()) {
  const pezzi = String(intestazione || "").split(",").map((p) => p.trim().split("="));
  const t = pezzi.find(([k]) => k === "t")?.[1];
  const firme = pezzi.filter(([k]) => k === "v1").map(([, v]) => v);
  if (!t || !firme.length) return false;
  if (Math.abs(adesso / 1000 - Number(t)) > TOLLERANZA_FIRMA_SECONDI) return false;
  const attesa = createHmac("sha256", segreto).update(`${t}.${corpoGrezzo}`).digest();
  return firme.some((f) => {
    const b = Buffer.from(f, "hex");
    return b.length === attesa.length && timingSafeEqual(b, attesa);
  });
}

// { a: { b: [ { c: 1 } ] } } -> a[b][0][c]=1
export function codificaForm(oggetto, prefisso = "", fuori = new URLSearchParams()) {
  for (const [k, v] of Object.entries(oggetto)) {
    if (v === undefined || v === null) continue;
    const nome = prefisso ? `${prefisso}[${k}]` : k;
    if (typeof v === "object") codificaForm(v, nome, fuori);
    else fuori.append(nome, String(v));
  }
  return fuori;
}

export function creaStripe(ambiente = process.env, chiama = fetch) {
  async function api(metodo, percorso, parametri) {
    const opzioni = {
      method: metodo,
      headers: { authorization: `Bearer ${serve("STRIPE_SECRET_KEY", ambiente)}` },
    };
    let url = `https://api.stripe.com/v1/${percorso}`;
    if (parametri && metodo === "GET") url += `?${codificaForm(parametri)}`;
    else if (parametri) {
      opzioni.headers["content-type"] = "application/x-www-form-urlencoded";
      opzioni.body = codificaForm(parametri).toString();
    }
    const r = await chiama(url, opzioni);
    const corpo = await r.json();
    if (!r.ok) throw new Error(`Stripe ${percorso}: ${r.status} ${corpo?.error?.message || ""}`);
    return corpo;
  }
  return { api };
}

// Prezzo Stripe -> prodotto AIRENDER. Gli id dei prezzi si creano nel
// cruscotto Stripe e stanno nelle variabili d'ambiente, non qui.
export const PRODOTTI = {
  prova: { variabile: "STRIPE_PREZZO_PROVA", piano: "prova", modo: "payment" },
  ricarica: { variabile: "STRIPE_PREZZO_RICARICA", piano: null, modo: "payment" },
  base_mese: { variabile: "STRIPE_PREZZO_BASE_MESE", piano: "base", intervallo: "mese", modo: "subscription" },
  base_anno: { variabile: "STRIPE_PREZZO_BASE_ANNO", piano: "base", intervallo: "anno", modo: "subscription" },
  pro_mese: { variabile: "STRIPE_PREZZO_PRO_MESE", piano: "pro", intervallo: "mese", modo: "subscription" },
  pro_anno: { variabile: "STRIPE_PREZZO_PRO_ANNO", piano: "pro", intervallo: "anno", modo: "subscription" },
  studio_mese: { variabile: "STRIPE_PREZZO_STUDIO_MESE", piano: "studio", intervallo: "mese", modo: "subscription" },
  studio_anno: { variabile: "STRIPE_PREZZO_STUDIO_ANNO", piano: "studio", intervallo: "anno", modo: "subscription" },
};

export function prodottoDelPrezzo(idPrezzo, ambiente = process.env) {
  for (const [nome, p] of Object.entries(PRODOTTI)) {
    if ((ambiente[p.variabile] || "").trim() === idPrezzo) return { nome, ...p };
  }
  return null;
}

// I dati per la fattura elettronica, come li raccoglie il Checkout: nome,
// indirizzo, partita IVA (tax_id_collection) e i campi su misura Codice
// destinatario SDI / PEC e codice fiscale.
export function datiFiscali(sessione) {
  const c = sessione.customer_details || {};
  const campo = (chiave) => (sessione.custom_fields || []).find((f) => f.key === chiave)?.text?.value || "";
  const piva = (c.tax_ids || []).find((t) => t.type === "eu_vat")?.value || "";
  const sdi = campo("sdi").trim();
  return {
    nome: c.name || "",
    email: c.email || "",
    partita_iva: piva,
    codice_fiscale: campo("codice_fiscale").trim().toUpperCase(),
    codice_sdi: sdi.includes("@") ? "" : sdi.toUpperCase(),
    pec: sdi.includes("@") ? sdi : "",
    indirizzo: {
      via: [c.address?.line1, c.address?.line2].filter(Boolean).join(" "),
      cap: c.address?.postal_code || "",
      citta: c.address?.city || "",
      provincia: c.address?.state || "",
      paese: c.address?.country || "",
    },
  };
}
