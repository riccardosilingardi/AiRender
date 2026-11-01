"""Inserisci nel contesto (fotoinserimento, 2026-11-01): prompt, Studio, coda, sonda.

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
from core import blocchi, config, contesto as modulo_contesto
from core.coda import Coda, Lavoro, LavoroNonValido, leggi_stato, metti_in_coda
from core.contesto import Contesto, ContestoNonValido
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

NANO = MODELLI[0].identificativo
KONTEXT = MODELLI[1].identificativo
AREA = [[0.3, 0.4], [0.6, 0.8]]


class ProviderConDueImmagini(ProviderDiProva):
    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _jpeg(larghezza=400, altezza=300, colore=(90, 130, 80)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), colore).save(uscita, "JPEG")
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


def _contesto(nome, **altro):
    return {"nome": nome, "area": AREA, "inquadratura": "zenitale", "pulisci_mappa": False, "luogo": "", **altro}


def _richiesta(studio, contesto, modello=NANO, **altro):
    destinazione = studio.destinazione(modello, contesto=contesto is not None)
    return {"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista", materiali="intonaco bianco").a_dizionario(),
            "preset": "rivista", "modello": modello,
            "destinazione_mostrata": destinazione["destinazione"], "contesto": contesto, **altro}


# --- prompt ----------------------------------------------------------------


def test_il_prompt_del_contesto_ha_regola_inquadratura_luogo_materiali_e_fuori_intatto():
    """Caso: la frase del luogo o dei materiali si perde, o l'ordine cambia."""
    testo = blocchi.componi_contesto("volo", luogo="Via Rontano, 44.52, 10.69", materiali="intonaco bianco")
    assert testo.startswith(blocchi.CONTESTO_REGOLA.testo)
    pezzi = [blocchi.INQUADRATURE["volo"].testo, "The site is at Via Rontano, 44.52, 10.69.",
             "Materials: intonaco bianco.", blocchi.CONTESTO_FUORI_INTATTO.testo, blocchi.COSA_EVITARE.testo]
    posizioni = [testo.index(p) for p in pezzi]
    assert posizioni == sorted(posizioni)


def test_pulisci_la_mappa_prende_il_posto_del_fuori_intatto():
    """Caso: il prompt chiede insieme di lasciare il contesto identico e di trasformarlo in foto."""
    testo = blocchi.componi_contesto("zenitale", pulisci_mappa=True)
    assert blocchi.CONTESTO_PULISCI_MAPPA.testo in testo
    assert blocchi.CONTESTO_FUORI_INTATTO.testo not in testo


def test_un_inquadratura_che_non_esiste_si_rifiuta():
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi_contesto("prospettiva")


def test_i_blocchi_del_contesto_non_si_presentano_come_provati():
    """Caso: un blocco mai mandato al modello appare a schermo come misurato."""
    tutti = [blocchi.CONTESTO_REGOLA, blocchi.CONTESTO_FUORI_INTATTO, blocchi.CONTESTO_PULISCI_MAPPA,
             *blocchi.INQUADRATURE.values()]
    assert {b.origine for b in tutti} == {config.SCELTA}


def test_da_terra_chiede_la_stessa_camera_della_foto():
    """Caso: una foto da Street View trattata come una vista dall'alto (prova di Riccardo, 2026-11-01)."""
    testo = blocchi.componi_contesto("terra")
    assert blocchi.INQUADRATURE["terra"].testo in testo
    assert "eye level" in testo and "vanishing points" in testo


def test_la_regola_non_tiene_il_grigio_della_vista():
    """Caso: «materials as designed» faceva uscire l'edificio grigio come la vista Allplan."""
    regola = blocchi.CONTESTO_REGOLA.testo
    assert "materials as designed" not in regola
    assert "not materials" in regola


def test_pulisci_la_mappa_con_una_foto_da_terra_si_rifiuta():
    """Caso: la pulizia della mappa trasformerebbe una foto da terra in una foto aerea."""
    with pytest.raises(ContestoNonValido):
        Contesto("x.png", AREA, inquadratura="terra", pulisci_mappa=True)
    assert Contesto("x.png", AREA, inquadratura="terra").inquadratura == "terra"


def test_la_regola_del_contesto_e_quella_della_bozza():
    bozza = (Path(__file__).resolve().parent.parent / "docs" / "ui" / "blocchi-stile-bozza.md").read_text(encoding="utf-8")
    assert f"> {blocchi.CONTESTO_REGOLA.testo}" in bozza


# --- il contesto ------------------------------------------------------------


def test_l_inquadratura_predefinita_e_zenitale():
    """Caso CONTESTO_INQUADRATURA_PREDEFINITA: senza scelta il contesto parte zenitale, ed e' un'inquadratura vera."""
    contesto = Contesto.da_dizionario({"file": "x.png", "area": AREA})
    assert contesto.inquadratura == config.CONTESTO_INQUADRATURA_PREDEFINITA == "zenitale"
    assert config.CONTESTO_INQUADRATURA_PREDEFINITA in blocchi.INQUADRATURE
    assert config.costante("CONTESTO_INQUADRATURA_PREDEFINITA").origine == config.SCELTA


