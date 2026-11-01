"""L'albero dei passi (core/passi.py), i lavori che partono da un passo e Studio · Passi.

Nessuna rete: il provider e' un finto che restituisce un PNG vero, perche' un
passo parte dal render del passo prima e la coda controlla che sia
un'immagine. Gli stati sono quelli di DESIGN.md, Studio · Passi.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from conftest import vista_shaded
from core import blocchi, config, passi as modulo_passi
from core.coda import ERRORE, FATTO, FORMATO, Coda, Lavoro, LavoroNonValido, leggi_stato, metti_in_coda
from core.errori import ErroreAirender, FileNonTrovato
from core.provider.base import Risultato
from core.ricetta import Ricetta, impronta
from core.studio.server import avvia_in_sottofondo, crea_server
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva
from test_studio import _chiedi

NANO = MODELLI[0].identificativo


def _png(colore=(120, 130, 140), larghezza=320, altezza=200) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), colore).save(uscita, format="PNG")
    return uscita.getvalue()


class ProviderCheRende(ProviderDiProva):
    """Come il finto della coda, ma il render e' un PNG e la ricetta porta i crediti."""

    def genera(self, richiesta):
        self.registro.append(richiesta)
        if self.errore:
            raise self.errore
        return Risultato(
            immagine=_png((len(self.registro) * 40 % 255, 90, 60)),
            formato="png",
            ricetta=Ricetta(
                provider=self.nome, modello=richiesta.modello, preset=richiesta.preset,
                preset_versione=richiesta.preset_versione, prompt=richiesta.prompt,
                testo_utente=richiesta.testo_utente, grana=richiesta.grana,
                dettaglio_grana=None, forza_struttura=None, risoluzione="", aspetto="",
                generazione_fissa=False, impronta_sorgente=impronta(richiesta.immagine),
                parametri={"crediti_usati": 17.17},
            ),
            avvisi=[],
        )


@pytest.fixture
def chiamate():
    return []


@pytest.fixture
def cartella(tmp_path) -> Path:
    percorso = tmp_path / "viste"
    percorso.mkdir()
    (percorso / "vista-1.png").write_bytes(vista_shaded(640, 400))
    return percorso


VISTA = "vista-1.png"


def _studio(cartella, chiamate, **opzioni):
    return Studio(cartella, provider="prova",
                  crea_provider=lambda _n: ProviderCheRende(chiamate, **opzioni),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate, **opzioni):
    return Coda(cartella, crea_provider=lambda _n: ProviderCheRende(chiamate, **opzioni), dire=lambda _t: None)


def _dest(studio):
    return studio.destinazione(NANO)["destinazione"]


def _genera(studio, preset="rivista", **altro):
    scelte = blocchi.da_preset(preset, materiali="intonaco a calce bianco").a_dizionario()
    return studio.invia({"vista": VISTA, "scelte": scelte, "preset": preset, "modello": NANO,
                         "destinazione_mostrata": _dest(studio), **altro})["identificativo"]


def _passo(studio, da, testo):
    return studio.invia_passo({"vista": VISTA, "da": da, "testo": testo, "modello": NANO,
                               "destinazione_mostrata": _dest(studio)})["identificativo"]


def _per_numero(dati, numero):
    return next(p for p in dati["passi"] if p["numero"] == numero)


