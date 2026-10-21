"""Sonda di Comfy Router: una chiamata vera, tutto stampato, niente costruito sopra.

    python scripts/sonda_comfy.py --solo-schema        # gratis: legge lo schema
    python scripts/sonda_comfy.py --catalogo           # gratis: elenca i modelli
    python scripts/sonda_comfy.py                      # schema + UNA generazione

Serve a una cosa sola: vedere come risponde davvero il Router prima di
scrivere lo schema dei modelli in core/provider/comfy.py. Il corpo della
richiesta qui sotto viene dalla documentazione (docs.comfy.org) e NON e' mai
stato eseguito: e' proprio quello che la sonda deve confermare o smentire.

Cosa fa, in ordine:
1. legge lo schema del modello: GET /v2/models/{provider}/{model}/openapi.json
   (non costa crediti);
2. manda una richiesta in coda: POST .../requests, con X-API-Key e
   Idempotency-Key, e fallback_provider=false perche' l'immagine vada solo al
   servizio annunciato;
3. controlla /status rispettando Retry-After;
4. prende il risultato con GET e salva l'immagine.

La chiave sta in COMFY_API_KEY e non compare mai nell'uscita: puoi incollarla
cosi' com'e'. L'immagine generata e le risposte complete restano sul disco,
nella cartella indicata da --uscita.

Solo libreria standard. Del motore usa soltanto il prompt del preset e le
costanti di rete di core/config.py, cosi' la sonda prova il prompt vero.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import config  # noqa: E402
from core.preset import preset as trova_preset  # noqa: E402
from core.prompt import componi  # noqa: E402

BASE = "https://api.comfy.org/v2/models"
VARIABILE_CHIAVE = "COMFY_API_KEY"
VISTA_PREDEFINITA = RADICE / "tests" / "dati" / "vista-20261021-093841.png"
MODELLO_PREDEFINITO = "bfl/flux-kontext-pro"

# Rapporti che sia FLUX.1 Kontext sia Gemini dichiarano di accettare. Si
# sceglie il piu' vicino alla vista: un rapporto diverso schiaccia l'edificio.
RAPPORTI = ("21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16")

# Corpi candidati, DALLA DOCUMENTAZIONE, NON VERIFICATI. Sono l'ipotesi che
# la sonda mette alla prova, non lo schema del provider.
FAMIGLIA_KONTEXT = "kontext"
FAMIGLIA_GEMINI = "gemini"
FAMIGLIE = {
    "bfl/flux-kontext-pro": FAMIGLIA_KONTEXT,
    "bfl/flux-kontext-max": FAMIGLIA_KONTEXT,
    "vertexai/gemini-3.1-flash-image": FAMIGLIA_GEMINI,
    "vertexai/gemini-3-pro-image": FAMIGLIA_GEMINI,
    "vertexai/gemini-2.5-flash-image": FAMIGLIA_GEMINI,
}

INTESTAZIONI_TACIUTE = ("set-cookie",)
# Link che il Router mette nelle sue risposte e che non sono l'immagine.
URL_DEL_ROUTER = ("status_url", "response_url", "cancel_url")
LUNGHEZZA_MASSIMA_STAMPATA = 160  # caratteri di una stringa prima di tagliarla


# --- cosa si stampa ----------------------------------------------------------


class Uscita:
    """Stampa tutto, ma la chiave non passa mai, nemmeno se il servizio la ripete."""

    def __init__(self, chiave: str = "", flusso=None) -> None:
        self.chiave = chiave
        self.flusso = flusso or sys.stdout

    def __call__(self, testo: str = "") -> None:
        if self.chiave:
            testo = testo.replace(self.chiave, "<chiave non stampata>")
        print(testo, file=self.flusso)

    def json(self, oggetto: object, rientro: str = "  ") -> None:
        testo = json.dumps(accorcia(oggetto), indent=2, ensure_ascii=False)
        for riga in testo.splitlines():
            self(rientro + riga)


def accorcia(oggetto: object) -> object:
    """Copia leggibile: stringhe lunghe (base64) tagliate, firme degli URL tolte."""
    if isinstance(oggetto, dict):
        return {k: accorcia(v) for k, v in oggetto.items()}
    if isinstance(oggetto, list):
        return [accorcia(v) for v in oggetto]
    if isinstance(oggetto, str):
        if oggetto.startswith(("http://", "https://")):
            return url_senza_firma(oggetto)
        if len(oggetto) > LUNGHEZZA_MASSIMA_STAMPATA:
            return f"<{len(oggetto)} caratteri, inizia con {oggetto[:40]!r}>"
    return oggetto


def url_senza_firma(indirizzo: str) -> str:
    """Il link all'immagine ha una firma nella query: non serve a capire, si toglie."""
    parti = urllib.parse.urlsplit(indirizzo)
    coda = "?<parametri omessi>" if parti.query else ""
    return f"{parti.scheme}://{parti.netloc}{parti.path}{coda}"


