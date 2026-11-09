"""I blocchi di stile e i preset che li combinano.

Da dove vengono i testi: `docs/ui/blocchi-stile-bozza.md`, bozza 7 del
2026-10-31 (la 3 del 2026-10-27 piu' intorno, verde e persone «poche» nella
4, piu' la regola dei passi e le richieste a parole nella 5, piu' la
fedelta' al disegno e il riferimento per lo stile nella 6, piu' le rese non
fotografiche nella 7, piu' «Inserisci nel contesto» nella 8). Sono **riscritti** dalla prompt library di Riccardo (Notion,
ispirata a Visoid), non copiati: un blocco tocca un asse solo, cosi' cambiarne
uno non disfa gli altri. Testo per il modello in inglese, nomi per l'utente in
italiano.

**Nessun blocco e' stato provato con il modello.** Ogni blocco porta
l'origine SCELTA di core/config.py, e chi lo mostra a schermo lo deve dire.
Quando un blocco sara' confrontato su viste vere, la sua origine cambia qui,
blocco per blocco.

L'ordine nel prompt e' fisso (PRD, sezione 5, riga del 2026-10-27):
regola fissa -> scena -> materiali -> look -> luce -> cielo (esterni) oppure
fuori dalle finestre + arredo (interni) oppure sfondo (arredo come prodotto,
bozza 8) -> intorno -> verde (esterni) -> persone -> qualita' -> cosa evitare.

Un blocco che aggiunge qualcosa all'immagine (contesto, verde, persone,
oggetti) dice anche cosa non toccare: finisce con NON_COPRIRE. Senza, un
albero o una persona davanti a una finestra cambiano il disegno.

Qui non c'e' nessun modello linguistico: i materiali scritti dall'utente
passano come sono, anche in italiano (PRD, sezione 9).
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields, replace

from . import config
from .errori import ErroreAirender
from .lessico import controlla_etichetta

# Cambia ogni volta che cambia il testo di un blocco o la composizione di un
# preset: senza, una ricetta non dice con quali parole e' stata fatta.
VERSIONE = "bozza-16"

ESTERNO = "esterno"
INTERNO = "interno"
# Un pezzo d'arredo da solo, fotografato come un prodotto (bozza 8, richiesta
# di Riccardo del 2026-11-01): sfondo neutro da studio, primo piano. Il nome
# per l'utente e' «Arredo»; l'identificativo e' «prodotto» perche' «arredo» e'
# gia' l'asse degli oggetti negli interni.
PRODOTTO = "prodotto"
# Una pianta, una planimetria o un planivolumetrico visti dall'alto (bozza 16,
# flussi 5, 6 e 7 di Riccardo, 2026-11-09). Che disegno e' lo dice l'asse
# «tipo»; il resto della tavola lo dice lo stile («look»).
PIANTA = "pianta"
SCENE = (ESTERNO, INTERNO, PRODOTTO, PIANTA)
NOMI_SCENE = {ESTERNO: "esterno", INTERNO: "interno", PRODOTTO: "arredo", PIANTA: "pianta"}


class SceltaNonValida(ErroreAirender):
    """Una scelta di stile che non esiste, o che non vale per quella scena."""


@dataclass(frozen=True)
class Blocco:
    """Un pezzo di prompt: un asse solo, un nome per l'utente, un testo per il modello."""

    identificativo: str
    nome: str
    testo: str
    origine: str = config.SCELTA
    # Vero se il blocco aggiunge qualcosa che nella vista non c'e'.
    aggiunge: bool = False
    # Una riga per l'utente: cosa cambia nel render, in parole semplici.
    descrizione: str = ""

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome del blocco {self.identificativo}")
        controlla_etichetta(self.descrizione, f"la descrizione del blocco {self.identificativo}")


def _blocchi(*righe: tuple[str, str, str]) -> dict[str, Blocco]:
    return {r[0]: Blocco(*r) for r in righe}


def _descritti(elenco: dict[str, Blocco], descrizioni: dict[str, str]) -> dict[str, Blocco]:
    """Gli stessi blocchi, con la riga che dice all'utente cosa cambiano."""
    return {i: replace(b, descrizione=descrizioni.get(i, b.descrizione)) for i, b in elenco.items()}


# La coda di ogni blocco che aggiunge qualcosa.
NON_COPRIRE = "do not cover or hide any building element"


def _aggiunta(identificativo: str, nome: str, testo: str) -> tuple[str, Blocco]:
    """Un blocco che aggiunge qualcosa: il testo finisce con cosa non toccare."""
    return identificativo, Blocco(identificativo, nome, f"{testo}; {NON_COPRIRE}.", aggiunge=True)


REGOLA_FISSA = Blocco(
    "regola",
    "Regola fissa",
    "Edit this exact image. Keep the camera, framing, proportions and every "
    "building element exactly as they are; do not add, remove or reshape any "
    "architecture. Change only the look described below.",
)

# Fedelta' al disegno: quanto il modello puo' discostarsi dalla vista. Non e'
# un parametro del modello (il Router non ha una forza strutturale, vedi
# provider/comfy.py): e' la regola fissa, scritta in tre modi. «Bilanciata» e'
# la regola fissa di sempre, parola per parola, cosi' i prompt di prima non
# cambiano. Nessuna delle tre e' provata: il piano «fedelta» del banco serve
# a misurarle.
FEDELTA = _blocchi(
    ("rigida", "Rigida",
     REGOLA_FISSA.testo + " Match the drawing strictly: same silhouette, same "
     "number and position of windows, doors, columns and floors, same roof line; "
     "if in doubt, change less."),
    ("bilanciata", "Bilanciata", REGOLA_FISSA.testo),
    ("libera", "Libera",
     "Edit this image. Keep the camera, framing, proportions and the building's "
     "volumes and openings; you may refine materials and add plausible "
     "construction details such as joints, sills, gutters and fixings. Do not "
     "change the building's shape. Change the look described below."),
)

# La regola fissa di un pezzo d'arredo (bozza 8): da preservare e' il pezzo,
# non l'architettura, e lo sfondo puo' cambiare. Stessi tre gradi, stessi nomi.
FEDELTA_PRODOTTO = _blocchi(
    ("rigida", "Rigida",
     "Edit this exact image. Keep the camera, framing and the furniture piece "
     "exactly as it is: same shape, proportions, joints and details; do not add, "
     "remove or reshape any part of it. Change only the look and the background "
     "described below. Match the drawing strictly: same silhouette, same number "
     "and position of legs, panels, cushions and handles; if in doubt, change less."),
    ("bilanciata", "Bilanciata",
     "Edit this exact image. Keep the camera, framing and the furniture piece "
     "exactly as it is: same shape, proportions, joints and details; do not add, "
     "remove or reshape any part of it. Change only the look and the background "
     "described below."),
    ("libera", "Libera",
     "Edit this image. Keep the camera, framing and the furniture piece's shape "
     "and proportions; you may refine materials and add plausible details such "
     "as seams, stitching, edge profiles and fixings. Change the look and the "
     "background described below."),
)

# SCELTA: e' la regola con cui sono stati fatti tutti i render fino al
# 2026-10-31. Cambia solo se il piano «fedelta» del banco dice che un'altra
# tiene meglio la geometria senza perdere resa.
FEDELTA_PREDEFINITA = "bilanciata"

COSA_EVITARE = Blocco(
    "evitare",
    "Cosa evitare",
    "Avoid: CGI or plastic look, HDR, oversharpening, clipped highlights, "
    "crushed blacks, heavy grain, artificial detail.",
)

# --- rese (bozza 7) -----------------------------------------------------------

# Fotorealistico non ha un blocco: e' quello che i blocchi fanno da sempre.
# Le altre quattro aggiungono la loro frase subito dopo i materiali, spengono
# gli assi che con quella resa non hanno senso (lo Studio li mostra in grigio
# e dice perche', non li nasconde) e, quando «cosa evitare» le
# contraddirebbe, hanno il loro. Scelte, non provate: il piano «rese» del
# banco le confronta.
FOTO = "foto"
RESA = _blocchi(
    ("plastico", "Plastico bianco",
     "Render it as a photograph of a white architectural scale model: matte "
     "white card and pale basswood, crisp cut edges, soft even studio light, "
     "plain light grey background."),
    ("schizzo", "Schizzo a matita",
     "Render it as a hand-drawn architectural pencil sketch on white paper: "
     "confident graphite lines following every edge of the view, light "
     "hatching for shade, no colour."),
    ("acquerello", "Acquerello",
     "Render it as an architectural watercolour illustration: fine ink lines "
     "following every edge of the view, loose transparent washes, soft colour "
     "bleeding, white paper showing through."),
    ("cinema", "Cinematografico",
     "Render it as a cinematic film still: anamorphic widescreen look, deep "
     "contrast, restrained teal and amber grading, a soft haze in the light."),
)
NOMI_RESE = {FOTO: "Fotorealistico", **{i: b.nome for i, b in RESA.items()}}

# Cosa spegne ogni resa. «materiali» sono le parole dell'utente: un plastico
# bianco o uno schizzo senza colore le contraddirebbero.
SPENTI_DA_RESA = {
    FOTO: frozenset(),
    "plastico": frozenset({"materiali", "look", "luce", "cielo", "fuori", "intorno", "verde", "sfondo", "persone", "qualita"}),
    "schizzo": frozenset({"materiali", "look", "cielo", "qualita"}),
    "acquerello": frozenset({"look", "qualita"}),
    "cinema": frozenset({"look", "qualita"}),
}

# «Cosa evitare» al posto di quello di sempre, per le rese che lo
# contraddirebbero (un plastico ha proprio l'aspetto «plastic»).
EVITARE_DA_RESA = _blocchi(
    ("evitare-plastico", "Cosa evitare · plastico",
     "Avoid: colour, glossy surfaces, real material textures, people, cars, sky."),
    ("evitare-schizzo", "Cosa evitare · schizzo",
     "Avoid: colour, photographic shading, smooth digital gradients, CGI look."),
    ("evitare-acquerello", "Cosa evitare · acquerello",
     "Avoid: photographic look, hard digital edges, oversaturated colour, CGI look."),
)


