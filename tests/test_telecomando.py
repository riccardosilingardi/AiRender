"""La palette v1 (il telecomando), provata senza Allplan.

Il provider e' quello finto di test_coda.py: niente rete, niente chiave. I
processi (Python, Studio, Edge) sono finti: si controlla cosa la palette
lancerebbe, non lo si lancia.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import vista_shaded, vista_wireframe
from core import battito, blocchi, config
from core.coda import Coda, coda_viva
from core.errori import ErroreProvider
from core.studio.servizio import MODELLI, Studio
from test_coda import ProviderDiProva

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "allplan" / "comune"))

import telecomando as tc  # noqa: E402  pylint: disable=wrong-import-position

NANO = MODELLI[0].nome


@pytest.fixture
def cartella(tmp_path) -> Path:
    percorso = tmp_path / "viste"
    percorso.mkdir()
    return percorso.resolve()


@pytest.fixture
def vista(cartella) -> str:
    percorso = cartella / "vista-20261031-120000.png"
    percorso.write_bytes(vista_shaded(640, 400))
    return str(percorso)


@pytest.fixture
def chiamate():
    return []


def _telecomando(cartella, chiamate, avviatore=None):
    studio = Studio(
        cartella, provider="prova",
        crea_provider=lambda _nome: ProviderDiProva(chiamate),
        coda_attiva=lambda: coda_viva(cartella) is not None,
    )
    return tc.Telecomando(cartella, avviatore=avviatore, studio=studio)


def _valori(**cambi) -> tc.ValoriPalette:
    base = {"preset_esterno": "Rivista d'architettura", "preset_interno": "Interno rivista", "modello": NANO}
    return tc.ValoriPalette(**{**base, **cambi})


def _coda_che_batte(cartella):
    battito.scrivi(battito.percorso(cartella, battito.FILE_CODA), {})


# --- le voci -------------------------------------------------------------------


def test_le_voci_della_palette_hanno_i_nomi_dello_studio():
    """Caso: la palette chiama «Ora blu» quello che lo Studio chiama in un altro modo."""
    voci = tc.voci_palette()
    assert ("ora-blu", "Ora blu") in voci["PresetEsterno"]
    assert ("blu", "Ora blu") in voci["LuceEsterno"]
    assert voci["Modello"][0] == (MODELLI[0].identificativo, "Nano Banana 2")
    for elenco in ("LuceEsterno", "LuceInterno", "Cielo", "Intorno"):
        assert voci[elenco][0] == (None, tc.COME_IL_PRESET)


def test_nessun_nome_rompe_l_elenco_del_pyp():
    """Caso: un nome con «|» spezza la voce in due nel .pyp, e la scelta letta e' un'altra."""
    for elenco, voci in tc.voci_palette().items():
        nomi = [n for _i, n in voci]
        assert len(nomi) == len(set(nomi)), elenco
        assert all("|" not in n for n in nomi), elenco


def test_come_il_preset_lascia_le_scelte_del_preset():
    """Caso: la palette cambia la luce del preset anche quando l'utente non l'ha toccata."""
    assert _valori().scelte() == blocchi.da_preset("rivista")


def test_un_cambio_della_palette_va_sopra_il_preset_e_il_resto_resta():
    """Caso: scegliere il cielo cancella il look del preset."""
    scelte = _valori(luce_esterno="Ora blu", cielo="Neve", intorno="Città", materiali="  mattoni   rossi ").scelte()
    assert (scelte.luce, scelte.cielo, scelte.intorno, scelte.materiali) == ("blu", "neve", "citta", "mattoni rossi")
    assert scelte.look == blocchi.da_preset("rivista").look


def test_un_interno_ignora_cielo_e_intorno_dell_esterno():
    """Caso: i campi nascosti dell'esterno partono con un interno e il motore lo rifiuta."""
    scelte = _valori(interno=True, luce_interno="Sera, luci accese", cielo="Neve", intorno="Città").scelte()
    assert scelte.scena == blocchi.INTERNO and scelte.luce == "sera"
    assert scelte.cielo is None and scelte.intorno is None
    blocchi.componi(scelte)


def test_la_fedelta_della_palette_parte_dalla_predefinita_e_si_cambia():
    """Caso: la palette apre su «Rigida» e cambia tutti i render senza che l'utente l'abbia scelto."""
    voci = tc.voci_palette()["Fedelta"]
    assert voci[0] == (blocchi.FEDELTA_PREDEFINITA, "Bilanciata")
    assert {i for i, _n in voci} == set(blocchi.FEDELTA)
    assert _valori().scelte().fedelta == blocchi.FEDELTA_PREDEFINITA
    assert _valori(fedelta="Rigida").scelte().fedelta == "rigida"


