"""Il provider dei crediti AIRENDER e il codice licenza."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


def _risultato_vuoto(scalati):
    corpo = {"candidates": [{"content": {"parts": [{"text": "non posso"}]}}]}
    return 200, {"x-airender-render-scalati": scalati}, corpo


def test_render_vuoto_rimborsato_lo_dice():
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("COMPLETED"), _risultato_vuoto("0")])
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(_richiesta())
    assert "non e' stato scalato" in errore.value.fatto


def test_render_vuoto_oltre_il_tetto_dice_che_e_stato_scalato_e_perche():
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("COMPLETED"), _risultato_vuoto("1")])
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(_richiesta())
    assert "e' stato scalato (1)" in errore.value.fatto
    assert str(config.LISTINO["rimborsi_senza_immagine_24h"]) in errore.value.fatto


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


def _rumore(lato: int, seme: int) -> bytes:
    import io, random
    from PIL import Image
    casuale = random.Random(seme)
    immagine = Image.frombytes("RGB", (lato, lato), bytes(casuale.getrandbits(8) for _ in range(lato * lato * 3)))
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


def _base64_inviato(trasporto) -> int:
    import json
    return len(json.dumps(trasporto.chiamate[0][3]))


def test_riferimenti_troppo_pesanti_insieme_si_rimpiccioliscono_e_la_vista_resta_intera():
    vista = _rumore(500, 1)
    riferimenti = (_rumore(1100, 2), _rumore(1100, 3))
    assert sum(len(d) for d in (vista, *riferimenti)) * 4 / 3 / 2**20 > config.SERVER_CORPO_MASSIMO_MB
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("COMPLETED"), _risultato_gemini()])
    risultato = _provider(trasporto).genera(_richiesta(
        immagine=vista, modello=config.NANO_BANANA_PRO, immagini_in_piu=riferimenti))
    import base64
    assert base64.b64encode(vista).decode() in str(trasporto.chiamate[0][3])
    assert _base64_inviato(trasporto) / 2**20 < 6
    assert any("rimpicciolite" in a for a in risultato.avvisi)


def test_se_anche_rimpicciolito_non_ci_sta_si_ferma_prima_di_ogni_chiamata(monkeypatch):
    monkeypatch.setattr(config, "SERVER_CORPO_MASSIMO_MB", 0.001)
    trasporto = TrasportoComfyFinto([])
    with pytest.raises(ErroreProvider) as errore:
        _provider(trasporto).genera(_richiesta(
            modello=config.NANO_BANANA_PRO, immagini_in_piu=(_rumore(300, 4),)))
    assert "non e' stato scalato credito" in errore.value.fatto
    assert "Togli un riferimento" in errore.value.cosa_fare
    assert trasporto.chiamate == []


def test_invio_leggero_parte_com_e():
    riferimento = _rumore(64, 5)
    trasporto = TrasportoComfyFinto([router_in_coda(), router_stato("COMPLETED"), _risultato_gemini()])
    risultato = _provider(trasporto).genera(_richiesta(
        modello=config.NANO_BANANA_PRO, immagini_in_piu=(riferimento,)))
    import base64
    assert base64.b64encode(riferimento).decode() in str(trasporto.chiamate[0][3])
    assert not any("rimpicciolite" in a for a in risultato.avvisi)


def test_una_mappa_a_pochi_colori_resta_png_e_non_mescola_i_colori():
    import io
    from PIL import Image
    from core import immagine as modulo_immagine
    mappa = Image.new("RGB", (2000, 1000), (255, 0, 0))
    mappa.paste((0, 0, 255), (1000, 0, 2000, 1000))
    uscita = io.BytesIO()
    mappa.save(uscita, format="PNG")
    ridotta = Image.open(io.BytesIO(modulo_immagine.riduci_lato(uscita.getvalue(), 500)))
    assert ridotta.format == "PNG" and ridotta.size == (500, 250)
    assert sorted(c for _, c in ridotta.getcolors(16)) == [(0, 0, 255), (255, 0, 0)]


@pytest.mark.parametrize("primo", ["core.licenza", "core.cli"])
def test_licenza_si_importa_per_prima_senza_import_circolare(primo):
    """`python -m core.cli` carica licenza prima di provider: un tempo falliva."""
    radice = Path(__file__).resolve().parent.parent
    esito = subprocess.run([sys.executable, "-c", f"import {primo}"], cwd=radice,
                           capture_output=True, text=True)
    assert esito.returncode == 0, esito.stderr


@pytest.mark.parametrize("indirizzo", ["http://server.prova", "server.prova", "ftp://server.prova"])
def test_il_codice_licenza_non_parte_mai_in_chiaro_verso_un_altro_pc(monkeypatch, indirizzo):
    monkeypatch.setenv("AIRENDER_SERVER", indirizzo)
    with pytest.raises(ErroreProvider) as errore:
        licenza.server()
    assert "https" in errore.value.fatto


@pytest.mark.parametrize("indirizzo", ["https://server.prova", "http://localhost:8888", "http://127.0.0.1:8888/"])
def test_https_o_lo_stesso_pc_vanno_bene(monkeypatch, indirizzo):
    monkeypatch.setenv("AIRENDER_SERVER", indirizzo)
    assert licenza.server() == indirizzo.rstrip("/")
