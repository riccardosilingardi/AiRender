# Blocchi di stile — bozza 9 (2026-11-01)

Riscritti dalla prompt library di Riccardo (Notion, da Visoid) con la skill architectural-prompt-enhancer: un blocco = un asse solo. **Nessun blocco è stato provato con il modello.** Testo per il modello in inglese, nomi per l'utente in italiano.

Cosa cambia dalla bozza 3 (2026-10-29): **Intorno** ha città, periferia e campagna; **Verde** è un asse nuovo degli esterni (nessuno, poco, rigoglioso), nel prompt subito dopo l'intorno; **Persone** ha «poche». Ogni blocco che aggiunge qualcosa che nella vista non c'è (contesto, verde, persone, oggetti, la vista fuori dalle finestre) finisce con «do not cover or hide any building element». Gli alberi sono passati da «Niente, sfondo neutro» al Verde, così i due assi non si contraddicono; i preset esterni hanno verde «nessuno». Per questo le lunghezze dei preset sono cresciute.

## Regola fissa (sempre per prima)

> Edit this exact image. Keep the camera, framing, proportions and every building element exactly as they are; do not add, remove or reshape any architecture. Change only the look described below.

## Fedeltà al disegno (bozza 6, 2026-10-31)

Cosa cambia dalla bozza 5: la regola fissa si sceglie fra tre. **Bilanciata** è la regola fissa di sempre, parola per parola, ed è la predefinita (SCELTA): i prompt delle bozze 4 e 5 non cambiano. **Rigida** aggiunge vincoli su sagoma, aperture e numero di elementi. **Libera** tiene volumi, aperture e inquadratura e permette dettagli costruttivi; il contesto lo decidono ancora Intorno e Verde, così i blocchi non si contraddicono. Non è un parametro del modello: il Router non ha una forza strutturale. Nessuna delle tre è provata; il piano «fedelta» del banco di prova le confronta sulla stessa vista e misura gli spigoli ritrovati.

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `rigida` | Rigida | Edit this exact image. Keep the camera, framing, proportions and every building element exactly as they are; do not add, remove or reshape any architecture. Change only the look described below. Match the drawing strictly: same silhouette, same number and position of windows, doors, columns and floors, same roof line; if in doubt, change less. | 345 |
| `bilanciata` | Bilanciata | Edit this exact image. Keep the camera, framing, proportions and every building element exactly as they are; do not add, remove or reshape any architecture. Change only the look described below. | 194 |
| `libera` | Libera | Edit this image. Keep the camera, framing, proportions and the building's volumes and openings; you may refine materials and add plausible construction details such as joints, sills, gutters and fixings. Do not change the building's shape. Change the look described below. | 272 |

## Riferimento per lo stile (bozza 6, 2026-10-31)

Solo quando in Studio · Genera c'è un'immagine di riferimento: parte come seconda immagine e questa frase entra subito prima di «cosa evitare». Non provata: il primo render con un riferimento è anche la prima volta che Nano Banana 2 riceve due immagini in una chiamata vera.

> The second image is a style reference only: take from it the colour palette, the light and the look of the materials. Do not copy its geometry, camera, objects or composition; the building stays the one in the first image.

## Inserisci nel contesto (bozza 9, 2026-11-01)

Cosa cambia dalla bozza 7: una scena nuova di Studio · Genera, il fotoinserimento. Parte con due immagini: **prima il contesto** portato dall'utente (screenshot satellitare, ortofoto, foto da drone) con il contorno magenta numerato dell'area dove va l'edificio, **poi la vista Allplan**. Il contesto va per primo perché il rapporto del render segue la prima immagine. Il prompt non usa i blocchi di stile: la luce è quella del contesto. Riscritti dal prompt Notion di Riccardo («Transform this Google Maps satellite screenshot…») e dal suo flusso a parole (thread del 2026-11-01). Nessuno è provato con il modello.

