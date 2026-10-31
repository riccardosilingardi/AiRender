"""La coda dei lavori su cartella.

Nessuna rete: il provider e' finto, come in test_cli.py. Si controlla quello
che palette e Studio leggeranno: le cartelle, lo stato, i messaggi.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import vista_shaded, vista_wireframe
from core import coda as modulo_coda
from core.blocchi import VERSIONE, da_preset
from core.coda import Coda, chiedi_annullamento, leggi_stato, metti_in_coda
from core.errori import ErroreProvider
from core.provider.base import IN_LAVORAZIONE, INVIATO, Provider, Risultato
from core.ricetta import Ricetta, impronta


class ProviderDiProva(Provider):
    """Un servizio che non esce di casa. Racconta cosa ha visto, e puo' fallire a comando."""

    nome = "prova"
    destinazione = "Servizio di prova (niente rete)"
    usa_forza_struttura = False

    def __init__(self, registro_chiamate, errore=None, durante=None, eco=False):
        self.registro = registro_chiamate
        self.errore = errore
        self.durante = durante
        self.eco = eco  # rimanda la vista com'e': un render vero, che si puo' misurare

    def destinazione_per(self, modello):
        return f"{self.destinazione} → {modello}"

    def genera(self, richiesta):
        self.registro.append(richiesta)
        self._segnala(INVIATO)
        if self.durante:
            self.durante()
        self._segnala(IN_LAVORAZIONE)
        if self.errore:
            raise self.errore
        return Risultato(
            immagine=richiesta.immagine if self.eco else b"render-finto",
            formato="png",
            ricetta=Ricetta(
                provider=self.nome, modello=richiesta.modello, preset=richiesta.preset,
                preset_versione=richiesta.preset_versione, prompt=richiesta.prompt,
                testo_utente=richiesta.testo_utente, grana=richiesta.grana,
                dettaglio_grana=None, forza_struttura=None, risoluzione="", aspetto="",
                generazione_fissa=False, impronta_sorgente=impronta(richiesta.immagine),
            ),
            avvisi=["Scostamento della geometria non misurato."],
        )

    def modifica_regione(self, richiesta):
        raise NotImplementedError

    def riesegui(self, ricetta, immagine):
        raise NotImplementedError


@pytest.fixture
def chiamate():
    return []


@pytest.fixture
def radice(tmp_path) -> Path:
    return tmp_path / "AIRENDER"


@pytest.fixture
def vista(tmp_path) -> Path:
    percorso = tmp_path / "vista.png"
    percorso.write_bytes(vista_shaded(640, 400))
    return percorso


def _crea(chiamate, **opzioni):
    return lambda _nome: ProviderDiProva(chiamate, **opzioni)


def _in_coda(radice, vista, chiamate, stile="ora-blu", **altro):
    return metti_in_coda(
        radice, vista, da_preset(stile, materiali="intonaco a calce bianco"),
        preset=stile, provider="prova", modello="modello-di-prova",
        crea_provider=_crea(chiamate), **altro,
    )


def _coda(radice, chiamate, **opzioni):
    detti = []
    return Coda(radice, crea_provider=_crea(chiamate, **opzioni), dire=detti.append), detti


def _lavori(radice, cartella):
    return sorted(p.name for p in (radice / "lavori" / cartella).iterdir())


# --- un lavoro che arriva ----------------------------------------------------


def test_un_lavoro_nasce_in_coda_con_la_destinazione_gia_scritta(radice, vista, chiamate):
    """Caso: la palette scrive il lavoro e l'utente non ha ancora letto dove va (regola 5)."""
    lavoro = _in_coda(radice, vista, chiamate)
    scritto = json.loads(
        (radice / "lavori" / "in-attesa" / f"{lavoro.identificativo}.json").read_text("utf-8")
    )
    assert scritto["destinazione"] == "Servizio di prova (niente rete) → modello-di-prova"
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "in coda"
    assert stato["destinazione"] == scritto["destinazione"]
    assert chiamate == []


def test_un_lavoro_arriva_e_lascia_render_ricetta_e_stato_fatto(radice, vista, chiamate):
    """Caso: il render c'e' ma nessuno sa dove, ne' come rifarlo."""
    lavoro = _in_coda(radice, vista, chiamate)
    coda, detti = _coda(radice, chiamate)
    assert coda.esegui_uno() == lavoro.identificativo

    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "fatto"
    render = Path(stato["render"])
    assert render.read_bytes() == b"render-finto"
    assert render.parent == radice / "lavori" / "fatto"
    ricetta = json.loads(Path(stato["ricetta"]).read_text("utf-8"))
    assert ricetta["preset"] == "ora-blu" and ricetta["preset_versione"] == VERSIONE
    assert ricetta["prompt"].startswith("Edit this exact image.")
    assert "Materials: intonaco a calce bianco." in ricetta["prompt"]
    assert stato["scostamento_geometria"] is None
    assert _lavori(radice, "in-attesa") == [] and _lavori(radice, "in-corso") == []
    assert f"{lavoro.identificativo}.json" in _lavori(radice, "fatto")
    assert any("destinazione dell'invio" in d for d in detti)


