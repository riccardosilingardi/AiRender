"""Il banco di prova dei blocchi, provato senza rete e senza chiave.

Il provider e' finto: rende l'immagine che riceve (o una sua modifica), cosi'
le misure si provano su immagini di cui si sa la risposta.
"""

from __future__ import annotations

import http.client
import io
import json
import sys
import threading
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from conftest import vista_shaded
from core import banco, blocchi, config, immagine
from core.errori import ErroreProvider
from core.provider.base import Risultato
from core.ricetta import Ricetta, impronta
from core.studio.servizio import MODELLI, Studio
from test_coda import ProviderDiProva

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import miniatura_da_banco  # noqa: E402  pylint: disable=wrong-import-position
import prova_blocchi  # noqa: E402  pylint: disable=wrong-import-position

NANO = MODELLI[0].identificativo
KONTEXT = MODELLI[1].identificativo

AREE = (
    banco.Area("rettangolo", ((0.1, 0.1), (0.4, 0.5)), "infissi in legno scuro"),
    banco.Area("libera", ((0.6, 0.6), (0.9, 0.62), (0.85, 0.9), (0.62, 0.85)), "una panchina"),
)


def _png(img: Image.Image) -> bytes:
    deposito = io.BytesIO()
    img.save(deposito, format="PNG")
    return deposito.getvalue()


class ProviderBanco(ProviderDiProva):
    """Rende l'immagine ricevuta, passata da `trasforma`. Fallisce per i prompt in `fallisce`."""

    def __init__(self, registro, trasforma=lambda dati: dati, fallisce=()):
        super().__init__(registro)
        self.trasforma = trasforma
        self.fallisce = fallisce

    def genera(self, richiesta):
        self.registro.append(richiesta)
        if any(pezzo in richiesta.prompt for pezzo in self.fallisce):
            raise ErroreProvider("Il servizio di prova ha detto di no.", "Riprova.")
        return Risultato(
            immagine=self.trasforma(richiesta.immagine), formato="png",
            ricetta=Ricetta(
                provider=self.nome, modello=richiesta.modello, preset=richiesta.preset,
                preset_versione=richiesta.preset_versione, prompt=richiesta.prompt,
                testo_utente="", grana=richiesta.grana, dettaglio_grana=None, forza_struttura=None,
                risoluzione="", aspetto="", generazione_fissa=False,
                impronta_sorgente=impronta(richiesta.immagine), parametri={"crediti_usati": "17.17"},
            ),
        )


@pytest.fixture
def vista(tmp_path) -> Path:
    percorso = tmp_path / "vista.png"
    percorso.write_bytes(vista_shaded(640, 360))
    return percorso


def lancia(vista, *altri, motore=None, risposta="si"):
    righe, domande = [], []
    argomenti = prova_blocchi.costruisci_parser().parse_args(
        ["--immagine", str(vista), "--uscita", str(vista.parent / "banchi"), *altri])

    def chiedi(testo):
        domande.append(testo)
        return risposta

    codice = prova_blocchi.esegui(argomenti, dire=righe.append, chiedi=chiedi,
                                  crea_motore=lambda: motore or ProviderBanco([]))
    return codice, "\n".join(righe), domande


def cartella_unica(vista) -> Path:
    (cartella,) = (vista.parent / "banchi").iterdir()
    return cartella


# --- i piani: quanti invii, quanto costano ------------------------------------


@pytest.mark.parametrize("nome,scena,quanti", [
    ("qualita", "esterno", 2), ("look", "esterno", 9), ("preset", "esterno", 8),
    ("preset", "interno", 6), ("catena", "esterno", 4), ("catena", "interno", 4), ("aree", "esterno", 2),
])
def test_ogni_piano_ha_i_suoi_invii_e_li_dice_prima_col_costo(vista, nome, scena, quanti):
    """Caso: il banco parte con piu' invii di quelli annunciati, o senza dire il costo (regola 5)."""
    registro = []
    codice, uscita, domande = lancia(vista, "--piano", nome, "--scena", scena, "--prova-a-secco",
                                     motore=ProviderBanco(registro))
    assert codice == 0 and registro == [] and domande == []
    assert f"Invii: {quanti}, uno dopo l'altro." in uscita
    totale = round(quanti * config.COSTO_NANO_BANANA_2_CREDITI)
    assert f"circa {totale} crediti per {quanti} immagini" in uscita
    assert f"Servizio di prova (niente rete) → {NANO}" in uscita
    assert "Prova a secco: non ho inviato niente." in uscita
    dati = banco.leggi_banco(cartella_unica(vista))
    assert len(dati["invii"]) == quanti
    assert {v["stato"] for v in dati["invii"]} == {banco.NON_INVIATO}


