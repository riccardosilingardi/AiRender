"""Le parole che il prodotto non usa.

Lo slider governa la *grana* — fine, media, grossa. Non governa la scala
metrica dei materiali: il provider non sa quanto e' alto un corso di mattoni.
Chiamarlo "scala" sarebbe una bugia che il cliente puo' verificare con un
metro in mano, ed e' il tipo di bugia che fa perdere un cliente.

Il divieto vale sulle *nostre* parole: nomi dei parametri, etichette,
descrizioni dei preset. Non vale sul testo libero dell'utente: in italiano
"scala" e' anche il vano scala, e rifiutare quella parola a un architetto
sarebbe assurdo.
"""

from __future__ import annotations

import re

from .errori import ParametroVietato

# Parole che, nelle nostre etichette, promettono una misura che non abbiamo.
PAROLE_VIETATE = ("scala", "scale", "scalatura", "millimetri", "1:100", "1:50")

_CONFINE = re.compile(r"[a-zA-Zàèéìòù]+|1:\d+")

SPIEGAZIONE = (
    "Il parametro si chiama grana (fine, media, grossa). Governa quanto e' "
    "minuta la texture, non la sua misura reale: il servizio non sa quanto e' "
    "alto un corso di mattoni, e promettere una scala sarebbe una bugia che il "
    "cliente verifica con un metro."
)


def controlla_etichetta(testo: str, dove: str) -> str:
    """Verifica che una nostra etichetta non prometta la scala metrica.

    Va chiamata su tutto cio' che scriviamo noi: nomi di parametri, titoli di
    preset, testi della palette. Restituisce il testo se e' pulito.
    """
    parole = {p.lower() for p in _CONFINE.findall(testo)}
    vietate = sorted(parole & set(PAROLE_VIETATE))
    if vietate:
        raise ParametroVietato(
            f"{dove} usa la parola \"{vietate[0]}\" per un parametro che non "
            f"promette una misura: {testo!r}.",
            SPIEGAZIONE,
        )
    return testo


def rifiuta_opzione_scala(argomenti: list[str]) -> None:
    """Se qualcuno scrive --scala sulla riga di comando, spiega perche' no.

    Argparse direbbe soltanto "unrecognized arguments". Una schermata vuota
    non e' una risposta.
    """
    for argomento in argomenti:
        nudo = argomento.split("=", 1)[0].lstrip("-").lower()
        if nudo in PAROLE_VIETATE:
            raise ParametroVietato(
                f"L'opzione --{nudo} non esiste, e non esistera'.",
                SPIEGAZIONE + " Usa --grana fine|media|grossa.",
            )
