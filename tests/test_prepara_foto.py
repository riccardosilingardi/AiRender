"""«Prepara la foto» del Fotoinserimento, senza rete.

Il provider e' finto: qui si prova che la coda mandi prima la pulizia a
Nano Banana 2 e poi l'ingrandimento a Magnific, che il risultato finisca fra
i contesti come una foto caricata, che una pulizia pagata resti anche se
l'ingrandimento fallisce, e che lo Studio non mandi niente verso una
destinazione che la pagina non ha mostrato (regola 5).
"""

from __future__ import annotations

import http.client
import json

import pytest

from conftest import vista_shaded
from core import blocchi, config, contesto, prepara_foto
from core.errori import ErroreProvider
from core.provider import comfy
from core.studio.server import avvia_in_sottofondo, crea_server
from core.studio.servizio import RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

FOTO = vista_shaded(320, 200)


class ProviderEco(ProviderDiProva):
    """Rimanda la foto com'e'; l'ingrandimento puo' fallire a comando."""

    def __init__(self, registro, errore_ingrandimento=None):
        super().__init__(registro, eco=True)
        self.errore_ingrandimento = errore_ingrandimento

    def genera(self, richiesta):
        if richiesta.modello == prepara_foto.MODELLO_INGRANDIMENTO and self.errore_ingrandimento:
            self.registro.append(richiesta)
            raise self.errore_ingrandimento
        return super().genera(richiesta)


def _foto(radice):
    nome = contesto.salva(radice, FOTO)
    return contesto.cartella_contesti(radice) / nome


def _coda(radice, registro, **altro):
    return prepara_foto.CodaPreparazioni(radice, crea_provider=lambda _n: ProviderEco(registro, **altro),
                                         dire=lambda _t: None)


def _in_coda(radice, ingrandimento=config.PREPARA_FOTO_INGRANDIMENTO, inquadratura=blocchi.VOLO):
    destinazione = ProviderDiProva([]).destinazione_per
    return prepara_foto.metti_in_coda(
        radice, _foto(radice), inquadratura, provider="prova",
        destinazione=destinazione(prepara_foto.MODELLO_PULIZIA),
        destinazione_ingrandimento=destinazione(prepara_foto.MODELLO_INGRANDIMENTO) if ingrandimento else "",
        ingrandimento=ingrandimento)


def test_il_prompt_toglie_le_scritte_e_non_sposta_niente():
    for inquadratura in (blocchi.ZENITALE, blocchi.VOLO, blocchi.TERRA):
        testo = prepara_foto.prompt(inquadratura)
        assert "labels" in testo and "Do not crop, zoom, rotate or shift" in testo
    assert "Google Earth 3D" in prepara_foto.prompt(blocchi.VOLO)
    with pytest.raises(prepara_foto.PreparazioneNonValida):
        prepara_foto.prompt("di lato")


def test_la_coda_pulisce_poi_ingrandisce_e_salva_fra_i_contesti(tmp_path):
    registro = []
    preparazione = _in_coda(tmp_path)
    assert _coda(tmp_path, registro).esegui_uno() == preparazione.identificativo
    pulizia, ingrandimento = registro
    assert (pulizia.modello, pulizia.dimensione_render) == (config.NANO_BANANA_2, config.PREPARA_FOTO_RISOLUZIONE)
    assert pulizia.immagini_in_piu == () and "Google Earth 3D" in pulizia.prompt
    assert (ingrandimento.modello, ingrandimento.ingrandimento, ingrandimento.tipo_finale) == (
        comfy.MODELLO_FINALE, config.PREPARA_FOTO_INGRANDIMENTO, "foto")
    stato = prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)
    assert stato["stato"] == prepara_foto.FATTO and stato["ingrandita"] is True and stato["avviso"] is None
    # Fra i contesti, come una foto caricata: il Fotoinserimento la puo' usare.
    pronta = contesto.controlla_file(tmp_path, contesto.cartella_contesti(tmp_path) / stato["preparata"])
    assert (stato["larghezza"], stato["altezza"]) == (320, 200)
    ricetta = json.loads((pronta.parent / f"{pronta.name}.ricetta.json").read_text(encoding="utf-8"))
    assert len(ricetta["invii"]) == 2 and ricetta["originale"] == _foto(tmp_path).name


def test_senza_ingrandimento_parte_solo_la_pulizia(tmp_path):
    registro = []
    preparazione = _in_coda(tmp_path, ingrandimento=0)
    _coda(tmp_path, registro).esegui_uno()
    assert [r.modello for r in registro] == [config.NANO_BANANA_2]
    assert prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)["ingrandita"] is False


def test_se_l_ingrandimento_fallisce_la_pulizia_pagata_resta(tmp_path):
    preparazione = _in_coda(tmp_path)
    _coda(tmp_path, [], errore_ingrandimento=ErroreProvider("Magnific non risponde.", "Riprova.")).esegui_uno()
    stato = prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)
    assert stato["stato"] == prepara_foto.FATTO and stato["ingrandita"] is False
    assert "Magnific non risponde." in stato["avviso"]


