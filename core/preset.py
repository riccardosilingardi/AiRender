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

# Il modello di ogni servizio. Nano Banana 2 su Comfy Router e' una scelta,
# non una misura: il 2026-10-27 la stessa vista vera e' passata da FLUX.1
# Kontext Pro e da Nano Banana 2. Riccardo ha giudicato a occhio che tutti e
# due tengono i tramezzi, e che Nano Banana rende meglio ombre e grana; tiene
# anche le proporzioni della vista (1376x768 contro 1392x752 di Kontext).
# Un'immagine sola: il confronto va ripetuto su altre viste.
MODELLI_PREDEFINITI = {
    "comfy": "vertexai/gemini-3.1-flash-image",
    "magnific": "realism",
}

# v2 (2026-10-21): oltre al prompt, il preset sceglie il modello di Comfy Router.
# v3 (2026-10-27): il modello di Comfy Router passa da FLUX.1 Kontext Pro a
# Nano Banana 2. Una ricetta v2 si riesegue col modello che ha salvato.
_VERSIONE = "3"


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
