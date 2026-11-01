"""Lo script di prova della color map con Nano Banana, con un motore finto."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

from core.provider.base import Risultato

RADICE = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("prova_colormap", RADICE / "scripts" / "prova_colormap.py")
prova = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prova)


def _png(immagine: Image.Image) -> bytes:
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


class MotoreFinto:
    nome = "finto"

    def __init__(self):
        self.richieste = []

    def destinazione_per(self, modello):
        return f"servizio finto ({modello})"

    def genera(self, richiesta):
        self.richieste.append(richiesta)
        resa = Image.new("RGB", (60, 30), (0, 0, 0))
        ImageDraw.Draw(resa).rectangle((0, 0, 29, 29), fill=(230, 25, 75))
        return Risultato(immagine=_png(resa), formato="png", ricetta=None,
                         scostamento_geometria=None, avvisi=[])


def _vista(tmp_path) -> Path:
    vista = Image.new("RGB", (120, 60), (200, 200, 200))
    ImageDraw.Draw(vista).rectangle((10, 10, 50, 50), fill=(90, 90, 90))
    percorso = tmp_path / "vista.png"
    vista.save(percorso)
    return percorso


def test_a_secco_dice_dove_va_e_non_invia(tmp_path):
    motore, righe = MotoreFinto(), []
    argomenti = prova.costruisci_parser().parse_args(["--immagine", str(_vista(tmp_path)), "--prova-a-secco"])
    assert prova.esegui(argomenti, dire=righe.append, crea_motore=lambda: motore) == 0
    assert motore.richieste == []
    assert any("servizio finto" in riga for riga in righe)
    assert any("metal cladding" in riga and "metallo" in riga for riga in righe)


def test_lascia_grezza_colormap_legenda_e_spigoli(tmp_path):
    motore = MotoreFinto()
    argomenti = prova.costruisci_parser().parse_args(
        ["--immagine", str(_vista(tmp_path)), "--zona", "metal cladding=metallo", "--zona", "glass"])
    assert prova.esegui(argomenti, dire=lambda _: None, crea_motore=lambda: motore) == 0

    assert "#E6194B" in motore.richieste[0].prompt
    for nome in ("grezza.png", ".png", ".json", "spigoli.png"):
        assert (tmp_path / f"vista-colormap{'-' if nome[0] != '.' else ''}{nome}").exists()
    assert Image.open(tmp_path / "vista-colormap.png").size == (120, 60)
    legenda = json.loads((tmp_path / "vista-colormap.json").read_text(encoding="utf-8"))
    assert legenda["zone"][0]["materiale_allplan"] == "metallo"
    assert legenda["zone"][0]["area_percento"] == 50.0
    assert legenda["scartate"] == ["glass"]
