"""La tabella dei materiali: elenco letto alla cattura, cambi scelti nello Studio, coda, prompt.

Nessuna rete e nessun Allplan. Il .surf finto e' un TIFF, come quelli veri
della 2027 (27 .surf del progetto 4253, 2026-11-02).
"""

from __future__ import annotations

import io
import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

from conftest import vista_shaded
from core import blocchi, config, coda as modulo_coda, materiali as modulo_materiali
from core.coda import Coda, LavoroNonValido, leggi_stato, metti_in_coda
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

RADICE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RADICE / "allplan" / "comune"))

import materiali_allplan  # noqa: E402  pylint: disable=wrong-import-position

NANO = MODELLI[0].identificativo
KONTEXT = MODELLI[1].identificativo
LETTORE = (RADICE / "allplan" / "v2027" / "pacchetto" / "PythonPartsScripts" / "riccardo_silingardi"
           / "airender" / "lettore_materiali.py")


class ProviderConPiuImmagini(ProviderDiProva):
    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _surf(colore=(200, 40, 40)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (120, 120), colore).save(uscita, format="TIFF")
    return uscita.getvalue()


def _jpeg(colore=(180, 120, 60)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (300, 200), colore).save(uscita, "JPEG")
    return uscita.getvalue()


MURO = {"GetDisplayName": "'Strato parete'",
        "attributi": {"335": "'design\\\\mattone.surf'", "508": "'Laterizio'"}, "superficie": {}}
PILASTRO = {"GetDisplayName": "Pilastro", "attributi": {"508": "CLS"}, "superficie": {}}
FACCIATA = {"GetDisplayName": "Sub-elemento facciata", "attributi": {}, "superficie": {}}


@pytest.fixture
def chiamate():
    return []


@pytest.fixture
def cartella(tmp_path) -> Path:
    """La cartella delle viste, con una vista e i suoi materiali letti dalla palette."""
    viste = tmp_path / "viste"
    viste.mkdir()
    vista = viste / "vista-1.png"
    vista.write_bytes(vista_shaded(640, 400))
    progetto = tmp_path / "Prj"
    (progetto / "design").mkdir(parents=True)
    (progetto / "design" / "mattone.surf").write_bytes(_surf())
    materiali_allplan.scrivi_per_vista(vista, [MURO, MURO, PILASTRO, FACCIATA], [progetto], "2026-11-02T15:00:00")
    return viste


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova",
                  crea_provider=lambda _nome: ProviderConPiuImmagini(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _richiesta(studio, materiali, modello=NANO):
    cambi = studio._cambi_scelti({"vista": "vista-1.png", "materiali": materiali})  # pylint: disable=protected-access
    destinazione = studio.destinazione(modello, materiali_immagini=modulo_materiali.quante_immagini(cambi))
    return {"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista").a_dizionario(),
            "preset": "rivista", "modello": modello,
            "destinazione_mostrata": destinazione["destinazione"], "materiali": materiali}


# --- lettura alla cattura (senza Allplan) ---------------------------------------


def test_l_elenco_ha_un_materiale_per_riga_il_piu_usato_primo_e_l_anteprima_del_surf(cartella):
    elenco = modulo_materiali.leggi_elenco(cartella / "vista-1.png")
    assert [(m.nome, m.elementi) for m in elenco["materiali"]] == [("mattone", 2), ("CLS", 1)]
    mattone, cls = elenco["materiali"]
    assert mattone.chiave == "design\\mattone.surf"
    assert cls.anteprima is None  # 508 e' solo un nome: nessun .surf, nessuna anteprima
    with Image.open(modulo_materiali.cartella_anteprime(cartella) / mattone.anteprima) as anteprima:
        assert anteprima.format == "PNG" and anteprima.getpixel((5, 5)) == (200, 40, 40)
    assert elenco["senza_materiale"] == ["Sub-elemento facciata 1"]
    assert elenco["errore"] is None


def test_un_errore_di_lettura_si_scrive_e_non_diventa_un_elenco_vuoto_muto(tmp_path):
    vista = tmp_path / "v.png"
    materiali_allplan.scrivi_errore(vista, "RuntimeError: documento assente", "2026-11-02T15:00:00")
    elenco = modulo_materiali.leggi_elenco(vista)
    assert elenco["materiali"] == [] and "documento assente" in elenco["errore"]
    assert modulo_materiali.leggi_elenco(tmp_path / "mai-letta.png") is None


def test_si_leggono_al_massimo_per_tipo_e_si_salta_il_2d():
    nomi = ["Linea"] * 10 + ["Sub-elemento facciata"] * 500 + ["Parete"] * 3
    scelti = materiali_allplan.scegli_elementi(nomi, per_tipo=150, massimo=4000)
    assert len(scelti) == 153 and all(nomi[i] != "Linea" for i in scelti)


