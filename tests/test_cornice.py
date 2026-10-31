"""La cornice: una vista di qualunque forma parte al rapporto che il modello
accetta e torna con i pixel esatti della vista (Allplan 2027, 2026-10-31:
una vista 1165x715 e' tornata 3:2 e lo Studio l'ha stirata del 9,3%)."""

from __future__ import annotations

import io

from PIL import Image

from core import immagine as modulo
from core.provider.base import RichiestaGenerazione
from core.provider.comfy import con_cornice, rapporto_piu_vicino


def vista(larghezza: int, altezza: int, colore=(200, 60, 40)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (larghezza, altezza), colore).save(uscita, format="PNG")
    return uscita.getvalue()


def _richiesta(dati: bytes, *in_piu: bytes) -> RichiestaGenerazione:
    return RichiestaGenerazione(immagine=dati, prompt="p", preset="x", preset_versione="1",
                                modello="m", grana="", dettaglio_grana=0, immagini_in_piu=in_piu)


def test_la_vista_di_riccardo_parte_esattamente_3_2_e_torna_1165x715():
    richiesta, cornice = con_cornice(_richiesta(vista(1165, 715)))
    l, a = modulo.dimensioni(richiesta.immagine)
    assert rapporto_piu_vicino(richiesta.immagine) == "3:2"
    assert abs(l / a - 1.5) < 0.002
    assert cornice is not None and cornice.alto > 0 and cornice.sinistra == 0

    # Il modello rimanda un'altra grandezza con lo stesso rapporto (1264x848):
    # la parte della vista e' rossa, la cornice blu.
    tela = Image.new("RGB", (1264, 848), (0, 0, 255))
    alto = round(cornice.alto * 848)
    basso = 848 - round(cornice.basso * 848)
    tela.paste(Image.new("RGB", (1264, basso - alto), (200, 60, 40)), (0, alto))
    uscita = io.BytesIO()
    tela.save(uscita, format="PNG")
    tagliato = modulo.togli_cornice(uscita.getvalue(), cornice)
    assert modulo.dimensioni(tagliato) == (1165, 715)
    with Image.open(io.BytesIO(tagliato)) as im:
        assert im.convert("RGB").getpixel((582, 2))[2] < 120  # niente blu della cornice in alto
        assert im.convert("RGB").getpixel((582, 712))[2] < 120


def test_una_vista_stretta_si_allarga_ai_lati_e_la_banda_continua_il_bordo():
    dati, cornice = modulo.allarga_a_rapporto(vista(600, 1000, (10, 200, 10)), 3 / 4)
    with Image.open(io.BytesIO(dati)) as im:
        assert abs(im.width / im.height - 0.75) < 0.002
        assert im.convert("RGB").getpixel((0, 500)) == (10, 200, 10)
    assert cornice.sinistra > 0 and cornice.alto == 0


def test_le_immagini_in_piu_della_stessa_misura_si_allargano_uguali():
    maschera = vista(1165, 715, (255, 255, 255))
    richiesta, _ = con_cornice(_richiesta(vista(1165, 715), maschera))
    assert modulo.dimensioni(richiesta.immagini_in_piu[0]) == modulo.dimensioni(richiesta.immagine)
