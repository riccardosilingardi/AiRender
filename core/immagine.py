"""Tutto cio' che apre un'immagine.

E' l'unico modulo del motore che importa Pillow. Se un giorno Pillow non e'
installabile nell'interprete Python di Allplan, si riscrive questo file e
basta: il resto del motore parla solo di byte e di numeri.
"""

from __future__ import annotations

import io
import math
import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config
from .errori import FileNonTrovato


@dataclass(frozen=True)
class Statistiche:
    """Cosa sappiamo di un'immagine senza chiedere niente all'utente."""

    larghezza: int
    altezza: int
    quota_sfondo: float
    toni_distinti: int
    deviazione_luminanza: float

    @property
    def lato_lungo(self) -> int:
        return max(self.larghezza, self.altezza)


def leggi(percorso: str | os.PathLike) -> bytes:
    """I byte del file, o un errore che dice dove ha guardato."""
    try:
        with open(percorso, "rb") as file:
            return file.read()
    except FileNotFoundError:
        raise FileNonTrovato(
            f"Non ho trovato nessun file in {percorso}.",
            "Controlla il percorso. In Allplan la vista si salva con "
            "\"Salva contenuto finestra come immagine\".",
        ) from None
    except OSError as errore:
        raise FileNonTrovato(
            f"Non sono riuscito a leggere {percorso}: {errore.strerror}.",
            "Controlla i permessi del file, o copialo in un'altra cartella.",
        ) from None


def _apri(dati: bytes) -> Image.Image:
    try:
        immagine = Image.open(io.BytesIO(dati))
        immagine.load()
        return immagine
    except Exception:
        raise FileNonTrovato(
            "Il file c'e' ma non e' un'immagine che so leggere.",
            "Salva la vista in PNG o JPEG dalla funzione di esportazione di Allplan.",
        ) from None


def misura(dati: bytes) -> Statistiche:
    """Le tre misure su cui si decide se la vista e' utilizzabile.

    Si misura su una copia rimpicciolita, e il rimpicciolimento e' a pixel
    vicino: interpolare inventerebbe toni intermedi e farebbe sembrare un
    wireframe una vista shaded.
    """
    immagine = _apri(dati)
    larghezza, altezza = immagine.size

    grigi = immagine.convert("L")
    lato = config.LATO_ANALISI_PX
    if max(grigi.size) > lato:
        scala_analisi = lato / max(grigi.size)
        nuova = (
            max(1, int(grigi.width * scala_analisi)),
            max(1, int(grigi.height * scala_analisi)),
        )
        grigi = grigi.resize(nuova, Image.Resampling.NEAREST)

    istogramma = grigi.histogram()
    totale = sum(istogramma)
    if totale == 0:  # numero-non-configurabile: immagine senza pixel
        return Statistiche(larghezza, altezza, 1.0, 0, 0.0)

    picco = istogramma.index(max(istogramma))
    tolleranza = config.TOLLERANZA_SFONDO
    intorno = sum(
        istogramma[livello]
        for livello in range(max(0, picco - tolleranza), min(len(istogramma), picco + tolleranza + 1))
    )

    media = sum(livello * conteggio for livello, conteggio in enumerate(istogramma)) / totale
    varianza = sum(
        conteggio * (livello - media) ** 2 for livello, conteggio in enumerate(istogramma)
    ) / totale

    return Statistiche(
        larghezza=larghezza,
        altezza=altezza,
        quota_sfondo=intorno / totale,
        toni_distinti=sum(1 for conteggio in istogramma if conteggio > 0),
        deviazione_luminanza=math.sqrt(varianza),
    )


def quota_colorata(dati: bytes) -> float:
    """La parte della vista con colori pieni, da 0 a 1.

    Serve all'avviso dei colori letti come materiali: Allplan colora le
    superfici per layer, e il modello le rende di quel colore. Si misura su
    una copia rimpicciolita, come le altre misure.
    """
    immagine = _apri(dati).convert("RGB")
    lato = config.LATO_ANALISI_PX
    if max(immagine.size) > lato:
        rapporto = lato / max(immagine.size)
        immagine = immagine.resize(
            (max(1, int(immagine.width * rapporto)), max(1, int(immagine.height * rapporto))),
            Image.Resampling.NEAREST,
        )
    saturazioni = immagine.convert("HSV").getchannel("S").histogram()
    totale = sum(saturazioni)
    if totale == 0:  # numero-non-configurabile: immagine senza pixel
        return 0.0
    return sum(saturazioni[config.SATURAZIONE_COLORE_MINIMA:]) / totale


def dimensione_mb(dati: bytes) -> float:
    """Peso in megabyte, per confrontarlo col limite del servizio."""
    return len(dati) / (1024 * 1024)  # numero-non-configurabile: definizione di megabyte


def sfuma_maschera(dati: bytes, raggio_px: int | None = None) -> bytes:
    """Sfuma il bordo della maschera prima di spedirla.

    Un bordo netto lascia una cucitura visibile fra la regione modificata e il
    resto dell'immagine.
    """
    raggio = config.MASCHERA_SFUMATURA_PX if raggio_px is None else raggio_px
    maschera = _apri(dati).convert("L")
    if raggio > 0:
        maschera = maschera.filter(ImageFilter.GaussianBlur(radius=raggio))
    uscita = io.BytesIO()
    maschera.save(uscita, format="PNG")
    return uscita.getvalue()


def dimensioni(dati: bytes) -> tuple[int, int]:
    """Larghezza e altezza, senza calcolare le statistiche."""
    immagine = _apri(dati)
    return immagine.size


def affianca(pannelli: list[tuple[str, bytes]]) -> bytes:
    """Le immagini una accanto all'altra, alla stessa altezza della prima, col nome sopra.

    Ogni immagine si ridimensiona tenendo le sue proporzioni: deformarla per
    farla combaciare nasconderebbe proprio l'edificio schiacciato che il
    confronto deve far vedere. La didascalia sta in una striscia sopra e non
    copre niente.
    """
    aperte = [(nome, _apri(dati).convert("RGB")) for nome, dati in pannelli]
    altezza = aperte[0][1].height
    ridotte = [
        (nome, im.resize((max(1, round(im.width * altezza / im.height)), altezza),
                         Image.Resampling.LANCZOS))
        for nome, im in aperte
    ]
    striscia = config.CONFRONTO_DIDASCALIA_PX
    fessura = 2  # px bianchi fra due pannelli, solo per separarli
    larghezza = sum(im.width for _, im in ridotte) + fessura * (len(ridotte) - 1)
    tela = Image.new("RGB", (larghezza, altezza + striscia), "white")
    disegno = ImageDraw.Draw(tela)
    try:
        carattere = ImageFont.load_default(size=striscia // 2)
    except TypeError:  # Pillow prima della 10.1: solo il carattere bitmap piccolo
        carattere = ImageFont.load_default()
    x = 0
    for nome, im in ridotte:
        tela.paste(im, (x, striscia))
        sinistra, alto, destra, basso = disegno.textbbox((0, 0), nome, font=carattere)
        disegno.text(
            (x + (im.width - (destra - sinistra)) // 2, (striscia - (basso - alto)) // 2),
            nome, fill="black", font=carattere,
        )
        x += im.width + fessura
    uscita = io.BytesIO()
    tela.save(uscita, format="PNG")
    return uscita.getvalue()
