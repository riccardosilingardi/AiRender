# Studio · Passi — screenshot degli stati

Fatti il 2026-10-30 con Playwright (Chromium, Linux), tema scuro salvo `38`,
a 1440 px di larghezza (pagina intera) e a 1280×800 (`-1280x800`, solo quello
che si vede senza scorrere).

**I «render» non sono render.** Server, coda, albero e pagina sono quelli
veri; il provider è finto: ha le destinazioni di Comfy Router ma non esce in
rete, e restituisce l'immagine che riceve tinta con Pillow (la vista per un
passo dalla vista, il render del passo prima per un passo su un render). Per
questo i passi si somigliano: non dicono niente di come lavora il modello.
L'errore di `37` è simulato (crediti finiti); in `39` il render del passo 2
è stato cancellato a mano.

L'albero è quello del mockup `Passi.dc.html`: 1 dalla vista, 2 dal 1, 3 e 4
dal 2 (un ramo), 5 dalla vista con FLUX.1 Kontext Pro; poi 6 dal 3, non
riuscito. Il file dell'albero che ne è uscito è `esempio-vista.passi.json`.

| File | Stato |
|---|---|
| 30 | vuoto: solo la riga 0 e «Nessun passo ancora» |
| 31 | in corso: il passo 2 nasce sotto l'1, con la striscia nella colonna |
| 32 | pieno: passo 4 contro la vista Allplan, strada 0 › 1 › 2 › 4, avviso della 3ª generazione |
| 33 | pieno: contro il passo prima, affiancati |
| 34 | Nuovo passo da qui sul passo 2 (apre un ramo), con il prompt che parte |
| 35 | Rifai pulito dalla vista: strada, richieste, prompt, destinazione e costo prima dell'invio |
| 36 | Rifai questo passo: la conferma con destinazione e costo |
| 37 | errore: passo non riuscito |
| 38 | pieno, tema chiaro |
| 39 | errore: il punto di partenza non c'è più |
| 40 | il passo 0 scelto: la vista da sola |
| 41 | Risultato con i lavori dei passi nell'elenco |
