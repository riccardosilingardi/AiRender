"""Il server locale dello Studio: http.server della libreria standard.

Solo su 127.0.0.1, porta scelta dal sistema. Due difese, perche' un server
locale lo puo' raggiungere anche una pagina web aperta nello stesso browser:

- l'intestazione Host deve essere 127.0.0.1 o localhost con la nostra porta
  (contro il DNS rebinding);
- ogni POST deve portare l'intestazione X-Airender: un sito estraneo non la
  puo' aggiungere senza un preflight CORS, che qui non riceve risposta.

Rotte:

    GET  /                                 la pagina
    GET  /pagine/<file>                    foglio di stile e script
    GET  /api/studio                       cartella, coda, viste, lavori attivi
    GET  /api/catalogo                     preset, assi, modelli
    GET  /api/viste/<nome>                 la vista e il suo esito di idoneita'
    GET  /api/viste/<nome>/render          i lavori nati da quella vista
    GET  /api/viste/<nome>/passi           l'albero dei passi della vista
    GET  /api/destinazione?modello=<id>&varianti=<n>   dove va la vista e quanto costa
    GET  /api/lavori/<id>                  stato di un lavoro
    GET  /api/lavori/<id>/ricetta          la ricetta del render
    GET  /file/vista/<nome>                l'immagine della vista
    GET  /file/render/<id>                 l'immagine del render
    GET  /file/miniatura/<preset>          la miniatura vera di un preset, se c'e'
    POST /api/componi                      prompt, riassunto, caratteri
    POST /api/prova-a-secco                tutto tranne l'invio
    POST /api/invia                        scrive il lavoro in coda
    POST /api/viste                        carica una vista (corpo: i byte)
    POST /api/lavori/<id>/annulla          file .annulla accanto al lavoro
    POST /api/lavori/<id>/misura           spigoli ritrovati di un render fatto prima della misura
    POST /api/lavori/<id>/rifai            stesso lavoro, di nuovo in coda («Rifai questo passo»)
    POST /api/passi/componi                il prompt di un passo nuovo, prima dell'invio
    POST /api/passi/invia                  un passo nuovo dal render di un passo
    POST /api/passi/pulito/componi         il prompt di «Rifai pulito dalla vista»
    POST /api/passi/pulito/invia           le richieste della strada in un invio dalla vista
    POST /api/ritocca/componi              il prompt di un ritocco (aree e note), prima di Applica
    POST /api/ritocca/invia                tutte le note in un invio sul render di un passo
    POST /api/apri-cartella                apre viste o render nel sistema
"""

from __future__ import annotations

import json
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from ..errori import ErroreAirender, FileNonTrovato
from .servizio import RichiestaStudioNonValida, Studio

INDIRIZZO = "127.0.0.1"
CARTELLA_PAGINE = Path(__file__).resolve().parent / "pagine"
INTESTAZIONE_STUDIO = "X-Airender"
_PAGINE = {"studio.css": "text/css", "studio.js": "text/javascript"}