def test_lo_stato_passa_da_in_coda_a_inviato_a_in_lavorazione_a_fatto(radice, vista, chiamate, monkeypatch):
    """Caso: lo Studio mostra "in coda" mentre il servizio sta gia' lavorando."""
    lavoro = _in_coda(radice, vista, chiamate)
    visti = []
    originale = modulo_coda.scrivi_stato

    def spia(radice_, identificativo, stato, **altro):
        visti.append(stato)
        return originale(radice_, identificativo, stato, **altro)

    monkeypatch.setattr(modulo_coda, "scrivi_stato", spia)
    _coda(radice, chiamate)[0].esegui_uno()
    assert visti == ["inviato", "in lavorazione", "fatto"]
    assert leggi_stato(radice, lavoro.identificativo)["stato"] == "fatto"


def test_il_prompt_scritto_a_mano_parte_al_posto_dei_blocchi(radice, vista, chiamate):
    """Caso: l'utente ha modificato il prompt completo e partono i blocchi."""
    _in_coda(radice, vista, chiamate, prompt_a_mano="Edit this image. My own words.")
    _coda(radice, chiamate)[0].esegui_uno()
    assert chiamate[0].prompt == "Edit this image. My own words."


# --- errori ------------------------------------------------------------------


def test_un_errore_del_servizio_finisce_in_errore_in_italiano_con_cosa_fare(radice, vista, chiamate):
    """Caso: il credito e' finito e lo Studio mostra un codice HTTP."""
    lavoro = _in_coda(radice, vista, chiamate)
    errore = ErroreProvider(
        "Comfy Router dice che i crediti del workspace sono finiti.",
        "Ricarica i crediti del workspace, poi rilancia.",
        stato=402,
    )
    _coda(radice, chiamate, errore=errore)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore"
    assert stato["fatto"].startswith("Comfy Router dice")
    assert stato["cosa_fare"].startswith("Ricarica")
    assert "402" not in stato["fatto"] + stato["cosa_fare"]
    assert f"{lavoro.identificativo}.json" in _lavori(radice, "errore")


def test_una_vista_non_adatta_non_parte_e_dice_cosa_risalvare(radice, tmp_path, chiamate):
    """Caso: un wireframe va in coda e si paga un render inutile."""
    wire = tmp_path / "wire.png"
    wire.write_bytes(vista_wireframe(640, 400))
    lavoro = _in_coda(radice, wire, chiamate)
    _coda(radice, chiamate)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore"
    assert stato["cosa_fare"]
    assert chiamate == []


def test_una_vista_sparita_dice_dove_la_cercava(radice, vista, chiamate):
    """Caso: la vista e' stata spostata fra la coda e l'invio."""
    lavoro = _in_coda(radice, vista, chiamate)
    vista.unlink()
    _coda(radice, chiamate)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore" and stato["cosa_fare"]
    assert chiamate == []


def test_se_la_destinazione_cambiata_non_parte_niente(radice, vista, chiamate):
    """Caso: l'utente ha letto una destinazione e l'immagine ne raggiunge un'altra."""
    lavoro = _in_coda(radice, vista, chiamate)
    percorso = radice / "lavori" / "in-attesa" / f"{lavoro.identificativo}.json"
    dati = json.loads(percorso.read_text("utf-8"))
    dati["destinazione"] = "Un altro servizio"
    percorso.write_text(json.dumps(dati), encoding="utf-8")
    _coda(radice, chiamate)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore"
    assert "Non ho inviato niente" in stato["fatto"]
    assert chiamate == []


def test_un_json_rotto_va_in_errore_e_la_coda_va_avanti(radice, vista, chiamate):
    """Caso: un file scritto a meta' ferma il processo e i lavori dopo restano li'."""
    (radice / "lavori" / "in-attesa").mkdir(parents=True)
    (radice / "lavori" / "in-attesa" / "00000000-rotto.json").write_text('{"formato": 1, "vi', "utf-8")
    buono = _in_coda(radice, vista, chiamate)
    coda, _ = _coda(radice, chiamate)
    assert coda.gira(una_volta=True) == 2
    rotto = leggi_stato(radice, "00000000-rotto")
    assert rotto["stato"] == "errore"
    assert "non e' un JSON leggibile" in rotto["fatto"]
    assert "Rimetti il lavoro in coda" in rotto["cosa_fare"]
    assert leggi_stato(radice, buono.identificativo)["stato"] == "fatto"


