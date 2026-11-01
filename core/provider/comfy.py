"""Comfy Router: il provider predefinito dal 2026-10-21.

Scelto perche' e' a consumo dai crediti del workspace Comfy, senza
abbonamento, e con una chiave sola arriva a piu' modelli di modifica
d'immagine (FLUX.1 Kontext, Nano Banana, Seedream, GPT Image). Solo libreria
standard, niente comfy-sdk, come magnific.py. La chiave e' del cliente: sta
in una variabile d'ambiente, mai nel repository.

Da dove viene quello che c'e' scritto qui:

- il protocollo della coda (POST .../requests, GET .../status con
  Retry-After, GET del risultato), le intestazioni X-API-Key e
  Idempotency-Key, fallback_provider e il 402 insufficient_credits vengono
  dalla documentazione di docs.comfy.org, letta il 2026-10-21 solo attraverso
  una ricerca: la rete della sessione non raggiungeva il sito. MAI ESEGUITO.
- il 2026-10-27 la sonda e' girata davvero sul PC di Riccardo, con
  FLUX.1 Kontext Pro e Nano Banana 2: invio, attesa fino a COMPLETED e
  lettura del risultato sono andati a buon fine.
- lo schema di ogni modello (che campi vuole, dove rimette l'immagine) sta
  in SCHEMI e si scrive solo partendo dall'uscita di una chiamata vera di
  scripts/sonda_comfy.py. Un modello senza schema non parte e lo dice.

Differenza che conta per il prodotto: i modelli di modifica del Router non
hanno un riferimento strutturale con una forza da 0 a 100. Se tengono la
geometria, la tengono per come sono fatti e per il prompt. Quindi
`usa_forza_struttura` e' falso e la ricetta scrive la forza come assente, non
come 70.
"""

from __future__ import annotations

import base64
import math
import os
import time
import urllib.parse
import uuid
from dataclasses import dataclass, replace
from email.utils import parsedate_to_datetime
from typing import Callable

from .. import config, immagine as modulo_immagine
from ..errori import ChiaveMancante, ErroreProvider, errore_da_stato_http
from ..ricetta import Ricetta, impronta
from .base import (
    IN_LAVORAZIONE,
    INVIATO,
    Provider,
    RichiestaGenerazione,
    RichiestaRegione,
    Risultato,
)
from .trasporto import ErroreRete, TrasportoConIntestazioni, TrasportoHTTP

BASE = "https://api.comfy.org/v2/models"
INTESTAZIONE_CHIAVE = "X-API-Key"
VARIABILI_CHIAVE = ("COMFY_API_KEY", "AIRENDER_COMFY_API_KEY")

# Il fallback del Router e' acceso se non lo si spegne: se il provider del
# modello fallisce, la stessa immagine riparte verso un altro provider. Il
# pubblico lavora sotto NDA e la destinazione si annuncia prima dell'invio,
# quindi si spegne. Il Router legge come "acceso" qualunque valore che non
# sia esattamente "false".
FALLBACK = "false"

STATO_FINITO = "COMPLETED"
STATI_IN_CORSO = ("IN_QUEUE", "IN_PROGRESS")
# Risposte che vale la pena ripetere, con la stessa Idempotency-Key.
STATI_PASSEGGERI = (429, 500, 502, 503, 504)  # numero-non-configurabile: codici HTTP
ANCORA_IN_CORSO = 202  # numero-non-configurabile: codice HTTP del risultato non pronto


@dataclass(frozen=True)
class SchemaModello:
    """Come parla un modello del Router. Si scrive dall'uscita della sonda, non dai documenti.

    - `corpo` costruisce il JSON della richiesta da una RichiestaGenerazione;
    - `immagine` trova l'immagine nel risultato e la restituisce come
      ("url" | "base64" | "data-uri", valore);
    - `verificato_il` e' la data della chiamata vera che lo ha confermato;
      vuoto vuol dire mai: lo schema e' quello della sua famiglia, aggiunto
      su richiesta prima della sonda, e l'interfaccia lo dice prima di ogni
      invio (`avviso`). Il primo render vero e' la verifica;
    - `piu_immagini` dice se il corpo sa portare immagini dopo la vista, e
      `piu_immagini_verificato_il` quando una chiamata vera lo ha confermato
      (vuoto: mai). Un corpo che le porta senza verifica si usa solo dal banco
      di prova, che lo dice prima dell'invio.
    """

    corpo: Callable[[RichiestaGenerazione], dict]
    immagine: Callable[[object], tuple[str, str]]
    verificato_il: str
    piu_immagini: bool = False
    piu_immagini_verificato_il: str = ""
    # I rapporti che il modello accetta. Vuoto: qualunque rapporto (il corpo
    # chiede la misura esatta in pixel), quindi niente cornice.
    rapporti: tuple[str, ...] = ()


