"""La sonda dell'elenco materiali: le parti senza Allplan, e il .pyp."""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "allplan" / "comune"))

import sonda_elenco as sonda  # noqa: E402  pylint: disable=wrong-import-position

V2027 = RADICE / "allplan" / "v2027" / "pacchetto"
PYP = V2027 / "Library" / "AIRENDER" / "AirenderSondaElenco.pyp"
SCRIPT = V2027 / "PythonPartsScripts" / "riccardo_silingardi" / "airender" / "AirenderSondaElenco.py"

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


def test_una_riga_per_materiale_la_piu_frequente_per_prima():
    materiali = sonda.elenca([MURO, PILASTRO, MURO, FACCIATA, SOLIDO])
    assert [(m.materiale, m.elementi) for m in materiali] == [("metallo", 2), ("Asphalt_01", 1), ("CLS", 1)]
    assert [m.colore for m in materiali] == list(sonda.TAVOLOZZA[:3])
    assert sonda.senza_materiale([MURO, FACCIATA, FACCIATA]) == ["Facciata 2"]
    righe = json.loads(sonda.json_materiali(materiali))
    assert righe[0]["valore"] == "nemetschek\\_aspetti\\metallo.surf"
    assert sonda.riassunto(materiali) == "3 materiali, 0 con il file .surf trovato, 0 con il campione"


def test_il_surf_si_cerca_nelle_cartelle_di_allplan(tmp_path):
    std = tmp_path / "Std"
    atteso = std / "design" / "30YearEdition Materials" / "Outdoor floors" / "Asphalt_01.surf"
    candidati = sonda.candidati_surf("30YearEdition Materials\\Outdoor floors\\Asphalt_01", [tmp_path / "Prj", std])
    assert atteso in candidati
    assert candidati.index(atteso) > 0  # il progetto viene prima
    assert sonda.candidati_surf("C:\\Allplan\\a.surf", [std]) == [Path("C:\\", "Allplan", "a.surf")]
    assert sonda.candidati_surf("", [std]) == []


def test_le_texture_nominate_nel_surf_in_ogni_codifica():
    testo = 'Bitmap="ruggine\\corten_01.JPG" Bump=corten_bump.png Bitmap="ruggine\\corten_01.JPG"'
    assert sonda.texture_nel_surf(testo) == ["ruggine\\corten_01.JPG", "corten_bump.png"]
    assert sonda.texture_nel_surf(sonda.testo_surf(testo.encode("utf-16"))) == [
        "ruggine\\corten_01.JPG", "corten_bump.png"]
    assert sonda.texture_nel_surf("nessuna immagine") == []


def test_il_campione_e_un_quadrato_dalla_texture_o_dal_colore(tmp_path):
    texture = tmp_path / "t.png"
    Image.new("RGB", (400, 200), "#336699").save(texture)
    sonda.campione_da_texture(texture, tmp_path / "c" / "01.png", lato=64)
    with Image.open(tmp_path / "c" / "01.png") as campione:
        assert campione.size == (64, 64)
        assert campione.getpixel((10, 10)) == (0x33, 0x66, 0x99)
    sonda.campione_da_colore(sonda.esadecimale(255, 0, 16), tmp_path / "c" / "02.png", lato=8)
    with Image.open(tmp_path / "c" / "02.png") as campione:
        assert campione.getpixel((0, 0)) == (255, 0, 16)
    assert sonda.nome_file(0, "Intonaco bianco/esterno", ".png") == "01-Intonaco_bianco_esterno.png"


def test_il_pyp_ha_i_due_pulsanti_dello_script():
    radice = ET.parse(PYP).getroot()
    assert radice.findtext("Script/Name") == "riccardo_silingardi\\airender\\AirenderSondaElenco.py"
    parametri = {p.findtext("Name"): p for p in radice.iter("Parameter")}
    eventi = sorted(int(p.findtext("EventId")) for p in parametri.values() if p.findtext("EventId"))
    testo = SCRIPT.read_text(encoding="utf-8")
    assert eventi == [3201, 3202]
    for evento in eventi:
        assert f"= {evento}" in testo


def test_la_sonda_non_cambia_niente_in_allplan():
    """Regola di Riccardo del 2026-11-02: solo lettura."""
    testo = SCRIPT.read_text(encoding="utf-8")
    for scrittura in ("ModifySurface", "CreateSurface", "ModifyElements", "CreateElements",
                      "SetAttributes", "DeleteElements", "SetTextureID"):
        assert not re.search(rf"\b{scrittura}\(", testo), scrittura


def test_la_logica_della_sonda_non_importa_allplan():
    testo = (RADICE / "allplan" / "comune" / "sonda_elenco.py").read_text(encoding="utf-8")
    assert "NemAll_Python" not in testo
