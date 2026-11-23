"""La velina del Fotoinserimento: dove vanno gli edifici e lo schizzo sopra la foto.

Richiesta di Riccardo del 2026-11-20, rifatta il 2026-11-23 dopo la sua prima
prova («UX pessima»):

- ogni edificio (A, B, ...) e' una vista di Allplan e ha un **perimetro**:
  l'impronta alla base disegnata sulla foto, vertice per vertice, sia su una
  foto zenitale sia su una aerea o da terra. Sostituisce il rettangolo, il
  «posto» e i 4 punti dell'aggancio;
- la **velina** e' facoltativa: una carta da forno che sbiadisce la foto, su
  cui si schizza a mano libera in rosso (cosa cambiare o togliere), verde
  (alberi e verde nuovi) e nero (profili).

Cosa parte, nell'ordine: (1) la foto pulita con il perimetro magenta di ogni
edificio e la sua lettera, come il contorno numerato che ha funzionato ad
Arceto; (2) la stessa foto sotto la velina con lo schizzo, solo se c'e' uno
schizzo; (3...) una vista per edificio.

Le coordinate sono frazioni dell'immagine, da 0 a 1, con l'origine in alto a
sinistra. Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from . import aree as modulo_aree, config, immagine as modulo_immagine
from .errori import ErroreAirender

Punto = tuple[float, float]

CAMBIA = "cambia"
VERDE = "verde"
PROFILO = "profilo"
COLORI = (CAMBIA, VERDE, PROFILO)
# I colori dello schizzo, uguali nello Studio (studio.js li legge dal
# catalogo): il prompt li nomina, quindi devono restare rosso, verde e nero.
RGB = {CAMBIA: (214, 50, 43), VERDE: (47, 138, 58), PROFILO: (20, 20, 20)}  # numero-non-configurabile: i colori che il prompt nomina (rosso, verde, nero)
# Come l'interfaccia chiama ogni colore, sempre con le stesse parole.
NOMI_COLORI = {CAMBIA: "Cambia o togli", VERDE: "Alberi e verde", PROFILO: "Profili"}
# Il colore della carta da forno.
CARTA = (247, 244, 236)  # numero-non-configurabile: il colore della carta da forno, solo aspetto
LETTERE = "ABCD"
PERIMETRO_MINIMO = 3  # numero-non-configurabile: un perimetro ha almeno tre vertici


class VelinaNonValida(ErroreAirender):
    """Una velina che non si puo' mandare: tratti, edifici o perimetri che non tornano."""


def _punto(p: object, che_cosa: str) -> Punto:
    try:
        x, y = (float(c) for c in p)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        raise VelinaNonValida(f"{che_cosa}: un vertice non e' [x, y].", "Ridisegna il perimetro.") from None
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise VelinaNonValida(f"{che_cosa}: un vertice sta fuori dalla foto.", "Ridisegna il perimetro.")
    return (x, y)


def _area(punti: tuple[Punto, ...]) -> float:
    """L'area del poligono (formula del laccio), in frazione della foto."""
    n = len(punti)
    return abs(sum(punti[i][0] * punti[(i + 1) % n][1] - punti[(i + 1) % n][0] * punti[i][1]
                   for i in range(n))) / 2


def _perimetro(voce: object, lettera: str) -> tuple[Punto, ...] | None:
    if voce in (None, [], ()):
        return None
    che_cosa = f"Il perimetro dell'edificio {lettera}"
    if not isinstance(voce, (list, tuple)) or len(voce) < PERIMETRO_MINIMO:
        raise VelinaNonValida(f"{che_cosa} ha meno di {PERIMETRO_MINIMO} vertici.",
                              "Clicca almeno tre angoli alla base dell'edificio, poi doppio clic per chiudere.")
    punti = tuple(_punto(p, che_cosa) for p in voce)
    if _area(punti) < config.PERIMETRO_AREA_MINIMA:
        raise VelinaNonValida(f"{che_cosa} e' troppo piccolo o e' una linea.",
                              "Ridisegnalo sugli angoli alla base dell'edificio.")
    return punti


