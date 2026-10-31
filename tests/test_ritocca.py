"""Studio · Ritocca: aree e note su un render, un invio, un passo nuovo (prompt 6).

Nessuna rete: il provider e' un finto. Gli stati sono quelli di DESIGN.md,
Studio · Ritocca. Quale modo (contorni o maschera) tiene i pixel fuori dalle
aree non lo dice nessun test: lo dice il piano «aree» del banco di prova.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from core import aree as modulo_aree, blocchi, config, passi as modulo_passi
from core.coda import FORMATO, FORMATO_RITOCCO, Lavoro, LavoroNonValido, leggi_stato, metti_in_coda
from core.provider.base import Risultato
from core.ricetta import Ricetta, impronta
from core.studio.server import avvia_in_sottofondo, crea_server
from core.studio.servizio import RichiestaStudioNonValida
from test_passi import (NANO, VISTA, ProviderCheRende, _coda, _dest, _genera, _passo, _per_numero,
                        _studio, cartella, chiamate)  # noqa: F401  (le fixture si usano per nome)
from test_studio import _chiedi

AREE = [
    {"forma": "rettangolo", "punti": [[0.1, 0.1], [0.4, 0.5]], "nota": "infissi in legno scuro"},
    {"forma": "libera", "punti": [[0.6, 0.6], [0.9, 0.62], [0.85, 0.9], [0.62, 0.85]], "nota": "una panchina in pietra"},
]


def _png(colore=(120, 130, 140), larghezza=320, altezza=200) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), colore).save(uscita, format="PNG")
    return uscita.getvalue()


def _aree():
    return modulo_aree.da_elenco(AREE)


class ProviderCheRimanda(ProviderCheRende):
    """Restituisce l'immagine che riceve: un modello che non tocca niente."""

    def genera(self, richiesta):
        risultato = super().genera(richiesta)
        return Risultato(immagine=richiesta.immagine, formato="png", ricetta=risultato.ricetta, avvisi=[])


class ProviderCheRimpicciolisce(ProviderCheRende):
    def genera(self, richiesta):
        risultato = super().genera(richiesta)
        return Risultato(immagine=_png((10, 10, 10), 160, 100), formato="png", ricetta=risultato.ricetta, avvisi=[])