@pytest.fixture
def catena(cartella, chiamate):
    """1 dalla vista, 2 dal 1, 3 dal 2, 4 dal 2 (un ramo), 5 dalla vista: l'albero del mockup."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    due = _passo(studio, uno, "due alberi davanti al fronte"); coda.esegui_uno()
    tre = _passo(studio, due, "qualche persona che cammina"); coda.esegui_uno()
    quattro = _passo(studio, due, "cielo al tramonto"); coda.esegui_uno()
    cinque = _genera(studio, modello=NANO); coda.esegui_uno()
    return studio, coda, {"1": uno, "2": due, "3": tre, "4": quattro, "5": cinque}


# --- l'albero: rami, strada, figli ------------------------------------------


def test_l_albero_ha_rami_strada_e_figli_come_nel_mockup(catena):
    """Caso: un passo fatto dal 2 finisce sotto il 3 invece che accanto, e un ramo sparisce."""
    studio, _coda_, ids = catena
    dati = studio.passi(VISTA)
    righe = [(p["numero"], p["profondita"], p["da_numero"]) for p in dati["passi"]]
    # ogni passo sotto suo padre, i rami nell'ordine in cui sono nati
    assert righe == [("1", 1, "0"), ("2", 2, "1"), ("3", 3, "2"), ("4", 3, "2"), ("5", 1, "0")]
    assert _per_numero(dati, "4")["strada"] == ["0", "1", "2", "4"]
    assert _per_numero(dati, "2")["figli"] == 2
    albero = modulo_passi.Albero.leggi(studio.percorso_vista(VISTA))
    assert [p["numero"] for p in albero.figli(ids["2"])] == [3, 4]
    assert [p["numero"] for p in albero.figli(modulo_passi.VISTA)] == [1, 5]


def test_l_avviso_compare_dalla_seconda_generazione_di_fila(catena):
    """Caso: un render passato tre volte dal modello senza dire che gli spigoli possono muoversi."""
    studio, _coda_, _ids = catena
    dati = studio.passi(VISTA)
    generazioni = {p["numero"]: (p["generazioni"], p["avviso"]) for p in dati["passi"]}
    assert config.PASSI_AVVISO_DA_GENERAZIONE == 2
    assert generazioni["1"] == (1, False) and generazioni["5"] == (1, False)
    assert generazioni["2"] == (2, True) and generazioni["4"] == (3, True)


def test_il_file_dei_passi_sta_accanto_alla_vista_ed_e_leggibile_a_mano(catena, cartella):
    """Caso: l'albero vive solo in memoria e alla chiusura dello Studio si perde."""
    studio, _coda_, ids = catena
    studio.passi(VISTA)
    file_albero = cartella / "vista-1.passi.json"
    dati = json.loads(file_albero.read_text(encoding="utf-8"))
    assert dati["formato"] == modulo_passi.FORMATO and dati["vista"] == VISTA
    quattro = next(p for p in dati["passi"] if p["identificativo"] == ids["4"])
    # la ricetta completa: partenza, richiesta, testo, aree, modello, blocchi, costo, data
    assert quattro["da"] == ids["2"] and quattro["partenza"]["passo"] == ids["2"]
    assert quattro["partenza"]["file"].endswith(f"{ids['2']}.png")
    assert quattro["richieste"] == ["cielo al tramonto"]
    assert "cielo al tramonto" in quattro["prompt"] and quattro["aree"] is None
    assert quattro["modello"] == NANO and quattro["versione_blocchi"] == blocchi.VERSIONE
    assert quattro["costo_crediti"] == 17.17 and quattro["creato_il"] and quattro["impronta_partenza"]
    # nessun file temporaneo lasciato in giro dalla scrittura atomica
    assert not [p for p in cartella.iterdir() if p.name.startswith(".")]


def test_l_impronta_della_partenza_e_quella_del_render_del_passo_prima(catena, cartella):
    """Caso: la ricetta di un passo dice che e' partito dalla vista mentre e' partito da un render."""
    studio, _coda_, ids = catena
    studio.passi(VISTA)
    albero = modulo_passi.Albero.leggi(cartella / VISTA)
    due, tre = albero.passo(ids["2"]), albero.passo(ids["3"])
    assert tre["impronta_partenza"] == impronta(Path(due["render"]).read_bytes())
    uno = albero.passo(ids["1"])
    assert uno["impronta_partenza"] == impronta((cartella / VISTA).read_bytes())


def test_un_file_dei_passi_rotto_non_si_riscrive(cartella, chiamate):
    """Caso: lo Studio trova il JSON rotto, lo sovrascrive vuoto e i passi sono persi."""
    studio = _studio(cartella, chiamate)
    rotto = cartella / "vista-1.passi.json"
    rotto.write_text("{ non e' json", encoding="utf-8")
    with pytest.raises(modulo_passi.AlberoNonValido) as errore:
        studio.passi(VISTA)
    assert "Non l'ho toccato" in errore.value.cosa_fare
    assert rotto.read_text(encoding="utf-8") == "{ non e' json"


# --- migrazione dei render esistenti -----------------------------------------


