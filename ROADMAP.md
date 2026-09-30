# AIRENDER — Roadmap

Ultimo aggiornamento: 2026-09-30.

Ogni fase ha un **criterio di uscita verificabile**: una cosa che si può
eseguire o guardare e che dice sì o no. Una fase non è chiusa finché il criterio
non è soddisfatto **e** le voci NON VERIFICATO che la riguardano sono aggiornate
(`PRD.md`, sezione 9).

**Versioni:** Allplan 2026 e Allplan 2027, entrambe fin dalla v1. Ogni verifica su
Allplan la fa il proprietario **su tutte e due**; una fase che tocca Allplan non
si chiude con una versione sola.

**Ordine:** le fasi sono in sequenza. Una fase non parte finché la precedente non
ha chiuso il suo criterio, salvo dove è scritto.

**Stato al 2026-09-30:** fase 0 in chiusura con questa sessione. La fase 1 è già
in gran parte scritta (sessione precedente) ma **il suo criterio di uscita non è
stato ricontrollato per intero**: vedi fase 1.

---

## Fase 0 — Documenti

**Obiettivo.** Un progetto che sa cosa sa e cosa non sa.

**Cosa produce.** `PRD.md`, `CLAUDE.md`, `ROADMAP.md` riscritti da zero il
2026-09-30, con ogni fatto esterno etichettato per fonte e ogni buco in NON
VERIFICATO.

**Come si verifica (criterio di uscita).**
- I tre file esistono, il PRD ha le 12 sezioni, e ogni voce di NON VERIFICATO
  dice a quale versione di Allplan si riferisce.
- Ogni fatto su Allplan, SDK o provider ha un URL e un'etichetta (`[snippet]`,
  `[utente]`, `[visto]`, `[terzi]`).
- Il proprietario ha risposto alle DOMANDE della sessione.

**Limite noto di questa fase.** Il proxy della sessione ha bloccato i domini
primari (help.allplan.com, pythonparts.allplan.com, allplan.com, GitHub
Allplan, docs.magnific.com): quasi tutte le voci del passo 2 sono rimaste NON
VERIFICATO. La **fase 0b**, sotto, è la sessione che le chiude.

**Cosa NON entra.** Codice. Correzione di README, DESIGN, FIRST-SESSION (PRD 9.25).

### Fase 0b — Chiudere le verifiche di documentazione *(da fare prima della fase 3)*

**Obiettivo.** Trasformare i `[snippet]` e i "non trovato" in fatti letti.

**Cosa produce.** Aggiornamento di PRD sezioni 4, 6, 9 con pagine **lette**.
Due modi: (a) una sessione con accesso di rete ai domini Allplan e Magnific
(impostazione del proprietario, non di Claude); (b) il proprietario incolla il
testo delle pagine. In entrambi i casi, per **2026 e 2027**:
- pagina di help su "Salva, carica inquadratura" (nome, cosa salva, come si ripristina);
- pagina di help sull'esportazione dell'immagine della finestra (risoluzione, formati);
- indice API `InterfaceStubs` e pagina Eventi dell'SDK;
- note di rilascio SDK (Python, `requests`, Pillow);
- pagine Plugin Manager / ALLEP;
- pagina Mystic e piani/prezzi API di Magnific, e i termini di servizio.

**Come si verifica.** Le tabelle 6a–6e del PRD non contengono più "non trovato"
per motivi di accesso: o hanno il fatto con URL letto, o "non esiste" con la
prova (indice consultato).

**Cosa NON entra.** Prove su macchina con Allplan. Chiamate al provider.

---

## Fase 1 — Motore in Python puro con CLI

**Obiettivo.** Il motore genera un render da una vista, da riga di comando, senza
Allplan, con un provider sostituibile, una config unica, e test con rete simulata.

**Cosa produce.** `core/` (CLI, provider, config, idoneità, lessico, ricetta,
errori), `tests/`. **Nessun import Allplan.**