def test_la_resa_della_palette_parte_da_fotorealistico_e_dice_cosa_spegne(cartella, chiamate):
    """Caso: la palette manda uno schizzo e l'utente crede che il cielo scelto parta."""
    assert tc.voci_palette()["Resa"][0] == (blocchi.FOTO, "Fotorealistico")
    assert _valori().scelte().resa == blocchi.FOTO
    assert _valori(resa="Schizzo a matita").scelte().resa == "schizzo"
    telecomando = _telecomando(cartella, chiamate)
    _dest, nota, _costo = telecomando.invio(_valori(resa="Schizzo a matita"))
    assert "Con la resa Schizzo a matita non partono: materiali, look, cielo, qualita." in nota
    assert "Con la resa" not in telecomando.invio(_valori())[1]


def test_una_voce_che_il_motore_non_conosce_dice_di_reinstallare():
    """Caso: palette vecchia con un motore nuovo, e la scelta si perde in silenzio."""
    with pytest.raises(blocchi.SceltaNonValida) as errore:
        _valori(cielo="Tempesta").scelte()
    assert "installa.ps1" in errore.value.cosa_fare


# --- vista e invio -----------------------------------------------------------------


def test_senza_vista_la_palette_dice_cosa_fare(cartella, chiamate):
    """Stato vuoto di DESIGN.md: niente miniatura finta, la frase del gesto."""
    assert _telecomando(cartella, chiamate).vista("") == (tc.NESSUNA_VISTA, "")


def test_una_vista_adatta_dice_dimensioni_e_numeri(cartella, chiamate, vista):
    """Stato pieno: «Adatta: shaded, N toni, sfondo uniforme X%»."""
    nome, esito = _telecomando(cartella, chiamate).vista(vista)
    assert nome == "vista-20261031-120000.png 640×400"
    assert esito.startswith("Adatta: shaded, ") and "toni, sfondo uniforme" in esito


def test_una_vista_non_adatta_dice_cosa_risalvare(cartella, chiamate):
    """Stato errore: la ragione e cosa risalvare, dalla regola di core/idoneita.py."""
    percorso = cartella / "vista-filo.png"
    percorso.write_bytes(vista_wireframe(640, 400))
    _nome, esito = _telecomando(cartella, chiamate).vista(str(percorso))
    assert esito.startswith("Non adatta: ") and "shaded" in esito


def test_una_vista_fuori_cartella_non_si_usa(cartella, chiamate, tmp_path):
    """Caso: la palette manda una vista che lo Studio non vede."""
    fuori = tmp_path / "altrove.png"
    fuori.write_bytes(vista_shaded(640, 400))
    _nome, esito = _telecomando(cartella, chiamate).vista(str(fuori))
    assert "non sta nella cartella delle viste" in esito


def test_destinazione_e_costo_si_leggono_prima_di_genera(cartella, chiamate):
    """Regola 5: dove va e quanto costa, prima del clic."""
    dove, nota, costo = _telecomando(cartella, chiamate).invio(_valori())
    assert dove == f"{ProviderDiProva.destinazione} → {MODELLI[0].identificativo}"
    assert "crediti" in costo and nota


# --- genera ------------------------------------------------------------------------


def test_genera_scrive_il_lavoro_e_torna_senza_mandare(cartella, chiamate, vista):
    """Caso: Allplan bloccato finche' il render non arriva, come nella palette di prova."""
    _coda_che_batte(cartella)
    telecomando = _telecomando(cartella, chiamate)
    dove, _nota, _costo = telecomando.invio(_valori())
    testo = telecomando.genera(vista, _valori(), dove)
    assert testo.startswith("In coda, verso ") and "Allplan resta libero" in testo
    assert not chiamate, "la palette non deve mandare niente: lo fa la coda"
    riepilogo = telecomando.riepilogo()
    assert riepilogo.lavoro_attivo and telecomando.testo_genera(riepilogo) == "Annulla"
    assert riepilogo.stato.startswith("In corso da 0:")