def test_i_render_gia_fatti_diventano_passi_figli_della_vista_senza_perderne_uno(cartella, chiamate):
    """Caso: dopo l'aggiornamento i render fatti prima dell'albero spariscono dallo Studio."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    fatti = [_genera(studio, preset) for preset in ("rivista", "ora-blu", "pioggia")]
    coda.gira(una_volta=True)
    # un lavoro del formato 1, scritto prima di questo PR, senza i campi dei passi
    vecchio = json.loads((cartella / "lavori" / "fatto" / f"{fatti[0]}.json").read_text(encoding="utf-8"))
    for chiave in ("parte_da", "partenza", "richieste"):
        vecchio.pop(chiave)
    vecchio["formato"] = 1
    (cartella / "lavori" / "fatto" / f"{fatti[0]}.json").write_text(json.dumps(vecchio), encoding="utf-8")
    # un errore e un lavoro ancora in coda contano anche loro
    errato = _genera(studio, "autunno")
    _coda(cartella, chiamate, errore=ErroreAirender("Crediti finiti.", "Ricarica i crediti.")).esegui_uno()
    in_coda = _genera(studio, "notte-luna")

    assert not (cartella / "vista-1.passi.json").exists()
    dati = studio.passi(VISTA)
    assert sorted(p["identificativo"] for p in dati["passi"]) == sorted(fatti + [errato, in_coda])
    assert all(p["da_numero"] == "0" and p["profondita"] == 1 for p in dati["passi"])
    assert [p["numero"] for p in dati["passi"]] == ["1", "2", "3", "4", "5"]
    stati = {p["identificativo"]: p["stato"] for p in dati["passi"]}
    assert stati[errato] == ERRORE and stati[in_coda] == "in coda" and stati[fatti[0]] == FATTO


def test_allineare_due_volte_non_cambia_numeri_ne_ordine(catena, cartella):
    """Caso: a ogni apertura dello Studio i passi si rinumerano e il 4 diventa il 3."""
    studio, _coda_, _ids = catena
    prima = studio.passi(VISTA)
    scritto = (cartella / "vista-1.passi.json").stat().st_mtime_ns
    dopo = studio.passi(VISTA)
    assert [p["numero"] for p in prima["passi"]] == [p["numero"] for p in dopo["passi"]]
    assert (cartella / "vista-1.passi.json").stat().st_mtime_ns == scritto  # niente da scrivere


def test_un_passo_resta_anche_se_la_cartella_dei_lavori_viene_pulita(catena, cartella):
    """Caso: si svuota lavori/ a mano e l'albero perde i passi."""
    studio, _coda_, ids = catena
    studio.passi(VISTA)
    for file in (cartella / "lavori" / "fatto").glob(f"{ids['3']}*"):
        file.unlink()
    (cartella / "lavori" / "stato" / f"{ids['3']}.json").unlink()
    tre = _per_numero(studio.passi(VISTA), "3")
    assert tre["stato"] == FATTO and not tre["render"] and not tre["si_parte"]
    assert "non c'e' piu'" in tre["motivo_non_si_parte"]


# --- un lavoro che parte da un passo -------------------------------------------


def test_un_lavoro_da_un_passo_manda_il_render_del_passo_non_la_vista(catena, cartella, chiamate):
    """Caso: «Nuovo passo da qui» rimanda la vista Allplan e il passo riparte da zero."""
    _studio_, _coda_, ids = catena
    albero = modulo_passi.Albero.leggi(cartella / VISTA)
    render_due = Path(albero.passo(ids["2"])["render"]).read_bytes()
    richiesta_tre = chiamate[2]
    assert richiesta_tre.immagine == render_due
    assert richiesta_tre.immagine != (cartella / VISTA).read_bytes()
    # il prompt di un passo: la regola del passo e la richiesta, non di nuovo tutto lo stile
    assert richiesta_tre.prompt.startswith(blocchi.REGOLA_PASSO.testo)
    assert "qualche persona che cammina" in richiesta_tre.prompt
    assert blocchi.LOOK["canon"].testo not in richiesta_tre.prompt
    assert blocchi.NON_COPRIRE in richiesta_tre.prompt


def test_il_file_del_lavoro_da_un_passo_porta_partenza_e_richieste(cartella, chiamate, tmp_path):
    """Caso: un motore vecchio legge il lavoro, ignora la partenza e manda la vista."""
    partenza = tmp_path / "render.png"
    partenza.write_bytes(_png())
    lavoro = metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova",
                           modello="m", parte_da="abc", partenza=partenza, richieste=["un albero"],
                           crea_provider=lambda _n: ProviderCheRende(chiamate))
    dati = json.loads((cartella / "lavori" / "in-attesa" / f"{lavoro.identificativo}.json").read_text(encoding="utf-8"))
    assert dati["formato"] == FORMATO == 2
    assert dati["parte_da"] == "abc" and dati["partenza"] == str(partenza.resolve())
    assert dati["richieste"] == ["un albero"]
    with pytest.raises(LavoroNonValido):  # partenza senza passo: non si indovina
        Lavoro.da_dizionario({**dati, "parte_da": None})


