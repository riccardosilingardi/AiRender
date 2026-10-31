"""Ogni costante di core/config.py, e il caso che protegge.

Un test per costante, col caso nel nome. L'ultimo test di questo file
controlla che non ne manchi nessuna: se domani si aggiunge una soglia senza
il suo caso, la suite lo dice.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import pytest
from PIL import Image

from conftest import (
    OrologioFinto,
    TrasportoComfyFinto,
    TrasportoFinto,
    maschera_netta,
    provider_comfy,
    risposta_lavoro,
    router_in_coda,
    router_risultato,
    router_stato,
    vista_piatta,
    vista_shaded,
    vista_wireframe,
)
from core import config, grana, immagine, idoneita
from core.errori import ErroreProvider
from core.provider.base import RichiestaGenerazione, RichiestaRegione
from core.provider.magnific import ProviderMagnific
from core.provider.trasporto import ErroreRete, TrasportoHTTP


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


# --- confronto affiancato ----------------------------------------------------


def test_confronto_didascalia_px_sta_sopra_e_non_copre_il_render():
    """Caso: una didascalia sovrapposta copre proprio la gronda che si deve guardare."""
    vista = vista_shaded(1600, 900)
    largo = vista_shaded(1200, 600)
    uscita = Image.open(io.BytesIO(immagine.affianca([("vista", vista), ("render", largo)])))
    assert uscita.height == 900 + config.CONFRONTO_DIDASCALIA_PX
    # Il render piu' largo resta piu' largo: le proporzioni non si toccano.
    assert uscita.width == 1600 + 2 + 1800


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


def test_tentativi_invio_massimi_ripetono_con_la_stessa_chiave_di_idempotenza(modello_verificato):
    """Caso: la rete cade dopo l'invio. Ripetere con una chiave nuova farebbe pagare due volte."""
    cadute = [ErroreRete("rete giu'", "riprova")] * (config.TENTATIVI_INVIO_MASSIMI - 1)
    trasporto = TrasportoComfyFinto(
        cadute + [router_in_coda(), router_stato("COMPLETED"), router_risultato()]
    )
    provider_comfy(trasporto).genera(
        _richiesta(vista_shaded(512, 512), modello=modello_verificato)
    )
    poste = trasporto.poste()
    assert len(poste) == config.TENTATIVI_INVIO_MASSIMI
    assert {p[2]["Idempotency-Key"] for p in poste} == {"idem-1"}


def test_tentativi_invio_massimi_poi_si_ferma_e_dice_di_guardare_i_crediti(modello_verificato):
    """Caso: la rete non torna. Rilanciare a mano senza guardare puo' far pagare due volte."""
    trasporto = TrasportoComfyFinto(
        [ErroreRete("rete giu'", "riprova")] * config.TENTATIVI_INVIO_MASSIMI
    )
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(
            _richiesta(vista_shaded(512, 512), modello=modello_verificato)
        )
    assert len(trasporto.poste()) == config.TENTATIVI_INVIO_MASSIMI
    assert "crediti del workspace" in errore.value.cosa_fare


def test_comfy_invio_massimo_mb_ferma_la_vista_troppo_pesante_prima_di_spedirla(modello_verificato):
    """Caso: una vista a 8k viaggia per un minuto e poi il modello la rifiuta."""
    trasporto = TrasportoComfyFinto()
    pesante = b"\x89PNG" + b"0" * int((config.COMFY_INVIO_MASSIMO_MB + 1) * 1024 * 1024)
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(_richiesta(pesante, modello=modello_verificato))
    assert trasporto.chiamate == []
    assert "risoluzione piu' bassa" in errore.value.cosa_fare


def test_risoluzione_predefinita_e_quella_che_parte_davvero():
    """Caso: chiedere 4k a ogni miniatura triplica il conto dell'utente."""
    trasporto = TrasportoFinto([
        risposta_lavoro("COMPLETED", prodotti=["https://esempio/x.png"]),
    ])
    _genera_ok(trasporto)
    _url, _intestazioni, corpo = trasporto.poste[0]
    assert corpo["resolution"] == config.RISOLUZIONE_PREDEFINITA


