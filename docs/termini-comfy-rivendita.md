# Termini di Comfy e rivendita di AIRENDER

Letto il 2026-11-03, prima della prima fattura. Non è un parere legale: dice
cosa c'è scritto, dove, e cosa non si è potuto leggere. Ogni citazione porta
il modo in cui è stata letta (vedi «Cosa si è letto, e come»).

> **Aggiornato la sera del 2026-11-03.** I Termini di servizio e l'accordo
> Enterprise di Comfy sono stati letti per intero e alla lettera: il testo, le
> clausole e cosa è permesso, vietato o da concordare per iscritto sono in
> **`docs/comfy-termini.md`**. Sui termini di Comfy vale quel file. Questo resta
> la fonte per i fornitori a monte, i rischi, la mail a Comfy e l'alternativa
> Vertex AI.

---

## In breve

1. **Nella forma di oggi, la rivendita non è permessa senza
   un'autorizzazione scritta di Comfy.** I Termini, letti per intero
   (`docs/comfy-termini.md`), danno il diritto d'uso solo «for your internal
   business purposes». Vietano di concedere i prodotti Comfy «directly or
   indirectly» in uso a terzi, e vietano ogni uso «not expressly permitted».
   Vendere le immagini che generi tu, invece, si può: l'Output è tuo.
2. **Anche l'accordo Enterprise vieta le stesse cose.** La differenza è che
   si firma, e un Order Form può contenere la clausola che manca. La licenza
   MiniMax venduta da Comfy esclude chi gestisce un «API aggregator,
   inference-as-a-service, or model-routing platform».
3. **Con Google e OpenAI un'applicazione propria basta, con Comfy no.** I
   loro termini permettono di integrare il servizio in un programma con valore
   autonomo, usato da terzi; vietano solo di rivendere il servizio. I Termini di
   Comfy non fanno questa distinzione: anche un'applicazione come AIRENDER
   (plugin, Studio, preset, controllo della geometria) ha bisogno
   dell'autorizzazione scritta. In più il server espone `/v2/models/*` «con lo
   stesso protocollo del Router» (`server/README.md`): ha la forma di un
   proxy, ed è la parte da non pubblicizzare né aprire ad altri.
4. **Prima della prima fattura serve una risposta scritta di Comfy.** La
   domanda è pronta da mandare, nella sezione 6.
5. **Scoperta nuova, che conta più della rivendita: la destinazione «Google»
   può essere falsa anche con `fallback_provider=false`.** Secondo la
   documentazione del Router, la catena Gemini di `vertexai` può passare la
   chiamata a un altro fornitore «that no header names». Tocca il non
   negoziabile 5 di `CLAUDE.md` e la promessa fatta ai clienti sotto NDA.

---

## Il caso da verificare

```
cliente (studio di architettura)            Riccardo                         Comfy Org (USA)
  licenza AIR-… + crediti AIRENDER  ──►  server Netlify  ──(una chiave Comfy)──►  Comfy Router  ──►  Google / BFL / OpenAI / BytePlus
  nessun account Comfy                  controlla piano e saldo
  non vede la chiave                    coda: POST …/requests?fallback_provider=false
                                        addebita solo a render riuscito
```

Più la rivendita di Serteco: licenze AIRENDER a listino -30%, attivate a mano.

**La domanda:** Comfy permette a un suo cliente di usare la propria chiave per
servire clienti propri che pagano?

---

## Cosa si è letto, e come

