# AIRENDER — Product Requirements

Documento vivo. Descrive quello che è vero **adesso**, non quello che è previsto.
Ogni sessione lo aggiorna. Ultimo aggiornamento: 2026-10-27

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

Riscritto il 2026-10-28 con lo Studio v1 (sezione 5, riga del 2026-10-27).

1. In Allplan cattura la vista dalla palette (o la salva con **Salva contenuto
   finestra come immagine**) nella cartella delle viste. Vista shaded, ombre
   attive, sfondo neutro.
2. Apre lo **Studio**, la pagina locale nella sua finestra: la vista più
   recente della cartella è già lì, con il suo esito di idoneità.
3. Sceglie esterno o interno e un preset. Le miniature sono **illustrazioni**, e
   lo dicono: non sono render del preset (DESIGN.md, Decisioni visive). I
   dettagli del preset (look, luce, cielo, intorno, persone) si cambiano uno
   per uno.
4. Se vuole, scrive i materiali a parole ("intonaco a calce bianco, infissi in
   rovere scuro"), che passano al modello come sono; chi vuole controllo
   modifica il prompt inglese completo.
5. Legge dove va la vista e quanto costa, poi Genera: il lavoro va in coda e
   Allplan resta libero. **Qui avviene la decisione**: davanti ha la vista di
   partenza e il render, prima/dopo con la linea da spostare, e la tenuta
   della geometria, scritta «Non misurata» finché non c'è la misura.
6. Se una superficie non gli piace: la clicca o la nomina a parole, sceglie un
   altro materiale o lo scrive, regola la grana. Il resto dell'immagine non si
   tocca.
7. Il risultato salvato non è un PNG ma una **pila di livelli** rieseguibile.

## 5 · Decisioni, con le ragioni

| Data | Decisione | Perché | Ribaltata? |
|---|---|---|---|
| 2026-09-14 | Una sola immagine in ingresso: la vista shaded | Profondità e spigoli si stimano dall'immagine. Chiedere più passate all'utente uccide l'adozione | |
| 2026-09-14 | Niente ID map esportata da Allplan in v1 | Sovra-ingegneria: la segmentazione a valle sul render dà una UX migliore e non richiede nulla all'utente | **Sì, 2026-10-22.** La mappa la cattura la palette da sola, quindi all'utente non chiede niente: vedi la riga del 2026-10-22 |
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
| 2026-10-22 | **La mappa dei materiali viene da Allplan** quando il modello ha il materiale; la segmentazione sul render resta solo per quello che Allplan non sa | Decisione di Riccardo: usare al meglio quello che Allplan sa già. Una zona presa dal modello è esatta e porta il nome vero del materiale, senza correzioni. La ragione del taglio del 2026-09-14 (chiedere all'utente un secondo export) non vale più: `SaveWindowToImageFile` cattura la finestra da script, verificato il 2026-10-21 | |
| 2026-10-27 | Modello predefinito dei preset su Comfy Router: **Nano Banana 2** (`vertexai/gemini-3.1-flash-image`), al posto di FLUX.1 Kontext Pro | Decisione di Riccardo, a occhio, sulla stessa cattura vera passata dai due modelli: i tramezzi tengono in tutti e due, Nano Banana rende meglio ombre e grana. Tiene anche le proporzioni della vista (1376x768 per 1536x857), Kontext no (1392x752). Un'immagine sola: va ripetuto su altre viste. Preset alla versione 3 | |
| 2026-10-27 | **Due superfici: la palette fa da telecomando, lo Studio è una finestra propria.** La palette PythonParts dentro Allplan ha quattro sezioni: 1 Vista (cattura e idoneità), 2 Stile (preset, materiali a parole, modello), 3 Invio (destinazione e costo prima di Genera), 4 Ultimo render (Apri nello Studio), più «In arrivo» in grigio. Lo Studio è una pagina locale servita dal motore (`http.server` della libreria standard, solo `127.0.0.1`) e aperta con `msedge --app=`, in un processo separato. Palette e Studio si parlano con la cartella delle viste e una coda di lavori su file | Decisione di Riccardo, che trova la palette di prova pessima da usare. Tre ragioni: **spazio per il confronto** (prima/dopo con la linea, A/B fra modelli: nella palette stretta non ci sta); **il mouse sul render** (cliccare una superficie, disegnare un riquadro: la palette non ha un'immagine cliccabile); **Allplan libero durante la generazione** (oggi la palette chiama il motore dentro Allplan e Allplan resta bloccato fino al render). Costa un processo in più da lanciare e da chiudere, e uno stato in più da tenere coerente fra palette, coda e Studio. Ribalta la riga di sezione 11 che scartava un'applicazione web separata: la ragione di allora (caricare e scaricare file a mano) non vale, perché lo Studio legge la stessa cartella in cui la palette salva. Stati e testi in `DESIGN.md`, mockup in `docs/ui/mockup/` | |
| 2026-10-27 | **Stile = preset curati + blocchi di prompt.** In alto 8 preset esterni e 6 interni; ogni preset compone blocchi di un asse solo, in ordine fisso: regola fissa → scena → materiali → look → luce → cielo (esterni) oppure fuori dalle finestre + arredo (interni) → intorno → persone → qualità → cosa evitare. Il prompt completo, in inglese, si vede e si modifica | Decisione di Riccardo (ibrido, fra solo preset e solo blocchi). Un blocco che tocca un asse solo si cambia senza disfare gli altri. I testi sono riscritti dalla prompt library di Riccardo, non copiati: `docs/ui/blocchi-stile-bozza.md`, bozza 3. **Nessun blocco è stato provato con il modello** | |
| 2026-10-27 | Miniature dei preset **illustrative, dichiarate tali a schermo**, al posto di quelle generate | Decisione di Riccardo: niente generazioni a pagamento solo per le miniature, per ora. Si sostituiscono con render veri dei preset. Finché sono illustrazioni, l'etichetta resta (`DESIGN.md`, Decisioni visive) | |
| 2026-10-28 | **Si lavora per passi, in un albero in una colonna.** Ogni render è un passo; 0 è la vista Allplan, ogni passo parte da quello sopra ed è rientrato sotto di lui, un passo fatto da un punto qualsiasi apre un ramo lì sotto. Niente grafo a nodi, niente schede di versione. La geometria si misura sempre contro la vista Allplan; dalla seconda generazione di fila un avviso; «Rifai pulito dalla vista» unisce le richieste della strada in un invio solo. Nella barra dello Studio «Livelli» diventa «Passi». Schermata Studio · Passi in `DESIGN.md`, mockup `Passi.dc.html` | Decisione di Riccardo: si fa un render, poi si aggiungono alberi, poi persone, e ogni giro deve restare ritrovabile. Un grafo a nodi alla Comfy o Weavy dopo dieci passi diventa un groviglio; con le schede di versione un ramo sparisce. Ogni generazione su un render può spostare un poco gli spigoli: per questo la misura sta contro la vista e c'è il rifai pulito. Quanto si spostino lo misura il piano «catena» del banco di prova | |
| 2026-10-28 | **Ritocca: rettangolo e selezione libera, con note adesive sull'immagine.** Strumenti Rettangolo e Selezione libera (lazo come in Photoshop); «Clicca una superficie» in grigio fino alla mappa materiali; a ogni area una nota numerata sull'immagine, le note anche in elenco a destra; un solo Applica per tutte, con costo e destinazione; il risultato è un passo nuovo nell'albero. Tolta la «Grana del nuovo materiale» | Decisione di Riccardo: le aree reali non sono rettangoli, e la modifica si scrive dove la si vede. Un invio per tutte le note costa meno di uno per area. Prima di costruirla va misurato se Nano Banana 2 rispetta aree e note, e in quale dei due modi (contorni disegnati o maschera): piano «aree» del banco. Vale la trappola del riempimento con maschera di `CLAUDE.md` | |
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
| Mappa dei materiali da Allplan | Per ogni zona della vista, quale materiale del modello c'è, col suo nome | **Mai provata.** Esatta, se Allplan sa produrla con la stessa camera (sezione 9). Non copre le superfici senza materiale |
| Segmentazione | Maschera della regione cliccata o nominata | Segue l'apparenza, non il modello |

**L'anello debole:** la segmentazione. Due materiali resi simili finiscono in una
regione sola; una facciata metà in ombra si spezza in due. L'interfaccia deve
prevedere aggiungi area / togli area fin dal primo giorno, perché il primo clic
non sarà mai perfetto. Con la mappa dei materiali da Allplan l'anello debole
resta solo dove il modello non ha il materiale.

## 7 · Costruito e funzionante

Il motore e lo Studio. Girano da riga di comando su qualunque macchina,
senza Allplan. `pytest`: **522 test verdi**, nessuna chiamata di rete, nessuna
chiave necessaria per farli girare.

```bash
python -m core.cli --image vista.png --preset base --testo "più caldo" --prova-a-secco
python scripts/sonda_comfy.py --solo-schema          # gratis: schema vero del modello
python scripts/sonda_comfy.py                        # una generazione vera, tutto stampato
python scripts/confronta_modelli.py --immagine vista.png
python -m core.coda --cartella C:\AIRENDER --aggiungi vista.png --stile ora-blu   # mette un lavoro in coda
python -m core.coda --cartella C:\AIRENDER                                       # il processo che lo fa
python -m core.studio --cartella C:\AIRENDER                                     # lo Studio: server, coda e finestra
python scripts/prova_blocchi.py --immagine vista.png --piano qualita --prova-a-secco # il banco di prova dei blocchi
python scripts/miniatura_da_banco.py --render <cartella del banco>\ora-blu.png      # un render del banco diventa miniatura
```

| Cosa | Dove | Stato |
|---|---|---|
| Riga di comando: vista + preset + testo → render, ricetta rieseguibile a fianco | `core/cli.py` | Funziona fino al render salvato: primo invio vero il 2026-10-27 sul PC di Riccardo (Nano Banana 2, 17,17 crediti, ricetta completa accanto al render). Durante l'attesa stampa una riga, per non sembrare bloccata |
| Coda dei lavori su cartella: il motore come processo a parte. Un lavoro è un JSON in `lavori/in-attesa`; il processo lo sposta in `in-corso`, poi in `fatto` (render e ricetta accanto), `errore` o `annullato`. Stato leggibile sempre in `lavori/stato/<id>.json` (in coda, inviato, in lavorazione, fatto, errore, annullato). Scrittura atomica, file `<id>.annulla` per fermare, recupero al riavvio dei lavori abbandonati. La destinazione si scrive nel lavoro quando nasce, e se al momento dell'invio non è più quella non parte niente | `core/coda.py` | Provata con `pytest` e con un giro vero da riga di comando senza chiave (si ferma con il messaggio della chiave mancante, senza scrivere «inviato»). **Mai girata con un invio vero**, mai su Windows. La usa lo Studio v1; la palette non ancora |
| Prompt a blocchi: regola fissa → scena → materiali → look → luce → cielo oppure fuori + arredo → intorno → verde → persone → qualità → cosa evitare; 14 preset (8 esterni, 6 interni). Dalla bozza 4 (2026-10-29): intorno città / periferia / campagna, verde nessuno / poco / rigoglioso, persone «poche»; ogni blocco che aggiunge qualcosa finisce con «do not cover or hide any building element». Il prompt di un passo su un render (solo gli assi che cambiano, oppure dalla bozza 5 la regola dei passi e le richieste a parole) e quello delle aree con note | `core/blocchi.py` | Testi identici alla bozza 5 (`docs/ui/blocchi-stile-bozza.md`), controllato da un test che legge la bozza; l'esempio completo e le 14 lunghezze misurate nella bozza tornano al carattere. Tutti i blocchi sono **SCELTI**: nessuno è stato mandato a un modello |
| Varianti per invio, da 1 a 4: N lavori in coda con le stesse scelte, costo scritto come N volte uno («circa 69 crediti per 4 immagini»), «non misurato» se il costo del modello non lo è | `core/studio/servizio.py`, `studio.js` | Provato con `pytest` e a schermo con Playwright su un provider finto. Mai con un invio vero |
| Banco di prova dei blocchi: piani qualità (2 invii), look (9), preset (8 o 6), catena (4), aree (2). Prima di partire dice quanti invii, dove, quanto, e chiede conferma; a secco prepara tutto senza mandare. Scrive `banco.json`, una pagina con le coppie affiancate, i prompt, le misure («non misurato» dove mancano) e i giudizi in `giudizi.json`. Misure: spigoli della vista ritrovati nel render (grezza, soglie SCELTE) e differenza fuori dalle aree | `core/banco.py`, `scripts/prova_blocchi.py`, `core/immagine.py` | Provato con `pytest` su un provider finto e immagini sintetiche, e a secco sulla vista dei test. **Mai lanciato davvero**: nessun piano ha ancora mandato un'immagine (sezione 9) |
| Miniature vere dei preset: un render del piano «preset» del banco, ritagliato a 16:9, diventa la miniatura del suo preset; nello Studio «render vero del <data>» sotto la tessera | `scripts/miniatura_da_banco.py`, `core/studio/miniature.py` | Provato con `pytest`. Nessuna miniatura vera nel repository: oggi sono tutte illustrazioni |
| Studio v1: `python -m core.studio` avvia il server locale (`http.server`, solo `127.0.0.1`, porta scelta dal sistema), la coda come processo figlio e la pagina (Edge `--app=` se c'è). Genera e Risultato come in `DESIGN.md`, Ritocca in grigio. Rotte JSON per viste, preset, composizione del prompt, destinazione e costo, prova a secco, invio, stato, render, ricetta, annulla, rifai. Niente CDN né font scaricati | `core/studio/` | Provato con `pytest` (rotte, prompt, stati, difese del server) e con Playwright su un provider finto: screenshot di ogni stato in `docs/ui/studio-v1/`. **Mai aperto su Windows né con Edge, mai con un invio vero** (sezione 9) |
| Studio · Passi: l'albero dei passi di una vista (0 è la vista Allplan, ogni passo figlio di quello da cui parte, rami), salvato in `<vista>.passi.json` accanto alla vista con la ricetta completa di ogni passo; i render già fatti diventano figli della vista. Un lavoro della coda (formato 2) può partire dal render di un passo con una richiesta a parole. Nello Studio: albero in una colonna, prima/dopo contro la vista o il passo prima, strada, ricetta, Nuovo passo da qui, Rifai questo passo, Rifai pulito dalla vista (le richieste della strada in un invio dalla vista, con il prompt mostrato prima), avviso dalla 2ª generazione di fila, tenuta «Non misurata» | `core/passi.py`, `core/coda.py`, `core/studio/` | Provato con `pytest` (rami, strada, figli, migrazione, unione delle richieste, lavoro da un passo, rotte) e con Playwright su un provider finto: screenshot in `docs/ui/studio-passi/`. **Mai con un invio vero, mai su Windows né con Edge**; nessun passo su un render è mai stato mandato a un modello (sezione 9) |
| Studio · Ritocca: aree a rettangolo o a selezione libera (lazo) sul render di un passo, una nota adesiva numerata per area (spostabile), le note anche in elenco, un solo Applica con destinazione e costo di un invio; il risultato è un passo figlio del render ritoccato, con la misura «fuori dalle aree» accanto. Le aree partono come contorni disegnati o come maschera in più (`RITOCCO_MODO_AREE`, SCELTA sui contorni). Lavoro della coda del formato 3 (solo per i ritocchi: gli altri restano nel 2), misura scritta nello stato del lavoro. «Clicca una superficie» in grigio | `core/aree.py`, `core/coda.py`, `core/passi.py`, `core/studio/` | Provato con `pytest` (i due modi, prompt, misura, formato 3, passo nell'albero, note vuote, rifai, rifai pulito, rotte) e con Playwright su un provider finto, disegnando con il mouse: screenshot in `docs/ui/studio-ritocca/`. **Mai con un invio vero**: il piano «aree» del banco non è ancora stato lanciato (sezione 9) |
| Casa unica delle decisioni: 41 costanti, ognuna con la ragione e l'etichetta MISURATA / SCELTA / VINCOLO | `core/config.py` | Fatta. Un test impedisce di cablare numeri altrove, e un altro che una costante resti senza il suo caso |
| Strato provider sostituibile: genera, modifica una regione con maschera, riesegue a parametri identici; ogni provider dice dove manda la vista e se ha una forza della struttura | `core/provider/` | Interfaccia + due provider. **Comfy Router**, predefinito: protocollo della coda (confermato dalla sonda il 2026-10-27), idempotenza, errori, crediti scalati nella ricetta; schemi verificati per FLUX.1 Kontext Pro e Nano Banana 2, ogni altro modello si ferma prima di partire. **Magnific**: registrato, non più a consumo |
| Sonda di Comfy Router: schema del modello (gratis), una generazione, risposte stampate senza chiave | `scripts/sonda_comfy.py` | Lanciata davvero sul PC di Riccardo il 2026-10-27: schema e una generazione per FLUX.1 Kontext Pro e per Nano Banana 2 |
| Confronto affiancato: la stessa vista attraverso due modelli, con la vista di partenza, per giudicare gli spigoli a occhio | `scripts/confronta_modelli.py` | Scritto e provato senza rete. I due modelli predefiniti hanno lo schema dal 2026-10-27: non è ancora stato lanciato davvero (il primo confronto è stato fatto a mano, con le immagini della sonda) |
| Rifiuto: vista inadatta (wireframe, senza ombre, troppo piccola), con il messaggio che dice cosa risalvare | `core/idoneita.py` | Funziona su immagini sintetiche e su **un** export vero di Allplan 2026, che passa (sezione 9). Un wireframe sintetico sul gradiente di Allplan passa anche lui |
| Rifiuto: il parametro della texture si chiama **grana** e non può chiamarsi scala, né nelle etichette né da riga di comando | `core/lessico.py` | Funziona. Il divieto vale sulle nostre parole, non sul testo libero dell'utente |
| Ricetta rieseguibile: provider, modello, versione del preset, tutti i parametri, impronta della vista di partenza | `core/ricetta.py` | Fatta. È il seme della pila di livelli, che arriva nella sessione 3 |
| Errori in italiano, ognuno con il gesto successivo; nessun codice HTTP da solo | `core/errori.py`, `core/provider/comfy.py` | Fatti per: chiave rifiutata, credito esaurito (per Comfy: credito del workspace, con cosa fare), workspace che non può usare il modello, modello sconosciuto, limite di chiamate, immagine troppo pesante, servizio rotto, lavoro fallito, schema del modello non ancora verificato |
| Palette v1 in Allplan 2026 (AIRENDER), il telecomando: Vista (cattura, dimensione, esito), Stile (Esterno/Interno, preset, ora, cielo, intorno, materiali, modello con i nomi dello Studio), Invio (destinazione e costo prima di Genera, prova a secco, Genera che scrive in coda e torna, Annulla), Ultimo render (riassunto, Apri nello Studio, Apri cartella). Se la coda non gira avvia lo Studio senza finestra con un Python che non è Allplan (regola della sonda) | `allplan/comune/telecomando.py`, `allplan/v2026/PythonPartsScripts/airender/AirenderPalette.py`, `allplan/v2026/Library/AIRENDER/AirenderPalette.pyp` (generato da `allplan/v2026/scrivi_palette_pyp.py`) | Costruita il 2026-10-31 (prompt 7). La logica è provata con pytest e con uno Studio vero avviato senza finestra su Linux (lavoro scritto, preso dalla coda, errore «manca la chiave» riletto dalla palette). **Mai aperta in Allplan**: sezione 9 |
| Una coda sola per cartella: coda e Studio riscrivono ogni secondo un file «sono vivo» in `lavori/` (`coda-viva.json`, `studio-vivo.json`, con pid e indirizzo). Una seconda coda sulla stessa cartella si rifiuta (metterebbe fra gli errori il lavoro in corso della prima); lo Studio usa la coda che trova | `core/battito.py`, `core/coda.py`, `core/studio/__main__.py` | Fatto, provato con pytest. Un processo ucciso lascia il file: vale come morto dopo `BATTITO_SCADUTO_SECONDI` |
| Palette di prova in Allplan 2026: cattura la finestra attiva in PNG con la sua camera, prova a secco, genera | `allplan/v2026/`, `allplan/comune/ponte.py` | Cattura, prova a secco e invio vero funzionano in Allplan 2026: primo render dalla palette il 2026-10-27, salvato in `Usr\Local\AIRENDER\viste` con la sua ricetta. La finestra di conferma tronca il percorso del render. Dal 2026-10-21 la palette parla con Comfy Router senza che l'adattatore sia cambiato: segue il predefinito del motore |

**Non c'è ancora:** nessun pacchetto ALLEP, nessuna cartella
sorvegliata, nessuna pila di livelli su disco, nessuna miniatura, nessuna
espansione del linguaggio naturale (il testo dell'utente viaggia com'è, in coda
al prompt del preset).

Dipendenze: **una**, Pillow, usata in un file solo (`core/immagine.py`). Il
trasporto HTTP usa `urllib` della libreria standard apposta, per non dipendere
da `requests`.

## 8 · NON COSTRUITO

**Piano in corso, dal 2026-10-27: quattro PR, in quest'ordine.** Una sessione
per PR (regola di `CLAUDE.md`).

1. **Lo Studio nei documenti** — PR #11, unito il 2026-10-28: `DESIGN.md` con palette v1 e
   Studio, questa sezione, mockup e bozza dei blocchi in `docs/ui/`. Niente
   codice.
2. **Coda di lavori** — fatto in questo PR (sezione 7). Il motore come processo a parte, che prende lavori da
   una cartella (`lavori/in-attesa`, `in-corso`, `fatto`, `errore`), con
   scrittura atomica, stato leggibile e annullamento; la composizione del
   prompt a blocchi. In `core/`, senza Allplan, senza Studio.
3. **Studio v1** — fatto in questo PR (sezione 7). Genera e Risultato, eseguibile senza Allplan
   (`python -m core.studio`), sulla coda del PR 2. Ritocca resta in grigio.
4. **Palette v1** — il telecomando. Costruita il 2026-10-31 (prompt 7,
   sezione 7) **prima** che la sonda della palette rispondesse, su richiesta
   di Riccardo: ogni domanda della sonda è un'impostazione con un ripiego
   (`PALETTE_IMMAGINI_DA_SCRIPT` spenta; Python ed Edge trovati con la regola
   della sonda). Resta da fare: lanciare la sonda, fissare le impostazioni,
   aprire la palette in Allplan (sezione 9).

**Dal 2026-10-29, dopo le decisioni del 2026-10-28 (sezione 5):**

5. **Passi e Ritocca nei documenti, blocchi mancanti, banco di prova** —
   PR #14, unito il 2026-10-30. `DESIGN.md` con Studio · Passi e Studio · Ritocca riscritta;
   blocchi intorno, verde, persone «poche» (bozza 4) accesi nello Studio;
   varianti 2–4 col costo; `scripts/prova_blocchi.py` con i piani qualità,
   look, preset, catena e aree; miniature vere dai render del banco.
6. **L'albero dei passi nello Studio** — fatto in questo PR (sezione 7):
   modello dei passi su disco, i render di oggi come passi figli della
   vista, lavori che partono da un passo, «Rifai pulito dalla vista». Fatto
   prima del piano «catena» del banco: la soglia dell'avviso resta SCELTA
   finché il banco non dice quanto costa ogni generazione in più in spigoli.
7. **Ritocca** — fatto il 2026-10-30 (sezione 7), prima del piano «aree» del
   banco, su richiesta di Riccardo: il modo delle aree è un'impostazione.
   Resta da fare: lanciare il piano «aree», fissare `RITOCCO_MODO_AREE` con
   il risultato, e se Nano Banana 2 non rispetta le aree in nessuno dei due
   modi, rimettere i pixel fuori dalle aree nel motore (qui sotto,
   «Annotazione per aree», punto 2) o cambiare la schermata.

- Video — rimandato, non annullato. Arriva come livello sopra un fermo immagine.
- LoRA di stile addestrati sui render dello studio — è l'argomento di vendita
  forte della v2, non serve all'MVP.
- Nodo Visual Scripting — possibile, chiamerà lo stesso motore.
- **Mappa dei materiali da Allplan** — in pipeline dal 2026-10-22, prima strada
  per la schermata Materiali (sezione 5). Accanto alla vista, la palette cattura
  con la stessa camera una seconda immagine della finestra: ogni materiale un
  colore pieno e diverso. A questa immagine si affianca l'elenco "colore →
  materiale" letto dal modello. Il motore la legge come mappa: cliccando una
  zona del render si sa quale materiale è e come si chiama in Allplan, e quel
  nome entra nel prompt. Il motore deve assegnare al colore più vicino i pixel
  di bordo, dove i colori si mescolano. Finché non si sa come produrla (sezione
  9), resta un'ipotesi. Sostituisce la vecchia voce "segmentazione derivata dalle
  superfici del modello", che la dava come aggiornamento di qualità.
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

  Dal 2026-10-28 le aree sono rettangoli o selezioni libere, con una nota
  adesiva numerata ciascuna (sezione 5, `DESIGN.md` Studio · Ritocca). Due
  modi di dire al modello dove intervenire, da scegliere con il piano «aree»
  del banco di prova (`scripts/prova_blocchi.py --piano aree`):
  una **maschera per area**, oppure il render con i **riquadri numerati
  disegnati sopra** e un testo che li nomina ("nel riquadro 1…"). Il secondo
  funziona con i modelli di modifica a istruzioni, se li capiscono: nessuno dei
  due è verificato.

  Prima di scriverne il codice servono: uno schema di modello verificato dalla
  sonda; la risposta su come disegnare un riquadro dentro Allplan (sezione 9);
  i quattro stati della schermata in `DESIGN.md`. Nella schermata Materiali sta
  accanto al clic su una superficie e al nome scritto a parole, non al loro
  posto.
- **Segmentazione sul render** — in pipeline, non costruita. Serve dove Allplan
  non sa: superfici senza materiale nel modello, e cose che il modello non ha e
  il render aggiunge (cielo, vegetazione, contesto). Si mostra come mappa a
  colori, una zona per superficie, e si corregge con due gesti: **unisci**
  ("questo pezzo va con quel colore") e **separa** ("staccalo dal suo colore").
  È l'idea di Riccardo del 2026-10-22 per rendere aggiungi area / togli area.
  Ha i limiti della sezione 6: segue l'apparenza.

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

La sessione del 2026-10-21 non raggiungeva né `docs.comfy.org` né
`api.comfy.org`. **Il 2026-10-27 Riccardo ha lanciato `scripts/sonda_comfy.py`
sul suo PC** (Python 3.10.10, `--base64-nudo`): schema e una generazione per
FLUX.1 Kontext Pro e per Nano Banana 2, sulla cattura vera
`tests/dati/vista-20261021-093841.png`.

**Verificato dalla sonda, e uscito da qui:**

- **Il protocollo della coda.** `POST .../requests?fallback_provider=false`
  risponde **201** con `request_id`, `status: IN_QUEUE`, `queue_position`,
  `status_url`, `response_url`, `cancel_url`. `GET .../status` passa per
  `IN_PROGRESS` con `Retry-After` in secondi (3, poi 7) e chiude con
  `COMPLETED` senza `Retry-After`. `GET .../requests/{id}` risponde 200 con
  l'uscita del modello e l'intestazione `x-comfy-credits-used`.
- **Gli schemi dei due modelli**, letti da `/openapi.json` e confermati dalla
  generazione. Kontext: obbligatorio solo `prompt`; `input_image` base64 o URL;
  `aspect_ratio`, `seed`, `output_format`; il link firmato torna in
  `result.sample`, valido fino a 24 ore. Nano Banana 2: corpo nativo di Gemini
  (`contents` → `parts` → `inlineData`); l'immagine torna in base64 in
  `candidates[0].content.parts[…].inlineData.data`, oppure come link in
  `fileData.fileUri` se si chiede `uploadImagesToStorage`. Scritti in `SCHEMI`.
- **L'immagine senza prefisso `data:` va bene** per tutti e due. Con il
  prefisso non si è provato, quindi il motore manda il base64 senza prefisso.
- **Il prezzo di una generazione** con Nano Banana 2: **17,17 crediti**
  (`x-comfy-credits-used`), circa 0,08 $ secondo `x-litellm-response-cost`.
  La generazione Kontext è durata 4,4 secondi lato BFL; il suo prezzo non è
  stato copiato.
- **Le proporzioni.** Nano Banana 2 ha reso 1376x768 (1,792, come la vista);
  Kontext 1392x752 (1,851, circa il 3% più largo). In tutti e due i casi si era
  chiesto 16:9.
- **La tenuta dei tramezzi su questa vista.** Riccardo ha giudicato a occhio
  che tengono in tutti e due i modelli. **Su una vista sola**, bianca e senza
  ombre portate.

**Resta non verificato:**

- **`aspect_ratio` assente dà le proporzioni della vista** — lo schema di
  Kontext lo dice, ma il motore lo manda comunque (il rapporto standard più
  vicino), come nelle chiamate vere.
- **`fallback_provider=false` vale anche sulla rotta della coda** — nelle
  risposte non è comparsa `X-Comfy-Router-Fallback-Provider`, il che è
  coerente ma non prova che il parametro sia letto.
- **Un errore dentro un `COMPLETED`** — mai visto: il nome del campo (`error`,
  `error_type`) resta un'ipotesi.
- **Il 402 `insufficient_credits` non addebita niente**, e **cosa si paga se il
  tempo scade** — invariati, come scritti il 2026-10-21: il workspace aveva
  credito e nessuna chiamata è scaduta.
- **I modelli tengono la geometria su viste diverse** — una vista sola, con
  pochi muri. Servono almeno una vista con solaio e ombre portate, e una con
  aperture e più piani. Per verificare: `scripts/confronta_modelli.py` sulle
  catture nuove, e un occhio sugli spigoli.
- **Gli altri modelli del catalogo** (Kontext Max e altri) non hanno schema:
  si fermano prima di partire finché non passano dalla sonda. Nano Banana Pro
  (2026-10-31), GPT Image 2 e Seedream 5.0 (2026-11-01) hanno uno schema preso
  dalla documentazione, non dalla sonda. Una fonte non ufficiale dice Nano Banana 2 deprecato in favore di
  `vertexai/gemini-nano-banana-2.1`: se il Router lo ritira, il preset va
  cambiato e il nuovo modello va sondato.
- **Il seme con Nano Banana** — lo schema di Gemini non ha un campo per il seme:
  la ricetta lo salva, ma non arriva al modello. Rifare una ricetta dà
  un'immagine diversa, e la riesecuzione lo dice già.
- **La grana passa solo come frase nel prompt** — invariato. Riccardo ha
  trovato la grana di Nano Banana migliore, ma una frase che cambia la grana
  percepita resta un'ipotesi.
- **La palette mostra la destinazione completa** e **`ImageFont.load_default(size=…)`
  esiste nel Pillow di Allplan** — invariati, da vedere a video.

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

### Lasciato dalla sessione del 2026-10-27 (sonda della palette)

La sonda `AIRENDER sonda` (`allplan/v2026/.../AirenderSonda.py`, logica in
`allplan/comune/sonda_palette.py` e `sonda_figlio.py`) risponde alle cinque
domande del piano UI (palette in Allplan + Studio in finestra propria). Da qui
sono provati con `pytest` solo la scelta degli interpreti, il registro e il
processo di prova che parte staccato, serve una pagina su `127.0.0.1` e batte.
Tutto il resto aspetta il PC di Riccardo:

- **Un'immagine `Picture` della palette si cambia da script** — due modi
  provati: stesso file riscritto e valore cambiato con un percorso assoluto.
  Nessuno dei due è garantito dalla documentazione, che dice solo che il file è
  relativo al `.pyp`.
- **`PictureButtonList` mostra PNG messi accanto al `.pyp`** — nomi in
  `ValueList2`, come dice la documentazione 2022; la sintassi 2026 non è stata
  letta (sito non raggiungibile da questa sessione).
- **Un PythonPart lancia un processo a parte senza bloccare Allplan, e con quale
  Python** — `sys.executable` dentro Allplan potrebbe essere Allplan stesso: la
  sonda non lo lancia mai e prova prima il Python di Allplan, poi `py`.
- **`msedge --app=` apre la pagina locale come finestra senza barra.**
- **Allplan resta usabile mentre il processo lavora**, e il processo sopravvive
  alla chiusura della palette.
- **`Expander` e `Text` come `ValueType` nel `.pyp`** — usati per la prima volta.

### Lasciato dalla sessione del 2026-10-31 (palette v1, prompt 7)

La palette v1 non è mai stata aperta in Allplan: questa sessione non ha
Allplan. Da verificare sul PC di Riccardo, in quest'ordine:

- **Il .pyp si carica** — `StringComboBox`, `Expander`, `Picture`,
  `RadioButtonGroup` e le condizioni `<Visible>` su un campo nascosto
  (`Interno == 0`, `InCorso == 1`) sono scritti dalla documentazione, non
  provati. Se la palette non si apre, il messaggio della finestra *Trace* dice
  quale parametro.
- **I campi si ridisegnano dopo un clic** — l'adattatore scrive i valori in
  `build_ele` dentro `on_control_event` e dentro `execute`. Non è provato che
  Allplan ridisegni la palette, né che chiami `execute` dopo il cambio di un
  elenco (serve per rileggere destinazione e costo quando si cambia modello).
  Se non lo fa, Genera si rifiuta comunque (la destinazione mostrata non è
  quella vera) e il clic successivo la riscrive.
- **Lo Studio parte da Allplan e Allplan resta libero** — è la domanda 3-5
  della sonda. La palette prova il Python di Allplan con `PYTHONPATH` sulla
  cartella di Pillow, poi `py`. Se nessuno risponde con Pillow, lo dice con
  cosa installare.
- **Uno Studio avviato senza finestra resta acceso** finché non si chiude la
  sessione di Windows: non ha una finestra da chiudere. Apri nello Studio
  riapre la sua pagina; chiudere la pagina non lo ferma. Se dà fastidio, serve
  un «Chiudi lo Studio» nella pagina.
- **Una coda rimasta orfana** (Studio ucciso dal Task Manager) continua a
  girare e a battere: il prossimo Studio la usa invece di avviarne un'altra.
  Provato su Linux, non su Windows.
- **Le miniature** restano spente finché la sonda non risponde alla domanda 1.

### Da prima

- **`NemAll_Python_Utility.StartMenuFunction` può lanciare il salvataggio
  immagine** — l'API esiste, il nome dell'evento no. Per verificare: prova su
  macchina con Allplan 2026.
- **La rappresentazione a colori piatti si cambia senza muovere la camera** —
  dal 2026-10-22 **serve**: è la mappa dei materiali da Allplan (sezione 8).
  Verifica manuale, poi da script. Le domande, in ordine:
  1. esiste una rappresentazione della finestra in cui ogni materiale (o
     superficie) ha un colore pieno, senza luci né texture?
  2. si attiva e si toglie da Python, senza spostare la camera?
  3. si riesce a sapere quale colore corrisponde a quale materiale?
  4. tutto questo è possibile **senza modificare il modello dell'utente**? Se
     per ottenerla bisogna cambiare gli attributi degli elementi, anche solo
     per un momento, la strada è un'altra: un'interruzione a metà lascerebbe il
     progetto del cliente alterato.

  Per verificare: in Allplan 2026, sulla stessa finestra della cattura, cercare
  una rappresentazione a colori per materiale. Poi rimandare indietro due
  catture fatte una dopo l'altra, la vista shaded e quella a colori, con il
  nome della rappresentazione usata. Se le due immagini combaciano al pixel, la
  strada c'è.
- **`requests` è disponibile nell'interprete Python di Allplan 2026** —
  confermato solo per la 2025. **Non è più un rischio per il motore:** il
  trasporto usa `urllib` della libreria standard. Resta da verificare solo se
  un giorno servirà `requests` dalla parte della palette.
- **`PictureButtonList` regge una griglia di 12+ miniature senza rallentare la
  palette** — verifica su macchina.
- **Le condizioni dei provider consentono la rivendita dell'accesso** — da
  leggere prima di emettere la prima fattura, non dopo.

### Lasciato dalla sessione del 2026-10-27 (lo Studio nei documenti)

Questa sessione ha scritto solo documenti. Le decisioni dell'interfaccia
poggiano su cose non ancora provate:

- **Tutto quello che chiede la sonda della palette** (blocco qui sopra): senza
  un processo a parte che parte da Allplan e lo lascia libero, lo Studio non
  ha senso come finestra propria.
- **I blocchi di prompt della bozza 3** non sono mai stati mandati a un
  modello. In particolare: se la lunghezza (718-882 caratteri per i preset,
  sopra i 500-600 indicati come ottimo) pesa; se «Altissima definizione (32k)»
  cambia qualcosa rispetto a Base. Per verificare: la stessa vista con lo
  stesso preset, Base e 32k, con `scripts/confronta_modelli.py`, e un occhio
  sul microdettaglio.
- **I materiali scritti in italiano** passano al modello come sono: non si sa
  se Nano Banana 2 li capisce o se vanno tradotti prima.
- **Nano Banana 2 accetta più immagini in una richiesta via Comfy Router** —
  serve alla mappa materiali (vista + mappa a colori + immagine di
  riferimento). Kontext Pro probabilmente ne prende una sola.
- **La mappa a colori non finisce nei colori del render** — è la trappola dei
  colori letti come materiali, al contrario. Da provare con un render solo
  prima di costruire la mappa.
- **I mockup in `docs/ui/mockup/` non si aprono da soli**: chiedono un
  `support.js` dell'ambiente in cui sono stati disegnati, che non è nel
  repository. Si leggono come sorgente (struttura e testi), non come pagine.

### Lasciato dalla sessione del 2026-10-28 (coda dei lavori)

- **Nessun lavoro della coda è mai partito davvero.** Provata con il provider
  finto dei test e con un giro senza chiave. Per verificare sul PC: `py -m
  core.coda --cartella C:\AIRENDER-prova --aggiungi
  tests\dati\vista-20261021-093841.png --stile ora-blu`, poi `py -m core.coda
  --cartella C:\AIRENDER-prova --una-volta`. Rimandare indietro il contenuto
  di `lavori\stato\` e dire se in `lavori\fatto\` c'è il render con la sua
  ricetta. Costa una generazione.
- **Rinomina atomica su Windows.** `os.replace` è atomica anche lì, ma
  fallisce se un altro processo ha il file aperto in quel momento (lo Studio
  che legge lo stato). Non succede mai nei test, che girano su Linux. Se
  capita, il lavoro finisce in errore con «errore imprevisto»: da guardare
  quando lo Studio leggerà la coda.
- **Lo stato «in lavorazione» viene dal Router** (`IN_PROGRESS` durante
  l'attesa). Con Nano Banana 2 la sonda del 2026-10-27 ha visto la coda del
  Router, ma non ha scritto se `IN_PROGRESS` compare davvero o se il lavoro
  passa da `IN_QUEUE` a `COMPLETED`. Se non compare, lo stato resta «inviato»
  fino alla fine.
- **Annullare durante l'attesa smette di aspettare, non ferma il Router.** Il
  Router non è stato interrogato su un'API di annullamento: la vista può
  essere già stata fatta e addebitata, e lo stato lo dice.
- **Due processi della coda sulla stessa cartella**: il lavoro si prende con
  una rinomina, quindi uno solo dei due lo prende. Provato solo in un
  processo; due processi insieme no.
- **Nella ricetta di un lavoro della coda la grana è «media» per convenzione**:
  i blocchi non hanno una grana e i modelli del Router non la usano
  (`dettaglio_grana` resta assente). Da rivedere se la grana tornerà nel
  cambio di materiale.

### Lasciato dalla sessione del 2026-10-28 (Studio v1)

- **Lo Studio non è mai stato aperto su Windows né con Edge.** Provato su Linux
  con Chromium (Playwright) e un provider finto che colora la vista: i «render»
  degli screenshot in `docs/ui/studio-v1/` non sono render. Per verificare sul
  PC: `py -m core.studio --cartella C:\AIRENDER-prova` (con dentro
  `tests\dati\vista-20261021-093841.png`), poi dire se si apre una finestra
  di Edge senza barra, se la vista c'è, e mandare uno screenshot di Genera.
  Un invio vero da lì costa una generazione (circa 17 crediti).
- **La coda come processo figlio.** Lo Studio la lancia con lo stesso Python
  (`sys.executable -m core.coda`) e la chiude con Ctrl+C. Se la palette o un
  altro Studio ne hanno già una sulla stessa cartella, girano in due: il
  lavoro si prende con una rinomina, ma due processi insieme non sono mai
  stati provati (blocco della coda, qui sopra). Chiudere lo Studio durante un
  invio lascia il lavoro a metà: al riavvio va fra gli errori.
- **Il costo mostrato è quello di tre generazioni Nano Banana 2 a 2k** del
  2026-10-27 (`COSTO_NANO_BANANA_2_CREDITI`, MISURATA). Per Kontext lo Studio
  scrive «non misurato».
- **L'avviso dei colori come materiali** scatta sopra il 5% di pixel saturi
  (`QUOTA_COLORATA_AVVISO`, `SATURAZIONE_COLORE_MINIMA`, tutte e due SCELTE):
  provate su immagini sintetiche, mai su una vista di Allplan colorata per
  layer. Rimandare una vista colorata e dire se l'avviso compare.
- **Copia immagine** usa gli appunti del browser: in Edge `--app=` su
  `127.0.0.1` dovrebbe funzionare, non è stato provato. **Apri cartella** usa
  `os.startfile` su Windows, mai provato.
- **Le voci del mockup senza blocco di prompt sono in grigio**: rese diverse
  da Fotorealistico e I miei preset. Si accendono quando hanno il loro blocco
  o il loro salvataggio. (Intorno, Verde e persone «Poche» sono accese dal
  2026-10-29, con i blocchi della bozza 4.)

### Lasciato dalla sessione del 2026-10-29 (blocchi, varianti, banco di prova)

- **Nessun piano del banco è stato lanciato davvero.** Provati con un provider
  finto e a secco sulla vista dei test. Tutti e cinque costano circa 429
  crediti con Nano Banana 2 (2 + 9 + 8 + 4 + 2 invii). Per verificare sul PC,
  un piano alla volta, partendo dal più economico: `py scripts\prova_blocchi.py
  --immagine tests\dati\vista-20261021-093841.png --piano qualita`, poi
  aprire la pagina con `--giudica <cartella>` e rimandare `banco.json` e
  `giudizi.json`. Se i render mancano o la pagina è vuota, il banco ha un
  difetto; se ci sono, i giudizi decidono il predefinito della qualità.
- **La seconda immagine a Nano Banana 2 non è mai partita.** Il piano «aree»,
  modo (b), manda vista e maschera come due parti `inlineData` nella stessa
  richiesta: è la forma di Vertex AI, mai provata attraverso il Router
  (`piu_immagini_verificato_il` vuoto in `core/provider/comfy.py`). Se il
  Router la rifiuta, (b) finisce fra gli errori della pagina e (a) resta
  valido. Kontext Pro con due immagini si ferma prima di partire.
- **I blocchi della bozza 4 non sono provati.** In particolare: se «do not
  cover or hide any building element» basta a tenere alberi e persone lontani
  dalle finestre; se «sfondo neutro» senza più la parola «trees», insieme a
  verde «nessuno», tiene il modello dall'aggiungere alberi come faceva il
  27/10. I prompt dei preset esterni sono cresciuti a 780–990 caratteri: se
  la lunghezza pesa, lo dice il piano «preset».
- **Le due misure del banco sono grezze.** «Spigoli della vista ritrovati»
  (`SPIGOLI_SOGLIA`, `SPIGOLI_LATO_PX`, `SPIGOLI_TOLLERANZA_PX`, tutte
  SCELTE) è provata su immagini sintetiche e sulla vista dei test spostata a
  mano: regge il ricampionamento a 1376x768 (99,8%) e vede uno spostamento di
  4 px (83%). Un'ombra nuova o un albero davanti contano come spigoli persi.
  Non è lo scostamento della geometria del motore, che resta «non misurato».
  «Fuori dalle aree» (`DIFFERENZA_PIXEL_SOGLIA`, `AREE_BORDO_ESCLUSO_PX`)
  non è mai stata tarata su un risultato vero.
- **Varianti 2–4**: mai con un invio vero. Annulla ferma anche le varianti in
  attesa, provato solo a codice.
- **Le miniature vere non esistono ancora.** Il comando c'è; la prima nasce
  dal piano «preset». Una miniatura entra nel repository: va fatta da una
  vista che si può mostrare a tutti, non da un progetto sotto NDA.
- (Ritocca e Passi sono usciti da qui il 2026-10-30: vedi le due sessioni
  qui sotto.)

### Lasciato dalla sessione del 2026-10-30 (albero dei passi)

- **Nessun passo su un render è mai partito verso un modello.** Non sappiamo
  se Nano Banana 2 rispetta «Make only the change described below» su un
  render già fatto, né quanto si spostano gli spigoli: lo dice il piano
  «catena» del banco. Fino ad allora `PASSI_AVVISO_DA_GENERAZIONE` (2) è
  SCELTA.
- **La regola dei passi e le richieste a parole (bozza 5) sono SCELTE.** In
  «Rifai pulito dalla vista» la regola fissa dei preset dice «Change only the
  look described below» e subito dopo arrivano richieste che aggiungono
  alberi o persone: se il modello le ignora per questo, va scritta una regola
  apposta. Le richieste viaggiano in italiano, come i materiali.
- **Il costo di un passo è quello del modello per una vista**: un render
  mandato come immagine di partenza può costare diverso se ha un'altra
  dimensione. Il costo vero si legge dalla ricetta dopo l'invio.
- **L'albero lo scrive solo lo Studio**, una richiesta alla volta dentro lo
  stesso processo. Due Studi aperti sulla stessa cartella possono scriverlo
  insieme: l'ultimo vince, ma l'allineamento successivo rimette i passi
  mancanti dai lavori (non le ricette dei lavori già cancellati a mano).
- **Mai aperto su Windows né con Edge.** Le schermate sono di Chromium su
  Linux, a 1440 px e a 1280×800, con un provider finto che tinge la vista.
- **La coda vecchia rifiuta i lavori nuovi** (formato 2) con un messaggio,
  invece di mandare la vista al posto del render: provato solo a codice.

### Lasciato dalla sessione del 2026-10-30 (Ritocca)

- **Il piano «aree» non è mai partito, e Ritocca è costruita senza.**
  `RITOCCO_MODO_AREE` = «contorni» è SCELTA: partono con un'immagine sola, e
  basta. Non sappiamo se Nano Banana 2 tiene fermo il resto, se toglie i
  contorni magenta e i numeri dal risultato (la misura non lo vede: i
  contorni stanno nella fascia esclusa, i numeri appena fuori), né se segue
  le note numerate.
- **Nessun ritocco è mai partito verso un modello**, né in modo contorni né
  in modo maschera. La maschera parte come seconda immagine: Nano Banana 2 la
  accetta secondo lo schema, mai provato.
- **La misura fuori dalle aree non è tarata** su un risultato vero; se un
  modello rende un'altra dimensione, la misura ricampiona e lo dice.
- **Il lazo si semplifica** (un punto ogni 0,4% del lato) e un'area sotto
  l'1% del lato si scarta come clic sbagliato: due numeri della pagina,
  scelti, non in `config.py` perché non toccano il motore.
- **Mai aperto su Windows né con Edge**, né con un touchpad o una penna: le
  schermate sono di Chromium su Linux con il mouse simulato.
- **Un motore vecchio rifiuta i ritocchi** (formato 3) con un messaggio,
  invece di mandare il render senza aree: provato solo a codice.

### Lasciato dalla sessione del 2026-10-31 (fedeltà al disegno)

- **Le tre fedeltà cambiano davvero il render** — non verificato. Rigida e
  Libera sono testi scritti, mai mandati a un modello; Bilanciata è la regola
  fissa di sempre. Il piano «fedelta» del banco (3 invii, circa 52 crediti con
  Nano Banana 2) le confronta sulla stessa vista e misura gli spigoli.
- **Il menu «Fedeltà al disegno» nella palette** — generato nel `.pyp`, mai
  aperto in Allplan.

### Lasciato dalla sessione del 2026-10-31 (riferimento per lo stile)

- **Nano Banana 2 riceve due immagini in una chiamata vera** — mai provato
  (`piu_immagini_verificato_il` vuoto). Il primo render con un riferimento è
  la prova, circa 17 crediti; lo Studio lo dice prima dell'invio.
- **Il modello prende dal riferimento solo palette, luce e materiali** — la
  frase è scritta, non provata. Se copia forme o inquadratura, va riscritta.

### Lasciato dalla sessione del 2026-10-31 (rese non fotografiche)

- **Le quattro rese rendono quello che promettono** — mai mandate a un
  modello. Il piano «rese» del banco (4 invii, circa 69 crediti con Nano
  Banana 2) le confronta sulla stessa vista.
- **Quali assi spegnere** — scelto a tavolino (SPENTI_DA_RESA in
  core/blocchi.py). Se uno schizzo con la luce accesa rende meglio, si
  riaccende lì.
- **Il menu Resa nella palette** — generato nel `.pyp`, mai aperto in Allplan.

### Lasciato dalla sessione del 2026-10-31 (esporta per il cliente)

- **Il PSD si apre in Photoshop con i livelli e i nomi giusti** — scritto a
  mano (core/esporta.py), riletto solo con Pillow. Da aprire una volta in
  Photoshop: deve mostrare la vista in basso e un livello per passo, con
  accenti e «·» nei nomi.
- **Il peso del PSD a 4K** — non compresso: circa 4 byte per pixel per
  livello, quindi un 4K con tre passi supera i 200 MB. Se pesa troppo, si
  aggiunge la compressione RLE.
- **Dove salvare** — Riccardo non l'ha detto; scelta `esportati/` accanto
  alle viste.

### Lasciato dalla sessione del 2026-10-31 (sonda dei materiali, prompt 15 fase A)

- **Da un elemento di Allplan 2027 si legge il materiale assegnato** — non
  verificato. La documentazione dell'API non si legge per intero da questo
  ambiente: si vedono solo i nomi di classi come `SurfaceDefinition`,
  `TextureMapping` e `ElementsSelectService.SelectAllElements`, e nessuna
  firma. La sonda `AIRENDER sonda materiali` prova le letture possibili
  (metodi `Get*` dell'elemento, proprietà comuni, attributi, elemento Python) e
  scrive cosa torna. Un nome di materiale in `risultati-materiali.txt` vuol
  dire sì.
- **La color map di Allplan dà un colore pieno per materiale, alla stessa
  grandezza della vista normale** — non verificato. Riccardo dice che la vista
  si può mettere in color map. La sonda non sa farlo da script: la color map la
  mette lui a mano, la sonda salva la finestra e conta i colori. Pochi colori
  che coprono quasi tutta l'immagine vogliono dire sì.
- **Il colore della color map si lega al nome del materiale** — non
  verificato, ed è la domanda più difficile. Se Allplan non dà l'elenco
  colore → materiale, serve un'altra strada, da decidere con l'uscita della
  sonda.
- **`SelectAllElements` lascia selezionato tutto il modello** — non
  verificato. È l'unica chiamata della sonda che tocca qualcosa; se succede,
  basta un clic nel vuoto.

### Lasciato dalla sessione del 2026-11-01 (inserisci nel contesto)

- **Nano Banana 2 inserisce l'edificio nell'area del contesto** — mai
  provato: blocchi scritti dal prompt Notion di Riccardo e dal suo flusso a
  parole, non mandati. Per verificare: nello Studio carica uno screenshot del
  luogo, disegna l'area, cattura da Allplan la vista in pianta (zenitale) o
  dall'alto di sbieco (volo d'uccello) e Genera. Guarda se l'edificio sta
  nell'area, alla scala giusta, e la misura «fuori dall'area».
- **L'ordine contesto-poi-vista dà al render la forma del contesto** —
  dedotto dal codice (il rapporto segue la prima immagine), non provato.
- **«Cerca sul web» (ricerca Google di Nano Banana) passa dal Router** —
  mai provato, comando in grigio. Per verificare:
  `py scripts\sonda_comfy.py --modello vertexai/gemini-3.1-flash-image --base64-nudo --ricerca-web`
  (una generazione, circa 17 crediti più l'eventuale ricerca). Se il Router
  rifiuta `tools`, resta spento; se lo accetta, vanno letti costo e
  suggerimenti di ricerca che i termini Google chiedono di mostrare.
- **Lo screenshot da Google Earth si può usare** — non è una questione del
  codice: i termini di Google Maps Platform vietano di usare quelle immagini
  con modelli di AI. AIRENDER non le scarica; lo screenshot lo porta
  l'utente, e per la vendita va detto (thread «Pianificare il
  fotoinserimento», 2026-11-01).

### Lasciato dalla sessione del 2026-11-01 (GPT Image 2 e Seedream 5.0)

- **GPT Image 2 e Seedream 5.0 rispondono al corpo scritto in `comfy.py`** —
  non verificato. Nomi (`openai/gpt-image-2`, `byteplus/seedream-5-0-260128`) e
  campi vengono dalle pagine «code» della documentazione del Router lette il
  2026-11-01 (quelle di `gpt-image-1.5` e `seedream-5-0-260128`; la pagina di
  `gpt-image-2` è uguale a parte il nome). Da qui api.comfy.org non risponde: il
  primo render vero è la prova, e lo Studio lo dice prima dell'invio.
- **GPT Image tiene la geometria** — non verificato, e c'è un motivo di dubbio:
  è un modello che ridisegna l'immagine intera, non un modello di modifica
  come Kontext. Confrontare gli spigoli col banco o a occhio.
- **Seedream rispetta la misura in pixel chiesta** — non verificato. Si chiede
  la forma esatta della vista (area fra circa 2560×1440 e 3072×3072, secondo la
  documentazione), senza cornice.
- **Costo di GPT Image 2 e Seedream 5.0** — non misurato: lo dice il primo
  render (`x-comfy-credits-used`).

### Usciti da questa sezione, con la loro verifica

- **Il motore stesso fa un invio vero** — verificato il 2026-10-27 sul PC di
  Riccardo, Windows, Allplan 2026, due volte: da `py -m core.cli --immagine
  tests\dati\vista-20261021-093841.png --preset base` e dal pulsante *Genera
  render* della palette di prova (vista 1550x857 del modello BOSCO). Tutte e due
  con Nano Banana 2, preset Base v3, 17,17 crediti ciascuna; ricetta salvata
  accanto al render con `fallback_provider` a `false`, l'id della richiesta, i
  crediti e nessuna chiave. La chiave arriva alla palette da una variabile
  d'ambiente utente permanente, letta da Allplan dopo il riavvio. Visto nei due
  render: il modello aggiunge un contesto che nella vista non c'è (alberi,
  cielo, prato, piazzale) e prende i colori di visualizzazione di Allplan per
  materiali (una falda viola è diventata lamiera viola). Vedi le Trappole note
  in `CLAUDE.md`.

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
  lavoro che il modello sa già fare da solo. **Ripresa il 2026-10-22** come mappa
  dei materiali (sezioni 5 e 8): la cattura la fa la palette, l'utente non fa
  niente in più.
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
**Scartati:** nodo Visual Scripting (nessuna UI persistente, pubblico ristretto).
~~Applicazione web separata (costringerebbe a caricare e scaricare file a mano).~~
**Ribaltato il 2026-10-27** (sezione 5): accanto alla palette c'è lo **Studio**,
una pagina locale servita dal motore su `127.0.0.1` e aperta in una finestra
propria. Non è un'applicazione web in rete: non carica né scarica file a mano,
legge la stessa cartella in cui la palette salva le viste. Resta scartata
un'applicazione su un server nostro.

**Accettiamo di non poter:**
- girare su macOS o Linux — Allplan è solo Windows;
- evitare un porting all'anno — Allplan rilascia una versione per anno;
- funzionare offline — la generazione è sempre remota;
- garantire che le immagini non lascino la macchina del cliente.

## 12 · Schermate

Dettaglio in `DESIGN.md`.

Dal 2026-10-27 le schermate sono quelle della palette v1 e dello Studio
(sezione 5). Le cinque della palette di prova sono sostituite: la tabella del
cambio è in `DESIGN.md`.

| Schermata | Lavoro che serve | Lo stato vuoto dice |
|---|---|---|
| Palette v1 (costruita il 2026-10-31, mai aperta in Allplan) | Catturare la vista, scegliere lo stile di base, mandare senza bloccare Allplan | "Nessuna vista ancora. Clicca una volta nella finestra 3D da rendere (shaded, con ombre), poi Cattura." |
| Studio · Genera | Scegliere lo stile con calma, vedere il prompt vero, la destinazione e il costo | "Nessuna vista ancora. Catturala dalla palette in Allplan, oppure scegli un file." |
| Studio · Risultato | Decidere se è ancora il proprio edificio, confrontare render e modelli | "Nessun render ancora. Scegli uno stile in Genera e premi Genera." |
| Studio · Passi | Ritrovare e rifare i passi di una vista | "Nessun passo ancora. Genera un render da Genera: sarà il passo 1." |
| Studio · Ritocca | Disegnare aree a rettangolo o libere con note numerate, un solo Applica; il risultato è un passo nuovo | "Prima serve un render. Generane uno da Genera." |
