"""«Tieni la geometria»: la prima passata con un ControlNet, prima di Nano Banana.

Un ControlNet e' un pezzo aggiunto a un modello aperto che lo obbliga a
seguire una guida, qui gli spigoli della vista (Canny). La vista va prima al
workflow `workflow/tieni-geometria.json` (Z-Image-Turbo con il ControlNet Fun
Union), pubblicato da Riccardo sulla Comfy Developer Platform come endpoint
serverless `https://<nome>.run.comfy.app` (`workflow/LEGGIMI.md`). Il suo
render parte poi verso Nano Banana come prima immagine, con la regola di non
spostare nessuno spigolo.

Non e' il Router: e' l'API v2 dei workflow (carica la vista come asset, manda
il grafo, aspetta il lavoro, scarica l'uscita). Due strade:

- chiave Comfy propria: la stessa del Router (COMFY_API_KEY), l'indirizzo del
  deployment in AIRENDER_COMFY_WORKFLOW_URL;
- crediti AIRENDER (provider "airender", plugin e web app): la stessa API v2
  sul server AIRENDER sotto /geometria (server/netlify/functions/
  geometria.mjs), col codice licenza. Il server ricostruisce il grafo dal suo
  modello, lo manda al deployment di Riccardo con la sua chiave e scala
  LISTINO["pesi_azioni"]["tieni_geometria"] solo se il workflow riesce.
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

from .. import config, immagine as modulo_immagine, licenza as modulo_licenza
from ..errori import ChiaveMancante, ErroreProvider
from . import comfy

VARIABILE_URL = "AIRENDER_COMFY_WORKFLOW_URL"
PROVIDER_AIRENDER = "airender"
PERCORSO_SERVER = "/geometria"  # dove il server AIRENDER espone l'API v2 dei workflow
WORKFLOW = Path(__file__).resolve().parent / "workflow" / "tieni-geometria.json"
NOME_WORKFLOW = "Z-Image-Turbo + ControlNet"
REGOLA_PROMPT = (
    "Image 1 is a draft render made with a ControlNet from the architectural view: its "
    "edges, openings, proportions and camera match the building exactly. Keep every edge, "
    "line and opening where it is; improve only materials, light, shadows and realism."
)
# I nodi del workflow che il motore riempie (vedi il file JSON).
NODO_IMMAGINE, NODO_LATO, NODO_PROMPT, NODO_FORZA, NODO_CAMPIONATORE = "1", "2", "6", "8", "9"
NODO_MODELLO, NODO_CAMPIONAMENTO = "4", "11"
# «Riaggancia alla vista»: il render rientra nel latente al posto del foglio
# vuoto, e il ControlNet lo riporta sulle linee della vista.
NODO_RENDER, NODI_RIAGGANCIA, NODO_LATENTE_VUOTO = "21", ("21", "22", "23"), "14"
NODO_LATENTE_RENDER = "23"
PROMPT_RIAGGANCIA = (
    "architectural photograph of the building, same materials, same light and same colours "
    "as the input image, every edge and opening exactly on the lines of the view"
)

# I tre controlli che l'utente puo' spuntare, nell'ordine in cui si
# incatenano sul modello. Ognuno e' un preprocessore che estrae una guida
# dalla vista e un nodo ControlNet (lo stesso ControlNet Union) che la
# applica. Gli altri nodi del file restano fuori dal grafo.
CONTROLLI = ("spigoli", "profondita", "linee")
CONTROLLI_PREDEFINITI = ("spigoli",)
NODI_CONTROLLO = {  # controllo: (preprocessore, ControlNet)
    "spigoli": ("3", "8"),
    "profondita": ("17", "18"),
    "linee": ("19", "20"),
}
NOMI_CONTROLLI = {"spigoli": "Spigoli", "profondita": "Profondità", "linee": "Linee dritte"}


def forza(controllo: str) -> float:
    return {"spigoli": config.GEOMETRIA_FORZA, "profondita": config.GEOMETRIA_FORZA_PROFONDITA,
            "linee": config.GEOMETRIA_FORZA_LINEE}[controllo]


def controlli_validi(valore: object) -> tuple[str, ...]:
    """I controlli scelti, in ordine e senza doppioni. Vuoto o sconosciuto: si rifiuta."""
    if valore is None:
        return CONTROLLI_PREDEFINITI
    if not isinstance(valore, (list, tuple)) or not valore or any(v not in CONTROLLI for v in valore):
        raise ErroreProvider(
            f"«Tieni la geometria» accetta come controlli {', '.join(CONTROLLI)}: e' arrivato {valore!r}.",
            "Spunta almeno uno fra Spigoli, Profondità e Linee dritte, oppure togli «Tieni la geometria».",
        )
    return tuple(c for c in CONTROLLI if c in valore)


def descrivi_controlli(controlli: tuple[str, ...]) -> str:
    nomi = [NOMI_CONTROLLI[c] for c in controlli]
    return nomi[0] if len(nomi) == 1 else ", ".join(nomi[:-1]) + " e " + nomi[-1]


def grafo_per(controlli: tuple[str, ...], riaggancia: bool = False) -> dict:
    """Il grafo coi soli controlli scelti, incatenati sul modello, e i valori di config.py.

    Restano da riempire solo vista, prompt e seme (workflow()), e il render
    con `riaggancia`. Lo usa anche scripts/scrivi_listino.py per il server,
    che non riceve il grafo dal client.

    Con `riaggancia` il campionatore non parte da un foglio vuoto ma dal
    render, e ne rifa' solo GEOMETRIA_RIAGGANCIA_DENOISE: i controlli restano
    presi dalla vista, cosi' le linee tornano al loro posto.
    """
    controlli = controlli_validi(controlli)
    grafo = copy.deepcopy(json.loads(WORKFLOW.read_text(encoding="utf-8")))
    precedente = [NODO_MODELLO, 0]
    for controllo in CONTROLLI:
        preprocessore, controlnet = NODI_CONTROLLO[controllo]
        if controllo not in controlli:
            del grafo[preprocessore], grafo[controlnet]
            continue
        grafo[controlnet]["inputs"]["model"] = precedente
        grafo[controlnet]["inputs"]["strength"] = forza(controllo)
        precedente = [controlnet, 0]
    grafo[NODO_CAMPIONAMENTO]["inputs"]["model"] = precedente
    grafo[NODO_LATO]["inputs"]["largest_size"] = config.GEOMETRIA_LATO_MASSIMO
    grafo[NODO_CAMPIONATORE]["inputs"]["steps"] = config.GEOMETRIA_PASSI
    if riaggancia:
        del grafo[NODO_LATENTE_VUOTO]
        grafo[NODO_CAMPIONATORE]["inputs"]["latent_image"] = [NODO_LATENTE_RENDER, 0]
        grafo[NODO_CAMPIONATORE]["inputs"]["denoise"] = config.GEOMETRIA_RIAGGANCIA_DENOISE
    else:
        for nodo in NODI_RIAGGANCIA:
            del grafo[nodo]
    return grafo


STATI_FINITI = ("succeeded", "failed", "expired", "canceled")


class TrasportoWorkflow(Protocol):
    """Il minimo che serve all'API v2: JSON, un caricamento multipart e un download con la chiave."""

    def chiama(self, metodo: str, url: str, intestazioni: dict,
               corpo: dict | None = None) -> tuple[int, dict, object]: ...

    def manda_byte(self, url: str, intestazioni: dict, dati: bytes) -> tuple[int, dict, object]: ...

    def scarica_con(self, url: str, intestazioni: dict) -> bytes: ...


