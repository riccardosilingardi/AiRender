"""Lo Studio: la logica (servizio.py) e le rotte del server locale.

Nessuna rete verso fuori: il provider e' quello finto di test_coda.py, e il
server si interroga con http.client su 127.0.0.1 (urllib e' vietato dalla
fixture di conftest). Gli stati sono quelli di DESIGN.md: vuoto, in corso,
errore, pieno.
"""

from __future__ import annotations

import http.client
import io
import json
import re
from pathlib import Path

import pytest
from PIL import Image

from conftest import vista_shaded, vista_wireframe
from core import blocchi, config
from core.coda import Coda, leggi_stato
from core.errori import ErroreAirender, ErroreProvider, FileNonTrovato
from core.provider import comfy
from core.studio import servizio as modulo_servizio
from core.studio.server import CARTELLA_PAGINE, avvia_in_sottofondo, crea_server
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

NANO = MODELLI[0].identificativo
KONTEXT = MODELLI[1].identificativo


class ProviderSenzaKontext(ProviderDiProva):
    """Come il finto, ma Kontext non ha uno schema verificato."""

    def cosa_manca(self, modello):
        return "schema non verificato" if modello == KONTEXT else None


def _vista_colorata(larghezza=640, altezza=400) -> bytes:
    """Una vista shaded con le superfici colorate per layer: viola e verde pieni."""
    immagine = Image.open(io.BytesIO(vista_shaded(larghezza, altezza))).convert("RGB")
    pixel = immagine.load()
    for y in range(altezza):
        for x in range(larghezza):
            g = pixel[x, y][0]
            pixel[x, y] = (g // 2 + 80, 30, g // 2 + 100) if x < larghezza // 2 else (40, g // 2 + 90, 50)
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


@pytest.fixture
def chiamate():
    return []


@pytest.fixture
def cartella(tmp_path) -> Path:
    percorso = tmp_path / "viste"
    percorso.mkdir()
    return percorso


@pytest.fixture
def vista(cartella) -> str:
    (cartella / "vista-1.png").write_bytes(vista_shaded(640, 400))
    return "vista-1.png"


def _studio(cartella, chiamate, coda_attiva=True, classe=ProviderDiProva, **opzioni):
    aperte = []
    studio = Studio(
        cartella, provider="prova",
        crea_provider=lambda _nome: classe(chiamate, **opzioni),
        coda_attiva=lambda: coda_attiva,
        apri=aperte.append,
    )
    studio.aperte = aperte
    return studio


def _coda(cartella, chiamate, **opzioni):
    return Coda(cartella, crea_provider=lambda _nome: ProviderDiProva(chiamate, **opzioni), dire=lambda _t: None)


def _richiesta(studio, vista, preset="rivista", **altro):
    scelte = blocchi.da_preset(preset, materiali="intonaco a calce bianco").a_dizionario()
    destinazione = studio.destinazione(altro.pop("modello", NANO))
    return {
        "vista": vista, "scelte": scelte, "preset": preset, "modello": destinazione["modello"],
        "destinazione_mostrata": destinazione["destinazione"], **altro,
    }


# --- catalogo e prompt -------------------------------------------------------


def test_il_catalogo_ha_gli_8_preset_esterni_e_i_6_interni_della_bozza(cartella, chiamate):
    """Caso: lo Studio mostra preset che il motore non sa comporre."""
    catalogo = _studio(cartella, chiamate).catalogo()
    esterni = catalogo["scene"]["esterno"]["preset"]
    interni = catalogo["scene"]["interno"]["preset"]
    assert len(esterni) == 8 and len(interni) == 6
    for preset in esterni + interni:
        assert blocchi.componi(blocchi.Scelte.da_dizionario(preset["scelte"]))
    assert catalogo["origine_blocchi"] == config.SCELTA


def test_le_voci_senza_blocco_sono_in_grigio_e_dicono_perche(cartella, chiamate):
    """Caso: un comando che si clicca e non cambia il prompt (regola delle funzioni future)."""
    catalogo = _studio(cartella, chiamate).catalogo()
    spente = [r for r in catalogo["rese"] if not r["attivo"]]
    assert [r["nome"] for r in catalogo["rese"] if r["attivo"]] == ["Fotorealistico"]
    assert spente and all(r["nota"] for r in spente)
    # gli assi dell'altra scena non compaiono
    assert "cielo" not in {a["id"] for a in catalogo["scene"]["interno"]["assi"]}
    assert "fuori" not in {a["id"] for a in catalogo["scene"]["esterno"]["assi"]}


def test_intorno_verde_e_persone_poche_sono_attivi_con_i_blocchi_della_bozza_4(cartella, chiamate):
    """Caso: lo Studio lascia in grigio una voce che il motore sa gia' comporre, o viceversa."""
    assi = {a["id"]: a for a in _studio(cartella, chiamate).catalogo()["scene"]["esterno"]["assi"]}
    for asse, attese in (("intorno", ["Niente, sfondo neutro", "Città", "Periferia", "Campagna"]),
                         ("verde", ["Nessuno", "Poco", "Rigoglioso"]),
                         ("persone", ["Nessuna", "Poche", "In movimento"])):
        assert [v["nome"] for v in assi[asse]["voci"]] == attese
        assert all(v["attivo"] and v["origine"] == config.SCELTA for v in assi[asse]["voci"])
    ordine = list(assi)
    assert ordine.index("intorno") + 1 == ordine.index("verde")


def test_il_riassunto_dice_intorno_verde_e_persone(cartella, chiamate):
    scelte = blocchi.da_preset("rivista", intorno="campagna", verde="poco", persone="poche")
    riassunto = _studio(cartella, chiamate).componi({"scelte": scelte.a_dizionario()})["riassunto"]
    assert "intorno: campagna · verde: poco · persone: poche" in riassunto


def test_componi_restituisce_il_prompt_dei_blocchi_e_il_riassunto_in_italiano(cartella, chiamate):
    """Caso: lo Studio mostra un prompt diverso da quello che la coda mandera'."""
    scelte = blocchi.da_preset("ora-blu", materiali="intonaco bianco")
    composto = _studio(cartella, chiamate).componi({"scelte": scelte.a_dizionario(), "preset": "ora-blu"})
    assert composto["prompt"] == blocchi.componi(scelte)
    assert composto["caratteri"] == len(composto["prompt"])
    assert composto["riassunto"].startswith("Regola fissa · esterno · i tuoi materiali · preset Ora blu")
    assert "ora blu" in composto["riassunto"] and composto["riassunto"].endswith("cosa evitare.")


def test_una_scelta_che_non_esiste_si_rifiuta_con_la_ragione(cartella, chiamate):
    """Caso: la pagina manda il cielo di un interno e il blocco sparisce in silenzio."""
    scelte = blocchi.da_preset("interno-rivista").a_dizionario()
    scelte["cielo"] = "sereno"
    with pytest.raises(ErroreAirender) as errore:
        _studio(cartella, chiamate).componi({"scelte": scelte})
    assert "cielo" in errore.value.fatto and errore.value.cosa_fare


# --- destinazione e costo ----------------------------------------------------


def test_la_destinazione_e_quella_del_provider_vero_senza_ripiego(cartella):
    """Caso: lo Studio annuncia una destinazione e la coda manda altrove (regola 5)."""
    studio = Studio(cartella)  # il provider predefinito vero: nessuna chiamata, solo nomi
    destinazione = studio.destinazione(NANO)
    assert destinazione["destinazione"] == comfy.ProviderComfy().destinazione_per(NANO)
    assert destinazione["senza_ripiego"] is True
    assert destinazione["cosa_manca"] is None


def test_il_costo_misurato_dice_circa_e_la_data_quello_non_misurato_lo_dice(cartella, chiamate):
    """Caso: un costo scelto o mai letto stampato come se fosse certo (regola 3)."""
    studio = _studio(cartella, chiamate)
    nano = studio.destinazione(NANO)
    assert nano["costo_misurato"] is True
    assert "circa 17 crediti" in nano["costo"] and "misurato il 27/10/2026" in nano["costo"]
    assert "17,17" in nano["costo"]
    kontext = studio.destinazione(KONTEXT)
    assert kontext["costo_misurato"] is False and kontext["costo"].startswith("non misurato")


def test_il_costo_di_n_varianti_e_n_volte_quello_di_un_render(cartella, chiamate):
    """Caso: quattro varianti annunciate al prezzo di una (regola 5)."""
    studio = _studio(cartella, chiamate)
    quattro = studio.destinazione(NANO, 4)
    assert quattro["varianti"] == 4
    totale = round(4 * config.COSTO_NANO_BANANA_2_CREDITI)
    assert quattro["costo"].startswith(f"circa {totale} crediti per 4 immagini")
    assert "4 × 17,17" in quattro["costo"] and "misurato il 27/10/2026" in quattro["costo"]
    assert studio.destinazione(KONTEXT, 3)["costo"].startswith("non misurato")
    assert "69" not in studio.destinazione(KONTEXT, 4)["costo"]


@pytest.mark.parametrize("varianti", [0, 5, "due", 2.5, True, None])
def test_un_numero_di_varianti_fuori_misura_si_rifiuta(cartella, chiamate, varianti):
    with pytest.raises(RichiestaStudioNonValida) as errore:
        _studio(cartella, chiamate).destinazione(NANO, varianti)
    assert str(config.VARIANTI_MASSIME) in errore.value.cosa_fare


def test_un_modello_sconosciuto_si_rifiuta(cartella, chiamate):
    """Caso: la pagina manda un modello che nessuno ha sondato."""
    with pytest.raises(RichiestaStudioNonValida):
        _studio(cartella, chiamate).destinazione("openai/gpt-image-1")


# --- viste -------------------------------------------------------------------


def test_stato_vuoto_senza_viste_e_senza_dati_finti(cartella, chiamate):
    """Caso: lo stato vuoto riempito con una vista o un render di esempio."""
    studio = _studio(cartella, chiamate)
    stato = studio.stato_studio()
    assert stato["viste"] == [] and stato["lavori_attivi"] == []
    assert stato["cartella"] == str(cartella.resolve())


def test_le_viste_si_elencano_dalla_piu_recente(cartella, chiamate):
    """Caso: la palette salva una vista nuova e lo Studio apre la vecchia."""
    import os

    (cartella / "vecchia.png").write_bytes(vista_shaded(320, 200))
    (cartella / "nuova.png").write_bytes(vista_shaded(320, 200))
    (cartella / "note.txt").write_text("non una vista")
    (cartella / "vecchia.camera.json").write_text('{"prospettiva_centrale": true}')
    os.utime(cartella / "vecchia.png", (1_000_000, 1_000_000))
    studio = _studio(cartella, chiamate)
    assert [v["nome"] for v in studio.elenco_viste()] == ["nuova.png", "vecchia.png"]
    assert studio.descrivi_vista("vecchia.png")["camera"] == "Prospettiva centrale"
    assert studio.descrivi_vista("nuova.png")["camera"] is None


@pytest.mark.parametrize("nome", ["../fuori.png", "sotto/vista.png", "..\\fuori.png", ".nascosta.png", "vista.txt", ""])
def test_una_vista_si_chiede_solo_per_nome_dentro_la_cartella(cartella, chiamate, nome):
    """Caso: la pagina (o un'altra pagina) chiede un file fuori dalla cartella delle viste."""
    with pytest.raises(RichiestaStudioNonValida):
        _studio(cartella, chiamate).percorso_vista(nome)


def test_una_vista_wireframe_e_un_errore_che_dice_cosa_risalvare(cartella, chiamate):
    """Caso: stato di errore di Genera, vista non adatta."""
    (cartella / "filo.png").write_bytes(vista_wireframe())
    descrizione = _studio(cartella, chiamate).descrivi_vista("filo.png")
    assert descrizione["idonea"] is False
    assert descrizione["fatto"] and descrizione["cosa_fare"]


def test_una_vista_colorata_per_layer_porta_l_avviso_dei_colori(cartella, chiamate):
    """Caso: la falda viola diventa lamiera viola e nessuno l'aveva detto prima."""
    (cartella / "colori.png").write_bytes(_vista_colorata())
    (cartella / "grigia.png").write_bytes(vista_shaded(640, 400))
    studio = _studio(cartella, chiamate)
    assert studio.descrivi_vista("colori.png")["colori_come_materiali"] is True
    assert studio.descrivi_vista("grigia.png")["colori_come_materiali"] is False


def test_una_vista_caricata_entra_nella_cartella_con_un_nome_nuovo(cartella, chiamate):
    """Caso: Usa un'altra vista scrive sopra una vista che c'era."""
    studio = _studio(cartella, chiamate)
    primo = studio.carica_vista(vista_shaded(320, 200), "mia.png")
    secondo = studio.carica_vista(vista_shaded(320, 200), "mia.png")
    assert primo["nome"] != secondo["nome"]
    assert (cartella / primo["nome"]).is_file() and (cartella / secondo["nome"]).is_file()
    with pytest.raises(FileNonTrovato):
        studio.carica_vista(b"non sono un'immagine")


def test_una_vista_troppo_pesante_si_rifiuta_prima_di_aprirla(cartella, chiamate, monkeypatch):
    """Caso: si trascina per sbaglio un file enorme e il server lo tiene in memoria."""
    monkeypatch.setattr(config, "STUDIO_CARICAMENTO_MASSIMO_MB", 0)
    with pytest.raises(RichiestaStudioNonValida) as errore:
        _studio(cartella, chiamate).carica_vista(vista_shaded(320, 200))
    assert "MB" in errore.value.fatto


# --- invio -------------------------------------------------------------------


def test_genera_scrive_il_lavoro_con_la_destinazione_mostrata(cartella, vista, chiamate):
    """Caso: stato in corso. Il lavoro c'e', lo stato dice in coda, niente e' partito."""
    studio = _studio(cartella, chiamate)
    risposta = studio.invia(_richiesta(studio, vista))
    stato = leggi_stato(cartella, risposta["identificativo"])
    assert stato["stato"] == "in coda"
    assert stato["destinazione"] == studio.destinazione(NANO)["destinazione"]
    attivi = studio.lavori_attivi()
    assert [a["identificativo"] for a in attivi] == [risposta["identificativo"]]
    assert attivi[0]["vista"] == vista and attivi[0]["preset_nome"] == "Rivista d'architettura"
    assert chiamate == []


def test_genera_con_tre_varianti_mette_tre_lavori_con_le_stesse_scelte(cartella, vista, chiamate):
    """Caso: le varianti partono con scelte diverse, o ne parte una sola e se ne pagano tre."""
    studio = _studio(cartella, chiamate)
    risposta = studio.invia(_richiesta(studio, vista, varianti=3))
    assert len(risposta["identificativi"]) == 3 and risposta["identificativo"] == risposta["identificativi"][0]
    lavori = [studio.lavoro(i) for i in risposta["identificativi"]]
    assert {str(l["scelte"]) for l in lavori} == {str(lavori[0]["scelte"])}
    assert all(l["stato"] == "in coda" for l in lavori)
    assert chiamate == []
    coda = _coda(cartella, chiamate)
    while coda.esegui_uno():
        pass
    assert len(chiamate) == 3 and len({c.prompt for c in chiamate}) == 1


def test_la_prova_a_secco_dice_quante_varianti_e_il_costo(cartella, vista, chiamate):
    studio = _studio(cartella, chiamate)
    secco = studio.prova_a_secco(_richiesta(studio, vista, varianti=2))
    assert secco["varianti"] == 2 and "per 2 immagini" in secco["destinazione"]["costo"]
    assert list((cartella / "lavori" / "in-attesa").iterdir()) == []


def test_genera_non_manda_se_la_destinazione_mostrata_e_un_altra(cartella, vista, chiamate):
    """Caso: la pagina ha letto una destinazione vecchia, il provider ne ha un'altra (regola 5)."""
    studio = _studio(cartella, chiamate)
    richiesta = _richiesta(studio, vista, destinazione_mostrata="Un altro servizio")
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.invia(richiesta)
    assert "Non ho inviato niente" in errore.value.fatto
    assert list((cartella / "lavori" / "in-attesa").iterdir()) == []


def test_genera_non_manda_una_vista_non_adatta(cartella, chiamate):
    """Caso: stato di errore di Genera, la vista wireframe parte lo stesso."""
    (cartella / "filo.png").write_bytes(vista_wireframe())
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia(_richiesta(studio, "filo.png"))
    assert list((cartella / "lavori" / "in-attesa").iterdir()) == []


def test_genera_si_ferma_prima_con_un_modello_senza_schema(cartella, vista, chiamate):
    """Caso: stato di errore di Genera, modello senza schema verificato."""
    studio = _studio(cartella, chiamate, classe=ProviderSenzaKontext)
    modelli = {m["id"]: m["verificato"] for m in studio.catalogo()["modelli"]}
    assert modelli[NANO] is True and modelli[KONTEXT] is False
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.invia(_richiesta(studio, vista, modello=KONTEXT))
    assert "Non mando" in errore.value.fatto


def test_il_prompt_scritto_a_mano_e_quello_che_parte(cartella, vista, chiamate):
    """Caso: l'utente modifica il prompt e parte quello ricomposto dalle scelte."""
    studio = _studio(cartella, chiamate)
    risposta = studio.invia(_richiesta(studio, vista, prompt_a_mano="  Edit this exact image. Make it blue.  "))
    _coda(cartella, chiamate).esegui_uno()
    assert chiamate[0].prompt == "Edit this exact image. Make it blue."
    assert studio.lavoro(risposta["identificativo"])["prompt_a_mano"] is True


def test_la_prova_a_secco_non_scrive_niente_e_dice_cosa_fermerebbe(cartella, vista, chiamate):
    """Caso: Prova a secco che manda, o che tace sulla chiave mancante."""
    studio = Studio(cartella, coda_attiva=lambda: False)  # Comfy vero, senza chiave
    secco = studio.prova_a_secco(_richiesta(studio, vista))
    assert secco["inviato"] is False
    assert secco["prompt"].startswith("Edit this exact image.")
    fatti = " ".join(p["fatto"] for p in secco["problemi"])
    assert "chiave" in fatti.lower()
    assert "coda dei lavori non sta girando" in fatti
    assert list((cartella / "lavori" / "in-attesa").iterdir()) == []


# --- il giro intero: pieno, errore, annullato, rifai -------------------------


def test_pieno_il_render_della_vista_con_la_sua_ricetta(cartella, vista, chiamate):
    """Caso: stato pieno di Risultato. Il render c'e' e lo Studio non lo trova."""
    studio = _studio(cartella, chiamate)
    identificativo = studio.invia(_richiesta(studio, vista))["identificativo"]
    _coda(cartella, chiamate).esegui_uno()

    lavori = studio.render_della_vista(vista)
    assert [l["identificativo"] for l in lavori] == [identificativo]
    assert lavori[0]["stato"] == "fatto" and lavori[0]["render"] is True
    assert lavori[0]["scostamento_geometria"] is None
    assert studio.file_render(identificativo).read_bytes() == b"render-finto"
    ricetta = studio.ricetta(identificativo)
    assert ricetta["preset"] == "rivista" and ricetta["modello"] == NANO
    assert ricetta["percorso_ricetta"].endswith(".ricetta.json")
    assert studio.lavori_attivi() == []


def test_errore_il_lavoro_fallito_resta_con_la_frase_e_senza_render(cartella, vista, chiamate):
    """Caso: stato di errore di Risultato, solo un codice HTTP e nessun gesto successivo."""
    studio = _studio(cartella, chiamate)
    identificativo = studio.invia(_richiesta(studio, vista))["identificativo"]
    errore = ErroreProvider("Il servizio dice che i crediti sono finiti.", "Ricarica i crediti.", stato=402)
    _coda(cartella, chiamate, errore=errore).esegui_uno()

    lavoro = studio.lavoro(identificativo)
    assert lavoro["stato"] == "errore" and lavoro["render"] is False
    assert lavoro["fatto"] == errore.fatto and lavoro["cosa_fare"] == errore.cosa_fare
    with pytest.raises(FileNonTrovato):
        studio.ricetta(identificativo)
    with pytest.raises(FileNonTrovato):
        studio.file_render(identificativo)


def test_annulla_prima_dell_invio_ferma_il_lavoro(cartella, vista, chiamate):
    """Caso: Annulla nella striscia non ferma niente."""
    studio = _studio(cartella, chiamate)
    identificativo = studio.invia(_richiesta(studio, vista))["identificativo"]
    studio.annulla(identificativo)
    _coda(cartella, chiamate).esegui_uno()
    assert studio.lavoro(identificativo)["stato"] == "annullato"
    assert chiamate == []


def test_rifai_rimette_in_coda_la_stessa_ricetta(cartella, vista, chiamate):
    """Caso: Rifai riparte con le scelte di adesso invece che con quelle del render."""
    studio = _studio(cartella, chiamate)
    richiesta = _richiesta(studio, vista, preset="pioggia", modello=KONTEXT)
    primo = studio.invia(richiesta)["identificativo"]
    _coda(cartella, chiamate).esegui_uno()

    secondo = studio.rifai(primo, {"destinazione_mostrata": studio.destinazione(KONTEXT)["destinazione"]})
    _coda(cartella, chiamate).esegui_uno()
    assert secondo["identificativo"] != primo
    assert chiamate[0].prompt == chiamate[1].prompt
    assert chiamate[1].modello == KONTEXT and chiamate[1].preset == "pioggia"
    assert len(studio.render_della_vista(vista)) == 2
    with pytest.raises(RichiestaStudioNonValida):
        studio.rifai(primo, {"destinazione_mostrata": "altrove"})


def test_due_render_della_stessa_vista_per_l_a_b_fra_modelli(cartella, vista, chiamate):
    """Caso: Confronta con non trova l'altro render della stessa vista."""
    (cartella / "altra.png").write_bytes(vista_shaded(640, 400, seme=9))
    studio = _studio(cartella, chiamate)
    studio.invia(_richiesta(studio, vista, modello=NANO))
    studio.invia(_richiesta(studio, vista, modello=KONTEXT))
    studio.invia(_richiesta(studio, "altra.png"))
    coda = _coda(cartella, chiamate)
    while coda.esegui_uno():
        pass
    lavori = studio.render_della_vista(vista)
    assert {l["modello_nome"] for l in lavori} == {"Nano Banana 2", "FLUX.1 Kontext Pro"}
    assert len(studio.render_della_vista("altra.png")) == 1


def test_un_id_di_lavoro_inventato_si_rifiuta_prima_di_diventare_un_percorso(cartella, chiamate):
    """Caso: /file/render/../../qualcosa legge un file fuori dalla coda."""
    studio = _studio(cartella, chiamate)
    for cattivo in ("../../etc/passwd", "20261028-100000-000000-zzzz", ""):
        with pytest.raises(RichiestaStudioNonValida):
            studio.file_render(cattivo)


def test_apri_cartella_apre_quella_dei_render(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    studio.apri_cartella("render")
    studio.apri_cartella("viste")
    assert studio.aperte == [cartella.resolve() / "lavori" / "fatto", cartella.resolve()]


# --- il server ---------------------------------------------------------------


@pytest.fixture
def server(cartella, vista, chiamate):
    studio = _studio(cartella, chiamate)
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    yield servito, studio
    servito.shutdown()
    servito.server_close()


def _chiedi(servito, metodo, percorso, corpo=None, intestazioni=None, host=None):
    porta = servito.server_address[1]
    connessione = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
    tutte = {"Host": host or f"127.0.0.1:{porta}", **(intestazioni or {})}
    if metodo == "POST":
        tutte.setdefault("X-Airender", "1")
    dati = json.dumps(corpo).encode() if isinstance(corpo, dict) else corpo
    connessione.request(metodo, percorso, body=dati, headers=tutte)
    risposta = connessione.getresponse()
    contenuto = risposta.read()
    connessione.close()
    return risposta.status, risposta.getheader("Content-Type") or "", contenuto


def test_il_server_ascolta_solo_su_127_0_0_1_con_la_porta_del_sistema(server):
    """Caso: lo Studio raggiungibile da un'altra macchina della rete dello studio."""
    servito, _studio_ = server
    assert servito.server_address[0] == "127.0.0.1"
    assert servito.server_address[1] > 0


def test_la_pagina_e_le_rotte_json_rispondono(server, vista):
    servito, _studio_ = server
    stato, tipo, corpo = _chiedi(servito, "GET", "/")
    assert stato == 200 and "text/html" in tipo and b"AIRENDER" in corpo
    for percorso in ("/pagine/studio.js", "/pagine/studio.css"):
        assert _chiedi(servito, "GET", percorso)[0] == 200
    stato, tipo, corpo = _chiedi(servito, "GET", "/api/studio")
    assert stato == 200 and "application/json" in tipo
    assert [v["nome"] for v in json.loads(corpo)["viste"]] == [vista]
    assert _chiedi(servito, "GET", "/api/catalogo")[0] == 200
    assert json.loads(_chiedi(servito, "GET", f"/api/viste/{vista}")[2])["idonea"] is True
    stato, tipo, corpo = _chiedi(servito, "GET", f"/file/vista/{vista}")
    assert stato == 200 and tipo == "image/png" and corpo.startswith(b"\x89PNG")
    destinazione = json.loads(_chiedi(servito, "GET", f"/api/destinazione?modello={NANO}")[2])
    assert destinazione["modello_nome"] == "Nano Banana 2"


def test_il_giro_intero_passando_dal_server(server, vista, cartella, chiamate):
    """Caso: le rotte funzionano una per una ma non in fila, come le usa la pagina."""
    servito, studio = server
    scelte = blocchi.da_preset("ora-blu").a_dizionario()
    composto = json.loads(_chiedi(servito, "POST", "/api/componi", {"scelte": scelte, "preset": "ora-blu"})[2])
    destinazione = studio.destinazione(NANO)["destinazione"]
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/invia", {
        "vista": vista, "scelte": scelte, "preset": "ora-blu", "modello": NANO,
        "destinazione_mostrata": destinazione,
    })
    assert stato == 200
    identificativo = json.loads(corpo)["identificativo"]
    assert json.loads(_chiedi(servito, "GET", f"/api/lavori/{identificativo}")[2])["stato"] == "in coda"
    _coda(cartella, chiamate).esegui_uno()
    assert chiamate[0].prompt == composto["prompt"]
    lavori = json.loads(_chiedi(servito, "GET", f"/api/viste/{vista}/render")[2])
    assert lavori[0]["stato"] == "fatto"
    assert _chiedi(servito, "GET", f"/file/render/{identificativo}")[2] == b"render-finto"
    ricetta = json.loads(_chiedi(servito, "GET", f"/api/lavori/{identificativo}/ricetta")[2])
    assert ricetta["preset"] == "ora-blu"