| Documento | Data | Come è stato letto |
|---|---|---|
| Termini di servizio Comfy | in vigore dal 2026-05-13 | **Integrale**, in `docs/comfy-termini.md`: dal sorgente pubblico del sito, confrontato parola per parola con la pagina viva |
| Informativa privacy Comfy | — | **Non letta** |
| Enterprise Customer Agreement Comfy | in vigore dal 2026-05-22 | **Integrale**, in `docs/comfy-termini.md`: dal sorgente del sito al 2026-10-26 |
| Licenza commerciale MiniMax venduta da Comfy | — | **Indiretto** |
| Documentazione del Router e dei Partner Node (docs.comfy.org) | commit `adfc0fd` di `Comfy-Org/docs`, ramo `main`, letto il 2026-11-03 | **Integrale**, dal sorgente pubblico su GitHub che genera il sito |
| Google Cloud Platform Terms of Service | modificati il 2026-10-12 | **Integrale** |
| Google Cloud Service Specific Terms, sezioni 15–20 (AI e AI generativa) | 2026-10-30 | **Integrale** per quelle sezioni |
| Google Cloud Acceptable Use Policy | 2026-10-12 | **Integrale** |
| Google Cloud Data Processing Addendum | 2026-10-30 | Solo la struttura (Google responsabile del trattamento, subresponsabili) |
| Google Generative AI Prohibited Use Policy | — | **Non letta** (`policies.google.com` bloccato) |
| Termini di BFL (FLUX), OpenAI, BytePlus (Seedream, Seedance) | vari | **Indiretto** |

«Indiretto» vuol dire che un motore di ricerca ha letto la pagina e ne ha
restituito frasi e riassunti. Le frasi fra virgolette sono quelle restituite,
ma il contesto attorno non si è visto. Prima di firmare qualcosa vanno rilette
sulla pagina.

---

## 1 · Comfy

### 1.1 e 1.2 Termini di servizio e accordo Enterprise

Letti per intero il 2026-11-03: testo, clausole e conclusioni in
**`docs/comfy-termini.md`**. In una riga: il diritto d'uso vale solo «for your
internal business purposes». È vietato «sublicense the Comfy Products for use
by a third party», anche «indirectly», e ogni uso «not expressly permitted».
Servire i propri clienti richiede un Order Form o un'autorizzazione scritta.

### 1.3 Documentazione del Router (letta per intero)

#### Chiave

- «Keep API keys on your server or in your local environment.» (Quickstart)
- La chiave «uses your workspace's model access and credit balance.» (Headers)
- «For security, never share your API Key or commit it to version control.»
  (Getting an API Key)

AIRENDER la tiene sul server e non la dà mai al cliente: su questo è in
regola. La domanda di sopra resta: il problema non è la chiave condivisa, è il
servizio reso a terzi.

#### Crediti

- **211 crediti = 1 $** (Concurrency Limits). I 17,17 crediti misurati dalla
  sonda per Nano Banana 2 fanno 0,081 $, coerente con il costo letto il
  2026-10-27.
- **Non rimborsabili:** «Currently, we do not support refunds for credits.»
  (FAQ Partner Node)
- **Scadono:** «Top-up credits: Expire 1 year from the date of purchase.»
- **Non trasferibili:** «your credits cannot be transferred to other users and
  are limited to the currently logged-in account». La pagina Credits aggiunge:
  «Sharing credits with other user accounts is not supported.»
- **Si pagano quando paga Comfy:** «You are billed when the provider bills
  Comfy.» (Billing) Un rifiuto per contenuto può essere addebitato: il catalogo
  lo dice per modello in `billing.charges_on_policy_rejection` (`yes`, `no`,
  `unknown`).
- **I tempi scaduti non sono gratis per forza:** «A timeout or lost connection
  does not prove that a generation was unbilled». E «An absent header does not
  mean the call was free.»

Per AIRENDER: il server addebita al cliente solo quando torna un'immagine, ma
Comfy può far pagare a Riccardo rifiuti e tempi scaduti. La differenza è un
costo di Riccardo e va messa nel prezzo. I crediti AIRENDER valgono 12 mesi,
come le ricariche Comfy: conviene comprare queste ultime a piccoli lotti, al
ritmo del consumo, così non ne scadono.

#### Concorrenza: un limite solo, condiviso da tutti i clienti

«Your concurrency limit is based on your lifetime paid spend, and applies at
the platform level across all endpoints you call.» (Concurrency Limits)

| Speso in tutto da sempre | Chiamate contemporanee |
|---|---:|
| 0 $ | 1 |
| più di 0 $, fino a 100 $ | 5 |
| 100 $ o più | 10 |
| 500 $ o più | 20 |
| 1.000 $ o più | 40 |

