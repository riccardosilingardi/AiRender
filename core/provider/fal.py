"""FLUX «Geometria rigida» su fal.ai: solo per l'uso personale, con la chiave FAL_KEY.

Perche' c'e' (2026-11-15, decisione di Riccardo): nella prova del 15/11 FLUX.1
dev con img2img dalla vista e ControlNet Union Pro (spigoli + profondita') ha
ritrovato il 96-98 % degli spigoli dello scatto Allplan, Nano Banana 2 il
79-95 %. Nano Banana 2 resta il predefinito; questo e' un modello in piu' che
compare nello Studio solo se sul PC c'e' la variabile d'ambiente FAL_KEY.

Cosa NON e':

- non passa dai crediti AIRENDER e non e' in vendita: FLUX.1 dev ha una
  licenza non commerciale di Black Forest Labs, e i Termini di fal chiedono
  un'autorizzazione scritta per le app integrate (§6(e)(ix)). Nessuna delle
  due cose e' stata chiesta;
- non e' in Europa: fal lavora negli Stati Uniti, e lo Studio lo scrive
  prima dell'invio (regola 5 di CLAUDE.md).

Come parla con fal (documentazione della coda di fal, la stessa che usa il
client fal_client della prova): POST https://queue.fal.run/<modello> con la
chiave nell'intestazione «Authorization: Key ...»; la risposta da' status_url
e response_url; si legge lo stato fino a COMPLETED e poi il risultato.
`sync_mode` fa tornare l'immagine come data URI, senza lasciarla nello
storico delle richieste; X-Fal-Store-IO: 0 chiede a fal di non conservare
ingressi e uscite (ESPLORAZIONE-FAL.md, 2026-11-15).

MAI ESEGUITO DA QUESTO FILE: la prova del 15/11 e' passata da fal_client e
dallo stesso corpo. Il primo render dallo Studio e' la verifica, e l'avviso
prima dell'invio lo dice.

Solo libreria standard, come comfy.py: niente fal_client da installare
nell'interprete di Allplan.
"""

from __future__ import annotations

import base64
import os
import random
import time
from dataclasses import replace

from .. import config, immagine as modulo_immagine, mappe as modulo_mappe
from ..errori import ChiaveMancante, ErroreProvider, errore_da_stato_http
from ..ricetta import Ricetta, impronta
from .base import IN_LAVORAZIONE, INVIATO, Provider, RichiestaGenerazione, RichiestaRegione, Risultato
from .trasporto import ErroreRete, TrasportoConIntestazioni, TrasportoHTTP

CODA = "https://queue.fal.run"
MODELLO = "fal-ai/flux-general/image-to-image"
MODELLI = (MODELLO,)
VARIABILI_CHIAVE = ("FAL_KEY",)
# Il ControlNet della prova del 2026-11-15: un'unione che sa leggere sia gli
# spigoli (canny) sia la profondita' (depth) nella stessa chiamata.
CONTROLNET = "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro"
# Il limite di FLUX.1 dev per una stessa generazione riproducibile: il seme e'
# un intero a 32 bit.
SEME_MASSIMO = 2**32 - 1  # numero-non-configurabile: intero senza segno a 32 bit
STATO_FINITO = "COMPLETED"
STATI_IN_CORSO = ("IN_QUEUE", "IN_PROGRESS")
STATI_PASSEGGERI = (429, 500, 502, 503, 504)  # numero-non-configurabile: codici HTTP

VERIFICATO_IL = ""  # vuoto: mai una chiamata vera da questo file (vedi sopra)


def chiave_da_ambiente() -> str | None:
    """La chiave fal di chi lavora, dall'ambiente. Mai da un file del repo."""
    for nome in VARIABILI_CHIAVE:
        valore = os.environ.get(nome, "").strip()
        if valore:
            return valore
    return None


def data_uri(dati: bytes) -> str:
    tipo = "image/png" if dati.startswith(b"\x89PNG") else "image/jpeg"
    return f"data:{tipo};base64,{base64.b64encode(dati).decode('ascii')}"


