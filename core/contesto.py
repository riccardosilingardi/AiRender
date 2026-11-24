"""Inserisci nel contesto: l'edificio di Allplan dentro un'immagine del luogo.

Il flusso di Riccardo (2026-11-01), messo nello Studio: l'utente porta
un'immagine del contesto (screenshot satellitare, ortofoto, foto da drone),
ci disegna un rettangolo dove va l'edificio, sceglie l'inquadratura (zenitale,
volo d'uccello o da terra, come una foto o uno Street View) e manda. Partono due immagini: prima il contesto con il
contorno dell'area, poi la vista Allplan.

AIRENDER non scarica immagini da mappe: il contesto lo porta l'utente. I
termini di Google Maps Platform vietano di usare quelle immagini con modelli
di AI e di salvarle (thread «Pianificare il fotoinserimento», 2026-11-01).

Le immagini del contesto stanno in <cartella>/contesti/, chiamate con la loro
impronta, come i riferimenti per lo stile.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from . import aree as modulo_aree, blocchi, config, immagine as modulo_immagine, velina as modulo_velina
from .errori import ErroreAirender, FileNonTrovato
from .ricetta import impronta

CARTELLA_CONTESTI = "contesti"

# La nota dell'area non la scrive l'utente: l'area dice solo dove va
# l'edificio, e cosa farci lo dice la regola del contesto.
NOTA_AREA = "the new building"


class ContestoNonValido(ErroreAirender):
    """Un contesto che non si puo' mandare: area, inquadratura o luogo che non tornano."""


def cartella_contesti(radice: Path) -> Path:
    return Path(radice) / CARTELLA_CONTESTI


def salva(radice: Path, dati: bytes) -> str:
    """Salva un'immagine del luogo fra i contesti, chiamata con la sua impronta, e ne da' il nome."""
    tipo = "png" if dati.startswith(b"\x89PNG") else "jpg"
    nome = f"ctx-{impronta(dati)[:16]}.{tipo}"  # numero-non-configurabile: 64 bit di impronta, come i riferimenti
    cartella = cartella_contesti(radice)
    cartella.mkdir(parents=True, exist_ok=True)
    percorso = cartella / nome
    if not percorso.exists():
        # Come coda.scrivi_atomico, che qui non si importa (coda importa contesto).
        temporaneo = percorso.with_name(f".{nome}.tmp")
        temporaneo.write_bytes(dati)
        os.replace(temporaneo, percorso)
    return nome


def controlla_file(radice: Path, file: Path) -> Path:
    """Il file del contesto, solo se sta nella cartella dei contesti e c'e'."""
    percorso = Path(file).resolve()
    if percorso.parent != cartella_contesti(radice).resolve():
        raise ContestoNonValido(
            "L'immagine del contesto non sta nella cartella dei contesti dello Studio.",
            "Caricala di nuovo in «Fotoinserimento».",
        )
    if not percorso.is_file():
        raise FileNonTrovato(
            f"L'immagine del contesto non c'e' piu': {percorso.name}. Non ho inviato niente.",
            "Caricala di nuovo in «Fotoinserimento», oppure togli il contesto.",
        )
    return percorso


