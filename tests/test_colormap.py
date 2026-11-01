"""La color map: zone qualunque -> un colore per zona e una legenda."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from core import colormap, config
from core.errori import ErroreAirender

LATO = (200, 100)


def _maschera(scatola, dimensioni=LATO) -> bytes:
    immagine = Image.new("L", dimensioni, 0)
    ImageDraw.Draw(immagine).rectangle(scatola, fill=255)
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


def _colore(dati: bytes, punto) -> str:
    rosso, verde, blu = Image.open(io.BytesIO(dati)).convert("RGB").getpixel(punto)
    return f"#{rosso:02x}{verde:02x}{blu:02x}"


def test_la_zona_piccola_sta_sopra_la_grande():
    """Caso: la parete dipinta dopo copre la finestra e la finestra sparisce dalla mappa."""
    finestra = colormap.Zona(_maschera([80, 30, 119, 69]), "glass", "Vetro")
    parete = colormap.Zona(_maschera([0, 0, 199, 99]), "wall", "CLS")
    mappa = colormap.componi(LATO, [finestra, parete])
    assert [voce.etichetta for voce in mappa.legenda] == ["wall", "glass"]
    assert _colore(mappa.immagine, (100, 50)) == mappa.legenda[1].colore
    assert _colore(mappa.immagine, (5, 5)) == mappa.legenda[0].colore
    # L'area e' quella che si vede: la parete perde i pixel coperti dalla finestra.
    assert mappa.legenda[0].area_percento == 92.0
    assert mappa.legenda[1].area_percento == 8.0
    assert mappa.legenda[1].materiale_allplan == "Vetro"


def test_i_pixel_senza_zona_restano_neri_e_si_contano():
    mappa = colormap.componi(LATO, [colormap.Zona(_maschera([0, 0, 99, 99]), "metallo")])
    assert _colore(mappa.immagine, (150, 50)) == colormap.NON_ASSEGNATO
    assert mappa.non_assegnato_percento == 50.0


def test_le_briciole_si_scartano_e_lo_si_dice():
    briciola = colormap.Zona(_maschera([0, 0, 1, 1]), "briciola")
    grande = colormap.Zona(_maschera([0, 0, 199, 49]), "tetto")
    mappa = colormap.componi(LATO, [briciola, grande])
    assert [voce.etichetta for voce in mappa.legenda] == ["tetto"]
    assert mappa.scartate == ["briciola"]


def test_oltre_le_zone_massime_si_tengono_le_piu_grandi(monkeypatch):
    monkeypatch.setattr(config, "COLORMAP_ZONE_MASSIME", 2)
    zone = [colormap.Zona(_maschera([0, 0, larghezza, 99]), f"z{larghezza}")
            for larghezza in (20, 60, 40)]
    mappa = colormap.componi(LATO, zone)
    assert [voce.etichetta for voce in mappa.legenda] == ["z60", "z40"]
    assert mappa.scartate == ["z20"]


def test_una_zona_senza_nome_prende_un_numero():
    mappa = colormap.componi(LATO, [colormap.Zona(_maschera([0, 0, 199, 99]))])
    assert mappa.legenda[0].etichetta == "zona 1"


def test_una_maschera_di_altre_dimensioni_si_rifiuta_e_spiega():
    """Caso: la segmentazione ridimensiona la vista e le zone finiscono nel posto sbagliato."""
    with pytest.raises(ErroreAirender) as errore:
        colormap.componi(LATO, [colormap.Zona(_maschera([0, 0, 9, 9], (50, 50)), "tetto")])
    assert "50×50" in errore.value.fatto


def test_la_legenda_json_si_rilegge():
    mappa = colormap.componi(LATO, [colormap.Zona(_maschera([0, 0, 199, 99]), "parete", "CLS", "rif.jpg")])
    dati = json.loads(mappa.legenda_json())
    assert dati["zone"][0] == {"colore": colormap.TAVOLOZZA[0], "etichetta": "parete",
                               "area_percento": 100.0, "materiale_allplan": "CLS",
                               "riferimento": "rif.jpg"}
    assert dati["non_assegnato"]["area_percento"] == 0.0


def test_zone_da_immagine_colorata_una_per_colore():
    """L'uscita a colori di OneFormer o SAM2 automatico diventa zone, la piu' grande prima."""
    immagine = Image.new("RGB", LATO, (10, 20, 30))
    ImageDraw.Draw(immagine).rectangle([0, 0, 49, 99], fill=(200, 0, 0))
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    zone = colormap.zone_da_immagine_colorata(uscita.getvalue())
    assert [zona.etichetta for zona in zone] == ["zona 1", "zona 2"]
    mappa = colormap.componi(LATO, zone)
    assert [voce.area_percento for voce in mappa.legenda] == [75.0, 25.0]


def test_una_foto_non_e_una_segmentazione():
    immagine = Image.new("RGB", (40, 40))
    immagine.putdata([(i % 256, i // 7 % 256, i // 3 % 256) for i in range(1600)])
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    with pytest.raises(ErroreAirender):
        colormap.zone_da_immagine_colorata(uscita.getvalue())


@pytest.mark.parametrize("valore, nome", [
    ("'nemetschek\\\\_aspetti\\\\metallo.surf'", "metallo"),
    ("'30YearEdition Materials\\\\Outdoor floors\\\\Asphalt_01'", "Asphalt_01"),
    ("'CLS'", "CLS"),
    ("''", ""),
    (None, ""),
])
def test_nome_materiale_nelle_tre_forme_della_sonda(valore, nome):
    assert colormap.nome_materiale(valore) == nome


def test_materiali_allplan_dagli_elementi_della_sonda():
    """Gli elementi come li scrive elementi.json della sonda 2 (progetto 4253, 2026-11-01)."""
    elementi = [
        {"attributi": {}, "superficie": {"SurfacePath": "'30YearEdition Materials\\\\Outdoor floors\\\\Asphalt_01'"}},
        {"attributi": {"335 Nome_aspetto": "'nemetschek\\\\_aspetti\\\\metallo.surf'",
                       "334 Path_aspetto": "''", "508 Materiale": "'CLS'", "141 Layer": "'3816'"}},
        {"attributi": {"508 Materiale": "'CLS'"}},
        {"attributi": {"498 Nome_oggetto": "'Vano'"}},
    ]
    assert colormap.materiali_allplan(elementi) == ["Asphalt_01", "metallo", "CLS"]


def test_core_colormap_non_importa_allplan():
    testo = (Path(colormap.__file__)).read_text(encoding="utf-8")
    assert "NemAll" not in testo
