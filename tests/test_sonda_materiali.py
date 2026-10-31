"""La sonda dei materiali, provata senza Allplan.

Quello che solo Allplan puo' dire (quali metodi esistono davvero, cosa
restituiscono, com'e' fatta la color map) resta fuori. Qui si prova che la
sonda legga senza cambiare niente, non si fermi a un errore, e riassuma
giusto le immagini e i materiali trovati.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

from PIL import Image

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "allplan" / "comune"))

import sonda_materiali as sonda  # noqa: E402  pylint: disable=wrong-import-position

V2027 = RADICE / "allplan" / "v2027" / "pacchetto"
PYP = V2027 / "Library" / "AIRENDER" / "AirenderSondaMateriali.pyp"
SCRIPT = V2027 / "PythonPartsScripts" / "riccardo_silingardi" / "airender" / "AirenderSondaMateriali.py"


class Superficie:
    """Finta superficie di Allplan."""

    def GetSurfaceName(self):  # noqa: N802  pylint: disable=invalid-name
        return "Laterizio rosso"

    def GetTextureID(self):  # noqa: N802  pylint: disable=invalid-name
        return 42


class Muro:
    """Finto elemento: legge, ha un metodo che cambierebbe il modello, uno che fallisce."""

    def __init__(self):
        self.cambiato = False

    def GetDisplayName(self):  # noqa: N802  pylint: disable=invalid-name
        return "Muro"

    def GetSurface(self):  # noqa: N802  pylint: disable=invalid-name
        return Superficie()

    def SetSurface(self, *_argomenti):  # noqa: N802  pylint: disable=invalid-name
        self.cambiato = True

    def SelectAll(self):  # noqa: N802  pylint: disable=invalid-name
        self.cambiato = True

    def GetMaterial(self, _quale):  # noqa: N802  pylint: disable=invalid-name
        return "mai"

    def GetModelGeometry(self):  # noqa: N802  pylint: disable=invalid-name
        raise AssertionError("la geometria non si legge: e' pesante e non ha materiali")


def test_descrivi_legge_e_non_cambia_niente():
    """Caso: la sonda chiama un Set* o un Select* e cambia il modello di Riccardo."""
    muro = Muro()
    dati = sonda.descrivi(muro)
    assert muro.cambiato is False
    assert dati["SetSurface"].startswith("metodo (non chiamato")
    assert dati["GetDisplayName"] == "'Muro'"
    assert dati["GetSurface"]["dentro"]["GetSurfaceName"] == "'Laterizio rosso'"
    assert dati["GetSurface"]["dentro"]["GetTextureID"] == "42"
    assert dati["GetMaterial"].startswith("errore: TypeError")  # esiste, ma vuole argomenti
    assert "GetModelGeometry" not in dati


def test_valori_di_materiale_trova_superfici_anche_annidate():
    elementi = [sonda.descrivi(Muro()), {"attributi": {"508 Surface": "'Intonaco'", "120 Layer": "'AR_MURI'"}},
                {"GetSurface": "errore: AttributeError: niente"}]
    trovati = sonda.valori_di_materiale(elementi)
    assert any(v == ["'Laterizio rosso'"] for k, v in trovati.items() if k.endswith("GetSurfaceName"))
    assert trovati["attributi.508 Surface"] == ["'Intonaco'"]
    assert not any("Layer" in k for k in trovati)
    assert not any(v[0].startswith("errore") for v in trovati.values())


def test_elenca_api_tiene_solo_i_nomi_che_servono():
    class SurfaceDefinition:
        """Definizione di una superficie."""

        def GetTextureID(self):  # noqa: N802  pylint: disable=invalid-name
            """L'id della texture."""

    class Inutile:
        def Calcola(self):  # noqa: N802  pylint: disable=invalid-name
            pass

    modulo = type(sys)("finto")
    modulo.SurfaceDefinition = SurfaceDefinition
    modulo.Inutile = Inutile
    testo = sonda.elenca_api({"finto": modulo, "assente": None})
    assert "- SurfaceDefinition: Definizione di una superficie." in testo
    assert "· GetTextureID: L'id della texture." in testo
    assert "Inutile" not in testo
    assert "## assente: non importato" in testo


def test_colori_distingue_una_color_map_da_una_vista(tmp_path):
    mappa = Image.new("RGB", (40, 20), (255, 0, 0))
    mappa.paste((0, 0, 255), (0, 0, 10, 20))
    mappa.save(tmp_path / "mappa.png")
    analisi = sonda.colori(tmp_path / "mappa.png")
    assert analisi["colori_diversi"] == 2
    assert analisi["primi"][0] == {"colore": "#ff0000", "parte": 0.75}
    assert analisi["parte_coperta_dai_primi"] == 1.0
    assert "2 colori diversi" in sonda.descrivi_colori(analisi)


def test_confronta_viste_avvisa_se_le_grandezze_non_tornano():
    normale = {"larghezza": 100, "altezza": 50, "colori_diversi": 9000}
    assert "stessa grandezza" in sonda.confronta_viste(normale, {**normale, "colori_diversi": 6})
    assert "DIVERSE" in sonda.confronta_viste(normale, {**normale, "larghezza": 99})
    assert "manca" in sonda.confronta_viste(None, normale)


def test_registro_scrive_righe_e_file(tmp_path):
    registro = sonda.Registro(tmp_path / "s", adesso=lambda: datetime(2026, 11, 1, 9, 0, 0))
    riga = registro.scrivi("2 elementi", "3 elementi")
    assert riga == "[2026-11-01 09:00:00] 2 elementi · 3 elementi"
    registro.scrivi_file(sonda.FILE_ELEMENTI, sonda.json_elementi([{"a": object()}]))
    assert json.loads((tmp_path / "s" / sonda.FILE_ELEMENTI).read_text(encoding="utf-8"))[0]["a"].startswith("<")


def test_il_pyp_punta_allo_script_e_ai_suoi_eventi():
    """Caso: Allplan apre il .pyp, ma un pulsante manda un evento che lo script non conosce."""
    radice = ET.parse(PYP).getroot()
    assert radice.findtext("Script/Name") == r"riccardo_silingardi\airender\AirenderSondaMateriali.py"
    eventi = {int(e.text) for e in radice.iter("EventId")}
    testo = SCRIPT.read_text(encoding="utf-8")
    nello_script = {int(n) for n in re.findall(r"^EVENTO_\w+ = (\d+)$", testo, re.MULTILINE)}
    assert eventi == nello_script == {3001, 3002, 3003, 3004, 3005}


def test_la_sonda_non_manda_niente_in_rete():
    """Regola 5 di CLAUDE.md: nessuna immagine parte senza che l'interfaccia l'abbia detto."""
    for file in (SCRIPT, RADICE / "allplan" / "comune" / "sonda_materiali.py"):
        testo = file.read_text(encoding="utf-8")
        assert not re.search(r"urllib|http\.client|requests|socket|core\.provider", testo), file
