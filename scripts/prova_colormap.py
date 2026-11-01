"""Prova della color map con Nano Banana: la vista ridipinta a colori piatti, un colore per materiale.

    py scripts\\prova_colormap.py --immagine vista-normale.png --prova-a-secco
    py scripts\\prova_colormap.py --immagine vista-normale.png
    py scripts\\prova_colormap.py --immagine vista.png --zona "metal cladding=metallo" --zona "glass="

Serve a capire se un modello d'immagine, senza segmentazione, sa fare da se'
la color map della mappa materiali (piano: /mnt/project-files/prompt/color-map-piano.md).
I workflow di segmentazione su Comfy Cloud (SAM3) chiedono l'abbonamento;
Nano Banana via Comfy Router no, ed e' gia' la strada dei render.

Ogni --zona e' «parola inglese=materiale Allplan»: la parola va nel prompt,
il materiale nella legenda. Senza --zona si usano i materiali che la sonda 2
ha letto sul progetto 4253 (metallo, CLS, Asphalt_01) piu' il vetro.

Lascia accanto alla vista:
- <vista>-colormap-grezza.png   quello che ha reso il modello;
- <vista>-colormap.png          le zone pulite da core/colormap.py;
- <vista>-colormap.json         la legenda (colore, area, materiale Allplan);
- <vista>-colormap-spigoli.png  la color map con sopra gli spigoli della vista,
                                per vedere a occhio se il modello li ha spostati.

E' un invio a pagamento (come un render). Prima che parta, si dice dove va.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from PIL import Image, ImageFilter  # noqa: E402

from core import colormap, immagine as modulo_immagine  # noqa: E402
from core.cli import USCITA_OK, USCITA_PROVIDER, _annuncia_destinazione  # noqa: E402
from core.errori import ErroreAirender  # noqa: E402
from core.provider.base import RichiestaGenerazione  # noqa: E402
from core.provider.comfy import ProviderComfy  # noqa: E402

MODELLO = "vertexai/gemini-3.1-flash-image"

# I materiali letti dalla sonda 2 sul progetto 4253 (2026-11-01), con la
# parola inglese che li descrive in una vista. Il vetro non e' un materiale
# letto: le aperture non hanno dato un nome.
ZONE_4253 = (
    ("metal cladding", "metallo"),
    ("asphalt", "Asphalt_01"),
    ("concrete", "CLS"),
    ("glass", ""),
)  # in quest'ordine prendono rosso, verde, giallo e blu dalla tavolozza


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/prova_colormap.py",
        description="La vista ridipinta da Nano Banana a colori piatti, poi pulita in zone.",
    )
    parser.add_argument("--immagine", required=True, help="la vista salvata da Allplan")
    parser.add_argument("--zona", action="append", default=[], metavar="PAROLA=MATERIALE",
                        help="una zona: parola inglese per il modello = materiale Allplan (ripetibile)")
    parser.add_argument("--modello", default=MODELLO, help="ID del Router")
    parser.add_argument("--uscita", help="cartella dei risultati (predefinita: quella della vista)")
    parser.add_argument("--prova-a-secco", action="store_true", dest="secco",
                        help="mostra prompt e destinazione e si ferma")
    return parser


def richiesti(zone: list[str]) -> list[colormap.ColoreRichiesto]:
    coppie = [tuple(voce.split("=", 1)) if "=" in voce else (voce, "") for voce in zone] or ZONE_4253
    return [colormap.ColoreRichiesto(colore=colore, etichetta=parola.strip(), materiale_allplan=materiale.strip())
            for colore, (parola, materiale) in zip(colormap.TAVOLOZZA, coppie)]


def prompt_colori_piatti(voci: list[colormap.ColoreRichiesto]) -> str:
    righe = [f"- {voce.etichetta}: pure flat {voce.colore.upper()}" for voce in voci]
    return (
        "Convert this architectural view into a flat-color segmentation map. "
        "Keep exactly the same framing, perspective, geometry and edges: do not "
        "move, add or remove anything. Paint every surface with ONE solid flat "
        "color, with no shading, shadows, texture, gradients, outlines or lighting:\n"
        + "\n".join(righe)
        + f"\n- sky, background and anything else: pure flat {colormap.NON_ASSEGNATO}\n"
        "Output only the flat-color map, same size as the input."
    )


def spigoli_sopra(vista: bytes, mappa: bytes) -> bytes:
    """La color map con gli spigoli della vista in bianco: se combaciano, il modello non li ha spostati."""
    base = Image.open(io.BytesIO(vista)).convert("L")
    sotto = Image.open(io.BytesIO(mappa)).convert("RGB")
    spigoli = base.filter(ImageFilter.FIND_EDGES).point(lambda v: 255 if v >= 48 else 0)  # numero-non-configurabile: soglia a occhio per uno strumento di prova
    sotto.paste((255, 255, 255), (0, 0), spigoli)
    uscita = io.BytesIO()
    sotto.save(uscita, format="PNG")
    return uscita.getvalue()


def esegui(argomenti, dire=print, crea_motore=ProviderComfy) -> int:
    sorgente = Path(argomenti.immagine)
    dati = modulo_immagine.leggi(sorgente)
    dimensioni = modulo_immagine.dimensioni(dati)
    voci = richiesti(argomenti.zona)
    prompt = prompt_colori_piatti(voci)
    motore = crea_motore()

    dire(f"Vista: {dimensioni[0]}x{dimensioni[1]} px. Zone chieste:")
    for voce in voci:
        dire(f"  {voce.colore}  {voce.etichetta}  (Allplan: {voce.materiale_allplan or 'non letto'})")
    _annuncia_destinazione(motore, argomenti.modello, dire)
    if argomenti.secco:
        dire("Prompt:\n" + prompt)
        dire("Prova a secco: non ho inviato niente.")
        return USCITA_OK

    try:
        risultato = motore.genera(RichiestaGenerazione(
            immagine=dati, prompt=prompt, preset="prova-colormap", preset_versione="1",
            modello=argomenti.modello, grana="", dettaglio_grana=0, testo_utente=""))
    except ErroreAirender as errore:
        dire(f"Non riuscito.\n{errore}")
        return USCITA_PROVIDER

    cartella = Path(argomenti.uscita) if argomenti.uscita else sorgente.parent
    cartella.mkdir(parents=True, exist_ok=True)
    radice = cartella / sorgente.stem
    grezza = Path(f"{radice}-colormap-grezza.png")
    Image.open(io.BytesIO(risultato.immagine)).save(grezza)
    mappa = colormap.componi(dimensioni, colormap.zone_da_colori_richiesti(risultato.immagine, voci, dimensioni))
    Path(f"{radice}-colormap.png").write_bytes(mappa.immagine)
    Path(f"{radice}-colormap.json").write_text(mappa.legenda_json(), encoding="utf-8")
    Path(f"{radice}-colormap-spigoli.png").write_bytes(spigoli_sopra(dati, mappa.immagine))

    dire(f"Il modello ha reso {Image.open(io.BytesIO(risultato.immagine)).size[0]}x"
         f"{Image.open(io.BytesIO(risultato.immagine)).size[1]} px.")
    for voce in mappa.legenda:
        dire(f"  {voce.colore}  {voce.etichetta}: {voce.area_percento}% "
             f"(Allplan: {voce.materiale_allplan or 'non letto'})")
    for etichetta in mappa.scartate:
        dire(f"  {etichetta}: scartata, troppo piccola o assente")
    dire(f"  non assegnato: {mappa.non_assegnato_percento}%")
    dire("Scostamento della geometria: non misurato. Guarda -colormap-spigoli.png.")
    dire(f"File in {cartella}")
    return USCITA_OK


def main(argv: list[str] | None = None) -> int:
    return esegui(costruisci_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
