import { test } from "node:test";
import assert from "node:assert/strict";
import { ORE, pulisci } from "../netlify/functions/pulizia.mjs";
import { corpoPulito, jpegPulito, pngPulito } from "../lib/pulisci.mjs";
import { zlibSync } from "./png-finto.mjs";

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

test("la pulizia toglie i risultati scaduti a giri di 500 e chiede quelli piu' vecchi di 48 ore", async () => {
  const db = dbConFile(Array.from({ length: 1203 }, (_, i) => `L1/r${i}-0.png`));
  const tolti = await pulisci({ db, log: () => {} });
  assert.equal(tolti, 1203);
  assert.equal(db.restanti.length, 0);
  assert.equal(ORE, 48);
  assert.deepEqual(db.chiamate[0], ["airender_risultati_vecchi", { p_ore: 48, p_quanti: 500 }]);
});

test("senza file vecchi non cancella niente", async () => {
  const db = dbConFile([]);
  assert.equal(await pulisci({ db, log: () => {} }), 0);
});

// Un PNG minimo valido, con un blocco tEXt e uno eXIf in mezzo.
function blocco(tipo, dati) {
  const lunghezza = Buffer.alloc(4); lunghezza.writeUInt32BE(dati.length);
  return Buffer.concat([lunghezza, Buffer.from(tipo, "latin1"), dati, Buffer.alloc(4)]);
}
const FIRMA = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const IHDR = blocco("IHDR", Buffer.alloc(13));
const IDAT = blocco("IDAT", zlibSync());
const IEND = blocco("IEND", Buffer.alloc(0));
const PNG_CON_TESTI = Buffer.concat([FIRMA, IHDR, blocco("tEXt", Buffer.from("Author\0Mario Rossi")),
  blocco("eXIf", Buffer.from("GPS")), IDAT, IEND]);

test("dal PNG escono testi ed EXIF, restano intestazione e pixel", () => {
  const pulito = pngPulito(PNG_CON_TESTI);
  assert.deepEqual(pulito, Buffer.concat([FIRMA, IHDR, IDAT, IEND]));
  assert.ok(!pulito.includes("Mario Rossi"));
});

test("dal JPEG escono APP1 (EXIF, XMP), APP13 e commenti; restano APP0, ICC e pixel", () => {
  const seg = (m, testo) => { const d = Buffer.from(testo); const l = Buffer.alloc(2); l.writeUInt16BE(d.length + 2); return Buffer.concat([Buffer.from([0xff, m]), l, d]); };
  const app0 = seg(0xe0, "JFIF\0..");
  const icc = seg(0xe2, "ICC_PROFILE\0");
  const pixel = Buffer.from([0xff, 0xda, 0x00, 0x02, 0x11, 0x22, 0xff, 0xd9]);
  const jpeg = Buffer.concat([Buffer.from([0xff, 0xd8]), app0, seg(0xe1, "Exif\0\0GPS 44.6N"), seg(0xe1, "http://ns.adobe.com/xap/1.0/\0<x/>"),
    seg(0xed, "Photoshop 3.0"), seg(0xfe, "di Mario"), icc, pixel]);
  assert.deepEqual(jpegPulito(jpeg), Buffer.concat([Buffer.from([0xff, 0xd8]), app0, icc, pixel]));
});

test("il corpo esce con le immagini ripulite, sia data URI sia base64 nudo, e il resto uguale", () => {
  const b64 = PNG_CON_TESTI.toString("base64");
  const pulito = Buffer.concat([FIRMA, IHDR, IDAT, IEND]).toString("base64");
  const corpo = {
    contents: [{ parts: [{ text: "rendi fotorealistico" }, { inlineData: { mimeType: "image/png", data: b64 } }] }],
    input_image: `data:image/png;base64,${b64}`,
    seed: 3,
  };
  assert.deepEqual(corpoPulito(corpo), {
    contents: [{ parts: [{ text: "rendi fotorealistico" }, { inlineData: { mimeType: "image/png", data: pulito } }] }],
    input_image: `data:image/png;base64,${pulito}`,
    seed: 3,
  });
});