def indirizzo() -> str:
    """La base dell'API: il deployment della Developer Platform scritto nell'ambiente."""
    scritto = os.environ.get(VARIABILE_URL, "").strip().rstrip("/")
    if not scritto:
        raise ErroreProvider(
            "Manca l'indirizzo del workflow «Tieni la geometria».",
            f"Pubblica core/provider/workflow/tieni-geometria.json sulla Developer Platform, poi "
            f"scrivi l'indirizzo con: setx {VARIABILE_URL} https://<nome>.run.comfy.app e riapri lo Studio.",
        )
    parti = urlparse(scritto)
    if parti.scheme != "https" or not parti.hostname:
        raise ErroreProvider(
            f"{VARIABILE_URL} vale {scritto!r}, che non e' un indirizzo https.",
            "Scrivi l'indirizzo del deployment come https://<nome>.run.comfy.app.",
        )
    return f"https://{parti.hostname}"


def destinazione(provider: str = "") -> str:
    """Il servizio che riceve la vista nella prima passata: si mostra prima dell'invio (regola 5)."""
    if provider == PROVIDER_AIRENDER:
        return destinazione_airender()
    return f"Comfy Developer Platform, workflow {NOME_WORKFLOW} su {urlparse(indirizzo()).hostname}"


def destinazione_airender() -> str:
    return (f"server AIRENDER ({urlparse(modulo_licenza.server()).hostname}) → "
            f"Comfy Developer Platform, workflow {NOME_WORKFLOW}")


def peso_airender() -> int:
    """Quanti render AIRENDER costa una prima passata, dal listino."""
    return int(config.LISTINO["pesi_azioni"]["tieni_geometria"])


def crea(provider: str, trasporto: "TrasportoWorkflow", controlla: Callable[[], None] = lambda: None) -> "Geometria":
    """Il client giusto per il servizio del lavoro: crediti AIRENDER o chiave Comfy propria."""
    if provider == PROVIDER_AIRENDER:
        return GeometriaAirender(trasporto, controlla=controlla)
    return Geometria(trasporto, controlla=controlla)


