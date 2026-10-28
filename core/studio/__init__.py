"""Lo Studio: la pagina locale dove si sceglie lo stile e si guarda il render.

    python -m core.studio --cartella C:\\...\\AIRENDER\\viste

Tre pezzi, tutti con la libreria standard:

- `servizio.py`  quello che lo Studio sa fare, senza HTTP: viste, preset,
  prompt, invio in coda, stato, render, ricetta. Si prova con pytest;
- `server.py`    le rotte JSON e le pagine statiche, solo su 127.0.0.1;
- `pagine/`      la pagina, il foglio di stile e lo script. Niente CDN, niente
  font scaricati: funziona senza internet tranne la generazione.

Lo Studio non chiama il motore: scrive lavori nella coda (core/coda.py) e
legge quello che la coda lascia nella cartella. Per questo funziona anche
con la palette chiusa, e la palette funziona con lo Studio chiuso.
"""
