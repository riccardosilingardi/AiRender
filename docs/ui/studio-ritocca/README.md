# Studio · Ritocca — screenshot degli stati

Fatti il 2026-10-30 con Playwright (Chromium, Linux), tema scuro salvo `59`,
a 1440 px di larghezza (pagina intera) e a 1280×800 (`-1280x800`, solo quello
che si vede senza scorrere). Le aree sono disegnate con il mouse vero
(Playwright muove il puntatore), non scritte nello stato della pagina.

**I «render» non sono render.** Server, coda, albero e pagina sono quelli
veri; il provider è finto: ha le destinazioni di Comfy Router ma non esce in
rete. Un render dalla vista è la vista tinta con Pillow. Un ritocco è il
render di partenza scurito **solo dentro le aree**: è un finto «modello che
rispetta le aree», per questo in `56` la misura fuori dalle aree dà 0,0. Non
dice niente di come lavora Nano Banana 2: quello lo dice il piano «aree» del
banco di prova. L'errore di `57` è simulato (crediti finiti).

Le aree partono come **contorni** (`RITOCCO_MODO_AREE`, scelta provvisoria).
L'albero che ne è uscito è `esempio-ritocco.passi.json`.

| File | Stato |
|---|---|
| 50 | vuoto: nessun render, strumenti spenti con la ragione, «Prima serve un render. Generane uno da Genera.» |
| 51 | un render, nessuna area: strumenti accesi, Applica spento con la ragione |
| 52 | un rettangolo appena chiuso: la nota attaccata, da scrivere, e la ragione accanto |
| 53 | pieno: rettangolo e selezione libera, due note, elenco, prompt aperto, destinazione e costo di un invio |
| 54 | errore: un'area senza nota ferma Applica e lo dice accanto a quella nota |
| 55 | in corso: aree e note bloccate, striscia con servizio, stato, tempo e Annulla |
| 56 | risultato: prima/dopo contro il render ritoccato, misura fuori dalle aree, note applicate |
| 57 | errore: invio non riuscito, aree e note restano come erano, Applica le rimanda |
| 58 | Passi: il ritocco è il passo 2, figlio dell'1, con aree, modo e misura nella ricetta |
| 59 | pieno, tema chiaro |

## Pennello nuovo, 2026-11-12 (`60`-`67`, JPEG)

Stesso metodo (Studio vero, provider finto, mouse vero di Playwright), a
1440×900. Il render è una foto d'esempio; il «ritocco» la scurisce, e lo
Studio la incolla solo nelle aree.

| File | Stato |
|---|---|
| 60 | vuoto: un render, nessuna area, la tela dice cosa fare |
| 61 | mentre dipingi: due tratti, un'area sola (@1), cerchio del pennello |
| 62 | pieno: Cambia (due tratti), Aggiungi con la gomma, Togli col lazo |
| 63 | zoom al 231% |
| 64 | errore: l'area 1 non è nel testo, Applica fermo con la ragione |
| 65 | in corso: aree e testo bloccati, striscia con Annulla |
| 66 | risultato: prima/dopo, fuori dalle aree com'era prima |
| 67 | Popola · Dipingo io: due tratti verdi, un'area |