@dataclass(frozen=True)
class Contesto:
    """Cosa serve per inserire l'edificio: l'immagine, l'area, l'inquadratura e il resto."""

    file: str
    # Un rettangolo, due angoli opposti in coordinate da 0 a 1 sul contesto.
    # Con una velina che dice gia' dove va ogni edificio (il perimetro alla
    # base) il rettangolo non serve: allora e' None. Resta per i lavori vecchi.
    area: tuple[tuple[float, float], tuple[float, float]] | None
    inquadratura: str = config.CONTESTO_INQUADRATURA_PREDEFINITA
    pulisci_mappa: bool = False
    luogo: str = ""
    # La carta da forno con lo schizzo e gli edifici da inserire (core/velina.py).
    velina: modulo_velina.Velina | None = None
    _area: modulo_aree.Area | None = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.file:
            raise ContestoNonValido(
                "Manca l'immagine del contesto.",
                "Carica l'immagine del luogo in «Fotoinserimento».",
            )
        area = None
        if self.area is None:
            if not (self.velina and self.velina.dice_dove):
                raise ContestoNonValido(
                    "Non so dove va l'edificio: manca il suo perimetro.",
                    "Disegna sulla foto il perimetro alla base dell'edificio.",
                )
        else:
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
        if self.pulisci_mappa and self.inquadratura == blocchi.TERRA:
            raise ContestoNonValido(
                "«Pulisci la mappa» vale per gli screenshot dall'alto, non per una foto da terra.",
                "Togli la spunta, oppure scegli Zenitale o Volo d'uccello.",
            )
        luogo = " ".join((self.luogo or "").split())
        if len(luogo) > config.CONTESTO_LUOGO_MASSIMO:
            raise ContestoNonValido(
                f"Il luogo e' lungo {len(luogo)} caratteri, ne entrano al massimo "
                f"{config.CONTESTO_LUOGO_MASSIMO}.",
                "Scrivi solo indirizzo o coordinate, per esempio «Via Rontano, Reggio Emilia, 44.5214, 10.6990».",
            )
        object.__setattr__(self, "luogo", luogo)
        object.__setattr__(self, "area", area.punti if area else None)
        object.__setattr__(self, "_area", area)

    @property
    def oggetti(self) -> int:
        """Quante viste di Allplan partono: una senza velina."""
        return len(self.velina.oggetti) if self.velina else 1

    def quante_immagini(self) -> int:
        """Il luogo, la velina se c'e' qualcosa da leggere, una vista per edificio."""
        return self.velina.quante_immagini() if self.velina else 2

    def prompt(self, materiali: str = "") -> str:
        velina = self.velina
        return blocchi.componi_contesto(
            self.inquadratura, pulisci_mappa=self.pulisci_mappa, luogo=self.luogo, materiali=materiali,
            area=self._area is not None,
            velina=(blocchi.DettagliVelina(
                schizzo=velina.colori_usati, edifici=len(velina.oggetti),
                perimetri=velina.ha_perimetri, parte=velina.parte_la_velina) if velina else None))

    def prepara(self, dati_contesto: bytes, viste: tuple[bytes, ...] = ()) -> bytes:  # noqa: ARG002
        """La prima immagine che parte: il luogo pulito, col perimetro magenta di ogni edificio o l'area."""
        if self.velina and self.velina.ha_perimetri:
            return modulo_velina.perimetri(dati_contesto, self.velina)
        if self._area is None:
            return dati_contesto
        dimensioni = modulo_immagine.dimensioni(dati_contesto)
        return modulo_immagine.disegna_aree(dati_contesto, modulo_aree.poligoni((self._area,), dimensioni))

    def in_piu(self, dati_contesto: bytes, viste: tuple[bytes, ...]) -> tuple[bytes, ...]:
        """Le immagini dopo il luogo: la velina con lo schizzo (se c'e'), poi una vista per edificio."""
        if self.velina and self.velina.parte_la_velina:
            return (modulo_velina.disegna(dati_contesto, self.velina), *viste)
        return tuple(viste)

    def misura(self, dati_contesto: bytes, render: bytes) -> dict | None:
        """Quanto e' cambiato il contesto fuori dal rettangolo.

        None con «pulisci la mappa», con uno schizzo o coi perimetri: con lo
        schizzo il luogo cambia apposta anche fuori, e un perimetro e' solo la
        base, l'edificio sale sopra di lui. Il numero sarebbe falso (regola 3).
        """
        if self.pulisci_mappa or self._area is None:
            return None
        if self.velina and (self.velina.ha_schizzo or self.velina.ha_perimetri):
            return None
        return modulo_aree.misura(dati_contesto, render, (self._area,))

    def a_dizionario(self) -> dict:
        return {
            "file": self.file,
            "area": [list(p) for p in self.area] if self.area else None,
            "inquadratura": self.inquadratura,
            "pulisci_mappa": self.pulisci_mappa,
            "luogo": self.luogo,
            **({"velina": self.velina.a_dizionario()} if self.velina else {}),
        }

    @classmethod
    def da_dizionario(cls, dati: object) -> "Contesto":
        if not isinstance(dati, dict):
            raise ContestoNonValido(
                "Il contesto non e' un oggetto.",
                "Il contesto e' {file, area, inquadratura, pulisci_mappa, luogo, velina}.",
            )
        velina = None
        if dati.get("velina"):
            try:
                velina = modulo_velina.Velina.da_dizionario(dati.get("velina"))
            except modulo_velina.VelinaNonValida as errore:
                raise ContestoNonValido(errore.fatto, errore.cosa_fare) from None
        try:
            area = tuple(tuple(float(c) for c in p) for p in dati.get("area") or ())
        except (TypeError, ValueError):
            area = ()
        if not area and velina is not None and velina.dice_dove:
            area = None  # type: ignore[assignment]
        elif len(area) != 2:
            raise ContestoNonValido(
                "Manca l'area dove va l'edificio.",
                "Disegna sulla foto il perimetro alla base dell'edificio.",
            )
        return cls(
            file=str(dati.get("file") or ""),
            area=area,  # type: ignore[arg-type]
            inquadratura=str(dati.get("inquadratura") or config.CONTESTO_INQUADRATURA_PREDEFINITA),
            pulisci_mappa=bool(dati.get("pulisci_mappa")),
            luogo=str(dati.get("luogo") or ""),
            velina=velina,
        )