def test_un_errore_arriva_alla_pagina_con_fatto_e_cosa_fare(server):
    """Caso: la pagina riceve un codice HTTP e niente da dire all'utente."""
    servito, _studio_ = server
    stato, tipo, corpo = _chiedi(servito, "GET", "/api/destinazione?modello=nessuno")
    errore = json.loads(corpo)["errore"]
    assert stato == 400 and "application/json" in tipo
    assert errore["fatto"] and errore["cosa_fare"]
    stato, _tipo, corpo = _chiedi(servito, "GET", "/api/viste/mancante.png")
    assert stato == 404 and json.loads(corpo)["errore"]["cosa_fare"]
    stato, _tipo, corpo = _chiedi(servito, "GET", "/non/esiste")
    assert stato == 404 and json.loads(corpo)["errore"]["fatto"]


def test_un_post_senza_l_intestazione_dello_studio_si_rifiuta(server, vista, cartella):
    """Caso: una pagina web qualunque aperta nel browser manda un lavoro allo Studio."""
    servito, _studio_ = server
    stato, _tipo, _corpo = _chiedi(servito, "POST", "/api/invia", {"vista": vista},
                                   intestazioni={"X-Airender": "0"})
    assert stato == 403
    assert list((cartella / "lavori" / "in-attesa").iterdir()) == []