def test_genera_non_parte_se_la_destinazione_mostrata_e_un_altra(cartella, chiamate, vista):
    """Regola 5: si cambia modello, la palette mostra ancora la destinazione di prima."""
    _coda_che_batte(cartella)
    testo = _telecomando(cartella, chiamate).genera(vista, _valori(), "Comfy Router → un altro modello")
    assert "Non ho inviato niente" in testo
    assert not list((cartella / "lavori" / "in-attesa").glob("*.json"))


def test_genera_senza_coda_avvia_lo_studio_senza_finestra(cartella, chiamate, vista):
    """Caso: il lavoro resta in attesa per sempre perche' nessuno ha acceso la coda."""
    class Avviatore:
        avviate = 0

        def assicura_coda(self):
            Avviatore.avviate += 1

    telecomando = _telecomando(cartella, chiamate, Avviatore())
    dove, _n, _c = telecomando.invio(_valori())
    assert telecomando.genera(vista, _valori(), dove).startswith("In coda")
    assert Avviatore.avviate == 1


def test_genera_dice_se_la_coda_non_parte(cartella, chiamate, vista):
    """Stato errore: il lavoro e' scritto ma la coda non c'e', e la palette lo dice."""
    class Avviatore:
        def assicura_coda(self):
            raise tc.StudioNonPartito("lo Studio non batte", "lancialo a mano")

    telecomando = _telecomando(cartella, chiamate, Avviatore())
    dove, _n, _c = telecomando.invio(_valori())
    testo = telecomando.genera(vista, _valori(), dove)
    assert "la coda dei lavori non gira" in testo and "lancialo a mano" in testo
    assert "La coda dei lavori non sta girando" in telecomando.riepilogo().stato


def test_genera_senza_vista_non_scrive_niente(cartella, chiamate):
    """Stato vuoto: Genera spento finche' non c'e' una vista."""
    assert "Cattura vista" in _telecomando(cartella, chiamate).genera("", _valori(), "x")


def test_genera_rifiuta_una_vista_non_adatta(cartella, chiamate):
    """Caso: si paga una chiamata per un wireframe."""
    percorso = cartella / "vista-filo.png"
    percorso.write_bytes(vista_wireframe(640, 400))
    telecomando = _telecomando(cartella, chiamate)
    dove, _n, _c = telecomando.invio(_valori())
    assert "Cosa fare" in telecomando.genera(str(percorso), _valori(), dove)
    assert not list((cartella / "lavori" / "in-attesa").glob("*.json"))


def test_prova_a_secco_dice_destinazione_prompt_e_non_manda(cartella, chiamate, vista):
    """Caso: la prova a secco manda davvero, o tace sul perche' Genera si fermerebbe."""
    testo = _telecomando(cartella, chiamate).prova_a_secco(vista, _valori())
    assert testo.startswith("Prova a secco: non ho mandato niente.")
    assert "Genera partirebbe." in testo and "Prompt (" in testo
    assert not chiamate and not list((cartella / "lavori" / "in-attesa").glob("*.json"))


def test_annulla_mette_il_segnale_accanto_al_lavoro(cartella, chiamate, vista):
    """Caso: Annulla nella palette non ferma niente."""
    _coda_che_batte(cartella)
    telecomando = _telecomando(cartella, chiamate)
    dove, _n, _c = telecomando.invio(_valori())
    telecomando.genera(vista, _valori(), dove)
    identificativo = telecomando.riepilogo().lavoro_attivo
    assert "addebitata" in telecomando.annulla(identificativo)
    assert (cartella / "lavori" / "in-attesa" / f"{identificativo}.annulla").exists()


# --- dopo il lavoro -------------------------------------------------------------------


def test_senza_lavori_ultimo_render_lo_dice(cartella, chiamate):
    """Stato vuoto di Ultimo render."""
    riepilogo = _telecomando(cartella, chiamate).riepilogo()
    assert riepilogo.ultimo == tc.NESSUN_RENDER and not riepilogo.lavoro_attivo


def test_un_render_fatto_si_riassume_con_preset_modello_e_render(cartella, chiamate, vista):
    """Stato pieno di Ultimo render: preset e modello, crediti, il file del render."""
    _coda_che_batte(cartella)
    telecomando = _telecomando(cartella, chiamate)
    dove, _n, _c = telecomando.invio(_valori())
    telecomando.genera(vista, _valori(), dove)
    Coda(cartella, crea_provider=lambda _n: ProviderDiProva(chiamate), dire=lambda _t: None).esegui_uno()
    riepilogo = telecomando.riepilogo()
    assert riepilogo.stato == "Render pronto."
    assert riepilogo.ultimo.startswith("Rivista d'architettura · Nano Banana 2 · ")
    assert Path(riepilogo.render).is_file() and not riepilogo.lavoro_attivo