@pytest.fixture
def base(cartella, chiamate):
    """Un render dalla vista (passo 1): il render da ritoccare."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    return studio, coda, uno


def _ritocca(studio, da, aree=AREE, **altro):
    return studio.invia_ritocco({"vista": VISTA, "da": da, "aree": aree, "modello": NANO,
                                 "destinazione_mostrata": _dest(studio), **altro})["identificativo"]


# --- aree: come partono --------------------------------------------------------


def test_con_i_contorni_parte_un_immagine_sola_con_le_aree_disegnate():
    immagine = _png()
    ingresso, in_piu = modulo_aree.prepara(immagine, _aree(), modulo_aree.CONTORNI)
    assert in_piu == ()
    assert ingresso != immagine
    assert Image.open(io.BytesIO(ingresso)).size == (320, 200)


def test_con_la_maschera_parte_l_immagine_com_e_e_la_maschera_dopo():
    immagine = _png()
    ingresso, in_piu = modulo_aree.prepara(immagine, _aree(), modulo_aree.MASCHERA)
    assert ingresso == immagine and len(in_piu) == 1
    maschera = Image.open(io.BytesIO(in_piu[0])).convert("L")
    assert maschera.size == (320, 200)
    assert maschera.getpixel((5, 5)) == 0          # fuori: nero
    assert maschera.getpixel((40, 30)) == 255      # dentro il rettangolo, lontano dal numero: bianco


def test_il_prompt_del_ritocco_ha_una_riga_per_nota_numerata_come_l_area():
    testo = modulo_aree.prompt(modulo_aree.CONTORNI, _aree())
    assert testo.startswith(blocchi.AREE_CONTORNI.testo)
    assert "Area 1: infissi in legno scuro." in testo and "Area 2: una panchina in pietra." in testo
    assert modulo_aree.prompt(modulo_aree.MASCHERA, _aree()).startswith(blocchi.AREE_MASCHERA.testo)


def test_un_area_senza_nota_o_un_modo_sconosciuto_si_rifiutano():
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.da_elenco([{**AREE[0], "nota": "  "}])
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.da_elenco([])
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.prompt("pennello", _aree())


def test_la_misura_fuori_dalle_aree_e_zero_se_il_resto_non_cambia():
    immagine = _png()
    misura = modulo_aree.misura(immagine, immagine, _aree())
    assert misura["differenza_media"] == 0 and misura["quota_cambiata"] == 0
    assert misura["dimensioni_render"] == [320, 200] and misura["ridimensionata"] is False
    assert modulo_aree.testo_misura(misura).startswith("Fuori dalle aree: differenza media 0,0 su 255")
    assert modulo_aree.testo_misura(None) == "Fuori dalle aree: non misurato."


# --- il lavoro di ritocco nella coda ---------------------------------------------


def test_un_lavoro_con_aree_e_del_formato_3_e_gli_altri_restano_nel_2(cartella, chiamate, tmp_path):
    """Caso: una palette che legge il formato 2 smette di funzionare anche senza ritocchi."""
    render = tmp_path / "render.png"
    render.write_bytes(_png())
    crea = lambda _n: ProviderCheRende(chiamate)
    ritocco = metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova", modello=NANO,
                            parte_da="x", partenza=render, aree=_aree(), modo_aree="contorni", crea_provider=crea)
    normale = metti_in_coda(cartella, cartella / VISTA, blocchi.da_preset("rivista"), provider="prova",
                            modello=NANO, crea_provider=crea)
    dati = ritocco.a_dizionario()
    assert dati["formato"] == FORMATO_RITOCCO and dati["modo_aree"] == "contorni" and len(dati["aree"]) == 2
    assert normale.a_dizionario()["formato"] == FORMATO and "aree" not in normale.a_dizionario()
    assert Lavoro.da_dizionario(dati) == ritocco


def test_un_ritocco_senza_render_di_partenza_o_con_aree_rotte_non_parte(cartella, chiamate, tmp_path):
    crea = lambda _n: ProviderCheRende(chiamate)
    with pytest.raises(LavoroNonValido):
        metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova", modello=NANO,
                      aree=_aree(), modo_aree="contorni", crea_provider=crea)
    render = tmp_path / "render.png"
    render.write_bytes(_png())
    dati = metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova", modello=NANO,
                         parte_da="x", partenza=render, aree=_aree(), modo_aree="contorni",
                         crea_provider=crea).a_dizionario()
    for rotto in ({**dati, "aree": []}, {**dati, "modo_aree": "pennello"},
                  {**dati, "parte_da": None, "partenza": None}):
        with pytest.raises(LavoroNonValido):
            Lavoro.da_dizionario(rotto)


def test_la_coda_manda_il_render_con_i_contorni_e_misura_contro_quello_senza(base, cartella, chiamate):
    """Caso: la misura si fa contro l'immagine con i contorni, e i contorni contano come «cambiato»."""
    studio, coda, uno = base
    rit = _ritocca(studio, uno)
    coda.esegui_uno()
    albero = modulo_passi.Albero.leggi(cartella / VISTA)
    partenza = Path(albero.passo(uno)["render"]).read_bytes()
    richiesta = chiamate[-1]
    assert richiesta.immagine != partenza and richiesta.immagini_in_piu == ()
    assert "Area 2: una panchina in pietra." in richiesta.prompt
    stato = leggi_stato(cartella, rit)
    assert stato["stato"] == "fatto" and stato["fuori_aree"]["dimensioni_render"] == [320, 200]
    # il finto rende un colore pieno: fuori dalle aree e' cambiato quasi tutto
    assert stato["fuori_aree"]["quota_cambiata"] > 0.9


