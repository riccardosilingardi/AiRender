"""Riscrive server/listino.json e server/geometria.json da core/config.py.

    python scripts/scrivi_listino.py

Il listino vive in core/config.py (LISTINO). Il server lo legge da un file
JSON accanto alle sue funzioni: questo script e' l'unico modo in cui quel
file cambia. tests/test_listino.py fallisce se i due divergono.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import config  # noqa: E402

FILE = RADICE / "server" / "listino.json"
FILE_GEOMETRIA = RADICE / "server" / "geometria.json"


def testo() -> str:
    return json.dumps(config.LISTINO, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def testo_geometria() -> str:
    from core.provider import geometria  # noqa: E402  pylint: disable=import-outside-toplevel

    dati = {
        "workflow": json.loads(geometria.WORKFLOW.read_text(encoding="utf-8")),
        "nodi": {"immagine": geometria.NODO_IMMAGINE, "lato": geometria.NODO_LATO,
                 "prompt": geometria.NODO_PROMPT, "forza": geometria.NODO_FORZA,
                 "campionatore": geometria.NODO_CAMPIONATORE},
        "lato_massimo": config.GEOMETRIA_LATO_MASSIMO,
        "forza": config.GEOMETRIA_FORZA,
        "passi": config.GEOMETRIA_PASSI,
        "nome": geometria.NOME_WORKFLOW,
    }
    return json.dumps(dati, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    FILE.write_text(testo(), encoding="utf-8")
    FILE_GEOMETRIA.write_text(testo_geometria(), encoding="utf-8")
    print(f"Scritti {FILE.relative_to(RADICE)} e {FILE_GEOMETRIA.relative_to(RADICE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
