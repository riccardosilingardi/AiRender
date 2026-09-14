# Regole di lavoro per questo repository

Leggi questo prima di toccare qualunque cosa. Ogni sessione di Claude Code
comincia da qui.

---

## Non negoziabili

1. **Il motore non sa che Allplan esiste.** Nessun import di `NemAll_Python_*`
   fuori dalla cartella dell'adattatore. Motivo: il motore deve essere
   eseguibile e testabile da riga di comando, su qualunque macchina, senza CAD.
   È l'unica cosa che rende misurabile questo progetto.
2. **Un file di adattatore per versione di Allplan.** Percorsi, schema della
   palette e chiamate specifiche stanno lì e solo lì. Allplan esce una volta
   all'anno: il porting deve costare mezza giornata, non una riscrittura.
3. **Mai stampare un valore incerto come se fosse certo.** Se lo scostamento
   della geometria non si è potuto misurare, l'interfaccia scrive che non si è
   potuto misurare. Un trattino batte un numero sbagliato.
4. **Mai una chiave nel repository.** Né nel codice, né nei preset, né nei
   favoriti del `.pyp`. La chiave vive in una variabile d'ambiente o in un file
   utente fuori dal repo, ed è del cliente.
5. **Nessuna immagine parte senza che l'interfaccia abbia detto dove va.** Il
   nome del servizio destinatario è visibile prima dell'invio, non nei termini.

## Dove vivono le decisioni

Ogni soglia, peso e limite sta in **`core/config.py`**, in un posto solo, con la
ragione nel commento accanto. Un numero che compare in due file prima o poi
diverge, e la divergenza non viene notata.

| Costante | Valore | Misurata o scelta? | Ragionamento |
|---|---|---|---|
| `STRUCTURE_STRENGTH_DEFAULT` | da definire | **scelta**, in attesa del test | Sarà misurata confrontando 50/70/90 |
| `GEOMETRY_DRIFT_WARN` | da definire | **scelta** | Sopra questa soglia l'interfaccia avvisa |
| `WATCH_FOLDER_POLL_SECONDS` | da definire | scelta | Compromesso fra reattività e CPU |
| `MASK_FEATHER_PX` | da definire | scelta | Sfumatura del bordo maschera |

Segna ogni costante onestamente. Un numero **scelto** è un giudizio e va
etichettato come tale anche a schermo, non solo qui.

## Trappole note

Cresce col progetto. Dopo un mese sarà la sezione più preziosa del repository.

- **La segmentazione segue l'apparenza, non il modello.** Due materiali resi
  simili diventano una regione sola. Non trattare mai la maschera come verità:
  servono sempre i comandi aggiungi area / togli area.
- **Il riempimento mascherato non ricalcola riflessi e luce di rimbalzo.** Per
  cambi radicali di materiale serve la modalità variante, non il ritocco.
- **Il seed da solo non basta a rendere riproducibile un livello.** Vanno
  salvati anche modello, versione del preset e tutti i parametri: i provider
  cambiano i modelli sotto lo stesso nome.

## Come parla l'interfaccia

- Lingua semplice. Un termine tecnico si spiega la prima volta che compare,
  nella stessa frase.
- Un rifiuto si spiega da solo. "Questa vista è un wireframe, serve una vista
  shaded con le ombre" è una risposta; una schermata vuota no.
- Si dice la stessa cosa sempre allo stesso modo. Un solo arrotondamento, una
  sola formulazione.
- Mai suggerire una certezza che il prodotto non ha. In particolare: **grana**,
  mai **scala**.

## Stile di lavoro

- **Prima si aggiusta.** Ogni sessione apre chiudendo quello che la precedente
  ha lasciato rotto, non verificato o a metà.
- **Prima il piano, poi il codice.**
- **Una prompt, un PR, una sessione.** Niente "già che ci sono".
- **Dichiara cosa NON hai verificato.** Ogni sessione finisce così, e la voce
  entra nella sezione NON VERIFICATO del PRD.
- **Non toccare codice funzionante che non c'entra col compito.**

## Verifiche che deve fare l'umano

Alcune cose nessuna sessione può controllarle. Quando ne lasci una, di'
esattamente: cosa aprire, cosa rimandare indietro, cosa significherebbe.

- **Installazione del pacchetto ALLEP dal Plugin Manager** — serve una macchina
  con Allplan 2026.
- **Tenuta della geometria** — servono due immagini affiancate e un occhio
  umano sugli spigoli.
- **Comportamento della griglia di miniature nella palette** — solo a video.

## Design

`DESIGN.md` contiene i quattro stati (vuoto, in corso, errore, pieno) di ogni
schermata. Non inventare una schermata che non c'è dentro: chiedi. Mai riempire
uno stato vuoto con dati finti per farlo sembrare finito.

## Come si chiude una sessione

Quattro righe, non di più: cosa è successo, i tre file che contano, una cosa che
la persona può cambiare senza rischio, una cosa che non deve toccare e cosa si
rompe se lo fa.