def test_passi_avviso_da_generazione_avvisa_gia_dal_primo_passo_su_un_render():
    """Caso: un passo fatto su un render, gia' la 2a generazione, non avvisa che gli spigoli si muovono."""
    assert config.PASSI_AVVISO_DA_GENERAZIONE == 2
    assert config.costante("PASSI_AVVISO_DA_GENERAZIONE").origine == config.SCELTA


def test_ritocco_modo_aree_e_un_modo_vero_e_resta_una_scelta_finche_il_banco_non_parla():
    """Caso: lo Studio manda le aree in un modo che il motore non sa preparare, o lo spaccia per misurato."""
    from core import aree

    assert config.RITOCCO_MODO_AREE in aree.MODI
    assert config.costante("RITOCCO_MODO_AREE").origine == config.SCELTA


def test_anteprima_taglio_scuro_lascia_vedere_la_scena_tagliata():
    """Caso: l'anteprima del formato nasconde del tutto cio' che taglia, o non lo distingue."""
    from tests.test_cornice import vista as tinta
    from core import immagine

    assert 0 < config.ANTEPRIMA_TAGLIO_SCURO < 1
    assert config.costante("ANTEPRIMA_TAGLIO_SCURO").origine == config.SCELTA
    anteprima = immagine._apri(immagine.anteprima_taglio(tinta(400, 200, (200, 200, 200)), 1.0))
    assert anteprima.getpixel((200, 100)) == (200, 200, 200)
    fuori = anteprima.getpixel((10, 100))[0]
    assert 0 < fuori < 200


def test_risoluzione_render_predefinita_chiede_imagesize_solo_sopra_1k():
    """Caso: render da 1279x827 con «altissima definizione» scelta (2026-10-31): 32k nel prompt non cambia i pixel."""
    from dataclasses import replace

    from core import blocchi
    from core.provider import comfy
    from core.provider.base import RichiestaGenerazione
    from tests.test_cornice import vista as tinta

    assert config.RISOLUZIONE_RENDER_PREDEFINITA == "1k"
    assert config.costante("RISOLUZIONE_RENDER_PREDEFINITA").origine == config.SCELTA
    assert blocchi.Scelte().risoluzione == "1k"
    base = RichiestaGenerazione(immagine=tinta(640, 360), prompt="p", preset="x", preset_versione="1",
                                modello="vertexai/gemini-3.1-flash-image", grana="", dettaglio_grana=0)
    assert "imageSize" not in comfy._corpo_gemini(base)["generationConfig"]["imageConfig"]
    grande = comfy._corpo_gemini(replace(base, dimensione_render="4k"))
    assert grande["generationConfig"]["imageConfig"]["imageSize"] == "4K"
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.Scelte(risoluzione="32k")


def test_esporta_qualita_jpeg_sta_nel_campo_di_pillow_ed_e_una_scelta():
    """Caso: un JPEG per il cliente esce sgranato, o con una qualita' che Pillow sconsiglia, spacciata per misurata."""
    assert 80 <= config.ESPORTA_QUALITA_JPEG <= 95
    assert config.costante("ESPORTA_QUALITA_JPEG").origine == config.SCELTA


def test_geometry_drift_warn_avvisa_solo_sotto_la_soglia_ed_e_una_scelta():
    """Caso: lo Studio avvisa a ogni render, o mai, con una soglia spacciata per misurata."""
    assert 0 < config.GEOMETRY_DRIFT_WARN < 1
    assert config.costante("GEOMETRY_DRIFT_WARN").origine == config.SCELTA


# --- guardia -----------------------------------------------------------------