**Come si verifica (criterio di uscita).**
1. `pytest` verde su una macchina pulita, senza chiave e senza rete.
2. `grep -r NemAll_Python core/` non trova import.
3. `python -m core.cli --image vista.png --preset base --prova-a-secco` stampa
   il servizio destinatario e non invia niente.
4. `python -m core.cli --image vista_wireframe.png --preset base --prova-a-secco`
   rifiuta e spiega cosa risalvare.
5. Ogni costante in `core/config.py` ha origine e ragione; un test impedisce
   numeri cablati altrove.
6. Il provider si sostituisce aggiungendo un file e una riga nel registro
   (mostrato con un provider finto nei test).

**Stato al 2026-09-30.** Punti 1, 3, 4 **visti** oggi (67 passati; prova a secco
su immagini sintetiche). Punti 2, 5, 6 sono coperti da test che passano, ma non
li ho rieseguiti a mano uno per uno. **Aperto:** il punto "rete simulata" non è
stato provato con la rete davvero staccata; il messaggio di rifiuto nomina un
comando Allplan non verificato (PRD 9.A.3); nessuna chiamata reale al provider
(PRD 9.16). Sono debiti di questa fase e si chiudono a inizio della fase 2.

**Cosa NON entra.** Palette, adattatori, cartella osservata, segmentazione,
livelli.

---

## Fase 2 — Misura della tenuta della geometria

**Obiettivo.** Sapere se il riferimento strutturale tiene gli spigoli di un
edificio, e a quale forza. È ciò che decide se il prodotto esiste.

**Prerequisiti.** Fase 0b chiusa per la parte Magnific (piano, costo, parametri).
Una chiave dell'utente; un budget dichiarato prima di partire. Da 2026-09-30 non
è dimostrato che l'accesso a consumo esista (PRD 9.17).

**Cosa produce.** Una cartella di misura fuori dal repository con: la stessa vista
shaded (esportata da Allplan, su almeno **due viste diverse**, una per
versione: 2026 e 2027) generata a forza **50, 70, 90**, le ricette salvate, le
coppie affiancate. Nel repository: la tabella dei risultati e, se giustificato,
`FORZA_STRUTTURA_PREDEFINITA` aggiornata e passata da SCELTA a MISURATA con la
misura descritta nella ragione. Una soglia di avviso sullo scostamento resta
SCELTA finché non c'è un confronto numerico.

**Come si verifica (criterio di uscita).**
- Per ciascuna vista e ciascuna forza, una coppia affiancata (partenza / render)
  guardata **da un umano** sugli spigoli, con un giudizio scritto (tiene / non
  tiene, dove cede).
- La ricetta di ogni render è salvata e riproduce i parametri.
- Se nessuna forza tiene: la fase si chiude con il verdetto "il motore
  candidato non tiene" e il PRD lo dice, con una decisione su cosa fare
  (secondo provider, Comfy). Non si sceglie un valore per far quadrare il conto.
- Se una forza tiene: la costante è aggiornata e la sua etichetta passa a
  MISURATA con riferimento alla misura. L'interfaccia scrive ancora che lo
  scostamento non è misurato numericamente, se non lo è.

**Serve un umano** a guardare gli spigoli.

**Cosa NON entra.** Metrica automatica di scostamento (può essere una fase
successiva); palette; qualsiasi decisione presa senza aver guardato le
immagini.

---

## Fase 3 — Acquisizione dell'immagine

**Obiettivo.** L'immagine esce da Allplan ed entra nel motore.

**v1 MANUALE** [decisione del proprietario]: l'utente ripristina l'inquadratura
(se serve), esporta l'immagine in una cartella, e il plugin la osserva.

**Cosa produce.**
- Un osservatore di cartella nel lato palette/adattatore (non nel motore).
  Il motore riceve un percorso, non osserva niente.
