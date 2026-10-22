# AIRENDER — Product Requirements

Documento vivo. Descrive quello che è vero **adesso**, non quello che è previsto.
Ogni sessione lo aggiorna. Ultimo aggiornamento: 2026-10-21

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
| 2026-09-14 | Cartella sorvegliata invece di cattura programmatica | L'export nativo esiste e dà risoluzione impostabile. Elimina lo screenshot e la dipendenza da API incerte || **In revisione 2026-10-18:** l'API c'è, `DrawingService.SaveWindowToImageFile(percorso, pixelWidth, pixelHeight)`, con esempio ufficiale nei PythonPartsExamples (ramo 2026). Si decide dopo la prova su macchina |
| 2026-09-14 | Palette PythonPart, non nodo Visual Scripting | Il nodo VS non ha UI persistente né job asincroni; e gli utenti VS sono una minoranza. Il nodo resta possibile in v2 sullo stesso motore | |
| 2026-09-14 | 2026-10-18 | La camera della finestra si salva accanto alla vista (`GetViewWorldProjection`: occhio, punto guardato, proiezione) | È il primo passo verso il legame diretto con la finestra Animazione che l'utente chiede | |
| Allplan 2026 come minimo, 2027 a seguire | Plugin Manager e pacchetto ALLEP esistono solo da lì | |
| 2026-09-14 | Motore immagine: Magnific come primo candidato | API a consumo senza abbonamento, `structure_reference` con forza regolabile, `fixed_generation`, editing per regione, 30+ modelli con una chiave | **Sì, 2026-10-21.** Il consumo senza abbonamento è chiuso dal 2026-06-30 (docs.magnific.com/pricing-payg): l'API ora scala i crediti di un piano prepagato. Cade la ragione principale della scelta. Magnific resta registrato come provider, non è più il predefinito |
| 2026-09-14 | ComfyUI come piano B | Controllo strutturale esplicito, ma richiede abbonamento attivo per eseguire, oppure hardware che l'utente non ha | **Superata 2026-10-21:** Comfy Router esegue i modelli dei partner a consumo dai crediti del workspace, senza abbonamento e senza hardware. Vedi le righe del 2026-10-21 |
| 2026-10-21 | Motore immagine predefinito: **Comfy Router** (`api.comfy.org`) | A consumo dai crediti del workspace, senza abbonamento (docs.comfy.org, Comfy Router). Una chiave per più modelli di modifica d'immagine: FLUX.1 Kontext, Nano Banana, Seedream, GPT Image. Il modello si sceglie nel preset. Solo libreria standard, niente `comfy-sdk` | |
| 2026-10-21 | Con Comfy Router **non c'è una forza della struttura** | I modelli di modifica del Router non hanno un `structure_strength` da 0 a 100: se tengono la geometria, la tengono per come sono fatti e per il prompt. Quindi l'interfaccia non stampa una forza, `--forza-struttura` viene rifiutata, la ricetta scrive la forza come assente. La sezione 2 ("propone di abbassare la libertà creativa") con Comfy non ha ancora una leva: la tenuta si giudica a occhio con `scripts/confronta_modelli.py`. La forza resta solo su Magnific | |
| 2026-10-21 | `fallback_provider=false` su ogni invio a Comfy Router | Il Router, se il provider del modello fallisce, ripiega su un altro provider, e lo fa se non gli si dice di no. Sotto NDA la destinazione si annuncia prima dell'invio: un ripiego la renderebbe falsa. Se il Router dichiara comunque un altro provider, il risultato porta un avviso | |
| 2026-10-21 | La **segmentazione resta in pipeline**: l'annotazione per aree le sta accanto, non la sostituisce | Decisione di Riccardo. Il riquadro copre un'area disegnata a mano; cliccare una superficie o nominarla a parole (sezione 4, passo 6) richiede ancora la segmentazione | |
| 2026-10-21 | Lo schema di un modello si scrive **solo dopo una chiamata vera** | Con Magnific endpoint e campi vengono dalla documentazione e non sono mai stati eseguiti. Per Comfy il protocollo della coda viene dalla documentazione; lo schema dei modelli no: `SCHEMI` in `core/provider/comfy.py` resta vuoto finché `scripts/sonda_comfy.py` non ha risposto, e senza schema l'invio si ferma prima di partire | |
| 2026-09-14 | Weavy escluso come motore | Nessuna API pubblica per applicazioni terze. Resta strumento manuale | |
| 2026-09-14 | Livello linguistico nel plugin, non nel grafo | Chiamata diretta all'API del modello linguistico: più economico, e permette di cambiare motore immagine senza toccare la parte che parla con l'utente | |
| 2026-09-14 | Due modalità: **ritocco** (maschera) e **variante** (rigenerazione a stesso seed) | Il riempimento mascherato non ricalcola riflessi e luce di rimbalzo. Un cambio radicale di materiale richiede di rilanciare la base | |
| 2026-09-14 | BYOK, chiave del cliente | Un modello a crediti richiede backend, fatturazione e antifrode: è un'azienda, non un MVP | |

