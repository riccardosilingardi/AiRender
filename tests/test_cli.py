"""La riga di comando vista da chi la usa.

Nessuna rete: il provider e' finto e registrato al volo, esattamente come
farebbe un secondo motore immagine vero.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import vista_shaded, vista_wireframe
from core import provider as registro
from core.preset import elenco, preset
from core.cli import (
    USCITA_CONFIGURAZIONE,
    USCITA_OK,
    USCITA_PROVIDER,
    USCITA_RIFIUTO,
    main,
)
from core.provider.base import Provider, Risultato
from core.ricetta import Ricetta, impronta


class ProviderDiProva(Provider):
    """Un motore che non esce di casa e racconta cosa gli hanno chiesto."""

    nome = "prova"
    destinazione = "Servizio di prova (niente rete)"
    chiamate: list[str] = []

    def genera(self, richiesta):
        type(self).chiamate.append("genera")
        return Risultato(
            immagine=b"render-finto",
            formato="png",
            ricetta=self._ricetta(richiesta.immagine, richiesta),
            scostamento_geometria=None,
            avvisi=["Scostamento della geometria non misurato."],
        )

    def modifica_regione(self, richiesta):
        type(self).chiamate.append("modifica_regione")
        raise NotImplementedError

    def riesegui(self, ricetta, immagine):
        type(self).chiamate.append("riesegui")
        return Risultato(b"render-rifatto", "png", ricetta, None, [])

    @staticmethod
    def _ricetta(dati, richiesta) -> Ricetta:
        return Ricetta(
            provider=ProviderDiProva.nome,
            modello=richiesta.modello,
            preset=richiesta.preset,
            preset_versione=richiesta.preset_versione,
            prompt=richiesta.prompt,
            testo_utente=richiesta.testo_utente,
            grana=richiesta.grana,
            dettaglio_grana=richiesta.dettaglio_grana,
            forza_struttura=richiesta.forza_struttura,
            risoluzione=richiesta.risoluzione,
            aspetto="standard_3_2",
            generazione_fissa=richiesta.generazione_fissa,
            impronta_sorgente=impronta(dati),
        )


@pytest.fixture
def motore_di_prova(monkeypatch):
    ProviderDiProva.chiamate = []
    monkeypatch.setitem(registro.REGISTRO, ProviderDiProva.nome, ProviderDiProva)
    # Come farebbe un motore vero: ogni preset dice quale modello usare con lui.
    for p in elenco():
        monkeypatch.setitem(p.modelli, ProviderDiProva.nome, "modello-di-prova")
    return ProviderDiProva


@pytest.fixture
def vista(tmp_path) -> Path:
    percorso = tmp_path / "vista.png"
    percorso.write_bytes(vista_shaded(1200, 800))
    return percorso


def test_elenca_i_preset_inclusi_senza_chiedere_niente(capsys):
    """Caso: l'utente non sa cosa scrivere dopo --preset."""
    assert main(["--elenca-preset"]) == USCITA_OK
    uscita = capsys.readouterr().out
    assert "base" in uscita and "Esterno giorno" in uscita


def test_dice_dove_manda_l_immagine_prima_di_mandarla(motore_di_prova, vista, capsys):
    """Caso: il pubblico lavora sotto NDA. Il nome del servizio si legge prima."""
    codice = main(
        ["--immagine", str(vista), "--provider", "prova", "--prova-a-secco"]
    )
    uscita = capsys.readouterr().out
    assert codice == USCITA_OK
    assert "Servizio di prova" in uscita
    assert uscita.index("Destinazione dell'invio") < uscita.index("non ho inviato niente")
    assert motore_di_prova.chiamate == []


def test_la_prova_a_secco_mostra_il_prompt_che_partirebbe(motore_di_prova, vista, capsys):
    """Caso: si vuole vedere cosa parte senza pagare la chiamata."""
    main([
        "--immagine", str(vista), "--provider", "prova", "--preset", "esterno-giorno",
        "--testo", "piu' caldo, mattone vecchio", "--grana", "grossa", "--prova-a-secco",
    ])
    uscita = capsys.readouterr().out
    assert "mattone vecchio" in uscita
    assert "coarse-grained" in uscita
    assert "grana grossa" in uscita


def test_una_generazione_lascia_il_render_e_la_sua_ricetta(motore_di_prova, vista, tmp_path, capsys):
    """Caso: il risultato non e' un PNG, e' un livello che si sa rifare."""
    destinazione = tmp_path / "render.png"
    codice = main([
        "--immagine", str(vista), "--provider", "prova", "--uscita", str(destinazione),
    ])
    assert codice == USCITA_OK
    assert destinazione.read_bytes() == b"render-finto"
    ricetta = json.loads(
        (tmp_path / "render.png.ricetta.json").read_text(encoding="utf-8")
    )
    assert ricetta["preset"] == "base"
    assert ricetta["preset_versione"] == preset("base").versione
    assert ricetta["modello"] == "modello-di-prova"
    assert ricetta["impronta_sorgente"] == impronta(vista.read_bytes())
    assert "Scostamento della geometria: non misurato." in capsys.readouterr().out


