"""Le miniature vere dei preset: render del banco di prova ritagliati.

Finche' un preset non ce l'ha, lo Studio disegna un'illustrazione e dice che
lo e' (decisione del 2026-10-27, DESIGN.md). Una miniatura vera nasce solo da
un render del piano «preset» del banco, cioe' dal preset com'e', senza cambi:
una miniatura che promette piu' di quello che il preset produce e' la prima
causa di sfiducia.

Le miniature stanno in questa cartella, nel repository: chi le mette sceglie
una vista che puo' mostrare a tutti.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from .. import blocchi, immagine as modulo_immagine
from ..coda import scrivi_atomico, scrivi_json

CARTELLA = Path(__file__).resolve().parent / "miniature"
INDICE = "indice.json"


def leggi(cartella: Path = CARTELLA) -> dict[str, dict]:
    """Preset -> {file, data, modello, render}. Solo le voci il cui file c'e'."""
    try:
        indice = json.loads((cartella / INDICE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(indice, dict):
        return {}
    return {
        preset: voce for preset, voce in indice.items()
        if preset in blocchi.PRESET_STILE and isinstance(voce, dict)
        and (cartella / str(voce.get("file", ""))).is_file()
    }


def file_di(preset: str, cartella: Path = CARTELLA) -> Path | None:
    voce = leggi(cartella).get(preset)
    return cartella / voce["file"] if voce else None


def metti(preset: str, render: bytes, *, modello: str, origine: str, quando: date,
          cartella: Path = CARTELLA) -> Path:
    """Ritaglia il render e lo mette come miniatura del preset. Restituisce il file."""
    blocchi.preset_stile(preset)  # solleva se il preset non esiste
    cartella.mkdir(parents=True, exist_ok=True)
    nome = f"{preset}.jpg"
    scrivi_atomico(cartella / nome, modulo_immagine.ritaglia_miniatura(render))
    try:
        indice = json.loads((cartella / INDICE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        indice = {}
    indice[preset] = {
        "file": nome,
        "data": quando.isoformat(),
        "modello": modello,
        "render": origine,
        "versione_blocchi": blocchi.VERSIONE,
    }
    scrivi_json(cartella / INDICE, dict(sorted(indice.items())))
    return cartella / nome
