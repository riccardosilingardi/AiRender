"""Unico posto dove vivono soglie, pesi e limiti.

Un numero che compare in due file prima o poi diverge, e la divergenza non
viene notata. Quindi: qui, una volta sola, con la ragione accanto e
l'etichetta di come quel numero e' nato.

Tre origini, non due:

- MISURATA  il numero viene da una misura ripetibile, descritta nella ragione;
- SCELTA    il numero e' un giudizio nostro, in attesa di misura;
- VINCOLO   il numero non lo decidiamo noi (limite dell'API, del formato).

CLAUDE.md chiede MISURATA o SCELTA. VINCOLO e' stato aggiunto perche'
chiamare "scelta" un limite imposto dal provider sarebbe una bugia nella
direzione opposta: farebbe sembrare nostro un numero che non possiamo
cambiare. Le costanti VINCOLO portano la fonte nella ragione.
"""

from __future__ import annotations

from dataclasses import dataclass

MISURATA = "MISURATA"
SCELTA = "SCELTA"
VINCOLO = "VINCOLO"

ORIGINI = (MISURATA, SCELTA, VINCOLO)


@dataclass(frozen=True)
class Costante:
    """Un numero con la sua provenienza dichiarata.

    `etichetta()` e' quello che l'interfaccia scrive accanto al valore. Un
    numero scelto non deve mai apparire a schermo come se fosse misurato.
    """

    nome: str
    valore: object
    origine: str
    ragione: str
    unita: str = ""

    def __post_init__(self) -> None:
        if self.origine not in ORIGINI:
            raise ValueError(
                f"origine sconosciuta per {self.nome}: {self.origine!r}. "
                f"Valori ammessi: {', '.join(ORIGINI)}."
            )
        if not self.ragione.strip():
            raise ValueError(
                f"la costante {self.nome} non dice perche' vale {self.valore}. "
                "Un numero senza ragione non entra in config.py."
            )

    def etichetta(self) -> str:
        testo = f"{self.valore}{self.unita}"
        if self.origine == MISURATA:
            return f"{testo} (misurato)"
        if self.origine == SCELTA:
            return f"{testo} (valore scelto, non ancora misurato)"
        return f"{testo} (limite del servizio)"


REGISTRO: dict[str, Costante] = {}


def _registra(costante: Costante):
    """Mette la costante nel registro e restituisce il suo valore nudo."""
    if costante.nome in REGISTRO:
        raise ValueError(f"costante duplicata: {costante.nome}")
    REGISTRO[costante.nome] = costante
    return costante.valore


def costante(nome: str) -> Costante:
    """La costante con la sua provenienza, per chi deve scriverla a schermo."""
    try:
        return REGISTRO[nome]
    except KeyError:
        raise KeyError(f"costante non dichiarata in core/config.py: {nome}") from None


# --- Riferimento strutturale -------------------------------------------------

FORZA_STRUTTURA_PREDEFINITA = _registra(Costante(
    nome="FORZA_STRUTTURA_PREDEFINITA",
    valore=70,
    origine=SCELTA,
    ragione=(
        "Quanto il render deve restare attaccato alla vista di partenza. "
        "Sara' misurata nella sessione 2 generando la stessa vista shaded a "
        "50, 70 e 90 e confrontando l'allineamento degli spigoli. Fino ad "
        "allora l'interfaccia deve dire che e' un valore scelto."
    ),
))

FORZA_STRUTTURA_MINIMA = _registra(Costante(
    nome="FORZA_STRUTTURA_MINIMA",
    valore=0,
    origine=VINCOLO,
    ragione="Estremo inferiore del parametro structure_strength dell'API Magnific.",
))

FORZA_STRUTTURA_MASSIMA = _registra(Costante(
    nome="FORZA_STRUTTURA_MASSIMA",
    valore=100,
    origine=VINCOLO,
    ragione="Estremo superiore del parametro structure_strength dell'API Magnific.",
))

# --- Idoneita' dell'immagine di partenza -------------------------------------

LATO_MINIMO_PX = _registra(Costante(
    nome="LATO_MINIMO_PX",
    valore=512,
    origine=SCELTA,
    ragione=(
        "Sotto questo lato lungo il riferimento strutturale ha troppo poco a "
        "cui aggrapparsi e il render si allontana dal disegno. Da misurare "
        "insieme alla forza della struttura."
    ),
    unita=" px",
))

LATO_ANALISI_PX = _registra(Costante(
    nome="LATO_ANALISI_PX",
    valore=384,
    origine=SCELTA,
    ragione=(
        "L'idoneita' si giudica su una copia rimpicciolita: e' un compromesso "
        "fra tempo di analisi e conservazione di ombre e spigoli."
    ),
    unita=" px",
))

