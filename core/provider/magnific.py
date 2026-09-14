"""Magnific: l'unico provider implementato.

Scelto nel PRD perche' e' a consumo senza abbonamento, ha un riferimento
strutturale con forza regolabile, la generazione fissa e l'editing per
regione. La chiave e' del cliente: sta in una variabile d'ambiente, mai nel
repository.

Endpoint e nomi dei campi vengono dalla documentazione pubblica dell'API
(Mystic per la generazione, ideogram-image-edit per la modifica di una
regione). NON SONO STATI ESEGUITI: in questa sessione non c'e' una chiave.
Vedi la sezione NON VERIFICATO del PRD.
"""

from __future__ import annotations

import base64
import os
import time

from .. import config, immagine as modulo_immagine
from ..errori import ChiaveMancante, ErroreProvider, errore_da_stato_http
from ..ricetta import Ricetta, impronta
from .base import Provider, RichiestaGenerazione, RichiestaRegione, Risultato
from .trasporto import Trasporto, TrasportoHTTP

BASE = "https://api.magnific.com/v1/ai"
INTESTAZIONE_CHIAVE = "x-magnific-api-key"
VARIABILI_CHIAVE = ("MAGNIFIC_API_KEY", "AIRENDER_MAGNIFIC_API_KEY")

# I formati che l'API accetta, col loro rapporto. Non sono soglie nostre: sono
# l'elenco chiuso del servizio.
FORMATI = {
    "square_1_1": 1 / 1,  # numero-non-configurabile: definizione del formato
    "classic_4_3": 4 / 3,  # numero-non-configurabile: definizione del formato
    "traditional_3_4": 3 / 4,  # numero-non-configurabile: definizione del formato
    "standard_3_2": 3 / 2,  # numero-non-configurabile: definizione del formato
    "portrait_2_3": 2 / 3,  # numero-non-configurabile: definizione del formato
    "widescreen_16_9": 16 / 9,  # numero-non-configurabile: definizione del formato
    "social_story_9_16": 9 / 16,  # numero-non-configurabile: definizione del formato
}

STATI_FINITI_BENE = ("COMPLETED",)
STATI_FINITI_MALE = ("FAILED", "ERROR", "CANCELLED")


def chiave_da_ambiente() -> str | None:
    """La chiave dell'utente, presa dall'ambiente. Mai da un file del repo."""
    for nome in VARIABILI_CHIAVE:
        valore = os.environ.get(nome, "").strip()
        if valore:
            return valore
    return None


def formato_piu_vicino(larghezza: int, altezza: int) -> str:
    """Il formato del servizio che deforma meno la vista di partenza.

    Chiedere un formato diverso da quello della vista significa consegnare un
    edificio schiacciato: e' geometria inventata, anche se nessuno la chiama
    cosi'.
    """
    rapporto = larghezza / altezza
    return min(FORMATI, key=lambda nome: abs(FORMATI[nome] - rapporto))