Ordine: regola → inquadratura → luogo (se c'è) → materiali (se ci sono) → fuori dall'area intatto **oppure** pulisci la mappa → cosa evitare.

> Photo insertion. The first image is the real site; the second image is a view of the new building designed for it. Place the building from the second image into the first image, inside the numbered magenta outline, and remove the outline and its number from the result. Adapt the building's perspective, scale and orientation to the site, so it stands on the ground at a believable size next to the roads, trees and buildings around it. Keep the building's shape, proportions, openings and materials as designed; do not redesign it. Match the light, sun direction, shadows, colour, haze and grain of the site image, so the building looks photographed together with it.

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `zenitale` | Zenitale | The site image is a top-down aerial view: show the building from straight above, as roofs, terraces and the ground around it, with its shadow cast on the ground in the same direction as the other shadows. | 204 |
| `volo` | Volo d'uccello | The site image is an oblique bird's-eye view: show the building from the same height and direction as the buildings around it, with its facades and roof foreshortened like theirs and its shadow in the same direction as the other shadows. | 237 |
| `contesto-fuori` | Fuori dall'area il contesto resta com'e' | Outside the outline keep every pixel of the site image exactly as it is. | 72 |
| `contesto-pulisci` | Pulisci lo screenshot della mappa | The site image is a map screenshot: remove every interface element (labels, street names, pins, icons, logos, buttons, compass, watermarks) and fill those spots with what would realistically be underneath. Turn the whole image into a photorealistic, high-resolution aerial photograph of the same place, keeping every road, building footprint, tree and field in its position, size and orientation; do not add or remove buildings. | 428 |

Il luogo passa come lo scrive l'utente, anche in italiano: «The site is at <luogo>.»

## Rese (bozza 7, 2026-10-31)

Cosa cambia dalla bozza 6: oltre a Fotorealistico ci sono quattro rese. Fotorealistico non ha un blocco: è quello che i blocchi fanno da sempre, e i suoi prompt non cambiano. Le altre quattro mettono la loro frase subito dopo i materiali, spengono gli assi che con quella resa non hanno senso (lo Studio li mostra in grigio e dice perché) e, quando «cosa evitare» le contraddirebbe, ne hanno uno loro. Scelte da Claude il 2026-10-31 («vedi tu» di Riccardo), non provate: il piano «rese» del banco di prova le confronta sulla stessa vista.

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `plastico` | Plastico bianco | Render it as a photograph of a white architectural scale model: matte white card and pale basswood, crisp cut edges, soft even studio light, plain light grey background. | 169 |
| `schizzo` | Schizzo a matita | Render it as a hand-drawn architectural pencil sketch on white paper: confident graphite lines following every edge of the view, light hatching for shade, no colour. | 165 |
| `acquerello` | Acquerello | Render it as an architectural watercolour illustration: fine ink lines following every edge of the view, loose transparent washes, soft colour bleeding, white paper showing through. | 181 |
| `cinema` | Cinematografico | Render it as a cinematic film still: anamorphic widescreen look, deep contrast, restrained teal and amber grading, a soft haze in the light. | 140 |

| Resa | Cosa spegne | Cosa evitare |
|---|---|---|
| Fotorealistico | — | quello di sempre |
| Plastico bianco | materiali, look, luce, cielo, fuori dalle finestre, intorno, verde, persone, qualità | proprio |
| Schizzo a matita | materiali, look, cielo, qualità | proprio |
| Acquerello | look, qualità | proprio |
| Cinematografico | look, qualità | quello di sempre |

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `evitare-plastico` | Cosa evitare · plastico | Avoid: colour, glossy surfaces, real material textures, people, cars, sky. | 74 |
| `evitare-schizzo` | Cosa evitare · schizzo | Avoid: colour, photographic shading, smooth digital gradients, CGI look. | 72 |
| `evitare-acquerello` | Cosa evitare · acquerello | Avoid: photographic look, hard digital edges, oversaturated colour, CGI look. | 77 |

Ordine con una resa: regola fissa → scena → materiali (se la resa non li spegne) → **resa** → gli assi accesi → cosa evitare (della resa, se ce l'ha).

## Cosa evitare (sempre in coda)

> Avoid: CGI or plastic look, HDR, oversharpening, clipped highlights, crushed blacks, heavy grain, artificial detail.

## Ordine nel prompt

Regola fissa (secondo la Fedeltà al disegno) → **Scena** (esterno, interno o arredo, dallo switch) → **Materiali** (dell'utente) → Look → Luce → Cielo (esterni) oppure Fuori dalle finestre + Arredo (interni) oppure Sfondo (arredo) → Intorno → Verde (esterni) → Persone → Qualità → Cosa evitare.

Un **passo** fatto su un render già generato (albero dei passi, piano «catena» del banco di prova) non rimanda tutto: regola fissa → scena → solo gli assi che cambiano → cosa evitare.

## Passi: richieste a parole (bozza 5, 2026-10-30)

Cosa cambia dalla bozza 4: Studio · Passi manda **richieste a parole** («due alberi davanti al fronte»), non assi. Le richieste passano come le scrive l'utente, anche in italiano, come i materiali. I testi dei blocchi della bozza 4 non cambiano.

Un passo su un render parte con la sua regola fissa, che non dice «cambia solo il look» ma «cambia solo quello che ti chiedo» (SCELTA, non provata):

> Edit this exact image. Keep the camera, framing, proportions, light and every building element exactly as they are; do not add, remove or reshape any architecture. Make only the change described below and leave everything else as it is.

Ordine: regola del passo → scena → `Change: <richiesta>; do not cover or hide any building element.` → cosa evitare. Con più richieste, `Changes: <prima>; <seconda>; …`.

**Rifai pulito dalla vista** riparte dalla vista con il prompt del primo passo della strada (i blocchi, o il testo scritto a mano) e ci aggiunge prima di «cosa evitare» le richieste di tutti i passi della strada: `Also make these changes: <prima>; <seconda>; do not cover or hide any building element.` La regola fissa resta quella dei preset («Change only the look described below»): dice una cosa diversa dalle richieste che seguono, e se il modello le ignora per questo lo dirà il piano «catena» del banco di prova.

Tolti su richiesta di Riccardo (27/10, 19:20) l'elenco «Cosa c'è nella vista» e il campo «Altro da dire». Il soggetto si riduce a esterno/interno dallo switch. Chi vuole scrivere il proprio testo lo fa con «Mostra e modifica il prompt completo», sotto il riassunto.

Esempio di materiali scritti dall'utente e tradotti:

> Materials: white lime plaster walls, dark oak window frames, light grey stone base.

## Scena

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `esterno` | Esterno (dallo switch) | The subject is a building exterior. | 35 |
| `interno` | Interno (dallo switch) | The subject is an interior space. | 33 |
| `prodotto` | Arredo (dallo switch, bozza 8) | The subject is a single piece of designer furniture, photographed as a product; the room around it is not part of the design. | 125 |

## Look fotografico

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `canon` | Canon tilt-shift · rivista | Professional architectural photograph, Canon EOS R5 with 17mm tilt-shift lens: perfectly straight verticals, deep focus, crisp micro-contrast, clean polarized colour. | 166 |
| `gfx` | Fujifilm GFX100S · caldo naturale | Fujifilm GFX100S photograph: warm natural colour, earthy muted tones, softly luminous highlights, deep but detailed shadows, gentle contrast, olive greens, pale blues. | 167 |
| `leica` | Leica SL2 · neutro profondo | Leica SL2 full-frame photograph: rich tonal depth, refined micro-contrast, restrained warm colour, smooth highlight roll-off, detailed shadows, tactile textures. | 161 |
| `portra160` | Kodak Portra 160 · morbido | Kodak Portra 160 film colour: soft and restrained, slightly warm neutrals, cream highlights, muted greens, moderate elegant contrast, fine grain, gentle pastel midtones. | 169 |
| `portra400` | Kodak Portra 400 · caldo vissuto | Kodak Portra 400 film colour: warm, soft and lived-in, slightly warm whites, muted organic greens, open shadows, creamy rolled-off highlights, fine visible grain. | 162 |
| `ektar` | Kodak Ektar 100 · colori vividi | Kodak Ektar 100 film colour: bold, clean, saturated, strong well-separated contrast, bright clean highlights, deep but open shadows, ultra-fine grain, sharp edges. | 163 |
| `metropolis` | LomoChrome Metropolis · urbano | LomoChrome Metropolis film colour: desaturated and slightly cool, muted cyan skies, subdued greens, vivid red and orange accents, punchy contrast, dense blacks, visible grain. | 175 |
| `x100v` | Fujifilm X100V · analogico 35mm | Fujifilm X100V with Classic Negative: warm muted colour, olive greens, cream highlights, lifted blacks with teal shadows, moderate contrast, fine grain, light vignette. | 168 |
| `mavic` | DJI Mavic · drone (solo viste dall'alto) | Aerial photo look of a DJI Mavic 3 Pro Hasselblad camera: deep focus to the horizon, natural muted colour, slightly cool shadows, soft distant haze, wide dynamic range. | 168 |

## Ora e luce — esterni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `mezzogiorno` | Mezzogiorno | Midday sun high in the sky, crisp natural shadows, deep blue sky with thin cirrus. | 82 |
| `estate` | Estate luminosa | Bright summer daylight, soft-to-medium shadows, cool skylight filling the shade, windows reflecting sky and surroundings, faint warm glow inside. | 145 |
| `giorno` | Giorno | Natural daylight, soft shadows. | 31 |
| `oro` | Ora d'oro | Golden hour: low warm sun, long soft shadows, warm light grazing the facades. | 77 |
| `blu` | Ora blu | Blue hour, about 20 minutes after sunset: no direct sun, no hard shadows, dark blue sky with a faint warm horizon glow, windows glowing warm amber from inside. | 159 |
| `notte` | Notte con luna | Night: moonlight as the main light, soft rim light on edges, warm interior lights against cool moonlight, slight atmospheric haze, natural night white balance. | 159 |

## Cielo e stagione — esterni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `sereno` | Sereno | Clear sky. | 10 |
| `coperto` | Coperto | Overcast sky, soft diffused light, no hard shadows. | 51 |
| `pioggia` | Pioggia | Rainy day: overcast sky, wet surfaces with subtle reflections on the ground, light rain. | 88 |
| `autunno` | Autunno nebbioso | Autumn: light mist, damp ground with subtle reflections, scattered fallen leaves, muted orange and brown tones with cool grey shadows. | 134 |
| `neve` | Neve | Winter: snow on the ground and on horizontal surfaces, cold soft light. | 71 |

## Intorno — esterni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `niente` | Niente, sfondo neutro | Plain neutral background; do not add buildings, cars or surroundings that are not in the view. | 94 |
| `citta` | Città | Urban surroundings: neighbouring buildings, pavement and street furniture in the background; do not cover or hide any building element. | 135 |
| `periferia` | Periferia | Suburban surroundings: low houses, gardens and a quiet street in the background; do not cover or hide any building element. | 123 |
| `campagna` | Campagna | Countryside surroundings: open fields and distant hills in the background; do not cover or hide any building element. | 117 |

## Verde — esterni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `nessuno` | Nessuno | Do not add trees, grass or planting that are not in the view. | 61 |
| `poco` | Poco | A few trees and some low planting around the building; do not cover or hide any building element. | 97 |
| `rigoglioso` | Rigoglioso | Lush mature trees, hedges and planting around the building; do not cover or hide any building element. | 102 |

## Luce — interni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `mattino` | Mattino da finestra | Soft morning daylight entering through the windows, gentle shadows on floor and walls, bright airy interior. | 108 |
| `pomeriggio` | Pomeriggio caldo | Warm low afternoon sun through the windows, long patches of light on the floor, warm bounce light. | 98 |
| `coperto_int` | Giorno coperto | Even overcast daylight from the windows, soft shadowless light, calm neutral tones. | 83 |
| `sera` | Sera, luci accese | Early evening: dim blue light outside the windows, warm artificial lights switched on inside, cosy contrast. | 108 |
| `notte_int` | Notte con lampade | Night: dark windows, warm lamps and concealed lighting as the only light, deep soft shadows. | 92 |

## Fuori dalle finestre — interni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `neutra` | Fuori dalle finestre: neutro | Keep the view outside the windows soft and neutral; do not invent a landscape. | 78 |
| `verde` | Fuori: verde | A soft out-of-focus green garden outside the windows; do not cover or hide any building element. | 96 |
| `citta` | Fuori: città | A soft out-of-focus city view outside the windows; do not cover or hide any building element. | 93 |

## Arredo — interni

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `nessuno` | Non aggiungere arredi | Do not add furniture or objects that are not in the view. | 57 |
| `leggero` | Qualche oggetto | Add only a few small objects (books, a plant, a throw) without changing the furniture; do not cover or hide any building element. | 129 |

## Persone

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `nessuna` | Nessuna | No people. | 10 |
| `poche` | Poche | Two or three people standing or walking, small in the frame, for scale; do not cover or hide any building element. | 114 |
| `movimento` | In movimento | A few people walking, slightly motion-blurred, for scale; do not cover or hide any building element. | 100 |

## Qualità

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `base` | Base | Professional architectural photography, natural detail. | 55 |
| `32k` | Altissima definizione (da provare) | Professional architectural photography, 32k, ultra-detailed, archi magazine quality. | 84 |

## Preset = combinazioni

Lunghezza misurata del prompt composto senza testo dell'utente. La skill indica 500-600 caratteri come ottimo per Nano Banana/Flux; con la regola fissa, la coda e (dalla bozza 4) le frasi «non coprire» stiamo sopra, fra 780 e 1000: da verificare se pesa, con il piano «preset» del banco di prova.

| Preset | Look | Luce | Cielo | Persone | Caratteri |
|---|---|---|---|---|---|
| Rivista d'architettura | Canon tilt-shift · rivista | Mezzogiorno | Sereno | Nessuna | 832 |
| Luce naturale calda | Fujifilm GFX100S · caldo naturale | Estate luminosa | Sereno | Nessuna | 896 |
| Pellicola morbida | Kodak Portra 160 · morbido | Giorno | Sereno | Nessuna | 784 |
| Urbano editoriale | LomoChrome Metropolis · urbano | Giorno | Coperto | In movimento | 921 |
| Ora blu | Leica SL2 · neutro profondo | Ora blu | Sereno | Nessuna | 904 |
| Notte con luna | Leica SL2 · neutro profondo | Notte con luna | Sereno | Nessuna | 904 |
| Giornata di pioggia | Kodak Portra 400 · caldo vissuto | Giorno | Pioggia | In movimento | 945 |
| Autunno nebbioso | Kodak Portra 400 · caldo vissuto | Giorno | Autunno nebbioso | In movimento | 991 |

### Preset interni

| Preset | Look | Luce | Fuori | Persone | Caratteri |
|---|---|---|---|---|---|
| Interno rivista | Canon tilt-shift · rivista | Mattino da finestra | Fuori dalle finestre: neutro | Nessuna | 825 |
| Interno caldo | Fujifilm GFX100S · caldo naturale | Pomeriggio caldo | Fuori: verde | Nessuna | 834 |
| Interno pellicola morbida | Kodak Portra 160 · morbido | Giorno coperto | Fuori dalle finestre: neutro | Nessuna | 803 |
| Interno sera | Leica SL2 · neutro profondo | Sera, luci accese | Fuori: città | Nessuna | 835 |
| Interno notte, lampade | Leica SL2 · neutro profondo | Notte con lampade | Fuori dalle finestre: neutro | Nessuna | 804 |
| Interno vissuto | Fujifilm X100V · analogico 35mm | Pomeriggio caldo | Fuori: verde | In movimento | 925 |

## Arredo come prodotto (bozza 8, 2026-11-01)

Cosa cambia dalla bozza 7: oltre a Esterno e Interno c'è una terza scena, **Arredo**, per un pezzo d'arredo da solo che il designer vuole valorizzare come prodotto: sfondo neutro da studio, luce da still life, primo piano. Richiesta di Riccardo del 2026-11-01. Nella prompt library di Notion non c'è niente di adatto (sono tutti prompt di architettura), quindi i blocchi sono scritti da zero con lo schema della skill architectural-prompt-enhancer: fotocamera e ottica, luce con la sua qualità, materiali con la loro grana. Nessuno è provato con il modello.

Nel codice l'identificativo della scena è `prodotto`, perché `arredo` è già l'asse degli oggetti negli interni.

Cosa vale per questa scena:

- **Regola fissa propria**: da preservare è il pezzo, non l'architettura, e lo sfondo può cambiare. Stessi tre gradi della Fedeltà al disegno, stessi nomi.
- **Look, Luce e Qualità propri** (Qualità dice «furniture product photography» invece di «architectural photography»). Il look riprende Leica, GFX e Portra 160 dagli esterni.
- **Sfondo** è l'asse nuovo della scena, al posto di cielo/intorno/verde e di fuori dalle finestre/arredo. Prende il posto di tutto quello che non è il pezzo; «Come nella vista» tiene la stanza di Allplan.
- **Persone** non c'è: un prodotto si fotografa da solo.
- **Cosa evitare proprio**, con gambe deformate, proporzioni cambiate e oggetti di scena aggiunti.
- Il **primo piano** non è un blocco: la regola fissa tiene l'inquadratura, quindi lo dà la vista salvata in Allplan. La profondità di campo invece sì (look Macro 100mm), perché non sposta niente.
- La resa **Plastico bianco** spegne anche lo sfondo: ha già il suo fondo grigio.

### Scena

Nella tabella «Scena» più sotto, riga `prodotto`.

### Fedeltà al disegno · arredo

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `rigida` | Rigida | Edit this exact image. Keep the camera, framing and the furniture piece exactly as it is: same shape, proportions, joints and details; do not add, remove or reshape any part of it. Change only the look and the background described below. Match the drawing strictly: same silhouette, same number and position of legs, panels, cushions and handles; if in doubt, change less. | 372 |
| `bilanciata` | Bilanciata | Edit this exact image. Keep the camera, framing and the furniture piece exactly as it is: same shape, proportions, joints and details; do not add, remove or reshape any part of it. Change only the look and the background described below. | 237 |
| `libera` | Libera | Edit this image. Keep the camera, framing and the furniture piece's shape and proportions; you may refine materials and add plausible details such as seams, stitching, edge profiles and fixings. Change the look and the background described below. | 246 |

### Look fotografico · arredo

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `hasselblad` | Hasselblad H6D · catalogo | Hasselblad H6D-100c product photograph, 120mm lens at f/11: true-to-life neutral colour, edge-to-edge sharpness, accurate material textures, clean highlights, no lens distortion. | 178 |
| `phaseone` | Phase One · editoriale design | Phase One IQ4 editorial still life, 80mm lens: rich tonal depth, refined micro-contrast, restrained slightly warm colour, design magazine furniture photography. | 160 |
| `macro` | Macro 100mm · dettaglio | Canon EOS R5 with 100mm macro lens at f/4: shallow depth of field with focus on the material and the joints, soft creamy falloff, tactile wood grain, fabric weave and metal finish. | 180 |
| `leica` | Leica SL2 · neutro profondo | Leica SL2 full-frame photograph: rich tonal depth, refined micro-contrast, restrained warm colour, smooth highlight roll-off, detailed shadows, tactile textures. | 161 |
| `gfx` | Fujifilm GFX100S · caldo naturale | Fujifilm GFX100S photograph: warm natural colour, earthy muted tones, softly luminous highlights, deep but detailed shadows, gentle contrast, olive greens, pale blues. | 167 |
| `portra160` | Kodak Portra 160 · morbido | Kodak Portra 160 film colour: soft and restrained, slightly warm neutrals, cream highlights, muted greens, moderate elegant contrast, fine grain, gentle pastel midtones. | 169 |

### Luce · arredo

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `softbox` | Softbox morbida | Large overhead softbox and two side softboxes: soft even studio light, gentle wraparound highlights, a soft contact shadow under the piece, no hard shadows. | 156 |
| `finestra` | Finestra laterale | Soft directional daylight from a large window on one side: gentle gradient across the piece, soft shadow falling away from the light, natural modelling of the volumes. | 167 |
| `radente` | Luce radente · texture | Low raking light from one side grazing the surfaces: it reveals wood grain, fabric weave and stitching, defined but soft shadows. | 129 |
| `sole` | Sole netto · editoriale | Hard late-afternoon sunlight through a window: crisp graphic shadows of the piece and of the window frame on floor and wall, warm tone. | 135 |
| `controluce` | Controluce, bordi accesi | Low-key studio light: a strong rim light from behind outlining the silhouette, a dim soft fill from the front, deep shadows, glowing edges. | 139 |

### Sfondo · arredo

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `bianco` | Fondo bianco infinito | Background: a seamless pure white studio sweep as wall and floor, no horizon line; replace everything around the piece with it. | 127 |
| `grigio` | Fondo grigio caldo | Background: a seamless matte warm light grey studio sweep as wall and floor, no horizon line; replace everything around the piece with it. | 138 |
| `calce` | Parete in calce | Background: a plain wall in matte off-white lime plaster with a subtle troweled texture and a pale smooth concrete floor; nothing else around the piece. | 152 |
| `scuro` | Fondo antracite | Background: a seamless matte charcoal studio backdrop as wall and floor, no horizon line; replace everything around the piece with it. | 134 |
| `vista` | Come nella vista | Background: keep the wall and the floor as they are in the view; only refine their materials and light. | 103 |
| `ambiente` | Stanza sfocata | Background: a softly out-of-focus minimal living room behind the piece, neutral tones, nothing in front of it; do not cover or hide any part of the piece. | 154 |

### Qualità · arredo

| id | Nome in UI | Testo per il modello | Caratteri |
|---|---|---|---|
| `base` | Base | Professional furniture product photography, natural detail. | 59 |
| `32k` | Altissima definizione (da provare) | Professional furniture product photography, 32k, ultra-detailed, design magazine quality. | 89 |

### Cosa evitare · arredo

> Avoid: CGI or plastic look, warped or extra legs, changed proportions, added props or decor, HDR, oversharpening, clipped highlights, crushed blacks.

### Preset arredo

I prompt sono più lunghi di quelli architettonici (1010-1065 caratteri): la regola fissa dell'arredo è più lunga, perché deve dire che lo sfondo può cambiare. Da verificare con il banco di prova.

| Preset | Look | Luce | Sfondo | Caratteri |
|---|---|---|---|---|
| Catalogo, fondo bianco | Hasselblad H6D · catalogo | Softbox morbida | Fondo bianco infinito | 1037 |
| Studio, grigio caldo | Hasselblad H6D · catalogo | Finestra laterale | Fondo grigio caldo | 1059 |
| Editoriale, ombre di sole | Phase One · editoriale design | Sole netto · editoriale | Parete in calce | 1023 |
| Dettaglio materiale | Macro 100mm · dettaglio | Luce radente · texture | Fondo grigio caldo | 1023 |
| Controluce, fondo scuro | Leica SL2 · neutro profondo | Controluce, bordi accesi | Fondo antracite | 1010 |
| Ambientato, stanza sfocata | Fujifilm GFX100S · caldo naturale | Finestra laterale | Stanza sfocata | 1064 |

### Esempio intero: arredo + materiali + Dettaglio materiale

> Edit this exact image. Keep the camera, framing and the furniture piece exactly as it is: same shape, proportions, joints and details; do not add, remove or reshape any part of it. Change only the look and the background described below. The subject is a single piece of designer furniture, photographed as a product; the room around it is not part of the design. Materials: natural oak frame, cognac leather seat. Canon EOS R5 with 100mm macro lens at f/4: shallow depth of field with focus on the material and the joints, soft creamy falloff, tactile wood grain, fabric weave and metal finish. Low raking light from one side grazing the surfaces: it reveals wood grain, fabric weave and stitching, defined but soft shadows. Background: a seamless matte warm light grey studio sweep as wall and floor, no horizon line; replace everything around the piece with it. Professional furniture product photography, natural detail. Avoid: CGI or plastic look, warped or extra legs, changed proportions, added props or decor, HDR, oversharpening, clipped highlights, crushed blacks.

## 16k / 32k

Il modello di modifica restituisce la sua risoluzione, qualunque cosa dica il testo: Nano Banana 2 ha reso 1376x768 per una vista di 1536x857 (sonda del 27/10). Quindi «32k» non aumenta i pixel. Può però spingere il modello verso più microdettaglio e nitidezza: non lo sappiamo. Per questo è un blocco **Qualità** a due voci, Base e Altissima definizione, da confrontare sulla stessa vista prima di scegliere il predefinito. I pixel veri arrivano da un modello che rende a 2K/4K o da un ingrandimento (upscale), da valutare.

## Esempio completo: esterno + materiali + Ora blu

> Edit this exact image. Keep the camera, framing, proportions and every building element exactly as they are; do not add, remove or reshape any architecture. Change only the look described below. The subject is a building exterior. Materials: white lime plaster walls, dark oak window frames, light grey stone base. Leica SL2 full-frame photograph: rich tonal depth, refined micro-contrast, restrained warm colour, smooth highlight roll-off, detailed shadows, tactile textures. Blue hour, about 20 minutes after sunset: no direct sun, no hard shadows, dark blue sky with a faint warm horizon glow, windows glowing warm amber from inside. Clear sky. Plain neutral background; do not add buildings, cars or surroundings that are not in the view. Do not add trees, grass or planting that are not in the view. No people. Professional architectural photography, natural detail. Avoid: CGI or plastic look, HDR, oversharpening, clipped highlights, crushed blacks, heavy grain, artificial detail.

Nota: i materiali arrivano in italiano; tradurli in inglese prima dell'invio è un passo da decidere (a mano nel motore o con un modello di testo). Finché non c'è, passano come sono.

## Materiali dalla mappa Allplan (in pipeline, non attivo)

Idea di Riccardo (27/10): Allplan dà una vista con un colore per materiale, stessa camera della vista shaded. Lo Studio la mostra in piccolo e sotto mette una riga per materiale:

| Colore | Materiale Allplan | Diventa (parole dell'utente) | Immagine di riferimento |
|---|---|---|---|
| giallo | Intonaco esterno (mat 12) | intonaco a calce bianco | facoltativa |
| rosso | Copertura (mat 4) | lamiera aggraffata antracite | facoltativa |

Le righe sopra sono un esempio, non dati veri.

Nel prompt il blocco Materiali diventa una riga per colore, al posto del testo libero:

> Image 2 is a colour map of the same view, one flat colour per material. Yellow areas in image 2: white lime plaster. Red areas in image 2: anthracite standing-seam metal roof. Image 3 shows the plaster to use for the yellow areas.

Cosa va verificato prima, in quest'ordine:

1. Che Allplan esporti la vista colorata per materiale con la stessa camera e la stessa dimensione della shaded (PRD §9). Senza questo non c'è niente da mostrare.
2. Che il motore riesca a leggere la mappa: un colore = un materiale, senza sfumature né ombre nei colori.
3. Che Nano Banana 2 accetti più immagini in una richiesta via Comfy Router e le usi come indicato. Kontext Pro probabilmente ne accetta una sola: per lui le righe restano solo testo.
4. Che la mappa non venga copiata nei colori del render: è la trappola «colori come materiali» del 27/10, al contrario. Da provare con un render solo prima di qualunque altra cosa.

Finché non c'è, resta attivo il campo Materiali a parole.