def prompt_per_flux(prompt: str) -> str:
    """Il prompt senza la regola delle mappe scritta per Nano Banana.

    Quella regola («Image 2 is an edge map...») serve a un modello che vede le
    mappe come immagini; FLUX le riceve nel ControlNet e non legge numeri di
    immagine. Con solo vista e mappe, la prima mappa e' l'immagine 2.
    """
    regola = f"\n\n{modulo_mappe.regola(2)}"
    return prompt[: -len(regola)] if prompt.endswith(regola) else prompt


def misura_render(vista: bytes) -> tuple[int, int]:
    return modulo_immagine.misura_multipla(vista, config.FAL_LATO_PX, config.FAL_MULTIPLO_PX)


def costo_stimato(misura: tuple[int, int]) -> float:
    """Dollari dal listino fal per un render di questa misura. Una stima, non una misura."""
    return misura[0] * misura[1] / 1_000_000 * config.FAL_DOLLARI_PER_MP  # numero-non-configurabile: pixel in un megapixel


def corpo(richiesta: RichiestaGenerazione, seme: int) -> tuple[dict, tuple[int, int]]:
    """Il JSON per fal-ai/flux-general/image-to-image, con vista e mappe alla stessa misura."""
    spigoli, profondita = richiesta.immagini_in_piu
    misura = misura_render(richiesta.immagine)
    vista = modulo_immagine.a_misura(richiesta.immagine, misura, "JPEG")
    controlli = [
        {"control_image_url": data_uri(modulo_immagine.a_misura(spigoli, misura)), "control_mode": "canny",
         "conditioning_scale": config.FAL_CONTROLLO_SPIGOLI, "end_percentage": config.FAL_CONTROLLO_FINE},
        {"control_image_url": data_uri(modulo_immagine.a_misura(profondita, misura)), "control_mode": "depth",
         "conditioning_scale": config.FAL_CONTROLLO_PROFONDITA, "end_percentage": config.FAL_CONTROLLO_FINE},
    ]
    return {
        "image_url": data_uri(vista),
        "prompt": prompt_per_flux(richiesta.prompt),
        "strength": config.FAL_FORZA_IMG2IMG,
        "num_inference_steps": config.FAL_PASSI,
        "guidance_scale": config.FAL_GUIDA,
        "seed": seme,
        "image_size": {"width": misura[0], "height": misura[1]},
        "output_format": "png",
        "num_images": 1,
        "sync_mode": True,
        "enable_safety_checker": False,
        "controlnet_unions": [{"path": CONTROLNET, "controls": controlli}],
    }, misura


def _senza_immagini(valore: object) -> object:
    """Il corpo da scrivere nella ricetta: i data URI diventano una scritta corta."""
    if isinstance(valore, dict):
        return {k: _senza_immagini(v) for k, v in valore.items()}
    if isinstance(valore, list):
        return [_senza_immagini(v) for v in valore]
    if isinstance(valore, str) and valore.startswith("data:"):
        return "(immagine, non salvata nella ricetta)"
    return valore