Un modello da 5 $ o più a chiamata ha un quarto del limite. Il limite di
chiamate al minuto «follows the authenticated caller, not the source IP»
(Capabilities and limits).

Con una chiave sola, **tutti i clienti AIRENDER insieme** stanno dentro questi
numeri. Dopo la prima ricarica sono 5 render contemporanei per tutto il
listino. Il server (`server/netlify/functions/router.mjs`) non tratta in modo
speciale il `429`: oggi un sesto cliente che genera nello stesso istante
riceve un errore.

#### Ripiego e destinazione

- `fallback_provider`: «Omitted, or any value other than `false`, leaves
  fallback on; `false` turns it off.» (API reference) È la trappola già scritta
  in `CLAUDE.md`, ora confermata dalla documentazione.
- **Sulla coda il ripiego non c'è:** «the queue has no fallback loop, so
  `fallback_provider` never changes the leg that runs», e «A queued submit has
  no fallback». AIRENDER usa la coda (`…/requests`), quindi lì il parametro
  non fa niente. Mandarlo non fa danni. Risponde alla domanda aperta in PRD
  sezione 9 (2026-10-21), ma dalla documentazione, non da una chiamata.
- **Altri fornitori dello stesso modello:** Nano Banana 2 e Pro si possono far
  servire anche da fal, Pika, Runware e WaveSpeed, ma solo se lo si chiede con
  `model_provider`. AIRENDER non lo chiede.
- **La catena interna di `vertexai`.** L'intestazione `X-Comfy-Router-Provider`
  nomina il fornitore che ha servito la chiamata, ma:

  > «which is the leg Router dispatched to and not necessarily the vendor that
  > produced the output, since a proxy-level cascade inside a native leg (the
  > `vertexai` Gemini image chain, for one) can hand the call to a different
  > vendor that no header names.»

  `vertexai/gemini-3.1-flash-image` è il modello predefinito dei preset. Anche
  con la coda e con `fallback_provider=false`, dire «va a Google» è una
  certezza che la documentazione di Comfy non dà. Quali siano gli altri
  fornitori della catena non è scritto da nessuna parte.

#### Dati

- **24 ore per i file dei Partner Node:** «All Partner Node media files are
  automatically deleted 24 hours after they are created.» (Data Retention dei
  Partner Node) Per il Router lo dice la sua pagina prodotto: «Inputs are kept
  for 24 hours after upload and outputs for 24 hours after generation. Then
  they’re deleted.» (comfy.org/platform/router, FAQ; `docs/comfy-termini.md`,
  sezione 3)
