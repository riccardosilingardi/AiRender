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

import dataclasses

from .. import config, immagine as modulo_immagine, licenza as modulo_licenza
from ..errori import ChiaveMancante, ErroreProvider
from .base import RichiestaGenerazione
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

    def _senza_immagine(self, errore: ErroreProvider, dettagli: dict) -> ErroreProvider:
        # Il server rimborsa i render vuoti fino a un tetto nelle 24 ore
        # (LISTINO["rimborsi_senza_immagine_24h"]); oltre li scala. Si dice
        # quale dei due e' successo, mai un "forse".
        scalati = str(dettagli.get("render_scalati", "0"))
        tetto = config.LISTINO["rimborsi_senza_immagine_24h"]
        if scalati in ("", "0"):
            return ErroreProvider(
                "Nano Banana ha chiuso il lavoro senza un'immagine. Il credito non e' stato scalato.",
                "Riprova, magari cambiando il testo del prompt: un rifiuto di solito "
                "dipende da cosa chiede il testo o da cosa c'e' nella vista.",
            )
        return ErroreProvider(
            f"Nano Banana ha chiuso il lavoro senza un'immagine e questa volta il render "
            f"e' stato scalato ({scalati}): nelle ultime 24 ore questa licenza ha gia' avuto "
            f"{tetto} render vuoti rimborsati, il massimo.",
            "Cambia il testo del prompt o la vista prima di riprovare; se pensi che sia un "
            "errore di AIRENDER, scrivici e controlliamo.",
        )

    def _assicura_chiave(self) -> None:
        if not self.chiave:
            raise ChiaveMancante(
                "Non hai ancora incollato il codice licenza AIRENDER: senza, non parte niente.",
                "Incolla il codice ricevuto per email con: python -m core.cli --licenza "
                "AIR-XXXX-XXXX-XXXX-XXXX. Se non hai una licenza, la compri dalla pagina "
                f"dei prezzi ({modulo_licenza.server()}).",
            )

    def _limite_mb(self) -> float:
        return config.SERVER_INVIO_MASSIMO_MB

    def _genera(self, richiesta: RichiestaGenerazione, avvisi_in_piu: list[str]):
        richiesta, alleggerite = self._alleggerisci_richiesta(richiesta)
        richiesta, avviso = self._sta_nel_server(richiesta)
        return super()._genera(richiesta, avvisi_in_piu=[*avvisi_in_piu, *alleggerite, *([avviso] if avviso else [])])

    def _sta_nel_server(self, richiesta: RichiestaGenerazione) -> tuple[RichiestaGenerazione, str | None]:
        """Vista e immagini in piu' devono stare insieme sotto il limite del server.

        Il controllo per immagine (SERVER_INVIO_MASSIMO_MB) non basta: con
        Nano Banana Pro, una vista e tre riferimenti passano uno per uno e
        insieme superano i 6 MB di Netlify. Si rimpiccioliscono le immagini in
        piu', mai la vista; se non basta, si ferma prima dell'invio, quando
        nessun credito e' stato riservato.
        """
        def totale(immagini) -> float:
            return sum(len(d) for d in immagini) * 4 / 3 / (1024 * 1024)  # numero-non-configurabile: base64 e megabyte

        limite = config.SERVER_CORPO_MASSIMO_MB
        extra = richiesta.immagini_in_piu
        if totale((richiesta.immagine, *extra)) <= limite:
            return richiesta, None
        for lato in config.SERVER_RIDUZIONE_LATI_PX:
            extra = tuple(modulo_immagine.riduci_lato(d, lato) for d in richiesta.immagini_in_piu)
            if totale((richiesta.immagine, *extra)) <= limite:
                avviso = (
                    f"Le immagini in piu' (riferimenti, materiali) sono state rimpicciolite a "
                    f"{lato} px di lato lungo: insieme alla vista superavano il limite del "
                    f"server AIRENDER ({limite} MB per invio). La vista e' partita intera."
                )
                return dataclasses.replace(richiesta, immagini_in_piu=extra), avviso
        raise ErroreProvider(
            f"Vista e immagini in piu' pesano insieme {totale((richiesta.immagine, *extra)):.1f} MB "
            f"anche rimpicciolite, e il server AIRENDER ne riceve al massimo {limite} per invio. "
            "Non e' partito niente e non e' stato scalato credito.",
            "Togli un riferimento, oppure salva di nuovo la vista da Allplan a una "
            "risoluzione piu' bassa (1920x1080 basta per un render a 2K).",
        )

    def _errore(self, stato: int, risposte: dict, corpo: object, modello: str) -> ErroreProvider:
        if isinstance(corpo, dict) and isinstance(corpo.get("error"), dict) and corpo.get("cosa_fare"):
            return modulo_licenza.errore_del_server(stato, corpo)
        return super()._errore(stato, risposte, corpo, modello)
