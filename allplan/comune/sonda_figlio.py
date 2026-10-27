"""Il processo di prova lanciato dalla sonda della palette.

Fa la parte che lo Studio vero dovra' fare: gira fuori da Allplan, serve una
pagina locale e dice di essere vivo. Ogni mezzo secondo riscrive `stato.json`
con un contatore, cosi' la palette puo' controllare se il processo lavora
mentre Allplan si usa. Dopo `--secondi` si spegne da solo.

Solo libreria standard: deve partire con qualunque Python trovi la sonda.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PAGINA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta http-equiv="refresh" content="1">
<title>AIRENDER sonda</title></head>
<body style="font-family: Segoe UI, sans-serif; background: #141518; color: #EDEDEF; padding: 24px">
<h1 style="font-size: 20px">AIRENDER · sonda dello Studio</h1>
<p>Se vedi questa pagina in una finestra senza barra degli indirizzi, la domanda 4 ha risposta si.</p>
<p>Il processo di prova e' vivo: battito <b>{battiti}</b>. Il numero sale ogni mezzo secondo.</p>
<p>Python {versione}</p>
</body></html>
"""


class Stato:
    def __init__(self, cartella: Path):
        self.cartella = cartella
        self.dati = {
            "pid": os.getpid(),
            "versione": sys.version.split()[0],
            "eseguibile": sys.executable,
            "pillow": importlib.util.find_spec("PIL") is not None,
            "porta": None,
            "battiti": 0,
            "avviato": time.time(),
            "ultimo": time.time(),
            "finito": False,
        }

    def scrivi(self) -> None:
        provvisorio = self.cartella / "stato.json.tmp"
        provvisorio.write_text(json.dumps(self.dati), encoding="utf-8")
        os.replace(provvisorio, self.cartella / "stato.json")


def gestore_per(stato: Stato):
    class Gestore(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 (nome imposto da http.server)
            corpo = PAGINA.format(battiti=stato.dati["battiti"], versione=stato.dati["versione"])
            corpo = corpo.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def log_message(self, *_argomenti):  # niente console da riempire
            return

    return Gestore


def main(argomenti: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cartella", required=True)
    parser.add_argument("--secondi", type=float, default=180)
    opzioni = parser.parse_args(argomenti)

    cartella = Path(opzioni.cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    stato = Stato(cartella)

    # Porta 0: la sceglie il sistema, cosi' non si scontra con niente.
    server = ThreadingHTTPServer(("127.0.0.1", 0), gestore_per(stato))
    stato.dati["porta"] = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()

    fine = time.time() + opzioni.secondi
    try:
        while time.time() < fine:
            stato.dati["battiti"] += 1
            stato.dati["ultimo"] = time.time()
            stato.scrivi()
            time.sleep(0.5)
    finally:
        stato.dati["finito"] = True
        stato.scrivi()
        server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
