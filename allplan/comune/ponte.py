"""Il ponte fra la palette di Allplan e il motore.

Qui non c'e' nessun import di Allplan: questo file si prova da riga di comando
come il motore. L'adattatore di ogni versione (allplan/v2026/...) fa solo le
chiamate che esistono soltanto dentro Allplan (cattura della finestra, lettura
della camera) e passa il resto a queste funzioni.

Il motore si chiama attraverso la sua riga di comando, `core.cli.main`, cosi'
la palette dice esattamente quello che direbbe il terminale: destinazione
dell'invio, rifiuti, errori in italiano. Nessuna seconda formulazione.
"""

from __future__ import annotations

import contextlib
import io
import json
from datetime import datetime
from pathlib import Path

PREFISSO_VISTA = "vista"
SUFFISSO_CAMERA = ".camera.json"


def percorso_vista(cartella: Path, adesso: datetime | None = None) -> Path:
    """Il file dove salvare la prossima cattura. Mai sovrascrivere una vista."""
    adesso = adesso or datetime.now()
    base = cartella / f"{PREFISSO_VISTA}-{adesso:%Y%m%d-%H%M%S}.png"
    candidato, indice = base, 1
    while candidato.exists():
        candidato = base.with_name(f"{base.stem}({indice}){base.suffix}")
        indice += 1
    return candidato


def scrivi_camera(vista: Path, camera: dict) -> Path:
    """Salva accanto alla vista da dove e' stata guardata.

    Serve per rifare la stessa inquadratura e, piu' avanti, per legare il
    render alla vista salvata di Allplan. Le voci che Allplan non ha saputo
    dare restano scritte come errore, non spariscono.
    """
    destinazione = vista.with_name(vista.stem + SUFFISSO_CAMERA)
    destinazione.write_text(json.dumps(camera, indent=2, ensure_ascii=False), encoding="utf-8")
    return destinazione


def argomenti_motore(vista: Path, preset: str = "base", testo: str = "",
                     a_secco: bool = True) -> list[str]:
    """La riga di comando che la palette fa eseguire al motore."""
    argomenti = ["--immagine", str(vista), "--preset", preset or "base"]
    if testo.strip():
        argomenti += ["--testo", testo.strip()]
    if a_secco:
        argomenti.append("--prova-a-secco")
    return argomenti


def esegui_motore(argomenti: list[str]) -> tuple[int, str]:
    """Esegue il motore e restituisce codice di uscita e testo da mostrare.

    Dentro Allplan non c'e' un terminale: tutto quello che il motore stampa si
    raccoglie e finisce in una finestra di messaggio.
    """
    raccolto = io.StringIO()
    try:
        from core import cli  # import qui: senza Pillow fallisce, e va detto bene
    except ImportError as errore:
        return 4, (
            f"Il motore non si carica: {errore}.\n"
            "Cosa fare: installa Pillow con lo strumento \"Install Python Package\" "
            "del PythonParts SDK (pacchetto: pillow), poi riavvia Allplan."
        )
    with contextlib.redirect_stdout(raccolto), contextlib.redirect_stderr(raccolto):
        try:
            codice = cli.main(argomenti)
        except SystemExit as uscita:  # argparse esce cosi' sugli argomenti sbagliati
            codice = uscita.code if isinstance(uscita.code, int) else 4
        except Exception as errore:  # pylint: disable=broad-exception-caught
            # La palette non deve mai restare muta: l'imprevisto si mostra com'e'.
            print(f"Errore imprevisto del motore: {type(errore).__name__}: {errore}")
            codice = 1
    return codice, raccolto.getvalue().strip()


def destinazione_predefinita() -> str:
    """Il servizio che ricevera' l'immagine, da mostrare prima di ogni invio."""
    try:
        from core import provider as registro
        return registro.classe(registro.PREDEFINITO).destinazione
    except ImportError:
        return "sconosciuta finche' il motore non si carica (manca Pillow?)"
