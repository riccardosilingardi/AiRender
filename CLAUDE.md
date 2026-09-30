# Regole di lavoro per questo repository

Leggi questo prima di toccare qualunque cosa. Ogni sessione di Claude Code
comincia da qui, poi da `PRD.md` (sezione 9, NON VERIFICATO) e `ROADMAP.md`.

Ultimo aggiornamento: 2026-09-30.

---

## Non negoziabili

1. **Il motore non sa che Allplan esiste.** Nessun import di `NemAll_Python_*`
   fuori dalla cartella degli adattatori. Motivo: il motore deve essere
   eseguibile e testabile da riga di comando, su qualunque macchina, senza CAD.
   È l'unica cosa che rende misurabile questo progetto. Un test lo controlla
   già (`tests/test_motore.py`): non rimuoverlo, non aggirarlo.
2. **Un file di adattatore per versione di Allplan, quindi due adattatori: 2026 e
   2027, con lo stesso motore sotto.** Percorsi, schema della palette, chiamate
   all'SDK e differenze fra le due versioni stanno lì e solo lì. Se 2026 e 2027
   differiscono, la differenza sta in un adattatore, mai in un `if versione` nel
   motore. Allplan esce una volta all'anno: il porting deve costare mezza
   giornata, non una riscrittura. *Nome e posizione degli adattatori: da fissare
   in ROADMAP fase 4; finché non esistono, non inventarli.*
3. **Mai stampare un valore incerto come se fosse certo.** Se lo scostamento
   della geometria non si è potuto misurare, l'interfaccia scrive che non si è
   potuto misurare. Un trattino batte un numero sbagliato. Vale anche per
   questo repository: un fatto su Allplan non verificato **non** si scrive come
   fatto, né in un documento né in un messaggio dell'interfaccia.
4. **Mai una chiave nel repository.** Né nel codice, né nei preset, né nei file
   `.pyp`, né nei log, né negli esempi. La chiave vive in una variabile
   d'ambiente (`MAGNIFIC_API_KEY`) o in un file utente fuori dal repo, ed è
   dell'utente.
5. **Nessuna immagine parte senza che l'interfaccia abbia detto dove va.** Il
   nome del servizio destinatario è visibile prima dell'invio, non nei termini.
   La prova a secco (`--prova-a-secco`) resta sempre disponibile e non invia
   niente.

## Dove vivono le decisioni

Ogni soglia, peso e limite sta in **`core/config.py`**, in un posto solo, con la
ragione nel commento accanto. Un numero che compare in due file prima o poi
diverge, e la divergenza non viene notata.

Ogni costante porta la sua provenienza:

- **MISURATA** — viene da una misura ripetibile, descritta nella ragione;
- **SCELTA** — è un giudizio nostro, in attesa di misura;
- **VINCOLO** — non lo decidiamo noi (limite del provider o del formato).
  Esiste già in `core/config.py` (VINCOLO); è una terza etichetta in più
  rispetto alle due richieste: chiamare "scelta" un limite altrui sarebbe una
  bugia. Il valore di un VINCOLO va comunque riletto sulla pagina ufficiale
  (vedi trappole).

Stato al 2026-09-30, letto da `core/config.py`. **Nessuna costante è MISURATA.**

| Costante | Valore | Origine | Ragionamento (riassunto) |
|---|---|---|---|
| `FORZA_STRUTTURA_PREDEFINITA` | 70 | **SCELTA** | Sarà misurata confrontando 50/70/90 (ROADMAP fase 2) |
| `FORZA_STRUTTURA_MINIMA` / `_MASSIMA` | 0 / 100 | VINCOLO | Estremi di `structure_strength`. *Non riletti sulla pagina ufficiale* |
| `LATO_MINIMO_PX` | 512 | **SCELTA** | Sotto, il riferimento strutturale ha poco a cui aggrapparsi |
| `LATO_ANALISI_PX` | 384 | **SCELTA** | Compromesso tempo di analisi / spigoli conservati |
| `TOLLERANZA_SFONDO` | 6 | **SCELTA** | Lo sfondo neutro non è mai esattamente uniforme |
| `QUOTA_SFONDO_MASSIMA` | 0.70 | **SCELTA** | Oltre, è un wireframe. Provata solo su immagini sintetiche |
| `TONI_DISTINTI_MINIMI` | 24 | **SCELTA** | Un wireframe ha pochi grigi. Idem |
| `DEVIAZIONE_LUMINANZA_MINIMA` | 12.0 | **SCELTA** | Sotto, colori pieni senza ombre. Idem |
| `MASCHERA_SFUMATURA_PX` | 3 | **SCELTA** | Un bordo netto lascia la cucitura |
| `GRANA_FINE` / `_MEDIA` / `_GROSSA` | 20 / 45 / 75 | **SCELTA** | Valori di `creative_detailing`; la corrispondenza con la grana percepita è un'ipotesi |
| `TIMEOUT_RETE_SECONDI` | 30 | **SCELTA** | Meglio dire che il servizio non risponde che restare appesi |
| `ATTESA_MASSIMA_SECONDI` | 300 | **SCELTA** | La palette deve poter dire qualcosa |
| `INTERVALLO_ATTESA_SECONDI` | 3 | **SCELTA** | Compromesso reattività / numero di chiamate |
| `INVIO_MASSIMO_MB` | 10 | VINCOLO | Limite dichiarato nel codice. *Non riletto sulla pagina ufficiale* |
| `RISOLUZIONE_PREDEFINITA` | "2k" | **SCELTA** | Costa meno di 4k |

