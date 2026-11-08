"""Il ponte fra lo Studio e il browser: la web app di AIRENDER.

Nella web app il motore Python gira nel browser (Pyodide, in un Web Worker:
web/pagine/motore.js). Non c'e' una porta su 127.0.0.1: la pagina dello
Studio chiede /studio/api/... e /studio/file/..., il service worker
(web/pagine/sw.js) gira la richiesta al worker, e il worker la passa qui.

Il ponte non riscrive lo Studio: usa lo stesso gestore HTTP del server
locale (core/studio/server.py) su una richiesta finta, cosi' rotte, errori e
risposte restano quelli dello Studio sul PC. Cambia solo cio' che nel
browser non c'e':

- la rete: urllib non esce dal browser, quindi `installa_rete` mette al suo
  posto una funzione che passa da fetch();
- l'attesa: time.sleep bloccherebbe il worker, `installa_attesa` la cede;
- la cartella: e' nel file system del browser, salvata in IndexedDB;
- «Apri cartella»: non c'e' un esplora file, lo si dice;
- «Esporta per il cliente»: il file esportato si scarica (`da_scaricare`).

Questo file sta fuori da core/ perche' e' un adattatore, come allplan/:
il motore non sa che il browser esiste (CLAUDE.md, regola 1).
"""

from __future__ import annotations

import io
import json
import os
import time
import urllib.error
import urllib.request
from email.message import Message
from http import HTTPStatus
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

# Prima di importare il motore: il canale e l'impronta valgono dalla prima
# richiesta al server (core/licenza.py).
CANALE = "web"
PREFISSO = "/studio"


class _ServerFinto:
    """Quello che il gestore chiede al server: solo l'indirizzo per il controllo dell'Host."""

    server_address = ("127.0.0.1", 0)


def _messaggio(intestazioni: dict) -> Message:
    m = Message()
    for nome, valore in intestazioni.items():
        m[nome] = str(valore)
    return m


class _Risposta(io.BytesIO):
    """Quello che il motore legge da urlopen: status, headers, read()."""

    def __init__(self, url: str, stato: int, intestazioni: dict, corpo: bytes) -> None:
        super().__init__(corpo)
        self.url = url
        self.status = stato
        self.code = stato
        self.headers = _messaggio(intestazioni)

    def getcode(self) -> int:
        return self.status


# chiama(url, metodo, intestazioni, corpo) -> (stato, intestazioni, corpo).
# Nel browser la fa motore.js con fetch(); nei test una funzione finta.
Chiamata = Callable[[str, str, dict, "bytes | None"], "tuple[int, dict, bytes]"]


def installa_rete(chiama: Chiamata) -> None:
    """urllib.request.urlopen passa da `chiama`. Errori HTTP e di rete come urllib."""

    def urlopen(richiesta, data=None, timeout=None, **_altro):  # pylint: disable=unused-argument
        if isinstance(richiesta, str):
            richiesta = urllib.request.Request(richiesta, data=data)
        url = richiesta.full_url
        metodo = richiesta.get_method()
        intestazioni = dict(richiesta.header_items())
        try:
            stato, risposte, corpo = chiama(url, metodo, intestazioni, richiesta.data)
        except Exception as errore:  # pylint: disable=broad-exception-caught
            raise urllib.error.URLError(str(errore) or "il browser non ha raggiunto il servizio") from None
        if stato >= 400:
            raise urllib.error.HTTPError(url, stato, "", _messaggio(risposte), io.BytesIO(corpo))
        return _Risposta(url, stato, risposte, corpo)

    urllib.request.urlopen = urlopen


def installa_attesa(dormi: Callable[[float], None]) -> None:
    """time.sleep cede il worker invece di bloccarlo (nel browser: un timer)."""
    time.sleep = dormi


def _non_sul_web(_percorso: Path) -> None:
    from core.studio.servizio import RichiestaStudioNonValida  # pylint: disable=import-outside-toplevel

    raise RichiestaStudioNonValida(
        "Nella web app le immagini stanno nel browser, non in una cartella del PC.",
        "Per tenere un render usa Esporta per il cliente: nella web app il file si scarica.",
    )


