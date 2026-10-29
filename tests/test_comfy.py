"""Comfy Router: cosa parte davvero, e cosa succede quando va storto.

Nessuna chiamata vera. Il Router e' finto, l'orologio e' finto, la chiave non
esiste, e lo schema del modello e' finto anche lui: quelli veri si scrivono
solo dall'uscita di scripts/sonda_comfy.py.
"""

from __future__ import annotations

import email.message
import io
import json

import pytest

from conftest import (
    MODELLO_DI_PROVA,
    OrologioFinto,
    TrasportoComfyFinto,
    provider_comfy,
    router_in_coda,
    router_risultato,
    router_stato,
    vista_shaded,
)
from core import config, grana, provider as registro
from core.errori import ChiaveMancante, ErroreProvider
from core.provider import comfy
from core.provider.base import RichiestaGenerazione, RichiestaRegione
from core.provider.trasporto import TrasportoHTTP
from core.ricetta import impronta

PNG = vista_shaded(640, 360)


def richiesta(dati: bytes = PNG, **cambi) -> RichiestaGenerazione:
    base = dict(
        immagine=dati,
        prompt="prompt tecnico",
        preset="base",
        preset_versione="2",
        modello=MODELLO_DI_PROVA,
        grana=grana.MEDIA,
        dettaglio_grana=grana.dettaglio(grana.MEDIA),
        testo_utente="piu' caldo",
    )
    base.update(cambi)
    return RichiestaGenerazione(**base)


