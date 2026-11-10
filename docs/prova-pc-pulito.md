# Provare AIRENDER su un PC pulito (Allplan 2027)

Per Serteco, o per chiunque provi il pacchetto per la prima volta. Serve un PC
Windows con Allplan 2027 e **senza** Python installato a parte: è il caso di
un cliente qualsiasi. Circa quindici minuti.

Si ricevono due cose:

- il file `AIRENDER-2027.allep` (circa 35 MB) e la sua impronta SHA-256;
- un codice licenza `AIR-XXXX-XXXX-XXXX-XXXX` per email.

## 0. Controlla che il file sia quello giusto

In PowerShell, nella cartella dove l'hai salvato:

```powershell
Get-FileHash .\AIRENDER-2027.allep -Algorithm SHA256
```

Il numero deve essere uguale a quello che ti è arrivato insieme al file. Se è
diverso, non installarlo e scrivi a chi te l'ha mandato.

## 1. Installa

1. Apri Allplan 2027.
2. Trascina `AIRENDER-2027.allep` dentro la finestra di Allplan.
3. Conferma l'installazione se Allplan lo chiede, poi chiudi e riapri Allplan.

Pillow, la libreria per le immagini, è già dentro il pacchetto: **non** serve
*Install Python Package*. Python e PowerShell non servono.

Da annotare: Allplan ha chiesto qualcosa? Ha dato errori? Nel Plugin Manager
compare AIRENDER 1.0.14?

## 2. Apri la palette

1. Apri un modello e metti una finestra in prospettiva centrale, *shaded* con
   ombre. Allplan colora le superfici per layer: per un render fedele usa i
   colori neutri o i materiali veri.
2. Premi il pulsante **AIRENDER** nell'Actionbar, oppure apri
   **Library › Privato › AIRENDER › AIRENDER**.

Se invece compare «AIRENDER non si apre», manda il file indicato nel messaggio
(`Usr\…\AIRENDER\avvio.txt`). La riga «Pillow scelto» dice quale Pillow ha
trovato.

## 3. Cattura e Studio

1. Clicca una volta nella finestra 3D, poi premi **Cattura vista**.
2. Premi **Apri nello Studio**: si apre una finestra di Edge con la vista.
3. Se lo Studio non parte e compare «Non trovo un Python, fuori da Allplan,
   con Pillow», annotalo parola per parola: è il punto che da qui non si può
   verificare (vedi sotto).

## 4. Licenza e primo render

1. Nello Studio, apri **Licenza e saldo** e incolla il codice licenza.
   Devono comparire piano e saldo.
2. Scegli un preset e **Genera** con Nano Banana 2 a 1K: costa 1 render.
3. Al termine il saldo deve essere sceso di 1.

Se il PC è in una rete aziendale con proxy o firewall, devono essere aperti
`airender-server.netlify.app` e `gkiqhntwhxtmuqjkvybs.supabase.co`.

## Cosa rimandare

- Screenshot della palette dopo **Cattura vista**.
- Screenshot dello Studio con il render finito e il saldo.
- Qualunque messaggio d'errore, parola per parola, e il file `avvio.txt` se c'è.
- Quanto tempo ci è voluto e in quale passo ti sei bloccato.

## Cosa non è mai stato provato

- Il drag & drop del pacchetto 1.0.14 con Pillow dentro: Pillow è stato
  provato solo installato dall'SDK.
- Lo Studio su un PC senza Python di sistema. La palette prova prima il Python
  di Allplan. Se Allplan non ne ha uno che si possa lanciare fuori da Allplan,
  oggi serve Python da python.org e poi `py -m pip install pillow`: è
  l'attrito che resta, e questa prova serve a scoprirlo.
- Se Allplan installa da solo le librerie elencate in `requirements.in`.
