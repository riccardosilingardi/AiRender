"""Mette un render del banco di prova come miniatura vera del suo preset.

    python scripts/miniatura_da_banco.py --render C:\\AIRENDER\\vista-banco-preset-20261029-101500\\ora-blu.png

Il render deve venire dal piano «preset» del banco: e' il preset com'e',
senza cambi, ed e' l'unico che una miniatura puo' promettere. Il comando lo
ritaglia alle proporzioni della tessera e lo scrive in core/studio/miniature/;
nello Studio la tessera mostra il render e sotto «render vero del <data>».

La miniatura finisce nel repository: usa una vista che puoi mostrare a tutti,
non quella di un cliente sotto NDA.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import banco, immagine as modulo_immagine  # noqa: E402
from core.cli import USCITA_OK, USCITA_RIFIUTO  # noqa: E402
from core.errori import ErroreAirender  # noqa: E402
from core.studio import miniature  # noqa: E402


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/miniatura_da_banco.py",
        description="Un render del piano preset del banco diventa la miniatura vera del suo preset.",
    )
    parser.add_argument("--render", required=True, help="un render dentro la cartella di un banco")
    return parser


def esegui(argomenti, dire=print, cartella_miniature: Path = miniature.CARTELLA) -> int:
    render = Path(argomenti.render)
    dati = banco.leggi_banco(render.parent)
    voce = next((v for v in dati["invii"] if v.get("render") == render.name), None)
    if voce is None:
        raise banco.PianoNonValido(
            f"{render.name} non e' un render di questo banco ({render.parent}).",
            "Scegli uno dei render elencati in banco.html.",
        )
    if dati["piano"] != "preset" or not voce.get("preset"):
        raise banco.PianoNonValido(
            f"{render.name} viene dal piano «{dati['piano']}»: non e' il preset com'e'.",
            "Le miniature vengono solo dal piano preset: python scripts/prova_blocchi.py "
            "--immagine vista.png --piano preset.",
        )
    try:
        creato = datetime.fromisoformat(dati["creato_il"]).date()
    except (KeyError, ValueError):
        creato = date.today()
    file = miniature.metti(
        voce["preset"], modulo_immagine.leggi(render),
        modello=dati["modello"], origine=f"{render.parent.name}/{render.name}", quando=creato,
        cartella=cartella_miniature,
    )
    dire(f"Miniatura del preset {voce['preset']} in {file}, render vero del {creato:%d/%m/%Y}.")
    dire("Attenzione: questo file entra nel repository. Se la vista e' di un cliente, non fare il commit.")
    return USCITA_OK


def main(argv: list[str] | None = None) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    try:
        return esegui(argomenti)
    except ErroreAirender as errore:
        print(str(errore), file=sys.stderr)
        return USCITA_RIFIUTO


if __name__ == "__main__":
    raise SystemExit(main())
