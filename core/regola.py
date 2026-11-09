"""Regola: luce e colore del render prima di esportarlo, come in Photoshop.

Richiesta di Riccardo (2026-11-08): «prima di esportare, tool per classici
ritocchi di illuminazione, contrasto, luci, ombre, curve come fa la palette di
Photoshop». Gira sul computer dell'utente (nello Studio o nel browser della
web app): nessuna immagine parte, non costa crediti.

Qui ci sono solo i numeri: cosa vuol dire ogni cursore, come si combinano, la
tabella di 256 toni che ne esce per ogni canale. I pixel li tocca
core/immagine.py, l'unico modulo che apre le immagini. Cosi' la matematica si
prova da riga di comando senza un'immagine.

L'ordine e' quello di una pila di livelli di regolazione:
Esposizione (sulla luce lineare) → Contrasto (curva a S) → Luci e Ombre →
Curva → Temperatura (rosso e blu) → Saturazione. Tutto vale su tutta
l'immagine allo stesso modo: Luci e Ombre sono curve, non il recupero locale
di Photoshop, e lo dicono anche a schermo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config
from .errori import ErroreAirender

TONI = 256  # numero-non-configurabile: toni di un canale a 8 bit
_BIANCO = TONI - 1
_MEZZO = 0.5  # numero-non-configurabile: il grigio medio, centro delle curve

# I cursori, nell'ordine in cui compaiono e si applicano, con il nome a schermo.
CURSORI = (
    ("esposizione", "Esposizione"),
    ("contrasto", "Contrasto"),
    ("luci", "Luci"),
    ("ombre", "Ombre"),
    ("temperatura", "Temperatura"),
    ("saturazione", "Saturazione"),
)
NOMI = dict(CURSORI)


class RegolazioneNonValida(ErroreAirender):
    """Un cursore fuori misura, una curva con punti impossibili."""


@dataclass(frozen=True)
class Regolazione:
    """I sei cursori (da -max a +max, 0 = niente) e la curva, punti (x, y) da 0 a 255."""

    esposizione: int = 0
    contrasto: int = 0
    luci: int = 0
    ombre: int = 0
    temperatura: int = 0
    saturazione: int = 0
    curva: tuple[tuple[int, int], ...] = field(default=())

    def neutra(self) -> bool:
        """Vero se non cambia niente: allora il render si esporta com'e'."""
        return all(getattr(self, nome) == 0 for nome, _ in CURSORI) and not self.curva_attiva()

    def curva_attiva(self) -> bool:
        """Falso se non c'e' curva o se e' la diagonale da un estremo all'altro."""
        if not self.curva:
            return False
        diagonale = all(x == y for x, y in self.curva)
        return not (diagonale and self.curva[0][0] == 0 and self.curva[-1][0] == _BIANCO)

    def descrizione(self) -> list[str]:
        """Le regolazioni a parole, per dire cosa c'e' nel file: «Esposizione +8», «Curva (3 punti)»."""
        righe = [f"{NOMI[nome]} {_segno(getattr(self, nome))}" for nome, _ in CURSORI if getattr(self, nome)]
        if self.curva_attiva():
            righe.append(f"Curva ({len(self.curva)} punti)")
        return righe

    def come_dati(self) -> dict:
        dati = {nome: getattr(self, nome) for nome, _ in CURSORI}
        dati["curva"] = [list(p) for p in self.curva]
        return dati


def _segno(valore: int) -> str:
    return f"+{valore}" if valore > 0 else f"−{-valore}"


def leggi(dati: dict | None) -> Regolazione:
    """La regolazione mandata dalla pagina, controllata. Niente (o {}) = nessuna regolazione."""
    if not dati:
        return Regolazione()
    if not isinstance(dati, dict):
        raise RegolazioneNonValida("Le regolazioni arrivate non si leggono.", "Premi Azzera e rifalle.")
    massimo = config.REGOLA_CURSORE_MASSIMO
    valori = {}
    for nome, etichetta in CURSORI:
        valore = dati.get(nome, 0)
        if isinstance(valore, bool) or not isinstance(valore, (int, float)):
            raise RegolazioneNonValida(f"{etichetta}: il valore non e' un numero.", "Premi Azzera e rifalle.")
        valore = round(valore)
        if abs(valore) > massimo:
            raise RegolazioneNonValida(
                f"{etichetta} vale {valore}: va da −{massimo} a +{massimo}.",
                f"Riporta {etichetta} dentro questi limiti.",
            )
        valori[nome] = valore
    return Regolazione(**valori, curva=_leggi_curva(dati.get("curva")))


def _leggi_curva(punti) -> tuple[tuple[int, int], ...]:
    if not punti:
        return ()
    if not isinstance(punti, list):
        raise RegolazioneNonValida("La curva arrivata non si legge.", "Premi Azzera sulla curva e rifalla.")
    if len(punti) > config.REGOLA_CURVA_PUNTI_MASSIMI:
        raise RegolazioneNonValida(
            f"La curva ha {len(punti)} punti: al massimo {config.REGOLA_CURVA_PUNTI_MASSIMI}.",
            "Togli qualche punto (doppio clic su un punto lo toglie).",
        )
    letti = []
    for punto in punti:
        if (not isinstance(punto, (list, tuple)) or len(punto) != 2
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in punto)):
            raise RegolazioneNonValida("Un punto della curva non si legge.", "Premi Azzera sulla curva e rifalla.")
        x, y = (round(v) for v in punto)
        if not (0 <= x <= _BIANCO and 0 <= y <= _BIANCO):
            raise RegolazioneNonValida(
                f"Un punto della curva ({x}, {y}) sta fuori da 0-{_BIANCO}.",
                "Trascina i punti dentro il riquadro della curva.",
            )
        letti.append((x, y))
    letti.sort()
    if len(letti) < 2:
        raise RegolazioneNonValida("Una curva ha bisogno di almeno due punti.", "Premi Azzera sulla curva.")
    if len({x for x, _ in letti}) != len(letti):
        raise RegolazioneNonValida(
            "Due punti della curva stanno sullo stesso tono.",
            "Sposta uno dei due a destra o a sinistra.",
        )
    return tuple(letti)


# --- le tabelle dei toni ---------------------------------------------------------


def _lineare(v: float) -> float:
    """Da sRGB alla luce lineare (IEC 61966-2-1)."""
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4  # numero-non-configurabile: formula sRGB


def _srgb(v: float) -> float:
    """Dalla luce lineare a sRGB (IEC 61966-2-1)."""
    return v * 12.92 if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055  # numero-non-configurabile: formula sRGB


def _taglia(v: float) -> float:
    return min(1.0, max(0.0, v))


def _campana(t: float) -> float:
    """0 ai bordi, 1 al centro: dove Luci e Ombre spingono di piu'."""
    return 4 * t * (1 - t) if 0 < t < 1 else 0.0  # numero-non-configurabile: 4t(1-t) vale 1 a meta'