def test_ogni_costante_dichiarata_ha_un_test_che_nomina_il_suo_caso():
    """Caso: si aggiunge una soglia e nessuno scrive il caso che protegge."""
    sorgente = Path(__file__).read_text(encoding="utf-8")
    citate = set(re.findall(r"\b[A-Z][A-Z0-9_]{3,}\b", sorgente))
    mancanti = sorted(set(config.REGISTRO) - citate)
    assert not mancanti, f"costanti senza un test che le nomini: {mancanti}"


# --- proporzioni della vista -------------------------------------------------


def test_cornice_tolleranza_lascia_partire_com_e_una_vista_gia_al_rapporto_giusto():
    """Caso: una vista 1920x1080 (16:9 esatto) si allarga lo stesso e perde pixel per niente."""
    from core.provider.comfy import con_cornice
    from core.provider.base import RichiestaGenerazione
    from tests.test_cornice import vista

    richiesta = RichiestaGenerazione(immagine=vista(1920, 1080), prompt="p", preset="x",
                                     preset_versione="1", modello="m", grana="", dettaglio_grana=0)
    assert con_cornice(richiesta)[1] is None
    assert config.CORNICE_TOLLERANZA < 0.05


# --- coda dei lavori ---------------------------------------------------------


def test_coda_intervallo_secondi_e_l_attesa_quando_la_coda_e_vuota(tmp_path):
    """Caso: il processo della coda gira a vuoto e tiene la CPU occupata."""
    from core.coda import Coda

    attese = []

    class Basta(Exception):
        pass

    def attendi(secondi):
        attese.append(secondi)
        raise Basta()

    with pytest.raises(Basta):
        Coda(tmp_path, dire=lambda _t: None, attesa=attendi).gira()
    assert attese == [config.CODA_INTERVALLO_SECONDI]


# --- Studio ------------------------------------------------------------------


def _png_tinta(colore, larghezza=64, altezza=64, colorati=1.0) -> bytes:
    """Un'immagine grigia con una parte (da sinistra) del colore dato."""
    img = Image.new("RGB", (larghezza, altezza), (128, 128, 128))
    img.paste(colore, (0, 0, int(larghezza * colorati), altezza))
    deposito = io.BytesIO()
    img.save(deposito, format="PNG")
    return deposito.getvalue()


def test_costo_nano_banana_2_crediti_e_quello_scritto_prima_di_genera(tmp_path):
    """Caso: lo Studio annuncia un costo diverso da quello misurato, o lo da' per certo."""
    from core.studio.servizio import MODELLI, Studio

    destinazione = Studio(tmp_path).destinazione(MODELLI[0].identificativo)
    assert f"circa {round(config.COSTO_NANO_BANANA_2_CREDITI)} crediti" in destinazione["costo"]
    assert config.costante("COSTO_NANO_BANANA_2_CREDITI").origine == config.MISURATA


def test_saturazione_colore_minima_separa_il_grigio_dal_colore_pieno():
    """Caso: una vista grigia appena tinta conta come colorata, o un viola pieno no."""
    assert 0 < config.SATURAZIONE_COLORE_MINIMA < 255
    assert immagine.quota_colorata(_png_tinta((128, 128, 128))) == 0.0
    assert immagine.quota_colorata(_png_tinta((150, 60, 170))) == 1.0
    # una tinta appena calda, sotto la soglia: una vista shaded con luce calda
    assert immagine.quota_colorata(_png_tinta((140, 132, 124))) == 0.0


def test_quota_colorata_avviso_lascia_passare_un_dettaglio_e_prende_una_facciata(tmp_path):
    """Caso: l'avviso dei colori scatta per un cielo azzurro, o tace su una facciata viola."""
    from core.studio.servizio import Studio

    poco = config.QUOTA_COLORATA_AVVISO / 2
    molto = config.QUOTA_COLORATA_AVVISO * 4
    (tmp_path / "poco.png").write_bytes(_png_tinta((150, 60, 170), 600, 400, colorati=poco))
    (tmp_path / "molto.png").write_bytes(_png_tinta((150, 60, 170), 600, 400, colorati=molto))
    studio = Studio(tmp_path)
    assert studio.descrivi_vista("poco.png")["colori_come_materiali"] is False
    assert studio.descrivi_vista("molto.png")["colori_come_materiali"] is True


