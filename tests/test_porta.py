"""«Porta su un'altra vista»: un render coerente su un'altra cattura (2026-11-04).

Riccardo vuole fotogrammi per il video da piu' viste Allplan, con lo stesso
stile e gli stessi ritocchi: la prima immagine all'inizio, le altre dopo.
"""

from __future__ import annotations

import pytest

from conftest import vista_shaded
from core import blocchi, config, ricette_utente
from core.coda import Coda
from core.errori import ErroreAirender
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


# --- Ricetta su piu' viste e Le mie ricette (2026-11-09, PR 4 dei flussi) ---------

TERZA = "vista-3.png"


@pytest.fixture
def tre_viste(strada, cartella):
    (cartella / TERZA).write_bytes(vista_shaded(640, 400))
    return strada


def test_l_anteprima_elenca_i_passi_in_italiano_e_il_costo_per_quante_viste(tre_viste):
    """Caso: la ricetta dice «richieste» in inglese e non si capisce cosa si rifa'."""
    studio, _coda_, ids = tre_viste
    anteprima = studio.anteprima_porta(ids["3"])
    assert anteprima["passi"][0] == f"Genera · {blocchi.PRESET_STILE['rivista'].nome}"
    assert anteprima["passi"][1].startswith("Passo · Due alberi")
    assert anteprima["passi"][2].startswith("Ritocco")
    assert len(anteprima["passi"]) == 3
    assert sorted(anteprima["viste"]) == [ALTRA, TERZA]
    assert len(anteprima["costi"]) == config.RICETTA_VISTE_MASSIME


def test_la_ricetta_parte_su_piu_viste_un_render_per_vista(tre_viste, cartella, chiamate):
    """Caso: tre viste per una tavola, rifatte a mano una per una."""
    studio, coda, ids = tre_viste
    render = studio.file_render(ids["3"]).read_bytes()
    risposta = studio.porta_su_vista(ids["3"], {"viste": [ALTRA, TERZA], "destinazione_mostrata": _dest_rif(studio)})
    assert risposta["viste"] == [ALTRA, TERZA] and len(risposta["identificativi"]) == 2
    prima = len(chiamate)
    coda.esegui_uno(); coda.esegui_uno()
    partite = chiamate[prima:]
    assert [c.immagine for c in partite] == [(cartella / ALTRA).read_bytes(), (cartella / TERZA).read_bytes()]
    assert all(c.immagini_in_piu == (render,) for c in partite)
    assert all("due alberi davanti al fronte" in c.prompt for c in partite)
    assert [p["numero"] for p in studio.passi(TERZA)["passi"]] == ["1"]


@pytest.mark.parametrize("viste, parola", [
    ([], "almeno una"),
    ([ALTRA, ALTRA], "due volte"),
    ([ALTRA, VISTA], "Variante"),
    ([ALTRA, "non-c-e.png"], "non"),
])
def test_con_una_vista_sbagliata_non_parte_niente_nemmeno_sulle_altre(tre_viste, cartella, viste, parola):
    """Caso: la seconda vista non va, ma la prima e' gia' partita e pagata."""
    studio, _coda_, ids = tre_viste
    with pytest.raises(ErroreAirender, match=parola):
        studio.porta_su_vista(ids["3"], {"viste": viste, "destinazione_mostrata": _dest_rif(studio)})
    assert studio.passi(ALTRA)["passi"] == []


def test_oltre_il_massimo_di_viste_si_rifiuta_prima_di_spendere(tre_viste, cartella, monkeypatch):
    studio, _coda_, ids = tre_viste
    monkeypatch.setattr(config, "RICETTA_VISTE_MASSIME", 1)
    with pytest.raises(RichiestaStudioNonValida, match="al massimo su 1"):
        studio.porta_su_vista(ids["3"], {"viste": [ALTRA, TERZA], "destinazione_mostrata": _dest_rif(studio)})
    assert studio.passi(ALTRA)["passi"] == []


def test_una_destinazione_diversa_ferma_tutte_le_viste(tre_viste):
    """Caso: regola 5 con piu' viste, la prima parte prima che si scopra la destinazione sbagliata."""
    studio, _coda_, ids = tre_viste
    with pytest.raises(RichiestaStudioNonValida, match="Non ho inviato niente"):
        studio.porta_su_vista(ids["3"], {"viste": [ALTRA, TERZA], "destinazione_mostrata": "altro"})
    assert studio.passi(ALTRA)["passi"] == [] and studio.passi(TERZA)["passi"] == []


def test_una_ricetta_salvata_si_rifa_dopo_su_una_vista_catturata_piu_tardi(strada, cartella, chiamate):
    """Caso: la vista nuova arriva domani, e i passi di oggi vanno ricordati a mano."""
    studio, coda, ids = strada
    elenco = studio.salva_mia_ricetta({"lavoro": ids["3"], "nome": "  Ora blu  con persone "})
    voce = elenco["ricette"][0]
    assert voce["nome"] == "Ora blu con persone" and voce["usabile"] and voce["vista"] == VISTA
    assert voce["passi"] == studio.anteprima_porta(ids["3"])["passi"]
    assert (cartella / ricette_utente.NOME_FILE).is_file()
    (cartella / TERZA).write_bytes(vista_shaded(640, 400))  # catturata dopo
    risposta = studio.usa_mia_ricetta({"nome": "ora blu con persone", "viste": [TERZA],
                                       "destinazione_mostrata": _dest_rif(studio)})
    coda.esegui_uno()
    assert chiamate[-1].immagine == (cartella / TERZA).read_bytes()
    assert studio.passi(TERZA)["passi"][0]["identificativo"] == risposta["identificativo"]


def test_due_ricette_con_lo_stesso_nome_si_sostituiscono_solo_se_lo_si_dice(strada):
    studio, _coda_, ids = strada
    studio.salva_mia_ricetta({"lavoro": ids["3"], "nome": "Notte"})
    with pytest.raises(ricette_utente.RicettaUtenteNonValida, match="gia'"):
        studio.salva_mia_ricetta({"lavoro": ids["2"], "nome": "notte"})
    elenco = studio.salva_mia_ricetta({"lavoro": ids["2"], "nome": "notte", "sovrascrivi": True})
    assert [r["lavoro"] for r in elenco["ricette"]] == [ids["2"]]
    assert studio.elimina_mia_ricetta({"nome": "Notte"})["ricette"] == []


def test_una_ricetta_il_cui_render_non_c_e_piu_lo_dice_e_non_parte(strada, cartella):
    """Caso: il render da cui viene la ricetta e' stato tolto; la ricetta partirebbe a vuoto."""
    studio, _coda_, ids = strada
    studio.salva_mia_ricetta({"lavoro": ids["3"], "nome": "Persa"})
    studio.file_render(ids["3"]).unlink()
    voce = studio.mie_ricette()["ricette"][0]
    assert voce["usabile"] is False and voce["perche_no"]
    assert voce["passi"]  # i nomi salvati restano, per sapere cos'era


def test_un_file_delle_ricette_che_non_si_legge_si_mette_da_parte(cartella):
    (cartella / ricette_utente.NOME_FILE).write_text("{non json", encoding="utf-8")
    elenco = ricette_utente.leggi(cartella)
    assert elenco.ricette == [] and "non si legge" in elenco.problema
    assert not (cartella / ricette_utente.NOME_FILE).exists()
    assert list(cartella.glob("ricette-utente.non-letto-*.json"))