**Costanti ancora da definire** (arrivano con le fasi che le usano; i nomi qui
sono proposte in italiano come le altre, non nomi esistenti): intervallo di
osservazione della cartella (ROADMAP fase 3, SCELTA), soglia di avviso sullo
scostamento della geometria (fase 2, SCELTA finché non c'è una misura).
Segna ogni costante onestamente. Un numero **scelto** è un giudizio e va
etichettato come tale anche a schermo, non solo qui.

## Trappole note

Cresce col progetto. Dopo un mese sarà la sezione più preziosa del repository.

### Del prodotto

- **La segmentazione segue l'apparenza, non il modello.** Due materiali resi
  simili diventano una regione sola. Non trattare mai la maschera come verità:
  servono sempre i comandi aggiungi area / togli area.
- **Il riempimento mascherato non ricalcola riflessi e luce di rimbalzo.** Per
  cambi radicali di materiale serve la modalità variante, non il ritocco.
- **Il seed da solo non basta a rendere riproducibile un livello.** Vanno
  salvati anche modello, versione del preset e tutti i parametri: i provider
  cambiano i modelli sotto lo stesso nome.

### Di Allplan e dell'SDK

- **Inquadratura salvata e immagine esportata sono due oggetti diversi.**
  La prima (secondo il manuale 2015 citato dal proprietario) salva camera,
  prospettiva e scala e **non è un'immagine**: riproduce la vista. La seconda è
  un file: è l'input dell'AI. Non scrivere mai, in codice o interfaccia, che il
  plugin "legge l'inquadratura" se legge un'immagine.
- **"Save, Load Arrangement" non è "Salva, carica inquadratura".** Il primo
  salva la disposizione delle finestre. Cercando nella documentazione si
  trovano pagine sull'uno credendo di leggere dell'altro.
- **Ciò che vale per la 2026 non vale per la 2027 finché non è provato.** Nomi
  dei comandi, versione di Python, pacchetti disponibili, Plugin Manager: ogni
  voce porta la versione a cui si riferisce. Mai "Allplan fa X" senza dire quale.
- **Non citare nei messaggi dell'interfaccia il nome di un comando Allplan non
  verificato.** Oggi `core/idoneita.py` cita "Salva contenuto finestra come
  immagine": nome **non verificato** su 2026/2027 (PRD 9.A.3). Da correggere,
  non da replicare.
- **`LibraryBitmapPreview` non esporta la finestra.** Serve alle miniature della
  libreria. Non usarlo come scorciatoia per l'acquisizione.
- **Il motore deve girare sull'interprete di Allplan.** Allplan 2026 usa Python
  3.13.9 (dopo l'hotfix 2026-0-3); per la 2027 non è noto. Il repository
  si sviluppa e si prova su Python 3.11: non introdurre sintassi o dipendenze
  che non siano verificate su **tutti** gli interpreti in uso. Ogni nuova
  dipendenza va verificata come installabile in Allplan 2026 **e** 2027 prima di
  entrare in `requirements.txt` (oggi: solo Pillow, non verificata).
- **`requests` non è una garanzia.** Distribuito con Allplan a partire da una
  versione ≤ 2025 secondo le note SDK; per 2026/2027 non verificato. Il
  trasporto usa `urllib` apposta.

### Del provider

- **Il provider cambia le condizioni.** Le note recenti dicono che l'accesso a
  consumo di Magnific è stato chiuso il 2026-06-30 (non verificato sulla pagina
  ufficiale). Prima di ogni misura che spende, controlla il piano e il costo.
- **Un limite dichiarato "VINCOLO" non è verificato finché non lo rilegge un
  umano sulla pagina ufficiale.**

### Del metodo

- **Uno snippet di ricerca non è una verifica.** Se non hai letto la pagina, il
  fatto va in NON VERIFICATO con l'etichetta `[snippet]` e l'URL. Se il proxy
  blocca il dominio, dillo: non riempire il buco.
- **Il vecchio contenuto non è una fonte.** Il PRD del 2026-09-14 conteneva fatti
  su Allplan e provider mai verificati. Riclassificati il 2026-09-30.

## Come parla l'interfaccia

- Lingua semplice. Un termine tecnico si spiega la prima volta che compare,
  nella stessa frase.
- Un rifiuto si spiega da solo. "Questa vista è un wireframe, serve una vista
  shaded con le ombre" è una risposta; una schermata vuota no.
- Si dice la stessa cosa sempre allo stesso modo. Un solo arrotondamento, una
  sola formulazione.
- Mai suggerire una certezza che il prodotto non ha. In particolare: **grana**,
  mai **scala** — per le texture dei materiali, in ogni etichetta, messaggio e
  argomento di riga di comando. Il divieto è applicato da `core/lessico.py` sulle
  nostre parole, non sul testo libero dell'utente. Fa eccezione la citazione
  letterale di un nome dell'interfaccia di Allplan (per esempio una scala di
  disegno): si cita com'è, tra virgolette, con la versione. *(Questa eccezione è
  un'interpretazione di questa sessione: se il proprietario la respinge, si
  toglie.)*
