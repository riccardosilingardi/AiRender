"""I miei preset (prompt 9, 2026-10-31): salvati dall'utente, fuori dal repository."""

from __future__ import annotations

import json

import pytest

from core import blocchi, preset_utente as pu


def _scelte(**cambi):
    return blocchi.da_preset("rivista", **cambi).a_dizionario()


def test_senza_file_non_ci_sono_preset_e_non_si_crea_niente(tmp_path):
    assert pu.leggi(tmp_path).preset == [] and not pu.percorso(tmp_path).exists()


def test_salva_e_ricarica_le_stesse_scelte(tmp_path):
    pu.salva(tmp_path, "  Notte   Rossi ", _scelte(luce="notte"), "vertexai/gemini-3-pro-image", "a mano")
    voce = pu.carica(pu.leggi(tmp_path).preset[0])
    assert voce["nome"] == "Notte Rossi" and voce["scelte"]["luce"] == "notte"
    assert voce["modello"] == "vertexai/gemini-3-pro-image" and voce["prompt_a_mano"] == "a mano"
    assert not voce["blocchi_cambiati"] and voce["perse"] == []


def test_nome_doppio_si_rifiuta_finche_non_si_conferma(tmp_path):
    """Caso: un salvataggio cancella in silenzio un preset con lo stesso nome."""
    pu.salva(tmp_path, "Giorno", _scelte(), "m")
    with pytest.raises(pu.PresetUtenteNonValido):
        pu.salva(tmp_path, "giorno", _scelte(luce="notte"), "m")
    pu.salva(tmp_path, "giorno", _scelte(luce="notte"), "m", sovrascrivi=True)
    assert len(pu.leggi(tmp_path).preset) == 1


def test_nome_vuoto_o_troppo_lungo(tmp_path):
    for nome in ("", "   ", "x" * 61):
        with pytest.raises(pu.PresetUtenteNonValido):
            pu.salva(tmp_path, nome, _scelte(), "m")


def test_un_file_rotto_si_mette_da_parte_e_non_si_perde(tmp_path):
    """Caso: un file rovinato viene sovrascritto e i preset dell'utente spariscono."""
    pu.percorso(tmp_path).write_text("{non e' json", encoding="utf-8")
    elenco = pu.leggi(tmp_path)
    assert elenco.preset == [] and "non si legge" in elenco.problema
    messi_da_parte = list(tmp_path.glob("preset-utente.non-letto-*.json"))
    assert len(messi_da_parte) == 1 and messi_da_parte[0].read_text(encoding="utf-8") == "{non e' json"


def test_blocchi_cambiati_dice_cosa_non_esiste_piu(tmp_path):
    """Caso: un preset vecchio si carica con una luce che non c'e' piu', in silenzio."""
    pu.salva(tmp_path, "Vecchio", _scelte(), "m")
    dati = json.loads(pu.percorso(tmp_path).read_text(encoding="utf-8"))
    dati["preset"][0]["versione_blocchi"] = "bozza-1"
    dati["preset"][0]["scelte"]["luce"] = "alba-che-non-esiste"
    dati["preset"][0]["scelte"]["vecchio_asse"] = "x"
    pu.percorso(tmp_path).write_text(json.dumps(dati), encoding="utf-8")
    voce = pu.carica(pu.leggi(tmp_path).preset[0])
    assert voce["blocchi_cambiati"]
    assert any("alba-che-non-esiste" in p for p in voce["perse"])
    assert any("vecchio_asse" in p for p in voce["perse"])
    assert voce["scelte"]["luce"] is None


def test_rinomina_ed_elimina(tmp_path):
    pu.salva(tmp_path, "A", _scelte(), "m")
    pu.salva(tmp_path, "B", _scelte(), "m")
    with pytest.raises(pu.PresetUtenteNonValido):
        pu.rinomina(tmp_path, "A", "b")
    pu.rinomina(tmp_path, "A", "C")
    pu.elimina(tmp_path, "B")
    assert [p["nome"] for p in pu.leggi(tmp_path).preset] == ["C"]
    with pytest.raises(pu.PresetUtenteNonValido):
        pu.elimina(tmp_path, "B")
