"""«Da un'immagine»: una foto, un render gia' fatto o uno schizzo come partenza (flussi 2, 8, 9, 10).

Nessuna rete: il provider e' un finto. Gli stati sono quelli di DESIGN.md,
Studio · Da un'immagine. Che le regole delle foto e dello schizzo tengano
davvero pareti, finestre e linee non lo dice nessun test: serve un render
vero e un occhio sugli spigoli.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from conftest import vista_shaded, vista_wireframe
from core import blocchi, coda as modulo_coda, partenza as modulo_partenza
from core.studio.server import avvia_in_sottofondo, crea_server
from core.studio.servizio import RichiestaStudioNonValida
from test_passi import NANO, _coda, _dest, _studio, cartella, chiamate  # noqa: F401  (fixture per nome)
from test_studio import _chiedi


def _foto(larghezza=900, altezza=600) -> bytes:
    """Una «foto»: colori veri, tanti toni, nessuno sfondo uniforme."""
    immagine = Image.open(io.BytesIO(vista_shaded(larghezza, altezza))).convert("RGB")
    pixel = immagine.load()
    for y in range(altezza):
        for x in range(larghezza):
            g = pixel[x, y][0]
            pixel[x, y] = (g, g // 2 + 60, 255 - g)
    uscita = io.BytesIO()
    immagine.save(uscita, format="JPEG")
    return uscita.getvalue()


# --- la regola fissa ------------------------------------------------------------


def test_la_vista_di_allplan_ha_la_regola_di_sempre_e_non_scrive_la_partenza():
    """Caso: un lavoro dalla vista cambia prompt, o un motore vecchio lo rifiuta per una voce nuova."""
    scelte = blocchi.da_preset("rivista")
    assert blocchi.componi(scelte).startswith(blocchi.REGOLA_FISSA.testo)
    assert "partenza" not in scelte.a_dizionario()
    assert blocchi.Scelte.da_dizionario(scelte.a_dizionario()) == scelte


@pytest.mark.parametrize("partenza", [blocchi.PARTENZA_FOTO, blocchi.PARTENZA_FOTO_ARREDI, blocchi.PARTENZA_SCHIZZO])
def test_da_un_immagine_la_regola_prende_il_posto_della_fedelta(partenza):
    scelte = blocchi.da_preset("interno-rivista", partenza=partenza, fedelta="rigida")
    prompt = blocchi.componi(scelte)
    assert prompt.startswith(blocchi.PARTENZE[partenza].testo)
    assert blocchi.FEDELTA["rigida"].testo not in prompt
    assert scelte.a_dizionario()["partenza"] == partenza


def test_tenere_gli_arredi_e_non_tenerli_dicono_cose_diverse():
    muri = blocchi.PARTENZE[blocchi.PARTENZA_FOTO].testo
    arredi = blocchi.PARTENZE[blocchi.PARTENZA_FOTO_ARREDI].testo
    assert "replace furniture" in muri and "every piece of furniture" in arredi


def test_da_una_foto_non_si_parte_con_un_pezzo_d_arredo():
    """Caso: la regola di una stanza parte su un prodotto, e il prodotto si deforma."""
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi(blocchi.da_preset("arredo-catalogo", partenza=blocchi.PARTENZA_FOTO))
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi(blocchi.Scelte(partenza="disegno"))


# --- caricare un'immagine ---------------------------------------------------------


def test_uno_schizzo_non_viene_rifiutato_come_wireframe(cartella, chiamate):
    """Caso: lo schizzo a matita e' per forza «troppo pochi toni»: la vista di Allplan lo rifiuterebbe."""
    studio = _studio(cartella, chiamate)
    r = studio.carica_vista(vista_wireframe(1200, 800), "schizzo.png", modulo_partenza.SCHIZZO)
    assert "lavoro" not in r  # lo schizzo passa da Genera
    d = studio.descrivi_vista(r["nome"])
    assert d["idonea"] and d["tipo"] == "schizzo" and d["tipo_nome"] == "Schizzo o plastico"
    assert [p["id"] for p in d["partenze"]] == [blocchi.PARTENZA_SCHIZZO]
    # Lo stesso file come vista di Allplan resta rifiutato.
    (cartella / "allplan.png").write_bytes(vista_wireframe(1200, 800))
    assert not studio.descrivi_vista("allplan.png")["idonea"]


