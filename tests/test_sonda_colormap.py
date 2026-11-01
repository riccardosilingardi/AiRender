"""La sonda della color map da Allplan: le parti senza Allplan, e il .pyp."""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "allplan" / "comune"))

import sonda_colormap as sonda  # noqa: E402  pylint: disable=wrong-import-position

V2027 = RADICE / "allplan" / "v2027" / "pacchetto"
PYP = V2027 / "Library" / "AIRENDER" / "AirenderSondaColormap.pyp"
SCRIPT = V2027 / "PythonPartsScripts" / "riccardo_silingardi" / "airender" / "AirenderSondaColormap.py"

# Le tre forme lette dalla sonda 2 sul progetto 4253 (2026-11-01).
SOLIDO = {"GetDisplayName": "Solido 3D", "attributi": {},
          "superficie": {"SurfacePath": "30YearEdition Materials\\Outdoor floors\\Asphalt_01"}}
MURO = {"GetDisplayName": "Strato parete", "attributi": {"335 Nome_aspetto": "nemetschek\\_aspetti\\metallo.surf",
                                                         "508 Materiale": "Acciaio"}, "superficie": {}}
PILASTRO = {"GetDisplayName": "Pilastro", "attributi": {"508 Materiale": "CLS"}, "superficie": {}}
FACCIATA = {"GetDisplayName": "Facciata", "attributi": {}, "superficie": {}}


def test_il_materiale_si_prende_nell_ordine_della_sonda_2():
    assert sonda.materiale_di(SOLIDO) == (
        "Asphalt_01", "30YearEdition Materials\\Outdoor floors\\Asphalt_01", "SurfacePath")
    assert sonda.materiale_di(MURO)[0::2] == ("metallo", "335")
    assert sonda.materiale_di(PILASTRO)[0::2] == ("CLS", "508")
    assert sonda.materiale_di(FACCIATA)[0] == sonda.SENZA_MATERIALE


def test_un_gruppo_per_materiale_il_piu_frequente_prende_il_primo_colore():
    gruppi = sonda.raggruppa([MURO, PILASTRO, MURO, FACCIATA, SOLIDO])
    assert [(g.materiale, g.indici) for g in gruppi] == [
        ("metallo", [0, 2]), ("Asphalt_01", [4]), ("CLS", [1])]
    assert [g.colore for g in gruppi] == list(sonda.TAVOLOZZA[:3])
    assert sonda.senza_materiale([MURO, FACCIATA, FACCIATA]) == ["Facciata 2"]


def test_oltre_la_tavolozza_un_materiale_resta_senza_colore():
    letti = [{"GetDisplayName": "x", "attributi": {"508 Materiale": f"m{i:02d}"}, "superficie": {}}
             for i in range(len(sonda.TAVOLOZZA) + 1)]
    gruppi = sonda.raggruppa(letti)
    assert gruppi[-1].colore == ""


def test_i_gruppi_si_rileggono_dal_file_di_ripristino():
    gruppi = sonda.raggruppa([MURO, SOLIDO])
    gruppi[0].superficie_nuova = "C:\\superfici\\airender_colormap_01.surf"
    assert sonda.gruppi_da_json(sonda.json_gruppi(gruppi)) == gruppi


def test_quanta_immagine_e_vicina_ai_colori_chiesti(tmp_path):
    rosso, verde = sonda.TAVOLOZZA[0], sonda.TAVOLOZZA[1]
    immagine = Image.new("RGB", (10, 10), (128, 128, 128))
    for x in range(5):
        for y in range(10):
            immagine.putpixel((x, y), tuple(c - 10 for c in sonda.rgb(rosso)))  # rosso un po' in ombra
    percorso = tmp_path / "colormap.png"
    immagine.save(percorso)

    analisi = sonda.vicini_alla_tavolozza(percorso, [rosso, verde])

    assert analisi["parte_vicina"] == 0.5
    assert analisi["vicini"] == [{"colore": rosso, "parte": 0.5}, {"colore": verde, "parte": 0.0}]
    legenda = json.loads(sonda.legenda(sonda.raggruppa([MURO, MURO, SOLIDO]), analisi))
    assert legenda["zone"][0] == {"colore": rosso, "materiale_allplan": "metallo", "da": "335",
                                  "elementi": 2, "parte_immagine": 0.5}


def test_il_pyp_ha_la_casella_della_copia_e_i_sei_pulsanti_dello_script():
    radice = ET.parse(PYP).getroot()
    assert radice.findtext("Script/Name") == "riccardo_silingardi\\airender\\AirenderSondaColormap.py"
    parametri = {p.findtext("Name"): p for p in radice.iter("Parameter")}
    assert parametri["Copia"].findtext("ValueType") == "CheckBox"
    assert parametri["Copia"].findtext("Value") == "False"
    eventi = sorted(int(p.findtext("EventId")) for p in parametri.values() if p.findtext("EventId"))
    testo = SCRIPT.read_text(encoding="utf-8")
    assert eventi == list(range(3101, 3107))
    for evento in eventi:
        assert f"= {evento}" in testo


def test_la_logica_della_sonda_non_importa_allplan():
    testo = (RADICE / "allplan" / "comune" / "sonda_colormap.py").read_text(encoding="utf-8")
    assert "NemAll_Python" not in testo
