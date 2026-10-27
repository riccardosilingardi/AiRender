"""La sonda della palette: le parti che si provano senza Allplan.

Serve a rispondere sul PC vero a cinque domande, prima di scrivere la palette
nuova e lo Studio (piano UI del 2026-10-27):

1. un'immagine della palette si puo' cambiare da script?
2. `PictureButtonList` mostra immagini da file?
3. un PythonPart puo' lanciare un processo a parte, e con quale Python?
4. `msedge --app=` apre una pagina locale come finestra?
5. Allplan resta usabile mentre quel processo lavora?

Qui non c'e' nessun import di Allplan. L'adattatore (`AirenderSonda.py`) fa
solo i clic e passa il resto a queste funzioni. Ogni risposta finisce in un
file di testo che Riccardo rimanda indietro: la sonda non decide niente, scrive
quello che ha visto.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

FILE_RISULTATI = "risultati-sonda.txt"
FILE_STATO = "stato.json"

# Quanto vive il processo di prova. Abbastanza per girare il modello, aprire
# Edge e premere Controlla due volte; poi si spegne da solo.
SECONDI_FIGLIO = 180

# Il codice che ogni Python candidato esegue per dire chi e' e se ha Pillow.
CODICE_IDENTITA = (
    "import sys, importlib.util as u; "
    "print(sys.version.split()[0], sys.executable, bool(u.find_spec('PIL')), sep='|')"
)

# Variabili che Allplan potrebbe impostare per il suo Python incorporato e che
# confonderebbero un Python di sistema lanciato da li'.
VARIABILI_DI_ALLPLAN = ("PYTHONHOME", "PYTHONPATH")


class Registro:
    """Il file dove la sonda scrive cosa ha visto, una riga per fatto."""

    def __init__(self, cartella: Path, adesso: Callable[[], datetime] = datetime.now):
        self.cartella = cartella
        self.percorso = cartella / FILE_RISULTATI
        self._adesso = adesso

    def scrivi(self, domanda: str, testo: str) -> str:
        riga = f"[{self._adesso():%Y-%m-%d %H:%M:%S}] {domanda} · {testo}"
        self.cartella.mkdir(parents=True, exist_ok=True)
        with self.percorso.open("a", encoding="utf-8") as file:
            file.write(riga + "\n")
        return riga

    def leggi(self) -> str:
        if not self.percorso.exists():
            return "Ancora niente: premi i pulsanti della sonda, dall'alto in basso."
        return self.percorso.read_text(encoding="utf-8")


def descrivi_python_corrente() -> str:
    """Il Python dentro cui gira la palette, detto senza interpretare."""
    return (f"versione {sys.version.split()[0]} · eseguibile {sys.executable} · "
            f"prefix {sys.prefix} · base_prefix {sys.base_prefix} · {platform.platform()}")


def _e_un_python(percorso: str) -> bool:
    # sys.executable dentro Allplan puo' essere Allplan.exe: lanciarlo aprirebbe
    # un secondo Allplan. Si accettano solo eseguibili che si chiamano python o py.
    nome = percorso.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nome in {"python.exe", "pythonw.exe", "python", "python3", "py.exe"}


def candidati_python(prefissi: list[str], eseguibile: str,
                     trova: Callable[[str], str | None]) -> list[tuple[str, list[str]]]:
    """Gli interpreti da provare, nell'ordine: prima quello di Allplan, poi il sistema.

    Ogni voce e' (da dove viene, comando). Niente doppioni.
    """
    visti: set[str] = set()
    candidati: list[tuple[str, list[str]]] = []

    def aggiungi(origine: str, comando: list[str]) -> None:
        chiave = os.path.normcase(comando[0])
        if chiave in visti:
            return
        visti.add(chiave)
        candidati.append((origine, comando))

    if eseguibile and _e_un_python(eseguibile):
        aggiungi("sys.executable", [eseguibile])
    for prefisso in prefissi:
        if not prefisso:
            continue
        for nome in ("python.exe", "python"):
            percorso = Path(prefisso) / nome
            if percorso.exists():
                aggiungi(f"Python di Allplan ({prefisso})", [str(percorso)])
                break
    lanciatore = trova("py")
    if lanciatore:
        aggiungi("py di sistema", [lanciatore, "-3"])
    for nome in ("python", "python3"):
        percorso = trova(nome)
        if percorso and _e_un_python(percorso):
            aggiungi(f"{nome} di sistema", [percorso])
    return candidati


def ambiente_per(origine: str, base: dict[str, str]) -> dict[str, str]:
    """Il Python di sistema parte senza le variabili del Python di Allplan."""
    ambiente = dict(base)
    if "sistema" in origine:
        for nome in VARIABILI_DI_ALLPLAN:
            ambiente.pop(nome, None)
    return ambiente


def interpreta_identita(uscita: str) -> dict:
    """Legge la riga stampata da CODICE_IDENTITA. Una riga strana resta com'e'."""
    righe = [r for r in uscita.strip().splitlines() if r.strip()]
    parti = righe[-1].split("|") if righe else []
    if len(parti) != 3:
        return {"letto": False, "uscita": uscita.strip()[:300]}
    versione, eseguibile, pil = parti
    return {"letto": True, "versione": versione, "eseguibile": eseguibile, "pillow": pil == "True"}


def opzioni_staccato() -> dict:
    """Come lanciare un processo che non tiene legata Allplan e non apre console."""
    opzioni: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        opzioni["creationflags"] = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        )
    else:
        opzioni["start_new_session"] = True
    return opzioni


def comando_figlio(python: list[str], figlio: Path, cartella: Path,
                   secondi: int = SECONDI_FIGLIO) -> list[str]:
    return [*python, str(figlio), "--cartella", str(cartella), "--secondi", str(secondi)]


def leggi_stato(cartella: Path) -> dict | None:
    """Lo stato scritto dal processo di prova, o None se non ha scritto niente."""
    percorso = cartella / FILE_STATO
    try:
        return json.loads(percorso.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def descrivi_stato(stato: dict | None, adesso: float) -> str:
    """Una frase su come sta il processo di prova, con i numeri che ha scritto lui."""
    if stato is None:
        return "il processo di prova non ha scritto niente: non e' partito o e' gia' morto subito"
    fermo_da = adesso - float(stato.get("ultimo", 0))
    vivo = not stato.get("finito") and fermo_da < 3
    return (
        f"{'vivo' if vivo else 'fermo'} · battiti {stato.get('battiti')} · "
        f"ultimo battito {fermo_da:.1f} s fa · pid {stato.get('pid')} · "
        f"Python {stato.get('versione')} ({stato.get('eseguibile')}) · "
        f"Pillow {'si' if stato.get('pillow') else 'no'} · "
        f"pagina http://127.0.0.1:{stato.get('porta')}/"
    )


def percorsi_edge(ambiente: dict[str, str], trova: Callable[[str], str | None]) -> list[str]:
    """Dove puo' essere Edge su Windows, il primo che esiste vince."""
    candidati = [trova("msedge") or ""]
    for variabile in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA"):
        radice = ambiente.get(variabile)
        if radice:
            candidati.append(str(Path(radice) / "Microsoft" / "Edge" / "Application" / "msedge.exe"))
    return [c for c in candidati if c]


def comando_edge(edge: str, indirizzo: str) -> list[str]:
    return [edge, f"--app={indirizzo}", "--new-window"]
