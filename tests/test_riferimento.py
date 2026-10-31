"""Immagine di riferimento per lo stile (prompt 11): Studio, coda, prompt, provider.

Nessuna rete. Il provider finto accetta piu' immagini solo per Nano Banana 2,
come lo schema vero di Comfy.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from conftest import vista_shaded
from core import blocchi, config, coda as modulo_coda
from core.coda import Coda, LavoroNonValido, leggi_stato, metti_in_coda
from core.errori import FileNonTrovato
from core.provider import comfy
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

NANO = MODELLI[0].identificativo
KONTEXT = MODELLI[1].identificativo


class ProviderConDueImmagini(ProviderDiProva):
    def accetta_piu_immagini(self, modello):
        return modello == NANO

    def avviso_piu_immagini(self, modello):
        return "prima prova con due immagini" if modello == NANO else None


def _jpeg(larghezza=300, altezza=200) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), (180, 120, 60)).save(uscita, "JPEG")
    return uscita.getvalue()


@pytest.fixture
def chiamate():
    return []


@pytest.fixture
def cartella(tmp_path) -> Path:
    percorso = tmp_path / "viste"
    percorso.mkdir()
    (percorso / "vista-1.png").write_bytes(vista_shaded(640, 400))
    return percorso


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova",
                  crea_provider=lambda _nome: ProviderConDueImmagini(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _richiesta(studio, modello=NANO, riferimento=None):
    destinazione = studio.destinazione(modello, riferimento=riferimento is not None)
    return {"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista").a_dizionario(),
            "preset": "rivista", "modello": modello,
            "destinazione_mostrata": destinazione["destinazione"], "riferimento": riferimento}


# --- caricare ------------------------------------------------------------------


def test_un_riferimento_si_salva_con_la_sua_impronta_e_si_rilegge(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    dati = _jpeg()
    caricato = studio.carica_riferimento(dati, "tramonto.jpg")
    assert caricato["nome"].startswith("rif-") and caricato["nome"].endswith(".jpg")
    assert (caricato["larghezza"], caricato["altezza"], caricato["da"]) == (300, 200, "tramonto.jpg")
    assert studio.percorso_riferimento(caricato["nome"]).read_bytes() == dati
    assert studio.carica_riferimento(dati)["nome"] == caricato["nome"]  # stesso file, stesso nome


def test_un_riferimento_troppo_pesante_o_che_non_e_un_immagine_si_rifiuta(cartella, chiamate, monkeypatch):
    """Caso: il riferimento si carica e il servizio lo rifiuta solo dopo il clic su Genera."""
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.carica_riferimento(b"GIF89a niente")
    assert "JPEG o un PNG" in errore.value.fatto
    monkeypatch.setattr(config, "COMFY_INVIO_MASSIMO_MB", 0)
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.carica_riferimento(_jpeg())
    assert "ne mandiamo al massimo 0" in errore.value.fatto


def test_un_nome_di_riferimento_non_e_mai_un_percorso(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    for nome in ("../vista-1.png", "vista-1.png", "rif-0123456789abcdef.gif"):
        with pytest.raises(RichiestaStudioNonValida):
            studio.percorso_riferimento(nome)
    with pytest.raises(FileNonTrovato):
        studio.percorso_riferimento("rif-0123456789abcdef.png")


# --- dire prima dove va (regola 5) ------------------------------------------------


def test_la_destinazione_dice_che_partono_due_immagini(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    senza = studio.destinazione(NANO)
    con = studio.destinazione(NANO, riferimento=True)
    assert senza["immagini"] == 1 and senza["avviso_riferimento"] is None
    assert con["immagini"] == 2 and "due immagini" in con["cosa_parte"]
    assert con["avviso_riferimento"] == "prima prova con due immagini"
    assert con["destinazione"] == senza["destinazione"]


def test_con_kontext_il_riferimento_si_spegne_e_non_parte(cartella, chiamate):
    """Caso: FLUX.1 Kontext riceve una immagine sola, e il riferimento sparirebbe in silenzio."""
    studio = _studio(cartella, chiamate)
    modelli = {m["id"]: m for m in studio.catalogo()["modelli"]}
    assert modelli[NANO]["piu_immagini"] and not modelli[KONTEXT]["piu_immagini"]
    assert "una sola immagine" in studio.destinazione(KONTEXT, riferimento=True)["riferimento_non_accettato"]
    nome = studio.carica_riferimento(_jpeg())["nome"]
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia(_richiesta(studio, KONTEXT, nome))
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


# --- in coda e in partenza ------------------------------------------------------


def test_genera_con_riferimento_manda_due_immagini_e_la_frase_del_riferimento(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    dati = _jpeg()
    nome = studio.carica_riferimento(dati)["nome"]
    risposta = studio.invia(_richiesta(studio, riferimento=nome))
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_RIFERIMENTO
    assert Path(scritto["riferimento"]).name == nome

    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "fatto"
    (richiesta,) = chiamate
    assert richiesta.immagini_in_piu == (dati,)
    assert richiesta.prompt.endswith(f"{blocchi.RIFERIMENTO_STILE.testo} {blocchi.COSA_EVITARE.testo}")


def test_il_riferimento_sparito_ferma_il_lavoro_prima_di_partire(cartella, chiamate):
    """Caso: il file del riferimento e' stato tolto e la vista partirebbe da sola."""
    studio = _studio(cartella, chiamate)
    nome = studio.carica_riferimento(_jpeg())["nome"]
    risposta = studio.invia(_richiesta(studio, riferimento=nome))
    (modulo_coda.cartella_riferimenti(cartella) / nome).unlink()
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert chiamate == []
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "errore"


