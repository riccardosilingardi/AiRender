# AIRENDER

Trasforma una vista 3D salvata da Allplan in un'immagine presentabile a un
cliente, senza che la geometria cambi.

## Cosa si rifiuta di fare

- **Non inventa geometria.** Se il controllo strutturale non tiene, lo dice.
  Un'immagine bella che rappresenta un edificio diverso da quello disegnato è
  un danno, non un risultato.
- **Non promette la scala metrica dei materiali.** Lo slider governa la grana,
  non i millimetri.
- **Non carica niente senza dire dove lo manda.** Il nome del servizio
  destinatario è visibile prima dell'invio.
- **Non gestisce crediti.** Chiave e tetto di spesa sono del cliente.
- **Non supporta Allplan sotto la 2026.**

## Come funziona

L'utente salva la vista con la funzione nativa di Allplan in una cartella
sorvegliata. Il plugin la trova, ne stima la struttura e genera il render
secondo il preset scelto e il testo libero dell'utente. Dopo, qualunque
superficie può essere selezionata — cliccandola o nominandola — e il suo
materiale cambiato senza rifare il resto dell'immagine. Il salvataggio produce
una pila di livelli rieseguibile, non un'immagine piatta.

## Dati

| Fonte | Cosa fornisce | Quanto è buona |
|---|---|---|
| Export immagine Allplan | Contenuto finestra a risoluzione impostabile | Ottima, nativa |
| Riferimento strutturale del provider | Aderenza alla composizione, forza 0-100 | Da misurare |
| Segmentazione | Maschera della regione scelta | Segue l'apparenza, non il modello |

L'anello debole è la segmentazione: due materiali resi simili finiscono in una
regione sola. Per questo i comandi di correzione della maschera ci sono dal
primo giorno.

## Farlo girare in locale

```bash
git clone [URL]
cd airender
python -m venv .venv && . .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env   # metti la tua chiave
python -m core.cli --image prova.png --preset base --testo "più caldo"
```

Il motore gira senza Allplan. È voluto: è l'unico modo per misurarlo.

## Cosa non è verificato

Vedi la sezione NON VERIFICATO di `PRD.md`. È mantenuta apposta. Un progetto che
sa cosa non sa vale più di uno che finge.

## Licenza

Da decidere prima del primo commit pubblico. Se l'obiettivo resta la rivendita,
il repository parte privato.