# Rapporti che sia FLUX.1 Kontext sia Gemini accettano (schemi letti dalla
# sonda il 2026-10-27). Si manda il piu' vicino alla vista: un rapporto
# diverso schiaccia l'edificio.
RAPPORTI = ("21:9", "16:9", "3:2", "4:3", "1:1", "3:4", "2:3", "9:16")


def rapporto_piu_vicino(dati: bytes, rapporti: tuple[str, ...] = RAPPORTI) -> str:
    larghezza, altezza = modulo_immagine.dimensioni(dati)
    voluto = larghezza / altezza

    def scarto(rapporto: str) -> float:
        a, b = (int(x) for x in rapporto.split(":"))
        return abs(a / b - voluto)

    return min(rapporti, key=scarto)


def con_cornice(richiesta: RichiestaGenerazione,
                rapporti: tuple[str, ...] = RAPPORTI) -> tuple[RichiestaGenerazione, "modulo_immagine.Cornice | None"]:
    """La richiesta con la vista (e le immagini in piu') al rapporto esatto che si mandera'.

    Il modello accetta solo i RAPPORTI fissi: una vista 1,63 partiva come 3:2
    e tornava di un'altra forma. Allargata con una cornice al rapporto piu'
    vicino, torna della stessa forma e la cornice si taglia (togli_cornice).
    Le immagini in piu' (maschera, mappa) hanno la misura della vista e si
    allargano allo stesso modo, cosi' restano sovrapposte.
    """
    larghezza, altezza = modulo_immagine.dimensioni(richiesta.immagine)
    a, b = (int(x) for x in rapporto_piu_vicino(richiesta.immagine, rapporti).split(":"))
    voluto = a / b
    if abs(larghezza / altezza - voluto) / voluto <= config.CORNICE_TOLLERANZA:
        return richiesta, None
    vista, cornice = modulo_immagine.allarga_a_rapporto(richiesta.immagine, voluto)
    in_piu = tuple(
        modulo_immagine.allarga_a_rapporto(dati, voluto)[0]
        if modulo_immagine.dimensioni(dati) == (larghezza, altezza) else dati
        for dati in richiesta.immagini_in_piu
    )
    return replace(richiesta, immagine=vista, immagini_in_piu=in_piu), cornice


def immagine_base64(dati: bytes) -> str:
    """La vista in base64 senza prefisso: e' il formato con cui le due chiamate vere sono riuscite."""
    return base64.b64encode(dati).decode("ascii")


def _corpo_kontext(richiesta: RichiestaGenerazione) -> dict:
    corpo = {
        "prompt": richiesta.prompt,
        "input_image": immagine_base64(richiesta.immagine),
        "aspect_ratio": rapporto_piu_vicino(richiesta.immagine),
        "output_format": "png",
    }
    if richiesta.seme is not None:
        corpo["seed"] = richiesta.seme
    return corpo


def _immagine_kontext(uscita: object) -> tuple[str, str]:
    """Il documento di BFL inoltrato dal Router: il link firmato sta in result.sample."""
    try:
        return "url", str(uscita["result"]["sample"])
    except (KeyError, TypeError):
        raise _risultato_senza_immagine() from None


def _corpo_gemini(richiesta: RichiestaGenerazione) -> dict:
    # Gemini non ha un campo per il seme: la ricetta lo salva comunque, ma
    # rieseguire non ridà la stessa immagine (lo dice gia' l'avviso).
    # Le immagini in piu' seguono la vista come altre parti inlineData, nello
    # stesso ordine: e' la forma di Vertex AI per piu' immagini, mai provata
    # attraverso il Router (PRD, sezione 9).
    immagini = (richiesta.immagine, *richiesta.immagini_in_piu)
    return {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": richiesta.prompt},
                *({"inlineData": {"mimeType": tipo_mime(dati), "data": immagine_base64(dati)}}
                  for dati in immagini),
            ],
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": _config_immagine_gemini(richiesta),
        },
    }


def _config_immagine_gemini(richiesta: RichiestaGenerazione) -> dict:
    """Rapporto e, sopra 1k, grandezza del render.

    imageSize ("2K", "4K") e' un campo dei documenti di Vertex AI, mai passato
    dal Router (2026-10-31): a 1k non si manda, cosi' il corpo resta quello
    verificato il 2026-10-27.
    """
    config_immagine = {"aspectRatio": rapporto_piu_vicino(richiesta.immagine)}
    if richiesta.dimensione_render in ("2k", "4k"):
        config_immagine["imageSize"] = richiesta.dimensione_render.upper()
    return config_immagine


