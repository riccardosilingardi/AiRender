# AIRENDER — Product Requirements

Documento vivo. Descrive quello che è vero **adesso**, non quello che è previsto.
Ultimo aggiornamento: **2026-09-30** (sessione 0, solo documenti).

> Repository: `airender`. Nome fissato il 2026-09-14.

## Come leggere le fonti in questo documento

Questa sessione **non ha potuto leggere nessuna pagina primaria**: il proxy di
rete della sessione blocca `help.allplan.com`, `pythonparts.allplan.com`,
`www.allplan.com`, `github.com/NemetschekAllplan` e `docs.magnific.com`
(risposta `EGRESS_BLOCKED` / 403, provato il 2026-09-30). Sono passate solo le
ricerche web, che restituiscono **titolo, URL e un riassunto** della pagina, non
il testo. Quindi:

- **[snippet]** = il fatto viene dal riassunto di una ricerca; l'URL accanto è
  la pagina che lo contiene, **ma la pagina non è stata letta**. Vale come
  indizio serio, non come verifica.
- **[utente]** = risposta data dal proprietario del progetto (sezione DECISIONI
  del prompt della sessione 0). Vale come fonte.
- **[visto]** = eseguito in questa sessione, con l'output sotto gli occhi.
- **[terzi]** = pagina non ufficiale (blog, forum). Indizio debole.
- Nessuna etichetta = non è un fatto, è una decisione o un piano.

Tutto ciò che nel vecchio PRD (2026-09-14) era scritto come fatto su Allplan,
sul suo SDK o su un provider, e che non ha trovato conferma qui sotto, è stato
**riclassificato NON VERIFICATO** (sezione 9).

---

## 1 · Cos'è

Un plugin per Allplan che trasforma una vista 3D in un'immagine presentabile a
un cliente, **senza che la geometria cambi**. È l'idea di Veras, ma dentro
Allplan. L'utente sceglie uno stile, scrive due parole se vuole, preme Genera, e
ottiene un render da confrontare con la vista di partenza. Dopo, potrà cambiare
il materiale di una superficie senza rifare il resto (fase 5 della ROADMAP).

Non è un motore di rendering. È uno strato che sta fra la vista di lavoro e
l'immagine di presentazione.

**Versioni supportate: Allplan 2026 e Allplan 2027, entrambe fin dalla v1** [utente],
con un adattatore per versione e lo stesso motore sotto.

## 2 · Cosa si rifiuta di fare

- **Non inventa geometria.** Se il controllo strutturale non tiene, lo dice.
  Non consegna un'immagine bella che rappresenta un edificio diverso da quello
  disegnato. *(Il rifiuto sull'immagine di partenza inadatta esiste nel motore;
  la misura della tenuta no: vedi sezione 9.)*
- **Non promette la scala metrica dei materiali.** Lo slider governa la
  **grana** (fine, media, grossa), non i millimetri.
- **Non manda niente fuori senza dire dove va.** Il nome del servizio
  destinatario è visibile prima dell'invio.
- **Non gestisce crediti né fatturazione.** La chiave API è dell'utente; il
  tetto di spesa si imposta presso il provider.
- **Non stampa un valore incerto come certo.** Se lo scostamento della
  geometria non si è potuto misurare, l'interfaccia lo scrive a parole.
- **Non genera video in v1.** Il video arriva dopo, come livello sopra un fermo
  immagine.
- **Non promette l'automazione dove non è dimostrata.** In v1 l'acquisizione
  dell'immagine è manuale; il pulsante automatico entra solo se la verifica SDK
  (ROADMAP fase 3) lo dimostra fattibile su 2026 **e** su 2027.

## 3 · Per chi è

**Versione 1: io e il mio studio, chiave API mia** [utente]. Nessun cliente
esterno, nessuna rivendita ora.

