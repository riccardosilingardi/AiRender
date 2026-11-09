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

Dal 2026-11-09 (compositore, bozza «flussi»): un'area puo' essere anche un
tratto di pennello, aggiungi o togli, e le note si possono scrivere in una
frase sola che chiama le aree con @1, @2: `da_testo` la divide in una nota
per area, e la nota di ogni area si vede prima di Applica.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from . import blocchi, config, immagine as modulo_immagine
from .errori import ErroreAirender

FORME = ("rettangolo", "libera", "pennello")
CAMBIA = "cambia"
AGGIUNGI = "aggiungi"
TOGLI = "togli"
AZIONI = (CAMBIA, AGGIUNGI, TOGLI)
# La nota di un tratto «togli» che il testo non chiama: togliere e' gia'
# tutto quello che serve dire.
NOTA_TOGLI = "togli quello che c'e' qui e ricostruisci quello che sta dietro"
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
    # Il numero del Rif. (riferimento di un oggetto o di una persona) che
    # questa nota usa, da 1. Il file sta nel lavoro, in `inserti`.
    inserto: int | None = None
    # cambia (rettangolo, selezione libera), aggiungi o togli (i pennelli).
    azione: str = CAMBIA
    # Solo per il pennello: lo spessore del tratto, in frazione della larghezza.
    spessore: float | None = None

    def __post_init__(self) -> None:
        if self.forma not in FORME:
            raise AreaNonValida(
                f"\"{self.forma}\" non e' una forma di area.",
                "Le forme sono rettangolo, selezione libera e pennello.",
            )
        if self.azione not in AZIONI:
            raise AreaNonValida(
                f"\"{self.azione}\" non e' un'azione di un'area.",
                "Le azioni sono cambia, aggiungi e togli.",
            )
        sottile, grosso = config.PENNELLO_SPESSORI
        if self.forma == "pennello":
            if not isinstance(self.spessore, (int, float)) or isinstance(self.spessore, bool) \
                    or not sottile <= self.spessore <= grosso:
                raise AreaNonValida(
                    f"Un tratto di pennello ha uno spessore che non torna: {self.spessore!r}.",
                    f"Lo spessore va da {sottile} a {grosso} della larghezza del render.",
                )
        elif self.spessore is not None:
            raise AreaNonValida(
                "Solo un tratto di pennello ha uno spessore.",
                "Togli lo spessore dall'area, oppure disegnala col pennello.",
            )
        minimo = {"rettangolo": 2, "libera": 3, "pennello": 1}[self.forma]  # numero-non-configurabile: punti di una forma
        if len(self.punti) < minimo or not all(
            len(p) == 2 and all(0 <= c <= 1 for c in p) for p in self.punti
        ):
            raise AreaNonValida(
                f"Un'area {self.forma} ha punti che non tornano: {list(self.punti)}.",
                "Un rettangolo ha due punti, una selezione libera almeno tre, "
                "un tratto di pennello almeno uno; ogni punto e' [x, y] fra 0 e 1.",
            )
        if not " ".join(self.nota.split()):
            raise AreaNonValida(
                "Un'area senza nota non dice al modello cosa fare.",
                "Scrivi la nota dell'area.",
            )
        if self.inserto is not None and not (
                isinstance(self.inserto, int) and 1 <= self.inserto <= config.INSERTI_MASSIMO):
            raise AreaNonValida(
                f"Un'area dice di usare il Rif. {self.inserto!r}, che non c'e'.",
                f"I riferimenti vanno da 1 a {config.INSERTI_MASSIMO}.",
            )

    def in_pixel(self, larghezza: int, altezza: int) -> list[tuple[float, float]]:
        punti = [(x * larghezza, y * altezza) for x, y in self.punti]
        if self.forma == "rettangolo":
            (x0, y0), (x1, y1) = punti[0], punti[1]
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if self.forma == "pennello":
            return contorno_tratto(punti, float(self.spessore) * larghezza / 2)  # numero-non-configurabile: raggio = meta' spessore
        return punti

    @classmethod
    def da_dizionario(cls, dati: object) -> "Area":
        if not isinstance(dati, dict):
            raise AreaNonValida("Un'area non e' un oggetto.", "Ogni area e' {forma, punti, nota}.")
        try:
            punti = tuple(tuple(float(c) for c in p) for p in dati.get("punti") or ())
        except (TypeError, ValueError):
            punti = ()
        inserto = dati.get("inserto")
        if inserto is not None and not (isinstance(inserto, int) and not isinstance(inserto, bool)):
            raise AreaNonValida(f"Un'area ha un Rif. che non e' un numero: {inserto!r}.",
                                "Togli l'immagine dalla nota e rimettila.")
        spessore = dati.get("spessore")
        if spessore is not None and (isinstance(spessore, bool) or not isinstance(spessore, (int, float))):
            raise AreaNonValida(f"Un tratto di pennello ha uno spessore che non e' un numero: {spessore!r}.",
                                "Ridisegna il tratto.")
        return cls(str(dati.get("forma") or ""), punti, str(dati.get("nota") or ""), inserto,
                   str(dati.get("azione") or CAMBIA), spessore)

    def a_dizionario(self) -> dict:
        voce = {"forma": self.forma, "punti": [list(p) for p in self.punti], "nota": self.nota}
        if self.inserto is not None:
            voce["inserto"] = self.inserto
        if self.azione != CAMBIA:
            voce["azione"] = self.azione
        if self.spessore is not None:
            voce["spessore"] = self.spessore
        return voce