TOLLERANZA_SFONDO = _registra(Costante(
    nome="TOLLERANZA_SFONDO",
    valore=6,
    origine=SCELTA,
    ragione=(
        "Due pixel entro questa distanza di luminanza dal tono piu' frequente "
        "sono considerati lo stesso sfondo. Lo sfondo neutro di Allplan non e' "
        "mai esattamente uniforme."
    ),
    unita=" livelli",
))

QUOTA_SFONDO_MASSIMA = _registra(Costante(
    nome="QUOTA_SFONDO_MASSIMA",
    valore=0.70,
    origine=SCELTA,
    ragione=(
        "Oltre questa quota di pixel sullo stesso tono l'immagine e' fatta di "
        "linee su fondo vuoto: un wireframe, non una vista shaded."
    ),
))

TONI_DISTINTI_MINIMI = _registra(Costante(
    nome="TONI_DISTINTI_MINIMI",
    valore=24,
    origine=SCELTA,
    ragione=(
        "Numero minimo di livelli di grigio presenti. Un wireframe ne ha "
        "pochissimi; una vista shaded con ombre ne ha decine."
    ),
    unita=" livelli",
))

DEVIAZIONE_LUMINANZA_MINIMA = _registra(Costante(
    nome="DEVIAZIONE_LUMINANZA_MINIMA",
    valore=12.0,
    origine=SCELTA,
    ragione=(
        "Scarto quadratico medio della luminanza sotto il quale l'immagine e' "
        "piatta: colori pieni senza ombre. Il riferimento strutturale non ha "
        "profondita' da leggere."
    ),
    unita=" livelli",
))

# --- Maschera ----------------------------------------------------------------

MASCHERA_SFUMATURA_PX = _registra(Costante(
    nome="MASCHERA_SFUMATURA_PX",
    valore=3,
    origine=SCELTA,
    ragione=(
        "Sfumatura del bordo della maschera prima dell'invio. Un bordo netto "
        "lascia una cucitura visibile fra regione modificata e resto."
    ),
    unita=" px",
))

# --- Grana (mai 'scala': vedi core/lessico.py) -------------------------------

GRANA_FINE = _registra(Costante(
    nome="GRANA_FINE",
    valore=20,
    origine=SCELTA,
    ragione=(
        "Valore di creative_detailing per la grana fine. Governa quanto "
        "minuta e' la texture, non la sua misura in millimetri."
    ),
))

GRANA_MEDIA = _registra(Costante(
    nome="GRANA_MEDIA",
    valore=45,
    origine=SCELTA,
    ragione="Valore di creative_detailing per la grana media. Predefinito dei preset.",
))

GRANA_GROSSA = _registra(Costante(
    nome="GRANA_GROSSA",
    valore=75,
    origine=SCELTA,
    ragione=(
        "Valore di creative_detailing per la grana grossa. Oltre questo il "
        "provider comincia a inventare dettaglio che non c'era."
    ),
))

# --- Rete --------------------------------------------------------------------

TIMEOUT_RETE_SECONDI = _registra(Costante(
    nome="TIMEOUT_RETE_SECONDI",
    valore=30,
    origine=SCELTA,
    ragione=(
        "Attesa massima per una singola chiamata HTTP. Oltre, e' piu' utile "
        "dire all'utente che il servizio non risponde che restare appesi."
    ),
    unita=" s",
))

ATTESA_MASSIMA_SECONDI = _registra(Costante(
    nome="ATTESA_MASSIMA_SECONDI",
    valore=300,
    origine=SCELTA,
    ragione=(
        "Tempo totale concesso a una generazione prima di dichiararla non "
        "riuscita. La palette deve poter dire qualcosa, non girare all'infinito."
    ),
    unita=" s",
))

INTERVALLO_ATTESA_SECONDI = _registra(Costante(
    nome="INTERVALLO_ATTESA_SECONDI",
    valore=3,
    origine=SCELTA,
    ragione=(
        "Intervallo fra due controlli dello stato del lavoro. Compromesso fra "
        "reattivita' e numero di chiamate; la documentazione del provider usa "
        "lo stesso ordine di grandezza."
    ),
    unita=" s",
))

INVIO_MASSIMO_MB = _registra(Costante(
    nome="INVIO_MASSIMO_MB",
    valore=10,
    origine=VINCOLO,
    ragione=(
        "Dimensione massima per immagine accettata dagli endpoint Magnific "
        "(documentazione API, formati JPEG/PNG/WebP)."
    ),
    unita=" MB",
))

RISOLUZIONE_PREDEFINITA = _registra(Costante(
    nome="RISOLUZIONE_PREDEFINITA",
    valore="2k",
    origine=SCELTA,
    ragione=(
        "Risoluzione chiesta al provider. 2k regge una stampa A3 e costa meno "
        "di 4k: sopra, si paga per pixel che il cliente non guarda. Da "
        "rivedere quando si misurera' il costo per immagine."
    ),
))
