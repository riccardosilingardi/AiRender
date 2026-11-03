"""Licenze fuori da Stripe: rivendita Serteco, prove regalate, accrediti a mano.

    set AIRENDER_ADMIN_TOKEN=...            (lo stesso del sito Netlify)
    py scripts/licenze.py crea --email studio@esempio.it --piano pro --mesi 12 --rivenditore serteco
    py scripts/licenze.py cerca --email studio@esempio.it
    py scripts/licenze.py accredita --email studio@esempio.it --render 50
    py scripts/licenze.py piano --email studio@esempio.it --piano studio
    py scripts/licenze.py sospendi --email studio@esempio.it
    py scripts/licenze.py nuovo-codice --email studio@esempio.it

Con la rivendita Serteco la fattura la fa Serteco: qui si attiva solo la
licenza, e il codice parte per email al cliente (--senza-email per darlo a
mano). Il gettone non sta mai nel repository.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import licenza  # noqa: E402
from core.provider.trasporto import TrasportoHTTP  # noqa: E402


def main(argv=None, trasporto=None) -> int:
    parser = argparse.ArgumentParser(prog="py scripts/licenze.py")
    parser.add_argument("azione", choices=["crea", "cerca", "accredita", "piano", "sospendi", "riattiva", "nuovo-codice"])
    parser.add_argument("--email")
    parser.add_argument("--licenza", help="id della licenza, se l'email ne ha piu' di una")
    parser.add_argument("--piano", choices=["prova", "base", "pro", "studio", "nessuno"])
    parser.add_argument("--mesi", type=int)
    parser.add_argument("--render", type=int)
    parser.add_argument("--rivenditore")
    parser.add_argument("--senza-email", action="store_true")
    a = parser.parse_args(argv)

    gettone = os.environ.get("AIRENDER_ADMIN_TOKEN", "").strip()
    if not gettone:
        print("Manca AIRENDER_ADMIN_TOKEN nell'ambiente (lo stesso impostato su Netlify).", file=sys.stderr)
        return 4  # numero-non-configurabile: convenzione della shell, come core/cli.py
    corpo = {k: v for k, v in {
        "azione": a.azione.replace("-", "_"), "email": a.email, "licenza": a.licenza, "piano": a.piano,
        "mesi": a.mesi, "render": a.render, "rivenditore": a.rivenditore,
        "manda_email": not a.senza_email,
    }.items() if v is not None}
    stato, _, risposta = (trasporto or TrasportoHTTP()).chiama(
        "POST", f"{licenza.server()}/api/admin",
        {"Authorization": f"Bearer {gettone}", "Content-Type": "application/json", "Accept": "application/json"},
        corpo,
    )
    print(json.dumps(risposta, ensure_ascii=False, indent=2))
    return 0 if stato < 400 else 3  # numero-non-configurabile: confine HTTP e codice d'uscita del motore


if __name__ == "__main__":
    raise SystemExit(main())
