# Termini di Comfy: si possono rivendere i render?

Letto il 2026-11-03, per intero e alla lettera. Non è un parere legale: riporta
il testo, dice da dove viene e come lo leggo. Le decisioni che contano vanno
fatte rivedere da un legale.

**Domanda.** Posso rivendere ai miei clienti render generati con i crediti del
mio account Comfy, attraverso un mio server, un'API pubblica o un server MCP?

---

## Risposta

**Rivendere le immagini sì. Far generare i clienti con il tuo account, no,
senza un'autorizzazione scritta di Comfy.** I Termini di servizio danno il
diritto di usare i prodotti Comfy solo «for your internal business purposes».
Vietano di concederli «directly or indirectly» in uso a terzi e vietano ogni
uso «not expressly permitted». Nessuna clausola permette di servire clienti
propri.

| Come vendi | Esito | Perché (clausole sotto) |
|---|---|---|
| **A.** Generi tu, o i tuoi dipendenti e collaboratori, e vendi le immagini ai clienti | **Permesso** | Le immagini (Output) sono tue (§2 Customer Data). L'uso serve la tua attività. Valgono i termini del fornitore del modello (§2 Partner Nodes) |
| **B.** Il cliente genera dall'app AIRENDER (plugin o web), attraverso il tuo server e la tua chiave. È il modello di oggi | **Non permesso dal testo: serve un accordo scritto** | Il diritto vale per i tuoi «Users», cioè dipendenti e collaboratori, e per scopi interni (§1, §2). È vietato «sublicense … for use by a third party», anche «indirectly» (§3 (i)), e ogni uso non espressamente permesso (§3 (vii)) |
| **C.** API pubblica che vende generazioni ad altri | **Vietato** | §3 (i), (v) prodotto concorrente (Comfy vende Comfy Router), (vii) |
| **D.** Server MCP | Dipende da chi lo usa | Se lo usi solo tu, è come A. Se lo usano i clienti con la licenza AIRENDER, è come B. Se è aperto a chiunque, è come C, e in più Comfy vende già un suo «Comfy MCP» (§3 (v)) |
| **E.** ComfyUI open source su un tuo server con GPU, con modelli aperti, senza Partner Nodes | **I Termini di Comfy non si applicano** | ComfyUI è «Comfy OSS», escluso dai Termini (§2 Comfy OSS), e la GPL-3.0 non pone obblighi a chi lo usa come servizio senza distribuirlo. Valgono però le licenze dei singoli modelli. Nano Banana, GPT Image e Seedream qui non ci sono: sono solo Partner Nodes (sezione 5) |

**Su B il contratto e la documentazione di Comfy non dicono la stessa
cosa.** Il contratto non lo permette:

- il diritto è dato a te e ai tuoi «Users», che il testo definisce come
  dipendenti e collaboratori;
- il divieto copre anche l'uso «indirectly» da parte di terzi;
- il punto (vii) chiude tutto ciò che non è espressamente permesso.

La documentazione tecnica, invece, descrive proprio lo schema di AIRENDER
come un uso normale. Per la Comfy API v2 dice: «Any application that shows
outputs to its own users…», e «Fetch `Output.url` from your own backend,
which already holds the API key, and stream the bytes to your user» (sezione
4). Anche le pagine marketing parlano di API «behind customer-facing
products». È il segnale più forte che Comfy considera accettabile servire i
propri utenti, ma ha tre limiti:

- è documentazione, non contratto;
- il §12 Entire Agreement mette da parte «statements, sales materials or
  presentations»;
- parla dei workflow, non del Router.

Per questo serve ancora che Comfy lo metta per iscritto. Ma è probabile che
dica di sì, e la mail può citare queste frasi.

**Cosa rischi, se lo fai lo stesso:**

- **Sospensione o chiusura immediata:** Comfy può farlo «immediately» se l'uso
  «violates this Agreement» (§5).
- **Crediti persi:** i crediti rimasti non si rimborsano «under any
  circumstances, including upon termination» (§4).
- **Danni da coprire:** ti impegni a tenere indenne Comfy dalle pretese di
  terzi che nascono dalla tua violazione (§10).

**La strada:**

- un **Order Form** o un accordo **Enterprise** con una clausola che permetta
  esplicitamente di servire i propri clienti (§2 «as set forth in the
  applicable Order Form»; MSA §11 «assented to in writing by both parties»);
- in alternativa, il diretto con Google Vertex AI (vedi
  `docs/termini-comfy-rivendita.md`, sezione 5);
- oppure ComfyUI open source con modelli aperti su una GPU propria (caso E,
  sezione 5): fuori dai Termini, ma senza Nano Banana.

---

## Fonti e come sono state lette

`comfy.org` e `docs.comfy.org` sono bloccati dalla rete di questa sessione:
il proxy risponde 403. Per questo i testi sono stati letti dai sorgenti
pubblici che generano i siti.

