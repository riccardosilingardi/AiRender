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

GEOMETRY_DRIFT_WARN = _registra(Costante(
    nome="GEOMETRY_DRIFT_WARN",
    valore=0.6,
    origine=SCELTA,
    ragione=(
        "Sotto questa quota di spigoli della vista ritrovati nel render, lo "
        "Studio avvisa che la geometria puo' essersi mossa. Non e' tarata: la "
        "misura e' grezza (ombre nuove, neve, vegetazione davanti contano come "
        "spigoli persi) e nessun render vero e' stato ancora giudicato a occhio "
        "accanto al numero. Si tara col banco, confrontando numero e giudizio."
    ),
))

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

STUDIO_PORTA = _registra(Costante(
    nome="STUDIO_PORTA",
    valore=47317,
    origine=SCELTA,
    ragione=(
        "La porta su cui lo Studio prova ad ascoltare, sempre la stessa. "
        "Con una porta scelta dal sistema, a ogni riavvio (per esempio dopo "
        "pacchetto.py --installa, che ferma lo Studio) la finestra di Edge "
        "rimasta aperta puntava a un indirizzo morto e diceva «server "
        "chiuso» per sempre (visto il 2026-11-04). Con la porta fissa la "
        "finestra si ricollega da sola. 47317 e' un numero qualunque fuori "
        "dalle porte note; se e' occupata lo Studio ne prende una dal sistema."
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

CAMBIA_SCELTE_MASSIME = _registra(Costante(
    nome="CAMBIA_SCELTE_MASSIME",
    valore=6,
    origine=SCELTA,
    ragione=(
        "Quante miniature di Cambia (ora del giorno, tempo e mood) si possono "
        "scegliere per un clic: ogni miniatura e' un passo, un invio e un "
        "credito. 6 e' una riga intera di «Ora del giorno»: abbastanza per "
        "confrontare le ore di una giornata nella griglia, pochi perche' un "
        "clic sbagliato non costi una dozzina di render. Giudizio del "
        "2026-11-09, mai provato da un cliente."
    ),
))

RICETTA_VISTE_MASSIME = _registra(Costante(
    nome="RICETTA_VISTE_MASSIME",
    valore=6,
    origine=SCELTA,
    ragione=(
        "Su quante viste si rifa' una ricetta con un clic: ogni vista e' un "
        "render, un invio e un credito. 6 come le miniature di Cambia: "
        "abbastanza per i fotogrammi di un video o per le viste di una "
        "tavola, pochi perche' un clic non costi una dozzina di render senza "
        "che lo si veda. Giudizio del 2026-11-09, mai provato da un cliente."
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

FINALE_INGRANDIMENTI = _registra(Costante(
    nome="FINALE_INGRANDIMENTI",
    valore=(2, 4),
    origine=SCELTA,
    ragione=(
        "Di quante volte «Finale» puo' ingrandire un render (Magnific "
        "Precision V2 dal Router, scale_factor da 2 a 16). Un render di Nano "
        "Banana 2 a 2K diventa 4K con 2 e 8K con 4: oltre, il file e' troppo "
        "grande per una tavola e il costo cresce con la misura. Giudizio del "
        "2026-11-04, nessun Finale ancora fatto."
    ),
))

FINALE_INGRANDIMENTO_PREDEFINITO = _registra(Costante(
    nome="FINALE_INGRANDIMENTO_PREDEFINITO",
    valore=2,
    origine=SCELTA,
    ragione=(
        "L'ingrandimento proposto da «Finale»: il piu' piccolo, che costa "
        "meno e basta per una tavola A3. Giudizio, non misurato."
    ),
))

ESEMPI_STILE_MASSIMO = _registra(Costante(
    nome="ESEMPI_STILE_MASSIMO",
    valore=4,
    origine=SCELTA,
    ragione=(
        "Quanti render d'esempio partono al massimo con «Stile da esempi», "
        "riferimento per lo stile compreso. Riccardo ne porterebbe 3 o 4 "
        "(2026-11-04); di piu' allunga l'invio senza che il modello ne tenga "
        "conto meglio, e con 15 o piu' immagini serve un LoRA, non dei "
        "riferimenti. Giudizio, mai provato con il modello."
    ),
))

INSERTI_MASSIMO = _registra(Costante(
    nome="INSERTI_MASSIMO",
    valore=4,
    origine=SCELTA,
    ragione=(
        "Quante immagini di oggetti o persone da inserire (Rif. 1, 2, ...) "
        "partono al massimo con un invio di Genera, Cambia o Ritocca. Nano "
        "Banana 2 e Pro accettano fino a 14 immagini, ma con piu' di quattro "
        "oggetti diversi in una volta il modello li confonde piu' facilmente "
        "e il testo per dire dove va ciascuno diventa lungo. 4 e' un giudizio "
        "del 2026-11-04, mai provato con il modello."
    ),
))

# --- Inserisci nel contesto -------------------------------------------------

CONTESTO_INQUADRATURA_PREDEFINITA = _registra(Costante(
    nome="CONTESTO_INQUADRATURA_PREDEFINITA",
    valore="zenitale",
    origine=SCELTA,
    ragione=(
        "L'inquadratura con cui si apre la scena «Inserisci nel contesto»: "
        "«zenitale» (vista dall'alto, come uno screenshot satellitare) o "
        "«volo» (volo d'uccello, obliqua). Zenitale perche' e' il caso piu' "
        "comune nel flusso di Riccardo (screenshot da Google Earth, "
        "2026-11-01) e perche' la vista Allplan in pianta e' la piu' facile "
        "da far combaciare. Nessuna delle due e' provata con il modello."
    ),
))

CONTESTO_LUOGO_MASSIMO = _registra(Costante(
    nome="CONTESTO_LUOGO_MASSIMO",
    valore=200,
    origine=SCELTA,
    ragione=(
        "Quanti caratteri al massimo per il luogo (indirizzo o coordinate) "
        "che entra nel prompt di «Inserisci nel contesto». Un indirizzo con "
        "coordinate sta in 100 caratteri; 200 lasciano margine senza far "
        "diventare il campo un secondo prompt."
    ),
    unita=" caratteri",
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

RITOCCO_INCOLLA_MARGINE_PX = _registra(Costante(
    nome="RITOCCO_INCOLLA_MARGINE_PX",
    valore=8,
    origine=SCELTA,
    ragione=(
        "Studio · Ritocca: di quanto si allarga ogni area quando il risultato "
        "del modello si incolla sull'immagine di prima. Il modello sfuma la "
        "modifica sul bordo dell'area (vedi AREE_BORDO_ESCLUSO_PX, stesso "
        "valore): senza margine una persona messa sul bordo resterebbe "
        "tagliata. Decisione di Riccardo del 2026-11-02: fuori dalle aree non "
        "deve sparire niente. Mai tarato su un ritocco vero."
    ),
    unita=" px",
))

RITOCCO_INCOLLA_SFUMATURA_PX = _registra(Costante(
    nome="RITOCCO_INCOLLA_SFUMATURA_PX",
    valore=6,
    origine=SCELTA,
    ragione=(
        "Studio · Ritocca: raggio della sfocatura del bordo della zona "
        "incollata. Un bordo netto lascia una cucitura visibile fra il ritocco "
        "e l'immagine di prima; troppo largo e il ritocco si mescola col resto. "
        "Piu' largo di MASCHERA_SFUMATURA_PX perche' qui si incolla un'immagine "
        "che il modello ha ridisegnato tutta, con toni che possono scostarsi. "
        "Mai tarato su un ritocco vero."
    ),
    unita=" px",
))

PENNELLO_SPESSORE = _registra(Costante(
    nome="PENNELLO_SPESSORE",
    valore=0.04,
    origine=SCELTA,
    ragione=(
        "Studio · Ritocca: lo spessore iniziale dei pennelli aggiungi e "
        "togli, in frazione della larghezza del render (0,04 = 4%: su un "
        "render largo 2000 px, un tratto di 80 px). Abbastanza largo per "
        "coprire una persona o un palo con un tratto, abbastanza stretto da "
        "non prendere la facciata accanto. Giudizio del 2026-11-09 dal "
        "mockup, mai provato su un ritocco vero; si cambia col cursore."
    ),
))

PENNELLO_SPESSORI = _registra(Costante(
    nome="PENNELLO_SPESSORI",
    valore=(0.01, 0.15),
    origine=SCELTA,
    ragione=(
        "Studio · Ritocca: lo spessore piu' sottile e piu' grosso del "
        "cursore dei pennelli, in frazione della larghezza del render. Sotto "
        "l'1% il tratto e' piu' sottile del contorno disegnato per il "
        "modello; sopra il 15% conviene un rettangolo. Giudizio del "
        "2026-11-09."
    ),
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

ESPORTA_QUALITA_JPEG = _registra(Costante(
    nome="ESPORTA_QUALITA_JPEG",
    valore=92,
    origine=SCELTA,
    ragione=(
        "Qualita' del JPEG di Esporta per il cliente (Pillow, 1-95), senza "
        "sottocampionamento del colore. 92 e' la soglia comune oltre la quale "
        "il file cresce molto senza differenze visibili; chi vuole i pixel "
        "esatti sceglie PNG o PSD. Non confrontata a occhio su un render vero."
    ),
))

# --- video (Studio · Video, 2026-11-01) --------------------------------------

VIDEO_DURATE_SECONDI = _registra(Costante(
    nome="VIDEO_DURATE_SECONDI",
    valore=(5, 10, 15, 20, 30),
    origine=SCELTA,
    ragione=(
        "Le durate offerte nella scheda Video. Seedance 2.5 accetta da 4 a 30 "
        "secondi (documentazione del Router). Il 2026-11-02 Riccardo ha chiesto "
        "video piu' lunghi: si offre fino al massimo del servizio, 30. Piu' "
        "lungo costa di piu' e la geometria ha piu' tempo per sciogliersi. "
        "Costo non misurato: lo dira' il primo video."
    ),
    unita=" s",
))

VIDEO_RISOLUZIONI = _registra(Costante(
    nome="VIDEO_RISOLUZIONI",
    valore=("720p", "1080p"),
    origine=SCELTA,
    ragione=(
        "Le risoluzioni offerte. Seedance 2.5 fa 480p, 720p e 1080p: 480p e' "
        "troppo poco per mostrare un progetto; 720p e' il predefinito del "
        "servizio e costa meno."
    ),
))

VIDEO_RIFERIMENTI_MASSIMI = _registra(Costante(
    nome="VIDEO_RIFERIMENTI_MASSIMI",
    valore=4,
    origine=SCELTA,
    ragione=(
        "Quanti render al massimo in «Piu' render come riferimento». Il "
        "servizio non dichiara un limite chiaro per Seedance 2.5; 4 viste "
        "dello stesso edificio bastano a descriverlo e tengono l'invio sotto "
        "il peso massimo."
    ),
))

VIDEO_ATTESA_MASSIMA_SECONDI = _registra(Costante(
    nome="VIDEO_ATTESA_MASSIMA_SECONDI",
    valore=1200,
    origine=SCELTA,
    ragione=(
        "Tempo concesso a un video prima di dichiararlo non riuscito. Un video "
        "ci mette minuti, non secondi (ATTESA_MASSIMA_SECONDI vale per le "
        "immagini). Non misurato: nessun video e' ancora stato fatto."
    ),
    unita=" s",
))


# --- color map (mappa materiali, 2026-11-01) ----------------------------------

COLORMAP_AREA_MINIMA_PERCENTO = _registra(Costante(
    nome="COLORMAP_AREA_MINIMA_PERCENTO",
    valore=0.5,
    origine=SCELTA,
    ragione=(
        "Sotto questa parte dell'immagine una zona della segmentazione si "
        "scarta: su una vista 1920×1080 lo 0,5% sono circa 10.000 pixel, "
        "un pezzo di facciata che si vede. Le zone piu' piccole sono quasi "
        "sempre briciole di SAM2 automatico, e un colore in piu' per ognuna "
        "confonde il modello. Non misurato: lo dira' la prima segmentazione vera."
    ),
    unita="%",
))

COLORMAP_ZONE_MASSIME = _registra(Costante(
    nome="COLORMAP_ZONE_MASSIME",
    valore=12,
    origine=SCELTA,
    ragione=(
        "Quante zone al massimo in una color map: si tengono le piu' grandi. "
        "Una vista di architettura ha raramente piu' di una dozzina di "
        "materiali che contano, e ogni colore in piu' e' una frase in piu' nel "
        "prompt. Deve restare sotto i 16 colori della tavolozza di core/colormap.py."
    ),
))

COLORMAP_COLORI_IN_INGRESSO_MASSIMI = _registra(Costante(
    nome="COLORMAP_COLORI_IN_INGRESSO_MASSIMI",
    valore=256,
    origine=SCELTA,
    ragione=(
        "Un'immagine di segmentazione a colori piatti con piu' colori di cosi' "
        "non e' una segmentazione: e' una foto o un JPEG che ha sporcato i "
        "bordi. OneFormer ADE20K ha 150 classi, quindi 256 basta e avanza."
    ),
))


# --- materiali del progetto Allplan (2026-11-02) -------------------------------

MATERIALI_CAMBIATI_MASSIMI = _registra(Costante(
    nome="MATERIALI_CAMBIATI_MASSIMI",
    valore=5,
    origine=SCELTA,
    ragione=(
        "Quanti materiali di Allplan si cambiano al massimo in un invio. Ogni "
        "materiale porta fino a due immagini (l'anteprima di Allplan e la "
        "foto di riferimento): con 5 materiali, la vista e il riferimento per "
        "lo stile sono 12 immagini, sotto le 14 che Gemini dichiara per un "
        "invio. Non misurato quanti materiali il modello tiene distinti."
    ),
))


# --- vendita: licenze e crediti AIRENDER (2026-11-02) --------------------------
#
# Il listino vive qui e solo qui. Il server (server/) lo legge da
# server/listino.json, che si riscrive con `python scripts/scrivi_listino.py`
# e che tests/test_listino.py confronta con questo: se divergono, la suite
# lo dice.

NANO_BANANA_2 = "vertexai/gemini-3.1-flash-image"
NANO_BANANA_PRO = "vertexai/gemini-3-pro-image"

LINK_ACCESSO_MINUTI = _registra(Costante(
    nome="LINK_ACCESSO_MINUTI",
    valore=15,
    origine=SCELTA,
    ragione=(
        "Quanto vale il link di accesso alla web app mandato per email: "
        "abbastanza per aprire la posta e cliccare, poco per chi trovasse "
        "l'email dopo. Si usa una volta sola."
    ),
    unita=" min",
))

LINK_ACCESSO_MASSIMI_ORA = _registra(Costante(
    nome="LINK_ACCESSO_MASSIMI_ORA",
    valore=5,
    origine=SCELTA,
    ragione=(
        "Quanti link di accesso parte al massimo per licenza in un'ora: chi "
        "scrive l'email di un altro non gli riempie la casella."
    ),
))

LISTINO = _registra(Costante(
    nome="LISTINO",
    valore={
        "versione": "2026-11-05",
        "valuta": "EUR",
        "iva": "esclusa",
        # Quanti render costa un invio, per modello e grandezza. Un modello che
        # non e' qui non parte coi crediti AIRENDER: serve la chiave propria.
        "pesi": {
            NANO_BANANA_2: {"1K": 1, "2K": 1, "4K": 2},
            NANO_BANANA_PRO: {"1K": 2, "2K": 2, "4K": 3},
        },
        # Pesi delle azioni che non sono un invio a Nano Banana. Finale e video
        # il server non li inoltra ancora coi crediti AIRENDER (il router
        # legge solo corpi Gemini); «Tieni la geometria» si' (geometria.mjs).
        # Stanno qui perche' il prezzo si decide in un posto solo.
        # Regola: ogni credito costa ad AIRENDER al massimo 0,09 EUR.
        # Finale x2 ~36 crediti Comfy (~0,15 EUR); x4 non misurato.
        # Video Seedance 2.5 1080p 5 s ~865 crediti Comfy (~3,60 EUR, stima
        # del listino Comfy) = ~0,72 EUR/s -> 8 crediti al secondo; 720p
        # stimato a meta' -> 4 al secondo. Nessuno dei due e' misurato.
        # «Tieni la geometria»: la prima passata col ControlNet sulla Comfy
        # Developer Platform, in piu' del render di Nano Banana che segue.
        # PROVVISORIO (2026-11-06): il costo a secondi di GPU del deployment
        # non e' ancora letto; Z-Image-Turbo a 8 passi e 1536 px e' qualche
        # secondo di GPU, una macchina fredda di piu'. Si rivede alla prima
        # fattura del deployment.
        "pesi_azioni": {
            "finale_x2": 2,
            "finale_x4": 4,
            "tieni_geometria": 1,
            "video_720p_al_secondo": 4,
            "video_1080p_al_secondo": 8,
        },
        "benvenuto": {"render": 10, "validita_mesi": 12},
        # Quanti render tornati SENZA immagine (Gemini rifiuta o risponde solo
        # testo) si rimborsano per licenza nelle ultime 24 ore; oltre, il
        # render vuoto si scala come uno riuscito (server, migrazione 005).
        # SCELTA (2026-11-10), non misurata: un uso onesto ne vede pochi
        # (anche 100 render in un giorno con il 5% di rifiuti fanno 5), quindi
        # 10 non tocca mai chi lavora; chi provoca apposta risposte vuote
        # costa ad AIRENDER al massimo 10 render al giorno per licenza invece
        # che senza limite. Non conta gli invii che il Router rifiuta ne' i
        # lavori fermati dal cliente: quelli si rimborsano sempre. Se Comfy non
        # fa pagare i risultati vuoti (da leggere in x-comfy-credits-used) il
        # tetto si puo' alzare.
        "rimborsi_senza_immagine_24h": 10,
        # "prompt_completo": il cliente vede e riscrive il prompt in inglese
        # («Avanzate» dello Studio). Solo Pro e Studio: chi compra il risultato
        # non ha bisogno del testo, e un testo in vista si copia (Riccardo,
        # 2026-11-05). E' una scelta di prodotto, non una misura.
        #
        # "funzioni": cosa apre il piano nello Studio. AIRENDER nasce per
        # Allplan (Riccardo, 2026-11-05): il plugin e' in tutti i piani e i
        # piani si dividono per qualita' e funzioni, non per canale. La
        # tabella materiali e' in Base perche' e' quello che l'AI Visualizer
        # di Allplan non fa. video = None: niente video; altrimenti la
        # risoluzione e la durata massime.
        "piani": {
            "prova": {
                "nome": "Prova", "tipo": "una_tantum", "prezzo": 15,
                "render": 50, "validita_mesi": 12, "postazioni": 1,
                "modelli": [NANO_BANANA_2, NANO_BANANA_PRO], "dimensione_massima": "4K",
                "canali": ["web", "plugin"], "studio": True, "prompt_completo": False,
                "funzioni": {
                    "varianti_massime": 4, "riferimenti_massimi": 4, "materiali": True,
                    "scene": True, "finale": True, "stile_da_esempi": True,
                    "video": {"risoluzione_massima": "720p", "secondi_massimi": 10},
                    "tieni_geometria": False, "crea_stile": False,
                },
            },
            "base": {
                "nome": "Base", "tipo": "abbonamento", "prezzo_mese": 19, "prezzo_anno": 190,
                "render_mese": 80, "postazioni": 1,
                "modelli": [NANO_BANANA_2], "dimensione_massima": "2K",
                "canali": ["web", "plugin"], "studio": True, "prompt_completo": False,
                "funzioni": {
                    "varianti_massime": 2, "riferimenti_massimi": 1, "materiali": True,
                    "scene": False, "finale": False, "stile_da_esempi": False,
                    "video": None, "tieni_geometria": False, "crea_stile": False,
                },
            },
            "pro": {
                "nome": "Pro", "tipo": "abbonamento", "prezzo_mese": 39, "prezzo_anno": 390,
                "render_mese": 200, "postazioni": 1,
                "modelli": [NANO_BANANA_2, NANO_BANANA_PRO], "dimensione_massima": "4K",
                "canali": ["web", "plugin"], "studio": True, "prompt_completo": True,
                "funzioni": {
                    "varianti_massime": 4, "riferimenti_massimi": 4, "materiali": True,
                    "scene": True, "finale": True, "stile_da_esempi": True,
                    "video": {"risoluzione_massima": "720p", "secondi_massimi": 10},
                    "tieni_geometria": False, "crea_stile": False,
                },
            },
            "studio": {
                "nome": "Studio", "tipo": "abbonamento", "prezzo_mese": 99, "prezzo_anno": 990,
                "render_mese": 600, "postazioni": 3,
                "modelli": [NANO_BANANA_2, NANO_BANANA_PRO], "dimensione_massima": "4K",
                "canali": ["web", "plugin"], "studio": True, "prompt_completo": True,
                "funzioni": {
                    "varianti_massime": 4, "riferimenti_massimi": 4, "materiali": True,
                    "scene": True, "finale": True, "stile_da_esempi": True,
                    "video": {"risoluzione_massima": "1080p", "secondi_massimi": 30},
                    "tieni_geometria": True, "crea_stile": True,
                },
            },
            # Abbonamento finito: restano i crediti di ricarica e benvenuto,
            # con le funzioni di Base.
            "nessuno": {
                "nome": "Senza abbonamento", "tipo": "nessuno", "postazioni": 1,
                "modelli": [NANO_BANANA_2], "dimensione_massima": "2K",
                "canali": ["web", "plugin"], "studio": True, "prompt_completo": False,
                "funzioni": {
                    "varianti_massime": 2, "riferimenti_massimi": 1, "materiali": True,
                    "scene": False, "finale": False, "stile_da_esempi": False,
                    "video": None, "tieni_geometria": False, "crea_stile": False,
                },
            },
        },
        "ricarica": {"nome": "Ricarica", "prezzo": 10, "render": 100, "validita_mesi": 12},
        "rivendita": {"sconto_segnalazione": 20, "sconto_rivenditore": 30},
        # Non sono prezzi: viaggiano qui perche' il listino e' l'unica strada
        # da core/config.py al server (LINK_ACCESSO_*, sopra).
        "accesso": {"link_minuti": LINK_ACCESSO_MINUTI, "link_massimi_ora": LINK_ACCESSO_MASSIMI_ORA},
    },
    origine=SCELTA,
    ragione=(
        "Prezzi decisi il 2026-11-02, piani rivisti il 2026-11-05 (thread "
        "«Definire i piani e le funzioni incluse»): ipotesi da pilota, non "
        "misurate sul mercato. I pesi seguono il costo vero: Nano Banana 2 "
        "circa 0,07 EUR a render (17,17 crediti Comfy, misurato), Pro circa il "
        "doppio, 4K circa una volta e mezza (listino Comfy e prezzi Google, "
        "stime). Ogni credito costa al massimo ~0,09 EUR: a 10 EUR per 100 la "
        "ricarica rende ~6%; i prezzi si decidono nel thread del posizionamento "
        "rispetto ai concorrenti e qui non cambiano. Annuale = 10 mensilita'. "
        "Il plugin Allplan e' in tutti i piani (AIRENDER nasce per Allplan); "
        "Base e' Nano Banana 2 fino a 2K con Ritocca, Ricetta e tabella "
        "materiali; Pro aggiunge Pro, 4K, scene, Finale e video a 720p fino a "
        "10 s; Studio 3 postazioni, video 1080p e le funzioni a due invii. "
        "L'annuale accredita 12 mesi di render in un lotto solo; i render del "
        "piano non si sommano da un mese all'altro."
    ),
))

SERVER_AIRENDER = _registra(Costante(
    nome="SERVER_AIRENDER",
    valore="https://airender-server.netlify.app",
    origine=SCELTA,
    ragione=(
        "Indirizzo del server AIRENDER (funzioni Netlify) che riceve la vista "
        "con il codice licenza e la passa al Comfy Router con la chiave di "
        "Riccardo. Progetto Netlify airender-server, online dal 2026-11-06. "
        "Quando ci sara' un dominio proprio si cambia qui o con la variabile "
        "d'ambiente AIRENDER_SERVER."
    ),
))

SERVER_CORPO_MASSIMO_MB = _registra(Costante(
    nome="SERVER_CORPO_MASSIMO_MB",
    valore=5.5,
    origine=VINCOLO,
    ragione=(
        "Quanto puo' pesare in tutto un invio al server AIRENDER: vista e "
        "immagini in piu' (riferimenti, materiali) in base64. Il limite vero "
        "e' 6 MB per richiesta a una funzione Netlify; mezzo MB resta al "
        "testo e al JSON. Sopra, Netlify risponde 413 senza dire perche'."
    ),
    unita=" MB",
))

SERVER_RIDUZIONE_LATI_PX = _registra(Costante(
    nome="SERVER_RIDUZIONE_LATI_PX",
    valore=(1536, 1024, 768),
    origine=SCELTA,
    ragione=(
        "Se l'invio supera SERVER_CORPO_MASSIMO_MB, le immagini in piu' (mai "
        "la vista) si rimpiccioliscono a questo lato lungo, un gradino alla "
        "volta, finche' il totale ci sta. Un riferimento di stile o di "
        "materiale a 1536 px porta ancora tutto quello che il modello legge."
    ),
    unita=" px",
))

SERVER_INVIO_MASSIMO_MB = _registra(Costante(
    nome="SERVER_INVIO_MASSIMO_MB",
    valore=4,
    origine=VINCOLO,
    ragione=(
        "Una funzione Netlify accetta al massimo 6 MB di corpo (docs.netlify.com, "
        "limiti delle funzioni). La vista viaggia in base64, che pesa un terzo "
        "in piu': 4 MB di immagine diventano circa 5,4 MB di richiesta. Mai "
        "provato con una vista vera a 4K."
    ),
    unita=" MB",
))

# --- «Tieni la geometria»: ControlNet prima di Nano Banana --------------------

GEOMETRIA_FORZA = _registra(Costante(
    nome="GEOMETRIA_FORZA",
    valore=0.8,
    origine=SCELTA,
    ragione=(
        "Quanto il ControlNet sugli spigoli comanda Z-Image-Turbo nella prima "
        "passata di «Tieni la geometria» (strength di QwenImageDiffsynthControlnet, "
        "il modello comfy.org usa 1). Un po' sotto 1 perche' gli spigoli di una "
        "vista Allplan sono anche quelli dei retini e dei giunti, e a 1 il "
        "render li ricalca come righe. Giudizio del 2026-11-04, nessun render fatto."
    ),
))

GEOMETRIA_FORZA_PROFONDITA = _registra(Costante(
    nome="GEOMETRIA_FORZA_PROFONDITA",
    valore=0.6,
    origine=SCELTA,
    ragione=(
        "Quanto comanda il controllo «Profondita'» (mappa di profondita' stimata "
        "con Depth Anything V2) nella prima passata. Tiene volumi, piani e "
        "prospettiva, non i dettagli: sotto gli Spigoli perche' insieme non "
        "irrigidiscano il render. Giudizio del 2026-11-09, nessun render fatto."
    ),
))

GEOMETRIA_FORZA_LINEE = _registra(Costante(
    nome="GEOMETRIA_FORZA_LINEE",
    valore=0.7,
    origine=SCELTA,
    ragione=(
        "Quanto comanda il controllo «Linee dritte» (M-LSD, solo segmenti "
        "dritti) nella prima passata. Ignora retini e texture, quindi regge una "
        "forza vicina agli Spigoli. Giudizio del 2026-11-09, nessun render fatto."
    ),
))

GEOMETRIA_RIAGGANCIA_DENOISE = _registra(Costante(
    nome="GEOMETRIA_RIAGGANCIA_DENOISE",
    valore=0.35,
    origine=SCELTA,
    ragione=(
        "«Riaggancia alla vista»: quanto del render si rifa' nella passata col "
        "ControlNet guidata dalla vista (1 = tutto da capo, 0 = niente). Basso "
        "perche' luce e materiali del render restino e si spostino solo le "
        "linee. Fra 0.3 e 0.4 nelle guide di img2img per architettura; "
        "giudizio del 2026-11-10, nessun render fatto."
    ),
))

GEOMETRIA_PASSI = _registra(Costante(
    nome="GEOMETRIA_PASSI",
    valore=8,
    origine=SCELTA,
    ragione=(
        "I passi del campionatore nella prima passata: 8 e' quello del modello "
        "comfy.org per Z-Image-Turbo, che e' fatto per pochi passi. Il costo su "
        "Comfy Cloud va a secondi di GPU, e piu' passi costano di piu'. Non misurato."
    ),
))

GEOMETRIA_LATO_MASSIMO = _registra(Costante(
    nome="GEOMETRIA_LATO_MASSIMO",
    valore=1536,
    origine=SCELTA,
    ragione=(
        "Il lato lungo, in pixel, a cui si porta la vista prima di estrarne gli "
        "spigoli. Il modello comfy.org avverte sopra i 2500; 1536 tiene i "
        "dettagli di una facciata e resta veloce. Nano Banana poi rifa' la "
        "misura del render. Giudizio, non misurato."
    ),
))

GEOMETRIA_ATTESA_SECONDI = _registra(Costante(
    nome="GEOMETRIA_ATTESA_SECONDI",
    valore=600,
    origine=SCELTA,
    ragione=(
        "Quanto si aspetta al massimo la prima passata su Comfy Cloud prima di "
        "fermare il lavoro. Una macchina fredda carica circa 20 GB di modelli "
        "(Z-Image-Turbo, il codificatore Qwen e il ControlNet) prima di partire. "
        "Dieci minuti e' un margine scelto, non misurato."
    ),
))

GEOMETRIA_INTERVALLO_SECONDI = _registra(Costante(
    nome="GEOMETRIA_INTERVALLO_SECONDI",
    valore=3,
    origine=SCELTA,
    ragione=(
        "Ogni quanto si chiede a Comfy Cloud se la prima passata e' finita. "
        "Compromesso fra quanto presto si vede il risultato e quante richieste "
        "partono; l'API v2 non ha un webhook per i lavori. Scelto."
    ),
))

# --- Regola: luce e colore prima di esportare (2026-11-09) --------------------
# Cursori come quelli di Photoshop o Lightroom, sul computer dell'utente: nessuna
# immagine parte e non si spendono crediti. Tutti i valori sono giudizi presi
# dall'abitudine di quei programmi, non confrontati su render veri.

REGOLA_CURSORE_MASSIMO = _registra(Costante(
    nome="REGOLA_CURSORE_MASSIMO",
    valore=100,
    origine=SCELTA,
    ragione=(
        "I cursori di Regola vanno da meno questo a piu' questo, con lo zero "
        "al centro che non cambia niente. Cento passi come Lightroom: abbastanza "
        "fini col mouse, un numero facile da ricordare e da scrivere."
    ),
))

REGOLA_ESPOSIZIONE_STOP = _registra(Costante(
    nome="REGOLA_ESPOSIZIONE_STOP",
    valore=1.0,
    origine=SCELTA,
    ragione=(
        "Quanti stop (raddoppi della luce) da' l'Esposizione a fondo cursore. "
        "Si moltiplica la luce lineare, come una macchina fotografica. Un render "
        "esce gia' esposto: piu' di un diaframma serve di rado, e un cursore "
        "piu' ampio diventa troppo sensibile. Scelto, non misurato."
    ),
    unita=" stop",
))

REGOLA_CONTRASTO_FORZA = _registra(Costante(
    nome="REGOLA_CONTRASTO_FORZA",
    valore=0.8,
    origine=SCELTA,
    ragione=(
        "Il Contrasto e' una curva a S attorno al grigio medio, x^g / (x^g + "
        "(1-x)^g), con g = 2 elevato a (cursore/100 * questo). Con 0,8 a fondo "
        "g vale circa 1,74 (piu' contrasto) o 0,57 (meno): forte ma senza "
        "bruciare. Neri e bianchi restano al loro posto. Scelto a occhio "
        "sulla curva, non su un render."
    ),
))

REGOLA_LUCI_OMBRE_AMPIEZZA = _registra(Costante(
    nome="REGOLA_LUCI_OMBRE_AMPIEZZA",
    valore=0.12,
    origine=SCELTA,
    ragione=(
        "Di quanto Luci e Ombre spostano al massimo un tono (su 1), a meta' "
        "della loro meta' di toni: Luci tocca solo i toni sopra il grigio "
        "medio, Ombre solo quelli sotto. Sopra 0,125 la curva si piegherebbe "
        "all'indietro (un tono piu' chiaro diventerebbe piu' scuro di uno meno "
        "chiaro): 0,12 resta sotto. E' una curva uguale su tutta l'immagine, "
        "non il recupero locale di Photoshop. Scelto."
    ),
))

REGOLA_TEMPERATURA_FORZA = _registra(Costante(
    nome="REGOLA_TEMPERATURA_FORZA",
    valore=0.12,
    origine=SCELTA,
    ragione=(
        "La Temperatura a fondo cursore alza il rosso e abbassa il blu (o il "
        "contrario) di questa frazione. Il 12% scalda o raffredda in modo "
        "chiaro senza dare una dominante da filtro. Non e' in kelvin: il "
        "render non sa a che luce e' stato fatto. Scelto."
    ),
))

REGOLA_SATURAZIONE_MASSIMA = _registra(Costante(
    nome="REGOLA_SATURAZIONE_MASSIMA",
    valore=1.0,
    origine=SCELTA,
    ragione=(
        "Quanto colore in piu' da' la Saturazione a fondo cursore: 1 vuol dire "
        "il doppio. All'altro capo l'immagine diventa in bianco e nero. Come "
        "il cursore di Lightroom; scelto, non misurato."
    ),
))

REGOLA_CURVA_PUNTI_MASSIMI = _registra(Costante(
    nome="REGOLA_CURVA_PUNTI_MASSIMI",
    valore=8,
    origine=SCELTA,
    ragione=(
        "Quanti punti al massimo sulla curva, estremi compresi. Una curva a S o "
        "un ritocco dei soli neri ne chiedono tre o quattro; con piu' di otto "
        "la curva ondeggia e il cielo si riempie di bande. Scelto."
    ),
))

REGOLA_ANTEPRIMA_LATO_PX = _registra(Costante(
    nome="REGOLA_ANTEPRIMA_LATO_PX",
    valore=1600,
    origine=SCELTA,
    ragione=(
        "Il lato lungo dell'anteprima mentre si muovono i cursori. Il file "
        "esportato e' sempre alla grandezza del render; l'anteprima e' piu' "
        "piccola perche' si rifa' a ogni movimento, anche nella web app dove "
        "Python gira nel browser. 1600 riempie il palco dello Studio. Scelto, "
        "tempi non misurati."
    ),
    unita=" px",
))

# --- punto di vista dalla pianta (bozza 16, flusso 7) ---------------------------

PUNTO_DI_VISTA_ALTEZZA_OCCHI_M = _registra(Costante(
    nome="PUNTO_DI_VISTA_ALTEZZA_OCCHI_M",
    valore="1.6",
    origine=SCELTA,
    ragione=(
        "L'altezza degli occhi della camera che il modello mette sulla pianta: "
        "una persona in piedi. E' una stringa perche' entra cosi' nel prompt. "
        "Scelta, come nel piano Flussi del 2026-11-08."
    ),
    unita=" m",
))

PUNTO_DI_VISTA_ALTEZZA_SOFFITTO_M = _registra(Costante(
    nome="PUNTO_DI_VISTA_ALTEZZA_SOFFITTO_M",
    valore="2.7",
    origine=SCELTA,
    ragione=(
        "L'altezza del soffitto quando la pianta non la dice: un piano "
        "abitativo. Senza Allplan il modello la immagina, e lo Studio scrive "
        "sull'immagine «stanza immaginata dalla pianta». Scelta."
    ),
    unita=" m",
))

PUNTO_DI_VISTA_APERTURA_GRADI = _registra(Costante(
    nome="PUNTO_DI_VISTA_APERTURA_GRADI",
    valore=60,
    origine=SCELTA,
    ragione=(
        "Quanto e' aperto il cono rosso disegnato sulla pianta: circa il campo "
        "orizzontale di un 24 mm. Il modello lo legge come direzione, non come "
        "ottica precisa: non e' misurato su un render."
    ),
    unita=" gradi",
))

PUNTO_DI_VISTA_CONO_LATO = _registra(Costante(
    nome="PUNTO_DI_VISTA_CONO_LATO",
    valore=0.18,
    origine=SCELTA,
    ragione=(
        "Lunghezza del cono rosso, in frazione del lato lungo della pianta: "
        "abbastanza per leggere la direzione, abbastanza corto da non coprire "
        "la stanza che si guarda. Scelta."
    ),
))

PUNTO_DI_VISTA_RAGGIO = _registra(Costante(
    nome="PUNTO_DI_VISTA_RAGGIO",
    valore=0.012,
    origine=SCELTA,
    ragione=(
        "Raggio del punto rosso, in frazione del lato lungo della pianta: "
        "visibile su una pianta di 2000 px senza coprire una porta. Scelta."
    ),
))

PUNTO_DI_VISTA_ROSSO = _registra(Costante(
    nome="PUNTO_DI_VISTA_ROSSO",
    valore=(230, 30, 30),
    origine=SCELTA,
    ragione=(
        "Il rosso del punto e del cono. Il prompt dice «red dot and red cone»: "
        "un rosso pieno che una pianta non usa per muri o pavimenti. Scelto."
    ),
))

PUNTO_DI_VISTA_CONO_OPACITA = _registra(Costante(
    nome="PUNTO_DI_VISTA_CONO_OPACITA",
    valore=110,
    origine=SCELTA,
    ragione=(
        "Opacita' del cono, da 0 a 255: sotto il rosso si vedono ancora muri e "
        "arredi che la camera guarda. Scelta."
    ),
))

PUNTO_DI_VISTA_TRASCINA_MINIMO = _registra(Costante(
    nome="PUNTO_DI_VISTA_TRASCINA_MINIMO",
    valore=0.02,
    origine=SCELTA,
    ragione=(
        "Sotto questa distanza (frazione della pianta) fra dove stai e verso "
        "dove guardi, il trascinamento e' un clic: la direzione non si legge e "
        "lo Studio la chiede di nuovo. Scelta."
    ),
))

PUNTO_DI_VISTA_ALLPLAN = _registra(Costante(
    nome="PUNTO_DI_VISTA_ALLPLAN",
    valore=False,
    origine=SCELTA,
    ragione=(
        "Spento: in Allplan la camera vera sul punto scelto aspetta la sonda di "
        "PythonParts (si puo' impostare la camera della finestra da script?). "
        "Finche' non risponde, lo Studio mostra «In Allplan» in grigio."
    ),
))