def test_con_un_modello_dal_costo_non_misurato_il_banco_non_inventa_un_numero(vista):
    _codice, uscita, _ = lancia(vista, "--piano", "qualita", "--modello", KONTEXT, "--prova-a-secco")
    assert "Costo stimato: non misurato" in uscita
    assert "crediti per" not in uscita


def test_ogni_piano_cambia_una_cosa_sola():
    """Caso: un confronto cambia due assi insieme e non si sa a quale dare la colpa."""
    qualita = banco.piano("qualita")
    assert qualita.invii[0].prompt.replace(blocchi.QUALITA["base"].testo, blocchi.QUALITA["32k"].testo) \
        == qualita.invii[1].prompt
    look = banco.piano("look")
    riferimento = look.invii[0]
    for invio in look.invii[1:]:
        diversi = {k for k in riferimento.scelte if riferimento.scelte[k] != invio.scelte[k]}
        assert diversi == {"look"}
    assert [i.preset for i in banco.piano("preset", "interno").invii] == [
        p for p, v in blocchi.PRESET_STILE.items() if v.scelte.scena == "interno"]


def test_il_piano_fedelta_cambia_solo_la_regola_in_testa():
    """Caso: le tre fedelta' partono con preset diversi e la differenza non si attribuisce."""
    fedelta = banco.piano("fedelta")
    assert [i.scelte["fedelta"] for i in fedelta.invii] == list(blocchi.FEDELTA)
    riferimento = fedelta.invii[0]
    for invio in fedelta.invii[1:]:
        diversi = {k for k in riferimento.scelte if riferimento.scelte[k] != invio.scelte[k]}
        assert diversi == {"fedelta"}
    assert fedelta.misura == banco.SPIGOLI
    assert {c.a for c in fedelta.confronti} >= {banco.VISTA}


def test_un_piano_che_non_esiste_dice_quali_esistono():
    with pytest.raises(banco.PianoNonValido) as errore:
        banco.piano("tutto")
    assert "qualita" in errore.value.cosa_fare


def test_senza_conferma_non_parte_niente(vista):
    registro = []
    codice, uscita, domande = lancia(vista, "--piano", "qualita", motore=ProviderBanco(registro), risposta="no")
    assert codice == 0 and registro == []
    assert domande == ["Mando 2 invii? Scrivi si per partire: "]
    assert "Non ho inviato niente." in uscita
    assert not (vista.parent / "banchi").exists()


def test_con_la_conferma_parte_e_misura(vista):
    registro = []
    codice, _uscita, _ = lancia(vista, "--piano", "qualita", motore=ProviderBanco(registro))
    assert codice == 0 and len(registro) == 2
    dati = banco.leggi_banco(cartella_unica(vista))
    assert [v["stato"] for v in dati["invii"]] == [banco.FATTO, banco.FATTO]
    # il provider finto rende la vista com'e': tutti gli spigoli si ritrovano
    assert all(v["misure"][banco.SPIGOLI] == 1.0 for v in dati["invii"])
    assert dati["invii"][0]["crediti"] == "17.17"
    assert (cartella_unica(vista) / "base.png.ricetta.json").exists()


# --- catena ----------------------------------------------------------------------


def _segna(dati: bytes) -> bytes:
    """Il render finto: l'immagine ricevuta con un punto in alto a sinistra, per riconoscerla."""
    img = Image.open(io.BytesIO(dati)).convert("RGB")
    img.putpixel((0, 0), (255, 0, 0))
    return _png(img)


def test_la_catena_parte_dal_render_prima_e_rifai_pulito_dalla_vista(vista):
    """Caso: il passo 2 riparte dalla vista e la catena non misura tre generazioni."""
    registro = []
    lancia(vista, "--piano", "catena", motore=ProviderBanco(registro, trasforma=_segna))
    passo1, passo2, passo3, pulito = registro
    originale = vista.read_bytes()
    assert passo1.immagine == originale and pulito.immagine == originale
    assert passo2.immagine == _segna(originale)
    assert passo3.immagine == _segna(_segna(originale))
    assert blocchi.VERDE["poco"].testo in passo2.prompt and "Canon" not in passo2.prompt
    assert blocchi.PERSONE["poche"].testo in passo3.prompt and "trees" not in passo3.prompt
    for pezzo in ("Canon", blocchi.VERDE["poco"].testo, blocchi.PERSONE["poche"].testo):
        assert pezzo in pulito.prompt