def test_un_host_diverso_si_rifiuta(server):
    """Caso: DNS rebinding, un dominio esterno che punta a 127.0.0.1."""
    servito, _studio_ = server
    assert _chiedi(servito, "GET", "/api/studio", host="esempio.it")[0] == 403
    assert _chiedi(servito, "POST", "/api/componi", {}, host="esempio.it")[0] == 403


def test_un_percorso_che_esce_dalla_cartella_non_si_serve(server):
    """Caso: /file/vista/..%2F..%2Fqualcosa legge un file del disco."""
    servito, _studio_ = server
    for percorso in ("/file/vista/..%2F..%2Fsegreto.png", "/file/render/..%2Fx", "/pagine/..%2Fservizio.py"):
        assert _chiedi(servito, "GET", percorso)[0] in (400, 404)


def test_si_carica_una_vista_dal_server(server, cartella):
    servito, _studio_ = server
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/viste", vista_shaded(320, 200),
                                  intestazioni={"Content-Type": "application/octet-stream"})
    assert stato == 200 and (cartella / json.loads(corpo)["nome"]).is_file()


# --- la pagina ---------------------------------------------------------------


def test_le_pagine_non_chiedono_niente_a_internet():
    """Caso: lo Studio offline mostra una pagina vuota perche' aspetta un CDN o un font."""
    for file in CARTELLA_PAGINE.iterdir():
        testo = file.read_text(encoding="utf-8")
        assert not re.search(r"https?://", testo), f"{file.name} chiede qualcosa a internet"