def router_che_riesce(*in_mezzo):
    return TrasportoComfyFinto(
        [router_in_coda(), *in_mezzo, router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )


# --- dove va l'immagine ------------------------------------------------------


def test_la_destinazione_nomina_il_router_e_il_modello():
    """Caso: sotto NDA non basta "Comfy": conta anche quale modello riceve la vista."""
    motore = comfy.ProviderComfy()
    assert motore.destinazione_per("bfl/flux-kontext-pro") == (
        "Comfy Router (api.comfy.org) → bfl/flux-kontext-pro"
    )


def test_il_fallback_e_spento_perche_la_vista_non_cambi_destinazione(modello_verificato):
    """Caso: il provider del modello cade e il Router ripiega su un altro, che nessuno ha annunciato."""
    trasporto = router_che_riesce()
    provider_comfy(trasporto).genera(richiesta())
    _metodo, url, intestazioni, corpo = trasporto.poste()[0]
    assert url == f"{comfy.BASE}/{MODELLO_DI_PROVA}/requests?fallback_provider=false"
    assert intestazioni["X-API-Key"] == "chiave-di-prova"
    assert intestazioni["Idempotency-Key"] == "idem-1"
    assert corpo["input_image"].startswith("data:image/png;base64,")


def test_se_il_router_dice_di_aver_ripiegato_lo_si_dice_all_utente(modello_verificato):
    """Caso: fallback spento, ma il Router dichiara comunque un altro provider."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(intestazioni={"x-comfy-router-fallback-provider": "altro"}),
         router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )
    risultato = provider_comfy(trasporto).genera(richiesta())
    assert any("altro" in avviso and "NDA" in avviso for avviso in risultato.avvisi)


def test_il_link_dell_immagine_si_scarica_senza_mandare_la_chiave(modello_verificato):
    """Caso: il link firmato sta su un altro dominio. La chiave resta su api.comfy.org."""
    trasporto = router_che_riesce()
    risultato = provider_comfy(trasporto).genera(richiesta())
    assert trasporto.scaricati == ["https://consegna.esempio/render.png?firma=x"]
    assert risultato.immagine == PNG and risultato.formato == "png"


# --- schema non ancora verificato -------------------------------------------


def test_un_modello_senza_schema_verificato_non_parte_e_dice_di_lanciare_la_sonda():
    """Caso: lo schema scritto dai documenti e mai provato. Si paga per scoprire che era sbagliato."""
    trasporto = TrasportoComfyFinto()
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(richiesta(modello="bfl/flux-kontext-max"))
    assert trasporto.chiamate == []
    assert "sonda_comfy.py --modello bfl/flux-kontext-max" in errore.value.cosa_fare


def test_solo_i_modelli_sondati_hanno_uno_schema_e_ognuno_dice_quando():
    """Caso: qualcuno aggiunge uno schema dai documenti, senza una chiamata vera dietro."""
    assert set(comfy.SCHEMI) == {"bfl/flux-kontext-pro", "vertexai/gemini-3.1-flash-image"}
    assert all(schema.verificato_il == "2026-10-27" for schema in comfy.SCHEMI.values())


def test_la_prova_a_secco_sa_gia_cosa_fermera_l_invio(modello_verificato):
    """Caso: la prova a secco promette un invio che poi si rifiuta."""
    motore = comfy.ProviderComfy()
    assert "non e' ancora stato verificato" in motore.cosa_manca("bfl/flux-kontext-max")
    assert motore.cosa_manca("bfl/flux-kontext-pro") is None
    assert motore.cosa_manca(modello_verificato) is None


# --- attesa ------------------------------------------------------------------


def test_l_attesa_rispetta_retry_after_e_senza_usa_l_intervallo(modello_verificato):
    """Caso: il Router dice quando ripassare; se tace, si usa il nostro intervallo."""
    orologio = OrologioFinto()
    trasporto = TrasportoComfyFinto(
        [router_in_coda(intestazioni={"retry-after": "7"}),
         router_stato("IN_PROGRESS"),
         router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )
    provider_comfy(trasporto, orologio=orologio).genera(richiesta())
    assert orologio.attese == [7.0, config.INTERVALLO_ATTESA_SECONDI]


def test_un_retry_after_oltre_il_tempo_concesso_si_dice_subito(modello_verificato):
    """Caso: il Router stima mezz'ora. Aspettarla a palette bloccata e poi fallire e' peggio."""
    orologio = OrologioFinto()
    lungo = str(config.ATTESA_MASSIMA_SECONDI + 1)
    trasporto = TrasportoComfyFinto([router_in_coda(intestazioni={"retry-after": lungo})])
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto, orologio=orologio).genera(richiesta())
    assert orologio.attese == []
    assert "rq-1" in errore.value.cosa_fare


def test_il_risultato_non_ancora_pronto_si_riprende_dopo_retry_after(modello_verificato):
    """Caso: lo stato dice COMPLETED ma il risultato risponde ancora 202."""
    orologio = OrologioFinto()
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"),
         (202, {"retry-after": "4"}, {"status": "IN_PROGRESS"}), router_risultato()],
        immagine=PNG,
    )
    provider_comfy(trasporto, orologio=orologio).genera(richiesta())
    assert orologio.attese == [config.INTERVALLO_ATTESA_SECONDI, 4.0]


# --- idempotenza -------------------------------------------------------------


def test_un_503_si_ripete_con_la_stessa_idempotency_key(modello_verificato):
    """Caso: il Router e' sovraccarico. Ripetere e' giusto, pagare due volte no."""
    orologio = OrologioFinto()
    trasporto = TrasportoComfyFinto(
        [(503, {"retry-after": "2"}, {"error": "busy"}),
         router_in_coda(), router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )
    provider_comfy(trasporto, orologio=orologio).genera(richiesta())
    chiavi = [p[2]["Idempotency-Key"] for p in trasporto.poste()]
    assert chiavi == ["idem-1", "idem-1"]
    assert orologio.attese[0] == 2.0


def test_due_generazioni_hanno_due_chiavi_diverse(modello_verificato):
    """Caso: la stessa chiave su una seconda generazione renderebbe la prima immagine."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"), router_risultato()] * 2, immagine=PNG
    )
    motore = provider_comfy(trasporto)
    motore.genera(richiesta())
    motore.genera(richiesta())
    assert [p[2]["Idempotency-Key"] for p in trasporto.poste()] == ["idem-1", "idem-2"]


# --- quando va storto --------------------------------------------------------


def test_credito_finito_diventa_una_frase_che_dice_cosa_fare(modello_verificato):
    """Caso: workspace senza crediti. "402" non dice a nessuno cosa fare."""
    trasporto = TrasportoComfyFinto(
        [(402, {"x-comfy-error-type": "insufficient_credits"},
          {"error": {"type": "insufficient_credits", "message": "no credits"}})]
    )
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(richiesta())
    assert errore.value.stato == 402
    assert len(trasporto.poste()) == 1
    assert "credito del tuo workspace Comfy" in errore.value.fatto
    assert "Ricarica i crediti" in errore.value.cosa_fare
    assert "402" not in str(errore.value)


def test_senza_chiave_non_parte_niente_e_dice_dove_metterla(modello_verificato):
    """Caso: prima esecuzione, chiave non ancora configurata."""
    trasporto = TrasportoComfyFinto()
    with pytest.raises(ChiaveMancante) as errore:
        comfy.ProviderComfy(chiave=None, trasporto=trasporto).genera(richiesta())
    assert trasporto.chiamate == []
    assert "COMFY_API_KEY" in errore.value.cosa_fare


