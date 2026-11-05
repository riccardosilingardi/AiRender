# Testi legali di AIRENDER — bozze

> **Non è una consulenza legale.** Sono bozze scritte il 2026-11-05 da una
> sessione di Claude, partendo dal codice di questo repository e da ricerche
> pubbliche. Vanno fatte rivedere da un avvocato privacy/IT **prima** di
> pubblicarle o di firmarle con un cliente. Le parti fra `[PARENTESI QUADRE]`
> sono dati che mancano (ragione sociale, P.IVA, sede, foro).

| File | Cosa è | Per chi |
|---|---|---|
| `termini.md` | Termini di servizio, quelli che si accettano con la casella al pagamento | Ogni cliente |
| `privacy.md` | Informativa privacy (art. 13 GDPR) | Ogni cliente, sul sito |
| `dpa.md` | Accordo sul trattamento dei dati (art. 28 GDPR), da firmare se il cliente lo chiede | Studi e rivenditori (Serteco) |
| `sub-responsabili.md` | Elenco dei fornitori che toccano i dati, con paese e garanzie | Allegato al DPA, pubblico sul sito |
| `sicurezza.md` | Pagina «Sicurezza»: cosa c'è oggi, cosa no | Sito, risposta ai questionari |

La versione dei termini in vigore è in `server/netlify/functions/acquista.mjs`
(`TERMINI_VERSIONE`): quando cambia un testo, cambia anche quella.

## Cosa deve guardare l'avvocato, in ordine di rischio

1. **Comfy senza DPA.** Comfy (USA) riceve le immagini e oggi non firma un
   accordo GDPR (mail di Yoland Yan, 2026-11-05). Finché manca, i termini
   vietano di caricare dati personali nelle immagini (`termini.md` §6). È una
   toppa: va chiesto a Comfy un DPA con clausole contrattuali standard UE.
2. **Clausole vessatorie (art. 1341-1342 c.c.).** Limitazione di
   responsabilità, recesso, foro e sospensione richiedono, secondo la
   giurisprudenza prevalente, un'approvazione specifica e separata anche fra
   imprese. Il Checkout di Stripe ha una sola casella: serve capire se basta,
   o se aggiungere una seconda conferma (campo personalizzato) o una pagina di
   accettazione prima del pagamento.
3. **Solo professionisti.** I termini escludono i consumatori, per non
   rientrare nel Codice del consumo (recesso di 14 giorni, clausole nulle).
   Il Checkout chiede la partita IVA ma non la rende obbligatoria: va deciso
   se bloccare chi non la mette.
4. **Ruoli GDPR** (titolare/responsabile) come descritti in `dpa.md`.
5. **AI Act art. 50 e legge 132/2025**: obblighi propri e obblighi girati al
   cliente (`termini.md` §8).
6. **Proprietà delle immagini generate** e assenza di garanzia sul diritto
   d'autore (`termini.md` §7, legge 132/2025 art. 25).

## Promesse nei testi che il codice non mantiene ancora

- Dati di uso (tabella `render`) cancellati dopo 24 mesi: la cancellazione
  automatica non c'è (`sicurezza.md`, da fare).
- Marcatura «generata con l'IA» nel PSD e nei video: non c'è.
- Regione UE di Supabase, Netlify e Resend: dipende da come si creano gli
  account.