def test_un_lavoro_di_un_altro_formato_si_rifiuta_con_cosa_fare(radice, vista, chiamate):
    lavoro = _in_coda(radice, vista, chiamate)
    percorso = radice / "lavori" / "in-attesa" / f"{lavoro.identificativo}.json"
    dati = json.loads(percorso.read_text("utf-8"))
    dati["formato"] = 99
    percorso.write_text(json.dumps(dati), encoding="utf-8")
    _coda(radice, chiamate)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore" and "Aggiorna il motore" in stato["cosa_fare"]


def test_un_imprevisto_non_ferma_il_processo(radice, vista, chiamate):
    """Caso: un'eccezione qualunque e la coda muore con i lavori dentro."""
    primo = _in_coda(radice, vista, chiamate)
    secondo = _in_coda(radice, vista, chiamate)
    coda, _ = _coda(radice, chiamate, errore=RuntimeError("boh"))
    assert coda.gira(una_volta=True) == 2
    assert leggi_stato(radice, primo.identificativo)["stato"] == "errore"
    assert "imprevisto" in leggi_stato(radice, secondo.identificativo)["fatto"]


# --- annullamento ------------------------------------------------------------


def test_annullato_prima_dell_invio_non_parte_niente(radice, vista, chiamate):
    """Caso: l'utente annulla subito, e la vista parte lo stesso."""
    lavoro = _in_coda(radice, vista, chiamate)
    chiedi_annullamento(radice, lavoro.identificativo)
    _coda(radice, chiamate)[0].esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "annullato"
    assert "non e' partita" in stato["fatto"]
    assert chiamate == []
    assert _lavori(radice, "annullato") == [f"{lavoro.identificativo}.json"]
    assert _lavori(radice, "in-attesa") == []


def test_annullato_durante_l_attesa_dice_che_puo_essere_addebitato(radice, vista, chiamate):
    """Caso: si annulla mentre il servizio lavora e si crede di non aver speso niente."""
    lavoro = _in_coda(radice, vista, chiamate)
    coda, _ = _coda(
        radice, chiamate, durante=lambda: chiedi_annullamento(radice, lavoro.identificativo)
    )
    coda.esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "annullato"
    assert "addebitarla" in stato["fatto"]
    assert "crediti" in stato["cosa_fare"]
    assert not list((radice / "lavori").rglob("*.annulla"))
    assert not list((radice / "lavori" / "fatto").glob("*.png"))


# --- due lavori, riavvio ----------------------------------------------------


def test_due_lavori_in_fila_si_fanno_nell_ordine_in_cui_sono_nati(radice, vista, chiamate):
    """Caso: il secondo lavoro passa davanti al primo."""
    primo = _in_coda(radice, vista, chiamate, stile="rivista")
    secondo = _in_coda(radice, vista, chiamate, stile="notte-luna")
    coda, _ = _coda(radice, chiamate)
    assert coda.esegui_uno() == primo.identificativo
    assert leggi_stato(radice, secondo.identificativo)["stato"] == "in coda"
    assert coda.esegui_uno() == secondo.identificativo
    assert coda.esegui_uno() is None
    assert [c.preset for c in chiamate] == ["rivista", "notte-luna"]


def test_al_riavvio_un_lavoro_non_ancora_partito_torna_in_coda(radice, vista, chiamate):
    """Caso: il processo muore subito dopo aver preso il lavoro, e il lavoro resta perso."""
    lavoro = _in_coda(radice, vista, chiamate)
    nome = f"{lavoro.identificativo}.json"
    (radice / "lavori" / "in-attesa" / nome).rename(radice / "lavori" / "in-corso" / nome)
    coda, detti = _coda(radice, chiamate)
    assert coda.gira(una_volta=True) == 1
    assert leggi_stato(radice, lavoro.identificativo)["stato"] == "fatto"
    assert any("torna in coda" in d for d in detti)


def test_al_riavvio_un_lavoro_gia_inviato_non_si_rimanda_da_solo(radice, vista, chiamate):
    """Caso: il processo muore durante l'attesa e al riavvio la stessa vista si paga due volte."""
    lavoro = _in_coda(radice, vista, chiamate)
    nome = f"{lavoro.identificativo}.json"
    (radice / "lavori" / "in-attesa" / nome).rename(radice / "lavori" / "in-corso" / nome)
    modulo_coda.scrivi_stato(radice, lavoro.identificativo, "in lavorazione")
    coda, _ = _coda(radice, chiamate)
    assert coda.gira(una_volta=True) == 0
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore"
    assert "in lavorazione" in stato["fatto"]
    assert "crediti" in stato["cosa_fare"]
    assert chiamate == []


