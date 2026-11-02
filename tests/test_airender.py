"""Il provider dei crediti AIRENDER e il codice licenza."""

from __future__ import annotations

import pytest

from conftest import OrologioFinto, TrasportoComfyFinto, router_in_coda, router_stato, vista_shaded
from core import cli, config, grana, licenza
from core import provider as registro
from core.errori import ChiaveMancante, ErroreProvider
from core.provider.airender import ProviderAirender
from core.provider.base import RichiestaGenerazione

CODICE = "AIR-0000-1111-2222-3333"


def _richiesta(**cambi) -> RichiestaGenerazione:
    base = dict(
        immagine=vista_shaded(), prompt="prompt", preset="base", preset_versione="3",
        modello=config.NANO_BANANA_2, grana=grana.MEDIA, dettaglio_grana=0,
    )
    base.update(cambi)
    return RichiestaGenerazione(**base)


def _provider(trasporto, chiave=CODICE):
    orologio = OrologioFinto()
    return ProviderAirender(chiave=chiave, trasporto=trasporto, attesa=orologio.attendi,
                            orologio=orologio.leggi, nuova_chiave_idempotenza=lambda: "idem-1")


def _risultato_gemini(intestazioni=None):
    corpo = {"candidates": [{"content": {"parts": [{"fileData": {"mimeType": "image/png", "fileUri": "https://storage/x.png"}}]}}]}
    return 200, dict(intestazioni or {}), corpo


def test_codice_si_normalizza_come_sul_server():
    assert licenza.valido("air oOlI abcd efgh jkOl")
    assert licenza.formatta("air oOlI abcd efgh jkOl") == "AIR-0011-ABCD-EFGH-JK01"
    assert not licenza.valido("AIR-1234")


def test_codice_si_salva_fuori_dal_repository_e_rende_predefinito_airender(tmp_path):
    assert registro.predefinito() == "comfy"
    percorso = licenza.salva("air-0000-1111-2222-3333")
    assert percorso.read_text(encoding="utf-8").strip() == CODICE
    assert "AiRender" not in str(percorso.parent) or "appdata" in str(percorso).lower()
    assert licenza.leggi() == CODICE
    assert registro.predefinito() == "airender"


def test_codice_sbagliato_non_si_salva():
    with pytest.raises(ChiaveMancante):
        licenza.salva("comfyui-abc")


def test_senza_codice_non_parte_niente_e_dice_come_incollarlo():
    trasporto = TrasportoComfyFinto([])
    with pytest.raises(ChiaveMancante) as errore:
        _provider(trasporto, chiave="").genera(_richiesta())
    assert "--licenza" in errore.value.cosa_fare
    assert trasporto.chiamate == []


def test_il_render_va_al_server_airender_col_codice_e_non_con_la_chiave_comfy(monkeypatch):
    monkeypatch.setenv("COMFY_API_KEY", "comfyui-NO")
    monkeypatch.setenv("AIRENDER_SERVER", "https://server.prova/")
    trasporto = TrasportoComfyFinto([
        router_in_coda(),
        router_stato("COMPLETED"),
        _risultato_gemini({"x-airender-render-scalati": "1", "x-airender-saldo": "41"}),
    ])
    risultato = _provider(trasporto).genera(_richiesta())
    metodo, url, intestazioni, _ = trasporto.chiamate[0]
    assert url == f"https://server.prova/v2/models/{config.NANO_BANANA_2}/requests?fallback_provider=false"
    assert intestazioni["X-Airender-Licenza"] == CODICE
    assert intestazioni["X-Airender-Canale"] == "plugin"
    assert len(intestazioni["X-Airender-Postazione"]) == 32
    assert all("comfyui-" not in str(v) for _, _, h, _ in trasporto.chiamate for v in h.values())
    assert risultato.ricetta.provider == "airender"
    assert risultato.ricetta.parametri["render_scalati"] == "1"
    assert risultato.ricetta.parametri["saldo_dopo"] == "41"


def test_saldo_finito_dice_ricarica_con_la_frase_del_server():
    corpo = {"error": {"type": "insufficient_credits",
                       "message": "Il saldo AIRENDER non basta: questo render costa 2 e ne restano 1."},
             "cosa_fare": "Premi Ricarica, poi rilancia."}
    trasporto = TrasportoComfyFinto([(402, {}, corpo)])
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(_richiesta())
    assert errore.value.stato == 402
    assert "non basta" in errore.value.fatto
    assert "Ricarica" in errore.value.cosa_fare
    assert "Comfy" not in errore.value.fatto


def test_modello_fuori_listino_si_annuncia_prima_dell_invio():
    p = _provider(TrasportoComfyFinto([]))
    assert "chiave Comfy" in p.cosa_manca("bfl/flux-kontext-pro")
    assert p.cosa_manca(config.NANO_BANANA_2) is None
    assert "server AIRENDER" in p.destinazione_per(config.NANO_BANANA_2)


def test_vista_troppo_pesante_per_il_server_si_ferma_prima(monkeypatch):
    monkeypatch.setattr(config, "SERVER_INVIO_MASSIMO_MB", 0.0001)
    trasporto = TrasportoComfyFinto([])
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(_richiesta())
    assert "server AIRENDER" in errore.value.fatto
    assert trasporto.chiamate == []


def test_peso_render_dal_listino():
    assert licenza.peso_render(config.NANO_BANANA_2, "2k") == 1
    assert licenza.peso_render(config.NANO_BANANA_PRO, "4k") == 3
    assert licenza.peso_render("bfl/flux-kontext-pro", "1k") is None


def test_riga_di_comando_incolla_il_codice_e_legge_il_saldo(monkeypatch, capsys):
    letti = {}

    def saldo_finto(codice=None, trasporto=None):
        letti["codice"] = licenza.leggi()
        return {"ultime_cifre": "3333", "email": "a@b.it", "funzioni": {"nome": "Pro"}, "saldo": 42,
                "in_attesa": 0, "prossima_scadenza": {"quantita": 10, "il": "2027-11-02T00:00:00Z"},
                "ricarica_url": "https://s/api/acquista?prodotto=ricarica&t=x"}

    monkeypatch.setattr(licenza, "saldo", saldo_finto)
    assert cli.main(["--licenza", CODICE, "--saldo"]) == 0
    uscita = capsys.readouterr().out
    assert "Codice licenza salvato" in uscita
    assert "Render disponibili: 42" in uscita
    assert "Ricarica" in uscita
    assert letti["codice"] == CODICE


def test_preset_vale_anche_per_i_crediti_airender():
    from core.preset import elenco
    for p in elenco():
        if "comfy" in p.modelli:
            assert p.modello_per("airender") == p.modelli["comfy"]
