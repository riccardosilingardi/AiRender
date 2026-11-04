"""«Tieni la geometria»: la prima passata con un ControlNet, prima di Nano Banana.

Un ControlNet e' un pezzo aggiunto a un modello aperto che lo obbliga a
seguire una guida, qui gli spigoli della vista (Canny). Nano Banana non ne ha:
segue la vista bene ma non sempre, soprattutto nei passi. Con «Tieni la
geometria» la vista va prima a un workflow su Comfy Cloud (Z-Image-Turbo con
il ControlNet Fun Union, `workflow/tieni-geometria.json`), e il suo render
parte poi verso Nano Banana come prima immagine, con la regola di non
spostare nessuno spigolo.

Non e' il Router: e' l'API v2 dei workflow di Comfy (carica l'immagine come
asset, manda il grafo, aspetta il lavoro, scarica l'uscita). La chiave e'
la stessa del Router (COMFY_API_KEY). L'indirizzo e' Comfy Cloud, che vuole
un abbonamento Cloud; con `AIRENDER_COMFY_WORKFLOW_URL` si puo' puntare a un
deployment della Developer Platform (https://<nome>.run.comfy.app).
NON VERIFICATO al 2026-11-04: nessun workflow e' mai partito da qui.
"""

from __future__ import annotations

import copy
import json
import os
import time
import uuid
from pathlib import Path
from typing import Callable, Protocol
from urllib.parse import urlparse

from .. import config
from ..errori import ErroreProvider
from . import comfy

VARIABILE_URL = "AIRENDER_COMFY_WORKFLOW_URL"
URL_PREDEFINITO = "https://cloud.comfy.org"
WORKFLOW = Path(__file__).resolve().parent / "workflow" / "tieni-geometria.json"
NOME_WORKFLOW = "Z-Image-Turbo + ControlNet sugli spigoli"
REGOLA_PROMPT = (
    "Image 1 is a draft render made with an edge ControlNet from the architectural view: its "
    "edges, openings, proportions and camera match the building exactly. Keep every edge, "
    "line and opening where it is; improve only materials, light, shadows and realism."
)
# I nodi del workflow che il motore riempie (vedi il file JSON).
NODO_IMMAGINE, NODO_LATO, NODO_PROMPT, NODO_FORZA, NODO_CAMPIONATORE = "1", "2", "6", "8", "9"
STATI_FINITI = ("succeeded", "failed", "expired", "canceled")


class TrasportoWorkflow(Protocol):
    """Il minimo che serve all'API v2: JSON, un caricamento multipart e un download con la chiave."""

    def chiama(self, metodo: str, url: str, intestazioni: dict,
               corpo: dict | None = None) -> tuple[int, dict, object]: ...

    def manda_byte(self, url: str, intestazioni: dict, dati: bytes) -> tuple[int, dict, object]: ...

    def scarica_con(self, url: str, intestazioni: dict) -> bytes: ...


def indirizzo() -> str:
    """La base dell'API: Comfy Cloud, o il deployment scritto nell'ambiente."""
    scritto = os.environ.get(VARIABILE_URL, "").strip().rstrip("/")
    if not scritto:
        return URL_PREDEFINITO
    parti = urlparse(scritto)
    if parti.scheme != "https" or not parti.hostname:
        raise ErroreProvider(
            f"{VARIABILE_URL} vale {scritto!r}, che non e' un indirizzo https.",
            "Scrivi l'indirizzo del deployment come https://<nome>.run.comfy.app, "
            "o togli la variabile per usare Comfy Cloud.",
        )
    return f"https://{parti.hostname}"


def destinazione() -> str:
    """Il servizio che riceve la vista nella prima passata: si mostra prima dell'invio (regola 5)."""
    return f"Comfy, workflow {NOME_WORKFLOW} su {urlparse(indirizzo()).hostname}"