def test_un_passo_senza_richiesta_si_rifiuta_prima_di_scrivere_il_lavoro(cartella, chiamate, tmp_path):
    """Caso: un passo vuoto parte, si paga, e il modello ridisegna l'immagine per niente."""
    partenza = tmp_path / "render.png"
    partenza.write_bytes(_png())
    with pytest.raises(blocchi.SceltaNonValida):
        metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova", modello="m",
                      parte_da="abc", partenza=partenza, richieste=["   "],
                      crea_provider=lambda _n: ProviderCheRende(chiamate))
    assert not list((cartella / "lavori" / "in-attesa").glob("*.json"))


def test_se_il_render_di_partenza_sparisce_la_coda_non_manda_niente(cartella, chiamate, tmp_path):
    """Caso: il render del passo prima e' stato cancellato e la coda manda la vista al suo posto."""
    partenza = tmp_path / "render.png"
    partenza.write_bytes(_png())
    lavoro = metti_in_coda(cartella, cartella / VISTA, blocchi.Scelte(), provider="prova", modello="m",
                           parte_da="abc", partenza=partenza, richieste=["un albero"],
                           crea_provider=lambda _n: ProviderCheRende(chiamate))
    partenza.unlink()
    _coda(cartella, chiamate).esegui_uno()
    stato = leggi_stato(cartella, lavoro.identificativo)
    assert stato["stato"] == ERRORE and not chiamate
    assert "punto di partenza non c'e' piu'" in stato["fatto"]
    assert "Rifai pulito dalla vista" in stato["cosa_fare"]


def test_un_lavoro_del_formato_1_si_legge_ancora_e_parte_dalla_vista(cartella, chiamate):
    """Caso: dopo l'aggiornamento i lavori gia' in coda vanno fra gli errori."""
    studio = _studio(cartella, chiamate)
    identificativo = _genera(studio)
    file_lavoro = cartella / "lavori" / "in-attesa" / f"{identificativo}.json"
    dati = json.loads(file_lavoro.read_text(encoding="utf-8"))
    for chiave in ("parte_da", "partenza", "richieste"):
        dati.pop(chiave)
    dati["formato"] = 1
    file_lavoro.write_text(json.dumps(dati), encoding="utf-8")
    _coda(cartella, chiamate).esegui_uno()
    assert leggi_stato(cartella, identificativo)["stato"] == FATTO
    assert chiamate[0].immagine == (cartella / VISTA).read_bytes()


# --- Nuovo passo da qui, Rifai questo passo ---------------------------------------


def test_dal_passo_0_e_da_un_passo_non_riuscito_non_si_parte(catena, cartella, chiamate):
    """Caso: un passo nuovo parte da un passo fallito, che non ha un render."""
    studio, _coda_, ids = catena
    with pytest.raises(RichiestaStudioNonValida) as errore:
        _passo(studio, modulo_passi.VISTA, "un albero")
    assert "Genera" in errore.value.cosa_fare
    fallito = _passo(studio, ids["1"], "un albero")
    _coda(cartella, chiamate, errore=ErroreAirender("Crediti finiti.", "Ricarica.")).esegui_uno()
    riga = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == fallito)
    assert riga["stato"] == ERRORE and not riga["si_parte"] and riga["figli"] == 0
    with pytest.raises(RichiestaStudioNonValida):
        _passo(studio, fallito, "un altro albero")


def test_componi_passo_dice_se_apre_un_ramo_nuovo(catena):
    """Caso: l'utente non sa se il passo continua il ramo o ne apre uno accanto."""
    studio, _coda_, ids = catena
    da_tre = studio.componi_passo({"vista": VISTA, "da": ids["3"], "testo": "una panchina"})
    da_due = studio.componi_passo({"vista": VISTA, "da": ids["2"], "testo": "una panchina"})
    assert da_tre["ramo_nuovo"] is False and da_due["ramo_nuovo"] is True
    assert da_tre["generazioni"] == 4 and "una panchina" in da_tre["prompt"]
    assert da_tre["caratteri"] == len(da_tre["prompt"])


def test_il_passo_rifiuta_una_destinazione_diversa_da_quella_mostrata(catena):
    """Caso: la pagina ha mostrato un servizio e il passo parte verso un altro (regola 5)."""
    studio, _coda_, ids = catena
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia_passo({"vista": VISTA, "da": ids["2"], "testo": "un albero", "modello": NANO,
                            "destinazione_mostrata": "un altro servizio"})


