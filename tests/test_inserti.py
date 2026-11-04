"""Rif. di oggetti e persone: fino a INSERTI_MASSIMO immagini da mettere nell'immagine di partenza.

Valgono in Genera, Cambia e Ritocca; partono dopo tutte le altre immagini e il
prompt dice quale immagine e' quale Rif. Nessuna rete: provider finti.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from core import aree as modulo_aree, blocchi, coda as modulo_coda, config
from core.coda import Lavoro, LavoroNonValido, leggi_stato
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_passi import NANO, VISTA, ProviderCheRende, _dest, _per_numero, cartella, chiamate  # noqa: F401

KONTEXT = MODELLI[1].identificativo
NOTA = {"forma": "rettangolo", "punti": [[0.1, 0.1], [0.4, 0.5]], "nota": "una poltrona"}


class ProviderConRif(ProviderCheRende):
    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _jpeg(colore) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (200, 160), colore).save(uscita, "JPEG")
    return uscita.getvalue()


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderConRif(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate):
    return modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderConRif(chiamate), dire=lambda _t: None)


def _rif(studio, *colori):
    return [studio.carica_riferimento(_jpeg(c))["nome"] for c in colori]


def _genera(studio, **altro):
    return studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(),
                         "preset": "rivista", "modello": NANO, "destinazione_mostrata": _dest(studio),
                         **altro})["identificativo"]


# --- prompt ----------------------------------------------------------------------


def test_il_prompt_dice_quale_immagine_e_quale_rif_e_la_regola_degli_inserti():
    testo = blocchi.aggiungi_inserti("Base text.", 3, 2)
    assert "Rif. 1 is image 3" in testo and "Rif. 2 is image 4" in testo
    assert blocchi.INSERTI_REGOLA.testo in testo
    assert blocchi.aggiungi_inserti("Base text.", 2, 0) == "Base text."


def test_la_prima_immagine_dei_rif_viene_dopo_maschera_riferimento_e_materiali():
    assert modulo_coda.prima_immagine_inserti(False, False, 0) == 2
    assert modulo_coda.prima_immagine_inserti(True, True, 2) == 6


def test_una_nota_che_cita_un_rif_lo_dice_nella_sua_riga():
    aree = modulo_aree.da_elenco([{**NOTA, "inserto": 1}])
    assert "Area 1: una poltrona; use the object or person shown in Rif. 1." in modulo_aree.prompt(modulo_aree.CONTORNI, aree)


@pytest.mark.parametrize("valore", [0, config.INSERTI_MASSIMO + 1, True, "1"])
def test_un_numero_di_rif_fuori_misura_nella_nota_si_rifiuta(valore):
    with pytest.raises(modulo_aree.AreaNonValida):
        modulo_aree.da_elenco([{**NOTA, "inserto": valore}])


# --- Genera ----------------------------------------------------------------------


def test_genera_con_due_rif_li_manda_per_ultimi_e_il_lavoro_e_del_formato_7(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nomi = _rif(studio, (200, 0, 0), (0, 0, 200))
    destinazione = studio.destinazione(NANO, inserti=2)
    assert destinazione["immagini"] == 3 and "2 Rif. di oggetti e persone" in destinazione["cosa_parte"]
    identificativo = _genera(studio, inserti=nomi)
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_INSERTI and len(scritto["inserti"]) == 2
    assert Lavoro.da_dizionario(scritto).inserti == tuple(scritto["inserti"])

    _coda(cartella, chiamate).esegui_uno()
    assert leggi_stato(cartella, identificativo)["stato"] == "fatto"
    (richiesta,) = chiamate
    assert len(richiesta.immagini_in_piu) == 2
    with Image.open(io.BytesIO(richiesta.immagini_in_piu[1])) as seconda:
        rosso, _verde, blu = seconda.getpixel((50, 50))
        assert blu > rosso
    assert "Rif. 1 is image 2" in richiesta.prompt and "Rif. 2 is image 3" in richiesta.prompt


def test_con_un_modello_a_una_sola_immagine_i_rif_non_partono(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nomi = _rif(studio, (200, 0, 0))
    assert studio.destinazione(KONTEXT, inserti=1)["inserti_non_accettati"]
    with pytest.raises((RichiestaStudioNonValida, LavoroNonValido)):
        studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(), "preset": "rivista",
                      "modello": KONTEXT, "destinazione_mostrata": studio.destinazione(KONTEXT)["destinazione"],
                      "inserti": nomi})
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_oltre_il_massimo_o_un_percorso_al_posto_del_nome_si_rifiuta(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nomi = _rif(studio, *[(i * 40, 10, 10) for i in range(config.INSERTI_MASSIMO + 1)])
    with pytest.raises(RichiestaStudioNonValida):
        _genera(studio, inserti=nomi)
    with pytest.raises(RichiestaStudioNonValida):
        _genera(studio, inserti=["../vista-1.png"])
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


# --- Cambia e Ritocca -------------------------------------------------------------


def test_cambia_con_un_rif_lo_manda_sul_render_del_passo(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    (nome,) = _rif(studio, (0, 200, 0))
    composto = studio.componi_passo({"vista": VISTA, "da": uno, "testo": "metti la poltrona del Rif. 1", "inserti": [nome]})
    assert "Rif. 1 is image 2" in composto["prompt"]
    due = studio.invia_passo({"vista": VISTA, "da": uno, "testo": "metti la poltrona del Rif. 1", "modello": NANO,
                              "destinazione_mostrata": _dest(studio), "inserti": [nome]})["identificativo"]
    coda.esegui_uno()
    assert leggi_stato(cartella, due)["stato"] == "fatto"
    assert len(chiamate[-1].immagini_in_piu) == 1


def test_ritocca_con_la_foto_nella_nota_e_rifai_la_rimanda(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    (nome,) = _rif(studio, (0, 200, 0))
    dati = {"vista": VISTA, "da": uno, "aree": [{**NOTA, "inserto": 1}], "modello": NANO,
            "destinazione_mostrata": _dest(studio), "inserti": [nome]}
    assert "Rif. 1 is image 2" in studio.componi_ritocco(dati)["prompt"]
    due = studio.invia_ritocco(dati)["identificativo"]
    coda.esegui_uno()
    assert leggi_stato(cartella, due)["stato"] == "fatto"
    assert "use the object or person shown in Rif. 1" in chiamate[-1].prompt
    studio.rifai(due, {"destinazione_mostrata": _dest(studio)})
    coda.esegui_uno()
    assert len(chiamate[-1].immagini_in_piu) == 1
    assert _per_numero(studio.passi(VISTA), "2")["identificativo"] == due


def test_una_nota_che_cita_un_rif_che_non_c_e_si_ferma_prima_di_comporre(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    with pytest.raises(RichiestaStudioNonValida, match="Rif. 1"):
        studio.componi_ritocco({"vista": VISTA, "da": uno, "aree": [{**NOTA, "inserto": 1}]})


# --- Stile da esempi ---------------------------------------------------------------


def test_stile_da_esempi_manda_riferimento_ed_esempi_dopo_la_vista_e_i_rif_dopo(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    primo, secondo, terzo, rif = _rif(studio, (200, 0, 0), (0, 200, 0), (0, 0, 200), (90, 90, 90))
    destinazione = studio.destinazione(NANO, riferimento=True, esempi=2, inserti=1)
    assert destinazione["immagini"] == 5 and "3 esempi di stile" in destinazione["cosa_parte"]
    composto = studio.componi({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(),
                               "riferimento": primo, "esempi": [secondo, terzo], "inserti": [rif]})
    assert "Images 2 to 4 are example renders" in composto["prompt"] and "Rif. 1 is image 5" in composto["prompt"]
    identificativo = _genera(studio, riferimento=primo, esempi=[secondo, terzo], inserti=[rif])
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_ESEMPI and len(scritto["esempi"]) == 2
    assert Lavoro.da_dizionario(scritto).inserti == tuple(scritto["inserti"])
    _coda(cartella, chiamate).esegui_uno()
    assert leggi_stato(cartella, identificativo)["stato"] == "fatto"
    (richiesta,) = chiamate
    assert len(richiesta.immagini_in_piu) == 4
    assert richiesta.prompt == composto["prompt"] or "Images 2 to 4" in richiesta.prompt


def test_gli_esempi_senza_riferimento_o_con_il_fotoinserimento_si_rifiutano(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    (uno,) = _rif(studio, (10, 10, 10))
    with pytest.raises(RichiestaStudioNonValida):
        _genera(studio, esempi=[uno])
    with pytest.raises(RichiestaStudioNonValida):
        studio._esempi_scelti({"esempi": [uno]}, contesto=True)  # pylint: disable=protected-access
    assert not list(cartella.glob("lavori/in-attesa/*.json"))
