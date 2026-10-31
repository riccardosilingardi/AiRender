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

# --- Confronto affiancato ----------------------------------------------------

CONFRONTO_DIDASCALIA_PX = _registra(Costante(
    nome="CONFRONTO_DIDASCALIA_PX",
    valore=28,
    origine=SCELTA,
    ragione=(
        "Altezza della striscia col nome sopra ogni immagine del confronto. "
        "Sta sopra, non sopra l'immagine: una didascalia sovrapposta coprirebbe "
        "proprio gli spigoli alti che si devono guardare."
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

TENTATIVI_INVIO_MASSIMI = _registra(Costante(
    nome="TENTATIVI_INVIO_MASSIMI",
    valore=3,
    origine=SCELTA,
    ragione=(
        "Quante volte si prova una chiamata a Comfy Router quando la rete cade "
        "o il servizio risponde 429 o 5xx. Ogni tentativo porta la stessa "
        "Idempotency-Key, cosi' il Router rende la risposta del primo invece "
        "di far pagare una seconda generazione. Oltre tre il guasto non e' "
        "passeggero, ed e' piu' utile dirlo all'utente che insistere."
    ),
))

COMFY_INVIO_MASSIMO_MB = _registra(Costante(
    nome="COMFY_INVIO_MASSIMO_MB",
    valore=10,
    origine=SCELTA,
    ragione=(
        "Peso massimo della vista mandata a Comfy Router. Il Router non "
        "dichiara un limite unico: dipende dal modello (25 MiB per FLUX.1 "
        "Kontext nella sua scheda su comfy.org). 10 MB sta sotto ogni limite "
        "letto finche' la sonda non dice altro, e una vista di Allplan a 2k "
        "pesa meno di 1 MB."
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

RISOLUZIONE_RENDER_PREDEFINITA = _registra(Costante(
    nome="RISOLUZIONE_RENDER_PREDEFINITA",
    valore="1k",
    origine=SCELTA,
    ragione=(
        "Quanto grande torna il render dai modelli Gemini (Nano Banana 2 e Pro): "
        "1k, 2k o 4k sul lato lungo. 1k e' l'unica provata con una chiamata vera "
        "(senza il campo imageSize); 2k e 4k sono un campo dei documenti di "
        "Vertex AI, mai passato dal Router, e costano di piu' per immagine. Il "
        "2026-10-31 Riccardo ha trovato il render da 1k poco definito."
    ),
))
RISOLUZIONI_RENDER = ("1k", "2k", "4k")  # numero-non-configurabile: i valori di imageSize di Vertex AI

# --- Coda dei lavori ---------------------------------------------------------

CODA_INTERVALLO_SECONDI = _registra(Costante(
    nome="CODA_INTERVALLO_SECONDI",
    valore=1,
    origine=SCELTA,
    ragione=(
        "Ogni quanto il processo della coda guarda se in lavori/in-attesa e' "
        "arrivato un lavoro. Un secondo e' meno del tempo che si impiega a "
        "passare da Genera allo Studio, e leggere una cartella al secondo non "
        "pesa sulla macchina. E' il WATCH_FOLDER_POLL_SECONDS di CLAUDE.md."
    ),
    unita=" s",
))

# --- Proporzioni della vista ----------------------------------------------------

CORNICE_TOLLERANZA = _registra(Costante(
    nome="CORNICE_TOLLERANZA",
    valore=0.01,
    origine=SCELTA,
    ragione=(
        "Scarto relativo fra il rapporto della vista e il piu' vicino che il "
        "modello accetta, sotto il quale la vista parte com'e'. Sopra, la si "
        "allarga con una cornice fino al rapporto esatto e al ritorno la "
        "cornice si taglia: senza, il 2026-10-31 una vista 1165x715 (1,63) e' "
        "tornata a 3:2 e lo Studio l'ha dovuta stirare del 9,3%. Un 1% e' "
        "meno di un pixel su dieci di una vista da 1000 px di lato."
    ),
))

ANTEPRIMA_TAGLIO_SCURO = _registra(Costante(
    nome="ANTEPRIMA_TAGLIO_SCURO",
    valore=0.6,
    origine=SCELTA,
    ragione=(
        "Quanto si scurisce, nell'anteprima della palette, la parte di vista "
        "che un formato fisso taglierebbe: 0 non si vede niente, 1 e' nero e "
        "non si capisce piu' cosa si perde. 0,6 lascia leggere la scena tagliata."
    ),
))


# --- Studio ------------------------------------------------------------------

COSTO_NANO_BANANA_2_CREDITI = _registra(Costante(
    nome="COSTO_NANO_BANANA_2_CREDITI",
    valore=17.17,
    origine=MISURATA,
    ragione=(
        "Crediti scalati da Comfy Router per una generazione con Nano Banana 2 "
        "(vertexai/gemini-3.1-flash-image), letti nell'intestazione "
        "x-comfy-credits-used della sonda del 2026-10-27 e dei due invii veri "
        "dello stesso giorno (riga di comando e palette di prova): 17,17 tutte "
        "le volte. Poche generazioni, a 2k: lo Studio lo scrive come "
        "\"circa\" e con la data. Il costo di FLUX.1 "
        "Kontext Pro non e' stato copiato, e lo Studio dice che non e' misurato."
    ),
    unita=" crediti",
))

SATURAZIONE_COLORE_MINIMA = _registra(Costante(
    nome="SATURAZIONE_COLORE_MINIMA",
    valore=60,
    origine=SCELTA,
    ragione=(
        "Saturazione (0-255, come la S di HSV in Pillow) sopra la quale un "
        "pixel della vista conta come colorato. Le viste shaded di Allplan in "
        "colori neutri stanno sotto 20; i colori per layer (viola, verde, "
        "rosso pieni) sopra 120. 60 sta in mezzo: provato solo sulla vista "
        "dei test, non su viste vere colorate."
    ),
))

QUOTA_COLORATA_AVVISO = _registra(Costante(
    nome="QUOTA_COLORATA_AVVISO",
    valore=0.05,
    origine=SCELTA,
    ragione=(
        "Quota di pixel colorati sopra la quale lo Studio avvisa che il "
        "modello leggera' i colori della vista come materiali (trappola nota "
        "in CLAUDE.md, verificata il 2026-10-27 con una falda viola). Il 5% "
        "lascia passare un cielo o un dettaglio colorato, e prende una "
        "facciata intera colorata per layer. E' un avviso, non un rifiuto."
    ),
))

STUDIO_CARICAMENTO_MASSIMO_MB = _registra(Costante(
    nome="STUDIO_CARICAMENTO_MASSIMO_MB",
    valore=50,
    origine=SCELTA,
    ragione=(
        "Peso massimo di una vista caricata nello Studio con Usa un'altra "
        "vista. Una vista di Allplan a 4k pesa pochi MB; 50 MB lascia passare "
        "un PNG grande senza far tenere in memoria al server locale un file "
        "qualunque trascinato per sbaglio. Il limite del servizio resta "
        "COMFY_INVIO_MASSIMO_MB, controllato prima dell'invio."
    ),
    unita=" MB",
))

VARIANTI_MASSIME = _registra(Costante(
    nome="VARIANTI_MASSIME",
    valore=4,
    origine=SCELTA,
    ragione=(
        "Quante varianti si possono chiedere con un Genera: ogni variante e' un "
        "lavoro in coda e un invio pagato. 4 viene dal mockup di Genera "
        "(«Varianti per invio 2-4», 2026-10-27): abbastanza per scegliere fra "
        "versioni dello stesso stile, poche perche' un clic non costi senza "
        "che lo si veda (con Nano Banana 2, circa 69 crediti)."
    ),
))

PASSI_AVVISO_DA_GENERAZIONE = _registra(Costante(
    nome="PASSI_AVVISO_DA_GENERAZIONE",
    valore=2,
    origine=SCELTA,
    ragione=(
        "Da quante generazioni di fila Studio · Passi avvisa che gli spigoli "
        "possono essersi spostati. 2 viene dalla decisione del 2026-10-28 "
        "(DESIGN.md, Studio · Passi): ogni giro ridisegna tutta l'immagine, "
        "quindi gia' il primo passo su un render puo' muovere l'edificio. "
        "Quanto si spostino davvero lo dira' il piano «catena» del banco di "
        "prova, e la soglia si tara li'."
    ),
))

RITOCCO_MODO_AREE = _registra(Costante(
    nome="RITOCCO_MODO_AREE",
    valore="contorni",
    origine=SCELTA,
    ragione=(
        "Come Studio · Ritocca manda le aree: «contorni» (contorni numerati "
        "disegnati sull'immagine) o «maschera» (l'immagine com'e' piu' una "
        "maschera come seconda immagine). Decide il piano «aree» del banco di "
        "prova: quale dei due tiene fermi i pixel fuori dalle aree. Al "
        "2026-10-30 il piano non e' ancora stato lanciato; «contorni» per ora "
        "solo perche' parte con un'immagine sola, quindi va anche con i "
        "modelli che non ne accettano due. Cambiare questo valore cambia solo i ritocchi "
        "nuovi: ognuno scrive il suo modo nel lavoro e nel passo."
    ),
))

# --- Banco di prova ----------------------------------------------------------

DIFFERENZA_PIXEL_SOGLIA = _registra(Costante(
    nome="DIFFERENZA_PIXEL_SOGLIA",
    valore=24,
    origine=SCELTA,
    ragione=(
        "Banco di prova, piano aree: di quanto (0-255, sul canale che cambia di "
        "piu') deve cambiare un pixel fuori dalle aree per contare come "
        "cambiato. Un modello che rigenera tutta l'immagine sposta comunque di "
        "qualche livello anche i pixel che non tocca, e una compressione JPEG "
        "aggiunge rumore: 24 lascia fuori quel rumore e prende un cambio che "
        "l'occhio vede. Mai tarato su un risultato vero."
    ),
))

AREE_BORDO_ESCLUSO_PX = _registra(Costante(
    nome="AREE_BORDO_ESCLUSO_PX",
    valore=8,
    origine=SCELTA,
    ragione=(
        "Banco di prova, piano aree: la fascia intorno a ogni area che non "
        "entra nella misura «fuori dalle aree». Sul bordo un modello sfuma la "
        "modifica, e contarlo farebbe sembrare violata un'area rispettata. Piu' "
        "largo di MASCHERA_SFUMATURA_PX, perche' qui non e' il motore a "
        "sfumare ma il modello."
    ),
    unita=" px",
))

CONTORNO_AREE_PX = _registra(Costante(
    nome="CONTORNO_AREE_PX",
    valore=6,
    origine=SCELTA,
    ragione=(
        "Spessore del contorno delle aree disegnato sull'immagine nel modo (a) "
        "del piano aree. Abbastanza spesso perche' il modello lo veda anche "
        "dopo il ridimensionamento interno a circa 1k di lato, non tanto da "
        "coprire gli spigoli dell'edificio."
    ),
    unita=" px",
))

SPIGOLI_SOGLIA = _registra(Costante(
    nome="SPIGOLI_SOGLIA",
    valore=40,
    origine=SCELTA,
    ragione=(
        "Banco di prova, misura grezza degli spigoli: un pixel e' spigolo se il "
        "filtro dei bordi di Pillow (FIND_EDGES, 0-255) lo da' sopra 40. Basso "
        "abbastanza per prendere gli spigoli di una vista shaded di Allplan, "
        "alto abbastanza per ignorare il rumore di un fondo uniforme. Provato "
        "solo su immagini sintetiche."
    ),
))

SPIGOLI_LATO_PX = _registra(Costante(
    nome="SPIGOLI_LATO_PX",
    valore=1024,
    origine=SCELTA,
    ragione=(
        "Banco di prova, misura grezza degli spigoli: vista e render si "
        "confrontano su copie di 1024 px di lato lungo. Sotto il lato dei "
        "render di Nano Banana 2 (1376), cosi' non si ingrandisce niente; "
        "abbastanza grande perche' uno spostamento di pochi pixel si veda. Con "
        "LATO_ANALISI_PX (384) uno spostamento di 10 px su una vista di 1536 "
        "non si vedeva (provato sulla vista dei test il 2026-10-29)."
    ),
    unita=" px",
))

SPIGOLI_TOLLERANZA_PX = _registra(Costante(
    nome="SPIGOLI_TOLLERANZA_PX",
    valore=2,
    origine=SCELTA,
    ragione=(
        "Banco di prova, misura grezza degli spigoli: uno spigolo della vista "
        "conta come ritrovato se nel render c'e' uno spigolo entro 2 px sulla "
        "copia di SPIGOLI_LATO_PX, circa 3 px su una vista di 1536. Meno di "
        "cosi' punirebbe il ricampionamento del modello; di piu' lascerebbe "
        "passare una finestra spostata."
    ),
    unita=" px",
))

MINIATURA_LARGHEZZA_PX = _registra(Costante(
    nome="MINIATURA_LARGHEZZA_PX",
    valore=384,
    origine=SCELTA,
    ragione=(
        "Larghezza della miniatura vera di un preset, ritagliata da un render "
        "del banco. Tre volte la tessera dello Studio (128 x 72), cosi' resta "
        "nitida su uno schermo ad alta densita'; in JPEG pesa poche decine di KB."
    ),
    unita=" px",
))

MINIATURA_ALTEZZA_PX = _registra(Costante(
    nome="MINIATURA_ALTEZZA_PX",
    valore=216,
    origine=SCELTA,
    ragione="Altezza della miniatura vera: 16:9 come la tessera dello Studio (vedi MINIATURA_LARGHEZZA_PX).",
    unita=" px",
))

# --- Palette v1 e processi vivi (prompt 7, 2026-10-31) ------------------------

BATTITO_INTERVALLO_SECONDI = _registra(Costante(
    nome="BATTITO_INTERVALLO_SECONDI",
    valore=1,
    origine=SCELTA,
    ragione=(
        "Ogni quanto la coda dei lavori e lo Studio riscrivono il loro file "
        "«sono vivo» in lavori/. Lo leggono la palette (deve sapere se c'e' gia' "
        "una coda prima di avviarne una) e la coda stessa (una seconda coda "
        "sulla stessa cartella metterebbe fra gli errori il lavoro in corso "
        "della prima). Un secondo: stesso ritmo di CODA_INTERVALLO_SECONDI."
    ),
    unita=" s",
))

BATTITO_SCADUTO_SECONDI = _registra(Costante(
    nome="BATTITO_SCADUTO_SECONDI",
    valore=5,
    origine=SCELTA,
    ragione=(
        "Dopo quanti secondi senza battito un processo si considera morto. "
        "Cinque battiti persi: abbastanza per un disco lento o un antivirus "
        "che tiene il file un attimo, abbastanza poco perche' la palette non "
        "aspetti a lungo prima di riavviare la coda dopo un crash."
    ),
    unita=" s",
))

PALETTE_IMMAGINI_DA_SCRIPT = _registra(Costante(
    nome="PALETTE_IMMAGINI_DA_SCRIPT",
    valore=False,
    origine=SCELTA,
    ragione=(
        "Se la palette di Allplan mostra la miniatura della vista e dell'ultimo "
        "render come immagine (Picture) cambiata da script. Lo dice la domanda "
        "1 della sonda della palette (PRD, sezione 9), mai lanciata al "
        "2026-10-31. Spenta, la palette scrive nome, dimensioni ed esito al "
        "posto dell'immagine: funziona in ogni caso. Si accende dopo che la "
        "sonda ha visto cambiare almeno una delle due immagini."
    ),
))

PALETTE_SECONDI_ATTESA_STUDIO = _registra(Costante(
    nome="PALETTE_SECONDI_ATTESA_STUDIO",
    valore=8,
    origine=SCELTA,
    ragione=(
        "Quanto la palette aspetta, dopo aver avviato lo Studio, che il suo "
        "battito compaia prima di dire che non e' partito. Il lavoro resta "
        "in coda comunque: l'attesa serve solo a dire la cosa giusta. Otto "
        "secondi: un Python a freddo con Pillow parte in uno o due, il resto "
        "e' margine per l'antivirus al primo avvio. Allplan e' fermo per "
        "questo tempo solo quando lo Studio non e' gia' aperto."
    ),
    unita=" s",
))