def test_un_passo_fallito_salta_quelli_che_partono_da_lui_ma_non_gli_altri(vista):
    registro = []
    codice, uscita, _ = lancia(vista, "--piano", "catena",
                               motore=ProviderBanco(registro, fallisce=("Mezzogiorno", "Midday sun")))
    dati = banco.leggi_banco(cartella_unica(vista))
    assert [v["stato"] for v in dati["invii"]] == [banco.ERRORE, banco.SALTATO, banco.SALTATO, banco.ERRORE]
    assert codice == prova_blocchi.USCITA_PROVIDER and "saltato" in uscita


# --- aree ------------------------------------------------------------------------


def test_le_aree_partono_disegnate_in_un_invio_e_come_maschera_nell_altro(vista):
    registro = []
    lancia(vista, "--piano", "aree", motore=ProviderBanco(registro))
    contorni, maschera = registro
    originale = vista.read_bytes()
    assert contorni.immagine != originale and contorni.immagini_in_piu == ()
    assert maschera.immagine == originale and len(maschera.immagini_in_piu) == 1
    for richiesta in registro:
        assert "Area 1: infissi in legno scuro." in richiesta.prompt
        assert "Area 2: una panchina in pietra chiara." in richiesta.prompt
    assert "magenta outlines" in contorni.prompt and "second image is a mask" in maschera.prompt


def test_l_immagine_coi_contorni_ha_il_contorno_e_il_numero_dove_sta_l_area():
    vista = vista_shaded(400, 300)
    poligoni = [a.in_pixel(400, 300) for a in AREE]
    disegnata = Image.open(io.BytesIO(immagine.disegna_aree(vista, poligoni))).convert("RGB")
    assert disegnata.size == (400, 300)
    # sul lato sinistro del rettangolo (x = 40), a meta' altezza: magenta
    assert disegnata.getpixel((40, 90)) == (255, 0, 255)
    # dentro l'area, lontano dal contorno: la vista com'era
    assert disegnata.getpixel((100, 100)) == Image.open(io.BytesIO(vista)).convert("RGB").getpixel((100, 100))
    # il numero 1 e' scritto nel cerchio sull'angolo, in bianco
    angolo = disegnata.crop((40 - 18, 30 - 18, 40 + 18, 30 + 18))
    assert (255, 255, 255) in [c for _n, c in angolo.getcolors(4096)]


def test_la_maschera_e_bianca_dentro_e_nera_fuori():
    maschera = Image.open(io.BytesIO(immagine.maschera_aree((400, 300), [a.in_pixel(400, 300) for a in AREE])))
    maschera = maschera.convert("RGB")
    assert maschera.getpixel((60, 50)) == (255, 255, 255)   # dentro il rettangolo, lontano dal numero
    assert maschera.getpixel((300, 240)) == (255, 255, 255)  # dentro la selezione libera
    assert maschera.getpixel((200, 20)) == (0, 0, 0)          # fuori


def _con_macchia(dati: bytes, scatola) -> bytes:
    img = Image.open(io.BytesIO(dati)).convert("RGB")
    ImageDraw.Draw(img).rectangle(scatola, fill=(255, 0, 0))
    return _png(img)


def test_la_differenza_fuori_dalle_aree_vede_solo_quello_che_esce():
    """Caso: il modello cambia anche fuori dalle aree e il banco dice che le ha rispettate."""
    vista = vista_shaded(400, 300)
    poligoni = [a.in_pixel(400, 300) for a in AREE]
    dentro = immagine.differenza_fuori_dalle_aree(vista, _con_macchia(vista, (60, 50, 140, 130)), poligoni)
    assert dentro["quota_cambiata"] == 0 and dentro["differenza_media"] == 0
    assert dentro["ridimensionata"] is False
    fuori = immagine.differenza_fuori_dalle_aree(vista, _con_macchia(vista, (200, 0, 260, 60)), poligoni)
    assert fuori["quota_cambiata"] > 0.02 and fuori["differenza_media"] > 1


def test_un_risultato_di_un_altra_dimensione_si_misura_e_lo_si_dice():
    vista = vista_shaded(400, 300)
    piu_piccolo = _png(Image.open(io.BytesIO(vista)).resize((344, 258)))
    misura = immagine.differenza_fuori_dalle_aree(vista, piu_piccolo, [a.in_pixel(400, 300) for a in AREE])
    assert misura["ridimensionata"] is True
    voce = {"misure": {banco.FUORI_AREE: {**misura, "dimensioni_render": [344, 258]}}}
    assert "344x258" in banco.testo_misura(voce, banco.FUORI_AREE)


