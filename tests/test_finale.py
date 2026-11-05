"""«Finale»: il render ingrandito con Magnific Precision V2 dal Router. Nessuna rete."""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from core import config, coda as modulo_coda
from core.coda import Lavoro, LavoroNonValido, leggi_stato
from core.provider import comfy
from core.provider.base import RichiestaGenerazione, Risultato
from core.studio.servizio import RichiestaStudioNonValida, Studio
from test_passi import (NANO, VISTA, ProviderCheRende, _dest, _genera, _per_numero, cartella,  # noqa: F401
                        chiamate)

FINALE = comfy.MODELLO_FINALE


class ProviderCheIngrandisce(ProviderCheRende):
    """Per Finale restituisce l'immagine ricevuta ingrandita, come farebbe Magnific."""

    def genera(self, richiesta):
        risultato = super().genera(richiesta)
        if richiesta.modello != FINALE:
            return risultato
        with Image.open(io.BytesIO(richiesta.immagine)) as im:
            grande = im.resize((im.width * richiesta.ingrandimento, im.height * richiesta.ingrandimento))
            uscita = io.BytesIO()
            grande.save(uscita, "PNG")
        return Risultato(immagine=uscita.getvalue(), formato="png", ricetta=risultato.ricetta, avvisi=[])


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderCheIngrandisce(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate):
    return modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderCheIngrandisce(chiamate), dire=lambda _t: None)


def _richiesta(ingrandimento=2, tipo="foto"):
    return RichiestaGenerazione(immagine=b"\x89PNG\r\n\x1a\n" + b"0" * 20, prompt="", preset="", preset_versione="",
                                modello=FINALE, grana="", dettaglio_grana=0, ingrandimento=ingrandimento, tipo_finale=tipo)


def test_il_corpo_del_finale_e_quello_della_documentazione_del_router():
    corpo = comfy.SCHEMI[FINALE].corpo(_richiesta(4, "illustrazione"))
    assert corpo["scale_factor"] == 4 and corpo["flavor"] == "sublime"
    assert set(corpo) == {"image", "scale_factor", "flavor"}
    assert comfy.SCHEMI[FINALE].verificato_il == "" and not comfy.SCHEMI[FINALE].piu_immagini


def test_l_immagine_del_finale_si_legge_da_data_generated():
    uscita = {"data": {"generated": ["https://esempio/upscaled.png"], "status": "COMPLETED"}}
    assert comfy.SCHEMI[FINALE].immagine(uscita) == ("url", "https://esempio/upscaled.png")
    with pytest.raises(Exception):
        comfy.SCHEMI[FINALE].immagine({"data": {"generated": []}})


def test_un_ingrandimento_che_lo_studio_non_offre_non_parte():
    with pytest.raises(Exception):
        comfy.SCHEMI[FINALE].corpo(_richiesta(16))


def test_finale_e_un_passo_figlio_del_render_ingrandito(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    composto = studio.componi_finale({"vista": VISTA, "da": uno, "ingrandimento": 2})
    assert composto["partenza"] == "320 × 200" and composto["uscita"] == "640 × 400"
    assert composto["destinazione"]["modello"] == FINALE
    dati = {"vista": VISTA, "da": uno, "ingrandimento": 2, "tipo": "foto",
            "destinazione_mostrata": composto["destinazione"]["destinazione"]}
    due = studio.invia_finale(dati)["identificativo"]
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{due}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_FINALE and scritto["finale"] == {"ingrandimento": 2, "tipo": "foto"}
    assert Lavoro.da_dizionario(scritto).finale == {"ingrandimento": 2, "tipo": "foto"}
    coda.esegui_uno()
    assert leggi_stato(cartella, due)["stato"] == "fatto"
    assert chiamate[-1].modello == FINALE and chiamate[-1].ingrandimento == 2
    passo = _per_numero(studio.passi(VISTA), "2")
    assert passo["identificativo"] == due and passo["da"] == uno
    lavoro = studio.lavoro(due)
    assert lavoro["preset_nome"] == "Finale ×2" and "ingrandito 2 volte" in lavoro["riassunto"]


def test_finale_dalla_vista_o_con_altro_si_rifiuta(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    with pytest.raises(RichiestaStudioNonValida):
        studio.componi_finale({"vista": VISTA, "da": uno, "ingrandimento": 3})
    with pytest.raises(RichiestaStudioNonValida):
        studio.componi_finale({"vista": VISTA, "da": uno, "ingrandimento": 2, "tipo": "acquerello"})
    with pytest.raises(LavoroNonValido):
        modulo_coda.metti_in_coda(cartella, cartella / VISTA, studio._scelte({}), provider="prova",  # pylint: disable=protected-access
                                  modello=FINALE, finale={"ingrandimento": 2, "tipo": "foto"},
                                  crea_provider=lambda _n: ProviderCheIngrandisce([]))
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_un_lavoro_finale_rotto_non_si_legge():
    base = {"formato": modulo_coda.FORMATO_FINALE, "identificativo": "x", "vista": "v.png", "provider": "prova",
            "modello": FINALE, "destinazione": "d", "parte_da": "a", "partenza": "a.png"}
    for finale in (None, {"ingrandimento": 8, "tipo": "foto"}, {"ingrandimento": True, "tipo": "foto"}):
        with pytest.raises(LavoroNonValido):
            Lavoro.da_dizionario({**base, "finale": finale})
    with pytest.raises(LavoroNonValido):
        Lavoro.da_dizionario({**base, "finale": {"ingrandimento": 2, "tipo": "foto"}, "richieste": ["notte"]})

