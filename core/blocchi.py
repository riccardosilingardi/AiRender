"""I blocchi di stile e i preset che li combinano.

Da dove vengono i testi: `docs/ui/blocchi-stile-bozza.md`, bozza 3 del
2026-10-27. Sono **riscritti** dalla prompt library di Riccardo (Notion,
ispirata a Visoid), non copiati: un blocco tocca un asse solo, cosi' cambiarne
uno non disfa gli altri. Testo per il modello in inglese, nomi per l'utente in
italiano.

**Nessun blocco e' stato provato con il modello.** Ogni blocco porta
l'origine SCELTA di core/config.py, e chi lo mostra a schermo lo deve dire.
Quando un blocco sara' confrontato su viste vere, la sua origine cambia qui,
blocco per blocco.

L'ordine nel prompt e' fisso (PRD, sezione 5, riga del 2026-10-27):
regola fissa -> scena -> materiali -> look -> luce -> cielo (esterni) oppure
fuori dalle finestre + arredo (interni) -> intorno -> persone -> qualita' ->
cosa evitare.

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
VERSIONE = "bozza-3"

ESTERNO = "esterno"
INTERNO = "interno"
SCENE = (ESTERNO, INTERNO)


class SceltaNonValida(ErroreAirender):
    """Una scelta di stile che non esiste, o che non vale per quella scena."""


@dataclass(frozen=True)
class Blocco:
    """Un pezzo di prompt: un asse solo, un nome per l'utente, un testo per il modello."""

    identificativo: str
    nome: str
    testo: str
    origine: str = config.SCELTA

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome del blocco {self.identificativo}")


def _blocchi(*righe: tuple[str, str, str]) -> dict[str, Blocco]:
    return {r[0]: Blocco(*r) for r in righe}


REGOLA_FISSA = Blocco(
    "regola",
    "Regola fissa",
    "Edit this exact image. Keep the camera, framing, proportions and every "
    "building element exactly as they are; do not add, remove or reshape any "
    "architecture. Change only the look described below.",
)

COSA_EVITARE = Blocco(
    "evitare",
    "Cosa evitare",
    "Avoid: CGI or plastic look, HDR, oversharpening, clipped highlights, "
    "crushed blacks, heavy grain, artificial detail.",
)

SCENA = _blocchi(
    (ESTERNO, "Esterno", "The subject is a building exterior."),
    (INTERNO, "Interno", "The subject is an interior space."),
)

LOOK = _blocchi(
    ("canon", "Canon tilt-shift · rivista",
     "Professional architectural photograph, Canon EOS R5 with 17mm tilt-shift "
     "lens: perfectly straight verticals, deep focus, crisp micro-contrast, "
     "clean polarized colour."),
    ("gfx", "Fujifilm GFX100S · caldo naturale",
     "Fujifilm GFX100S photograph: warm natural colour, earthy muted tones, "
     "softly luminous highlights, deep but detailed shadows, gentle contrast, "
     "olive greens, pale blues."),
    ("leica", "Leica SL2 · neutro profondo",
     "Leica SL2 full-frame photograph: rich tonal depth, refined "
     "micro-contrast, restrained warm colour, smooth highlight roll-off, "
     "detailed shadows, tactile textures."),
    ("portra160", "Kodak Portra 160 · morbido",
     "Kodak Portra 160 film colour: soft and restrained, slightly warm "
     "neutrals, cream highlights, muted greens, moderate elegant contrast, "
     "fine grain, gentle pastel midtones."),
    ("portra400", "Kodak Portra 400 · caldo vissuto",
     "Kodak Portra 400 film colour: warm, soft and lived-in, slightly warm "
     "whites, muted organic greens, open shadows, creamy rolled-off "
     "highlights, fine visible grain."),
    ("ektar", "Kodak Ektar 100 · colori vividi",
     "Kodak Ektar 100 film colour: bold, clean, saturated, strong "
     "well-separated contrast, bright clean highlights, deep but open "
     "shadows, ultra-fine grain, sharp edges."),
    ("metropolis", "LomoChrome Metropolis · urbano",
     "LomoChrome Metropolis film colour: desaturated and slightly cool, muted "
     "cyan skies, subdued greens, vivid red and orange accents, punchy "
     "contrast, dense blacks, visible grain."),
    ("x100v", "Fujifilm X100V · analogico 35mm",
     "Fujifilm X100V with Classic Negative: warm muted colour, olive greens, "
     "cream highlights, lifted blacks with teal shadows, moderate contrast, "
     "fine grain, light vignette."),
    ("mavic", "DJI Mavic · drone (solo viste dall'alto)",
     "Aerial photo look of a DJI Mavic 3 Pro Hasselblad camera: deep focus to "
     "the horizon, natural muted colour, slightly cool shadows, soft distant "
     "haze, wide dynamic range."),
)

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

INTORNO = _blocchi(
    ("niente", "Niente, sfondo neutro",
     "Plain neutral background; do not add trees, cars or surroundings that "
     "are not in the view."),
)

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

