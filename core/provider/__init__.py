"""Registro dei provider.

Aggiungere un motore immagine costa: un file accanto a magnific.py e
comfy.py, una riga qui. Il resto del motore non cambia.
"""

from __future__ import annotations

from ..errori import ProviderSconosciuto
from .airender import ProviderAirender
from .base import Provider, RichiestaGenerazione, RichiestaRegione, Risultato
from .comfy import ProviderComfy
from .magnific import ProviderMagnific

REGISTRO: dict[str, type[Provider]] = {
    ProviderAirender.nome: ProviderAirender,
    ProviderComfy.nome: ProviderComfy,
    ProviderMagnific.nome: ProviderMagnific,
}



def predefinito() -> str:
    """Con un codice licenza incollato, i crediti AIRENDER; senza, la chiave Comfy propria.

    Comfy Router dal 2026-10-21 (Magnific non e' piu' a consumo, PRD sezione
    5); dal 2026-11-02 il cliente che compra AIRENDER non ha un account Comfy
    e passa dal server AIRENDER. Chi ha solo COMFY_API_KEY (Riccardo, BYOK)
    resta su Comfy diretto.
    """
    from .. import licenza

    return ProviderAirender.nome if licenza.leggi() else ProviderComfy.nome


# Letto all'avvio: dopo aver incollato il codice si riavvia lo Studio (o
# Allplan) perche' valga.
PREDEFINITO = predefinito()


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
    "ProviderAirender",
    "ProviderComfy",
    "ProviderMagnific",
    "REGISTRO",
    "PREDEFINITO",
    "predefinito",
    "crea",
    "classe",
    "nomi",
]
