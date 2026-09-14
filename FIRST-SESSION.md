# Prima sessione

Incolla il blocco qui sotto in Claude Code come prima prompt su questo
repository. Completa le parti fra parentesi quadre prima di incollarlo.
Cancella questo file quando il progetto è avviato.

---

```
Leggi prima PRD.md e CLAUDE.md. Questo repository è uno scaffold: i documenti
sono compilati, ma non esiste ancora codice. Pianifica prima di scrivere.

COSA STIAMO COSTRUENDO
Un plugin per Allplan che trasforma una vista 3D shaded salvata in un'immagine
presentabile a un cliente, senza che la geometria cambi. In questa sessione
NON si tocca Allplan: si costruisce solo il motore, che deve funzionare da riga
di comando su una qualunque immagine. Dettagli nelle sezioni 1, 2 e 4 del PRD.

STACK
Python 3.11, nessun framework. Il motore non importa nulla di Allplan.
Se proponi una dipendenza, spiega perché e verifica che sia installabile
nell'interprete Python incorporato di Allplan (vedi NON VERIFICATO nel PRD).

COMPITO 1 — la cosa più piccola che gira.
Una riga di comando che prende un file immagine, un preset e un testo libero, e
restituisce un'immagine generata. Un solo provider, un solo percorso reale,
nessun dato finto. Se la chiamata fallisce, l'errore è in italiano e dice cosa
fare.

COMPITO 2 — le decisioni hanno una casa.
Crea core/config.py come unico posto dove vivono soglie, pesi e limiti, con la
ragione nel commento accanto e l'etichetta MISURATA o SCELTA. Nessun valore
numerico cablato altrove.

COMPITO 3 — lo strato provider è sostituibile.
Una sola interfaccia interna con i metodi che servono al prodotto: generazione
con riferimento strutturale e forza, modifica di una regione con maschera,
riesecuzione a parametri identici. Implementa un provider solo. Il secondo deve
potersi aggiungere senza toccare il resto.

COMPITO 4 — i rifiuti esistono dal primo giorno.
La sezione 2 del PRD elenca cosa il prodotto si rifiuta di fare. Implementane
almeno due adesso: il rilevamento di un'immagine inadatta (wireframe o troppo
piatta) con messaggio che spiega cosa salvare, e il divieto di chiamare il
parametro di grana "scala". Un rifiuto aggiunto dopo non viene mai aggiunto.

COMPITO 5 — test che nominano i loro casi.
`pytest` gira e riporta i conteggi. Ogni costante del COMPITO 2 ha un test che
nomina il caso che protegge. Le chiamate di rete sono simulate nei test: la
suite deve girare senza chiave e senza connessione.

NON costruire nient'altro. Niente palette, niente interfaccia Allplan, niente
pila di livelli: arrivano nella sessione 2, quando il motore sarà misurato.

Quando hai finito: riporta i conteggi dei test, aggiorna le sezioni 7 e 9 del
PRD perché corrispondano a quello che ora esiste, apri un PR, e dimmi in lingua
semplice cosa hai costruito e cosa NON hai verificato.
```

---

## Dopo quel primo PR

Ogni sessione successiva segue lo stesso giro:

1. La persona riferisce la fusione del PR.
2. Claude clona il repo, esegue test e build, e misura il comportamento
   cambiato su dati reali.
3. Claude trova cosa è sbagliato, ordinato per danno, e pianifica.
4. Claude consegna esattamente una prompt, che si apre con ciò che la sessione
   precedente ha lasciato non verificato.
5. Si ripete.

## Sessioni previste dopo la prima

- **Sessione 2** — misurazione del riferimento strutturale a forze diverse, e
  scelta del valore di `STRUCTURE_STRENGTH_DEFAULT`. Fino ad allora quel numero
  resta etichettato SCELTO.
- **Sessione 3** — cartella sorvegliata e pila di livelli su disco.
- **Sessione 4** — palette Allplan e pacchetto ALLEP.
- **Sessione 5** — installazione dal Plugin Manager su macchina reale.
