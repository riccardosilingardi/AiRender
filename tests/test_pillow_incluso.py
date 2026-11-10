"""Pillow dentro il pacchetto 2027: scelta all'avvio e costruzione del pacchetto."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
import zipfile
from pathlib import Path

import pytest

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "allplan" / "comune"))

import pillow_incluso  # noqa: E402  pylint: disable=wrong-import-position


def _modulo(nome: str, percorso: Path):
    specifica = importlib.util.spec_from_file_location(nome, percorso)
    modulo = importlib.util.module_from_spec(specifica)
    sys.modules[nome] = modulo
    specifica.loader.exec_module(modulo)
    return modulo


pacchetto = _modulo("pacchetto_2027_pillow", RADICE / "allplan" / "v2027" / "pacchetto.py")


def test_la_cartella_segue_la_versione_di_python(tmp_path):
    assert pillow_incluso.cartella_per(tmp_path, (3, 13)) == tmp_path / "_pillow" / "cp313"


def test_un_pillow_che_si_carica_resta_quello(tmp_path):
    assert pillow_incluso.assicura(tmp_path) == "Pillow installato in Allplan"


def test_un_pillow_rotto_lascia_il_posto_a_quello_del_pacchetto(tmp_path, monkeypatch):
    """Caso del 2026-10-31: Pillow nella Usr compilato per un altro Python."""
    versione = sys.version_info[:2]
    incluso = pillow_incluso.cartella_per(tmp_path, versione) / "PIL"
    incluso.mkdir(parents=True)
    (incluso / "__init__.py").write_text("", encoding="utf-8")
    (incluso / "Image.py").write_text("DEL_PACCHETTO = True\n", encoding="utf-8")
    tentativi = []
    vero = pillow_incluso.importlib.import_module

    def importa(nome):
        tentativi.append(nome)
        if len(tentativi) == 1:
            raise ImportError("cannot import name '_imaging' from 'PIL'")
        return vero(nome)

    monkeypatch.setattr(pillow_incluso.importlib, "import_module", importa)
    monkeypatch.setattr(sys, "path", list(sys.path))
    salvati = {n: m for n, m in sys.modules.items() if n == "PIL" or n.startswith("PIL.")}
    try:
        esito = pillow_incluso.assicura(tmp_path, versione)
        assert esito.startswith("Pillow del pacchetto"), esito
        assert sys.modules["PIL.Image"].DEL_PACCHETTO
    finally:
        for n in [n for n in sys.modules if n == "PIL" or n.startswith("PIL.")]:
            del sys.modules[n]
        sys.modules.update(salvati)


def test_senza_pillow_e_senza_cartella_lo_dice(tmp_path, monkeypatch):
    def rotto(_nome):
        raise ImportError("No module named 'PIL'")

    monkeypatch.setattr(pillow_incluso.importlib, "import_module", rotto)
    assert "non ne ha uno" in pillow_incluso.assicura(tmp_path, (3, 13))


def _ruota_finta(cache: Path, etichetta: str) -> str:
    cache.mkdir(parents=True, exist_ok=True)
    percorso = cache / pacchetto.nome_ruota(etichetta)
    with zipfile.ZipFile(percorso, "w") as archivio:
        archivio.writestr("PIL/__init__.py", "")
        archivio.writestr(f"pillow-{pacchetto.PILLOW_VERSIONE}.dist-info/LICENSE", "HPND")
        archivio.writestr(f"pillow-{pacchetto.PILLOW_VERSIONE}.dist-info/RECORD", "")
    return hashlib.sha256(percorso.read_bytes()).hexdigest()


def test_il_pacchetto_include_pillow_e_la_licenza(tmp_path, monkeypatch):
    cache = tmp_path / "ruote"
    monkeypatch.setattr(pacchetto, "PILLOW_RUOTE", {"cp313": _ruota_finta(cache, "cp313")})
    pacchetto.includi_pillow(tmp_path / "script", cache)
    base = tmp_path / "script" / "_pillow" / "cp313"
    assert (base / "PIL" / "__init__.py").is_file()
    assert (base / f"pillow-{pacchetto.PILLOW_VERSIONE}.dist-info" / "LICENSE").is_file()
    assert not (base / f"pillow-{pacchetto.PILLOW_VERSIONE}.dist-info" / "RECORD").exists()


def test_una_ruota_con_l_impronta_sbagliata_non_entra(tmp_path, monkeypatch):
    cache = tmp_path / "ruote"
    _ruota_finta(cache, "cp313")
    monkeypatch.setattr(pacchetto, "PILLOW_RUOTE", {"cp313": "0" * 64})
    with pytest.raises(SystemExit, match="impronta"):
        pacchetto.includi_pillow(tmp_path / "script", cache)


def test_le_impronte_sono_quelle_di_pypi_per_ogni_python_di_allplan():
    assert set(pacchetto.PILLOW_RUOTE) == {"cp310", "cp311", "cp312", "cp313", "cp314"}
    assert all(len(h) == 64 for h in pacchetto.PILLOW_RUOTE.values())