def test_l_anteprima_si_chiede_solo_per_nome_nella_sua_cartella(cartella):
    for nome in ("../vista-1.png", "a/b.png", ".nascosto", ""):
        with pytest.raises(modulo_materiali.MaterialeNonValido):
            modulo_materiali.controlla_anteprima(cartella, nome)


def test_il_lettore_di_allplan_non_scrive_niente_in_allplan():
    """Regola di Riccardo del 2026-11-02: solo lettura."""
    testo = LETTORE.read_text(encoding="utf-8")
    for scrittura in ("ModifySurface", "CreateSurface", "ModifyElements", "CreateElements",
                      "SetAttributes", "DeleteElements", "SetTextureID", "ChangeAttribute"):
        assert not re.search(rf"\b{scrittura}\(", testo), scrittura
    assert "NemAll_Python" not in (RADICE / "allplan" / "comune" / "materiali_allplan.py").read_text("utf-8")
    assert "NemAll_Python" not in (RADICE / "core" / "materiali.py").read_text("utf-8")


# --- cambi e prompt ---------------------------------------------------------------


def test_un_cambio_senza_cosa_diventa_si_rifiuta_con_la_ragione():
    with pytest.raises(modulo_materiali.MaterialeNonValido, match="manca cosa deve diventare"):
        modulo_materiali.Cambio("mattone", "   ")


def test_oltre_il_massimo_o_doppi_si_rifiuta():
    troppi = tuple(modulo_materiali.Cambio(f"m{i}", "x") for i in range(config.MATERIALI_CAMBIATI_MASSIMI + 1))
    with pytest.raises(modulo_materiali.MaterialeNonValido):
        modulo_materiali.controlla_cambi(troppi)
    with pytest.raises(modulo_materiali.MaterialeNonValido):
        modulo_materiali.controlla_cambi((modulo_materiali.Cambio("a", "x"), modulo_materiali.Cambio("a", "y")))


def test_il_prompt_numera_le_immagini_dopo_la_vista_e_il_riferimento():
    cambi = (modulo_materiali.Cambio("mattone", "corten", "a.png", "b.jpg"),
             modulo_materiali.Cambio("CLS", "legno di larice"))
    testo = modulo_materiali.prompt("Base.", cambi, prima_immagine=modulo_materiali.prima_immagine(True))
    assert testo.startswith("Base. Material changes.")
    assert "Image 3 is a sample of the material «mattone»" in testo
    assert "Image 4 is a photo of the new material" in testo
    assert "«CLS» (no sample available) become: legno di larice" in testo
    assert modulo_materiali.prima_immagine(False) == 2
    assert modulo_materiali.quante_immagini(cambi) == 2
    assert modulo_materiali.prompt("Base.", (), 2) == "Base."


# --- Studio e coda ------------------------------------------------------------------


def test_lo_studio_da_la_tabella_con_le_anteprime_servite_dallo_studio(cartella, chiamate):
    tabella = _studio(cartella, chiamate).materiali_della_vista("vista-1.png")
    assert tabella["letti"] and tabella["massimo"] == config.MATERIALI_CAMBIATI_MASSIMI
    assert tabella["materiali"][0]["anteprima"].startswith("/file/materiale/")
    assert tabella["materiali"][1]["anteprima"] is None


def test_senza_lettura_lo_studio_lo_dice_e_non_inventa_materiali(tmp_path, chiamate):
    viste = tmp_path / "viste"
    viste.mkdir()
    (viste / "vista-1.png").write_bytes(vista_shaded(640, 400))
    tabella = _studio(viste, chiamate).materiali_della_vista("vista-1.png")
    assert tabella["letti"] is False and tabella["materiali"] == []


def test_un_materiale_che_la_palette_non_ha_letto_si_rifiuta(cartella, chiamate):
    """Caso: la pagina manda una chiave o un percorso inventato."""
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida):
        studio._cambi_scelti({"vista": "vista-1.png",  # pylint: disable=protected-access
                              "materiali": [{"chiave": "C:\\Windows\\win.ini", "diventa": "x"}]})


