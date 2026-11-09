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

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageFont

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


def riduci_lato(dati: bytes, lato_massimo: int) -> bytes:
    """L'immagine col lato lungo al massimo `lato_massimo`, piu' leggera da spedire.

    Una foto diventa JPEG; un'immagine a pochi colori o con trasparenza (una
    mappa dei materiali, una maschera) resta PNG e si rimpicciolisce senza
    mescolare i colori, che per il modello sono informazione.
    """
    immagine = _apri(dati)
    larghezza, altezza = immagine.size
    fattore = min(1.0, lato_massimo / max(larghezza, altezza))
    nuova = (max(1, round(larghezza * fattore)), max(1, round(altezza * fattore)))
    pochi_colori = immagine.getcolors(256) is not None  # numero-non-configurabile: tavolozza PNG
    trasparente = "A" in immagine.getbands() or "transparency" in immagine.info
    uscita = io.BytesIO()
    if pochi_colori or trasparente:
        immagine.resize(nuova, Image.Resampling.NEAREST).save(uscita, format="PNG", optimize=True)
    else:
        immagine.convert("RGB").resize(nuova, Image.Resampling.LANCZOS).save(
            uscita, format="JPEG", quality=88)  # numero-non-configurabile: qualita' JPEG senza artefatti visibili
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


# --- cornice: la vista al rapporto che il modello accetta ----------------------


@dataclass(frozen=True)
class Cornice:
    """Quanto si e' aggiunto attorno alla vista, in frazioni dell'immagine allargata.

    In frazioni e non in pixel perche' il modello rimanda un'immagine di
    un'altra grandezza, con lo stesso rapporto: si taglia in proporzione.
    """

    larghezza: int  # della vista di partenza, in px
    altezza: int
    sinistra: float
    alto: float
    destra: float
    basso: float

    def come_dizionario(self) -> dict:
        cifre = 5  # numero-non-configurabile: solo per rendere leggibile la ricetta
        return {
            "vista_px": [self.larghezza, self.altezza],
            "sinistra": round(self.sinistra, cifre), "alto": round(self.alto, cifre),
            "destra": round(self.destra, cifre), "basso": round(self.basso, cifre),
        }


def allarga_a_rapporto(dati: bytes, rapporto: float) -> tuple[bytes, Cornice]:
    """La vista allargata fino a `rapporto` (larghezza/altezza), al centro.

    Le bande aggiunte ripetono la riga o la colonna di bordo della vista,
    stirata: il modello vede la scena continuare invece di una fascia di
    colore che potrebbe leggere come un muro. Tanto la cornice si taglia.
    """
    vista = _apri(dati).convert("RGB")
    larghezza, altezza = vista.size
    if larghezza / altezza < rapporto:
        nuova_l, nuova_a = round(altezza * rapporto), altezza
    else:
        nuova_l, nuova_a = larghezza, round(larghezza / rapporto)
    x, y = (nuova_l - larghezza) // 2, (nuova_a - altezza) // 2
    tela = Image.new("RGB", (nuova_l, nuova_a))
    tela.paste(vista, (x, y))
    if x:
        sinistra = vista.crop((0, 0, 1, altezza)).resize((x, altezza))
        destra = vista.crop((larghezza - 1, 0, larghezza, altezza)).resize((nuova_l - larghezza - x, altezza))
        tela.paste(sinistra, (0, y))
        tela.paste(destra, (x + larghezza, y))
    if y:
        alto = tela.crop((0, y, nuova_l, y + 1)).resize((nuova_l, y))
        basso = tela.crop((0, y + altezza - 1, nuova_l, y + altezza)).resize((nuova_l, nuova_a - altezza - y))
        tela.paste(alto, (0, 0))
        tela.paste(basso, (0, y + altezza))
    cornice = Cornice(
        larghezza=larghezza, altezza=altezza,
        sinistra=x / nuova_l, alto=y / nuova_a,
        destra=(nuova_l - larghezza - x) / nuova_l, basso=(nuova_a - altezza - y) / nuova_a,
    )
    return _png(tela), cornice