class ProviderMagnific(Provider):
    nome = "magnific"
    destinazione = "Magnific (api.magnific.com)"

    def __init__(
        self,
        chiave: str | None = None,
        trasporto: Trasporto | None = None,
        attesa=time.sleep,
        orologio=time.monotonic,
    ) -> None:
        self.chiave = chiave or chiave_da_ambiente()
        self.trasporto = trasporto or TrasportoHTTP()
        self._attesa = attesa
        self._orologio = orologio

    # --- cose che il prodotto chiede ----------------------------------------

    def genera(self, richiesta: RichiestaGenerazione) -> Risultato:
        self._assicura_chiave()
        self._assicura_forza(richiesta.forza_struttura)
        self._assicura_peso(richiesta.immagine, "la vista di partenza")

        aspetto = richiesta.aspetto or formato_piu_vicino(
            *modulo_immagine.dimensioni(richiesta.immagine)
        )
        ricetta = Ricetta(
            provider=self.nome,
            modello=richiesta.modello,
            preset=richiesta.preset,
            preset_versione=richiesta.preset_versione,
            prompt=richiesta.prompt,
            testo_utente=richiesta.testo_utente,
            grana=richiesta.grana,
            dettaglio_grana=richiesta.dettaglio_grana,
            forza_struttura=richiesta.forza_struttura,
            risoluzione=richiesta.risoluzione,
            aspetto=aspetto,
            generazione_fissa=richiesta.generazione_fissa,
            impronta_sorgente=impronta(richiesta.immagine),
            seme=richiesta.seme,
        )
        return self._esegui_mystic(ricetta, richiesta.immagine)

    def riesegui(self, ricetta: Ricetta, immagine: bytes) -> Risultato:
        """Rifa' la stessa immagine. Il seme da solo non basterebbe.

        Si controlla anche che la vista di partenza sia quella di allora: con
        un'altra vista gli stessi parametri danno un'altra immagine, e
        chiamarla riesecuzione sarebbe falso.
        """
        self._assicura_chiave()
        if impronta(immagine) != ricetta.impronta_sorgente:
            raise ErroreProvider(
                "La vista di partenza non e' la stessa con cui era stato fatto "
                "questo livello.",
                "Ripesca la vista originale, oppure rigenera il livello da capo: "
                "con un'altra vista gli stessi parametri danno un'altra immagine.",
            )
        fissata = Ricetta.da_dizionario({**ricetta.a_dizionario(), "generazione_fissa": True})
        return self._esegui_mystic(fissata, immagine)

    def modifica_regione(self, richiesta: RichiestaRegione) -> Risultato:
        """Cambia solo la regione della maschera.

        Trappola nota: il riempimento mascherato non ricalcola riflessi e luce
        di rimbalzo. Per un cambio radicale di materiale serve rigenerare la
        base, non ritoccarla; l'avviso viaggia col risultato.
        """
        self._assicura_chiave()
        self._assicura_peso(richiesta.immagine, "il render da ritoccare")
        self._assicura_peso(richiesta.maschera, "la maschera")

        maschera = modulo_immagine.sfuma_maschera(richiesta.maschera)
        corpo = {
            "prompt": richiesta.prompt,
            "image": _in_base64(richiesta.immagine),
            "mask": _in_base64(maschera),
        }
        if richiesta.seme is not None:
            corpo["seed"] = richiesta.seme

        risposta = self._posta(f"{BASE}/ideogram-image-edit", corpo)
        dati, formato = self._attendi_immagine(f"{BASE}/ideogram-image-edit", risposta)

        ricetta = Ricetta(
            provider=self.nome,
            modello=richiesta.modello or "ideogram-image-edit",
            preset=richiesta.preset,
            preset_versione=richiesta.preset_versione,
            prompt=richiesta.prompt,
            testo_utente="",
            grana=richiesta.grana,
            dettaglio_grana=richiesta.dettaglio_grana,
            forza_struttura=config.FORZA_STRUTTURA_MASSIMA,
            risoluzione="",
            aspetto="",
            generazione_fissa=False,
            impronta_sorgente=impronta(richiesta.immagine),
            seme=richiesta.seme,
        )
        return Risultato(
            immagine=dati,
            formato=formato,
            ricetta=ricetta,
            scostamento_geometria=None,
            avvisi=[
                "Ritocco mascherato: riflessi e luce di rimbalzo del resto "
                "dell'immagine non sono ricalcolati. Se il materiale cambia "
                "radicalmente, rigenera la base invece di ritoccare.",
                "Scostamento della geometria non misurato.",
            ],
        )

    # --- dentro ---------------------------------------------------------------

    def _esegui_mystic(self, ricetta: Ricetta, sorgente: bytes) -> Risultato:
        corpo = {
            "prompt": ricetta.prompt,
            "model": ricetta.modello,
            "resolution": ricetta.risoluzione,
            "aspect_ratio": ricetta.aspetto,
            "structure_reference": _in_base64(sorgente),
            "structure_strength": ricetta.forza_struttura,
            "creative_detailing": ricetta.dettaglio_grana,
            "engine": "automatic",
            "fixed_generation": ricetta.generazione_fissa,
            "filter_nsfw": True,
        }
        risposta = self._posta(f"{BASE}/mystic", corpo)
        dati, formato = self._attendi_immagine(f"{BASE}/mystic", risposta)
        return Risultato(
            immagine=dati,
            formato=formato,
            ricetta=ricetta,
            scostamento_geometria=None,
            avvisi=[
                "Scostamento della geometria non misurato: il motore non lo "
                "sa ancora calcolare. Guarda gli spigoli a occhio.",
                "La forza della struttura "
                f"({config.costante('FORZA_STRUTTURA_PREDEFINITA').etichetta()}) "
                "non e' ancora stata misurata.",
            ],
        )

    def _assicura_chiave(self) -> None:
        if not self.chiave:
            raise ChiaveMancante(
                "Manca la chiave API di Magnific: senza, non parte niente.",
                "Metti la tua chiave nella variabile d'ambiente "
                f"{VARIABILI_CHIAVE[0]}. La chiave e' tua, resta sulla tua "
                "macchina e non entra mai nel plugin.",
            )

    def _assicura_forza(self, forza: int) -> None:
        if not (
            config.FORZA_STRUTTURA_MINIMA <= forza <= config.FORZA_STRUTTURA_MASSIMA
        ):
            raise ErroreProvider(
                f"La forza della struttura chiesta ({forza}) e' fuori dai "
                "limiti del servizio.",
                f"Usa un valore fra {config.FORZA_STRUTTURA_MINIMA} e "
                f"{config.FORZA_STRUTTURA_MASSIMA}. Piu' alta e' la forza, piu' "
                "il render resta attaccato alla vista disegnata.",
            )

    def _assicura_peso(self, dati: bytes, cosa: str) -> None:
        peso = modulo_immagine.dimensione_mb(dati)
        if peso > config.INVIO_MASSIMO_MB:
            raise ErroreProvider(
                f"{cosa.capitalize()} pesa {peso:.1f} MB e il servizio accetta "
                f"al massimo {config.INVIO_MASSIMO_MB} MB.",
                "Salva di nuovo la vista da Allplan a una risoluzione piu' bassa.",
            )

    def _intestazioni(self) -> dict:
        return {INTESTAZIONE_CHIAVE: self.chiave}

    def _posta(self, url: str, corpo: dict) -> dict:
        stato, risposta = self.trasporto.posta(url, self._intestazioni(), corpo)
        return self._corpo_o_errore(stato, risposta)

    def _corpo_o_errore(self, stato: int, risposta: object) -> dict:
        if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
            raise errore_da_stato_http(self.destinazione, stato, _testo(risposta))
        if not isinstance(risposta, dict):
            raise ErroreProvider(
                f"{self.destinazione} ha risposto qualcosa che non so leggere.",
                "Riprova fra qualche minuto. Se si ripete, e' cambiata l'API del "
                "servizio e va aggiornato il file core/provider/magnific.py.",
                stato=stato,
            )
        return risposta.get("data", risposta)

    def _attendi_immagine(self, url_lavoro: str, primo: dict) -> tuple[bytes, str]:
        """Aspetta che il lavoro finisca, poi scarica l'immagine."""
        corpo = primo
        identificativo = corpo.get("task_id") or corpo.get("id")
        scadenza = self._orologio() + config.ATTESA_MASSIMA_SECONDI

        while True:
            stato_lavoro = str(corpo.get("status", "")).upper()
            if stato_lavoro in STATI_FINITI_BENE:
                return self._scarica_prodotto(corpo)
            if stato_lavoro in STATI_FINITI_MALE:
                raise ErroreProvider(
                    f"{self.destinazione} ha interrotto la generazione "
                    f"(stato {stato_lavoro.lower()}).",
                    "Riprova, magari con un preset diverso. Se si ripete sempre "
                    "sulla stessa vista, e' la vista a non piacergli.",
                )
            if not identificativo:
                raise ErroreProvider(
                    f"{self.destinazione} non ha detto che lavoro ha aperto.",
                    "Riprova. Se si ripete, e' cambiata l'API del servizio e va "
                    "aggiornato il file core/provider/magnific.py.",
                )
            if self._orologio() >= scadenza:
                raise ErroreProvider(
                    f"{self.destinazione} non ha finito entro "
                    f"{config.ATTESA_MASSIMA_SECONDI} secondi.",
                    "Il lavoro puo' essere ancora in corso sul servizio: "
                    "controlla il cruscotto del tuo account prima di rilanciare, "
                    "cosi' non lo paghi due volte.",
                )
            self._attesa(config.INTERVALLO_ATTESA_SECONDI)
            stato, risposta = self.trasporto.leggi(
                f"{url_lavoro}/{identificativo}", self._intestazioni()
            )
            corpo = self._corpo_o_errore(stato, risposta)

    def _scarica_prodotto(self, corpo: dict) -> tuple[bytes, str]:
        prodotti = corpo.get("generated") or corpo.get("images") or []
        if not prodotti:
            raise ErroreProvider(
                f"{self.destinazione} dice di aver finito ma non ha allegato "
                "nessuna immagine.",
                "Riprova. Se si ripete, e' cambiata l'API del servizio e va "
                "aggiornato il file core/provider/magnific.py.",
            )
        primo = prodotti[0]
        indirizzo = primo if isinstance(primo, str) else primo.get("url", "")
        if not indirizzo:
            raise ErroreProvider(
                f"{self.destinazione} ha risposto senza l'indirizzo dell'immagine.",
                "Riprova fra qualche minuto.",
            )
        dati = self.trasporto.scarica(indirizzo)
        formato = "jpg" if ".jpg" in indirizzo.lower() or ".jpeg" in indirizzo.lower() else "png"
        return dati, formato


def _in_base64(dati: bytes) -> str:
    return base64.b64encode(dati).decode("ascii")


def _testo(risposta: object) -> str:
    if isinstance(risposta, str):
        return risposta
    if isinstance(risposta, dict):
        for chiave in ("message", "error", "detail", "title"):
            if chiave in risposta:
                return str(risposta[chiave])
    return ""
