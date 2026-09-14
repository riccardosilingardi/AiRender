"""La grana: quanto e' minuta la texture. Tre valori, non un numero libero.

Non e' la scala. Vedi core/lessico.py per il perche' quella parola non si usa.
"""

from __future__ import annotations

from . import config
from .errori import ParametroVietato
from .lessico import controlla_etichetta

FINE = "fine"
MEDIA = "media"
GROSSA = "grossa"

LIVELLI = (FINE, MEDIA, GROSSA)

_DETTAGLIO = {
    FINE: config.GRANA_FINE,
    MEDIA: config.GRANA_MEDIA,
    GROSSA: config.GRANA_GROSSA,
}

# Come la grana entra nel prompt tecnico. Inglese: e' la lingua del provider,
# non quella dell'utente.
_FRASE = {
    FINE: "fine-grained surface texture, small scale-free detail",
    MEDIA: "medium-grained surface texture",
    GROSSA: "coarse-grained surface texture, pronounced material relief",
}

# Il nome del parametro passa dal controllo delle parole come ogni altra
# etichetta che scriviamo noi.
NOME_PARAMETRO = controlla_etichetta("grana", "il parametro della texture")

for _livello in LIVELLI:
    controlla_etichetta(_livello, f"il livello di {NOME_PARAMETRO}")


def normalizza(valore: str) -> str:
    """Accetta il nome di un livello, o si spiega."""
    pulito = (valore or "").strip().lower()
    if pulito in LIVELLI:
        return pulito
    raise ParametroVietato(
        f"Non conosco la grana \"{valore}\".",
        f"I livelli sono: {', '.join(LIVELLI)}.",
    )


def dettaglio(livello: str) -> int:
    """Il valore che il provider chiama creative_detailing."""
    return _DETTAGLIO[normalizza(livello)]


def frase(livello: str) -> str:
    """Il pezzo di prompt tecnico che descrive la grana."""
    return _FRASE[normalizza(livello)]


def etichetta(livello: str) -> str:
    """Cosa scrive l'interfaccia accanto allo slider: il livello, non il numero.

    Il numero e' un valore scelto, non misurato, e non va mostrato come se
    significasse qualcosa per l'utente.
    """
    livello = normalizza(livello)
    return f"grana {livello}"