def test_un_errore_dice_il_fatto_e_rimanda_allo_studio(cartella, chiamate, vista):
    """Stato errore di DESIGN.md: la frase del motore, mai un codice da solo, e Apri nello Studio."""
    _coda_che_batte(cartella)
    telecomando = _telecomando(cartella, chiamate)
    dove, _n, _c = telecomando.invio(_valori())
    telecomando.genera(vista, _valori(), dove)
    Coda(cartella, crea_provider=lambda _n: ProviderDiProva(chiamate, errore=ErroreProvider("Il servizio ha rifiutato la vista.", "Riprova fra un minuto.")),
         dire=lambda _t: None).esegui_uno()
    riepilogo = telecomando.riepilogo()
    assert riepilogo.stato.startswith("Non e' andato: Il servizio ha rifiutato la vista.")
    assert "Riprova fra un minuto." in riepilogo.stato and "Apri nello Studio" in riepilogo.stato


@pytest.mark.parametrize("secondi, testo", [(0, "0:00"), (12, "0:12"), (75, "1:15"), (None, "un tempo che non so dire")])
def test_il_tempo_in_corso_si_scrive_come_nel_mockup(secondi, testo):
    assert tc.durata(secondi) == testo


# --- processi ---------------------------------------------------------------------------


class Sistema:
    """Un Windows finto: quali programmi ci sono e cosa rispondono."""

    def __init__(self, risposte: dict[str, str]):
        self.risposte = risposte
        self.lanciati: list[dict] = []
        self.eseguiti: list[dict] = []

    def trova(self, nome):
        return {"py": "C:/Windows/py.exe", "msedge": None}.get(nome)

    def esegui(self, comando, **opzioni):
        self.eseguiti.append({"comando": comando, **opzioni})
        return SimpleNamespace(stdout=self.risposte.get(comando[0], ""), stderr="")

    def lancia(self, comando, **opzioni):
        self.lanciati.append({"comando": comando, **opzioni})


def _avviatore(cartella, sistema, tmp_path, **altro):
    allplan = tmp_path / "Allplan" / "Python"
    allplan.mkdir(parents=True)
    (allplan / "python.exe").write_text("")
    return tc.Avviatore(
        cartella, tmp_path / "script",
        prefissi=[str(allplan)], eseguibile="C:/Allplan/Allplan.exe",
        cartella_pillow="C:/Usr/PythonParts-site-packages",
        ambiente={"PYTHONHOME": "C:/Allplan/Python", "PATH": "x"},
        trova=sistema.trova, esegui=sistema.esegui, lancia=sistema.lancia,
        aspetta=lambda _s: None, **altro,
    ), str(allplan / "python.exe")


def test_il_python_di_allplan_con_pillow_vince_e_vede_la_cartella_di_pillow(cartella, tmp_path):
    """Caso: il Python di Allplan fuori da Allplan non trova Pillow e lo Studio muore all'avvio."""
    sistema = Sistema({})
    avviatore, python_allplan = _avviatore(cartella, sistema, tmp_path)
    sistema.risposte[python_allplan] = f"3.11.9|{python_allplan}|True"
    origine, comando, ambiente = avviatore.python()
    assert comando == [python_allplan] and "Allplan" in origine
    assert ambiente["PYTHONPATH"].startswith("C:/Usr/PythonParts-site-packages")
    # Senza console Windows scriverebbe in cp1252: la freccia «→» faceva fallire il lavoro.
    assert ambiente["PYTHONIOENCODING"] == "utf-8"


def test_senza_pillow_si_passa_al_python_di_sistema_senza_le_variabili_di_allplan(cartella, tmp_path):
    """Caso: py di sistema eredita PYTHONHOME di Allplan e non parte."""
    sistema = Sistema({"C:/Windows/py.exe": "3.12.1|C:/Python312/python.exe|True"})
    avviatore, python_allplan = _avviatore(cartella, sistema, tmp_path)
    sistema.risposte[python_allplan] = f"3.11.9|{python_allplan}|False"
    origine, comando, ambiente = avviatore.python()
    assert comando == ["C:/Windows/py.exe", "-3"] and "sistema" in origine
    assert "PYTHONHOME" not in ambiente and "PYTHONPATH" not in ambiente
    assert ambiente["PYTHONIOENCODING"] == "utf-8"


