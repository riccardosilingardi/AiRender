"""Pillow dentro il pacchetto: il cliente non lo installa a mano.

Il pacchetto .allep porta Pillow gia' compilato per Windows, una cartella per
ogni versione di Python che Allplan puo' avere (`_pillow/cp310` ... `cp314`):
`allplan/v2027/pacchetto.py` lo prende da PyPI e ne controlla l'impronta.

All'avvio la palette chiama `assicura(cartella_dello_script)`:

- se c'e' gia' un Pillow che si carica davvero (quello installato con
  «Install Python Package»), si usa quello;
- se manca, o c'e' ma e' compilato per un altro Python (`cannot import name
  '_imaging'`, visto il 2026-10-31), si usa quello del pacchetto per la
  versione di Python che gira.

Nessun import di Allplan: si prova con pytest.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

CARTELLA = "_pillow"


def cartella_per(base: Path, versione: tuple[int, int] | None = None) -> Path:
    """La cartella del Pillow incluso per questa versione di Python (cp313 per 3.13)."""
    maggiore, minore = versione or sys.version_info[:2]
    return Path(base) / CARTELLA / f"cp{maggiore}{minore}"


def _carica() -> str | None:
    """Importa Pillow per davvero (anche la parte compilata). Restituisce l'errore, o None."""
    try:
        importlib.import_module("PIL.Image")
    except Exception as errore:  # pylint: disable=broad-exception-caught
        return f"{type(errore).__name__}: {errore}"
    return None


def _dimentica() -> None:
    for nome in [n for n in sys.modules if n == "PIL" or n.startswith("PIL.")]:
        del sys.modules[nome]


def assicura(base: Path, versione: tuple[int, int] | None = None) -> str:
    """Fa in modo che `import PIL` funzioni. Restituisce, in parole, quale Pillow si usa."""
    errore = _carica()
    if errore is None:
        return "Pillow installato in Allplan"
    incluso = cartella_per(base, versione)
    if not (incluso / "PIL").is_dir():
        return (f"Pillow non si carica ({errore}) e il pacchetto non ne ha uno per "
                f"Python {incluso.name}")
    _dimentica()
    sys.path.insert(0, str(incluso))
    importlib.invalidate_caches()
    di_nuovo = _carica()
    if di_nuovo is not None:
        return f"Pillow del pacchetto ({incluso.name}) non si carica: {di_nuovo}"
    return f"Pillow del pacchetto ({incluso.name})"
