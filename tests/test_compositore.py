"""Studio · Ritocca con il compositore (2026-11-09): una frase con @1, @2 e i pennelli.

La frase si divide in una nota per area (core/aree.py da_testo); i tratti di
pennello aggiungi e togli sono aree come le altre, con il contorno ricavato
dal tratto. Nessuna rete: il provider e' un finto. Che il modello capisca le
parole dei pennelli non lo dice nessun test.
"""

from __future__ import annotations

import math

import pytest

from core import aree as modulo_aree, config, passi as modulo_passi
from core.coda import leggi_stato
from test_passi import VISTA, _studio, cartella, chiamate  # noqa: F401  (le fixture si usano per nome)
from test_ritocca import _pixel, _ritocca, base  # noqa: F401

RETT = {"forma": "rettangolo", "punti": [[0.1, 0.1], [0.4, 0.5]]}
AGGIUNGI = {"forma": "pennello", "azione": "aggiungi", "spessore": 0.05, "punti": [[0.6, 0.7], [0.8, 0.7]]}
TOGLI = {"forma": "pennello", "azione": "togli", "spessore": 0.05, "punti": [[0.7, 0.2]]}


# --- la frase: una nota per area ------------------------------------------------


def test_ogni_pezzo_della_frase_va_all_area_che_chiama():
    note = [a["nota"] for a in modulo_aree.da_testo(
        "Rivesti @1 di legno chiaro, metti persone che passeggiano in @2; togli il palo in @3", [RETT, AGGIUNGI, TOGLI])]
    assert note == ["Rivesti quest'area di legno chiaro", "metti persone che passeggiano in quest'area",
                    "togli il palo in quest'area"]


def test_la_chiamata_in_testa_al_pezzo_non_si_ripete_nella_nota():
    uno, due = modulo_aree.da_testo("@1 rivesti di legno chiaro, @2 metti persone", [RETT, AGGIUNGI])
    assert (uno["nota"], due["nota"]) == ("rivesti di legno chiaro", "metti persone")


def test_con_un_area_sola_tutta_la_frase_e_la_sua_nota():
    (area,) = modulo_aree.da_testo("legno scuro, 0,5 m di zoccolo in pietra", [RETT])
    assert area["nota"] == "legno scuro, 0,5 m di zoccolo in pietra"


def test_un_pezzo_senza_area_va_con_quello_prima_o_con_quello_dopo():
    uno, due = modulo_aree.da_testo("luce calda. Rivesti @1 di legno, anche il davanzale. Alberi in @2", [RETT, AGGIUNGI])
    assert uno["nota"] == "luce calda; Rivesti quest'area di legno; anche il davanzale"
    assert due["nota"] == "Alberi in quest'area"


def test_un_pezzo_con_due_aree_va_a_tutte_e_due_e_dice_qual_e_l_altra():
    uno, due = modulo_aree.da_testo("@1 e @2 dello stesso legno", [RETT, AGGIUNGI])
    assert uno["nota"] == "quest'area e l'area 2 dello stesso legno"
    assert due["nota"] == "l'area 1 e quest'area dello stesso legno"


def test_un_togli_che_la_frase_non_chiama_toglie_e_basta():
    _uno, tre = modulo_aree.da_testo("Rivesti @1 di legno", [RETT, TOGLI])
    assert tre["nota"] == modulo_aree.NOTA_TOGLI


@pytest.mark.parametrize("testo, aree, parola", [
    ("Rivesti @1 di legno", [RETT, AGGIUNGI], "area 2"),
    ("Rivesti @4 di legno", [RETT, AGGIUNGI], "@4"),
    ("", [RETT], "cosa cambiare"),
])
def test_un_area_che_la_frase_non_chiama_o_un_numero_sbagliato_si_fermano(testo, aree, parola):
    with pytest.raises(modulo_aree.AreaNonValida) as errore:
        modulo_aree.da_testo(testo, aree)
    assert parola in errore.value.fatto


# --- i pennelli --------------------------------------------------------------


def test_un_tratto_di_pennello_e_largo_quanto_lo_spessore_con_le_punte_tonde():
    contorno = modulo_aree.contorno_tratto([(0.0, 0.0), (100.0, 0.0)], 10.0)
    xs, ys = [p[0] for p in contorno], [p[1] for p in contorno]
    assert min(xs) == pytest.approx(-10) and max(xs) == pytest.approx(110)
    assert min(ys) == pytest.approx(-10) and max(ys) == pytest.approx(10)
    cerchio = modulo_aree.contorno_tratto([(50.0, 50.0)], 5.0)
    assert all(math.dist(p, (50, 50)) == pytest.approx(5) for p in cerchio)


