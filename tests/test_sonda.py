"""La sonda di Comfy Router, provata senza rete.

La sua uscita viene incollata in una conversazione: il test che conta di piu'
e' che la chiave non ci finisca dentro, nemmeno se il servizio la ripete.
"""

from __future__ import annotations

import base64
import email.message
import io
import json
import sys
import urllib.error
from pathlib import Path

import pytest

from conftest import OrologioFinto, vista_shaded

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sonda_comfy as sonda  # noqa: E402  pylint: disable=wrong-import-position

CHIAVE = "chiave-finta-segretissima-0123456789"
PNG_GENERATO = vista_shaded(640, 360)


class Risposta:
    def __init__(self, stato: int, corpo, intestazioni=None):
        self.status = stato
        self._corpo = corpo if isinstance(corpo, bytes) else json.dumps(corpo).encode()
        self.headers = email.message.Message()
        for nome, valore in (intestazioni or {}).items():
            self.headers[nome] = valore

    def read(self):
        return self._corpo

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class RouterFinto:
    """Risponde in ordine e ricorda ogni richiesta, intestazioni comprese."""

    def __init__(self, risposte):
        self.risposte = list(risposte)
        self.richieste = []

    def __call__(self, richiesta, timeout=None):
        self.richieste.append(richiesta)
        risposta = self.risposte.pop(0)
        if risposta.status >= 400:
            raise urllib.error.HTTPError(
                richiesta.full_url, risposta.status, "errore", risposta.headers,
                io.BytesIO(risposta.read()),
            )
        return risposta


def percorso_riuscito():
    return [
        Risposta(200, {"openapi": "3.1.0", "paths": {}}),
        Risposta(201, {"request_id": "rq-1", "status": "IN_QUEUE"}, {"Retry-After": "5"}),
        Risposta(200, {"status": "IN_PROGRESS"}, {"Retry-After": "2"}),
        Risposta(200, {"status": "COMPLETED"}),
        Risposta(200, {"result": {"sample": "https://consegna.esempio/x.png?firma=abc&eco=" + CHIAVE}}),
        Risposta(200, PNG_GENERATO),
    ]


def lancia(router, tmp_path, monkeypatch, *argomenti):
    monkeypatch.setenv(sonda.VARIABILE_CHIAVE, CHIAVE)
    vista = tmp_path / "vista.png"
    vista.write_bytes(vista_shaded(1536, 857))
    flusso = io.StringIO()
    orologio = OrologioFinto()
    codice = sonda.main(
        ["--immagine", str(vista), "--uscita", str(tmp_path / "uscita"), *argomenti],
        apri=router, flusso=flusso, attendi=orologio.attendi, orologio=orologio.leggi,
    )
    return codice, flusso.getvalue(), orologio


def test_la_chiave_non_compare_mai_nell_uscita_da_incollare(tmp_path, monkeypatch):
    """Caso: l'uscita finisce in una chat. Se il servizio ripete la chiave, non deve passare."""
    codice, uscita, _ = lancia(RouterFinto(percorso_riuscito()), tmp_path, monkeypatch)
    assert codice == 0
    assert CHIAVE not in uscita
    assert "firma=abc" not in uscita


def test_una_sola_generazione_con_la_stessa_chiave_di_idempotenza(tmp_path, monkeypatch):
    """Caso: la sonda e' 'una chiamata'. Un secondo POST sarebbe una seconda spesa."""
    router = RouterFinto(percorso_riuscito())
    _codice, uscita, _ = lancia(router, tmp_path, monkeypatch)
    poste = [r for r in router.richieste if r.get_method() == "POST"]
    assert len(poste) == 1
    assert "fallback_provider=false" in poste[0].full_url
    assert poste[0].full_url.startswith(f"{sonda.BASE}/bfl/flux-kontext-pro/requests")
    chiave_idempotenza = poste[0].get_header("Idempotency-key")
    assert chiave_idempotenza and chiave_idempotenza in uscita
    corpo = json.loads(poste[0].data)
    assert corpo["input_image"].startswith("data:image/png;base64,")
    assert corpo["aspect_ratio"] == "16:9"


def test_l_attesa_rispetta_retry_after(tmp_path, monkeypatch):
    """Caso: il Router dice quando ha senso ripassare. Martellarlo fa scattare i limiti."""
    _codice, _uscita, orologio = lancia(RouterFinto(percorso_riuscito()), tmp_path, monkeypatch)
    assert orologio.attese == [5.0, 2.0]


def test_il_link_dell_immagine_si_scarica_senza_la_chiave(tmp_path, monkeypatch):
    """Caso: il link firmato e' di un altro dominio. La chiave non deve viaggiare fin li'."""
    router = RouterFinto(percorso_riuscito())
    _codice, uscita, _ = lancia(router, tmp_path, monkeypatch)
    scaricamento = router.richieste[-1]
    assert scaricamento.full_url.startswith("https://consegna.esempio/")
    assert scaricamento.get_header("X-api-key") is None
    salvata = tmp_path / "uscita" / "bfl_flux-kontext-pro.png"
    assert salvata.read_bytes() == PNG_GENERATO
    assert "Rapporto: vista 1.792, render 1.778" in uscita


def test_il_credito_finito_si_vede_e_non_parte_altro(tmp_path, monkeypatch):
    """Caso: workspace senza crediti. La sonda mostra la risposta e si ferma."""
    router = RouterFinto([
        Risposta(200, {"openapi": "3.1.0", "paths": {}}),
        Risposta(402, {"error": {"type": "insufficient_credits"}},
                 {"X-Comfy-Error-Type": "insufficient_credits"}),
    ])
    codice, uscita, _ = lancia(router, tmp_path, monkeypatch)
    assert codice == 3
    assert "HTTP 402" in uscita and "insufficient_credits" in uscita
    assert len(router.richieste) == 2


def test_solo_schema_non_spende_niente(tmp_path, monkeypatch):
    """Caso: si vuole vedere lo schema prima di pagare."""
    router = RouterFinto([Risposta(200, {"openapi": "3.1.0", "paths": {}})])
    codice, _uscita, _ = lancia(router, tmp_path, monkeypatch, "--solo-schema")
    assert codice == 0
    assert [r.get_method() for r in router.richieste] == ["GET"]


@pytest.mark.parametrize("nudo", [False, True])
def test_gemini_riceve_l_immagine_dentro_inline_data(nudo):
    """Caso: la famiglia Gemini ha un corpo diverso; il base64 nudo e' un'opzione esplicita."""
    dati = vista_shaded(800, 600)
    corpo = sonda.corpo_candidato("vertexai/gemini-3.1-flash-image", "p", dati, nudo)
    parte = corpo["contents"][0]["parts"][1]["inlineData"]
    assert parte["mimeType"] == "image/png"
    assert parte["data"].startswith("data:") is not nudo
    assert base64.b64decode(parte["data"].split(",")[-1]) == dati
    assert corpo["generationConfig"]["imageConfig"]["aspectRatio"] == "4:3"
