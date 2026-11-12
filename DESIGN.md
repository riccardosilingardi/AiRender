# AIRENDER — Design

Documento vivo, come il PRD. Si aggiorna ogni volta che una schermata cambia.

> Dal 2026-10-27 l'interfaccia ha **due superfici** (PRD, sezione 5):
>
> - la **palette** dentro Allplan fa da telecomando: cattura la vista, sceglie
>   lo stile di base, dice dove va l'immagine e manda. Colori, font e
>   spaziature li decide Allplan, inclusa la modalità scura;
> - lo **Studio** è una pagina locale servita dal motore e aperta in una
>   finestra propria, in un processo a parte: lì c'è lo spazio per scegliere
>   con calma, confrontare e lavorare col mouse sul render. Colori e font li
>   decidiamo noi.
>
> Quello che decidiamo in tutte e due è **cosa c'è, in che ordine, e cosa dice
> quando non c'è niente.**

I mockup stanno in `docs/ui/mockup/` (copiati dal progetto il 2026-10-27,
aggiornati il 2026-10-29): `Palette.dc.html` è la palette v1, `Stile.dc.html`
è Studio · Genera, `Main.dc.html` è Studio · Risultato, `Passi.dc.html` è
Studio · Passi, `Ritocca.dc.html` è Studio · Ritocca. I testi dei blocchi di
prompt sono in `docs/ui/blocchi-stile-bozza.md` (bozza 5).
Dove questo documento e un mockup non dicono la stessa cosa, vale questo
documento.

## Regole che valgono per ogni schermata

- Ogni schermata ha quattro stati: **vuoto**, **in corso**, **errore**,
  **pieno**.
- **Lo stato vuoto non ha dati finti.** Niente render di esempio, niente
  costi inventati, niente nomi di materiali presi da un altro progetto. Se un
  esempio serve a spiegare, è scritto che è un esempio e non si può usare.
- **Le funzioni future sono in grigio, con l'etichetta «In arrivo», e non si
  attivano.** Un clic non fa niente, non apre un messaggio d'errore e non
  manda niente. Accanto c'è cosa serve prima che arrivino.
- **Prima di Genera si vedono sempre la destinazione e il costo** (regola 5 di
  `CLAUDE.md`): «La vista va a Comfy Router → Google (Nano Banana 2), senza
  ripiego su altri servizi», e il costo con la data in cui è stato misurato.
- Un numero scelto e non misurato lo dice anche a schermo (regola 3).

## Vincoli ereditati

**Palette**
- Contenitore: palette Allplan 2026, larghezza stretta e variabile.
- Elementi disponibili: expander annidati, immagini ridimensionabili, griglia di
  pulsanti-immagine, barra di avanzamento, testo, slider, pulsanti. Quali di
  questi si aggiornano da script lo dice la sonda della palette (PRD, sezione
  9): finché non risponde, la palette v1 non si scrive.
- La palette deve restare usabile mentre una generazione è in corso. Per
  questo la generazione non gira più dentro Allplan: la palette scrive un
  lavoro in coda e torna libera.

**Studio**
- Pagina locale servita dal motore con `http.server` della libreria standard,
  solo su `127.0.0.1`, aperta con `msedge --app=` come finestra senza barra.
- Deve funzionare senza internet per tutto quello che non è la generazione:
  niente CDN, niente font scaricati (i mockup usano Google Fonts, lo Studio
  vero no).
- Palette e Studio non si chiamano a vicenda: si parlano attraverso la
  cartella delle viste e la coda dei lavori su file. Ognuno dei due funziona
  anche se l'altro è chiuso.

## Schermate

### Palette v1 — il telecomando

**Dal 2026-11-04 la palette cattura e basta** (scelta di Riccardo: «solo per
cattura vista, poi apro tutto in studio»). Restano **Vista** (nome, esito,
Cattura vista, Dimensione, Formato, **Vedi cosa ha tagliato**) e **Studio**
(«Stile, render, ritocchi e video si fanno nello Studio.», **Apri nello
Studio**, Apri cartella), più la riga di Esc in cima e la cartella in fondo.
Tolti Stile, Invio, Ultimo render e Nello Studio. Un formato fisso taglia la
vista alla cattura: nella cartella c'è solo la parte che resta, e la finestra
intera scurita si apre da sola per far vedere il taglio. Quello che segue
descrive la palette fino al 2026-11-03.

Mockup: `Palette.dc.html`. Quattro expander in fila, numerati, più uno che
rimanda allo Studio. In cima una riga: «Per tornare alla Library premi Esc».
Allplan non dà un pulsante Chiudi nella palette di un PythonPart: si esce con
Esc (aggiornato il 2026-11-01). In fondo il percorso della cartella delle viste.

1. **Vista** — finestra attiva, Cattura vista, dimensione (come la finestra,
   1920×1080, 3840×2160), miniatura, esito dell'idoneità.
2. **Stile** — resa (miniature illustrative, dichiarate tali), ora, cielo,
   intorno, materiali a parole, modello. È la versione corta di Studio ·
   Genera: le stesse scelte, con gli stessi nomi.
3. **Invio** — dove va la vista, costo, Prova a secco, Genera.
4. **Ultimo render** — preset e modello, crediti, **Apri nello Studio**, Apri
   cartella.
5. **Nello Studio** — Annota aree e ritocchi (scheda Ritocca), Video dai
   render (scheda Video). Cambia materiale e Livelli non compaiono finché non
   funzionano: Riccardo le leggeva come promesse (aggiornato il 2026-11-01).

- **Vuoto:** «Nessuna vista ancora. Clicca una volta nella finestra 3D da
  rendere (shaded, con ombre), poi Cattura.» Stile si può già impostare;
  Genera è spento finché non c'è una vista adatta; Ultimo render dice
  «Nessun render ancora».
- **In corso:** «In corso da 0:12. Allplan resta libero; l'avanzamento è nello
  Studio.» Genera diventa Annulla. Le altre sezioni restano usabili: si può
  già catturare la vista successiva.
- **Errore:** due errori diversi, scritti diversi. Vista non adatta: la
  miniatura resta visibile con la ragione e cosa risalvare (regola di
  `core/idoneita.py`). Invio fallito: la frase del motore in italiano con il
  gesto successivo, mai un codice HTTP da solo, e Apri nello Studio per i
  dettagli.
- **Pieno:** miniatura e dimensioni della vista con l'esito («Adatta: shaded,
  67 toni, sfondo uniforme 10%»), le scelte di stile, destinazione e costo, e
  in Ultimo render il riassunto dell'ultimo lavoro con Apri nello Studio.

**Palette v1, costruita il 2026-10-31** (prompt 7), prima che la sonda della
palette abbia risposto sul PC di Riccardo. Dove la palette costruita si scosta
da qui:

- **Miniature spente.** La miniatura della vista e quella dell'ultimo render
  sono immagini solo se `PALETTE_IMMAGINI_DA_SCRIPT` è acceso (SCELTA, spento):
  finché la sonda non dice che Allplan aggiorna un'immagine da script, la
  palette scrive nome, dimensioni ed esito. Una miniatura che non si aggiorna
  mostrerebbe la vista sbagliata.
- ~~**Resa in una riga, non in griglia.**~~ Dal 2026-10-31 (prompt 12) la
  Resa è un menu a cinque voci, che apre su Fotorealistico. Gli assi che una
  resa spegne restano nei menu: la riga «Ripiego» della sezione Invio dice
  quali non partono.
- **Esterno / Interno e il preset in Stile.** Il mockup non li ha; senza, la
  palette non saprebbe da quale combinazione partire. Sono lo switch e i preset
  dello Studio · Genera, con gli stessi nomi; Ora, Cielo e Intorno partono da
  «Come il preset». Cielo e Intorno si vedono solo con Esterno. Dal
  2026-11-01 (bozza 8) il gruppo Vista ha una terza voce, **Arredo**: preset,
  Luce e Sfondo dell'arredo, e Persone nascosto (condizione `Interno != 2`,
  la prima con `!=`: da verificare che Allplan la accetti).
- **Aggiorna.** Una palette di Allplan non si ridisegna da sola: lo stato del
  lavoro si rilegge dal disco a ogni clic, e Aggiorna serve a rileggerlo senza
  fare altro. «In corso da 0:12» è il tempo all'ultimo clic, non un orologio.
- **Errori in finestra di messaggio.** I campi della palette sono righe
  corte: la frase intera (fatto e cosa fare) arriva in una finestra di
  messaggio, il campo Stato ne tiene l'inizio.
- **Come parte la coda.** Genera scrive il lavoro e, se sulla cartella non
  gira una coda, avvia lo Studio senza finestra, che la fa partire. Apri nello
  Studio riapre lo Studio che gira, o lo avvia con la finestra. Una coda sola
  per cartella (`lavori/coda-viva.json`, vedi PRD sezione 7).

### Studio · Genera

Mockup: `Stile.dc.html`. In alto la barra comune dello Studio: a cosa è
collegato («Collegato ad Allplan 2026 · BOSCO · Prospettiva centrale»), le
schede **Genera · Risultato · Passi · Ritocca** e, in grigio, **Video** e
**Chiave e tetto di spesa** (fino al 2026-10-28 la voce Passi si chiamava
Livelli; attiva dal 2026-10-30). Sotto, la vista con il suo esito di idoneità e
Usa un'altra vista…; se la vista ha colori di visualizzazione, l'avviso «Il
modello legge i colori della vista come materiali. Per colori veri, salva la
vista con colori neutri.»

**Colonna sinistra — lo stile**
- Switch **Esterno / Interno / Arredo**. È l'unico modo di dire cosa c'è nella
  vista: non esiste un campo «Cosa c'è nella vista». **Arredo** (dal
  2026-11-01, bozza 8) è un pezzo d'arredo da solo fotografato come prodotto:
  i Dettagli del preset hanno Resa, Look, Luce e **Sfondo**, senza Persone; il
  primo piano lo dà l'inquadratura salvata in Allplan.
- **Parti da un preset**: 8 preset esterni, 6 interni o 6 d'arredo, secondo lo switch
  (elenco in `docs/ui/blocchi-stile-bozza.md`). Le miniature sono
  **illustrazioni**, e lo dice la riga sopra la griglia: «Miniature
  illustrative: rendono l'idea, non sono render del modello». Si sostituiscono
  con render veri dei preset quando ci saranno.
- **Dettagli del preset**, **aperti per default**: il preset imposta i
  comandi, l'utente ne cambia uno e il resto resta com'è. Da chiusi mostrano
  la sintesi in una riga. Dentro:
  1. Resa;
  2. Look fotografico (colore, contrasto, pellicola o digitale: solo per le
     rese fotografiche);
  3. Ora / Luce;
  4. per gli esterni **Cielo e stagione**; per gli interni **Fuori dalle
     finestre** e **Arredo**;
  5. per gli esterni **Cosa può aggiungere il modello**: intorno all'edificio
     (niente e sfondo neutro, città, periferia, campagna), verde (nessuno,
     poco, rigoglioso), persone (nessuna, poche, in movimento); per gli
     interni le persone. Ogni voce che aggiunge qualcosa dice al modello anche
     di non coprire l'edificio («do not cover or hide any building element»).

**Colonna destra — cosa parte**
- **Materiali a parole** (attivo): testo libero, «intonaco a calce bianco,
  infissi in rovere scuro».