@pytest.mark.parametrize("stato, atteso", [
    (401, "COMFY_API_KEY"),
    (403, "workspace"),
    (404, "--catalogo"),
])
def test_chiave_rifiutata_workspace_senza_modello_e_modello_sconosciuto_si_distinguono(
    modello_verificato, stato, atteso
):
    """Caso: sul Router 401 e 403 non sono la stessa cosa. Dire "chiave sbagliata" a un 403 manda fuori strada."""
    trasporto = TrasportoComfyFinto([(stato, {}, {"message": "no"})])
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(richiesta())
    assert atteso in errore.value.cosa_fare
    assert len(trasporto.poste()) == 1


def test_un_lavoro_completato_con_un_errore_non_diventa_un_immagine(modello_verificato):
    """Caso: il Router non ha uno stato "fallito": finisce COMPLETED con un errore dentro."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED", error={"type": "provider_error"})]
    )
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(richiesta())
    assert "provider_error" in errore.value.fatto


def test_uno_stato_sconosciuto_si_ferma_invece_di_girare_fino_al_tempo_massimo(modello_verificato):
    """Caso: l'API cambia i nomi degli stati e la palette resta appesa cinque minuti."""
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("FAILED")])
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(richiesta())
    assert "FAILED" in errore.value.fatto
    assert "comfy.py" in errore.value.cosa_fare


def test_byte_che_non_sono_un_immagine_si_rifiutano(modello_verificato):
    """Caso: il link porta a una pagina d'errore HTML, salvata come render."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"), router_risultato()],
        immagine=b"<html>scaduto</html>",
    )
    with pytest.raises(ErroreProvider):
        provider_comfy(trasporto).genera(richiesta())


def test_il_ritocco_con_maschera_si_rifiuta_e_dice_cosa_fare_invece():
    """Caso: nessun modello con maschera verificato sul Router."""
    with pytest.raises(ErroreProvider) as errore:
        comfy.ProviderComfy(trasporto=TrasportoComfyFinto()).modifica_regione(
            RichiestaRegione(immagine=PNG, maschera=PNG, prompt="mattone")
        )
    assert "modalita' variante" in errore.value.cosa_fare


# --- ricetta -----------------------------------------------------------------


def test_la_ricetta_salva_modello_versione_e_tutti_i_parametri_ma_non_la_chiave(modello_verificato):
    """Caso: i provider cambiano i modelli sotto lo stesso nome. Il seme da solo non basta."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(intestazioni={"x-comfy-request-id": "cr-9"}),
         router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )
    ricetta = provider_comfy(trasporto).genera(richiesta()).ricetta
    assert ricetta.provider == "comfy" and ricetta.modello == MODELLO_DI_PROVA
    assert ricetta.preset_versione == "2"
    assert ricetta.forza_struttura is None and ricetta.dettaglio_grana is None
    parametri = ricetta.parametri
    assert parametri["fallback_provider"] == "false"
    assert parametri["chiave_idempotenza"] == "idem-1"
    assert parametri["richiesta_id"] == "rq-1" and parametri["id_router"] == "cr-9"
    assert parametri["corpo"] == {
        "prompt": "prompt tecnico", "input_image": f"<vista sha256:{impronta(PNG)}>"
    }
    testo = ricetta.a_json()
    assert "chiave-di-prova" not in testo
    assert json.loads(testo)["parametri"]["schema_verificato_il"]


def test_la_riesecuzione_usa_una_chiave_nuova_e_avvisa_che_l_immagine_puo_cambiare(modello_verificato):
    """Caso: riusare la chiave vecchia renderebbe l'immagine di ieri, chiamandola rifatta."""
    prima = provider_comfy(router_che_riesce()).genera(richiesta()).ricetta
    trasporto = router_che_riesce()
    dopo = provider_comfy(trasporto).riesegui(prima, PNG)
    assert trasporto.poste()[0][3]["prompt"] == prima.prompt
    assert dopo.ricetta.parametri["chiave_idempotenza"] == "idem-1"
    assert any("generazione fissa" in avviso for avviso in dopo.avvisi)


def test_la_riesecuzione_con_un_altra_vista_si_ferma_prima_di_spendere(modello_verificato):
    """Caso: la vista e' stata risalvata. Non e' piu' lo stesso livello."""
    prima = provider_comfy(router_che_riesce()).genera(richiesta()).ricetta
    trasporto = TrasportoComfyFinto()
    with pytest.raises(ErroreProvider):
        provider_comfy(trasporto).riesegui(prima, vista_shaded(640, 360, seme=99))
    assert trasporto.chiamate == []


# --- registro e trasporto ----------------------------------------------------


