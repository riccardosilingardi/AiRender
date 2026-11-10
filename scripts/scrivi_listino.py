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
    from itertools import combinations  # noqa: E402  pylint: disable=import-outside-toplevel

    from core.provider import geometria  # noqa: E402  pylint: disable=import-outside-toplevel

    # Un grafo per ogni insieme di controlli (Spigoli, Profondita', Linee
    # dritte), gia' coi valori di config.py: il server sceglie quello giusto
    # e riempie solo vista, prompt e seme.
    grafi, riagganci = {}, {}
    for quanti in range(1, len(geometria.CONTROLLI) + 1):
        for scelta in combinations(geometria.CONTROLLI, quanti):
            grafi["+".join(scelta)] = geometria.grafo_per(scelta)
            riagganci["+".join(scelta)] = geometria.grafo_per(scelta, riaggancia=True)
    dati = {
        "grafi": grafi,
        # «Riaggancia alla vista»: gli stessi controlli, col render nel latente.
        "grafi_riaggancia": riagganci,
        "nodi": {"immagine": geometria.NODO_IMMAGINE, "prompt": geometria.NODO_PROMPT,
                 "campionatore": geometria.NODO_CAMPIONATORE, "render": geometria.NODO_RENDER},
        # Da quale nodo ControlNet si riconosce un controllo nel grafo del
        # client, nell'ordine dei nomi dei grafi (una lista: le chiavi si ordinano).
        "controlli": [[c, geometria.NODI_CONTROLLO[c][1]] for c in geometria.CONTROLLI],
        "lato_massimo": config.GEOMETRIA_LATO_MASSIMO,
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
