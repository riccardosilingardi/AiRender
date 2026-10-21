"""Il rifiuto numero uno: una vista che non serve non parte.

Ogni test nomina cosa l'utente ha sbagliato a salvare, e controlla che il
messaggio glielo dica.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import vista_piatta, vista_shaded, vista_wireframe
from core import config, immagine
from core.errori import FileNonTrovato, ImmagineNonIdonea
from core.idoneita import (
    SEMBRA_WIREFRAME,
    TROPPO_PIATTA,
    TROPPO_PICCOLA,
    assicura_idonea,
    valuta,
)

# Export vero: Allplan 2026, modello BOSCO, finestra Animazione, 2026-10-21.
# E' uno solo dei dieci che servono (PRD, sezione 9).
VISTA_VERA = Path(__file__).parent / "dati" / "vista-20261021-093841.png"


def test_la_vista_vera_di_allplan_passa_tutte_e_tre_le_soglie():
    """Caso: un export vero, fatto giusto. Un falso rifiuto qui blocca chi non ha sbagliato."""
    statistiche = immagine.misura(immagine.leggi(VISTA_VERA))
    esito = valuta(statistiche)
    assert esito.idonea and esito.motivo is None
    assert statistiche.quota_sfondo < config.QUOTA_SFONDO_MASSIMA
    assert statistiche.toni_distinti >= config.TONI_DISTINTI_MINIMI
    assert statistiche.deviazione_luminanza >= config.DEVIAZIONE_LUMINANZA_MINIMA


def test_la_vista_vera_di_allplan_misura_ancora_come_il_2026_10_21():
    """Caso: si cambia il modo di misurare e le soglie non valgono piu' per gli export veri.

    Se questo test si rompe, le tre soglie vanno riguardate su questa vista
    prima di andare avanti, non ritoccate finche' il test torna verde.
    """
    statistiche = immagine.misura(immagine.leggi(VISTA_VERA))
    assert (statistiche.larghezza, statistiche.altezza) == (1536, 857)
    assert statistiche.quota_sfondo == pytest.approx(0.101, abs=0.001)
    assert statistiche.toni_distinti == 67
    assert statistiche.deviazione_luminanza == pytest.approx(35.4, abs=0.1)


def test_una_vista_shaded_con_le_ombre_passa():
    """Caso: quello che l'utente deve salvare. Deve passare senza discussioni."""
    esito = valuta(immagine.misura(vista_shaded()))
    assert esito.idonea and esito.motivo is None


def test_il_wireframe_viene_scartato_e_il_messaggio_dice_cosa_salvare():
    """Caso: l'utente salva la vista di lavoro a fil di ferro."""
    esito = valuta(immagine.misura(vista_wireframe()))
    assert esito.motivo == SEMBRA_WIREFRAME
    assert "wireframe" in esito.fatto
    assert "shaded" in esito.fatto or "shaded" in esito.cosa_fare
    assert "Salva contenuto finestra come immagine" in esito.cosa_fare


def test_la_vista_senza_ombre_viene_scartata_e_il_messaggio_parla_di_ombre():
    """Caso: shaded, ma con le ombre spente."""
    esito = valuta(immagine.misura(vista_piatta()))
    assert esito.motivo == TROPPO_PIATTA
    assert "ombre" in esito.cosa_fare


def test_la_miniatura_viene_scartata_con_le_sue_dimensioni_in_chiaro():
    """Caso: l'utente salva l'anteprima da 320 px e si chiede perche' viene male."""
    esito = valuta(immagine.misura(vista_shaded(320, 200)))
    assert esito.motivo == TROPPO_PICCOLA
    assert "320x200" in esito.fatto


def test_il_rifiuto_arriva_come_errore_con_il_motivo_attaccato():
    """Caso: chi chiama vuole fermarsi, non leggere un booleano."""
    with pytest.raises(ImmagineNonIdonea) as errore:
        assicura_idonea(immagine.misura(vista_wireframe()))
    assert errore.value.motivo == SEMBRA_WIREFRAME
    assert errore.value.cosa_fare


def test_un_file_che_non_esiste_dice_dove_ho_guardato():
    """Caso: il percorso e' sbagliato. Un traceback non e' una risposta."""
    with pytest.raises(FileNonTrovato) as errore:
        immagine.leggi("/cartella/che/non/esiste/vista.png")
    assert "vista.png" in errore.value.fatto
    assert "Salva contenuto finestra come immagine" in errore.value.cosa_fare


def test_un_file_che_non_e_un_immagine_lo_dice_senza_traceback():
    """Caso: si passa un .dwg o un .txt rinominato."""
    with pytest.raises(FileNonTrovato) as errore:
        immagine.misura(b"non sono un'immagine")
    assert "PNG" in errore.value.cosa_fare