def test_allplan_exe_non_si_lancia_mai(cartella, tmp_path):
    """Caso: sys.executable dentro Allplan e' Allplan.exe, e lanciarlo apre un secondo Allplan."""
    sistema = Sistema({})
    avviatore, _p = _avviatore(cartella, sistema, tmp_path)
    with pytest.raises(tc.PythonNonTrovato) as errore:
        avviatore.python()
    assert all("Allplan.exe" not in e["comando"][0] for e in sistema.eseguiti)
    assert "pip install pillow" in errore.value.cosa_fare


def test_assicura_coda_avvia_lo_studio_senza_finestra_e_aspetta_il_battito(cartella, tmp_path):
    """Caso: la palette lancia lo Studio e dice «fatto» prima di sapere se la coda c'e'."""
    sistema = Sistema({"C:/Windows/py.exe": "3.12.1|C:/Python312/python.exe|True"})
    avviatore, python_allplan = _avviatore(cartella, sistema, tmp_path)
    sistema.risposte[python_allplan] = "niente"
    originale = sistema.lancia

    def lancia(comando, **opzioni):
        originale(comando, **opzioni)
        _coda_che_batte(cartella)

    avviatore._lancia = lancia  # pylint: disable=protected-access
    avviatore.assicura_coda()
    lancio = sistema.lanciati[0]
    assert lancio["comando"][-5:] == ["-m", "core.studio", "--cartella", str(cartella), "--senza-finestra"]
    assert lancio["cwd"] == str(tmp_path / "script") and lancio["stdin"] == subprocess.DEVNULL
    avviatore.assicura_coda()
    assert len(sistema.lanciati) == 1, "con la coda viva non si lancia un secondo Studio"


def test_assicura_coda_dice_se_il_battito_non_arriva(cartella, tmp_path):
    """Stato errore: lo Studio lanciato non parte, e la palette dice come lanciarlo a mano."""
    sistema = Sistema({"C:/Windows/py.exe": "3.12.1|C:/Python312/python.exe|True"})
    orologio = iter(range(0, 1000))
    avviatore, _p = _avviatore(cartella, sistema, tmp_path, orologio=lambda: next(orologio))
    with pytest.raises(tc.StudioNonPartito) as errore:
        avviatore.assicura_coda()
    assert f"{config.PALETTE_SECONDI_ATTESA_STUDIO} secondi" in errore.value.fatto
    assert "core.studio" in errore.value.cosa_fare


def test_apri_studio_riapre_quello_che_gira_invece_di_avviarne_un_altro(cartella, tmp_path):
    """Caso: ogni clic su Apri nello Studio avvia un server in piu'."""
    sistema = Sistema({})
    aperti = []
    avviatore, _p = _avviatore(cartella, sistema, tmp_path, apri_url=aperti.append, esiste=lambda _p: False)
    battito.scrivi(battito.percorso(cartella, battito.FILE_STUDIO), {"indirizzo": "http://127.0.0.1:5000/"})
    assert "browser predefinito" in avviatore.apri_studio()
    assert aperti == ["http://127.0.0.1:5000/"] and not sistema.lanciati


def test_apri_studio_usa_edge_in_modalita_app_se_c_e(cartella, tmp_path):
    sistema = Sistema({})
    avviatore, _p = _avviatore(cartella, sistema, tmp_path, esiste=lambda p: p.endswith("msedge.exe"))
    avviatore.ambiente["ProgramFiles"] = "C:/Program Files"
    battito.scrivi(battito.percorso(cartella, battito.FILE_STUDIO), {"indirizzo": "http://127.0.0.1:5000/"})
    avviatore.apri_studio()
    assert "--app=http://127.0.0.1:5000/" in sistema.lanciati[0]["comando"]


def test_apri_studio_senza_studio_lo_avvia_con_la_finestra(cartella, tmp_path):
    sistema = Sistema({"C:/Windows/py.exe": "3.12.1|C:/Python312/python.exe|True"})
    avviatore, _p = _avviatore(cartella, sistema, tmp_path)
    assert "Studio avviato" in avviatore.apri_studio()
    assert "--senza-finestra" not in sistema.lanciati[0]["comando"]