Architetti che usano Allplan ogni giorno e che oggi, per avere un'immagine
presentabile, pagano un visualizzatore esterno o perdono mezza giornata. Hanno
provato l'AI e si sono irritati perché "cambia il progetto". Non devono sapere
cos'è una mappa di profondità. Due paure concrete: che il disegno del cliente
finisca su un server sconosciuto, e che l'immagine consegnata non corrisponda al
progetto approvato.

*(Il pubblico più ampio del vecchio PRD — studi terzi, NDA — è fuori dalla v1.
Resta come direzione, non come requisito.)*

## 4 · Percorso utente

Due oggetti diversi, che il vecchio PRD confondeva. Vanno tenuti separati:

| | **Inquadratura salvata** | **Immagine esportata** |
|---|---|---|
| A cosa serve | Riprodurre **la vista** in Allplan (camera, prospettiva, scala) | Essere **l'input** che il plugin manda all'AI |
| È un'immagine? | Secondo il manuale 2015: **no** [utente, da verificare su 2026 e 2027] | Sì: un file (JPG, PNG, BMP, …) |
| Chi la produce | Funzione "Salva, carica inquadratura" [utente] | Funzione di esportazione dell'immagine della finestra |
| Chi la legge | Solo Allplan | Il plugin (cartella osservata) |

### Come è verificato oggi