def togli_cornice(dati: bytes, cornice: Cornice) -> bytes:
    """Il render senza la cornice, al rapporto esatto della vista e alla grandezza del render.

    Non si riporta ai pixel della vista: il 2026-10-31 un render di Nano
    Banana Pro e' tornato a 1279x827 perche' la vista era quella, buttando
    via i pixel che il modello aveva dato (e che a 2k o 4k sono di piu').
    """
    render = _apri(dati).convert("RGB")
    l, a = render.size
    ritaglio = render.crop((
        round(cornice.sinistra * l), round(cornice.alto * a),
        l - round(cornice.destra * l), a - round(cornice.basso * a),
    ))
    altezza = ritaglio.height
    larghezza = round(altezza * cornice.larghezza / cornice.altezza)
    if (larghezza, altezza) == ritaglio.size:
        return _png(ritaglio)
    return _png(ritaglio.resize((larghezza, altezza), Image.Resampling.LANCZOS))


def _scatola_rapporto(larghezza: int, altezza: int, rapporto: float) -> tuple[int, int, int, int]:
    """Il riquadro piu' grande a `rapporto`, al centro della vista."""
    if larghezza / altezza > rapporto:
        nuova = round(altezza * rapporto)
        x = (larghezza - nuova) // 2
        return x, 0, x + nuova, altezza
    nuova = round(larghezza / rapporto)
    y = (altezza - nuova) // 2
    return 0, y, larghezza, y + nuova


def ritaglia_a_rapporto(dati: bytes, rapporto: float) -> bytes:
    """La vista tagliata al centro a `rapporto` (larghezza/altezza), in PNG.

    E' il formato fisso scelto nella palette: si manda solo cio' che resta,
    e quello che si taglia si e' visto prima nell'anteprima.
    """
    vista = _apri(dati).convert("RGB")
    return _png(vista.crop(_scatola_rapporto(*vista.size, rapporto)))


def anteprima_taglio(dati: bytes, rapporto: float) -> bytes:
    """La vista intera con scurito quello che il formato taglierebbe."""
    vista = _apri(dati).convert("RGB")
    scatola = _scatola_rapporto(*vista.size, rapporto)
    scura = Image.blend(vista, Image.new("RGB", vista.size), config.ANTEPRIMA_TAGLIO_SCURO)
    scura.paste(vista.crop(scatola), scatola[:2])
    return _png(scura)


# --- banco di prova: aree, differenze, spigoli, miniature ----------------------

Punto = tuple[float, float]

_PIENO = 255  # numero-non-configurabile: il bianco pieno di un canale a 8 bit
_MAGENTA = (_PIENO, 0, _PIENO)  # il colore dei contorni: raro in una vista di Allplan


def _png(immagine: Image.Image) -> bytes:
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


def _carattere(altezza: int):
    try:
        return ImageFont.load_default(size=altezza)
    except TypeError:  # Pillow prima della 10.1: solo il carattere bitmap piccolo
        return ImageFont.load_default()


def _centro(punti: list[Punto]) -> Punto:
    return sum(x for x, _ in punti) / len(punti), sum(y for _, y in punti) / len(punti)


def disegna_aree(dati: bytes, aree: list[list[Punto]]) -> bytes:
    """L'immagine con il contorno di ogni area e il suo numero (1, 2, ...) in un cerchio.

    Le aree sono poligoni in pixel dell'immagine: un rettangolo ha quattro
    punti, una selezione libera quanti ne ha il lazo. E' il modo (a) del piano
    aree: il modello vede dove intervenire, il testo dice cosa fare.
    """
    tela = _apri(dati).convert("RGB")
    disegno = ImageDraw.Draw(tela)
    spessore = config.CONTORNO_AREE_PX
    raggio = spessore * 3  # numero-non-configurabile: il cerchio del numero segue lo spessore
    carattere = _carattere(raggio)
    for numero, punti in enumerate(aree, start=1):
        disegno.line([*punti, punti[0]], fill=_MAGENTA, width=spessore, joint="curve")
        x, y = punti[0]
        disegno.ellipse((x - raggio, y - raggio, x + raggio, y + raggio), fill=_MAGENTA)
        disegno.text((x, y), str(numero), fill="white", font=carattere, anchor="mm")
    return _png(tela)


