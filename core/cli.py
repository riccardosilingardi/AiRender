"""La riga di comando del motore.

    python -m core.cli --image vista.png --preset base --testo "piu' caldo"

Gira senza Allplan, su qualunque macchina. E' voluto: e' l'unico modo per
misurare il motore.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config, grana as modulo_grana, immagine as modulo_immagine, provider as registro
from .errori import ChiaveMancante, ErroreAirender, ErroreProvider, ImmagineNonIdonea
from .idoneita import valuta
from .lessico import rifiuta_opzione_scala
from .preset import elenco, preset as trova_preset
from .prompt import componi
from .provider.base import RichiestaGenerazione
from .ricetta import Ricetta

USCITA_OK = 0  # numero-non-configurabile: convenzione della shell
USCITA_RIFIUTO = 2  # numero-non-configurabile: convenzione della shell
USCITA_PROVIDER = 3  # numero-non-configurabile: convenzione della shell
USCITA_CONFIGURAZIONE = 4  # numero-non-configurabile: convenzione della shell


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core.cli",
        description=(
            "Trasforma una vista shaded salvata da Allplan in un'immagine "
            "presentabile, senza cambiare la geometria."
        ),
    )
    parser.add_argument(
        "--immagine", "--image", dest="immagine",
        help="la vista salvata da Allplan (PNG o JPEG)",
    )
    parser.add_argument(
        "--preset", default="base", help="lo stile, fra quelli inclusi nel pacchetto"
    )
    parser.add_argument(
        "--testo", default="", help="due parole tue, in italiano, sul risultato che vuoi"
    )
    parser.add_argument(
        "--grana",
        choices=list(modulo_grana.LIVELLI),
        help=(
            "quanto e' minuta la texture. Non e' la scala metrica dei "
            "materiali: quella non la promettiamo"
        ),
    )
    parser.add_argument(
        "--forza-struttura", type=int, dest="forza",
        help=(
            "quanto il render resta attaccato alla vista "
            f"(predefinito: {config.costante('FORZA_STRUTTURA_PREDEFINITA').etichetta()})"
        ),
    )
    parser.add_argument("--uscita", help="dove salvare il render")
    parser.add_argument(
        "--provider", default=registro.PREDEFINITO, choices=registro.nomi(),
        help="quale servizio riceve l'immagine",
    )
    parser.add_argument(
        "--rifai", metavar="RICETTA.json",
        help="riesegue una generazione a parametri identici, dalla sua ricetta",
    )
    parser.add_argument(
        "--prova-a-secco", action="store_true", dest="secco",
        help="mostra cosa partirebbe e si ferma prima di inviare",
    )
    parser.add_argument(
        "--elenca-preset", action="store_true", dest="elenca",
        help="elenca i preset inclusi e si ferma",
    )
    return parser


def _scrivi(testo: str = "", flusso=None) -> None:
    print(testo, file=flusso or sys.stdout)


def _mostra_preset() -> int:
    for p in elenco():
        _scrivi(f"{p.identificativo}  —  {p.nome} (v{p.versione}, modello {p.modello})")
        _scrivi(f"    {p.descrizione}")
        _scrivi(f"    grana predefinita: {p.grana_predefinita}")
    return USCITA_OK


def _percorso_uscita(dato: str | None, sorgente: Path, formato: str) -> Path:
    if dato:
        return Path(dato)
    return sorgente.with_name(f"{sorgente.stem}-airender.{formato}")


def _salva(risultato, destinazione: Path) -> Path:
    destinazione.write_bytes(risultato.immagine)
    ricetta = destinazione.with_suffix(destinazione.suffix + ".ricetta.json")
    ricetta.write_text(risultato.ricetta.a_json(), encoding="utf-8")
    return ricetta


def _racconta(risultato, destinazione: Path, ricetta: Path) -> None:
    _scrivi(f"Render salvato in {destinazione}")
    _scrivi(f"Ricetta rieseguibile in {ricetta}")
    if risultato.scostamento_geometria is None:
        _scrivi("Scostamento della geometria: non misurato.")
    else:
        _scrivi(f"Scostamento della geometria: {risultato.scostamento_geometria:.1f}")
    for avviso in risultato.avvisi:
        _scrivi(f"Avviso: {avviso}")


def _annuncia_destinazione(motore, quante: int = 1) -> None:
    """Prima che qualcosa parta, si dice dove va. Sempre."""
    _scrivi(
        f"Destinazione dell'invio: {motore.destinazione}. "
        f"{quante} immagine lascia questa macchina."
    )


def esegui(argomenti, uscita_standard=None) -> int:
    def dire(testo=""):
        _scrivi(testo, uscita_standard)

    if argomenti.elenca:
        return _mostra_preset()

    if argomenti.rifai:
        return _riesegui(argomenti, dire)

    if not argomenti.immagine:
        dire("Manca la vista di partenza.")
        dire("Cosa fare: passa --immagine con il file salvato da Allplan.")
        return USCITA_CONFIGURAZIONE

    sorgente = Path(argomenti.immagine)
    dati = modulo_immagine.leggi(sorgente)
    statistiche = modulo_immagine.misura(dati)
    giudizio = valuta(statistiche)

    # Anche quando la scarta, l'interfaccia dice cosa ha visto: l'utente deve
    # capire perche', non trovarsi davanti un no.
    dire(
        f"Vista: {statistiche.larghezza}x{statistiche.altezza} px, "
        f"{statistiche.toni_distinti} livelli di grigio, "
        f"sfondo uniforme al {statistiche.quota_sfondo:.0%}."
    )
    if not giudizio.idonea:
        raise ImmagineNonIdonea(giudizio.fatto, giudizio.cosa_fare, giudizio.motivo or "")

    scelto = trova_preset(argomenti.preset)
    livello = modulo_grana.normalizza(argomenti.grana or scelto.grana_predefinita)
    forza = scelto.forza_struttura if argomenti.forza is None else argomenti.forza

    richiesta = RichiestaGenerazione(
        immagine=dati,
        prompt=componi(scelto, argomenti.testo, livello),
        preset=scelto.identificativo,
        preset_versione=scelto.versione,
        modello=scelto.modello,
        grana=livello,
        dettaglio_grana=modulo_grana.dettaglio(livello),
        testo_utente=argomenti.testo,
        forza_struttura=forza,
    )

    motore = registro.crea(argomenti.provider)
    dire(f"Preset: {scelto.nome} (v{scelto.versione})  ·  {modulo_grana.etichetta(livello)}")
    dire(f"Forza della struttura: {forza} — valore scelto, non ancora misurato.")
    _annuncia_destinazione(motore)

    if argomenti.secco:
        dire("Prova a secco: non ho inviato niente.")
        dire(f"Prompt che partirebbe: {richiesta.prompt}")
        return USCITA_OK

    risultato = motore.genera(richiesta)
    destinazione = _percorso_uscita(argomenti.uscita, sorgente, risultato.formato)
    percorso_ricetta = _salva(risultato, destinazione)
    _racconta(risultato, destinazione, percorso_ricetta)
    return USCITA_OK


def _riesegui(argomenti, dire) -> int:
    percorso = Path(argomenti.rifai)
    ricetta = Ricetta.da_json(percorso.read_text(encoding="utf-8"))
    if not argomenti.immagine:
        dire("Per rifare un livello serve anche la vista di partenza di allora.")
        dire("Cosa fare: passa --immagine con la stessa vista.")
        return USCITA_CONFIGURAZIONE

    sorgente = Path(argomenti.immagine)
    dati = modulo_immagine.leggi(sorgente)
    motore = registro.crea(ricetta.provider)

    dire(
        f"Rifaccio il livello: preset {ricetta.preset} v{ricetta.preset_versione}, "
        f"modello {ricetta.modello}, forza {ricetta.forza_struttura}, "
        f"grana {ricetta.grana}."
    )
    dire(
        "Il modello puo' essere cambiato sotto lo stesso nome: una riesecuzione "
        "identica nei parametri non garantisce un'immagine identica."
    )
    _annuncia_destinazione(motore)

    if argomenti.secco:
        dire("Prova a secco: non ho inviato niente.")
        return USCITA_OK

    risultato = motore.riesegui(ricetta, dati)
    destinazione = _percorso_uscita(argomenti.uscita, sorgente, risultato.formato)
    percorso_ricetta = _salva(risultato, destinazione)
    _racconta(risultato, destinazione, percorso_ricetta)
    return USCITA_OK


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        rifiuta_opzione_scala(argv)
        argomenti = costruisci_parser().parse_args(argv)
        return esegui(argomenti)
    except ImmagineNonIdonea as errore:
        _scrivi(str(errore), sys.stderr)
        return USCITA_RIFIUTO
    except ChiaveMancante as errore:
        _scrivi(str(errore), sys.stderr)
        return USCITA_CONFIGURAZIONE
    except ErroreProvider as errore:
        _scrivi(str(errore), sys.stderr)
        return USCITA_PROVIDER
    except ErroreAirender as errore:
        _scrivi(str(errore), sys.stderr)
        return USCITA_RIFIUTO


if __name__ == "__main__":
    raise SystemExit(main())