FUORI = _blocchi(
    ("neutra", "Fuori dalle finestre: neutro",
     "Keep the view outside the windows soft and neutral; do not invent a "
     "landscape."),
    ("verde", "Fuori: verde", "A soft out-of-focus green garden outside the windows."),
    ("citta", "Fuori: città", "A soft out-of-focus city view outside the windows."),
)

ARREDO = _blocchi(
    ("nessuno", "Non aggiungere arredi",
     "Do not add furniture or objects that are not in the view."),
    ("leggero", "Qualche oggetto",
     "Add only a few small objects (books, a plant, a throw) without changing "
     "the furniture."),
)

PERSONE = _blocchi(
    ("nessuna", "Nessuna", "No people."),
    ("movimento", "In movimento",
     "A few people walking, slightly motion-blurred, for scale."),
)

QUALITA = _blocchi(
    ("base", "Base", "Professional architectural photography, natural detail."),
    ("32k", "Altissima definizione (da provare)",
     "Professional architectural photography, 32k, ultra-detailed, archi "
     "magazine quality."),
)

# Asse -> (blocchi possibili, scene in cui vale). Un asse fuori dalla sua
# scena si rifiuta: il cielo di un interno non esiste.
ASSI = {
    "look": (LOOK, SCENE),
    "luce": (None, SCENE),  # dipende dalla scena: vedi _blocchi_luce
    "cielo": (CIELO, (ESTERNO,)),
    "fuori": (FUORI, (INTERNO,)),
    "arredo": (ARREDO, (INTERNO,)),
    "intorno": (INTORNO, (ESTERNO,)),
    "persone": (PERSONE, SCENE),
    "qualita": (QUALITA, SCENE),
}

QUALITA_PREDEFINITA = "base"


def _blocchi_luce(scena: str) -> dict[str, Blocco]:
    return LUCE_ESTERNI if scena == ESTERNO else LUCE_INTERNI


@dataclass(frozen=True)
class Scelte:
    """Le scelte di stile di un lavoro. Un campo vuoto vuol dire: quel blocco non parte."""

    scena: str = ESTERNO
    materiali: str = ""
    look: str | None = None
    luce: str | None = None
    cielo: str | None = None
    fuori: str | None = None
    arredo: str | None = None
    intorno: str | None = None
    persone: str | None = None
    qualita: str = QUALITA_PREDEFINITA

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
        persone=persone,
    ))


def _interno(identificativo, nome, look, luce, fuori, persone) -> PresetStile:
    return PresetStile(identificativo, nome, Scelte(
        scena=INTERNO, look=look, luce=luce, fuori=fuori, arredo="nessuno",
        persone=persone,
    ))


# Le combinazioni della bozza 3. Intorno ("niente") e arredo ("nessuno") non
# sono nelle colonne delle tabelle, ma ci sono nelle lunghezze che la bozza
# ha misurato: solo con loro i conti tornano al carattere. Lo controlla un test.
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
    elenco = elenco if elenco is not None else _blocchi_luce(scena)
    try:
        return elenco[valore]
    except KeyError:
        raise SceltaNonValida(
            f"Per \"{asse}\" non esiste la scelta \"{valore}\" in una vista {scena}.",
            f"Le scelte possibili sono: {', '.join(elenco)}.",
        ) from None


def blocchi_scelti(scelte: Scelte) -> list[Blocco]:
    """I blocchi che partono, nell'ordine fisso. I materiali non sono un blocco: sono parole dell'utente."""
    if scelte.scena not in SCENE:
        raise SceltaNonValida(
            f"La scena \"{scelte.scena}\" non esiste.",
            "Scegli esterno o interno.",
        )
    ordine = ["look", "luce"]
    ordine += ["cielo"] if scelte.scena == ESTERNO else ["fuori", "arredo"]
    ordine += ["intorno", "persone", "qualita"]
    # Un asse dell'altra scena, se compilato, si rifiuta invece di sparire
    # in silenzio: l'utente crederebbe di averlo mandato.
    for asse in ("cielo", "fuori", "arredo", "intorno"):
        if asse not in ordine and getattr(scelte, asse):
            _blocco(asse, getattr(scelte, asse), scelte.scena)
    blocchi = [REGOLA_FISSA, SCENA[scelte.scena]]
    for asse in ordine:
        valore = getattr(scelte, asse)
        if valore:
            blocchi.append(_blocco(asse, valore, scelte.scena))
    blocchi.append(COSA_EVITARE)
    return blocchi


def frase_materiali(materiali: str) -> str:
    testo = " ".join((materiali or "").split()).rstrip(".")
    return f"Materials: {testo}." if testo else ""


def componi(scelte: Scelte) -> str:
    """Il prompt che parte al modello, in inglese, nell'ordine fisso."""
    blocchi = blocchi_scelti(scelte)
    pezzi = [b.testo for b in blocchi[:2]]  # regola fissa, scena
    materiali = frase_materiali(scelte.materiali)
    if materiali:
        pezzi.append(materiali)
    pezzi += [b.testo for b in blocchi[2:]]
    return " ".join(pezzi)
