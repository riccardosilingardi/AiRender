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

from .. import config
from ..ricetta import Ricetta


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

    @abstractmethod
    def genera(self, richiesta: RichiestaGenerazione) -> Risultato:
        """Genera partendo dalla vista come riferimento strutturale."""

    @abstractmethod
    def modifica_regione(self, richiesta: RichiestaRegione) -> Risultato:
        """Cambia solo la regione coperta dalla maschera."""

    @abstractmethod
    def riesegui(self, ricetta: Ricetta, immagine: bytes) -> Risultato:
        """Rifa' la stessa immagine dagli stessi parametri."""
