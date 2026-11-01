"""La palette v1 per Allplan 2026: il .pyp generato e l'adattatore che lo legge.

Allplan non c'e' qui: si controlla che i pezzi combacino (nomi dei campi,
eventi, file copiati dall'installazione), non che Allplan li mostri.
"""

from __future__ import annotations

import ast
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RADICE = Path(__file__).resolve().parents[1]
V2026 = RADICE / "allplan" / "v2026"
PYP = V2026 / "Library" / "AIRENDER" / "AirenderPalette.pyp"
ADATTATORE = V2026 / "PythonPartsScripts" / "airender" / "AirenderPalette.py"

sys.path.insert(0, str(V2026))

import scrivi_palette_pyp  # noqa: E402  pylint: disable=wrong-import-position


def _parametri() -> dict[str, ET.Element]:
    return {p.findtext("Name"): p for p in ET.parse(PYP).getroot().iter("Parameter")}


def test_il_pyp_nel_repository_e_quello_generato():
    """Caso: si cambia un nome in core/blocchi.py e la palette offre ancora quello vecchio."""
    assert PYP.read_text(encoding="utf-8") == scrivi_palette_pyp.pyp(), (
        "rilancia: python allplan/v2026/scrivi_palette_pyp.py"
    )


def test_ogni_campo_che_l_adattatore_usa_esiste_nel_pyp():
    """Caso: un nome sbagliato nell'adattatore, e la palette si chiude con un AttributeError in Allplan."""
    usati = set(re.findall(r"(?:build_ele|\be)\.([A-Z][A-Za-z0-9]+)\.value", ADATTATORE.read_text(encoding="utf-8")))
    assert usati, "l'adattatore non legge nessun campo?"
    mancanti = sorted(usati - set(_parametri()))
    assert not mancanti, f"campi usati da AirenderPalette.py ma non nel .pyp: {mancanti}"


def test_gli_eventi_dei_pulsanti_sono_quelli_dell_adattatore():
    """Caso: Genera manda l'evento di Annulla."""
    albero = ast.parse(ADATTATORE.read_text(encoding="utf-8"))
    costanti = {
        n.targets[0].id: n.value.value for n in albero.body
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
        and n.targets[0].id.startswith("EVENTO_")
    }
    nel_pyp = {p.findtext("EventId") for p in _parametri().values() if p.findtext("EventId")}
    assert {str(v) for v in costanti.values()} == nel_pyp
    assert sorted(costanti.values()) == sorted(scrivi_palette_pyp.EVENTI.values())


def test_le_condizioni_di_visibilita_nominano_campi_che_esistono():
    """Caso: una condizione su un campo rinominato, e un pulsante sparisce per sempre."""
    parametri = _parametri()
    for nome, parametro in parametri.items():
        condizione = parametro.findtext("Visible")
        if condizione and condizione != "False":
            campo = re.split(r"==|!=", condizione)[0].strip()
            assert campo in parametri, f"{nome}: {condizione}"


def test_le_immagini_restano_nascoste_finche_la_sonda_non_risponde():
    """Caso: la palette mostra una miniatura che Allplan non aggiorna, cioe' la vista sbagliata."""
    parametri = _parametri()
    for nome in ("VistaImmagine", "UltimoImmagine"):
        assert parametri[nome].findtext("Visible") == "ImmaginiDaScript == 1"
    assert parametri["ImmaginiDaScript"].findtext("Value") == "0"


def test_genera_e_annulla_non_si_vedono_mai_insieme():
    """Stato in corso di DESIGN.md: Genera diventa Annulla."""
    parametri = _parametri()
    assert parametri["Genera"].findtext("Visible") == "InCorso == 0"
    assert parametri["Annulla"].findtext("Visible") == "InCorso == 1"


def test_l_installazione_copia_tutto_quello_che_la_palette_importa():
    """Caso: in Allplan manca telecomando.py e la palette non si carica."""
    installa = (V2026 / "installa.ps1").read_text(encoding="utf-8")
    for file in ("telecomando.py", "sonda_palette.py", "ponte.py", "AirenderPalette.py",
                 "AirenderPalette.pyp", scrivi_palette_pyp.IMMAGINE_VUOTA):
        assert file in installa, file
    assert (PYP.parent / scrivi_palette_pyp.IMMAGINE_VUOTA).is_file()


def test_telecomando_non_importa_allplan():
    """Regola 1 e 2: solo l'adattatore della versione importa NemAll_Python."""
    testo = (RADICE / "allplan" / "comune" / "telecomando.py").read_text(encoding="utf-8")
    assert "NemAll_Python" not in testo
    assert "NemAll_Python" not in (V2026 / "scrivi_palette_pyp.py").read_text(encoding="utf-8")


def test_la_palette_non_promette_funzioni_che_non_ci_sono():
    """Caso (2026-11-01): Riccardo vede «Cambia materiale» e «Video» come «in arrivo»."""
    testo = PYP.read_text(encoding="utf-8").lower()
    assert "in arrivo" not in testo
    assert "cambia materiale" not in testo


def test_la_palette_dice_come_tornare_alla_library():
    """Caso (2026-11-01): dalla palette non si trova la via per tornare alla Library."""
    assert "premi Esc" in PYP.read_text(encoding="utf-8")


def _ritorno_di_on_cancel(percorso: Path) -> str:
    albero = ast.parse(percorso.read_text(encoding="utf-8"))
    for nodo in ast.walk(albero):
        if isinstance(nodo, ast.FunctionDef) and nodo.name == "on_cancel_function":
            return ast.unparse(nodo)
    return ""


def test_esc_chiude_palette_e_sonda_senza_creare_niente():
    """Esc deve chiudere, non creare elementi ne' ricominciare l'input."""
    sonda = (RADICE / "allplan" / "v2027" / "pacchetto" / "PythonPartsScripts"
             / "riccardo_silingardi" / "airender" / "AirenderSondaMateriali.py")
    for percorso in (ADATTATORE, sonda):
        corpo = _ritorno_di_on_cancel(percorso)
        assert "OnCancelFunctionResult.CANCEL_INPUT" in corpo, percorso
        assert "CREATE_ELEMENTS" not in corpo and "RESTART" not in corpo, percorso
