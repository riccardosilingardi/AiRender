"""Il rifiuto numero due: quel parametro si chiama grana, e non cambiera' nome.

Promettere la scala metrica dei materiali e' una bugia che il cliente
verifica con un metro in mano. Il divieto vale sulle nostre parole, non su
quelle dell'utente: in italiano "scala" e' anche il vano scala.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core import grana
from core.errori import ParametroVietato
from core.lessico import controlla_etichetta, rifiuta_opzione_scala
from core.preset import Preset, elenco
from core.prompt import componi

RADICE = Path(__file__).resolve().parent.parent


def test_una_nostra_etichetta_che_dice_scala_non_passa():
    """Caso: qualcuno chiama "scala materiali" lo slider della grana."""
    with pytest.raises(ParametroVietato) as errore:
        controlla_etichetta("Scala dei materiali", "lo slider")
    assert "grana" in errore.value.cosa_fare


def test_un_preset_che_promette_i_millimetri_non_si_lascia_costruire():
    """Caso: una descrizione di preset che vende una precisione che non c'e'."""
    with pytest.raises(ParametroVietato):
        Preset(
            identificativo="finto",
            nome="Mattone in scala 1:100",
            descrizione="corsi in millimetri",
            modello="realism",
            prompt_tecnico="x",
        )


def test_opzione_scala_da_riga_di_comando_spiega_perche_non_esiste():
    """Caso: l'utente prova --scala perche' l'ha vista altrove."""
    with pytest.raises(ParametroVietato) as errore:
        rifiuta_opzione_scala(["--immagine", "v.png", "--scala=3"])
    assert "--grana" in errore.value.cosa_fare
    assert "metro" in errore.value.cosa_fare


def test_il_testo_libero_dell_utente_puo_dire_scala_perche_e_un_vano_scala():
    """Caso: un architetto scrive "scala interna in cemento". Non e' affar nostro."""
    prompt = componi(elenco()[0], "scala interna in cemento", grana.FINE)
    assert "scala interna in cemento" in prompt


def test_nessun_preset_incluso_promette_una_misura():
    """Caso: i preset del pacchetto sono la prima cosa che l'utente legge."""
    for preset in elenco():
        controlla_etichetta(preset.nome, preset.identificativo)
        controlla_etichetta(preset.descrizione, preset.identificativo)


def test_nessuna_opzione_del_motore_si_chiama_scala():
    """Caso: il nome del parametro si rifa' vivo in un'altra schermata."""
    opzioni = set()
    for file in (RADICE / "core").rglob("*.py"):
        opzioni |= set(re.findall(r'"--([a-zà-ù-]+)"', file.read_text(encoding="utf-8")))
    assert "scala" not in opzioni
    assert "grana" in opzioni