def test_studio_caricamento_massimo_mb_ferma_un_file_enorme_trascinato_per_sbaglio(tmp_path, monkeypatch):
    """Caso: Usa un'altra vista riceve un file da centinaia di MB e il server lo tiene in memoria."""
    from core.studio.servizio import RichiestaStudioNonValida, Studio

    studio = Studio(tmp_path)
    assert studio.carica_vista(_png_tinta((128, 128, 128), 600, 400))["nome"]
    monkeypatch.setattr(config, "STUDIO_CARICAMENTO_MASSIMO_MB", 0)
    with pytest.raises(RichiestaStudioNonValida):
        studio.carica_vista(_png_tinta((128, 128, 128), 600, 400))


# --- banco di prova e varianti -------------------------------------------------


def test_varianti_massime_ferma_un_genera_che_costerebbe_senza_che_si_veda(tmp_path):
    """Caso: un numero di varianti fuori misura arriva dalla pagina e si pagano dieci invii."""
    from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio

    studio = Studio(tmp_path)
    assert studio.destinazione(MODELLI[0].identificativo, config.VARIANTI_MASSIME)["varianti"] == config.VARIANTI_MASSIME
    with pytest.raises(RichiestaStudioNonValida):
        studio.destinazione(MODELLI[0].identificativo, config.VARIANTI_MASSIME + 1)


def _due_toni(scatola_cambiata, valore) -> tuple[bytes, bytes]:
    prima = Image.new("RGB", (200, 100), (100, 100, 100))
    dopo = prima.copy()
    dopo.paste((valore,) * 3, scatola_cambiata)
    return _png(prima), _png(dopo)


def _png(img) -> bytes:
    deposito = io.BytesIO()
    img.save(deposito, format="PNG")
    return deposito.getvalue()


def test_differenza_pixel_soglia_ignora_il_rumore_e_prende_un_cambio_visibile():
    """Caso: il rumore della rigenerazione conta come area violata, o un cambio vero passa."""
    rumore = _due_toni((0, 0, 200, 100), 100 + config.DIFFERENZA_PIXEL_SOGLIA)
    assert immagine.differenza_fuori_dalle_aree(*rumore, [])["quota_cambiata"] == 0
    visibile = _due_toni((0, 0, 200, 100), 100 + config.DIFFERENZA_PIXEL_SOGLIA + 1)
    assert immagine.differenza_fuori_dalle_aree(*visibile, [])["quota_cambiata"] == 1


def test_aree_bordo_escluso_px_non_conta_la_sfumatura_sul_bordo_dell_area():
    """Caso: il modello sfuma la modifica oltre il bordo e il banco dice che ha violato l'area."""
    area = [(50, 20), (100, 20), (100, 80), (50, 80)]
    bordo = config.AREE_BORDO_ESCLUSO_PX
    dentro_la_fascia = _due_toni((50 - bordo + 1, 20, 50, 80), 250)
    assert immagine.differenza_fuori_dalle_aree(*dentro_la_fascia, [area])["quota_cambiata"] == 0
    oltre = _due_toni((50 - bordo - 4, 20, 50 - bordo - 1, 80), 250)
    assert immagine.differenza_fuori_dalle_aree(*oltre, [area])["quota_cambiata"] > 0


def test_contorno_aree_px_e_lo_spessore_del_contorno_disegnato():
    """Caso: un contorno troppo sottile sparisce quando il modello rimpicciolisce l'immagine."""
    vista = _png(Image.new("RGB", (200, 200), (120, 120, 120)))
    disegnata = Image.open(io.BytesIO(immagine.disegna_aree(vista, [[(50, 150), (150, 150), (150, 190), (50, 190)]])))
    colonna = [disegnata.convert("RGB").getpixel((100, y)) for y in range(140, 160)]
    assert config.CONTORNO_AREE_PX - 1 <= colonna.count((255, 0, 255)) <= config.CONTORNO_AREE_PX + 1