def test_un_luogo_troppo_lungo_si_rifiuta_e_gli_spazi_si_puliscono():
    """Caso CONTESTO_LUOGO_MASSIMO: il campo luogo diventa un secondo prompt."""
    assert Contesto("x.png", AREA, luogo="  Via   Rontano  ").luogo == "Via Rontano"
    Contesto("x.png", AREA, luogo="a" * config.CONTESTO_LUOGO_MASSIMO)
    with pytest.raises(ContestoNonValido):
        Contesto("x.png", AREA, luogo="a" * (config.CONTESTO_LUOGO_MASSIMO + 1))


@pytest.mark.parametrize("area", [[[0.3, 0.4]], [[0.3, 0.4], [0.3, 0.8]], [[0.3, 0.4], [1.2, 0.8]], []])
def test_un_area_che_non_e_un_rettangolo_si_rifiuta(area):
    with pytest.raises(ContestoNonValido):
        Contesto.da_dizionario({"file": "x.png", "area": area})


def test_il_contesto_va_e_torna_dal_dizionario():
    contesto = Contesto("x.png", AREA, "volo", True, "Reggio Emilia")
    assert Contesto.da_dizionario(contesto.a_dizionario()) == contesto


def test_prepara_disegna_il_contorno_solo_sull_area():
    dati = _jpeg()
    preparata = Contesto("x.png", AREA).prepara(dati)
    prima = Image.open(io.BytesIO(dati)).convert("RGB")
    dopo = Image.open(io.BytesIO(preparata)).convert("RGB")
    assert dopo.size == prima.size
    assert dopo.getpixel((10, 10)) == prima.getpixel((10, 10))  # lontano dall'area non cambia
    assert dopo.getpixel((int(0.45 * 400), int(0.4 * 300))) != prima.getpixel((int(0.45 * 400), int(0.4 * 300)))


# --- Studio ------------------------------------------------------------------


