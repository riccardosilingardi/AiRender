"""Lo strato provider: cosa parte davvero, e cosa succede quando va storto.

Nessuna chiamata vera. Il trasporto e' finto, l'orologio e' finto, la chiave
non esiste: questa suite gira su una macchina senza rete e senza account.
"""

from __future__ import annotations

import base64

import pytest

from conftest import (
    OrologioFinto,
    TrasportoFinto,
    maschera_netta,
    risposta_lavoro,
    vista_shaded,
)
from core import config, grana, provider as registro
from core.errori import ChiaveMancante, ErroreProvider, ProviderSconosciuto
from core.provider.base import (
    Provider,
    RichiestaGenerazione,
    RichiestaRegione,
    Risultato,
)
from core.provider.magnific import (
    INTESTAZIONE_CHIAVE,
    ProviderMagnific,
    formato_piu_vicino,
)
from core.ricetta import Ricetta, impronta


def richiesta(dati: bytes, **cambi) -> RichiestaGenerazione:
    base = dict(
        immagine=dati,
        prompt="prompt tecnico",
        preset="base",
        preset_versione="1",
        modello="realism",
        grana=grana.MEDIA,
        dettaglio_grana=grana.dettaglio(grana.MEDIA),
        testo_utente="piu' caldo",
    )
    base.update(cambi)
    return RichiestaGenerazione(**base)


def provider(trasporto, chiave="chiave-di-prova"):
    orologio = OrologioFinto()
    return ProviderMagnific(
        chiave=chiave,
        trasporto=trasporto,
        attesa=orologio.attendi,
        orologio=orologio.leggi,
    )


def trasporto_che_riesce(immagine=b"immagine-generata"):
    return TrasportoFinto(
        [
            risposta_lavoro("CREATED"),
            risposta_lavoro("COMPLETED", prodotti=["https://esempio/render.png"]),
        ],
        immagine=immagine,
    )


# --- generazione con riferimento strutturale ---------------------------------


def test_la_vista_parte_come_riferimento_strutturale_con_la_sua_forza():
    """Caso: e' l'unica cosa che decide se il prodotto esiste."""
    dati = vista_shaded(640, 480)
    trasporto = trasporto_che_riesce()
    risultato = provider(trasporto).genera(richiesta(dati, forza_struttura=80))

    _url, intestazioni, corpo = trasporto.poste[0]
    assert corpo["structure_reference"] == base64.b64encode(dati).decode("ascii")
    assert corpo["structure_strength"] == 80
    assert corpo["model"] == "realism"
    assert corpo["creative_detailing"] == grana.dettaglio(grana.MEDIA)
    assert corpo["fixed_generation"] is False
    assert intestazioni[INTESTAZIONE_CHIAVE] == "chiave-di-prova"
    assert risultato.immagine == b"immagine-generata"


def test_il_formato_chiesto_e_quello_della_vista_altrimenti_l_edificio_si_schiaccia():
    """Caso: una vista panoramica chiesta quadrata torna deformata."""
    trasporto = trasporto_che_riesce()
    provider(trasporto).genera(richiesta(vista_shaded(1600, 900)))
    assert trasporto.poste[0][2]["aspect_ratio"] == "widescreen_16_9"
    assert formato_piu_vicino(900, 1600) == "social_story_9_16"


def test_lo_scostamento_della_geometria_torna_non_misurato_non_zero():
    """Caso: un numero inventato qui e' peggio di nessun numero."""
    risultato = provider(trasporto_che_riesce()).genera(richiesta(vista_shaded(512, 512)))
    assert risultato.scostamento_geometria is None
    assert any("non misurato" in avviso for avviso in risultato.avvisi)


def test_la_ricetta_porta_modello_preset_e_versioni_non_solo_il_seme():
    """Caso: i provider cambiano i modelli sotto lo stesso nome."""
    dati = vista_shaded(512, 512)
    risultato = provider(trasporto_che_riesce()).genera(richiesta(dati))
    ricetta = risultato.ricetta
    assert ricetta.modello == "realism"
    assert ricetta.preset == "base" and ricetta.preset_versione == "1"
    assert ricetta.impronta_sorgente == impronta(dati)
    assert ricetta.motore_versione
    assert Ricetta.da_json(ricetta.a_json()) == ricetta


# --- riesecuzione ------------------------------------------------------------


def test_la_riesecuzione_chiede_la_generazione_fissa():
    """Caso: rifare un livello a parametri identici, non "qualcosa di simile"."""
    dati = vista_shaded(512, 512)
    prima = provider(trasporto_che_riesce()).genera(richiesta(dati))
    trasporto = trasporto_che_riesce()
    dopo = provider(trasporto).riesegui(prima.ricetta, dati)
    assert trasporto.poste[0][2]["fixed_generation"] is True
    assert dopo.ricetta.prompt == prima.ricetta.prompt


def test_la_riesecuzione_con_un_altra_vista_si_ferma_prima_di_spendere():
    """Caso: la vista di partenza e' stata risalvata. Non e' piu' lo stesso livello."""
    dati = vista_shaded(512, 512)
    prima = provider(trasporto_che_riesce()).genera(richiesta(dati))
    trasporto = TrasportoFinto()
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).riesegui(prima.ricetta, vista_shaded(512, 512, seme=99))
    assert trasporto.poste == []
    assert "vista originale" in errore.value.cosa_fare


# --- modifica di una regione -------------------------------------------------


