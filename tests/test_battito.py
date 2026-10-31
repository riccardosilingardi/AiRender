"""Il file «sono vivo» della coda e dello Studio, e la coda che non si raddoppia."""

from __future__ import annotations

import json
import os

import pytest

from core import battito, coda as modulo_coda


def test_un_battito_fresco_si_legge_con_il_pid(tmp_path):
    """Caso: la palette non riconosce la coda che gira e ne avvia un'altra."""
    file = tmp_path / "lavori" / battito.FILE_CODA
    battito.scrivi(file, {"cartella": "x"})
    letto = battito.leggi(file)
    assert letto["pid"] == os.getpid() and letto["cartella"] == "x"


@pytest.mark.parametrize("contenuto", ["", "{rotto", json.dumps({"pid": 1}), json.dumps([1, 2])])
def test_un_battito_rotto_vale_come_processo_morto(tmp_path, contenuto):
    """Caso: un file a meta' fa credere viva una coda che non c'e'."""
    file = tmp_path / "vivo.json"
    file.write_text(contenuto, encoding="utf-8")
    assert battito.leggi(file) is None


def test_il_battito_sparisce_quando_il_processo_esce(tmp_path):
    """Caso: lo Studio chiuso lascia un battito e la palette prova ad aprire una pagina morta."""
    file = tmp_path / "lavori" / battito.FILE_STUDIO
    with battito.Battito(file, {"indirizzo": "http://127.0.0.1:1/"}, intervallo=0.01):
        assert battito.leggi(file)["indirizzo"] == "http://127.0.0.1:1/"
    assert not file.exists()


def test_il_battito_di_un_altro_processo_non_si_cancella(tmp_path):
    """Caso: lo Studio che si chiude cancella il battito di un altro Studio che ha preso il posto."""
    file = tmp_path / "vivo.json"
    with battito.Battito(file, intervallo=10):
        file.write_text(json.dumps({"pid": os.getpid() + 1, "battito": 0}), encoding="utf-8")
    assert file.exists()


def test_una_seconda_coda_sulla_stessa_cartella_si_rifiuta(tmp_path):
    """Caso: una seconda coda prende per abbandonato il lavoro in corso della prima e lo mette fra gli errori."""
    file = battito.percorso(tmp_path, battito.FILE_CODA)
    file.parent.mkdir(parents=True)
    file.write_text(json.dumps({"pid": os.getpid() + 1, "battito": __import__("time").time()}), encoding="utf-8")
    with pytest.raises(modulo_coda.CodaGiaAttiva) as errore:
        modulo_coda.Coda(tmp_path, dire=lambda _t: None).gira(una_volta=True)
    assert "ne basta una" in errore.value.fatto
    assert errore.value.cosa_fare


def test_la_coda_batte_mentre_gira_e_smette_quando_esce(tmp_path):
    """Caso: la palette non vede la coda accesa e ne lancia un'altra."""
    visti = []
    coda = modulo_coda.Coda(tmp_path, dire=lambda _t: None)
    originale = coda.esegui_uno

    def guarda():
        visti.append(modulo_coda.coda_viva(tmp_path))
        return originale()

    coda.esegui_uno = guarda
    coda.gira(una_volta=True)
    assert visti and visti[0]["pid"] == os.getpid()
    assert modulo_coda.coda_viva(tmp_path) is None