# Quanti punti ha mezzo cerchio in testa e in coda a un tratto: abbastanza
# perche' la punta sembri tonda, pochi perche' il poligono resti piccolo.
_PUNTI_MEZZO_CERCHIO = 8  # numero-non-configurabile: forma della punta, non un giudizio sul risultato


def contorno_tratto(punti: list[tuple[float, float]], raggio: float) -> list[tuple[float, float]]:
    """Il contorno di un tratto di pennello largo 2 x raggio, punte tonde.

    Il tratto si allarga di `raggio` a sinistra e a destra di ogni punto; un
    tratto di un punto solo e' un cerchio. Un tratto che si incrocia da solo
    fa un poligono che si incrocia: si riempie lo stesso, tranne a volte
    il pezzetto dell'incrocio (la stessa regola dello Studio, studio.js).
    """
    tratto = [punti[0]]
    for p in punti[1:]:
        if math.dist(p, tratto[-1]) > 1e-6:  # numero-non-configurabile: punti uguali
            tratto.append(p)
    if len(tratto) == 1:
        (x, y), n = tratto[0], 2 * _PUNTI_MEZZO_CERCHIO
        return [(x + raggio * math.cos(2 * math.pi * i / n), y + raggio * math.sin(2 * math.pi * i / n))
                for i in range(n)]

    def normale(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        lungo = math.hypot(dx, dy)
        return (-dy / lungo, dx / lungo)

    normali = []
    for i in range(len(tratto)):
        prima = normale(tratto[i - 1], tratto[i]) if i > 0 else None
        dopo = normale(tratto[i], tratto[i + 1]) if i < len(tratto) - 1 else None
        nx, ny = ((prima[0] + dopo[0]) / 2, (prima[1] + dopo[1]) / 2) if prima and dopo else (prima or dopo)
        lungo = math.hypot(nx, ny) or 1.0
        normali.append((nx / lungo, ny / lungo))

    def mezzo_cerchio(centro, verso):
        # Da sinistra a destra del tratto, passando davanti (verso = direzione).
        angolo = math.atan2(verso[1], verso[0])
        return [(centro[0] + raggio * math.cos(angolo + math.pi / 2 - math.pi * i / _PUNTI_MEZZO_CERCHIO),
                 centro[1] + raggio * math.sin(angolo + math.pi / 2 - math.pi * i / _PUNTI_MEZZO_CERCHIO))
                for i in range(1, _PUNTI_MEZZO_CERCHIO)]

    sinistra = [(p[0] + n[0] * raggio, p[1] + n[1] * raggio) for p, n in zip(tratto, normali)]
    destra = [(p[0] - n[0] * raggio, p[1] - n[1] * raggio) for p, n in zip(tratto, normali)]
    # La normale e' (-dy, dx): la direzione del tratto e' (ny, -nx).
    avanti = (normali[-1][1], -normali[-1][0])
    indietro = (-normali[0][1], normali[0][0])
    return sinistra + mezzo_cerchio(tratto[-1], avanti) + destra[::-1] + mezzo_cerchio(tratto[0], indietro)


def da_elenco(dati: object) -> tuple[Area, ...]:
    """Le aree di un lavoro o di una richiesta dello Studio, almeno una."""
    if not isinstance(dati, (list, tuple)) or not dati:
        raise AreaNonValida(
            "Il ritocco non ha aree.",
            "Disegna un'area sul render, poi scrivi cosa cambiare nella sua nota.",
        )
    return tuple(Area.da_dizionario(a) for a in dati)


_MENZIONE = re.compile(r"@(\d+)")
# Dove finisce un pezzo di frase: punto e virgola, virgola o punto seguiti da
# uno spazio (o a fine testo). «0,5 m» resta intero.
_FINE_PEZZO = re.compile(r"\s*(?:;|,(?=\s)|\.(?=\s|$))\s*")


def da_testo(testo: object, aree: object) -> list[dict]:
    """Le aree di una richiesta con la nota di ognuna, presa da una frase sola.

    La frase chiama le aree con @1, @2 («rivesti @1 di legno, togli il palo in
    @3»). Si divide ai punti, alle virgole e ai punto e virgola: ogni pezzo va
    alle aree che chiama, con @N riscritto «quest'area»; un pezzo che non
    chiama nessuna area va con il pezzo prima (o con quello dopo, se e' il
    primo). Con un'area sola tutto il testo e' la sua nota. Un tratto
    «togli» che il testo non chiama toglie e basta; ogni altra area il testo
    la deve chiamare.
    """
    if not isinstance(aree, (list, tuple)) or not aree:
        raise AreaNonValida(
            "Il ritocco non ha aree.",
            "Disegna un'area sul render, poi scrivi cosa cambiare.",
        )
    if not all(isinstance(a, dict) for a in aree):
        raise AreaNonValida("Un'area non e' un oggetto.", "Ogni area e' {forma, punti}.")
    quante = len(aree)
    frase = " ".join(str(testo or "").split())
    pezzi = [p for p in _FINE_PEZZO.split(frase) if p]
    note: list[list[str]] = [[] for _ in aree]
    def senza_testa(pezzo: str, numero: int) -> str:
        # «@1 rivesti di legno»: la riga e' gia' «Area 1:», la @ in testa non serve.
        # Solo se il pezzo chiama quest'area e basta: «@1 e @2 dello stesso legno» resta intero.
        if {int(m) for m in _MENZIONE.findall(pezzo)} != {numero}:
            return pezzo
        resto = re.sub(rf"^@{numero}\b\s*", "", pezzo)
        return resto or pezzo

    if quante == 1:
        if pezzi:
            note[0].append(_MENZIONE.sub("quest'area", senza_testa(frase, 1)).rstrip("."))
    else:
        da_dare: list[str] = []
        ultime: list[int] = []
        for pezzo in pezzi:
            numeri = []
            for m in _MENZIONE.finditer(pezzo):
                numero = int(m.group(1))
                if not 1 <= numero <= quante:
                    raise AreaNonValida(
                        f"Il testo chiama @{numero}, ma le aree sono {quante}.",
                        f"Le aree vanno da @1 a @{quante}: correggi il numero.",
                    )
                if numero not in numeri:
                    numeri.append(numero)
            if not numeri:
                if ultime:
                    for numero in ultime:
                        note[numero - 1].append(pezzo)
                else:
                    da_dare.append(pezzo)
                continue
            for numero in numeri:
                riscritto = _MENZIONE.sub(
                    lambda m, n=numero: "quest'area" if int(m.group(1)) == n else f"l'area {m.group(1)}",
                    senza_testa(pezzo, numero))
                note[numero - 1].extend([*da_dare, riscritto])
            da_dare, ultime = [], numeri
    risultato = []
    for numero, (area, sue) in enumerate(zip(aree, note), start=1):
        nota = "; ".join(sue)
        if not nota and area.get("azione") == TOGLI:
            nota = NOTA_TOGLI
        if not nota:
            raise AreaNonValida(
                f"L'area {numero} non e' nel testo." if frase else "Il ritocco non dice cosa cambiare.",
                f"Scrivi @{numero} dove va la sua modifica, oppure togli l'area." if frase
                else "Scrivi cosa cambiare e chiama le aree con @1, @2.",
            )
        risultato.append({**area, "nota": nota})
    return risultato


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
    return blocchi.componi_aree(_BLOCCHI[controlla_modo(modo)], [a.nota for a in aree],
                                [a.inserto for a in aree], [a.azione for a in aree])


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


def incolla(prima: bytes, dopo: bytes, aree: tuple[Area, ...]) -> bytes:
    """Il render del ritocco: il risultato del modello solo dentro le aree, il resto com'era prima."""
    return modulo_immagine.incolla_nelle_aree(prima, dopo, poligoni(aree, modulo_immagine.dimensioni(prima)))


def _numero(valore: float, cifre: int = 1) -> str:
    return f"{valore:.{cifre}f}".replace(".", ",")


def _percento(quota: float) -> str:
    return f"{_numero(quota * 100)}%"  # numero-non-configurabile: da quota a percento


def testo_misura(valore: dict | None) -> str:
    """La misura fuori dalle aree in una frase, o «non misurato». Sempre lo stesso arrotondamento."""
    if valore and valore.get("incollato"):
        # Il render e' il ritocco incollato sull'immagine di prima: fuori
        # dalle aree i pixel sono quelli di prima per costruzione.
        return "Fuori dalle aree: com'era prima."
    if not valore or valore.get("differenza_media") is None:
        return "Fuori dalle aree: non misurato."
    testo = (f"Fuori dalle aree: differenza media {_numero(valore['differenza_media'])} su 255 · "
             f"{_percento(valore['quota_cambiata'])} dei pixel cambiati in modo visibile.")
    if valore.get("ridimensionata"):
        larghezza, altezza = valore.get("dimensioni_render") or ("?", "?")
        testo += (f" Il render e' {larghezza}x{altezza}, non della dimensione di partenza: "
                  "la misura conta anche il ricampionamento.")
    return testo
