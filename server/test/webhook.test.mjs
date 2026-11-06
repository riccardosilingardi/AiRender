import { test } from "node:test";
import assert from "node:assert/strict";
import { gestisci } from "../netlify/functions/stripe-webhook.mjs";
import { gestisci as admin } from "../netlify/functions/admin.mjs";
import { hashCodice } from "../lib/codice.mjs";
import { dbFinto, firmaStripe } from "./finti.mjs";

const SEGRETO = "whsec_prova";
const ambiente = { STRIPE_WEBHOOK_SECRET: SEGRETO, STRIPE_PREZZO_PRO_MESE: "price_pm", STRIPE_PREZZO_BASE_ANNO: "price_ba" };

function servizi(extra = {}) {
  const email = { mandate: [], async inviaCodice(a, codice, piano) { this.mandate.push({ a, codice, piano }); } };
  const fatture = { create: [], inviate: [], inviaAutomatico: true,
    async crea(corpo) { this.create.push(corpo); return `doc-${this.create.length}`; },
    async inviaSdi(d) { this.inviate.push(d); } };
  const stripe = { async api(metodo, percorso, p) {
    assert.equal(percorso, "checkout/sessions");
    return { data: [{ id: "cs_sub", customer_details: { name: "Studio Bianchi", email: "b@s.it", address: { country: "IT" } }, custom_fields: [] }] };
  } };
  return { db: dbFinto(), email, fatture, stripe, ambiente, ...extra };
}

function evento(tipo, oggetto, id = "evt_1") {
  const corpo = JSON.stringify({ id, type: tipo, data: { object: oggetto } });
  return () => new Request("https://s/api/stripe-webhook", { method: "POST", body: corpo, headers: { "stripe-signature": firmaStripe(corpo, SEGRETO) } });
}

const sessioneProva = {
  id: "cs_1", mode: "payment", payment_status: "paid", metadata: { prodotto: "prova" }, customer: "cus_1",
  amount_subtotal: 1500, amount_total: 1830, total_details: { amount_discount: 0 }, created: 1_762_000_000,
  customer_details: { name: "Studio Rossi", email: "r@s.it", tax_ids: [{ type: "eu_vat", value: "IT01234567890" }], address: { country: "IT", city: "Bologna" } },
  custom_fields: [{ key: "sdi", text: { value: "M5UXCR1" } }],
};

test("una firma falsa si rifiuta", async () => {
  const s = servizi();
  const r = await gestisci(new Request("https://s", { method: "POST", body: "{}", headers: { "stripe-signature": "t=1,v1=00" } }), s);
  assert.equal(r.status, 400);
});

test("la Prova crea la licenza, manda il codice, accredita 10 + 50 e fattura; ripetuta non raddoppia", async () => {
  const s = servizi();
  const e = evento("checkout.session.completed", sessioneProva);
  assert.equal((await gestisci(e(), s)).status, 200);
  assert.equal((await gestisci(e(), s)).status, 200);
  assert.equal(s.db.stato.licenze.length, 1);
  const l = s.db.stato.licenze[0];
  assert.equal(l.piano, "prova");
  assert.equal(s.email.mandate.length, 1, "un'email sola");
  assert.equal(hashCodice(s.email.mandate[0].codice), l.hash_codice, "il codice mandato e' quello salvato");
  assert.deepEqual(s.db.stato.lotti.map((x) => x.residuo).sort((a, b) => a - b), [10, 50]);
  assert.equal(s.fatture.create.length, 1, "una fattura sola");
  const f = s.fatture.create[0].data;
  assert.equal(f.items_list[0].net_price, 15);
  assert.equal(f.payments_list[0].amount, 18.3);
  assert.equal(f.entity.ei_code, "M5UXCR1");
  assert.equal(f.entity.vat_number, "01234567890");
});

test("se l'email era fallita, l'evento ripetuto genera un codice nuovo e lo manda", async () => {
  const s = servizi();
  s.email.inviaCodice = async () => { throw new Error("giu'"); };
  assert.equal((await gestisci(evento("checkout.session.completed", sessioneProva)(), s)).status, 500);
  assert.deepEqual(s.db.stato.lotti.map((x) => x.residuo).sort((a, b) => a - b), [10, 50],
    "i render pagati ci sono anche se l'email non e' partita");
  const vecchio = s.db.stato.licenze[0].hash_codice;
  const mandate = [];
  s.email.inviaCodice = async (a, codice) => { mandate.push(codice); };
  assert.equal((await gestisci(evento("checkout.session.completed", sessioneProva)(), s)).status, 200);
  assert.equal(mandate.length, 1);
  assert.notEqual(s.db.stato.licenze[0].hash_codice, vecchio);
  assert.equal(hashCodice(mandate[0]), s.db.stato.licenze[0].hash_codice);
});

