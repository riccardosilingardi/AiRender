// Fatture in Cloud (API v2): una fattura elettronica per ogni pagamento
// Stripe, inviata allo SdI solo se FIC_INVIA_SDI=si. Spento per default: le
// prime fatture si guardano nel cruscotto di Fatture in Cloud prima di
// mandarle. Forma del corpo dalla documentazione di developers.fattureincloud.it
// letta il 2026-11-02; MAI ESEGUITO con un account vero.

import { facoltativa, serve } from "./ambiente.mjs";

const BASE = "https://api-v2.fattureincloud.it";

const PAESI = { IT: "Italia", SM: "San Marino", CH: "Svizzera", DE: "Germania", FR: "Francia", AT: "Austria", ES: "Spagna" };

// importi in centesimi, come li da' Stripe
export function corpoFattura(dati, { descrizione, imponibile, totale, data }, ambiente = process.env) {
  const italiano = !dati.indirizzo?.paese || dati.indirizzo.paese === "IT";
  const iva = facoltativa("FIC_ID_IVA", ambiente);
  const conto = facoltativa("FIC_ID_CONTO", ambiente);
  return {
    data: {
      type: "invoice",
      entity: {
        name: dati.nome,
        vat_number: dati.partita_iva.replace(/^IT/i, ""),
        tax_code: dati.codice_fiscale || dati.partita_iva.replace(/^IT/i, ""),
        address_street: dati.indirizzo?.via || "",
        address_postal_code: dati.indirizzo?.cap || "",
        address_city: dati.indirizzo?.citta || "",
        address_province: dati.indirizzo?.provincia || "",
        country: PAESI[dati.indirizzo?.paese] || dati.indirizzo?.paese || "Italia",
        email: dati.email,
        certified_email: dati.pec || undefined,
        ei_code: dati.codice_sdi || (italiano ? "0000000" : "XXXXXXX"),
      },
      date: data,
      currency: { id: "EUR" },
      language: { code: "it", name: "Italiano" },
      items_list: [{
        name: descrizione,
        qty: 1,
        net_price: imponibile / 100,
        ...(iva ? { vat: { id: Number(iva) } } : {}),
      }],
      payments_list: [{
        amount: totale / 100,
        due_date: data,
        paid_date: data,
        status: "paid",
        ...(conto ? { payment_account: { id: Number(conto) } } : {}),
      }],
      e_invoice: true,
      ei_data: { payment_method: "MP08" },
    },
  };
}

export function creaFatture(ambiente = process.env, chiama = fetch) {
  const azienda = () => serve("FIC_ID_AZIENDA", ambiente);
  const intestazioni = () => ({
    authorization: `Bearer ${serve("FIC_TOKEN", ambiente)}`,
    "content-type": "application/json",
  });

  async function crea(corpo) {
    const r = await chiama(`${BASE}/c/${azienda()}/issued_documents`, {
      method: "POST", headers: intestazioni(), body: JSON.stringify(corpo),
    });
    const uscita = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(`Fatture in Cloud: ${r.status} ${JSON.stringify(uscita).slice(0, 300)}`);
    return String(uscita.data.id);
  }

  async function inviaSdi(documento) {
    const r = await chiama(`${BASE}/c/${azienda()}/issued_documents/${documento}/e_invoice/send`, {
      method: "POST", headers: intestazioni(), body: JSON.stringify({ data: {} }),
    });
    if (!r.ok) throw new Error(`Fatture in Cloud (SdI): ${r.status} ${(await r.text()).slice(0, 300)}`);
  }

  return { crea, inviaSdi, inviaAutomatico: facoltativa("FIC_INVIA_SDI", ambiente) === "si" };
}

// Crea (se manca) e invia (se acceso) la fattura di un pagamento. Si puo'
// richiamare quante volte si vuole sullo stesso riferimento: la tabella
// fatture ricorda a che punto e'.
export async function fattura({ db, fatture }, riferimento, licenzaId, dati, riga) {
  const [esistente] = await db.select("fatture", `riferimento=eq.${encodeURIComponent(riferimento)}`);
  let documento = esistente?.fic_documento;
  if (!esistente) await db.inserisci("fatture", { riferimento, licenza_id: licenzaId });
  try {
    if (!documento) {
      documento = await fatture.crea(corpoFattura(dati, riga));
      await db.aggiorna("fatture", `riferimento=eq.${encodeURIComponent(riferimento)}`,
        { fic_documento: documento, stato: "creata", errore: null, aggiornata_il: new Date().toISOString() });
    }
    if (fatture.inviaAutomatico && esistente?.stato !== "inviata") {
      await fatture.inviaSdi(documento);
      await db.aggiorna("fatture", `riferimento=eq.${encodeURIComponent(riferimento)}`,
        { stato: "inviata", aggiornata_il: new Date().toISOString() });
    }
  } catch (e) {
    await db.aggiorna("fatture", `riferimento=eq.${encodeURIComponent(riferimento)}`,
      { stato: "errore", errore: String(e.message).slice(0, 500), aggiornata_il: new Date().toISOString() });
    throw e;
  }
}
