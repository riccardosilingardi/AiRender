"""AIRENDER per Allplan 2027: il pacchetto plugin (.allep) e l'installazione nella Usr.

Allplan non c'e' qui: si controlla che i pezzi combacino (percorsi del .pyp,
dell'install-config.yml e delle icone, file copiati), non che Allplan li
installi. Quello si prova sul PC di Riccardo (docs/installa-2027.md).
"""

from __future__ import annotations

import importlib.util
import re
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

RADICE = Path(__file__).resolve().parents[1]
V2026 = RADICE / "allplan" / "v2026"
V2027 = RADICE / "allplan" / "v2027"
PACCHETTO = V2027 / "pacchetto"
ADATTATORE_2026 = V2026 / "PythonPartsScripts" / "airender" / "AirenderPalette.py"
ADATTATORE_2027 = PACCHETTO / "PythonPartsScripts" / "riccardo_silingardi" / "airender" / "AirenderPalette.py"
PYP_2027 = PACCHETTO / "Library" / "AIRENDER" / "AirenderPalette.pyp"


def _modulo(nome: str, percorso: Path):
    specifica = importlib.util.spec_from_file_location(nome, percorso)
    modulo = importlib.util.module_from_spec(specifica)
    sys.modules[nome] = modulo
    specifica.loader.exec_module(modulo)
    return modulo


pacchetto = _modulo("pacchetto_2027", V2027 / "pacchetto.py")
scrivi_2027 = _modulo("scrivi_palette_pyp_2027", V2027 / "scrivi_palette_pyp.py")


def _config() -> str:
    return (PACCHETTO / "install-config.yml").read_text(encoding="utf-8")


def _corpo(testo: str) -> str:
    """L'adattatore senza la sua docstring di testa."""
    return testo.split('"""', 2)[2]


def test_l_adattatore_2027_e_quello_2026():
    """Caso: si corregge la palette 2026 e la 2027 resta col difetto."""
    assert _corpo(ADATTATORE_2027.read_text(encoding="utf-8")) == _corpo(
        ADATTATORE_2026.read_text(encoding="utf-8")), (
        "copia allplan/v2026/.../AirenderPalette.py nel pacchetto 2027, sotto la sua docstring")


def test_il_pyp_2027_e_quello_generato():
    assert PYP_2027.read_text(encoding="utf-8") == scrivi_2027.pyp(), (
        "rilancia: python allplan/v2027/scrivi_palette_pyp.py")


def test_il_pyp_2027_punta_allo_script_nel_pacchetto():
    """Caso: Allplan apre il .pyp ma non trova lo script, e la palette resta vuota."""
    nome = re.search(r"<Name>(.+?\.py)</Name>", PYP_2027.read_text(encoding="utf-8")).group(1)
    assert (PACCHETTO / "PythonPartsScripts" / Path(*nome.split("\\"))) == ADATTATORE_2027


def test_il_pyp_2026_non_cambia():
    """La 2026 resta com'era: installa.ps1 copia ancora in PythonPartsScripts\\airender."""
    testo = (V2026 / "Library" / "AIRENDER" / "AirenderPalette.pyp").read_text(encoding="utf-8")
    assert "<Name>airender\\AirenderPalette.py</Name>" in testo


def test_install_config_nomina_file_che_esistono():
    """Caso: un'icona o un .pyp scritto male, e Allplan rifiuta il plugin."""
    config = _config()
    percorsi = re.findall(r"(?:pyp|small|large):\s*(\S+)", config)
    assert len(percorsi) == 3
    for percorso in percorsi:
        assert (PACCHETTO / Path(*percorso.split("\\"))).is_file(), percorso
    assert re.search(r"developer:\s*" + pacchetto.SVILUPPATORE, config)
    assert "min-allplan-version: 2027" in config
    assert "target-location: USR" in config


def test_le_icone_hanno_le_misure_dell_sdk():
    cartella = PACCHETTO / "PythonPartsActionbar" / pacchetto.SVILUPPATORE / pacchetto.PLUGIN
    for misura in (24, 128):
        with Image.open(cartella / f"Airender_{misura}.png") as icona:
            assert icona.size == (misura, misura)


def test_requirements_porta_pillow():
    assert "pillow" in (PACCHETTO / "requirements.in").read_text(encoding="utf-8").lower()


def test_l_allep_ha_le_cinque_voci_e_tutto_quello_che_la_palette_importa(tmp_path):
    albero = pacchetto.costruisci(tmp_path)
    allep = pacchetto.comprimi(albero, tmp_path / "AIRENDER-2027.allep")
    with zipfile.ZipFile(allep) as archivio:
        nomi = set(archivio.namelist())
    assert {n.split("/")[0] for n in nomi} == set(pacchetto.VOCI_ALLEP)
    script = "PythonPartsScripts/riccardo_silingardi/airender/"
    for file in ("AirenderPalette.py", *pacchetto.FILE_COMUNI, "core/__init__.py",
                 "core/studio/__main__.py", "core/config.py"):
        assert script + file in nomi, file
    assert not [n for n in nomi if "__pycache__" in n or n.endswith(".pyc")]
    assert not [n for n in nomi if "\\" in n]


