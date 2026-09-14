"""Errori del motore.

Regola unica: un rifiuto si spiega da solo. Ogni errore porta due cose, il
fatto e il gesto successivo. Mai un codice HTTP da solo, mai una frase che
lascia l'utente fermo.
"""

from __future__ import annotations


class ErroreAirender(Exception):
    """Base di tutti gli errori del motore."""

    def __init__(self, fatto: str, cosa_fare: str) -> None:
        self.fatto = fatto
        self.cosa_fare = cosa_fare
        super().__init__(f"{fatto}\nCosa fare: {cosa_fare}")


class FileNonTrovato(ErroreAirender):
    """Il percorso indicato non esiste o non e' leggibile."""


class ImmagineNonIdonea(ErroreAirender):
    """La vista di partenza non e' adatta: wireframe, piatta o troppo piccola."""

    def __init__(self, fatto: str, cosa_fare: str, motivo: str) -> None:
        self.motivo = motivo
        super().__init__(fatto, cosa_fare)


class ParametroVietato(ErroreAirender):
    """Si e' chiamato un parametro con un nome che promette cio' che non diamo."""


class ChiaveMancante(ErroreAirender):
    """Manca la chiave API. La chiave e' del cliente e non vive nel repository."""


class PresetSconosciuto(ErroreAirender):
    """Il preset chiesto non esiste nel pacchetto."""


class ProviderSconosciuto(ErroreAirender):
    """Il provider chiesto non e' fra quelli registrati."""


class ErroreProvider(ErroreAirender):
    """Il servizio esterno ha risposto male, o non ha risposto."""

    def __init__(self, fatto: str, cosa_fare: str, stato: int | None = None) -> None:
        self.stato = stato
        super().__init__(fatto, cosa_fare)


def errore_da_stato_http(servizio: str, stato: int, corpo: str = "") -> ErroreProvider:
    """Traduce uno stato HTTP in una frase utile.

    Il codice resta disponibile in `.stato` per i log, ma non e' mai la sola
    cosa che l'utente legge.
    """
    dettaglio = corpo.strip()
    if len(dettaglio) > 300:  # numero-non-configurabile: taglio di cortesia del messaggio
        dettaglio = dettaglio[:300] + "..."  # numero-non-configurabile: stesso taglio
    coda = f" Il servizio ha aggiunto: {dettaglio}" if dettaglio else ""

    if stato in (401, 403):  # numero-non-configurabile: codici HTTP
        return ErroreProvider(
            f"{servizio} non ha accettato la chiave.{coda}",
            "Controlla la chiave nella variabile d'ambiente MAGNIFIC_API_KEY, "
            "o rigenerala nel cruscotto del tuo account. La chiave e' tua e "
            "non sta dentro il plugin.",
            stato=stato,
        )
    if stato == 402:  # numero-non-configurabile: codice HTTP
        return ErroreProvider(
            f"{servizio} dice che il credito del tuo account e' esaurito.{coda}",
            "Ricarica il credito nel cruscotto del tuo account. "
            "AIRENDER non gestisce crediti: paghi il servizio direttamente tu.",
            stato=stato,
        )
    if stato == 429:  # numero-non-configurabile: codice HTTP
        return ErroreProvider(
            f"{servizio} sta rifiutando le richieste perche' sono troppo "
            f"ravvicinate.{coda}",
            "Aspetta un minuto e rilancia. Se succede sempre, il tuo piano ha "
            "un limite di chiamate al minuto piu' basso di quello che serve.",
            stato=stato,
        )
    if stato == 413:  # numero-non-configurabile: codice HTTP
        return ErroreProvider(
            f"{servizio} ha rifiutato l'immagine perche' e' troppo pesante.{coda}",
            "Salva di nuovo la vista da Allplan a una risoluzione piu' bassa.",
            stato=stato,
        )
    if 400 <= stato < 500:  # numero-non-configurabile: famiglia di codici HTTP
        return ErroreProvider(
            f"{servizio} ha rifiutato la richiesta.{coda}",
            "E' un problema della richiesta, non della rete. Riprova con un "
            "preset diverso; se si ripete, segnala il messaggio qui sopra.",
            stato=stato,
        )
    return ErroreProvider(
        f"{servizio} non e' riuscito a rispondere.{coda}",
        "E' un problema del servizio, non tuo. Riprova fra qualche minuto: "
        "la tua vista e i tuoi parametri sono rimasti sul disco.",
        stato=stato,
    )