class _Gestore(BaseHTTPRequestHandler):
    studio: Studio  # messo dalla fabbrica qui sotto
    server_version = "AirenderStudio"

    # --- risposte --------------------------------------------------------

    def _invia(self, stato: int, corpo: bytes, tipo: str) -> None:
        self.send_response(stato)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(corpo)

    def _json(self, dati: object, stato: int = HTTPStatus.OK) -> None:
        self._invia(stato, json.dumps(dati, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8")

    def _errore(self, errore: ErroreAirender) -> None:
        stato = HTTPStatus.NOT_FOUND if isinstance(errore, FileNonTrovato) else HTTPStatus.BAD_REQUEST
        self._json({"errore": {"fatto": errore.fatto, "cosa_fare": errore.cosa_fare}}, stato)

    def _file(self, percorso: Path) -> None:
        tipo = mimetypes.guess_type(percorso.name)[0] or "application/octet-stream"
        self._invia(HTTPStatus.OK, percorso.read_bytes(), tipo)

    def log_message(self, format, *args):  # pylint: disable=redefined-builtin
        pass  # la console dello Studio racconta i lavori, non ogni richiesta

    # --- difese ----------------------------------------------------------

    def _host_valido(self) -> bool:
        porta = self.server.server_address[1]
        return self.headers.get("Host", "") in (f"{INDIRIZZO}:{porta}", f"localhost:{porta}")

    def _corpo(self) -> bytes:
        lunghezza = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(lunghezza) if lunghezza > 0 else b""

    def _corpo_json(self) -> dict:
        try:
            dati = json.loads(self._corpo() or b"{}")
        except ValueError:
            raise RichiestaStudioNonValida(
                "La pagina ha mandato una richiesta che non si legge.",
                "Ricarica la pagina dello Studio.",
            ) from None
        if not isinstance(dati, dict):
            raise RichiestaStudioNonValida(
                "La pagina ha mandato una richiesta che non si legge.",
                "Ricarica la pagina dello Studio.",
            )
        return dati

    # --- GET -------------------------------------------------------------

    def do_GET(self) -> None:  # pylint: disable=invalid-name
        if not self._host_valido():
            self._invia(HTTPStatus.FORBIDDEN, b"", "text/plain")
            return
        indirizzo = urlsplit(self.path)
        parti = [unquote(p) for p in indirizzo.path.split("/") if p]
        domanda = parse_qs(indirizzo.query)
        try:
            self._get(parti, domanda)
        except ErroreAirender as errore:
            self._errore(errore)

    def _get(self, parti: list[str], domanda: dict) -> None:
        studio = self.studio
        match parti:
            case []:
                self._file(CARTELLA_PAGINE / "index.html")
            case ["pagine", nome] if nome in _PAGINE:
                self._invia(HTTPStatus.OK, (CARTELLA_PAGINE / nome).read_bytes(),
                            _PAGINE[nome] + "; charset=utf-8")
            case ["api", "studio"]:
                self._json(studio.stato_studio())
            case ["api", "catalogo"]:
                self._json(studio.catalogo())
            case ["api", "viste", nome]:
                self._json(studio.descrivi_vista(nome))
            case ["api", "viste", nome, "render"]:
                self._json(studio.render_della_vista(nome))
            case ["api", "viste", nome, "passi"]:
                self._json(studio.passi(nome))
            case ["api", "destinazione"]:
                self._json(studio.destinazione((domanda.get("modello") or [""])[0],
                                               (domanda.get("varianti") or ["1"])[0]))
            case ["api", "lavori", identificativo]:
                self._json(studio.lavoro(identificativo))
            case ["api", "lavori", identificativo, "ricetta"]:
                self._json(studio.ricetta(identificativo))
            case ["file", "vista", nome]:
                self._file(studio.percorso_vista(nome))
            case ["file", "render", identificativo]:
                self._file(studio.file_render(identificativo))
            case ["file", "miniatura", preset]:
                self._file(studio.file_miniatura(preset))
            case _:
                self._json({"errore": {"fatto": "Questa pagina dello Studio non esiste.",
                                       "cosa_fare": "Torna alla pagina principale."}},
                           HTTPStatus.NOT_FOUND)

    # --- POST ------------------------------------------------------------

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        if not self._host_valido() or self.headers.get(INTESTAZIONE_STUDIO) != "1":
            self._invia(HTTPStatus.FORBIDDEN, b"", "text/plain")
            return
        parti = [unquote(p) for p in urlsplit(self.path).path.split("/") if p]
        try:
            self._post(parti)
        except ErroreAirender as errore:
            self._errore(errore)

    def _post(self, parti: list[str]) -> None:
        studio = self.studio
        match parti:
            case ["api", "componi"]:
                self._json(studio.componi(self._corpo_json()))
            case ["api", "prova-a-secco"]:
                self._json(studio.prova_a_secco(self._corpo_json()))
            case ["api", "invia"]:
                self._json(studio.invia(self._corpo_json()))
            case ["api", "viste"]:
                self._json(studio.carica_vista(self._corpo(), self.headers.get("X-Nome-File", "")))
            case ["api", "lavori", identificativo, "annulla"]:
                self._json(studio.annulla(identificativo))
            case ["api", "lavori", identificativo, "misura"]:
                self._json(studio.misura_ora(identificativo))
            case ["api", "lavori", identificativo, "rifai"]:
                self._json(studio.rifai(identificativo, self._corpo_json()))
            case ["api", "passi", "componi"]:
                self._json(studio.componi_passo(self._corpo_json()))
            case ["api", "passi", "invia"]:
                self._json(studio.invia_passo(self._corpo_json()))
            case ["api", "passi", "pulito", "componi"]:
                self._json(studio.componi_pulito(self._corpo_json()))
            case ["api", "passi", "pulito", "invia"]:
                self._json(studio.invia_pulito(self._corpo_json()))
            case ["api", "ritocca", "componi"]:
                self._json(studio.componi_ritocco(self._corpo_json()))
            case ["api", "ritocca", "invia"]:
                self._json(studio.invia_ritocco(self._corpo_json()))
            case ["api", "apri-cartella"]:
                self._json(studio.apri_cartella(str(self._corpo_json().get("quale", ""))))
            case _:
                self._json({"errore": {"fatto": "Lo Studio non sa fare questa richiesta.",
                                       "cosa_fare": "Ricarica la pagina dello Studio."}},
                           HTTPStatus.NOT_FOUND)


def crea_server(studio: Studio, porta: int = 0) -> ThreadingHTTPServer:
    """Il server, legato a 127.0.0.1. Con porta 0 la sceglie il sistema."""
    gestore = type("GestoreStudio", (_Gestore,), {"studio": studio})
    server = ThreadingHTTPServer((INDIRIZZO, porta), gestore)
    server.daemon_threads = True
    return server


def indirizzo(server: ThreadingHTTPServer) -> str:
    return f"http://{INDIRIZZO}:{server.server_address[1]}/"


def avvia_in_sottofondo(server: ThreadingHTTPServer) -> threading.Thread:
    """Per i test e per chi vuole il server senza bloccare: serve finche' non lo si chiude."""
    filo = threading.Thread(target=server.serve_forever, daemon=True)
    filo.start()
    return filo