## 6 · Fonti dati

| Fonte | Cosa fornisce davvero | Quanto è buona |
|---|---|---|
| Export immagine Allplan | Contenuto finestra a risoluzione impostabile, anche superiore allo schermo | Ottima. Nativa, nessuna dipendenza |
| Riferimento strutturale del provider | Aderenza alla composizione dell'immagine sorgente, con forza 0-100 | **Da misurare.** È l'unica cosa che decide se il prodotto esiste. Con Comfy Router, il predefinito, la forza non c'è: l'aderenza dipende dal modello e dal prompt, e si guarda col confronto affiancato |
| Stima di profondità | Mappa di profondità dedotta dall'immagine | Buona su viste shaded pulite, degrada su wireframe |
| Segmentazione | Maschera della regione cliccata o nominata | Segue l'apparenza, non il modello |

**L'anello debole:** la segmentazione. Due materiali resi simili finiscono in una
regione sola; una facciata metà in ombra si spezza in due. L'interfaccia deve
prevedere aggiungi area / togli area fin dal primo giorno, perché il primo clic
non sarà mai perfetto.

## 7 · Costruito e funzionante

Il motore, e solo il motore. Gira da riga di comando su qualunque macchina,
senza Allplan. `pytest`: **121 test verdi**, nessuna chiamata di rete, nessuna
chiave necessaria per farli girare.

```bash
python -m core.cli --image vista.png --preset base --testo "più caldo" --prova-a-secco
python scripts/sonda_comfy.py --solo-schema          # gratis: schema vero del modello
python scripts/sonda_comfy.py                        # una generazione vera, tutto stampato
python scripts/confronta_modelli.py --immagine vista.png
```