- **Ma il contenuto in generale resta di più:** la pagina generale sulla
  conservazione dei dati dice per «Customer content — Prompts, workflows,
  outputs, and other content you create or upload»: «Retained for as long as
  necessary to operate, analyze, and improve the service». Le due pagine non si
  contraddicono per forza (una parla dei file, l'altra dei contenuti), ma per un
  cliente sotto NDA la seconda frase è quella che pesa.
- **Al fornitore va tutto:** «Partner Nodes send your inputs (prompts, images,
  and other content) to third-party providers for processing. These providers
  enforce their own content moderation policies.» (FAQ Partner Node)
- **Fornitori «Verified»:** «"Yes" means Comfy has a signed contract with this
  provider. The contract says the provider does not use your content to train
  or improve its models when you use it through Comfy. The provider also gives
  IP indemnity to Comfy.» (Model Providers)
- **Dove si trattano i dati** e **licenza commerciale**, dalla tabella dei
  fornitori. Comfy la definisce «a structure we're actively filling in, not a
  finished reference». La colonna licenza parla di «commercial use through
  Comfy Cloud»: il Router non è nominato.

| Fornitore (modello AIRENDER) | Verified | Uso commerciale (Cloud) | Dove |
|---|---|---|---|
| Google (Nano Banana 2, Nano Banana Pro) | Yes | ✓ | Pending (non dichiarato) |
| Black Forest Labs (FLUX.1 Kontext) | Yes | ✓ | US, EU, Israele |
| Singdata (ByteDance: Seedream, Seedance) | Yes | ✓ | Malaysia, EU (alcuni modelli) |
| OpenAI (GPT Image 2) | **non in tabella** | — | — |

«Additional data residency options may be available for Enterprise
customers.»

### 1.4 MiniMax: come scrive Comfy quando esclude chi rivende

AIRENDER non usa MiniMax. Ma la licenza commerciale MiniMax, che Comfy vende
come «the only official reseller», esclude (indiretto): «Reselling or
sublicensing the model, and running a model marketplace, API aggregator,
inference-as-a-service, or model-routing platform.» È il linguaggio da cercare
nei Termini di servizio (sezione 1.1). Ed è la forma che il server AIRENDER
non deve avere.

---

## 2 · I fornitori dietro il Router

Per l'accordo Enterprise, i termini del fornitore si aggiungono a quelli di
Comfy. Passando da Comfy, il cliente di Google, BFL, OpenAI e BytePlus è
Comfy, non Riccardo. Questi termini contano per tre ragioni: dicono cosa il
fornitore permette in generale, Comfy li fa valere a valle, e diventano il
contratto di Riccardo se va diretto (sezione 5).

### Google: Nano Banana 2 e Pro (termini Google Cloud, letti per intero)

- **Applicazioni per terzi: sì.** Sezione 1.1: «Customer may use the Services,
  and integrate the GCP Services […] into any Customer Application that has
  material value independent of the Services». «"End Users" means the
  individuals who are permitted by Customer to use the Services. For clarity,
  End Users may include employees of Customer Affiliates and other authorized
  third parties.»
- **Rivendere il servizio: no.** Sezione 3.3: il cliente non deve «(c) sell,
  resell, sublicense, transfer, or distribute any or all of the Services».
- **L'immagine è del cliente.** Service Specific Terms 20(a): «Generated
  Output is Customer Data. As between Customer and Google, Google does not
  assert any ownership rights in any new intellectual property created in the
  Generated Output.»
- **Nessun addestramento.** Sezione 18: «Google will not use Customer Data to
  train or fine-tune any AI/ML models without Customer's prior permission or
  instruction.»
- **Niente minori.** Sezione 20(d): niente uso «as part of a website, Customer
  Application, or other online service that is directed towards or is likely to
  be accessed by individuals under the age of 18.» Per AIRENDER, che vende a
  studi professionali, basta scriverlo nei propri termini.
- **«Cerca sul web» (Grounding with Google Search, comando in grigio, PRD
  sezione 9).** Sezione 20(k): solo «in a Customer Application that is owned
  and operated by the Customer». Vanno mostrati i suggerimenti di ricerca a chi
  ha fatto la domanda, ed è vietato «cache, frame, syndicate, resell» i
  risultati. Passando da Comfy, il «Customer» è Comfy: prima di accendere il
  comando va chiesto a Comfy come si applica.
- **Concorrenza e modelli:** vietato usare l'uscita per sviluppare un prodotto
  concorrente o per addestrare modelli simili a quelli di Google (17(a), 17(b)).
- **Uso vietato:** la Prohibited Use Policy di Google è incorporata nell'AUP
  (20(c)). **Non letta.**

### Black Forest Labs: FLUX.1 Kontext (indiretto)

Termini del sito e di FLUX (rivisti il 2025-05-29; versione del 2026-08-01
citata): BFL non rivendica la proprietà delle uscite, che si possono usare
«for personal or commercial purposes», nei limiti dei termini. È vietato usarle
per addestrare modelli concorrenti. L'API ha propri Developer Terms
(2025-06-26) e FLUX API Service Terms, **non letti**. Nella tabella di Comfy:
Verified, uso commerciale ✓.

### OpenAI: GPT Image 2 (indiretto)

OpenAI Services Agreement: permesso «to integrate the Services into Customer
Applications and to make Customer Applications available to End Users».
Vietato «buy, sell, or transfer API keys from, to, or with a third party».
Nella versione Enterprise: «Customer may not resell or lease access to its
account». **OpenAI non compare nella tabella dei fornitori di Comfy**: per GPT
Image 2 via Router, l'uso commerciale non è dichiarato da Comfy.

### BytePlus: Seedream 5.0 e Seedance 2.5 (indiretto)

Specific Terms for the BytePlus Video Generation Model Services: licenza
«non-exclusive, non-transferable, non-sublicensable, revocable, and limited».
Vietato usare input e output per addestrare altri modelli. Il cliente deve far
rispettare agli utenti finali l'Acceptable Use Policy e la GenAI Acceptable
Use Policy di BytePlus. Esistono anche «Copyright and Portrait Feature Usage
Rules», **non lette**: contano se nei video compaiono persone. Chi possiede
l'uscita non è risultato dagli estratti. Nella tabella di Comfy: Singdata
(ByteDance), Verified, uso commerciale ✓.

---

## 3 · Cosa vuol dire per AIRENDER

In ordine di peso.

| # | Rischio | Perché | Cosa fare |
|---|---|---|---|
| 1 | Comfy sospende l'account perché i servizi sono resi a terzi | I Termini limitano l'uso agli scopi interni e vietano l'uso da parte di terzi, anche indiretto (`docs/comfy-termini.md`) | Autorizzazione scritta di Comfy (sezione 6) **prima della prima fattura** del modello attuale. Se dice di no: Vertex AI diretto (sezione 5) |
| 2 | La destinazione annunciata è falsa | Catena `vertexai` che passa a fornitori non nominati (1.3) | Chiedere a Comfy chi c'è nella catena e se si può fermarla su Google. Finché non risponde, la frase a schermo non può dire «Google» come certezza: per esempio «Comfy Router (Comfy Org, USA), che lo passa a Google Vertex AI o a un fornitore della sua catena per questo modello». È una modifica all'interfaccia, da fare in un PR suo |
| 3 | Il server ha la forma di un proxy del Router | Stesso protocollo su `/v2/models/*` | Non documentarlo né venderlo come API: solo per plugin e web app. Tenere chiusi per piano i modelli e i parametri (in parte c'è già). Nei termini AIRENDER, vietare l'uso del server fuori dalle app |
| 4 | Comfy manca dagli accordi sul trattamento dei dati | Il server README elenca i DPA con Supabase, Netlify, Stripe e Resend, non con Comfy. I dati vanno negli USA e da lì a Google, BFL, OpenAI o BytePlus. Conservazione «as long as necessary…» | Un DPA esiste: la pagina Enterprise viva dice «A DPA and enterprise agreement are available» e «Processing is in the United States on Google Cloud» (`docs/comfy-termini.md`, sezione 3). Chiederlo, con i subresponsabili (sezione 6). Nominarli nell'informativa AIRENDER, con il paese |
| 5 | Crediti persi o pagati senza render | Non rimborsabili, scadono in 12 mesi, rifiuti e tempi scaduti possono costare | Ricariche piccole al ritmo del consumo. Mettere nel prezzo una quota per i render pagati e non riusciti |
| 6 | Clienti bloccati dal limite di concorrenza | Un limite solo per tutti: 5 dopo la prima ricarica | Prima ricarica da almeno 100 $ (limite a 10). Gestire il `429` nel server con un'attesa invece di un errore. Chiedere a Comfy un limite personalizzato |
| 7 | GPT Image 2 senza uso commerciale dichiarato | OpenAI assente dalla tabella di Comfy | Tenerlo fuori dai piani a pagamento finché Comfy non conferma, oppure chiederlo nella stessa email |
| 8 | Minori di 18 anni (Google) | 20(d) | Nei termini AIRENDER: uso professionale, solo maggiorenni |

---

## 4 · Prima della prima fattura

- [x] Termini di servizio di Comfy letti per intero (`docs/comfy-termini.md`).
- [ ] Informativa privacy di Comfy letta.
- [ ] Risposta scritta di Comfy alla sezione 6, salvata accanto a questo file.
- [ ] Decisione: Router con il consenso di Comfy, accordo Enterprise, oppure
      Vertex AI diretto.
- [ ] Frase della destinazione corretta nello Studio e nella palette (rischio 2).
- [ ] Comfy (e i suoi fornitori) nell'informativa e nell'elenco dei DPA di
      `server/README.md`.
- [ ] Termini di vendita AIRENDER: uso professionale e maggiorenni; niente uso
      del server fuori dalle app; uscite AI senza garanzia; gli studi
      rispondono di ciò che caricano.

---

## 5 · Alternativa: Vertex AI diretto

`server/README.md` la cita già («stesso corpo Gemini»).

**A favore**
- I termini Google Cloud sono stati letti per intero e prevedono proprio
  questo caso: un'applicazione con valore autonomo usata da terzi autorizzati
  (1.1, «End Users»).
- La destinazione è certa, con un contratto diretto.
- Google offre un DPA (Data Processing Addendum).
- La sezione 16 dei Service Specific Terms permette di fissare la regione per
  i servizi elencati in `cloud.google.com/terms/data-residency`. Che i modelli
  immagine Gemini ci siano non è verificato.

**Contro**
- Solo i modelli Google. FLUX, GPT Image e Seedream/Seedance richiedono
  contratti a parte.
- Serve un account Google Cloud con fatturazione.
- Il prezzo per immagine va misurato.

**Quanto costa nel codice:** un provider nuovo in `core/provider/`. Il corpo
della richiesta è lo stesso (nativo Gemini), cambiano indirizzo e
autenticazione.

---

## 6 · La domanda a Comfy

Da mandare a `support@comfy.org`, oppure dal modulo
<https://comfy.org/contact/> se si vuole parlare di Enterprise. Va in inglese.

> Subject: Using Comfy Router inside our own application for paying customers — permitted?
>
> Hello,
>
> We are a small Italian software business. We build AIRENDER, an Allplan plugin
> and web app that turns architectural 3D views into presentation images. Our
> server holds one Comfy workspace API key and calls Comfy Router (queued
> requests, `vertexai/gemini-3.1-flash-image`, `vertexai/gemini-3-pro-image`,
> `bfl/flux-kontext-pro`, `openai/gpt-image-2`, `byteplus/seedream-5-0-260128`,
> `byteplus/dreamina-seedance-2-5-260628`) on behalf of our paying customers,
> mostly architecture firms.
> Customers never see the key, have no Comfy account and cannot call Router
> directly: they only use our application, and we charge them in our own
> credits. A partner company also resells licences to our application.
>
> 1. Your Terms of Service grant use "for your internal business purposes"
>    (Section 2) and exclude sublicensing "for use by a third party" and any
>    purpose "not expressly permitted" (Section 3 (i) and (vii)). Your Comfy API
>    v2 documentation describes exactly our pattern ("Fetch `Output.url` from
>    your own backend, which already holds the API key, and stream the bytes
>    to your user"). Will you give us a written authorization, or an Order
>    Form clause, that permits the same use of Router? Which agreement do we
>    need (Enterprise, reseller, other)? Your docs also say "Router is not
>    generally available yet": when is general availability expected?
> 2. Your API reference says that `X-Comfy-Router-Provider` is "not necessarily
>    the vendor that produced the output, since a proxy-level cascade inside a
>    native leg (the `vertexai` Gemini image chain, for one) can hand the call
>    to a different vendor". Which vendors can serve the two `vertexai` models
>    above on the native leg? Can we restrict them to Google only? We promise
>    our customers, some under NDA, to name the destination before sending.
> 3. Is a Data Processing Agreement (GDPR, with Standard Contractual Clauses)
>    available for Router customers, with a subprocessor list? How long are
>    Router inputs and outputs retained: the 24 hours stated on the Router page,
>    or "for as long as your account remains active" (Terms, Section 2)? Can
>    processing stay in the EU?
> 4. Is commercial use of the outputs confirmed for these models when called
>    through Router? OpenAI is not listed on your Model Providers page.
> 5. Can our Partner Node concurrency limit be raised with a custom limit as
>    our customer base grows?
> 6. Grounding with Google Search through Router: how do Google's display and
>    use conditions apply to us?
>
> Thank you,
> Riccardo Silingardi

**Cosa rimandare indietro:** la risposta scritta, intera, salvata in
`docs/` accanto a questo file o incollata nella PR.

**Cosa significa:**
- un sì scritto alla 1 chiude il rischio 1;
- un «serve Enterprise» apre una trattativa;
- un no porta alla sezione 5;
- la risposta alla 2 decide la frase della destinazione.

---

## 7 · NON VERIFICATO

- **L'informativa privacy di Comfy:** non letta. I Termini e l'accordo
  Enterprise sono stati letti per intero più tardi, lo stesso giorno
  (`docs/comfy-termini.md`).
- **La licenza MiniMax e i termini di BFL, OpenAI e BytePlus:** letti solo in
  estratti dal motore di ricerca. Il testo attorno alle frasi citate non si è
  visto.
- **La Prohibited Use Policy di Google:** non letta.
- **La documentazione del Router vale per l'API che AIRENDER usa oggi:** letta
  al commit `adfc0fd`, ma le pagine non hanno data. Il motore di ricerca
  conserva una versione precedente della pagina Headers che dava il Router
  come non ancora disponibile a tutti. La versione letta non lo dice più, e la
  sonda del 2026-10-27 ha generato davvero.
- **La coda non ha ripiego:** lo dice la documentazione. Nessuna chiamata lo ha
  provato.
- **I fornitori della catena `vertexai`:** non sono scritti da nessuna parte.
- **La licenza commerciale «Cloud» della tabella copre anche il Router:**
  non scritto.
- **Fuori dal perimetro di questo documento**, da guardare con un consulente:
  obblighi di trasparenza dell'AI Act sulle immagini generate, informativa
  GDPR verso gli studi, regime fiscale e IVA.

---

## Fonti

Documentazione di Comfy, letta dal sorgente `github.com/Comfy-Org/docs`,
commit `adfc0fd` (stesso testo del sito):

- <https://docs.comfy.org/development/comfy-router/quickstart>
- <https://docs.comfy.org/development/comfy-router/headers>
- <https://docs.comfy.org/development/comfy-router/reference>: `model_provider`,
  `fallback_provider`, `X-Comfy-Router-Provider`, stime, file risultato
- <https://docs.comfy.org/development/comfy-router/limitations>
- <https://docs.comfy.org/development/comfy-router/billing>
- <https://docs.comfy.org/development/comfy-router/providers>
- <https://docs.comfy.org/development/comfy-router/models/google/nano-banana-2/code>
- <https://docs.comfy.org/development/api-development/getting-an-api-key>
- <https://docs.comfy.org/tutorials/partner-nodes/faq>
- <https://docs.comfy.org/tutorials/partner-nodes/concurrency-limits>
- <https://docs.comfy.org/tutorials/partner-nodes/data-retention>
- <https://docs.comfy.org/tutorials/partner-nodes/model-providers>
- <https://docs.comfy.org/support/data-retention>
- <https://docs.comfy.org/interface/credits>

Comfy, non lette o lette in estratti:

- <https://www.comfy.org/terms-of-service> (non letta)
- <https://www.comfy.org/privacy-policy> (non letta)
- <https://comfy.org/enterprise-msa/> (estratti)
- <https://comfy.org/minimax/license/> (estratti)
- <https://comfy.org/pricing/> (estratti)

Google Cloud, lette per intero:

- <https://cloud.google.com/terms> (2026-10-12)
- <https://cloud.google.com/terms/service-terms> (2026-10-30), sezioni 15–20
- <https://cloud.google.com/terms/aup> (2026-10-12)
- <https://cloud.google.com/terms/data-processing-addendum> (2026-10-30), solo
  la struttura

Altri fornitori, estratti:

- <https://bfl.ai/legal/terms-of-service>,
  <https://bfl.ai/legal/developer-terms-of-service>
- <https://cdn.openai.com/osa/openai-services-agreement.pdf>
- <https://docs.byteplus.com/en/docs/ModelArk/Specific_Terms_for_the_BytePlus_Video_Generation_Model_Services>