def resa_valida(resa: str | None) -> str:
    resa = resa or FOTO
    if resa not in NOMI_RESE:
        raise SceltaNonValida(
            f"La resa \"{resa}\" non esiste.",
            f"Le rese possibili sono: {', '.join(NOMI_RESE)}.",
        )
    return resa


def spenti(scelte: "Scelte") -> frozenset[str]:
    """Gli assi (e i materiali) che la resa scelta non manda."""
    return SPENTI_DA_RESA[resa_valida(scelte.resa)]


def _evitare(resa: str, scena: str = ESTERNO) -> Blocco:
    if scena == PIANTA:
        return COSA_EVITARE_PIANTA
    if resa == FOTO and scena == PRODOTTO:
        return COSA_EVITARE_PRODOTTO
    return EVITARE_DA_RESA.get(f"evitare-{resa}", COSA_EVITARE)


SCENA = _blocchi(
    (ESTERNO, "Esterno", "The subject is a building exterior."),
    (INTERNO, "Interno", "The subject is an interior space."),
    (PRODOTTO, "Arredo",
     "The subject is a single piece of designer furniture, photographed as a "
     "product; the room around it is not part of the design."),
    (PIANTA, "Pianta",
     "The subject is an architectural drawing seen from straight above."),
)

LOOK = _blocchi(
    ("canon", "Nitido da rivista",
     "Professional architectural photograph, Canon EOS R5 with 17mm tilt-shift "
     "lens: perfectly straight verticals, deep focus, crisp micro-contrast, "
     "clean polarized colour."),
    ("gfx", "Caldo naturale",
     "Fujifilm GFX100S photograph: warm natural colour, earthy muted tones, "
     "softly luminous highlights, deep but detailed shadows, gentle contrast, "
     "olive greens, pale blues."),
    ("leica", "Neutro profondo",
     "Leica SL2 full-frame photograph: rich tonal depth, refined "
     "micro-contrast, restrained warm colour, smooth highlight roll-off, "
     "detailed shadows, tactile textures."),
    ("portra160", "Pellicola morbida",
     "Kodak Portra 160 film colour: soft and restrained, slightly warm "
     "neutrals, cream highlights, muted greens, moderate elegant contrast, "
     "fine grain, gentle pastel midtones."),
    ("portra400", "Pellicola calda",
     "Kodak Portra 400 film colour: warm, soft and lived-in, slightly warm "
     "whites, muted organic greens, open shadows, creamy rolled-off "
     "highlights, fine visible grain."),
    ("ektar", "Colori vividi",
     "Kodak Ektar 100 film colour: bold, clean, saturated, strong "
     "well-separated contrast, bright clean highlights, deep but open "
     "shadows, ultra-fine grain, sharp edges."),
    ("metropolis", "Urbano freddo",
     "LomoChrome Metropolis film colour: desaturated and slightly cool, muted "
     "cyan skies, subdued greens, vivid red and orange accents, punchy "
     "contrast, dense blacks, visible grain."),
    ("x100v", "Analogico 35 mm",
     "Fujifilm X100V with Classic Negative: warm muted colour, olive greens, "
     "cream highlights, lifted blacks with teal shadows, moderate contrast, "
     "fine grain, light vignette."),
    ("mavic", "Da drone (solo viste dall'alto)",
     "Aerial photo look of a DJI Mavic 3 Pro Hasselblad camera: deep focus to "
     "the horizon, natural muted colour, slightly cool shadows, soft distant "
     "haze, wide dynamic range."),
)

# Il look non cambia obiettivo ne' inquadratura: quelli li tiene la regola
# fissa, dalla vista di Allplan. La marca della fotocamera o della pellicola
# resta nel testo per il modello, perche' e' lei che da' colore, contrasto e
# grana; a schermo si legge l'effetto (richiesta di Riccardo del 2026-11-05:
# chi non fotografa non sa cosa vuol dire «Portra 160»).
LOOK = _descritti(LOOK, {
    "canon": "Verticali dritte, tutto a fuoco, colori puliti.",
    "gfx": "Colori caldi e terrosi, luci morbide, verdi oliva.",
    "leica": "Contrasto raffinato, colore trattenuto, ombre ricche di dettaglio.",
    "portra160": "Toni pastello, bianchi color crema, grana fine.",
    "portra400": "Caldo e vissuto, ombre aperte, grana visibile.",
    "ektar": "Colori saturi, contrasto forte, molto nitido.",
    "metropolis": "Desaturato, cieli ciano, rossi e arancioni accesi, neri densi.",
    "x100v": "Caldo smorzato, ombre verde acqua, leggera vignettatura.",
    "mavic": "Tutto a fuoco fino all'orizzonte, foschia lontana. La vista dall'alto la deve dare Allplan.",
})

LUCE_ESTERNI = _blocchi(
    ("mezzogiorno", "Mezzogiorno",
     "Midday sun high in the sky, crisp natural shadows, deep blue sky with "
     "thin cirrus."),
    ("estate", "Estate luminosa",
     "Bright summer daylight, soft-to-medium shadows, cool skylight filling "
     "the shade, windows reflecting sky and surroundings, faint warm glow "
     "inside."),
    ("giorno", "Giorno", "Natural daylight, soft shadows."),
    ("oro", "Ora d'oro",
     "Golden hour: low warm sun, long soft shadows, warm light grazing the "
     "facades."),
    ("blu", "Ora blu",
     "Blue hour, about 20 minutes after sunset: no direct sun, no hard "
     "shadows, dark blue sky with a faint warm horizon glow, windows glowing "
     "warm amber from inside."),
    ("notte", "Notte con luna",
     "Night: moonlight as the main light, soft rim light on edges, warm "
     "interior lights against cool moonlight, slight atmospheric haze, "
     "natural night white balance."),
)

CIELO = _blocchi(
    ("sereno", "Sereno", "Clear sky."),
    ("coperto", "Coperto", "Overcast sky, soft diffused light, no hard shadows."),
    ("pioggia", "Pioggia",
     "Rainy day: overcast sky, wet surfaces with subtle reflections on the "
     "ground, light rain."),
    ("autunno", "Autunno nebbioso",
     "Autumn: light mist, damp ground with subtle reflections, scattered "
     "fallen leaves, muted orange and brown tones with cool grey shadows."),
    ("neve", "Neve",
     "Winter: snow on the ground and on horizontal surfaces, cold soft light."),
)

# Gli alberi non stanno qui: sono dell'asse verde, cosi' "sfondo neutro"
# insieme a "verde: poco" non si contraddicono.
INTORNO = {
    "niente": Blocco(
        "niente", "Niente, sfondo neutro",
        "Plain neutral background; do not add buildings, cars or surroundings "
        "that are not in the view."),
    **dict((
        _aggiunta("citta", "Città",
                  "Urban surroundings: neighbouring buildings, pavement and street "
                  "furniture in the background"),
        _aggiunta("periferia", "Periferia",
                  "Suburban surroundings: low houses, gardens and a quiet street in "
                  "the background"),
        _aggiunta("campagna", "Campagna",
                  "Countryside surroundings: open fields and distant hills in the "
                  "background"),
    )),
}

VERDE = {
    "nessuno": Blocco(
        "nessuno", "Nessuno",
        "Do not add trees, grass or planting that are not in the view."),
    **dict((
        _aggiunta("poco", "Poco",
                  "A few trees and some low planting around the building"),
        _aggiunta("rigoglioso", "Rigoglioso",
                  "Lush mature trees, hedges and planting around the building"),
    )),
}

LUCE_INTERNI = _blocchi(
    ("mattino", "Mattino da finestra",
     "Soft morning daylight entering through the windows, gentle shadows on "
     "floor and walls, bright airy interior."),
    ("pomeriggio", "Pomeriggio caldo",
     "Warm low afternoon sun through the windows, long patches of light on "
     "the floor, warm bounce light."),
    ("coperto_int", "Giorno coperto",
     "Even overcast daylight from the windows, soft shadowless light, calm "
     "neutral tones."),
    ("sera", "Sera, luci accese",
     "Early evening: dim blue light outside the windows, warm artificial "
     "lights switched on inside, cosy contrast."),
    ("notte_int", "Notte con lampade",
     "Night: dark windows, warm lamps and concealed lighting as the only "
     "light, deep soft shadows."),
)

FUORI = {
    "neutra": Blocco(
        "neutra", "Fuori dalle finestre: neutro",
        "Keep the view outside the windows soft and neutral; do not invent a "
        "landscape."),
    **dict((
        _aggiunta("verde", "Fuori: verde", "A soft out-of-focus green garden outside the windows"),
        _aggiunta("citta", "Fuori: città", "A soft out-of-focus city view outside the windows"),
    )),
}

ARREDO = {
    "nessuno": Blocco(
        "nessuno", "Non aggiungere arredi",
        "Do not add furniture or objects that are not in the view."),
    **dict((
        _aggiunta("leggero", "Qualche oggetto",
                  "Add only a few small objects (books, a plant, a throw) without "
                  "changing the furniture"),
    )),
}

# --- arredo come prodotto (bozza 8) ---------------------------------------------

# Un pezzo solo, da catalogo o da rivista di design. Scritti con lo schema
# dell'Arch prompt enhancer (fotocamera e ottica, luce con la sua qualita',
# materiali con la loro grana), non presi da Notion: la prompt library di
# Riccardo non ha prompt per un prodotto. Il primo piano non e' un blocco: la
# regola fissa tiene l'inquadratura, quindi lo da' la vista di Allplan. La
# profondita' di campo invece si', perche' non sposta niente.
LOOK_PRODOTTO = {
    **_blocchi(
        ("hasselblad", "Catalogo fedele",
         "Hasselblad H6D-100c product photograph, 120mm lens at f/11: true-to-life "
         "neutral colour, edge-to-edge sharpness, accurate material textures, clean "
         "highlights, no lens distortion."),
        ("phaseone", "Rivista di design",
         "Phase One IQ4 editorial still life, 80mm lens: rich tonal depth, refined "
         "micro-contrast, restrained slightly warm colour, design magazine "
         "furniture photography."),
        ("macro", "Dettaglio, sfondo sfocato",
         "Canon EOS R5 with 100mm macro lens at f/4: shallow depth of field with "
         "focus on the material and the joints, soft creamy falloff, tactile wood "
         "grain, fabric weave and metal finish."),
    ),
    **{i: LOOK[i] for i in ("leica", "gfx", "portra160")},
}

