"""Regola: luce e colore prima di esportare (richiesta di Riccardo del 2026-11-08).

La matematica si prova senza immagini (core/regola.py), i pixel con Pillow
(core/immagine.py), e poi l'anteprima e l'esportazione dallo Studio.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

import pytest
from PIL import Image

from core import blocchi, config, immagine, regola
from test_esporta import NANO, _esegui, _studio, cartella, chiamate  # noqa: F401  (fixture)


def _png(colore, misura=(160, 90)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", misura, colore).save(uscita, "PNG")
    return uscita.getvalue()


def _monotona(tabella) -> bool:
    return all(a <= b for a, b in zip(tabella, tabella[1:]))


# --- i numeri ------------------------------------------------------------------


def test_senza_regolazioni_ogni_tono_resta_dov_e():
    """Caso: un render esportato senza toccare i cursori esce diverso da com'era."""
    nessuna = regola.leggi({})
    assert nessuna.neutra() and nessuna.descrizione() == []
    assert regola.tabelle(nessuna) == (list(range(256)),) * 3
    assert regola.leggi({"curva": [[0, 0], [255, 255]]}).neutra()  # la diagonale non e' una curva
    assert regola.fattore_saturazione(nessuna) == 1


@pytest.mark.parametrize("cursore", ["esposizione", "contrasto", "luci", "ombre"])
@pytest.mark.parametrize("verso", [1, -1])
def test_a_fondo_cursore_la_curva_non_torna_mai_indietro(cursore, verso):
    """Caso: un tono piu' chiaro diventa piu' scuro di uno meno chiaro, e nel cielo compaiono bande."""
    tutti = {c: verso * config.REGOLA_CURSORE_MASSIMO for c in ("esposizione", "contrasto", "luci", "ombre")}
    for valori in ({cursore: verso * config.REGOLA_CURSORE_MASSIMO}, tutti):
        for tabella in regola.tabelle(regola.leggi(valori)):
            assert _monotona(tabella), valori


def test_ogni_cursore_va_nel_verso_che_dice():
    grigio = 128
    assert regola.tabelle(regola.leggi({"esposizione": 50}))[1][grigio] > grigio
    assert regola.tabelle(regola.leggi({"esposizione": -50}))[1][grigio] < grigio
    piu = regola.tabelle(regola.leggi({"contrasto": 60}))[1]
    assert piu[64] < 64 and piu[192] > 192 and piu[0] == 0 and piu[255] == 255
    assert regola.tabelle(regola.leggi({"luci": -60}))[1][192] < 192
    assert regola.tabelle(regola.leggi({"luci": -60}))[1][64] == 64     # Luci non tocca le ombre
    assert regola.tabelle(regola.leggi({"ombre": 60}))[1][64] > 64
    assert regola.tabelle(regola.leggi({"ombre": 60}))[1][192] == 192   # Ombre non tocca le luci
    rosso, verde, blu = regola.tabelle(regola.leggi({"temperatura": 50}))
    assert rosso[grigio] > verde[grigio] > blu[grigio]
    assert regola.fattore_saturazione(regola.leggi({"saturazione": -100})) == 0


def test_la_curva_passa_dai_punti_e_non_ondeggia():
    """Caso: una curva a S con tre punti fa un'onda fra un punto e l'altro (bande nel cielo)."""
    curva = regola.leggi({"curva": [[0, 0], [64, 40], [192, 215], [255, 255]]})
    tabella = regola.tabella_curva(curva)
    assert tabella[64] == 40 and tabella[192] == 215 and _monotona(tabella)
    # fuori dagli estremi resta piatta, come in Photoshop
    alzati = regola.tabella_curva(regola.leggi({"curva": [[30, 20], [255, 255]]}))
    assert alzati[:30] == [20] * 30


def test_la_descrizione_dice_quello_che_entra_nel_file():
    r = regola.leggi({"esposizione": 8, "luci": -4, "curva": [[0, 0], [128, 150], [255, 255]]})
    assert r.descrizione() == ["Esposizione +8", "Luci −4", "Curva (3 punti)"]


@pytest.mark.parametrize("dati,parola", [
    ({"contrasto": 101}, "Contrasto"),
    ({"ombre": "tanto"}, "Ombre"),
    ({"curva": [[0, 0], [0, 50], [255, 255]]}, "stesso tono"),
    ({"curva": [[0, 0], [300, 10]]}, "fuori"),
    ({"curva": [[0, 0]]}, "due punti"),
    ({"curva": [[i * 30, i * 30] for i in range(9)]}, "al massimo"),
])
def test_una_regolazione_impossibile_si_rifiuta_e_dice_cosa_fare(dati, parola):
    with pytest.raises(regola.RegolazioneNonValida) as errore:
        regola.leggi(dati)
    assert parola in errore.value.fatto and errore.value.cosa_fare