def intestazioni_leggibili(intestazioni: dict, chiave: str = "") -> dict:
    pulite = {}
    for nome, valore in intestazioni.items():
        if nome.lower() in INTESTAZIONI_TACIUTE:
            continue
        if nome.lower() == "x-api-key" or (chiave and chiave in str(valore)):
            valore = "<chiave non stampata>"
        pulite[nome] = valore
    return pulite


# --- immagine ----------------------------------------------------------------


def tipo_immagine(dati: bytes) -> str:
    if dati.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if dati.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if dati[:4] == b"RIFF" and dati[8:12] == b"WEBP":
        return "image/webp"
    return "application/octet-stream"


def dimensioni(dati: bytes) -> tuple[int, int] | None:
    """Larghezza e altezza senza Pillow: PNG, JPEG e WebP. None se non lo so leggere."""
    tipo = tipo_immagine(dati)
    if tipo == "image/png" and len(dati) >= 24:
        return struct.unpack(">II", dati[16:24])
    if tipo == "image/jpeg":
        posizione = 2
        while posizione + 9 < len(dati):
            if dati[posizione] != 0xFF:
                posizione += 1
                continue
            marcatore = dati[posizione + 1]
            lunghezza = struct.unpack(">H", dati[posizione + 2:posizione + 4])[0]
            if 0xC0 <= marcatore <= 0xCF and marcatore not in (0xC4, 0xC8, 0xCC):
                altezza, larghezza = struct.unpack(">HH", dati[posizione + 5:posizione + 9])
                return larghezza, altezza
            posizione += 2 + lunghezza
        return None
    if tipo == "image/webp" and len(dati) >= 30:
        blocco = dati[12:16]
        if blocco == b"VP8X":
            larghezza = 1 + int.from_bytes(dati[24:27], "little")
            altezza = 1 + int.from_bytes(dati[27:30], "little")
            return larghezza, altezza
        if blocco == b"VP8 ":
            larghezza, altezza = struct.unpack("<HH", dati[26:30])
            return larghezza & 0x3FFF, altezza & 0x3FFF
        if blocco == b"VP8L":
            bit = int.from_bytes(dati[21:25], "little")
            return (bit & 0x3FFF) + 1, ((bit >> 14) & 0x3FFF) + 1
    return None


def rapporto_piu_vicino(larghezza: int, altezza: int) -> str:
    voluto = larghezza / altezza

    def scarto(rapporto: str) -> float:
        a, b = (int(x) for x in rapporto.split(":"))
        return abs(a / b - voluto)

    return min(RAPPORTI, key=scarto)


def immagine_per_invio(dati: bytes, nudo: bool) -> str:
    codificata = base64.b64encode(dati).decode("ascii")
    if nudo:
        return codificata
    return f"data:{tipo_immagine(dati)};base64,{codificata}"


# --- il corpo da provare -----------------------------------------------------


