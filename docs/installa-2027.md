# Installare AIRENDER in Allplan 2027

Una volta sola, dal PC con Allplan 2027. Servono circa dieci minuti. I comandi
sono per PowerShell e usano `py`, il Python che hai già usato per la sonda.

## Prima di cominciare

- Scarica il repository come ZIP da GitHub (pulsante verde *Code* › *Download
  ZIP*) ed estrailo, per esempio in `Downloads\AiRender`. Tutti i comandi
  sotto partono da quella cartella.
- La chiave `COMFY_API_KEY` che hai impostato per la 2026 è una variabile
  d'ambiente di Windows: vale anche per la 2027, non serve rifarla.

## 1. Pillow nella 2027 (con Allplan aperto)

Ogni versione di Allplan ha il suo Python e la sua cartella di pacchetti, quindi
Pillow va installato di nuovo.

1. Apri Allplan 2027.
2. Cerca lo strumento **Install Python Package** del PythonParts SDK (nella
   barra *PythonPart SDK* o con la lente in alto a destra).
   - Se non c'è, l'SDK per la 2027 non è installato: si scarica dalla guida
     ufficiale, <https://pythonparts.allplan.com/2027/manual/getting_started/>,
     punto 2 «Get the SDK». L'SDK 3.0 vale solo dalla 2027 in poi.
3. Pacchetto `pillow`, destinazione **USR**, *Install*.
4. Chiudi Allplan.

## 2. Copia AIRENDER (Allplan chiuso)

```powershell
cd $env:USERPROFILE\Downloads\AiRender
py allplan\v2027\pacchetto.py --installa
```

Il comando:

- trova da solo la cartella Usr della 2027 (Documenti, OneDrive o
  `C:\Data\Allplan\Allplan 2027`) e dice quale ha usato;
- copia la palette, il motore e lo Studio;
- toglie *AIRENDER prova* e *AIRENDER sonda*, le prove della 2026. Le tue viste e
  i render in `Usr\AIRENDER` non li tocca;
- se non vede Pillow, lo scrive: in quel caso rifai il punto 1.

Se dice «Non trovo la cartella Usr», in Allplan 2027 apri
*Menu › Servizi › Esplora file › Miei documenti CAD*, copia il percorso e
rilancia così:

```powershell
py allplan\v2027\pacchetto.py --installa --usr "C:\...\Usr\Local"
```

## 3. Prova

1. Apri Allplan 2027 e un modello, poi metti una finestra in prospettiva
   centrale, *shaded* con ombre.
2. **Library › Privato › AIRENDER › AIRENDER**. La palette si apre nella
   scheda *Proprietà*.
3. Clicca una volta nella finestra 3D, poi premi **Cattura vista**.
4. Premi **Prova a secco**.
5. Solo se vuoi spendere (circa 17 crediti): premi **Genera render**. Allplan
   resta libero; premi **Aggiorna** ogni tanto.
6. Premi **Apri nello Studio**.

## 4. Il pulsante nell'Actionbar (facoltativo, mai provato)

Lo stesso comando del punto 2 scrive anche `dist\AIRENDER-2027.allep`: è
AIRENDER nel formato plugin della 2027, lo stesso con cui Allplan distribuisce
il PythonParts SDK. Installato da Allplan, aggiunge l'area **AIRENDER** con un
pulsante e la sua icona nell'Actionbar/Toolscape, così non serve passare dalla
Library.

Non so ancora da quale voce di menu la 2027 installa un `.allep` da file:
cercala fra i plugin (o prova a trascinare il file nella finestra di Allplan).
I file vanno negli stessi posti del punto 2, quindi non si crea un doppione.

## 5. Nano Banana Pro (facoltativo)

Il nome del modello sul Router è `vertexai/gemini-3-pro-image` (dalla
documentazione di Comfy). Come per gli altri modelli, entra nel menu solo dopo
una chiamata vera.

```powershell
py scripts\sonda_comfy.py --modello vertexai/gemini-3-pro-image --solo-schema
py scripts\sonda_comfy.py --modello vertexai/gemini-3-pro-image --base64-nudo --immagine "<una vista catturata>"
```

Il primo comando è gratis. Il secondo fa una generazione vera: il costo lo
stampa la sonda (`x-comfy-credits-used`).

## Cosa rimandarmi

- L'uscita del comando del punto 2.
- Uno screenshot della palette dopo *Cattura vista* e il testo di *Prova a
  secco*.
- La riga «Load AirenderPalette.py, Python …» della finestra *Trace*: dice
  la versione di Python della 2027. Più qualunque errore della *Trace*.
- Se l'hai provato: se l'`.allep` si installa e dove compare il pulsante.
- Se l'hai lanciata: l'uscita della sonda di Nano Banana Pro.
