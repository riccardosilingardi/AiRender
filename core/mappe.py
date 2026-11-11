"""«Tieni la geometria»: le mappe della vista accanto alla vista, verso Nano Banana.

Le mappe le calcola la pagina dello Studio sul computer di chi lavora (sul
PC e nella web app), prima dell'invio: nessun servizio in piu' le riceve e
nessuno le fa pagare. Sono due:

- spigoli: Canny sulla vista (soglie 0,1 e 0,32, come il nodo Canny di
  ComfyUI che si usava prima);
- profondita': Depth Anything V2 Small (Apache-2.0), vicino chiaro e
  lontano scuro.

Nano Banana non ha un ingresso ControlNet: le mappe sono immagini in piu'
che il prompt chiede di seguire. Prova del 2026-11-10/11 (docs/prova-nano-
mappe-2026-11-10.md): sulle viste prospettiche ambigue la profondita' tiene
partizioni e volumi; gli spigoli da soli peggiorano. Le linee dritte (M-LSD)
non ci sono piu': servirebbe un'altra rete, e la prova le dava ininfluenti.

Partono per ultime, dopo vista, riferimenti, materiali e Rif.: cosi' i numeri
delle altre immagini nel prompt restano quelli di sempre.
"""

from __future__ import annotations

MAPPE = ("spigoli", "profondita")
NOMI = {"spigoli": "Spigoli", "profondita": "Profondità"}
SPIEGA = {
    "spigoli": "an edge map (white lines on black): every white line is a real edge of the building "
               "and must appear in the photograph at exactly the same position",
    "profondita": "a depth map (near is bright, far is dark): keep the same volumes, distances and overlaps",
}
MODELLO_PROFONDITA = "Depth Anything V2 Small (Apache-2.0)"
DOVE = ("calcolate su questo computer, partono con la vista verso lo stesso modello: "
        "nessun servizio in più")


def regola(prima: int) -> str:
    """Il testo che spiega le mappe al modello. `prima` e' il numero dell'immagine della prima mappa."""
    righe = [f"Image {prima + i} is {SPIEGA[m]} of image 1." for i, m in enumerate(MAPPE)]
    ultime = f"Images {prima}-{prima + len(MAPPE) - 1}"
    return (" ".join(righe) + " Do not add, remove, move or reshape any wall, opening, mullion, fin, slab, "
            f"column, railing or roof edge of image 1. {ultime} are construction guides only: never copy "
            "their colours or look, and never draw them into the photograph. The output is one photograph of image 1, "
            "same framing.")