def test_genera_con_i_materiali_manda_vista_anteprima_e_foto_nell_ordine_del_prompt(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    foto = _jpeg()
    rif = studio.carica_riferimento(foto)["nome"]
    scelti = [{"chiave": "design\\mattone.surf", "diventa": "acciaio corten", "riferimento": rif},
              {"chiave": "CLS", "diventa": "cemento sabbiato"}]
    secco = studio.prova_a_secco(_richiesta(studio, scelti))
    assert secco["problemi"] == [] and secco["destinazione"]["immagini"] == 3
    risposta = studio.invia(_richiesta(studio, scelti))
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json")
                         .read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_MATERIALI
    assert [m["nome"] for m in scritto["materiali"]] == ["mattone", "CLS"]

    Coda(cartella, crea_provider=lambda _n: ProviderConPiuImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "fatto"
    (richiesta,) = chiamate
    anteprima, seconda = richiesta.immagini_in_piu
    assert seconda == foto
    with Image.open(io.BytesIO(anteprima)) as immagine:
        assert immagine.getpixel((5, 5)) == (200, 40, 40)
    assert "Image 2 is a sample of the material «mattone»" in richiesta.prompt
    assert "Image 3 is a photo of the new material" in richiesta.prompt
    assert "«CLS» (no sample available) become: cemento sabbiato" in richiesta.prompt


def test_con_un_modello_a_una_sola_immagine_i_materiali_non_partono(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    scelti = [{"chiave": "design\\mattone.surf", "diventa": "corten"}]
    assert studio.destinazione(KONTEXT, materiali_immagini=1)["materiali_non_accettati"]
    with pytest.raises((RichiestaStudioNonValida, LavoroNonValido)):
        studio.invia(_richiesta(studio, scelti, modello=KONTEXT))
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_i_materiali_non_partono_da_un_passo(cartella, chiamate):
    vista = cartella / "vista-1.png"
    with pytest.raises(LavoroNonValido):
        metti_in_coda(cartella, vista, blocchi.da_preset("rivista"), provider="prova", modello=NANO,
                      parte_da="x", partenza=vista,
                      materiali=(modulo_materiali.Cambio("CLS", "legno"),),
                      crea_provider=lambda _n: ProviderConPiuImmagini([]))


def test_un_lavoro_del_formato_6_senza_materiali_si_rifiuta():
    with pytest.raises(LavoroNonValido):
        modulo_coda.Lavoro.da_dizionario({
            "formato": modulo_coda.FORMATO_MATERIALI, "identificativo": "x", "vista": "v.png",
            "provider": "prova", "modello": NANO, "destinazione": "d",
        })


# --- materiali scelti sulla vista (selezione libera, senza Allplan) -------------


def test_il_campione_dalla_vista_ha_una_frase_sua_e_il_flusso_allplan_resta_uguale():
    dalla_vista = modulo_materiali.Cambio("materiale 1", "lamiera grecata", "c.png", "r.jpg", dalla_vista=True)
    allplan = modulo_materiali.Cambio("mattone", "corten", "a.png")
    testo = modulo_materiali.prompt("Base.", (dalla_vista, allplan), prima_immagine=2)
    assert "Image 2 is a crop of image 1 that shows the material «materiale 1»" in testo
    assert "Image 3 is a photo of the new material" in testo
    assert "Image 4 is a sample of the material «mattone» as the CAD model shows it" in testo
    assert "dalla_vista" not in allplan.a_dizionario()
    assert modulo_materiali.Cambio.da_dizionario(dalla_vista.a_dizionario()) == dalla_vista


def test_genera_con_un_materiale_scelto_sulla_vista_manda_il_ritaglio(tmp_path, chiamate):
    """Caso web app: la vista non ha l'elenco di Allplan, il campione e' un ritaglio salvato fra i riferimenti."""
    viste = tmp_path / "viste"
    viste.mkdir()
    (viste / "vista-1.png").write_bytes(vista_shaded(640, 400))
    studio = _studio(viste, chiamate)
    campione = studio.carica_riferimento(_jpeg((90, 90, 200)))["nome"]
    foto = _jpeg((20, 140, 60))
    rif = studio.carica_riferimento(foto)["nome"]
    scelti = [{"campione": campione, "diventa": "lamiera grecata", "riferimento": rif}]
    assert studio.prova_a_secco(_richiesta(studio, scelti))["destinazione"]["immagini"] == 3
    risposta = studio.invia(_richiesta(studio, scelti))
    scritto = json.loads((viste / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json").read_text("utf-8"))
    assert scritto["materiali"][0]["dalla_vista"] is True

    Coda(viste, crea_provider=lambda _n: ProviderConPiuImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert leggi_stato(viste, risposta["identificativo"])["stato"] == "fatto"
    (richiesta,) = chiamate
    ritaglio, seconda = richiesta.immagini_in_piu
    assert seconda == foto
    with Image.open(io.BytesIO(ritaglio)) as immagine:
        assert abs(immagine.getpixel((5, 5))[2] - 200) < 10
    assert "Image 2 is a crop of image 1 that shows the material «materiale 1»" in richiesta.prompt
    assert "becomes: lamiera grecata" in richiesta.prompt


def test_un_campione_che_non_e_fra_i_riferimenti_si_rifiuta(tmp_path, chiamate):
    viste = tmp_path / "viste"
    viste.mkdir()
    (viste / "vista-1.png").write_bytes(vista_shaded(640, 400))
    studio = _studio(viste, chiamate)
    with pytest.raises(Exception):
        studio._cambi_scelti({"vista": "vista-1.png",  # pylint: disable=protected-access
                              "materiali": [{"campione": "../../win.ini", "diventa": "x"}]})