def test_con_la_maschera_un_modello_che_non_tocca_niente_misura_zero(base, cartella, chiamate, monkeypatch):
    studio, _coda_, uno = base
    monkeypatch.setattr(config, "RITOCCO_MODO_AREE", "maschera")
    rit = _ritocca(studio, uno)
    from core.coda import Coda
    Coda(cartella, crea_provider=lambda _n: ProviderCheRimanda(chiamate), dire=lambda _t: None).esegui_uno()
    richiesta = chiamate[-1]
    assert len(richiesta.immagini_in_piu) == 1
    assert richiesta.prompt.startswith(blocchi.AREE_MASCHERA.testo)
    misura = leggi_stato(cartella, rit)["fuori_aree"]
    assert misura["differenza_media"] == 0 and misura["quota_cambiata"] == 0


# --- Studio · Ritocca ------------------------------------------------------------


def test_il_ritocco_e_un_passo_figlio_del_render_ritoccato_con_aree_e_modo(base, cartella):
    studio, coda, uno = base
    rit = _ritocca(studio, uno)
    coda.esegui_uno()
    dati = studio.passi(VISTA)
    passo = next(p for p in dati["passi"] if p["identificativo"] == rit)
    assert passo["da"] == uno and passo["tipo"] == "ritocco" and passo["strada"] == ["0", "1", "2"]
    assert [a["nota"] for a in passo["aree"]] == ["infissi in legno scuro", "una panchina in pietra"]
    assert passo["modo_aree"] == config.RITOCCO_MODO_AREE
    assert passo["nome"].startswith("Ritocco · 2 note")
    assert passo["riassunto"] == "Ritocco del passo 1: area 1, infissi in legno scuro; area 2, una panchina in pietra"
    assert passo["fuori_aree_testo"].startswith("Fuori dalle aree: differenza media")
    assert passo["avviso"] is True  # e' la seconda generazione di fila
    # nel file dell'albero, leggibile a mano
    salvato = json.loads(modulo_passi.percorso(cartella / VISTA).read_text(encoding="utf-8"))
    assert next(p for p in salvato["passi"] if p["identificativo"] == rit)["aree"][0]["forma"] == "rettangolo"


def test_componi_ritocco_mostra_il_prompt_e_il_modo_prima_di_applica(base):
    studio, _coda_, uno = base
    composto = studio.componi_ritocco({"vista": VISTA, "da": uno, "aree": AREE})
    assert composto["note"] == 2 and composto["modo"] == config.RITOCCO_MODO_AREE
    assert "Area 1: infissi in legno scuro." in composto["prompt"]
    assert composto["generazioni"] == 2 and composto["ramo_nuovo"] is False


def test_una_nota_vuota_ferma_applica_e_non_scrive_il_lavoro(base, cartella):
    studio, _coda_, uno = base
    prima = len(list((cartella / "lavori" / "in-attesa").glob("*.json")))
    with pytest.raises(RichiestaStudioNonValida) as errore:
        _ritocca(studio, uno, aree=[AREE[0], {**AREE[1], "nota": ""}])
    assert "nota" in errore.value.fatto
    with pytest.raises(RichiestaStudioNonValida):
        _ritocca(studio, uno, aree=[])
    assert len(list((cartella / "lavori" / "in-attesa").glob("*.json"))) == prima


def test_dalla_vista_e_con_una_destinazione_diversa_non_si_ritocca(base):
    studio, _coda_, uno = base
    with pytest.raises(RichiestaStudioNonValida):
        _ritocca(studio, "0")
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia_ritocco({"vista": VISTA, "da": uno, "aree": AREE, "modello": NANO,
                              "destinazione_mostrata": "un altro servizio"})


