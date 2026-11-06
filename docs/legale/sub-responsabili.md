# Sub-responsabili e fornitori di AIRENDER

**Bozza, 2026-11-05; Netlify e Supabase aggiornati il 2026-11-06.** Fornitori che toccano dati dei clienti, con cosa
ricevono, dove e con quale garanzia. «Da verificare» vuol dire che la
sessione che ha scritto questa pagina non ha potuto leggere il documento del
fornitore: va controllato prima di pubblicarla.

| Fornitore | Cosa fa | Cosa riceve | Dove | Garanzia per il trasferimento | Stato |
|---|---|---|---|---|---|
| Comfy Org, Inc. | Comfy Router: passa la richiesta al modello | Immagini (senza metadati) e testo del prompt | USA | **Nessun DPA** (mail di Yoland Yan, 2026-11-05) | **Da chiudere**: chiedere DPA con SCC |
| Google LLC (Vertex AI) | Modelli Nano Banana 2 e Pro | Immagini e prompt, tramite Comfy | Endpoint «global»: regione non garantita | Contratto fra Comfy e Google; Google Cloud DPA e SCC | Da verificare: conservazione e uso dei dati con l'account di Comfy |
| Netlify, Inc. | Server (funzioni) e sito | Immagini in transito, codice licenza, email all'acquisto | Funzioni: USA, Ohio (regione predefinita del piano Free); pagine statiche dalla CDN | DPA Netlify (dentro il Self-Serve Subscription Agreement, accettato con l'account), SCC 2021/914 e certificazione DPF | Da fare: piano Pro (20 $/mese) e regione delle funzioni su Francoforte, poi nuovo deploy |
| Supabase, Inc. | Database licenze e crediti; archivio temporaneo dei risultati (48 ore) | Email, dati fiscali, impronta del codice, movimenti; immagini generate grandi | UE, Francoforte (`eu-central-1`, progetto `airender`, creato il 2026-11-06) | DPA Supabase, SCC | Da fare: firmare il DPA dal cruscotto (Organization settings > Legal documents) |
| Stripe Payments Europe, Ltd. | Pagamenti e abbonamenti | Dati di pagamento e fatturazione | UE (Irlanda), con trasferimenti a Stripe USA | DPA Stripe, SCC/DPF | Accettato con l'account |
| TeamSystem S.p.A. (Fatture in Cloud) | Fatture elettroniche | Dati fiscali | Italia | DPA TeamSystem | Da verificare |
| Sinch Mailjet SAS | Email con il codice licenza | Email, nome del piano, codice | UE (Francia) | DPA Mailjet (nei termini del servizio) | Da verificare: DPA accettato con l'account di Riccardo. Resend (USA) resta solo come alternativa nel codice, non attiva |
| Serteco | Rivenditore | Dati per attivare la licenza | Italia | Accordo di rivendita con clausola privacy | Da scrivere |

Solo i modelli del listino partono con i crediti AIRENDER (oggi Nano Banana 2
e Nano Banana Pro, entrambi Google). Altri modelli (FLUX di Black Forest Labs,
Seedream e Seedance di ByteDance) partono solo con una chiave Comfy del
cliente stesso e non passano dal nostro server.

Ogni volta che si aggiunge un fornitore, si aggiorna questa pagina **prima**
di usarlo, e i clienti con un DPA firmato ricevono un avviso (`dpa.md` §6).
