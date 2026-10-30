"""Le aree di un ritocco (Studio · Ritocca) e del piano «aree» del banco di prova.

Un'area e' un rettangolo o una selezione libera disegnata su un render, con
la sua nota a parole: «infissi in legno scuro». Le aree partono in un invio
solo, in uno dei due modi che il banco mette a confronto:

- contorni  i contorni numerati disegnati sull'immagine che parte;
- maschera  l'immagine com'e', e dopo una maschera (bianco dentro le aree)
            come immagine in piu'.

Quale dei due tiene fermi i pixel fuori dalle aree lo dice il piano «aree»;
il modo che usa lo Studio sta in config.RITOCCO_MODO_AREE.

Le coordinate vanno da 0 a 1 sull'immagine: le aree restano giuste anche se
l'immagine si mostra piu' piccola, e il file si legge a mano.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import blocchi, immagine as modulo_immagine
from .errori import ErroreAirender

FORME = ("rettangolo", "libera")
CONTORNI = "contorni"
MASCHERA = "maschera"
MODI = (CONTORNI, MASCHERA)

# Come l'interfaccia dice un modo, sempre con le stesse parole.
NOMI_MODI = {
    CONTORNI: "contorni numerati disegnati sull'immagine",
    MASCHERA: "maschera come seconda immagine",
}

_BLOCCHI = {CONTORNI: blocchi.AREE_CONTORNI, MASCHERA: blocchi.AREE_MASCHERA}


class AreaNonValida(ErroreAirender):
    """Un'area che non si puo' mandare: forma, punti o nota che non tornano."""


@dataclass(frozen=True)
class Area:
    """Un'area in coordinate da 0 a 1 sull'immagine.

    Un rettangolo ha due punti (due angoli opposti); una selezione libera ne
    ha almeno tre, nell'ordine del lazo.
    """

    forma: str
    punti: tuple[tuple[float, float], ...]
    nota: str

    def __post_init__(self) -> None:
        if self.forma not in FORME:
            raise AreaNonValida(
                f"\"{self.forma}\" non e' una forma di area.",
                "Le forme sono rettangolo e libera.",
            )
        minimo = 2 if self.forma == "rettangolo" else 3  # numero-non-configurabile: punti di un poligono
        if len(self.punti) < minimo or not all(
            len(p) == 2 and all(0 <= c <= 1 for c in p) for p in self.punti
        ):
            raise AreaNonValida(
                f"Un'area {self.forma} ha punti che non tornano: {list(self.punti)}.",
                "Un rettangolo ha due punti, una selezione libera almeno tre; "
                "ogni punto e' [x, y] fra 0 e 1.",
            )
        if not " ".join(self.nota.split()):
            raise AreaNonValida(
                "Un'area senza nota non dice al modello cosa fare.",
                "Scrivi la nota dell'area.",
            )

    def in_pixel(self, larghezza: int, altezza: int) -> list[tuple[float, float]]:
        punti = [(x * larghezza, y * altezza) for x, y in self.punti]
        if self.forma == "rettangolo":
            (x0, y0), (x1, y1) = punti[0], punti[1]
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return punti

    @classmethod
    def da_dizionario(cls, dati: object) -> "Area":
        if not isinstance(dati, dict):
            raise AreaNonValida("Un'area non e' un oggetto.", "Ogni area e' {forma, punti, nota}.")
        try:
            punti = tuple(tuple(float(c) for c in p) for p in dati.get("punti") or ())
        except (TypeError, ValueError):
            punti = ()
        return cls(str(dati.get("forma") or ""), punti, str(dati.get("nota") or ""))

    def a_dizionario(self) -> dict:
        return {"forma": self.forma, "punti": [list(p) for p in self.punti], "nota": self.nota}


def da_elenco(dati: object) -> tuple[Area, ...]:
    """Le aree di un lavoro o di una richiesta dello Studio, almeno una."""
    if not isinstance(dati, (list, tuple)) or not dati:
        raise AreaNonValida(
            "Il ritocco non ha aree.",
            "Disegna un'area sul render, poi scrivi cosa cambiare nella sua nota.",
        )
    return tuple(Area.da_dizionario(a) for a in dati)


def controlla_modo(modo: object) -> str:
    if modo not in MODI:
        raise AreaNonValida(
            f"\"{modo}\" non e' un modo di mandare le aree.",
            f"I modi sono {' e '.join(MODI)}.",
        )
    return str(modo)


def poligoni(aree: tuple[Area, ...], dimensioni_immagine: tuple[int, int]) -> list[list[tuple[float, float]]]:
    larghezza, altezza = dimensioni_immagine
    return [a.in_pixel(larghezza, altezza) for a in aree]


def prompt(modo: str, aree: tuple[Area, ...]) -> str:
    """Il testo che parte: come sono indicate le aree, una riga per nota, cosa evitare."""
    return blocchi.componi_aree(_BLOCCHI[controlla_modo(modo)], [a.nota for a in aree])


def prepara(immagine: bytes, aree: tuple[Area, ...], modo: str) -> tuple[bytes, tuple[bytes, ...]]:
    """L'immagine che parte e le immagini in piu', nel modo scelto."""
    controlla_modo(modo)
    dimensioni = modulo_immagine.dimensioni(immagine)
    forme = poligoni(aree, dimensioni)
    if modo == CONTORNI:
        return modulo_immagine.disegna_aree(immagine, forme), ()
    return immagine, (modulo_immagine.maschera_aree(dimensioni, forme),)


def misura(prima: bytes, dopo: bytes, aree: tuple[Area, ...]) -> dict:
    """Quanto e' cambiata l'immagine fuori dalle aree, con la dimensione del risultato."""
    risultato = modulo_immagine.differenza_fuori_dalle_aree(
        prima, dopo, poligoni(aree, modulo_immagine.dimensioni(prima)))
    risultato["dimensioni_render"] = list(modulo_immagine.dimensioni(dopo))
    return risultato


def _numero(valore: float, cifre: int = 1) -> str:
    return f"{valore:.{cifre}f}".replace(".", ",")


def _percento(quota: float) -> str:
    return f"{_numero(quota * 100)}%"  # numero-non-configurabile: da quota a percento


def testo_misura(valore: dict | None) -> str:
    """La misura fuori dalle aree in una frase, o «non misurato». Sempre lo stesso arrotondamento."""
    if not valore or valore.get("differenza_media") is None:
        return "Fuori dalle aree: non misurato."
    testo = (f"Fuori dalle aree: differenza media {_numero(valore['differenza_media'])} su 255 · "
             f"{_percento(valore['quota_cambiata'])} dei pixel cambiati in modo visibile.")
    if valore.get("ridimensionata"):
        larghezza, altezza = valore.get("dimensioni_render") or ("?", "?")
        testo += (f" Il render e' {larghezza}x{altezza}, non della dimensione di partenza: "
                  "la misura conta anche il ricampionamento.")
    return testo