const fatturaPro = (motivo, id = "in_1") => ({
  id, subscription: "sub_1", customer: "cus_2", billing_reason: motivo, amount_paid: 4758, total_excluding_tax: 3900,
  lines: { data: [{ price: { id: "price_pm" }, period: { end: 1_765_000_000 } }] },
});

test("abbonamento: se l'email non parte il mese e' accreditato lo stesso", async () => {
  const s = servizi();
  s.email.inviaCodice = async () => { throw new Error("giu'"); };
  assert.equal((await gestisci(evento("invoice.paid", fatturaPro("subscription_create"))(), s)).status, 500);
  assert.equal(s.db.stato.lotti.filter((x) => x.origine === "piano").length, 1);
});

test("il primo pagamento di un abbonamento crea la licenza dalla sessione e accredita il mese", async () => {
  const s = servizi();
  await gestisci(evento("invoice.paid", fatturaPro("subscription_create"))(), s);
  const l = s.db.stato.licenze[0];
  assert.equal(l.piano, "pro");
  assert.equal(l.stripe_abbonamento, "sub_1");
  assert.equal(l.email, "b@s.it");
  assert.deepEqual(s.db.stato.lotti.map((x) => x.residuo).sort((a, b) => a - b), [10, 200]);
  // rinnovo: altri 200, nessuna licenza nuova
  await gestisci(evento("invoice.paid", fatturaPro("subscription_cycle", "in_2"), "evt_2")(), s);
  assert.equal(s.db.stato.licenze.length, 1);
  assert.equal(s.db.stato.lotti.filter((x) => x.origine === "piano").length, 2);
  // un conguaglio non accredita un mese intero
  await gestisci(evento("invoice.paid", fatturaPro("subscription_update", "in_3"), "evt_3")(), s);
  assert.equal(s.db.stato.lotti.filter((x) => x.origine === "piano").length, 2);
  assert.equal(s.fatture.create.length, 3);
});

test("cambio di piano dal portale e disdetta", async () => {
  const s = servizi();
  await gestisci(evento("invoice.paid", fatturaPro("subscription_create"))(), s);
  await gestisci(evento("customer.subscription.updated", { id: "sub_1", status: "active", items: { data: [{ price: { id: "price_ba" } }] } })(), s);
  assert.equal(s.db.stato.licenze[0].piano, "base");
  await gestisci(evento("customer.subscription.deleted", { id: "sub_1" })(), s);
  assert.equal(s.db.stato.licenze[0].piano, "nessuno");
});

test("la ricarica accredita 100 render alla licenza del link", async () => {
  const s = servizi();
  s.db.stato.licenze.push({ id: "L9", email: "x@y.it", piano: "pro" });
  await gestisci(evento("checkout.session.completed", { ...sessioneProva, id: "cs_r", metadata: { prodotto: "ricarica", licenza: "L9" } })(), s);
  assert.deepEqual(s.db.stato.lotti.map((x) => [x.licenza_id, x.residuo]), [["L9", 100]]);
});

test("admin: senza gettone no; con il gettone crea una licenza Serteco con i render dei mesi pagati", async () => {
  const s = servizi();
  const amb = { AIRENDER_ADMIN_TOKEN: "segreto-admin" };
  const corpo = JSON.stringify({ azione: "crea", email: "c@d.it", piano: "pro", mesi: 12, rivenditore: "serteco" });
  const no = await admin(new Request("https://s/api/admin", { method: "POST", body: corpo, headers: { authorization: "Bearer no" } }), { ambiente: amb, db: s.db, email: s.email });
  assert.equal(no.status, 401);
  const si = await admin(new Request("https://s/api/admin", { method: "POST", body: corpo, headers: { authorization: "Bearer segreto-admin" } }), { ambiente: amb, db: s.db, email: s.email });
  const uscita = await si.json();
  assert.equal(si.status, 200);
  assert.equal(uscita.render, 2400);
  assert.match(uscita.codice, /^AIR-/);
  assert.equal(s.db.stato.licenze[0].rivenditore, "serteco");
  assert.equal(s.db.stato.licenze[0].origine, "manuale");
});