LOOK_PRODOTTO = _descritti(LOOK_PRODOTTO, {
    "hasselblad": "Colori fedeli, nitido da bordo a bordo, materiali precisi.",
    "phaseone": "Toni profondi, colore leggermente caldo, da rivista d'arredo.",
    "macro": "A fuoco materiali e giunti, il resto sfuma.",
})

LUCE_PRODOTTO = _blocchi(
    ("softbox", "Softbox morbida",
     "Large overhead softbox and two side softboxes: soft even studio light, "
     "gentle wraparound highlights, a soft contact shadow under the piece, no "
     "hard shadows."),
    ("finestra", "Finestra laterale",
     "Soft directional daylight from a large window on one side: gentle "
     "gradient across the piece, soft shadow falling away from the light, "
     "natural modelling of the volumes."),
    ("radente", "Luce radente · texture",
     "Low raking light from one side grazing the surfaces: it reveals wood "
     "grain, fabric weave and stitching, defined but soft shadows."),
    ("sole", "Sole netto · editoriale",
     "Hard late-afternoon sunlight through a window: crisp graphic shadows of "
     "the piece and of the window frame on floor and wall, warm tone."),
    ("controluce", "Controluce, bordi accesi",
     "Low-key studio light: a strong rim light from behind outlining the "
     "silhouette, a dim soft fill from the front, deep shadows, glowing edges."),
)

# Lo sfondo prende il posto di tutto quello che non e' il pezzo: la scena lo
# dice («the room around it is not part of the design»). «Come nella vista»
# serve quando in Allplan la stanza c'e' e va tenuta.
SFONDO = {
    **_blocchi(
        ("bianco", "Fondo bianco infinito",
         "Background: a seamless pure white studio sweep as wall and floor, no "
         "horizon line; replace everything around the piece with it."),
        ("grigio", "Fondo grigio caldo",
         "Background: a seamless matte warm light grey studio sweep as wall and "
         "floor, no horizon line; replace everything around the piece with it."),
        ("calce", "Parete in calce",
         "Background: a plain wall in matte off-white lime plaster with a subtle "
         "troweled texture and a pale smooth concrete floor; nothing else around "
         "the piece."),
        ("scuro", "Fondo antracite",
         "Background: a seamless matte charcoal studio backdrop as wall and floor, "
         "no horizon line; replace everything around the piece with it."),
        ("vista", "Come nella vista",
         "Background: keep the wall and the floor as they are in the view; only "
         "refine their materials and light."),
    ),
    "ambiente": Blocco(
        "ambiente", "Stanza sfocata",
        "Background: a softly out-of-focus minimal living room behind the piece, "
        "neutral tones, nothing in front of it; do not cover or hide any part of "
        "the piece.", aggiunge=True),
}

QUALITA_PRODOTTO = _blocchi(
    ("base", "Base", "Professional furniture product photography, natural detail."),
    ("32k", "Altissima definizione",
     "Professional furniture product photography, 32k, ultra-detailed, design "
     "magazine quality."),
)

COSA_EVITARE_PRODOTTO = Blocco(
    "evitare-prodotto",
    "Cosa evitare · arredo",
    "Avoid: CGI or plastic look, warped or extra legs, changed proportions, "
    "added props or decor, HDR, oversharpening, clipped highlights, crushed "
    "blacks.",
)

# --- pianta, planimetria e planivolumetrico (bozza 16) ---------------------------

# Flussi 5, 6 e 7 di Riccardo (2026-11-08): una cattura dall'alto di Allplan
# (vista in pianta o zenitale), o un'immagine di pianta caricata, diventa una
# tavola. Il punto fermo non e' l'edificio in prospettiva ma il disegno: muri,
# aperture, impronte, strade e confini restano dove sono, alla stessa scala.
# Scritti con lo schema del prompt architettonico (cosa e', cosa resta, il
# materiale con la sua grana, la luce con la sua direzione), non presi da
# Notion: la prompt library di Riccardo non ha piante. Nessuno provato.
EDIFICIO = "edificio"
SITO = "sito"
VOLUMI = "volumi"
TIPO_PREDEFINITO = EDIFICIO

TIPI_PIANTA = _descritti(_blocchi(
    (EDIFICIO, "Pianta dell'edificio",
     "The subject is a floor plan of one storey seen from straight above: "
     "walls, openings, door swings, stairs and the furniture drawn in it."),
    (SITO, "Planimetria",
     "The subject is a site plan seen from straight above: building "
     "footprints and roofs, roads, paths, plot lines, lawns and trees."),
    (VOLUMI, "Planivolumetrico",
     "The subject is a massing site plan seen from straight above: the "
     "buildings as solid volumes with their real heights, the ground, roads "
     "and plot lines around them."),
), {
    EDIFICIO: "Un piano: stanze, muri, porte e finestre, gli arredi disegnati.",
    SITO: "Il lotto: edifici dall'alto, strade, percorsi, verde, confini.",
    VOLUMI: "I volumi dall'alto, con le ombre che seguono le altezze vere.",
})

# La regola fissa di un disegno dall'alto: da tenere e' il disegno, non la
# prospettiva. Stessi tre gradi, stessi nomi delle altre scene.
_REGOLA_PIANTA = (
    "Edit this exact drawing. Keep the framing, the scale and every wall, "
    "opening, building footprint, road, path and plot line exactly where it "
    "is and at the same thickness; do not add, remove, move or reshape any of "
    "them. Keep the view straight from above unless the style below asks for "
    "an axonometric view. Change only the look described below."
)
FEDELTA_PIANTA = _blocchi(
    ("rigida", "Rigida",
     _REGOLA_PIANTA + " Match the drawing strictly: same number and position of "
     "rooms, doors, windows, stairs and buildings; if in doubt, change less."),
    ("bilanciata", "Bilanciata", _REGOLA_PIANTA),
    ("libera", "Libera",
     "Edit this drawing. Keep the framing, the scale and the position of every "
     "wall, opening, footprint and road; you may simplify small drawn details "
     "and add plausible floor finishes, planting and paving. Keep the view "
     "straight from above unless the style below asks for an axonometric view. "
     "Change the look described below."),
)

# Lo stile della tavola: prende il posto del look fotografico. Ogni voce dice
# cosa diventano pavimenti, tetti, terreno e verde, in modo che valga per i
# tre tipi (una pianta non ha tetti, una planimetria non ha pavimenti: il
# modello prende quello che c'e').
LOOK_PIANTA = _descritti(_blocchi(
    ("materica", "Resa materica",
     "Rendered presentation plan: walls cut in solid charcoal, floors in real "
     "materials with visible grain (light oak in living rooms and bedrooms, "
     "large-format stone tiles in kitchens and bathrooms), roofs in their real "
     "materials, lawns with fine grass texture, trees as soft round canopies."),
    ("concorso", "Colori da concorso",
     "Competition-style coloured plan: flat muted colours with no texture, "
     "walls and roofs in solid dark grey, floors and paving in warm light "
     "neutrals, lawns in soft sage green, water in pale blue-grey, thin "
     "crisp outlines."),
    ("biancoenero", "Bianco e nero con ombre",
     "Black and white architectural plan: white floors and ground, walls and "
     "cut elements in solid black, fine grey hatching for paving and planting, "
     "soft grey cast shadows as the only tone."),
    ("assonometria", "Assonometria",
     "Cut-away isometric view at 45 degrees from above: walls and buildings "
     "extruded to their real height (2.7 m per storey), cut at 1.2 m with the "
     "cut in solid charcoal, floors and ground in real materials, clean light "
     "background, no roof over the cut storey."),
    ("plastico", "Plastico bianco",
     "Photograph of a white architectural scale model from straight above: "
     "matte white card for buildings and walls, pale basswood for the ground "
     "and paving, trees as small white spheres, crisp cut edges."),
    ("drone", "Foto dall'alto",
     "Photorealistic aerial orthophoto taken by a drone at about 120 m, "
     "straight down: real roof materials with gentle weathering, mowed lawns, "
     "tree canopies, paving and asphalt with true texture; inside a building "
     "the roof is removed and the floors show their real materials."),
    ("acquerello", "Acquerello",
     "Architectural watercolour plan: fine ink lines on every wall and edge, "
     "loose transparent washes for floors, lawns and trees, soft colour "
     "bleeding, white paper showing through."),
), {
    "materica": "Pavimenti e tetti nei materiali veri, muri tagliati pieni.",
    "concorso": "Colori piatti e tenui, linee nette, niente texture.",
    "biancoenero": "Bianco e nero, retini grigi, solo le ombre fanno tono.",
    "assonometria": "Muri alzati a 2,70 m e tagliati, vista a 45 gradi.",
    "plastico": "Cartoncino bianco e legno chiaro, come un plastico.",
    "drone": "Come una foto da drone dritta verso il basso.",
    "acquerello": "Linee a china e velature trasparenti.",
})

# Luce e ombre di una tavola: la convenzione e' il sole da nord-ovest. Nel
# planivolumetrico le ombre lunghe fanno leggere le altezze.
LUCE_PIANTA = _descritti(_blocchi(
    ("nordovest", "Ombre morbide da nord-ovest",
     "Soft daylight from the top left (north-west), short soft shadows cast "
     "by walls, buildings and trees towards the bottom right."),
    ("radente", "Sole basso, ombre lunghe",
     "Low late-afternoon sun from the left: long crisp shadows that show the "
     "height of every wall, building and tree, warm light on the lit sides."),
    ("diffusa", "Luce diffusa, senza ombre",
     "Even diffuse light with no cast shadows, as on an overcast day: every "
     "part of the drawing equally readable."),
), {
    "nordovest": "La convenzione delle tavole: ombre corte verso il basso a destra.",
    "radente": "Ombre lunghe: si leggono le altezze, utile nel planivolumetrico.",
    "diffusa": "Tutto leggibile, nessuna ombra.",
})