def maschera_aree(dimensioni_immagine: tuple[int, int], aree: list[list[Punto]]) -> bytes:
    """La maschera delle aree: nero fuori, bianco dentro, il numero dell'area in nero al centro.

    E' il modo (b) del piano aree, mandata come immagine in piu' dopo la vista.
    """
    maschera = Image.new("RGB", dimensioni_immagine, "black")
    disegno = ImageDraw.Draw(maschera)
    carattere = _carattere(config.CONTORNO_AREE_PX * 4)  # numero-non-configurabile: leggibile dentro l'area
    for numero, punti in enumerate(aree, start=1):
        disegno.polygon(punti, fill="white")
        disegno.text(_centro(punti), str(numero), fill="black", font=carattere, anchor="mm")
    return _png(maschera)


def _dentro_aree(dimensioni_immagine: tuple[int, int], aree: list[list[Punto]], bordo: int) -> Image.Image:
    """Bianco dove stanno le aree, piu' una fascia di `bordo` px intorno."""
    dentro = Image.new("L", dimensioni_immagine, 0)
    disegno = ImageDraw.Draw(dentro)
    for punti in aree:
        disegno.polygon(punti, fill=_PIENO)
        if bordo > 0:
            disegno.line([*punti, punti[0]], fill=_PIENO, width=bordo * 2, joint="curve")
    return dentro


def differenza_fuori_dalle_aree(prima: bytes, dopo: bytes, aree: list[list[Punto]]) -> dict:
    """Quanto e' cambiata l'immagine fuori dalle aree: la domanda del piano aree.

    Restituisce la differenza media (0-255) e la quota di pixel cambiati oltre
    DIFFERENZA_PIXEL_SOGLIA, contando solo i pixel fuori dalle aree e dalla
    fascia di AREE_BORDO_ESCLUSO_PX. Se il risultato ha un'altra dimensione si
    riporta a quella di partenza e lo si dice: allora la misura conta anche
    il ricampionamento.
    """
    base = _apri(prima).convert("RGB")
    nuova = _apri(dopo).convert("RGB")
    ridimensionata = nuova.size != base.size
    if ridimensionata:
        nuova = nuova.resize(base.size, Image.Resampling.LANCZOS)
    dentro = _dentro_aree(base.size, aree, config.AREE_BORDO_ESCLUSO_PX)
    canali = ImageChops.difference(base, nuova).split()
    piu_alto = ImageChops.lighter(ImageChops.lighter(canali[0], canali[1]), canali[2])
    # Quanti pixel fuori dalle aree per ogni valore di differenza, da 0 a 255.
    conteggi = piu_alto.histogram(mask=ImageChops.invert(dentro))
    totale = sum(conteggi)
    if not totale:
        return {"pixel_fuori": 0, "differenza_media": None, "quota_cambiata": None,
                "ridimensionata": ridimensionata}
    soglia = config.DIFFERENZA_PIXEL_SOGLIA
    return {
        "pixel_fuori": totale,
        "differenza_media": sum(valore * n for valore, n in enumerate(conteggi)) / totale,
        "quota_cambiata": sum(conteggi[soglia + 1:]) / totale,
        "ridimensionata": ridimensionata,
    }


