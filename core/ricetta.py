"""La ricetta: tutto quello che serve per rifare la stessa immagine.

Trappola nota: il seme da solo non basta. I provider cambiano i modelli sotto
lo stesso nome e noi stessi cambiamo i testi dei preset. Quindi la ricetta
porta anche il modello, la versione del preset, la versione del motore e
l'impronta della vista di partenza.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from . import __version__


def impronta(dati: bytes) -> str:
    """Impronta della vista di partenza: dice se e' ancora la stessa."""
    return hashlib.sha256(dati).hexdigest()


@dataclass(frozen=True)
class Ricetta:
    """Il record rieseguibile di una generazione."""

    provider: str
    modello: str
    preset: str
    preset_versione: str
    prompt: str
    testo_utente: str
    grana: str
    dettaglio_grana: int
    forza_struttura: int
    risoluzione: str
    aspetto: str
    generazione_fissa: bool
    impronta_sorgente: str
    seme: int | None = None
    motore_versione: str = __version__
    creata_il: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def a_dizionario(self) -> dict:
        return asdict(self)

    def a_json(self) -> str:
        return json.dumps(self.a_dizionario(), ensure_ascii=False, indent=2)

    @classmethod
    def da_dizionario(cls, dati: dict) -> "Ricetta":
        campi = {k: v for k, v in dati.items() if k in cls.__dataclass_fields__}
        return cls(**campi)

    @classmethod
    def da_json(cls, testo: str) -> "Ricetta":
        return cls.da_dizionario(json.loads(testo))
