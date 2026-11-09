"""Le mie ricette: i passi di un'immagine riuscita, salvati con un nome per rifarli su altre viste.

Una ricetta non copia i passi: ricorda da quale render viene (il lavoro) e
li rilegge da li' quando si usa, cosi' quello che parte e' sempre quello che
l'immagine ha davvero avuto. Accanto tiene i nomi dei passi com'erano al
salvataggio, per poterli mostrare anche quando quel render non c'e' piu'.

Vive in `ricette-utente.json` nella cartella delle viste, accanto a
`preset-utente.json` e con le stesse regole: fuori dal repository (regola
4), scritto in modo atomico, e se un giorno non si legge non si sovrascrive
ma si mette da parte con un nome che lo dice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .coda import scrivi_atomico
from .errori import ErroreAirender

NOME_FILE = "ricette-utente.json"
FORMATO = 1
LUNGHEZZA_MASSIMA_NOME = 60  # numero-non-configurabile: sta in una riga dell'elenco, come i preset


class RicettaUtenteNonValida(ErroreAirender):
    """Un nome vuoto o doppio, una ricetta che non c'e', un file che non si legge."""


@dataclass(frozen=True)
class Elenco:
    ricette: list[dict]
    problema: str | None = None  # il file c'era ma non si leggeva: cosa e' successo


def percorso(cartella: Path) -> Path:
    return Path(cartella) / NOME_FILE


def leggi(cartella: Path) -> Elenco:
    file = percorso(cartella)
    if not file.exists():
        return Elenco([])
    try:
        dati = json.loads(file.read_text(encoding="utf-8"))
        ricette = dati["ricette"]
        if dati.get("formato") != FORMATO or not isinstance(ricette, list):
            raise ValueError("formato sconosciuto")
    except (OSError, ValueError, KeyError, TypeError) as errore:
        riserva = file.with_name(f"ricette-utente.non-letto-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            file.rename(riserva)
            dove = f"L'ho messo da parte come {riserva.name}, non l'ho cancellato."
        except OSError:
            dove = "Non sono riuscito a spostarlo: resta com'era."
        return Elenco([], problema=f"Il file delle tue ricette non si legge ({errore}). {dove}")
    return Elenco([r for r in ricette if isinstance(r, dict) and isinstance(r.get("nome"), str)
                   and isinstance(r.get("lavoro"), str)])


def _scrivi(cartella: Path, ricette: list[dict]) -> None:
    scrivi_atomico(percorso(cartella), json.dumps(
        {"formato": FORMATO, "ricette": ricette}, ensure_ascii=False, indent=2))


def _nome_pulito(nome: object) -> str:
    pulito = " ".join(str(nome or "").split())
    if not pulito:
        raise RicettaUtenteNonValida("La ricetta non ha un nome.",
                                     "Scrivi un nome, per esempio «Ora blu con persone».")
    if len(pulito) > LUNGHEZZA_MASSIMA_NOME:
        raise RicettaUtenteNonValida(
            f"Il nome ha {len(pulito)} caratteri, al massimo {LUNGHEZZA_MASSIMA_NOME}.",
            "Accorcialo: deve stare in una riga dell'elenco.")
    return pulito


def _trova(ricette: list[dict], nome: str) -> int | None:
    for indice, voce in enumerate(ricette):
        if voce["nome"].casefold() == nome.casefold():
            return indice
    return None


def trova(cartella: Path, nome: str) -> dict:
    ricette = leggi(cartella).ricette
    indice = _trova(ricette, str(nome or ""))
    if indice is None:
        raise RicettaUtenteNonValida(f"Non trovo la ricetta «{nome}».", "Ricarica lo Studio.")
    return ricette[indice]


def salva(cartella: Path, nome: object, lavoro: str, vista: str, passi: list[str],
          sovrascrivi: bool = False) -> dict:
    """Aggiunge (o, con sovrascrivi, sostituisce) una ricetta che viene dal render `lavoro`."""
    nome = _nome_pulito(nome)
    elenco = leggi(cartella)
    if elenco.problema:
        raise RicettaUtenteNonValida(elenco.problema, "Salva di nuovo: ora parte un file nuovo.")
    ricette = elenco.ricette
    voce = {
        "nome": nome, "lavoro": str(lavoro), "vista": str(vista),
        "passi": [str(p) for p in passi],
        "salvata_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    indice = _trova(ricette, nome)
    if indice is not None and not sovrascrivi:
        raise RicettaUtenteNonValida(
            f"Hai gia' una ricetta che si chiama «{ricette[indice]['nome']}».",
            "Scegli un altro nome, o conferma di sostituirla.")
    if indice is None:
        ricette.append(voce)
    else:
        ricette[indice] = voce
    _scrivi(cartella, ricette)
    return voce


def elimina(cartella: Path, nome: str) -> None:
    ricette = leggi(cartella).ricette
    indice = _trova(ricette, str(nome or ""))
    if indice is None:
        raise RicettaUtenteNonValida(f"Non trovo la ricetta «{nome}».", "Ricarica lo Studio.")
    del ricette[indice]
    _scrivi(cartella, ricette)