| Documento | Versione | Da dove | Confronto con il sito |
|---|---|---|---|
| [Terms of Service](https://www.comfy.org/terms-of-service) | «Effective Date: May 13, 2026» | Repository ufficiale `Comfy-Org/ComfyUI_frontend`, commit [`cca126a`](https://github.com/Comfy-Org/ComfyUI_frontend/blob/cca126acd1734b4cfd9ad26a00491cd98a7cf107/apps/website/src/locales/en/main.json) del 2026-10-26, chiavi `tos.*` | **Identico parola per parola alla pagina viva.** Il confronto è con i due PDF caricati da Riccardo il 2026-11-03. Quello completo, delle 20:48 UTC, coincide per intero: 5.239 parole su 5.239, dalla data fino a «legal@comfy.org». Quello in modalità lettura, delle 20:46, coincide per la parte che contiene |
| [Enterprise Customer Agreement](https://comfy.org/enterprise-msa/) | «Effective Date: May 22, 2026», modello | Stesso commit, chiavi `enterprise-msa.*` | **Identico parola per parola alla pagina viva**: 4.976 parole su 4.976, confrontate con il PDF di Riccardo del 2026-11-03, 21:10 UTC |
| [Comfy Router](https://comfy.org/platform/router) | — | Stesso commit, `pages/platform/router.astro` e chiavi `platform.router.*` | **Confrontato con la pagina viva** (PDF del 2026-11-03, 21:12 UTC). Tutte le frasi citate qui ci sono, parola per parola, tranne la risposta della FAQ 10 su BYOK: nella stampa manca (sezione 3) |
| [Comfy Enterprise](https://comfy.org/enterprise/) | — | Solo il PDF della pagina viva del 2026-11-03, 21:24 UTC | **Riscritta dopo il 2026-10-26**: 38 frasi della pagina viva non esistono nel sorgente pubblico. Non c'è un sorgente con cui confrontarla: le citazioni vengono dal PDF |
| [Comfy API](https://comfy.org/platform/comfy-api), [Comfy MCP](https://comfy.org/mcp), FAQ prezzi | — | Stesso commit | Non confrontato |
| docs.comfy.org: Partner Nodes, Model Providers, Credits, Data Retention, Concurrency, Router, API v2 | — | Repository ufficiale `Comfy-Org/docs`, commit [`adfc0fd`](https://github.com/Comfy-Org/docs/tree/adfc0fded5825c21b091009736e98fe91e165085), ancora l'ultimo il 2026-11-03 | È il sorgente da cui il sito è generato. Due pagine confrontate con i PDF della pagina viva caricati da Riccardo il 2026-11-03: «Comfy Router capabilities and limits» (21:03 UTC) e «Comfy API v2 Overview» (21:02 UTC). **Stesso testo.** Mancano solo le parti che la modalità lettura del browser non stampa: blocchi di codice, riquadri «Note», schede «Next» |
| [ComfyUI](https://github.com/Comfy-Org/ComfyUI): `LICENSE` e `README.md` | GPL-3.0 | Repository ufficiale, commit [`2c75dc1`](https://github.com/Comfy-Org/ComfyUI/tree/2c75dc1b379a59e0880619d029607af5169a62ef) del 2026-11-03 | È il repository stesso |

Il commit `cca126a` è l'ultimo in cui il sito era pubblico. Il commit
successivo, `59201a9` («chore(website): remove the migrated website from the
frontend (#21861)»), lo ha spostato in `Comfy-Org/comfy-website`, che è
privato. I PDF della pagina viva confermano che dal 26 ottobre a oggi Termini
e accordo Enterprise non sono cambiati di una parola. Sulla pagina del Router
è cambiata una sola cosa: la FAQ su BYOK. La pagina commerciale Enterprise
(`comfy.org/enterprise`, diversa dall'accordo) invece è stata riscritta.
Comfy API, Comfy MCP e le FAQ prezzi restano senza conferma.

Negli indirizzi email del sorgente, `{'@'}` è l'escape di vue-i18n per `@`.
Qui sotto è scritto `@`.

---

## 1 · Terms of Service

<https://www.comfy.org/terms-of-service> — in vigore dal 13 maggio 2026. Valgono
per il tuo account self-serve: l'«Order Form» include «the online sign-up
flow».

### Introduzione

> These Comfy Terms of Service (the “Agreement”) are made available by Comfy
> Organization, Inc., a Delaware corporation (“Comfy”) and set forth your
> rights and obligations when accessing the Comfy Products (as defined below).

> The Agreement is entered into by and between Comfy and the entity or person
> accessing the Comfy Products (“Customer” or “you”). If you are accessing or
> using the Comfy Products on behalf of your company, you represent that you
> are authorized to enter into the Agreement on behalf of your company.

### §1 Definitions

> “Comfy API” means the application programming interface and related
> developer tools made available by Comfy that allow you to access and execute
> visual AI workflows programmatically as production endpoints from within your
> own applications or systems.

> “Comfy Products” means Comfy Cloud, Comfy API, Comfy Enterprise and other
> products, software, features, tools, and functionality made available by
> Comfy to you under these Terms of Service, excluding any Comfy OSS.

> “Customer Data” means electronic data and information submitted or generated
> by Customer in connection with its use of the Comfy Products, including all
> Inputs and Outputs.

> “Order Form” means the online sign-up flow, order form or other ordering
> document entered into or otherwise agreed by Customer that references this
> Agreement.

> “User” means Customer’s or Customer’s Affiliates’ employees and contractors
> who are authorized by Customer to access and use the Comfy Products on
> Customer’s or Customer’s Affiliates’ behalf according to the terms of this
> Agreement.

**Come lo leggo:**

- Il Router non è nominato, ma rientra in «other products … features, tools,
  and functionality».
- La «Comfy API» è quella dei *workflow*. «From within your own applications»
  dice da dove la chiami, non per chi: il limite degli scopi interni resta.
- I tuoi clienti **non sono «Users»**: non sono dipendenti né collaboratori.

### §2 Comfy Products

**Right to Access and Use Comfy Products.**

> Subject to your compliance with all of the terms and conditions of this
> Agreement, Comfy grants you and your Users a non-exclusive,
> non-sublicensable, non-transferable right during the term of this Agreement
> to access and use the Comfy Products as set forth in the applicable Order
> Form for your internal business purposes.

È la clausola che decide.

- **Il perimetro:** il diritto è tuo e dei tuoi Users, non trasferibile né
  sublicenziabile, per scopi interni.
- **La leva:** «as set forth in the applicable Order Form» è il punto in cui
  un accordo scritto può allargare quel perimetro.

**Customer Data.**

> As between Comfy and Customer, Customer retains all right, title, and
> interest in and to any data, images, videos, prompts, models, workflows,
> nodes, parameters, or other materials submitted or uploaded by Customer to
> the Comfy Products (“Input”), as well as any images, videos, designs, or
> other visual content generated through Customer’s use of the Comfy Products
> as a result of processing Customer’s Input (“Output”). Customer acknowledges
> that due to the nature of artificial intelligence, Comfy may generate the
> same or similar Output for other customers, and Customer shall have no right,
> title, or interest in or to Output generated for any other customer.

**I render sono tuoi**, e Comfy non pone limiti alla loro vendita. È la base
del caso A.

**No AI Training.**

> Comfy will not use Input or Output to train generative AI or diffusion
> models. Comfy may, however, collect and use limited metadata derived from
> Customer’s use of the Comfy Products, such as prompt classifications,
> workflow structures, and node configurations, to improve the performance,
> functionality, and user experience of the Comfy Products.

**Partner Nodes.**

> Certain features of the Comfy Products allow you to access third-party AI
> model providers (“Partner Nodes”) through Comfy. When you use a Partner Node,
> Comfy proxies your request to the applicable third-party provider,
> transmitting the information necessary to fulfill your request, including
> prompts, images, models, and parameters. Comfy does not transmit your
> identity or account information to third-party providers in connection with
> Partner Node requests. Your use of Partner Nodes is subject to the terms and
> policies of the applicable third-party provider, and Comfy is not responsible
> for the data practices of such providers. Usage of Partner Nodes is metered
> and billed through Comfy.

Sopra i Termini di Comfy valgono anche quelli di Google, BFL, OpenAI e
BytePlus (`docs/termini-comfy-rivendita.md`, sezione 2).

**Modification of Comfy Products.**

> Comfy may, at any time and in its sole discretion, modify, update, enhance,
> restrict, suspend, or discontinue the Comfy Products, in whole or in part,
> including by changing or removing features, functionality, endpoints,
> specifications, documentation, access methods, usage limits, or
> availability. […] Customer acknowledges that its use of the Comfy Products
> is at its own risk and that it should not rely on the continued availability
> of any aspect of the Comfy Products.

**Data Retention and Deletion.**

> Comfy retains Customer Data for as long as your account remains active or as
> otherwise necessary to provide the Comfy Products, comply with applicable
> legal obligations, resolve disputes, and enforce this Agreement. Specific
> retention periods for different categories of Customer Data are set forth in
> Comfy’s retention documentation, available at
> docs.comfy.org/support/data-retention, as updated from time to time. You may
> request deletion of your account and associated Customer Data by contacting
> Comfy at legal@comfy.org. […] (iii) aggregated or de-identified data derived
> from your use of the Comfy Products may be retained indefinitely.

### §3 Customer Responsibilities

**Registration.**

> You agree to be responsible for the security of your account. You accept that
> you are solely responsible for all activities that take place through your
> account, and that failure to limit access to your devices or systems may
> permit unauthorized use by third parties.

**General Technology Restrictions** (per intero):

> You agree that you will not, directly or indirectly: (i) sublicense the Comfy
> Products for use by a third party; (ii) reverse engineer or attempt to
> extract the source code or underlying methodology from the Comfy Products or
> any related software, except to the extent that this restriction is
> expressly prohibited by Applicable Laws; (iii) use or facilitate the use of
> the Comfy Products for any activities that are prohibited by Applicable Laws
> or otherwise; (iv) bypass or circumvent measures employed to prevent or limit
> access to the Comfy Products; (v) use the Comfy Products to create a product
> or service competitive with Comfy’s products or services; (vi) create
> derivative works of or otherwise create, attempt to create or derive, or
> knowingly assist any third party to create or derive, the source code
> underlying the Comfy Products; or (vii) otherwise use or interact with the
> Comfy Products for any purpose not expressly permitted under this Agreement.

Come pesano i punti sui quattro casi:

- **(i):** pesa su B, C e D. «Directly or indirectly» copre anche il cliente
  che usa Comfy attraverso il tuo server.
- **(v):** chiude C e la variante aperta di D. Un'API o un MCP che rivende
  generazioni fa concorrenza a Comfy Router e a Comfy MCP.
- **(vii):** chiude tutto ciò che il testo non permette. Il testo non permette
  di servire clienti terzi.

**Acceptable Use; Prohibited Customer Data** (i punti che toccano AIRENDER):

> Customer is solely responsible for ensuring that all Input submitted to the
> Comfy Products complies with all Applicable Laws, and Customer agrees that it
> will not, and will not permit any third party to submit to Comfy or the Comfy
> Products or otherwise use the Comfy Products to create: […] (iv) any Customer
> Data that infringes or misappropriates the intellectual property rights,
> privacy rights, or publicity rights of any third party, including without
> limitation by submitting models, images, or other materials without the
> right to do so; (v) any content or information that is intentionally
> deceptive or misleading, including without limitation synthetic media
> designed to impersonate a real individual without their consent; […]

Anche con un accordo, **di quello che caricano i tuoi clienti rispondi tu**:
uno screenshot di Google Earth, la foto di un progetto altrui.

### §4 Payment

**Plans; Fees; Free Tier** (ultima parte):

> You are responsible for all usage under your account, including usage by
> your Users and under your credentials and API keys.

**Prepaid Credits.**

> Customer may prepay for usage credits (“Credits”) which may be applied toward
> usage of the Comfy Products at the rates set forth on Comfy’s pricing page.
> Except for documented billing errors or similar service issues attributed to
> Comfy, all purchases of Credits are final and non-refundable, and Comfy will
> not issue refunds or credits for any unused, partially used, or remaining
> Credits under any circumstances, including upon termination or expiration of
> Customer’s account. Comfy reserves the right to modify the pricing or Credit
> redemption rates applicable to future Credit purchases upon reasonable
> notice, but any Credits purchased prior to such modification will be honored
> at the rates in effect at the time of purchase.

**Taxes; Price Changes; No Refunds** (ultima frase):

> Except as required by law or expressly stated in the Order Forms, all fees
> are non-cancellable and non-refundable.

**Late Payments; Suspension** (ultima frase):

> Comfy may suspend or limit access to the Comfy Products (including
> throttling, disabling API keys, or downgrading to the Free Tier) for
> non-payment of undisputed amounts after providing commercially reasonable
> notice and an opportunity to cure, unless Comfy reasonably determines
> immediate suspension is necessary to protect the Comfy Products or comply
> with Applicable Laws.

### §5 Term; Termination

**Termination of Agreement.**

> You may stop using the Comfy Products at any time with or without notice.
> This Agreement will remain in effect until terminated in accordance with this
> Section. Either party may terminate this Agreement for convenience upon
> written notice to the other; […]

**Effect of Termination.**

> Upon any termination or expiration of an Order Form (or this Agreement, if no
> Order Form is then in effect), Customer will promptly cease all use of the
> Comfy Products under the terminated arrangement and, if applicable, any
> continued use must be pursuant to a then-effective Order Form or other
> written authorization from Comfy. Comfy may suspend or terminate Customer’s
> access to the Comfy Products, or discontinue the Comfy Products or any
> portion or feature thereof, at any time; provided that Comfy will not
> terminate an unexpired Order Form for convenience unless the applicable Order
> Form expressly permits it, and any suspension or termination may be
> implemented immediately if Comfy reasonably determines that Customer’s use
> poses a security risk, violates this Agreement, or materially degrades the
> Comfy Products. Except as expressly set forth in an Order Form, Comfy will
> have no liability or other obligation to Customer arising out of or relating
> to any termination, suspension, or discontinuance under this Section.

Due cose per chi vende un servizio sopra Comfy:

- **Senza un Order Form a termine, Comfy può chiudere «at any time».** Il
  contratto con i tuoi clienti dura 12 mesi; quello con Comfy no.
- **Il testo stesso nomina gli strumenti:** «Order Form or other written
  authorization from Comfy».

### §6 Confidentiality (per i clienti sotto NDA)

> Confidential Information of Customer includes Customer Data; […]

**Data Security.**

> In the event Comfy becomes aware of a confirmed security breach that results
> in unauthorized access to or disclosure of Customer Data, Comfy will notify
> Customer without undue delay and will provide reasonable cooperation to
> assist Customer in investigating and mitigating the effects of such breach.

### §8 Disclaimer e §9 Limitation of Liability

> THE Comfy Products AND OUTPUT ARE PROVIDED “AS IS” WITHOUT ANY WARRANTY OF
> ANY KIND. […] YOU AGREE AND ACKNOWLEDGE THAT YOUR USE OF ANY OUTPUT PROVIDED
> BY THE Comfy Products IS AT YOUR OWN RISK.

> TO THE EXTENT PERMITTED BY LAW, THE TOTAL LIABILITY OF Comfy, AND ITS
> SUPPLIERS AND DISTRIBUTORS, FOR ANY CLAIM UNDER THIS AGREEMENT, INCLUDING FOR
> ANY IMPLIED WARRANTIES, IS LIMITED TO THE GREATER OF (A) ONE THOUSAND DOLLARS
> ($1,000); AND (B) THE AMOUNTS PAID OR PAYABLE BY CUSTOMER IN THE SIX (6)
> MONTHS PRECEDING THE DATE OF THE CLAIM.

Quello che prometti ai tuoi clienti non lo copre Comfy oltre questo tetto.

### §10 Indemnification

> You agree to defend, indemnify, and hold harmless Comfy Organization, Inc.
> and its officers, directors, employees, contractors, and agents from and
> against any and all third-party claims, demands, actions, suits, or
> proceedings, and any resulting losses, damages, liabilities, costs, and
> expenses (including reasonable attorneys’ fees) to the extent resulting from
> your Customer Data or your breach of this Agreement. […]

### §11 Governing Law and Dispute Resolution

> This Agreement and any dispute, claim, or controversy arising out of or
> relating to this Agreement, the Comfy Products, or the parties’ relationship
> (each, a “Dispute”), shall be governed by and construed in accordance with
> the laws of the State of California, […]

> […] any Dispute shall be finally resolved by binding arbitration administered
> by JAMS […]. The arbitration shall be seated in San Francisco, California,
> and conducted in English before one (1) arbitrator.

> To the fullest extent permitted by Applicable Law, any Dispute must be
> brought by you within one (1) year after the claim or cause of action first
> arose, or it is permanently barred.

### §12 Miscellaneous

**Assignment; Delegation.**

> Neither party hereto may assign or otherwise transfer this Agreement, in
> whole or in part, without the other party’s prior written consent, […]

**Amendment; Waiver.**

> Comfy reserves the right in its sole discretion and at any time and for any
> reason to modify this Agreement. Any modifications to this Agreement shall
> become effective upon the date of posting. Your continued use of, or access
> to, the Comfy Products after an update goes into effect will constitute
> acceptance of the update. […]

**Entire Agreement.**

> This Agreement comprises the entire agreement between you and Comfy with
> respect to its subject matter, and supersedes all prior and contemporaneous
> proposals, statements, sales materials or presentations and agreements (oral
> and written). No oral or written information or advice given by Comfy, its
> agents or employees will create a warranty or in any way increase the scope
> of the warranties in this Agreement.

Questa clausola ha due conseguenze:

- **Il marketing non conta:** le frasi delle pagine prodotto (sezione 3) non
  allargano il diritto del §2.
- **Il permesso va scritto:** un «sì» detto da qualcuno di Comfy non basta.
  Deve stare in un documento.

### §13 Contact Us

> If you have any questions regarding this Agreement or the Comfy Products,
> please contact us at: legal@comfy.org.

---

## 2 · Enterprise Customer Agreement (modello)

<https://comfy.org/enterprise-msa/> — «Effective Date: May 22, 2026». Si firma.
Non si accetta online.

> This Enterprise Customer Agreement (the “Agreement”) is entered into by and
> between Comfy Organization, Inc., a Delaware corporation (“Comfy”), and the
> entity identified on the applicable Order Form (“Customer”), and is effective
> as of the date set forth on the applicable Order Form (the “Effective Date”).

**I divieti sono gli stessi dei Termini.** Definizione di «User», diritto «for
Customer’s internal business purposes» e restrizioni (i)–(vii) sono identici,
con «Customer» al posto di «you»:

> **Right to Access and Use Comfy Products.** Subject to Customer’s compliance
> with all of the terms and conditions of this Agreement, Comfy grants Customer
> and Customer’s Users a non-exclusive, non-sublicensable, non-transferable
> right during the term of this Agreement to access and use the Comfy Products
> as set forth in the applicable Order Form for Customer’s internal business
> purposes.

> **General Technology Restrictions.** Customer agrees that it will not,
> directly or indirectly: (i) sublicense the Comfy Products for use by a third
> party; […] (v) use the Comfy Products to create a product or service
> competitive with Comfy’s products or services; […] or (vii) otherwise use or
> interact with the Comfy Products for any purpose not expressly permitted
> under this Agreement.

**Cosa cambia rispetto ai Termini:**

- Si risolve per violazione solo dopo **30 giorni per rimediare**:

  > Each party may also terminate this Agreement or the applicable Order Form
  > upon written notice in the event (a) the other party commits any material
  > breach of this Agreement or the applicable Order Form and fails to remedy
  > such breach within thirty (30) days after written notice of such breach
  > […]

- **Dati cancellati entro 60 giorni** dalla fine:

  > Upon expiration or termination of this Agreement, Comfy will delete
  > Customer Data from its primary production systems within sixty (60) days.

- **Comfy tiene indenne il cliente** per violazioni di brevetti, copyright e
  segreti commerciali USA dei prodotti. Fra le esclusioni c'è proprio l'uso
  delle uscite fuori dal contratto:

  > Comfy will have no liability or obligation with respect to any Claim to the
  > extent such Claim is caused by […] (B) Customer’s use of any outputs,
  > generated content, or models in a manner not authorized under this
  > Agreement; […]

- **Le modifiche valgono solo se firmate da tutti e due.** Nei Termini, Comfy
  cambia da sola:

  > **Amendment; Waiver.** No amendment or modification to this Agreement, nor
  > any waiver of any rights hereunder, will be effective unless assented to in
  > writing by both parties. […]

- **Il testo pubblicato è solo un modello:**

  > This document reproduces the current template of the Enterprise Customer
  > Agreement for reference only. The executed Agreement between Comfy and
  > Customer, together with any signed Order Forms, governs the relationship
  > between the parties. To request an executable copy, please contact
  > sales@comfy.org.

**Come lo leggo.** Firmare l'Enterprise non basta: il modello vieta le stesse
cose. Serve che l'**Order Form** firmato contenga una clausola che permetta di
servire i propri clienti (proposta nella sezione 7). L'Enterprise rende
quella clausola stabile: Comfy non può cambiarla da sola, e una violazione
contestata lascia 30 giorni per rimediare.

---

## 3 · Pagine prodotto (marketing, non contratto)

### Comfy Router

<https://comfy.org/platform/router>. Niente su rivendita o clienti terzi.
Contano queste frasi:

> Run the same model on fal, Runware, or Wavespeed, and switch with one
> parameter when one is rate limited or another is cheaper. Comfy never
> switches the route for you, and every job reports the provider that ran it.

> **Does Comfy pick the provider for me?** Not at launch. You name the provider
> and Comfy runs it there. Nothing is swapped behind your back.

> **What happens if my provider is unavailable?** The request fails on the
> provider you chose, with no silent substitution. Ordered fallback is on the
> roadmap: a backup list, used only when a retry is known to be safe.

> **How long do you keep my inputs and outputs?** Inputs are kept for 24 hours
> after upload and outputs for 24 hours after generation. Then they’re deleted.

> **Where do my API keys, usage, and billing live?** On the Developer Platform.
> Your API keys, run history, credits, and payments live there.

> **Can I bring my own provider key?** BYOK is available for select models on
> Enterprise. Access is enabled by request.

Questa FAQ c'era il 2026-10-26, ma **nella pagina viva del 2026-11-03 non
compare**. Le altre undici risposte sono stampate, compresa la 5, che ha
anche un link. Sulla pagina BYOK resta solo nella roadmap, sotto «Coming soon
to the same API.»:

> Use your own provider key for supported models while keeping the same Comfy
> Router integration.

Quindi, per il Router, BYOK oggi è annunciato, non offerto. La FAQ prezzi del
sito (sezione 3, sotto) lo dava come disponibile su Enterprise per Runway e
Google Gemini, ma quella pagina non è stata confrontata con il sito di oggi.

> **Do I need a Comfy subscription?** No. Router runs on credits. Add credits
> and start calling models.

E dalla roadmap:

> […] so a pipeline you build in ComfyUI ships to your app as one request.

**La pagina contraddice l'API reference** del Router
(`development/comfy-router/reference`, sezione 4). La reference dice che
`fallback_provider` «Omitted, or any value other than `false`, leaves fallback
on». E dice che la catena Gemini di `vertexai` «can hand the call to a
different vendor that no header names». Per il §12 conta quello che il
servizio fa, non la pagina: `fallback_provider=false` resta, e la destinazione
«Google» resta non garantita.

### Comfy API e Comfy MCP

<https://comfy.org/platform/comfy-api>, per i workflow, non per il Router:

> Deploy your ComfyUI workflows as APIs behind customer-facing products,
> internal tools, and automated creative pipelines. Build the experience your
> users need without exposing the graph.

> At Silverside, Comfy workflows are where our creative expertise becomes
> infrastructure. We build production pipelines then serve them through Comfy
> API so our clients can run the same proven workflows at scale.

<https://comfy.org/mcp>:

> Comfy MCP exposes the full ComfyUI engine over the Model Context Protocol.
> Generate images, video, audio, and 3D from Claude Code, Claude Desktop, and
> any MCP-compatible client.

**Come lo leggo.** Comfy *vende* l'idea di prodotti per i clienti costruiti
sopra di sé, e mostra un cliente che serve i suoi clienti. Commercialmente è
un buon segno: una richiesta di autorizzazione ha buone probabilità di
ottenere un sì. Contrattualmente non conta (§12 Entire Agreement). Il fatto
che Comfy venda un suo MCP rende un MCP pubblico costruito sui crediti Comfy
un «product or service competitive» (§3 (v)).

### Pagina Comfy Enterprise (pagina viva, 2026-11-03)

<https://comfy.org/enterprise/>. È la pagina commerciale, non l'accordo. Il
testo qui sotto viene dal PDF stampato da Riccardo: dopo il 2026-10-26 la
pagina è stata riscritta, e non c'è un sorgente pubblico con cui confrontarla.
Niente su rivendita o clienti terzi. Le frasi che contano:

> Procurement
> A DPA and enterprise agreement are available.
> Processing is in the United States on Google Cloud.

> SOC 2
> Type II report available on request.

> Data control
> For local deployments, Comfy Workflows and outputs stay where they run.
> Comfy does not train on customer data.

> Model policy and BYOK
> Choose the partner, open, and private models teams can use. Bring supported
> provider keys and existing contracts.

> On Cloud, every model is licensed for commercial use. On local, licenses vary
> by provider and commercial terms are available on request. Comfy is also an
> official reseller for MiniMax commercial licenses.

> Bring one known-good environment or the production requirement your team
> needs to scale. We will map deployment, governance, capacity, commercial
> terms, and the right implementation path.

**Come lo leggo.**

- **Un DPA esiste.** Risponde in parte al rischio 4 di
  `docs/termini-comfy-rivendita.md`: l'accordo sul trattamento dei dati c'è,
  almeno con l'Enterprise. Il trattamento avviene negli Stati Uniti, su Google
  Cloud, quindi è un trasferimento fuori dall'UE da dichiarare ai clienti.
  Il DPA non è stato letto.
- **BYOK fa parte dell'offerta Enterprise** («Bring supported provider
  keys»). La pagina non dice quali chiavi né se valgono nel Router, che lo
  mette ancora in roadmap.
- **La pagina parla di «teams» e «organization», cioè di uso interno**, in
  linea con il §2 dei Termini. Dice però che i termini commerciali si
  definiscono caso per caso («We will map … commercial terms»). È lì che va
  chiesta la clausola per servire i propri clienti.

### FAQ prezzi ed Enterprise del sito (al 2026-10-26)

Queste FAQ erano nel sorgente del 2026-10-26. **Nella pagina Enterprise viva
non ci sono più**, perché è stata riscritta. Se restino nella pagina prezzi
non è stato verificato.

> **Does Comfy support BYOK (bring your own key)? Can I bring my own provider
> key?** Yes. We support BYOK for **Runway and Google Gemini** today, and we
> can add other providers on request for Enterprise customers. BYOK is turned
> on per workspace, and Partner Node calls that run on your own key are billed
> by that provider directly instead of drawing your Comfy credits.

> **What if I'm running Comfy at scale?** For teams running Comfy in production
> and at scale, Enterprise adds higher API rate limits, advanced security, and
> dedicated support. […] reach out at enterprise@comfy.org.

> **What does Comfy Enterprise include?** […] a commercial-use guarantee on
> every model in Comfy Cloud. […]

---

## 4 · docs.comfy.org

Commit `adfc0fd` di `Comfy-Org/docs`.

### Partner Nodes — FAQ

<https://docs.comfy.org/tutorials/partner-nodes/faq>

> **Are unused credits refundable?** Currently, we do not support refunds for
> credits.

> **Do credits expire?** Yes, the expiration depends on the type of credits:
> - **Monthly credits**: Expire at the end of your billing period
> - **Top-up credits**: Expire 1 year from the date of purchase

> **Can credits be transferred or shared?** No, your credits cannot be
> transferred to other users and are limited to the currently logged-in
> account, but we do not restrict the number of devices that can log in.

> **Is there content moderation for Partner Nodes?** Partner Nodes send your
> inputs (prompts, images, and other content) to third-party providers for
> processing. These providers enforce their own content moderation policies.

Vendere crediti AIRENDER non è trasferire crediti Comfy: sono un'unità tua.
Ma il divieto conferma l'impostazione: **un account, un titolare**.

### Model Providers

<https://docs.comfy.org/tutorials/partner-nodes/model-providers>

> This page tracks the model providers behind Comfy's Partner Nodes in one
> table: verification status, commercial licensing for Cloud and local use, and
> data residency. It's a structure we're actively filling in, not a finished
> reference.

> **Verified**: "Yes" means Comfy has a signed contract with this provider. The
> contract says the provider does not use your content to train or improve its
> models when you use it through Comfy. The provider also gives IP indemnity to
> Comfy.

> **Commercial License (Cloud)**: whether commercial use through Comfy Cloud is
> confirmed for that provider's models.

| Fornitore (modello AIRENDER) | Verified | Commercial License (Cloud) | Data Residency |
|---|---|---|---|
| Google (Nano Banana 2 e Pro) | Yes | ✓ | Pending |
| Black Forest Labs (FLUX.1 Kontext) | Yes | ✓ | US, EU, Israel |
| Singdata (ByteDance: Seedream, Seedance) | Yes | ✓ | Malaysia, EU (some models) |
| OpenAI (GPT Image 2) | assente dalla tabella | — | — |

> Additional data residency options may be available for Enterprise customers.

Il sito, però, elenca GPT Image 2 fra i modelli «cleared for commercial use»
su Comfy Cloud. «Commercial use» vuol dire che le immagini si possono usare
commercialmente. Non vuol dire che si possa dare il servizio a terzi: quello
lo decide il §2 dei Termini.

### Credits

<https://docs.comfy.org/interface/credits>

> **Can I share my credits with other users?** You can sign into the same
> account on multiple devices. Sharing credits with other user accounts is not
> supported. On Cloud Team workspaces, members share the workspace balance
> under owner-set limits.

> **Can credits go negative?** Credits are not intended as a credit line.
> Partner Nodes sometimes report cost after execution, so one run can leave a
> temporary negative balance. While the balance is negative, Partner Nodes stay
> blocked until you top up.

### Concurrency Limits

<https://docs.comfy.org/tutorials/partner-nodes/concurrency-limits>

> Your concurrency limit is based on your lifetime paid spend, and applies at
> the platform level across all endpoints you call.

> **Custom limits override the table.** If our team has set a specific limit on
> your account, for example for an enterprise arrangement or a policy
> restriction, it takes precedence over every spend-based row, including down
> to 0 (Partner Node access disabled).

I tuoi clienti dividono un limite solo: 5 render contemporanei dopo la prima
ricarica, 10 da 100 $ spesi in tutto. E Comfy può portarlo a 0.

### Data Retention

<https://docs.comfy.org/tutorials/partner-nodes/data-retention>

> All Partner Node media files are automatically deleted **24 hours** after
> they are created.

<https://docs.comfy.org/support/data-retention>, riga «Customer content»:

> Prompts, workflows, outputs, and other content you create or upload |
> Retained for as long as necessary to operate, analyze, and improve the
> service

### Comfy API v2 Overview (confrontata con la pagina viva)

<https://docs.comfy.org/api-reference/v2/overview>, per i workflow. È la
pagina che descrive come un'applicazione serve i propri utenti:

> Three different lifetimes govern "the URL for my output" and they are not
> the same number. Any application that shows outputs to its own users has to
> plan for all three.

> The practical consequence: `Output.url` is not a shareable link. Put it in an
> `<img src>` that your users' browsers load and they get a `401`, because
> their browser does not carry your API key. The signed URL is the one you can
> hand out.

> ### Showing an Output in Your Own Product
>
> To still be showing an output a day later, do one of these:
>
> - **Re-host the bytes.** Download the output once and copy it into your own
>   storage. Most applications end up here.
> - **Re-mint on demand.** […]
> - **Proxy it.** Fetch `Output.url` from your own backend, which already
>   holds the API key, and stream the bytes to your user.

E sul Router, in fondo alla stessa pagina:

> Comfy API v2 runs workflows as durable jobs you submit and poll. For direct
> model calls (one partner model, one request, the model's native input and
> output), see the Comfy Router. Review the Router limitations first. Router
> is not generally available yet.

Sulla strada E, cioè ComfyUI open source (sezione 5):

> **Open-source ComfyUI, via the proxy.** A self-hosted ComfyUI speaks v2
> through comfy-api-proxy, a small open-source service that runs alongside
> it:

**Come lo leggo.**

- **Lo schema di AIRENDER è descritto come uso normale.** «Your own backend,
  which already holds the API key», «stream the bytes to your user»: server
  con la chiave, immagini girate al cliente. È proprio AIRENDER, ma per i
  workflow e non per il Router. Come detto nella Risposta, non cambia il
  contratto. È però l'argomento migliore per la richiesta a Comfy.
- **Il Router non è ancora disponibile a tutti in forma definitiva.**
  Insieme al §2 Modification, che permette a Comfy di cambiare o chiudere
  qualunque prodotto «with or without notice», è un rischio in più per un
  servizio a pagamento costruito sopra. La API v2 invece promette che le
  modifiche dentro v2 sono solo aggiunte (riquadro «Note» del sorgente: «Changes
  within v2 are additive; breaking changes ship as v3»).
- **ComfyUI open source parla la stessa API dei workflow** di Comfy Cloud,
  attraverso un proxy open source. Passare dall'uno all'altro costerebbe poco
  nel codice. Non si applica ai modelli dei Partner Nodes.

### Comfy Router: capabilities and limits (confrontata con la pagina viva)

<https://docs.comfy.org/development/comfy-router/limitations>. Niente su
rivendita o terzi. Per AIRENDER conta questa frase, già usata in
`docs/termini-comfy-rivendita.md`:

> The request-rate limit applies to invocation and catalog/schema reads,
> including requests refused before generation. It follows the authenticated
> caller, not the source IP.

Con una chiave sola, il «caller» è uno: tutti i clienti AIRENDER dividono lo
stesso limite.

### Chiave

<https://docs.comfy.org/development/api-development/getting-an-api-key>

> For security, never share your API Key or commit it to version control.

<https://docs.comfy.org/development/comfy-router/quickstart>

> Keep API keys on your server or in your local environment.

---

## 5 · ComfyUI open source

<https://github.com/Comfy-Org/ComfyUI>, letto il 2026-11-03 al commit
`2c75dc1` (ramo `master`): licenza e README.

**I Termini di Comfy lo escludono.** Dal §1 e dal §2 dei Termini:

> “Comfy OSS” means the open-source software, source code, libraries, tools,
> and related components made available by Comfy under one or more open source
> licenses, including the software repositories published by Comfy at
> https://github.com/Comfy-Org, as updated, modified, or supplemented from time
> to time. For the avoidance of doubt, Comfy OSS does not include any
> proprietary software, infrastructure, or functionality made available by
> Comfy under these Terms of Service or in connection with any commercial
> product or offering.

> You may use Comfy OSS under the terms of the applicable Open Source
> License(s) governing each respective component, as identified in the
> corresponding source code repository, rather than under these Terms. Nothing
> in these Terms shall be construed to limit, supersede, or modify any rights
> or obligations arising under an applicable Open Source License. If you choose
> to use the Comfy Products in conjunction with Comfy OSS, these Terms apply
> solely to your use of the Comfy Products and not to the Comfy OSS itself.

**La licenza è la GPL-3.0** (`LICENSE`: «GNU GENERAL PUBLIC LICENSE Version 3,
29 June 2007»). Due frasi decidono il caso di un servizio:

> To "convey" a work means any kind of propagation that enables other parties
> to make or receive copies.  Mere interaction with a user through a computer
> network, with no transfer of a copy, is not conveying.

> You may make, run and propagate covered works that you do not convey,
> without conditions so long as your license otherwise remains in force.

**Come lo leggo.** ComfyUI può girare su un tuo server o su una GPU in
affitto, e i clienti possono usarlo attraverso AIRENDER senza riceverne una
copia: nessun limite di Comfy e nessun obbligo della GPL. È la GPL-3.0, non la
AGPL: l'uso in rete non obbliga a pubblicare il codice. Gli obblighi scattano
se **distribuisci** ComfyUI, o un'opera derivata, per esempio dentro il
pacchetto del plugin. In quel caso servono il codice sorgente e la stessa
licenza.

**Tre limiti:**

1. **I Partner Nodes tornano sotto i Termini.** Dal README:

   > Partner nodes provide access to the best closed source models such as
   > Nano Banana, Seedance, Hunyuan3D, etc.

   > Use `--offline` to disable the optional paid Comfy API nodes and force all
   > built-in functionality to stay offline, or `--disable-partner-nodes` to
   > only disable the API nodes.

   I Partner Nodes chiamano il servizio a pagamento di Comfy con i crediti:
   sono «Comfy Products», e vale di nuovo il §2 «internal business purposes».
   Nano Banana, GPT Image, Seedream e Seedance esistono solo come Partner
   Nodes. **Per questa strada i modelli di oggi non ci sono.**
2. **Ogni modello ha la sua licenza.** ComfyUI è il motore; i pesi dei
   modelli hanno licenze proprie. Ognuna deve permettere l'uso commerciale e
   il servizio a terzi. FLUX.1 Kontext [dev], per esempio, ha una licenza
   commerciale a parte di BFL («Self-Hosted Commercial License»). **Le licenze
   dei singoli modelli non sono state lette.**
3. **Serve una GPU.** ComfyUI in locale è stato tagliato il 2026-09-14 perché
   la macchina disponibile ha 4 GB (PRD, sezione 10). Una GPU in affitto è un
   fornitore in più che riceve le viste dei clienti (DPA, paese). Comfy Cloud,
   cioè ComfyUI ospitato da Comfy, è invece un «Comfy Product»: vale di nuovo
   il §2.

**Conclusione.** È l'unica strada in cui i Termini di Comfy non contano
affatto. Il prezzo: modelli aperti al posto di Nano Banana, una GPU da pagare
e gestire, e la tenuta della geometria da rimisurare da capo con il banco di
prova.

---

## 6 · Permesso, vietato, accordo scritto

### Permesso

- **Usare Comfy, Router compreso, per la tua attività**, tu e i tuoi
  dipendenti e collaboratori (§1 «User», §2 Right to Access).
- **Far girare ComfyUI open source su un tuo server per i clienti**, con
  modelli aperti e senza Partner Nodes: i Termini non si applicano (§2 Comfy
  OSS). Valgono la GPL-3.0 e la licenza di ogni modello (sezione 5).
- **Vendere le immagini che generi:** sono tue (§2 Customer Data). Restano i
  termini dei fornitori (§2 Partner Nodes) e i limiti d'uso del §3.
- **Tenere la chiave sul server**, mai al cliente (docs, Quickstart).
- **Comprare crediti prepagati** e usarli per 12 mesi (§4; FAQ). Non si
  rimborsano.

### Vietato

- **Far usare Comfy a terzi:** clienti, rivenditori, sviluppatori, «directly
  or indirectly» (§3 (i)).
- **Un'API pubblica o un MCP pubblico che rivende generazioni:** è un prodotto
  concorrente di Comfy Router e Comfy MCP (§3 (v)), oltre a (i) e (vii).
- **Condividere crediti o chiavi con altri account** (FAQ, Credits).
- **Ogni uso non espressamente permesso** (§3 (vii)).
- **Per conto di chiunque, generare** contenuti che violano diritti altrui o
  che impersonano persone reali (§3 Acceptable Use (iv), (v)).

### Serve un accordo scritto

- **Il modello AIRENDER di oggi (caso B):** il cliente avvia la generazione
  dall'app, attraverso il tuo server e i tuoi crediti. Serve un Order Form o
  una «written authorization from Comfy» (§2, §5). Meglio dentro un accordo
  Enterprise, dove le modifiche valgono solo se firmate da entrambi (MSA §11).
- **La rivendita Serteco**, se le licenze vendute danno ai clienti
  generazioni Comfy: è lo stesso caso B, con un intermediario in più.
- **BYOK Gemini:** la tua chiave Google dentro il Router. Solo «on request»
  per Enterprise, secondo la FAQ prezzi del sito al 2026-10-26. La pagina
  Enterprise viva lo conferma in generale («Bring supported provider keys and
  existing contracts»). Sulla pagina viva del Router, invece, il 2026-11-03 è
  solo nella roadmap («Coming soon»). Non cambia i divieti del §3: cambia solo
  chi fattura i modelli.
- **Il DPA:** esiste («A DPA and enterprise agreement are available»,
  pagina Enterprise viva). Va chiesto e letto prima di dichiararlo ai clienti.
- **Un limite di concorrenza personalizzato** e **la residenza dei dati in
  UE**: «enterprise arrangement» (Concurrency; Model Providers).
- **La certezza del fornitore per i modelli `vertexai`:** non è nei testi.
  Va chiesta (`docs/termini-comfy-rivendita.md`, sezione 6, domanda 2).

---

## 7 · Cosa fare

1. **Nessuna fattura per il caso B** finché non c'è un'autorizzazione scritta.
   Il caso A si può vendere da subito: generi tu e consegni le immagini.
2. **Scrivere a `sales@comfy.org`** (copia esecutiva dell'Enterprise) o a
   `enterprise@comfy.org`, con `legal@comfy.org` per l'interpretazione dei
   Termini. La mail pronta è in `docs/termini-comfy-rivendita.md`, sezione 6.
   La domanda 1 ora può citare le clausole: §2 «internal business purposes»,
   §3 (i) e (vii).
3. **Chiedere che nell'Order Form ci sia una clausola come questa.** È una
   bozza scritta qui, da far rivedere a un legale, **non un testo di Comfy**:

   ```text
   Notwithstanding Section 2 (Right to Access and Use Comfy Products) and
   Section 3 (General Technology Restrictions) (i) and (vii), Customer may
   integrate the Comfy Products, including Comfy Router, into Customer's own
   software applications and make the resulting functionality and Outputs
   available to Customer's end customers and authorized resellers, provided
   that (a) end customers do not receive Comfy API keys, Comfy accounts or
   direct access to the Comfy Products, (b) Customer remains responsible for
   all usage under its account, and (c) Customer does not offer a
   general-purpose API or model-routing service to third parties.
   ```

4. **Se Comfy dice di no:** Vertex AI diretto. I termini Google Cloud
   permettono un'applicazione propria usata da terzi
   (`docs/termini-comfy-rivendita.md`, sezione 5). Oppure ComfyUI open source
   con modelli aperti su una GPU propria (sezione 5), che però cambia i
   modelli.

---

## 8 · NON VERIFICATO

- **Le licenze dei modelli aperti** (FLUX.1 Kontext [dev], Qwen Image Edit e
  gli altri del README di ComfyUI): non lette. Decidono se la strada E è
  praticabile.
- **Un modello aperto tiene la geometria come Nano Banana 2:** non misurato.
  Per verificare: il banco di prova (`scripts/confronta_modelli.py`) su una
  GPU in affitto, con le stesse viste.

- **Il testo vivo di Comfy API, Comfy MCP e FAQ prezzi del sito:** letto al
  2026-10-26 dal repository, non confrontato con le pagine di oggi. Sono
  confrontati, e uguali, i Termini, l'accordo Enterprise, la pagina del
  Router (salvo la FAQ 10) e due pagine di docs.comfy.org. La pagina
  commerciale Enterprise è stata confrontata ed è cambiata: le sue citazioni
  vengono solo dal PDF.
- **BYOK nel Router:** la pagina Enterprise viva lo offre in generale, la
  pagina viva del Router lo mette in roadmap. Che la FAQ 10 del Router sia
  stata tolta, e non solo saltata dalla stampa, è probabile ma non provato.
  Per verificare: aprire la FAQ «Can I bring my own provider key?» in fondo a
  <https://comfy.org/platform/router>.
- **Il DPA di Comfy:** esiste, ma non è stato letto. Chi lo firma (solo
  Enterprise o anche self-serve) e quali clausole valgono per il
  trasferimento negli USA: non si sa.
- **I subresponsabili di Comfy:** l'elenco è nel Trust Center di Comfy,
  <https://app.vanta.com/comfy.org/trust/o6nu46b16iu3e7fhc41hnz/subprocessors>.
  Non letto: `app.vanta.com` è bloccato dalla rete di questa sessione. Per
  verificare: stampare la pagina in PDF, come le altre, e rimandarla
  indietro. Va confrontato con i fornitori dei modelli (Google, BFL, OpenAI,
  BytePlus) e con l'elenco dei DPA in `server/README.md`.
- **Il Router diventa disponibile a tutti, e quando:** la documentazione dice
  solo «not generally available yet». Va chiesto a Comfy insieme
  all'autorizzazione.
- **Che il caso B violi i Termini:** è una lettura del testo, non una
  sentenza. Il contratto è retto dalla legge della California e le
  controversie vanno in arbitrato JAMS a San Francisco (§11). Solo un legale,
  o una risposta scritta di Comfy, chiude la questione.
- **La legge italiana o europea a tutela di chi compra:** non toccata. Tu
  compri come impresa, quindi le tutele del consumatore probabilmente non si
  applicano.
- **L'informativa privacy di Comfy:** non letta in questa sessione. È nel
  repository, a fianco dei Termini, se serve.
