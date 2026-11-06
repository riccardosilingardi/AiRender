# Sicurezza di AIRENDER

**Bozza, 2026-11-05.** Cosa c'è oggi nel codice e cosa no. Ogni riga «c'è» si
può controllare nel repository; le righe «da fare» non vanno presentate a un
cliente come fatte.

## Cosa c'è

**Immagini**
- Prima di ogni invio si tolgono i metadati: EXIF con la posizione GPS, dati
  del telefono, XMP, IPTC, commenti. Lo fanno il plugin e lo Studio
  (`core/immagine.py`, `senza_metadati`) e di nuovo il server
  (`server/lib/pulisci.mjs`).
- Il server non salva né le viste né i prompt. Le immagini generate troppo
  grandi per la risposta vanno in un archivio privato con link firmato che
  scade dopo 24 ore. Una funzione oraria le cancella dopo 48 ore
  (`server/netlify/functions/pulizia.mjs`).
- La destinazione (servizio e modello) si vede nell'interfaccia prima di ogni
  invio. Il ripiego su altri fornitori è spento (`fallback_provider=false`).
- Ogni immagine generata porta nel file un'indicazione XMP «generata con
  l'IA» (IPTC Digital Source Type), senza prompt né nomi.

**Accessi e chiavi**
- La chiave Comfy e la chiave di servizio del database vivono solo nelle
  variabili d'ambiente di Netlify, mai nel codice né nel plugin.
- Il codice licenza è salvato solo come impronta SHA-256: chi legge il
  database non può ricostruirlo.
- Ogni richiesta di stato o risultato è controllata contro la licenza che la
  chiede: un cliente non può leggere il render di un altro.
- Database con Row Level Security accesa e nessuna regola pubblica: la chiave
  pubblica non vede niente.
- Tutte le comunicazioni passano in HTTPS.

**Pagamenti**
- I dati delle carte li tratta solo Stripe (PCI DSS): non passano dal nostro
  server.
- I webhook di Stripe sono verificati con la firma.

## Da fare prima di vendere

- [ ] Autenticazione a due fattori su GitHub, Netlify, Supabase, Stripe,
      Comfy, Mailjet, Fatture in Cloud e sull'email di Riccardo.
- [ ] Progetto Supabase in regione UE (Francoforte): la regione non si cambia
      dopo la creazione.
- [ ] Regione UE per le funzioni Netlify (le email partono da Mailjet, UE), se il piano
      lo permette.
- [ ] Cancellazione automatica dei dati di uso (tabella `render`) dopo 24 mesi.
- [ ] Registro dei trattamenti (art. 30 GDPR).
- [ ] Procedura scritta per le violazioni di dati: chi avvisa chi, entro
      quando (72 ore al Garante).
- [ ] Backup del database e prova di ripristino.
- [ ] Rotazione delle chiavi: come si cambia la chiave Comfy senza fermare il
      servizio.
- [ ] Marcatura «generata con l'IA» anche nel PSD e nei video.

## Cosa non c'è, e quando avrebbe senso

Nessuna certificazione (SOC 2, ISO 27001). Servono quando un cliente grande la
chiede nel contratto. A quel punto uno strumento come Vanta o Drata automatizza
la raccolta delle prove; prima costa più di quanto rende.
