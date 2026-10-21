"""Registro dei provider.

Aggiungere un motore immagine costa: un file accanto a magnific.py e
comfy.py, una riga qui. Il resto del motore non cambia.
"""

from __future__ import annotations

from ..errori import ProviderSconosciuto
from .base import Provider, RichiestaGenerazione, RichiestaRegione, Risultato
from .comfy import ProviderComfy
from .magnific import ProviderMagnific

REGISTRO: dict[str, type[Provider]] = {
    ProviderComfy.nome: ProviderComfy,
    ProviderMagnific.nome: ProviderMagnific,
}

# Comfy Router dal 2026-10-21: Magnific non e' piu' a consumo (PRD, sezione 5).
PREDEFINITO = ProviderComfy.nome


def nomi() -> list[str]:
    return sorted(REGISTRO)


def classe(nome: str) -> type[Provider]:
    try:
        return REGISTRO[nome]
    except KeyError:
        raise ProviderSconosciuto(
            f"Non conosco il provider \"{nome}\".",
            f"Quelli registrati sono: {', '.join(nomi())}.",
        ) from None


def crea(nome: str = PREDEFINITO, **parametri) -> Provider:
    """Costruisce il provider chiesto."""
    return classe(nome)(**parametri)


__all__ = [
    "Provider",
    "RichiestaGenerazione",
    "RichiestaRegione",
    "Risultato",
    "ProviderComfy",
    "ProviderMagnific",
    "REGISTRO",
    "PREDEFINITO",
    "crea",
    "classe",
    "nomi",
]