# --- scrittura atomica --------------------------------------------------------


def test_chi_legge_non_vede_mai_un_file_a_meta(tmp_path, monkeypatch):
    """Caso: lo Studio legge lo stato mentre il processo lo scrive e trova mezzo JSON."""
    destinazione = tmp_path / "stato.json"
    modulo_coda.scrivi_json(destinazione, {"stato": "in coda"})

    def rinomina_rotta(_da, _a):
        raise OSError("disco pieno")

    monkeypatch.setattr(modulo_coda.os, "replace", rinomina_rotta)
    with pytest.raises(OSError):
        modulo_coda.scrivi_json(destinazione, {"stato": "fatto", "molto": "x" * 10000})
    assert json.loads(destinazione.read_text("utf-8")) == {"stato": "in coda"}
    assert [p.name for p in tmp_path.iterdir()] == ["stato.json"]


def test_i_file_temporanei_non_sono_lavori(radice, vista, chiamate):
    """Caso: la coda prende un file ancora in scrittura."""
    cartella = radice / "lavori" / "in-attesa"
    cartella.mkdir(parents=True)
    (cartella / ".20261028-x.json.123.ab.tmp").write_text("{", "utf-8")
    (cartella / ".nascosto.json").write_text("{", "utf-8")
    coda, _ = _coda(radice, chiamate)
    assert coda.esegui_uno() is None


# --- riga di comando ---------------------------------------------------------


def test_la_riga_di_comando_mette_in_coda_e_dice_la_destinazione(radice, vista, capsys):
    """Caso: provare la coda senza Studio, e la destinazione non si legge da nessuna parte."""
    codice = modulo_coda.main([
        "--cartella", str(radice), "--aggiungi", str(vista), "--stile", "ora-blu",
        "--materiali", "intonaco bianco",
    ])
    uscita = capsys.readouterr().out
    assert codice == 0
    assert "Destinazione dell'invio: Comfy Router (api.comfy.org) → vertexai/gemini-3.1-flash-image" in uscita
    assert len(_lavori(radice, "in-attesa")) == 1


def test_la_riga_di_comando_rifiuta_uno_stile_sconosciuto_con_cosa_fare(radice, vista, capsys):
    codice = modulo_coda.main(["--cartella", str(radice), "--aggiungi", str(vista), "--stile", "x"])
    assert codice == 2
    assert "Cosa fare:" in capsys.readouterr().err


def test_la_riga_di_comando_annulla_un_lavoro(radice, vista, chiamate):
    lavoro = _in_coda(radice, vista, chiamate)
    assert modulo_coda.main(["--cartella", str(radice), "--annulla", lavoro.identificativo]) == 0
    assert (radice / "lavori" / "in-attesa" / f"{lavoro.identificativo}.annulla").exists()


def test_senza_chiave_lo_stato_non_dice_mai_inviato(radice, vista, monkeypatch):
    """Caso: lo Studio scrive «inviato» per una vista che non e' mai partita."""
    from core.provider import comfy

    visti = []
    originale = modulo_coda.scrivi_stato

    def spia(radice_, identificativo, stato, **altro):
        visti.append(stato)
        return originale(radice_, identificativo, stato, **altro)

    monkeypatch.setattr(modulo_coda, "scrivi_stato", spia)
    lavoro = metti_in_coda(radice, vista, da_preset("rivista"))
    Coda(radice, dire=lambda _t: None).esegui_uno()
    stato = leggi_stato(radice, lavoro.identificativo)
    assert stato["stato"] == "errore"
    assert comfy.VARIABILI_CHIAVE[0] in stato["cosa_fare"]
    assert "inviato" not in visti


def test_dire_sicuro_non_fa_fallire_un_lavoro_su_una_uscita_cp1252(monkeypatch):
    """Caso vero (Allplan 2027, 2026-10-31): coda senza console su Windows, la
    freccia della destinazione in cp1252 sollevava UnicodeEncodeError."""
    import io

    from core import coda as modulo

    grezzo = io.BytesIO()
    uscita = io.TextIOWrapper(grezzo, encoding="cp1252")
    monkeypatch.setattr(modulo.sys, "stdout", uscita)
    modulo.dire_sicuro("Lavoro x: destinazione Comfy Router (api.comfy.org) → vertexai/gemini")
    uscita.flush()
    assert "Comfy Router (api.comfy.org) ? vertexai" in grezzo.getvalue().decode("cp1252")


def test_dire_sicuro_senza_uscita_non_solleva(monkeypatch):
    from core import coda as modulo

    monkeypatch.setattr(modulo.sys, "stdout", None)
    modulo.dire_sicuro("→")
