# AIRENDER — Product Requirements

Documento vivo. Descrive quello che è vero **adesso**, non quello che è previsto.
Ogni sessione lo aggiorna. Ultimo aggiornamento: 2026-09-14

> Repository: `airender`. Nome fissato il 2026-09-14.

---

## 1 · Cos'è

Un plugin per Allplan che trasforma una vista 3D salvata in un'immagine
presentabile a un cliente, **senza che la geometria cambi**. L'utente scrive in
linguaggio naturale cosa vuole, sceglie uno stile da una griglia di miniature, e
ottiene un render. Dopo, può cliccare su una superficie e cambiarne il materiale
senza rifare il resto dell'immagine.

Non è un motore di rendering. È uno strato che sta fra la vista di lavoro e
l'immagine di presentazione.

## 2 · Cosa si rifiuta di fare

- **Non inventa geometria.** Se il controllo strutturale non tiene, il plugin lo
  dice e propone di abbassare la libertà creativa. Non consegna un'immagine bella
  che rappresenta un edificio diverso da quello disegnato.
- **Non promette la scala metrica dei materiali.** Lo slider governa la *grana*
  — fine, media, grossa — non i corsi di mattoni in millimetri. Chiamarla scala
  sarebbe una bugia verificabile dal cliente.
- **Non carica niente senza un gesto esplicito.** Ogni invio a un servizio
  esterno è preceduto dall'indicazione di quale servizio riceverà l'immagine.
  Il pubblico lavora sotto NDA.
- **Non gestisce crediti né fatturazione.** L'utente mette la propria chiave API
  e il proprio tetto di spesa. Nessun conto da ricaricare dentro il plugin.
- **Non genera video in v1.** Ogni modello video parte da un fermo immagine: è
  un livello sopra, non un percorso parallelo.
- **Non supporta Allplan sotto la 2026.** Senza Plugin Manager l'installazione è
  manuale e la palette è un'altra.

## 3 · Per chi è

Architetti e studi che usano Allplan quotidianamente e che oggi, per avere
un'immagine presentabile, o pagano un visualizzatore esterno o perdono mezza
giornata. Sanno di AI quel tanto che basta per averla provata e essersi irritati
perché "cambia il progetto". Non sanno cos'è una mappa di profondità e non devono
saperlo. Hanno due paure concrete: che il disegno del cliente finisca su un
server sconosciuto, e che l'immagine consegnata non corrisponda al progetto
approvato.

## 4 · Il percorso dell'utente

1. In Allplan salva la vista con **Salva contenuto finestra come immagine** nella
   cartella sorvegliata dal plugin. Vista shaded, ombre attive, sfondo neutro.
2. Apre la palette. Il plugin ha già trovato l'immagine e la mostra.
3. Sceglie uno stile dalla griglia di miniature. Ogni miniatura è stata generata
   eseguendo quel preset, quindi mostra il risultato reale.
