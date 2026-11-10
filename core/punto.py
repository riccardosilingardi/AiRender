"""Il punto di vista dalla pianta: dove sta la camera e verso dove guarda.

Flusso 7 di Riccardo (2026-11-08): su una pianta si clicca dove si sta e si
trascina verso dove si guarda; il modello rende la foto che quella camera
farebbe. Senza Allplan la stanza e' immaginata dal modello (altezze, arredi
non disegnati), e lo Studio lo scrive sull'immagine. Con Allplan la camera
vera aspetta la sonda di PythonParts (core/config.py, PUNTO_DI_VISTA_ALLPLAN).

Il modello riceve due immagini: la pianta com'e', e la stessa pianta con un
punto e un cono rossi. Li disegna questo modulo, qui e non nel browser, cosi'
la ricetta li puo' rifare uguali e un test li puo' controllare.

Le coordinate sono frazioni della pianta, da 0 a 1, con l'origine in alto a
sinistra: non dipendono dalla misura in pixel ne' dello schermo.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

from . import blocchi, config
from .errori import ErroreAirender


class PuntoNonValido(ErroreAirender):
    """Un punto di vista che non si puo' disegnare o non dice dove guarda."""


@dataclass(frozen=True)
class PuntoDiVista:
    """Dove sta la camera (x, y), un punto verso cui guarda (verso_x, verso_y), e come rendere."""

    x: float
    y: float
    verso_x: float
    verso_y: float
    tipo: str = blocchi.TIPO_PREDEFINITO
    stile: str = "giorno"

    def a_dizionario(self) -> dict:
        return {"x": self.x, "y": self.y, "verso_x": self.verso_x, "verso_y": self.verso_y,
                "tipo": self.tipo, "stile": self.stile}

    @property
    def scena(self) -> str:
        """La scena dell'immagine che esce: un interno da una pianta, un esterno da una planimetria."""
        return blocchi.scena_punto(self.tipo)

    def prompt(self, materiali: str = "") -> str:
        return blocchi.componi_punto_di_vista(self.tipo, self.stile, materiali)

    def direzione_gradi(self) -> float:
        """Verso dove guarda, in gradi: 0 a destra, 90 in basso (come l'immagine)."""
        return math.degrees(math.atan2(self.verso_y - self.y, self.verso_x - self.x)) % 360  # numero-non-configurabile: un giro


def _frazione(valore: object, nome: str) -> float:
    if isinstance(valore, bool) or not isinstance(valore, (int, float)) or not math.isfinite(valore) \
            or not 0 <= valore <= 1:
        raise PuntoNonValido(
            f"Il punto di vista ha {nome} = {valore!r}: serve un numero fra 0 e 1, una frazione della pianta.",
            "Clicca di nuovo dove stai sulla pianta, poi trascina verso dove guardi.",
        )
    return float(valore)


def da_dizionario(dati: object) -> PuntoDiVista:
    """Il punto di vista arrivato dallo Studio o letto dal file del lavoro, controllato."""
    if not isinstance(dati, dict):
        raise PuntoNonValido(
            "Il punto di vista non e' arrivato.",
            "Clicca sulla pianta dove stai, poi trascina verso dove guardi.",
        )
    x, y = _frazione(dati.get("x"), "x"), _frazione(dati.get("y"), "y")
    vx, vy = _frazione(dati.get("verso_x"), "verso_x"), _frazione(dati.get("verso_y"), "verso_y")
    if math.hypot(vx - x, vy - y) < config.PUNTO_DI_VISTA_TRASCINA_MINIMO:
        raise PuntoNonValido(
            "Il punto di vista non dice verso dove guardi: il trascinamento e' troppo corto.",
            "Clicca dove stai e trascina un po' piu' in la', verso dove guardi.",
        )
    tipo = dati.get("tipo") or blocchi.TIPO_PREDEFINITO
    if tipo not in blocchi.TIPI_PIANTA:
        raise PuntoNonValido(
            f"\"{tipo}\" non e' un tipo di pianta.",
            "Scegli pianta dell'edificio, planimetria o planivolumetrico.",
        )
    stile = dati.get("stile") or "giorno"
    punto = PuntoDiVista(x, y, vx, vy, str(tipo), str(stile))
    punto.prompt()  # uno stile che non esiste si ferma qui, con la sua ragione
    return punto


def disegna(pianta: bytes, punto: PuntoDiVista) -> bytes:
    """La pianta con il punto e il cono rossi, in PNG: la seconda immagine dell'invio."""
    from PIL import Image, ImageDraw

    try:
        immagine = Image.open(io.BytesIO(pianta)).convert("RGB")
    except Exception as errore:  # Pillow solleva tipi diversi per file diversi
        raise PuntoNonValido(
            f"La pianta non si legge come immagine ({errore}).",
            "Rifai il punto di vista da una pianta resa o da una vista caricata.",
        ) from None
    larghezza, altezza = immagine.size
    lato = max(larghezza, altezza)
    cx, cy = punto.x * larghezza, punto.y * altezza
    angolo = math.radians(punto.direzione_gradi())
    mezza = math.radians(config.PUNTO_DI_VISTA_APERTURA_GRADI / 2)
    lunghezza = lato * config.PUNTO_DI_VISTA_CONO_LATO
    vertici = [(cx, cy)] + [
        (cx + lunghezza * math.cos(angolo + a), cy + lunghezza * math.sin(angolo + a))
        for a in (-mezza, mezza)
    ]
    sopra = Image.new("RGBA", immagine.size, (0, 0, 0, 0))
    disegno = ImageDraw.Draw(sopra)
    rosso = config.PUNTO_DI_VISTA_ROSSO
    pieno, bianco = 255, (255, 255, 255, 255)  # numero-non-configurabile: opaco, e il bianco del bordo
    disegno.polygon(vertici, fill=(*rosso, config.PUNTO_DI_VISTA_CONO_OPACITA), outline=(*rosso, pieno))
    raggio = max(4.0, lato * config.PUNTO_DI_VISTA_RAGGIO)  # numero-non-configurabile: 4 px, sotto non si vede
    bordo = max(1, round(raggio / 3))  # numero-non-configurabile: bordo bianco un terzo del raggio
    disegno.ellipse((cx - raggio, cy - raggio, cx + raggio, cy + raggio),
                    fill=(*rosso, pieno), outline=bianco, width=bordo)
    finale = Image.alpha_composite(immagine.convert("RGBA"), sopra).convert("RGB")
    uscita = io.BytesIO()
    finale.save(uscita, format="PNG")
    return uscita.getvalue()
