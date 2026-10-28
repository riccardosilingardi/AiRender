# Studio v1 — screenshot degli stati

Fatti il 2026-10-28 con Playwright (Chromium, Linux), tema scuro salvo
`02b`, a 1440 px di larghezza (pagina intera) e a 1280×800 (`-1280x800`,
solo quello che si vede senza scorrere).

**I «render» non sono render.** Il server, la coda e la pagina sono quelli
veri; il provider è finto: ha le destinazioni di Comfy Router ma non esce in
rete, e restituisce la vista colorata con Pillow (1376×768 per «Nano Banana
2», 1392×752 per «Kontext», come le misure della sonda del 2026-10-27).
L'errore di `08` e `18` è simulato (crediti finiti).

| File | Schermata | Stato |
|---|---|---|
| 01 | Genera | vuoto: nessuna vista nella cartella |
| 02, 02b | Genera | pieno (scuro, chiaro) |
| 03 | Genera | pieno, prompt completo aperto |
| 04 | Genera | prova a secco |
| 05 | Genera | errore: vista non adatta (wireframe) |
| 06 | Genera | in corso |
| 07 | Genera | FLUX.1 Kontext Pro: costo non misurato |
| 08 | Genera | errore: invio fallito |
| 09 | Genera | interno |
| 10 | Risultato | vuoto |
| 11 | Risultato | in corso |
| 12, 13 | Risultato | pieno, prima/dopo; linea spostata con le frecce |
| 14, 15 | Risultato | affiancati; solo render |
| 16 | Risultato | Rifai, la conferma con destinazione e costo |
| 17 | Risultato | confronto fra due render della stessa vista (A/B fra modelli) |
| 18 | Risultato | errore |
| 20, 21 | Ritocca | vuoto; anteprime in grigio |