def test_rifai_questo_passo_stessa_partenza_stessa_richiesta_ramo_accanto(catena, cartella, chiamate):
    """Caso: «Rifai questo passo» riparte dalla vista e perde il passo di partenza."""
    studio, coda, ids = catena
    nuovo = studio.rifai(ids["3"], {"destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    assert chiamate[-1].immagine == chiamate[2].immagine and chiamate[-1].prompt == chiamate[2].prompt
    dati = studio.passi(VISTA)
    riga = next(p for p in dati["passi"] if p["identificativo"] == nuovo)
    assert riga["da_numero"] == "2" and riga["strada"] == ["0", "1", "2", "6"]
    assert _per_numero(dati, "2")["figli"] == 3


def test_rifai_un_passo_senza_partenza_propone_rifai_pulito(catena, cartella):
    """Caso: il render del passo prima e' stato tolto e Rifai fallisce senza dire cosa fare."""
    studio, _coda_, ids = catena
    albero = modulo_passi.Albero.leggi(cartella / VISTA)
    Path(albero.passo(ids["2"])["render"]).unlink()
    with pytest.raises(FileNonTrovato) as errore:
        studio.rifai(ids["3"], {"destinazione_mostrata": _dest(studio)})
    assert "Rifai pulito dalla vista" in errore.value.cosa_fare
    tre = _per_numero(studio.passi(VISTA), "3")
    assert tre["partenza_mancante"] is True


# --- Rifai pulito dalla vista ------------------------------------------------------


def test_rifai_pulito_unisce_le_richieste_della_strada_in_un_prompt_dalla_vista(catena):
    """Caso: «rifai pulito» manda solo l'ultima richiesta e perde lo stile e gli alberi."""
    studio, _coda_, ids = catena
    pulito = studio.componi_pulito({"vista": VISTA, "passo": ids["4"]})
    assert pulito["strada"] == ["0", "1", "2", "4"] and pulito["generazioni"] == 3
    assert pulito["richieste"] == ["due alberi davanti al fronte", "cielo al tramonto"]
    prompt = pulito["prompt"]
    stile = blocchi.componi(blocchi.da_preset("rivista", materiali="intonaco a calce bianco"))
    assert prompt.startswith(stile[: -len(blocchi.COSA_EVITARE.testo)].rstrip())
    assert prompt.endswith(blocchi.COSA_EVITARE.testo)
    assert prompt.index("due alberi") < prompt.index("cielo al tramonto") < prompt.index("Avoid:")
    assert "qualche persona" not in prompt  # il 3 e' su un altro ramo


def test_rifai_pulito_parte_dalla_vista_ed_e_un_ramo_nuovo_sotto_lo_0(catena, cartella, chiamate):
    """Caso: «rifai pulito» parte dal render del passo e accumula un'altra generazione."""
    studio, coda, ids = catena
    mostrato = studio.componi_pulito({"vista": VISTA, "passo": ids["4"]})["prompt"]
    nuovo = studio.invia_pulito({"vista": VISTA, "passo": ids["4"], "modello": NANO,
                                 "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    assert chiamate[-1].immagine == (cartella / VISTA).read_bytes()
    assert chiamate[-1].prompt == mostrato  # parte il prompt che si e' visto
    riga = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == nuovo)
    assert riga["da_numero"] == "0" and riga["generazioni"] == 1 and not riga["avviso"]
    assert riga["tipo"] == "pulito" and riga["nome"].startswith("Pulito dalla vista")


def test_rifai_pulito_di_un_passo_dalla_vista_non_ha_niente_da_unire(catena):
    """Caso: «rifai pulito» su un passo 1 rimanda lo stesso invio e lo fa pagare."""
    studio, _coda_, ids = catena
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.componi_pulito({"vista": VISTA, "passo": ids["1"]})
    assert "Rifai questo passo" in errore.value.cosa_fare


def test_rifai_pulito_con_il_prompt_scritto_a_mano_lo_tiene(cartella, chiamate):
    """Caso: il passo 1 aveva il prompt modificato a mano e «rifai pulito» lo rimpiazza coi blocchi."""
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio, prompt_a_mano="Edit this image. My own words."); coda.esegui_uno()
    due = _passo(studio, uno, "un albero"); coda.esegui_uno()
    prompt = studio.componi_pulito({"vista": VISTA, "passo": due})["prompt"]
    assert prompt.startswith("Edit this image. My own words.") and "un albero" in prompt


# --- blocchi dei passi ---------------------------------------------------------------


def test_le_richieste_passano_come_le_scrive_l_utente_con_cosa_non_toccare():
    """Caso: la richiesta in italiano viene persa o tagliata, o il passo copre le finestre."""
    testo = blocchi.componi_richieste(blocchi.ESTERNO, ["  due alberi   davanti al fronte. "])
    assert "Change: due alberi davanti al fronte; do not cover" in testo
    assert testo.startswith(blocchi.REGOLA_PASSO.testo) and testo.endswith(blocchi.COSA_EVITARE.testo)
    assert blocchi.REGOLA_PASSO.origine == config.SCELTA
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi_richieste("giardino", ["un albero"])


def test_aggiungi_richieste_senza_richieste_lascia_il_testo_com_e():
    base = blocchi.componi(blocchi.da_preset("rivista"))
    assert blocchi.aggiungi_richieste(base, []) == base
    assert blocchi.aggiungi_richieste("testo mio", ["un albero"]).startswith("testo mio Also make")


# --- il server -------------------------------------------------------------------------


@pytest.fixture
def server(catena):
    studio, coda, ids = catena
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    yield servito, studio, coda, ids
    servito.shutdown()
    servito.server_close()


def test_le_rotte_dei_passi_rispondono_e_vogliono_l_intestazione(server):
    """Caso: una pagina estranea manda un passo pagato con un POST."""
    servito, studio, _coda_, ids = server
    stato, _tipo, corpo = _chiedi(servito, "GET", f"/api/viste/{VISTA}/passi")
    assert stato == 200 and len(json.loads(corpo)["passi"]) == 5
    corpo_passo = {"vista": VISTA, "da": ids["3"], "testo": "una panchina"}
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/passi/componi", corpo_passo)
    assert stato == 200 and "una panchina" in json.loads(corpo)["prompt"]
    stato, _tipo, _corpo = _chiedi(servito, "POST", "/api/passi/invia",
                                   {**corpo_passo, "modello": NANO, "destinazione_mostrata": _dest(studio)},
                                   intestazioni={"X-Airender": "0"})
    assert stato == 403
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/passi/invia",
                                  {**corpo_passo, "modello": NANO, "destinazione_mostrata": _dest(studio)})
    assert stato == 200 and json.loads(corpo)["identificativo"]
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/passi/pulito/componi", {"vista": VISTA, "passo": ids["4"]})
    assert stato == 200 and json.loads(corpo)["strada"] == ["0", "1", "2", "4"]
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/passi/pulito/invia",
                                  {"vista": VISTA, "passo": ids["4"], "modello": NANO,
                                   "destinazione_mostrata": _dest(studio)})
    assert stato == 200