def test_comfy_e_il_predefinito_e_magnific_resta_registrato():
    """Caso: Magnific non e' piu' a consumo, ma le ricette vecchie devono potersi rifare."""
    assert registro.PREDEFINITO == "comfy"
    assert {"comfy", "magnific"} <= set(registro.nomi())


def test_il_trasporto_vero_rende_le_intestazioni_in_minuscolo(monkeypatch):
    """Caso: il Router scrive Retry-After, un proxy lo riscrive retry-after."""
    intestazioni = email.message.Message()
    intestazioni["Retry-After"] = "3"
    viste = []

    class Risposta(io.BytesIO):
        status = 201
        headers = intestazioni

    def urlopen_finto(richiesta_http, timeout=None):
        viste.append(richiesta_http)
        return Risposta(b'{"request_id": "rq-1"}')

    monkeypatch.setattr("urllib.request.urlopen", urlopen_finto)
    stato, risposte, corpo = TrasportoHTTP().chiama("POST", "https://x/y", {"A": "b"}, {"k": 1})
    assert (stato, risposte, corpo) == (201, {"retry-after": "3"}, {"request_id": "rq-1"})
    assert viste[0].get_header("Content-type") == "application/json"


# --- schemi veri, sulle forme che il Router ha reso il 2026-10-27 -------------


VISTA_LARGA = vista_shaded(1536, 857)  # le proporzioni della cattura vera


def test_kontext_manda_base64_nudo_rapporto_vicino_e_seme():
    """Caso: con il prefisso data: la chiamata vera non e' mai stata provata."""
    corpo = comfy.SCHEMI["bfl/flux-kontext-pro"].corpo(
        richiesta(VISTA_LARGA, modello="bfl/flux-kontext-pro", seme=7))
    assert corpo["input_image"] == comfy.immagine_base64(VISTA_LARGA)
    assert not corpo["input_image"].startswith("data:")
    assert corpo["aspect_ratio"] == "16:9" and corpo["seed"] == 7
    assert corpo["output_format"] == "png"


def test_kontext_senza_seme_non_manda_il_campo():
    corpo = comfy.SCHEMI["bfl/flux-kontext-pro"].corpo(richiesta(modello="bfl/flux-kontext-pro"))
    assert "seed" not in corpo


def test_kontext_trova_il_link_dove_lo_ha_messo_la_chiamata_vera():
    uscita = {"id": "x", "status": "Ready", "result": {
        "sample": "https://storage.esempio/bfl.png?Expires=1", "seed": 1913500001}}
    assert comfy.SCHEMI["bfl/flux-kontext-pro"].immagine(uscita) == (
        "url", "https://storage.esempio/bfl.png?Expires=1")


