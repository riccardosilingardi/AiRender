// Prima di passare la richiesta al Comfy Router, il server toglie dalle
// immagini i metadati che possono dire qualcosa di qualcuno: EXIF (posizione
// GPS, modello del telefono, a volte il nome dell'autore), XMP, IPTC,
// commenti, testi PNG. Il plugin e lo Studio li tolgono gia' prima di mandare
// (core/immagine.py, senza_metadati): questo e' il secondo cancello, per chi
// arriva da un client vecchio o, domani, da un'API.
//
// Si lavora sui byte, senza decodificare i pixel e senza librerie: in PNG si
// buttano i blocchi di testo e di EXIF, in JPEG i segmenti APP1 (EXIF e XMP),
// APP13 (IPTC) e i commenti. Il profilo colore (iCCP, APP2) resta.
//
// Limite: in JPEG l'orientamento sta nell'EXIF, e senza EXIF una foto girata
// arriva girata. Il plugin e lo Studio raddrizzano i pixel prima di togliere
// l'EXIF; un client web deve fare lo stesso (ridisegnando la foto su un
// canvas, che toglie anche tutto il resto).

const PNG_FIRMA = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const PNG_DA_TOGLIERE = new Set(["tEXt", "zTXt", "iTXt", "eXIf", "tIME"]);
// APP1 = EXIF o XMP, APP13 = IPTC/Photoshop, COM = commento.
const JPEG_DA_TOGLIERE = new Set([0xe1, 0xed, 0xfe]);

export function pngPulito(byte) {
  if (byte.length < 8 || !byte.subarray(0, 8).equals(PNG_FIRMA)) return byte;
  const parti = [byte.subarray(0, 8)];
  let i = 8;
  while (i + 12 <= byte.length) {
    const lunghezza = byte.readUInt32BE(i);
    const tipo = byte.toString("latin1", i + 4, i + 8);
    const fine = i + 12 + lunghezza;
    if (fine > byte.length) return byte; // PNG rotto: lo giudichera' il servizio
    if (!PNG_DA_TOGLIERE.has(tipo)) parti.push(byte.subarray(i, fine));
    i = fine;
    if (tipo === "IEND") break;
  }
  return Buffer.concat(parti);
}

export function jpegPulito(byte) {
  if (byte.length < 4 || byte[0] !== 0xff || byte[1] !== 0xd8) return byte;
  const parti = [byte.subarray(0, 2)];
  let i = 2;
  while (i + 4 <= byte.length && byte[i] === 0xff) {
    const marcatore = byte[i + 1];
    // Dopo l'inizio della scansione (SOS) ci sono i pixel: si copia tutto.
    if (marcatore === 0xda) break;
    const lunghezza = byte.readUInt16BE(i + 2);
    const fine = i + 2 + lunghezza;
    if (fine > byte.length) return byte;
    if (!JPEG_DA_TOGLIERE.has(marcatore)) parti.push(byte.subarray(i, fine));
    i = fine;
  }
  parti.push(byte.subarray(i));
  return Buffer.concat(parti);
}

export function immaginePulita(byte) {
  return jpegPulito(pngPulito(byte));
}

const DATA_URI = /^data:(image\/[a-z.+-]+);base64,(.*)$/s;
// Le prime lettere del base64 di un PNG e di un JPEG.
const SEMBRA_IMMAGINE = /^(iVBORw0KGgo|\/9j\/)/;

function stringaPulita(valore) {
  const uri = valore.match(DATA_URI);
  if (uri) return `data:${uri[1]};base64,${immaginePulita(Buffer.from(uri[2], "base64")).toString("base64")}`;
  if (SEMBRA_IMMAGINE.test(valore)) return immaginePulita(Buffer.from(valore, "base64")).toString("base64");
  return valore;
}

// Il corpo della richiesta, con ogni immagine (data URI o base64 nudo) ripulita.
// Tutto il resto resta com'e'.
export function corpoPulito(corpo) {
  if (typeof corpo === "string") return stringaPulita(corpo);
  if (Array.isArray(corpo)) return corpo.map(corpoPulito);
  if (corpo && typeof corpo === "object") {
    return Object.fromEntries(Object.entries(corpo).map(([k, v]) => [k, corpoPulito(v)]));
  }
  return corpo;
}