def test_la_maschera_parte_sfumata_e_col_suo_avviso_sui_riflessi():
    """Caso: il riempimento mascherato non ricalcola riflessi e luce di rimbalzo."""
    trasporto = TrasportoFinto(
        [risposta_lavoro("COMPLETED", prodotti=["https://esempio/ritocco.png"])]
    )
    maschera = maschera_netta()
    risultato = provider(trasporto).modifica_regione(
        RichiestaRegione(
            immagine=vista_shaded(600, 400), maschera=maschera, prompt="mattone vecchio"
        )
    )
    _url, _intestazioni, corpo = trasporto.poste[0]
    assert corpo["prompt"] == "mattone vecchio"
    assert corpo["mask"] != base64.b64encode(maschera).decode("ascii")
    assert any("rimbalzo" in avviso for avviso in risultato.avvisi)
    assert risultato.scostamento_geometria is None


# --- quando va storto --------------------------------------------------------


def test_senza_chiave_non_parte_niente_e_lo_dice_in_italiano():
    """Caso: l'utente non ha ancora messo la sua chiave."""
    trasporto = TrasportoFinto()
    with pytest.raises(ChiaveMancante) as errore:
        ProviderMagnific(chiave=None, trasporto=trasporto).genera(
            richiesta(vista_shaded(512, 512))
        )
    assert trasporto.poste == []
    assert "MAGNIFIC_API_KEY" in errore.value.cosa_fare


def test_una_chiave_rifiutata_non_diventa_un_401_sullo_schermo():
    """Caso: la chiave e' scaduta. "401" non dice a nessuno cosa fare."""
    trasporto = TrasportoFinto([(401, {"message": "invalid api key"})])
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).genera(richiesta(vista_shaded(512, 512)))
    assert errore.value.stato == 401
    assert "chiave" in errore.value.fatto
    assert "MAGNIFIC_API_KEY" in errore.value.cosa_fare


def test_il_limite_di_chiamate_dice_di_aspettare_non_di_riprovare_subito():
    """Caso: troppe generazioni ravvicinate dalla griglia delle miniature."""
    trasporto = TrasportoFinto([(429, {"message": "rate limit"})])
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).genera(richiesta(vista_shaded(512, 512)))
    assert "Aspetta" in errore.value.cosa_fare


def test_un_servizio_rotto_dice_che_non_e_colpa_dell_utente():
    """Caso: 500 dall'altra parte. L'utente non deve mettersi a cercare."""
    trasporto = TrasportoFinto([(500, "gateway error")])
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).genera(richiesta(vista_shaded(512, 512)))
    assert "non tuo" in errore.value.cosa_fare


def test_il_lavoro_fallito_dall_altra_parte_non_diventa_un_immagine_vuota():
    """Caso: il servizio accetta e poi rinuncia."""
    trasporto = TrasportoFinto([risposta_lavoro("FAILED")])
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).genera(richiesta(vista_shaded(512, 512)))
    assert "interrotto" in errore.value.fatto


def test_una_risposta_senza_immagine_lo_dice_invece_di_esplodere():
    """Caso: il servizio dice COMPLETED e non allega niente."""
    trasporto = TrasportoFinto([risposta_lavoro("COMPLETED", prodotti=[])])
    with pytest.raises(ErroreProvider) as errore:
        provider(trasporto).genera(richiesta(vista_shaded(512, 512)))
    assert "magnific.py" in errore.value.cosa_fare


# --- il registro -------------------------------------------------------------


def test_un_secondo_provider_si_aggiunge_senza_toccare_il_resto(monkeypatch):
    """Caso: il piano B del PRD. Deve costare un file e una riga."""

    class ProviderFinto(Provider):
        nome = "finto"
        destinazione = "Servizio di prova (nessuna rete)"

        def genera(self, richiesta):
            return Risultato(b"x", "png", _ricetta_vuota())

        def modifica_regione(self, richiesta):
            return Risultato(b"x", "png", _ricetta_vuota())

        def riesegui(self, ricetta, immagine):
            return Risultato(b"x", "png", ricetta)

    monkeypatch.setitem(registro.REGISTRO, ProviderFinto.nome, ProviderFinto)
    motore = registro.crea("finto")
    assert isinstance(motore, Provider)
    assert "finto" in registro.nomi()


def test_un_provider_che_non_esiste_elenca_quelli_che_esistono():
    """Caso: un preset punta a un motore che e' stato tolto."""
    with pytest.raises(ProviderSconosciuto) as errore:
        registro.crea("weavy")
    assert "magnific" in errore.value.cosa_fare


def test_ogni_provider_dichiara_dove_manda_l_immagine():
    """Caso: il pubblico lavora sotto NDA. Il nome del servizio si vede prima."""
    for nome, classe in registro.REGISTRO.items():
        assert classe.destinazione, f"{nome} non dice dove manda le immagini"


def _ricetta_vuota() -> Ricetta:
    return Ricetta(
        provider="finto",
        modello="",
        preset="",
        preset_versione="",
        prompt="",
        testo_utente="",
        grana=grana.MEDIA,
        dettaglio_grana=config.GRANA_MEDIA,
        forza_struttura=config.FORZA_STRUTTURA_PREDEFINITA,
        risoluzione=config.RISOLUZIONE_PREDEFINITA,
        aspetto="square_1_1",
        generazione_fissa=False,
        impronta_sorgente="",
    )