- **Materiali del progetto** (2026-11-02): la tabella dei materiali che la
  palette ha letto quando ha catturato la vista. AIRENDER non cambia mai i
  materiali di Allplan: li legge e basta. Una riga per materiale: cubetto
  d'anteprima del .surf (vuoto se il .surf non si trova), nome, numero di
  elementi, spunta **Cambia**. Con la spunta compaiono «diventa» (a parole,
  obbligatorio) e **+ Riferimento** (foto facoltativa). Al massimo
  `MATERIALI_CAMBIATI_MASSIMI` spunte (scelto). Ricerca e «Mostra tutti» oltre
  le prime righe; sotto, gli elementi senza materiale (es. facciate).
  - *Vuoto:* la vista non ha l'elenco di Allplan (web app, immagini da altri
    programmi): al posto della tabella compare **Materiali della vista**, sotto.
    Nessuna riga d'esempio.
  - *In corso:* «Carico i materiali…».
  - *Errore:* il messaggio scritto dalla palette, con cosa fare.
  - *Pieno:* la tabella e una riga «N da cambiare, M immagini in più».
  Con FLUX.1 Kontext (una sola immagine) le anteprime non partono: lo dice e
  Genera si spegne finché non si cambia modello o si tolgono le spunte.
- **Materiali della vista** (2026-11-06, ok di Riccardo al lazo libero): quando
  la vista non ha l'elenco dei materiali di Allplan. **+ Seleziona un
  materiale** mette la vista in modo disegno: si traccia il contorno a mano
  libera tenendo premuto, come il lazo del Ritocca, e al rilascio la pagina
  ritaglia il pezzo (fuori dal contorno grigio piatto). Il ritaglio è il
  campione della riga, al posto del cubetto di Allplan; il resto è come sopra:
  «diventa» obbligatorio, **+ Riferimento** facoltativo, **Togli**. I contorni
  restano sulla vista, numerati. **Fine selezione** esce dal disegno. Al
  massimo `MATERIALI_CAMBIATI_MASSIMI` materiali. Il flusso Allplan non cambia.
  - *Vuoto:* «Indica sulla vista le superfici da cambiare: per ognuna scrivi
    cosa diventa.» e il pulsante. Nessuna riga d'esempio.
  - *In corso:* «Disegna sulla vista il contorno di una superficie…».
  - *Errore:* «Il pezzo selezionato non si è potuto ritagliare dalla vista.»
    con cosa fare; una riga senza «diventa» lo dice e non parte.
  - *Pieno:* le righe con il campione, «N di massimo M materiali scelti sulla
    vista».
- ~~**Cosa parte, in breve**~~: tolto il 2026-11-12, ripeteva la riga di
  «Dettagli del preset». Il link al prompt completo sta in fondo all'Invio.
- **Avanzate: mostra e modifica il prompt completo**: il testo vero che parte
  al modello, in inglese, modificabile, con il numero di caratteri. Se l'utente
  lo modifica, i comandi a sinistra non lo toccano più finché non preme
  **Ricomponi dalle scelte**. È l'unico posto dove si scrive testo libero per
  il modello. Solo coi piani Pro e Studio, o con una chiave propria
  (2026-11-05): negli altri piani il pulsante non c'è, e nemmeno «Il prompt
  che parte» di Cambia, Ritocca, Rifai tutto e Com'è stato fatto. Il cliente
  compra il risultato, e un testo in vista si copia.
- **Look fotografico**: i nomi dicono l'effetto («Nitido da rivista», «Caldo
  naturale»…), con una riga sotto che dice cosa cambia. La marca della
  fotocamera o della pellicola resta solo nel prompt. Il look non cambia
  l'inquadratura: quella resta della vista Allplan.
- **I miei preset**: «Nessuno — scelte libere» e Salva queste scelte.
- **Modello**: Nano Banana 2 (predefinito), FLUX.1 Kontext Pro; gli altri
  scritti «non ancora provato» e non selezionabili finché il loro schema non è
  verificato.
- **Qualità**: Base / Altissima definizione (32k) — «da confrontare». Il
  predefinito si sceglie dopo un confronto sulla stessa vista.
- **Varianti per invio**: 1, 2, 3 o 4. Con N varianti partono N lavori nella
  coda con le stesse scelte, uno dopo l'altro, e il costo accanto a Genera è
  N volte quello di un render («circa 69 crediti per 4 immagini»). Se il
  costo del modello non è misurato, resta «non misurato», mai un numero.
- **Fedeltà al disegno**: Rigida / Bilanciata / Libera, predefinita
  Bilanciata (SCELTA). Una riga sotto dice cosa fa ognuna e che i tre testi
  non sono ancora confrontati sul banco di prova. Si conserva quando si
  cambia preset o scena, come la qualità.
- **Immagine di riferimento per lo stile**: un file JPEG o PNG, con la
  miniatura, il nome e Togli. Con FLUX.1 Kontext e Nano Banana Pro il
  comando è spento e dice perché (ricevono una sola immagine).
- **Destinazione e costo**, poi **Prova a secco** e **Genera** («Genera 3
  render» quando le varianti sono più di una).

- **Vuoto:** nessuna vista nella cartella. Al posto della vista: «Nessuna
  vista ancora. Catturala dalla palette in Allplan, oppure scegli un file con
  Usa un'altra vista…», con il percorso della cartella. Preset e dettagli si
  possono impostare; Genera è spento con la ragione scritta accanto.
- **In corso:** una striscia in alto, «Comfy Router sta lavorando · in
  lavorazione · 0:12 · Allplan resta libero», con Annulla. Le scelte restano
  modificabili per il lavoro successivo, ma non toccano quello partito.
- **Errore:** vista non adatta (la vista resta visibile, con la ragione e cosa
  risalvare); invio fallito (frase del motore e gesto successivo, la ricetta
  resta per rifarlo); modello senza schema verificato (si ferma prima di
  partire, e lo dice).
- **Pieno:** vista adatta, preset scelto, dettagli compilati, riassunto,
  destinazione e costo; Genera acceso.

### Studio · Risultato

Mockup: `Main.dc.html`. Titolo: **«È ancora il tuo edificio?»** — è la
decisione che questa schermata deve far prendere.

- Vista predefinita: **prima / dopo con la linea da spostare** (trascinandola o
  con i tasti ← →). Poi **Affiancati** e **Solo render**.
- **Confronta con**: la vista di partenza di Allplan (predefinito) oppure un
  altro render della stessa vista, per esempio lo stesso preset con un altro
  modello (A/B fra modelli).
- **Render di questa vista**: l'elenco dei render fatti dalla stessa vista,
  con modello e data, per sceglierne uno o confrontarne due.
- **Tenuta della geometria** (dal 2026-10-31): «Spigoli ritrovati: 82%», la
  quota degli spigoli della vista Allplan ritrovati nel render, misurata dalla
  coda appena il render è salvato. Sotto `GEOMETRY_DRIFT_WARN` (scelta, non
  tarata) un avviso: «la geometria può essersi mossa». Sempre accanto, la
  frase che la misura è grezza (ombre, neve, vegetazione nuove contano come
  spigoli persi). Se non si è potuta fare: «Non misurata» e il perché, mai un
  numero. Render fatti prima della misura: «Non misurata», il perché e il
  pulsante **Misura ora**.
- **Com'è stato fatto** (la ricetta, chiusa per default dal 2026-11-12, con
  dentro le note del motore): stile, modello, le parole dell'utente,
  intorno, servizio («Comfy Router, senza ripiego»), costo, seme («salvato, il
  modello non lo usa» quando è così), percorso del render e della ricetta.
- **Sotto l'immagine** (dal 2026-11-02): **Ritocca · Variante · Video**, vedi
  «Azioni sotto l'immagine»; dal 2026-11-04 **Cambia · Ritocca · Variante ·
  Video · Altra vista**, vedi «Una barra sola sotto ogni immagine».
- **Adesso**: Apri cartella, Copia immagine, **Esporta per il cliente** (dal
  2026-10-31, vedi sotto).

- **Vuoto:** «Nessun render ancora. Scegli uno stile in Genera e premi
  Genera.» Niente slider, niente ricetta.
- **In corso:** la vista di partenza a tutta larghezza con la striscia di
  avanzamento: tempo trascorso, nome del servizio, stato del lavoro (in coda,
  inviato, in lavorazione), Annulla.
- **Errore:** il messaggio del provider tradotto in una frase utile, più cosa
  fare adesso; la ricetta del tentativo resta visibile, con Rifai. Se il
  servizio dichiara un provider diverso da quello annunciato, il render ha un
  avviso in testa.
- **Pieno:** prima/dopo, Render di questa vista, tenuta della geometria
  (spigoli ritrovati, o «Non misurata» col perché), ricetta, Rifai.

### Studio · Passi

Mockup: `Passi.dc.html`. Decisione di Riccardo del 2026-10-28 (PRD, sezione
5): si lavora su un render dopo l'altro (prima lo stile, poi gli alberi, poi
le persone) e ogni passo deve restare ritrovabile, senza diventare un grafo a
nodi alla Comfy o Weavy. **Costruita il 2026-10-30** (sotto, «Studio · Passi,
costruito il 2026-10-30», dove si scosta). Nella barra laterale la voce si
chiama **Passi** (era Livelli).

**Colonna sinistra — l'albero dei passi di una vista**
- Un albero solo, in una colonna. La riga **0 è la vista Allplan**. Ogni passo
  parte da quello sopra di lui ed è rientrato sotto di lui: «1 Rivista
  d'architettura», sotto «2 Alberi sul fronte», sotto «3 Persone in
  movimento».
- Un passo nuovo fatto da un punto qualsiasi apre un **ramo** lì sotto: se dal
  passo 2 si fa «4 Cielo al tramonto», il 4 sta sotto il 2, accanto al 3, con
  la sua linea di collegamento. Un altro render dalla vista (per esempio lo
  stesso stile con Kontext Pro) è un ramo sotto lo 0.
- Niente grafo a nodi, niente schede di versione: con le schede un ramo
  sparisce, con i nodi dopo dieci passi è un groviglio.
- Ogni riga: numero, nome breve (dalle scelte o dalla nota), modello, data.
  **Nuovo passo da qui** su ogni riga.

**Centro — prima e dopo**
- Prima/dopo con la linea, come in Risultato, fra il passo scelto e **la vista
  Allplan** (predefinito) oppure **il passo prima**. Affiancati a un clic.