def test_le_aree_si_leggono_da_un_file_e_quelle_sbagliate_si_rifiutano(tmp_path):
    file = tmp_path / "aree.json"
    file.write_text(json.dumps([a.a_dizionario() for a in AREE]), encoding="utf-8")
    assert prova_blocchi.leggi_aree(str(file)) == AREE
    for sbagliata in ([{"forma": "cerchio", "punti": [[0, 0], [1, 1]], "nota": "x"}],
                      [{"forma": "libera", "punti": [[0, 0], [1, 1]], "nota": "x"}],
                      [{"forma": "rettangolo", "punti": [[0, 0], [2, 1]], "nota": "x"}],
                      [{"forma": "rettangolo", "punti": [[0, 0], [1, 1]], "nota": "  "}]):
        file.write_text(json.dumps(sbagliata), encoding="utf-8")
        with pytest.raises(banco.PianoNonValido):
            prova_blocchi.leggi_aree(str(file))
    with pytest.raises(banco.PianoNonValido):
        banco.piano("aree", aree=AREE[:1])


# --- spigoli ---------------------------------------------------------------------


VISTA_VERA = Path(__file__).resolve().parent / "dati" / "vista-20261021-093841.png"


def test_la_misura_grezza_degli_spigoli_regge_il_ricampionamento_e_vede_uno_spostamento():
    """Caso: la misura non distingue un edificio spostato di pochi pixel da uno rimasto fermo."""
    vista = VISTA_VERA.read_bytes()
    originale = Image.open(io.BytesIO(vista)).convert("RGB")
    assert immagine.spigoli_ritrovati(vista, vista) == 1.0
    # il render di Nano Banana 2 ha un'altra dimensione: non deve contare come spostamento
    assert immagine.spigoli_ritrovati(vista, _png(originale.resize((1376, 768)))) > 0.99
    spostata = Image.new("RGB", originale.size, "white")
    spostata.paste(originale, (4, 4))
    assert immagine.spigoli_ritrovati(vista, _png(spostata)) < 0.9
    assert immagine.spigoli_ritrovati(_png(Image.new("RGB", (100, 80), "grey")), vista) is None


def test_una_misura_che_non_c_e_si_scrive_non_misurato():
    """Caso: un trattino batte un numero sbagliato (regola 3)."""
    assert banco.testo_misura({"misure": {}}, banco.SPIGOLI) == "Spigoli della vista ritrovati: non misurato."
    assert banco.testo_misura({"misure": {}}, banco.FUORI_AREE) == "Fuori dalle aree: non misurato."
    assert "87,5%" in banco.testo_misura({"misure": {banco.SPIGOLI: 0.875}}, banco.SPIGOLI)
    assert "non validata" in banco.testo_misura({"misure": {banco.SPIGOLI: 0.875}}, banco.SPIGOLI)


# --- la pagina e i giudizi -------------------------------------------------------------


def test_la_pagina_affianca_le_coppie_con_prompt_misure_e_giudizio(vista):
    lancia(vista, "--piano", "catena")
    cartella = cartella_unica(vista)
    pagina = (cartella / banco.FILE_PAGINA).read_text(encoding="utf-8")
    dati = banco.leggi_banco(cartella)
    assert pagina.count("class='coppia'") == len(dati["confronti"]) == 4
    assert "<img src='passo-3.png'" in pagina and "<img src='vista.png'" in pagina
    assert "A few trees and some low planting" in pagina
    assert "Spigoli della vista ritrovati: 100,0%" in pagina
    for giudizio in banco.GIUDIZI:
        assert f"value='{giudizio}'" in pagina
    assert "https://" not in pagina  # niente CDN: si apre anche senza rete


def test_la_pagina_a_secco_lo_dice_e_non_mostra_render(vista):
    lancia(vista, "--piano", "aree", "--prova-a-secco")
    cartella = cartella_unica(vista)
    pagina = (cartella / banco.FILE_PAGINA).read_text(encoding="utf-8")
    assert "Prova a secco: non ho inviato niente." in pagina
    assert "prova a secco: niente inviato" in pagina
    assert "preparata-contorni.png" in pagina and "preparata-maschera.png" in pagina
    assert (cartella / "preparata-contorni.png").exists()