def workflow(asset: str, prompt: str, seme: int) -> dict:
    """Il grafo in formato API, coi valori del lavoro. La nota del file non parte."""
    grafo = {k: v for k, v in json.loads(WORKFLOW.read_text(encoding="utf-8")).items()
             if not k.startswith("_")}
    grafo = copy.deepcopy(grafo)
    grafo[NODO_IMMAGINE]["inputs"]["image"] = {"__type": "core/ASSET", "info": {"id": asset}}
    grafo[NODO_LATO]["inputs"]["largest_size"] = config.GEOMETRIA_LATO_MASSIMO
    grafo[NODO_PROMPT]["inputs"]["text"] = prompt
    grafo[NODO_FORZA]["inputs"]["strength"] = config.GEOMETRIA_FORZA
    grafo[NODO_CAMPIONATORE]["inputs"]["seed"] = seme
    grafo[NODO_CAMPIONATORE]["inputs"]["steps"] = config.GEOMETRIA_PASSI
    return grafo


def _multipart(dati: bytes, nome: str, tipo: str) -> tuple[bytes, str]:
    confine = uuid.uuid4().hex
    righe = []
    for campo, valore in (("file_path", nome), ("content_type", tipo)):
        righe.append(f"--{confine}\r\nContent-Disposition: form-data; name=\"{campo}\"\r\n\r\n{valore}\r\n".encode())
    # Il file per ultimo: l'API lo chiede dopo gli altri campi.
    righe.append(f"--{confine}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{nome}\"\r\n"
                 f"Content-Type: {tipo}\r\n\r\n".encode() + dati + b"\r\n")
    righe.append(f"--{confine}--\r\n".encode())
    return b"".join(righe), f"multipart/form-data; boundary={confine}"


