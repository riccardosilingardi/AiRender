"""FLUX «Geometria rigida» su fal: senza rete e senza chiave vera.

Caso che protegge: la vista parte verso fal senza che lo Studio l'abbia
detto, senza mappe, o con la regola delle mappe scritta per Nano Banana.
"""

from __future__ import annotations

import base64
import io
import json

import pytest
from PIL import Image

from core import config, mappe
from core.errori import ChiaveMancante, ErroreProvider
from core.provider import ProviderFal, RichiestaGenerazione, crea, fal

from conftest import vista_shaded


def _png(larghezza: int, altezza: int, colore=(200, 200, 200)) -> bytes:
    deposito = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), colore).save(deposito, format="PNG")
    return deposito.getvalue()


RENDER = _png(1536, 1024, (90, 120, 160))


class TrasportoFalFinto:
    def __init__(self, stati=("IN_PROGRESS", "COMPLETED"), risultato=None, stato_invio=200):
        self.chiamate: list[tuple[str, str, dict, dict | None]] = []
        self._stati = list(stati)
        self._stato_invio = stato_invio
        self._risultato = risultato or {
            "images": [{"url": "data:image/png;base64," + base64.b64encode(RENDER).decode()}],
            "seed": 4253, "has_nsfw_concepts": [False],
        }

    def chiama(self, metodo, url, intestazioni, corpo=None):
        self.chiamate.append((metodo, url, intestazioni, corpo))
        if metodo == "POST":
            if self._stato_invio >= 400:
                return self._stato_invio, {}, {"detail": "no"}
            return 200, {}, {"request_id": "r1", "status": "IN_QUEUE",
                             "status_url": "https://queue.fal.run/fal-ai/flux-general/requests/r1/status",
                             "response_url": "https://queue.fal.run/fal-ai/flux-general/requests/r1"}
        if url.endswith("/status"):
            return 200, {}, {"status": self._stati.pop(0)}
        return 200, {}, self._risultato

    def scarica(self, url):
        raise AssertionError("con sync_mode l'immagine arriva nel risultato")


def _richiesta(prompt="A photograph of image 1.", in_piu=None) -> RichiestaGenerazione:
    vista = vista_shaded(1200, 800)
    return RichiestaGenerazione(
        immagine=vista, prompt=f"{prompt}\n\n{mappe.regola(2)}", preset="p", preset_versione="1",
        modello=fal.MODELLO, grana="media", dettaglio_grana=0,
        immagini_in_piu=in_piu if in_piu is not None else (_png(1200, 800, (0, 0, 0)), _png(1200, 800, (128, 128, 128))),
    )


def _provider(trasporto) -> ProviderFal:
    return ProviderFal(chiave="chiave-finta", trasporto=trasporto, attesa=lambda _s: None, nuovo_seme=lambda: 7)


def test_fal_e_nel_registro_e_annuncia_stati_uniti_prima_dell_invio():
    motore = crea("fal", chiave="chiave-finta")
    assert isinstance(motore, ProviderFal)
    assert "Stati Uniti" in motore.destinazione_per(fal.MODELLO)
    assert "fal.ai" in motore.destinazione_per(fal.MODELLO)
    assert "non commerciale" in motore.avviso(fal.MODELLO)


def test_senza_fal_key_non_parte_niente_e_lo_dice_prima():
    motore = ProviderFal(trasporto=TrasportoFalFinto())
    assert "FAL_KEY" in motore.cosa_manca(fal.MODELLO)
    with pytest.raises(ChiaveMancante):
        motore.genera(_richiesta())


def test_genera_manda_la_ricetta_della_prova_con_vista_e_mappe_alla_stessa_misura():
    trasporto = TrasportoFalFinto()
    risultato = _provider(trasporto).genera(_richiesta())
    metodo, url, intestazioni, corpo = trasporto.chiamate[0]
    assert (metodo, url) == ("POST", f"{fal.CODA}/{fal.MODELLO}")
    assert intestazioni["Authorization"] == "Key chiave-finta"
    assert intestazioni["X-Fal-Store-IO"] == "0"
    assert corpo["strength"] == config.FAL_FORZA_IMG2IMG and corpo["seed"] == 7
    assert corpo["sync_mode"] is True
    assert corpo["image_size"] == {"width": 1536, "height": 1024}
    unione = corpo["controlnet_unions"][0]
    assert unione["path"] == fal.CONTROLNET
    modi = [(c["control_mode"], c["conditioning_scale"]) for c in unione["controls"]]
    assert modi == [("canny", config.FAL_CONTROLLO_SPIGOLI), ("depth", config.FAL_CONTROLLO_PROFONDITA)]
    for dato in (corpo["image_url"], *(c["control_image_url"] for c in unione["controls"])):
        grezzo = base64.b64decode(dato.split(",", 1)[1])
        assert Image.open(io.BytesIO(grezzo)).size == (1536, 1024)
    # La regola delle mappe e' per Nano Banana: a FLUX parte il prompt senza.
    assert corpo["prompt"] == "A photograph of image 1."
    assert risultato.ricetta.provider == "fal" and risultato.ricetta.seme == 4253
    assert "data:" not in json.dumps(risultato.ricetta.parametri)
    assert any("listino fal" in a for a in risultato.avvisi)
    assert Image.open(io.BytesIO(risultato.immagine)).size == (1536, 1024)


def test_senza_le_due_mappe_si_ferma_prima_di_mandare():
    trasporto = TrasportoFalFinto()
    with pytest.raises(ErroreProvider, match="mappe"):
        _provider(trasporto).genera(_richiesta(in_piu=()))
    assert trasporto.chiamate == []


def test_chiave_rifiutata_lo_dice_con_le_parole_di_fal():
    with pytest.raises(ErroreProvider, match="chiave"):
        _provider(TrasportoFalFinto(stato_invio=401)).genera(_richiesta())


def test_riferimenti_e_materiali_non_entrano_ma_le_mappe_si():
    motore = _provider(TrasportoFalFinto())
    assert not motore.accetta_piu_immagini(fal.MODELLO)
    assert motore.accetta_mappe(fal.MODELLO) and motore.vuole_mappe(fal.MODELLO)


def test_studio_mostra_flux_solo_con_fal_key_e_lo_manda_sempre_a_fal(monkeypatch, tmp_path):
    from core.studio import servizio

    assert servizio.MODELLO_GEOMETRIA_RIGIDA not in servizio.modelli_visibili()
    monkeypatch.setenv("FAL_KEY", "chiave-finta")
    assert servizio.MODELLO_GEOMETRIA_RIGIDA in servizio.modelli_visibili()
    studio = servizio.Studio(tmp_path, provider="comfy")
    assert studio.provider_per(fal.MODELLO) == "fal"
    assert studio.provider_per(servizio.MODELLI[0].identificativo) == "comfy"
    d = studio.destinazione(fal.MODELLO, geometria=True)
    assert "Stati Uniti" in d["destinazione"] and d["personale"] and d["cosa_manca"] is None
    assert d["mappe_obbligatorie"] is None and d["mappe_non_accettate"] is None
    assert "listino fal" in d["costo"]
    senza = studio.destinazione(fal.MODELLO, geometria=False)
    assert "Tieni la geometria" in senza["mappe_obbligatorie"]
    assert studio.destinazione(fal.MODELLO, riferimento=True, geometria=True)["riferimento_non_accettato"]