def test_il_riferimento_non_parte_da_un_passo_ne_da_fuori_cartella(cartella, chiamate, tmp_path):
    fuori = tmp_path / "rif-0123456789abcdef.jpg"
    fuori.write_bytes(_jpeg())
    crea = lambda _n: ProviderConDueImmagini(chiamate)  # noqa: E731
    with pytest.raises(LavoroNonValido):
        metti_in_coda(cartella, cartella / "vista-1.png", blocchi.da_preset("rivista"),
                      provider="prova", modello=NANO, riferimento=fuori, crea_provider=crea)
    with pytest.raises(LavoroNonValido):
        metti_in_coda(cartella, cartella / "vista-1.png", blocchi.da_preset("rivista"),
                      provider="prova", modello=NANO, parte_da="x", partenza=cartella / "vista-1.png",
                      riferimento=fuori, crea_provider=crea)


def test_un_lavoro_del_formato_4_senza_riferimento_si_rifiuta():
    with pytest.raises(LavoroNonValido):
        modulo_coda.Lavoro.da_dizionario({
            "formato": modulo_coda.FORMATO_RIFERIMENTO, "identificativo": "x", "vista": "v.png",
            "provider": "prova", "modello": NANO, "destinazione": "d",
        })


# --- prompt e provider ---------------------------------------------------------


def test_la_frase_del_riferimento_e_quella_della_bozza():
    bozza = (Path(__file__).resolve().parent.parent / "docs" / "ui" / "blocchi-stile-bozza.md").read_text(encoding="utf-8")
    assert f"> {blocchi.RIFERIMENTO_STILE.testo}" in bozza
    assert blocchi.RIFERIMENTO_STILE.origine == config.SCELTA


def test_il_prompt_composto_nello_studio_mostra_la_frase_del_riferimento(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    scelte = blocchi.da_preset("rivista").a_dizionario()
    assert blocchi.RIFERIMENTO_STILE.testo not in studio.componi({"scelte": scelte})["prompt"]
    assert blocchi.RIFERIMENTO_STILE.testo in studio.componi({"scelte": scelte, "riferimento": "rif"})["prompt"]


def test_comfy_dice_chi_riceve_piu_immagini_e_che_nano_banana_non_e_mai_stato_provato_con_due():
    motore = comfy.ProviderComfy(chiave="finta")
    assert motore.accetta_piu_immagini("vertexai/gemini-3.1-flash-image")
    assert not motore.accetta_piu_immagini("bfl/flux-kontext-pro")
    assert not motore.accetta_piu_immagini("vertexai/gemini-3-pro-image")
    assert comfy.SCHEMI["vertexai/gemini-3.1-flash-image"].piu_immagini_verificato_il == ""
    assert "questo render e' la prova" in motore.avviso_piu_immagini("vertexai/gemini-3.1-flash-image")
    assert motore.avviso_piu_immagini("bfl/flux-kontext-pro") is None
