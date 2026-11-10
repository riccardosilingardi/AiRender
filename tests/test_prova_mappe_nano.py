"""Lo script di prova Nano Banana + mappe: prompt e grafo, senza inviare niente."""

import importlib.util
from pathlib import Path

from core.provider import geometria as g

_spec = importlib.util.spec_from_file_location(
    "prova_mappe_nano", Path(__file__).resolve().parent.parent / "scripts" / "prova_mappe_nano.py")
prova = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prova)


def test_il_prompt_numera_una_immagine_per_mappa_dopo_la_vista():
    testo = prova.prompt_con_mappe(prova.MAPPE, "PRESET")
    assert testo.startswith("You receive 4 images")
    assert "Image 2 is an edge map" in testo and "Image 3 is a depth map" in testo
    assert "Image 4 is a straight-line map" in testo
    assert testo.endswith("PRESET")


def test_il_grafo_di_una_mappa_non_ha_il_modello_di_diffusione():
    for mappa in prova.MAPPE:
        grafo = prova.grafo_mappa("asset-1", mappa)
        assert set(grafo) == {g.NODO_IMMAGINE, g.NODO_LATO, g.NODI_CONTROLLO[mappa][0], prova.NODO_SALVA}
        assert grafo[prova.NODO_SALVA]["inputs"]["images"] == [g.NODI_CONTROLLO[mappa][0], 0]
        assert grafo[g.NODO_IMMAGINE]["inputs"]["image"]["info"]["id"] == "asset-1"