def test_spigoli_soglia_lato_e_tolleranza_vedono_uno_spostamento_di_pochi_pixel():
    """Caso: la misura grezza degli spigoli non distingue un edificio fermo da uno spostato."""
    prima = Image.new("RGB", (config.SPIGOLI_LATO_PX, config.SPIGOLI_LATO_PX // 2), (200, 200, 200))
    prima.paste((60, 60, 60), (300, 100, 600, 400))
    vicino = Image.new("RGB", prima.size, (200, 200, 200))
    lontano = Image.new("RGB", prima.size, (200, 200, 200))
    vicino.paste((60, 60, 60), (300 + config.SPIGOLI_TOLLERANZA_PX, 100, 600 + config.SPIGOLI_TOLLERANZA_PX, 400))
    lontano.paste((60, 60, 60), (300 + 4 * config.SPIGOLI_TOLLERANZA_PX, 100,
                                 600 + 4 * config.SPIGOLI_TOLLERANZA_PX, 400))
    assert immagine.spigoli_ritrovati(_png(prima), _png(vicino)) == 1.0
    assert immagine.spigoli_ritrovati(_png(prima), _png(lontano)) < 0.7
    assert 0 < config.SPIGOLI_SOGLIA < 140  # il salto fra i due grigi si vede


def test_miniatura_larghezza_e_altezza_px_sono_le_proporzioni_della_tessera():
    """Caso: la miniatura vera ha altre proporzioni e la tessera la taglia male."""
    alta = _png(Image.new("RGB", (600, 900), (90, 90, 90)))
    piccola = Image.open(io.BytesIO(immagine.ritaglia_miniatura(alta)))
    assert piccola.size == (config.MINIATURA_LARGHEZZA_PX, config.MINIATURA_ALTEZZA_PX)
    assert config.MINIATURA_LARGHEZZA_PX * 9 == config.MINIATURA_ALTEZZA_PX * 16


# --- battito e palette v1 ----------------------------------------------------


def test_battito_scaduto_secondi_separa_un_processo_vivo_da_uno_fermo(tmp_path):
    """Caso: la palette crede viva una coda morta e il lavoro resta in attesa per sempre."""
    from core import battito

    file = tmp_path / "vivo.json"
    battito.scrivi(file, {}, adesso=lambda: 1000.0)
    assert battito.leggi(file, adesso=lambda: 1000.0 + config.BATTITO_SCADUTO_SECONDI) is not None
    assert battito.leggi(file, adesso=lambda: 1000.1 + config.BATTITO_SCADUTO_SECONDI) is None


def test_battito_intervallo_secondi_e_piu_corto_della_scadenza():
    """Caso: il battito arriva piu' di rado di quanto si aspetta chi lo legge, e un processo vivo sembra morto."""
    assert config.BATTITO_INTERVALLO_SECONDI * 2 <= config.BATTITO_SCADUTO_SECONDI


def test_palette_immagini_da_script_e_spenta_finche_la_sonda_non_risponde():
    """Caso: la palette conta su un'immagine che Allplan non aggiorna e mostra la vista sbagliata."""
    assert config.PALETTE_IMMAGINI_DA_SCRIPT is False
    assert config.costante("PALETTE_IMMAGINI_DA_SCRIPT").origine == config.SCELTA


def test_palette_secondi_attesa_studio_lascia_al_battito_il_tempo_di_comparire():
    """Caso: la palette dice «lo Studio non e' partito» prima che il primo battito possa arrivare."""
    assert config.PALETTE_SECONDI_ATTESA_STUDIO > config.BATTITO_INTERVALLO_SECONDI
