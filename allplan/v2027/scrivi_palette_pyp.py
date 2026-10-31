"""Scrive il .pyp della palette v1 per Allplan 2027, dentro il pacchetto plugin.

    python allplan/v2027/scrivi_palette_pyp.py

La palette e' la stessa della 2026: i campi li scrive
allplan/v2026/scrivi_palette_pyp.py. Qui cambiano solo l'anno dello schema e
il percorso dello script, che nel pacchetto .allep sta sotto
PythonPartsScripts/<sviluppatore>/<plugin>/ come nel PythonParts SDK.
Lo schema XML resta quello del 2026: gli esempi ufficiali del ramo 2027
(PythonPartsExamples, main) puntano ancora a pythonparts.allplan.com/2026,
e serve solo agli editor, Allplan non lo legge.
Nessun import di Allplan: gira con un Python qualunque.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

QUI = Path(__file__).resolve().parent
PACCHETTO = QUI / "pacchetto"
SCRIPT = "riccardo_silingardi\\airender\\AirenderPalette.py"
DESTINAZIONE = PACCHETTO / "Library" / "AIRENDER" / "AirenderPalette.pyp"


def _generatore_2026():
    percorso = QUI.parent / "v2026" / "scrivi_palette_pyp.py"
    specifica = importlib.util.spec_from_file_location("scrivi_palette_pyp_2026", percorso)
    modulo = importlib.util.module_from_spec(specifica)
    specifica.loader.exec_module(modulo)
    return modulo


def pyp() -> str:
    return _generatore_2026().pyp(
        anno_schema="2026", script=SCRIPT, generato_da="allplan/v2027/scrivi_palette_pyp.py")


if __name__ == "__main__":
    DESTINAZIONE.write_text(pyp(), encoding="utf-8")
    print(f"Scritto {DESTINAZIONE}")
