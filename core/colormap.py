"""La color map: la stessa vista, con un colore piatto per ogni zona di materiale.

Da qui passa la mappa materiali (prompt 15, fase B). Una segmentazione,
qualunque sia, da' le zone: SAM3 con le parole, SAM2 automatico, OneFormer,
o le aree disegnate a mano. Questo modulo le trasforma in un'immagine sola,
con un colore per zona, e in una legenda che dice per ogni colore:

- l'etichetta della zona («metal cladding», «parete», «zona 3»);
- la parte di immagine che copre, in percentuale;
- il materiale di Allplan, quando e' assegnato;
- l'immagine di riferimento, quando c'e'.

Il prompt di modifica dira' poi a Nano Banana: «nella zona di colore X metti
il materiale dell'immagine Y».

Le zone vengono dall'apparenza, non dal modello (Trappole note in CLAUDE.md):
due materiali resi simili diventano una zona sola. Per questo la legenda non
promette niente e lo Studio tiene i comandi aggiungi area / togli area.

Qui non c'e' nessun import di Allplan e nessuna rete, come in tutto core/.
"""

from __future__ import annotations

import io
import json
from dataclasses import asdict, dataclass, field
from pathlib import PureWindowsPath

from PIL import Image

from . import config
from .errori import ErroreAirender

# Il colore dei pixel che nessuna zona copre. Nero, perche' nessuna zona lo
# prende dalla tavolozza e un pixel scuro in una color map si nota.
NON_ASSEGNATO = "#000000"

# Colori pieni e lontani fra loro: la color map si legge a occhio e il
# modello li distingue anche dopo la compressione JPEG di qualche servizio.
# Niente nero, che vuol dire «non assegnato», e niente bianco o grigi, che in
# una vista di Allplan sono gia' intonaco e cielo.
TAVOLOZZA = (
    "#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
    "#46f0f0", "#f032e6", "#bcf60c", "#fabebe", "#008080", "#9a6324",
    "#800000", "#aaffc3", "#808000", "#000075",
)  # numero-non-configurabile: e' una tavolozza, non una soglia


@dataclass(frozen=True)
class Zona:
    """Una zona della segmentazione: maschera PNG in scala di grigi, bianco dentro."""

    maschera: bytes
    etichetta: str = ""
    materiale_allplan: str = ""
    riferimento: str = ""


@dataclass(frozen=True)
class VoceLegenda:
    colore: str
    etichetta: str
    area_percento: float
    materiale_allplan: str = ""
    riferimento: str = ""


@dataclass(frozen=True)
class ColorMap:
    immagine: bytes
    legenda: list[VoceLegenda]
    scartate: list[str] = field(default_factory=list)
    non_assegnato_percento: float = 0.0

    def legenda_json(self) -> str:
        return json.dumps({
            "zone": [asdict(voce) for voce in self.legenda],
            "scartate": self.scartate,
            "non_assegnato": {"colore": NON_ASSEGNATO, "area_percento": self.non_assegnato_percento},
        }, ensure_ascii=False, indent=2)


def percento(parte: int, tutto: int) -> float:
    """Un solo arrotondamento per tutta la color map: una cifra decimale."""
    return round(100 * parte / tutto, 1) if tutto else 0.0  # numero-non-configurabile: percentuale


def _maschera(dati: bytes, dimensioni: tuple[int, int], etichetta: str) -> Image.Image:
    try:
        maschera = Image.open(io.BytesIO(dati))
        maschera.load()
    except Exception as errore:  # pylint: disable=broad-exception-caught
        raise ErroreAirender(
            f"La maschera della zona «{etichetta}» non e' un'immagine leggibile ({errore}).",
            "Rifai la segmentazione: la maschera arrivata e' rovinata.",
        ) from errore
    if maschera.size != dimensioni:
        raise ErroreAirender(
            f"La maschera della zona «{etichetta}» e' {maschera.size[0]}×{maschera.size[1]}, "
            f"la vista {dimensioni[0]}×{dimensioni[1]}.",
            "La segmentazione deve lavorare sulla vista com'e', senza ridimensionarla.",
        )
    # Bianco dentro, nero fuori: una maschera sfumata si taglia a meta'.
    return maschera.convert("L").point(lambda valore: 255 if valore >= 128 else 0)  # numero-non-configurabile: bianco/nero a meta' della scala di grigi a 8 bit