class Ponte:
    """Uno Studio su una cartella del browser, e la sua coda dei lavori."""

    def __init__(self, cartella: Path, postazione: str = "") -> None:
        os.environ["AIRENDER_CANALE"] = CANALE
        if postazione:
            os.environ["AIRENDER_POSTAZIONE"] = postazione
        # pylint: disable=import-outside-toplevel
        from core import coda as modulo_coda
        from core.provider import ProviderAirender
        from core.studio.server import _Gestore
        from core.studio.servizio import Studio

        self.cartella = Path(cartella)
        # Nel browser non c'e' una chiave Comfy propria: solo i crediti AIRENDER.
        self.studio = Studio(self.cartella, provider=ProviderAirender.nome,
                             coda_attiva=lambda: True, apri=_non_sul_web)
        self._gestore = type("GestoreWeb", (_Gestore,), {"studio": self.studio})
        # Il file appena esportato: motore.js lo passa alla pagina, che lo scarica.
        self.da_scaricare: Path | None = None
        esporta = self.studio.esporta

        def esporta_e_scarica(identificativo: str, dati: dict) -> dict:
            esito = esporta(identificativo, dati)
            self.da_scaricare = Path(esito["file"])
            return esito

        self.studio.esporta = esporta_e_scarica
        self.coda = modulo_coda.Coda(self.cartella)
        self._video = None
        self._recuperati = False

    # --- le richieste della pagina -----------------------------------------

    def rispondi(self, metodo: str, percorso: str, intestazioni: dict, corpo: bytes = b"") -> tuple[int, dict, bytes]:
        """Una richiesta della pagina, come l'avrebbe servita lo Studio sul PC."""
        indirizzo = urlsplit(percorso)
        strada = indirizzo.path
        if strada.startswith(PREFISSO + "/"):
            strada = strada[len(PREFISSO):]
        if indirizzo.query:
            strada += "?" + indirizzo.query
        gestore = object.__new__(self._gestore)
        gestore.server = _ServerFinto()
        gestore.command = metodo
        gestore.path = strada
        gestore.request_version = "HTTP/1.1"
        gestore.requestline = f"{metodo} {strada} HTTP/1.1"
        gestore.client_address = ("127.0.0.1", 0)
        corpo = corpo or b""
        gestore.headers = _messaggio({
            **{k: v for k, v in intestazioni.items() if k.lower() not in ("host", "content-length")},
            "Host": "127.0.0.1:0",
            "Content-Length": str(len(corpo)),
        })
        gestore.rfile = io.BytesIO(corpo)
        gestore.wfile = io.BytesIO()
        raccolta: dict = {"stato": HTTPStatus.INTERNAL_SERVER_ERROR, "intestazioni": {}}

        def send_response(stato, _messaggio_stato=None):
            raccolta["stato"] = int(stato)

        def send_header(nome, valore):
            raccolta["intestazioni"][nome] = valore

        gestore.send_response = send_response
        gestore.send_header = send_header
        gestore.end_headers = lambda: None
        if metodo == "GET":
            gestore.do_GET()
        elif metodo == "POST":
            gestore.do_POST()
        else:
            return HTTPStatus.METHOD_NOT_ALLOWED, {"Content-Type": "text/plain"}, b""
        return raccolta["stato"], raccolta["intestazioni"], gestore.wfile.getvalue()

    def prendi_da_scaricare(self) -> tuple[str, bytes] | None:
        """Nome e byte del file esportato dall'ultima richiesta, una volta sola."""
        file, self.da_scaricare = self.da_scaricare, None
        return (file.name, file.read_bytes()) if file is not None and file.is_file() else None

    def rispondi_json(self, metodo: str, percorso: str, intestazioni_json: str, corpo: bytes = b"") -> str:
        """Come `rispondi`, con le intestazioni in JSON: comodo da JavaScript."""
        stato, intestazioni, dati = self.rispondi(metodo, percorso, json.loads(intestazioni_json or "{}"), corpo)
        self.ultimo_corpo = dati
        return json.dumps({"stato": stato, "intestazioni": intestazioni})

    # --- la coda -------------------------------------------------------------

    def giro_coda(self) -> str | None:
        """Un lavoro della coda (immagine o video), se c'e'. Lo chiama motore.js a intervalli.

        Lo stesso lavoro della coda sul PC (core.coda.Coda.gira), un passo
        alla volta: il worker resta libero fra un giro e l'altro.
        """
        # pylint: disable=import-outside-toplevel
        from core import video as modulo_video
        from core import provider as registro

        if not self._recuperati:
            self.coda.recupera_abbandonati()
            self._video = modulo_video.CodaVideo(self.cartella, registro.crea, self.coda._dire)  # pylint: disable=protected-access
            self._video.recupera_abbandonati()
            self._recuperati = True
        fatto = self.coda.esegui_uno()
        if fatto is None:
            fatto = self._video.esegui_uno()
        return fatto