def test_le_rotte_dei_passi_rifiutano_con_fatto_e_cosa_fare(server):
    servito, _studio_, _coda_, ids = server
    stato, _tipo, corpo = _chiedi(servito, "POST", "/api/passi/componi", {"vista": VISTA, "da": "nessuno", "testo": "x"})
    assert stato == 400
    errore = json.loads(corpo)["errore"]
    assert errore["fatto"] and errore["cosa_fare"]
    stato, _tipo, _corpo = _chiedi(servito, "GET", "/api/viste/..%2Fsegreto.png/passi")
    assert stato == 400


def test_la_pagina_ha_la_scheda_passi_attiva(server):
    """Caso: la voce Passi resta in grigio anche ora che la schermata c'e'."""
    servito, *_resto = server
    _stato, _tipo, corpo = _chiedi(servito, "GET", "/")
    assert b'href="#passi"' in corpo
    _stato, _tipo, script = _chiedi(servito, "GET", "/pagine/studio.js")
    assert b"Nessun passo ancora. Genera un render da Genera: sar\xc3\xa0 il passo 1." in script


def test_la_regola_del_passo_e_quella_della_bozza():
    """Caso: la regola dei passi riscritta nel codice e non nella bozza."""
    bozza = (Path(__file__).resolve().parent.parent / "docs" / "ui" / "blocchi-stile-bozza.md").read_text(encoding="utf-8")
    assert "bozza 9" in bozza.splitlines()[0] and blocchi.VERSIONE == "bozza-9"
    assert f"> {blocchi.REGOLA_PASSO.testo}" in bozza
