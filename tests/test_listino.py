"""Il listino: uno solo, in core/config.py, copiato pari pari per il server."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from core import config

RADICE = Path(__file__).resolve().parent.parent


def _scrittore():
    spec = importlib.util.spec_from_file_location("scrivi_listino", RADICE / "scripts" / "scrivi_listino.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_listino_del_server_e_quello_di_config():
    """Caso: si cambia un prezzo o un peso in config.py e il server continua a scalare il vecchio."""
    assert (RADICE / "server" / "listino.json").read_text(encoding="utf-8") == _scrittore().testo(), (
        "server/listino.json non e' allineato: lancia python scripts/scrivi_listino.py"
    )


def test_listino_pesi_decisi_il_2026_11_02():
    """Caso: un peso cambia per sbaglio e un render a 4K costa come uno a 1K."""
    pesi = config.LISTINO["pesi"]
    assert pesi[config.NANO_BANANA_2] == {"1K": 1, "2K": 1, "4K": 2}
    assert pesi[config.NANO_BANANA_PRO] == {"1K": 2, "2K": 2, "4K": 3}
    assert config.costante("LISTINO").origine == config.SCELTA


def test_listino_annuale_dieci_mensilita_e_plugin_da_pro():
    """Caso: l'annuale costa dodici mesi, o il piano Base apre il plugin di Allplan."""
    piani = config.LISTINO["piani"]
    for nome in ("base", "pro", "studio"):
        assert piani[nome]["prezzo_anno"] == piani[nome]["prezzo_mese"] * 10
        assert "web" in piani[nome]["canali"]
    assert "plugin" not in piani["base"]["canali"]
    assert "plugin" in piani["pro"]["canali"] and "plugin" in piani["studio"]["canali"]
    assert piani["studio"]["postazioni"] == 3
    for piano in piani.values():
        assert set(piano["modelli"]) <= set(config.LISTINO["pesi"])


def test_listino_e_json_puro():
    """Caso: nel listino entra un oggetto Python che il server non sa leggere."""
    json.loads(json.dumps(config.LISTINO))
