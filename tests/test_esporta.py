"""Esporta per il cliente (prompt 14): JPEG, PNG e PSD con un livello per passaggio.

Il PSD si rilegge con Pillow: niente librerie in piu', niente Photoshop.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from conftest import vista_shaded
from core import blocchi, esporta
from core.coda import Coda
from core.studio.servizio import MODELLI, Studio
from test_coda import ProviderDiProva

NANO = MODELLI[0].identificativo


def _png(colore, misura=(160, 90), testo: str | None = None) -> bytes:
    uscita = io.BytesIO()
    immagine = Image.new("RGB", misura, colore)
    if testo:
        from PIL.PngImagePlugin import PngInfo
        info = PngInfo()
        info.add_text("prompt", testo)
        immagine.save(uscita, "PNG", pnginfo=info)
    else:
        immagine.save(uscita, "PNG")
    return uscita.getvalue()


def _livello(psd: bytes, indice: int) -> Image.Image:
    """Il livello `indice` (1 = il piu' in basso). Pillow ignora seek(1) appena aperto: si passa dal 2."""
    immagine = Image.open(io.BytesIO(psd))
    immagine.seek(2 if indice == 1 else indice)
    if indice == 1:
        immagine.seek(1)
    return immagine.convert("RGB")


# --- motore ------------------------------------------------------------------


@pytest.mark.parametrize("formato,firma", [("jpg", b"\xff\xd8"), ("png", b"\x89PNG")])
def test_jpg_e_png_portano_solo_i_pixel(formato, firma):
    """Caso: il file per il cliente porta dentro il prompt (o una chiave) che il servizio ci aveva scritto."""
    dati = esporta.esporta(_png((10, 120, 200), testo="segreto: prompt e chiave"), formato)
    assert dati.startswith(firma)
    assert b"segreto" not in dati and b"prompt" not in dati
    assert Image.open(io.BytesIO(dati)).size == (160, 90)


def test_il_psd_ha_un_livello_per_passaggio_dal_basso_in_alto():
    psd = esporta.psd_a_livelli([
        ("Vista Allplan", _png((10, 20, 30), (200, 120))),
        ("1 · Rivista d'architettura", _png((200, 0, 0))),
        ("2 · più verde", _png((0, 200, 0))),
    ])
    immagine = Image.open(io.BytesIO(psd))
    assert immagine.format == "PSD" and immagine.size == (160, 90) and immagine.n_frames == 3
    assert immagine.convert("RGB").getpixel((5, 5)) == (0, 200, 0)  # la composita e' il render in cima
    assert [_livello(psd, i).getpixel((5, 5)) for i in (1, 2, 3)] == [(10, 20, 30), (200, 0, 0), (0, 200, 0)]
    assert all(_livello(psd, i).size == (160, 90) for i in (1, 2, 3))
    # il nome vero, con accenti e «·», sta nel blocco unicode che Photoshop legge
    assert "2 · più verde".encode("utf-16-be") in psd


def test_un_formato_che_non_esiste_si_rifiuta_con_quelli_possibili():
    with pytest.raises(esporta.EsportazioneNonValida) as errore:
        esporta.esporta(_png((0, 0, 0)), "tiff")
    assert "PSD" in errore.value.cosa_fare


def test_un_psd_senza_livelli_si_rifiuta():
    with pytest.raises(esporta.EsportazioneNonValida):
        esporta.psd_a_livelli([])


# --- Studio --------------------------------------------------------------------


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
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderDiProva(chiamate, eco=True),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _esegui(cartella, chiamate):
    Coda(cartella, crea_provider=lambda _n: ProviderDiProva(chiamate, eco=True), dire=lambda _t: None).esegui_uno()


def test_dal_render_di_un_passo_esce_un_psd_con_vista_e_passi(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    destinazione = studio.destinazione(NANO)["destinazione"]
    primo = studio.invia({"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista").a_dizionario(),
                          "preset": "rivista", "modello": NANO, "destinazione_mostrata": destinazione})
    _esegui(cartella, chiamate)
    secondo = studio.invia_passo({"vista": "vista-1.png", "da": primo["identificativo"], "modello": NANO,
                                  "testo": "due alberi davanti al fronte", "destinazione_mostrata": destinazione})
    _esegui(cartella, chiamate)

    esito = studio.esporta(secondo["identificativo"], {"formato": "psd"})
    assert esito["livelli"] == ["Vista Allplan", "1 · Rivista d'architettura", "2 · due alberi davanti al fronte"]
    file = Path(esito["file"])
    assert file.parent == cartella / "esportati" and file.name.startswith("vista-1-passo2-") and file.suffix == ".psd"
    assert Image.open(file).n_frames == 3

    jpg = studio.esporta(secondo["identificativo"], {"formato": "jpg"})
    assert Path(jpg["file"]).suffix == ".jpg" and jpg["livelli"] is None
    assert b"due alberi" not in Path(jpg["file"]).read_bytes()


def test_un_lavoro_senza_render_non_si_esporta(cartella, chiamate):
    from core.errori import FileNonTrovato

    studio = _studio(cartella, chiamate)
    destinazione = studio.destinazione(NANO)["destinazione"]
    lavoro = studio.invia({"vista": "vista-1.png", "scelte": blocchi.da_preset("rivista").a_dizionario(),
                           "preset": "rivista", "modello": NANO, "destinazione_mostrata": destinazione})
    with pytest.raises(FileNonTrovato):
        studio.esporta(lavoro["identificativo"], {"formato": "png"})
    assert not (cartella / "esportati").exists()