| Cosa | Dove | Stato |
|---|---|---|
| Riga di comando: vista + preset + testo → render, ricetta rieseguibile a fianco | `core/cli.py` | Percorso completo fino all'invio. L'invio vero non è mai stato eseguito: manca lo schema verificato del modello (vedi sezione 9) |
| Casa unica delle decisioni: 21 costanti, ognuna con la ragione e l'etichetta MISURATA / SCELTA / VINCOLO | `core/config.py` | Fatta. Un test impedisce di cablare numeri altrove, e un altro che una costante resti senza il suo caso |
| Strato provider sostituibile: genera, modifica una regione con maschera, riesegue a parametri identici; ogni provider dice dove manda la vista e se ha una forza della struttura | `core/provider/` | Interfaccia + due provider. **Comfy Router**, predefinito: protocollo della coda, idempotenza, errori; nessuno schema di modello ancora, quindi l'invio vero si ferma prima di partire. **Magnific**: registrato, non più a consumo |
| Sonda di Comfy Router: schema del modello (gratis), una generazione, risposte stampate senza chiave | `scripts/sonda_comfy.py` | Scritta e provata senza rete. Mai lanciata contro il Router: la rete di questa sessione non arrivava a `api.comfy.org` |
| Confronto affiancato: la stessa vista attraverso due modelli, con la vista di partenza, per giudicare gli spigoli a occhio | `scripts/confronta_modelli.py` | Scritto e provato senza rete. Parte davvero solo quando i due modelli hanno lo schema |
| Rifiuto: vista inadatta (wireframe, senza ombre, troppo piccola), con il messaggio che dice cosa risalvare | `core/idoneita.py` | Funziona su immagini sintetiche e su **un** export vero di Allplan 2026, che passa (sezione 9). Un wireframe sintetico sul gradiente di Allplan passa anche lui |
| Rifiuto: il parametro della texture si chiama **grana** e non può chiamarsi scala, né nelle etichette né da riga di comando | `core/lessico.py` | Funziona. Il divieto vale sulle nostre parole, non sul testo libero dell'utente |
| Ricetta rieseguibile: provider, modello, versione del preset, tutti i parametri, impronta della vista di partenza | `core/ricetta.py` | Fatta. È il seme della pila di livelli, che arriva nella sessione 3 |
| Errori in italiano, ognuno con il gesto successivo; nessun codice HTTP da solo | `core/errori.py`, `core/provider/comfy.py` | Fatti per: chiave rifiutata, credito esaurito (per Comfy: credito del workspace, con cosa fare), workspace che non può usare il modello, modello sconosciuto, limite di chiamate, immagine troppo pesante, servizio rotto, lavoro fallito, schema del modello non ancora verificato |
| Palette di prova in Allplan 2026: cattura la finestra attiva in PNG con la sua camera, prova a secco, genera | `allplan/v2026/`, `allplan/comune/ponte.py` | Cattura e prova a secco funzionano in Allplan 2026 (prova del 2026-10-21). L'invio vero non è ancora partito. Dal 2026-10-21 la palette parla con Comfy Router senza che l'adattatore sia cambiato: segue il predefinito del motore |

**Non c'è ancora:** nessuno schema di modello Comfy verificato (quindi nessun
render vero), nessuna palette vera (solo quella di prova), nessun pacchetto ALLEP, nessuna cartella
sorvegliata, nessuna pila di livelli su disco, nessuna miniatura, nessuna
espansione del linguaggio naturale (il testo dell'utente viaggia com'è, in coda
al prompt del preset).

Dipendenze: **una**, Pillow, usata in un file solo (`core/immagine.py`). Il
trasporto HTTP usa `urllib` della libreria standard apposta, per non dipendere
da `requests`.

## 8 · NON COSTRUITO

- Video — rimandato, non annullato. Arriva come livello sopra un fermo immagine.
- LoRA di stile addestrati sui render dello studio — è l'argomento di vendita
  forte della v2, non serve all'MVP.
- Nodo Visual Scripting — possibile, chiamerà lo stesso motore.
- Segmentazione derivata dalle superfici del modello Allplan — darebbe maschere
  esatte e scala vera. Aggiornamento di qualità, non prerequisito.
- Proxy e licenza per la rivendita — fase 2, prima del primo cliente pagante.
- **Annotazione per aree** — in pipeline dal 2026-10-21, richiesta di Riccardo.
  Riferimento: lo strumento *Annotate Image* di rendair.ai. L'utente traccia uno
  o più riquadri numerati sul render e accanto a ciascuno scrive cosa cambiare
  ("balconi alla francese", "un piccolo caffè con la tenda verde"). Poi una sola
  generazione applica tutte le note. Per AIRENDER conta per tre ragioni:
  1. **Dà una strada che non dipende dalla segmentazione.** L'area la disegna
     l'utente, non la indovina un modello. La segmentazione però **resta in
     pipeline** (sezione 5): il riquadro le sta accanto, non la sostituisce.
  2. **Fuori dai riquadri l'immagine non cambia, e lo si può dimostrare.** Il
     motore rimette i pixel del render di partenza fuori dalle aree, con il
     bordo sfumato di `MASCHERA_SFUMATURA_PX`, qualunque modello abbia fatto la
     modifica. È l'unico modo di promettere "il resto non si tocca" con un
     modello che rigenera tutta l'immagine, e si verifica con un confronto
     pixel per pixel fuori dalle aree. Funziona solo se il modello rende
     un'immagine della stessa dimensione di quella mandata.
  3. **Una chiamata per tutte le note**, invece di una per area: costa meno, ma
     le note si influenzano a vicenda. La trappola del riempimento mascherato
     vale ancora: luce e riflessi del resto non si ricalcolano.

  Due modi di dire al modello dove intervenire, da scegliere dopo la sonda:
  una **maschera per area**, oppure il render con i **riquadri numerati
  disegnati sopra** e un testo che li nomina ("nel riquadro 1…"). Il secondo
  funziona con i modelli di modifica a istruzioni, se li capiscono: nessuno dei
  due è verificato.

  Prima di scriverne il codice servono: uno schema di modello verificato dalla
  sonda; la risposta su come disegnare un riquadro dentro Allplan (sezione 9);
  i quattro stati della schermata in `DESIGN.md`. Nella schermata Materiali sta
  accanto al clic su una superficie e al nome scritto a parole, non al loro
  posto.
