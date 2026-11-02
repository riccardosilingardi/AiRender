"""Lo storico dello Studio: tutte le immagini di tutte le viste, in una striscia.

Il problema di Riccardo del 2026-11-02: una cattura nuova faceva sparire il
render di prima e i suoi passi. Qui si controlla che lo storico li tenga
tutti, un gruppo per vista, e che una cattura nuova si aggiunga e basta.
Nessuna rete: il provider e' un finto.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from core import video as modulo_video
from test_passi import (VISTA, _coda, _genera, _passo, _studio,  # noqa: F401
                        cartella, chiamate)
from test_ritocca import AREE, _ritocca
from test_studio import _chiedi, vista_shaded


def _nuova_cattura(cartella: Path, nome: str = "vista-2.png") -> str:
    """Una vista salvata dalla palette dopo la prima: piu' recente."""
    percorso = cartella / nome
    percorso.write_bytes(vista_shaded(640, 400))
    prima = (cartella / VISTA).stat().st_mtime
    os.utime(percorso, (prima + 60, prima + 60))
    return nome


def test_una_cattura_nuova_si_aggiunge_e_i_render_di_prima_restano(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    due = _passo(studio, uno, "due alberi davanti"); coda.esegui_uno()
    nuova = _nuova_cattura(cartella)
    gruppi = studio.storico()["gruppi"]
    assert [g["vista"] for g in gruppi] == [nuova, VISTA]
    # la cattura nuova ha solo se' stessa; quella di prima tiene tutto
    assert [v["tipo"] for v in gruppi[0]["voci"]] == ["cattura"]
    vecchia = gruppi[1]["voci"]
    assert [v["tipo"] for v in vecchia] == ["cattura", "stile", "passo"]
    assert [v["identificativo"] for v in vecchia[1:]] == [uno, due]
    assert all(v["immagine"] for v in vecchia)
    assert [v["etichetta"] for v in vecchia] == ["Vista", "Render", "Modifica"]


def test_i_ritocchi_stanno_nel_gruppo_della_vista_in_ordine(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    rit = _ritocca(studio, uno, aree=[AREE[0]]); coda.esegui_uno()
    voci = studio.storico()["gruppi"][0]["voci"]
    assert [(v["tipo"], v["identificativo"]) for v in voci] == [("cattura", None), ("stile", uno), ("ritocco", rit)]
    assert voci[2]["etichetta"] == "Ritocco" and voci[2]["da"] == uno


def test_un_lavoro_in_coda_c_e_gia_e_si_dice_attivo(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    uno = _genera(studio)
    voce = studio.storico()["gruppi"][0]["voci"][1]
    assert voce["identificativo"] == uno and voce["attivo"] is True and voce["immagine"] is False


def test_un_video_sta_accanto_al_render_da_cui_parte(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    _genera(studio); coda.esegui_uno()
    richiesta = modulo_video.metti_in_coda(cartella, [studio.file_render(uno)])
    (cartella / "caricate").mkdir()
    caricata = cartella / "caricate" / "altra.png"
    caricata.write_bytes(vista_shaded(64, 40))
    sciolto = modulo_video.metti_in_coda(cartella, [caricata])
    gruppi = studio.storico()["gruppi"]
    tipi = [(v["tipo"], v["identificativo"]) for v in gruppi[0]["voci"]]
    assert tipi[:3] == [("cattura", None), ("stile", uno), ("video", richiesta.identificativo)]
    assert gruppi[-1]["vista"] is None and gruppi[-1]["voci"][0]["identificativo"] == sciolto.identificativo
    assert gruppi[0]["voci"][2]["attivo"] is True


def test_un_albero_rotto_non_ferma_lo_storico_delle_altre_viste(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    _genera(studio); coda.esegui_uno()
    nuova = _nuova_cattura(cartella)
    (cartella / "vista-2.passi.json").write_text("{rotto", encoding="utf-8")
    gruppi = studio.storico()["gruppi"]
    assert gruppi[0]["vista"] == nuova and gruppi[0]["errore"]["fatto"]
    assert [v["tipo"] for v in gruppi[0]["voci"]] == ["cattura"]
    assert len(gruppi[1]["voci"]) == 2


def test_la_rotta_dello_storico_risponde(cartella, chiamate):
    from core.studio.server import avvia_in_sottofondo, crea_server
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    _genera(studio); coda.esegui_uno()
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    try:
        stato, tipo, corpo = _chiedi(servito, "GET", "/api/storico")
    finally:
        servito.shutdown()
        servito.server_close()
    assert stato == 200 and tipo.startswith("application/json")
    assert len(json.loads(corpo)["gruppi"][0]["voci"]) == 2
