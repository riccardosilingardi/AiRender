"""L'interfaccia che il resto del motore conosce.

Tre cose, perche' tre cose servono al prodotto:

1. generare con un riferimento strutturale e una forza;
2. modificare una regione delimitata da una maschera;
3. rieseguire a parametri identici.

Chi implementa un secondo provider scrive un file accanto a magnific.py e lo
aggiunge al registro. Niente altro nel motore deve cambiare.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable

from .. import config
from ..ricetta import Ricetta


# Le due cose che un provider sa dire mentre aspetta. Le parole sono quelle
# dello stato di un lavoro in core/coda.py: chi legge lo stato non traduce.
INVIATO = "inviato"
IN_LAVORAZIONE = "in lavorazione"


@dataclass(frozen=True)
class RichiestaGenerazione:
    """Tutto quello che serve per una generazione, ricetta compresa."""

    immagine: bytes
    prompt: str
    preset: str
    preset_versione: str
    modello: str
    grana: str
    dettaglio_grana: int
    testo_utente: str = ""
    forza_struttura: int = config.FORZA_STRUTTURA_PREDEFINITA
    risoluzione: str = config.RISOLUZIONE_PREDEFINITA
    aspetto: str | None = None
    generazione_fissa: bool = False
    seme: int | None = None
    # Immagini dopo la vista, nello stesso invio (una maschera, una mappa).
    # Solo i modelli il cui schema lo dichiara le accettano: gli altri si
    # fermano prima di partire.
    immagini_in_piu: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class RichiestaRegione:
    """Una modifica limitata a una regione: il resto dell'immagine non si tocca."""

    immagine: bytes
    maschera: bytes
    prompt: str
    preset: str = ""
    preset_versione: str = ""
    modello: str = ""
    grana: str = ""
    dettaglio_grana: int = 0
    seme: int | None = None


@dataclass(frozen=True)
class Risultato:
    """Cosa torna indietro.

    `scostamento_geometria` vale None finche' nessuno l'ha misurato, e None
    non si stampa come un numero: si stampa come "non misurato".
    """

    immagine: bytes
    formato: str
    ricetta: Ricetta
    scostamento_geometria: float | None = None
    avvisi: list[str] = field(default_factory=list)


class Provider(ABC):
    """Un motore immagine visto dal resto del prodotto."""

    #: nome breve, quello che si scrive nel registro e nella ricetta
    nome: str = ""
    #: cosa legge l'utente prima che l'immagine parta da casa sua
    destinazione: str = ""
    #: se il servizio ha davvero una forza della struttura da 0 a 100. Se non
    #: ce l'ha, l'interfaccia non deve stampare un numero che non parte.
    usa_forza_struttura: bool = True
    #: chi vuole sapere a che punto e' il lavoro (la coda) mette qui una
    #: funzione che riceve INVIATO o IN_LAVORAZIONE. Viene chiamata a ogni
    #: controllo dello stato, non solo ai cambi: e' anche il momento in cui
    #: la coda puo' fermare l'attesa, sollevando un errore.
    avanzamento: Callable[[str], None] | None = None

    def _segnala(self, stato: str) -> None:
        if self.avanzamento is not None:
            self.avanzamento(stato)

    def destinazione_per(self, modello: str) -> str:
        """La destinazione completa per questo modello, da mostrare prima dell'invio."""
        return self.destinazione

    def cosa_manca(self, modello: str) -> str | None:
        """Cosa fermerebbe l'invio vero, detto gia' nella prova a secco. None se niente."""
        return None

    def controlla_prima_dell_invio(self, modello: str, immagine: bytes) -> None:
        """Solleva l'errore che fermerebbe l'invio (chiave, schema, peso), senza inviare.

        La coda lo chiama prima di scrivere "inviato": uno stato che dice
        partito per un'immagine rimasta a casa e' una bugia.
        """

    @abstractmethod
    def genera(self, richiesta: RichiestaGenerazione) -> Risultato:
        """Genera partendo dalla vista come riferimento strutturale."""

    @abstractmethod
    def modifica_regione(self, richiesta: RichiestaRegione) -> Risultato:
        """Cambia solo la regione coperta dalla maschera."""

    @abstractmethod
    def riesegui(self, ricetta: Ricetta, immagine: bytes) -> Risultato:
        """Rifa' la stessa immagine dagli stessi parametri."""
