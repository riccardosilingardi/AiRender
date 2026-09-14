"""Da preset + testo dell'utente al prompt tecnico.

Qui non c'e' nessun modello linguistico. L'espansione del linguaggio naturale
("piu' caldo, mattone vecchio" -> prompt tecnico coerente col preset) e' una
decisione presa nel PRD ma non ancora costruita: e' una seconda chiave e un
secondo servizio. Finche' non esiste, il testo dell'utente viene passato
com'e', in coda al preset, e questo file non finge di capirlo.
"""

from __future__ import annotations

from . import grana as modulo_grana
from .preset import Preset


def componi(preset: Preset, testo_libero: str = "", grana: str | None = None) -> str:
    """Il prompt che parte davvero, nell'ordine in cui conta."""
    livello = modulo_grana.normalizza(grana or preset.grana_predefinita)
    pezzi = [preset.prompt_tecnico.strip()]
    testo = (testo_libero or "").strip()
    if testo:
        pezzi.append(testo)
    pezzi.append(modulo_grana.frase(livello))
    return ", ".join(pezzi)