def test_un_immagine_troppo_piccola_si_rifiuta_prima_di_salvarla(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    prima = sorted(p.name for p in cartella.iterdir())
    with pytest.raises(RichiestaStudioNonValida) as rifiuto:
        studio.carica_vista(_foto(300, 200), "piccola.jpg", modulo_partenza.FOTO)
    assert "troppo piccola" in rifiuto.value.fatto
    assert sorted(p.name for p in cartella.iterdir()) == prima


def test_un_tipo_sconosciuto_si_rifiuta(cartella, chiamate):
    with pytest.raises(modulo_partenza.TipoNonValido):
        _studio(cartella, chiamate).carica_vista(_foto(), "x.jpg", "disegno")


def test_in_una_foto_i_colori_sono_veri_e_non_c_e_l_avviso(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    r = studio.carica_vista(_foto(), "stanza.jpg", modulo_partenza.FOTO, scena=blocchi.INTERNO)
    assert studio.descrivi_vista(r["nome"])["colori_come_materiali"] is False


# --- un render gia' fatto diventa subito un risultato ------------------------------


def test_un_render_gia_fatto_e_subito_un_risultato_senza_invio(cartella, chiamate):
    """Caso: per lavorare su un render di un altro programma si paga un Genera che non serve."""
    studio = _studio(cartella, chiamate)
    r = studio.carica_vista(_foto(), "casa.jpg", modulo_partenza.RENDER)
    assert chiamate == []  # niente e' partito
    lavori = studio.render_della_vista(r["nome"])
    assert [l["identificativo"] for l in lavori] == [r["lavoro"]]
    caricata = lavori[0]
    assert caricata["importata"] and caricata["render"] and caricata["stato"] == modulo_coda.FATTO
    assert caricata["modello_nome"] == "Immagine caricata"
    assert caricata["destinazione"] == modulo_coda.DESTINAZIONE_NESSUNA
    # La tenuta non si misura: contro se stessa darebbe un numero falso (regola 3).
    assert caricata["tenuta"]["spigoli"] is None and not caricata["tenuta"]["da_misurare"]
    assert studio.file_render(r["lavoro"]).read_bytes() == (cartella / r["nome"]).read_bytes()
    passi = studio.passi(r["nome"])["passi"]
    uno = [p for p in passi if p["identificativo"] == r["lavoro"]][0]
    assert uno["si_parte"] and uno["nome"] == "Immagine caricata"
    voci = studio.storico()["gruppi"][0]["voci"]
    assert [v["etichetta"] for v in voci] == ["Immagine", "Caricata"]


def test_l_immagine_caricata_non_si_rifa_non_si_porta_e_non_si_misura(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    r = studio.carica_vista(_foto(), "casa.jpg", modulo_partenza.RENDER)
    for prova in (lambda: studio.rifai(r["lavoro"], {}),
                  lambda: studio.ricetta_da_portare(r["lavoro"]),
                  lambda: studio.misura_ora(r["lavoro"])):
        with pytest.raises(RichiestaStudioNonValida) as rifiuto:
            prova()
        assert "l'immagine che hai caricato" in rifiuto.value.fatto
    assert chiamate == []


def test_da_una_foto_si_cambia_e_si_ritocca_come_da_un_render(cartella, chiamate):
    """Flussi 9 e 10: la foto ha subito la barra, e un Cambia parte dalla foto con la scena giusta."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    r = studio.carica_vista(_foto(), "soggiorno.jpg", modulo_partenza.FOTO, scena=blocchi.INTERNO)
    risposta = studio.invia_passo({"vista": r["nome"], "da": r["lavoro"], "testo": "luce della sera",
                                   "modello": NANO, "destinazione_mostrata": _dest(studio)})
    coda.esegui_uno()
    assert len(chiamate) == 1
    assert chiamate[0].immagine == (cartella / r["nome"]).read_bytes()
    passi = {p["identificativo"]: p for p in studio.passi(r["nome"])["passi"]}
    assert passi[risposta["identificativo"]]["da"] == r["lavoro"]
    assert passi[risposta["identificativo"]]["scena"] == blocchi.INTERNO
    ritocco = studio.invia_ritocco({
        "vista": r["nome"], "da": r["lavoro"], "modello": NANO, "destinazione_mostrata": _dest(studio),
        "aree": [{"forma": "rettangolo", "punti": [[0.2, 0.3], [0.5, 0.7]], "nota": "un tavolo rotondo in rovere"}],
    })
    assert ritocco["identificativo"]


def test_lo_schizzo_parte_da_genera_con_la_sua_regola_e_senza_idoneita_di_allplan(cartella, chiamate):
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    r = studio.carica_vista(vista_wireframe(1200, 800), "schizzo.png", modulo_partenza.SCHIZZO)
    scelte = blocchi.da_preset("rivista").a_dizionario()  # la pagina non manda la partenza
    composto = studio.componi({"vista": r["nome"], "scelte": scelte, "preset": "rivista"})
    assert composto["prompt"].startswith(blocchi.PARTENZE[blocchi.PARTENZA_SCHIZZO].testo)
    assert composto["riassunto"].startswith("Regola fissa da schizzo o plastico")
    identificativo = studio.invia({"vista": r["nome"], "scelte": scelte, "preset": "rivista", "modello": NANO,
                                   "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    assert modulo_coda.leggi_stato(cartella, identificativo)["stato"] == modulo_coda.FATTO
    assert chiamate[0].prompt.startswith(blocchi.PARTENZE[blocchi.PARTENZA_SCHIZZO].testo)
    lavoro = json.loads((cartella / "lavori" / "fatto" / f"{identificativo}.json").read_text(encoding="utf-8"))
    assert lavoro["scelte"]["partenza"] == blocchi.PARTENZA_SCHIZZO


def test_da_una_foto_si_sceglie_cosa_tenere_ma_non_la_regola_di_un_altro_tipo(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    r = studio.carica_vista(_foto(), "stanza.jpg", modulo_partenza.FOTO, scena=blocchi.INTERNO)
    scelte = blocchi.da_preset("interno-rivista").a_dizionario()
    predefinita = studio.componi({"vista": r["nome"], "scelte": scelte})
    assert predefinita["prompt"].startswith(blocchi.PARTENZE[blocchi.PARTENZA_FOTO].testo)
    arredi = studio.componi({"vista": r["nome"], "scelte": {**scelte, "partenza": blocchi.PARTENZA_FOTO_ARREDI}})
    assert arredi["prompt"].startswith(blocchi.PARTENZE[blocchi.PARTENZA_FOTO_ARREDI].testo)
    with pytest.raises(modulo_partenza.TipoNonValido):
        studio.componi({"vista": r["nome"], "scelte": {**scelte, "partenza": blocchi.PARTENZA_SCHIZZO}})


def test_da_una_vista_di_allplan_la_regola_delle_foto_si_rifiuta(cartella, chiamate):
    """Caso: una pagina vecchia o sbagliata manda la regola delle foto per una vista di Allplan."""
    (cartella / "vista-1.png").write_bytes(vista_shaded(640, 400))
    studio = _studio(cartella, chiamate)
    scelte = blocchi.da_preset("rivista").a_dizionario()
    assert studio.componi({"vista": "vista-1.png", "scelte": scelte})["prompt"].startswith(blocchi.REGOLA_FISSA.testo)
    with pytest.raises(modulo_partenza.TipoNonValido):
        studio.componi({"vista": "vista-1.png", "scelte": {**scelte, "partenza": blocchi.PARTENZA_FOTO}})


def test_col_fotoinserimento_la_vista_resta_l_edificio(cartella, chiamate):
    """Caso: la foto come luogo e la vista come edificio; la regola delle foto non c'entra."""
    studio = _studio(cartella, chiamate)
    contesto = studio.carica_contesto(_foto(), "luogo.jpg")
    scelte = blocchi.da_preset("rivista").a_dizionario()
    composto = studio.componi({"vista": "vista-1.png", "scelte": scelte,
                               "contesto": {"nome": contesto["nome"], "area": [[0.2, 0.2], [0.6, 0.7]],
                                            "inquadratura": blocchi.TERRA}})
    assert composto["riassunto"].startswith("Fotoinserimento")


# --- il server -----------------------------------------------------------------------


def _json(server, metodo, percorso, corpo=None, intestazioni=None):
    stato, _tipo, contenuto = _chiedi(server, metodo, percorso, corpo, intestazioni)
    return stato, json.loads(contenuto)


def test_il_server_passa_tipo_e_scena_dall_intestazione(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    server = crea_server(studio)
    avvia_in_sottofondo(server)
    try:
        stato, risposta = _json(server, "POST", "/api/viste", _foto(), {
            "Content-Type": "application/octet-stream", "X-Nome-File": "stanza.jpg",
            "X-Tipo-Immagine": "foto", "X-Scena": "interno"})
        assert stato == 200 and risposta["tipo"] == "foto" and risposta["lavoro"]
        stato, descrizione = _json(server, "GET", f"/api/viste/{risposta['nome']}")
        assert descrizione["tipo"] == "foto" and descrizione["partenza_predefinita"] == blocchi.PARTENZA_FOTO
        # Senza intestazione: una vista come prima, senza file accanto.
        stato, vecchia = _json(server, "POST", "/api/viste", vista_shaded(640, 400), {
            "Content-Type": "application/octet-stream", "X-Nome-File": "vista.png"})
        assert stato == 200 and "tipo" not in vecchia
        assert not modulo_partenza.percorso(cartella / vecchia["nome"]).exists()
    finally:
        server.shutdown()
        server.server_close()
    assert studio.passi(risposta["nome"])["passi"][0]["scena"] == blocchi.INTERNO