def test_la_pagina_ha_i_testi_degli_stati_di_design_md():
    """Caso: uno stato di DESIGN.md manca dalla pagina, o ha cambiato parole."""
    script = (CARTELLA_PAGINE / "studio.js").read_text(encoding="utf-8")
    for testo in (
        "Nessuna vista ancora.",                                   # Genera, vuoto
        "Catturala dalla palette in Allplan",
        "sta lavorando",                                           # in corso
        "Allplan resta libero",
        "Annulla",
        "Vista non adatta",                                        # errore
        "L'invio non è andato.",
        "Miniature illustrative: rendono l'idea, non sono render del modello",
        "Mostra e modifica il prompt completo",
        "Ricomponi dalle scelte",
        "Prova a secco",
        "Il modello legge i colori della vista come materiali.",
        "Nessun render ancora. Scegli uno stile in Genera e premi Genera.",  # Risultato, vuoto
        "È ancora il tuo edificio?",
        "Prima / dopo", "Affiancati", "Solo render", "Confronta con",
        "Non misurata",
        "Misura grezza: ombre nuove, neve e vegetazione davanti contano come spigoli persi.",
        "Misura ora",
        "Rifai con la stessa ricetta",
        "Prima serve un render. Generane uno da Genera.",            # Ritocca, vuoto
        "Disegna un'area, poi scrivi cosa cambiare nella sua nota.",
        "Un'area senza nota non dice al modello cosa fare.",
    ):
        assert testo in script, testo


