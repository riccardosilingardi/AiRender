"""python -m core.studio: il server dello Studio, la coda dei lavori e la finestra.

    python -m core.studio --cartella C:\\...\\AIRENDER\\viste

Avvia tre cose e le chiude insieme (Ctrl+C):

1. il server locale su 127.0.0.1, porta scelta dal sistema;
2. la coda dei lavori (`python -m core.coda`) come processo figlio, sulla
   stessa cartella: e' lei che manda le viste, non lo Studio;
3. la pagina, con Edge in modalita' app se c'e', altrimenti col browser
   predefinito.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from .. import battito as modulo_battito, coda as modulo_coda, provider as registro
from ..errori import ErroreAirender
from .server import crea_server, indirizzo
from .servizio import Studio

# La radice del pacchetto, da cui `-m core.coda` si trova.
RADICE = Path(__file__).resolve().parents[2]


def cartella_predefinita() -> Path:
    """Senza Allplan non si conosce la cartella Usr: si usa quella dell'utente."""
    return Path.home() / "AIRENDER" / "viste"


def trova_edge() -> str | None:
    trovato = shutil.which("msedge")
    if trovato:
        return trovato
    for variabile in ("ProgramFiles(x86)", "ProgramFiles"):
        base = os.environ.get(variabile)
        if base:
            candidato = Path(base) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
            if candidato.is_file():
                return str(candidato)
    return None


def apri_finestra(url: str) -> str:
    """Apre la pagina. Restituisce con cosa l'ha aperta, per dirlo nella console."""
    edge = trova_edge()
    if edge:
        subprocess.Popen([edge, f"--app={url}"])  # pylint: disable=consider-using-with
        return "Edge in modalità app"
    webbrowser.open(url)
    return "il browser predefinito"


def avvia_coda(cartella: Path) -> subprocess.Popen:
    return subprocess.Popen(  # pylint: disable=consider-using-with
        [sys.executable, "-m", "core.coda", "--cartella", str(cartella)],
        cwd=str(RADICE),
    )


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core.studio",
        description="Lo Studio: scegli lo stile, manda la vista, guarda il render.",
    )
    parser.add_argument(
        "--cartella", default=None,
        help=f"la cartella delle viste (predefinita: {cartella_predefinita()})",
    )
    parser.add_argument("--porta", type=int, default=0, help="0 = la sceglie il sistema")
    parser.add_argument("--senza-finestra", action="store_true", dest="senza_finestra",
                        help="non apre la pagina: stampa solo l'indirizzo")
    parser.add_argument("--senza-coda", action="store_true", dest="senza_coda",
                        help="non avvia la coda (per esempio perche' gira gia')")
    parser.add_argument("--provider", default=registro.PREDEFINITO, choices=registro.nomi())
    return parser


def main(argv: list[str] | None = None) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    cartella = Path(argomenti.cartella) if argomenti.cartella else cartella_predefinita()
    coda = None
    gia_viva = modulo_coda.coda_viva(cartella.resolve()) is not None
    try:
        if not argomenti.senza_coda and not gia_viva:
            coda = avvia_coda(cartella.resolve())
        studio = Studio(
            cartella,
            provider=argomenti.provider,
            # Vale anche per una coda avviata da altri (la palette, a mano):
            # conta il suo battito, non chi l'ha lanciata.
            coda_attiva=(lambda: modulo_coda.coda_viva(studio.cartella) is not None
                         or (coda is not None and coda.poll() is None)),
        )
        server = crea_server(studio, argomenti.porta)
    except (ErroreAirender, OSError) as errore:
        if coda is not None:
            coda.terminate()
        print(f"Lo Studio non parte: {errore}", file=sys.stderr)
        return 2  # numero-non-configurabile: convenzione della shell, come core.cli
    url = indirizzo(server)
    print(f"Studio su {url}")
    print(f"Cartella delle viste: {studio.cartella}")
    if coda:
        print("La coda dei lavori gira.")
    elif gia_viva:
        print("Su questa cartella gira gia' una coda dei lavori: lo Studio usa quella.")
    else:
        print("La coda dei lavori non e' stata avviata (--senza-coda).")
    if not argomenti.senza_finestra:
        print(f"Pagina aperta con {apri_finestra(url)}.")
    print("Ctrl+C per chiudere lo Studio e la coda.")
    try:
        # Il battito dice alla palette di Allplan che lo Studio c'e' e dove:
        # «Apri nello Studio» riapre questa pagina invece di avviarne un altro.
        with modulo_battito.Battito(
            modulo_battito.percorso(studio.cartella, modulo_battito.FILE_STUDIO),
            {"indirizzo": url, "cartella": str(studio.cartella)},
        ):
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if coda is not None and coda.poll() is None:
            coda.terminate()
            print(
                "Studio chiuso. Un lavoro rimasto a meta' la coda lo ritrova al "
                "prossimo avvio: se non era partito torna in coda, se era partito "
                "va fra gli errori (il servizio puo' averlo gia' addebitato)."
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
