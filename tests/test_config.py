"""Ogni costante di core/config.py, e il caso che protegge.

Un test per costante, col caso nel nome. L'ultimo test di questo file
controlla che non ne manchi nessuna: se domani si aggiunge una soglia senza
il suo caso, la suite lo dice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import (
    OrologioFinto,
    TrasportoFinto,
    maschera_netta,
    risposta_lavoro,
    vista_piatta,
    vista_shaded,
    vista_wireframe,
)
from core import config, grana, immagine, idoneita
from core.errori import ErroreProvider
from core.provider.base import RichiestaGenerazione, RichiestaRegione
from core.provider.magnific import ProviderMagnific
from core.provider.trasporto import TrasportoHTTP


def _richiesta(dati: bytes, **cambi) -> RichiestaGenerazione:
    base = dict(
        immagine=dati,
        prompt="prompt di prova",
        preset="base",
        preset_versione="1",
        modello="realism",
        grana=grana.MEDIA,
        dettaglio_grana=grana.dettaglio(grana.MEDIA),
    )
    base.update(cambi)
    return RichiestaGenerazione(**base)


def _provider(trasporto, orologio=None):
    orologio = orologio or OrologioFinto()
    return ProviderMagnific(
        chiave="chiave-di-prova",
        trasporto=trasporto,
        attesa=orologio.attendi,
        orologio=orologio.leggi,
    )


def _genera_ok(trasporto, **cambi):
    return _provider(trasporto).genera(_richiesta(vista_shaded(512, 512), **cambi))


# --- riferimento strutturale -------------------------------------------------


def test_forza_struttura_predefinita_non_si_spaccia_per_misurata():
    """Caso: nessuno ha ancora misurato la forza. L'interfaccia non deve fingere."""
    dichiarata = config.costante("FORZA_STRUTTURA_PREDEFINITA")
    assert dichiarata.origine == config.SCELTA
    assert "non ancora misurato" in dichiarata.etichetta()


def test_forza_struttura_minima_ferma_un_valore_sotto_il_limite_del_servizio():
    """Caso: una forza negativa partirebbe e tornerebbe un errore HTTP opaco."""
    trasporto = TrasportoFinto()
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(
            _richiesta(vista_shaded(512, 512), forza_struttura=config.FORZA_STRUTTURA_MINIMA - 1)
        )
    assert trasporto.poste == []
    assert str(config.FORZA_STRUTTURA_MINIMA) in errore.value.cosa_fare


def test_forza_struttura_massima_ferma_un_valore_sopra_il_limite_del_servizio():
    """Caso: 150 non vuol dire "ancora piu' fedele", vuol dire richiesta rifiutata."""
    trasporto = TrasportoFinto()
    with pytest.raises(ErroreProvider):
        _provider(trasporto).genera(
            _richiesta(vista_shaded(512, 512), forza_struttura=config.FORZA_STRUTTURA_MASSIMA + 1)
        )
    assert trasporto.poste == []


# --- idoneita' ---------------------------------------------------------------


def test_lato_minimo_px_scarta_la_miniatura_e_tiene_la_vista_grande():
    """Caso: si salva per sbaglio l'anteprima invece della vista."""
    piccola = immagine.misura(vista_shaded(config.LATO_MINIMO_PX - 100, 200))
    grande = immagine.misura(vista_shaded(config.LATO_MINIMO_PX + 100, 600))
    assert idoneita.valuta(piccola).motivo == idoneita.TROPPO_PICCOLA
    assert idoneita.valuta(grande).idonea


def test_lato_analisi_px_non_fa_dire_dimensioni_sbagliate_all_interfaccia():
    """Caso: l'analisi lavora su una copia ridotta; l'utente deve leggere la vera."""
    statistiche = immagine.misura(vista_shaded(1600, 900))
    assert (statistiche.larghezza, statistiche.altezza) == (1600, 900)
    assert config.LATO_ANALISI_PX < 1600