def test_le_etichette_dello_studio_non_promettono_la_scala():
    """Caso: una nostra etichetta dice scala dove il prodotto governa la grana."""
    from core.lessico import PAROLE_VIETATE

    pagina = re.sub(r"<[^>]+>", " ", (CARTELLA_PAGINE / "index.html").read_text(encoding="utf-8"))
    script = (CARTELLA_PAGINE / "studio.js").read_text(encoding="utf-8")
    # Solo i testi: i nomi delle proprieta' CSS e del codice non li legge nessuno.
    stringhe = re.findall(r'"[^"\n]*"|`[^`]*`', script)
    parole = set(re.findall(r"[a-zA-Zàèéìòù]+", " ".join([pagina, *stringhe]).lower()))
    assert not parole & set(PAROLE_VIETATE)


def test_il_modulo_studio_non_importa_allplan():
    """Caso: lo Studio smette di girare senza Allplan (regola 1)."""
    cartella = Path(modulo_servizio.__file__).parent
    for file in cartella.glob("*.py"):
        assert "NemAll_Python" not in file.read_text(encoding="utf-8"), file.name


# --- tenuta della geometria (prompt 8, 2026-10-31) -------------------------------


def test_ogni_render_esce_con_la_sua_misura_degli_spigoli(cartella, vista, chiamate):
    """Caso: Risultato scrive «Non misurata» anche quando la misura si poteva fare."""
    studio = _studio(cartella, chiamate)
    studio.invia(_richiesta(studio, vista))
    _coda(cartella, chiamate, eco=True).esegui_uno()
    tenuta = studio.render_della_vista(vista)[0]["tenuta"]
    assert tenuta["spigoli"] == 1.0 and tenuta["motivo"] is None and not tenuta["avvisa"]