- **Segmentazione sul render** — in pipeline, non costruita. Serve a cliccare una
  superficie o a nominarla a parole (sezione 4, passo 6; schermata Materiali in
  `DESIGN.md`). Con i suoi limiti della sezione 6: segue l'apparenza, quindi
  servono sempre aggiungi area e togli area.

## 9 · NON VERIFICATO

**Sezione permanente.** Creduto ma non provato. Si esce solo con una verifica, e
la verifica si nomina qui.

### Lasciato dalla sessione 1 (motore)

- **L'API Magnific risponde alle chiamate che il motore fa** — non verificato:
  in questa sessione non c'era nessuna chiave e la rete verso il dominio del
  provider era chiusa. Endpoint (`POST /v1/ai/mystic`, `GET /v1/ai/mystic/{id}`,
  `POST /v1/ai/ideogram-image-edit`), nome dell'intestazione della chiave e nomi
  dei campi vengono dalla documentazione pubblica, non da una risposta vera. Per
  verificare: `python -m core.cli --image vista.png --preset base` con una chiave
  in `MAGNIFIC_API_KEY`. Se il nome di un campo è cambiato, si tocca un file solo,
  `core/provider/magnific.py`. Dal 2026-10-21 Magnific non è più il
  predefinito e la verifica richiede un piano a crediti prepagati, non più una
  chiave a consumo: va fatta solo se si decide di tenerlo.
- **Il riferimento strutturale tiene la geometria di un edificio** — non
  verificato, per la stessa ragione. Per verificare: stessa vista shaded a forza
  50, 70 e 90, e confronto di allineamento degli spigoli. Fino ad allora
  `FORZA_STRUTTURA_PREDEFINITA = 70` resta etichettata SCELTA, e l'interfaccia lo
  scrive.
- **`fixed_generation` basta a rifare la stessa immagine** — non verificato. La
  ricetta salva anche modello e versione del preset proprio perché non ci
  fidiamo; la riesecuzione avvisa che un'immagine identica non è garantita.
- **Le soglie che scartano una vista inadatta reggono sugli export veri** — per
  verificare: dieci export veri da Allplan — cinque shaded buone, tre
  wireframe, due senza ombre — e nessun falso rifiuto sulle prime cinque. **È
  la verifica più urgente:** un falso rifiuto blocca un utente che ha fatto
  tutto giusto. **Fatto 1 su 10** (2026-10-21): la cattura vera
  `tests/dati/vista-20261021-093841.png` (shaded, finestra Animazione, 1536x857)
  passa, ed è diventata un test di regressione in `tests/test_idoneita.py`:

  | Misura | Valore misurato | Soglia | Margine |
  |---|---|---|---|
  | Sfondo uniforme (`QUOTA_SFONDO_MASSIMA`) | 10,1% | sotto 70% | ampio |
  | Livelli di grigio (`TONI_DISTINTI_MINIMI`) | 67 | almeno 24 | ampio |
  | Scarto di luminanza (`DEVIAZIONE_LUMINANZA_MINIMA`) | 35,4 | almeno 12 | ampio |

  **Mancano 9 export veri:** quattro shaded buone, tre wireframe, due senza
  ombre. Le tre soglie restano SCELTE. Un dubbio nuovo, da verificare con i
  wireframe veri: lo sfondo di Allplan nella cattura **non è un tono unico ma un
  gradiente** azzurro-grigio, per questo lo sfondo uniforme misura solo il 10%.
  Il rilevamento del wireframe conta proprio su uno sfondo uniforme. Prova
  sintetica, non un export: linee nere disegnate sul gradiente ricostruito dagli
  angoli della cattura vera danno sfondo uniforme al 4,7%, 65 livelli di grigio,
  scarto 36,0, e la vista **passa come idonea**. Se i tre wireframe veri fanno
  lo stesso, il rifiuto del wireframe non funziona con lo sfondo predefinito di
  Allplan. Un rifiuto che manca fa pagare una chiamata inutile, non blocca
  nessuno: è meno grave di un falso rifiuto, ma va saputo.
