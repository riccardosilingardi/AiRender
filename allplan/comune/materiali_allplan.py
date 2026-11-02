"""I materiali del progetto Allplan aperto: le parti che si provano senza Allplan.

Quando la palette cattura una vista, l'adattatore legge il materiale di ogni
elemento 3D (solo lettura: AIRENDER non cambia mai i materiali di Allplan,
decisione di Riccardo del 2026-11-02) e passa qui quello che ha letto. Qui si
raggruppa per materiale, si trova il file .surf di ognuno, se ne estrae
l'anteprima e si scrive tutto accanto alla vista con `core.materiali`.

Provato con la sonda dell'elenco sul progetto 4253 (2026-11-02): 38
materiali, 27 con il .surf trovato, l'anteprima dentro ogni .surf.

Qui non c'e' nessun import di Allplan.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path, PureWindowsPath
from typing import Any

from core import materiali as modulo_materiali
from core.colormap import nome_materiale
from core.ricetta import impronta

SENZA_MATERIALE = "(senza materiale)"
FILE_DIARIO = "diario-materiali.txt"
# Valori dell'attributo 335 che non sono un materiale.
NON_MATERIALI = ("*varia*",)
# Le sottocartelle in cui Allplan tiene le superfici, dentro progetto, Usr e Std.
SOTTOCARTELLE_SURF = ("design", "")
# Quanti elementi leggere per ogni tipo e in tutto. Sul 4253 (13570 elementi)
# 2732 elementi 3D si sono letti in pochi secondi e hanno dato 38 materiali.
PER_TIPO = 150  # numero-non-configurabile: misurato sul 4253 con la sonda dell'elenco, 2026-11-02
MASSIMO_ELEMENTI = 4000  # numero-non-configurabile: misurato sul 4253 con la sonda dell'elenco, 2026-11-02


# Gli elementi 2D: non hanno materiale (lista della sonda materiali, 2026-11-01).
NOMI_2D = re.compile(
    r"^(linea|punto|punto singolo|testo|cerchio|arco|polilinea|polilinea 2d|spline|curva|retino|campitura|"
    r"riempimento|quota|quotatura|linea misura|simbolo|smart symbol|etichetta|stile etichetta|freccia|"
    r"testo variabile|indicatore testo|line|point|text|circle|polyline|hatch(ing)?|pattern|fill(ing)?|"
    r"dimension( line)?|label)$",
    re.IGNORECASE)


def scegli_elementi(nomi: list[str], per_tipo: int = PER_TIPO, massimo: int = MASSIMO_ELEMENTI) -> list[int]:
    """Gli indici da leggere: fino a `per_tipo` per ogni tipo che non e' 2D, fino a `massimo`."""
    presi: Counter = Counter()
    scelti: list[int] = []
    for indice, nome in enumerate(nomi):
        pulito = pulisci(nome)
        if not pulito or NOMI_2D.match(pulito) or presi[pulito] >= per_tipo:
            continue
        presi[pulito] += 1
        scelti.append(indice)
        if len(scelti) >= massimo:
            break
    return scelti


def pulisci(valore: Any) -> str:
    """Il valore come Allplan lo ha dato: senza apici e senza le barre raddoppiate da repr()."""
    testo = str(valore or "").strip().strip("'\"")
    while "\\\\" in testo:
        testo = testo.replace("\\\\", "\\")
    return testo.rstrip("\\").strip()


def materiale_di(letto: dict[str, Any]) -> tuple[str, str, str]:
    """(nome leggibile, valore letto, da dove): SurfacePath, poi attributo 335, poi 508."""
    superficie = pulisci((letto.get("superficie") or {}).get("SurfacePath", ""))
    nome = nome_materiale(superficie)
    if nome and not superficie.startswith("errore"):
        return nome, superficie, "SurfacePath"
    attributi = letto.get("attributi") or {}
    for numero in ("335", "508"):
        for chiave, valore in attributi.items():
            if str(chiave).split(" ", 1)[0] == numero:
                pulito = pulisci(valore)
                nome = nome_materiale(pulito)
                if nome and pulito.lower() not in NON_MATERIALI:
                    return nome, pulito, numero
    return SENZA_MATERIALE, "", ""


