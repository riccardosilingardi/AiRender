import { test } from "node:test";
import assert from "node:assert/strict";
import { ORE, pulisci } from "../netlify/functions/pulizia.mjs";

function dbConFile(nomi) {
  const restanti = [...nomi];
  const chiamate = [];
  return {
    chiamate,
    restanti,
    rpc: async (nome, a) => { chiamate.push([nome, a]); return restanti.slice(0, a.p_quanti); },
    rimuoviRisultati: async (tolti) => { for (const n of tolti) restanti.splice(restanti.indexOf(n), 1); },
  };
}

test("la pulizia toglie i risultati scaduti a giri di 500 e chiede quelli piu' vecchi di 24 ore", async () => {
  const db = dbConFile(Array.from({ length: 1203 }, (_, i) => `L1/r${i}-0.png`));
  const tolti = await pulisci({ db, log: () => {} });
  assert.equal(tolti, 1203);
  assert.equal(db.restanti.length, 0);
  assert.equal(ORE, 24);
  assert.deepEqual(db.chiamate[0], ["airender_risultati_vecchi", { p_ore: 24, p_quanti: 500 }]);
});

test("senza file vecchi non cancella niente", async () => {
  const db = dbConFile([]);
  assert.equal(await pulisci({ db, log: () => {} }), 0);
});