- Costante dell'intervallo di osservazione in `core/config.py` (SCELTA).
- Testo dell'interfaccia con i nomi **verificati** dei comandi Allplan, per 2026 e 2027.
- **Solo se** la fase 0b dimostra un'API per ripristinare l'inquadratura e
  avviare l'esportazione: il pulsante **"Genera da inquadratura"**. Va provato
  **sia su 2026 sia su 2027**; se funziona su una sola, entra solo per quella
  con un adattatore che lo dichiara e l'altra versione resta manuale.

**Come si verifica (criterio di uscita).**
- **Manuale:** su 2026 e su 2027, l'utente esporta un'immagine nella cartella e
  il plugin la mostra entro un tempo dichiarato, senza riavviare; se il file è
  inadatto, il rifiuto spiega cosa risalvare con il nome **giusto** del comando.
- **Automatico (se entra):** su ciascuna versione, dal pulsante alla comparsa
  dell'immagine nella palette, senza interventi manuali, per tre viste diverse; e
  la vista ripristinata coincide con quella salvata (confronto a occhio, due
  immagini affiancate).
- Se il pulsante non è dimostrato fattibile: la fase chiude con la sola
  acquisizione manuale, e il PRD scrive "automatico: non fattibile o non
  dimostrato" con la ragione.

**Cosa NON entra.** Screenshot dello schermo. Uso di `LibraryBitmapPreview` come
esportazione. Qualsiasi automatismo non dimostrato su entrambe le versioni.

---

## Fase 4 — Palette con griglia di miniature

**Obiettivo.** L'utente sceglie uno stile da una griglia dentro Allplan e preme
Genera (livello "Veras" a comando).

**Cosa produce.** Palette PythonPart con le schermate Sorgente / Stile /
Risultato di `DESIGN.md` (senza Materiali e Livelli); preset base con miniature
**generate** dal preset, non disegnate; **adattatore 2026 e adattatore 2027**,
con la stessa interfaccia verso il motore. L'interfaccia dice il servizio
destinatario prima dell'invio, mostra "valore scelto" dove serve, e i quattro
stati (vuoto, in corso, errore, pieno) di ogni schermata.

**Come si verifica (criterio di uscita).**
- Lo stesso motore, senza modifiche, è chiamato da entrambi gli adattatori
  (`grep` mostra che gli import `NemAll_Python_*` stanno solo nella cartella
  degli adattatori).
- Su 2026 e su 2027: aprire la palette, vedere la vista trovata, scegliere uno
  stile, premere Genera, vedere partenza e render affiancati. Ripetuto su entrambe.
- Lo stato vuoto, in corso, errore, pieno di ogni schermata è stato **visto** a video.
- La griglia di miniature regge 12+ elementi senza rallentare la palette
  (PRD 9.15), a occhio, su entrambe.
- Se le due versioni differiscono: la differenza è scritta nel PRD e sta in un
  adattatore.

**Serve un umano** per tutto ciò che è a video.

**Cosa NON entra.** Segmentazione, livelli, materiali, anteprima live, video.

---

## Fase 5 — Segmentazione, pila di livelli, preset incrementali

**Obiettivo.** Cambiare il materiale di una superficie senza rifare il resto;
salvare una pila di livelli rieseguibile.

**Cosa produce.**
- Segmentazione **a valle sul render** [decisione del proprietario], con comandi
  **aggiungi area / togli area** fin dal primo giorno.
- Due modalità: ritocco (maschera) e variante (rigenerazione). L'interfaccia dice
  quale sta usando.
- Pila di livelli su disco: per ogni livello provider, modello, versione del
  preset, tutti i parametri, seed, impronta dell'immagine di partenza.
- Preset incrementali, uno alla volta, ciascuno con la sua miniatura generata:
  **paesaggio**, poi **persone**, poi **auto**.
- Livello linguistico nel plugin: espansione del testo libero in prompt.

**Come si verifica (criterio di uscita).**
- Su un render vero: cliccare una superficie, correggere la maschera con
  aggiungi/togli, applicare un materiale diverso; il resto dell'immagine è
  invariato (confronto affiancato a occhio).
