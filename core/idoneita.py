"""Il primo rifiuto: una vista che non serve a niente si scarta subito.

Il riferimento strutturale legge profondita' e spigoli dall'immagine. Da un
wireframe non li legge, da una vista a colori piatti nemmeno. Mandarla lo
stesso significa pagare una chiamata per ricevere un edificio diverso.

Il rifiuto dice cosa salvare, non "immagine non valida".
"""

from __future__ import annotations

from dataclasses import dataclass

from . import config
from .errori import ImmagineNonIdonea
from .immagine import Statistiche

TROPPO_PICCOLA = "troppo_piccola"
SEMBRA_WIREFRAME = "sembra_wireframe"
TROPPO_PIATTA = "troppo_piatta"

# La scena di blocchi.PIANTA, scritta qui per non legare l'idoneita' ai blocchi.
SCENA_DISEGNO = "pianta"

_COME_SI_SALVA = (
    "In Allplan: metti la vista in shaded con le ombre attive e lo sfondo "
    "neutro, poi \"Salva contenuto finestra come immagine\" con il lato lungo "
    f"ad almeno {config.LATO_MINIMO_PX} px."
)


@dataclass(frozen=True)
class Esito:
    """Il giudizio sulla vista di partenza, con i numeri che l'hanno prodotto."""

    idonea: bool
    motivo: str | None
    fatto: str
    cosa_fare: str
    statistiche: Statistiche


def valuta(statistiche: Statistiche, scena: str | None = None) -> Esito:
    """Giudica la vista. Non solleva: chi chiama decide se fermarsi.

    Una pianta (scena «pianta») e' fatta proprio di linee su fondo chiaro, o
    di colori piatti: per lei contano solo i pixel. Il controllo del
    wireframe e della vista piatta vale per una vista in prospettiva.

    L'ordine conta. Una vista a colori piatti ha poche tonalita' quanto un
    wireframe: le separa il contrasto. Il wireframe e' fatto di linee nere su
    fondo chiaro e ha uno scarto di luminanza alto; la vista piatta non ce
    l'ha. Quindi si guarda prima la piattezza, altrimenti a chi ha solo
    dimenticato le ombre diremmo che ha salvato un wireframe.
    """
    if statistiche.lato_lungo < config.LATO_MINIMO_PX:
        return Esito(
            idonea=False,
            motivo=TROPPO_PICCOLA,
            fatto=(
                f"Questa vista e' {statistiche.larghezza}x{statistiche.altezza} px: "
                f"troppo piccola. Sotto {config.LATO_MINIMO_PX} px di lato lungo il "
                "controllo della struttura ha troppo poco a cui aggrapparsi."
            ),
            cosa_fare=_COME_SI_SALVA,
            statistiche=statistiche,
        )

    if scena == SCENA_DISEGNO:
        return Esito(
            idonea=True,
            motivo=None,
            fatto=(
                f"Pianta {statistiche.larghezza}x{statistiche.altezza} px: per un "
                "disegno dall'alto contano solo i pixel, linee e colori piatti vanno bene."
            ),
            cosa_fare="",
            statistiche=statistiche,
        )

    if statistiche.deviazione_luminanza < config.DEVIAZIONE_LUMINANZA_MINIMA:
        return Esito(
            idonea=False,
            motivo=TROPPO_PIATTA,
            fatto=(
                "Questa vista e' troppo piatta: le superfici hanno colori pieni "
                "senza ombre, quindi non c'e' profondita' da leggere."
            ),
            cosa_fare=(
                "Attiva le ombre nella vista shaded e salvala di nuovo. " + _COME_SI_SALVA
            ),
            statistiche=statistiche,
        )

    sfondo_dominante = statistiche.quota_sfondo > config.QUOTA_SFONDO_MASSIMA
    pochi_toni = statistiche.toni_distinti < config.TONI_DISTINTI_MINIMI
    if sfondo_dominante and pochi_toni:
        return Esito(
            idonea=False,
            motivo=SEMBRA_WIREFRAME,
            fatto=(
                "Questa sembra una vista wireframe: "
                f"{statistiche.quota_sfondo:.0%} dell'immagine e' sullo stesso tono e "
                f"ci sono solo {statistiche.toni_distinti} livelli di grigio. "
                "Serve una vista shaded con le ombre attive."
            ),
            cosa_fare=_COME_SI_SALVA,
            statistiche=statistiche,
        )

    return Esito(
        idonea=True,
        motivo=None,
        fatto=(
            f"Vista {statistiche.larghezza}x{statistiche.altezza} px, "
            f"{statistiche.toni_distinti} livelli di grigio."
        ),
        cosa_fare="",
        statistiche=statistiche,
    )


def valuta_immagine(statistiche: Statistiche) -> Esito:
    """Un'immagine caricata con «Da un'immagine» (core/partenza.py): conta solo la misura.

    Ombre, toni e sfondo uniforme dicono se una vista di Allplan e' stata
    salvata bene; una foto o un render li hanno per forza, e uno schizzo a
    matita sembrerebbe sempre un wireframe. Resta il lato minimo: sotto, il
    modello ha troppo poco da cui partire.
    """
    if statistiche.lato_lungo < config.LATO_MINIMO_PX:
        return Esito(
            idonea=False,
            motivo=TROPPO_PICCOLA,
            fatto=(
                f"Questa immagine e' {statistiche.larghezza}x{statistiche.altezza} px: "
                f"troppo piccola. Sotto {config.LATO_MINIMO_PX} px di lato lungo il "
                "modello ha troppo poco da cui partire."
            ),
            cosa_fare=f"Carica la stessa immagine piu' grande, con il lato lungo ad almeno {config.LATO_MINIMO_PX} px.",
            statistiche=statistiche,
        )
    return Esito(
        idonea=True,
        motivo=None,
        fatto=f"Immagine {statistiche.larghezza}x{statistiche.altezza} px.",
        cosa_fare="",
        statistiche=statistiche,
    )


def assicura_idonea(statistiche: Statistiche, scena: str | None = None) -> Esito:
    """Come `valuta`, ma si ferma se la vista non va bene."""
    esito = valuta(statistiche, scena)
    if not esito.idonea:
        raise ImmagineNonIdonea(esito.fatto, esito.cosa_fare, esito.motivo or "")
    return esito