def componi(dimensioni: tuple[int, int], zone: list[Zona]) -> ColorMap:
    """Una color map da zone qualunque, sulla vista di queste dimensioni.

    Le zone piu' grandi si dipingono prima, le piccole sopra: una finestra
    dentro una parete resta finestra. Le zone sotto
    config.COLORMAP_AREA_MINIMA_PERCENTO, o oltre config.COLORMAP_ZONE_MASSIME
    (si tengono le piu' grandi), si scartano e lo si dice in `scartate`.
    """
    larghezza, altezza = dimensioni
    totale = larghezza * altezza
    misurate = []
    for indice, zona in enumerate(zone):
        etichetta = zona.etichetta.strip() or f"zona {indice + 1}"
        maschera = _maschera(zona.maschera, dimensioni, etichetta)
        pixel = maschera.histogram()[255]  # numero-non-configurabile: bianco pieno di una maschera a 8 bit
        misurate.append((pixel, indice, etichetta, zona, maschera))

    misurate.sort(key=lambda voce: (-voce[0], voce[1]))
    tenute, scartate = [], []
    for voce in misurate:
        pixel, _indice, etichetta, _zona, _maschera_zona = voce
        troppo_piccola = 100 * pixel / totale < config.COLORMAP_AREA_MINIMA_PERCENTO  # numero-non-configurabile: percentuale
        if troppo_piccola or len(tenute) >= config.COLORMAP_ZONE_MASSIME:
            scartate.append(etichetta)
        else:
            tenute.append(voce)

    tela = Image.new("RGB", dimensioni, NON_ASSEGNATO)
    for posto, (_pixel, _indice, _etichetta, _zona, maschera) in enumerate(tenute):
        tela.paste(TAVOLOZZA[posto], (0, 0), maschera)

    # L'area si misura sulla tela finita: una zona coperta in parte da una
    # piu' piccola mostra solo quello che resta visibile.
    conteggi = {colore: conto for conto, colore in tela.getcolors(maxcolors=totale)}
    legenda = []
    for posto, (_pixel, _indice, etichetta, zona, _maschera_zona) in enumerate(tenute):
        colore = TAVOLOZZA[posto]
        visibili = conteggi.get(_rgb(colore), 0)
        legenda.append(VoceLegenda(
            colore=colore, etichetta=etichetta, area_percento=percento(visibili, totale),
            materiale_allplan=zona.materiale_allplan, riferimento=zona.riferimento))

    uscita = io.BytesIO()
    tela.save(uscita, format="PNG")
    return ColorMap(
        immagine=uscita.getvalue(), legenda=legenda, scartate=scartate,
        non_assegnato_percento=percento(conteggi.get(_rgb(NON_ASSEGNATO), 0), totale))


def zone_da_immagine_colorata(dati: bytes) -> list[Zona]:
    """Le zone di un'immagine a colori piatti, un colore per zona.

    E' la forma in cui escono OneFormer e SAM2 automatico: ogni colore
    diverso diventa una zona, con etichetta «zona N» finche' qualcuno non le
    da' un nome. Un'immagine con troppi colori non e' una segmentazione (e'
    una foto, o un JPEG rovinato) e si rifiuta.
    """
    immagine = Image.open(io.BytesIO(dati)).convert("RGB")
    colori = immagine.getcolors(maxcolors=config.COLORMAP_COLORI_IN_INGRESSO_MASSIMI)
    if colori is None:
        raise ErroreAirender(
            f"L'immagine ha piu' di {config.COLORMAP_COLORI_IN_INGRESSO_MASSIMI} colori: "
            "non e' una segmentazione a colori piatti.",
            "Usa l'uscita a colori della segmentazione, salvata in PNG e non in JPEG.",
        )
    zone = []
    for numero, (_conto, colore) in enumerate(sorted(colori, key=lambda voce: -voce[0]), start=1):
        maschera = _uguale_a(immagine, colore)
        uscita = io.BytesIO()
        maschera.save(uscita, format="PNG")
        zone.append(Zona(maschera=uscita.getvalue(), etichetta=f"zona {numero}"))
    return zone


def _uguale_a(immagine: Image.Image, colore: tuple[int, int, int]) -> Image.Image:
    canali = [canale.point(lambda valore, voluto=voluto: 255 if valore == voluto else 0)  # numero-non-configurabile: bianco/nero di una maschera a 8 bit
              for canale, voluto in zip(immagine.split(), colore)]
    risultato = canali[0]
    for canale in canali[1:]:
        risultato = Image.composite(canale, Image.new("L", immagine.size, 0), risultato)
    return risultato


def _rgb(colore: str) -> tuple[int, int, int]:
    return tuple(int(colore[i:i + 2], 16) for i in (1, 3, 5))  # numero-non-configurabile: posizioni delle cifre in '#rrggbb'


# --- materiali di Allplan ----------------------------------------------------


def nome_materiale(valore: str) -> str:
    """Il nome leggibile di un materiale letto da Allplan.

    La sonda 2 (2026-11-01) li ha trovati in tre forme:
    - attributo 335 Nome_aspetto: 'nemetschek\\_aspetti\\metallo.surf' -> 'metallo';
    - SurfacePath: '30YearEdition Materials\\Outdoor floors\\Asphalt_01' -> 'Asphalt_01';
    - attributo 508 Materiale: 'CLS' -> 'CLS'.
    """
    testo = str(valore or "").strip().strip("'\"")
    if not testo:
        return ""
    nome = PureWindowsPath(testo).name
    if nome.lower().endswith(".surf"):
        nome = nome[:-len(".surf")]
    return nome.strip()


def materiali_allplan(elementi: list[dict]) -> list[str]:
    """I materiali diversi di una lista di elementi letti in Allplan, in ordine di comparsa.

    Ogni elemento e' un dizionario come quelli di elementi.json della sonda:
    si guardano «superficie» > «SurfacePath» e gli attributi 335 e 508.
    """
    visti: list[str] = []
    for elemento in elementi:
        attributi = elemento.get("attributi") or {}
        superficie = elemento.get("superficie") or {}
        candidati = [superficie.get("SurfacePath", "")]
        for chiave, valore in attributi.items():
            numero = str(chiave).split(" ", 1)[0]
            if numero in ("335", "508"):
                candidati.append(valore)
        for candidato in candidati:
            nome = nome_materiale(candidato)
            if nome and nome not in visti:
                visti.append(nome)
    return visti