@dataclass(frozen=True)
class Tratto:
    """Un tratto di matita sulla velina: il colore e la pennellata (come nel Ritocca)."""

    colore: str
    operazione: modulo_aree.Operazione

    def __post_init__(self) -> None:
        if self.colore not in COLORI:
            raise VelinaNonValida(f"Lo schizzo ha un colore che non conosco: \"{self.colore}\".",
                                  "Usa le matite della velina: rosso, verde o nero.")

    def a_dizionario(self) -> dict:
        return {"colore": self.colore, **self.operazione.a_dizionario()}


@dataclass(frozen=True)
class Oggetto:
    """Un edificio da inserire. `vista` vuota = la vista del lavoro; le altre sono file della cartella delle viste."""

    vista: str = ""
    perimetro: tuple[Punto, ...] | None = None

    def a_dizionario(self) -> dict:
        voce: dict = {"vista": self.vista}
        if self.perimetro:
            voce["perimetro"] = [list(p) for p in self.perimetro]
        return voce

    @classmethod
    def da_dizionario(cls, dati: object, lettera: str = "A") -> "Oggetto":
        if not isinstance(dati, dict):
            raise VelinaNonValida("Un edificio da inserire non e' un oggetto.", "Ricarica lo Studio.")
        return cls(vista=str(dati.get("vista") or ""), perimetro=_perimetro(dati.get("perimetro"), lettera))


@dataclass(frozen=True)
class Velina:
    """Lo schizzo sulla carta da forno e gli edifici da inserire (il primo e' la vista del lavoro)."""

    tratti: tuple[Tratto, ...] = ()
    opacita: float = config.VELINA_OPACITA
    oggetti: tuple[Oggetto, ...] = field(default_factory=lambda: (Oggetto(),))

    def __post_init__(self) -> None:
        if isinstance(self.opacita, bool) or not isinstance(self.opacita, (int, float)) \
                or not 0 <= self.opacita <= config.VELINA_OPACITA_MASSIMA:
            raise VelinaNonValida(
                f"La velina ha un'opacita' che non torna: {self.opacita!r}.",
                f"Va da 0 a {config.VELINA_OPACITA_MASSIMA}: rimettila col cursore.",
            )
        if not self.oggetti or len(self.oggetti) > config.CONTESTO_OGGETTI_MASSIMO:
            raise VelinaNonValida(
                f"Gli edifici da inserire sono {len(self.oggetti)}: ne partono da 1 a {config.CONTESTO_OGGETTI_MASSIMO}.",
                "Togline qualcuno.",
            )
        if self.oggetti[0].vista:
            raise VelinaNonValida("Il primo edificio dev'essere la vista scelta.", "Ricarica lo Studio.")
        if any(not o.vista for o in self.oggetti[1:]):
            raise VelinaNonValida("Un edificio in piu' non dice da che vista viene.", "Scegli di nuovo la vista.")
        if len(self.oggetti) > 1:
            senza = [LETTERE[i] for i, o in enumerate(self.oggetti) if not o.perimetro]
            if senza:
                raise VelinaNonValida(
                    "Non so dove va l'edificio " + ", ".join(senza) + ": manca il suo perimetro.",
                    "Disegna il perimetro alla base di ogni edificio, oppure togli quello che non serve.",
                )
        punti = sum(len(t.operazione.punti) for t in self.tratti)
        if punti > config.PITTURA_PUNTI_MASSIMI:
            raise VelinaNonValida(
                f"Lo schizzo ha {punti} punti: ne entrano al massimo {config.PITTURA_PUNTI_MASSIMI}.",
                "Cancella qualche tratto con Annulla o con la gomma.",
            )

    # --- cosa dice ---------------------------------------------------------

    @property
    def ha_schizzo(self) -> bool:
        return any(not t.operazione.gomma for t in self.tratti)

    @property
    def lettere(self) -> tuple[str, ...]:
        return tuple(LETTERE[i] for i in range(len(self.oggetti)))

    @property
    def ha_perimetri(self) -> bool:
        return any(o.perimetro for o in self.oggetti)

    @property
    def parte_la_velina(self) -> bool:
        """La seconda immagine parte solo se c'e' qualcosa da leggere sopra: lo schizzo."""
        return self.ha_schizzo

    @property
    def dice_dove(self) -> bool:
        """I perimetri dicono dove vanno gli edifici: allora il rettangolo non serve."""
        return all(o.perimetro for o in self.oggetti)

    @property
    def colori_usati(self) -> tuple[str, ...]:
        usati = {t.colore for t in self.tratti if not t.operazione.gomma}
        return tuple(c for c in COLORI if c in usati)

    def quante_immagini(self) -> int:
        return 1 + int(self.parte_la_velina) + len(self.oggetti)

    # --- dizionario ----------------------------------------------------------

    def a_dizionario(self) -> dict:
        return {
            "tratti": [t.a_dizionario() for t in self.tratti],
            "opacita": self.opacita,
            "oggetti": [o.a_dizionario() for o in self.oggetti],
        }

    @classmethod
    def da_dizionario(cls, dati: object) -> "Velina":
        if not isinstance(dati, dict):
            raise VelinaNonValida("La velina non e' arrivata per intero.", "Ricarica lo Studio.")
        voci = dati.get("tratti") or []
        if not isinstance(voci, list):
            raise VelinaNonValida("Lo schizzo non e' un elenco di tratti.", "Ridisegna.")
        tratti = []
        for voce in voci:
            if not isinstance(voce, dict):
                raise VelinaNonValida("Un tratto dello schizzo non e' un oggetto.", "Ridisegna.")
            try:
                operazione = modulo_aree.Operazione.da_dizionario({k: v for k, v in voce.items() if k != "colore"})
            except modulo_aree.AreaNonValida as errore:
                raise VelinaNonValida(f"Lo schizzo: {errore.fatto}", errore.cosa_fare) from None
            tratti.append(Tratto(str(voce.get("colore") or ""), operazione))
        oggetti = dati.get("oggetti") or [{}]
        if not isinstance(oggetti, list) or len(oggetti) > len(LETTERE):
            raise VelinaNonValida("Gli edifici da inserire non sono un elenco valido.", "Ricarica lo Studio.")
        opacita = dati.get("opacita", config.VELINA_OPACITA)
        return cls(tratti=tuple(tratti), opacita=opacita,
                   oggetti=tuple(Oggetto.da_dizionario(o, LETTERE[i]) for i, o in enumerate(oggetti)))

    def con_viste(self, viste: tuple[str, ...]) -> "Velina":
        """La stessa velina con i file delle viste in piu' al posto dei nomi (il primo resta vuoto)."""
        oggetti = (self.oggetti[0],) + tuple(
            Oggetto(v, o.perimetro) for o, v in zip(self.oggetti[1:], viste))
        return Velina(self.tratti, self.opacita, oggetti)