def incolla_nelle_aree(prima: bytes, dopo: bytes, aree: list[list[Punto]]) -> bytes:
    """Il ritocco messo sull'immagine di prima: cambia solo dentro le aree.

    `dopo` e' quello che ha mandato il modello, che di solito ridisegna tutta
    l'immagine. Si riporta alla dimensione di `prima` e si incolla solo nelle
    aree, allargate di RITOCCO_INCOLLA_MARGINE_PX e con il bordo sfumato di
    RITOCCO_INCOLLA_SFUMATURA_PX. Fuori da li' i pixel sono quelli di prima,
    uguali: quello che un ritocco precedente aveva messo non sparisce.
    """
    base = _apri(prima).convert("RGB")
    nuova = _apri(dopo).convert("RGB")
    if nuova.size != base.size:
        nuova = nuova.resize(base.size, Image.Resampling.LANCZOS)
    maschera = _dentro_aree(base.size, aree, config.RITOCCO_INCOLLA_MARGINE_PX)
    sfumatura = config.RITOCCO_INCOLLA_SFUMATURA_PX
    if sfumatura > 0:
        maschera = maschera.filter(ImageFilter.GaussianBlur(radius=sfumatura))
    return _png(Image.composite(nuova, base, maschera))


def _spigoli(immagine: Image.Image) -> Image.Image:
    scala = config.SPIGOLI_LATO_PX / max(immagine.size)
    piccola = immagine.convert("L").resize(
        (max(1, round(immagine.width * scala)), max(1, round(immagine.height * scala))),
        Image.Resampling.LANCZOS)
    spigoli = piccola.filter(ImageFilter.FIND_EDGES).point(
        lambda v: _PIENO if v > config.SPIGOLI_SOGLIA else 0)
    # Il filtro vede un bordo lungo la cornice di ogni immagine: non e' uno spigolo.
    ImageDraw.Draw(spigoli).rectangle((0, 0, spigoli.width - 1, spigoli.height - 1), outline=0)
    return spigoli


def spigoli_ritrovati(vista: bytes, render: bytes) -> float | None:
    """Misura grezza: la quota di spigoli della vista che si ritrovano nel render.

    Spigoli dal filtro dei bordi di Pillow su una copia di SPIGOLI_LATO_PX,
    ritrovati se nel render ce n'e' uno entro SPIGOLI_TOLLERANZA_PX. Il render
    si porta alla dimensione della vista. Non e' lo scostamento della
    geometria del motore: un'ombra nuova o un albero davanti contano come
    spigoli persi. Serve a confrontare fra loro le generazioni dello stesso
    banco, non a dire se un edificio tiene. None se la vista non ha spigoli.
    """
    base = _apri(vista).convert("RGB")
    nuova = _apri(render).convert("RGB").resize(base.size, Image.Resampling.LANCZOS)
    della_vista = _spigoli(base)
    del_render = _spigoli(nuova).filter(ImageFilter.MaxFilter(config.SPIGOLI_TOLLERANZA_PX * 2 + 1))
    totali = della_vista.histogram()[_PIENO]
    ritrovati = ImageChops.multiply(della_vista, del_render).histogram()[_PIENO]
    return ritrovati / totali if totali else None


