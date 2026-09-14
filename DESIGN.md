# AIRENDER — Design

Documento vivo, come il PRD. Si aggiorna ogni volta che una schermata cambia.

> Nota: l'interfaccia vive dentro la palette di Allplan. I colori, i font e le
> spaziature li decide Allplan, non noi — inclusa la modalità scura. Quello che
> decidiamo è **cosa c'è, in che ordine, e cosa dice quando non c'è niente.**

## Vincoli ereditati

- Contenitore: palette Allplan 2026, larghezza stretta e variabile.
- Elementi disponibili: expander annidati, immagini ridimensionabili, griglia di
  pulsanti-immagine, barra di avanzamento, testo, slider, pulsanti.
- La palette deve restare usabile mentre una generazione è in corso.

## Schermate

### 1 — Sorgente

- **Vuoto:** "Salva una vista da Allplan in questa cartella e la trovo io." Con
  il percorso visibile e un pulsante per cambiarlo. Nessun pulsante Genera.
- **In corso:** miniatura della vista trovata, con nome file e ora.
- **Errore:** "Questa sembra una vista wireframe. Serve una vista shaded con le
  ombre attive, sfondo neutro." Con l'immagine comunque mostrata: l'utente deve
  vedere cosa è stato scartato e perché.
- **Pieno:** miniatura, dimensioni in pixel, e un solo pulsante per sostituirla.

### 2 — Stile

- **Vuoto:** non esiste. I preset sono inclusi nel pacchetto.
- **Pieno:** griglia di miniature. Ogni miniatura è generata eseguendo il preset
  stesso su una scena di prova standard, quindi mostra il risultato reale, non
  un'illustrazione. Sotto: una riga di testo libero, e lo slider della **grana**.
- **Errore:** un preset il cui modello non è più disponibile appare in grigio con
  la ragione, non sparisce.

### 3 — Risultato

- **Vuoto:** "Nessun render ancora. Scegli uno stile e premi Genera."
- **In corso:** barra di avanzamento con il tempo trascorso e il nome del
  servizio che sta lavorando. Annullabile.
- **Errore:** il messaggio del provider tradotto in una frase utile, più cosa
  fare adesso. Mai un codice HTTP da solo.
- **Pieno:** vista di partenza e render affiancati, e l'indicatore di
  scostamento della geometria. Se lo scostamento non si è potuto misurare,
  scritto a parole, non un numero inventato.

### 4 — Materiali

- **Vuoto:** "Clicca una superficie del render, oppure scrivi come si chiama."
- **In corso:** la maschera evidenziata sull'immagine mentre si calcola.
- **Errore:** "Non ho trovato quella superficie. Prova a cliccarla."
- **Pieno:** maschera visibile con aggiungi area / togli area, scelta del nuovo
  materiale fra preset o testo libero, slider della grana. Un solo pulsante
  Applica, che sceglie da sé fra ritocco e variante in base a quanto è radicale
  il cambio, e **dice quale delle due sta usando**.

### 5 — Livelli

- **Vuoto:** non compare finché non esiste un render.
- **Pieno:** elenco dei livelli dal basso, ognuno con stile, testo e data.
  Ogni livello si rifà da solo. L'ultima riga è sempre il risultato corrente.

## Decisioni visive

- Scelta: vista di partenza e render **affiancati**, non in sovrapposizione —
  perché la decisione che l'utente deve prendere è "è ancora il mio edificio?",
  e si prende confrontando, non alternando.
- Scelta: le miniature sono generate, non disegnate — perché una miniatura che
  promette più di quello che il preset produce è la prima causa di sfiducia.
- Scartata: anteprima in tempo reale mentre si scrive il prompt — costa una
  chiamata a ogni tasto e il pubblico paga a consumo.

## Verifiche di accessibilità

- [ ] leggibile in modalità scura e chiara, entrambe ereditate da Allplan
- [ ] nessuna informazione affidata al solo colore (lo scostamento geometria ha
      anche un'etichetta testuale)
- [ ] la palette resta usabile a larghezza minima
- [ ] i testi non vengono tagliati quando si allarga il carattere di sistema

## Non ancora progettato

- Schermata di configurazione della chiave API e del tetto di spesa.
- Esportazione finale (formati, risoluzione, dove salva).
- Qualunque cosa riguardi il video.