- Il servizio destinatario dell'immagine è sempre nominato prima dell'invio.
- Un valore SCELTO si scrive come scelto ("valore scelto, non ancora misurato").

## Stile di lavoro

- **Prima si aggiusta.** Ogni sessione apre chiudendo quello che la precedente
  ha lasciato rotto, non verificato o a metà. Comincia leggendo la sezione
  NON VERIFICATO del PRD.
- **Prima il piano, poi il codice.**
- **Una prompt, un PR, una sessione.** Niente "già che ci sono".
- **Fonti certe o niente.** Documentazione ufficiale Allplan (help.allplan.com,
  versioni 2026 e 2027), SDK (pythonparts.allplan.com, github.com/NemetschekAllplan),
  documentazione dei provider. **URL accanto a ogni fatto.** Se non trovi,
  scrivilo in NON VERIFICATO e chiedilo a fine sessione.
- **Dichiara cosa NON hai verificato.** Ogni sessione finisce così, e la voce
  entra nella sezione NON VERIFICATO del PRD, con la versione di Allplan.
- **In "Costruito" solo ciò che hai visto funzionare.** Con l'output sotto gli
  occhi, non per averlo scritto.
- **Non toccare codice funzionante che non c'entra col compito.**

## Verifiche che deve fare l'umano

Alcune cose nessuna sessione può controllarle. Le verifiche su Allplan le fa il
proprietario **su tutte e due le versioni, 2026 e 2027**. Quando ne lasci una,
di' esattamente: cosa aprire, cosa rimandare indietro, cosa significherebbe.

- **Comportamento di "Salva, carica inquadratura"** e nome esatto dei comandi —
  2026 e 2027.
- **Esportazione dell'immagine**: funzione, risoluzione massima, formati —
  2026 e 2027.
- **Indice dell'API SDK** (`InterfaceStubs`) aperto in un browser normale: cosa
  offre su viste, viewport, bitmap — 2026 e 2027. (Le sessioni Claude possono
  avere il proxy chiuso su questi domini.)
- **Versione di Python, `requests`, Pillow** nella console Python — 2026 e 2027.
- **Installazione del pacchetto ALLEP dal Plugin Manager** — 2026 e 2027.
- **Tenuta della geometria** — due immagini affiancate e un occhio umano sugli
  spigoli.
- **Comportamento della griglia di miniature nella palette** — solo a video,
  2026 e 2027.
- **Piano e costo dell'API del provider** — cruscotto dell'account.

## Design

`DESIGN.md` contiene i quattro stati (vuoto, in corso, errore, pieno) di ogni
schermata. Non inventare una schermata che non c'è dentro: chiedi. Mai riempire
uno stato vuoto con dati finti per farlo sembrare finito. *(Nota: `DESIGN.md` e
`README.md` sono in parte superati rispetto al PRD del 2026-09-30, vedi PRD 9.25.)*

## Come si chiude una sessione

Sempre in questo formato, questa compresa:

```
COSA SI È FATTO: elenco breve e concreto, con i file toccati.
NEXT STEP: una sola cosa, con il prompt della sessione successiva.
DA VERIFICARE: cosa non hai potuto controllare, cosa deve aprire o provare il
  proprietario (e su quale versione di Allplan) e cosa significherebbe il
  risultato. Ogni voce entra anche in PRD.md, sezione NON VERIFICATO.
DOMANDE: solo quelle che non hai potuto risolvere con fonti.
```

Un solo commit sul branch di lavoro e una PR. Mai merge dalla sessione.