def test_un_errore_della_pulizia_resta_sulla_preparazione(tmp_path):
    preparazione = _in_coda(tmp_path)
    coda = prepara_foto.CodaPreparazioni(
        tmp_path, crea_provider=lambda _n: ProviderDiProva([], errore=ErroreProvider("Crediti finiti.", "Ricarica.")),
        dire=lambda _t: None)
    coda.esegui_uno()
    stato = prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)
    assert (stato["stato"], stato["fatto"], stato["cosa_fare"]) == (prepara_foto.ERRORE, "Crediti finiti.", "Ricarica.")


def test_una_destinazione_cambiata_ferma_prima_di_mandare(tmp_path):
    registro = []
    preparazione = prepara_foto.metti_in_coda(tmp_path, _foto(tmp_path), blocchi.ZENITALE, provider="prova",
                                              destinazione="altrove")
    _coda(tmp_path, registro).esegui_uno()
    assert registro == []
    assert prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)["stato"] == prepara_foto.ERRORE


def test_una_preparazione_partita_e_abbandonata_non_si_rimanda(tmp_path):
    preparazione = _in_coda(tmp_path)
    prepara_foto.scrivi_stato(tmp_path, preparazione.identificativo, prepara_foto.PULIZIA)
    assert _coda(tmp_path, []).recupera_abbandonati() == [preparazione.identificativo]
    assert "crediti" in prepara_foto.leggi_stato(tmp_path, preparazione.identificativo)["cosa_fare"]


def test_annulla_toglie_solo_una_preparazione_ancora_in_coda(tmp_path):
    preparazione = _in_coda(tmp_path)
    assert prepara_foto.annulla(tmp_path, preparazione.identificativo) is True
    assert prepara_foto.annulla(tmp_path, preparazione.identificativo) is False
    assert _coda(tmp_path, []).esegui_uno() is None


def test_una_foto_fuori_dalla_cartella_dei_contesti_non_entra(tmp_path):
    (tmp_path / "fuori.png").write_bytes(FOTO)
    with pytest.raises(contesto.ContestoNonValido):
        prepara_foto.metti_in_coda(tmp_path, tmp_path / "fuori.png", blocchi.VOLO, provider="prova", destinazione="x")


# --- lo Studio ----------------------------------------------------------------------

def _studio(cartella, registro):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderEco(registro),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def test_lo_studio_dice_dove_va_prima_e_manda_solo_verso_quello(tmp_path):
    studio = _studio(tmp_path, [])
    nome = studio.carica_contesto(FOTO, "earth.png")["nome"]
    composto = studio.componi_preparazione({"nome": nome, "inquadratura": "volo"})
    assert composto["partenza"] == "320 × 200" and composto["volte"] == config.PREPARA_FOTO_INGRANDIMENTO
    assert config.NANO_BANANA_2 in composto["pulizia"]["destinazione"]
    assert comfy.MODELLO_FINALE in composto["ingrandimento"]["destinazione"]
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia_preparazione({"nome": nome, "inquadratura": "volo", "destinazione_mostrata": "altrove"})
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia_preparazione({"nome": nome, "inquadratura": "volo", "ingrandisci": True,
                                   "destinazione_mostrata": composto["pulizia"]["destinazione"],
                                   "destinazione_ingrandimento_mostrata": "altrove"})
    esito = studio.invia_preparazione({
        "nome": nome, "inquadratura": "volo", "ingrandisci": True,
        "destinazione_mostrata": composto["pulizia"]["destinazione"],
        "destinazione_ingrandimento_mostrata": composto["ingrandimento"]["destinazione"]})
    assert studio.stato_preparazione(esito["identificativo"])["stato"] == prepara_foto.IN_CODA
    with pytest.raises(RichiestaStudioNonValida):
        studio.stato_preparazione("../../x")


def test_le_rotte_di_prepara_la_foto(tmp_path):
    registro = []
    studio = _studio(tmp_path, registro)
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    porta = servito.server_address[1]

    def chiedi(metodo, percorso, corpo=None, intestazioni=None):
        connessione = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        connessione.request(metodo, percorso, body=corpo,
                            headers={"Host": f"127.0.0.1:{porta}", "X-Airender": "1", **(intestazioni or {})})
        risposta = connessione.getresponse()
        return risposta.status, json.loads(risposta.read() or b"null")

    try:
        _stato, caricata = chiedi("POST", "/api/contesti", FOTO, {"X-Nome-File": "earth.png"})
        richiesta = {"nome": caricata["nome"], "inquadratura": "zenitale"}
        stato, composto = chiedi("POST", "/api/contesti/prepara/componi", json.dumps(richiesta).encode())
        assert stato == 200 and composto["risoluzione"] == "2K"
        stato, esito = chiedi("POST", "/api/contesti/prepara", json.dumps(
            {**richiesta, "destinazione_mostrata": composto["pulizia"]["destinazione"]}).encode())
        assert stato == 200
        identificativo = esito["identificativo"]
        stato, voce = chiedi("GET", f"/api/contesti/prepara/{identificativo}")
        assert voce["stato"] == prepara_foto.IN_CODA
        stato, voce = chiedi("POST", f"/api/contesti/prepara/{identificativo}/annulla", b"{}")
        assert voce == {"annullato": True}
        assert registro == []
    finally:
        servito.shutdown()
        servito.server_close()