class ProviderFal(Provider):
    nome = "fal"
    destinazione = "fal.ai (queue.fal.run, Stati Uniti)"
    # La forza dell'img2img c'e' ma non e' la «forza della struttura» da 0 a
    # 100 del prodotto: sta in config.py e nella ricetta, non a schermo.
    usa_forza_struttura = False

    def __init__(self, chiave: str | None = None, trasporto: TrasportoConIntestazioni | None = None,
                 attesa=time.sleep, orologio=time.monotonic, nuovo_seme=None) -> None:
        self.chiave = chiave or chiave_da_ambiente()
        self.trasporto = trasporto or TrasportoHTTP()
        self._attesa = attesa
        self._orologio = orologio
        self._nuovo_seme = nuovo_seme or (lambda: random.randint(0, SEME_MASSIMO))

    # --- quello che lo Studio legge prima dell'invio -------------------------

    def destinazione_per(self, modello: str) -> str:
        return f"{self.destinazione} → FLUX.1 dev + ControlNet"

    def cosa_manca(self, modello: str) -> str | None:
        if modello not in MODELLI:
            return f"{modello} non e' un modello di fal che AIRENDER sa usare."
        if not self.chiave:
            return (f"su questo PC non c'e' la chiave fal (variabile d'ambiente {VARIABILI_CHIAVE[0]}): "
                    "l'invio vero si fermerebbe prima di partire.")
        return None

    def avviso(self, modello: str) -> str | None:
        return ("Solo per il tuo uso: FLUX.1 dev ha una licenza non commerciale e passa dal tuo conto fal, "
                "non dai crediti AIRENDER. Le immagini vanno negli Stati Uniti. "
                "Mai provato dallo Studio: il primo render è la prova.")

    def accetta_piu_immagini(self, modello: str) -> bool:
        # Riferimenti, materiali e Rif. non hanno un ingresso in questa ricetta.
        return False

    def accetta_mappe(self, modello: str) -> bool:
        return modello in MODELLI

    def vuole_mappe(self, modello: str) -> bool:
        return modello in MODELLI

    def controlla_prima_dell_invio(self, modello: str, immagine: bytes) -> None:
        self._assicura_chiave()
        if modello not in MODELLI:
            raise ErroreProvider(f"{modello} non e' un modello di fal che AIRENDER sa usare.",
                                 "Scegli FLUX.1 dev · Geometria rigida, oppure Nano Banana 2.")
        self._assicura_peso(immagine)

    # --- le tre cose del prodotto --------------------------------------------

    def genera(self, richiesta: RichiestaGenerazione) -> Risultato:
        return self._genera(richiesta, [])

    def riesegui(self, ricetta: Ricetta, immagine: bytes) -> Risultato:
        raise ErroreProvider(
            "FLUX «Geometria rigida» non si riesegue da sola: servono anche le mappe della vista.",
            "Rifallo da Studio · Genera con la stessa vista: il seme e' nella ricetta, "
            "ma le mappe si calcolano di nuovo nella pagina.",
        )

    def modifica_regione(self, richiesta: RichiestaRegione) -> Risultato:
        raise ErroreProvider(
            "FLUX «Geometria rigida» rifà tutta l'immagine dalla vista: non ritocca un'area.",
            "Per Ritocca e Cambia usa Nano Banana 2.",
        )

    # --- dentro --------------------------------------------------------------

    def _genera(self, richiesta: RichiestaGenerazione, avvisi_in_piu: list[str]) -> Risultato:
        self.controlla_prima_dell_invio(richiesta.modello, richiesta.immagine)
        if len(richiesta.immagini_in_piu) != len(modulo_mappe.MAPPE):
            raise ErroreProvider(
                f"FLUX «Geometria rigida» parte con la vista e le {len(modulo_mappe.MAPPE)} mappe "
                f"(spigoli e profondità): la richiesta porta {1 + len(richiesta.immagini_in_piu)} immagini. "
                "Non ho inviato niente.",
                "Spunta «Tieni la geometria» e togli riferimenti, materiali con foto e Rif.",
            )
        seme = richiesta.seme if richiesta.seme is not None else self._nuovo_seme()
        pulita = replace(richiesta, immagine=modulo_immagine.senza_metadati(richiesta.immagine))
        da_mandare, misura = corpo(pulita, seme)
        uscita, dettagli = self._esegui(richiesta.modello, da_mandare)
        dati = self._immagine(uscita)
        dati = modulo_immagine.marca_generata(dati)  # AI Act, art. 50.2
        seme_usato = uscita.get("seed", seme) if isinstance(uscita, dict) else seme
        ricetta = Ricetta(
            provider=self.nome,
            modello=richiesta.modello,
            preset=richiesta.preset,
            preset_versione=richiesta.preset_versione,
            prompt=da_mandare["prompt"],
            testo_utente=richiesta.testo_utente,
            grana=richiesta.grana,
            dettaglio_grana=None,
            forza_struttura=None,
            risoluzione=f"{misura[0]}x{misura[1]}",
            aspetto="",
            generazione_fissa=True,
            impronta_sorgente=impronta(richiesta.immagine),
            seme=seme_usato,
            parametri={
                "corpo": _senza_immagini(da_mandare),
                "immagini_in_piu": [impronta(d) for d in richiesta.immagini_in_piu],
                "costo_listino_dollari": round(costo_stimato(misura), 3),  # numero-non-configurabile: millesimi di dollaro
                "schema_verificato_il": VERIFICATO_IL,
                **dettagli,
            },
        )
        avvisi = [
            "Scostamento della geometria non misurato dal motore: guarda la % di spigoli e la linea del prima/dopo.",
            f"Costo dal listino fal: circa {costo_stimato(misura):.2f} $ sul tuo conto fal ".replace(".", ",")
            + f"({misura[0]}x{misura[1]} px). Non misurato da AIRENDER.",
            *avvisi_in_piu,
        ]
        if isinstance(uscita, dict) and any(uscita.get("has_nsfw_concepts") or []):
            avvisi.append("fal ha segnato l'immagine come non adatta: se è tutta nera, l'ha oscurata il suo filtro.")
        return Risultato(immagine=dati, formato="png" if dati.startswith(b"\x89PNG") else "jpg",
                         ricetta=ricetta, scostamento_geometria=None, avvisi=avvisi)

    def _intestazioni(self) -> dict:
        return {"Authorization": f"Key {self.chiave}", "Accept": "application/json", "X-Fal-Store-IO": "0"}

    def _esegui(self, modello: str, da_mandare: dict) -> tuple[object, dict]:
        """La coda di fal: un invio solo (fal non ha una chiave di idempotenza), poi stato e risultato."""
        try:
            stato, _risposte, inviata = self.trasporto.chiama("POST", f"{CODA}/{modello}", self._intestazioni(), da_mandare)
        except ErroreRete as errore:
            raise ErroreProvider(
                errore.fatto,
                errore.cosa_fare + " Prima di rilanciare guarda le richieste sul tuo conto fal "
                "(fal.ai/dashboard): se il lavoro e' partito, rilanciando lo paghi due volte.",
            ) from None
        if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
            raise self._errore(stato, inviata)
        if not isinstance(inviata, dict) or not inviata.get("request_id") or not inviata.get("status_url"):
            raise ErroreProvider(f"{self.destinazione} non ha detto che lavoro ha aperto.",
                                 "Riprova. Se si ripete, e' cambiata l'API della coda di fal: va aggiornato "
                                 "core/provider/fal.py.", stato=stato)
        dettagli = {"richiesta_id": inviata["request_id"]}
        risultato_url = inviata.get("response_url") or f"{CODA}/{modello}/requests/{inviata['request_id']}"
        scadenza = self._orologio() + config.ATTESA_MASSIMA_SECONDI
        stato_fal = str(inviata.get("status") or "IN_QUEUE")
        while stato_fal != STATO_FINITO:
            if stato_fal not in STATI_IN_CORSO:
                raise ErroreProvider(f"fal ha chiuso il lavoro con lo stato {stato_fal}, senza un'immagine.",
                                     "Riprova; se si ripete, guarda la richiesta sul tuo conto fal.")
            self._segnala(IN_LAVORAZIONE if stato_fal == "IN_PROGRESS" else INVIATO)
            if self._orologio() >= scadenza:
                raise ErroreProvider(
                    f"fal non ha finito entro {config.ATTESA_MASSIMA_SECONDI} secondi.",
                    f"Il lavoro {inviata['request_id']} puo' finire lo stesso: guardalo sul tuo conto fal.")
            self._attesa(config.INTERVALLO_ATTESA_SECONDI)
            stato_fal = self._leggi_stato(str(inviata["status_url"]))
        stato, _risposte, uscita = self._leggi(risultato_url)
        if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
            raise self._errore(stato, uscita)
        return uscita, dettagli

    def _leggi(self, url: str) -> tuple[int, dict, object]:
        """Una lettura (stato o risultato), ripetuta sugli errori passeggeri: leggere non spende."""
        for tentativo in range(1, config.TENTATIVI_INVIO_MASSIMI + 1):
            try:
                stato, risposte, corpo_letto = self.trasporto.chiama("GET", url, self._intestazioni())
            except ErroreRete:
                if tentativo == config.TENTATIVI_INVIO_MASSIMI:
                    raise
                self._attesa(config.INTERVALLO_ATTESA_SECONDI)
                continue
            if stato in STATI_PASSEGGERI and tentativo < config.TENTATIVI_INVIO_MASSIMI:
                self._attesa(config.INTERVALLO_ATTESA_SECONDI)
                continue
            return stato, risposte, corpo_letto
        raise AssertionError("irraggiungibile")  # pragma: no cover

    def _leggi_stato(self, url: str) -> str:
        stato, _risposte, corpo_letto = self._leggi(url)
        if stato >= 400:  # numero-non-configurabile: confine HTTP fra ok ed errore
            raise self._errore(stato, corpo_letto)
        return str(corpo_letto.get("status") if isinstance(corpo_letto, dict) else "")

    def _immagine(self, uscita: object) -> bytes:
        try:
            valore = str(uscita["images"][0]["url"])
        except (KeyError, IndexError, TypeError):
            raise ErroreProvider("fal ha chiuso il lavoro senza un'immagine nel risultato.",
                                 "Riprova. Se si ripete, e' cambiato lo schema del modello.") from None
        if valore.startswith("data:"):
            return base64.b64decode(valore.split(",", 1)[1])
        return self.trasporto.scarica(valore)

    def _errore(self, stato: int, corpo_letto: object) -> ErroreProvider:
        if stato in (401, 403):  # numero-non-configurabile: codici HTTP di chiave rifiutata
            return ErroreProvider(
                "fal ha rifiutato la chiave.",
                f"Controlla la variabile d'ambiente {VARIABILI_CHIAVE[0]} di Windows (la chiave si crea su "
                "fal.ai/dashboard/keys), poi chiudi e riapri lo Studio.", stato=stato)
        if stato == 402 or (isinstance(corpo_letto, (dict, str)) and "balance" in str(corpo_letto).lower()):  # numero-non-configurabile: codice HTTP di credito finito
            return ErroreProvider(
                "Il conto fal non ha abbastanza credito per questo render.",
                "Ricarica su fal.ai/dashboard/billing, poi riprova. Non e' partito niente.", stato=stato)
        return errore_da_stato_http(self.destinazione, stato, str(corpo_letto)[:500])  # numero-non-configurabile: quanto testo dell'errore mostrare

    def _assicura_chiave(self) -> None:
        if not self.chiave:
            raise ChiaveMancante(
                f"Su questo PC non c'e' la chiave fal (variabile d'ambiente {VARIABILI_CHIAVE[0]}).",
                "Crea una chiave su fal.ai/dashboard/keys, mettila nella variabile d'ambiente "
                f"{VARIABILI_CHIAVE[0]} di Windows e riapri lo Studio.",
            )

    def _assicura_peso(self, dati: bytes) -> None:
        peso = modulo_immagine.dimensione_mb(dati)
        if peso > config.INVIO_MASSIMO_MB:
            raise ErroreProvider(
                f"La vista pesa {peso:.1f} MB, piu' dei {config.INVIO_MASSIMO_MB} MB che AIRENDER manda in un invio.",
                "Salva di nuovo la vista da Allplan a una risoluzione piu' bassa (1920x1080 basta).",
            )
