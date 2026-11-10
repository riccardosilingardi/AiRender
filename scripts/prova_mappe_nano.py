"""Nano Banana con le mappe del ControlNet accanto alla vista: tiene meglio la geometria?

    py scripts\\prova_mappe_nano.py --immagine vista.png
    py scripts\\prova_mappe_nano.py --immagine vista.png --prova-a-secco

Una prova, non una funzione del prodotto. Fa tre cose:

1. Chiede al deployment di «Tieni la geometria» (AIRENDER_COMFY_WORKFLOW_URL)
   solo le tre mappe della vista: spigoli (Canny), profondita' (Depth
   Anything V2), linee dritte (M-LSD). Nessun render, pochi secondi di GPU.
2. Manda a Nano Banana 2 (vertexai/gemini-3.1-flash-image, Comfy Router) la
   stessa vista tre volte, collo stesso seme:
     A  solo la vista, prompt del preset;
     B  vista + mappa degli spigoli, prompt che spiega la mappa;
     C  vista + le tre mappe, prompt che spiega le tre mappe.
3. Salva le mappe, i tre render e un confronto affiancato, e misura gli
   spigoli ritrovati di ogni render contro la vista.

Nano Banana non ha un ingresso ControlNet: le mappe sono solo immagini in
piu' che il prompt chiede di seguire. Se le segue, e quanto, lo dice solo
questa prova. La % di spigoli da sola inganna (prova del 2026-11-10): va
guardato anche il confronto, spigolo per spigolo.

Costo: tre lavori brevi sul deployment e tre render di Nano Banana 2.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import blocchi, coda, config, immagine as modulo_immagine  # noqa: E402
from core.errori import ErroreAirender  # noqa: E402
from core.provider import geometria as g  # noqa: E402
from core.provider.base import RichiestaGenerazione  # noqa: E402
from core.provider.comfy import ProviderComfy  # noqa: E402
from core.provider.trasporto import TrasportoHTTP  # noqa: E402

MODELLO = "vertexai/gemini-3.1-flash-image"
SEME = 42
MAPPE = ("spigoli", "profondita", "linee")
NODO_SALVA = "90"

SPIEGA = {
    "spigoli": "an edge map (white lines on black): every white line is a real edge of the building "
               "and must appear in the photograph at exactly the same position",
    "profondita": "a depth map (near is bright, far is dark): keep the same volumes, distances and overlaps",
    "linee": "a straight-line map: these lines stay straight, parallel and exactly where they are",
}


def prompt_con_mappe(mappe: tuple[str, ...], prompt_preset: str) -> str:
    """Il prompt dedicato: cosa e' ogni immagine, poi il prompt del preset."""
    righe = [f"You receive {len(mappe) + 1} images of the same view. "
             "Image 1 is the architectural view exported from CAD: it fixes the camera, the framing "
             "and every building element."]
    for numero, mappa in enumerate(mappe, start=2):
        righe.append(f"Image {numero} is {SPIEGA[mappa]}.")
    ultime = "images 2" if len(mappe) == 1 else f"images 2-{len(mappe) + 1}"
    righe.append(
        "Do not add, remove, move or reshape any wall, opening, mullion, fin, slab, column, railing or "
        f"roof edge. {ultime.capitalize()} are construction guides only: never copy their colours or look. "
        "The output is one photograph of image 1, same size and same framing.")
    return " ".join(righe) + "\n\n" + prompt_preset


def grafo_mappa(asset: str, mappa: str) -> dict:
    """Solo vista → misura → preprocessore → salva: nessun modello di diffusione."""
    intero = json.loads(g.WORKFLOW.read_text(encoding="utf-8"))
    preprocessore = g.NODI_CONTROLLO[mappa][0]
    grafo = {n: copy.deepcopy(intero[n]) for n in (g.NODO_IMMAGINE, g.NODO_LATO, preprocessore)}
    grafo[g.NODO_IMMAGINE]["inputs"]["image"] = {"__type": "core/ASSET", "info": {"id": asset}}
    grafo[g.NODO_LATO]["inputs"]["largest_size"] = config.GEOMETRIA_LATO_MASSIMO
    grafo[NODO_SALVA] = {"class_type": "SaveImage",
                         "inputs": {"images": [preprocessore, 0], "filename_prefix": f"airender-mappa-{mappa}"}}
    return grafo


def mappe_dal_deployment(vista: bytes, base: str, dire=print) -> dict[str, bytes]:
    cliente = g.Geometria(TrasportoHTTP(), base=base)
    originale = g.workflow
    uscita = {}
    try:
        for mappa in MAPPE:
            g.workflow = lambda asset, *_a, _m=mappa, **_k: grafo_mappa(asset, _m)
            uscita[mappa], lavoro = cliente.esegui(vista, "", SEME, (mappa,))
            dire(f"Mappa {mappa}: fatta (lavoro {lavoro}).")
    finally:
        g.workflow = originale
    return uscita


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="py scripts\\prova_mappe_nano.py", description=__doc__.splitlines()[0])
    parser.add_argument("--immagine", required=True, help="la vista salvata da Allplan")
    parser.add_argument("--preset", default="rivista", help="lo stile (blocchi), uguale per i tre render")
    parser.add_argument("--uscita", help="cartella dei risultati (predefinita: <vista>-mappe accanto alla vista)")
    parser.add_argument("--prova-a-secco", action="store_true", dest="secco",
                        help="scrive i prompt e dice dove andrebbero gli invii, senza inviare niente")
    parser.add_argument("--deployment", default=os.environ.get(g.VARIABILE_URL, ""),
                        help=f"indirizzo del deployment (predefinito: la variabile {g.VARIABILE_URL})")
    argomenti = parser.parse_args(argv)

    sorgente = Path(argomenti.immagine)
    vista = modulo_immagine.leggi(sorgente)
    cartella = Path(argomenti.uscita) if argomenti.uscita else sorgente.with_name(sorgente.stem + "-mappe")
    cartella.mkdir(parents=True, exist_ok=True)
    preset = blocchi.componi(blocchi.da_preset(argomenti.preset))
    varianti = (("A-solo-vista", ()), ("B-spigoli", ("spigoli",)), ("C-tre-mappe", MAPPE))
    for nome, mappe in varianti:
        (cartella / f"prompt-{nome}.txt").write_text(
            prompt_con_mappe(mappe, preset) if mappe else preset, encoding="utf-8")

    print("Dove vanno le immagini:")
    print(f"  le mappe: il deployment Comfy Developer Platform ({argomenti.deployment or g.VARIABILE_URL + ' non impostato'})")
    print(f"  i render: Comfy Router → {MODELLO} (Google Vertex AI), tre invii")
    if argomenti.secco:
        print(f"Prova a secco: prompt scritti in {cartella}, niente inviato.")
        return 0

    try:
        mappe = mappe_dal_deployment(vista, argomenti.deployment)
    except ErroreAirender as errore:
        print(f"Le mappe non sono arrivate:\n{errore}", file=sys.stderr)
        return 1
    for mappa, dati in mappe.items():
        (cartella / f"mappa-{mappa}.png").write_bytes(dati)

    motore = ProviderComfy()
    pannelli = [("Vista", vista)]
    righe = []
    for nome, scelte in varianti:
        richiesta = RichiestaGenerazione(
            immagine=vista, prompt=(cartella / f"prompt-{nome}.txt").read_text(encoding="utf-8"),
            preset=argomenti.preset, preset_versione="prova-mappe", modello=MODELLO,
            grana="", dettaglio_grana=0, seme=SEME,
            immagini_in_piu=tuple(mappe[m] for m in scelte))
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