def _immagine_gemini(uscita: object) -> tuple[str, str]:
    """La risposta di Vertex AI: l'immagine e' una parte con inlineData (base64) o fileData (link).

    Si sceglie la parte per il campo, non per posizione: accanto all'immagine
    puo' esserci una parte di testo (schema del Router, 2026-10-27).
    """
    try:
        parti = uscita["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        raise _risultato_senza_immagine() from None
    for parte in parti:
        if not isinstance(parte, dict):
            continue
        if isinstance(parte.get("inlineData"), dict) and parte["inlineData"].get("data"):
            return "base64", str(parte["inlineData"]["data"])
        if isinstance(parte.get("fileData"), dict) and parte["fileData"].get("fileUri"):
            return "url", str(parte["fileData"]["fileUri"])
    raise _risultato_senza_immagine()


# --- GPT Image e Seedream: dalla documentazione di Comfy Router ----------------
# Letta il 2026-11-01 (docs.comfy.org/development/comfy-router/models, pagine
# «code» di openai/gpt-image-1.5 e byteplus/seedream-5-0-260128). MAI ESEGUITO:
# il primo render vero e' la prova, e lo Studio lo dice prima dell'invio.

# GPT Image accetta solo queste misure (campo size): si manda la piu' vicina
# alla vista, allargata con la cornice e poi tagliata, come per gli altri.
MISURE_GPT = {"3:2": "1536x1024", "1:1": "1024x1024", "2:3": "1024x1536"}


def _corpo_gpt(richiesta: RichiestaGenerazione) -> dict:
    """Modifica d'immagine: la vista (e le immagini in piu') nel campo image, come data-URI.

    Il Router prende gli URL solo dal suo archivio: il data-URI e' l'unica
    forma che la documentazione dice funzionante da fuori.
    """
    immagini = (richiesta.immagine, *richiesta.immagini_in_piu)
    return {
        "prompt": richiesta.prompt,
        "image": [immagine_data_uri(dati) for dati in immagini],
        "size": MISURE_GPT[rapporto_piu_vicino(richiesta.immagine, tuple(MISURE_GPT))],
        "quality": "high",
        "output_format": "png",
        "n": 1,
    }


# Seedream 5.0 chiede la misura in pixel (WxH): l'area deve stare fra circa
# 2560x1440 e 3072x3072, il rapporto fra 1/16 e 16. Si chiede la forma esatta
# della vista, quindi niente cornice.
AREA_SEEDREAM = {"1k": 2560 * 1440, "2k": 2048 * 2048, "4k": 3072 * 3072}  # numero-non-configurabile: limiti di Seedream 5.0 (documentazione del Router)
MULTIPLO_SEEDREAM = 16  # numero-non-configurabile: misure multiple di 16, come i modelli a diffusione si aspettano


def misura_seedream(dati: bytes, risoluzione: str = "") -> str:
    larghezza, altezza = modulo_immagine.dimensioni(dati)
    area = AREA_SEEDREAM.get(risoluzione or "2k", AREA_SEEDREAM["2k"])
    rapporto = larghezza / altezza
    w = max(MULTIPLO_SEEDREAM, round(math.sqrt(area * rapporto) / MULTIPLO_SEEDREAM) * MULTIPLO_SEEDREAM)
    h = max(MULTIPLO_SEEDREAM, round(area / w / MULTIPLO_SEEDREAM) * MULTIPLO_SEEDREAM)
    return f"{w}x{h}"


def _corpo_seedream(richiesta: RichiestaGenerazione) -> dict:
    immagini = [immagine_data_uri(dati) for dati in (richiesta.immagine, *richiesta.immagini_in_piu)]
    corpo = {
        "prompt": richiesta.prompt,
        "image": immagini[0] if len(immagini) == 1 else immagini,
        "size": misura_seedream(richiesta.immagine, richiesta.dimensione_render),
        "response_format": "b64_json",
        "watermark": False,
        "sequential_image_generation": "disabled",
    }
    if richiesta.seme is not None:
        corpo["seed"] = richiesta.seme
    return corpo


def _immagine_dati(uscita: object) -> tuple[str, str]:
    """Forma OpenAI, usata anche da Seedream: data[0].b64_json oppure data[0].url."""
    try:
        voce = uscita["data"][0]
    except (KeyError, IndexError, TypeError):
        raise _risultato_senza_immagine() from None
    if isinstance(voce, dict) and voce.get("b64_json"):
        return "base64", str(voce["b64_json"])
    if isinstance(voce, dict) and voce.get("url"):
        return "url", str(voce["url"])
    raise _risultato_senza_immagine()


def _risultato_senza_immagine() -> ErroreProvider:
    return ErroreProvider(
        "Comfy Router ha chiuso il lavoro senza un'immagine nel risultato.",
        "Riprova. Se si ripete, e' cambiato lo schema del modello e va rifatta "
        "la sonda (python scripts/sonda_comfy.py).",
    )


# Scritti dall'uscita di scripts/sonda_comfy.py sul PC di Riccardo, il
# 2026-10-27: schema letto da /openapi.json e una generazione vera per
# modello, con l'immagine in base64 senza prefisso (--base64-nudo). Un
# modello che non e' qui non parte: va prima sondato.
SCHEMI: dict[str, SchemaModello] = {
    "bfl/flux-kontext-pro": SchemaModello(
        corpo=_corpo_kontext,
        immagine=_immagine_kontext,
        verificato_il="2026-10-27",
        rapporti=RAPPORTI,
    ),
    "vertexai/gemini-3.1-flash-image": SchemaModello(
        corpo=_corpo_gemini,
        immagine=_immagine_gemini,
        verificato_il="2026-10-27",
        piu_immagini=True,
        rapporti=RAPPORTI,
    ),
    # Nano Banana Pro: aggiunto il 2026-10-31 su richiesta di Riccardo, PRIMA
    # della sonda. Il nome viene dalla documentazione di Comfy; il corpo e'
    # quello di Nano Banana 2 (stessa famiglia Gemini su Vertex AI), non
    # verificato. Se il Router lo rifiuta, l'errore lo dice e si rifa' la
    # sonda: scripts/sonda_comfy.py --modello vertexai/gemini-3-pro-image.
    "vertexai/gemini-3-pro-image": SchemaModello(
        corpo=_corpo_gemini,
        immagine=_immagine_gemini,
        verificato_il="",
        rapporti=RAPPORTI,
    ),
    # GPT Image 2 e Seedream 5.0: aggiunti il 2026-11-01 su richiesta di
    # Riccardo, dalla documentazione del Router e senza sonda (vedi sopra).
    "openai/gpt-image-2": SchemaModello(
        corpo=_corpo_gpt,
        immagine=_immagine_dati,
        verificato_il="",
        piu_immagini=True,
        rapporti=tuple(MISURE_GPT),
    ),
    "byteplus/seedream-5-0-260128": SchemaModello(
        corpo=_corpo_seedream,
        immagine=_immagine_dati,
        verificato_il="",
        piu_immagini=True,
    ),
}


def chiave_da_ambiente() -> str | None:
    """La chiave dell'utente, presa dall'ambiente. Mai da un file del repo."""
    for nome in VARIABILI_CHIAVE:
        valore = os.environ.get(nome, "").strip()
        if valore:
            return valore
    return None


def tipo_mime(dati: bytes) -> str:
    """Dai primi byte, senza aprire l'immagine."""
    if dati.startswith(b"\x89PNG"):
        return "image/png"
    if dati.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if dati[:4] == b"RIFF" and dati[8:12] == b"WEBP":  # numero-non-configurabile: intestazione WebP
        return "image/webp"
    return "application/octet-stream"


def immagine_data_uri(dati: bytes) -> str:
    """La vista come la chiede il Router nei campi immagine: data:image/png;base64,..."""
    return f"data:{tipo_mime(dati)};base64,{base64.b64encode(dati).decode('ascii')}"


def secondi_retry_after(intestazioni: dict) -> float | None:
    """Retry-After in secondi: puo' arrivare come numero o come data HTTP."""
    valore = intestazioni.get("retry-after")
    if valore is None:
        return None
    try:
        return max(0.0, float(valore))
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(valore).timestamp() - time.time())
    except (TypeError, ValueError):
        return None


