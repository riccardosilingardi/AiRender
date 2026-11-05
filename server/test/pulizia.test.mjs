import { test } from "node:test";
import assert from "node:assert/strict";
import { pulisci } from "../netlify/functions/pulizia-risultati.mjs";
import { corpoPulito, jpegPulito, pngPulito } from "../lib/pulisci.mjs";
import { zlibSync } from "./png-finto.mjs";

const ADESSO = Date.parse("2026-11-05T12:00:00Z");

function storageFinto(file) {
  const cancellati = [];
  return {
    cancellati,
    async elencaRisultati(prefisso) {
      if (!prefisso) return [...new Set(file.map((f) => f.percorso.split("/")[0]))].map((name) => ({ name, id: null }));
      return file.filter((f) => f.percorso.startsWith(prefisso))
        .map((f) => ({ name: f.percorso.slice(prefisso.length), id: "x", created_at: f.creato }));
    },
    async cancellaRisultati(percorsi) { cancellati.push(...percorsi); },
  };
}

test("la pulizia cancella solo i risultati piu' vecchi di 48 ore", async () => {
  const db = storageFinto([
    { percorso: "L1/vecchio-0.png", creato: "2026-11-02T10:00:00Z" },
    { percorso: "L1/recente-0.png", creato: "2026-11-05T09:00:00Z" },
    { percorso: "L2/vecchio-0.jpeg", creato: "2026-11-01T10:00:00Z" },
  ]);
  const esito = await pulisci({ db, adesso: ADESSO });
  assert.deepEqual(db.cancellati.sort(), ["L1/vecchio-0.png", "L2/vecchio-0.jpeg"]);
  assert.equal(esito.cancellati, 2);
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