QUALITA_PIANTA = _blocchi(
    ("base", "Base", "Professional architectural presentation drawing, clean and legible."),
    ("32k", "Altissima definizione",
     "Professional architectural presentation drawing, 32k, ultra-detailed, "
     "competition board quality."),
)

COSA_EVITARE_PIANTA = Blocco(
    "evitare-pianta",
    "Cosa evitare · pianta",
    "Avoid: perspective or tilted camera unless the style asks for it, text, "
    "labels, room names, dimension lines, north arrows, scale bars, new walls "
    "or rooms, bent or doubled lines, CGI look.",
)


# --- Arreda per zone (bozza 16, flusso 6) --------------------------------------

# Una zona e' un'area del Ritocca su una pianta: un rettangolo o una selezione
# libera, con il tipo di stanza. Lo stile vale per tutte le zone di un invio.
# La nota di ogni zona dice cosa mettere e cosa non toccare: muri, aperture e
# le altre zone. Testi scelti, mai provati: le misure degli arredi in pianta
# sono il punto dove il modello sbaglia di piu'.
STANZE_ARREDA = {
    "soggiorno": ("Soggiorno", "a living room: a sofa, armchairs, a coffee table, a rug and a TV unit"),
    "cucina": ("Cucina", "a kitchen: a run of base cabinets with sink and hob along the wall, a small island if there is room"),
    "pranzo": ("Pranzo", "a dining area: a table for six with chairs and a sideboard"),
    "camera": ("Camera", "a double bedroom: a double bed with two bedside tables, a wardrobe along a wall"),
    "cameretta": ("Cameretta", "a single bedroom: a single bed, a desk with a chair and a wardrobe"),
    "bagno": ("Bagno", "a bathroom: toilet, washbasin with vanity, a shower or a bath where there is room"),
    "studio": ("Studio", "a home office: a desk with a chair, shelving along a wall and an armchair"),
    "ingresso": ("Ingresso", "an entrance hall: a coat cabinet, a bench and a console"),
}
STILI_ARREDA = {
    "nordico": ("Nordico", "Scandinavian style: light oak, white and pale grey fabrics"),
    "contemporaneo": ("Contemporaneo caldo", "warm contemporary style: walnut, cream fabrics and brass details"),
    "minimale": ("Minimale", "minimal style: few pieces, white lacquer, light grey stone"),
    "industriale": ("Industriale", "industrial style: black steel, dark leather and reclaimed wood"),
    "mediterraneo": ("Mediterraneo", "Mediterranean style: natural linen, rattan, terracotta and whitewashed wood"),
}


def _arreda(stanza: object, stile: object) -> tuple[str, str]:
    if not isinstance(stanza, str) or stanza not in STANZE_ARREDA:
        raise SceltaNonValida(
            f"\"{stanza}\" non e' un tipo di stanza di Arreda.",
            "Scegli il tipo di stanza per ogni zona: " + ", ".join(n.lower() for n, _ in STANZE_ARREDA.values()) + ".",
        )
    if not isinstance(stile, str) or stile not in STILI_ARREDA:
        raise SceltaNonValida(
            f"\"{stile}\" non e' uno stile di Arreda.",
            "Scegli uno stile: " + ", ".join(n.lower() for n, _ in STILI_ARREDA.values()) + ".",
        )
    return stanza, stile


def nota_arreda(stanza: object, stile: object) -> str:
    """La nota di una zona di Arreda: cosa mettere, a che misura, cosa non toccare."""
    stanza, stile = _arreda(stanza, stile)
    return (f"furnish this area as {STANZE_ARREDA[stanza][1]}, in {STILI_ARREDA[stile][1]}; "
            "furniture at real sizes for the room, at least 80 cm of walking space, nothing in "
            "front of doors or windows, seen from straight above in the same rendering style and "
            "light as the rest of the plan; keep walls, openings and every other area unchanged")


def nome_arreda(stanza: str, stile: str) -> str:
    """Come lo Studio chiama una zona: «Arreda · soggiorno, nordico»."""
    return f"Arreda · {STANZE_ARREDA[stanza][0].lower()}, {STILI_ARREDA[stile][0].lower()}"


# --- Punto di vista dalla pianta, senza Allplan (bozza 16, flusso 7) -------------

# Dalla pianta resa a una foto ad altezza d'occhi. Partono due immagini: la
# pianta, e la stessa pianta con un punto e un cono rossi dove sta la camera
# e verso dove guarda (li disegna il motore, core/punto.py). Senza Allplan il
# modello immagina la stanza: altezze e arredi non disegnati sono suoi, e lo
# Studio lo scrive sull'immagine («stanza immaginata dalla pianta»). Con
# Allplan la camera vera aspetta la sonda di PythonParts. Testi mai provati.
ALTEZZA_OCCHI_M = config.PUNTO_DI_VISTA_ALTEZZA_OCCHI_M
ALTEZZA_SOFFITTO_M = config.PUNTO_DI_VISTA_ALTEZZA_SOFFITTO_M

PUNTO_DI_VISTA = Blocco(
    "punto-di-vista",
    "Punto di vista dalla pianta",
    "Image 1 is a floor plan seen from straight above. Image 2 is the same plan "
    "with a red dot and a red cone: the dot is a camera at eye height "
    f"{ALTEZZA_OCCHI_M} m, the cone shows where it looks. Render the photograph "
    "that camera would take, at eye level with straight verticals: walls, "
    "doors, windows, stairs and furniture where the plan has them, ceiling "
    f"height {ALTEZZA_SOFFITTO_M} m. Do not add rooms, walls or openings that "
    "are not in the plan, and do not draw the dot, the cone or any plan "
    "lines in the photograph.",
)
PUNTO_DI_VISTA_SITO = Blocco(
    "punto-di-vista-sito",
    "Punto di vista dalla planimetria",
    "Image 1 is a site plan seen from straight above. Image 2 is the same plan "
    "with a red dot and a red cone: the dot is a person standing on the ground "
    f"with eyes at {ALTEZZA_OCCHI_M} m, the cone shows where they look. Render "
    "the photograph that person would take, at eye level with straight "
    "verticals: buildings, roads, paths and trees where the plan has them, "
    "buildings at believable heights. Do not add buildings or roads that are "
    "not in the plan, and do not draw the dot, the cone or any plan lines in "
    "the photograph.",
)
STILI_PUNTO = {
    "giorno": ("Giorno, luce naturale",
               "Professional architectural photograph, natural daylight, soft shadows, "
               "true-to-life materials and colours."),
    "caldo": ("Pomeriggio caldo",
              "Warm late-afternoon sunlight raking in through the windows, long soft shadows, "
              "golden tones, editorial interior photograph."),
    "sera": ("Sera, luci accese",
             "Evening, warm 3000 K lamps switched on, dark blue sky outside, cosy contrast, "
             "editorial photograph."),
}


def scena_punto(tipo: str | None) -> str:
    """La scena dell'immagine che esce: un interno da una pianta, un esterno da una planimetria."""
    return INTERNO if (tipo or TIPO_PREDEFINITO) == EDIFICIO else ESTERNO


def componi_punto_di_vista(tipo: str | None, stile: object, materiali: str = "") -> str:
    """Il prompt del punto di vista: le due immagini, la camera, lo stile, cosa evitare."""
    if not isinstance(stile, str) or stile not in STILI_PUNTO:
        raise SceltaNonValida(
            f"\"{stile}\" non e' uno stile del punto di vista.",
            "Scegli fra " + ", ".join(n.lower() for n, _ in STILI_PUNTO.values()) + ".",
        )
    regola = PUNTO_DI_VISTA if (tipo or TIPO_PREDEFINITO) == EDIFICIO else PUNTO_DI_VISTA_SITO
    pezzi = [regola.testo, STILI_PUNTO[stile][1]]
    if frase_materiali(materiali):
        pezzi.append(frase_materiali(materiali))
    pezzi.append(COSA_EVITARE.testo)
    return " ".join(pezzi)


PERSONE = {
    "nessuna": Blocco("nessuna", "Nessuna", "No people."),
    **dict((
        _aggiunta("poche", "Poche",
                  "Two or three people standing or walking, small in the frame, for scale"),
        _aggiunta("movimento", "In movimento",
                  "A few people walking, slightly motion-blurred, for scale"),
    )),
}

QUALITA = _blocchi(
    ("base", "Base", "Professional architectural photography, natural detail."),
    ("32k", "Altissima definizione",
     "Professional architectural photography, 32k, ultra-detailed, archi "
     "magazine quality."),
)

# Asse -> (blocchi possibili, scene in cui vale). Un asse fuori dalla sua
# scena si rifiuta: il cielo di un interno non esiste. None vuol dire che i
# blocchi dipendono dalla scena: vedi PER_SCENA.
ASSI = {
    "tipo": (TIPI_PIANTA, (PIANTA,)),
    "fedelta": (None, SCENE),
    "look": (None, SCENE),
    "luce": (None, SCENE),
    "cielo": (CIELO, (ESTERNO,)),
    "fuori": (FUORI, (INTERNO,)),
    "arredo": (ARREDO, (INTERNO,)),
    "sfondo": (SFONDO, (PRODOTTO,)),
    "intorno": (INTORNO, (ESTERNO,)),
    "verde": (VERDE, (ESTERNO,)),
    "persone": (PERSONE, (ESTERNO, INTERNO)),
    "qualita": (None, SCENE),
}

PER_SCENA = {
    "fedelta": {ESTERNO: FEDELTA, INTERNO: FEDELTA, PRODOTTO: FEDELTA_PRODOTTO, PIANTA: FEDELTA_PIANTA},
    "look": {ESTERNO: LOOK, INTERNO: LOOK, PRODOTTO: LOOK_PRODOTTO, PIANTA: LOOK_PIANTA},
    "luce": {ESTERNO: LUCE_ESTERNI, INTERNO: LUCE_INTERNI, PRODOTTO: LUCE_PRODOTTO, PIANTA: LUCE_PIANTA},
    "qualita": {ESTERNO: QUALITA, INTERNO: QUALITA, PRODOTTO: QUALITA_PRODOTTO, PIANTA: QUALITA_PIANTA},
}

QUALITA_PREDEFINITA = "base"