def test_i_giudizi_si_salvano_solo_se_parlano_di_questo_banco(vista):
    lancia(vista, "--piano", "qualita")
    cartella = cartella_unica(vista)
    percorso = banco.salva_giudizi(cartella, {"giudizi": [
        {"a": "base", "b": "32k", "giudizio": "meglio B", "note": "più nitido"}]})
    assert json.loads(percorso.read_text(encoding="utf-8"))["giudizi"][0]["giudizio"] == "meglio B"
    for sbagliati in ({"giudizi": [{"a": "base", "b": "altro", "giudizio": "meglio B"}]},
                      {"giudizi": [{"a": "base", "b": "32k", "giudizio": "bellissimo"}]},
                      {"niente": 1}):
        with pytest.raises(banco.PianoNonValido):
            banco.salva_giudizi(cartella, sbagliati)


def test_il_server_dei_giudizi_serve_la_pagina_e_salva_solo_con_l_intestazione(vista):
    lancia(vista, "--piano", "qualita")
    cartella = cartella_unica(vista)
    server = banco.server_giudizi(cartella)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        assert server.server_address[0] == "127.0.0.1"
        porta = server.server_address[1]

        def chiedi(metodo, percorso, corpo=None, intestazioni=None):
            connessione = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
            connessione.request(metodo, percorso, body=corpo, headers=intestazioni or {})
            risposta = connessione.getresponse()
            return risposta.status, risposta.read()

        stato, pagina = chiedi("GET", "/")
        assert stato == 200 and b"Banco di prova" in pagina
        assert chiedi("GET", "/../vista.png")[0] == 404
        corpo = json.dumps({"giudizi": [{"a": "base", "b": "32k", "giudizio": "uguali", "note": ""}]})
        assert chiedi("POST", "/giudizi", corpo)[0] == 403
        assert chiedi("POST", "/giudizi", corpo, {banco.INTESTAZIONE_BANCO: "1"})[0] == 200
        assert (cartella / banco.FILE_GIUDIZI).exists()
    finally:
        server.shutdown()
        server.server_close()


# --- miniature vere -----------------------------------------------------------------


def test_un_render_del_piano_preset_diventa_la_miniatura_vera_del_suo_preset(vista, tmp_path):
    lancia(vista, "--piano", "preset")
    cartella = cartella_unica(vista)
    miniature = tmp_path / "miniature"
    righe = []
    argomenti = miniatura_da_banco.costruisci_parser().parse_args(["--render", str(cartella / "ora-blu.png")])
    assert miniatura_da_banco.esegui(argomenti, dire=righe.append, cartella_miniature=miniature) == 0
    assert Image.open(miniature / "ora-blu.jpg").size == (config.MINIATURA_LARGHEZZA_PX,
                                                          config.MINIATURA_ALTEZZA_PX)
    assert "repository" in "\n".join(righe)

    studio = Studio(tmp_path / "viste", cartella_miniature=miniature)
    preset = {p["id"]: p for p in studio.catalogo()["scene"]["esterno"]["preset"]}
    assert preset["ora-blu"]["miniatura"]["url"] == "/file/miniatura/ora-blu"
    assert preset["ora-blu"]["miniatura"]["data"].count("/") == 2
    assert preset["rivista"]["miniatura"] is None
    assert studio.file_miniatura("ora-blu") == miniature / "ora-blu.jpg"
    with pytest.raises(Exception):
        studio.file_miniatura("rivista")
    with pytest.raises(Exception):
        studio.file_miniatura("../indice.json")


def test_una_miniatura_non_viene_da_un_piano_che_cambia_il_preset(vista, tmp_path):
    """Caso: la miniatura di «Rivista» e' in realta' Rivista col look Ektar."""
    lancia(vista, "--piano", "look")
    cartella = cartella_unica(vista)
    argomenti = miniatura_da_banco.costruisci_parser().parse_args(["--render", str(cartella / "look-ektar.png")])
    with pytest.raises(banco.PianoNonValido) as errore:
        miniatura_da_banco.esegui(argomenti, dire=lambda _t: None, cartella_miniature=tmp_path / "m")
    assert "piano preset" in errore.value.cosa_fare
    assert not (tmp_path / "m").exists()


def test_nel_repository_non_ci_sono_miniature_finte():
    """Caso: lo stato vuoto riempito con dati finti. Le miniature vere arrivano solo dal banco."""
    from core.studio import miniature

    assert miniature.leggi() == {} or all(
        (miniature.CARTELLA / v["file"]).is_file() and v.get("render") for v in miniature.leggi().values())