def raggruppa(letti: list[dict[str, Any]]) -> list[tuple[str, str, int]]:
    """(nome, valore, quanti elementi) per materiale, il piu' usato per primo."""
    conta: Counter = Counter()
    nomi: dict[str, str] = {}
    for letto in letti:
        nome, valore, _da = materiale_di(letto)
        if nome == SENZA_MATERIALE:
            continue
        conta[valore] += 1
        nomi[valore] = nome
    return sorted(((nomi[v], v, n) for v, n in conta.items()), key=lambda r: (-r[2], r[0].lower()))


def senza_materiale(letti: list[dict[str, Any]]) -> list[str]:
    conta = Counter(pulisci(letto.get("GetDisplayName", "?")) for letto in letti
                    if materiale_di(letto)[0] == SENZA_MATERIALE)
    return [f"{nome} {quanti}" for nome, quanti in conta.most_common()]


def candidati_surf(valore: str, radici: list[Path]) -> list[Path]:
    """Dove puo' stare il .surf di un valore letto: assoluto, o relativo al progetto, a Usr, a Std."""
    parti = PureWindowsPath(valore).parts
    if not parti:
        return []
    nomi = [parti]
    if not parti[-1].lower().endswith(".surf"):
        nomi.append((*parti[:-1], parti[-1] + ".surf"))
    if PureWindowsPath(valore).is_absolute():
        return [Path(*p) for p in nomi]
    trovati: list[Path] = []
    for radice in radici:
        for sotto in SOTTOCARTELLE_SURF:
            base = radice / sotto if sotto else radice
            for nome in nomi:
                percorso = base.joinpath(*nome)
                if percorso not in trovati:
                    trovati.append(percorso)
    return trovati


def scrivi_per_vista(vista: Path, letti: list[dict[str, Any]], radici: list[Path],
                     letto_il: str) -> Path:
    """L'elenco dei materiali accanto alla vista, con le anteprime nella cartella dei materiali."""
    cartella = modulo_materiali.cartella_anteprime(Path(vista).parent)
    cartella.mkdir(parents=True, exist_ok=True)
    materiali = []
    for nome, valore, quanti in raggruppa(letti):
        materiali.append(modulo_materiali.MaterialeModello(
            valore, nome, quanti, _anteprima(valore, radici, cartella)))
    return modulo_materiali.scrivi_elenco(vista, materiali, senza_materiale(letti), letto_il)


def scrivi_errore(vista: Path, errore: str, letto_il: str) -> Path:
    return modulo_materiali.scrivi_elenco(vista, [], [], letto_il, errore=errore)


def _anteprima(valore: str, radici: list[Path], cartella: Path) -> str | None:
    """Il nome del PNG estratto dal .surf, o None se il .surf non c'e' o non si apre."""
    for percorso in candidati_surf(valore, radici):
        try:
            if not percorso.is_file():
                continue
            png = modulo_materiali.anteprima_da_surf(percorso.read_bytes())
        except (OSError, ValueError):
            return None
        nome = f"{impronta(png)[:16]}.png"  # numero-non-configurabile: 64 bit di impronta, come i riferimenti
        destinazione = cartella / nome
        if not destinazione.exists():
            destinazione.write_bytes(png)
        return nome
    return None


class Diario:
    """Una riga su disco PRIMA di ogni chiamata ad Allplan: se Allplan si chiude, dice dove."""

    def __init__(self, cartella: Path):
        self.percorso = Path(cartella) / FILE_DIARIO

    def ricomincia(self) -> None:
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        self.percorso.write_text("", encoding="utf-8")

    def prima(self, testo: str) -> None:
        with self.percorso.open("a", encoding="utf-8") as file:
            file.write(testo + "\n")
            file.flush()
            os.fsync(file.fileno())