- Un livello si rifà da solo dalla ricetta; se l'immagine ottenuta non è
  identica, l'interfaccia lo dice.
- Un cambio radicale di materiale sceglie la modalità variante e lo dichiara.
- Ogni preset nuovo entra con la propria misura di tenuta (come fase 2) su una
  vista con quel contenuto, prima di essere abilitato.

**Cosa NON entra.** Segmentazione derivata dal modello Allplan (aggiornamento di
qualità, non prerequisito). Video.

---

## Fase 6 — Pacchetto ALLEP e installazione su macchina reale

**Obiettivo.** Un file che il proprietario installa dal Plugin Manager, e che
funziona.

**Cosa produce.** Un pacchetto `.allep`; una **checklist di prova** scritta,
identica per le due versioni; il resoconto della prova compilato una volta su
**Allplan 2026** e una volta su **Allplan 2027**.

**Come si verifica (criterio di uscita).**
- La checklist è eseguita per intero su 2026 **e** su 2027, con esito scritto per
  ogni riga: installazione, comparsa nel Plugin Manager, apertura della palette,
  prima generazione, disinstallazione pulita, reinstallazione.
- Ogni differenza fra le due versioni è registrata; se ne emerge una che tocca il
  motore, torna alla fase 4 come difetto.
- Nel pacchetto non c'è nessuna chiave (`grep` sul contenuto scompattato).
- Le dipendenze necessarie (Pillow) risultano disponibili o installabili nelle
  due versioni (PRD 9.12).

**Serve un umano** con Allplan 2026 e 2027.

**Cosa NON entra.** Distribuzione ad altri studi. Pubblicazione sul plugin hub.

---

## Fase 7 — Uso reale nello studio, con misure

**Obiettivo.** Sapere se serve davvero.

**Cosa produce.** Un periodo d'uso dichiarato (durata e numero di progetti decisi
all'inizio), con un registro: quante generazioni, quante scartate, quante per
tenuta della geometria, costo per immagine, tempo risparmiato rispetto al
metodo di prima, errori incontrati.

**Come si verifica (criterio di uscita).**
- Il registro esiste e ha numeri, non impressioni.
- Il PRD è aggiornato: le costanti SCELTE che l'uso ha messo alla prova sono
  rivalutate; quelle misurate portano il riferimento.
- Una decisione scritta: continuare, cambiare motore, o fermarsi — con la ragione.

**Cosa NON entra.** Rivendita. Nuovi preset non richiesti dall'uso.

---

## Dopo (non ora, ma scritte)

Ciascuna di queste voci, quando sarà il momento, diventa una fase con il suo
criterio di uscita.

- **Video (Higgsfield, Krea)** come **livello sopra un fermo immagine**, non
  percorso parallelo. Le condizioni e i costi di ciascun servizio vanno
  verificati prima.
- **Anteprima quasi live.** Costa una chiamata a ogni modifica: serve un tetto di
  spesa visibile all'utente e un modo di annullare.
- **Comfy Serverless come motore v2.** Controllo strutturale esplicito; le
  ragioni per cui era stato scartato Comfy in locale e a canone vanno riverificate
  (PRD 9.23).
- **Rivendita, licenza e lettura delle condizioni dei provider.** Prima della
  prima fattura, non dopo (PRD 9.22). Richiede una decisione sul modello
  (chiave del cliente o proxy) e sul repository (privato finché non è decisa la licenza).
- **Allplan 2028 quando esce.** Un terzo adattatore, stesso motore. Il costo di
  quel porting è la misura di se la regola "un file per versione" funziona:
  criterio proposto, mezza giornata.
- **Segmentazione derivata dalle superfici del modello Allplan** (maschere esatte).
- **Nodo Visual Scripting** che chiama lo stesso motore.
- **LoRA di stile addestrati sui render dello studio.**
