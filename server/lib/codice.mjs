// Codici licenza: AIR-XXXX-XXXX-XXXX-XXXX, base32 di Crockford (niente I, L,
// O, U: non si confondono quando si ricopiano da un'email). 80 bit casuali.
// Nel database va solo lo SHA-256 del codice normalizzato.

import { createHash, createHmac, randomBytes, timingSafeEqual } from "node:crypto";

const ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ";

export function generaCodice(casuale = randomBytes) {
  const byte = casuale(10);
  let bit = 0n;
  for (const b of byte) bit = (bit << 8n) | BigInt(b);
  let simboli = "";
  for (let i = 0; i < 16; i++) {
    simboli = ALFABETO[Number(bit & 31n)] + simboli;
    bit >>= 5n;
  }
  return `AIR-${simboli.match(/.{4}/g).join("-")}`;
}

// Chi ricopia il codice a mano scrive O per 0 o l per 1: si perdona.
export function normalizza(codice) {
  return String(codice || "")
    .toUpperCase()
    .replace(/^AIR/, "")
    .replace(/[\s-]/g, "")
    .replace(/O/g, "0")
    .replace(/[IL]/g, "1");
}

export function valido(codice) {
  const n = normalizza(codice);
  return n.length === 16 && [...n].every((c) => ALFABETO.includes(c));
}

export function hashCodice(codice) {
  return createHash("sha256").update(normalizza(codice)).digest("hex");
}

export function ultimeCifre(codice) {
  return normalizza(codice).slice(-4);
}

// Un gettone firmato per i link che apre il browser (Ricarica, Gestisci
// abbonamento): porta l'id della licenza, non il codice, e scade.
export function firma(dati, segreto, scadeTraSecondi = 3600, adesso = Date.now()) {
  const carico = Buffer.from(JSON.stringify({ ...dati, scade: Math.floor(adesso / 1000) + scadeTraSecondi })).toString("base64url");
  const sigillo = createHmac("sha256", segreto).update(carico).digest("base64url");
  return `${carico}.${sigillo}`;
}

export function leggiFirma(gettone, segreto, adesso = Date.now()) {
  const [carico, sigillo] = String(gettone || "").split(".");
  if (!carico || !sigillo) return null;
  const atteso = createHmac("sha256", segreto).update(carico).digest();
  const dato = Buffer.from(sigillo, "base64url");
  if (dato.length !== atteso.length || !timingSafeEqual(dato, atteso)) return null;
  const dati = JSON.parse(Buffer.from(carico, "base64url").toString("utf8"));
  if (!dati.scade || dati.scade * 1000 < adesso) return null;
  return dati;
}
