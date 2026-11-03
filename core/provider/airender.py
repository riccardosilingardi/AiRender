"""I crediti AIRENDER: lo stesso Comfy Router, passando dal server AIRENDER.

Il cliente non ha un account Comfy. Il plugin manda la vista al server
AIRENDER (funzioni Netlify, server/ in questo repository) con il codice
licenza; il server controlla piano e saldo, la passa al Comfy Router con la
chiave di Riccardo e scala il credito solo se il render torna con
un'immagine. Il protocollo e' quello del Router (coda, stato, risultato),
quindi tutto il resto e' ProviderComfy: cambiano indirizzo, intestazioni e
le frasi degli errori.

Solo i modelli del listino (core/config.py, LISTINO) partono coi crediti; gli
altri restano per chi usa la propria chiave Comfy (--provider comfy).
"""

from __future__ import annotations

from .. import config, immagine as modulo_immagine, licenza as modulo_licenza
from ..errori import ChiaveMancante, ErroreProvider
from .comfy import ProviderComfy


class ProviderAirender(ProviderComfy):
    nome = "airender"
    destinazione = "server AIRENDER (Netlify) → Comfy Router (api.comfy.org)"

    def __init__(self, chiave: str | None = None, canale: str = "plugin", **parametri) -> None:
        super().__init__(chiave=chiave or modulo_licenza.leggi() or "", **parametri)
        self.canale = canale
        self.base = f"{modulo_licenza.server()}/v2/models"

    def cosa_manca(self, modello: str) -> str | None:
        if modello not in config.LISTINO["pesi"]:
            return (
                f"il modello {modello} non e' compreso nei crediti AIRENDER: parte solo "
                "con la tua chiave Comfy (--provider comfy)."
            )
        return super().cosa_manca(modello)

    def _intestazioni_chiave(self) -> dict:
        return modulo_licenza.intestazioni(self.chiave, self.canale)

    def _dettagli_risultato(self, risposte: dict) -> dict:
        dettagli = {}
        if risposte.get("x-airender-render-scalati") is not None:
            dettagli["render_scalati"] = risposte["x-airender-render-scalati"]
        if risposte.get("x-airender-saldo") is not None:
            dettagli["saldo_dopo"] = risposte["x-airender-saldo"]
        return dettagli

    def _assicura_chiave(self) -> None:
        if not self.chiave:
            raise ChiaveMancante(
                "Non hai ancora incollato il codice licenza AIRENDER: senza, non parte niente.",
                "Incolla il codice ricevuto per email con: python -m core.cli --licenza "
                "AIR-XXXX-XXXX-XXXX-XXXX. Se non hai una licenza, la compri dalla pagina "
                f"dei prezzi ({modulo_licenza.server()}).",
            )

    def _assicura_peso(self, dati: bytes) -> None:
        peso = modulo_immagine.dimensione_mb(dati)
        if peso > config.SERVER_INVIO_MASSIMO_MB:
            raise ErroreProvider(
                f"La vista di partenza pesa {peso:.1f} MB e il server AIRENDER ne "
                f"riceve al massimo {config.SERVER_INVIO_MASSIMO_MB}.",
                "Salva di nuovo la vista da Allplan a una risoluzione piu' bassa "
                "(1920x1080 basta per un render a 2K).",
            )

    def _errore(self, stato: int, risposte: dict, corpo: object, modello: str) -> ErroreProvider:
        if isinstance(corpo, dict) and isinstance(corpo.get("error"), dict) and corpo.get("cosa_fare"):
            return modulo_licenza.errore_del_server(stato, corpo)
        return super()._errore(stato, risposte, corpo, modello)