def test_un_render_di_dimensione_diversa_si_dice_nella_misura(cartella, chiamate):
    """Caso: il risultato e' piu' piccolo e fuori dalle aree non si puo' rimettere il pixel di prima."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    rit = _ritocca(studio, uno)
    from core.coda import Coda
    Coda(cartella, crea_provider=lambda _n: ProviderCheRimpicciolisce(chiamate), dire=lambda _t: None).esegui_uno()
    passo = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == rit)
    assert passo["fuori_aree"]["ridimensionata"] is True
    assert "160x100, non della dimensione di partenza" in passo["fuori_aree_testo"]


def test_rifai_un_ritocco_tiene_aree_e_modo_anche_se_il_modo_cambia(base, cartella, chiamate, monkeypatch):
    studio, coda, uno = base
    rit = _ritocca(studio, uno)
    coda.esegui_uno()
    monkeypatch.setattr(config, "RITOCCO_MODO_AREE", "maschera")
    nuovo = studio.rifai(rit, {"destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == nuovo)
    assert passo["da"] == uno and passo["modo_aree"] == "contorni" and len(passo["aree"]) == 2
    assert chiamate[-1].immagini_in_piu == ()


def test_rifai_pulito_mette_le_note_come_richieste_e_dice_che_le_aree_non_valgono(base):
    """Caso: «Rifai pulito» perde le note del ritocco, o le manda come se sapesse ancora dove."""
    studio, coda, uno = base
    rit = _ritocca(studio, uno)
    coda.esegui_uno()
    sopra = _passo(studio, rit, "qualche persona"); coda.esegui_uno()
    composto = studio.componi_pulito({"vista": VISTA, "passo": sopra})
    assert composto["richieste"] == ["infissi in legno scuro", "una panchina in pietra", "qualche persona"]
    assert composto["senza_aree"] == ["2"]
    assert "Area 1" not in composto["prompt"]


def test_ritoccare_un_ritocco_apre_la_strada_sotto_di_lui(base):
    studio, coda, uno = base
    rit = _ritocca(studio, uno); coda.esegui_uno()
    sopra = _ritocca(studio, rit, aree=AREE[:1]); coda.esegui_uno()
    dati = studio.passi(VISTA)
    assert _per_numero(dati, "3")["identificativo"] == sopra
    assert _per_numero(dati, "3")["strada"] == ["0", "1", "2", "3"]


# --- rotte e pagina -------------------------------------------------------------


@pytest.fixture
def server(base):
    studio, coda, uno = base
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    yield servito, studio, coda, uno
    servito.shutdown()
    servito.server_close()


def test_le_rotte_del_ritocco_rispondono_e_vogliono_l_intestazione(server):
    """Caso: una pagina estranea manda un ritocco pagato con un POST."""
    servito, studio, _coda_, uno = server
    corpo = {"vista": VISTA, "da": uno, "aree": AREE}
    stato, _tipo, risposta = _chiedi(servito, "POST", "/api/ritocca/componi", corpo)
    assert stato == 200 and json.loads(risposta)["note"] == 2
    invio = {**corpo, "modello": NANO, "destinazione_mostrata": _dest(studio)}
    stato, _tipo, _r = _chiedi(servito, "POST", "/api/ritocca/invia", invio, intestazioni={"X-Airender": "0"})
    assert stato == 403
    stato, _tipo, risposta = _chiedi(servito, "POST", "/api/ritocca/invia", invio)
    assert stato == 200 and json.loads(risposta)["identificativo"]
    stato, _tipo, risposta = _chiedi(servito, "POST", "/api/ritocca/componi", {**corpo, "aree": [{**AREE[0], "nota": ""}]})
    assert stato == 400 and json.loads(risposta)["errore"]["cosa_fare"]


def test_lo_studio_dice_come_partono_le_aree_e_che_e_una_scelta(server):
    servito, *_resto = server
    _stato, _tipo, risposta = _chiedi(servito, "GET", "/api/studio")
    ritocco = json.loads(risposta)["ritocco"]
    assert ritocco == {"modo": config.RITOCCO_MODO_AREE,
                       "modo_nome": modulo_aree.NOMI_MODI[config.RITOCCO_MODO_AREE],
                       "origine": config.SCELTA}


def test_la_voce_ritocca_non_e_piu_grigia(server):
    servito, *_resto = server
    _stato, _tipo, pagina = _chiedi(servito, "GET", "/")
    assert b'class="voce-rotaia" href="#ritocca"' in pagina
    _stato, _tipo, script = _chiedi(servito, "GET", "/pagine/studio.js")
    assert "Anteprima delle funzioni in arrivo".encode() not in script
    assert "Clicca una superficie".encode() in script