class Geometria:
    """Un client dell'API v2 dei workflow, solo per la prima passata."""

    def __init__(self, trasporto: TrasportoWorkflow, chiave: str | None = None, base: str | None = None,
                 dormi: Callable[[float], None] = time.sleep, adesso: Callable[[], float] = time.monotonic,
                 controlla: Callable[[], None] = lambda: None) -> None:
        self.trasporto = trasporto
        self.chiave = chiave if chiave is not None else comfy.chiave_da_ambiente()
        self.base = base or indirizzo()
        self.dormi, self.adesso, self.controlla = dormi, adesso, controlla

    def destinazione(self) -> str:
        return f"Comfy, workflow {NOME_WORKFLOW} su {urlparse(self.base).hostname}"

    def _intestazioni(self) -> dict:
        if not self.chiave:
            raise ErroreProvider(
                "Manca la chiave di Comfy per «Tieni la geometria».",
                f"Imposta la variabile d'ambiente {comfy.VARIABILI_CHIAVE[0]} con la tua chiave "
                "(la stessa del Router) e riapri lo Studio. Non ho inviato niente.",
            )
        return {"Authorization": f"Bearer {self.chiave}"}

    def _errore(self, cosa: str, stato: int, corpo: object) -> ErroreProvider:
        dettaglio = corpo.get("message") or corpo.get("error") if isinstance(corpo, dict) else corpo
        aggiunta = ""
        if stato in (401, 402, 403):  # numero-non-configurabile: codici HTTP di chiave e abbonamento
            aggiunta = (" Comfy Cloud vuole un abbonamento Cloud per i workflow; con i soli crediti del "
                        "Router serve un deployment della Developer Platform "
                        f"({VARIABILE_URL}).")
        return ErroreProvider(
            f"«Tieni la geometria»: {cosa} non e' riuscito (HTTP {stato}): {str(dettaglio)[:300]}.",  # numero-non-configurabile: taglio del messaggio d'errore a schermo
            "Togli la spunta «Tieni la geometria» per mandare solo a Nano Banana, o controlla "
            f"la chiave e l'abbonamento.{aggiunta}",
        )

    def carica(self, immagine: bytes) -> str:
        tipo = comfy.tipo_mime(immagine)
        corpo, contenuto = _multipart(immagine, "vista." + tipo.rsplit("/", 1)[-1], tipo)
        stato, _int, risposta = self.trasporto.manda_byte(
            f"{self.base}/api/v2/assets", {**self._intestazioni(), "Content-Type": contenuto}, corpo)
        if stato not in (200, 201) or not isinstance(risposta, dict) or not risposta.get("id"):  # numero-non-configurabile: HTTP OK e Created
            raise self._errore("il caricamento della vista", stato, risposta)
        return str(risposta["id"])

    def esegui(self, immagine: bytes, prompt: str, seme: int) -> tuple[bytes, str]:
        """Carica la vista, manda il workflow, aspetta e scarica. Torna l'immagine e l'id del lavoro Comfy."""
        asset = self.carica(immagine)
        self.controlla()
        stato, _int, lavoro = self.trasporto.chiama(
            "POST", f"{self.base}/api/v2/jobs",
            {**self._intestazioni(), "Idempotency-Key": str(uuid.uuid4())},
            {"workflow": workflow(asset, prompt, seme)})
        if stato not in (200, 201) or not isinstance(lavoro, dict) or not lavoro.get("id"):  # numero-non-configurabile: HTTP OK e Created
            raise self._errore("l'invio del workflow", stato, lavoro)
        identificativo = str(lavoro["id"])
        collegamenti = lavoro.get("urls") if isinstance(lavoro.get("urls"), dict) else {}
        # L'API dice di seguire i suoi link, non di costruirli: un deployment ha un prefisso suo.
        se_stesso = self._risolvi(collegamenti.get("self") or f"/api/v2/jobs/{identificativo}")
        annulla = self._risolvi(collegamenti.get("cancel") or f"/api/v2/jobs/{identificativo}/cancel")
        scadenza = self.adesso() + config.GEOMETRIA_ATTESA_SECONDI
        while lavoro.get("status") not in STATI_FINITI:
            if self.adesso() > scadenza:
                self.trasporto.chiama("POST", annulla, self._intestazioni(), {})
                raise ErroreProvider(
                    f"«Tieni la geometria»: il workflow non ha finito in {config.GEOMETRIA_ATTESA_SECONDI} "
                    "secondi e l'ho fermato.",
                    "Riprova: la prima volta Comfy carica i modelli. Se succede ancora, togli la spunta.",
                )
            self.dormi(config.GEOMETRIA_INTERVALLO_SECONDI)
            self.controlla()
            stato, _int, lavoro = self.trasporto.chiama(
                "GET", se_stesso, self._intestazioni())
            if stato != 200 or not isinstance(lavoro, dict):  # numero-non-configurabile: HTTP OK
                raise self._errore("la lettura del lavoro", stato, lavoro)
        if lavoro.get("status") != "succeeded":
            raise self._errore(f"il workflow ({lavoro.get('status')})", stato, lavoro.get("error") or lavoro)
        indirizzi = [u.get("url") for u in lavoro.get("outputs") or [] if isinstance(u, dict) and u.get("url")]
        if not indirizzi:
            raise self._errore("il workflow (nessuna immagine in uscita)", stato, lavoro)
        return self.trasporto.scarica_con(self._risolvi(indirizzi[0]), self._intestazioni()), identificativo

    def _risolvi(self, collegamento: str) -> str:
        """Un link dell'API: assoluto si usa com'e', con la / iniziale si attacca all'origine."""
        if collegamento.startswith("/"):
            parti = urlparse(self.base)
            return f"{parti.scheme}://{parti.netloc}{collegamento}"
        if urlparse(collegamento).hostname != urlparse(self.base).hostname:
            raise ErroreProvider(
                f"«Tieni la geometria»: Comfy ha indicato un link su un altro indirizzo ({collegamento[:120]}).",  # numero-non-configurabile: taglio del link nel messaggio
                "Non mando la chiave fuori dal servizio annunciato. Togli la spunta e segnala il caso.",
            )
        return collegamento
