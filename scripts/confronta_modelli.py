"""La stessa vista attraverso due modelli di Comfy Router, affiancate, per giudicare gli spigoli a occhio.

    python scripts/confronta_modelli.py --immagine vista.png
    python scripts/confronta_modelli.py --immagine vista.png \
        --modelli bfl/flux-kontext-pro vertexai/gemini-3.1-flash-image --prova-a-secco

Il motore non sa ancora misurare lo scostamento della geometria: questo
confronto e' il modo di guardarlo finche' non lo sa. Lascia nella cartella
d'uscita un render per modello con la sua ricetta accanto, e un'immagine
<vista>-confronto.png con vista di partenza e render affiancati alla stessa
altezza, ognuno con le sue proporzioni.

Ogni modello e' un invio a pagamento. Prima che parta qualcosa, si dice dove
va ogni invio.

Finche' un modello non ha lo schema verificato dalla sonda
(scripts/sonda_comfy.py), il suo invio si ferma prima di partire.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import grana as modulo_grana, immagine as modulo_immagine  # noqa: E402
from core.cli import (  # noqa: E402
    USCITA_OK,
    USCITA_PROVIDER,
    USCITA_RIFIUTO,
    _annuncia_destinazione,
    _salva,
)
from core.errori import ErroreAirender, ImmagineNonIdonea  # noqa: E402
from core.idoneita import valuta  # noqa: E402
from core.preset import preset as trova_preset  # noqa: E402
from core.prompt import componi  # noqa: E402
from core.provider.base import RichiestaGenerazione  # noqa: E402
from core.provider.comfy import ProviderComfy  # noqa: E402

MODELLI_PREDEFINITI = ("bfl/flux-kontext-pro", "vertexai/gemini-3.1-flash-image")


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/confronta_modelli.py",
        description="La stessa vista attraverso due modelli, affiancate.",
    )
    parser.add_argument("--immagine", required=True, help="la vista salvata da Allplan")
    parser.add_argument("--modelli", nargs=2, default=list(MODELLI_PREDEFINITI),
                        metavar=("MODELLO_A", "MODELLO_B"), help="due ID del Router")
    parser.add_argument("--preset", default="base", help="lo stile, uguale per i due modelli")
    parser.add_argument("--testo", default="", help="due parole tue, uguali per i due modelli")
    parser.add_argument("--uscita", help="cartella dei risultati (predefinita: quella della vista)")
    parser.add_argument("--prova-a-secco", action="store_true", dest="secco",
                        help="dice dove andrebbero i due invii e si ferma")
    return parser


def _nome_file(modello: str) -> str:
    return modello.replace("/", "_")


def esegui(argomenti, dire=print, crea_motore=ProviderComfy) -> int:
    sorgente = Path(argomenti.immagine)
    dati = modulo_immagine.leggi(sorgente)
    statistiche = modulo_immagine.misura(dati)
    giudizio = valuta(statistiche)
    dire(
        f"Vista: {statistiche.larghezza}x{statistiche.altezza} px, "
        f"{statistiche.toni_distinti} livelli di grigio, "
        f"sfondo uniforme al {statistiche.quota_sfondo:.0%}."
    )
    if not giudizio.idonea:
        raise ImmagineNonIdonea(giudizio.fatto, giudizio.cosa_fare, giudizio.motivo or "")

    scelto = trova_preset(argomenti.preset)
    livello = modulo_grana.normalizza(scelto.grana_predefinita)
    prompt = componi(scelto, argomenti.testo, livello)
    motore = crea_motore()
    cartella = Path(argomenti.uscita) if argomenti.uscita else sorgente.parent
    modelli = list(argomenti.modelli)

    dire(f"Preset: {scelto.nome} (v{scelto.versione})  ·  {modulo_grana.etichetta(livello)}")
    dire(f"La stessa vista parte {len(modelli)} volte, una per modello:")
    for modello in modelli:
        _annuncia_destinazione(motore, modello, dire)

    if argomenti.secco:
        dire("Prova a secco: non ho inviato niente.")
        for modello in modelli:
            mancante = motore.cosa_manca(modello)
            if mancante:
                dire(f"Attenzione: {mancante}")
        return USCITA_OK

    cartella.mkdir(parents=True, exist_ok=True)
    pannelli = [("Vista di partenza", dati)]
    falliti = 0
    for modello in modelli:
        richiesta = RichiestaGenerazione(
            immagine=dati,
            prompt=prompt,
            preset=scelto.identificativo,
            preset_versione=scelto.versione,
            modello=modello,
            grana=livello,
            dettaglio_grana=modulo_grana.dettaglio(livello),
            testo_utente=argomenti.testo,
        )
        try:
            risultato = motore.genera(richiesta)
        except ErroreAirender as errore:
            # Il primo modello e' gia' stato pagato: non si butta per colpa del secondo.
            dire(f"{modello}: non riuscito.\n{errore}")
            falliti += 1
            continue
        destinazione = cartella / f"{sorgente.stem}-{_nome_file(modello)}.{risultato.formato}"
        ricetta = _salva(risultato, destinazione)
        dire(f"{modello}: render in {destinazione}, ricetta in {ricetta}")
        pannelli.append((modello, risultato.immagine))

    if len(pannelli) > 1:
        confronto = cartella / f"{sorgente.stem}-confronto.png"
        confronto.write_bytes(modulo_immagine.affianca(pannelli))
        dire(f"Confronto affiancato in {confronto}")
        dire(
            "Scostamento della geometria: non misurato. Guarda gli spigoli: "
            "gronde, aperture, spigoli dei muri contro il cielo."
        )
    return USCITA_PROVIDER if falliti else USCITA_OK


def main(argv: list[str] | None = None) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    try:
        return esegui(argomenti)
    except ErroreAirender as errore:
        print(str(errore), file=sys.stderr)
        return USCITA_RIFIUTO


if __name__ == "__main__":
    raise SystemExit(main())