- **La grana corrisponde a `creative_detailing`** — i tre valori (20 / 45 / 75)
  sono scelti, non misurati, e la corrispondenza fra quel parametro e la grana
  percepita è un'ipotesi. Per verificare: stessa vista, tre livelli, e un occhio
  su una facciata in mattoni.
- **I formati accettati dal servizio sono quelli che il motore conosce** —
  l'elenco in `core/provider/magnific.py` viene dalla documentazione. Se ne manca
  uno, il motore chiede il più vicino e l'edificio si schiaccia un po'.

### Lasciato dalla sessione del 2026-10-18 (palette di prova)

Prova sul PC di Riccardo, Allplan 2026, modello BOSCO, 2026-10-21. **Verificato**:
`installa.ps1` col percorso Usr predefinito; Pillow installato da "Install
Python Package" visibile ai PythonPart; `core/` e `ponte.py` importati accanto
allo script; `SaveWindowToImageFile` che salva la **finestra Animazione** (in prospettiva
centrale) alla sua dimensione (1536x857), in due catture a pochi minuti di
distanza con la stessa camera; occhio, punto guardato e
`IsCentralProjection` letti senza errori; prova a secco completa, con la vista
giudicata idonea (67 livelli di grigio, sfondo uniforme al 10%) e la destinazione
mostrata prima dell'invio.

Resta non verificato:

- **Quale finestra cattura quando ce ne sono due aperte** — provato con una
  finestra sola. Per verificare: due finestre affiancate, clic nella seconda,
  Cattura vista.
- **`GetViewAngle` non è l'apertura della camera** — ha restituito `0.0` in una
  vista prospettica, quindi è probabilmente la rotazione della vista, non il
  campo visivo. Non usarlo come angolo di camera finché non lo si confronta con
  un'apertura cambiata a mano.
- **`GetViewSize` è in unità del modello, non in pixel** — ha restituito circa
  31539 x 17597 per una finestra di 1536x857 px.
- **La cattura mostra le ombre portate quando sono attive** — nella prova le
  ombre erano attive, ma nell'immagine non se ne vedono. Ipotesi, non verificata:
  il modello BOSCO non ha solaio né terreno sotto i muri, quindi le ombre non
  hanno dove cadere (sotto i muri si vede lo sfondo). Per verificare: cattura di
  un modello con un solaio o un terreno, ombre attive. Il motore l'ha comunque
  giudicata idonea: le soglie non distinguono una vista con ombre da una senza.
- **PythonParts SDK 3.0.0 dichiara `min-allplan-version: 2027`** nel suo
  `install-config.yml`, ma il Plugin Manager della 2026 lo ha installato.
  Probabilmente serve una versione precedente: da guardare nel Plugin Manager.

### Lasciato dalla sessione del 2026-10-21 (Comfy Router)

In questa sessione la rete della macchina non raggiungeva né `docs.comfy.org`
né `api.comfy.org`: la documentazione è stata letta **solo attraverso gli
estratti di una ricerca**, e nessuna chiamata è partita. Tutto quello che segue
si verifica lanciando `scripts/sonda_comfy.py` e incollandone l'uscita.

