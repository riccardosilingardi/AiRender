"""I miei preset: le scelte dello Studio salvate con un nome, dall'utente.

Vivono in `preset-utente.json` nella cartella delle viste, fuori dal
repository (regola 4: niente dell'utente nel codice). Il file si scrive in
modo atomico; se un giorno non si legge, non si sovrascrive: si mette da
parte con un nome che lo dice, e lo Studio lo spiega.

Ogni preset ricorda la versione dei blocchi con cui e' stato salvato. Se i
blocchi sono cambiati, al caricamento si dice cosa non esiste piu' invece di
caricarlo in silenzio con scelte diverse da quelle salvate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import blocchi
from .coda import scrivi_atomico
from .errori import ErroreAirender

NOME_FILE = "preset-utente.json"
FORMATO = 1
LUNGHEZZA_MASSIMA_NOME = 60  # numero-non-configurabile: sta in una riga del menu


class PresetUtenteNonValido(ErroreAirender):
    """Un nome vuoto o doppio, un preset che non c'e', un file che non si legge."""


@dataclass(frozen=True)
class Elenco:
    preset: list[dict]
    problema: str | None = None  # il file c'era ma non si leggeva: cosa e' successo


def percorso(cartella: Path) -> Path:
    return Path(cartella) / NOME_FILE


def leggi(cartella: Path) -> Elenco:
    file = percorso(cartella)
    if not file.exists():
        return Elenco([])
    try:
        dati = json.loads(file.read_text(encoding="utf-8"))
        preset = dati["preset"]
        if dati.get("formato") != FORMATO or not isinstance(preset, list):
            raise ValueError("formato sconosciuto")
    except (OSError, ValueError, KeyError, TypeError) as errore:
        riserva = file.with_name(f"preset-utente.non-letto-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            file.rename(riserva)
            dove = f"L'ho messo da parte come {riserva.name}, non l'ho cancellato."
        except OSError:
            dove = "Non sono riuscito a spostarlo: resta com'era."
        return Elenco([], problema=f"Il file dei tuoi preset non si legge ({errore}). {dove}")
    return Elenco([p for p in preset if isinstance(p, dict) and isinstance(p.get("nome"), str)])


def _scrivi(cartella: Path, preset: list[dict]) -> None:
    scrivi_atomico(percorso(cartella), json.dumps(
        {"formato": FORMATO, "preset": preset}, ensure_ascii=False, indent=2))


def _nome_pulito(nome: object) -> str:
    pulito = " ".join(str(nome or "").split())
    if not pulito:
        raise PresetUtenteNonValido("Il preset non ha un nome.", "Scrivi un nome, per esempio «Notte cliente Rossi».")
    if len(pulito) > LUNGHEZZA_MASSIMA_NOME:
        raise PresetUtenteNonValido(
            f"Il nome ha {len(pulito)} caratteri, al massimo {LUNGHEZZA_MASSIMA_NOME}.",
            "Accorcialo: deve stare in una riga del menu.")
    return pulito


def _trova(preset: list[dict], nome: str) -> int | None:
    for indice, voce in enumerate(preset):
        if voce["nome"].casefold() == nome.casefold():
            return indice
    return None


def salva(cartella: Path, nome: object, scelte: dict, modello: str,
          prompt_a_mano: str | None = None, sovrascrivi: bool = False) -> dict:
    """Aggiunge (o, con sovrascrivi, sostituisce) un preset. Le scelte devono essere valide."""
    nome = _nome_pulito(nome)
    scelte = blocchi.Scelte.da_dizionario(scelte or {}).a_dizionario()
    elenco = leggi(cartella)
    if elenco.problema:
        raise PresetUtenteNonValido(elenco.problema, "Salva di nuovo: ora parte un file nuovo.")
    preset = elenco.preset
    voce = {
        "nome": nome, "scelte": scelte, "modello": modello,
        "prompt_a_mano": (prompt_a_mano or None),
        "versione_blocchi": blocchi.VERSIONE,
        "salvato_il": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    indice = _trova(preset, nome)
    if indice is not None and not sovrascrivi:
        raise PresetUtenteNonValido(
            f"Hai gia' un preset che si chiama «{preset[indice]['nome']}».",
            "Scegli un altro nome, o conferma di sostituirlo.")
    if indice is None:
        preset.append(voce)
    else:
        preset[indice] = voce
    _scrivi(cartella, preset)
    return voce


def rinomina(cartella: Path, vecchio: str, nuovo: object) -> dict:
    nuovo = _nome_pulito(nuovo)
    preset = leggi(cartella).preset
    indice = _trova(preset, str(vecchio or ""))
    if indice is None:
        raise PresetUtenteNonValido(f"Non trovo il preset «{vecchio}».", "Ricarica lo Studio.")
    altro = _trova(preset, nuovo)
    if altro is not None and altro != indice:
        raise PresetUtenteNonValido(f"Hai gia' un preset che si chiama «{preset[altro]['nome']}».",
                                    "Scegli un altro nome.")
    preset[indice] = {**preset[indice], "nome": nuovo}
    _scrivi(cartella, preset)
    return preset[indice]


def elimina(cartella: Path, nome: str) -> None:
    preset = leggi(cartella).preset
    indice = _trova(preset, str(nome or ""))
    if indice is None:
        raise PresetUtenteNonValido(f"Non trovo il preset «{nome}».", "Ricarica lo Studio.")
    del preset[indice]
    _scrivi(cartella, preset)


def carica(voce: dict) -> dict:
    """Le scelte di un preset salvato, con cosa non vale piu' se i blocchi sono cambiati."""
    salvate = voce.get("scelte") or {}
    validi = {f for f in blocchi.Scelte().a_dizionario()}
    perse = []
    pulite = {}
    for asse, valore in salvate.items():
        if asse not in validi:
            perse.append(f"{asse}: la voce non esiste piu'")
            continue
        pulite[asse] = valore
    scena = pulite.get("scena", blocchi.ESTERNO)
    predefinite = {"qualita": blocchi.QUALITA_PREDEFINITA, "fedelta": blocchi.FEDELTA_PREDEFINITA}
    for asse in ("fedelta", *blocchi.ORDINE_ASSI):
        valore = pulite.get(asse)
        if not valore:
            continue
        try:
            if scena not in blocchi.ASSI[asse][1] or valore not in blocchi.voci(asse, scena):
                raise KeyError(valore)
        except (KeyError, blocchi.SceltaNonValida):
            perse.append(f"{asse}: «{valore}» non esiste piu'")
            pulite[asse] = predefinite.get(asse)
    try:
        scelte = blocchi.Scelte.da_dizionario(pulite).a_dizionario()
    except blocchi.SceltaNonValida as errore:
        perse.append(errore.fatto)
        scelte = blocchi.Scelte(scena=scena).a_dizionario()
    cambiati = voce.get("versione_blocchi") != blocchi.VERSIONE
    return {
        "nome": voce["nome"],
        "scelte": scelte,
        "modello": voce.get("modello"),
        "prompt_a_mano": voce.get("prompt_a_mano"),
        "versione_blocchi": voce.get("versione_blocchi"),
        "blocchi_cambiati": cambiati,
        "perse": perse,
    }