def test_un_render_illeggibile_resta_non_misurato_col_perche(cartella, vista, chiamate):
    studio = _studio(cartella, chiamate)
    studio.invia(_richiesta(studio, vista))
    _coda(cartella, chiamate).esegui_uno()
    tenuta = studio.render_della_vista(vista)[0]["tenuta"]
    assert tenuta["spigoli"] is None and "non e' un'immagine" in tenuta["motivo"]


def test_un_render_vecchio_dice_perche_non_e_misurato_e_si_misura_a_richiesta(cartella, vista, chiamate):
    """Caso: un render di prima della misura mostra un numero inventato, o niente e nessun modo di misurarlo."""
    from core import coda as modulo_coda

    studio = _studio(cartella, chiamate)
    studio.invia(_richiesta(studio, vista))
    _coda(cartella, chiamate, eco=True).esegui_uno()
    lavoro = studio.render_della_vista(vista)[0]
    render = next((cartella / "lavori" / "fatto").glob("*.png"))
    modulo_coda.percorso_misura(render).unlink()
    vecchio = studio.render_della_vista(vista)[0]["tenuta"]
    assert vecchio["spigoli"] is None and vecchio["da_misurare"] and "prima" in vecchio["motivo"]
    assert studio.misura_ora(lavoro["identificativo"])["spigoli"] is not None


def test_la_misura_che_non_si_puo_fare_non_diventa_un_numero(tmp_path):
    """Regola 3: vista sparita, la misura dice perche' e non stampa un numero."""
    from core import coda as modulo_coda

    render = tmp_path / "r.png"
    render.write_bytes(vista_shaded(320, 200))
    misura = modulo_coda.misura_tenuta(tmp_path / "non-c-e.png", render)
    assert misura["spigoli"] is None and "Non ho trovato" in misura["motivo"]