def test_le_costanti_di_regola_sono_scelte_e_lo_dicono():
    for nome in ("REGOLA_ESPOSIZIONE_STOP", "REGOLA_CONTRASTO_FORZA", "REGOLA_LUCI_OMBRE_AMPIEZZA",
                 "REGOLA_TEMPERATURA_FORZA", "REGOLA_SATURAZIONE_MASSIMA", "REGOLA_ANTEPRIMA_LATO_PX"):
        assert config.costante(nome).origine == config.SCELTA
    # sopra 0,125 Luci e Ombre piegherebbero la curva all'indietro
    assert config.REGOLA_LUCI_OMBRE_AMPIEZZA <= 0.125


# --- i pixel ---------------------------------------------------------------------


def test_i_pixel_seguono_le_tabelle_e_la_saturazione():
    r = regola.leggi({"esposizione": 40, "saturazione": -100})
    uscita = Image.open(io.BytesIO(immagine.regola(_png((200, 60, 30)), regola.tabelle(r), regola.fattore_saturazione(r))))
    rosso, verde, blu = uscita.convert("RGB").getpixel((5, 5))
    assert abs(rosso - verde) <= 1 and abs(verde - blu) <= 1  # in bianco e nero
    assert uscita.size == (160, 90)


def test_l_anteprima_e_piccola_ma_con_le_stesse_proporzioni():
    r = regola.Regolazione()
    dati = immagine.regola(_png((90, 90, 90), (4000, 2250)), regola.tabelle(r), 1,
                           lato_massimo=config.REGOLA_ANTEPRIMA_LATO_PX, formato="JPEG")
    assert dati.startswith(b"\xff\xd8")
    assert Image.open(io.BytesIO(dati)).size == (config.REGOLA_ANTEPRIMA_LATO_PX, 900)


# --- Studio ------------------------------------------------------------------------


def _un_render(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    destinazione = studio.destinazione(NANO)["destinazione"]
    lavoro = studio.invia({"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista").a_dizionario(),
                           "preset": "rivista", "modello": NANO, "destinazione_mostrata": destinazione})
    _esegui(cartella, chiamate)
    return studio, lavoro["identificativo"]


def test_l_anteprima_dello_studio_non_manda_niente_e_dice_la_misura_vera(cartella, chiamate):
    """Caso: muovere un cursore spedisce il render a un servizio, o costa crediti."""
    studio, identificativo = _un_render(cartella, chiamate)
    chiamate_prima = len(chiamate)
    esito = studio.anteprima_regola(identificativo, {"regola": {"esposizione": 60}})
    assert len(chiamate) == chiamate_prima
    assert esito["immagine"].startswith("data:image/jpeg;base64,")
    anteprima = Image.open(io.BytesIO(base64.b64decode(esito["immagine"].split(",", 1)[1])))
    render = Image.open(studio._render(identificativo))
    assert (esito["larghezza"], esito["altezza"]) == render.size
    assert max(anteprima.size) <= config.REGOLA_ANTEPRIMA_LATO_PX
    assert esito["regolazioni"] == ["Esposizione +60"] and len(esito["curva"]) == 256


def test_esportato_con_le_regolazioni_il_file_le_porta_e_il_psd_ha_un_livello_in_piu(cartella, chiamate):
    studio, identificativo = _un_render(cartella, chiamate)
    originale = Image.open(studio._render(identificativo)).convert("RGB")
    png = studio.esporta(identificativo, {"formato": "png", "regola": {"esposizione": 80}})
    assert png["regolazioni"] == ["Esposizione +80"]
    regolata = Image.open(png["file"]).convert("RGB")
    assert regolata.size == originale.size
    assert sum(regolata.getpixel((20, 20))) > sum(originale.getpixel((20, 20)))

    psd = studio.esporta(identificativo, {"formato": "psd", "regola": {"esposizione": 80}})
    assert psd["livelli"][-1] == "Regola · Esposizione +80"
    assert psd["livelli"][-2].startswith("1 ·")  # sotto, il render com'era: in Photoshop si spegne

    senza = studio.esporta(identificativo, {"formato": "jpg"})
    assert senza["regolazioni"] == []


def test_una_regolazione_sbagliata_non_scrive_il_file(cartella, chiamate):
    studio, identificativo = _un_render(cartella, chiamate)
    with pytest.raises(regola.RegolazioneNonValida):
        studio.esporta(identificativo, {"formato": "jpg", "regola": {"saturazione": 500}})
    assert not (cartella / "esportati").exists() or not list((cartella / "esportati").iterdir())


def test_lo_studio_dice_alla_pagina_i_cursori_e_i_limiti(cartella, chiamate):
    stato = _studio(cartella, chiamate).stato_studio()
    assert stato["regola"]["massimo"] == config.REGOLA_CURSORE_MASSIMO
    assert [c["nome"] for c in stato["regola"]["cursori"]] == [
        "Esposizione", "Contrasto", "Luci", "Ombre", "Temperatura", "Saturazione"]


def test_il_server_ha_la_strada_dell_anteprima():
    sorgente = (Path(__file__).resolve().parents[1] / "core" / "studio" / "server.py").read_text(encoding="utf-8")
    assert '"api", "lavori", identificativo, "regola"' in sorgente
