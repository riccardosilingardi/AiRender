# Adattatori Allplan

`comune/ponte.py` non importa Allplan e si prova con `pytest`. Ogni versione di
Allplan ha la sua cartella (`v2026/`, poi `v2027/`) con l'unico file che
importa `NemAll_Python_*`.

## Allplan 2027: pacchetto plugin e installazione

`v2027/pacchetto/` e' AIRENDER nel formato plugin della 2027 (`.allep`):
`install-config.yml`, `requirements.in` (Pillow), il `.pyp`, l'adattatore e le
icone dell'Actionbar, con la disposizione del PythonParts SDK 3.0.0
(`PythonPartsScripts/<sviluppatore>/<plugin>/`). L'adattatore e' la copia di
quello 2026 (un test lo tiene uguale), il `.pyp` lo scrive
`v2027/scrivi_palette_pyp.py`.

    python allplan/v2027/pacchetto.py              # dist/AIRENDER-2027.allep
    python allplan/v2027/pacchetto.py --installa   # copia nella Usr della 2027

`--installa` trova la Usr, copia gli stessi file dell'.allep e toglie le
prove della 2026 (AIRENDER prova e sonda). Passi per Riccardo:
[`docs/installa-2027.md`](../docs/installa-2027.md).

## La palette v1: `AIRENDER` (Allplan 2026, prompt 7)

Il telecomando di `DESIGN.md`: Vista, Stile, Invio, Ultimo render. Genera non
blocca Allplan: scrive un lavoro nella coda e torna. Se sulla cartella non
gira una coda, la palette avvia lo Studio senza finestra, che la fa partire.
Logica in `comune/telecomando.py` (pytest), Allplan solo in
`v2026/PythonPartsScripts/airender/AirenderPalette.py`. Il `.pyp` si genera:
dopo un cambio dei blocchi, `python allplan/v2026/scrivi_palette_pyp.py`.

Come provarla, la prima volta (mai aperta in Allplan prima):

1. Rilancia `installa.ps1`, riavvia Allplan.
2. Libreria › Privato › AIRENDER › **AIRENDER**. Se non si apre, copia il
   messaggio della finestra *Trace*.
3. Clicca nella finestra 3D, **Cattura vista**: in Vista compaiono nome,
   dimensioni ed esito.
4. In Stile cambia **Modello**: «La vista va a» e Costo cambiano subito, o
   solo al clic successivo? Scrivimelo.
5. **Prova a secco**: finestra con destinazione, costo e prompt.
6. Solo se vuoi spendere (circa 17 crediti, `COMFY_API_KEY` impostata):
   **Genera render**. Allplan deve restare libero subito; Stato dice «In
   corso da…», Genera diventa Annulla. Premi **Aggiorna** ogni tanto.
7. **Apri nello Studio**: si apre la finestra dello Studio sulla stessa
   cartella?

Da rimandare: uno screenshot della palette dopo il punto 3 e dopo il punto 6,
il testo delle finestre di messaggio e qualunque errore della *Trace*.

## `AIRENDER prova` (Allplan 2026)

Una palette minima, per verificare sulla macchina vera le tre cose che nessuna
sessione può verificare da qui:

1. **Cattura vista** salva la finestra attiva in PNG con
   `DrawingService.SaveWindowToImageFile` (alla dimensione della finestra o a
   quella scelta), e accanto un `.camera.json` con occhio, punto guardato e tipo
   di proiezione letti da `GetViewWorldProjection()`.
2. **Prova a secco** passa la vista al motore, che la giudica (wireframe? piatta?)
   e dice cosa partirebbe e verso quale servizio, senza inviare niente.
3. **Genera render** invia davvero, con la chiave in `COMFY_API_KEY`.

## Come provarla (Allplan 2026)

1. **Pillow.** Barra PythonParts SDK › *Install Python Package* › pacchetto
   `pillow`, destinazione `USR` › Install. Annota dove compare la cartella
   `PythonParts-site-packages`: chi la contiene è la tua cartella Usr.
2. **Copia.** In PowerShell, dalla cartella del repository:
   `powershell -ExecutionPolicy Bypass -File allplan\v2026\installa.ps1`
   (aggiungi `-Usr "<cartella Usr>"` se non è quella predefinita).
3. **Riavvia Allplan**, apri un modello, metti una finestra in prospettiva
   centrale, shaded con ombre.
4. Libreria › Privato › AIRENDER › **AIRENDER prova**.
5. Clicca una volta nella finestra 3D, poi **Cattura vista**. Ripeti con la
   finestra *Animazione* aperta e attiva.
6. **Prova a secco.**
7. Solo se vuoi spendere: imposta `COMFY_API_KEY` come variabile d'ambiente
   utente di Windows, riavvia Allplan, **Genera render**. Durante l'attesa
   Allplan resta bloccato: è voluto in questa prova, non nel prodotto.

## Cosa rimandare indietro

- Il PNG catturato dalla finestra normale e quello dalla finestra Animazione.
- I due `.camera.json`.
- Il testo della finestra di messaggio di **Prova a secco**.
- Qualunque errore della finestra *Trace* di Allplan.

## La sonda: `AIRENDER sonda` (2026-10-27)

Una seconda palette usa e getta, per sapere sul PC vero se la palette nuova e lo
Studio si possono fare come nel piano UI. Si installa con lo stesso
`installa.ps1` e compare accanto ad *AIRENDER prova*.

1. Rilancia `installa.ps1`, riavvia Allplan.
2. Libreria › Privato › AIRENDER › **AIRENDER sonda**.
3. **1 · Cambia immagine**, due o tre volte. Guarda quali delle due immagini in
   alto cambiano lettera (A/B): la prima, la seconda, nessuna.
4. **2 · Miniature**: si vedono cinque immagini o caselle vuote? Clicca la terza,
   poi **Registra la scelta**.
5. **3 · Trova Python**, poi **Avvia processo**. Per mezzo minuto gira il
   modello e zooma: Allplan risponde?
6. **5 · Controlla processo**: deve dire *vivo* con un numero di battiti.
7. **4 · Apri in Edge**: si apre una finestra senza barra degli indirizzi, con
   un numero che sale?
8. Chiudi la palette, riaprila, **Controlla processo** di nuovo: il processo è
   ancora vivo?
9. **Riepilogo**.

Da rimandare: il file `Usr\Local\AIRENDER\sonda\risultati-sonda.txt`, uno
screenshot della palette dopo il punto 4, uno della finestra di Edge, e a parole
se Allplan rispondeva al punto 5. Il processo di prova si spegne da solo dopo
tre minuti.