def workflow(asset: str, prompt: str, seme: int, controlli: tuple[str, ...] = CONTROLLI_PREDEFINITI,
             render: str | None = None) -> dict:
    """Il grafo in formato API, coi controlli scelti e i valori del lavoro.

    Con `render` (l'asset del render da riagganciare) e' «Riaggancia alla vista».
    """
    grafo = grafo_per(controlli, riaggancia=render is not None)
    grafo[NODO_IMMAGINE]["inputs"]["image"] = {"__type": "core/ASSET", "info": {"id": asset}}
    if render is not None:
        grafo[NODO_RENDER]["inputs"]["image"] = {"__type": "core/ASSET", "info": {"id": render}}
    grafo[NODO_PROMPT]["inputs"]["text"] = prompt
    grafo[NODO_CAMPIONATORE]["inputs"]["seed"] = seme
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
        return f"Comfy Developer Platform, workflow {NOME_WORKFLOW} su {urlparse(self.base).hostname}"

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
        if stato in (401, 403):  # numero-non-configurabile: codici HTTP di una chiave rifiutata
            aggiunta = f" Il deployment ha rifiutato la chiave: controlla {comfy.VARIABILI_CHIAVE[0]}."
        return ErroreProvider(
            f"«Tieni la geometria»: {cosa} non e' riuscito (HTTP {stato}): {str(dettaglio)[:300]}.",  # numero-non-configurabile: taglio del messaggio d'errore a schermo
            f"Togli la spunta «Tieni la geometria» per mandare solo a Nano Banana.{aggiunta}",
        )

    def carica(self, immagine: bytes, nome: str = "vista") -> str:
        immagine = modulo_immagine.senza_metadati(immagine)  # partono solo i pixel, senza EXIF ne' XMP
        tipo = comfy.tipo_mime(immagine)
        corpo, contenuto = _multipart(immagine, nome + "." + tipo.rsplit("/", 1)[-1], tipo)
        stato, _int, risposta = self.trasporto.manda_byte(
            f"{self.base}/api/v2/assets", {**self._intestazioni(), "Content-Type": contenuto}, corpo)
        if stato not in (200, 201) or not isinstance(risposta, dict) or not risposta.get("id"):  # numero-non-configurabile: HTTP OK e Created
            raise self._errore(f"il caricamento del{'la vista' if nome == 'vista' else ' render'}", stato, risposta)
        return str(risposta["id"])

    def esegui(self, immagine: bytes, prompt: str, seme: int,
               controlli: tuple[str, ...] = CONTROLLI_PREDEFINITI,
               render: bytes | None = None) -> tuple[bytes, str]:
        """Carica la vista, manda il workflow, aspetta e scarica. Torna l'immagine e l'id del lavoro Comfy.

        Con `render` e' «Riaggancia alla vista»: carica anche il render, che il
        workflow riporta sulle linee della vista.
        """
        asset = self.carica(immagine)
        asset_render = self.carica(render, "render") if render is not None else None
        self.controlla()
        stato, _int, lavoro = self.trasporto.chiama(
            "POST", f"{self.base}/api/v2/jobs",
            {**self._intestazioni(), "Idempotency-Key": str(uuid.uuid4())},
            {"workflow": workflow(asset, prompt, seme, controlli, asset_render)})
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
                    "Riprova: a freddo il deployment carica i modelli prima di partire. Se succede ancora, togli la spunta.",
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


class GeometriaAirender(Geometria):
    """La stessa API v2, sul server AIRENDER, col codice licenza al posto della chiave Comfy.

    Il server sceglie il deployment e ricostruisce il grafo: dal client prende
    solo l'asset caricato, il prompt e il seme.
    """

    def __init__(self, trasporto: TrasportoWorkflow, codice: str | None = None, canale: str = "plugin",
                 **altro) -> None:
        super().__init__(trasporto, chiave=codice if codice is not None else (modulo_licenza.leggi() or ""),
                         base=modulo_licenza.server() + PERCORSO_SERVER, **altro)
        self.canale = canale

    def destinazione(self) -> str:
        return destinazione_airender()

    def _intestazioni(self) -> dict:
        if not self.chiave:
            raise ChiaveMancante(
                "Non hai ancora incollato il codice licenza AIRENDER: «Tieni la geometria» non parte.",
                "Incolla il codice ricevuto per email con: python -m core.cli --licenza AIR-XXXX-XXXX-XXXX-XXXX.",
            )
        return modulo_licenza.intestazioni(self.chiave, self.canale)

    def _errore(self, cosa: str, stato: int, corpo: object) -> ErroreProvider:
        if isinstance(corpo, dict) and isinstance(corpo.get("error"), dict) and corpo.get("cosa_fare"):
            return modulo_licenza.errore_del_server(stato, corpo)
        return super()._errore(cosa, stato, corpo)
