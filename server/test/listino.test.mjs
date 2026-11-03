import { test } from "node:test";
import assert from "node:assert/strict";
import { dimensioneDaCorpo, fuoriDalPiano, peso, renderDelPeriodo } from "../lib/listino.mjs";

const NB2 = "vertexai/gemini-3.1-flash-image";
const PRO = "vertexai/gemini-3-pro-image";

test("i pesi sono quelli decisi: NB2 1 fino a 2K e 2 a 4K, Pro 2 e 3 a 4K", () => {
  assert.equal(peso(NB2, "1K"), 1);
  assert.equal(peso(NB2, "2K"), 1);
  assert.equal(peso(NB2, "4K"), 2);
  assert.equal(peso(PRO, "2K"), 2);
  assert.equal(peso(PRO, "4K"), 3);
  assert.equal(peso("bfl/flux-kontext-pro", "1K"), null);
});

test("la grandezza si legge dal corpo; assente e' 1K, sconosciuta e' rifiutata", () => {
  assert.equal(dimensioneDaCorpo({}), "1K");
  assert.equal(dimensioneDaCorpo({ generationConfig: { imageConfig: { imageSize: "4k" } } }), "4K");
  assert.equal(dimensioneDaCorpo({ generationConfig: { imageConfig: { imageSize: "8K" } } }), null);
});

test("Base: solo web app, solo NB2, fino a 2K", () => {
  assert.equal(fuoriDalPiano("base", NB2, "2K", "web"), null);
  assert.equal(fuoriDalPiano("base", NB2, "2K", "plugin").tipo, "canale_non_incluso");
  assert.equal(fuoriDalPiano("base", PRO, "1K", "web").tipo, "modello_non_incluso");
  assert.equal(fuoriDalPiano("base", NB2, "4K", "web").tipo, "dimensione_non_inclusa");
});

test("Pro, Studio e Prova aprono il plugin, Pro e 4K", () => {
  for (const p of ["pro", "studio", "prova"]) assert.equal(fuoriDalPiano(p, PRO, "4K", "plugin"), null, p);
});

test("l'annuale accredita 12 mesi di render, il mensile uno", () => {
  assert.equal(renderDelPeriodo("pro", "mese"), 200);
  assert.equal(renderDelPeriodo("pro", "anno"), 2400);
  assert.equal(renderDelPeriodo("prova", "mese"), 0);
});
