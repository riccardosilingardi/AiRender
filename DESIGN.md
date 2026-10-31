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

Mockup: `Palette.dc.html`. Quattro expander in fila, numerati, più uno in
grigio. In fondo il percorso della cartella delle viste e Chiudi.

1. **Vista** — finestra attiva, Cattura vista, dimensione (come la finestra,
   1920×1080, 3840×2160), miniatura, esito dell'idoneità.
2. **Stile** — resa (miniature illustrative, dichiarate tali), ora, cielo,
   intorno, materiali a parole, modello. È la versione corta di Studio ·
   Genera: le stesse scelte, con gli stessi nomi.
3. **Invio** — dove va la vista, costo, Prova a secco, Genera.
4. **Ultimo render** — preset e modello, crediti, **Apri nello Studio**, Apri
   cartella.
5. **In arrivo** (chiuso, in grigio) — Cambia materiale, Annota aree, Livelli,
   Video.

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
- **Resa in una riga, non in griglia.** Nello Studio solo «Fotorealistico» ha
  un blocco di prompt; una griglia di cinque miniature con quattro spente non
  aggiunge niente. La riga lo dice e rimanda allo Studio.
- **Esterno / Interno e il preset in Stile.** Il mockup non li ha; senza, la
  palette non saprebbe da quale combinazione partire. Sono lo switch e i preset
  dello Studio · Genera, con gli stessi nomi; Ora, Cielo e Intorno partono da
  «Come il preset». Cielo e Intorno si vedono solo con Esterno.
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
- Switch **Esterno / Interno**. È l'unico modo di dire cosa c'è nella vista:
  non esiste un campo «Cosa c'è nella vista».
- **Parti da un preset**: 8 preset esterni o 6 interni, secondo lo switch
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
- **Dalla mappa materiali di Allplan** (in grigio, «In arrivo»): una riga per
  materiale con colore nella mappa | materiale Allplan | diventa (a parole) |
  immagine di riferimento facoltativa. Le righe mostrate sono marcate
  «esempio, non calcolato». Serve prima la verifica della vista a colori per
  materiale (PRD, sezione 9).
- **Cosa parte, in breve**: il riassunto delle scelte in italiano.
- **Mostra e modifica il prompt completo**: il testo vero che parte al
  modello, in inglese, modificabile, con il numero di caratteri. Se l'utente
  lo modifica, i comandi a sinistra non lo toccano più finché non preme
  **Ricomponi dalle scelte**. È l'unico posto dove si scrive testo libero per
  il modello.
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
- **Com'è stato fatto** (la ricetta): stile, modello, le parole dell'utente,
  intorno, servizio («Comfy Router, senza ripiego»), costo, seme («salvato, il
  modello non lo usa» quando è così), percorso del render e della ricetta.
- **Adesso**: Rifai con la stessa ricetta, Apri cartella, Copia immagine; in
  grigio Esporta per il cliente.
- **Cambia una parte**: **Annota per aree** apre Ritocca su questo render; in
  grigio Cambia un materiale e Fai un video da qui.

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
- **Un solo Applica per tutte le note**: «Applica le 2 note · un invio», con
  la destinazione e il costo di **un** invio (regola 5).
- Il risultato è **un passo nuovo nell'albero** (Studio · Passi), figlio del
  render su cui si sono disegnate le aree.
- **Da verificare prima**, scritto a schermo finché vale: se il modello
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

## Studio v1, costruito il 2026-10-28

Codice in `core/studio/`, screenshot di ogni stato (anche a 1280×800) in
`docs/ui/studio-v1/`: lì i «render» sono la vista colorata da un provider
finto, non render veri. Dove lo Studio v1 si scosta dal mockup, e perché:

- **In testa non c'è «Collegato ad Allplan 2026 · BOSCO · …».** Lo Studio non
  parla con Allplan: mostra se la coda dei lavori gira, la cartella delle
  viste e, se la palette l'ha salvata, la camera (Prospettiva centrale o
  Vista parallela). Dire «collegato» sarebbe un'informazione che non abbiamo.
- **Resa**: solo Fotorealistico è attiva. Plastico bianco, Schizzo a matita,
  Acquerello e Cinematografico sono in grigio: non hanno ancora un blocco di
  prompt, e un comando che non cambia il prompt mentirebbe.
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
- **Rifai con la stessa ricetta** chiede conferma, con destinazione e costo,
  prima di rimettere il lavoro in coda: è un invio che si paga (regola 5).
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
  «Pulito dalla vista · <preset>». È spento su un passo partito dalla vista:
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

- Schermata di configurazione della chiave API e del tetto di spesa (nello
  Studio c'è solo il segnaposto in grigio).
- Esportazione finale (formati, risoluzione, dove salva).
- Qualunque cosa riguardi il video.
- Cambia un materiale (clic su una superficie con la mappa di Allplan): i suoi
  stati si scrivono quando la mappa esiste.