def ritaglia_miniatura(dati: bytes) -> bytes:
    """Il centro del render alle proporzioni della tessera, a MINIATURA_LARGHEZZA_PX, in JPEG."""
    immagine = _apri(dati).convert("RGB")
    larghezza, altezza = config.MINIATURA_LARGHEZZA_PX, config.MINIATURA_ALTEZZA_PX
    rapporto = larghezza / altezza
    if immagine.width / immagine.height > rapporto:
        nuova = round(immagine.height * rapporto)
        scatola = ((immagine.width - nuova) // 2, 0, (immagine.width - nuova) // 2 + nuova, immagine.height)
    else:
        nuova = round(immagine.width / rapporto)
        scatola = (0, (immagine.height - nuova) // 2, immagine.width, (immagine.height - nuova) // 2 + nuova)
    piccola = immagine.crop(scatola).resize((larghezza, altezza), Image.Resampling.LANCZOS)
    uscita = io.BytesIO()
    piccola.save(uscita, format="JPEG", quality=85)  # numero-non-configurabile: qualita' JPEG di una miniatura
    return uscita.getvalue()


# --- prima di partire e dopo il ritorno: privacy e marcatura -----------------
#
# Due cose che chiedono le regole, non il render:
#
# - prima dell'invio, dalla vista o dalla foto si tolgono i metadati (EXIF con
#   la posizione GPS e il modello del telefono, XMP, commenti, testi PNG). Una
#   foto per l'inserimento nel contesto scattata col telefono porta le
#   coordinate del cantiere e a volte il nome di chi l'ha scattata: al servizio
#   che fa il render servono solo i pixel (GDPR, art. 5.1.c, minimizzazione);
# - al ritorno, nel file si scrive che l'immagine e' generata con l'IA, in un
#   formato che le macchine leggono (AI Act, art. 50.2): un pacchetto XMP con
#   il campo IPTC «Digital Source Type». Niente prompt, ricetta o nome del
#   cliente: solo il fatto che e' generata.

# Metadati che un'immagine si tiene senza dire niente di nessuno: il profilo
# colore (senza, i colori cambiano), la risoluzione di stampa, la trasparenza.
_INFO_INNOCUE = frozenset({
    "icc_profile", "dpi", "transparency", "gamma", "srgb", "chromaticity",
    "jfif", "jfif_version", "jfif_unit", "jfif_density", "adobe", "adobe_transform",
    "progressive", "progression", "aspect", "interlace", "bbox",
})

TIPO_SORGENTE_IA = "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia"
DESCRIZIONE_IA = "Immagine generata con intelligenza artificiale (AIRENDER)"
_XMP_JPEG = b"http://ns.adobe.com/xap/1.0/\x00"
_XMP_PNG = b"XML:com.adobe.xmp"
_CAMPO_LUNGHEZZA_PNG = 4  # numero-non-configurabile: in PNG la lunghezza del blocco sta nei 4 byte prima del tipo
_DUE_BYTE = 2  # numero-non-configurabile: in JPEG marcatore e campo lunghezza sono di 2 byte
_CRC_32 = 0xFFFFFFFF  # numero-non-configurabile: il CRC del PNG e' a 32 bit


def metadati_personali(dati: bytes) -> list[str]:
    """I nomi dei metadati che la pulizia toglierebbe; vuota se non c'e' niente da togliere."""
    try:
        immagine = Image.open(io.BytesIO(dati))
        immagine.load()
    except Exception:
        return []
    trovati = [chiave for chiave in immagine.info if chiave not in _INFO_INNOCUE]
    if len(immagine.getexif()) and "exif" not in trovati:
        trovati.append("exif")
    return sorted(trovati)


def senza_metadati(dati: bytes) -> bytes:
    """I pixel e basta, pronti a partire.

    Se non c'e' niente da togliere tornano gli stessi byte: le viste salvate da
    Allplan non si ricodificano e il render parte dagli stessi pixel di prima.
    Se c'e' un orientamento EXIF lo si applica ai pixel prima di toglierlo,
    cosi' il servizio vede la foto dritta come la vede l'utente. Il profilo
    colore resta. Un file che non si apre torna com'e': lo fermera' chi lo
    deve leggere, con il suo messaggio.
    """
    if not metadati_personali(dati):
        return dati
    from PIL import ImageOps

    immagine = Image.open(io.BytesIO(dati))
    formato = immagine.format
    if formato not in ("PNG", "JPEG", "WEBP"):
        return dati
    profilo = immagine.info.get("icc_profile")
    pulita = ImageOps.exif_transpose(immagine).copy()
    pulita.info = {}
    opzioni = {"icc_profile": profilo} if profilo else {}
    uscita = io.BytesIO()
    if formato == "JPEG":
        pulita.convert("RGB").save(uscita, "JPEG", quality=95, **opzioni)  # numero-non-configurabile: qualita' quasi senza perdita per una vista che riparte
    elif formato == "WEBP":
        pulita.save(uscita, "WEBP", lossless=True, **opzioni)
    else:
        pulita.save(uscita, "PNG", **opzioni)
    return uscita.getvalue()


def _xmp_generata() -> bytes:
    return (
        '<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about=""'
        ' xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"'
        ' xmlns:xmp="http://ns.adobe.com/xap/1.0/"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        f' Iptc4xmpExt:DigitalSourceType="{TIPO_SORGENTE_IA}"'
        ' xmp:CreatorTool="AIRENDER">'
        f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{DESCRIZIONE_IA}</rdf:li></rdf:Alt></dc:description>'
        '</rdf:Description></rdf:RDF></x:xmpmeta><?xpacket end="r"?>'
    ).encode("utf-8")


def _blocco_png(tipo: bytes, contenuto: bytes) -> bytes:
    import struct
    import zlib

    return (struct.pack(">I", len(contenuto)) + tipo + contenuto
            + struct.pack(">I", zlib.crc32(tipo + contenuto) & _CRC_32))


def e_marcata(dati: bytes) -> bool:
    """Vero se il file dice gia' di essere generato con l'IA (il nostro XMP o uno uguale)."""
    return TIPO_SORGENTE_IA.encode("ascii") in dati


def marca_generata(dati: bytes) -> bytes:
    """Gli stessi pixel, con dentro la dichiarazione «generata con l'IA» in XMP.

    Si scrive nei byte, senza ricodificare: PNG riceve un blocco iTXt prima
    della fine, JPEG un segmento APP1 dopo l'intestazione. Gli altri formati
    tornano come sono (nessun servizio del Router li manda oggi).
    """
    if e_marcata(dati):
        return dati
    xmp = _xmp_generata()
    if dati.startswith(b"\x89PNG\r\n\x1a\n"):
        fine = dati.rfind(b"IEND") - _CAMPO_LUNGHEZZA_PNG
        if fine < 0:
            return dati
        # iTXt: parola chiave, poi compressione, metodo, lingua e traduzione vuote.
        blocco = _blocco_png(b"iTXt", _XMP_PNG + b"\x00" * 5 + xmp)  # numero-non-configurabile: i 5 separatori del blocco iTXt
        return dati[:fine] + blocco + dati[fine:]
    if dati.startswith(b"\xff\xd8"):
        posizione = _DUE_BYTE
        if dati[posizione:posizione + _DUE_BYTE] == b"\xff\xe0":  # dopo l'APP0 JFIF, se c'e'
            posizione += _DUE_BYTE + int.from_bytes(dati[posizione + _DUE_BYTE:posizione + 2 * _DUE_BYTE], "big")
        contenuto = _XMP_JPEG + xmp
        segmento = b"\xff\xe1" + (len(contenuto) + _DUE_BYTE).to_bytes(_DUE_BYTE, "big") + contenuto
        return dati[:posizione] + segmento + dati[posizione:]
    return dati


def regola(dati: bytes, tabelle: tuple[list[int], list[int], list[int]], saturazione: float,
           lato_massimo: int | None = None, formato: str = "PNG") -> bytes:
    """Il render con luce e colore regolati (core/regola.py dice i numeri), in PNG o JPEG.

    `tabelle` porta, per rosso, verde e blu, il tono d'arrivo di ognuno dei 256
    toni; `saturazione` e' il fattore del colore (1 = come prima). Con
    `lato_massimo` l'immagine prima si rimpicciolisce: e' l'anteprima dei
    cursori. Sempre RGB: la trasparenza di un render non serve al cliente.
    """
    immagine = _apri(dati).convert("RGB")
    if lato_massimo and max(immagine.size) > lato_massimo:
        fattore = lato_massimo / max(immagine.size)
        immagine = immagine.resize(
            (max(1, round(immagine.width * fattore)), max(1, round(immagine.height * fattore))),
            Image.Resampling.LANCZOS)
    rosso, verde, blu = tabelle
    immagine = immagine.point(list(rosso) + list(verde) + list(blu))
    if saturazione != 1:
        immagine = ImageEnhance.Color(immagine).enhance(saturazione)
    uscita = io.BytesIO()
    if formato == "JPEG":
        immagine.save(uscita, format="JPEG", quality=config.ESPORTA_QUALITA_JPEG)
    else:
        immagine.save(uscita, format="PNG")
    return uscita.getvalue()
