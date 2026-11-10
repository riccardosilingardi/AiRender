# Nano Banana 2 con le mappe del ControlNet: risultati del 2026-11-10

Prove fatte da Claude dal container, la sera del 10 novembre 2026. Script:
`scripts/prova_mappe_nano.py` (PR #84). Modello: `vertexai/gemini-3.1-flash-image`
(Nano Banana 2) dal Comfy Router. Le mappe vengono dal deployment
`dep-869f2345-e051-4b75-a7e5-84fa5cbd3b25.run.comfy.app`, con il solo
preprocessore e senza diffusione.

Le mappe sono tre:
- **spigoli**: Canny, soglie 0,1/0,32;
- **profondità**: Depth Anything V2, Large (vitl) se non è detto altro;
- **linee**: M-LSD.

Il prompt dedicato dice cosa è ogni immagine (si legge nei file `prompt-*.txt`).

La «%» è la quota di spigoli della vista ritrovati nel render
(`coda.misura_tenuta`). **Da sola inganna**: un render diventato nebbia ha dato
77%. Va sempre guardato il confronto prima/dopo. Ogni variante è stata fatta
**una volta sola**, e Gemini non ha un seme fisso: 1-2 punti di differenza sono
rumore.

## Risultati

| Vista | A solo vista | B + spigoli | C + 3 mappe | Altro |
|---|---|---|---|---|
| Edificio circolare 4253 (vista Allplan) | 91% | 90% | 92% | — |
| Casa colorata con alberi (schermata Allplan ritagliata) | 85% | 86% | **92%** | E spigoli + linee, senza profondità: 85% · F 3 mappe con profondità **Small**: **90%** |
| Pianta 2D da internet (preset `pianta-materica`) | **98%** | 94% | 98% | D solo ControlNet Z-Image (spigoli 0,6 + profondità 0,4): 85% |

Cosa si vede a occhio:

- **Edificio circolare.** I tre render sono quasi uguali e tengono ritmo delle
  lamelle, montanti e solai. In B la mappa degli spigoli porta dentro i
  tratteggi blu del terreno, che diventano strisce dipinte.
- **Casa colorata.**
  - A inventa una vetrata con reticolare e i coppi sul tetto.
  - B aggiunge pietra.
  - C è la più fedele (partizioni, lamelle, muro grigio, forma del tetto), ma è
    piatta e prende i colori dei layer alla lettera.
  - E, senza profondità, inventa lamelle in legno e scandole.
  - F, con profondità Small, tiene la geometria come C ed è più realistica.
- **Pianta 2D.**
  - A è fedele.
  - B cambia il terrazzo e riempie il vano ascensore.
  - C è fedele, ma inventa piscina e giardino fuori.
  - D è illustrativa, coi muri neri, e perde il terrazzo.

## Conclusioni

1. La mappa che tiene la geometria è la **profondità**. Gli spigoli da soli
   peggiorano sempre, perché portano dentro il rumore della vista (tratteggi,
   texture del terreno).
2. Le tre mappe servono sulle **viste prospettiche ambigue**. Sulle piante 2D e
   su viste già chiare Nano Banana 2 da solo basta.
3. La profondità **Small** dà quasi lo stesso risultato della Large (90% contro
   92% sulla casa, geometria uguale a occhio).
4. **Licenze.**
   - Depth Anything V2 **Small è Apache-2.0**.
   - Base, Large e Giant sono **CC-BY-NC-4.0**, cioè non commerciali. Il
     deployment di stasera usa la Large: non va bene per render venduti.
   - Depth Anything 3: Small e Base sono Apache-2.0, Large e Giant CC-BY-NC.
     Per Metric-Large e Mono-Large ci sono solo fonti di terzi, quindi va
     verificato.
5. Flux + ControlNet non si è potuto provare: non c'è sul Router, e Flux dev ha
   una licenza non commerciale. Z-Image Turbo (Apache-2.0) è l'equivalente
   aperto (variante D).

## Tre Depth Anything calcolati in locale (2026-11-10, notte)

Profondità calcolata **sulla CPU del container** (4 core, ONNX Runtime), senza
deployment. Spigoli e linee sono quelli di prima, dal deployment. Poi Nano
Banana 2 con vista + spigoli + profondità + linee, stesso prompt della
variante C. Un render per casella. File in `tre-da/`.

| Modello (licenza, peso) | Tempo CPU per vista | Edificio circolare | Casa colorata | Pianta 2D |
|---|---|---|---|---|
| DA2 Small (Apache-2.0, 95 MB) | 0,2-0,5 s | 35% (vedi sotto) | 88% | 98% |
| DA3 Small (Apache-2.0, 101 MB) | 0,3-0,6 s | 94% | 80% | 99% |
| DA3 Base (Apache-2.0, 394 MB) | 0,7-1,4 s | 92% | 88% | 97% |

Cosa si vede a occhio:

- **Edificio circolare.** I tre render tengono lamelle, montanti e solai. Il 35%
  di DA2 Small è la piazza diventata liscia (spariscono i puntini della ghiaia),
  non l'edificio: altro caso in cui la % inganna. DA3 Base trasforma il terreno
  in lastre.
- **Casa colorata.** DA2 Small inventa una gradinata in primo piano e tiene il
  blu dei layer. DA3 Small fa la casa più realistica ma la stacca da terra
  (ombra sotto, casa sospesa). DA3 Base è la più fedele: tiene anche l'area
  verde/gialla in basso e le partizioni.
- **Pianta.** Tutte fedeli nei muri. Cambia solo il fuori: DA2 Small un
  terrazzo in legno, DA3 Small un prato, DA3 Base degli alberi.

Conclusione: **nessun vincitore netto** con un render per casella. DA3 Base è la
più fedele sulla vista difficile ma pesa 4 volte tanto e va il doppio più
lenta. Per il browser il candidato è **DA3 Small o DA2 Small** (circa 100 MB,
sotto il secondo su CPU); DA3 Base resta l'opzione «qualità» se il peso del
download è accettabile. Tutte e tre sono Apache-2.0, quindi vendibili.

Non verificato: tempi nel browser (qui era CPU Linux, non WebGPU su Edge/Chrome);
più render per casella; spigoli e linee calcolati anch'essi in locale.

## Costi (stima, crediti non letti dallo script)

Circa 0,08 $ per render di Nano Banana 2 (17,17 crediti misurati il
2026-10-27). In tutto sono 20 render, circa 1,60 $ (11 della prima serie, 9 dei tre Depth Anything). Le mappe dal deployment
sono lavori di pochi secondi di GPU. Il deployment costa 4,68 $/mese di storage
finché non si cancella.

## Non verificato

- Una sola esecuzione per variante: niente media né spread.
- Profondità calcolata **nel browser** (transformers.js / WebGPU): mai provata.
  Sulla CPU del container sì (sezione tre Depth Anything); nel browser va misurata.
- Profondità presa dal modello Allplan: la camera si legge già (occhio, punto
  guardato, proiezione; `GetMatrix` e `ViewToPixel` esistono nell'API). Manca
  l'apertura (`GetViewAngle` ha dato 0) e una passata di distanza. Da provare la
  nebbia dell'animazione come mappa di profondità.
- Viste con colori neutri o materiali veri: i colori dei layer restano letti come
  materiali (trappola nota del CLAUDE.md).

## File

Le cartelle sono `./` (edificio circolare), `casa/` e `pianta/`. In ognuna ci
sono vista, mappe, prompt, render e confronti. In `casa/` ci sono anche
`senza-profondita.png` e `profondita-small.png`.
