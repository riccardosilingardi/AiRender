"""«Riaggancia alla vista»: un render gia' fatto ripassa nel ControlNet guidato dalla vista.

Nessuna rete: l'API v2 dei workflow e' il finto di test_geometria. Il
workflow vero non e' mai partito (PRD, NON VERIFICATO): qui si prova che il
render entri nel latente al posto del foglio vuoto, che partano vista e
render e nient'altro, che Nano Banana non riceva niente e che il risultato
sia un passo figlio misurato contro la vista.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import blocchi, coda as modulo_coda, config
from core.coda import FATTO, Lavoro, LavoroNonValido, leggi_stato
from core.provider import geometria as modulo_geometria
from core.studio.servizio import RichiestaStudioNonValida
from test_geometria import BASE, ComfyFinto, _coda, _png, _studio
from test_passi import NANO, VISTA, _dest, cartella, chiamate  # noqa: F401


def _primo_render(studio, cartella, chiamate):
    """Un render da Genera, senza «Tieni la geometria», fatto dalla coda."""
    identificativo = studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(),
                                   "preset": "rivista", "modello": NANO,
                                   "destinazione_mostrata": _dest(studio)})["identificativo"]
    _coda(cartella, chiamate, ComfyFinto()).esegui_uno()
    assert leggi_stato(cartella, identificativo)["stato"] == FATTO
    return identificativo


def _riaggancia(studio, da, **altro):
    composto = studio.componi_riaggancia({"vista": VISTA, "da": da, **altro})
    return studio.invia_riaggancia({"vista": VISTA, "da": da, "destinazione_mostrata": composto["destinazione"],
                                    **altro})["identificativo"]


def test_il_grafo_del_riaggancio_parte_dal_render_e_tiene_i_controlli_della_vista():
    grafo = modulo_geometria.workflow("vista-1", "x", 3, ("spigoli", "profondita"), render="render-1")
    assert modulo_geometria.NODO_LATENTE_VUOTO not in grafo
    assert grafo["9"]["inputs"]["latent_image"] == [modulo_geometria.NODO_LATENTE_RENDER, 0]
    assert grafo["9"]["inputs"]["denoise"] == config.GEOMETRIA_RIAGGANCIA_DENOISE
    assert grafo[modulo_geometria.NODO_RENDER]["inputs"]["image"]["info"]["id"] == "render-1"
    # I controlli leggono la vista, non il render.
    assert grafo["3"]["inputs"]["image"] == ["2", 0] and grafo["17"]["inputs"]["image"] == ["2", 0]
    assert grafo["1"]["inputs"]["image"]["info"]["id"] == "vista-1"
    for nodo in grafo.values():
        for valore in nodo["inputs"].values():
            if isinstance(valore, list):
                assert valore[0] in grafo


def test_senza_riaggancio_il_grafo_non_porta_i_nodi_del_render():
    grafo = modulo_geometria.workflow("vista-1", "x", 3)
    assert not set(modulo_geometria.NODI_RIAGGANCIA) & set(grafo)
    assert grafo["9"]["inputs"]["denoise"] == 1


def test_riaggancia_manda_vista_e_render_solo_al_workflow_e_fa_un_passo_figlio(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio = _studio(cartella, chiamate)
    da = _primo_render(studio, cartella, chiamate)
    gia = len(chiamate)
    composto = studio.componi_riaggancia({"vista": VISTA, "da": da})
    assert "Nano Banana non riceve niente" in composto["cosa_parte"]
    assert composto["quanto_rifa"] == round(config.GEOMETRIA_RIAGGANCIA_DENOISE * 100)
    identificativo = _riaggancia(studio, da, controlli_geometria=["linee"])
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_RIAGGANCIA and scritto["riaggancia"] is True
    assert scritto["parte_da"] == da and scritto["controlli_geometria"] == ["linee"]

    finto = ComfyFinto()
    _coda(cartella, chiamate, finto).esegui_uno()
    stato = leggi_stato(cartella, identificativo)
    assert stato["stato"] == FATTO, stato
    assert len(chiamate) == gia, "Nano Banana non riceve niente"
    caricati = [c for c in finto.chiamate if c[0] == "ASSET"]
    assert len(caricati) == 2
    assert b'filename="vista.png"' in caricati[0][3] and b'filename="render.png"' in caricati[1][3]
    grafo = next(c for c in finto.chiamate if c[0] == "POST" and c[1].endswith("/jobs"))[3]["workflow"]
    assert grafo["9"]["inputs"]["latent_image"] == ["23", 0] and "20" in grafo and "8" not in grafo
    assert stato["geometria"]["riaggancia"] is True
    # La % di spigoli si misura contro la vista, come per gli altri render.
    assert modulo_coda.leggi_misura(Path(stato["render"])) is not None
    lavoro = studio.lavoro(identificativo)
    assert lavoro["preset_nome"] == "Riaggancia alla vista"
    assert lavoro["modello_nome"] == modulo_geometria.NOME_WORKFLOW

def test_se_la_destinazione_mostrata_e_un_altra_non_parte_niente(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio = _studio(cartella, chiamate)
    da = _primo_render(studio, cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida, match="Non ho inviato niente"):
        studio.invia_riaggancia({"vista": VISTA, "da": da, "destinazione_mostrata": "altrove"})
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_riaggancia_senza_render_si_rifiuta(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    with pytest.raises(RichiestaStudioNonValida):
        _studio(cartella, chiamate).componi_riaggancia({"vista": VISTA, "da": "non-esiste"})


def test_un_file_del_formato_12_senza_render_di_partenza_non_parte():
    dati = {"formato": modulo_coda.FORMATO_RIAGGANCIA, "identificativo": "x", "vista": "v.png", "provider": "p",
            "modello": modulo_coda.MODELLO_RIAGGANCIA, "destinazione": "d", "riaggancia": True,
            "destinazione_geometria": "d", "scelte": blocchi.Scelte().a_dizionario()}
    with pytest.raises(LavoroNonValido, match="Riaggancia"):
        Lavoro.da_dizionario(dati)


def test_un_file_del_formato_12_si_rilegge_uguale(cartella):
    lavoro = Lavoro(identificativo="20261110-000000-abcd", vista=str(cartella / "v.png"), scelte=blocchi.Scelte(),
                    provider="prova", modello=modulo_coda.MODELLO_RIAGGANCIA, destinazione="d",
                    parte_da="p1", partenza=str(cartella / "r.png"), destinazione_geometria="d",
                    controlli_geometria=("profondita",), riaggancia=True)
    riletto = Lavoro.da_dizionario(lavoro.a_dizionario())
    assert riletto.riaggancia and riletto.controlli_geometria == ("profondita",)
    assert riletto.formato == modulo_coda.FORMATO_RIAGGANCIA
    assert riletto.prompt() == modulo_geometria.PROMPT_RIAGGANCIA
    assert _png()  # il finto resta importato per chi legge questo file