def test_un_contesto_si_salva_con_la_sua_impronta_e_il_nome_non_e_mai_un_percorso(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    dati = _jpeg()
    caricato = studio.carica_contesto(dati, "earth.jpg")
    assert caricato["nome"].startswith("ctx-") and (caricato["larghezza"], caricato["altezza"]) == (400, 300)
    assert studio.percorso_contesto(caricato["nome"]).read_bytes() == dati
    for nome in ("../vista-1.png", "rif-0123456789abcdef.jpg", "ctx-zz.jpg"):
        with pytest.raises(RichiestaStudioNonValida):
            studio.percorso_contesto(nome)


def test_un_contesto_che_non_e_un_immagine_si_rifiuta(cartella, chiamate):
    with pytest.raises(RichiestaStudioNonValida):
        _studio(cartella, chiamate).carica_contesto(b"GIF89a niente", "mappa.gif")


def test_la_destinazione_dice_che_partono_due_immagini_contesto_per_primo(cartella, chiamate):
    destinazione = _studio(cartella, chiamate).destinazione(NANO, contesto=True)
    assert destinazione["immagini"] == 2
    assert destinazione["cosa_parte"].startswith("Partono due immagini: prima il contesto")
    assert destinazione["contesto_non_accettato"] is None


def test_con_kontext_il_contesto_non_parte(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    assert studio.destinazione(KONTEXT, contesto=True)["contesto_non_accettato"]
    secco = studio.prova_a_secco(_richiesta(studio, _contesto(nome), modello=KONTEXT))
    assert any("una sola immagine" in p["fatto"] for p in secco["problemi"])
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia(_richiesta(studio, _contesto(nome), modello=KONTEXT))


def test_il_prompt_composto_nello_studio_e_quello_del_contesto(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    composto = studio.componi({"scelte": blocchi.da_preset("rivista", materiali="intonaco bianco").a_dizionario(),
                               "contesto": _contesto(nome, luogo="Rontano")})
    assert composto["prompt"] == blocchi.componi_contesto("zenitale", luogo="Rontano", materiali="intonaco bianco")
    assert composto["riassunto"].startswith("Inserisci nel contesto")


def test_contesto_e_riferimento_insieme_si_rifiutano(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    rif = studio.carica_riferimento(_jpeg(colore=(1, 2, 3)))["nome"]
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia(_richiesta(studio, _contesto(nome), riferimento=rif))


def test_il_catalogo_dice_le_inquadrature_e_che_la_ricerca_web_e_spenta(cartella, chiamate):
    voce = _studio(cartella, chiamate).catalogo()["contesto"]
    assert [i["id"] for i in voce["inquadrature"]] == ["zenitale", "volo", "terra"]
    assert voce["ricerca_web_verificata"] is False


# --- coda ------------------------------------------------------------------------


def test_genera_con_contesto_manda_prima_il_contesto_poi_la_vista(cartella, chiamate):
    """Caso: le due immagini partono nell'ordine sbagliato e il render prende il rapporto della vista."""
    studio = _studio(cartella, chiamate)
    dati = _jpeg()
    nome = studio.carica_contesto(dati)["nome"]
    risposta = studio.invia(_richiesta(studio, _contesto(nome, luogo="Rontano")))
    lavoro = json.loads((cartella / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json").read_text("utf-8"))
    assert lavoro["formato"] == 5 and lavoro["contesto"]["luogo"] == "Rontano"
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    (richiesta,) = chiamate
    assert Image.open(io.BytesIO(richiesta.immagine)).size == (400, 300)  # il contesto, con l'area
    assert richiesta.immagini_in_piu == ((cartella / "vista-1.png").read_bytes(),)
    assert richiesta.prompt == blocchi.componi_contesto("zenitale", luogo="Rontano", materiali="intonaco bianco")
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "fatto"


def test_con_contesto_si_misura_fuori_dall_area_e_non_la_tenuta_degli_spigoli(cartella, chiamate):
    """Caso: la tenuta contro la vista stampata per un render che e' il contesto (regola 3)."""
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    risposta = studio.invia(_richiesta(studio, _contesto(nome)))
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate, eco=True), dire=lambda _t: None).esegui_uno()
    stato = leggi_stato(cartella, risposta["identificativo"])
    assert stato["stato"] == "fatto"
    assert stato["fuori_aree"] is not None and "differenza_media" in stato["fuori_aree"]
    assert not Path(stato["render"] + ".misura.json").exists()


def test_con_pulisci_la_mappa_la_misura_fuori_dall_area_non_si_fa(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    risposta = studio.invia(_richiesta(studio, _contesto(nome, pulisci_mappa=True)))
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate, eco=True), dire=lambda _t: None).esegui_uno()
    assert leggi_stato(cartella, risposta["identificativo"])["fuori_aree"] is None


def test_il_contesto_sparito_ferma_il_lavoro_prima_di_partire(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    risposta = studio.invia(_richiesta(studio, _contesto(nome)))
    (modulo_contesto.cartella_contesti(cartella) / nome).unlink()
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert chiamate == []
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "errore"


def test_il_contesto_fuori_dalla_cartella_o_con_un_passo_si_rifiuta(cartella, chiamate, tmp_path):
    fuori = tmp_path / "fuori.jpg"
    fuori.write_bytes(_jpeg())
    with pytest.raises(ContestoNonValido):
        metti_in_coda(cartella, cartella / "vista-1.png", blocchi.da_preset("rivista"),
                      modello=NANO, contesto=Contesto(str(fuori), AREA),
                      crea_provider=lambda _n: ProviderConDueImmagini(chiamate))
    with pytest.raises(LavoroNonValido):
        metti_in_coda(cartella, cartella / "vista-1.png", blocchi.da_preset("rivista"),
                      modello=NANO, parte_da="x", partenza=cartella / "vista-1.png",
                      contesto=Contesto(str(fuori), AREA),
                      crea_provider=lambda _n: ProviderConDueImmagini(chiamate))


def test_un_lavoro_del_formato_5_senza_contesto_si_rifiuta():
    dati = {"formato": 5, "identificativo": "x", "vista": "v.png", "provider": "p", "modello": NANO,
            "destinazione": "d", "scelte": {}}
    with pytest.raises(LavoroNonValido):
        Lavoro.da_dizionario(dati)


def test_rifai_un_lavoro_col_contesto_lo_rimanda_col_suo_contesto(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    primo = studio.invia(_richiesta(studio, _contesto(nome, inquadratura="volo")))
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    destinazione = studio.destinazione(NANO, contesto=True)
    secondo = studio.rifai(primo["identificativo"], {"destinazione_mostrata": destinazione["destinazione"]})
    lavoro = json.loads((cartella / "lavori" / "in-attesa" / f"{secondo['identificativo']}.json").read_text("utf-8"))
    assert lavoro["contesto"]["inquadratura"] == "volo"


# --- sonda -------------------------------------------------------------------------


def test_la_sonda_accende_la_ricerca_web_solo_per_gemini():
    import importlib.util
    percorso = Path(__file__).resolve().parent.parent / "scripts" / "sonda_comfy.py"
    specifica = importlib.util.spec_from_file_location("sonda_comfy_contesto", percorso)
    sonda = importlib.util.module_from_spec(specifica)
    specifica.loader.exec_module(sonda)
    corpo = sonda.con_ricerca_web("vertexai/gemini-3.1-flash-image", {"contents": []})
    assert corpo["tools"] == [{"googleSearch": {}}]
    with pytest.raises(SystemExit):
        sonda.con_ricerca_web("bfl/flux-kontext-pro", {})
