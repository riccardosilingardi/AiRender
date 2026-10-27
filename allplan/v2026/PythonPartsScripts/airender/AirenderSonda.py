"""AIRENDER sonda — cinque domande sulla palette, da far girare in Allplan 2026.

Non e' il prodotto: e' una prova usa e getta, come la prima palette. Ogni
pulsante risponde a una domanda e scrive cosa ha visto in
`Usr\\...\\AIRENDER\\sonda\\risultati-sonda.txt`. La logica che non ha bisogno di
Allplan sta in `sonda_palette.py` e si prova con pytest.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_Utility as AllplanUtil

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

import sonda_palette as sonda  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_IMMAGINE = 2001
EVENTO_MINIATURA = 2002
EVENTO_TROVA_PYTHON = 2003
EVENTO_AVVIA = 2004
EVENTO_CONTROLLA = 2005
EVENTO_EDGE = 2006
EVENTO_RIEPILOGO = 2007

IMMAGINE_A = "sonda_a.png"
IMMAGINE_B = "sonda_b.png"
IMMAGINE_FISSA = "sonda_anteprima.png"

print("Load AirenderSonda.py")

_VERSIONE_ALLPLAN = {"valore": "sconosciuta"}


def check_allplan_version(_build_ele: BuildingElement, version: str) -> bool:
    _VERSIONE_ALLPLAN["valore"] = str(version)
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderSonda(build_ele, script_object_data)


class AirenderSonda(BaseScriptObject):
    """Sette pulsanti, uno per domanda, piu' il riepilogo."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        usr = Path(AllplanSettings.AllplanPaths.GetUsrPath())
        self.cartella = usr / "AIRENDER" / "sonda"
        self.libreria = usr / "Library" / "AIRENDER"
        self.registro = sonda.Registro(self.cartella)
        self.mostra_b = False
        self.python: list[str] | None = None
        self.origine_python = ""
        self.registro.scrivi(
            "avvio",
            f"Allplan {_VERSIONE_ALLPLAN['valore']} · {sonda.descrivi_python_corrente()} · "
            f"Usr {usr} · libreria {self.libreria} (esiste: {self.libreria.exists()})")

    def execute(self) -> CreateElementResult:
        return CreateElementResult()

    def on_control_event(self, event_id: int) -> None:
        azioni = {
            EVENTO_IMMAGINE: self._cambia_immagine,
            EVENTO_MINIATURA: self._registra_miniatura,
            EVENTO_TROVA_PYTHON: self._trova_python,
            EVENTO_AVVIA: self._avvia_processo,
            EVENTO_CONTROLLA: self._controlla_processo,
            EVENTO_EDGE: self._apri_edge,
            EVENTO_RIEPILOGO: self._riepilogo,
        }
        azione = azioni.get(event_id)
        if azione is None:
            return
        try:
            azione()
        except Exception as errore:  # pylint: disable=broad-exception-caught
            # Una sonda che si zittisce non serve: l'errore si scrive com'e'.
            riga = self.registro.scrivi(f"errore evento {event_id}", f"{type(errore).__name__}: {errore}")
            AllplanUtil.ShowMessageBox(riga, AllplanUtil.MB_OK)

    # ---------------------------------------------------------- domanda 1

    def _cambia_immagine(self) -> None:
        """Due modi di cambiare un'immagine: stesso file riscritto, oppure nuovo percorso."""
        self.mostra_b = not self.mostra_b
        nuova = IMMAGINE_B if self.mostra_b else IMMAGINE_A
        sorgente = self.libreria / nuova
        shutil.copyfile(sorgente, self.libreria / IMMAGINE_FISSA)
        self.build_ele.AnteprimaVariabile.value = str(sorgente)
        lettera = "B" if self.mostra_b else "A"
        self.registro.scrivi(
            "1 immagine",
            f"premuto Cambia immagine: tutte e due le immagini ora dovrebbero mostrare {lettera}")
        AllplanUtil.ShowMessageBox(
            f"Ora le due immagini in alto dovrebbero mostrare la lettera {lettera}.\n\n"
            "Guarda quali sono cambiate (la prima, la seconda, nessuna) e scrivimelo.",
            AllplanUtil.MB_OK)

    # ---------------------------------------------------------- domanda 2

    def _registra_miniatura(self) -> None:
        valore = self.build_ele.Miniature.value
        self.registro.scrivi("2 miniature", f"valore scelto nella griglia: {valore}")
        AllplanUtil.ShowMessageBox(
            f"La griglia dice che hai scelto la miniatura {valore}.\n\n"
            "Scrivimi anche se le miniature si vedevano come immagini o erano vuote.",
            AllplanUtil.MB_OK)

    # ---------------------------------------------------------- domanda 3

    def _trova_python(self) -> None:
        candidati = sonda.candidati_python(
            [sys.prefix, sys.base_prefix, str(Path(sys.executable).parent)],
            sys.executable, shutil.which)
        if not candidati:
            riga = self.registro.scrivi("3 python", "nessun interprete Python trovato, ne' di Allplan ne' di sistema")
            AllplanUtil.ShowMessageBox(riga, AllplanUtil.MB_OK)
            return
        righe = []
        for origine, comando in candidati:
            try:
                risultato = subprocess.run(
                    [*comando, "-c", sonda.CODICE_IDENTITA], capture_output=True, text=True,
                    timeout=20, env=sonda.ambiente_per(origine, dict(os.environ)),
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                identita = sonda.interpreta_identita(risultato.stdout + risultato.stderr)
            except (OSError, subprocess.SubprocessError) as errore:
                identita = {"letto": False, "uscita": f"{type(errore).__name__}: {errore}"}
            righe.append(self.registro.scrivi("3 python", f"{origine} · {comando} · {identita}"))
            if identita.get("letto") and self.python is None:
                self.python, self.origine_python = comando, origine
        scelto = f"Usero' {self.origine_python}." if self.python else "Nessuno ha risposto."
        AllplanUtil.ShowMessageBox("\n\n".join(righe) + f"\n\n{scelto}", AllplanUtil.MB_OK)

    def _avvia_processo(self) -> None:
        if self.python is None:
            self._trova_python()
        if self.python is None:
            return
        cartella_figlio = self.cartella / "processo"
        cartella_figlio.mkdir(parents=True, exist_ok=True)
        (cartella_figlio / sonda.FILE_STATO).unlink(missing_ok=True)
        comando = sonda.comando_figlio(self.python, _CARTELLA / "sonda_figlio.py", cartella_figlio)
        inizio = time.time()
        processo = subprocess.Popen(  # pylint: disable=consider-using-with
            comando, env=sonda.ambiente_per(self.origine_python, dict(os.environ)),
            **sonda.opzioni_staccato())
        durata = time.time() - inizio
        self.registro.scrivi(
            "3 processo",
            f"Popen tornato in {durata:.2f} s · pid {processo.pid} · {self.origine_python} · {comando}")
        AllplanUtil.ShowMessageBox(
            f"Processo di prova lanciato (pid {processo.pid}). Vive {sonda.SECONDI_FIGLIO} secondi.\n\n"
            "Adesso, per mezzo minuto, usa Allplan normalmente: gira il modello, zooma.\n"
            "Poi premi Controlla processo. Poi Apri in Edge.",
            AllplanUtil.MB_OK)

    # ---------------------------------------------------------- domanda 5

    def _controlla_processo(self) -> None:
        stato = sonda.leggi_stato(self.cartella / "processo")
        riga = self.registro.scrivi("5 processo", sonda.descrivi_stato(stato, time.time()))
        AllplanUtil.ShowMessageBox(
            riga + "\n\nAllplan rispondeva mentre giravi il modello? Scrivimelo a parole.",
            AllplanUtil.MB_OK)

    # ---------------------------------------------------------- domanda 4

    def _apri_edge(self) -> None:
        stato = sonda.leggi_stato(self.cartella / "processo")
        if stato and stato.get("porta") and not stato.get("finito"):
            indirizzo = f"http://127.0.0.1:{stato['porta']}/"
        else:
            pagina = self.cartella / "pagina-sonda.html"
            pagina.write_text(
                "<!doctype html><meta charset='utf-8'><title>AIRENDER sonda</title>"
                "<h1>Edge si apre, ma il processo di prova non e' attivo.</h1>", encoding="utf-8")
            indirizzo = pagina.as_uri()
        edge = next((p for p in sonda.percorsi_edge(dict(os.environ), shutil.which)
                     if Path(p).exists()), None)
        if edge is None:
            riga = self.registro.scrivi("4 edge", "msedge.exe non trovato nei percorsi soliti")
            AllplanUtil.ShowMessageBox(riga, AllplanUtil.MB_OK)
            return
        subprocess.Popen(sonda.comando_edge(edge, indirizzo), **sonda.opzioni_staccato())  # pylint: disable=consider-using-with
        riga = self.registro.scrivi("4 edge", f"lanciato {edge} su {indirizzo}")
        AllplanUtil.ShowMessageBox(
            riga + "\n\nSi e' aperta una finestra senza barra degli indirizzi? "
            "Il numero del battito sale? Scrivimelo.", AllplanUtil.MB_OK)

    # ---------------------------------------------------------- riepilogo

    def _riepilogo(self) -> None:
        AllplanUtil.ShowMessageBox(
            f"Il file da mandarmi:\n{self.registro.percorso}\n\n{self.registro.leggi()[-1500:]}",
            AllplanUtil.MB_OK)
