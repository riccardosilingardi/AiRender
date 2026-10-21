"""Il confronto affiancato di due modelli, provato senza rete."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from conftest import (
    TrasportoComfyFinto,
    provider_comfy,
    router_in_coda,
    router_risultato,
    router_stato,
    schema_di_prova,
    vista_shaded,
    vista_wireframe,
)
from core.errori import ImmagineNonIdonea
from core.provider import comfy

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import confronta_modelli as confronto  # noqa: E402  pylint: disable=wrong-import-position

MODELLI = ("prova/kontext", "prova/banana")


@pytest.fixture
def due_modelli_verificati(monkeypatch):
    for modello in MODELLI:
        monkeypatch.setitem(comfy.SCHEMI, modello, schema_di_prova())


def lancia(tmp_path, trasporto, *altri):
    vista = tmp_path / "vista.png"
    if not vista.exists():
        vista.write_bytes(vista_shaded(1200, 675))
    righe = []
    argomenti = confronto.costruisci_parser().parse_args(
        ["--immagine", str(vista), "--modelli", *MODELLI, "--uscita", str(tmp_path / "esito"), *altri]
    )
    codice = confronto.esegui(
        argomenti, dire=righe.append, crea_motore=lambda: provider_comfy(trasporto)
    )
    return codice, "\n".join(righe)


def test_prima_di_partire_dice_dove_vanno_tutti_e_due_gli_invii(tmp_path):
    """Caso: due invii a pagamento sotto NDA. Si leggono entrambe le destinazioni prima."""
    trasporto = TrasportoComfyFinto()
    codice, uscita = lancia(tmp_path, trasporto, "--prova-a-secco")
    assert codice == 0
    for modello in MODELLI:
        assert f"Comfy Router (api.comfy.org) → {modello}" in uscita
    assert trasporto.chiamate == []
    assert uscita.count("non e' ancora stato verificato") == 2


def test_lascia_due_render_con_ricetta_e_il_confronto(tmp_path, due_modelli_verificati):
    """Caso: si giudicano gli spigoli a occhio, ma ogni render deve potersi rifare."""
    giro = [router_in_coda(), router_stato("COMPLETED"), router_risultato()]
    trasporto = TrasportoComfyFinto(giro * 2, immagine=vista_shaded(800, 450))
    codice, uscita = lancia(tmp_path, trasporto)
    esito = tmp_path / "esito"
    assert codice == 0
    for modello in MODELLI:
        nome = modello.replace("/", "_")
        assert (esito / f"vista-{nome}.png").exists()
        assert (esito / f"vista-{nome}.png.ricetta.json").exists()
    assert (esito / "vista-confronto.png").exists()
    assert "non misurato" in uscita


def test_se_il_secondo_modello_fallisce_il_primo_render_non_si_perde(tmp_path, monkeypatch):
    """Caso: il primo invio e' gia' pagato. Buttarlo per colpa del secondo e' spreco."""
    monkeypatch.setitem(comfy.SCHEMI, MODELLI[0], schema_di_prova())
    giro = [router_in_coda(), router_stato("COMPLETED"), router_risultato()]
    trasporto = TrasportoComfyFinto(giro, immagine=vista_shaded(800, 450))
    codice, uscita = lancia(tmp_path, trasporto)
    assert codice != 0
    assert (tmp_path / "esito" / "vista-prova_kontext.png").exists()
    assert (tmp_path / "esito" / "vista-confronto.png").exists()
    assert "prova/banana: non riuscito" in uscita


def test_una_vista_inadatta_si_ferma_prima_dei_due_invii(tmp_path):
    """Caso: due chiamate pagate per due edifici inventati da un wireframe."""
    (tmp_path / "vista.png").write_bytes(vista_wireframe())
    trasporto = TrasportoComfyFinto()
    with pytest.raises(ImmagineNonIdonea) as errore:
        lancia(tmp_path, trasporto)
    assert "wireframe" in str(errore.value)
    assert trasporto.chiamate == []