def corpo_candidato(modello: str, prompt: str, dati: bytes, nudo: bool) -> dict:
    """Il corpo che la documentazione suggerisce. Ipotesi, non schema."""
    famiglia = FAMIGLIE.get(modello)
    larghezza, altezza = dimensioni(dati) or (1, 1)
    rapporto = rapporto_piu_vicino(larghezza, altezza)
    immagine = immagine_per_invio(dati, nudo)
    if famiglia == FAMIGLIA_KONTEXT:
        return {"prompt": prompt, "input_image": immagine, "aspect_ratio": rapporto}
    if famiglia == FAMIGLIA_GEMINI:
        return {
            "contents": [{
                "role": "user",
                "parts": [
                    {"text": prompt},
                    {"inlineData": {"mimeType": tipo_immagine(dati), "data": immagine}},
                ],
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": rapporto},
            },
        }
    raise SystemExit(
        f"Per il modello {modello} non ho un corpo candidato dalla documentazione.\n"
        f"Cosa fare: lancia con --solo-schema per leggere lo schema, oppure scegli "
        f"fra: {', '.join(sorted(FAMIGLIE))}."
    )


# --- rete --------------------------------------------------------------------


def chiama(metodo: str, indirizzo: str, intestazioni: dict, corpo: dict | None = None,
           apri=urllib.request.urlopen) -> tuple[int, dict, bytes]:
    dati = None if corpo is None else json.dumps(corpo).encode("utf-8")
    richiesta = urllib.request.Request(indirizzo, data=dati, method=metodo, headers=intestazioni)
    try:
        with apri(richiesta, timeout=config.TIMEOUT_RETE_SECONDI) as risposta:
            return risposta.status, dict(risposta.headers.items()), risposta.read()
    except urllib.error.HTTPError as errore:
        return errore.code, dict(errore.headers.items()) if errore.headers else {}, errore.read()


def decodifica(grezzo: bytes) -> object:
    testo = grezzo.decode("utf-8", errors="replace")
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        return testo


def leggi_intestazione(intestazioni: dict, nome: str) -> str | None:
    for chiave, valore in intestazioni.items():
        if chiave.lower() == nome.lower():
            return valore
    return None


def secondi_retry_after(intestazioni: dict) -> float | None:
    valore = leggi_intestazione(intestazioni, "Retry-After")
    if valore is None:
        return None
    try:
        return max(0.0, float(valore))
    except ValueError:
        from email.utils import parsedate_to_datetime

        try:
            return max(0.0, parsedate_to_datetime(valore).timestamp() - time.time())
        except (TypeError, ValueError):
            return None


# --- dove sta l'immagine nel risultato ----------------------------------------


def trova_immagine(oggetto: object, percorso: str = "") -> tuple[str, str, str] | None:
    """Cerca nel risultato un link o un base64 d'immagine. Restituisce (percorso, tipo, valore).

    Non sa lo schema: e' proprio quello che si sta cercando di imparare.
    """
    if isinstance(oggetto, dict):
        for chiave, valore in oggetto.items():
            trovata = trova_immagine(valore, f"{percorso}.{chiave}" if percorso else chiave)
            if trovata:
                return trovata
    elif isinstance(oggetto, list):
        for indice, valore in enumerate(oggetto):
            trovata = trova_immagine(valore, f"{percorso}[{indice}]")
            if trovata:
                return trovata
    elif isinstance(oggetto, str):
        if oggetto.startswith("data:image/"):
            return percorso, "data-uri", oggetto
        ultimo = percorso.rsplit(".", 1)[-1]
        if oggetto.startswith(("http://", "https://")) and ultimo not in URL_DEL_ROUTER:
            return percorso, "url", oggetto
        if len(oggetto) > 1000:  # una stringa cosi' lunga in un risultato e' quasi sempre base64
            try:
                dati = base64.b64decode(oggetto, validate=True)
            except ValueError:
                return None
            if tipo_immagine(dati) != "application/octet-stream":
                return percorso, "base64", oggetto
    return None


def byte_immagine(tipo: str, valore: str, apri=urllib.request.urlopen) -> bytes:
    if tipo == "url":
        # Niente chiave qui: il link e' firmato e la chiave non deve uscire
        # verso un dominio che non e' api.comfy.org.
        with apri(urllib.request.Request(valore), timeout=config.TIMEOUT_RETE_SECONDI) as risposta:
            return risposta.read()
    if tipo == "data-uri":
        valore = valore.split(",", 1)[1]
    return base64.b64decode(valore)


# --- i tre comandi -----------------------------------------------------------


def stampa_risposta(dire: Uscita, titolo: str, stato: int, intestazioni: dict,
                    corpo: object, chiave: str) -> None:
    dire(f"{titolo}: HTTP {stato}")
    dire("  intestazioni:")
    dire.json(intestazioni_leggibili(intestazioni, chiave), "    ")
    dire("  corpo:")
    dire.json(corpo, "    ")


def riassumi_schema(dire: Uscita, documento: object) -> None:
    """Le proprieta' d'ingresso e d'uscita, risolvendo i $ref locali."""
    if not isinstance(documento, dict):
        return
    componenti = documento.get("components", {}).get("schemas", {})

    def risolvi(schema: object) -> object:
        if isinstance(schema, dict) and "$ref" in schema:
            return componenti.get(schema["$ref"].rsplit("/", 1)[-1], schema)
        return schema

    for percorso, operazioni in documento.get("paths", {}).items():
        for metodo, operazione in operazioni.items():
            if not isinstance(operazione, dict):
                continue
            dire(f"  {metodo.upper()} {percorso}")
            corpo = (operazione.get("requestBody", {}).get("content", {})
                     .get("application/json", {}).get("schema"))
            if corpo:
                corpo = risolvi(corpo)
                dire(f"    ingresso, obbligatori: {corpo.get('required', [])}")
                for nome, proprieta in corpo.get("properties", {}).items():
                    proprieta = risolvi(proprieta)
                    sintesi = {k: proprieta[k] for k in
                               ("type", "format", "enum", "default", "minimum", "maximum",
                                "description") if k in proprieta}
                    dire(f"      {nome}: {json.dumps(accorcia(sintesi), ensure_ascii=False)}")
            uscita = (operazione.get("responses", {}).get("200", {}).get("content", {})
                      .get("application/json", {}).get("schema"))
            if uscita:
                uscita = risolvi(uscita)
                dire(f"    uscita 200, campi: {sorted(uscita.get('properties', {}))}")


def leggi_schema(dire: Uscita, modello: str, chiave: str, cartella: Path, apri) -> None:
    indirizzo = f"{BASE}/{modello}/openapi.json"
    dire(f"== Schema del modello (gratis) ==\nGET {indirizzo}")
    stato, intestazioni, grezzo = chiama("GET", indirizzo, {"X-API-Key": chiave}, apri=apri)
    documento = decodifica(grezzo)
    if stato == 200 and isinstance(documento, dict):  # numero-non-configurabile: HTTP
        cartella.mkdir(parents=True, exist_ok=True)
        file = cartella / f"{modello.replace('/', '_')}.openapi.json"
        file.write_text(json.dumps(documento, indent=2, ensure_ascii=False), encoding="utf-8")
        dire(f"HTTP {stato}. Schema completo salvato in {file}")
        riassumi_schema(dire, documento)
    else:
        stampa_risposta(dire, "Schema", stato, intestazioni, documento, chiave)


def catalogo(dire: Uscita, chiave: str, apri) -> None:
    dire(f"== Catalogo (gratis) ==\nGET {BASE}")
    cursore, visti = None, set()
    while True:
        query = {"limit": 100}
        if cursore:
            query["cursor"] = cursore
        stato, intestazioni, grezzo = chiama(
            "GET", f"{BASE}?{urllib.parse.urlencode(query)}", {"X-API-Key": chiave}, apri=apri
        )
        corpo = decodifica(grezzo)
        if stato != 200 or not isinstance(corpo, dict):
            stampa_risposta(dire, "Catalogo", stato, intestazioni, corpo, chiave)
            return
        voci = corpo.get("data") or corpo.get("models") or []
        if not voci:
            dire("  Non riconosco la forma del catalogo. Eccolo com'e':")
            dire.json(corpo, "    ")
            return
        for voce in voci:
            if isinstance(voce, dict):
                dire(f"  {voce.get('id')}  ingressi={voce.get('input_modalities', voce.get('inputs', '?'))}")
        cursore = corpo.get("next_cursor") or corpo.get("cursor")
        if not cursore or cursore in visti:
            dire(f"  (campi di una voce: {sorted(voci[0]) if isinstance(voci[0], dict) else '?'})")
            return
        visti.add(cursore)


def genera(dire: Uscita, argomenti, chiave: str, apri, attendi=time.sleep,
           orologio=time.monotonic) -> int:
    modello = argomenti.modello
    vista = Path(argomenti.immagine)
    dati = vista.read_bytes()
    scelto = trova_preset(argomenti.preset)
    prompt = componi(scelto, argomenti.testo)
    corpo = corpo_candidato(modello, prompt, dati, argomenti.base64_nudo)
    chiave_idempotenza = argomenti.chiave_idempotenza or str(uuid.uuid4())
    query = urllib.parse.urlencode({"fallback_provider": "false"})
    indirizzo = f"{BASE}/{modello}/requests?{query}"
    cartella = Path(argomenti.uscita)

    dire("== Generazione (costa crediti) ==")
    dire(f"Destinazione dell'invio: Comfy Router (api.comfy.org) → {modello}. "
         "1 immagine lascia questa macchina.")
    dire(f"Vista: {vista.name}, {tipo_immagine(dati)}, {dimensioni(dati)}, {len(dati)} byte")
    dire(f"Immagine inviata come: {'base64 nudo' if argomenti.base64_nudo else 'data URI'}")
    dire(f"Idempotency-Key: {chiave_idempotenza}")
    dire(f"POST {indirizzo}")
    dire("Corpo (dalla documentazione, da verificare):")
    dire.json(corpo)

    intestazioni = {
        "X-API-Key": chiave,
        "Idempotency-Key": chiave_idempotenza,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        stato, risposte, grezzo = chiama("POST", indirizzo, intestazioni, corpo, apri=apri)
    except (urllib.error.URLError, TimeoutError) as errore:
        dire(f"La rete non ha risposto: {errore}.")
        dire("Cosa fare: rilancia con --chiave-idempotenza "
             f"{chiave_idempotenza}: se il Router aveva gia' accettato, ti rende la "
             "stessa risposta invece di farti pagare due volte.")
        return 3
    inviata = decodifica(grezzo)
    stampa_risposta(dire, "Invio", stato, risposte, inviata, chiave)
    if stato >= 400 or not isinstance(inviata, dict):  # numero-non-configurabile: HTTP
        return 3

    richiesta_id = inviata.get("request_id")
    if not richiesta_id:
        dire("La risposta non contiene request_id: mi fermo qui. Incolla tutto.")
        return 3
    base_lavoro = f"{BASE}/{modello}/requests/{richiesta_id}"
    lettura = {"X-API-Key": chiave, "Accept": "application/json"}
    scadenza = orologio() + config.ATTESA_MASSIMA_SECONDI

    dire("== Attesa ==")
    corpo_stato = inviata
    stato_lavoro = str(inviata.get("status", ""))
    while stato_lavoro != "COMPLETED":
        attesa = secondi_retry_after(risposte)
        attesa = config.INTERVALLO_ATTESA_SECONDI if attesa is None else attesa
        if orologio() + attesa > scadenza:
            dire(f"Non finito entro {config.ATTESA_MASSIMA_SECONDI} s. Il risultato resta "
                 f"sul Router: GET {base_lavoro}")
            return 3
        attendi(attesa)
        stato, risposte, grezzo = chiama("GET", f"{base_lavoro}/status", lettura, apri=apri)
        corpo_stato = decodifica(grezzo)
        if stato != 200 or not isinstance(corpo_stato, dict):  # numero-non-configurabile: HTTP
            stampa_risposta(dire, "Stato", stato, risposte, corpo_stato, chiave)
            return 3
        stato_lavoro = str(corpo_stato.get("status", ""))
        dire(f"  {stato_lavoro}  coda={corpo_stato.get('queue_position')}  "
             f"Retry-After={leggi_intestazione(risposte, 'Retry-After')}  "
             f"altri campi={sorted(set(corpo_stato) - {'status', 'queue_position'})}")
    stampa_risposta(dire, "Ultimo stato", stato, risposte, corpo_stato, chiave)

    stato, risposte, grezzo = chiama("GET", base_lavoro, lettura, apri=apri)
    risultato = decodifica(grezzo)
    cartella.mkdir(parents=True, exist_ok=True)
    nome = modello.replace("/", "_")
    (cartella / f"{nome}.risultato.json").write_text(
        json.dumps(risultato, indent=2, ensure_ascii=False) if not isinstance(risultato, str)
        else risultato, encoding="utf-8")
    stampa_risposta(dire, "Risultato", stato, risposte, risultato, chiave)

    trovata = trova_immagine(risultato)
    if not trovata:
        dire("Nel risultato non ho trovato un'immagine. Incolla tutto: e' l'informazione che serve.")
        return 3
    percorso, tipo, valore = trovata
    dire(f"Immagine trovata in: {percorso} ({tipo})")
    immagine = byte_immagine(tipo, valore, apri=apri)
    estensione = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(
        tipo_immagine(immagine), "bin")
    file = cartella / f"{nome}.{estensione}"
    file.write_bytes(immagine)
    dentro, fuori = dimensioni(dati), dimensioni(immagine)
    dire(f"Salvata in {file}: {tipo_immagine(immagine)}, {fuori}, {len(immagine)} byte")
    if dentro and fuori:
        dire(f"Rapporto: vista {dentro[0] / dentro[1]:.3f}, render {fuori[0] / fuori[1]:.3f}")
    return 0


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python scripts/sonda_comfy.py", description=__doc__.split("\n")[0])
    parser.add_argument("--modello", default=MODELLO_PREDEFINITO,
                        help=f"ID del Router, provider/modello (predefinito: {MODELLO_PREDEFINITO})")
    parser.add_argument("--immagine", default=str(VISTA_PREDEFINITA),
                        help="la vista da mandare (predefinita: la cattura vera della prova)")
    parser.add_argument("--preset", default="base", help="il preset da cui prendere il prompt")
    parser.add_argument("--testo", default="", help="due parole in coda al prompt del preset")
    parser.add_argument("--uscita", default="sonda-comfy", help="cartella per schema, risposte e immagine")
    parser.add_argument("--solo-schema", action="store_true", help="legge lo schema e si ferma: gratis")
    parser.add_argument("--catalogo", action="store_true", help="elenca i modelli del Router: gratis")
    parser.add_argument("--base64-nudo", action="store_true",
                        help="manda il base64 senza 'data:image/png;base64,' davanti")
    parser.add_argument("--chiave-idempotenza",
                        help="riusa la Idempotency-Key di un tentativo interrotto")
    return parser


def main(argv: list[str] | None = None, apri=urllib.request.urlopen, flusso=None,
         attendi=time.sleep, orologio=time.monotonic) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    chiave = os.environ.get(VARIABILE_CHIAVE, "").strip()
    dire = Uscita(chiave, flusso)
    if not chiave:
        dire(f"Manca la chiave: la sonda la legge da {VARIABILE_CHIAVE}.")
        dire("Cosa fare: crea una chiave nel tuo workspace Comfy e mettila in "
             f"{VARIABILE_CHIAVE}. Non serve incollarla da nessuna parte.")
        return 4
    try:
        if argomenti.catalogo:
            catalogo(dire, chiave, apri)
            return 0
        leggi_schema(dire, argomenti.modello, chiave, Path(argomenti.uscita), apri)
        if argomenti.solo_schema:
            return 0
        return genera(dire, argomenti, chiave, apri, attendi, orologio)
    except (urllib.error.URLError, TimeoutError) as errore:
        dire(f"Non sono riuscito a raggiungere api.comfy.org: {errore}.")
        dire("Cosa fare: controlla la connessione o il proxy aziendale. Se l'errore "
             "e' arrivato dopo l'invio, il lavoro puo' essere gia' partito: guarda "
             "l'Idempotency-Key stampata sopra e rilancia con --chiave-idempotenza.")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