# --- disegno ---------------------------------------------------------------


def _apri(dati: bytes) -> Image.Image:
    with Image.open(io.BytesIO(dati)) as aperta:
        return aperta.convert("RGB")


def _png(immagine: Image.Image) -> bytes:
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


def perimetri(luogo: bytes, velina: Velina) -> bytes:
    """La foto pulita con il perimetro magenta di ogni edificio e la sua lettera: la prima immagine che parte."""
    if not velina.ha_perimetri:
        return luogo
    larghezza, altezza = modulo_immagine.dimensioni(luogo)
    poligoni, lettere = [], []
    for lettera, oggetto in zip(velina.lettere, velina.oggetti):
        if oggetto.perimetro:
            poligoni.append([(x * larghezza, y * altezza) for x, y in oggetto.perimetro])
            lettere.append(lettera)
    return modulo_immagine.disegna_aree(luogo, poligoni, lettere)


def disegna(luogo: bytes, velina: Velina) -> bytes:
    """La foto sotto la carta da forno con lo schizzo: la seconda immagine che parte.

    I tratti si dipingono in ordine su uno strato trasparente: la gomma toglie
    quello che c'era sotto, come nel Ritocca.
    """
    foto = _apri(luogo)
    carta = Image.new("RGB", foto.size, CARTA)
    sotto = Image.blend(foto, carta, velina.opacita)
    strato = Image.new("RGBA", foto.size, (0, 0, 0, 0))
    disegno = ImageDraw.Draw(strato)
    larghezza, altezza = foto.size
    for tratto in velina.tratti:
        pezzo = tratto.operazione.in_pixel(larghezza, altezza)
        modulo_immagine._dipingi(disegno, pezzo, (*RGB[tratto.colore], 255), (0, 0, 0, 0))  # numero-non-configurabile: alfa pieno
    sotto = sotto.convert("RGBA")
    sotto.alpha_composite(strato)
    return _png(sotto.convert("RGB"))