def test_tolleranza_sfondo_regge_uno_sfondo_neutro_non_perfettamente_uniforme():
    """Caso: lo sfondo di Allplan ha rumore di compressione, non e' un colore solo."""
    sporco = idoneita.valuta(immagine.misura(vista_wireframe(rumore=config.TOLLERANZA_SFONDO // 2)))
    assert sporco.motivo == idoneita.SEMBRA_WIREFRAME


def test_quota_sfondo_massima_non_scarta_un_render_su_fondo_pulito():
    """Caso: un edificio isolato su cielo uniforme non e' un wireframe."""
    statistiche = immagine.misura(vista_shaded(1200, 800))
    assert statistiche.quota_sfondo < config.QUOTA_SFONDO_MASSIMA
    assert idoneita.valuta(statistiche).idonea


def test_toni_distinti_minimi_separano_il_disegno_di_linee_dalla_vista_shaded():
    """Caso: due materiali resi con pochi toni sono linee, non superfici."""
    wireframe = immagine.misura(vista_wireframe())
    shaded = immagine.misura(vista_shaded())
    assert wireframe.toni_distinti < config.TONI_DISTINTI_MINIMI <= shaded.toni_distinti


def test_deviazione_luminanza_minima_scarta_la_vista_senza_ombre():
    """Caso: shaded con le ombre spente. Non c'e' profondita' da leggere."""
    statistiche = immagine.misura(vista_piatta())
    esito = idoneita.valuta(statistiche)
    assert statistiche.deviazione_luminanza < config.DEVIAZIONE_LUMINANZA_MINIMA
    assert esito.motivo == idoneita.TROPPO_PIATTA
    assert "ombre" in esito.cosa_fare


# --- maschera ----------------------------------------------------------------


def test_maschera_sfumatura_px_toglie_la_cucitura_dal_bordo_della_regione():
    """Caso: un bordo netto lascia un contorno visibile intorno al materiale nuovo."""
    prima = immagine.misura(maschera_netta())
    dopo = immagine.misura(immagine.sfuma_maschera(maschera_netta()))
    assert config.MASCHERA_SFUMATURA_PX > 0
    assert dopo.toni_distinti > prima.toni_distinti


# --- grana -------------------------------------------------------------------


def test_grana_fine_chiede_meno_dettaglio_di_quella_media():
    """Caso: uno slider che va al contrario e' peggio di uno slider assente."""
    assert config.GRANA_FINE < config.GRANA_MEDIA
    assert grana.dettaglio(grana.FINE) == config.GRANA_FINE


def test_grana_media_e_il_punto_di_partenza_dei_preset():
    """Caso: un preset senza grana dichiarata deve partire da un valore noto."""
    from core.preset import preset

    assert preset("base").grana_predefinita == grana.MEDIA
    assert grana.dettaglio(grana.MEDIA) == config.GRANA_MEDIA


def test_grana_grossa_resta_sotto_il_punto_in_cui_il_provider_inventa():
    """Caso: oltre questo dettaglio il servizio aggiunge cio' che non c'era."""
    assert config.GRANA_MEDIA < config.GRANA_GROSSA < config.FORZA_STRUTTURA_MASSIMA
    assert grana.dettaglio(grana.GROSSA) == config.GRANA_GROSSA


# --- rete --------------------------------------------------------------------


def test_timeout_rete_secondi_e_quello_che_usa_il_trasporto_vero():
    """Caso: una chiamata appesa blocca la palette finche' l'utente la chiude."""
    assert TrasportoHTTP().timeout == config.TIMEOUT_RETE_SECONDI


def test_attesa_massima_secondi_chiude_il_lavoro_che_non_finisce_mai():
    """Caso: il lavoro resta in coda dall'altra parte e nessuno lo dice all'utente."""
    orologio = OrologioFinto()
    risposte = [risposta_lavoro("CREATED")]
    risposte += [risposta_lavoro("IN_PROGRESS")] * 500
    trasporto = TrasportoFinto(risposte)
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto, orologio).genera(_richiesta(vista_shaded(512, 512)))
    assert orologio.adesso >= config.ATTESA_MASSIMA_SECONDI
    assert "cruscotto" in errore.value.cosa_fare


def test_intervallo_attesa_secondi_non_martella_il_servizio():
    """Caso: controllare lo stato in ciclo stretto fa scattare il limite di chiamate."""
    orologio = OrologioFinto()
    trasporto = TrasportoFinto([
        risposta_lavoro("CREATED"),
        risposta_lavoro("IN_PROGRESS"),
        risposta_lavoro("COMPLETED", prodotti=["https://esempio/x.png"]),
    ])
    _provider(trasporto, orologio).genera(_richiesta(vista_shaded(512, 512)))
    assert orologio.attese == [config.INTERVALLO_ATTESA_SECONDI] * 2


def test_invio_massimo_mb_ferma_l_immagine_troppo_pesante_prima_di_spedirla():
    """Caso: una vista a 8k parte, viaggia per un minuto e viene rifiutata."""
    trasporto = TrasportoFinto()
    pesante = b"\x89PNG" + b"0" * int((config.INVIO_MASSIMO_MB + 1) * 1024 * 1024)
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).modifica_regione(
            RichiestaRegione(immagine=pesante, maschera=maschera_netta(), prompt="x")
        )
    assert trasporto.poste == []
    assert "risoluzione piu' bassa" in errore.value.cosa_fare


def test_risoluzione_predefinita_e_quella_che_parte_davvero():
    """Caso: chiedere 4k a ogni miniatura triplica il conto dell'utente."""
    trasporto = TrasportoFinto([
        risposta_lavoro("COMPLETED", prodotti=["https://esempio/x.png"]),
    ])
    _genera_ok(trasporto)
    _url, _intestazioni, corpo = trasporto.poste[0]
    assert corpo["resolution"] == config.RISOLUZIONE_PREDEFINITA


# --- guardia -----------------------------------------------------------------


def test_ogni_costante_dichiarata_ha_un_test_che_nomina_il_suo_caso():
    """Caso: si aggiunge una soglia e nessuno scrive il caso che protegge."""
    sorgente = Path(__file__).read_text(encoding="utf-8")
    citate = set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", sorgente))
    mancanti = sorted(set(config.REGISTRO) - citate)
    assert not mancanti, f"costanti senza un test che le nomini: {mancanti}"
