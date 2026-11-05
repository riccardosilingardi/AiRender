import { test } from "node:test";
import assert from "node:assert/strict";
import { codificaForm, datiFiscali, firmaValida, prodottoDelPrezzo } from "../lib/stripe.mjs";
import { firmaStripe } from "./finti.mjs";
import { parametriCheckout, TERMINI_VERSIONE } from "../netlify/functions/acquista.mjs";

test("la firma del webhook si verifica, e una vecchia o falsa no", () => {
  const corpo = '{"id":"evt_1"}';
  const t = 1_700_000_000;
  const h = firmaStripe(corpo, "whsec_x", t);
  assert.ok(firmaValida(corpo, h, "whsec_x", t * 1000));
  assert.ok(!firmaValida(corpo + " ", h, "whsec_x", t * 1000));
  assert.ok(!firmaValida(corpo, h, "whsec_y", t * 1000));
  assert.ok(!firmaValida(corpo, h, "whsec_x", (t + 301) * 1000));
  assert.ok(!firmaValida(corpo, "", "whsec_x"));
});

test("i parametri annidati si codificano come li vuole Stripe", () => {
  const f = codificaForm({ line_items: [{ price: "p_1", quantity: 1 }], metadata: { prodotto: "pro_mese" }, vuoto: null });
  assert.equal(f.toString(), "line_items%5B0%5D%5Bprice%5D=p_1&line_items%5B0%5D%5Bquantity%5D=1&metadata%5Bprodotto%5D=pro_mese");
});

test("il Checkout chiede dati fiscali, codici sconto e porta la licenza della ricarica", () => {
  const p = parametriCheckout("ricarica", { sito: "https://s", prezzo: "price_r", licenza: "L1", iva: "txr_22" });
  assert.equal(p.mode, "payment");
  assert.equal(p.allow_promotion_codes, true);
  assert.equal(p.tax_id_collection.enabled, true);
  assert.equal(p.metadata.licenza, "L1");
  assert.deepEqual(p.line_items[0].tax_rates, ["txr_22"]);
  assert.deepEqual(p.custom_fields.map((c) => c.key), ["sdi", "codice_fiscale"]);
  const a = parametriCheckout("pro_anno", { sito: "https://s", prezzo: "price_pa" });
  assert.equal(a.mode, "subscription");
  assert.equal(a.customer_creation, undefined);
});

test("senza spuntare i Termini non si paga, e la versione accettata resta nei metadati", () => {
  for (const nome of ["prova", "ricarica", "pro_mese"]) {
    const p = parametriCheckout(nome, { sito: "https://s", prezzo: "price_x", licenza: "L1" });
    assert.deepEqual(p.consent_collection, { terms_of_service: "required" });
    assert.match(p.custom_text.terms_of_service_acceptance.message, /https:\/\/s\/termini\.html/);
    assert.match(p.custom_text.terms_of_service_acceptance.message, /https:\/\/s\/privacy\.html/);
    assert.equal(p.metadata.termini, TERMINI_VERSIONE);
  }
});

test("i dati fiscali escono dalla sessione; una PEC nel campo SDI va in PEC", () => {
  const d = datiFiscali({
    customer_details: { name: "Studio Rossi", email: "r@s.it", tax_ids: [{ type: "eu_vat", value: "IT01234567890" }],
      address: { line1: "Via Emilia 1", postal_code: "40100", city: "Bologna", state: "BO", country: "IT" } },
    custom_fields: [{ key: "sdi", text: { value: "rossi@pec.it" } }, { key: "codice_fiscale", text: { value: "rssmra80a01a944x" } }],
  });
  assert.equal(d.partita_iva, "IT01234567890");
  assert.equal(d.pec, "rossi@pec.it");
  assert.equal(d.codice_sdi, "");
  assert.equal(d.codice_fiscale, "RSSMRA80A01A944X");
  assert.equal(d.indirizzo.citta, "Bologna");
});

test("un prezzo Stripe si riconosce dalla sua variabile d'ambiente", () => {
  const amb = { STRIPE_PREZZO_PRO_ANNO: "price_pa" };
  assert.deepEqual(
    (({ piano, intervallo }) => ({ piano, intervallo }))(prodottoDelPrezzo("price_pa", amb)),
    { piano: "pro", intervallo: "anno" },
  );
  assert.equal(prodottoDelPrezzo("price_x", amb), null);
});