def _curva_monotona(punti: tuple[tuple[int, int], ...]):
    """La funzione che passa dai punti senza ondeggiare (Fritsch-Carlson), piatta fuori dagli estremi."""
    xs = [x / _BIANCO for x, _ in punti]
    ys = [y / _BIANCO for _, y in punti]
    n = len(xs)
    pendenze = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(n - 1)]
    tangenti = [pendenze[0]] + [
        0.0 if pendenze[i - 1] * pendenze[i] <= 0 else (pendenze[i - 1] + pendenze[i]) / 2 for i in range(1, n - 1)
    ] + [pendenze[-1]]
    for i, d in enumerate(pendenze):
        if d == 0:
            tangenti[i] = tangenti[i + 1] = 0.0
            continue
        a, b = tangenti[i] / d, tangenti[i + 1] / d
        somma = a * a + b * b
        if somma > 9:  # numero-non-configurabile: limite di Fritsch-Carlson perche' resti monotona
            tau = 3 / somma ** 0.5  # numero-non-configurabile: idem
            tangenti[i], tangenti[i + 1] = tau * a * d, tau * b * d

    def f(x: float) -> float:
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = max(k for k in range(n - 1) if xs[k] <= x)
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * tangenti[i]  # numero-non-configurabile: base di Hermite
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * tangenti[i + 1])  # numero-non-configurabile: idem
    return f


def tono(regolazione: Regolazione, v: float) -> float:
    """Un tono (da 0 a 1) dopo Esposizione, Contrasto, Luci, Ombre e Curva, uguale per i tre canali."""
    massimo = config.REGOLA_CURSORE_MASSIMO
    r = regolazione
    if r.esposizione:
        v = _srgb(min(1.0, _lineare(v) * 2 ** (r.esposizione / massimo * config.REGOLA_ESPOSIZIONE_STOP)))
    if r.contrasto and 0 < v < 1:
        g = 2 ** (r.contrasto / massimo * config.REGOLA_CONTRASTO_FORZA)
        v = v ** g / (v ** g + (1 - v) ** g)
    if r.luci and v > _MEZZO:
        v += r.luci / massimo * config.REGOLA_LUCI_OMBRE_AMPIEZZA * _campana((v - _MEZZO) / _MEZZO)
    if r.ombre and v < _MEZZO:
        v += r.ombre / massimo * config.REGOLA_LUCI_OMBRE_AMPIEZZA * _campana(v / _MEZZO)
    v = _taglia(v)
    if r.curva_attiva():
        v = _taglia(_curva_monotona(r.curva)(v))
    return v


def tabelle(regolazione: Regolazione) -> tuple[list[int], list[int], list[int]]:
    """Per rosso, verde e blu: in che tono va ognuno dei 256 toni. Temperatura compresa."""
    caldo = regolazione.temperatura / config.REGOLA_CURSORE_MASSIMO * config.REGOLA_TEMPERATURA_FORZA
    toni = [tono(regolazione, i / _BIANCO) for i in range(TONI)]

    def otto_bit(valori):
        return [round(_taglia(v) * _BIANCO) for v in valori]

    return (otto_bit(v * (1 + caldo) for v in toni), otto_bit(toni), otto_bit(v * (1 - caldo) for v in toni))


def tabella_curva(regolazione: Regolazione) -> list[int]:
    """Solo la curva, 256 toni: la pagina la disegna sotto i punti."""
    if not regolazione.curva_attiva():
        return list(range(TONI))
    f = _curva_monotona(regolazione.curva)
    return [round(_taglia(f(i / _BIANCO)) * _BIANCO) for i in range(TONI)]


def fattore_saturazione(regolazione: Regolazione) -> float:
    """1 = come prima, 0 = bianco e nero, 2 = il doppio del colore (con i valori di config)."""
    return 1 + regolazione.saturazione / config.REGOLA_CURSORE_MASSIMO * config.REGOLA_SATURAZIONE_MASSIMA