class ProviderComfy(Provider):
    nome = "comfy"
    destinazione = "Comfy Router (api.comfy.org)"
    usa_forza_struttura = False

    def __init__(
        self,
        chiave: str | None = None,
        trasporto: TrasportoConIntestazioni | None = None,
        attesa=time.sleep,
        orologio=time.monotonic,
        nuova_chiave_idempotenza=lambda: str(uuid.uuid4()),
    ) -> None:
        self.chiave = chiave or chiave_da_ambiente()
        self.trasporto = trasporto or TrasportoHTTP()
        self._attesa = attesa
        self._orologio = orologio
        self._nuova_chiave_idempotenza = nuova_chiave_idempotenza

    def destinazione_per(self, modello: str) -> str:
        return f"{self.destinazione} → {modello}"

    def cosa_manca(self, modello: str) -> str | None:
        if modello in SCHEMI:
            return None
        return (
            f"lo schema del modello {modello} non e' ancora stato verificato con "
            "una chiamata vera, quindi l'invio vero si fermera' prima di partire."
        )

    def avviso(self, modello: str) -> str | None:
        schema = SCHEMI.get(modello)
        if schema is None or schema.verificato_il:
            return None
        return (
            f"{modello} non e' ancora stato provato con una chiamata vera: questo "
            "render e' la prova. Se il servizio lo rifiuta, l'errore lo dice."
        )

    def accetta_piu_immagini(self, modello: str) -> bool:
        schema = SCHEMI.get(modello)
        return schema is not None and schema.piu_immagini

    def avviso_piu_immagini(self, modello: str) -> str | None:
        schema = SCHEMI.get(modello)
        if schema is None or not schema.piu_immagini or schema.piu_immagini_verificato_il:
            return None
        return (
            f"{modello} non ha mai ricevuto due immagini in una chiamata vera: "
            "questo render e' la prova. Se il servizio le rifiuta, l'errore lo dice."
        )

    def controlla_prima_dell_invio(self, modello: str, immagine: bytes) -> None:
        self._assicura_chiave()
        self._assicura_peso(immagine)
        self._schema(modello)

    # --- cose che il prodotto chiede ----------------------------------------

    def genera(self, richiesta: RichiestaGenerazione) -> Risultato:
        return self._genera(richiesta, avvisi_in_piu=[])

    def riesegui(self, ricetta: Ricetta, immagine: bytes) -> Risultato:
        """Rifa' lo stesso livello dagli stessi parametri, con la stessa vista.

        Con una Idempotency-Key nuova: riusare quella vecchia entro 24 ore
        renderebbe l'immagine di allora senza rifarla, e chiamarlo
        riesecuzione sarebbe falso.
        """
        if impronta(immagine) != ricetta.impronta_sorgente:
            raise ErroreProvider(
                "La vista di partenza non e' la stessa con cui era stato fatto "
                "questo livello.",
                "Ripesca la vista originale, oppure rigenera il livello da capo: "
                "con un'altra vista gli stessi parametri danno un'altra immagine.",
            )
        richiesta = RichiestaGenerazione(
            immagine=immagine,
            prompt=ricetta.prompt,
            preset=ricetta.preset,
            preset_versione=ricetta.preset_versione,
            modello=ricetta.modello,
            grana=ricetta.grana,
            dettaglio_grana=ricetta.dettaglio_grana or 0,
            testo_utente=ricetta.testo_utente,
            seme=ricetta.seme,
        )
        return self._genera(richiesta, avvisi_in_piu=[
            "Comfy Router non ha una generazione fissa verificata: la stessa "
            "ricetta puo' dare un'immagine diversa.",
        ])

    def modifica_regione(self, richiesta: RichiestaRegione) -> Risultato:
        raise ErroreProvider(
            "Il ritocco con una maschera non passa ancora da Comfy Router: "
            "nessun modello con maschera e' stato verificato.",
            "Per cambiare un materiale rigenera l'immagine col testo nuovo "
            "(modalita' variante). Il ritocco con maschera c'e' solo con "
            "--provider magnific, che pero' richiede un piano a crediti.",
        )

    def fa_video(self) -> bool:
        return True

    def controlla_video(self, immagini) -> None:
        """Chiave e peso di ogni immagine: quello che fermerebbe un video prima di mandarlo."""
        self._assicura_chiave()
        for dati in immagini:
            self._assicura_peso(dati)

    def genera_video(self, modello: str, corpo: dict, immagini: tuple[bytes, ...]) -> tuple[bytes, dict]:
        """Un video dal Router: stesso protocollo di coda, attesa piu' lunga, mp4 scaricato.

        Il corpo lo costruisce core/video.py dalla documentazione del modello;
        qui si controllano chiave e peso delle immagini, si manda col fallback
        spento e si scarica `content.video_url` (link firmato, scade).
        """
        self.controlla_video(immagini)
        chiave_idempotenza = self._nuova_chiave_idempotenza()
        uscita, dettagli = self._esegui(modello, corpo, chiave_idempotenza,
                                        attesa_massima=config.VIDEO_ATTESA_MASSIMA_SECONDI)
        try:
            indirizzo = str(uscita["content"]["video_url"])
        except (KeyError, TypeError):
            raise ErroreProvider(
                "Comfy Router ha chiuso il lavoro senza un video nel risultato.",
                "Riprova. Se si ripete, e' cambiato lo schema del modello video.",
            ) from None
        video = self.trasporto.scarica(indirizzo)
        if video[4:8] not in (b"ftyp", b"moov"):  # numero-non-configurabile: intestazione MP4/MOV
            raise ErroreProvider(
                f"{self.destinazione} ha mandato un file che non e' un video MP4.",
                "Riprova. Se si ripete, e' cambiato lo schema del modello video.",
            )
        return video, {**dettagli, "chiave_idempotenza": chiave_idempotenza,
                       "fallback_provider": FALLBACK}

    # --- dentro ---------------------------------------------------------------

    def _genera(self, richiesta: RichiestaGenerazione, avvisi_in_piu: list[str]) -> Risultato:
        self._assicura_chiave()
        for dati in (richiesta.immagine, *richiesta.immagini_in_piu):
            self._assicura_peso(dati)
        schema = self._schema(richiesta.modello)
        if richiesta.immagini_in_piu and not schema.piu_immagini:
            raise ErroreProvider(
                f"{richiesta.modello} riceve una sola immagine per invio: la "
                f"richiesta ne porta {1 + len(richiesta.immagini_in_piu)}. Non ho inviato niente.",
                "Togli le immagini in piu' (maschera, mappa), oppure usa Nano Banana 2.",
            )

        inviata, cornice = con_cornice(richiesta, schema.rapporti) if schema.rapporti else (richiesta, None)
        corpo = schema.corpo(inviata)
        chiave_idempotenza = self._nuova_chiave_idempotenza()
        uscita, dettagli = self._esegui(richiesta.modello, corpo, chiave_idempotenza)
        tipo, valore = schema.immagine(uscita)
        dati = self._byte_immagine(tipo, valore)
        if cornice is not None:
            dati = modulo_immagine.togli_cornice(dati, cornice)
            dettagli = {**dettagli, "cornice": cornice.come_dizionario()}

        ricetta = Ricetta(
            provider=self.nome,
            modello=richiesta.modello,
            preset=richiesta.preset,
            preset_versione=richiesta.preset_versione,
            prompt=richiesta.prompt,
            testo_utente=richiesta.testo_utente,
            grana=richiesta.grana,
            dettaglio_grana=None,
            forza_struttura=None,
            risoluzione=((richiesta.dimensione_render or "1k") if schema.corpo is _corpo_gemini
                         else str(corpo.get("size", ""))),
            aspetto="",
            generazione_fissa=False,
            impronta_sorgente=impronta(richiesta.immagine),
            seme=richiesta.seme,
            parametri={
                "corpo": _senza_immagini(corpo, (inviata.immagine, *inviata.immagini_in_piu)),
                "immagini_in_piu": [impronta(d) for d in richiesta.immagini_in_piu],
                "fallback_provider": FALLBACK,
                "chiave_idempotenza": chiave_idempotenza,
                "schema_verificato_il": schema.verificato_il,
                **dettagli,
            },
        )
        avvisi = [
            "Scostamento della geometria non misurato: il motore non lo sa "
            "ancora calcolare. Guarda gli spigoli a occhio.",
            f"{richiesta.modello} non ha una forza della struttura: se la "
            "geometria tiene, la tiene per come e' fatto il modello e per il "
            "prompt. Confronta gli spigoli con la vista di partenza.",
            *avvisi_in_piu,
        ]
        servito_da = dettagli.get("servito_da")
        if servito_da:
            avvisi.append(
                f"Il Router dice di aver servito la chiamata con {servito_da}, "
                "un provider diverso da quello annunciato, anche se il fallback "
                "era spento. Segnalalo prima di mandare altre viste sotto NDA."
            )
        return Risultato(
            immagine=dati,
            formato=tipo_mime(dati).split("/")[-1].replace("jpeg", "jpg"),
            ricetta=ricetta,
            scostamento_geometria=None,
            avvisi=avvisi,
        )

    def _schema(self, modello: str) -> SchemaModello:
        try:
            return SCHEMI[modello]
        except KeyError:
            raise ErroreProvider(
                f"Il modello {modello} non ha ancora uno schema verificato con "
                "una chiamata vera, quindi non parte niente.",
                f"Lancia python scripts/sonda_comfy.py --modello {modello} "
                "(costa una generazione) e porta la sua uscita nella sessione di "
                "sviluppo: lo schema si scrive in core/provider/comfy.py da li'.",
            ) from None

    def _esegui(self, modello: str, corpo: dict, chiave_idempotenza: str,
                attesa_massima: float | None = None) -> tuple[object, dict]:
        """Coda del Router: invio, attesa rispettando Retry-After, risultato."""
        massimo = config.ATTESA_MASSIMA_SECONDI if attesa_massima is None else attesa_massima
        query = urllib.parse.urlencode({"fallback_provider": FALLBACK})
        intestazioni = {
            INTESTAZIONE_CHIAVE: self.chiave,
            "Idempotency-Key": chiave_idempotenza,
            "Accept": "application/json",
        }
        stato, risposte, inviata = self._con_tentativi(
            "POST", f"{BASE}/{modello}/requests?{query}", intestazioni, corpo
        )
        if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
            raise self._errore(stato, risposte, inviata, modello)
        richiesta_id = inviata.get("request_id") if isinstance(inviata, dict) else None
        if not richiesta_id:
            raise ErroreProvider(
                f"{self.destinazione} non ha detto che lavoro ha aperto.",
                "Riprova. Se si ripete, e' cambiata l'API del servizio e va "
                "aggiornato il file core/provider/comfy.py.",
                stato=stato,
            )
        dettagli = {
            "richiesta_id": richiesta_id,
            "id_router": risposte.get("x-comfy-request-id", ""),
        }
        servito_da = risposte.get("x-comfy-router-fallback-provider")
        if servito_da:
            dettagli["servito_da"] = servito_da

        # Le letture portano la chiave ma non l'idempotenza: non spendono.
        lettura = {INTESTAZIONE_CHIAVE: self.chiave, "Accept": "application/json"}
        lavoro = f"{BASE}/{modello}/requests/{urllib.parse.quote(str(richiesta_id), safe='')}"
        scadenza = self._orologio() + massimo

        corpo_stato = inviata
        while (stato_router := self._stato_lavoro(corpo_stato, richiesta_id)) != STATO_FINITO:
            self._segnala(IN_LAVORAZIONE if stato_router == "IN_PROGRESS" else INVIATO)
            self._aspetta(risposte, scadenza, richiesta_id, massimo)
            stato, risposte, corpo_stato = self._con_tentativi("GET", f"{lavoro}/status", lettura)
            if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
                raise self._errore(stato, risposte, corpo_stato, modello)
        self._assicura_senza_errore(corpo_stato, richiesta_id)

        while True:
            stato, risposte, uscita = self._con_tentativi("GET", lavoro, lettura)
            if stato == ANCORA_IN_CORSO:
                self._aspetta(risposte, scadenza, richiesta_id, massimo)
                continue
            if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
                raise self._errore(stato, risposte, uscita, modello)
            # Il Router dice quanto ha scalato sulla lettura del risultato
            # (17.17 crediti per Nano Banana 2, sonda del 2026-10-27).
            if risposte.get("x-comfy-credits-used"):
                dettagli["crediti_usati"] = risposte["x-comfy-credits-used"]
            return uscita, dettagli

    def _con_tentativi(
        self, metodo: str, url: str, intestazioni: dict, corpo: dict | None = None
    ) -> tuple[int, dict, object]:
        """La stessa chiamata, con le stesse intestazioni, fino a TENTATIVI_INVIO_MASSIMI volte.

        Stesse intestazioni vuol dire stessa Idempotency-Key: se il primo
        invio era arrivato, il Router rende quella risposta e non addebita
        una seconda generazione.
        """
        for tentativo in range(1, config.TENTATIVI_INVIO_MASSIMI + 1):
            ultimo = tentativo == config.TENTATIVI_INVIO_MASSIMI
            try:
                stato, risposte, corpo_risposta = self.trasporto.chiama(
                    metodo, url, intestazioni, corpo
                )
            except ErroreRete as errore:
                if ultimo:
                    raise ErroreProvider(
                        errore.fatto,
                        errore.cosa_fare + " Prima di rilanciare guarda i crediti "
                        "del workspace Comfy: se sono scesi, la generazione era "
                        "partita e rilanciando la paghi due volte.",
                    ) from None
                self._attesa(config.INTERVALLO_ATTESA_SECONDI)
                continue
            if stato in STATI_PASSEGGERI and not ultimo:
                attesa = secondi_retry_after(risposte)
                attesa = config.INTERVALLO_ATTESA_SECONDI if attesa is None else attesa
                if attesa <= config.ATTESA_MASSIMA_SECONDI:
                    self._attesa(attesa)
                    continue
            return stato, risposte, corpo_risposta
        raise AssertionError("non raggiungibile")  # il ciclo esce sempre con return o raise

    def _aspetta(self, risposte: dict, scadenza: float, richiesta_id: str,
                 massimo: float | None = None) -> None:
        """Aspetta quanto chiede Retry-After. Se supera il tempo concesso, lo dice subito."""
        attesa = secondi_retry_after(risposte)
        attesa = config.INTERVALLO_ATTESA_SECONDI if attesa is None else attesa
        if self._orologio() + attesa > scadenza:
            raise ErroreProvider(
                f"{self.destinazione} non ha finito entro "
                f"{config.ATTESA_MASSIMA_SECONDI if massimo is None else massimo} secondi.",
                "Il lavoro puo' essere ancora in corso sul Router, che conserva il "
                f"risultato per 24 ore (richiesta {richiesta_id}): controlla i "
                "crediti del workspace prima di rilanciare, cosi' non lo paghi "
                "due volte.",
            )
        self._attesa(attesa)

    def _stato_lavoro(self, corpo: object, richiesta_id: str) -> str:
        stato = str(corpo.get("status", "")).upper() if isinstance(corpo, dict) else ""
        if stato == STATO_FINITO or stato in STATI_IN_CORSO:
            return stato
        raise ErroreProvider(
            f"{self.destinazione} ha risposto con uno stato che non conosco: "
            f"{stato or 'nessuno'} (richiesta {richiesta_id}).",
            "Riprova fra qualche minuto. Se si ripete, e' cambiata l'API del "
            "servizio e va aggiornato il file core/provider/comfy.py.",
        )

    def _assicura_senza_errore(self, corpo: dict, richiesta_id: str) -> None:
        """Il Router non ha uno stato "fallito": un lavoro finito male e' COMPLETED con un errore."""
        tipo = _tipo_errore(corpo, {})
        if tipo:
            raise ErroreProvider(
                f"{self.destinazione} ha chiuso il lavoro con un errore: {tipo} "
                f"(richiesta {richiesta_id}).",
                "Riprova, magari con un preset diverso. Se si ripete sempre "
                "sulla stessa vista, e' la vista a non piacere al modello.",
            )

    def _errore(self, stato: int, risposte: dict, corpo: object, modello: str) -> ErroreProvider:
        tipo = _tipo_errore(corpo, risposte)
        dettaglio = _testo(corpo)
        coda = f" Il servizio ha aggiunto: {dettaglio}" if dettaglio else ""
        if stato == 402 or tipo == "insufficient_credits":  # numero-non-configurabile: HTTP
            return ErroreProvider(
                "Il credito del tuo workspace Comfy e' finito: la generazione non "
                "e' partita.",
                "Ricarica i crediti del workspace a cui appartiene la chiave, "
                "dalla sua pagina di fatturazione su comfy.org, poi rilancia lo "
                "stesso comando. AIRENDER non gestisce crediti: li paghi "
                "direttamente a Comfy.",
                stato=stato,
            )
        if stato == 401:  # numero-non-configurabile: codice HTTP
            return ErroreProvider(
                f"{self.destinazione} non ha accettato la chiave.{coda}",
                f"Controlla la chiave nella variabile d'ambiente {VARIABILI_CHIAVE[0]} "
                "(comincia con comfyui-), o creane una nuova nel tuo workspace "
                "Comfy. La chiave e' tua e non sta dentro il plugin.",
                stato=stato,
            )
        if stato == 403:  # numero-non-configurabile: codice HTTP
            return ErroreProvider(
                f"La chiave e' valida, ma il suo workspace non puo' usare il "
                f"modello {modello}.{coda}",
                "Controlla nel workspace Comfy che il modello sia abilitato, "
                "oppure scegli un preset con un altro modello.",
                stato=stato,
            )
        if stato == 404:  # numero-non-configurabile: codice HTTP
            return ErroreProvider(
                f"{self.destinazione} non conosce il modello {modello}.{coda}",
                "Il modello sta scritto nel preset: confrontalo con il catalogo "
                "del Router (python scripts/sonda_comfy.py --catalogo).",
                stato=stato,
            )
        return errore_da_stato_http(self.destinazione_per(modello), stato, dettaglio)

    def _byte_immagine(self, tipo: str, valore: str) -> bytes:
        if tipo == "url":
            # Il link e' firmato e sta su un altro dominio: si scarica senza chiave.
            dati = self.trasporto.scarica(valore)
        else:
            if tipo == "data-uri":
                valore = valore.split(",", 1)[-1]
            try:
                dati = base64.b64decode(valore, validate=True)
            except ValueError:
                dati = b""
        if tipo_mime(dati) == "application/octet-stream":
            raise ErroreProvider(
                f"{self.destinazione} ha mandato un'immagine che non so decodificare.",
                "Riprova. Se si ripete, e' cambiato lo schema del modello e va "
                "rifatta la sonda.",
            )
        return dati

    def _assicura_chiave(self) -> None:
        if not self.chiave:
            raise ChiaveMancante(
                "Manca la chiave API di Comfy: senza, non parte niente.",
                "Crea una chiave nel tuo workspace Comfy e mettila nella variabile "
                f"d'ambiente {VARIABILI_CHIAVE[0]}. La chiave e' tua, resta sulla "
                "tua macchina e non entra mai nel plugin.",
            )

    def _assicura_peso(self, dati: bytes) -> None:
        peso = modulo_immagine.dimensione_mb(dati)
        if peso > config.COMFY_INVIO_MASSIMO_MB:
            raise ErroreProvider(
                f"La vista di partenza pesa {peso:.1f} MB e ne mandiamo al massimo "
                f"{config.COMFY_INVIO_MASSIMO_MB} a {self.destinazione}.",
                "Salva di nuovo la vista da Allplan a una risoluzione piu' bassa.",
            )


