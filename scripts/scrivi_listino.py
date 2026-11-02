"""Riscrive server/listino.json da core/config.py.

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


def testo() -> str:
    return json.dumps(config.LISTINO, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def main() -> int:
    FILE.write_text(testo(), encoding="utf-8")
    print(f"Scritto {FILE.relative_to(RADICE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