def _elenco(asse: str, scena: str) -> dict[str, Blocco]:
    elenco, _scene = ASSI[asse]
    return elenco if elenco is not None else PER_SCENA[asse][scena]


@dataclass(frozen=True)
class Scelte:
    """Le scelte di stile di un lavoro. Un campo vuoto vuol dire: quel blocco non parte."""

    scena: str = ESTERNO
    materiali: str = ""
    # Solo per una pianta: che disegno e' (pianta, planimetria, planivolumetrico).
    tipo: str | None = None
    look: str | None = None
    luce: str | None = None
    cielo: str | None = None
    fuori: str | None = None
    arredo: str | None = None
    sfondo: str | None = None
    intorno: str | None = None
    verde: str | None = None
    persone: str | None = None
    qualita: str = QUALITA_PREDEFINITA
    fedelta: str = FEDELTA_PREDEFINITA
    resa: str = FOTO
    # Non e' un blocco di prompt: e' la grandezza del render che si chiede al
    # modello. Sta qui perche' viaggia con le scelte dalla palette alla coda.
    risoluzione: str = config.RISOLUZIONE_RENDER_PREDEFINITA

    def __post_init__(self) -> None:
        if self.risoluzione not in config.RISOLUZIONI_RENDER:
            raise SceltaNonValida(
                f"La risoluzione del render \"{self.risoluzione}\" non esiste.",
                f"Scegli fra {', '.join(config.RISOLUZIONI_RENDER)}.",
            )

    def a_dizionario(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def da_dizionario(cls, dati: dict) -> "Scelte":
        sconosciute = sorted(set(dati) - {f.name for f in fields(cls)})
        if sconosciute:
            raise SceltaNonValida(
                f"Nelle scelte di stile c'e' una voce che non conosco: {sconosciute[0]}.",
                "Togli quella voce dal lavoro. Le voci possibili sono: "
                + ", ".join(f.name for f in fields(cls)) + ".",
            )
        return cls(**dati)


@dataclass(frozen=True)
class PresetStile:
    """Un preset curato: un nome e una combinazione di blocchi."""

    identificativo: str
    nome: str
    scelte: Scelte
    versione: str = VERSIONE
    note: str = field(default="")

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome del preset {self.identificativo}")


def _esterno(identificativo, nome, look, luce, cielo, persone) -> PresetStile:
    return PresetStile(identificativo, nome, Scelte(
        scena=ESTERNO, look=look, luce=luce, cielo=cielo, intorno="niente",
        verde="nessuno", persone=persone,
    ))


def _interno(identificativo, nome, look, luce, fuori, persone) -> PresetStile:
    return PresetStile(identificativo, nome, Scelte(
        scena=INTERNO, look=look, luce=luce, fuori=fuori, arredo="nessuno",
        persone=persone,
    ))


def _prodotto(identificativo, nome, look, luce, sfondo) -> PresetStile:
    return PresetStile(identificativo, nome, Scelte(
        scena=PRODOTTO, look=look, luce=luce, sfondo=sfondo,
    ))


def _pianta(identificativo, nome, tipo, look, luce) -> PresetStile:
    return PresetStile(identificativo, nome, Scelte(
        scena=PIANTA, tipo=tipo, look=look, luce=luce,
    ))


# Le combinazioni della bozza 4. Intorno ("niente"), verde ("nessuno") e arredo
# ("nessuno") non sono nelle colonne delle tabelle, ma ci sono nelle lunghezze
# che la bozza ha misurato: solo con loro i conti tornano al carattere. Lo
# controlla un test.
PRESET_STILE = {
    p.identificativo: p
    for p in (
        _esterno("rivista", "Rivista d'architettura", "canon", "mezzogiorno", "sereno", "nessuna"),
        _esterno("luce-calda", "Luce naturale calda", "gfx", "estate", "sereno", "nessuna"),
        _esterno("pellicola-morbida", "Pellicola morbida", "portra160", "giorno", "sereno", "nessuna"),
        _esterno("urbano", "Urbano editoriale", "metropolis", "giorno", "coperto", "movimento"),
        _esterno("ora-blu", "Ora blu", "leica", "blu", "sereno", "nessuna"),
        _esterno("notte-luna", "Notte con luna", "leica", "notte", "sereno", "nessuna"),
        _esterno("pioggia", "Giornata di pioggia", "portra400", "giorno", "pioggia", "movimento"),
        _esterno("autunno", "Autunno nebbioso", "portra400", "giorno", "autunno", "movimento"),
        _interno("interno-rivista", "Interno rivista", "canon", "mattino", "neutra", "nessuna"),
        _interno("interno-caldo", "Interno caldo", "gfx", "pomeriggio", "verde", "nessuna"),
        _interno("interno-pellicola", "Interno pellicola morbida", "portra160", "coperto_int", "neutra", "nessuna"),
        _interno("interno-sera", "Interno sera", "leica", "sera", "citta", "nessuna"),
        _interno("interno-notte", "Interno notte, lampade", "leica", "notte_int", "neutra", "nessuna"),
        _interno("interno-vissuto", "Interno vissuto", "x100v", "pomeriggio", "verde", "movimento"),
        _prodotto("arredo-catalogo", "Catalogo, fondo bianco", "hasselblad", "softbox", "bianco"),
        _prodotto("arredo-studio", "Studio, grigio caldo", "hasselblad", "finestra", "grigio"),
        _prodotto("arredo-editoriale", "Editoriale, ombre di sole", "phaseone", "sole", "calce"),
        _prodotto("arredo-dettaglio", "Dettaglio materiale", "macro", "radente", "grigio"),
        _prodotto("arredo-controluce", "Controluce, fondo scuro", "leica", "controluce", "scuro"),
        _prodotto("arredo-ambientato", "Ambientato, stanza sfocata", "gfx", "finestra", "ambiente"),
        # Bozza 16: i nomi delle chip del Design canvas (artboard C) e delle
        # schede «Preset nuovi» della pagina Flussi.
        _pianta("pianta-materica", "Pianta, resa materica", EDIFICIO, "materica", "nordovest"),
        _pianta("pianta-assonometria", "Pianta in assonometria", EDIFICIO, "assonometria", "nordovest"),
        _pianta("pianta-concorso", "Pianta colorata da concorso", EDIFICIO, "concorso", "diffusa"),
        _pianta("pianta-biancoenero", "Pianta bianco e nero con ombre", EDIFICIO, "biancoenero", "nordovest"),
        _pianta("planimetria-illustrata", "Planimetria illustrata", SITO, "concorso", "nordovest"),
        _pianta("planimetria-drone", "Planimetria, foto da drone", SITO, "drone", "nordovest"),
        _pianta("planimetria-acquerello", "Planimetria ad acquerello", SITO, "acquerello", "nordovest"),
        _pianta("planivolumetrico-plastico", "Planivolumetrico, plastico bianco", VOLUMI, "plastico", "radente"),
        _pianta("planivolumetrico-materico", "Planivolumetrico materico", VOLUMI, "materica", "radente"),
    )
}


def preset_stile(identificativo: str) -> PresetStile:
    try:
        return PRESET_STILE[identificativo]
    except KeyError:
        raise SceltaNonValida(
            f"Non esiste un preset di stile chiamato \"{identificativo}\".",
            f"I preset di stile sono: {', '.join(PRESET_STILE)}.",
        ) from None


def da_preset(identificativo: str, **cambi) -> Scelte:
    """Le scelte di un preset, con i cambi dell'utente sopra. Il resto resta com'e'."""
    return replace(preset_stile(identificativo).scelte, **cambi)


def _blocco(asse: str, valore: str, scena: str) -> Blocco:
    elenco, scene = ASSI[asse]
    if scena not in scene:
        raise SceltaNonValida(
            f"La scelta \"{asse}\" non vale per una vista {scena}.",
            f"Togli {asse} dalle scelte, oppure cambia la scena in "
            f"{' o '.join(scene)}.",
        )
    elenco = _elenco(asse, scena)
    try:
        return elenco[valore]
    except KeyError:
        raise SceltaNonValida(
            f"Per \"{asse}\" non esiste la scelta \"{valore}\" in una vista {scena}.",
            f"Le scelte possibili sono: {', '.join(elenco)}.",
        ) from None


def voci(asse: str, scena: str) -> dict[str, Blocco]:
    """I blocchi possibili di un asse in una scena: quelli che lo Studio mostra."""
    return _elenco(asse, scena)


def blocco(asse: str, valore: str, scena: str) -> Blocco:
    """Il blocco di una scelta, o l'errore che dice perche' non esiste."""
    return _blocco(asse, valore, scena)


def blocchi_scelti(scelte: Scelte) -> list[Blocco]:
    """I blocchi che partono, nell'ordine fisso. I materiali non sono un blocco: sono parole dell'utente."""
    if scelte.scena not in SCENE:
        raise SceltaNonValida(
            f"La scena \"{scelte.scena}\" non esiste.",
            "Scegli esterno, interno, arredo o pianta.",
        )
    if scelte.scena != PIANTA and scelte.tipo:
        _blocco("tipo", scelte.tipo, scelte.scena)  # il tipo di disegno vale solo per una pianta
    if scelte.scena == PIANTA and resa_valida(scelte.resa) != FOTO:
        raise SceltaNonValida(
            f"Una pianta non prende la resa «{NOMI_RESE[scelte.resa]}»: lo stile della tavola fa gia' da resa.",
            "Scegli lo stile della tavola (resa materica, colori da concorso, acquerello...).",
        )
    ordine = [a for a in ORDINE_ASSI if scelte.scena in ASSI[a][1]]
    # Un asse di un'altra scena, se compilato, si rifiuta invece di sparire
    # in silenzio: l'utente crederebbe di averlo mandato.
    for asse in ORDINE_ASSI:
        if asse not in ordine and getattr(scelte, asse):
            _blocco(asse, getattr(scelte, asse), scelte.scena)
    resa = resa_valida(scelte.resa)
    via = SPENTI_DA_RESA[resa]
    # Per una pianta la scena e' il tipo di disegno: dice gia' che e' visto dall'alto.
    blocchi = [_blocco("fedelta", scelte.fedelta or FEDELTA_PREDEFINITA, scelte.scena),
               _blocco("tipo", scelte.tipo or TIPO_PREDEFINITO, PIANTA) if scelte.scena == PIANTA
               else SCENA[scelte.scena]]
    if resa != FOTO:
        blocchi.append(RESA[resa])
    for asse in ordine:
        valore = getattr(scelte, asse)
        if valore and asse not in via:
            blocchi.append(_blocco(asse, valore, scelte.scena))
        elif valore:
            _blocco(asse, valore, scelte.scena)  # spento, ma deve comunque esistere
    blocchi.append(_evitare(resa, scelte.scena))
    return blocchi


def frase_materiali(materiali: str) -> str:
    testo = " ".join((materiali or "").split()).rstrip(".")
    return f"Materials: {testo}." if testo else ""


def componi(scelte: Scelte) -> str:
    """Il prompt che parte al modello, in inglese, nell'ordine fisso."""
    blocchi = blocchi_scelti(scelte)
    pezzi = [b.testo for b in blocchi[:2]]  # regola fissa (secondo la fedelta'), scena
    materiali = frase_materiali(scelte.materiali) if "materiali" not in spenti(scelte) else ""
    if materiali:
        pezzi.append(materiali)
    pezzi += [b.testo for b in blocchi[2:]]
    return " ".join(pezzi)


# L'ordine degli assi nel prompt, per chi compone solo una parte (un passo).
ORDINE_ASSI = ("look", "luce", "cielo", "fuori", "arredo", "sfondo", "intorno", "verde", "persone", "qualita")


# --- passi: richieste a parole su un render (Studio · Passi) ---------------

# Su un render gia' fatto lo stile c'e': la regola di un passo non dice
# "cambia solo il look" ma "cambia solo quello che ti chiedo". Come ogni
# blocco, non provata con il modello.
REGOLA_PASSO = Blocco(
    "regola-passo",
    "Regola fissa di un passo",
    "Edit this exact image. Keep the camera, framing, proportions and every "
    "building element exactly as they are; do not add, remove or reshape any "
    "architecture. Keep the light as it is unless the change below is about "
    "light, time of day or weather. Make only the change described below and "
    "leave everything else as it is.",
)


def _pulisci_richieste(richieste) -> list[str]:
    pulite = [" ".join((r or "").split()).rstrip(".") for r in (richieste or ())]
    if not pulite or not all(pulite):
        raise SceltaNonValida(
            "Un passo senza richiesta non cambia niente.",
            "Scrivi cosa cambiare, per esempio «due alberi davanti al fronte».",
        )
    return pulite


def _frase_richieste(pulite: list[str], apertura: str) -> str:
    """Le richieste dell'utente come le ha scritte, poi cosa non toccare.

    Una richiesta a parole di solito aggiunge qualcosa (alberi, persone,
    un cielo): finisce con NON_COPRIRE come i blocchi che aggiungono.
    """
    return f"{apertura} {'; '.join(pulite)}; {NON_COPRIRE}."


def componi_richieste(scena: str, richieste) -> str:
    """Il prompt di un passo fatto su un render: regola del passo, scena, le richieste, cosa evitare.

    Le richieste passano come le scrive l'utente, anche in italiano, come i
    materiali: qui non c'e' nessun modello linguistico che le traduca.
    """
    if scena not in SCENE:
        raise SceltaNonValida(f"La scena \"{scena}\" non esiste.", "Scegli esterno, interno, arredo o pianta.")
    pulite = _pulisci_richieste(richieste)
    apertura = "Change:" if len(pulite) == 1 else "Changes:"
    return " ".join([REGOLA_PASSO.testo, SCENA[scena].testo,
                     _frase_richieste(pulite, apertura), _evitare(FOTO, scena).testo])


def aggiungi_richieste(base: str, richieste) -> str:
    """Un prompt dalla vista con in piu' le richieste dei passi: «Rifai pulito dalla vista».

    Le richieste entrano prima di «cosa evitare», che resta in coda come
    sempre. Se il testo di partenza e' stato scritto a mano e non finisce con
    «cosa evitare», le richieste vanno in fondo.
    """
    if not richieste:
        return base
    frase = _frase_richieste(_pulisci_richieste(richieste), "Also make these changes:")
    return _prima_di_evitare(base, frase)


def _prima_di_evitare(base: str, frase: str) -> str:
    """La frase subito prima di «cosa evitare» (quello di sempre o quello della resa), o in fondo."""
    base = base.strip()
    for evitare in (COSA_EVITARE, COSA_EVITARE_PRODOTTO, COSA_EVITARE_PIANTA, *EVITARE_DA_RESA.values()):
        if base.endswith(evitare.testo):
            testa = base[: -len(evitare.testo)].rstrip()
            return f"{testa} {frase} {evitare.testo}"
    return f"{base} {frase}"


def componi_passo(scena: str, cambi: dict[str, str]) -> str:
    """Il prompt di un passo fatto su un render: regola fissa, scena, solo gli assi che cambiano, cosa evitare.

    Serve al banco di prova (piano "catena") e servira' all'albero dei passi:
    su un render gia' fatto non si rimanda tutto lo stile, solo la richiesta
    nuova, per esempio {"verde": "poco"}.
    """
    if scena not in SCENE:
        raise SceltaNonValida(f"La scena \"{scena}\" non esiste.", "Scegli esterno, interno, arredo o pianta.")
    if not cambi:
        raise SceltaNonValida(
            "Un passo senza richieste non cambia niente.",
            "Indica almeno un asse da cambiare, per esempio verde o persone.",
        )
    sconosciuti = sorted(set(cambi) - set(ORDINE_ASSI))
    if sconosciuti:
        raise SceltaNonValida(
            f"\"{sconosciuti[0]}\" non e' un asse dei blocchi.",
            f"Gli assi sono: {', '.join(ORDINE_ASSI)}.",
        )
    pezzi = [REGOLA_FISSA.testo, SCENA[scena].testo]
    pezzi += [_blocco(asse, cambi[asse], scena).testo for asse in ORDINE_ASSI if asse in cambi]
    pezzi.append(_evitare(FOTO, scena).testo)
    return " ".join(pezzi)


# --- riferimento per lo stile (Studio · Genera, bozza 6) ----------------------

# La seconda immagine dell'invio: una foto scelta dall'utente da cui prendere
# solo l'atmosfera. Come ogni blocco, non provato con il modello; il primo
# render con un riferimento e' anche la prima volta che Nano Banana 2 riceve
# due immagini in una chiamata vera.
RIFERIMENTO_STILE = Blocco(
    "riferimento",
    "Immagine di riferimento per lo stile",
    "The second image is a style reference only: take from it the colour "
    "palette, the light and the look of the materials. Do not copy its "
    "geometry, camera, objects or composition; the building stays the one in "
    "the first image.",
)


# «Porta su un'altra vista» (2026-11-04): la seconda immagine e' un render
# dello stesso progetto da un'altra camera, gia' ritoccato. Qui il modello deve
# riprendere materiali e oggetti, non solo l'atmosfera: e' il contrario di
# RIFERIMENTO_STILE su oggetti e arredo. Non provato con il modello.
RIFERIMENTO_COERENZA = Blocco(
    "riferimento-coerenza",
    "Stesso progetto da un'altra vista",
    "The second image is the same project rendered from another camera. Keep "
    "this render consistent with it: the same materials, colours, furniture, "
    "objects, people style and light, wherever they are visible from this "
    "camera. Do not copy its camera or composition; the geometry and the "
    "viewpoint stay the ones in the first image.",
)


# «Stile da esempi» (bozza 14, 2026-11-04): da 2 a 4 render d'esempio dello
# stile da ottenere, al posto del riferimento singolo. Come il riferimento:
# atmosfera, luce, materiali e taglio fotografico si prendono, la geometria
# no. Non provata con il modello.
ESEMPI_STILE = Blocco(
    "esempi-stile",
    "Stile da esempi",
    "Images 2 to {ultima} are example renders of the style to match: take "
    "from them what they have in common, the colour grading, the light, the "
    "look of the materials, the photographic treatment and the level of "
    "detail. Do not copy their buildings, cameras, objects or compositions; "
    "the building and the viewpoint stay the ones in the first image.",
)


def aggiungi_riferimento(base: str, coerenza: bool = False, esempi: int = 0) -> str:
    """Il prompt con la frase del riferimento prima di «cosa evitare», se c'e'.

    `esempi` e' quanti render d'esempio partono oltre al riferimento: con
    almeno uno la frase diventa quella di «Stile da esempi».
    """
    if esempi and not coerenza:
        return _prima_di_evitare(base, ESEMPI_STILE.testo.format(ultima=2 + esempi))
    return _prima_di_evitare(base, (RIFERIMENTO_COERENZA if coerenza else RIFERIMENTO_STILE).testo)


# --- riferimenti di oggetti e persone (Studio, bozza 13, 2026-11-04) ----------

# Le immagini che l'utente porta per dire «metti questo»: una poltrona, una
# persona, un albero, un'auto. Partono dopo la vista o il render e dopo le
# altre immagini; nel testo l'utente le chiama «Rif. 1», «Rif. 2»... e questa
# frase dice al modello quale immagine e' quale. E' il contrario del
# riferimento per lo stile: qui l'oggetto si copia, l'atmosfera no. Come ogni
# blocco, non provata con il modello.
INSERTI_REGOLA = Blocco(
    "inserti",
    "Riferimenti di oggetti e persone",
    "These images show objects or people to place into image 1. Insert each "
    "one only where the text asks for it, keeping its shape, colours and "
    "materials, at the scale, perspective and light of image 1, with a "
    "matching shadow. Do not copy the background, camera or framing of a "
    "reference image, and do not change anything else in image 1.",
)

# Quando una nota di Ritocca ha la sua immagine: la nota dice da quale Rif.
NOTA_CON_INSERTO = "use the object or person shown in Rif. {numero}"


def frase_inserti(prima_immagine: int, quanti: int) -> str:
    """Quale immagine e' ciascun Rif., poi la regola. Vuota se non ce ne sono."""
    if quanti <= 0:
        return ""
    nomi = "; ".join(f"Rif. {n} is image {prima_immagine + n - 1}" for n in range(1, quanti + 1))
    return f"Reference images: {nomi}. {INSERTI_REGOLA.testo}"


def aggiungi_inserti(base: str, prima_immagine: int, quanti: int) -> str:
    """Il prompt con i riferimenti di oggetti e persone prima di «cosa evitare», se ce ne sono."""
    if quanti <= 0:
        return base
    return _prima_di_evitare(base, frase_inserti(prima_immagine, quanti))


# --- aree e note (banco di prova, piano "aree"; Ritocca non c'e' ancora) -----

# Due modi di dire al modello dove intervenire. Nessuno dei due e' provato:
# il piano "aree" del banco serve a sceglierne uno.
AREE_CONTORNI = Blocco(
    "aree-contorni",
    "Aree disegnate sull'immagine",
    "Edit this exact image. Numbered magenta outlines are drawn on it. Make "
    "each change listed below only inside the outline with its number. Outside "
    "the outlines keep every pixel exactly as it is. Remove the outlines and "
    "the numbers from the result.",
)

AREE_MASCHERA = Blocco(
    "aree-maschera",
    "Aree in una maschera",
    "Edit the first image. The second image is a mask of the same view: the "
    "numbered white areas are the only places to change. Make each change "
    "listed below only inside the white area with its number. Outside the "
    "white areas keep every pixel of the first image exactly as it is. Do not "
    "copy the mask into the result.",
)


# Come una riga del ritocco dice cosa fare in un tratto di pennello (bozza
# «flussi», 2026-11-09). «cambia» non aggiunge niente: la riga resta quella
# di prima. Testi mai provati con il modello.
AZIONI_AREE = {
    "aggiungi": "add this inside the area, keep what is around it",
    "togli": "remove this from the area and rebuild what is behind it, matching the surroundings",
}


def componi_aree(modo: Blocco, note: list[str], inserti: list[int | None] | None = None,
                 azioni: list[str] | None = None) -> str:
    """Il prompt di un invio con aree: come sono indicate, una riga per nota, cosa evitare.

    Le note passano come le scrive l'utente, anche in italiano, come i materiali.
    `inserti` dice, per ogni nota, il numero del suo Rif. (o None): la nota
    finisce con «use the object or person shown in Rif. N».
    """
    pulite = [" ".join((n or "").split()).rstrip(".") for n in note]
    if not pulite or not all(pulite):
        raise SceltaNonValida(
            "Un'area senza nota non dice al modello cosa fare.",
            "Scrivi una nota per ogni area, oppure togli l'area.",
        )
    inserti = list(inserti or [None] * len(pulite))
    azioni = list(azioni or [None] * len(pulite))
    righe = [f"Area {numero}" + (f" ({AZIONI_AREE[azione]})" if azione in AZIONI_AREE else "") + f": {nota}"
             + (f"; {NOTA_CON_INSERTO.format(numero=rif)}." if rif else ".")
             for numero, (nota, rif, azione) in enumerate(zip(pulite, inserti, azioni), start=1)]
    return " ".join([modo.testo, *righe, COSA_EVITARE.testo])


# --- inserisci nel contesto (Studio · Genera, bozza 9, rivista in bozza 10) ---

# La scena del fotoinserimento (thread del 2026-11-01): la prima immagine e'
# il contesto portato dall'utente (screenshot satellitare, ortofoto, foto da
# drone) con un contorno magenta dove va l'edificio; la seconda e' la vista
# Allplan. Il contesto va per primo perche' il rapporto del render segue la
# prima immagine. Testi riscritti dal prompt di Riccardo (Notion, «Transform
# this Google Maps satellite screenshot...») e dal suo flusso a parole: come
# ogni blocco, non provati con il modello.
ZENITALE = "zenitale"
VOLO = "volo"
# Bozza 10 (prova di Riccardo del 2026-11-01 con una foto da Street View):
# una foto scattata da terra, ad altezza d'occhio.
TERRA = "terra"

CONTESTO_REGOLA = Blocco(
    "contesto-regola",
    "Regola dell'inserimento nel contesto",
    "Photo insertion. The first image is the real site; the second image is a "
    "view of the new building designed for it. Place the building from the "
    "second image into the first image, inside the numbered magenta outline, "
    "and remove the outline and its number from the result. Adapt the "
    "building's perspective, scale and orientation to the site, so it stands "
    "on the ground at a believable size next to the roads, trees and "
    "buildings around it. Keep the building's shape, proportions and "
    "openings as designed; do not redesign it. The second image is an "
    "untextured CAD view: its flat greys and colours are not materials, so "
    "give the building real, photographed building materials, glass that "
    "reflects the site, and real weathering. Match the light, sun "
    "direction, shadows, colour, haze and grain of the site image, so the "
    "building looks photographed together with it.",
)

CONTESTO_FUORI_INTATTO = Blocco(
    "contesto-fuori",
    "Fuori dall'area il contesto resta com'e'",
    "Outside the outline keep every pixel of the site image exactly as it is.",
)

INQUADRATURE = _blocchi(
    (ZENITALE, "Zenitale",
     "The site image is a top-down aerial view: show the building from "
     "straight above, as roofs, terraces and the ground around it, with its "
     "shadow cast on the ground in the same direction as the other shadows."),
    (VOLO, "Volo d'uccello",
     "The site image is an oblique bird's-eye view: show the building from "
     "the same height and direction as the buildings around it, with its "
     "facades and roof foreshortened like theirs and its shadow in the same "
     "direction as the other shadows."),
    (TERRA, "Da terra (foto)",
     "The site image is a photograph taken from the ground at eye level: "
     "show the building as the same camera would see it, from the same eye "
     "height, with the same perspective, vanishing points and lens; size it "
     "against the cars, people, doors and trees in the photo; let objects "
     "in front of the outline, such as trees, poles or cars, stay in front "
     "of the building."),
)

CONTESTO_PULISCI_MAPPA = Blocco(
    "contesto-pulisci",
    "Pulisci lo screenshot della mappa",
    "The site image is a map screenshot: remove every interface element "
    "(labels, street names, pins, icons, logos, buttons, compass, "
    "watermarks) and fill those spots with what would realistically be "
    "underneath. Turn the whole image into a photorealistic, high-resolution "
    "aerial photograph of the same place, keeping every road, building "
    "footprint, tree and field in its position, size and orientation; do not "
    "add or remove buildings.",
)


def controlla_inquadratura(inquadratura: object) -> str:
    if inquadratura not in INQUADRATURE:
        raise SceltaNonValida(
            f"\"{inquadratura}\" non e' un'inquadratura del contesto.",
            "Scegli zenitale, volo d'uccello o da terra.",
        )
    return str(inquadratura)


def frase_luogo(luogo: str) -> str:
    """Il luogo come lo scrive l'utente (indirizzo o coordinate), anche in italiano."""
    testo = " ".join((luogo or "").split()).rstrip(".")
    return f"The site is at {testo}." if testo else ""


def componi_contesto(inquadratura: str, *, pulisci_mappa: bool = False,
                     luogo: str = "", materiali: str = "") -> str:
    """Il prompt di «Inserisci nel contesto»: regola, inquadratura, luogo, materiali, fuori dall'area, cosa evitare.

    Con «pulisci la mappa» il contesto non resta identico fuori dall'area:
    diventa una foto, e la frase del fuori intatto lascia il posto a quella
    della pulizia (direbbero due cose opposte).
    """
    pezzi = [CONTESTO_REGOLA.testo, INQUADRATURE[controlla_inquadratura(inquadratura)].testo]
    pezzi += [p for p in (frase_luogo(luogo), frase_materiali(materiali)) if p]
    pezzi.append(CONTESTO_PULISCI_MAPPA.testo if pulisci_mappa else CONTESTO_FUORI_INTATTO.testo)
    pezzi.append(COSA_EVITARE.testo)
    return " ".join(pezzi)


# --- Cambia: ora e mood (bozza 15, 2026-11-09) ---------------------------------

# Le scorciatoie di Cambia diventano miniature in due righe, «Ora del giorno»
# e «Tempo e mood» (bozza «flussi», scheda «Preset nuovi»). Ogni voce e' una
# richiesta di un passo: entra in componi_richieste dopo «Change:», come le
# richieste scritte a mano, e finisce con cosa tenere. Piu' voci scelte
# insieme = un invio per voce. Testi scritti con la skill di prompt
# architettonico; nessuno provato con il modello.
ORA = "ora"
MOOD = "mood"
GRUPPI_VARIAZIONI = {ORA: "Ora del giorno", MOOD: "Tempo e mood"}

_TIENI = "keep the building, every material, every object and the camera exactly as they are"


@dataclass(frozen=True)
class Variazione:
    """Una miniatura di Cambia: un nome per l'utente, una richiesta per il modello."""

    identificativo: str
    gruppo: str
    nome: str
    testo: str
    # Le scene in cui ha senso: la neve sui tetti non serve a un pezzo d'arredo.
    scene: tuple[str, ...] = (ESTERNO, INTERNO)
    origine: str = config.SCELTA

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome della variazione {self.identificativo}")


def _variazioni(*righe: Variazione) -> dict[str, Variazione]:
    return {v.identificativo: v for v in righe}


VARIAZIONI = _variazioni(
    Variazione("alba", ORA, "Alba",
               "only the time of day, to early sunrise: low warm sun just above the horizon from "
               "the side, soft peach and pale blue sky, long gentle shadows, a thin morning haze "
               f"in the distance; {_TIENI}"),
    Variazione("mattino", ORA, "Mattino",
               "only the time of day, to mid-morning: clear fresh daylight from the side, light "
               f"blue sky, crisp defined shadows of medium length, neutral white balance; {_TIENI}"),
    Variazione("mezzogiorno", ORA, "Mezzogiorno",
               "only the time of day, to midday: high bright sun, deep blue sky, short hard "
               f"shadows under eaves and balconies, saturated but natural colours; {_TIENI}"),
    Variazione("tramonto", ORA, "Tramonto",
               "only the time of day, to sunset: warm low raking light, long shadows, orange and "
               f"pink sky fading to blue, warm reflections on the glazing; {_TIENI}"),
    Variazione("ora_blu", ORA, "Ora blu",
               "only the time of day, to blue hour about twenty minutes after sunset: deep cobalt "
               "sky with a faint warm glow at the horizon, interior lights on at 3000 K glowing "
               f"through the glazing, soft ambient light with no hard shadows; {_TIENI}"),
    Variazione("notte", ORA, "Notte",
               "only the time of day, to night: dark sky, artificial lights switched on, light and "
               f"reflections coming only from the lamps, deep soft shadows; {_TIENI}"),
    Variazione("nuvoloso", MOOD, "Nuvoloso",
               "only the weather, to an overcast day: even soft diffuse light, light grey sky, "
               f"faint shadows, calm neutral tones; {_TIENI}"),
    Variazione("pioggia", MOOD, "Pioggia",
               "only the weather, to light rain: grey sky, wet reflective ground and surfaces, "
               f"small puddles, soft diffuse light; {_TIENI}", scene=(ESTERNO,)),
    Variazione("neve", MOOD, "Neve",
               "only the season, to winter with fresh snow on the ground, roofs and horizontal "
               f"surfaces, cold bright light, bare trees; {_TIENI}", scene=(ESTERNO,)),
    Variazione("nebbia", MOOD, "Nebbia",
               "only the weather, to a still foggy morning: dense soft fog that fades the "
               "background and the trees behind the building, diffuse grey-white light, no "
               "shadows, damp ground with faint reflections; the building stays sharp and readable "
               f"in the foreground; {_TIENI}", scene=(ESTERNO,)),
    Variazione("drammatico", MOOD, "Drammatico",
               "only the mood, to dramatic late afternoon: low sun from the side raking across "
               "the facade, long crisp shadows, dark storm clouds breaking behind the building "
               f"with bright gaps of light, strong local contrast in the sky; {_TIENI}",
               scene=(ESTERNO,)),
    Variazione("nordico", MOOD, "Nordico",
               "only the light, to a clear Scandinavian day in early spring: cool bright daylight, "
               "pale clear sky, crisp air, low-saturation colours, soft but defined shadows; "
               f"{_TIENI}"),
    Variazione("luci_accese", MOOD, "Luci accese",
               "switch on all the artificial lights, warm 3000 K, glowing through the glazing and "
               f"onto nearby surfaces; keep the daylight as it is and {_TIENI}"),
)


def variazioni(scena: str) -> list[Variazione]:
    """Le miniature di Cambia che hanno senso in questa scena, nell'ordine delle righe."""
    return [v for v in VARIAZIONI.values() if scena in v.scene]


def variazione(identificativo: object, scena: str) -> Variazione:
    """La variazione scelta, se esiste ed e' di questa scena."""
    trovata = VARIAZIONI.get(identificativo) if isinstance(identificativo, str) else None
    if trovata is None:
        raise SceltaNonValida(
            f"\"{identificativo}\" non e' una miniatura di Cambia.",
            "Scegli una delle miniature di «Ora del giorno» o «Tempo e mood».",
        )
    if scena not in trovata.scene:
        raise SceltaNonValida(
            f"«{trovata.nome}» non vale per questa scena.",
            "Scegli una delle miniature che Cambia mostra per questa immagine.",
        )
    return trovata


# --- Popola: persone, alberi, auto (bozza 15, 2026-11-09) -----------------------

# Due modi di dire dove: «Dipingo io» (pennello verde del Ritocca, la frase
# diventa la nota di ogni tratto) e «Decide il modello» (un passo a parole su
# tutta l'immagine, con le regole su dove metterle). La scala delle persone
# si lega a porte e piani: e' il punto dove Nano Banana sbaglia di piu', da
# provare. Testi mai provati con il modello.
PERSONE_POPOLA = "persone"
ALBERI_POPOLA = "alberi"
AUTO_POPOLA = "auto"


@dataclass(frozen=True)
class CosaPopola:
    """Cosa mette Popola: il nome, il soggetto per ogni quantita', come stanno e dove."""

    identificativo: str
    nome: str
    # quante -> il soggetto in inglese, con il numero dentro.
    soggetti: dict
    descrizione: str
    # come -> le parole del movimento; vuoto se non si muove.
    modi: dict
    # Dove li mette il modello quando decide lui, per scena.
    dove: dict
    # Lo stesso dove, come lo legge l'utente prima di applicare.
    dove_nome: dict
    scene: tuple[str, ...]

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome di Popola {self.identificativo}")
        for testo in self.dove_nome.values():
            controlla_etichetta(testo, f"il dove di Popola {self.identificativo}")


QUANTE_POPOLA = {"poche": "Poche", "alcune": "Alcune", "molte": "Molte"}
COME_POPOLA = {"ferme": "Ferme", "movimento": "In movimento"}

COSE_POPOLA = {c.identificativo: c for c in (
    CosaPopola(
        PERSONE_POPOLA, "Persone",
        {"poche": "two or three people", "alcune": "five to eight people", "molte": "about fifteen people"},
        "ordinary adults in contemporary everyday clothes, scaled to the doors and floor heights, "
        "lit from the same direction as the scene, each casting a soft shadow on the ground",
        {"ferme": "standing or sitting still", "movimento": "walking naturally, with a very slight motion blur"},
        {ESTERNO: "on the paths, terraces and near the entrances, never in front of the main facade",
         INTERNO: "in the free floor areas and at the tables, never blocking the main view of the room"},
        {ESTERNO: "sui percorsi, sulle terrazze e vicino agli ingressi, mai davanti alla facciata principale",
         INTERNO: "nei passaggi liberi e ai tavoli, mai davanti alla vista principale della stanza"},
        (ESTERNO, INTERNO),
    ),
    CosaPopola(
        ALBERI_POPOLA, "Alberi",
        {"poche": "one or two trees", "alcune": "three to five trees", "molte": "a row of eight to ten trees"},
        "native deciduous species of believable size for a planting about ten years old, trunks "
        "rooted in the ground, foliage lit like the rest of the scene, shadows following the sun "
        "direction, not covering windows or the main entrance",
        {},
        {ESTERNO: "along the edges of the plot, the paths and the street, never in front of windows "
                  "or the main entrance"},
        {ESTERNO: "ai bordi del lotto, lungo i percorsi e la strada, mai davanti alle finestre o all'ingresso"},
        (ESTERNO,),
    ),
    CosaPopola(
        AUTO_POPOLA, "Auto",
        {"poche": "one or two cars", "alcune": "three or four cars", "molte": "six to eight cars"},
        "recent unbranded European models in muted colours, correct perspective and size for the "
        "street, reflections and shadows consistent with the sky",
        {"ferme": "parked", "movimento": "moving slowly along the road, with a slight motion blur"},
        {ESTERNO: "only on roads, driveways and parking spaces, never on lawns or paths"},
        {ESTERNO: "solo su strade, passi carrai e parcheggi, mai sul prato o sui percorsi"},
        (ESTERNO,),
    ),
)}


def _popola(cosa: object, quante: object, come: object, scena: str) -> tuple[CosaPopola, str, str]:
    voce = COSE_POPOLA.get(cosa) if isinstance(cosa, str) else None
    if voce is None or scena not in voce.scene:
        validi = [c.nome.lower() for c in COSE_POPOLA.values() if scena in c.scene]
        raise SceltaNonValida(
            f"Popola non sa mettere \"{cosa}\" in questa scena.",
            f"Scegli fra {', '.join(validi)}." if validi else "Popola non vale per un pezzo d'arredo.",
        )
    if quante not in voce.soggetti:
        raise SceltaNonValida(f"\"{quante}\" non e' una quantita' di Popola.", "Scegli poche, alcune o molte.")
    if voce.modi and come not in voce.modi:
        raise SceltaNonValida(f"\"{come}\" non dice come stanno.", "Scegli ferme o in movimento.")
    return voce, str(quante), str(come) if voce.modi else ""


def _soggetto_popola(voce: CosaPopola, quante: str, come: str) -> str:
    pezzi = [voce.soggetti[quante], voce.descrizione]
    if come:
        pezzi.insert(1, voce.modi[come])
    return ", ".join(pezzi)


def nota_popola(cosa: object, quante: object, come: object, scena: str = ESTERNO) -> str:
    """La nota di ogni tratto verde di «Dipingo io»: cosa aggiungere dentro l'area."""
    voce, quante, come = _popola(cosa, quante, come, scena)
    return f"{_soggetto_popola(voce, quante, come)}; do not change anything outside the marked area"


def richiesta_popola(cosa: object, quante: object, come: object, scena: str = ESTERNO) -> str:
    """La richiesta di «Decide il modello»: cosa aggiungere e dove, su tutta l'immagine."""
    voce, quante, come = _popola(cosa, quante, come, scena)
    return f"add {_soggetto_popola(voce, quante, come)}, placed {voce.dove[scena]}"


def nome_popola(cosa: str, quante: str, come: str) -> str:
    """Come lo Studio chiama un Popola: «Popola · persone, poche, ferme»."""
    voce = COSE_POPOLA[cosa]
    pezzi = [voce.nome.lower(), QUANTE_POPOLA[quante].lower()]
    if voce.modi and come:
        pezzi.append(COME_POPOLA[come].lower())
    return f"Popola · {', '.join(pezzi)}"


def _nomi_richieste() -> dict[str, str]:
    nomi = {v.testo: f"Cambia · {v.nome}" for v in VARIAZIONI.values()}
    for voce in COSE_POPOLA.values():
        for scena in voce.scene:
            for quante in voce.soggetti:
                for come in (voce.modi or {"": ""}):
                    nome = nome_popola(voce.identificativo, quante, come)
                    nomi[nota_popola(voce.identificativo, quante, come, scena)] = nome
                    nomi[richiesta_popola(voce.identificativo, quante, come, scena)] = nome
    for stanza in STANZE_ARREDA:
        for stile in STILI_ARREDA:
            nomi[nota_arreda(stanza, stile)] = nome_arreda(stanza, stile)
    return nomi


_NOMI_RICHIESTE = _nomi_richieste()


def nome_richiesta(testo: object) -> str | None:
    """Il nome in italiano di una richiesta scritta da una miniatura o da Popola, None se scritta a mano."""
    return _NOMI_RICHIESTE.get(" ".join(str(testo or "").split()).rstrip("."))