**Immagine esportata.** Esiste, in versioni di Allplan precedenti, una funzione
del menu File che salva il contenuto della finestra come bitmap. Formato scelto
fra JPG, PNG, BMP, EPS e altri; dimensione scelta come *risoluzione ed estensione*, *dimensione in pixel*
oppure *percentuale della dimensione dello schermo*; il TIFF genera anche un
GeoTIFF [snippet: Allplan 2016-1 "Saving contents of viewport as a bitmap"
https://help.allplan.com/Allplan/2016-1/1033/Allplan/7671.htm — Allplan 2018-0
"Transferring bitmap data from Allplan to other programs"
https://help.allplan.com/Allplan/2018-0/1033/Allplan/7407.htm — Allplan 2020-1
"Setting the resolution of bitmap images"
https://help.allplan.com/Allplan/2020-1/1033/Allplan/7406.htm].
**Non ho verificato che la funzione esista con lo stesso nome, gli stessi formati
e le stesse risoluzioni in Allplan 2026 e 2027.** Il nome esatto nell'interfaccia
italiana non è noto: quello scritto nel vecchio PRD ("Salva contenuto finestra
come immagine") non ha trovato conferma.

**Inquadratura salvata.** La procedura descritta dal proprietario è: icona
"Salva, carica inquadratura" (barra strumenti della finestra, menu contestuale
o barra inferiore) → Nuovo → nome → Invio [utente]. **Non l'ho trovata nella
documentazione 2026 né 2027.** Ho trovato invece una funzione diversa,
"Save, Load Arrangement" nel menu a tendina *Window*, che salva la **disposizione
delle finestre** e non la camera [snippet: Allplan 2026-0 "Window (dropdown list)"
https://help.allplan.com/Allplan/2026-0/1033/Allplan/93777.htm — Allplan 2021-1
"Saving a viewport arrangement"
https://help.allplan.com/Allplan/2021-1/1033/Allplan/7756.htm]. Sono due cose
distinte e non vanno confuse: cosa salva davvero l'icona, come si chiama, come
si ripristina, e se 2026 e 2027 differiscono, è **NON VERIFICATO** (sezione 9).

### Percorso v1 (piano, da confermare con le verifiche di ROADMAP fasi 2–3)

1. **A mano, in Allplan:** l'utente ripristina l'inquadratura salvata (se serve
   ritrovare la vista), mette la vista in shaded con ombre attive e sfondo
   neutro, ed **esporta l'immagine** in una cartella che il plugin osserva.
2. Il plugin trova il file, lo controlla (vista adatta? abbastanza grande?) e lo
   mostra. Se l'immagine è inadatta dice perché e cosa risalvare.
3. L'utente sceglie uno stile e, se vuole, scrive due parole. **Stile a comando:
   sceglie e preme Genera** [utente]. Nessuna anteprima live.
4. Prima dell'invio l'interfaccia dice **a quale servizio** va l'immagine.
5. Il plugin mostra vista di partenza e render affiancati. Lo scostamento della
   geometria è mostrato solo se misurato; altrimenti è scritto che non si è
   potuto misurare.
6. *(Fase 5)* L'utente sceglie una superficie e cambia il materiale.
7. *(Fase 5)* Il risultato è una pila di livelli rieseguibile, non un PNG piatto.

Il passo 1 è manuale **per decisione** [utente]: il pulsante "Genera da
inquadratura" entra solo se la verifica SDK lo dimostra, ed è da provare su
entrambe le versioni.

## 5 · Decisioni, con le ragioni

| Data | Decisione | Perché | Stato |
|---|---|---|---|
| 2026-09-30 | Acquisizione v1 **manuale**; automatico dopo la verifica SDK | Non è dimostrato che l'SDK permetta di ripristinare un'inquadratura né di lanciare l'esportazione (sezione 6b) | [utente] |
| 2026-09-30 | **Due adattatori, 2026 e 2027**, stesso motore sotto, fin dalla v1 | Il proprietario ha entrambe le versioni installate e le verifica entrambe | [utente] |
| 2026-09-30 | Livello "Veras" v1 **a comando** (scegli stile, premi Genera) | Anteprima live costa una chiamata a ogni modifica | [utente] |
| 2026-09-30 | Pubblico v1: **io e il mio studio, chiave API mia**; rivendita non ora | Evita backend, fatturazione, licenze | [utente] |
| 2026-09-30 | Motore immagine: **Magnific come primo candidato, non validato** | Il test di tenuta non è mai stato eseguito (il connettore rispondeva in errore) | [utente] |
| 2026-09-30 | **Segmentazione a valle sul render**; il livello linguistico sta nel plugin | La segmentazione a valle non chiede nulla all'utente; cambiare motore non tocca la parte che parla con l'utente | [utente] |
| 2026-09-14 | Una sola immagine in ingresso: la vista shaded | Chiedere più passate all'utente uccide l'adozione | Decisione, invariata |
| 2026-09-14 | Niente ID map esportata da Allplan in v1 | La segmentazione a valle dà una UX migliore | Decisione, invariata |
| 2026-09-14 | Palette PythonPart, non nodo Visual Scripting | *Ragione originale ("il nodo VS non ha UI persistente né job asincroni") non verificata — NON VERIFICATO* | Decisione da riconfermare |
| 2026-09-14 | Due modalità: **ritocco** (maschera) e **variante** (rigenerazione a stesso seed) | Il riempimento mascherato non ricalcola riflessi e luce di rimbalzo | Decisione, invariata |
| 2026-09-14 | BYOK, chiave del cliente | Un modello a crediti richiede backend, fatturazione, antifrode | Decisione, invariata |
| 2026-09-14 | ~~Allplan 2026 come minimo, 2027 a seguire~~ | — | **Ribaltata il 2026-09-30**: 2026 e 2027 insieme |
| 2026-09-14 | ~~Cartella sorvegliata invece di cattura programmatica~~ | — | **Precisata**: resta la cartella osservata, ma v1 è esportazione manuale |
| 2026-09-14 | ~~Magnific "API a consumo senza abbonamento"~~ | — | **Sotto accusa**: fonti recenti dicono che il pay-per-usage è stato chiuso il 2026-06-30 (sezione 6e). Da verificare prima di spendere |

## 6 · Fonti dati

### Dati del prodotto

| Fonte | Cosa fornisce | Quanto è buona |
|---|---|---|
| Immagine esportata da Allplan | Contenuto della finestra, formato e dimensione scelti dall'utente | Esiste nelle versioni precedenti [snippet, sez. 4]. **2026 e 2027 non verificate** |
| Riferimento strutturale del provider (`structure_reference`, `structure_strength`) | Aderenza alla composizione dell'immagine sorgente | **Da misurare.** È ciò che decide se il prodotto esiste |
| Stima di profondità | Deduzione dall'immagine | Non verificata da nessuna misura nostra |
| Segmentazione a valle | Maschera della regione scelta | **Segue l'apparenza, non il modello**: è l'anello debole |

### Risultati della verifica del 2026-09-30 (passo 2)

Regola: dove non ho trovato, scrivo "non trovato". Non ho riempito nessun buco.

**a) Procedura d'uso, 2026 e 2027**

| Domanda | 2026 | 2027 |
|---|---|---|
| Cosa salva "Salva, carica inquadratura" | **Non trovato** | **Non trovato** |
| Nome nella UI (italiano) | **Non trovato** | **Non trovato** |
| Come si ripristina | **Non trovato** | **Non trovato** |
| Esportazione immagine: funzione | Non confermata per la 2026 (esiste nelle versioni precedenti, sez. 4) | **Non trovato** |
| Esportazione: risoluzione e formati | Non confermati per la 2026 (in versioni precedenti: JPG, PNG, BMP, EPS…, risoluzione/pixel/percentuale) | **Non trovato** |
| Differenze 2026 ↔ 2027 | **Non confrontabili**: nessuna pagina 2027 trovata sulla funzione. Non è "nessuna differenza trovata": è "non ho potuto cercare" | |

Nota: il manuale 2015 citato dal proprietario non l'ho riletto; l'affermazione
"salva camera, prospettiva e scala, non un'immagine" è sua [utente].

**b) SDK PythonParts, 2026 e 2027**

| Cosa | Risultato |
|---|---|
| (1) Leggere o ripristinare un'inquadratura salvata | **Non trovato** in nessuna delle due versioni. Cercati: `ViewportUtil`, `ViewSettings`, `GetViewSettings`, `SetViewSettings`: nessuna corrispondenza in una pagina dell'SDK |
| (2) Avviare l'esportazione dell'immagine | **Non trovato.** Il modulo `LibraryBitmapPreview` [snippet: https://pythonparts.allplan.com/latest/api_reference/Utils/LibraryBitmapPreview/] serve alle miniature della libreria, non all'esportazione della finestra: **non è la stessa cosa** e non va usato come sostituto |
| (3) Osservare una cartella | **Non trovato** nell'SDK. Esiste un sistema di eventi ("invocazione passiva in risposta a eventi") [snippet: https://pythonparts.allplan.com/2027/manual/features/events/], che non è un osservatore di cartelle. Osservare una cartella con la libreria standard di Python resta possibile in linea di principio, ma **come si comporta dentro la palette (thread, ciclo di vita) non è verificato** |
| Altro trovato | `ZoomService` in `NemAll_Python_BaseElements` porta la vista su elementi dati [snippet: https://pythonparts.allplan.com/latest/api_reference/InterfaceStubs/] — non ripristina inquadrature |

Esistono pagine di documentazione con prefisso `/2027/` [snippet:
https://pythonparts.allplan.com/2027/manual/key_components/ e
https://pythonparts.allplan.com/2027/manual/features/events/], quindi la
documentazione SDK 2027 esiste; **non ho potuto aprirla**. Il sito `latest`
reindirizza al 2026 [snippet: https://pythonparts.allplan.com/latest/] al momento
degli indici di ricerca. "Non trovato" significa: nessuna pagina restituita dalla
ricerca, **non** "l'API non esiste". La verifica vera è aprire l'indice
dell'API (`InterfaceStubs`) 2026 e 2027 con un browser normale, e cercare
"view", "viewport", "bitmap", "camera".

**c) Interprete Python di Allplan**

| | 2026 | 2027 |
|---|---|---|
| Versione di Python | **3.13.9**, dall'hotfix 2026-0-3 (22 gennaio 2026) [snippet: https://www.allplan.com/system/releasenotes/2026/allplan-2026-0-3/]. La versione prima dell'hotfix: non trovata | **Non trovato** |
| `requests` | Le note di rilascio dell'SDK dicono che il pacchetto è "ora distribuito con ALLPLAN" [snippet: https://pythonparts.allplan.com/2025/release_notes/] — pagina del 2025, quindi vale per una versione **≤ 2025**; per la 2026 è probabile, **non verificato** | **Non trovato** |
| Pillow | **Non trovato** fra i pacchetti distribuiti. È installabile a mano: copiando in `…\Prg\Python\lib\site-packages` o col PythonPart di esempio `InstallPythonPackage` [snippet, percorsi di una versione precedente: https://pythonhosted.org/allpy/setup.html — https://connect.allplan.com/forum/topics/topic/topics/pythonparts/import-additional-libraries.html] | **Non trovato** |

Nota di progetto: il motore usa `urllib` (libreria standard) e Pillow in un file
solo (`core/immagine.py`) [visto], quindi l'assenza di `requests` non lo blocca;
l'assenza di Pillow sì (o costringe a riscrivere quel file).

**d) Plugin Manager e pacchetto ALLEP**

| | 2026 | 2027 |
|---|---|---|
| Esistenza | Il Plugin Manager "offre un modo nuovo per installare, aggiornare e disinstallare plugin ALLEP" e mostra i plugin del plugin hub [snippet: https://www.allplan.com/system/releasenotes/2026/allplan-2026/] | **Non trovato** |
| Installazione | Si scarica il file `.allep` dalle release GitHub e compare nel Plugin Manager [snippet: https://github.com/NemetschekAllplan/plugin-hub] | **Non trovato** |
| Formato pacchetto | Semplificato, più tipi di contenuto [snippet, stessa pagina delle note 2026] | **Non trovato** |
| Differenze 2026 ↔ 2027 | **Non confrontabili** | |

**e) Magnific API**

| Domanda | Risultato |
|---|---|
| Parametri | `structure_reference` (valore codificato, l'esempio è una stringa base64) e `structure_strength` (numero, esempio 50) sono nella pagina dell'endpoint Mystic [snippet: https://docs.magnific.com/api-reference/mystic/post-mystic]. **Intervallo 0–100, semantica e valori validi: non letti dalla pagina** |
| Accesso a consumo senza piano enterprise | **Contraddetto dalle fonti più recenti.** Il pay-per-usage sarebbe stato chiuso il **30 giugno 2026**; restano piani a crediti Business o Enterprise (indicato ~55 $/utente/mese annuale) [terzi: https://www.scopeful.org/blog/magnific-api-pay-per-usage-discontinued-2026; snippet: https://docs.magnific.com/pricing-payg]. Endpoint e intestazione `x-magnific-api-key` restano uguali. **Non verificato sulla pagina ufficiale né sul cruscotto dell'account** |
| Condizioni sulla rivendita | **Non trovato.** Non ho letto i termini |

## 7 · Costruito

**Solo ciò che ho visto funzionare in questa sessione (2026-09-30), su Linux, Python 3.11, Pillow 12.3.0** [visto]:

- `pytest`: **67 passati** in 28 secondi.
- Prova a secco su un'immagine sintetica ombreggiata: il motore misura la vista
  (900×600, 37 livelli di grigio), dice la destinazione (*"Magnific
  (api.magnific.com). 1 immagine lascia questa macchina."*), scrive la forza
  della struttura come *"70 — valore scelto, non ancora misurato"* e mostra il
  prompt che partirebbe. **Non ha inviato niente.**
- Su un'immagine sintetica wireframe (2 livelli di grigio, sfondo 99%) il motore
  **rifiuta** e dice cosa risalvare.
- `core/config.py` ha costanti con etichetta di provenienza. Il motore non
  importa nulla di Allplan (un test lo controlla; `grep` sul codice conferma).

| Cosa | Dove | Stato visto |
|---|---|---|
| Riga di comando: vista + preset + testo → ricetta rieseguibile | `core/cli.py` | Provata **fino alla prova a secco**. L'invio vero: **mai eseguito** |
| Casa unica delle decisioni | `core/config.py` | Presente; test la proteggono |
| Strato provider sostituibile (un solo provider, Magnific) | `core/provider/` | Presente; provato solo con rete simulata |
| Rifiuto vista inadatta | `core/idoneita.py` | Provato su **immagini sintetiche**, mai su export veri |
| Rifiuto "scala" nelle nostre etichette | `core/lessico.py` | Coperto dai test |
| Ricetta rieseguibile | `core/ricetta.py` | Coperta dai test |
| Errori in italiano con il gesto successivo | `core/errori.py` | Coperti dai test |

**Non c'è:** nessuna palette, nessun adattatore (né 2026 né 2027), nessun pacchetto
ALLEP, nessuna cartella osservata, nessuna pila di livelli su disco, nessuna
miniatura, nessuna espansione del linguaggio naturale, nessuna misura di
tenuta della geometria, nessuna chiamata reale al provider.

## 8 · NON COSTRUITO

- Adattatore Allplan 2026 e adattatore Allplan 2027.
- Cartella osservata dal plugin.
- Palette con griglia di miniature.
- Misura della tenuta della geometria (forza 50/70/90).
- Segmentazione e pila di livelli.
- Preset incrementali: paesaggio, persone, auto.
- Pacchetto ALLEP e installazione.
- Pulsante automatico "Genera da inquadratura" (condizionato alla verifica SDK).
- Video (Higgsfield, Krea) — dopo, come livello sopra un fermo immagine.
- Anteprima quasi live — dopo.
- Comfy Serverless come motore v2 — dopo.
- Nodo Visual Scripting — possibile, stesso motore.
- Segmentazione derivata dalle superfici del modello Allplan.
- Rivendita, licenza, proxy — dopo.
- Allplan 2028 — quando esce.

## 9 · NON VERIFICATO

**Sezione permanente.** Ogni voce dice la **versione di Allplan** a cui si
riferisce, cosa aprire o provare, e cosa significherebbe il risultato. Si esce
solo con una verifica.

### A · Procedura d'uso (Allplan 2026 **e** 2027, da fare su entrambe)

1. **Cosa salva davvero "Salva, carica inquadratura"** — *2026 e 2027.* Aprire
   la funzione, salvare un'inquadratura, cambiare vista, ripristinare. Se torna
   la stessa camera e prospettiva: l'inquadratura è utile per ritrovare la vista.
   Se dopo il ripristino la vista è diversa (per esempio non torna lo stile di
   visualizzazione o le ombre), il percorso deve dire all'utente di risalvare
   quei parametri a mano.
2. **Nome esatto in italiano dell'icona e dei comandi** — *2026 e 2027.* Copiare
   le etichette dall'interfaccia. Finché non sono note, i testi dell'interfaccia
   non le citano tra virgolette.
3. **Come si esporta un'immagine e con quale nome** — *2026 e 2027.* Il codice
   contiene oggi il nome **"Salva contenuto finestra come immagine"**
   (`core/idoneita.py`, messaggio di rifiuto) e questa frase non è verificata:
   se il nome è diverso, il messaggio manda l'utente a cercare un comando che
   non esiste. Da correggere in una sessione di codice.
4. **Risoluzione massima e formati dell'esportazione** — *2026 e 2027.*
   Provare a esportare a risoluzione alta; annotare pixel massimi, formati
   disponibili, se l'esportazione include lo sfondo e le ombre. Se il lato
   lungo massimo è sotto `LATO_MINIMO_PX` (512), il motore rifiuterebbe ogni
   export.
5. **Le viste shaded con ombre di Allplan passano il controllo di idoneità** —
   *2026 e 2027.* Dieci export veri: cinque shaded buone, tre wireframe, due
   senza ombre. Nessun falso rifiuto sulle prime cinque. **Verifica più urgente
   del motore:** un falso rifiuto blocca chi ha fatto tutto giusto.

### B · SDK PythonParts (2026 e 2027)

6. **Esiste un'API per leggere o ripristinare un'inquadratura salvata** — *2026
   e 2027.* Non trovata (sez. 6b). Aprire l'indice API di ciascuna versione con
   un browser normale e cercare "view", "viewport", "camera". Se non esiste, il
   passo 1 della v1 resta manuale per sempre.
7. **Esiste un modo di avviare l'esportazione dell'immagine dal plugin** — *2026
   e 2027.* Non trovato. Se non esiste, come sopra.
8. **Come osservare una cartella dentro una palette** — *2026 e 2027.* Nessuna
   funzione dedicata trovata. Da provare: un thread con polling (compromesso in
   `WATCH_FOLDER_POLL_SECONDS`, da definire) dentro una palette PythonPart:
   regge? si ferma alla chiusura della palette?
9. **La documentazione SDK 2027 differisce dalla 2026 in modo che tocca il
   progetto** — *2027.* Non ho potuto aprirla.

### C · Interprete Python

10. **Versione di Python** — *2026:* 3.13.9 dopo l'hotfix 2026-0-3 [snippet];
    *2027:* non trovata. Verifica: nella console Python di Allplan, `import sys;
    print(sys.version)`, su entrambe.
11. **`requests` disponibile** — *2026 e 2027.* Vedi sez. 6c. Non blocca il
    motore (usa `urllib`). Serve solo se un giorno la palette lo userà.
12. **Pillow disponibile o installabile** — *2026 e 2027.* Verifica: `import PIL`
    nella console Python di Allplan. Se manca, provare `InstallPythonPackage`
    (percorso di versione precedente, sez. 6c). Se non si può installare: si
    riscrive `core/immagine.py` e basta, il resto del motore parla solo di byte
    e numeri.

### D · Plugin Manager e ALLEP

13. **L'installazione del pacchetto ALLEP dal Plugin Manager funziona** — *2026
    e 2027, macchina reale.* Nessun pacchetto esiste ancora.
14. **Differenze di installazione 2026 ↔ 2027** — non trovate. Verifica: stessa
    procedura di ROADMAP fase 6 su entrambe.
15. **La palette regge una griglia di 12+ miniature senza rallentare** — *2026 e
    2027,* solo a video.

### E · Provider

16. **L'API Magnific risponde alle chiamate che il motore fa** — l'endpoint
    `POST https://api.magnific.com/v1/ai/mystic` e l'intestazione
    `x-magnific-api-key` sono nel codice [visto]; risposta vera: **mai ottenuta**.
    Il motore non ha mai inviato nulla. Per verificare: una chiave in
    `MAGNIFIC_API_KEY` e `python -m core.cli --image vista.png --preset base`.
17. **Accesso a Magnific a consumo, senza piano Business/Enterprise** — *fonti
    recenti dicono di no* (sez. 6e). Verifica: cruscotto dell'account Magnific,
    sezione API. Se serve un piano a canone: il costo entra nel calcolo prima di
    ROADMAP fase 2.
18. **Il riferimento strutturale tiene la geometria di un edificio** — *mai
    misurato.* Per verificare: stessa vista shaded a forza 50, 70, 90 e occhio
    umano sugli spigoli (ROADMAP fase 2). Finché non è fatto,
    `FORZA_STRUTTURA_PREDEFINITA = 70` resta SCELTA e l'interfaccia lo scrive.
19. **`fixed_generation` basta a rifare la stessa immagine** — non verificato.
    La ricetta salva modello e versione del preset perché non ci fidiamo.
20. **La grana corrisponde a `creative_detailing`** — i tre valori (20 / 45 /
    75) sono scelti; la corrispondenza è un'ipotesi. Verifica: stessa vista,
    tre livelli, occhio su una facciata in mattoni.
21. **I formati accettati dal servizio sono quelli che il motore conosce** —
    elenco nel codice, mai confrontato con la pagina ufficiale.
22. **Le condizioni dei provider consentono la rivendita** — non lette.
    Rimandato: rivendita fuori dalla v1.

### F · Contenuto vecchio riclassificato

23. **Ragioni del vecchio PRD che nessuna fonte qui sopra conferma:** "ComfyUI
    richiede abbonamento attivo", "Weavy senza API pubblica", "Krea con API
    fatturata a parte e senza controllo strutturale", "il nodo VS non ha UI
    persistente", "la macchina ha 4 GB di VRAM". Le **decisioni** restano; le
    **ragioni** vanno riverificate prima di rimettere in gioco quei candidati.
24. **Stima di profondità "buona su viste shaded pulite, degrada su wireframe"**
    (vecchio PRD, sez. 6) — nessuna misura nostra dietro.
25. **README.md, DESIGN.md e FIRST-SESSION.md non sono stati toccati** (fuori dal
    compito di questa sessione) e contengono affermazioni ora superate:
    "Non supporta Allplan sotto la 2026", "cartella sorvegliata" come metodo
    unico, "Allplan 2026 come minimo", nome dell'esportazione non verificato.
    Da riallineare in una sessione a parte.

## 10 · Tagliato

- **ID map esportata da Allplan** — tagliata il 2026-09-14: chiede all'utente un
  lavoro che la segmentazione a valle fa da sola.
- **Screenshot a schermo intero con Pillow** — tagliato il 2026-09-14:
  l'esportazione nativa è preferibile (esiste nelle versioni precedenti; sul
  2026/2027 da verificare, vedi 9.A).
- **Krea come motore v1** — tagliato il 2026-09-14. *Ragione non verificata (9.23).*
- **ComfyUI locale** — tagliato il 2026-09-14. *Ragione (VRAM) non verificata (9.23).*
- **Abbonamento Comfy Cloud per l'MVP** — tagliato il 2026-09-14. *Ragione non
  verificata (9.23).* "Comfy Serverless" torna come motore v2 (ROADMAP, dopo).
- **Supporto a una sola versione di Allplan** — tagliato il 2026-09-30:
  2026 e 2027 insieme [utente].

## 11 · Target e limiti

**Target:** plugin desktop per Allplan **2026 e 2027**. PythonPart (palette) in
pacchetto ALLEP, installato dal Plugin Manager [piano; installazione **non
verificata**, sez. 9.13]. Un adattatore per versione, un motore in Python puro.
**Scartati:** nodo Visual Scripting (ragione da riverificare); applicazione web
separata.

**Accettiamo di non poter:**
- girare fuori da Windows — Allplan è solo Windows *(dichiarato dal vecchio PRD, non
  ricontrollato)*;
- evitare un porting all'anno: per questo l'adattatore è un file per versione;
- funzionare offline — la generazione è remota;
- garantire che le immagini non lascino la macchina: per questo l'interfaccia
  dice sempre dove va l'immagine prima dell'invio.

## 12 · Schermate

Dettaglio in `DESIGN.md` (non toccato in questa sessione; vedi 9.25).

| Schermata | Lavoro che serve | Lo stato vuoto dice |
|---|---|---|
| Palette — Sorgente | Trovare e mostrare l'immagine esportata | "Esporta la vista da Allplan nella cartella X. La cerco io." |
| Palette — Stile | Scegliere il preset dalla griglia | Mai vuota: i preset sono nel pacchetto |
| Palette — Risultato | Confrontare partenza e render, decidere | "Nessun render ancora. Scegli uno stile e premi Genera." |
| Palette — Materiali | Cambiare una superficie *(fase 5)* | "Clicca una superficie del render, o scrivi come si chiama." |
| Palette — Livelli | Rifare un livello *(fase 5)* | Non compare finché non esiste un render |
