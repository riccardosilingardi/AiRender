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


def test_listino_annuale_dieci_mensilita_e_plugin_in_tutti_i_piani():
    """Caso: l'annuale costa dodici mesi, o un piano chiude il plugin di Allplan (AIRENDER nasce per Allplan)."""
    piani = config.LISTINO["piani"]
    for nome in ("base", "pro", "studio"):
        assert piani[nome]["prezzo_anno"] == piani[nome]["prezzo_mese"] * 10
    for piano in piani.values():
        assert "web" in piano["canali"] and "plugin" in piano["canali"]
    assert piani["studio"]["postazioni"] == 3
    for piano in piani.values():
        assert set(piano["modelli"]) <= set(config.LISTINO["pesi"])


def test_listino_e_json_puro():
    """Caso: nel listino entra un oggetto Python che il server non sa leggere."""
    json.loads(json.dumps(config.LISTINO))


def test_listino_funzioni_per_piano():
    """Caso: il video finisce in Base, o una funzione manca dal piano e lo Studio non sa se mostrarla."""
    piani = config.LISTINO["piani"]
    chiavi = set(piani["pro"]["funzioni"])
    for nome, piano in piani.items():
        assert set(piano["funzioni"]) == chiavi, nome
    assert piani["base"]["funzioni"]["video"] is None
    assert piani["base"]["funzioni"]["materiali"] is True
    assert piani["pro"]["funzioni"]["video"] == {"risoluzione_massima": "720p", "secondi_massimi": 10}
    assert piani["studio"]["funzioni"]["video"]["risoluzione_massima"] == "1080p"
    for piano in piani.values():
        video = piano["funzioni"]["video"]
        if video:
            assert video["risoluzione_massima"] in config.VIDEO_RISOLUZIONI
            assert video["secondi_massimi"] in config.VIDEO_DURATE_SECONDI
    # Un credito AIRENDER non deve costare piu' di ~0,09 EUR: il video a
    # 1080p (~0,72 EUR/s, stima) ne vale 8 al secondo.
    assert config.LISTINO["pesi_azioni"]["video_1080p_al_secondo"] == 8


def test_il_workflow_di_tieni_la_geometria_del_server_e_quello_del_motore():
    """Caso: si cambia il workflow o la forza in config.py e il server continua a mandare il vecchio."""
    assert (RADICE / "server" / "geometria.json").read_text(encoding="utf-8") == _scrittore().testo_geometria(), (
        "server/geometria.json non e' allineato: lancia python scripts/scrivi_listino.py"
    )


def test_tieni_la_geometria_ha_un_peso_e_sta_solo_nello_studio():
    """Caso: la prima passata parte gratis coi crediti AIRENDER, o finisce in un piano che non la vende."""
    assert config.LISTINO["pesi_azioni"]["tieni_geometria"] >= 1
    aperta = {n for n, p in config.LISTINO["piani"].items() if p["funzioni"]["tieni_geometria"]}
    assert aperta == {"studio"}