**Colonna destra — il passo scelto**
- **La strada** del passo, dalla vista fino a lui: «0 › 1 › 2 › 4».
- **La ricetta** del passo (com'è stato fatto, come in Risultato).
- **Tenuta della geometria**, misurata **sempre contro la vista Allplan**, non
  contro il passo prima: è l'edificio disegnato che deve restare, e un
  confronto col passo prima nasconderebbe lo spostamento accumulato. Stessa
  misura e stesse frasi di Risultato; senza misura: «Non misurata» e perché.
- **Dalla seconda generazione di fila**, un avviso: «Questo passo è la 2ª
  generazione di fila: gli spigoli possono spostarsi un poco a ogni
  giro. Se vedi l'edificio cambiare, rifai pulito dalla vista.» Quanto si
  spostino davvero lo misura il piano «catena» del banco di prova (sezione 9
  del PRD).
- **Rifai pulito dalla vista**: unisce le richieste della strada (stile del
  passo 1, alberi del 2, cielo del 4) in **un solo invio dalla vista
  Allplan**. Il risultato è un ramo nuovo sotto lo 0. Prima dell'invio si
  vedono destinazione e costo (regola 5).
- **Rifai questo passo**: stesso punto di partenza, stessa richiesta, un ramo
  nuovo accanto.

- **Vuoto:** nessun render della vista. L'albero ha solo la riga 0, «Vista
  Allplan», e sotto «Nessun passo ancora. Genera un render da Genera: sarà il
  passo 1.» Niente prima/dopo, niente ricetta.
- **In corso:** il passo che sta nascendo è già nell'albero, al suo posto, con
  la striscia di avanzamento (servizio, stato del lavoro, tempo, Annulla).
  Gli altri passi restano sceglibili.
- **Errore:** il passo fallito resta nell'albero, marcato «non riuscito», con
  la frase del motore e il gesto successivo; non ha figli e non si può
  scegliere come punto di partenza. Se il passo da cui parte è stato
  cancellato dalla cartella, lo dice («il punto di partenza non c'è più») e
  propone Rifai pulito dalla vista.
- **Pieno:** albero con rami, prima/dopo sul passo scelto, strada, ricetta,
  tenuta «Non misurata», l'avviso dove serve, i due Rifai.

### Studio · Ritocca

Mockup: `Ritocca.dc.html`. Riscritta il 2026-10-28 su richiesta di Riccardo:
le aree si disegnano come in Photoshop e le modifiche si scrivono su note
adesive sull'immagine. **Costruita il 2026-10-30** (prompt 6), prima del piano
«aree» del banco di prova: il modo in cui partono le aree (contorni disegnati o
maschera) è un'impostazione, `RITOCCO_MODO_AREE` in `core/config.py`, SCELTA
sui contorni finché il banco non dice quale tiene fermi i pixel fuori dalle
aree. Dove la schermata costruita si scosta da qui, sotto «Ritocca, costruita
il 2026-10-30».

**Strumenti**, in una fila sopra il render:
- **Rettangolo**: si trascina un riquadro.
- **Selezione libera**: lazo a mano libera, come in Photoshop; la forma si
  chiude da sola quando si rilascia.
- **Clicca una superficie**, in grigio con «In arrivo» fino alla mappa
  materiali di Allplan (PRD, sezione 8): senza la mappa lo Studio non sa dove
  finisce una superficie.

**Sul render**
- Ogni area ha il suo contorno e il suo **numero** (1, 2, …).
- A ogni area si attacca una **nota adesiva**, numerata come l'area, con il
  testo della modifica: «infissi in legno scuro», «una panchina in pietra».
  La nota si sposta per non coprire quello che si sta guardando; l'area no.
- Un'area si cancella con la sua nota.

**Colonna destra**
- **Le note in elenco**, nello stesso ordine e con lo stesso numero, per
  rileggerle e correggerle senza cercarle sull'immagine.
- **Un solo Applica per tutte le note**: «Applica le 2 note», con
  la destinazione e il costo di **un** invio (regola 5).
- Il risultato è **un passo nuovo nell'albero** (Studio · Passi), figlio del
  render su cui si sono disegnate le aree.
- ~~**Da verificare prima**~~ tolto dallo schermo il 2026-11-12 (erano note
  per noi, restano nel PRD); a schermo resta una riga: «Per un materiale tutto
  diverso, rifai il render da Genera», col perché nel «?». Era: se il modello
  rispetta le aree e lascia uguale il resto (piano «aree» del banco); che la
  selezione libera diventa una maschera, e un riempimento con maschera non
  ricalcola riflessi e luce di rimbalzo (trappola di `CLAUDE.md`: per un
  cambio radicale serve la modalità variante); che Clicca una superficie
  aspetta la mappa materiali.

Tolta la vecchia **«Grana del nuovo materiale»** (fine / media / grossa): con
note scritte a parole non ha un comando da muovere, e i modelli del Router
non hanno un dettaglio della grana (la ricetta lo scrive già come assente).

- **Vuoto:** nessun render della vista: «Prima serve un render. Generane uno
  da Genera.» Gli strumenti sono spenti con la ragione accanto. Con un render
  ma senza aree: il render, gli strumenti accesi e «Disegna un'area, poi
  scrivi cosa cambiare nella sua nota»; Applica è spento con la ragione.
- **In corso:** dopo Applica, aree e note restano visibili e bloccate, con la
  striscia di avanzamento (servizio, stato, tempo, Annulla). Allplan e il
  resto dello Studio restano liberi.
- **Errore:** un'area senza nota o una nota vuota ferma Applica e lo dice
  accanto a quella nota; un invio fallito lascia aree e note come erano, con
  la frase del motore e Rifai; un risultato di dimensione diversa dal render
  di partenza si dice, perché fuori dalle aree non si può più rimettere il
  pixel di prima.
- **Pieno:** render con aree e note numerate, elenco delle note, Applica con
  destinazione e costo. Dopo l'invio, il passo nuovo è scelto nell'albero.

### Ritocca, costruita il 2026-10-30

Codice in `core/aree.py` (aree, i due modi, misura), `core/coda.py` (lavoro
del formato 3), `core/studio/`; screenshot di ogni stato in
`docs/ui/studio-ritocca/`, con render finti. Dove si scosta da sopra, e perché:

- **Il render da ritoccare si sceglie in testa**, fra i passi riusciti della
  vista (predefinito: quello scelto nei Passi, altrimenti il più recente).
  Cambiarlo svuota le aree: erano disegnate su un'altra immagine.
- **Risultato in Ritocca, non subito nei Passi.** Finito l'invio la scheda
  mostra il prima/dopo contro il render ritoccato, la misura **fuori dalle
  aree** accanto e le note applicate, con «Ritocca questo render», «Torna al
  render di prima» e «Vedi nei Passi». Il passo nuovo è già scelto
  nell'albero. La misura è quella del banco (`DIFFERENZA_PIXEL_SOGLIA`,
  `AREE_BORDO_ESCLUSO_PX`, SCELTE), contro il render di partenza senza
  contorni; se il motore non l'ha potuta fare, «non misurato». Un risultato di
  dimensione diversa lo dice nella stessa frase.
- **La riga della destinazione dice cosa parte**: «Il render, con le aree
  disegnate sopra, va a …» (o «con la maschera delle aree»), non «la vista».
- **In Passi un ritocco è un passo come gli altri**: nome «Ritocco · 2 note ·
  …», nella ricetta le aree con le note e il modo, il pannello «Fuori dalle
  aree». «Rifai questo passo» lo rimanda con le stesse aree e lo stesso modo,
  anche se nel frattempo `RITOCCO_MODO_AREE` è cambiato. «Rifai pulito dalla
  vista» mette le note come richieste a parole e avvisa che le aree non valgono
  più: erano disegnate su un render.
- **Il motore non rimette i pixel fuori dalle aree.** L'idea della sezione 8
  del PRD (incollare il render di partenza fuori dalle aree, con il bordo
  sfumato) non è in questo PR: prima si guarda cosa fa il modello da solo.

### Ritocca col compositore, costruita il 2026-11-09

Dalla proposta «flussi» approvata da Riccardo il 2026-11-09 (Design canvas
«AIRENDER Studio flussi», schermata A4). Codice in `core/aree.py`
(`da_testo`, `contorno_tratto`, azione e spessore dell'area),
`core/blocchi.py` (`AZIONI_AREE`), `core/studio/pagine/studio.js`. La web app
usa la stessa pagina, quindi cambia insieme. Screenshot con un provider finto:
`docs/ui/studio-ritocca/55-ritocca-compositore-tre-aree.png` e
`56-ritocca-esito-pennelli.png`. Cosa cambia rispetto a sopra:

- **Una frase sola al posto delle note adesive.** Sotto il render c'è un
  campo unico: «rivesti @1 di legno chiaro, metti persone in @2, togli il palo
  in @3». Ogni area disegnata entra nel testo come @N dove sta il cursore;
  sotto il campo, un bottone per area rimette la sua @. Il server divide la
  frase ai punti, alle virgole e ai punto e virgola: ogni pezzo va alle aree
  che chiama, un pezzo senza @ va con quello prima. Con un'area sola tutta la
  frase è sua. A destra, per ogni area, si legge la parte di testo che le
  tocca: quello che parte non è mai una sorpresa.
- **Pennello aggiungi (verde) e pennello togli (rosso)**, accanto a
  rettangolo e selezione libera, con il cursore dello spessore
  (`PENNELLO_SPESSORE`, `PENNELLO_SPESSORI`, SCELTE). Un tratto è un'area come
  le altre: il motore ne ricava il contorno (punte tonde) e lo disegna, lo
  maschera, lo misura e lo incolla come un poligono. Nel prompt la riga di un
  tratto dice «add» o «remove and rebuild what is behind»; un tratto «togli»
  che la frase non chiama toglie e basta.
- **Rif. per area**: «+ Rif.» nell'elenco delle aree, come prima «+
  Immagine» nella nota.
- **Togliere un'area rinumera il testo**: la sua @ sparisce, quelle dopo
  scalano di uno.
- **Errori**: un'area che la frase non chiama («L'area 2 non è nel testo»)
  o una @ che non esiste ferma Applica, con il motivo accanto.
- **Restano uguali**: un invio solo, destinazione e costo prima di Applica,
  il risultato come passo figlio, la misura fuori dalle aree, «Clicca una
  superficie» in grigio. Il testo della frase non si salva nel lavoro: si
  salvano le note per area che ne escono, come prima.
- **Non fatto in questo PR**: «Punti» come campione di materiale sul render
  (la selezione libera dei materiali c'è già in Genera) e «Popola» con
  «Decide il modello»; vengono col PR di Cambia e Popola.

## Studio v1, costruito il 2026-10-28

Codice in `core/studio/`, screenshot di ogni stato (anche a 1280×800) in
`docs/ui/studio-v1/`: lì i «render» sono la vista colorata da un provider
finto, non render veri. Dove lo Studio v1 si scosta dal mockup, e perché:

- **In testa non c'è «Collegato ad Allplan 2026 · BOSCO · …».** Lo Studio non
  parla con Allplan: mostra se la coda dei lavori gira, la cartella delle
  viste e, se la palette l'ha salvata, la camera (Prospettiva centrale o
  Vista parallela). Dire «collegato» sarebbe un'informazione che non abbiamo.
- ~~**Resa**: solo Fotorealistico è attiva.~~ Tutte e cinque attive dal
  2026-10-31 (prompt 12), vedi sotto «Rese non fotografiche».
- ~~**Intorno** Città / Periferia / Campagna, **Verde** e **persone «Poche»**:
  in grigio per la stessa ragione.~~ Attive dal 2026-10-29, con i blocchi
  della bozza 4. Le voci attive sono quelle di `core/blocchi.py`, e lo Studio
  le legge da lì: una voce nuova nei blocchi compare da sola.
- **Ora / Luce** degli esterni ha le sei voci dei blocchi (Mezzogiorno,
  Estate luminosa, Giorno, Ora d'oro, Ora blu, Notte con luna), non le quattro
  del mockup.
- ~~**I miei preset**: «Nessuno — scelte libere» e Salva in grigio.~~ Attivi
  dal 2026-10-31 (prompt 9), vedi sotto «I miei preset».
- **Le miniature** sono disegnate dallo Studio (casa, cielo, luce), non
  immagini: illustrazioni dichiarate tali, come chiede la decisione del
  2026-10-27. Dal 2026-10-29 un preset può avere una **miniatura vera**,
  ritagliata da un render del banco di prova (`scripts/miniatura_da_banco.py`):
  sotto la tessera c'è «render vero del <data>», e la riga sopra la griglia
  dice quante sono illustrazioni e quante render veri.
- **Rifai con la stessa ricetta** è diventato **Variante** sotto l'immagine
  (2026-11-02): parte con un clic, e destinazione e costo sono scritti sotto i
  pulsanti prima del clic (regola 5).
- **Genera è spento mentre un lavoro è in corso**, con la ragione accanto: due
  invii di fila per un clic doppio si pagano due volte. Le scelte restano
  modificabili.
- **Confronto fra immagini di proporzioni diverse**: la linea del prima/dopo
  sovrappone le due immagini alla misura del render; se le proporzioni
  differiscono (Kontext rende circa il 3% più largo), lo dice sotto con la
  percentuale, perché gli spigoli possono non coincidere per questo.
- **Usa un'altra vista…** elenca le viste della cartella e accetta un file:
  lo Studio ne mette una copia nella cartella con un nome nuovo.

## Studio · Passi, costruito il 2026-10-30

Codice in `core/passi.py` (l'albero), `core/coda.py` (lavori che partono da
un passo), `core/studio/` (rotte e pagina). Screenshot di ogni stato, anche a
1280×800, in `docs/ui/studio-passi/`: lì i render sono la vista tinta da un
provider finto. Dove la schermata si scosta da quello che c'è sopra, e perché:

- **L'albero sta in un file accanto alla vista**, `<nome della vista>.passi.json`,
  scritto atomico e leggibile a mano (un esempio in
  `docs/ui/studio-passi/esempio-vista.passi.json`). Lo Studio lo allinea ai
  lavori della cartella ogni volta che lo legge: un render che l'albero non
  ha ancora (fatto prima di questo file, dalla palette o da riga di comando)
  diventa un figlio della vista. Un passo non si cancella mai: se la cartella
  dei lavori viene pulita, resta con l'ultimo stato noto e «render tolto». Un
  file dell'albero che non si legge non si riscrive: lo Studio lo dice e si
  ferma.
- **«Nuovo passo da qui» sulla riga 0 porta a Genera.** Dalla vista si parte
  scegliendo uno stile, e lo stile si sceglie in Genera: un secondo posto per
  farlo direbbe la stessa cosa in due modi.
- **Un passo nuovo è una richiesta a parole**, una sola per invio, con il
  modello (predefinito: quello del passo da cui parte), il prompt che parte
  (in sola lettura), destinazione e costo, e **Applica**. «Su un'area…»
  apre Ritocca sul render di quel passo (dal 2026-10-30), come «Ritocca da
  qui» in Adesso. Il prompt di un passo non si scrive a mano:
  quello si fa in Genera, dove i comandi sanno che il testo è stato toccato.
- **Da un render non si controlla l'idoneità**: giudica una vista di Allplan
  (shaded, toni, sfondo), e un render non lo è. Si controlla che il render ci
  sia e che sia un'immagine; se non c'è più, la coda non manda niente e dice
  di rifare pulito dalla vista.
- **Rifai questo passo** e **Rifai pulito dalla vista** chiedono conferma con
  destinazione e costo, come Rifai in Risultato. Rifai pulito mostra la
  strada, lo stile del primo passo, le richieste in fila e il prompt intero
  prima di Conferma e invia; il risultato è un ramo sotto lo 0 che si chiama
  «Tutto dalla vista · <preset>». È spento su un passo partito dalla vista:
  non c'è niente da unire.
- **L'avviso parte da `PASSI_AVVISO_DA_GENERAZIONE` generazioni** (2,
  SCELTA in `core/config.py`) e lo dice sotto il testo: la soglia si tara
  con il piano «catena» del banco di prova.
- **In corso:** la striscia sta sotto la riga del passo che nasce, nella
  colonna; il passo scelto resta quello che era. Quando il lavoro finisce, lo
  Studio resta in Passi e sceglie il passo nuovo (da Genera, invece, va a
  Risultato come prima).
- **Errore:** il passo fallito ha l'etichetta «non riuscito», la frase del
  motore al centro sopra l'immagine da cui era partito, e Nuovo passo da qui
  spento con la ragione; Rifai questo passo resta acceso. Un passo il cui
  passo di partenza ha perso il render ha l'avviso «Il punto di partenza non
  c'è più», Rifai questo passo spento e Rifai pulito dalla vista in evidenza.
- **Il passo 0 si può scegliere**: al centro c'è la vista da sola, e niente
  ricetta.
- **Un lavoro della coda è nel formato 2**: in più ha il passo di partenza,
  il file del suo render e le richieste. La coda legge ancora il formato 1;
  un motore vecchio rifiuta il 2 invece di mandare la vista al posto del
  render.

## I miei preset, costruiti il 2026-10-31

Nella colonna destra di Studio · Genera. Salvano tutte le scelte di adesso
(scena, assi, materiali a parole, qualità, risoluzione, modello e il prompt
scritto a mano se c'è) con un nome. Stanno in `preset-utente.json` nella
cartella delle viste: sono dell'utente, non del repository.

- **Vuoto:** il menu dice «Nessuno salvato — scelte libere»; c'è solo
  **Salva queste scelte**.
- **In corso:** il salvataggio è istantaneo; un nome già usato chiede se
  sostituirlo, e Elimina chiede conferma («Non si può annullare»).
- **Errore:** nome vuoto, troppo lungo o doppio: la frase dice cosa fare. Se
  il file non si legge, lo Studio non lo sovrascrive: lo mette da parte come
  `preset-utente.non-letto-<data>.json` e lo scrive in un avviso rosso.
- **Pieno:** il menu con i preset dell'utente; sceglierne uno carica le
  scelte, e compaiono **Rinomina** ed **Elimina**. Se il preset è stato
  salvato con un'altra versione dei blocchi, una riga dice cosa non esiste
  più («luce: «alba» non esiste più») e che il resto è caricato.

Nella palette di Allplan i miei preset non compaiono: il menu della palette è
scritto nel `.pyp` quando si installa, e cambiarlo da script non è provato.

## Fedeltà al disegno, costruita il 2026-10-31

Un comando a tre voci nella colonna destra di Studio · Genera e un menu
«Fedeltà al disegno» nella sezione 2 della palette. Non è un parametro del
modello: cambia la regola fissa in testa al prompt (blocchi, bozza 6).

- **Vuoto:** non esiste: c'è sempre una voce scelta, Bilanciata
  all'apertura, che è la regola fissa di sempre.
- **In corso:** come Genera; la fedeltà del lavoro partito non cambia se la
  si tocca dopo.
- **Errore:** una fedeltà che il motore non conosce (palette vecchia, preset
  salvato con una voce tolta) si rifiuta con le voci possibili; un mio
  preset con una fedeltà che non c'è più torna a Bilanciata e lo dice.
- **Pieno:** «Cosa parte, in breve» comincia con «Fedeltà al disegno
  rigida» o «libera» quando non è Bilanciata; il prompt completo mostra il
  testo vero.

## Immagine di riferimento per lo stile, costruita il 2026-10-31

Nella colonna destra di Studio · Genera, sotto le varianti. Nella palette
non c'è: il riferimento si sceglie nello Studio.

- **Vuoto:** una riga dice cosa fa («solo colori, luce e materiali, non la
  forma; parte come seconda immagine») e il campo per scegliere il file.
- **In corso:** come Genera. Prima del clic, sotto la destinazione:
  «Partono due immagini: la vista e il riferimento per lo stile.» Finché
  Nano Banana 2 non ha ricevuto due immagini in una chiamata vera, un avviso
  giallo dice che questo render è la prova.
- **Errore:** un file che non è JPEG o PNG, o più pesante di quanto si manda
  a Comfy Router, si rifiuta al caricamento. Con un modello che riceve una
  sola immagine il comando è spento e, se un riferimento era già caricato,
  Genera è spento con la ragione. Se il file sparisce prima dell'invio, il
  lavoro si ferma senza mandare niente.
- **Pieno:** miniatura, nome del file e misure, Togli. La ricetta salva
  l'impronta del riferimento, non l'immagine; il file resta in
  `riferimenti/` nella cartella delle viste.

## Inserisci in un luogo, rifatta il 2026-11-01

Dal 2026-11-04 si chiama **Fotoinserimento** (Riccardo: funziona anche per un
arredo dentro una foto di un interno). Sottotitolo: «Quello che hai in
Allplan, edificio o arredo, dentro una foto vera: dall'alto, a volo d'uccello
o da terra.» Passi: «Segna dove va», «Com'è stata scattata la foto», «Da
Allplan». Il prompt non cambia.

Il fotoinserimento: l'edificio di Allplan dentro una foto del luogo. La prima
versione (in cima alla colonna destra, immagine piccola, stile spento) non si
capiva: Riccardo l'ha provata con uno Street View e non ha trovato dove
disegnare. Adesso è un **modo di Genera**: in cima due schede grandi,
«Render della vista» e «Inserisci in un luogo». Lo Studio non scarica mappe:
la foto la porta l'utente. Screenshot in `docs/ui/studio-contesto/` (65–68).

- **Vuoto:** passo 1 «Carica la foto del luogo», un riquadro grande
  tratteggiato da cliccare (Google Earth, ortofoto, drone, foto da terra o
  Street View); i passi 2 e 3 accanto, il 2 spento. Genera spento: «Passo 1:
  carica la foto del luogo.»
- **Foto senza area:** la foto grande a sinistra, sopra in blu «Trascina sulla
  foto un rettangolo, da un angolo all'altro, dove deve stare l'edificio».
  A destra 2 · Com'è stata scattata la foto (Zenitale | Volo d'uccello | Da
  terra (foto), con una riga su che foto è) e 3 · L'edificio, da Allplan (la
  vista in piccolo e che vista catturare per quell'inquadratura). Ogni passo
  fatto ha la spunta verde. Genera e Prova a secco spenti con la ragione.
- **Pieno:** il rettangolo numerato sulla foto (trascinando si rifà),
  «cambia foto», «togli». Sotto a sinistra «Facoltativo»: materiali a parole
  (la vista è grigia: senza materiali li sceglie il modello), dove si trova,
  «È uno screenshot con scritte e icone» (non c'è con Da terra), «Cerca il
  luogo sul web» in grigio, Da provare. Una riga dice che preset e stile qui
  non servono. A destra «Cosa parte», modello, risoluzione, varianti, invio;
  qualità e fedeltà al disegno non ci sono perché non entrano nel prompt.
- **In corso:** come Genera. Prima del clic: «Partono due immagini: prima il
  contesto con l'area segnata in magenta, poi la vista.»
- **Errore:** file non JPEG/PNG o troppo pesante rifiutato al caricamento;
  con FLUX.1 Kontext Genera è spento con la ragione; «pulisci la mappa» con
  Da terra rifiutato dal motore; se il file sparisce prima dell'invio il
  lavoro si ferma senza mandare niente.
- **Risultato:** come prima: la misura «fuori dall'area» al posto della
  tenuta degli spigoli.
- Tornando a «Render della vista» la foto e l'area restano da parte e
  tornano quando si rientra.

## Rese non fotografiche, costruite il 2026-10-31

Le tessere della sezione 1 · Resa di Studio · Genera, e il menu Resa della
palette. Blocchi nella bozza 7; quali rese e che testi li ha scelti Claude
(«vedi tu» di Riccardo).

- **Vuoto:** non esiste: all'apertura è scelto Fotorealistico, che non
  aggiunge niente al prompt di sempre.
- **In corso:** come Genera; cambiare resa dopo il clic non tocca il lavoro
  partito.
- **Errore:** una resa che il motore non conosce si rifiuta con quelle
  possibili; un mio preset con una resa tolta torna a Fotorealistico e lo
  dice.
- **Pieno:** la tessera scelta; sotto il titolo una riga dice cosa spegne
  («Schizzo a matita spegne: materiali a parole, look fotografico, cielo,
  qualità»). Gli assi spenti restano visibili, in grigio, con «Spento con la
  resa …: non parte». Le miniature sono l'illustrazione con un filtro, non
  render del modello.

## Esporta per il cliente, costruita il 2026-10-31

In Studio · Risultato, sotto «Adesso». Decisioni di Riccardo: JPG, PNG, o PSD
con un livello per ogni passaggio. Dove salvare non l'ha detto: si salva in
`esportati/` nella cartella delle viste, e «Apri cartella esportati» la apre.
Alla grandezza del render, senza ingrandire.

- **Vuoto:** il pulsante c'è solo quando il render scelto ha un file; senza
  render non compare.
- **In corso:** tre scelte di formato con una riga ciascuna (cosa contiene,
  dove va, che nel file ci sono solo immagini), poi Esporta → «Esporto…».
- **Errore:** il render tolto dalla cartella, un formato sconosciuto,
  un'immagine che non si legge: la frase dice il fatto e cosa fare, il file
  non si scrive.
- **Pieno:** «Salvato: vista-1-passo2-20261031-221500.psd», misure, peso e,
  per il PSD, i nomi dei livelli dal basso: «Vista Allplan, 1 · Rivista
  d'architettura, 2 · due alberi davanti al fronte». Un passo senza render
  (fallito o tolto) non diventa un livello vuoto.

Nel file non entrano prompt, ricetta o chiave: si riscrivono solo i pixel.

## Regola, prima di esportare, costruita il 2026-11-09

Richiesta di Riccardo (2026-11-08): «prima di esportare, tool per classici
ritocchi di illuminazione, contrasto, luci, ombre, curve come fa la palette di
Photoshop». Mockup: Design canvas, schermata A5 «Consegna», sezione 2 · Regola.
Per ora vive dentro «Esporta per il cliente» (Studio · Risultato › Adesso), sopra
la scelta del formato: la schermata Consegna intera (Finale per uso, più immagini
insieme, TIFF e PDF) arriva con i PR successivi del piano dei flussi.

Gira sul computer: nello Studio sul PC, nella web app dentro il browser. Nessuna
immagine parte e non costa crediti; lo si scrive in verde accanto al titolo
(«su questo computer · gratis», sul web «in questo browser · gratis»).

- **Vuoto:** sei cursori a 0 (Esposizione, Contrasto, Luci, Ombre, Temperatura,
  Saturazione, da −100 a +100), la curva diritta. «Senza regolazioni» e
  «Azzera» sono grigi: non c'è niente da togliere.
- **In corso:** il cursore si muove e il render sul palco cambia (anteprima
  col lato lungo di 1600 px, rifatta dal motore pochi centesimi di secondo dopo
  che il cursore si ferma). Sopra il palco: «Con le regolazioni · le vedi qui,
  il file le prende quando esporti». **Senza regolazioni** si tiene premuto (col
  mouse, o Spazio dalla tastiera) e mostra il render com'era. Doppio clic su un
  cursore lo riporta a 0. **Curva** apre un quadrato coi toni: clic aggiunge un
  punto (al massimo 8), trascinare lo sposta, doppio clic o Canc lo toglie,
  frecce lo spostano di 1 (Maiusc: 10). Sotto i punti la curva vera calcolata
  dal motore.
- **Errore:** un valore che il motore rifiuta (un cursore fuori misura, due
  punti sullo stesso tono) dice il fatto e cosa fare nel pannello; il file non
  si scrive.
- **Pieno:** dopo Esporta, sotto «Salvato: …» una riga dice cosa c'è dentro:
  «Con le regolazioni: Esposizione +8, Contrasto +12, Curva (3 punti).» oppure
  «Senza regolazioni: i pixel del render come sono.». Nel PSD le regolazioni
  sono un livello in più in cima («Regola · Esposizione +8, …»), sopra il
  render com'era: in Photoshop si spegne e si confronta.

Cosa dice di sé: Luci e Ombre cambiano i toni chiari e scuri **su tutta
l'immagine**, come una curva; non sono il recupero locale di Photoshop che
schiarisce solo le zone in ombra. La Temperatura non è in kelvin. Tutti i
numeri (quanti stop dà l'Esposizione, quanto spinge il Contrasto…) sono scelti
in `core/config.py`, `REGOLA_*`, e non ancora confrontati su render veri.
Le regolazioni restano a ogni render finché lo Studio è aperto; chiuso lo
Studio, si ripartono da 0.

## Studio · Video, costruita il 2026-11-01

Decisione di Riccardo (2026-10-31): «I video li voglio che possa caricare i
render fatti e costruirlo da quelle», con Seedance, l'ultimo modello. La scheda
Video della rotaia si accende. Il modello è `byteplus/dreamina-seedance-2-5-260628`
(Seedance 2.5) attraverso Comfy Router, preso dalla documentazione del Router e
mai provato con una chiamata vera: lo si dice prima di ogni invio.

**Colonna sinistra: le immagini**
- **Come partire**, tre scelte:
  - **Da un render**: il video comincia dal render e la camera si muove.
  - **Da un render a un altro**: primo e ultimo fotogramma, per esempio
    lo stesso edificio di giorno e di notte, o due punti di vista.
  - **Più render come riferimento**, fino a 4: il modello li usa come
    riferimento dell'edificio, ma non parte da nessuno di loro. È la scelta
    che tiene meno la geometria, e lo dice.
- Ogni posto si riempie con **Carica un render…** (JPEG o PNG, anche fatti
  fuori da AIRENDER) oppure arriva già pieno da Risultato › **Fai un video da
  qui**.
- Il video prende la forma della prima immagine: con un primo fotogramma il
  modello non accetta un altro formato.

**Colonna destra: il movimento e l'invio**
- **Movimento della camera**: Avanza piano, Gira attorno, Panoramica, Sale
  come un drone, Camera ferma (si muovono solo luce, nuvole e persone). Più
  **Cosa succede, a parole** (facoltativo).
- **Durata** 5 o 10 secondi, **Risoluzione** 720p o 1080p, **Audio** spento
  (si accende a mano: per un render d'architettura di solito non serve).
- **Dove va**, prima del clic (regola 5): «Le immagini vanno a Comfy Router
  (api.comfy.org) → byteplus/dreamina-seedance-2-5-260628 (ByteDance,
  Seedance 2.5), senza ripiego su altri servizi», quante immagini partono, e
  il costo «non misurato».
- **Prova a secco** e **Genera video**.

**I video fatti**, sotto: ognuno col suo lettore, le immagini da cui è nato,
durata, risoluzione e costo letto dal servizio; **Apri cartella**.

- **Vuoto:** nessuna immagine scelta: «Carica il render da cui partire, oppure
  da Risultato premi Fai un video da qui.» Genera video è spento con la
  ragione accanto. Nessun video fatto: «Nessun video ancora.»
- **In corso:** il video in lavorazione in cima all'elenco con stato e tempo
  («Seedance di solito ci mette qualche minuto»), Annulla finché non è
  partito. Lo Studio e Allplan restano liberi; le immagini scelte restano.
- **Errore:** la frase del motore (servizio, chiave, crediti, tempo scaduto)
  con cosa fare, sul video fallito. Un'immagine troppo pesante o che non è un
  JPEG/PNG si rifiuta al caricamento, non al clic.
- **Pieno:** le immagini scelte, il movimento, Dove va e Genera video acceso;
  sotto, i video fatti, il più recente per primo.

## Storico e ritocco che tiene il resto, costruiti il 2026-11-02

Decisione di Riccardo (2026-11-02): «Quando faccio una nuova cattura vista
sparisce il render precedente e i passi, non va bene, deve rimanere storico» e
«se avevo già aggiunto persone e gli dico di aggiungerne altre in un posto con
una auto mi ha fatto sparire quelle precedenti». Niente interfaccia a nodi.

**Storico: la colonna a sinistra, in ogni scheda** (era una striscia in alto;
colonna scelta da Riccardo il 2026-11-05, mock B, perché con molte viste la
striscia si allungava di lato senza fine)
- Un gruppo per vista, uno sotto l'altro, la vista catturata per ultima in
  alto. Ogni gruppo si apre e si chiude dalla sua testa (freccia, miniatura
  della vista, nome, quante immagini fatte); senza una scelta a mano è
  aperta la vista su cui si lavora e quella appena catturata. Si scorre in
  verticale, dentro la colonna.
- «Chiudi» in cima riduce la colonna a una barra sottile «Storico», per
  dare all'immagine tutta la larghezza; la scelta resta su questo PC.
- Dentro il gruppo una tessera per immagine, su due colonne: ogni cattura,
  render, modifica, ritocco e video, nell'ordine in cui sono nate. Etichette di una o due parole («Vista»,
  «Render 1», «Ritocco 3», «Video»); il resto (stato, data) al passaggio del
  mouse.
- Un clic porta all'immagine: la cattura in Genera, un render o un ritocco in
  Risultato (e diventa il passo scelto, quindi Ritocca parte da lì), un video
  in Video.
- Una cattura nuova dalla palette apre un gruppo nuovo con «Nuova»: i gruppi
  di prima restano. In Genera, senza lavori in corso, la cattura nuova si
  apre subito; altrove resta nello storico e quello su cui si lavora non
  cambia.
- **Vuoto:** nessuna vista nella cartella: la colonna non c'è.
- **In corso:** la tessera del lavoro c'è già, e pulsa finché non finisce.
- **Errore:** la tessera dice «Errore» o «Annullato»; un file dei passi
  rotto lascia nel suo gruppo solo la cattura, gli altri gruppi restano.
- **Pieno:** tutte le immagini, quella aperta bordata.

**Ritocco: cambiano solo le aree**
- Il modello ridisegna tutta l'immagine. Il render del ritocco è il suo
  risultato incollato **solo dentro le aree** (allargate di
  `RITOCCO_INCOLLA_MARGINE_PX`, bordo sfumato di
  `RITOCCO_INCOLLA_SFUMATURA_PX`, entrambi scelti) sul render da cui parte:
  fuori, i pixel sono quelli di prima. Il risultato intero del modello resta
  in `lavori/fatto/<id>.modello.png`.
- Finito un ritocco, il prossimo parte da lì: dall'ultima immagine, non da
  quella di prima.
- Il pannello «Fuori dalle aree» dice «com'era prima» invece della misura;
  la misura del risultato intero resta nello stato del lavoro.

## Azioni sotto l'immagine, meno parole e video, costruiti il 2026-11-02

Proposte 3, 4 e 5 delle migliorie allo Studio, più due richieste di Riccardo
sul video («devo poter caricare le immagini frame di riferimento, ad esempio
inizio, fine e intermezzo», «le immagini del video le carichi direttamente dai
render fatti», durata più lunga).

**Azioni sotto l'immagine (Risultato)**
- Tre pulsanti uguali per ogni render: **Ritocca** (apre Ritocca su questo
  render), **Variante** (stessa ricetta, un'altra immagine), **Video**.
- Sotto i pulsanti, sempre visibile: «Variante: va a <servizio> · costo».
- Il risultato nasce accanto all'immagine da cui parte: la striscia dello
  storico è in ordine d'albero, ogni immagine subito dopo quella da cui parte.
  Finito, è già quello scelto.
- **Video** apre un riquadro piccolo: movimento della camera, «Cosa succede» a
  parole (facoltativo, entra nel prompt), dove va con modello «mai provato»,
  durata e risoluzione (le prime della scheda Video), **Genera video**. Spento
  finché non c'è un movimento, o se un video è già in lavorazione, con la
  ragione accanto. Mandato: «Video in coda», e la tessera compare nella
  striscia accanto all'immagine.
- Al posto di «Cambia una parte» e di «Rifai con la stessa ricetta».
- Dal 2026-11-04 la riga di Variante dice da dove riparte e con cosa: «Variante:
  un'altra versione di questa immagine. Riparte dalla vista Allplan (o
  dall'immagine da cui era nata questa), con lo stesso stile (…) e lo stesso
  modello (…). Va a <servizio> · costo».
- Dal 2026-11-04 un quarto pulsante, **Altra vista** (Porta su un'altra vista),
  per i fotogrammi di un video da più viste Allplan. Apre un riquadro come
  Video: «Su quale vista» (le altre catture della cartella), stile, modello e
  l'elenco delle richieste e note dei ritocchi che porta, la frase «Questa
  immagine parte come seconda immagine… Le aree dei ritocchi non si portano»,
  dove va e costo, **Porta su questa vista**. Vuoto: «Non c'è un'altra vista.
  In Allplan inquadra il punto di vista del prossimo fotogramma e cattura
  dalla palette: comparirà qui.» Mandato: «In coda sulla vista …». Il
  risultato è un passo 1 della vista nuova.

**Meno parole**
- Le spiegazioni lunghe diventano un «?» accanto all'etichetta: il testo
  intero al passaggio del mouse o con Tab. Dove la spiegazione dice che un
  numero o un testo è **scelto e non misurato**, resta una riga breve visibile
  («Testi scelti, non ancora confrontati.», «Scelte nostre, non misurate.»).
- Errori, rifiuti e stati vuoti non cambiano: si spiegano da soli.

**Video**
- Ogni posto si riempie con **Dai render** (la griglia dei render fatti, di
  tutte le viste) o **Da file…**.
- Nuovo modo **Inizio, intermezzo, fine** (3 render). Seedance 2.5 non ha un
  fotogramma di mezzo: partono due video primo-ultimo (inizio→intermezzo,
  intermezzo→fine) con la durata scelta ciascuno. Nell'elenco sono una voce
  sola con un lettore che suona i due tratti di fila; nella cartella sono due
  file, e lo si dice.
- Durate: 5, 10, 15, 20, 30 secondi (Seedance arriva a 30).

## Una barra sola sotto ogni immagine, costruita il 2026-11-04

Richiesta di Riccardo del 2026-11-04: «partendo da un render che va bene, non è
chiaro come posso fare una variante modificando solo le luci, ad esempio un
interno notturno... Se devo passare da ritocca non ha senso xche devo
selezionare il tutto. Rifai pulito, ritocca da qui, non si capisce.» Scelta
sua: una barra sola, uguale in Risultato e in Passi.

**La barra:** **Cambia · Ritocca · Variante · Video · Altra vista**
(dal 2026-11-09 **Altra vista** si chiama **Ricetta**, vedi «Ricetta su altre
viste»).
- **Cambia** (nuovo, primo): cambia tutta l'immagine a parole, senza
  disegnare aree. Apre un riquadro sotto la barra: «Cambia tutta l'immagine, a
  parole», il campo per la richiesta e le scorciatoie **Notte · Tramonto ·
  Nuvoloso · Pioggia · Neve · Luci accese**, che scrivono una frase nel campo
  (si può correggere). Sotto: «Scorciatoie: testi scelti, non provati.» e
  «Per cambiare solo una parte usa Ritocca.» Poi destinazione, costo e
  **Applica**. Il risultato è un passo nuovo sotto l'immagine di partenza.
- La regola del passo (blocchi bozza 12) non chiede più di tenere la luce
  quando la richiesta parla di luce, ora del giorno o tempo atmosferico.
- **Ritocca**, **Variante**, **Video**, **Altra vista** come sopra.

**Passi, colonna destra:** al posto di «Adesso» la stessa barra, con i suoi
riquadri. Tolti **Nuovo passo da qui**, **Rifai questo passo** e **Ritocca da
qui** (facevano quello che fanno Cambia, Variante e Ritocca). Su ogni riga
dell'albero il collegamento è **Cambia** (sulla riga 0, la vista, **Genera**).
**Rifai pulito dalla vista** si chiama **Rifai tutto dalla vista** e compare
solo quando serve: dalla seconda generazione di fila, o quando il punto di
partenza non c'è più. Resta **Apri cartella**.

- **Vuoto / in corso / errore:** come prima; un passo non riuscito non ha la
  barra (non c'è un'immagine da cui partire).

**Suggerimenti e parole, stesso giorno (richiesta di Riccardo).**
- Ogni pulsante d'azione ha una frase al passaggio del mouse che dice cosa fa.
  Le frasi stanno in un elenco solo (`SPIEGA_PULSANTI` in `studio.js`), così
  la stessa azione si spiega sempre allo stesso modo. Le scelte (preset,
  luce, cielo…) non ne hanno: il nome basta, e dove serve c'è già il «?».
- Stesse parole per le stesse cose: «Chiudi» per i riquadri (era «Lascia
  stare»), «Apri cartella» ovunque, «Applica» senza «· un invio», un passo da
  Cambia si chiama «Cambia» nello storico e «Cambia: …» nell'elenco dei
  render (era «Modifica» e «Passo: …»), un ritocco «Ritocco: …» (prima
  risultava «Scelte libere»), un render da Rifai tutto «Tutto dalla vista · …».
- Tolte le frasi che ripetevano quello che si vede già (sotto «Parti da un
  preset», sotto Applica in Ritocca, il secondo «il primo video è la prova»).


## Ricetta su altre viste, costruita il 2026-11-09

PR 4 del piano dei flussi (pagina «Ricette e confronto», prototipo «Ricetta»).
Il pulsante **Altra vista** della barra diventa **Ricetta**: stesso posto,
stessa barra in Risultato e in Passi. Assorbe «Altra vista su più viste».

**Il riquadro Ricetta** (si apre sotto la barra, come Video):
- «Ricetta di questa immagine»: i passi numerati in italiano, quelli che
  portano qualcosa a parole: «Genera · Rivista d'architettura», «Cambia · Ora
  blu», «Popola · persone, poche, in movimento», «Ritocco · 2 note · …». Finale
  e i passi senza richiesta non si elencano: sull'altra vista non cambiano
  niente.
- Sotto: «Modello …. I pennelli e le aree dei ritocchi non si portano: sono
  disegnati su questa inquadratura, passano a parole.»
- Nome (proposto dagli ultimi due passi) e **Salva ricetta**: «Salvata «…».
  La ritrovi in Genera › Le mie ricette.» Un nome già usato chiede se
  sostituire.
- «Rifalla su»: una spunta per ogni altra vista della cartella, la prima già
  spuntata. Dove va e costo per il numero di viste spuntate («circa 34 crediti
  per 2 immagini (2 × 17,17) · … · un render per vista»). **Rifai su 1 vista** /
  **Rifai su N viste**. Spento con la ragione accanto: nessuna vista spuntata,
  oltre `RICETTA_VISTE_MASSIME` (6, scelta), un lavoro in corso, modello che
  non accetta la seconda immagine.

**Quattro stati del riquadro**
- *Vuoto* (nessun'altra vista): i passi e Salva ricetta restano; al posto
  delle spunte «Non c'è un'altra vista. In Allplan inquadra un altro punto di
  vista e cattura dalla palette: comparirà qui. Intanto puoi salvare la
  ricetta.»
- *In corso*: «Leggo i passi di questa immagine…»; dopo l'invio «In coda su
  N viste: …. Le trovi nello storico a sinistra, ognuna sotto la sua vista.
  Aprila: il prima/dopo la confronta con la sua vista Allplan.»
- *Errore*: il rifiuto del motore, che si spiega da solo. Se una vista non va
  (stessa vista → «qui serve Variante», vista sparita, vista non adatta,
  destinazione cambiata) **non parte niente**, nemmeno sulle altre.
- *Pieno*: il riquadro descritto sopra.

**Genera · Le mie ricette** (pannello «Modello e qualità», sotto I miei
preset, non in Fotoinserimento):
- Vuoto: «Nessuna ricetta salvata. Sotto un render riuscito apri Ricetta e
  premi Salva ricetta: qui la rifai sulle viste che catturi dopo.»
- Pieno: menu delle ricette, **Elimina**, i passi, «Viene da un render di
  <vista>, che parte come seconda immagine. Stile e modello (…) sono i suoi: le
  scelte di questa pagina non contano.», dove va e costo, **Rifalla su questa
  vista**. Spento sulla vista da cui viene («qui serve Variante») o con un
  lavoro in corso.
- Errore: una ricetta il cui render è stato tolto resta nel menu come «(non si
  usa più)» con i passi salvati e il perché; il file che non si legge si mette
  da parte come per I miei preset.

**Il prima/dopo resta.** Il risultato di una ricetta è un passo 1 della vista
nuova: si apre in Risultato e in Passi con il confronto di sempre (Prima /
dopo predefinito, Affiancati, Solo render) contro la sua vista Allplan.
Screenshot (provider finto) in `docs/ui/studio-ricetta/`.

## Cambia con le miniature e Popola, costruiti il 2026-11-09

Dal piano dei flussi approvato da Riccardo (PR 3; Design canvas, schermate A3 e
A4; testi nella scheda «Preset nuovi» della pagina Flussi). Studio e web app,
stessa pagina. Schermate in `docs/ui/studio-cambia/`.

**Cambia** (barra sotto l'immagine): le sei scorciatoie a parole diventano
miniature disegnate in due righe, **Ora del giorno** (Alba, Mattino,
Mezzogiorno, Tramonto, Ora blu, Notte) e **Tempo e mood** (Nuvoloso, Pioggia,
Neve, Nebbia, Drammatico, Nordico, Luci accese). Negli interni restano solo
quelle che hanno senso (niente neve, pioggia, nebbia, drammatico); per un pezzo
d'arredo non ci sono miniature e resta il campo a parole. Se ne scelgono fino a
`CAMBIA_SCELTE_MASSIME` (6, scelta); ognuna è un passo e un invio. Sotto:
«Miniature disegnate, non render: dicono l'idea.» Il campo libero resta: da
solo fa un passo come prima, con delle miniature si aggiunge a ognuna. Con più
scelte la riga sotto la destinazione dice «Partono N invii, uno per scelta.
Costo: …» e il bottone è **Applica N**.

**Griglia** (Passi): quando un passo ha fratelli (passi nati dallo stesso
render) il confronto ha una terza voce, **Griglia (N)**: la partenza
tratteggiata e tutti i fratelli affiancati; quelli non ancora finiti mostrano
lo stato su sfondo a righe. Un clic sceglie il passo e apre subito il suo
**Prima / dopo** contro il render di partenza (il confronto A/B resta sempre, è
una regola di Riccardo del 2026-11-09); gli altri restano nell'albero. Dopo Applica con più scelte lo Studio va in Passi
con la griglia aperta. I nomi nell'albero sono «Cambia · Ora blu» (più il testo
libero, se c'è).

**Popola** (barra, dopo Ritocca): Cosa (Persone, Alberi, Auto; negli interni
solo Persone, per un arredo niente), Quante (Poche, Alcune, Molte), Come (Ferme,
In movimento; non per gli alberi), Dove:
- **Dipingo io** (predefinito): il bottone «Dipingi dove, nel Ritocca» apre il
  Ritocca col pennello verde e gli altri strumenti spenti. Al posto della frase
  con le @: «Popola · Persone, alcune, ferme» con **Esci da Popola**. Ogni
  tratto prende la stessa frase, che l'elenco delle aree mostra. Applica dice
  «Applica Popola · N tratti». Fuori dal verde resta il render di prima.
- **Decide il modello**: un passo a parole su tutta l'immagine; il pannello
  dice dove le mette («sui percorsi, sulle terrazze e vicino agli ingressi, mai
  davanti alla facciata principale») e che ridisegna tutta l'immagine.
Sempre: «La grandezza delle persone si lega a porte e piani: è il punto dove il
modello sbaglia di più. Testi scelti, non ancora provati.»

Quattro stati. **Vuoto**: nessuna miniatura e nessun testo, Applica grigio con
il perché; Popola dipingo senza tratti: «Passa il pennello verde dove le vuoi».
**In corso**: i passi in coda si seguono uno dopo l'altro, nella griglia le
celle mostrano lo stato. **Errore**: messaggio del motore sopra Applica; scelte e
tratti restano; miniature doppie, sconosciute o troppe non mandano niente.
**Pieno**: i passi nuovi nell'albero e nella griglia.

## Studio · Da un'immagine, costruita il 2026-11-09

Dal piano dei flussi approvato da Riccardo (PR 5, partenza «Un'immagine»;
Design canvas, schermata B-Immagine). Studio e web app, stessa pagina.
Schermate in `docs/ui/studio-immagine/`.

**Ingresso** (Genera, riquadro della vista): accanto a «Usa un'altra vista…»
c'è **Da un'immagine…**; a vista vuota è il bottone principale. Apre un
pannello con tre scelte: **Un render già fatto**, **Una foto**, **Uno schizzo o
un plastico**. Per la foto si sceglie anche cosa farne (**Cambia il look**,
**Cambia arredi o materiali**, **Metti il progetto qui**) e, per le prime due,
**Che cosa si vede?** (Un esterno / Un interno). Poi «Scegli l'immagine…».

Dove porta:
- **Render già fatto**: niente Genera. L'immagine diventa subito un risultato
  («Caricata 1» nello storico) e da lì partono Cambia, Ritocca, Popola, Video e
  Finale, con la stessa barra. Non parte niente e non costa niente: il riquadro
  «Com'è stato fatto» dice «Nessun invio», la tenuta dice «Non misurata» col
  perché. Variante e Altra vista non ci sono (serve una vista di Allplan).
- **Foto, Cambia il look**: Genera, con **Cosa tenere** sotto la vista: «Muri e
  finestre» (predefinito) o «Anche gli arredi». Preset, look, riferimento di
  stile come per una vista. La foto è anche subito un risultato, come il render.
- **Foto, Cambia arredi o materiali**: Ritocca sulla foto, coi riquadri e le
  foto di riferimento che ci sono già.
- **Foto, Metti il progetto qui**: Fotoinserimento, con la foto come luogo.
- **Schizzo o plastico**: Genera come una vista, Cosa tenere = «Le linee dello
  schizzo». Arredo (prodotto) è spento per tutte le immagini caricate.

Su un'immagine caricata il controllo di idoneità guarda solo la misura (lato
minimo): ombre, toni e sfondo uniforme valgono per le viste di Allplan. La riga
sotto la vista dice il tipo («Foto», «Schizzo o plastico», «Render già fatto»).

**Punti** (Materiali della vista, fuori da Allplan): «+ Punti» accanto a «+
Contorno». Ogni clic sulla vista è un quadratino campione (`PUNTO_LATO`, 5% del
lato, scelta) e una riga «Materiale N · dalla vista» con «diventa…» e «+
Riferimento». «Fine selezione» chiude.

**Prima / dopo**: resta il confronto predefinito in Risultato e in Passi. Per
l'immagine caricata la partenza si chiama «Immagine caricata» (o «Foto di
partenza», «Schizzo di partenza») e una riga sopra il cursore dice che prima e
dopo sono uguali finché non parte il primo Cambia, Ritocca o Popola.

Quattro stati. **Vuoto**: pannello chiuso; aperto senza tipo, «Scegli
l'immagine…» grigio. **In corso**: «Carico…» sul bottone. **Errore**: messaggio
del motore nel pannello (immagine troppo piccola, formato, tipo sconosciuto);
niente viene salvato. **Pieno**: la vista caricata in Genera, o il risultato in
Risultato, o il Ritocca aperto, secondo la scelta.

## Pianta, planimetria e planivolumetrico, costruiti il 2026-11-09

Dal piano dei flussi approvato da Riccardo (PR 6; Design canvas, schermata
C-Pianta; testi nella scheda «Preset nuovi» della pagina Flussi). Studio e web
app, stessa pagina. Schermate in `docs/ui/studio-pianta/`.

**Genera**: la scena **Pianta** si aggiunge a Esterno, Interno e Arredo. Nove
preset (pianta resa materica, in assonometria, colorata da concorso, bianco e
nero; planimetria illustrata, da drone, ad acquerello; planivolumetrico plastico
bianco e materico). Nei dettagli: **1 · Che disegno è** (Pianta dell'edificio,
Planimetria, Planivolumetrico), **2 · Stile della tavola**, **3 · Luce e
ombre**. Il giudizio della vista per una pianta non chiede ombre né toni di
grigio: «Pianta adatta · linee e colori piatti vanno bene». «Tieni la
geometria» si chiama «Tieni la geometria · muri e aperture». Accanto a «Pianta
adatta» c'è **Punto di vista**, per una pianta già fatta.

**Barra sotto un render di pianta**: al posto di Popola ci sono **Arreda** e
**Punto di vista**. Il resto (Cambia, Ritocca, Variante, Video, Altra vista,
Finale) resta com'è.
- **Arreda** apre il Ritocca in modo Arreda: solo Rettangolo e Selezione libera,
  lo stile in alto (scelte di `STILI_ARREDA`) con **Esci da Arreda**, e per ogni
  zona a destra «Stanza» (soggiorno, cucina, camera, bagno, studio, ingresso…).
  Applica dice «Arreda · N zone». Fuori dalle zone resta la pianta di prima.
- **Punto di vista**: la pianta grande; si clicca dove si sta e si trascina
  verso dove si guarda, e compaiono il punto e il cono rossi, gli stessi che il
  motore disegna sulla seconda immagine che parte. Sotto: Dove (Dentro la casa,
  Fuori nel lotto), Luce (Giorno, Pomeriggio caldo, Sera), Camera (**Senza
  Allplan** scelta; **In Allplan** spenta con «In arrivo»: aspetta la sonda di
  PythonParts). Sempre, prima di Rendi: «Stanza immaginata dalla pianta. Altezze
  (occhi a 1,6 m, soffitto a 2,7 m, scelte), arredi e finestre che la pianta non
  disegna li ha immaginati il modello.» Il modello deve ricevere più immagini.

**Prima/dopo (A/B)**: resta il confronto predefinito in Risultato, Passi e
Ritocca, anche per Arreda e per il punto di vista. Sopra il render di un punto
di vista il titolo è «La foto dal punto di vista» con lo stesso avviso «Stanza
immaginata dalla pianta», anche in Passi.

Quattro stati. **Vuoto**: in Punto di vista, «Clicca sulla pianta dove stai»
accanto a Rendi grigio; trascinamento troppo corto, «Trascina un po' più in
là»; in Arreda senza zone, «Disegna un rettangolo su ogni stanza da arredare».
**In corso**: il lavoro si segue come gli altri passi. **Errore**: il messaggio
del motore sopra Rendi o Applica; punto, zone e stanze restano. **Pieno**: un
passo nuovo sotto la pianta, col prima/dopo.

## Studio · Licenza e saldo, costruita il 2026-11-05

Bozza A scelta da Riccardo il 2026-11-05 fra due (A scheda intera, B cassetto
dalla testata; bozze in `/mnt/project-files/mockup/licenza-saldo/`). Il
pulsante in alto a destra, prima «Chiave e tetto di spesa · In arrivo», ora è
«Licenza e saldo» (`#licenza`). Accanto, una pastiglia sempre visibile:
«42 render · Pro», «Nessuna licenza», «Saldo non letto» o «Chiave Comfy tua».
Senza codice e senza chiave Comfy sul PC, lo Studio si apre sulla scheda.

| Stato | Cosa si vede |
|---|---|
| Vuoto | «Attiva AIRENDER»: campo del codice, Attiva, il nome del server che lo controlla, «Non hai una licenza? Vedi i piani», il riquadro della chiave Comfy propria |
| In corso | Campo e Attiva spenti, «Chiedo al server AIRENDER (<host>) se il codice è valido.» con la rotella |
| Errore | Codice rifiutato: bordo rosso e la frase del server con Cosa fare; il codice non si salva. Server muto con codice già salvato: «Licenza …WN3B», l'avviso, Riprova, Cambia codice |
| Pieno | Piano, render disponibili (e in corso), scadenza del lotto più vicino, postazioni, licenza; Ricarica e Gestisci abbonamento (link firmati, un'ora); costo di un render per modello dal listino; Cambia codice |

L'errore «Il saldo AIRENDER non basta» in Genera ha accanto Ricarica e «Vedi
il saldo». La scelta crediti AIRENDER o chiave Comfy vale per lo Studio
aperto; senza chiave Comfy sul PC il pulsante non c'è e si spiega dove
metterla.
## Oggetti e persone da inserire, e scelta del modello, costruiti il 2026-11-04

Richieste di Riccardo del 2026-11-04: «vorrei poter inserire ref image di
oggetti da inserire, o persone… sulla vista base o sul render successivo» e
«togli i modelli dalla tendina e raggruppali per categorie e funzioni con un
minimo di spiega sintetica, spunta per quello che selezioni».

**Oggetti e persone da inserire (Rif.).** Fino a 4 foto (`INSERTI_MASSIMO`),
chiamate **Rif. 1 … Rif. 4**, da citare nel testo («metti la poltrona del Rif. 1
accanto alla finestra»).
- **Genera**, colonna destra sotto «Immagine di riferimento per lo stile»: una
  fila di riquadri con la foto, «Rif. N» e × per toglierla, poi «+ Rif. N».
  Non c'è con Fotoinserimento.
- **Cambia**: la stessa fila, sotto «Solo una parte? Usa Ritocca.».
- **Ritocca**: ogni nota (sul foglietto e nell'elenco) ha **+ Immagine**; la
  foto si mostra piccola con «Rif. N · nome» e «Togli». I numeri seguono
  l'ordine delle note che hanno una foto. Sotto l'elenco: «Partono N immagini:
  il render e M Rif. delle note.»
- Il conteggio delle immagini si dice prima dell'invio («Partono 3 immagini:
  … e 2 Rif. di oggetti e persone»). Con un modello che riceve una sola
  immagine i riquadri restano, «+ Rif.» è spento e la frase lo dice; il
  server non manda.
- **Vuoto:** solo «+ Rif. 1». **In corso:** come l'invio di sempre.
  **Errore:** caricamento rifiutato (formato, peso) sotto la fila; una nota
  che cita un Rif. che non c'è si ferma con «La nota N usa il Rif. M, che non
  c'è». **Pieno:** `docs/ui/studio-rif/72-genera-due-rif.png`,
  `73-ritocca-nota-con-rif.png`, `74-cambia-con-rif.png`.

**Scelta del modello.** Al posto della tendina, in Genera, Cambia, Ritocca e
Rifai tutto: chiusa, la scheda del modello scelto (spunta, nome, fornitore,
«predefinito», una riga su a cosa serve, «Più immagini per invio» o «Una sola
immagine per invio», costo) e «Cambia modello (N altri)». Aperta, le schede per
gruppo: **Consigliati**, **Altri modelli**, **Una sola immagine**, con il «?»
che spiega il gruppo (senza scritte «da provare», richiesta di Riccardo del
2026-11-04). Un modello che non può fare l'invio (schema non
verificato, oppure una sola immagine quando ne partono di più) resta visibile,
spento, con il perché sulla scheda. Schermate:
`docs/ui/studio-rif/70-genera-rif-e-modello-chiuso.png`,
`71-scelta-modello-aperta.png`.

## Stile da esempi, costruito il 2026-11-04

Richiesta di Riccardo del 2026-11-04: «copio qualche immagine di altri render,
anche solo 3 o 4, e mi restituisce un preset che renderizza uguale». In Genera,
sotto il riferimento per lo stile caricato: «+ Un altro esempio (Stile da
esempi)». Con due o più immagini il riquadro diventa **Stile da esempi**: una
fila «Esempio 1 … 4» (`ESEMPI_STILE_MASSIMO`, scelta) con × e «+ Esempio N»,
il «?» che dice cosa si prende (colori, luce, materiali, taglio fotografico) e
(la promessa «Crea il mio stile», LoRA, tolta il 2026-11-12: non è costruita). Togliere
l'esempio 1 fa diventare riferimento il 2. Il conteggio «Partono N immagini: la
vista, M esempi di stile…» compare prima dell'invio. Gli esempi entrano nella
ricetta per impronta, come il riferimento. Salvarli come preset è il passo dopo.

## Tieni la geometria, rifatto il 2026-11-11 (mappe sul computer)

Decisione di Riccardo del 2026-11-11, dopo le prove del 2026-11-10
(`docs/prova-nano-mappe-2026-11-10.md`): niente più ControlNet su un deployment
Comfy. In Genera, dopo il riferimento per lo stile e prima dei Rif., la spunta
**Tieni la geometria** con accanto l'etichetta verde **Incluso · nessun
credito in più** (il valore aggiunto, detto in una riga). Sotto, una frase:
«AIRENDER calcola sul tuo computer spigoli e profondità della vista e li dà al
modello come guida: muri, aperture e volumi restano dove li hai disegnati.» col
suo «?» (cosa sono le due mappe, che partono con la vista verso lo stesso
modello, quando aiutano, che vale solo in Genera dalla vista). Nel riquadro
Invio la destinazione resta una: il conteggio dice «Partono 3 immagini: la
vista, più le 2 mappe della vista (spigoli e profondità), calcolate sul tuo
computer.» e una riga «Tieni la geometria: le mappe sono calcolate su questo
computer, partono con la vista verso lo stesso modello: nessun servizio in
più. Costo: **incluso: nessun credito in più**» (con la chiave Comfy propria:
«circa 0,3 crediti Comfy in più per render (misurato una volta, a 1K)»).
Non c'è nel Fotoinserimento, in Cambia e in Ritocca.
- **Vuoto:** la spunta tolta, nessuna riga in più.
- **In corso:** con la spunta accesa, «Sto calcolando spigoli e profondità sul
  tuo computer. La prima volta scarico anche il modello della profondità
  (circa 50 MB, una volta sola).»; Genera resta spento con «Sto calcolando le
  mappe della vista sul tuo computer: Genera si accende appena sono pronte.»
- **Errore:** «Le mappe non si sono calcolate: <motivo>» col gesto (connessione
  per il primo scaricamento, oppure togliere la spunta) e **Riprova**.
- **Pieno:** le due miniature **Spigoli** e **Profondità** e «Pronte in 9,6 s, su
  questo computer.» (`docs/ui/studio-rif/78-tieni-la-geometria-mappe.png`).

Fuori piano (resta solo nel piano Studio, Riccardo 2026-11-11) la spunta è
grigia con «Il piano <nome> non comprende «Tieni la geometria»: è nel piano
Studio.»; senza saldo letto, si rimanda alla scheda Licenza.

Tolti il 2026-11-11 insieme al deployment: i tre controlli (Spigoli,
Profondità, Linee dritte) e **Riaggancia alla vista**. Nello storico i render
fatti prima restano con il loro nome («Riaggancia alla vista», «Tieni: Spigoli
(ControlNet)»).

## Finale, costruito il 2026-11-04

Richiesta di Riccardo del 2026-11-04: «upscale e dettagli». Nella barra sotto
ogni immagine, dopo **Altra vista**: **Finale**. Apre un riquadro «Finale ·
ingrandisci con più dettaglio»: chi lo fa (Magnific Precision V2 di Freepik,
dal Router, senza prompt), **Quanto più grande** ×2 · ×4
(`FINALE_INGRANDIMENTI`, scelta), **Che immagine è** Foto · Illustrazione, la
misura «Da L × A a L×n × A×n pixel», destinazione e costo, **Applica**. Esce
un passo nuovo, «Finale ×2» nello storico e nell'albero.
- **Vuoto:** non c'è: il pulsante c'è solo sotto un'immagine riuscita.
- **In corso:** come gli altri passi. **Errore:** sotto Applica, con il gesto.
- **Pieno:** `docs/ui/studio-rif/75-finale.png`.

## Schermate sostituite il 2026-10-27

Le cinque schermate della palette di prova (Sorgente, Stile, Risultato,
Materiali, Livelli) erano pensate per stare tutte dentro Allplan. Dove
contraddicono le nuove, valgono le nuove:

| Prima | Adesso | Cosa cambia |
|---|---|---|
| 1 — Sorgente | Palette · 1 Vista; Studio · Genera, la vista in testa | La cattura la fa la palette dalla finestra attiva; lo stato vuoto non parla più di cartella sorvegliata |
| 2 — Stile | Palette · 2 Stile; Studio · Genera | Miniature **illustrative** e dichiarate tali, non generate dal preset (vedi Decisioni visive). Niente slider della grana nella scelta dello stile; dal 2026-10-28 neanche nel ritocco (Studio · Ritocca). Il testo libero non è una riga sotto la griglia ma il prompt completo modificabile |
| 3 — Risultato | Studio · Risultato | Prima/dopo con la linea come vista predefinita, affiancati come seconda scelta |
| 4 — Materiali | Studio · Ritocca, in grigio; Materiali a parole in Genera | La direzione del 2026-10-22 (zone dalla mappa di Allplan, unisci e separa) resta, dentro Ritocca |
| 5 — Livelli | Studio · Passi (dal 2026-10-28) | Non più livelli sopra un render ma un albero di passi, ognuno con la sua ricetta; costruito il 2026-10-30 |

## Web app · Accedi, costruita il 2026-11-06

La web app è lo Studio stesso, servito da `airender-server.netlify.app/studio/`
invece che da 127.0.0.1 (decisione di Riccardo, 2026-11-06: «Lo Studio vero nel
browser»). L'unica schermata nuova è l'ingresso, prima dello Studio, con lo
stile dello Studio. Sotto, sempre, lo stato del motore che si prepara nel
browser. Con un codice già salvato in quel browser si entra senza ripetere.

Dal 2026-11-06 sera (PR 2) si entra di solito con un **link via email**: si
scrive l'email, «Mandami il link», e arriva un link per ogni licenza attiva di
quell'email, valido 15 minuti (SCELTA) e una volta sola. Il codice licenza
resta a un clic, «Ho il codice licenza». Il link porta il browser dentro anche
se è aperto in un'altra scheda: la scheda nuova lo passa a quella con lo
Studio e dice di tornarci.

| Stato | Cosa si vede |
|---|---|
| Vuoto | «Accedi ad AIRENDER Studio», la frase su dove restano le immagini e dove va la vista quando si preme Genera, Email, «Mandami il link», «Ho il codice licenza», la frase su come arriva il link, «Vedi i piani» |
| In corso | Pulsante spento, «Chiedo al server AIRENDER (<host>) di mandarti il link.»; poi «Se <email> è l'email di una licenza AIRENDER, ti abbiamo mandato un link per entrare. Vale 15 minuti. Se non arriva, guarda nella posta indesiderata.» (uguale per ogni email: non si scopre chi è cliente). Col link: «Controllo il link con il server AIRENDER…», poi «Licenza trovata. Aspetto che lo Studio sia pronto nel browser…» |
| Errore | Link usato o scaduto: «Questo link di accesso non vale più» e «Chiedine un altro»; col codice: email e codice col bordo rosso e la frase del server, che non dice quale dei due è sbagliato; motore non partito o browser senza JSPI: la ragione e «Apri la web app con Chrome o Edge aggiornati»; seconda scheda: «Lo Studio è già aperto in un'altra scheda» |
| Pieno | Lo Studio, come sul PC |

Nella web app «Apri cartella» risponde che le immagini stanno nel browser;
«Esporta per il cliente» scarica il file. I testi dello Studio che parlano
della palette restano fino alla PR 2.

## Decisioni visive

- **Ribaltata il 2026-10-27:** vista di partenza e render ~~affiancati, non in
  sovrapposizione~~. Adesso la vista predefinita è **prima/dopo con la linea
  da spostare**, e Affiancati resta a un clic. La domanda resta «è ancora il
  mio edificio?», ma nello Studio c'è il mouse sul render: spostando la linea
  sullo stesso spigolo si vede subito se si è mosso, cosa che con due
  immagini piccole affiancate nella palette non si poteva fare.
- **Rimandata il 2026-10-27:** ~~le miniature sono generate, non disegnate~~.
  Per ora le miniature sono illustrazioni, per decisione di Riccardo (niente
  generazioni a pagamento solo per le miniature), e **lo dicono a schermo**. La
  ragione della regola vecchia vale ancora: una miniatura che promette più di
  quello che il preset produce è la prima causa di sfiducia. Per questo
  l'etichetta non si toglie finché non sono render veri.
- Scelta: **Dettagli del preset aperti per default** — il preset è un punto di
  partenza, non una scatola chiusa; si vede subito cosa imposta.
- Scelta: **il prompt vero si mostra**, in inglese, modificabile. Chi vuole
  controllo lo ha; chi non lo vuole legge il riassunto in italiano.
- Scartata: anteprima in tempo reale mentre si scrive il prompt — costa una
  chiamata a ogni tasto e il pubblico paga a consumo.

## Testi asciutti e pop-up «?», 2026-11-12

Richiesta di Riccardo del 2026-11-12: «semplifica o togli notevolmente il
testo inutile, se serve spiega in un pop-up». Regola da qui in poi:

- **A schermo resta solo quello che serve per decidere o per agire**: il nome
  della cosa, la scelta, il servizio dove va l'invio e il costo (regola 5),
  gli errori. Il perché, i dati tecnici e le avvertenze vanno nel «?».
- **Il «?» apre un pop-up vero** (al passaggio del mouse, col Tab o con un
  clic sul touch; Esc lo chiude), non il tooltip lento del browser.
- **La destinazione si scrive sempre allo stesso modo**: «La vista va a
  **Comfy Router → Google** · Nano Banana 2 (?) · **circa 17 crediti per
  immagine** (?)». L'indirizzo esatto e «senza ripiego» nel primo «?», la data
  della misura del costo nel secondo. Vale per Genera, Cambia, Ritocca,
  Finale, Video.
- **Niente pannelli che ripetono**: «Cosa parte, in breve» tolto; «Com'è
  stato fatto» chiuso; «Note del motore» dentro «Com'è stato fatto»; le
  ricette vuote non occupano posto; la scheda del modello chiusa dice nome e
  costo, il «perché» si legge aprendo la lista.
- **Niente promesse di funzioni che non ci sono** (LoRA).
- Il prima/dopo resta com'era, ovunque.

Schermate: `docs/ui/studio-testi/` (prima e dopo, app vera con provider finto).

## Verifiche di accessibilità

- [ ] palette: leggibile in modalità scura e chiara, entrambe ereditate da
      Allplan
- [ ] Studio: leggibile in modalità scura e chiara, seguendo quella di sistema
- [ ] nessuna informazione affidata al solo colore (lo scostamento geometria,
      le funzioni in grigio e l'origine delle zone hanno anche un'etichetta
      testuale)
- [ ] la linea del prima/dopo si sposta anche da tastiera
- [ ] la palette resta usabile a larghezza minima
- [ ] i testi non vengono tagliati quando si allarga il carattere di sistema

## Non ancora progettato

- Tetto di spesa per la chiave Comfy propria (la Licenza e saldo è costruita,
  vedi sopra).
- Il video oltre la scheda Video: montare più video, musica, titoli.
- Cambia un materiale (clic su una superficie con la mappa di Allplan): i suoi
  stati si scrivono quando la mappa esiste.
