"""Nano Banana con le mappe accanto alla vista: tiene meglio la geometria?

    py scripts\\prova_mappe_nano.py --immagine vista.png --spigoli s.png --profondita p.png
    py scripts\\prova_mappe_nano.py --immagine vista.png --spigoli s.png --profondita p.png --prova-a-secco

Una prova, non una funzione del prodotto. Le mappe sono quelle che calcola
lo Studio (core/mappe.py): si salvano dalla pagina o da qualunque altro
strumento. Manda a Nano Banana 2 (Comfy Router) la stessa vista due volte:

  A  solo la vista, prompt del preset;
  B  vista + spigoli + profondita', col prompt di «Tieni la geometria».

Salva i due render e un confronto affiancato, e misura gli spigoli ritrovati
di ogni render contro la vista. La % da sola inganna (prova del 2026-11-10):
va guardato anche il confronto, spigolo per spigolo.

Costo: due render di Nano Banana 2.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import blocchi, coda, immagine as modulo_immagine, mappe as modulo_mappe  # noqa: E402
from core.errori import ErroreAirender  # noqa: E402
from core.provider.base import RichiestaGenerazione  # noqa: E402
from core.provider.comfy import ProviderComfy  # noqa: E402

MODELLO = "vertexai/gemini-3.1-flash-image"
SEME = 42


def prompt_con_mappe(prompt_preset: str) -> str:
    """Il prompt della variante B: quello del preset, poi la regola delle mappe (immagini 2 e 3)."""
    return f"{prompt_preset}\n\n{modulo_mappe.regola(2)}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="py scripts\\prova_mappe_nano.py", description=__doc__.splitlines()[0])
    parser.add_argument("--immagine", required=True, help="la vista salvata da Allplan")
    parser.add_argument("--spigoli", required=True, help="la mappa degli spigoli della vista")
    parser.add_argument("--profondita", required=True, help="la mappa di profondita' della vista")
    parser.add_argument("--preset", default="rivista", help="lo stile (blocchi), uguale per i due render")
    parser.add_argument("--uscita", help="cartella dei risultati (predefinita: <vista>-mappe accanto alla vista)")
    parser.add_argument("--prova-a-secco", action="store_true", dest="secco",
                        help="scrive i prompt e dice dove andrebbero gli invii, senza inviare niente")
    argomenti = parser.parse_args(argv)

    sorgente = Path(argomenti.immagine)
    vista = modulo_immagine.leggi(sorgente)
    mappe = tuple(modulo_immagine.leggi(Path(p)) for p in (argomenti.spigoli, argomenti.profondita))
    cartella = Path(argomenti.uscita) if argomenti.uscita else sorgente.with_name(sorgente.stem + "-mappe")
    cartella.mkdir(parents=True, exist_ok=True)
    preset = blocchi.componi(blocchi.da_preset(argomenti.preset))
    varianti = (("A-solo-vista", preset, ()), ("B-con-mappe", prompt_con_mappe(preset), mappe))
    for nome, prompt, _ in varianti:
        (cartella / f"prompt-{nome}.txt").write_text(prompt, encoding="utf-8")

    print(f"Dove vanno le immagini: Comfy Router → {MODELLO} (Google Vertex AI), due invii.")
    if argomenti.secco:
        print(f"Prova a secco: prompt scritti in {cartella}, niente inviato.")
        return 0

    motore = ProviderComfy()
    pannelli, righe = [("Vista", vista)], []
    for nome, prompt, in_piu in varianti:
        richiesta = RichiestaGenerazione(
            immagine=vista, prompt=prompt, preset=argomenti.preset, preset_versione="prova-mappe",
            modello=MODELLO, grana="", dettaglio_grana=0, seme=SEME, immagini_in_piu=in_piu)
        try:
            risultato = motore.genera(richiesta)
        except ErroreAirender as errore:
            print(f"{nome}: non riuscito.\n{errore}", file=sys.stderr)
            continue
        file = cartella / f"render-{nome}.{risultato.formato}"
        file.write_bytes(risultato.immagine)
        misura = coda.misura_tenuta(sorgente, file)
        quota = "non misurato" if misura["spigoli"] is None else f"{misura['spigoli']:.0%} degli spigoli ritrovati"
        righe.append(f"{nome}: {quota}" + (f" ({misura['motivo']})" if misura["motivo"] else ""))
        pannelli.append((f"{nome} · {quota}", risultato.immagine))

    if len(pannelli) > 1:
        (cartella / "confronto.png").write_bytes(modulo_immagine.affianca(pannelli))
    print("\n".join(righe))
    print(f"Tutto in {cartella}. Guarda il confronto: lamelle, montanti, bordi dei solai, aperture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