def test_installa_copia_e_toglie_le_prove_vecchie(tmp_path):
    usr = tmp_path / "Usr" / "Local"
    (usr / "PythonPartsScripts" / "airender" / "core").mkdir(parents=True)
    libreria = usr / "Library" / "AIRENDER"
    libreria.mkdir(parents=True)
    for vecchio in ("AirenderProva.pyp", "AirenderSonda.pyp", "sonda_a.png"):
        (libreria / vecchio).write_text("vecchio")
    viste = usr / "AIRENDER" / "viste"
    viste.mkdir(parents=True)
    (viste / "vista.png").write_text("una vista")
    script = usr / pacchetto.CARTELLA_SCRIPT
    (script / "core").mkdir(parents=True)
    (script / "core" / "rimasto.py").write_text("file vecchio del motore")

    esito = pacchetto.installa(pacchetto.costruisci(tmp_path / "dist"), usr)

    assert not (usr / "PythonPartsScripts" / "airender").exists()
    assert sorted(p.name for p in libreria.iterdir()) == [
        "AirenderPalette.pyp", "AirenderSondaColormap.pyp", "AirenderSondaMateriali.pyp", "palette_nessuna.png"]
    assert (script / "AirenderPalette.py").is_file()
    assert not (script / "core" / "rimasto.py").exists()
    assert (usr / "PythonPartsActionbar" / pacchetto.SVILUPPATORE / "airender" / "Airender_24.png").is_file()
    assert not (usr / "install-config.yml").exists()
    assert (viste / "vista.png").read_text() == "una vista"  # le viste non si toccano
    assert len(esito.tolti) == 4
    assert esito.avvisi and "Pillow" in esito.avvisi[0]


def test_installa_non_avvisa_se_pillow_c_e(tmp_path):
    usr = tmp_path / "Usr"
    (usr / "PythonParts-site-packages" / "PIL").mkdir(parents=True)
    assert pacchetto.installa(pacchetto.costruisci(tmp_path / "dist"), usr).avvisi == []


def test_trova_usr_preferisce_quella_con_i_pacchetti_dell_sdk(tmp_path):
    vuota = tmp_path / "Documents" / "Nemetschek" / "Allplan" / "2027" / "Usr" / "Local"
    vuota.mkdir(parents=True)
    giusta = tmp_path / "OneDrive" / "Documenti" / "Nemetschek" / "Allplan" / "2027" / "Usr" / "Local"
    (giusta / "PythonParts-site-packages").mkdir(parents=True)
    assert pacchetto.trova_usr(tmp_path) == giusta
    assert pacchetto.trova_usr(tmp_path / "nessuno") in (None, Path("C:/Data/Allplan/Allplan 2027/Usr/Local"))


def test_main_senza_usr_spiega_cosa_fare(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(pacchetto, "trova_usr", lambda _casa: None)
    assert pacchetto.main(["--uscita", str(tmp_path), "--installa"]) == 1
    assert "--usr" in capsys.readouterr().out


@pytest.mark.parametrize("file", [ADATTATORE_2027, V2027 / "pacchetto.py", V2027 / "scrivi_palette_pyp.py"])
def test_solo_l_adattatore_importa_allplan(file):
    """Regola 1 e 2 di CLAUDE.md."""
    importa = "import NemAll_Python" in file.read_text(encoding="utf-8")
    assert importa == (file == ADATTATORE_2027)


def test_l_installatore_ferma_coda_e_studio_su_windows():
    """Caso: WinError 32 del 2026-10-31, la coda teneva aperta la cartella dello script."""
    lanciati = []

    def lancia(argomenti, **_opzioni):
        lanciati.append(argomenti)
        return SimpleNamespace(stdout="1234\n5678\n")

    assert pacchetto.ferma_coda_e_studio(lancia, sistema="nt") == ["1234", "5678"]
    assert "core\\.(studio|coda)" in lanciati[0][-1]
    assert pacchetto.ferma_coda_e_studio(lancia, sistema="posix") == []
    assert len(lanciati) == 1


def test_l_installatore_dice_cosa_ha_fermato(tmp_path):
    usr = tmp_path / "Usr" / "Local"
    (usr / "PythonParts-site-packages" / "PIL").mkdir(parents=True)
    esito = pacchetto.installa(pacchetto.costruisci(tmp_path / "dist"), usr, ferma=lambda: ["42"])
    assert any("42" in avviso for avviso in esito.avvisi)
