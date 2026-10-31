"""Il file «sono vivo» di un processo: coda dei lavori e Studio.

Un processo che gira riscrive ogni BATTITO_INTERVALLO_SECONDI un piccolo JSON
in `<cartella>/lavori/` con il suo pid e l'ora. Chi vuole sapere se c'e'
(la palette di Allplan, una seconda coda, lo Studio) legge il file: se
l'ultimo battito e' piu' vecchio di BATTITO_SCADUTO_SECONDI, il processo e'
morto o bloccato.

Perche' un file e non il pid: dalla palette non si puo' chiedere a Windows
se un pid e' vivo senza ctypes, e un pid si ricicla. Un battito fermo si
riconosce senza chiedere niente a nessuno.

Il battito gira in un thread a parte: un lavoro che aspetta il servizio per
un minuto non ferma il battito.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from . import config

FILE_CODA = "coda-viva.json"
FILE_STUDIO = "studio-vivo.json"


def percorso(radice: Path, nome: str) -> Path:
    """Il file del battito sotto <radice>/lavori/. Il nome di cartella e' quello della coda."""
    return Path(radice) / "lavori" / nome


def scrivi(file: Path, dati: dict, adesso: Callable[[], float] = time.time) -> dict:
    """Riscrive il battito, atomico: chi legge non vede mai un JSON a meta'."""
    contenuto = {**dati, "pid": os.getpid(), "battito": adesso()}
    file.parent.mkdir(parents=True, exist_ok=True)
    temporaneo = file.with_name(f".{file.name}.{os.getpid()}.tmp")
    temporaneo.write_text(json.dumps(contenuto, ensure_ascii=False), encoding="utf-8")
    os.replace(temporaneo, file)
    return contenuto


def leggi(file: Path, adesso: Callable[[], float] = time.time) -> dict | None:
    """Il battito se il processo e' vivo, None se il file manca, non si legge o e' vecchio."""
    try:
        dati = json.loads(Path(file).read_text(encoding="utf-8"))
        eta = adesso() - float(dati["battito"])
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if not isinstance(dati, dict) or eta > config.BATTITO_SCADUTO_SECONDI:
        return None
    return dati


class Battito:
    """Il thread che tiene vivo il file. Si usa con `with`: all'uscita il file sparisce."""

    def __init__(self, file: Path, dati: dict | None = None,
                 intervallo: float = config.BATTITO_INTERVALLO_SECONDI) -> None:
        self.file = Path(file)
        self.dati = {"python": sys.executable, **(dati or {})}
        self._intervallo = intervallo
        self._ferma = threading.Event()
        self._thread = threading.Thread(target=self._gira, name=f"battito {self.file.name}", daemon=True)

    def __enter__(self) -> "Battito":
        scrivi(self.file, self.dati)
        self._thread.start()
        return self

    def __exit__(self, *_eccezione) -> None:
        self._ferma.set()
        self._thread.join()
        try:
            # Solo se e' ancora nostro: un altro processo puo' averlo preso dopo.
            if json.loads(self.file.read_text(encoding="utf-8")).get("pid") == os.getpid():
                self.file.unlink()
        except (OSError, ValueError):
            pass

    def _gira(self) -> None:
        while not self._ferma.wait(self._intervallo):
            try:
                scrivi(self.file, self.dati)
            except OSError:
                continue  # un disco occupato un attimo: il prossimo battito riprova