- **Il protocollo della coda è quello scritto in `core/provider/comfy.py`** —
  dalla documentazione, mai eseguito: `POST /v2/models/{provider}/{model}/requests`
  che risponde 201 con `request_id`; `GET .../requests/{id}/status` con
  `status` fra `IN_QUEUE`, `IN_PROGRESS`, `COMPLETED` e l'intestazione
  `Retry-After`; `GET .../requests/{id}` che risponde 202 finché non è pronto,
  poi 200 con l'uscita del modello; nessuno stato "fallito", ma un errore dentro
  un `COMPLETED`, con un nome di campo che non conosco (cerco `error` ed
  `error_type`). Una pagina vecchia della guida diceva che il Router non era
  ancora attivo e rispondeva 404 sulle rotte `/v1/`: le pagine dei modelli usano
  `/v2/`. Se qualcosa non torna, si tocca un file solo, `comfy.py`.
- **Lo schema dei modelli di modifica** — `SCHEMI` è vuoto apposta. Dalla
  documentazione, da confermare con la sonda: FLUX.1 Kontext
  (`bfl/flux-kontext-pro`, `bfl/flux-kontext-max`) vuole `prompt`,
  `input_image` in base64 e `aspect_ratio`, e restituisce un link in
  `result.sample`; Nano Banana 2 (`vertexai/gemini-3.1-flash-image`) e Nano
  Banana Pro (`vertexai/gemini-3-pro-image`) usano il corpo nativo di Gemini
  (`contents` → `parts` → `inlineData` con `mimeType` e `data`) e rendono il
  base64 in `candidates[0].content.parts[…].inlineData.data`. Nel catalogo ci
  sono anche Seedream (`byteplus/seedream-4-5-251128`, poi 5.0) e GPT Image
  (`openai/gpt-image-1.5`, `openai/gpt-image-2`), ma i loro schemi di modifica
  non li ho trovati: non sono nella sonda. Una fonte non ufficiale dice Nano
  Banana 2 deprecato in favore di `vertexai/gemini-nano-banana-2.1`.
- **Il Router accetta l'immagine come `data:image/png;base64,…`** — la sonda la
  manda così, come chiesto. Per Gemini il campo nativo `inlineData.data` di
  solito vuole il base64 senza prefisso: se torna un 400, rilanciare con
  `--base64-nudo`.
- **`fallback_provider=false` vale anche sulla rotta della coda** — documentato
  come parametro di query sulla rotta diretta (note di rilascio degli SDK). Per
  verificare: nell'uscita della sonda non deve comparire
  `X-Comfy-Router-Fallback-Provider`.
- **Il 402 `insufficient_credits` non addebita niente** — dalla documentazione,
  che dice anche che il controllo del credito viene prima della validazione del
  corpo: un workspace vuoto risponde 402 anche a una richiesta sbagliata. Prima
  la ricarica, poi lo schema.
- **Il render torna con le proporzioni della vista** — la sonda chiede il
  rapporto standard più vicino (16:9 per la cattura 1536x857) e stampa i due
  rapporti a confronto. Se non coincidono, l'edificio è schiacciato.
- **FLUX.1 Kontext o Nano Banana tengono la geometria di un edificio** — è la
  domanda del prodotto, e senza una forza della struttura non c'è una leva per
  aggiustarla. Per verificare: `scripts/confronta_modelli.py` sulla cattura vera,
  e un occhio sugli spigoli.
- **La grana passa solo come frase nel prompt** — con Comfy non esiste
  `creative_detailing`; la ricetta scrive il dettaglio della grana come assente.
  Che la frase basti a cambiare la grana percepita è un'ipotesi.
- **Rifare una ricetta Comfy dà la stessa immagine** — no, quasi certamente: non
  c'è una generazione fissa verificata e la riesecuzione lo dice. Si usa una
  Idempotency-Key nuova apposta: quella vecchia, entro 24 ore, renderebbe
  l'immagine di allora senza rifarla.
- **Cosa si paga se il tempo scade** — le fonti si contraddicono: la guida dice
  che un 504 per tempo scaduto non si paga, un esempio in coreano dice che una
  generazione finita dal provider si paga comunque. Il motore usa la coda e,
  quando smette di aspettare, dice di guardare i crediti prima di rilanciare.
- **Il prezzo per immagine** — non letto. Va guardato nel catalogo del Router
  (`billing` di ogni modello) prima di decidere la risoluzione e il numero di
  miniature.