def test_lo_studio_vero_batte_con_il_suo_indirizzo_e_usa_la_coda_che_c_e(cartella, monkeypatch):
    """Caso: lo Studio lanciato dalla palette avvia una seconda coda accanto a quella che gira."""
    from core.studio import __main__ as principale

    _coda_che_batte(cartella)
    avviate = []
    monkeypatch.setattr(principale, "avvia_coda", avviate.append)
    letto = {}

    class Server:
        def serve_forever(self):
            letto.update(battito.leggi(battito.percorso(cartella, battito.FILE_STUDIO)) or {})
            raise KeyboardInterrupt

        def server_close(self):
            pass

    monkeypatch.setattr(principale, "crea_server", lambda _s, _p: Server())
    monkeypatch.setattr(principale, "indirizzo", lambda _s: "http://127.0.0.1:4321/")
    assert principale.main(["--cartella", str(cartella), "--senza-finestra"]) == 0
    assert not avviate
    assert letto["indirizzo"] == "http://127.0.0.1:4321/"
    assert not battito.percorso(cartella, battito.FILE_STUDIO).exists()


# --- formato fisso, verde e persone (2026-10-31) --------------------------------


def test_un_formato_fisso_manda_una_vista_tagliata_al_rapporto_esatto(cartella, chiamate, vista):
    """Caso: si sceglie 16:9 e parte la finestra intera, che poi torna di un'altra forma."""
    from core import immagine

    _coda_che_batte(cartella)
    (cartella / "vista-20261031-120000.camera.json").write_text("{}", encoding="utf-8")
    telecomando = _telecomando(cartella, chiamate)
    valori = _valori(formato="16:9")
    dove, _nota, _costo = telecomando.invio(valori)
    assert telecomando.genera(vista, valori, dove).startswith("In coda, verso ")
    tagliata = cartella / "vista-20261031-120000-16x9.png"
    assert immagine.dimensioni(tagliata.read_bytes()) == (640, 360)
    assert (cartella / "vista-20261031-120000-16x9.camera.json").is_file()
    lavoro = next((cartella / "lavori" / "in-attesa").glob("*.json")).read_text(encoding="utf-8")
    assert "vista-20261031-120000-16x9.png" in lavoro


def test_come_la_finestra_non_taglia_e_non_scrive_anteprime(cartella, chiamate, vista):
    telecomando = _telecomando(cartella, chiamate)
    assert telecomando.anteprima(vista, _valori()) == vista
    assert telecomando.vista_al_formato(vista, _valori()) == vista
    assert not (cartella / tc.CARTELLA_ANTEPRIME).exists()


def test_l_anteprima_del_taglio_sta_fuori_dalle_viste(cartella, chiamate, vista):
    """Caso: l'anteprima scurita finisce fra le viste dello Studio e qualcuno la manda."""
    telecomando = _telecomando(cartella, chiamate)
    anteprima = Path(telecomando.anteprima(vista, _valori(formato="9:16 verticale")))
    assert anteprima.parent == cartella / tc.CARTELLA_ANTEPRIME and anteprima.is_file()
    assert [v["nome"] for v in telecomando.studio.elenco_viste()] == ["vista-20261031-120000.png"]


def test_i_formati_della_palette_sono_i_rapporti_che_il_modello_accetta():
    from core.provider import comfy

    formati = tc.voci_palette()["Formato"]
    assert formati[0] == (None, tc.COME_LA_FINESTRA)
    assert [i for i, _n in formati[1:]] == list(comfy.RAPPORTI)


def test_verde_e_persone_della_palette_arrivano_nel_prompt():
    """Caso: «come aggiungo alberi e persone?» e la palette non lo permette."""
    scelte = _valori(verde="Rigoglioso", persone="Poche").scelte()
    assert scelte.verde == "rigoglioso" and scelte.persone == "poche"
    interno = _valori(interno=True, verde="Rigoglioso", persone="In movimento").scelte()
    assert interno.persone == "movimento"
    assert interno.verde != "rigoglioso"  # il verde e' degli esterni, come nello Studio


def test_la_risoluzione_scelta_in_palette_arriva_al_modello(cartella, chiamate, vista):
    """Caso: si sceglie 4K e il modello riceve la richiesta di sempre, a 1K (2026-10-31)."""
    _coda_che_batte(cartella)
    telecomando = _telecomando(cartella, chiamate)
    valori = _valori(risoluzione="4K · da provare")
    assert valori.scelte().risoluzione == "4k"
    assert _valori().scelte().risoluzione == "1k"
    dove, _nota, _costo = telecomando.invio(valori)
    telecomando.genera(vista, valori, dove)
    Coda(cartella, crea_provider=lambda _n: ProviderDiProva(chiamate), dire=lambda _t: None).esegui_uno()
    assert chiamate[0].dimensione_render == "4k"
