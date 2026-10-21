"""Il filo che porta i byte fuori dalla macchina.

Sta in un file suo per due ragioni: i test lo sostituiscono con un finto, e
il motore non dipende da `requests`. Il PRD dice che `requests` e' confermato
solo per l'interprete Python di Allplan 2025: `urllib` e' nella libreria
standard e non ha bisogno di essere installato.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Protocol

from .. import config
from ..errori import ErroreProvider


class ErroreRete(ErroreProvider):
    """La richiesta non e' arrivata, o la risposta non e' tornata.

    Separato dagli altri errori perche' e' l'unico caso in cui ripetere la
    stessa chiamata ha senso.
    """


class Trasporto(Protocol):
    """Il minimo che serve a un provider HTTP."""

    def posta(self, url: str, intestazioni: dict, corpo: dict) -> tuple[int, object]: ...

    def leggi(self, url: str, intestazioni: dict) -> tuple[int, object]: ...

    def scarica(self, url: str) -> bytes: ...


class TrasportoConIntestazioni(Protocol):
    """Per i servizi che parlano anche con le intestazioni (Retry-After, id di richiesta).

    Le intestazioni tornano coi nomi in minuscolo: HTTP non distingue, il
    codice che le legge non deve farlo.
    """

    def chiama(
        self, metodo: str, url: str, intestazioni: dict, corpo: dict | None = None
    ) -> tuple[int, dict, object]: ...

    def scarica(self, url: str) -> bytes: ...


def _minuscole(intestazioni) -> dict:
    if intestazioni is None:
        return {}
    return {nome.lower(): valore for nome, valore in intestazioni.items()}


def _decodifica(grezzo: bytes) -> object:
    testo = grezzo.decode("utf-8", errors="replace")
    try:
        return json.loads(testo)
    except json.JSONDecodeError:
        return testo


class TrasportoHTTP:
    """Trasporto reale, sopra urllib."""

    def __init__(self, timeout: int | None = None) -> None:
        self.timeout = config.TIMEOUT_RETE_SECONDI if timeout is None else timeout

    def _esegui(self, richiesta: urllib.request.Request) -> tuple[int, object]:
        stato, _intestazioni, corpo = self._esegui_completo(richiesta)
        return stato, corpo

    def _esegui_completo(self, richiesta: urllib.request.Request) -> tuple[int, dict, object]:
        try:
            with urllib.request.urlopen(richiesta, timeout=self.timeout) as risposta:
                return risposta.status, _minuscole(risposta.headers), _decodifica(risposta.read())
        except urllib.error.HTTPError as errore:
            return errore.code, _minuscole(errore.headers), _decodifica(errore.read())
        except urllib.error.URLError as errore:
            raise ErroreRete(
                f"Non sono riuscito a raggiungere il servizio: {errore.reason}.",
                "Controlla la connessione. Se sei dietro un proxy aziendale, "
                "serve che consenta il traffico verso il servizio indicato "
                "sopra. La tua vista e' rimasta sul disco.",
            ) from None
        except TimeoutError:
            raise ErroreRete(
                f"Il servizio non ha risposto entro {self.timeout} secondi.",
                "Riprova fra qualche minuto. Niente e' andato perso.",
            ) from None

    def chiama(
        self, metodo: str, url: str, intestazioni: dict, corpo: dict | None = None
    ) -> tuple[int, dict, object]:
        dati = None if corpo is None else json.dumps(corpo).encode("utf-8")
        tipo = {} if corpo is None else {"Content-Type": "application/json"}
        richiesta = urllib.request.Request(
            url, data=dati, method=metodo, headers={**tipo, **intestazioni}
        )
        return self._esegui_completo(richiesta)

    def posta(self, url: str, intestazioni: dict, corpo: dict) -> tuple[int, object]:
        dati = json.dumps(corpo).encode("utf-8")
        richiesta = urllib.request.Request(
            url,
            data=dati,
            method="POST",
            headers={"Content-Type": "application/json", **intestazioni},
        )
        return self._esegui(richiesta)

    def leggi(self, url: str, intestazioni: dict) -> tuple[int, object]:
        richiesta = urllib.request.Request(url, method="GET", headers=dict(intestazioni))
        return self._esegui(richiesta)

    def scarica(self, url: str) -> bytes:
        richiesta = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(richiesta, timeout=self.timeout) as risposta:
                return risposta.read()
        except (urllib.error.URLError, TimeoutError) as errore:
            raise ErroreProvider(
                f"L'immagine e' stata generata ma non sono riuscito a "
                f"scaricarla: {errore}.",
                "Riprova: il lavoro e' gia' stato pagato, il link resta valido "
                "per qualche ora.",
            ) from None
