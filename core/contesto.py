"""Inserisci nel contesto: l'edificio di Allplan dentro un'immagine del luogo.

Il flusso di Riccardo (2026-11-01), messo nello Studio: l'utente porta
un'immagine del contesto (screenshot satellitare, ortofoto, foto da drone),
ci disegna un rettangolo dove va l'edificio, sceglie l'inquadratura (zenitale
o volo d'uccello) e manda. Partono due immagini: prima il contesto con il
contorno dell'area, poi la vista Allplan.

AIRENDER non scarica immagini da mappe: il contesto lo porta l'utente. I
termini di Google Maps Platform vietano di usare quelle immagini con modelli
di AI e di salvarle (thread «Pianificare il fotoinserimento», 2026-11-01).

Le immagini del contesto stanno in <cartella>/contesti/, chiamate con la loro
impronta, come i riferimenti per lo stile.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import aree as modulo_aree, blocchi, config, immagine as modulo_immagine
from .errori import ErroreAirender, FileNonTrovato

CARTELLA_CONTESTI = "contesti"

# La nota dell'area non la scrive l'utente: l'area dice solo dove va
# l'edificio, e cosa farci lo dice la regola del contesto.
NOTA_AREA = "the new building"


class ContestoNonValido(ErroreAirender):
    """Un contesto che non si puo' mandare: area, inquadratura o luogo che non tornano."""


def cartella_contesti(radice: Path) -> Path:
    return Path(radice) / CARTELLA_CONTESTI


def controlla_file(radice: Path, file: Path) -> Path:
    """Il file del contesto, solo se sta nella cartella dei contesti e c'e'."""
    percorso = Path(file).resolve()
    if percorso.parent != cartella_contesti(radice).resolve():
        raise ContestoNonValido(
            "L'immagine del contesto non sta nella cartella dei contesti dello Studio.",
            "Caricala di nuovo in «Inserisci nel contesto».",
        )
    if not percorso.is_file():
        raise FileNonTrovato(
            f"L'immagine del contesto non c'e' piu': {percorso.name}. Non ho inviato niente.",
            "Caricala di nuovo in «Inserisci nel contesto», oppure togli il contesto.",
        )
    return percorso


@dataclass(frozen=True)
class Contesto:
    """Cosa serve per inserire l'edificio: l'immagine, l'area, l'inquadratura e il resto."""

    file: str
    # Un rettangolo, due angoli opposti in coordinate da 0 a 1 sul contesto.
    area: tuple[tuple[float, float], tuple[float, float]]
    inquadratura: str = config.CONTESTO_INQUADRATURA_PREDEFINITA
    pulisci_mappa: bool = False
    luogo: str = ""
    _area: modulo_aree.Area = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.file:
            raise ContestoNonValido(
                "Manca l'immagine del contesto.",
                "Carica l'immagine del luogo in «Inserisci nel contesto».",
            )
        try:
            area = modulo_aree.Area("rettangolo", tuple(tuple(p) for p in self.area), NOTA_AREA)
        except modulo_aree.AreaNonValida:
            raise ContestoNonValido(
                "L'area dove va l'edificio non e' un rettangolo sul contesto.",
                "Disegna un rettangolo sull'immagine del contesto, trascinando da un angolo all'altro.",
            ) from None
        (x0, y0), (x1, y1) = area.punti
        if x0 == x1 or y0 == y1:
            raise ContestoNonValido(
                "L'area dove va l'edificio e' una linea, non un rettangolo.",
                "Disegna di nuovo l'area, trascinando da un angolo all'altro.",
            )
        try:
            blocchi.controlla_inquadratura(self.inquadratura)
        except blocchi.SceltaNonValida as errore:
            raise ContestoNonValido(errore.fatto, errore.cosa_fare) from None
        luogo = " ".join((self.luogo or "").split())
        if len(luogo) > config.CONTESTO_LUOGO_MASSIMO:
            raise ContestoNonValido(
                f"Il luogo e' lungo {len(luogo)} caratteri, ne entrano al massimo "
                f"{config.CONTESTO_LUOGO_MASSIMO}.",
                "Scrivi solo indirizzo o coordinate, per esempio «Via Rontano, Reggio Emilia, 44.5214, 10.6990».",
            )
        object.__setattr__(self, "luogo", luogo)
        object.__setattr__(self, "area", area.punti)
        object.__setattr__(self, "_area", area)

    def prompt(self, materiali: str = "") -> str:
        return blocchi.componi_contesto(
            self.inquadratura, pulisci_mappa=self.pulisci_mappa, luogo=self.luogo, materiali=materiali)

    def prepara(self, dati_contesto: bytes) -> bytes:
        """Il contesto con il contorno magenta numerato dell'area: e' la prima immagine che parte."""
        dimensioni = modulo_immagine.dimensioni(dati_contesto)
        return modulo_immagine.disegna_aree(dati_contesto, modulo_aree.poligoni((self._area,), dimensioni))

    def misura(self, dati_contesto: bytes, render: bytes) -> dict | None:
        """Quanto e' cambiato il contesto fuori dall'area. None con «pulisci la mappa»: li' cambia apposta."""
        if self.pulisci_mappa:
            return None
        return modulo_aree.misura(dati_contesto, render, (self._area,))

    def a_dizionario(self) -> dict:
        return {
            "file": self.file,
            "area": [list(p) for p in self.area],
            "inquadratura": self.inquadratura,
            "pulisci_mappa": self.pulisci_mappa,
            "luogo": self.luogo,
        }

    @classmethod
    def da_dizionario(cls, dati: object) -> "Contesto":
        if not isinstance(dati, dict):
            raise ContestoNonValido(
                "Il contesto non e' un oggetto.",
                "Il contesto e' {file, area, inquadratura, pulisci_mappa, luogo}.",
            )
        try:
            area = tuple(tuple(float(c) for c in p) for p in dati.get("area") or ())
        except (TypeError, ValueError):
            area = ()
        if len(area) != 2:
            raise ContestoNonValido(
                "Manca l'area dove va l'edificio.",
                "Disegna un rettangolo sull'immagine del contesto.",
            )
        return cls(
            file=str(dati.get("file") or ""),
            area=area,  # type: ignore[arg-type]
            inquadratura=str(dati.get("inquadratura") or config.CONTESTO_INQUADRATURA_PREDEFINITA),
            pulisci_mappa=bool(dati.get("pulisci_mappa")),
            luogo=str(dati.get("luogo") or ""),
        )