def test_gemini_manda_testo_e_immagine_e_chiede_solo_un_immagine():
    corpo = comfy.SCHEMI["vertexai/gemini-3.1-flash-image"].corpo(
        richiesta(VISTA_LARGA, modello="vertexai/gemini-3.1-flash-image"))
    parti = corpo["contents"][0]["parts"]
    assert parti[0] == {"text": "prompt tecnico"}
    assert parti[1]["inlineData"] == {
        "mimeType": "image/png", "data": comfy.immagine_base64(VISTA_LARGA)}
    assert corpo["generationConfig"] == {
        "responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "16:9"}}


def test_gemini_sceglie_la_parte_per_il_campo_non_per_la_posizione():
    """Caso: lo schema dice che accanto all'immagine puo' esserci una parte di testo."""
    schema = comfy.SCHEMI["vertexai/gemini-3.1-flash-image"]
    in_linea = {"candidates": [{"content": {"parts": [
        {"text": "ecco"}, {"inlineData": {"mimeType": "image/png", "data": "QUJD"}}]}}]}
    assert schema.immagine(in_linea) == ("base64", "QUJD")
    con_link = {"candidates": [{"content": {"parts": [
        {"fileData": {"mimeType": "image/png", "fileUri": "https://storage.esempio/g.png"}}]}}]}
    assert schema.immagine(con_link) == ("url", "https://storage.esempio/g.png")


@pytest.mark.parametrize("uscita", [{}, {"candidates": []},
                                    {"candidates": [{"content": {"parts": [{"text": "no"}]}}]}])
def test_un_risultato_senza_immagine_lo_dice_invece_di_rompersi(uscita):
    with pytest.raises(ErroreProvider):
        comfy.SCHEMI["vertexai/gemini-3.1-flash-image"].immagine(uscita)
    with pytest.raises(ErroreProvider):
        comfy.SCHEMI["bfl/flux-kontext-pro"].immagine(uscita)


def test_gemini_dall_invio_all_immagine_decodificata():
    """Caso: tutta la strada, col Router finto che rende la forma vera di Vertex AI."""
    risultato_vero = (200, {}, {"candidates": [{"content": {"role": "model", "parts": [
        {"inlineData": {"mimeType": "image/png", "data": comfy.immagine_base64(PNG)}}]},
        "finishReason": "STOP"}], "modelVersion": "gemini-3.1-flash-image"})
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"), risultato_vero])
    esito = provider_comfy(trasporto).genera(
        richiesta(modello="vertexai/gemini-3.1-flash-image"))
    assert esito.immagine == PNG and trasporto.scaricati == []
    assert esito.ricetta.parametri["schema_verificato_il"] == "2026-10-27"
    assert esito.ricetta.parametri["corpo"]["contents"][0]["parts"][1]["inlineData"]["data"] == (
        f"<vista sha256:{impronta(PNG)}>")


def test_gemini_mette_le_immagini_in_piu_dopo_la_vista_e_la_ricetta_non_le_tiene():
    """Caso: la maschera del banco di prova parte prima della vista, o finisce in chiaro nella ricetta."""
    maschera = vista_shaded(64, 64, seme=3)
    risultato_vero = (200, {}, {"candidates": [{"content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": comfy.immagine_base64(PNG)}}]}}]})
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("COMPLETED"), risultato_vero])
    esito = provider_comfy(trasporto).genera(
        richiesta(modello="vertexai/gemini-3.1-flash-image", immagini_in_piu=(maschera,)))
    parti = trasporto.poste()[0][3]["contents"][0]["parts"]
    assert [p.get("text") for p in parti[:1]] == ["prompt tecnico"]
    assert parti[2]["inlineData"]["data"] == comfy.immagine_base64(maschera)
    salvate = esito.ricetta.parametri["corpo"]["contents"][0]["parts"]
    assert salvate[2]["inlineData"]["data"] == f"<immagine 2 sha256:{impronta(maschera)}>"
    assert esito.ricetta.parametri["immagini_in_piu"] == [impronta(maschera)]
    assert comfy.SCHEMI["vertexai/gemini-3.1-flash-image"].piu_immagini_verificato_il == ""


def test_kontext_con_due_immagini_si_ferma_prima_di_partire():
    """Caso: Kontext riceve la maschera, la ignora in silenzio, e il confronto del banco non vale."""
    trasporto = TrasportoComfyFinto([])
    with pytest.raises(ErroreProvider) as errore:
        provider_comfy(trasporto).genera(
            richiesta(modello="bfl/flux-kontext-pro", immagini_in_piu=(PNG,)))
    assert "una sola immagine" in errore.value.fatto and "Non ho inviato niente" in errore.value.fatto
    assert trasporto.chiamate == []


def test_i_crediti_scalati_finiscono_nella_ricetta():
    """Caso: a fine mese si vuole sapere quanto e' costato ogni livello."""
    risultato = (200, {"x-comfy-credits-used": "17.17"}, {"result": {"sample": "https://s.esempio/r.png"}})
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"), risultato], immagine=PNG)
    esito = provider_comfy(trasporto).genera(richiesta(modello="bfl/flux-kontext-pro"))
    assert esito.ricetta.parametri["crediti_usati"] == "17.17"


def test_durante_l_attesa_dice_a_chi_ascolta_se_il_lavoro_e_inviato_o_in_lavorazione(modello_verificato):
    """Caso: la coda scrive "inviato" per tutta l'attesa e lo Studio non sa che il Router ci lavora."""
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("IN_QUEUE"), router_stato("IN_PROGRESS"),
         router_stato("COMPLETED"), router_risultato()],
        immagine=PNG,
    )
    motore = provider_comfy(trasporto)
    sentiti = []
    motore.avanzamento = sentiti.append
    motore.genera(richiesta())
    assert sentiti == ["inviato", "inviato", "in lavorazione"]


def test_chi_ascolta_l_avanzamento_puo_fermare_l_attesa(modello_verificato):
    """Caso: l'utente annulla mentre il Router lavora, e il motore continua ad aspettare."""

    class Fermati(Exception):
        pass

    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("IN_PROGRESS"), router_stato("COMPLETED"),
         router_risultato()],
        immagine=PNG,
    )
    motore = provider_comfy(trasporto)

    def ascolta(stato):
        if stato == "in lavorazione":
            raise Fermati()

    motore.avanzamento = ascolta
    with pytest.raises(Fermati):
        motore.genera(richiesta())
    assert trasporto.scaricati == []
