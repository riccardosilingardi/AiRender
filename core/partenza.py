"""Da dove viene una vista: Allplan, oppure un'immagine caricata («Da un'immagine»).

Una vista catturata dalla palette e' una vista di Allplan: shaded, con le
ombre, e su di lei vale il controllo di idoneita'. Un'immagine caricata dallo
Studio con «Da un'immagine» e' un'altra cosa, e lo dice un file accanto,
`<nome della vista>.partenza.json`, scritto quando la si carica:

- «render»: un render gia' fatto (di AIRENDER o di un altro programma). Si
  salta Genera: diventa subito un risultato da cui partono Cambia, Ritocca,
  Popola, Finale e Regola;
- «foto»: una foto del luogo o di una stanza. Si cambia il look da Genera
  (con la regola delle foto); come un render, e' anche subito un risultato,
  e da Ritocca se ne cambiano arredi e materiali. Come luogo di «Inserisci
  nel contesto» non passa di qui: va fra i contesti;
- «schizzo»: uno schizzo a mano o la foto di un plastico. Passa da Genera
  come una vista, con la regola dello schizzo.

Su un'immagine caricata il controllo di idoneita' guarda solo la misura:
ombre, toni e sfondo uniforme sono regole di una vista di Allplan, e uno
schizzo sembrerebbe sempre un wireframe.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import blocchi, coda as modulo_coda
from .errori import ErroreAirender

SUFFISSO = ".partenza.json"

RENDER = "render"
FOTO = "foto"
SCHIZZO = "schizzo"
TIPI = (RENDER, FOTO, SCHIZZO)
# Quelli che diventano subito anche un risultato (coda.importa_immagine).
SUBITO_RISULTATO = (RENDER, FOTO)

NOMI = {
    RENDER: "Render già fatto",
    FOTO: "Foto",
    SCHIZZO: "Schizzo o plastico",
}

# La regola che parte con Genera per ogni tipo, finche' l'utente non sceglie
# altro. Un render gia' fatto si tratta come una foto in cui si tiene tutto:
# cambia solo luce, colori e materiali.
PARTENZA_PREDEFINITA = {
    RENDER: blocchi.PARTENZA_FOTO_ARREDI,
    FOTO: blocchi.PARTENZA_FOTO,
    SCHIZZO: blocchi.PARTENZA_SCHIZZO,
}
# Le regole fra cui si sceglie in Genera per ogni tipo.
PARTENZE_POSSIBILI = {
    RENDER: (blocchi.PARTENZA_FOTO_ARREDI, blocchi.PARTENZA_FOTO),
    FOTO: (blocchi.PARTENZA_FOTO, blocchi.PARTENZA_FOTO_ARREDI),
    SCHIZZO: (blocchi.PARTENZA_SCHIZZO,),
}


class TipoNonValido(ErroreAirender):
    """Un tipo d'immagine che lo Studio non conosce."""


def controlla_tipo(tipo: object) -> str:
    if tipo not in TIPI:
        raise TipoNonValido(
            f"\"{tipo}\" non e' un tipo d'immagine che lo Studio conosce.",
            "Scegli fra render gia' fatto, foto, schizzo o plastico.",
        )
    return str(tipo)


def percorso(vista: Path) -> Path:
    """Il file accanto alla vista, con lo stesso nome."""
    vista = Path(vista)
    return vista.with_name(vista.stem + SUFFISSO)


def scrivi(vista: Path, tipo: str, nome_originale: str = "") -> dict:
    dati = {"tipo": controlla_tipo(tipo), "nome_originale": nome_originale or ""}
    modulo_coda.scrivi_json(percorso(vista), dati)
    return dati


def leggi(vista: Path) -> str | None:
    """Il tipo dell'immagine caricata, o None per una vista di Allplan (o un file che non si legge)."""
    try:
        dati = json.loads(percorso(vista).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    tipo = dati.get("tipo") if isinstance(dati, dict) else None
    return tipo if tipo in TIPI else None


def partenza_per(vista: Path, scelta: str | None) -> str:
    """La regola che parte da questa vista: quella scelta, se vale per il tipo, o la predefinita.

    Da una vista di Allplan la partenza e' sempre la vista: una pagina
    vecchia che non la manda non cambia niente. Da un'immagine caricata una
    partenza che non vale per il suo tipo si rifiuta invece di cambiarla in
    silenzio.
    """
    tipo = leggi(vista)
    if tipo is None:
        if scelta and scelta != blocchi.VISTA_ALLPLAN:
            raise TipoNonValido(
                "Questa e' una vista di Allplan: la regola delle foto e degli schizzi non vale.",
                "Ricarica lo Studio: la regola torna quella della vista.",
            )
        return blocchi.VISTA_ALLPLAN
    if not scelta or scelta == blocchi.VISTA_ALLPLAN:
        return PARTENZA_PREDEFINITA[tipo]
    if scelta not in PARTENZE_POSSIBILI[tipo]:
        raise TipoNonValido(
            f"Per {NOMI[tipo].lower()} la regola «{blocchi.NOMI_PARTENZE.get(scelta, scelta)}» non vale.",
            "Ricarica lo Studio e scegli di nuovo cosa tenere.",
        )
    return scelta
