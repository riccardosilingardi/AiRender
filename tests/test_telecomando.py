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
from core.coda import coda_viva
from core.studio.servizio import Studio
from test_coda import ProviderDiProva

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "allplan" / "comune"))

import telecomando as tc  # noqa: E402  pylint: disable=wrong-import-position

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


def _coda_che_batte(cartella):
    battito.scrivi(battito.percorso(cartella, battito.FILE_CODA), {})


# --- vista -----------------------------------------------------------------


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


# --- formato fisso: si taglia alla cattura (2026-11-04) ----------------------


def test_un_formato_fisso_taglia_la_vista_catturata_al_rapporto_esatto(cartella, chiamate, vista):
    """Caso: si sceglie 16:9 e nello Studio arriva la finestra intera, che poi torna di un'altra forma."""
    from core import immagine

    telecomando = _telecomando(cartella, chiamate)
    assert telecomando.taglia_cattura(vista, tc.ValoriPalette(formato="16:9"))
    assert immagine.dimensioni(Path(vista).read_bytes()) == (640, 360)
    assert [v["nome"] for v in telecomando.studio.elenco_viste()] == ["vista-20261031-120000.png"]


def test_come_la_finestra_non_taglia_e_non_scrive_anteprime(cartella, chiamate, vista):
    telecomando = _telecomando(cartella, chiamate)
    assert not telecomando.taglia_cattura(vista, tc.ValoriPalette())
    assert telecomando.anteprima(vista) == vista
    assert not (cartella / tc.CARTELLA_ANTEPRIME).is_dir() or not any((cartella / tc.CARTELLA_ANTEPRIME).iterdir())


def test_l_anteprima_del_taglio_sta_fuori_dalle_viste_e_mostra_la_finestra_intera(cartella, chiamate, vista):
    """Caso: l'anteprima scurita finisce fra le viste dello Studio e qualcuno la manda."""
    from core import immagine

    telecomando = _telecomando(cartella, chiamate)
    telecomando.taglia_cattura(vista, tc.ValoriPalette(formato="9:16 verticale"))
    anteprima = Path(telecomando.anteprima(vista))
    assert anteprima.parent == cartella / tc.CARTELLA_ANTEPRIME
    assert immagine.dimensioni(anteprima.read_bytes()) == (640, 400)
    assert [v["nome"] for v in telecomando.studio.elenco_viste()] == ["vista-20261031-120000.png"]


def test_una_cattura_nuova_senza_formato_non_mostra_il_taglio_di_prima(cartella, chiamate, vista):
    telecomando = _telecomando(cartella, chiamate)
    telecomando.taglia_cattura(vista, tc.ValoriPalette(formato="1:1 quadrato"))
    Path(vista).write_bytes(vista_shaded(640, 400))
    telecomando.taglia_cattura(vista, tc.ValoriPalette())
    assert telecomando.anteprima(vista) == vista


def test_i_formati_della_palette_sono_i_rapporti_che_il_modello_accetta():
    from core.provider import comfy

    formati = tc.voci_palette()["Formato"]
    assert formati[0] == (None, tc.COME_LA_FINESTRA)
    assert [i for i, _n in formati[1:]] == list(comfy.RAPPORTI)


def test_un_formato_che_il_motore_non_conosce_dice_di_reinstallare():
    with pytest.raises(blocchi.SceltaNonValida, match="Reinstalla"):
        tc.ValoriPalette(formato="7:5 strano").rapporto()