def _senza_immagine(corpo: object, dati: bytes, nome: str = "vista") -> object:
    """Il corpo da salvare nella ricetta: tutto, tranne l'immagine, che diventa la sua impronta."""
    codificata = base64.b64encode(dati).decode("ascii")
    segnaposto = f"<{nome} sha256:{impronta(dati)}>"
    if isinstance(corpo, dict):
        return {k: _senza_immagine(v, dati, nome) for k, v in corpo.items()}
    if isinstance(corpo, list):
        return [_senza_immagine(v, dati, nome) for v in corpo]
    if isinstance(corpo, str) and corpo.endswith(codificata):
        return segnaposto
    return corpo


def _senza_immagini(corpo: object, immagini: tuple[bytes, ...]) -> object:
    """Come _senza_immagine, per la vista e ogni immagine in piu'."""
    for indice, dati in enumerate(immagini):
        corpo = _senza_immagine(corpo, dati, "vista" if indice == 0 else f"immagine {indice + 1}")
    return corpo


def _tipo_errore(corpo: object, risposte: dict) -> str:
    """Il tipo d'errore del Router: dall'intestazione, o dal corpo."""
    if risposte.get("x-comfy-error-type"):
        return str(risposte["x-comfy-error-type"])
    if not isinstance(corpo, dict):
        return ""
    errore = corpo.get("error") or corpo.get("error_type") or ""
    if isinstance(errore, dict):
        return str(errore.get("type") or errore.get("code") or "")
    return str(errore)


def _testo(risposta: object) -> str:
    if isinstance(risposta, str):
        return risposta
    if isinstance(risposta, dict):
        errore = risposta.get("error")
        if isinstance(errore, dict) and errore.get("message"):
            return str(errore["message"])
        for chiave in ("message", "error", "detail", "title"):
            if chiave in risposta and not isinstance(risposta[chiave], dict):
                return str(risposta[chiave])
    return ""
