"""Il codice licenza di AIRENDER e il saldo dei crediti.

Chi compra AIRENDER riceve per email un codice (AIR-XXXX-XXXX-XXXX-XXXX).
Si incolla una volta:

    python -m core.cli --licenza AIR-XXXX-XXXX-XXXX-XXXX

e finisce in un file dell'utente, fuori dal repository e fuori dal pacchetto
del plugin (CLAUDE.md, regola 4). Da li' in poi i render passano dal server
AIRENDER, che scala i crediti; con `--saldo` si legge quanti ne restano.

Il codice vale come una chiave: chi lo ha spende i crediti. Il file si scrive
solo per l'utente che lo ha incollato.
"""

from __future__ import annotations

import getpass
import hashlib
import os
import platform
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from . import config
from .errori import ChiaveMancante, ErroreProvider

if TYPE_CHECKING:
    from .provider.trasporto import TrasportoConIntestazioni

# Il trasporto si importa dentro saldo(): core.provider, all'import, chiede a
# questo modulo se c'e' un codice licenza (provider.predefinito). Importarlo
# qui in cima rendeva circolare `python -m core.cli`, che carica licenza prima
# di provider.

VARIABILE = "AIRENDER_LICENZA"
VARIABILE_SERVER = "AIRENDER_SERVER"
INTESTAZIONE = "X-Airender-Licenza"
INTESTAZIONE_POSTAZIONE = "X-Airender-Postazione"
INTESTAZIONE_CANALE = "X-Airender-Canale"

_ALFABETO = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_PREFISSO = "AIR"
_SIMBOLI = 16  # numero-non-configurabile: forma del codice, la stessa di server/lib/codice.mjs
_GRUPPO = 4  # numero-non-configurabile: forma del codice, la stessa di server/lib/codice.mjs
_IMPRONTA = 32  # numero-non-configurabile: lunghezza dell'impronta della postazione


def file_licenza() -> Path:
    """Dove sta il codice: %APPDATA%\\AIRENDER su Windows, ~/.config/airender altrove."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "AIRENDER" / "licenza.txt"
    return Path.home() / ".config" / "airender" / "licenza.txt"


def normalizza(codice: str) -> str:
    """Come il server: maiuscole, senza AIR, trattini e spazi; O letta come 0, I e L come 1."""
    testo = re.sub(r"[\s-]", "", (codice or "").upper())
    testo = testo[len(_PREFISSO):] if testo.startswith(_PREFISSO) else testo
    return testo.replace("O", "0").replace("I", "1").replace("L", "1")


def valido(codice: str) -> bool:
    n = normalizza(codice)
    return len(n) == _SIMBOLI and all(c in _ALFABETO for c in n)


def formatta(codice: str) -> str:
    n = normalizza(codice)
    return f"{_PREFISSO}-" + "-".join(n[i:i + _GRUPPO] for i in range(0, _SIMBOLI, _GRUPPO))


def leggi() -> str | None:
    """Il codice incollato, dalla variabile d'ambiente o dal file dell'utente."""
    valore = os.environ.get(VARIABILE, "").strip()
    if valore:
        return valore
    try:
        valore = file_licenza().read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return valore or None


def salva(codice: str) -> Path:
    if not valido(codice):
        raise ChiaveMancante(
            "Questo non sembra un codice licenza AIRENDER.",
            "Il codice ha la forma AIR-XXXX-XXXX-XXXX-XXXX: ricopialo dall'email "
            "che hai ricevuto dopo l'acquisto.",
        )
    percorso = file_licenza()
    percorso.parent.mkdir(parents=True, exist_ok=True)
    percorso.write_text(formatta(codice) + "\n", encoding="utf-8")
    try:
        percorso.chmod(0o600)  # numero-non-configurabile: permessi del solo utente
    except OSError:
        pass
    return percorso


def server() -> str:
    return (os.environ.get(VARIABILE_SERVER, "").strip() or config.SERVER_AIRENDER).rstrip("/")


def postazione() -> str:
    """Un'impronta di questa macchina e utente: il server conta le postazioni, non chi sono.

    Non manda il nome della macchina ne' dell'utente, solo l'hash.
    """
    try:
        utente = getpass.getuser()
    except Exception:  # pylint: disable=broad-exception-caught
        utente = ""
    grezzo = f"{platform.node()}|{utente}|{uuid.getnode()}"
    return hashlib.sha256(grezzo.encode("utf-8")).hexdigest()[:_IMPRONTA]


def intestazioni(codice: str, canale: str = "plugin") -> dict:
    return {
        INTESTAZIONE: codice,
        INTESTAZIONE_POSTAZIONE: postazione(),
        INTESTAZIONE_CANALE: canale,
    }


def peso_render(modello: str, dimensione: str) -> int | None:
    """Quanti render costa un invio, dal listino. None: non compreso nei crediti."""
    return config.LISTINO["pesi"].get(modello, {}).get((dimensione or "1k").upper())


def saldo(codice: str | None = None, trasporto: TrasportoConIntestazioni | None = None) -> dict:
    """Piano, saldo e link di Ricarica, chiesti al server AIRENDER."""
    codice = codice or leggi()
    if not codice:
        raise ChiaveMancante(
            "Non hai ancora incollato un codice licenza AIRENDER.",
            "Incollalo con: python -m core.cli --licenza AIR-XXXX-XXXX-XXXX-XXXX",
        )
    from .provider.trasporto import ErroreRete, TrasportoHTTP

    trasporto = trasporto or TrasportoHTTP()
    try:
        stato, _, corpo = trasporto.chiama(
            "GET", f"{server()}/api/saldo", {**intestazioni(codice), "Accept": "application/json"}
        )
    except ErroreRete as errore:
        raise ErroreProvider(f"Il server AIRENDER non risponde: {errore.fatto}", errore.cosa_fare) from None
    if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
        raise errore_del_server(stato, corpo)
    return corpo if isinstance(corpo, dict) else {}


def errore_del_server(stato: int, corpo: object) -> ErroreProvider:
    """Il server scrive gia' la frase in italiano: si mostra com'e'."""
    if isinstance(corpo, dict) and isinstance(corpo.get("error"), dict):
        fatto = str(corpo["error"].get("message") or "")
        cosa_fare = str(corpo.get("cosa_fare") or "")
        if fatto:
            return ErroreProvider(fatto, cosa_fare or "Riprova; se si ripete, scrivi a AIRENDER.", stato=stato)
    return ErroreProvider(
        f"Il server AIRENDER ha risposto con un errore ({stato}).",
        "Riprova fra qualche minuto; se si ripete, scrivi a AIRENDER.",
        stato=stato,
    )


def racconta_saldo(dati: dict) -> str:
    """Il saldo in parole, come lo stampa la riga di comando."""
    righe = [
        f"Licenza ...{dati.get('ultime_cifre', '')} ({dati.get('email', '')}), "
        f"piano {dati.get('funzioni', {}).get('nome', dati.get('piano', ''))}.",
        f"Render disponibili: {dati.get('saldo', 0)}"
        + (f" (piu' {dati['in_attesa']} in corso)" if dati.get("in_attesa") else "") + ".",
    ]
    scadenza = dati.get("prossima_scadenza")
    if scadenza:
        righe.append(f"{scadenza['quantita']} scadono il {str(scadenza['il']).split('T')[0]}.")
    if dati.get("ricarica_url"):
        righe.append(f"Ricarica (link valido un'ora): {dati['ricarica_url']}")
    if dati.get("gestisci_url"):
        righe.append(f"Abbonamento: {dati['gestisci_url']}")
    return "\n".join(righe)