- **La palette mostra la destinazione completa** — il campo Destinazione della
  palette di prova legge `ponte.destinazione_predefinita()`, che dà "Comfy
  Router (api.comfy.org)" senza il modello; il modello compare nel testo della
  prova a secco. L'adattatore non si è toccato. Da vedere a video.
- **`ImageFont.load_default(size=…)` esiste nel Pillow di Allplan** — serve solo
  alle didascalie del confronto; se manca, si ripiega sul carattere piccolo.

### Lasciato dalla richiesta del 2026-10-21 (annotazione per aree)

- **Si può disegnare un riquadro su un'immagine dentro la palette di Allplan** —
  non verificato, ed è la domanda che decide come si costruisce l'annotazione.
  Gli elementi della palette elencati in `DESIGN.md` (immagini, griglia di
  pulsanti-immagine, slider, testo, pulsanti) mostrano un'immagine. Non risulta
  che nessuno restituisca un trascinamento del mouse su di essa. Lo stesso dubbio
  vale già per "clicca una superficie del render" della schermata Materiali. Se
  non si può, le strade sono tre: una finestra a parte aperta dalla palette; una
  pagina locale nel browser; oppure riquadri ricavati dagli oggetti selezionati
  nel modello Allplan, proiettati sulla vista con la camera salvata accanto.
  L'ultima darebbe aree esatte, dal modello e non dall'apparenza. Per
  verificare: cercare nei PythonPartsExamples del ramo 2026 un controllo della
  palette che restituisca le coordinate di un clic su un'immagine. Se c'è, la
  palette basta. Se non c'è, si sceglie fra le tre strade.
- **I modelli di modifica del Router capiscono un render con riquadri numerati
  disegnati sopra** — non verificato. Per verificare, dopo la sonda: lo stesso
  render con due riquadri e due note, mandato a FLUX.1 Kontext e a Nano Banana
  con `scripts/confronta_modelli.py`. Poi guardare se ciascuna nota è finita
  nel suo riquadro e se i riquadri disegnati sono spariti dal risultato.

### Da prima

- **`NemAll_Python_Utility.StartMenuFunction` può lanciare il salvataggio
  immagine** — l'API esiste, il nome dell'evento no. Per verificare: prova su
  macchina con Allplan 2026.
- **La rappresentazione a colori piatti si cambia senza muovere la camera** —
  serve solo se un giorno si torna alla multi-passata. Verifica manuale.
- **`requests` è disponibile nell'interprete Python di Allplan 2026** —
  confermato solo per la 2025. **Non è più un rischio per il motore:** il
  trasporto usa `urllib` della libreria standard. Resta da verificare solo se
  un giorno servirà `requests` dalla parte della palette.
- **`PictureButtonList` regge una griglia di 12+ miniature senza rallentare la
  palette** — verifica su macchina.
- **Le condizioni dei provider consentono la rivendita dell'accesso** — da
  leggere prima di emettere la prima fattura, non dopo.

### Usciti da questa sezione, con la loro verifica

- **Pillow è installabile nell'interprete Python incorporato di Allplan 2026** —
  verificato il 2026-10-21 sul PC di Riccardo, Allplan 2026: installato da
  PythonParts SDK › *Install Python Package* (pacchetto `pillow`, destinazione
  USR); dentro la palette di prova `core/immagine.py` lo ha importato e la prova
  a secco ha misurato la vista vera (67 livelli di grigio, sfondo uniforme al
  10%). Vedi il blocco della sessione del 2026-10-18 qui sopra.
- **L'API Magnific è accessibile a consumo senza piano enterprise** — risolto il
  2026-10-21, con risposta **no**: il consumo senza abbonamento è chiuso dal
  2026-06-30. Fonte: docs.magnific.com/pricing-payg, indicata da Riccardo. In
  questa sessione la pagina non era raggiungibile dalla rete della macchina:
  l'ho letta solo nell'estratto di una ricerca, che dice "API Pay-per-usage plan
  will be discontinued on June 30. Switch to a credit based plan to keep using
  the API."

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
  un'alternativa a consumo senza canone. Era Magnific, che dal 2026-06-30 non è
  più a consumo; il taglio resta, perché l'alternativa a consumo adesso è Comfy
  Router (sezione 5), che scala crediti del workspace e non è l'abbonamento.

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
