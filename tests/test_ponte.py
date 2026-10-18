"""Il ponte fra palette e motore, provato senza Allplan."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from conftest import vista_shaded, vista_wireframe

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "allplan" / "comune"))

import ponte  # noqa: E402  pylint: disable=wrong-import-position


def test_una_cattura_non_sovrascrive_mai_una_vista(tmp_path):
    """Caso: due catture nello stesso secondo, la prima andrebbe persa."""
    adesso = datetime(2026, 10, 18, 14, 30, 0)
    primo = ponte.percorso_vista(tmp_path, adesso)
    primo.write_bytes(b"x")
    secondo = ponte.percorso_vista(tmp_path, adesso)
    assert primo != secondo
    assert not secondo.exists()


def test_la_camera_si_salva_accanto_alla_vista(tmp_path):
    """Caso: la vista arriva al render ma nessuno sa piu' da dove era guardata."""
    vista = tmp_path / "vista-1.png"
    camera = {"occhio": [1.0, 2.0, 3.0], "angolo": "errore: non disponibile"}
    percorso = ponte.scrivi_camera(vista, camera)
    assert percorso.name == "vista-1.camera.json"
    assert json.loads(percorso.read_text(encoding="utf-8")) == camera


def test_la_palette_parte_sempre_a_secco_se_non_chiede_altro(tmp_path):
    """Caso: un clic sbagliato fa partire un'immagine sotto NDA."""
    argomenti = ponte.argomenti_motore(tmp_path / "v.png")
    assert "--prova-a-secco" in argomenti
    assert "--prova-a-secco" not in ponte.argomenti_motore(tmp_path / "v.png", a_secco=False)


def test_la_prova_a_secco_dice_dove_andrebbe_l_immagine(tmp_path):
    """Caso: la palette mostra un risultato ma non dice a chi lo manderebbe."""
    vista = tmp_path / "vista.png"
    vista.write_bytes(vista_shaded())
    codice, testo = ponte.esegui_motore(ponte.argomenti_motore(vista, testo="piu' caldo"))
    assert codice == 0
    assert ponte.destinazione_predefinita() in testo
    assert "non ho inviato niente" in testo


def test_un_rifiuto_arriva_alla_palette_in_italiano(tmp_path):
    """Caso: il motore scarta un wireframe e la palette resta muta."""
    vista = tmp_path / "vista.png"
    vista.write_bytes(vista_wireframe())
    codice, testo = ponte.esegui_motore(ponte.argomenti_motore(vista))
    assert codice != 0
    assert "Cosa fare" in testo


def test_un_argomento_sbagliato_non_chiude_allplan(tmp_path):
    """Caso: argparse chiama sys.exit, e dentro Allplan sys.exit fa danni."""
    codice, _testo = ponte.esegui_motore(["--opzione-che-non-esiste"])
    assert codice != 0
