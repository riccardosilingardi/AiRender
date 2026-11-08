# Server di vendita AIRENDER

Licenze e crediti senza account Comfy per il cliente. Funzioni Netlify, dati
su Supabase, pagamenti Stripe, fatture elettroniche Fatture in Cloud. Nessuna
dipendenza npm: solo Node 20+ e `fetch`.

```
plugin / web app ──(vista + codice licenza)──► Netlify /v2/models/*  ──(chiave di Riccardo, fallback spento)──► Comfy Router ──► Google
                                                 │  riserva, addebita solo a render riuscito
                                                 ▼
                                              Supabase: licenze, lotti di crediti, render, movimenti, fatture
Pagina prezzi ─► /api/acquista ─► Stripe Checkout ─► /api/stripe-webhook ─► licenza + crediti + email + Fatture in Cloud
```

## Cosa c'è

| Percorso | Funzione | Cosa fa |
|---|---|---|
| `/` | `public/index.html` | Pagina prezzi: Base, Pro, Studio (mensile/annuale), Prova, Ricarica |
| `/v2/models/*` | `router.mjs` | Stesso protocollo del Comfy Router: invio, stato, risultato. Riserva all'invio, addebita al risultato con immagine, annulla se il Router fallisce |
| `/studio/` | `public/studio/` (costruita) | La web app: lo Studio nel browser, costruito a ogni deploy da `scripts/scrivi_web.py` |
| `/api/accedi` | `accedi.mjs` | Accesso alla web app: email e codice della stessa licenza, oppure il gettone del link (crea la chiave del browser) |
| `/api/link-accesso` | `link-accesso.mjs` | Manda per email il link di accesso alla web app, uno per licenza attiva (migrazione 004) |
| `/api/saldo` | `saldo.mjs` | Piano, saldo, scadenza, funzioni, link firmati Ricarica e Gestisci |
| `/api/acquista?prodotto=…` | `acquista.mjs` | Apre il Checkout (dati fiscali, codici sconto) |
| `/api/gestisci?t=…` | `gestisci.mjs` | Portale clienti Stripe (cambio piano, disdetta) |
| `/api/stripe-webhook` | `stripe-webhook.mjs` | Crea licenze, accredita, manda il codice, fattura |
| `/api/admin` | `admin.mjs` | Licenze manuali (rivendita Serteco), accrediti, sospensioni. Da `scripts/licenze.py` |
| `/api/listino` | `listino.mjs` | Il listino per la pagina prezzi |
| (ogni ora) | `pulizia.mjs` | Cancella dallo Storage i risultati piu' vecchi di 48 ore |

Il listino (prezzi, pesi, piani) vive in `core/config.py`, `LISTINO`.
`listino.json` si riscrive con `python scripts/scrivi_listino.py` e
`tests/test_listino.py` fallisce se diverge.

## Messa in produzione, in ordine

1. **Supabase.** Nuovo progetto in regione UE, Francoforte (`eu-central-1`):
   la regione non si cambia dopo. SQL editor: incolla ed esegui
   `supabase/migrations/001_crediti.sql`, poi
   `supabase/migrations/002_pulizia_risultati.sql` e
   `supabase/migrations/003_funzioni_chiuse.sql` (le funzioni dei crediti le
   esegue solo `service_role`) e `supabase/migrations/004_accesso_link.sql`
   (link di accesso via email e chiavi del browser). Il bucket privato `risultati` lo crea la 001. Copia l'URL e la chiave
   segreta (`sb_secret_…`, in `SUPABASE_SECRET_KEY`).
2. **Stripe.** Catalogo prodotti: un prodotto per piano con i prezzi del
   listino (Prova 15 € e Ricarica 10 € una tantum; Base 19/190, Pro 39/390,
   Studio 99/990 ricorrenti mese/anno), IVA esclusa. Copia gli id `price_…`.
   Tax rates: IVA 22% esclusa, se serve. Customer portal: attiva cambio
   piano e disdetta. Webhook verso `https://<sito>/api/stripe-webhook` con
   gli eventi `checkout.session.completed`, `invoice.paid`,
   `customer.subscription.updated`, `customer.subscription.deleted`.
3. **Codici sconto Serteco.** Stripe > Coupon: 20%, durata 12 mesi
   (repeating), poi un Promotion code per segnalatore (es. `SERTECO20`). Il
   Checkout li accetta già; il codice usato resta sulla licenza.
4. **Fatture in Cloud.** Token personale con permesso documenti emessi;
   id azienda, id dell'aliquota IVA e del conto di incasso. Lascia
   `FIC_INVIA_SDI` vuoto finché le prime fatture non sono giuste.
5. **Email.** Mailjet (UE): API key e secret key, mittente verificato
   (`EMAIL_MITTENTE`). In alternativa Resend: dominio verificato, chiave API.
6. **Netlify.** Nuovo sito dal repository, *Base directory* `server`. Tutte le
   variabili di `.env.example`. Poi `SERVER_AIRENDER` in `core/config.py` (o
   `AIRENDER_SERVER` sul PC) con l'indirizzo vero.
7. **Prova completa in modalità test di Stripe**: compra la Prova con la
   carta 4242…, controlla email, licenza in Supabase (10 + 50 render), bozza
   in Fatture in Cloud; poi `python -m core.cli --licenza AIR-…`,
   `--saldo`, un render, saldo sceso di 1.

## Rivendita Serteco

Serteco fattura al cliente a listino -30%; Riccardo attiva a mano:

```
set AIRENDER_ADMIN_TOKEN=...
py scripts/licenze.py crea --email cliente@studio.it --piano pro --mesi 12 --rivenditore serteco
```

Il codice parte per email al cliente (o `--senza-email` e lo stampa).

## Test

```
cd server && npm test                       # 37 test, nessuna rete (quello SQL si salta)
AIRENDER_PG=postgresql://... npm test       # anche le funzioni SQL su un Postgres vuoto
```

## Da verificare prima del lancio

- Termini di Comfy sulla rivendita di generazioni fatte con una chiave sola:
  letti (`docs/comfy-termini.md`). L'uso vale solo «for your internal business
  purposes»: servire i clienti da questo server richiede un'autorizzazione
  scritta di Comfy. Nessuna fattura prima di averla. Rischi e mail a Comfy in
  `docs/termini-comfy-rivendita.md`. Alternativa: Vertex AI diretto, stesso
  corpo Gemini.
- GDPR: DPA con Comfy (e i suoi fornitori), Supabase, Netlify, Stripe, Mailjet; le viste passano dal
  server ma non si salvano, tranne i risultati sopra 4,5 MB (Storage, link di
  24 ore, cancellati dopo 48 ore da `pulizia.mjs`, funzione
  programmata ogni ora). Prima di inoltrare, il router toglie dalle immagini
  EXIF, XMP e testi (`lib/pulisci.mjs`). Comfy non ha un DPA (mail del
  2026-11-05): testi e stato in `docs/legale/`.
- Termini: il Checkout chiede di spuntarli (`consent_collection`). Prima di
  andare dal vivo vanno pubblicati `termini.html` e `privacy.html` in
  `public/` (testi in `docs/legale/`, dopo la revisione dell'avvocato) e
  l'indirizzo dei Termini va scritto in Stripe, Impostazioni > Dettagli
  pubblici: senza, Stripe rifiuta la sessione.
- Regime fiscale di Riccardo (forfettario o no): decide IVA e natura
  sulla fattura.