4. Se vuole, scrive due parole in linguaggio naturale ("più caldo, mattone
   vecchio"). Il plugin le espande in un prompt tecnico coerente col preset.
5. Genera. **Qui avviene la decisione**: davanti ha la vista di partenza e il
   render, affiancati, e un indicatore di quanto la geometria si è mossa.
6. Se una superficie non gli piace: la clicca o la nomina a parole, sceglie un
   altro materiale o lo scrive, regola la grana. Il resto dell'immagine non si
   tocca.
7. Il risultato salvato non è un PNG ma una **pila di livelli** rieseguibile.

## 5 · Decisioni, con le ragioni

| Data | Decisione | Perché | Ribaltata? |
|---|---|---|---|
| 2026-09-14 | Una sola immagine in ingresso: la vista shaded | Profondità e spigoli si stimano dall'immagine. Chiedere più passate all'utente uccide l'adozione | |
| 2026-09-14 | Niente ID map esportata da Allplan in v1 | Sovra-ingegneria: la segmentazione a valle sul render dà una UX migliore e non richiede nulla all'utente | |
| 2026-09-14 | Cartella sorvegliata invece di cattura programmatica | L'export nativo esiste e dà risoluzione impostabile. Elimina lo screenshot e la dipendenza da API incerte | |
| 2026-09-14 | Palette PythonPart, non nodo Visual Scripting | Il nodo VS non ha UI persistente né job asincroni; e gli utenti VS sono una minoranza. Il nodo resta possibile in v2 sullo stesso motore | |
| 2026-09-14 | Allplan 2026 come minimo, 2027 a seguire | Plugin Manager e pacchetto ALLEP esistono solo da lì | |
| 2026-09-14 | Motore immagine: Magnific come primo candidato | API a consumo senza abbonamento, `structure_reference` con forza regolabile, `fixed_generation`, editing per regione, 30+ modelli con una chiave | |
| 2026-09-14 | ComfyUI come piano B | Controllo strutturale esplicito, ma richiede abbonamento attivo per eseguire, oppure hardware che l'utente non ha | |
| 2026-09-14 | Weavy escluso come motore | Nessuna API pubblica per applicazioni terze. Resta strumento manuale | |
| 2026-09-14 | Livello linguistico nel plugin, non nel grafo | Chiamata diretta all'API del modello linguistico: più economico, e permette di cambiare motore immagine senza toccare la parte che parla con l'utente | |
| 2026-09-14 | Due modalità: **ritocco** (maschera) e **variante** (rigenerazione a stesso seed) | Il riempimento mascherato non ricalcola riflessi e luce di rimbalzo. Un cambio radicale di materiale richiede di rilanciare la base | |
| 2026-09-14 | BYOK, chiave del cliente | Un modello a crediti richiede backend, fatturazione e antifrode: è un'azienda, non un MVP | |

## 6 · Fonti dati

| Fonte | Cosa fornisce davvero | Quanto è buona |
|---|---|---|
| Export immagine Allplan | Contenuto finestra a risoluzione impostabile, anche superiore allo schermo | Ottima. Nativa, nessuna dipendenza |
| Riferimento strutturale del provider | Aderenza alla composizione dell'immagine sorgente, con forza 0-100 | **Da misurare.** È l'unica cosa che decide se il prodotto esiste |
| Stima di profondità | Mappa di profondità dedotta dall'immagine | Buona su viste shaded pulite, degrada su wireframe |
| Segmentazione | Maschera della regione cliccata o nominata | Segue l'apparenza, non il modello |

**L'anello debole:** la segmentazione. Due materiali resi simili finiscono in una
regione sola; una facciata metà in ombra si spezza in due. L'interfaccia deve
prevedere aggiungi area / togli area fin dal primo giorno, perché il primo clic
non sarà mai perfetto.

## 7 · Costruito e funzionante

- Niente. Il repository è uno scaffold.

## 8 · NON COSTRUITO

- Video — rimandato, non annullato. Arriva come livello sopra un fermo immagine.
- LoRA di stile addestrati sui render dello studio — è l'argomento di vendita
  forte della v2, non serve all'MVP.
- Nodo Visual Scripting — possibile, chiamerà lo stesso motore.
- Segmentazione derivata dalle superfici del modello Allplan — darebbe maschere
  esatte e scala vera. Aggiornamento di qualità, non prerequisito.
- Proxy e licenza per la rivendita — fase 2, prima del primo cliente pagante.

## 9 · NON VERIFICATO

**Sezione permanente.** Creduto ma non provato. Si esce solo con una verifica, e
la verifica si nomina qui.

- **Il riferimento strutturale tiene la geometria di un edificio** — non
  verificato: il connettore Magnific risponde in errore su ogni chiamata dal
  2026-09-14. Per verificare: stessa vista shaded a forza 50, 70, 90 e confronto
  di allineamento degli spigoli.
- **L'API Magnific è accessibile a consumo senza piano enterprise** — le fonti si
  contraddicono. Per verificare: sezione API del cruscotto dell'account.
- **`NemAll_Python_Utility.StartMenuFunction` può lanciare il salvataggio
  immagine** — l'API esiste, il nome dell'evento no. Per verificare: prova su
  macchina con Allplan 2026.
- **La rappresentazione a colori piatti si cambia senza muovere la camera** —
  serve solo se un giorno si torna alla multi-passata. Verifica manuale.
- **`requests` è disponibile nell'interprete Python di Allplan 2026** —
  confermato solo per la 2025.
- **`PictureButtonList` regge una griglia di 12+ miniature senza rallentare la
  palette** — verifica su macchina.
- **Le condizioni dei provider consentono la rivendita dell'accesso** — da
  leggere prima di emettere la prima fattura, non dopo.

## 10 · Tagliato

- **ID map esportata da Allplan** — tagliata il 2026-09-14: chiede all'utente un
  lavoro che il modello sa già fare da solo.
- **Screenshot a schermo intero con Pillow** — tagliato il 2026-09-14: l'export
  nativo è migliore sotto ogni aspetto.
- **Krea come motore** — tagliato il 2026-09-14: l'API è fatturata a parte dal
  piano dell'app, e non offre controllo strutturale.
- **ComfyUI locale** — tagliato il 2026-09-14: la macchina disponibile ha 4 GB di
  VRAM contro i 12-16 necessari.
- **Abbonamento Comfy Cloud per l'MVP** — tagliato il 2026-09-14: esiste
  un'alternativa a consumo senza canone.

## 11 · Target e limiti accettati

**Target:** plugin desktop — PythonPart in pacchetto ALLEP per Allplan 2026 e
successive, installato dal Plugin Manager.
**Perché:** la palette è l'unico posto dentro Allplan con interfaccia
persistente, pulsanti, avanzamento e immagini.
**Scartati:** nodo Visual Scripting (nessuna UI persistente, pubblico ristretto);
applicazione web separata (costringerebbe a caricare e scaricare file a mano).

**Accettiamo di non poter:**
- girare su macOS o Linux — Allplan è solo Windows;
- evitare un porting all'anno — Allplan rilascia una versione per anno;
- funzionare offline — la generazione è sempre remota;
- garantire che le immagini non lascino la macchina del cliente.

## 12 · Schermate

Dettaglio in `DESIGN.md`.

| Schermata | Lavoro che serve | Lo stato vuoto dice |
|---|---|---|
| Palette — Sorgente | Trovare e mostrare la vista salvata | "Salva una vista da Allplan nella cartella X. La cerco io." |
| Palette — Stile | Scegliere il preset dalla griglia | Mai vuota: i preset sono inclusi nel pacchetto |
| Palette — Risultato | Confrontare partenza e render, decidere | "Nessun render ancora. Scegli uno stile e premi Genera." |
| Palette — Materiali | Cambiare una superficie | "Clicca una superficie del render, o scrivi come si chiama." |
