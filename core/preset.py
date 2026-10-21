"""I preset inclusi nel pacchetto.

Un preset e' un prompt tecnico con un modello e dei valori di partenza, piu'
una versione: senza versione una pila di livelli non si rifa' uguale, perche'
noi stessi cambieremo questi testi.

Le miniature generate (DESIGN.md, schermata 2) arrivano quando ci sara' una
palette: qui ci sono solo i dati che le produrranno.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import config, grana
from .errori import PresetSconosciuto
from .lessico import controlla_etichetta

# Il modello di ogni servizio. FLUX.1 Kontext Pro su Comfy Router e' una
# scelta, non una misura: e' il primo modello di modifica che la sonda prova.
# Lo confronto con un secondo modello (scripts/confronta_modelli.py) decide
# se resta.
MODELLI_PREDEFINITI = {
    "comfy": "bfl/flux-kontext-pro",
    "magnific": "realism",
}

# v2 (2026-10-21): oltre al prompt, il preset sceglie il modello di Comfy Router.
_VERSIONE = "2"


@dataclass(frozen=True)
class Preset:
    """Uno stile della griglia."""

    identificativo: str
    nome: str
    descrizione: str
    prompt_tecnico: str
    modelli: dict = field(default_factory=lambda: dict(MODELLI_PREDEFINITI))
    grana_predefinita: str = grana.MEDIA
    forza_struttura: int = config.FORZA_STRUTTURA_PREDEFINITA
    versione: str = "1"

    def modello_per(self, provider: str) -> str:
        """Il modello che questo preset usa con quel servizio."""
        try:
            return self.modelli[provider]
        except KeyError:
            raise PresetSconosciuto(
                f"Il preset {self.identificativo} non dice quale modello usare "
                f"con {provider}.",
                "Scegli uno dei servizi per cui ha un modello: "
                f"{', '.join(sorted(self.modelli))}.",
            ) from None

    def __post_init__(self) -> None:
        if not self.modelli:
            raise ValueError(f"il preset {self.identificativo} non ha nessun modello")
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
            prompt_tecnico=(
                "architectural visualization of the reference building, "
                "photographic realism, neutral overcast daylight, plausible "
                "construction materials, " + _INVARIANZA
            ),
            versione=_VERSIONE,
        ),
        Preset(
            identificativo="esterno-giorno",
            nome="Esterno giorno",
            descrizione=(
                "Sole basso, ombre lunghe, cielo leggero. Per una facciata da "
                "mostrare al cliente."
            ),
            prompt_tecnico=(
                "exterior architectural photograph of the reference building, "
                "late afternoon sunlight, long soft shadows, clear sky, "
                "context vegetation kept minimal, " + _INVARIANZA
            ),
            versione=_VERSIONE,
        ),
        Preset(
            identificativo="interno-neutro",
            nome="Interno neutro",
            descrizione=(
                "Luce naturale da finestra, superfici opache, nessun arredo "
                "aggiunto che non ci sia nel modello."
            ),
            prompt_tecnico=(
                "interior architectural photograph of the reference space, "
                "natural window light, matte surfaces, no furniture that is "
                "not present in the reference, " + _INVARIANZA
            ),
            grana_predefinita=grana.FINE,
            versione=_VERSIONE,
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
