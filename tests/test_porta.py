"""«Porta su un'altra vista»: un render coerente su un'altra cattura (2026-11-04).

Riccardo vuole fotogrammi per il video da piu' viste Allplan, con lo stesso
stile e gli stessi ritocchi: la prima immagine all'inizio, le altre dopo.
"""

from __future__ import annotations

import pytest

from conftest import vista_shaded
from core import blocchi
from core.coda import Coda
from core.studio.servizio import RichiestaStudioNonValida, Studio
from test_passi import NANO, VISTA, ProviderCheRende, _genera, _passo, cartella, chiamate  # noqa: F401
from test_ritocca import AREE, _ritocca


class ProviderConDueImmagini(ProviderCheRende):
    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderConDueImmagini(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate):
    return Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None)

ALTRA = "vista-2.png"


@pytest.fixture
def strada(cartella, chiamate):
    """Vista 1: render, un passo a parole, un ritocco con nota. Poi una seconda cattura."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    due = _passo(studio, uno, "due alberi davanti al fronte"); coda.esegui_uno()
    tre = _ritocca(studio, due); coda.esegui_uno()
    (cartella / ALTRA).write_bytes(vista_shaded(640, 400))
    return studio, coda, {"1": uno, "2": due, "3": tre}


def _dest_rif(studio):
    return studio.destinazione(NANO, riferimento=True)["destinazione"]


def test_l_anteprima_dice_stile_modello_richieste_e_viste_su_cui_portare(strada):
    """Caso: si porta su un'altra vista senza sapere con quale stile e quali ritocchi."""
    studio, _coda_, ids = strada
    anteprima = studio.anteprima_porta(ids["3"])
    assert anteprima["stile"] == blocchi.PRESET_STILE["rivista"].nome
    assert anteprima["modello"] == NANO
    assert anteprima["richieste"] == ["due alberi davanti al fronte", *[a["nota"] for a in AREE]]
    assert anteprima["viste"] == [ALTRA]  # non la vista da cui viene


def test_porta_parte_dalla_vista_nuova_con_l_immagine_come_seconda_e_la_frase_di_coerenza(strada, cartella, chiamate):
    """Caso: la vista nuova esce con un altro stile, o senza le sedie aggiunte col ritocco."""
    studio, coda, ids = strada
    render = studio.file_render(ids["3"]).read_bytes()
    nuovo = studio.porta_su_vista(ids["3"], {"vista": ALTRA, "destinazione_mostrata": _dest_rif(studio)})
    coda.esegui_uno()
    ultima = chiamate[-1]
    assert ultima.immagine == (cartella / ALTRA).read_bytes()
    assert ultima.immagini_in_piu == (render,)
    assert blocchi.RIFERIMENTO_COERENZA.testo in ultima.prompt
    assert blocchi.RIFERIMENTO_STILE.testo not in ultima.prompt
    assert "due alberi davanti al fronte" in ultima.prompt
    for area in AREE:
        assert area["nota"] in ultima.prompt
    riga = studio.passi(ALTRA)["passi"]
    assert [p["numero"] for p in riga] == ["1"] and riga[0]["identificativo"] == nuovo["identificativo"]


def test_porta_sulla_stessa_vista_rimanda_a_variante(strada):
    """Caso: si paga un invio che e' solo una Variante con un nome diverso."""
    studio, _coda_, ids = strada
    with pytest.raises(RichiestaStudioNonValida, match="Variante"):
        studio.porta_su_vista(ids["3"], {"vista": VISTA, "destinazione_mostrata": _dest_rif(studio)})


def test_porta_rifiuta_una_destinazione_diversa_da_quella_mostrata(strada):
    """Caso: la pagina ha mostrato un servizio e la vista parte verso un altro (regola 5)."""
    studio, _coda_, ids = strada
    with pytest.raises(RichiestaStudioNonValida):
        studio.porta_su_vista(ids["3"], {"vista": ALTRA, "destinazione_mostrata": "un altro servizio"})
