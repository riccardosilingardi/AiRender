"""I preset inclusi nel pacchetto.

Un preset e' un prompt tecnico con un modello e dei valori di partenza, piu'
una versione: senza versione una pila di livelli non si rifa' uguale, perche'
noi stessi cambieremo questi testi.

Le miniature generate (DESIGN.md, schermata 2) arrivano quando ci sara' una
palette: qui ci sono solo i dati che le produrranno.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config, grana
from .errori import PresetSconosciuto
from .lessico import controlla_etichetta


@dataclass(frozen=True)
class Preset:
    """Uno stile della griglia."""

    identificativo: str
    nome: str
    descrizione: str
    modello: str
    prompt_tecnico: str
    grana_predefinita: str = grana.MEDIA
    forza_struttura: int = config.FORZA_STRUTTURA_PREDEFINITA
    versione: str = "1"

    def __post_init__(self) -> None:
        controlla_etichetta(self.nome, f"il nome del preset {self.identificativo}")
        controlla_etichetta(
            self.descrizione, f"la descrizione del preset {self.identificativo}"
        )
        grana.normalizza(self.grana_predefinita)
        if not (
            config.FORZA_STRUTTURA_MINIMA
            <= self.forza_struttura
            <= config.FORZA_STRUTTURA_MASSIMA
        ):
            raise ValueError(
                f"il preset {self.identificativo} chiede una forza della "
                f"struttura fuori dai limiti del servizio: {self.forza_struttura}"
            )


_INVARIANZA = (
    "keep the exact same camera, perspective and building geometry as the "
    "reference image; do not add, remove or move volumes, openings or floors"
)

PRESET = {
    p.identificativo: p
    for p in (
        Preset(
            identificativo="base",
            nome="Base",
            descrizione=(
                "Resa neutra e fedele. Materiali plausibili, luce diffusa, "
                "nessuna interpretazione d'atmosfera."
            ),
            modello="realism",
            prompt_tecnico=(
                "architectural visualization of the reference building, "
                "photographic realism, neutral overcast daylight, plausible "
                "construction materials, " + _INVARIANZA
            ),
        ),
        Preset(
            identificativo="esterno-giorno",
            nome="Esterno giorno",
            descrizione=(
                "Sole basso, ombre lunghe, cielo leggero. Per una facciata da "
                "mostrare al cliente."
            ),
            modello="realism",
            prompt_tecnico=(
                "exterior architectural photograph of the reference building, "
                "late afternoon sunlight, long soft shadows, clear sky, "
                "context vegetation kept minimal, " + _INVARIANZA
            ),
        ),
        Preset(
            identificativo="interno-neutro",
            nome="Interno neutro",
            descrizione=(
                "Luce naturale da finestra, superfici opache, nessun arredo "
                "aggiunto che non ci sia nel modello."
            ),
            modello="realism",
            prompt_tecnico=(
                "interior architectural photograph of the reference space, "
                "natural window light, matte surfaces, no furniture that is "
                "not present in the reference, " + _INVARIANZA
            ),
            grana_predefinita=grana.FINE,
        ),
    )
}


def preset(identificativo: str) -> Preset:
    """Il preset chiesto, o l'elenco di quelli che esistono."""
    try:
        return PRESET[identificativo]
    except KeyError:
        raise PresetSconosciuto(
            f"Non esiste un preset chiamato \"{identificativo}\".",
            f"I preset inclusi sono: {', '.join(sorted(PRESET))}.",
        ) from None


def elenco() -> list[Preset]:
    return [PRESET[k] for k in sorted(PRESET)]