def test_un_wireframe_viene_fermato_e_l_utente_sa_cosa_risalvare(vista, capsys, tmp_path):
    """Caso: si salva la vista di lavoro invece della shaded."""
    sbagliata = tmp_path / "linee.png"
    sbagliata.write_bytes(vista_wireframe())
    codice = main(["--immagine", str(sbagliata)])
    catturato = capsys.readouterr()
    assert codice == USCITA_RIFIUTO
    assert "wireframe" in catturato.err
    assert "Salva contenuto finestra come immagine" in catturato.err


def test_l_opzione_scala_viene_rifiutata_con_la_sua_ragione(capsys):
    """Caso: l'utente cerca uno slider di scala che non esistera' mai."""
    codice = main(["--immagine", "x.png", "--scala", "3"])
    assert codice == USCITA_RIFIUTO
    assert "--grana" in capsys.readouterr().err


def test_senza_chiave_si_ferma_e_dice_dove_metterla(vista, capsys):
    """Caso: prima esecuzione, chiave non ancora configurata."""
    codice = main(["--immagine", str(vista)])
    assert codice == USCITA_CONFIGURAZIONE
    assert "COMFY_API_KEY" in capsys.readouterr().err


def test_la_prova_a_secco_predefinita_dice_comfy_router_e_il_modello(vista, capsys):
    """Caso: il servizio predefinito e' cambiato. L'utente deve leggerlo prima, col modello."""
    codice = main(["--immagine", str(vista), "--prova-a-secco"])
    uscita = capsys.readouterr().out
    assert codice == USCITA_OK
    modello = preset("base").modello_per("comfy")
    assert f"Destinazione dell'invio: Comfy Router (api.comfy.org) → {modello}." in uscita
    assert uscita.index("Destinazione dell'invio") < uscita.index("non ho inviato niente")


def test_la_prova_a_secco_avvisa_se_l_invio_vero_si_fermera(vista, capsys):
    """Caso: la prova a secco dice "tutto bene" e l'invio vero poi si rifiuta."""
    main(["--immagine", str(vista), "--prova-a-secco"])
    assert "non e' ancora stato verificato" in capsys.readouterr().out


def test_con_comfy_la_forza_non_si_stampa_come_un_numero(vista, capsys):
    """Caso: 70 a schermo per un parametro che non parte e' un valore inventato."""
    main(["--immagine", str(vista), "--prova-a-secco"])
    uscita = capsys.readouterr().out
    assert "Forza della struttura: non usata" in uscita
    assert "Forza della struttura: 70" not in uscita


def test_forza_struttura_chiesta_a_comfy_viene_rifiutata_con_la_ragione(vista, capsys):
    """Caso: l'utente regola una forza che il modello ignorerebbe in silenzio."""
    codice = main(["--immagine", str(vista), "--forza-struttura", "90", "--prova-a-secco"])
    errore = capsys.readouterr().err
    assert codice == USCITA_RIFIUTO
    assert "--provider magnific" in errore


def test_un_preset_che_non_esiste_elenca_quelli_che_esistono(vista, capsys):
    """Caso: un refuso nel nome del preset."""
    codice = main(["--immagine", str(vista), "--preset", "notturno"])
    assert codice == USCITA_RIFIUTO
    assert "esterno-giorno" in capsys.readouterr().err


def test_rifare_un_livello_passa_dalla_ricetta_non_dal_prompt(motore_di_prova, vista, tmp_path, capsys):
    """Caso: si rifa' un livello di ieri. I parametri sono quelli di ieri."""
    destinazione = tmp_path / "render.png"
    main(["--immagine", str(vista), "--provider", "prova", "--uscita", str(destinazione)])
    capsys.readouterr()

    ricetta = tmp_path / "render.png.ricetta.json"
    codice = main([
        "--rifai", str(ricetta), "--immagine", str(vista),
        "--uscita", str(tmp_path / "rifatto.png"),
    ])
    assert codice == USCITA_OK
    assert "riesegui" in motore_di_prova.chiamate
    assert (tmp_path / "rifatto.png").read_bytes() == b"render-rifatto"
    uscita = capsys.readouterr().out
    assert "non garantisce un'immagine identica" in uscita


def test_senza_vista_di_partenza_lo_dice_invece_di_partire(capsys):
    """Caso: si lancia il comando nudo."""
    assert main([]) == USCITA_CONFIGURAZIONE
    assert "--immagine" in capsys.readouterr().out


def test_il_file_che_non_esiste_non_diventa_un_traceback(capsys):
    """Caso: percorso sbagliato, il caso piu' comune di tutti."""
    codice = main(["--immagine", "/non/esiste/vista.png"])
    assert codice in (USCITA_RIFIUTO, USCITA_PROVIDER)
    assert "Non ho trovato" in capsys.readouterr().err