def test_lo_spessore_si_misura_sulla_larghezza_del_render():
    area = modulo_aree.Area.da_dizionario({**AGGIUNGI, "nota": "persone"})
    ys = [p[1] for p in area.in_pixel(1000, 500)]
    # spessore 0,05 di 1000 px = 50 px: 25 sopra e 25 sotto il tratto (a y = 350).
    assert min(ys) == pytest.approx(325) and max(ys) == pytest.approx(375)


@pytest.mark.parametrize("cambio", [
    {"spessore": None}, {"spessore": 0.5}, {"spessore": True}, {"azione": "colora"},
])
def test_un_pennello_senza_spessore_giusto_o_con_un_azione_sconosciuta_si_rifiuta(cambio):
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.Area.da_dizionario({**AGGIUNGI, "nota": "persone", **cambio})


def test_solo_il_pennello_ha_uno_spessore():
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.Area.da_dizionario({**RETT, "nota": "legno", "spessore": 0.05})


def test_azione_e_spessore_restano_nel_file_del_lavoro():
    area = modulo_aree.Area.da_dizionario({**TOGLI, "nota": "il palo"})
    assert modulo_aree.Area.da_dizionario(area.a_dizionario()) == area
    assert "azione" not in modulo_aree.Area.da_dizionario({**RETT, "nota": "legno"}).a_dizionario()


def test_la_riga_di_un_pennello_dice_al_modello_se_aggiungere_o_togliere():
    aree = modulo_aree.da_elenco(modulo_aree.da_testo("metti persone in @1, togli il palo in @2", [AGGIUNGI, TOGLI]))
    prompt = modulo_aree.prompt(modulo_aree.CONTORNI, aree)
    assert "Area 1 (add this inside the area" in prompt and "Area 2 (remove this from the area" in prompt
    # «cambia» resta la riga di prima.
    solo = modulo_aree.prompt(modulo_aree.CONTORNI, modulo_aree.da_elenco([{**RETT, "nota": "legno"}]))
    assert "Area 1: legno." in solo


# --- lo Studio -----------------------------------------------------------------


def test_componi_con_la_frase_mostra_la_nota_di_ogni_area(base):
    studio, _coda_, uno = base
    composto = studio.componi_ritocco({"vista": VISTA, "da": uno, "testo": "legno in @1, persone in @2",
                                       "aree": [RETT, AGGIUNGI]})
    assert composto["note_aree"] == ["legno in quest'area", "persone in quest'area"]
    assert "Area 2 (add this inside the area" in composto["prompt"]


def test_un_area_non_chiamata_ferma_applica_e_non_scrive_il_lavoro(base, cartella):
    studio, _coda_, uno = base
    prima = len(list((cartella / "lavori" / "in-attesa").glob("*.json")))
    with pytest.raises(Exception) as errore:
        _ritocca(studio, uno, aree=[RETT, AGGIUNGI], testo="legno in @1")
    assert "area 2" in errore.value.fatto
    assert len(list((cartella / "lavori" / "in-attesa").glob("*.json"))) == prima


def test_il_pennello_cambia_solo_dove_si_e_dipinto(base, cartella):
    studio, coda, uno = base
    rit = _ritocca(studio, uno, aree=[AGGIUNGI], testo="persone che passeggiano")
    coda.esegui_uno()
    studio.passi(VISTA)
    albero = modulo_passi.Albero.leggi(cartella / VISTA)
    partenza, render = albero.passo(uno)["render"], albero.passo(rit)["render"]
    stato = leggi_stato(cartella, rit)
    # Il render finto e' 320 x 200: il tratto va da x 192 a 256 a y 140, largo 16 px.
    assert _pixel(render, 220, 140) == _pixel(stato["modello_intero"], 220, 140)
    assert _pixel(render, 220, 140) != _pixel(partenza, 220, 140)
    assert _pixel(render, 220, 40) == _pixel(partenza, 220, 40)
    assert stato["fuori_aree"]["incollato"] is True


def test_lo_studio_dice_lo_spessore_iniziale_e_i_limiti_del_pennello(cartella, chiamate):
    stato = _studio(cartella, chiamate).stato_studio()
    assert stato["ritocco"]["pennello"] == config.PENNELLO_SPESSORE
    assert stato["ritocco"]["pennelli"] == list(config.PENNELLO_SPESSORI)
