import { test } from "node:test";
import assert from "node:assert/strict";
import { firma, generaCodice, hashCodice, leggiFirma, normalizza, ultimeCifre, valido } from "../lib/codice.mjs";

test("il codice ha la forma AIR-XXXX-XXXX-XXXX-XXXX e passa la validazione", () => {
  const c = generaCodice();
  assert.match(c, /^AIR-[0-9A-HJKMNP-TV-Z]{4}(-[0-9A-HJKMNP-TV-Z]{4}){3}$/);
  assert.ok(valido(c));
  assert.notEqual(generaCodice(), c);
});

test("un codice ricopiato a mano con O, l, spazi e minuscole da' lo stesso hash", () => {
  const c = "AIR-0011-ABCD-EFGH-JK01";
  assert.equal(hashCodice(c), hashCodice("air oOlI abcd efgh jkOl"));
  assert.equal(normalizza(c), "0011ABCDEFGHJK01");
  assert.equal(ultimeCifre(c), "JK01");
  assert.ok(!valido("AIR-1234"));
});

test("il gettone firmato scade e non si falsifica", () => {
  const g = firma({ licenza: "L1" }, "segreto", 60, 1_000_000);
  assert.equal(leggiFirma(g, "segreto", 1_000_000).licenza, "L1");
  assert.equal(leggiFirma(g, "altro", 1_000_000), null);
  assert.equal(leggiFirma(g, "segreto", 1_000_000 + 61_000), null);
  assert.equal(leggiFirma(g.replace(/^./, "x"), "segreto", 1_000_000), null);
  assert.equal(leggiFirma("", "segreto"), null);
});
