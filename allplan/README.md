# Adattatori Allplan

`comune/ponte.py` non importa Allplan e si prova con `pytest`. Ogni versione di
Allplan ha la sua cartella (`v2026/`, poi `v2027/`) con l'unico file che
importa `NemAll_Python_*`.

## Cosa c'è adesso: `AIRENDER prova` (Allplan 2026)

Una palette minima, per verificare sulla macchina vera le tre cose che nessuna
sessione può verificare da qui:

1. **Cattura vista** salva la finestra attiva in PNG con
   `DrawingService.SaveWindowToImageFile` (alla dimensione della finestra o a
   quella scelta), e accanto un `.camera.json` con occhio, punto guardato e tipo
   di proiezione letti da `GetViewWorldProjection()`.
2. **Prova a secco** passa la vista al motore, che la giudica (wireframe? piatta?)
   e dice cosa partirebbe e verso quale servizio, senza inviare niente.
3. **Genera render** invia davvero, con la chiave in `MAGNIFIC_API_KEY`.

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
7. Solo se vuoi spendere: imposta `MAGNIFIC_API_KEY` come variabile d'ambiente
   utente di Windows, riavvia Allplan, **Genera render**. Durante l'attesa
   Allplan resta bloccato: è voluto in questa prova, non nel prodotto.

## Cosa rimandare indietro

- Il PNG catturato dalla finestra normale e quello dalla finestra Animazione.
- I due `.camera.json`.
- Il testo della finestra di messaggio di **Prova a secco**.
- Qualunque errore della finestra *Trace* di Allplan.
