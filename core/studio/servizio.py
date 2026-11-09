"""Quello che lo Studio sa fare, senza HTTP.

Ogni metodo pubblico prende e restituisce dizionari semplici, quelli che il
server manda alla pagina come JSON. Un errore e' sempre un ErroreAirender,
con il fatto e il gesto successivo: il server lo passa alla pagina com'e'.

La cartella dello Studio e' la cartella delle viste: la palette ci salva le
viste, la coda ci tiene `lavori/`. Lo Studio la legge e ci scrive lavori, e
non tocca nient'altro.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .. import aree as modulo_aree, blocchi, config, coda as modulo_coda, immagine as modulo_immagine
from .. import contesto as modulo_contesto
from .. import licenza as modulo_licenza
from .. import materiali as modulo_materiali
from .. import passi as modulo_passi
from .. import esporta as modulo_esporta, preset_utente
from .. import regola as modulo_regola
from .. import video as modulo_video
from .. import licenza as modulo_licenza
from .. import provider as registro
from ..errori import ErroreAirender, FileNonTrovato
from ..idoneita import valuta
from ..preset import MODELLI_PREDEFINITI
from ..provider import comfy, geometria as modulo_geometria
from ..provider.base import Provider
from ..ricetta import Ricetta, impronta
from . import miniature as modulo_miniature


class RichiestaStudioNonValida(ErroreAirender):
    """La pagina ha chiesto qualcosa che non esiste o non torna."""


ESTENSIONI_VISTA = (".png", ".jpg", ".jpeg")
_BYTE_PER_MB = 1024 * 1024  # numero-non-configurabile: definizione di MB
# Esporta per il cliente: dentro la cartella delle viste, accanto ai lavori.
CARTELLA_ESPORTATI = "esportati"
SUFFISSO_CAMERA = ".camera.json"

# Gli identificativi che nuovo_identificativo() di core/coda.py produce.
# Tutto il resto si rifiuta prima di diventare un percorso.
_ID_LAVORO = re.compile(r"^\d{8}-\d{6}-\d{6}-[0-9a-f]{4}$")

# Le cartelle della coda nell'ordine in cui un lavoro le attraversa.
_CARTELLE_LAVORO = (
    modulo_coda.IN_ATTESA_DIR,
    modulo_coda.IN_CORSO_DIR,
    modulo_coda.FATTO_DIR,
    modulo_coda.ERRORE_DIR,
    modulo_coda.ANNULLATO_DIR,
)
STATI_ATTIVI = (modulo_coda.IN_CODA, modulo_coda.INVIATO, modulo_coda.IN_LAVORAZIONE)


@dataclass(frozen=True)
class Modello:
    """Un modello del Router come lo vede l'utente."""

    identificativo: str
    nome: str
    fornitore: str
    # Il costo per generazione, se misurato. None si scrive "non misurato".
    costo_crediti: float | None = None
    costo_misurato_il: str = ""
    # Il gruppo in cui lo Studio lo mostra e una riga su a cosa serve. La riga
    # e' un giudizio (SCELTA), non un confronto misurato: a schermo lo si dice.
    categoria: str = ""
    spiega: str = ""


# I gruppi della scelta del modello, nell'ordine in cui compaiono.
CATEGORIE_MODELLI = (
    ("consigliati", "Consigliati", "I modelli con cui lo Studio è stato provato di più."),
    ("alternative", "Altri modelli", "Altri modelli che ricevono più immagini: utili per un secondo parere sullo stesso render."),
    ("una_immagine", "Una sola immagine", "Ricevono solo la vista o il render: niente riferimenti, foto dei materiali o Rif."),
)

# L'ordine qui non e' quello a schermo: lo Studio li mostra per categoria.
MODELLI = (
    Modello(
        MODELLI_PREDEFINITI["comfy"], "Nano Banana 2", "Google",
        costo_crediti=config.COSTO_NANO_BANANA_2_CREDITI, costo_misurato_il="27/10/2026",
        categoria="consigliati", spiega="Veloce, tiene gli spigoli, ombre e grana buone. Il predefinito.",
    ),
    # Secondo in elenco: i test lo usano come «il modello a una sola immagine».
    Modello("bfl/flux-kontext-pro", "FLUX.1 Kontext Pro", "Black Forest Labs",
            categoria="una_immagine", spiega="Modifica mirata della sola vista."),
    # Costo non ancora misurato: lo dira' il primo render.
    Modello("vertexai/gemini-3-pro-image", "Nano Banana Pro", "Google",
            categoria="consigliati", spiega="Più dettaglio e testi leggibili, fino a 4K. Più lento."),
    # Aggiunti il 2026-11-01 dalla documentazione del Router, senza sonda:
    # selezionabili, con l'avviso «non ancora provato» prima di ogni invio.
    Modello("openai/gpt-image-2", "GPT Image 2", "OpenAI",
            categoria="alternative", spiega="Interpreta più liberamente: adatto a illustrazioni e schizzi."),
    Modello("byteplus/seedream-5-0-260128", "Seedream 5.0", "ByteDance",
            categoria="alternative", spiega="Fotorealismo marcato, fino a 4K."),
)
# «Finale»: non e' un modello di render, non sta fra le schede. Costo «a
# misura e ingrandimento» secondo il Router, nessuna stima prima dell'invio.
MODELLO_FINALE = Modello(comfy.MODELLO_FINALE, "Magnific Precision V2", "Freepik",
                         categoria="finale", spiega="Ingrandisce e aggiunge dettaglio, senza cambiare il disegno.")
NOMI_TIPI_FINALE = {"foto": "Foto", "illustrazione": "Illustrazione"}

# Scritti a schermo e non selezionabili: oggi nessuno, restano per i prossimi.
MODELLI_NON_PROVATI: tuple[str, ...] = ()

# Come lo Studio chiama quello che una resa spegne.
_NOMI_SPENTI = {
    "materiali": "materiali a parole", "look": "look fotografico", "luce": "luce",
    "cielo": "cielo", "fuori": "fuori dalle finestre", "intorno": "intorno",
    "verde": "verde", "sfondo": "sfondo", "persone": "persone", "qualita": "qualità",
}


def _rese() -> list[dict]:
    """Le cinque rese, tutte con il loro blocco dalla bozza 7, e cosa spegne ognuna."""
    return [
        {"id": resa, "nome": nome, "attivo": True, "nota": "", "origine": config.SCELTA,
         "spegne": sorted(blocchi.SPENTI_DA_RESA[resa]),
         "spegne_testo": ", ".join(_NOMI_SPENTI[a] for a in _NOMI_SPENTI if a in blocchi.SPENTI_DA_RESA[resa])}
        for resa, nome in blocchi.NOMI_RESE.items()
    ]

_TITOLI_ASSI = {
    "fedelta": "Fedeltà al disegno",
    "look": "Look fotografico",
    "luce": "Ora / Luce",
    "cielo": "Cielo e stagione",
    "fuori": "Fuori dalle finestre",
    "arredo": "Arredo",
    "sfondo": "Sfondo",
    "intorno": "Intorno all'edificio",
    "verde": "Verde",
    "persone": "Persone",
    "qualita": "Qualità",
}


def _adesso() -> datetime:
    return datetime.now(timezone.utc)


def _numero(valore: float, cifre: int = 2) -> str:
    """Un numero con la virgola, come si scrive in italiano."""
    return f"{valore:.{cifre}f}".replace(".", ",")


def _errore_dict(errore: ErroreAirender) -> dict:
    return {"fatto": errore.fatto, "cosa_fare": errore.cosa_fare}


def apri_nel_sistema(percorso: Path) -> None:
    """Apre una cartella con l'esplora file del sistema."""
    if sys.platform.startswith("win"):
        os.startfile(str(percorso))  # pylint: disable=no-member
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(percorso)])  # pylint: disable=consider-using-with
    else:
        subprocess.Popen(["xdg-open", str(percorso)])  # pylint: disable=consider-using-with


class Studio:
    """Lo Studio su una cartella delle viste."""

    def __init__(
        self,
        cartella: Path,
        provider: str = registro.PREDEFINITO,
        crea_provider: Callable[[str], Provider] = registro.crea,
        coda_attiva: Callable[[], bool] = lambda: False,
        apri: Callable[[Path], None] = apri_nel_sistema,
        adesso: Callable[[], datetime] = _adesso,
        cartella_miniature: Path = modulo_miniature.CARTELLA,
        leggi_saldo: Callable[..., dict] = modulo_licenza.saldo,
    ) -> None:
        self.cartella = Path(cartella).resolve()
        self.cartella.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self._crea_provider = crea_provider
        self._coda_attiva = coda_attiva
        self._apri = apri
        self._adesso = adesso
        self.cartella_miniature = Path(cartella_miniature)
        self._leggi_saldo = leggi_saldo
        self.percorsi = modulo_coda.cartelle(self.cartella)
        self._prompt_completo: bool | None = None
        # Il server risponde a piu' richieste insieme: l'albero dei passi lo
        # allinea e lo scrive una richiesta alla volta.
        self._blocco_albero = threading.Lock()
        # Regola: il render gia' rimpicciolito per l'anteprima, uno solo
        # (identificativo, byte). I cursori lo chiedono a ogni movimento.
        self._base_anteprima: tuple[str, bytes] | None = None
        self._dimensioni_anteprima: tuple[int, int] = (0, 0)

    # --- in testa --------------------------------------------------------

    def stato_studio(self) -> dict:
        viste = self.elenco_viste()
        return {
            "cartella": str(self.cartella),
            "coda_attiva": self._coda_attiva(),
            "provider": self.provider,
            "viste": viste,
            "lavori_attivi": self.lavori_attivi(),
            "modello_predefinito": MODELLI[0].identificativo,
            "regola": {
                "massimo": config.REGOLA_CURSORE_MASSIMO,
                "curva_punti": config.REGOLA_CURVA_PUNTI_MASSIMI,
                "cursori": [{"id": nome, "nome": etichetta} for nome, etichetta in modulo_regola.CURSORI],
            },
            "ritocco": {
                "modo": config.RITOCCO_MODO_AREE,
                "modo_nome": modulo_aree.NOMI_MODI[config.RITOCCO_MODO_AREE],
                "origine": config.costante("RITOCCO_MODO_AREE").origine,
                "pennello": config.PENNELLO_SPESSORE,
                "pennelli": list(config.PENNELLO_SPESSORI),
            },
        }

    # --- licenza e saldo -------------------------------------------------

    def _chiave_comfy(self) -> bool:
        return comfy.chiave_da_ambiente() is not None

    def licenza(self) -> dict:
        """La scheda Licenza: codice salvato o no, e il saldo detto dal server AIRENDER.

        Senza codice non si chiama il server. Se il server non risponde la
        scheda lo dice e il codice resta salvato: non e' il codice a essere
        sbagliato.
        """
        codice = modulo_licenza.leggi()
        stato = {
            "presente": bool(codice),
            "ultime_cifre": modulo_licenza.formatta(codice)[-4:] if codice and modulo_licenza.valido(codice) else "",  # numero-non-configurabile: le ultime cifre del codice, come le mostra il server
            "server": modulo_licenza.server(),
            "provider": self.provider,
            "chiave_comfy": self._chiave_comfy(),
            "saldo": None,
            "errore": None,
        }
        if codice:
            try:
                stato["saldo"] = self._leggi_saldo(codice)
            except ErroreAirender as errore:
                stato["errore"] = {"fatto": errore.fatto, "cosa_fare": errore.cosa_fare}
        return stato

    def attiva_licenza(self, dati: dict) -> dict:
        """Controlla il codice col server e solo se va lo salva su questo PC.

        Da qui i render dello Studio passano dai crediti AIRENDER, senza
        riavviare: ogni lavoro nuovo porta il provider con se'.
        """
        codice = str(dati.get("codice") or "").strip()
        if not modulo_licenza.valido(codice):
            raise RichiestaStudioNonValida(
                "Questo non sembra un codice licenza AIRENDER.",
                "Il codice ha la forma AIR-XXXX-XXXX-XXXX-XXXX: ricopialo dall'email "
                "che hai ricevuto dopo l'acquisto.",
            )
        codice = modulo_licenza.formatta(codice)
        saldo = self._leggi_saldo(codice)  # un rifiuto del server esce da qui, e non si salva niente
        modulo_licenza.salva(codice)
        self.provider = registro.ProviderAirender.nome
        # Il piano del codice nuovo decide se il prompt si vede (prompt_completo).
        self._prompt_completo = bool((saldo.get("funzioni") or {}).get("prompt_completo"))
        return {**self.licenza(), "saldo": saldo, "errore": None}

    def usa_servizio(self, dati: dict) -> dict:
        """Crediti AIRENDER o chiave Comfy propria, per questo Studio aperto."""
        scelto = str(dati.get("provider") or "")
        if scelto == comfy.ProviderComfy.nome:
            if not self._chiave_comfy():
                raise RichiestaStudioNonValida(
                    "Non trovo una chiave Comfy su questo PC.",
                    "Crea una chiave nel tuo workspace Comfy, mettila nella variabile "
                    f"d'ambiente {comfy.VARIABILI_CHIAVE[0]} di Windows e riapri lo Studio.",
                )
        elif scelto == registro.ProviderAirender.nome:
            if not modulo_licenza.leggi():
                raise RichiestaStudioNonValida(
                    "Non hai ancora inserito un codice licenza AIRENDER.",
                    "Incollalo qui sopra e premi Attiva.",
                )
        else:
            raise RichiestaStudioNonValida(
                "Lo Studio non conosce questo servizio.", "Ricarica la pagina dello Studio.")
        self.provider = scelto
        return self.licenza()

    # --- viste -----------------------------------------------------------

    def elenco_viste(self) -> list[dict]:
        """Le viste della cartella, la piu' recente per prima."""
        viste = [
            p for p in self.cartella.iterdir()
            if p.is_file() and p.suffix.lower() in ESTENSIONI_VISTA
            and not p.name.startswith(".")
        ]
        viste.sort(key=lambda p: (p.stat().st_mtime, p.name), reverse=True)
        return [
            {
                "nome": p.name,
                "modificata_il": datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds"),
            }
            for p in viste
        ]

    def percorso_vista(self, nome: str) -> Path:
        """Il file di una vista della cartella. Solo un nome, mai un percorso."""
        if (
            not nome or "/" in nome or "\\" in nome or nome.startswith(".")
            or Path(nome).suffix.lower() not in ESTENSIONI_VISTA
        ):
            raise RichiestaStudioNonValida(
                f"\"{nome}\" non e' il nome di una vista.",
                "Scegli una vista dall'elenco, o caricane una con Usa un'altra vista.",
            )
        percorso = self.cartella / nome
        if not percorso.is_file():
            raise FileNonTrovato(
                f"Nella cartella {self.cartella} non c'e' piu' la vista {nome}.",
                "Scegli un'altra vista dall'elenco, o catturala di nuovo dalla palette.",
            )
        return percorso

    def descrivi_vista(self, nome: str) -> dict:
        """La vista con il suo esito di idoneita', come la mostra Genera."""
        percorso = self.percorso_vista(nome)
        descrizione = {"nome": nome, "percorso": str(percorso), "camera": self._camera(percorso)}
        try:
            dati = modulo_immagine.leggi(percorso)
            statistiche = modulo_immagine.misura(dati)
            quota = modulo_immagine.quota_colorata(dati)
        except ErroreAirender as errore:
            return {**descrizione, "leggibile": False, "idonea": False, **_errore_dict(errore)}
        esito = valuta(statistiche)
        return {
            **descrizione,
            "leggibile": True,
            "idonea": esito.idonea,
            "motivo": esito.motivo,
            "fatto": esito.fatto,
            "cosa_fare": esito.cosa_fare,
            "larghezza": statistiche.larghezza,
            "altezza": statistiche.altezza,
            "toni": statistiche.toni_distinti,
            "quota_sfondo": round(statistiche.quota_sfondo, 3),  # numero-non-configurabile: cifre per la pagina
            "quota_colorata": round(quota, 3),  # numero-non-configurabile: cifre per la pagina
            "colori_come_materiali": quota >= config.QUOTA_COLORATA_AVVISO,
        }

    @staticmethod
    def _camera(percorso: Path) -> str | None:
        """Cosa dice il file della camera salvato dalla palette accanto alla vista."""
        file_camera = percorso.with_name(percorso.stem + SUFFISSO_CAMERA)
        try:
            dati = json.loads(file_camera.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(dati, dict) or "prospettiva_centrale" not in dati:
            return None
        return "Prospettiva centrale" if dati["prospettiva_centrale"] else "Vista parallela"

    def carica_vista(self, dati: bytes, nome_originale: str = "") -> dict:
        """Salva nella cartella una vista scelta dall'utente, con un nome nuovo."""
        massimo = config.STUDIO_CARICAMENTO_MASSIMO_MB
        if len(dati) > massimo * _BYTE_PER_MB:
            raise RichiestaStudioNonValida(
                f"Il file pesa {_numero(len(dati) / _BYTE_PER_MB, 1)} MB, lo Studio ne accetta {massimo}.",
                "Salva la vista da Allplan a una risoluzione piu' bassa.",
            )
        modulo_immagine.misura(dati)  # solleva se non e' un'immagine
        estensione = ".jpg" if comfy.tipo_mime(dati) == "image/jpeg" else ".png"
        if comfy.tipo_mime(dati) not in ("image/png", "image/jpeg"):
            raise RichiestaStudioNonValida(
                "Lo Studio accetta viste in PNG o JPEG.",
                "Salva la vista da Allplan in PNG.",
            )
        istante = self._adesso().astimezone()
        nome = f"vista-{istante:%Y%m%d-%H%M%S}{estensione}"
        indice = 1
        while (self.cartella / nome).exists():
            indice += 1
            nome = f"vista-{istante:%Y%m%d-%H%M%S}-{indice}{estensione}"
        modulo_coda.scrivi_atomico(self.cartella / nome, dati)
        return {"nome": nome, "da": nome_originale}

    # --- immagine di riferimento per lo stile -----------------------------

    def carica_contesto(self, dati: bytes, nome_originale: str = "") -> dict:
        """Salva l'immagine del contesto nella cartella dei contesti, chiamata con la sua impronta.

        Come un riferimento: peso massimo quello che si manda a Comfy Router,
        solo JPEG o PNG. Lo Studio non scarica immagini da mappe: il contesto
        lo porta l'utente.
        """
        massimo = config.COMFY_INVIO_MASSIMO_MB
        if len(dati) > massimo * _BYTE_PER_MB:
            raise RichiestaStudioNonValida(
                f"L'immagine del contesto pesa {_numero(len(dati) / _BYTE_PER_MB, 1)} MB, ne mandiamo al massimo {massimo}.",
                "Riducila o salvala in JPEG, poi caricala di nuovo.",
            )
        tipo = comfy.tipo_mime(dati)
        if tipo not in ("image/png", "image/jpeg"):
            raise RichiestaStudioNonValida(
                "L'immagine del contesto dev'essere un JPEG o un PNG.",
                "Salvala in JPEG o PNG (uno screenshot va bene), poi caricala di nuovo.",
            )
        larghezza, altezza = modulo_immagine.dimensioni(dati)  # solleva se non si legge
        estensione = ".jpg" if tipo == "image/jpeg" else ".png"
        nome = f"ctx-{impronta(dati)[:16]}{estensione}"  # numero-non-configurabile: 64 bit di impronta, come i riferimenti
        cartella = modulo_contesto.cartella_contesti(self.cartella)
        cartella.mkdir(parents=True, exist_ok=True)
        if not (cartella / nome).exists():
            modulo_coda.scrivi_atomico(cartella / nome, dati)
        return {"nome": nome, "da": nome_originale, "larghezza": larghezza,
                "altezza": altezza, "impronta": impronta(dati)}

    def percorso_contesto(self, nome: str) -> Path:
        """Il file di un contesto. Solo un nome della cartella dei contesti, mai un percorso."""
        if not re.fullmatch(r"ctx-[0-9a-f]{16}\.(jpg|png)", nome or ""):
            raise RichiestaStudioNonValida(
                f"\"{nome}\" non e' il nome di un'immagine del contesto.",
                "Caricala di nuovo in «Fotoinserimento».",
            )
        percorso = modulo_contesto.cartella_contesti(self.cartella) / nome
        if not percorso.is_file():
            raise FileNonTrovato(
                f"L'immagine del contesto {nome} non c'e' piu' nella cartella dei contesti.",
                "Caricala di nuovo, oppure togli il contesto.",
            )
        return percorso

    def _contesto_scelto(self, dati: dict) -> modulo_contesto.Contesto | None:
        """Il contesto della richiesta dello Studio, o None. Il file e' solo un nome della cartella."""
        voce = dati.get("contesto")
        if not voce:
            return None
        if not isinstance(voce, dict):
            raise RichiestaStudioNonValida("Il contesto non e' arrivato per intero.", "Ricarica lo Studio.")
        if dati.get("riferimento"):
            raise RichiestaStudioNonValida(
                "Il riferimento per lo stile e il contesto non partono insieme: sarebbero tre immagini.",
                "Togli il riferimento per lo stile, oppure togli il contesto.",
            )
        percorso = self.percorso_contesto(str(voce.get("nome") or ""))
        try:
            return modulo_contesto.Contesto.da_dizionario({**voce, "file": str(percorso)})
        except modulo_contesto.ContestoNonValido as errore:
            raise RichiestaStudioNonValida(errore.fatto, errore.cosa_fare) from None

    def carica_riferimento(self, dati: bytes, nome_originale: str = "") -> dict:
        """Salva un'immagine di riferimento nella cartella dei riferimenti, chiamata con la sua impronta.

        Il peso massimo e' quello che si manda a Comfy Router: un riferimento
        piu' pesante sarebbe rifiutato al momento dell'invio, dopo il clic.
        """
        massimo = config.COMFY_INVIO_MASSIMO_MB
        if len(dati) > massimo * _BYTE_PER_MB:
            raise RichiestaStudioNonValida(
                f"Il riferimento pesa {_numero(len(dati) / _BYTE_PER_MB, 1)} MB, ne mandiamo al massimo {massimo}.",
                "Riducilo o salvalo in JPEG, poi caricalo di nuovo.",
            )
        tipo = comfy.tipo_mime(dati)
        if tipo not in ("image/png", "image/jpeg"):
            raise RichiestaStudioNonValida(
                "Il riferimento per lo stile dev'essere un JPEG o un PNG.",
                "Salvalo in JPEG o PNG, poi caricalo di nuovo.",
            )
        larghezza, altezza = modulo_immagine.dimensioni(dati)  # solleva se non si legge
        estensione = ".jpg" if tipo == "image/jpeg" else ".png"
        nome = f"rif-{impronta(dati)[:16]}{estensione}"  # numero-non-configurabile: 64 bit di impronta bastano a non confondere due riferimenti
        cartella = modulo_coda.cartella_riferimenti(self.cartella)
        cartella.mkdir(parents=True, exist_ok=True)
        if not (cartella / nome).exists():
            modulo_coda.scrivi_atomico(cartella / nome, dati)
        return {"nome": nome, "da": nome_originale, "larghezza": larghezza,
                "altezza": altezza, "impronta": impronta(dati)}

    def percorso_riferimento(self, nome: str) -> Path:
        """Il file di un riferimento. Solo un nome della cartella dei riferimenti, mai un percorso."""
        if not re.fullmatch(r"rif-[0-9a-f]{16}\.(jpg|png)", nome or ""):
            raise RichiestaStudioNonValida(
                f"\"{nome}\" non e' il nome di un riferimento per lo stile.",
                "Caricalo di nuovo con «Immagine di riferimento per lo stile».",
            )
        percorso = modulo_coda.cartella_riferimenti(self.cartella) / nome
        if not percorso.is_file():
            raise FileNonTrovato(
                f"Il riferimento {nome} non c'e' piu' nella cartella dei riferimenti.",
                "Caricalo di nuovo, oppure toglilo.",
            )
        return percorso

    # --- stile -----------------------------------------------------------

    def catalogo(self) -> dict:
        """Preset, assi e modelli, con quello che e' attivo e quello in grigio."""
        scene = {}
        vere = modulo_miniature.leggi(self.cartella_miniature)
        for scena in blocchi.SCENE:
            scene[scena] = {
                "preset": [
                    {"id": p.identificativo, "nome": p.nome, "scelte": p.scelte.a_dizionario(),
                     "miniatura": _miniatura_dict(p.identificativo, vere.get(p.identificativo))}
                    for p in blocchi.PRESET_STILE.values() if p.scelte.scena == scena
                ],
                "assi": self._assi(scena),
            }
        return {
            "versione_blocchi": blocchi.VERSIONE,
            "origine_blocchi": config.SCELTA,
            "scene": scene,
            "rese": _rese(),
            "varianti_massime": config.VARIANTI_MASSIME,
            "prompt_completo": self.prompt_completo(),
            "inserti_massimi": config.INSERTI_MASSIMO,
            "esempi_stile_massimi": config.ESEMPI_STILE_MASSIMO,
            "finale": {
                "modello": self._modello_dict(MODELLO_FINALE),
                "ingrandimenti": list(config.FINALE_INGRANDIMENTI),
                "predefinito": config.FINALE_INGRANDIMENTO_PREDEFINITO,
                "tipi": [{"id": k, "nome": v} for k, v in NOMI_TIPI_FINALE.items()],
            },
            "modelli": [self._modello_dict(m) for m in MODELLI],
            "categorie_modelli": [{"id": c, "nome": n, "spiega": s} for c, n, s in CATEGORIE_MODELLI],
            "modelli_non_provati": list(MODELLI_NON_PROVATI),
            "risoluzioni": [
                {"id": r, "nome": r.upper()}
                for r in config.RISOLUZIONI_RENDER
            ],
            "contesto": {
                "inquadrature": [{"id": i, "nome": b.nome} for i, b in blocchi.INQUADRATURE.items()],
                "predefinita": config.CONTESTO_INQUADRATURA_PREDEFINITA,
                "luogo_massimo": config.CONTESTO_LUOGO_MASSIMO,
                # «Cerca sul web» (ricerca Google di Nano Banana): in grigio
                # finche' una chiamata vera non dice che il Router lo lascia
                # passare (scripts/sonda_comfy.py --ricerca-web).
                "ricerca_web_verificata": False,
            },
        }

    def prompt_completo(self) -> bool:
        """Vero se l'utente puo' vedere e riscrivere il prompt in inglese.

        Con una chiave propria (Comfy, Magnific) si': il conto e' suo. Coi
        crediti AIRENDER lo dice il piano della licenza (LISTINO, voce
        "prompt_completo": Pro e Studio). Se il server non risponde il prompt
        resta nascosto, e si richiede alla prossima apertura dello Studio.
        """
        if self.provider != "airender":
            return True
        if self._prompt_completo is None:
            try:
                funzioni = self._leggi_saldo().get("funzioni") or {}
            except ErroreAirender:
                return False
            self._prompt_completo = bool(funzioni.get("prompt_completo"))
        return self._prompt_completo

    # --- i miei preset ------------------------------------------------

    def miei_preset(self) -> dict:
        elenco = preset_utente.leggi(self.cartella)
        return {
            "preset": [preset_utente.carica(v) for v in elenco.preset],
            "problema": elenco.problema,
            "file": str(preset_utente.percorso(self.cartella)),
        }

    def salva_mio_preset(self, dati: dict) -> dict:
        modello = self._modello(str(dati.get("modello") or "")).identificativo
        preset_utente.salva(
            self.cartella, dati.get("nome"), dati.get("scelte") or {}, modello,
            prompt_a_mano=_prompt_a_mano(dati), sovrascrivi=bool(dati.get("sovrascrivi")),
        )
        return self.miei_preset()

    def rinomina_mio_preset(self, dati: dict) -> dict:
        preset_utente.rinomina(self.cartella, str(dati.get("nome") or ""), dati.get("nuovo"))
        return self.miei_preset()

    def elimina_mio_preset(self, dati: dict) -> dict:
        preset_utente.elimina(self.cartella, str(dati.get("nome") or ""))
        return self.miei_preset()

    def _assi(self, scena: str) -> list[dict]:
        assi = []
        for asse, (_elenco, valide) in blocchi.ASSI.items():
            if scena not in valide:
                continue
            voci = [
                {"id": b.identificativo, "nome": b.nome, "descrizione": b.descrizione,
                 "attivo": True, "origine": b.origine}
                for b in blocchi.voci(asse, scena).values()
            ]
            titolo = _TITOLI_ASSI[asse]
            if asse == "luce" and scena != blocchi.ESTERNO:
                titolo = "Luce"
            assi.append({"id": asse, "titolo": titolo, "voci": voci})
        return assi

    def _scelte(self, dati: object) -> blocchi.Scelte:
        if not isinstance(dati, dict):
            raise RichiestaStudioNonValida(
                "Le scelte di stile non sono arrivate.",
                "Ricarica la pagina dello Studio.",
            )
        scelte = blocchi.Scelte.da_dizionario(dati)
        blocchi.componi(scelte)  # solleva SceltaNonValida con la ragione
        return scelte

    def componi(self, dati: dict) -> dict:
        """Il prompt vero, il riassunto in italiano e quanti caratteri."""
        scelte = self._scelte(dati.get("scelte"))
        contesto = self._contesto_scelto(dati)
        cambi = self._cambi_scelti(dati) if not contesto else ()
        esempi = self._esempi_scelti(dati, contesto is not None)
        stile = (int(bool(dati.get("riferimento"))) + len(esempi)) if not contesto else 0
        prompt = _prompt_genera(None, scelte, contesto, stile, len(esempi), cambi,
                                len(self._inserti_scelti(dati, contesto is not None)),
                                geometria=self._geometria_scelta(dati, contesto))
        return {
            "prompt": prompt,
            "caratteri": len(prompt),
            "riassunto": riassunto_contesto(contesto, scelte.materiali) if contesto else riassunto(scelte, dati.get("preset")),
            "versione_blocchi": blocchi.VERSIONE,
        }

    def file_miniatura(self, preset: str) -> Path:
        """La miniatura vera di un preset. Solo un preset che esiste, solo dalla sua cartella."""
        percorso = modulo_miniature.file_di(preset, self.cartella_miniature) \
            if preset in blocchi.PRESET_STILE else None
        if percorso is None:
            raise FileNonTrovato(
                f"Il preset {preset} non ha una miniatura vera.",
                "Lo Studio mostra la sua illustrazione.",
            )
        return percorso

    # --- destinazione e costo --------------------------------------------

    def _modello(self, identificativo: str) -> Modello:
        for modello in (*MODELLI, MODELLO_FINALE):
            if modello.identificativo == identificativo:
                return modello
        raise RichiestaStudioNonValida(
            f"Il modello {identificativo} non e' fra quelli che lo Studio sa usare.",
            "Scegli Nano Banana 2 o FLUX.1 Kontext Pro.",
        )

    def _modello_dict(self, modello: Modello) -> dict:
        motore = self._crea_provider(self.provider)
        return {
            "id": modello.identificativo,
            "nome": modello.nome,
            "fornitore": modello.fornitore,
            "categoria": modello.categoria,
            "spiega": modello.spiega,
            "costo": testo_costo(modello, 1),
            "verificato": motore.cosa_manca(modello.identificativo) is None,
            "piu_immagini": motore.accetta_piu_immagini(modello.identificativo),
        }

    def destinazione(self, identificativo_modello: str, varianti: object = 1,
                     riferimento: bool = False, contesto: bool = False,
                     materiali_immagini: object = 0, inserti: object = 0, esempi: object = 0,
                     geometria: bool = False) -> dict:
        """Dove va la vista e quanto costa, da mostrare prima di Genera (regola 5).

        Con N varianti il costo e' N volte quello di un render, e lo si dice
        cosi'. Se il costo del modello non e' misurato resta "non misurato".
        """
        modello = self._modello(identificativo_modello)
        quante = numero_varianti(varianti)
        try:
            dei_materiali = max(0, int(materiali_immagini or 0))
        except (TypeError, ValueError):
            dei_materiali = 0
        try:
            dei_rif = max(0, int(inserti or 0))
        except (TypeError, ValueError):
            dei_rif = 0
        try:
            degli_esempi = max(0, int(esempi or 0)) if riferimento else 0
        except (TypeError, ValueError):
            degli_esempi = 0
        motore = self._crea_provider(self.provider)
        # Anche "airender" passa dal Router, e il server forza il fallback spento.
        senza_ripiego = isinstance(motore, comfy.ProviderComfy) and comfy.FALLBACK == "false"
        return {
            "modello": modello.identificativo,
            "modello_nome": modello.nome,
            "fornitore": modello.fornitore,
            "destinazione": motore.destinazione_per(modello.identificativo),
            "senza_ripiego": senza_ripiego,
            "varianti": quante,
            "costo": testo_costo(modello, quante),
            "costo_misurato": modello.costo_crediti is not None,
            "cosa_manca": motore.cosa_manca(modello.identificativo),
            "avviso": motore.avviso(modello.identificativo),
            # Regola 5: quante immagini partono, detto prima del clic.
            "immagini": (2 if (riferimento or contesto) else 1) + degli_esempi + dei_materiali + dei_rif,
            "inserti": dei_rif,
            "esempi": degli_esempi,
            "cosa_parte": (_cosa_parte(riferimento, contesto, dei_materiali, dei_rif, degli_esempi)
                           .replace("la vista", "il render della prima passata", 1)
                           if geometria and not contesto else
                           _cosa_parte(riferimento, contesto, dei_materiali, dei_rif, degli_esempi)),
            "contesto_non_accettato": (
                f"{modello.nome} riceve una sola immagine per invio: «Fotoinserimento» ne manda due. "
                "Scegli Nano Banana 2."
                if contesto and not motore.accetta_piu_immagini(modello.identificativo) else None),
            "riferimento_non_accettato": (
                f"{modello.nome} riceve una sola immagine per invio: il riferimento non partirebbe. "
                "Toglilo, oppure scegli Nano Banana 2."
                if riferimento and not motore.accetta_piu_immagini(modello.identificativo) else None),
            "materiali_non_accettati": (
                f"{modello.nome} riceve una sola immagine per invio: le immagini dei materiali non partirebbero. "
                "Scegli Nano Banana 2."
                if dei_materiali and not motore.accetta_piu_immagini(modello.identificativo) else None),
            "inserti_non_accettati": (
                f"{modello.nome} riceve una sola immagine per invio: i Rif. di oggetti e persone non partirebbero. "
                "Scegli Nano Banana 2."
                if dei_rif and not motore.accetta_piu_immagini(modello.identificativo) else None),
            "avviso_riferimento": (motore.avviso_piu_immagini(modello.identificativo)
                                   if (riferimento or contesto or dei_materiali or dei_rif) else None),
            "geometria": _geometria_dict(quante, self.provider) if geometria and not contesto else None,
        }

    # --- prova a secco e invio -------------------------------------------

    def prova_a_secco(self, dati: dict) -> dict:
        """Tutto quello che farebbe Genera, tranne mandare. Elenca cosa lo fermerebbe."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        scelte = self._scelte(dati.get("scelte"))
        contesto = self._contesto_scelto(dati)
        riferimento = self._riferimento_scelto(dati)
        cambi = self._cambi_scelti(dati, vista) if not contesto else ()
        inserti = self._inserti_scelti(dati, contesto is not None)
        esempi = self._esempi_scelti(dati, contesto is not None, riferimento)
        geometria = self._geometria_scelta(dati, contesto)
        destinazione = self.destinazione(str(dati.get("modello") or ""), dati.get("varianti", 1),
                                         riferimento=riferimento is not None, contesto=contesto is not None,
                                         materiali_immagini=modulo_materiali.quante_immagini(cambi),
                                         inserti=len(inserti), esempi=len(esempi), geometria=geometria)
        prompt = _prompt_genera(_prompt_a_mano(dati), scelte, contesto,
                                int(riferimento is not None) + len(esempi), len(esempi), cambi, len(inserti),
                                geometria=geometria)
        problemi = []
        descrizione = self.descrivi_vista(vista.name)
        if not descrizione["idonea"]:
            problemi.append({"fatto": descrizione["fatto"], "cosa_fare": descrizione["cosa_fare"]})
        else:
            try:
                motore = self._crea_provider(self.provider)
                motore.controlla_prima_dell_invio(destinazione["modello"], modulo_immagine.leggi(vista))
            except ErroreAirender as errore:
                problemi.append(_errore_dict(errore))
        if destinazione["riferimento_non_accettato"]:
            problemi.append({"fatto": destinazione["riferimento_non_accettato"],
                             "cosa_fare": "Togli il riferimento, oppure scegli Nano Banana 2."})
        if destinazione["contesto_non_accettato"]:
            problemi.append({"fatto": destinazione["contesto_non_accettato"],
                             "cosa_fare": "Scegli Nano Banana 2, oppure togli il contesto."})
        if destinazione["materiali_non_accettati"]:
            problemi.append({"fatto": destinazione["materiali_non_accettati"],
                             "cosa_fare": "Scegli Nano Banana 2, oppure togli la spunta dai materiali."})
        if destinazione["inserti_non_accettati"]:
            problemi.append({"fatto": destinazione["inserti_non_accettati"],
                             "cosa_fare": "Scegli Nano Banana 2, oppure togli i Rif."})
        if destinazione["geometria"] and destinazione["geometria"]["errore"]:
            problemi.append({"fatto": destinazione["geometria"]["errore"],
                             "cosa_fare": destinazione["geometria"]["cosa_fare"]})
        if not self._coda_attiva():
            problemi.append(_CODA_FERMA)
        return {
            "inviato": False,
            "varianti": destinazione["varianti"],
            "prompt": prompt,
            "caratteri": len(prompt),
            "destinazione": destinazione,
            "problemi": problemi,
        }

    def _geometria_scelta(self, dati: dict, contesto: object) -> bool:
        if not dati.get("geometria"):
            return False
        if contesto is not None:
            raise RichiestaStudioNonValida(
                "«Tieni la geometria» non va col Fotoinserimento: il render e' il luogo, non la vista.",
                "Togli la spunta, oppure usa «Render della vista».")
        return True

    def invia(self, dati: dict) -> dict:
        """Scrive in coda un lavoro per variante. Solo se la destinazione e' quella che la pagina ha mostrato.

        Le varianti sono lavori con le stesse scelte: la coda li fa uno dopo
        l'altro, e ognuno e' un invio pagato. Il costo per N l'ha mostrato
        destinazione() prima del clic.
        """
        if _prompt_a_mano(dati) and not self.prompt_completo():
            raise RichiestaStudioNonValida(
                "Il prompt scritto a mano si usa solo con i piani Pro e Studio.",
                "Ricarica lo Studio: il prompt si ricompone dalle scelte. Per scriverlo a mano serve Pro o Studio.",
            )
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        scelte = self._scelte(dati.get("scelte"))
        contesto = self._contesto_scelto(dati)
        riferimento = self._riferimento_scelto(dati)
        cambi = self._cambi_scelti(dati, vista) if not contesto else ()
        inserti = self._inserti_scelti(dati, contesto is not None)
        esempi = self._esempi_scelti(dati, contesto is not None, riferimento)
        geometria = self._geometria_scelta(dati, contesto)
        destinazione = self.destinazione(str(dati.get("modello") or ""), dati.get("varianti", 1),
                                         riferimento=riferimento is not None, contesto=contesto is not None,
                                         materiali_immagini=modulo_materiali.quante_immagini(cambi),
                                         inserti=len(inserti), esempi=len(esempi), geometria=geometria)
        return self._metti_in_coda(
            vista, scelte, destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=dati.get("preset") or None,
            prompt_a_mano=_prompt_a_mano(dati),
            varianti=destinazione["varianti"],
            riferimento=riferimento,
            contesto=contesto,
            materiali=cambi,
            inserti=inserti,
            esempi=esempi,
            geometria_mostrata=dati.get("destinazione_geometria_mostrata") if geometria else None,
        )

    def _esempi_scelti(self, dati: dict, contesto: bool = False, riferimento: object = True) -> tuple[Path, ...]:
        """Gli esempi di «Stile da esempi» oltre al riferimento: nomi della cartella dei riferimenti."""
        nomi = dati.get("esempi") or []
        if not isinstance(nomi, list) or not all(isinstance(n, str) and n for n in nomi):
            raise RichiestaStudioNonValida("Gli esempi di stile devono essere un elenco di nomi.",
                                           "Ricarica lo Studio e scegli di nuovo le immagini.")
        if not nomi:
            return ()
        if contesto:
            raise RichiestaStudioNonValida("Il Fotoinserimento non prende esempi di stile: la luce la dà il luogo.",
                                           "Togli gli esempi, oppure usa «Render della vista».")
        if riferimento is None:
            raise RichiestaStudioNonValida("Gli esempi di stile partono dopo il riferimento per lo stile, che manca.",
                                           "Carica di nuovo il primo esempio.")
        if 1 + len(nomi) > config.ESEMPI_STILE_MASSIMO:
            raise RichiestaStudioNonValida(
                f"Hai scelto {1 + len(nomi)} esempi di stile: ne partono al massimo {config.ESEMPI_STILE_MASSIMO}.",
                "Togline qualcuno.")
        return tuple(self.percorso_riferimento(n) for n in nomi)

    def _riferimento_scelto(self, dati: dict) -> Path | None:
        nome = dati.get("riferimento")
        return self.percorso_riferimento(str(nome)) if nome else None

    def _inserti_scelti(self, dati: dict, contesto: bool = False) -> tuple[Path, ...]:
        """I Rif. 1-4 di oggetti e persone: nomi della cartella dei riferimenti, mai percorsi."""
        nomi = dati.get("inserti") or []
        if not isinstance(nomi, list) or not all(isinstance(n, str) and n for n in nomi):
            raise RichiestaStudioNonValida("I Rif. di oggetti e persone devono essere un elenco di nomi.",
                                           "Ricarica lo Studio e scegli di nuovo le immagini.")
        if len(nomi) > config.INSERTI_MASSIMO:
            raise RichiestaStudioNonValida(
                f"Hai scelto {len(nomi)} Rif.: ne partono al massimo {config.INSERTI_MASSIMO}.",
                "Togline qualcuno.")
        if nomi and contesto:
            raise RichiestaStudioNonValida("Il Fotoinserimento non prende Rif. di oggetti e persone.",
                                           "Genera il render, poi aggiungi gli oggetti con Cambia o Ritocca.")
        return tuple(self.percorso_riferimento(n) for n in nomi)

    # --- materiali del progetto Allplan ----------------------------------

    def materiali_della_vista(self, nome: str) -> dict:
        """I materiali che la palette ha letto quando ha catturato la vista."""
        vista = self.percorso_vista(nome)
        elenco = modulo_materiali.leggi_elenco(vista)
        massimo = config.MATERIALI_CAMBIATI_MASSIMI
        if elenco is None:
            return {"letti": False, "materiali": [], "senza_materiale": [], "massimo": massimo,
                    "letto_il": None, "errore": None}
        return {
            "letti": True,
            "letto_il": elenco["letto_il"],
            "errore": elenco["errore"],
            "massimo": massimo,
            "senza_materiale": elenco["senza_materiale"],
            "materiali": [{**m.a_dizionario(),
                           "anteprima": f"/file/materiale/{m.anteprima}" if m.anteprima else None}
                          for m in elenco["materiali"]],
        }

    def percorso_anteprima_materiale(self, nome: str) -> Path:
        return modulo_materiali.controlla_anteprima(self.cartella, nome)

    def _cambi_scelti(self, dati: dict, vista: Path | None = None) -> tuple:
        """I materiali spuntati, con anteprima e foto prese dalle loro cartelle, mai dalla pagina.

        Una voce con `campione` viene dalla selezione libera sulla vista (web
        app, viste che non vengono da Allplan): il campione e' un ritaglio
        della vista che la pagina ha salvato fra i riferimenti.
        """
        scelti = dati.get("materiali") or []
        if not scelti:
            return ()
        if not isinstance(scelti, list):
            raise RichiestaStudioNonValida("I materiali da cambiare non sono arrivati bene.",
                                           "Ricarica la pagina dello Studio.")
        vista = vista or self.percorso_vista(str(dati.get("vista") or ""))
        elenco = modulo_materiali.leggi_elenco(vista)
        per_chiave = {m.chiave: m for m in (elenco["materiali"] if elenco else [])}
        cambi = []
        for voce in scelti:
            if isinstance(voce, dict) and voce.get("campione"):
                # Un materiale scelto con la selezione libera sulla vista: il
                # campione e' un ritaglio della vista, salvato fra i riferimenti.
                riferimento = voce.get("riferimento")
                cambi.append(modulo_materiali.Cambio(
                    f"materiale {len(cambi) + 1}", str(voce.get("diventa") or ""),
                    str(self.percorso_riferimento(str(voce["campione"]))),
                    str(self.percorso_riferimento(str(riferimento))) if riferimento else None,
                    dalla_vista=True))
                continue
            chiave = str((voce or {}).get("chiave") or "")
            materiale = per_chiave.get(chiave)
            if materiale is None:
                raise RichiestaStudioNonValida(
                    f"Il materiale {chiave!r} non e' fra quelli letti per la vista {vista.name}.",
                    "Cattura di nuovo la vista dalla palette, poi rifai la scelta.")
            riferimento = voce.get("riferimento")
            cambi.append(modulo_materiali.Cambio(
                materiale.nome, str(voce.get("diventa") or ""),
                str(self.percorso_anteprima_materiale(materiale.anteprima)) if materiale.anteprima else None,
                str(self.percorso_riferimento(str(riferimento))) if riferimento else None))
        return modulo_materiali.controlla_cambi(tuple(cambi))

    def _metti_in_coda(self, vista, scelte, destinazione, mostrata, preset, prompt_a_mano,
                       varianti: int = 1, parte_da: str | None = None,
                       partenza: Path | None = None, richieste=(), aree=(),
                       modo_aree: str | None = None, riferimento: Path | None = None,
                       portato_da: str | None = None,
                       contesto: modulo_contesto.Contesto | None = None,
                       materiali: tuple = (), inserti: tuple = (), finale: dict | None = None,
                       esempi: tuple = (), geometria_mostrata: str | None = None) -> dict:
        if mostrata != destinazione["destinazione"]:
            raise RichiestaStudioNonValida(
                f"La pagina ha mostrato come destinazione {mostrata!r}, ma la vista "
                f"partirebbe verso {destinazione['destinazione']}. Non ho inviato niente.",
                "Ricarica lo Studio: la destinazione si rilegge e si mostra di nuovo.",
            )
        prima_passata = destinazione.get("geometria")
        if prima_passata:
            if prima_passata["errore"]:
                raise RichiestaStudioNonValida(f"Non mando: {prima_passata['errore']}",
                                               f"{prima_passata['cosa_fare']} Oppure togli la spunta «Tieni la geometria».")
            if geometria_mostrata != prima_passata["destinazione"]:
                raise RichiestaStudioNonValida(
                    f"La pagina ha mostrato come prima passata {geometria_mostrata!r}, ma la vista "
                    f"partirebbe verso {prima_passata['destinazione']}. Non ho inviato niente.",
                    "Ricarica lo Studio: le destinazioni si rileggono e si mostrano di nuovo.",
                )
        if destinazione["cosa_manca"]:
            raise RichiestaStudioNonValida(
                f"Non mando: {destinazione['cosa_manca']}",
                "Scegli Nano Banana 2, il modello predefinito, il cui schema e' verificato.",
            )
        if destinazione.get("riferimento_non_accettato"):
            raise RichiestaStudioNonValida(f"Non mando: {destinazione['riferimento_non_accettato']}",
                                           "Togli il riferimento, oppure scegli Nano Banana 2.")
        if destinazione.get("contesto_non_accettato"):
            raise RichiestaStudioNonValida(f"Non mando: {destinazione['contesto_non_accettato']}",
                                           "Scegli Nano Banana 2, oppure togli il contesto.")
        if destinazione.get("materiali_non_accettati"):
            raise RichiestaStudioNonValida(f"Non mando: {destinazione['materiali_non_accettati']}",
                                           "Scegli Nano Banana 2, oppure togli la spunta dai materiali.")
        if destinazione.get("inserti_non_accettati"):
            raise RichiestaStudioNonValida(f"Non mando: {destinazione['inserti_non_accettati']}",
                                           "Scegli Nano Banana 2, oppure togli i Rif.")
        if partenza is None:
            # Da un render l'idoneita' non conta: giudica una vista di
            # Allplan, e quello che parte e' il render del passo.
            descrizione = self.descrivi_vista(vista.name)
            if not descrizione["idonea"]:
                raise RichiestaStudioNonValida(descrizione["fatto"], descrizione["cosa_fare"])
        lavori = [
            modulo_coda.metti_in_coda(
                self.cartella, vista, scelte,
                preset=preset,
                provider=self.provider,
                modello=destinazione["modello"],
                prompt_a_mano=prompt_a_mano,
                parte_da=parte_da,
                partenza=partenza,
                richieste=tuple(richieste),
                aree=tuple(aree),
                modo_aree=modo_aree,
                riferimento=riferimento,
                portato_da=portato_da,
                contesto=contesto,
                materiali=tuple(materiali),
                inserti=tuple(inserti),
                finale=finale,
                esempi=tuple(esempi),
                destinazione_geometria=prima_passata["destinazione"] if prima_passata else None,
                crea_provider=self._crea_provider,
            )
            for _ in range(varianti)
        ]
        return {
            "identificativo": lavori[0].identificativo,
            "identificativi": [l.identificativo for l in lavori],
            "destinazione": lavori[0].destinazione,
            "coda_attiva": self._coda_attiva(),
        }

    def ricetta_da_portare(self, identificativo: str) -> dict:
        """Cosa porta «Porta su un'altra vista» da questa immagine: stile, modello e richieste di tutta la strada.

        Lo stile e' quello del primo render dalla vista; dopo, ogni passo e
        ogni ritocco aggiunge le sue richieste e le sue note, nell'ordine. Le
        aree no: sono disegnate su un'altra inquadratura. Le prende a parole,
        e l'immagine scelta parte come seconda immagine perche' il modello
        veda come sono venute.
        """
        lavoro, _cartella = self._lavoro(identificativo)
        if lavoro.contesto is not None:
            raise RichiestaStudioNonValida(
                "Un'immagine di «Fotoinserimento» non si porta su un'altra vista: "
                "la sua prima immagine e' il luogo, non la vista.",
                "Scegli un render nato da una vista Allplan.")
        render = self._render(identificativo)
        if render is None:
            raise RichiestaStudioNonValida(
                "Questa immagine non ha un render da portare.",
                "Scegli un render riuscito, oppure aspetta che finisca.")
        vista = Path(lavoro.vista)
        strada = [p["identificativo"] for p in self._albero(vista).strada(identificativo)] or [identificativo]
        lavori = [self._lavoro(i)[0] for i in strada]
        origine = next((l for l in lavori if not l.partenza), None)
        if origine is None:
            raise RichiestaStudioNonValida(
                "Non trovo il primo render di questa strada: lo stile da portare non si sa.",
                "Parti da un render fatto da Genera.")
        richieste: list[str] = []
        for passo in lavori:
            richieste += [r for r in passo.richieste if r.strip()]
            richieste += [a.nota for a in passo.aree if a.nota.strip()]
        return {"lavoro": lavoro, "render": render, "vista": vista, "origine": origine,
                "richieste": richieste}

    def porta_su_vista(self, identificativo: str, dati: dict) -> dict:
        """Un render nuovo su un'altra vista, coerente con questa immagine.

        Stesse scelte e stesso modello del primo render, tutte le richieste
        e le note della strada, e questa immagine come seconda immagine
        (blocchi.RIFERIMENTO_COERENZA). E' un lavoro dalla vista nuova:
        nell'albero di quella vista e' un passo 1.
        """
        ricetta = self.ricetta_da_portare(identificativo)
        lavoro, origine = ricetta["lavoro"], ricetta["origine"]
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        if vista.resolve() == ricetta["vista"].resolve():
            raise RichiestaStudioNonValida(
                "Questa e' la stessa vista dell'immagine: qui serve Variante.",
                "Cattura in Allplan l'altra inquadratura, poi sceglila qui.")
        riferimento = self.percorso_riferimento(
            self.carica_riferimento(ricetta["render"].read_bytes(), ricetta["render"].name)["nome"])
        destinazione = self.destinazione(lavoro.modello, riferimento=True)
        return self._metti_in_coda(
            vista, origine.scelte, destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=origine.preset, prompt_a_mano=origine.prompt_a_mano,
            richieste=ricetta["richieste"], riferimento=riferimento,
            portato_da=lavoro.identificativo,
        )

    def anteprima_porta(self, identificativo: str) -> dict:
        """Quello che la pagina mostra prima del clic: da dove viene e cosa porta."""
        ricetta = self.ricetta_da_portare(identificativo)
        lavoro, origine = ricetta["lavoro"], ricetta["origine"]
        modello = next((m for m in MODELLI if m.identificativo == lavoro.modello), None)
        preset = blocchi.PRESET_STILE.get(origine.preset or "")
        return {
            "modello": lavoro.modello,
            "modello_nome": modello.nome if modello else lavoro.modello,
            "stile": "Prompt scritto a mano" if (origine.prompt_a_mano or "").strip()
                     else (preset.nome if preset else "Scelte libere"),
            "richieste": ricetta["richieste"],
            "vista": ricetta["vista"].name,
            "viste": [v["nome"] for v in self.elenco_viste() if v["nome"] != ricetta["vista"].name],
        }

    def rifai(self, identificativo: str, dati: dict) -> dict:
        """Rimette in coda un lavoro con la stessa ricetta: stesse scelte, stesso modello, stessa partenza.

        Per un passo e' «Rifai questo passo»: stesso passo di partenza, stessa
        richiesta, e nell'albero un ramo nuovo accanto.
        """
        lavoro, _cartella = self._lavoro(identificativo)
        partenza = Path(lavoro.partenza) if lavoro.partenza else None
        if partenza is not None and not self._render_valido(partenza):
            raise FileNonTrovato(
                "Il punto di partenza di questo passo non c'e' piu': il suo render e' "
                "stato tolto dalla cartella dei lavori.",
                "Usa «Rifai tutto dalla vista»: riparte dalla vista Allplan con le "
                "stesse richieste.",
            )
        vista = Path(lavoro.vista)
        if not vista.is_file():
            raise FileNonTrovato(
                f"La vista di questo lavoro non c'e' piu': {vista}.",
                "Catturala di nuovo dalla palette, poi genera da Genera.",
            )
        if vista.parent.resolve() != self.cartella:
            raise RichiestaStudioNonValida(
                "La vista di questo lavoro non sta nella cartella dello Studio.",
                "Riaprila con Usa un'altra vista, poi genera da Genera.",
            )
        riferimento = Path(lavoro.riferimento) if lavoro.riferimento else None
        inserti = tuple(Path(i) for i in lavoro.inserti)
        esempi = tuple(Path(e) for e in lavoro.esempi)
        destinazione = self.destinazione(lavoro.modello, riferimento=riferimento is not None,
                                         contesto=lavoro.contesto is not None, inserti=len(inserti),
                                         esempi=len(esempi))
        return self._metti_in_coda(
            vista, lavoro.scelte, destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=lavoro.preset,
            prompt_a_mano=lavoro.prompt_a_mano,
            parte_da=lavoro.parte_da,
            partenza=partenza,
            richieste=lavoro.richieste,
            # Un ritocco si rifa' con le sue aree e il suo modo, anche se nel
            # frattempo RITOCCO_MODO_AREE e' cambiato: e' la sua ricetta.
            aree=lavoro.aree,
            modo_aree=lavoro.modo_aree,
            riferimento=riferimento,
            contesto=lavoro.contesto,
            inserti=inserti,
            finale=lavoro.finale,
            esempi=esempi,
        )

    def annulla(self, identificativo: str) -> dict:
        self._controlla_id(identificativo)
        segnale = modulo_coda.chiedi_annullamento(self.cartella, identificativo)
        return {"identificativo": identificativo, "segnale": str(segnale)}

    # --- lavori ----------------------------------------------------------

    def _controlla_id(self, identificativo: str) -> str:
        if not _ID_LAVORO.match(identificativo or ""):
            raise RichiestaStudioNonValida(
                f"\"{identificativo}\" non e' l'identificativo di un lavoro.",
                "Scegli il render dall'elenco Render di questa vista.",
            )
        return identificativo

    def _lavoro(self, identificativo: str) -> tuple[modulo_coda.Lavoro, str]:
        self._controlla_id(identificativo)
        for nome in _CARTELLE_LAVORO:
            percorso = self.percorsi[nome] / f"{identificativo}.json"
            try:
                return modulo_coda.Lavoro.da_dizionario(
                    json.loads(percorso.read_text(encoding="utf-8"))
                ), nome
            except FileNotFoundError:
                continue
            except ValueError:
                break
        raise FileNonTrovato(
            f"Non trovo il lavoro {identificativo} nella cartella {self.cartella / modulo_coda.CARTELLA_LAVORI}.",
            "Forse la cartella e' stata pulita a mano. Genera di nuovo da Genera.",
        )

    def _lavori(self) -> list[tuple[dict, str]]:
        """Tutti i lavori leggibili della cartella, con la cartella dove stanno."""
        trovati = []
        for nome in _CARTELLE_LAVORO:
            for percorso in self.percorsi[nome].glob("*.json"):
                if percorso.name.startswith(modulo_coda.PREFISSO_TEMPORANEO):
                    continue
                try:
                    dati = json.loads(percorso.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue  # la coda lo mettera' fra gli errori con la ragione
                if isinstance(dati, dict) and dati.get("identificativo") == percorso.stem:
                    trovati.append((dati, nome))
        return trovati

    def lavoro(self, identificativo: str) -> dict:
        """Un lavoro con il suo stato, quanto tempo e' passato e, se c'e', il render."""
        lavoro, _cartella = self._lavoro(identificativo)
        return self._riassunto_lavoro(lavoro.a_dizionario())

    def _riassunto_lavoro(self, dati: dict) -> dict:
        identificativo = dati["identificativo"]
        stato = modulo_coda.leggi_stato(self.cartella, identificativo) or {
            "identificativo": identificativo, "stato": modulo_coda.IN_CODA,
        }
        try:
            creato = datetime.fromisoformat(dati.get("creato_il") or "")
            secondi = max(0, int((self._adesso() - creato).total_seconds()))
        except ValueError:
            secondi = None
        modello = next((m for m in (*MODELLI, MODELLO_FINALE) if m.identificativo == dati.get("modello")), None)
        preset = blocchi.PRESET_STILE.get(dati.get("preset") or "")
        render = self._render(identificativo, stato)
        richieste = [r for r in (dati.get("richieste") or []) if isinstance(r, str)]
        try:
            scelte = blocchi.Scelte.da_dizionario(dati.get("scelte") or {})
            testo_riassunto = riassunto(scelte, dati.get("preset"))
        except ErroreAirender:
            testo_riassunto = ""
        finale = dati.get("finale") if isinstance(dati.get("finale"), dict) else None
        if finale:
            testo_riassunto = _riassunto_finale(finale)
        elif dati.get("partenza"):
            # Un passo su un render: lo stile non riparte, solo la richiesta.
            testo_riassunto = "Passo sul render di prima: " + "; ".join(richieste) + "."
        elif richieste:
            testo_riassunto += " Più: " + "; ".join(richieste) + "."
        return {
            "identificativo": identificativo,
            "stato": stato.get("stato"),
            "attivo": stato.get("stato") in STATI_ATTIVI,
            "aggiornato_il": stato.get("aggiornato_il"),
            "fatto": stato.get("fatto"),
            "cosa_fare": stato.get("cosa_fare"),
            "avvisi": stato.get("avvisi") or [],
            "secondi": secondi,
            "creato_il": dati.get("creato_il"),
            "vista": Path(dati.get("vista") or "").name,
            "destinazione": dati.get("destinazione"),
            "modello": dati.get("modello"),
            "modello_nome": modello.nome if modello else dati.get("modello"),
            "preset": dati.get("preset"),
            "preset_nome": (
                f"Finale ×{finale.get('ingrandimento')}" if finale
                else "Ritocco: " + modulo_passi.nome_breve(str((dati.get("aree") or [{}])[0].get("nota") or ""))
                if dati.get("aree") and isinstance((dati.get("aree") or [None])[0], dict)
                else "Cambia: " + modulo_passi.nome_breve(richieste[0]) if dati.get("partenza") and richieste
                else preset.nome if preset else "Scelte libere"
            ),
            "parte_da": dati.get("parte_da"),
            "scelte": dati.get("scelte"),
            "riassunto": testo_riassunto,
            "prompt_a_mano": bool(dati.get("prompt_a_mano")),
            "render": render is not None,
            "scostamento_geometria": stato.get("scostamento_geometria"),
            "tenuta": self._tenuta(render),
        }

    def _tenuta(self, render: Path | None) -> dict | None:
        """La misura degli spigoli di un render, come la mostra lo Studio. None senza render."""
        if render is None:
            return None
        misura = modulo_coda.leggi_misura(render)
        if misura is None:
            return {"spigoli": None, "motivo": "render fatto prima che la misura esistesse",
                    "da_misurare": True, "avvisa": False, "soglia": config.GEOMETRY_DRIFT_WARN}
        spigoli = misura.get("spigoli")
        numero = isinstance(spigoli, (int, float))
        return {
            "spigoli": spigoli if numero else None,
            "motivo": None if numero else (misura.get("motivo") or "misura non riuscita"),
            "da_misurare": False,
            "avvisa": numero and spigoli < config.GEOMETRY_DRIFT_WARN,
            "soglia": config.GEOMETRY_DRIFT_WARN,
        }

    def misura_ora(self, identificativo: str) -> dict:
        """Misura gli spigoli di un render fatto prima della misura, e la salva accanto."""
        self._controlla_id(identificativo)
        render = self._render(identificativo)
        if render is None:
            raise FileNonTrovato(
                "Questo lavoro non ha un render da misurare.",
                "Scegli un render fatto nell'elenco dei render della vista.",
            )
        lavoro, _cartella = self._lavoro(identificativo)
        modulo_coda.scrivi_misura(Path(lavoro.vista), render)
        return self._tenuta(render)

    # --- esporta per il cliente ----------------------------------------------

    def cartella_esportati(self) -> Path:
        return self.cartella / CARTELLA_ESPORTATI

    def esporta(self, identificativo: str, dati: dict) -> dict:
        """Scrive il render scelto in JPEG, PNG o PSD a livelli nella cartella esportati, e dice dove.

        Il PSD ha in basso la vista di Allplan e sopra un livello per ogni passo
        della strada fino a questo render. Nessun file contiene prompt o ricetta.
        """
        self._controlla_id(identificativo)
        formato = str(dati.get("formato") or "").lower()
        render = self._render(identificativo)
        if render is None:
            raise FileNonTrovato(
                "Questo lavoro non ha un render da esportare.",
                "Scegli un render fatto nell'elenco dei render della vista.",
            )
        regolazione = modulo_regola.leggi(dati.get("regola"))
        lavoro, _cartella = self._lavoro(identificativo)
        vista = Path(lavoro.vista)
        pixel = render.read_bytes()
        regolato = None
        if not regolazione.neutra():
            regolato = modulo_immagine.regola(
                pixel, modulo_regola.tabelle(regolazione), modulo_regola.fattore_saturazione(regolazione))
        livelli = None
        if formato == "psd":
            livelli = self._livelli_della_strada(vista, identificativo, render)
            if regolato is not None:
                # Sopra il render com'era, cosi' in Photoshop si spegne e si confronta.
                livelli.append(("Regola · " + ", ".join(regolazione.descrizione()), regolato))
        contenuto = modulo_esporta.esporta(regolato if regolato is not None else pixel, formato, livelli)
        numero = self._numero_passo(vista, identificativo)
        istante = self._adesso().astimezone()
        cartella = self.cartella_esportati()
        cartella.mkdir(parents=True, exist_ok=True)
        base = f"{vista.stem}-passo{numero}-{istante:%Y%m%d-%H%M%S}" if numero else f"{vista.stem}-{istante:%Y%m%d-%H%M%S}"
        file = cartella / (base + modulo_esporta.ESTENSIONI[formato])
        indice = 1
        while file.exists():
            indice += 1
            file = cartella / f"{base}-{indice}{modulo_esporta.ESTENSIONI[formato]}"
        modulo_coda.scrivi_atomico(file, contenuto)
        larghezza, altezza = modulo_immagine.dimensioni(render.read_bytes())
        return {
            "file": str(file), "nome": file.name, "cartella": str(cartella), "formato": formato,
            "larghezza": larghezza, "altezza": altezza,
            "livelli": [nome for nome, _dati in livelli] if livelli else None,
            "regolazioni": regolazione.descrizione(),
            "peso_mb": round(len(contenuto) / _BYTE_PER_MB, 1),
        }

    def anteprima_regola(self, identificativo: str, dati: dict) -> dict:
        """Il render scelto con le regolazioni, piccolo, per vederlo mentre si muovono i cursori.

        Tutto qui, sul computer: nessuna immagine parte. Il file esportato si
        rifa' a grandezza piena con gli stessi numeri (core/regola.py).
        """
        self._controlla_id(identificativo)
        regolazione = modulo_regola.leggi(dati.get("regola"))
        render = self._render(identificativo)
        if render is None:
            raise FileNonTrovato(
                "Questo lavoro non ha un render da regolare.",
                "Scegli un render fatto nell'elenco dei render della vista.",
            )
        chiave = f"{identificativo}:{render.stat().st_mtime_ns}"
        if not self._base_anteprima or self._base_anteprima[0] != chiave:
            dati_render = render.read_bytes()
            self._dimensioni_anteprima = modulo_immagine.dimensioni(dati_render)
            self._base_anteprima = (chiave, modulo_immagine.regola(
                dati_render, modulo_regola.tabelle(modulo_regola.Regolazione()), 1,
                lato_massimo=config.REGOLA_ANTEPRIMA_LATO_PX, formato="PNG"))
        anteprima = modulo_immagine.regola(
            self._base_anteprima[1], modulo_regola.tabelle(regolazione),
            modulo_regola.fattore_saturazione(regolazione), formato="JPEG")
        return {
            "immagine": "data:image/jpeg;base64," + base64.b64encode(anteprima).decode("ascii"),
            "regolazioni": regolazione.descrizione(),
            "curva": modulo_regola.tabella_curva(regolazione),
            # La misura del render vero: l'anteprima e' piu' piccola.
            "larghezza": self._dimensioni_anteprima[0], "altezza": self._dimensioni_anteprima[1],
        }

    def _numero_passo(self, vista: Path, identificativo: str) -> int | None:
        try:
            passo = self._albero(vista).passo(identificativo)
        except (ErroreAirender, OSError):
            return None
        return passo.get("numero") if passo else None

    def _livelli_della_strada(self, vista: Path, identificativo: str, render: Path) -> list[tuple[str, bytes]]:
        """Vista di Allplan, poi i render della strada fino a questo, dal basso in alto."""
        livelli: list[tuple[str, bytes]] = []
        if vista.is_file():
            livelli.append(("Vista Allplan", vista.read_bytes()))
        try:
            strada = self._albero(vista).strada(identificativo)
        except (ErroreAirender, OSError):
            strada = []
        for passo in strada:
            file = Path(passo["render"]) if passo.get("render") else None
            if passo["identificativo"] == identificativo:
                file = render
            if file is None or not self._render_valido(file):
                continue  # un passo senza render (tolto, fallito) non diventa un livello vuoto
            livelli.append((_nome_livello(passo), file.read_bytes()))
        if not livelli or livelli[-1][1] != render.read_bytes():
            livelli.append(("Render", render.read_bytes()))
        return livelli

    def _render_valido(self, percorso: Path) -> bool:
        """Un render si usa come partenza solo se sta in lavori/fatto e c'e' ancora."""
        try:
            percorso = Path(percorso).resolve()
        except OSError:
            return False
        return percorso.parent == self.percorsi[modulo_coda.FATTO_DIR].resolve() and percorso.is_file()

    def _render(self, identificativo: str, stato: dict | None = None) -> Path | None:
        """Il file del render di un lavoro fatto, solo se sta in lavori/fatto."""
        stato = stato if stato is not None else modulo_coda.leggi_stato(self.cartella, identificativo) or {}
        if stato.get("stato") != modulo_coda.FATTO or not stato.get("render"):
            return None
        percorso = Path(stato["render"]).resolve()
        if percorso.parent != self.percorsi[modulo_coda.FATTO_DIR].resolve() or not percorso.is_file():
            return None
        return percorso

    def file_render(self, identificativo: str) -> Path:
        self._controlla_id(identificativo)
        percorso = self._render(identificativo)
        if percorso is None:
            raise FileNonTrovato(
                f"Il lavoro {identificativo} non ha un render.",
                "Guarda lo stato del lavoro in Risultato.",
            )
        return percorso

    def ricetta(self, identificativo: str) -> dict:
        """La ricetta salvata accanto al render, piu' i percorsi da mostrare."""
        self._controlla_id(identificativo)
        stato = modulo_coda.leggi_stato(self.cartella, identificativo) or {}
        render = self._render(identificativo, stato)
        if render is None:
            raise FileNonTrovato(
                f"Il lavoro {identificativo} non ha una ricetta: non e' finito con un render.",
                "Guarda lo stato del lavoro in Risultato.",
            )
        percorso = render.with_name(render.name + ".ricetta.json")
        try:
            ricetta = Ricetta.da_json(percorso.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            raise FileNonTrovato(
                f"La ricetta accanto al render non si legge: {percorso}.",
                "Il render resta valido; per rifarlo usa Rifai, che riparte dal lavoro.",
            ) from None
        parametri = ricetta.parametri or {}
        crediti = parametri.get("crediti_usati")
        return {
            "identificativo": identificativo,
            "provider": ricetta.provider,
            "modello": ricetta.modello,
            "preset": ricetta.preset,
            "preset_versione": ricetta.preset_versione,
            "prompt": ricetta.prompt,
            "testo_utente": ricetta.testo_utente,
            "seme": ricetta.seme,
            "fallback": parametri.get("fallback_provider"),
            "crediti": f"{_numero(float(crediti))} crediti" if _e_numero(crediti) else None,
            "creata_il": ricetta.creata_il,
            "percorso_render": str(render),
            "percorso_ricetta": str(percorso),
        }

    def ultimo_lavoro(self) -> dict | None:
        """Il lavoro nato per ultimo nella cartella, qualunque sia il suo stato. Per la palette."""
        lavori = self._lavori()
        if not lavori:
            return None
        dati, _cartella = max(lavori, key=lambda c: (c[0].get("creato_il") or "", c[0]["identificativo"]))
        return self._riassunto_lavoro(dati)

    def lavori_attivi(self) -> list[dict]:
        return [
            r for r in (self._riassunto_lavoro(d) for d, cartella in self._lavori()
                        if cartella in (modulo_coda.IN_ATTESA_DIR, modulo_coda.IN_CORSO_DIR))
            if r["attivo"]
        ]

    def _lavori_della_vista(self, vista: Path) -> list[dict]:
        """I file dei lavori nati da questa vista, anche quelli partiti da un suo passo."""
        vista = Path(vista).resolve()
        trovati = []
        for dati, _cartella in self._lavori():
            try:
                stessa = Path(dati.get("vista") or "").resolve() == vista
            except OSError:
                stessa = False
            if stessa:
                trovati.append(dati)
        return trovati

    def render_della_vista(self, nome: str) -> list[dict]:
        """Tutti i lavori nati da questa vista, il piu' recente per primo."""
        vista = self.percorso_vista(nome)
        lavori = [self._riassunto_lavoro(d) for d in self._lavori_della_vista(vista)]
        lavori.sort(key=lambda r: (r.get("creato_il") or "", r["identificativo"]), reverse=True)
        return lavori

    # --- passi -----------------------------------------------------------

    def _albero(self, vista: Path, lavori: list[dict] | None = None) -> modulo_passi.Albero:
        """L'albero della vista, allineato ai lavori della cartella e scritto se e' cambiato.

        `lavori` sono i lavori di questa vista, se chi chiama li ha gia' letti.
        """
        with self._blocco_albero:
            albero = modulo_passi.Albero.leggi(vista)
            lavori = self._lavori_della_vista(vista) if lavori is None else lavori
            stati, ricette = {}, {}
            for dati in lavori:
                identificativo = dati["identificativo"]
                stato = modulo_coda.leggi_stato(self.cartella, identificativo) or {}
                stati[identificativo] = stato
                render = self._render(identificativo, stato)
                if render is not None:
                    try:
                        ricette[identificativo] = json.loads(
                            render.with_name(render.name + ".ricetta.json").read_text(encoding="utf-8"))
                    except (OSError, ValueError):
                        pass  # il passo resta senza costo: "non letto dal servizio"
            if albero.allinea(lavori, stati, ricette):
                albero.scrivi(vista)
            return albero

    def passi(self, nome: str) -> dict:
        """L'albero dei passi di una vista, come lo disegna Studio · Passi."""
        vista = self.percorso_vista(nome)
        albero = self._albero(vista)
        righe = [self._passo_dict(albero, passo, profondita) for passo, profondita in albero.in_ordine()]
        return {
            "vista": nome,
            "file": str(modulo_passi.percorso(vista)),
            "catturata_il": datetime.fromtimestamp(vista.stat().st_mtime).isoformat(timespec="seconds"),
            "avviso_da_generazione": config.PASSI_AVVISO_DA_GENERAZIONE,
            "passi": righe,
        }

    # --- storico ---------------------------------------------------------

    def storico(self) -> dict:
        """Tutte le immagini di tutte le viste, per lo storico a sinistra nello Studio.

        Un gruppo per vista, la vista catturata per ultima per prima. Dentro
        il gruppo: la cattura, poi i render, i ritocchi e i video in ordine
        d'albero: ognuno subito dopo l'immagine da cui parte. Una cattura nuova apre un gruppo nuovo: i gruppi di
        prima restano come sono. Niente si cancella da qui.
        """
        lavori_per_vista: dict[str, list[dict]] = {}
        for dati, _cartella in self._lavori():
            try:
                chiave = str(Path(dati.get("vista") or "").resolve())
            except OSError:
                continue
            lavori_per_vista.setdefault(chiave, []).append(dati)
        video_per_lavoro, video_sciolti = self._video_per_lavoro()
        gruppi = []
        for voce_vista in self.elenco_viste():
            nome = voce_vista["nome"]
            vista = self.cartella / nome
            voci = [{"tipo": "cattura", "vista": nome, "identificativo": None,
                     "etichetta": "Vista", "creato_il": voce_vista["modificata_il"],
                     "stato": modulo_coda.FATTO, "attivo": False, "immagine": True}]
            errore = None
            try:
                albero = self._albero(vista, lavori_per_vista.get(str(vista.resolve()), []))
                # In ordine d'albero: ogni immagine subito dopo quella da cui
                # parte, cosi' un ritocco o una variante stanno accanto.
                passi = [passo for passo, _profondita in albero.in_ordine()]
            except ErroreAirender as problema:
                passi, errore = [], _errore_dict(problema)
            for passo in passi:
                identificativo = passo["identificativo"]
                render = Path(passo["render"]) if passo.get("render") else None
                voci.append({
                    "tipo": _tipo_passo(passo),
                    "vista": nome,
                    "identificativo": identificativo,
                    "numero": str(passo.get("numero")),
                    "da": albero.padre(passo),
                    "etichetta": _ETICHETTE_STORICO.get(_tipo_passo(passo), "Render"),
                    "creato_il": passo.get("creato_il"),
                    "stato": passo.get("stato"),
                    "attivo": passo.get("stato") in STATI_ATTIVI,
                    "immagine": render is not None and self._render_valido(render),
                })
                voci.extend(video_per_lavoro.get(identificativo, []))
            gruppi.append({"vista": nome, "catturata_il": voce_vista["modificata_il"],
                           "voci": voci, "errore": errore})
        if video_sciolti:
            gruppi.append({"vista": None, "catturata_il": None, "voci": video_sciolti, "errore": None})
        return {"gruppi": gruppi}

    def _video_per_lavoro(self) -> tuple[dict[str, list[dict]], list[dict]]:
        """I video, attaccati al render da cui partono; quelli da un'immagine caricata a parte."""
        fatti = self.percorsi[modulo_coda.FATTO_DIR].resolve()
        per_lavoro: dict[str, list[dict]] = {}
        sciolti = []
        for voce in sorted(modulo_video.elenco(self.cartella), key=lambda v: v.get("identificativo", "")):
            immagini = (voce.get("richiesta") or {}).get("immagini") or []
            voce_storico = {
                "tipo": "video", "vista": None, "identificativo": voce.get("identificativo"),
                "etichetta": "Video", "creato_il": voce.get("aggiornato_il"),
                "stato": voce.get("stato"),
                "attivo": voce.get("stato") in (modulo_video.IN_CODA, modulo_video.INVIATO),
                "immagine": voce.get("stato") == modulo_video.FATTO and bool(voce.get("video")),
            }
            lavoro = None
            if immagini:
                try:
                    primo = Path(immagini[0]).resolve()
                    if primo.parent == fatti:
                        lavoro = primo.stem
                except OSError:
                    lavoro = None
            if lavoro:
                per_lavoro.setdefault(lavoro, []).append(voce_storico)
            else:
                sciolti.append(voce_storico)
        return per_lavoro, sciolti

    def _passo_dict(self, albero: modulo_passi.Albero, passo: dict, profondita: int) -> dict:
        identificativo = passo["identificativo"]
        strada = albero.strada(identificativo)
        generazioni = len(strada)
        padre = albero.padre(passo)
        padre_passo = albero.passo(padre) if padre != modulo_passi.VISTA else None
        render = Path(passo["render"]) if passo.get("render") else None
        ha_render = render is not None and self._render_valido(render)
        stato = passo.get("stato")
        modello = next((m for m in MODELLI if m.identificativo == passo.get("modello")), None)
        # Da un passo si parte solo se ha un render che c'e' ancora.
        if stato in STATI_ATTIVI:
            motivo = "il passo non e' ancora finito"
        elif stato != modulo_coda.FATTO:
            motivo = "il passo non e' riuscito: non ha un render da cui partire"
        elif not ha_render:
            motivo = "il render di questo passo non c'e' piu' nella cartella dei lavori"
        else:
            motivo = None
        partenza = passo.get("partenza") or {}
        # Un passo fatto su un render il cui render non c'e' piu': non si
        # puo' rifare uguale, si propone di rifarlo pulito dalla vista.
        partenza_mancante = _tipo_passo(passo) in ("passo", "ritocco") and (
            padre_passo is None
            or not (padre_passo.get("render") and self._render_valido(Path(padre_passo["render"])))
        )
        return {
            "identificativo": identificativo,
            "numero": str(passo.get("numero")),
            "da": padre,
            "da_numero": "0" if padre_passo is None else str(padre_passo.get("numero")),
            "profondita": profondita,
            "generazioni": generazioni,
            "avviso": generazioni >= config.PASSI_AVVISO_DA_GENERAZIONE,
            "strada": ["0"] + [str(p.get("numero")) for p in strada],
            "nome": _nome_passo(passo),
            "tipo": _tipo_passo(passo),
            "modello": passo.get("modello"),
            "modello_nome": modello.nome if modello else passo.get("modello"),
            "creato_il": passo.get("creato_il"),
            "stato": stato,
            "attivo": stato in STATI_ATTIVI,
            "tenuta": self._tenuta(render) if ha_render else None,
            "render": ha_render,
            "si_parte": motivo is None,
            "motivo_non_si_parte": motivo,
            "figli": len(albero.figli(identificativo)),
            "richieste": passo.get("richieste") or [],
            "riassunto": _riassunto_passo(passo, padre_passo),
            "prompt": passo.get("prompt"),
            "prompt_a_mano": bool(passo.get("prompt_a_mano")),
            "versione_blocchi": passo.get("versione_blocchi"),
            "destinazione": passo.get("destinazione"),
            "costo": _costo_passo(passo, modello),
            "fatto": passo.get("fatto"),
            "cosa_fare": passo.get("cosa_fare"),
            "partenza_file": partenza.get("file"),
            "partenza_mancante": bool(partenza_mancante),
            "percorso_render": passo.get("render"),
            "percorso_ricetta": passo.get("ricetta"),
            "aree": passo.get("aree"),
            "modo_aree": passo.get("modo_aree"),
            "modo_aree_nome": modulo_aree.NOMI_MODI.get(passo.get("modo_aree") or ""),
            "fuori_aree": passo.get("fuori_aree") if stato == modulo_coda.FATTO else None,
            "fuori_aree_testo": modulo_aree.testo_misura(passo.get("fuori_aree"))
            if passo.get("aree") and stato == modulo_coda.FATTO else None,
        }

    def _passo_di_partenza(self, albero: modulo_passi.Albero, identificativo: str) -> tuple[dict, Path]:
        """Il passo da cui ne parte uno nuovo, e il file del suo render."""
        passo = albero.passo(str(identificativo or ""))
        if passo is None:
            raise RichiestaStudioNonValida(
                f"Nell'albero di questa vista non c'e' il passo {identificativo!r}.",
                "Scegli il passo di partenza nell'albero. Dalla vista (passo 0) si parte da Genera.",
            )
        render = Path(passo["render"]) if passo.get("render") else None
        if passo.get("stato") != modulo_coda.FATTO or render is None or not self._render_valido(render):
            raise RichiestaStudioNonValida(
                f"Dal passo {passo.get('numero')} non si puo' partire: non ha un render "
                "nella cartella dei lavori.",
                "Scegli un passo riuscito, oppure rifallo.",
            )
        return passo, render

    def _scena(self, albero: modulo_passi.Albero, passo: dict) -> str:
        for p in [passo, *reversed(albero.strada(passo["identificativo"]))]:
            if p.get("scena") in blocchi.SCENE:
                return p["scena"]
        return blocchi.ESTERNO

    def componi_passo(self, dati: dict) -> dict:
        """Il prompt di un passo nuovo, da mostrare prima dell'invio."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        albero = self._albero(vista)
        passo, _render = self._passo_di_partenza(albero, dati.get("da"))
        prompt = blocchi.componi_richieste(self._scena(albero, passo), [str(dati.get("testo") or "")])
        inserti = self._inserti_scelti(dati)
        prompt = blocchi.aggiungi_inserti(prompt, modulo_coda.prima_immagine_inserti(False, False, 0), len(inserti))
        return {
            "prompt": prompt,
            "caratteri": len(prompt),
            "da_numero": str(passo.get("numero")),
            "ramo_nuovo": bool(albero.figli(passo["identificativo"])),
            "generazioni": albero.generazioni(passo["identificativo"]) + 1,
        }

    def invia_passo(self, dati: dict) -> dict:
        """Un passo nuovo dal render di un passo: la richiesta a parole, sul suo render."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        albero = self._albero(vista)
        passo, render = self._passo_di_partenza(albero, dati.get("da"))
        inserti = self._inserti_scelti(dati)
        destinazione = self.destinazione(str(dati.get("modello") or ""), inserti=len(inserti))
        return self._metti_in_coda(
            vista, blocchi.Scelte(scena=self._scena(albero, passo)), destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=None, prompt_a_mano=None,
            parte_da=passo["identificativo"], partenza=render,
            richieste=[str(dati.get("testo") or "")],
            inserti=inserti,
        )

    def _unione(self, albero: modulo_passi.Albero, identificativo: str) -> dict:
        """Le richieste della strada di un passo, unite per un invio solo dalla vista."""
        strada = albero.strada(str(identificativo or ""))
        if not strada:
            raise RichiestaStudioNonValida(
                f"Nell'albero di questa vista non c'e' il passo {identificativo!r}.",
                "Scegli un passo nell'albero.",
            )
        if len(strada) < 2:
            raise RichiestaStudioNonValida(
                "Questo passo e' partito dalla vista: non ci sono richieste da unire.",
                "Per rifarlo uguale usa Variante, sotto l'immagine.",
            )
        base = strada[0]
        if not base.get("scelte"):
            raise RichiestaStudioNonValida(
                f"Il primo passo della strada, il {base.get('numero')}, non e' partito dalla "
                "vista: il suo punto di partenza non c'e' piu', e non so con quale stile.",
                "Genera di nuovo dalla vista in Genera, poi rifai i passi.",
            )
        scelte = blocchi.Scelte.da_dizionario(base["scelte"])
        # Le note di un ritocco entrano come richieste a parole: dalla vista
        # le aree non valgono piu', erano disegnate su un render. Lo si dice.
        richieste = [r for p in strada for r in _richieste_del_passo(p)]
        senza_aree = [str(p.get("numero")) for p in strada if p.get("aree")]
        testo_base = (base.get("prompt_a_mano") or "").strip() or blocchi.componi(scelte)
        prompt = blocchi.aggiungi_richieste(testo_base, richieste)
        return {
            "scelte": scelte,
            "preset": base.get("preset"),
            "prompt_a_mano": base.get("prompt_a_mano"),
            "richieste": richieste,
            "prompt": prompt,
            "strada": ["0"] + [str(p.get("numero")) for p in strada],
            "generazioni": len(strada),
            "senza_aree": senza_aree,
        }

    def componi_pulito(self, dati: dict) -> dict:
        """Il prompt di «Rifai pulito dalla vista», da mostrare prima dell'invio."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        unione = self._unione(self._albero(vista), dati.get("passo"))
        return {
            "prompt": unione["prompt"],
            "caratteri": len(unione["prompt"]),
            "richieste": unione["richieste"],
            "strada": unione["strada"],
            "generazioni": unione["generazioni"],
            "riassunto": riassunto(unione["scelte"], unione["preset"]),
            "senza_aree": unione["senza_aree"],
        }

    def invia_pulito(self, dati: dict) -> dict:
        """«Rifai pulito dalla vista»: le richieste della strada in un solo invio dalla vista Allplan."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        unione = self._unione(self._albero(vista), dati.get("passo"))
        destinazione = self.destinazione(str(dati.get("modello") or ""))
        return self._metti_in_coda(
            vista, unione["scelte"], destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=unione["preset"] or None,
            prompt_a_mano=unione["prompt_a_mano"],
            richieste=unione["richieste"],
        )

    # --- ritocco ---------------------------------------------------------

    def _ritocco(self, dati: dict) -> tuple[Path, modulo_passi.Albero, dict, Path, tuple]:
        """Vista, albero, passo da ritoccare, il suo render e le aree della richiesta.

        I Rif. citati dalle note si leggono con _inserti_scelti: una nota che
        cita un Rif. che non c'e' si ferma qui, prima di comporre. Con
        `testo` (il compositore: una frase con @1, @2) le note delle aree le
        scrive modulo_aree.da_testo.
        """
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        albero = self._albero(vista)
        passo, render = self._passo_di_partenza(albero, dati.get("da"))
        try:
            elenco = dati.get("aree")
            if "testo" in dati:
                elenco = modulo_aree.da_testo(dati.get("testo"), elenco)
            aree = modulo_aree.da_elenco(elenco)
        except modulo_aree.AreaNonValida as errore:
            raise RichiestaStudioNonValida(errore.fatto, errore.cosa_fare) from None
        quanti = len(self._inserti_scelti(dati))
        for numero, area in enumerate(aree, start=1):
            if area.inserto is not None and area.inserto > quanti:
                raise RichiestaStudioNonValida(
                    f"La nota {numero} usa il Rif. {area.inserto}, che non c'e'.",
                    "Aggiungi l'immagine alla nota, oppure togli il Rif. dalla nota.")
        return vista, albero, passo, render, aree

    def componi_ritocco(self, dati: dict) -> dict:
        """Il prompt di un ritocco, da mostrare prima di Applica."""
        _vista, albero, passo, _render, aree = self._ritocco(dati)
        inserti = self._inserti_scelti(dati)
        prompt = blocchi.aggiungi_inserti(
            modulo_aree.prompt(config.RITOCCO_MODO_AREE, aree),
            modulo_coda.prima_immagine_inserti(config.RITOCCO_MODO_AREE == modulo_aree.MASCHERA, False, 0),
            len(inserti))
        return {
            "prompt": prompt,
            "caratteri": len(prompt),
            "note": len(aree),
            "note_aree": [a.nota for a in aree],
            "modo": config.RITOCCO_MODO_AREE,
            "modo_nome": modulo_aree.NOMI_MODI[config.RITOCCO_MODO_AREE],
            "da_numero": str(passo.get("numero")),
            "ramo_nuovo": bool(albero.figli(passo["identificativo"])),
            "generazioni": albero.generazioni(passo["identificativo"]) + 1,
        }

    def invia_ritocco(self, dati: dict) -> dict:
        """Tutte le note in un invio solo, sul render del passo: il risultato e' un passo figlio."""
        vista, albero, passo, render, aree = self._ritocco(dati)
        inserti = self._inserti_scelti(dati)
        destinazione = self.destinazione(str(dati.get("modello") or ""), inserti=len(inserti))
        return self._metti_in_coda(
            vista, blocchi.Scelte(scena=self._scena(albero, passo)), destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=None, prompt_a_mano=None,
            parte_da=passo["identificativo"], partenza=render,
            aree=aree, modo_aree=config.RITOCCO_MODO_AREE,
            inserti=inserti,
        )

    # --- Finale ----------------------------------------------------------

    def _finale(self, dati: dict) -> tuple[Path, dict, Path, dict]:
        """Vista, passo di partenza, il suo render e {ingrandimento, tipo} chiesti."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        passo, render = self._passo_di_partenza(self._albero(vista), dati.get("da"))
        ingrandimento = dati.get("ingrandimento", config.FINALE_INGRANDIMENTO_PREDEFINITO)
        tipo = dati.get("tipo") or "foto"
        if ingrandimento not in config.FINALE_INGRANDIMENTI or isinstance(ingrandimento, bool) \
                or tipo not in NOMI_TIPI_FINALE:
            raise RichiestaStudioNonValida(
                "«Finale» ingrandisce di " + " o ".join(f"{n} volte" for n in config.FINALE_INGRANDIMENTI)
                + ", per una foto o un'illustrazione.",
                "Scegli una delle voci di «Finale».")
        return vista, passo, render, {"ingrandimento": int(ingrandimento), "tipo": tipo}

    def componi_finale(self, dati: dict) -> dict:
        """Cosa fa «Finale», prima di Applica: misura di partenza e d'uscita, destinazione, costo."""
        _vista, passo, render, finale = self._finale(dati)
        larghezza, altezza = modulo_immagine.dimensioni(modulo_immagine.leggi(render))
        n = finale["ingrandimento"]
        return {
            "da_numero": str(passo.get("numero")),
            "partenza": f"{larghezza} × {altezza}",
            "uscita": f"{larghezza * n} × {altezza * n}",
            "riassunto": _riassunto_finale(finale),
            "destinazione": self.destinazione(MODELLO_FINALE.identificativo),
        }

    def invia_finale(self, dati: dict) -> dict:
        """«Finale» sul render di un passo: il risultato e' un passo figlio, ingrandito."""
        vista, passo, render, finale = self._finale(dati)
        destinazione = self.destinazione(MODELLO_FINALE.identificativo)
        return self._metti_in_coda(
            vista, blocchi.Scelte(scena=self._scena(self._albero(vista), passo)), destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=None, prompt_a_mano=None,
            parte_da=passo["identificativo"], partenza=render,
            finale=finale,
        )

    # --- cartella --------------------------------------------------------

    # --- video (Studio · Video) -------------------------------------------

    def catalogo_video(self) -> dict:
        """Modello, modi, movimenti, durate e dove va: tutto quello che la scheda Video mostra prima del clic."""
        motore = self._crea_provider(comfy.ProviderComfy.nome)
        return {
            "modello": modulo_video.MODELLO,
            "modello_nome": modulo_video.NOME_MODELLO,
            "fornitore": modulo_video.FORNITORE,
            "destinazione": motore.destinazione_per(modulo_video.MODELLO),
            "senza_ripiego": comfy.FALLBACK == "false",
            "fa_video": motore.fa_video(),
            "avviso": (f"{modulo_video.MODELLO} non è ancora stato provato con una chiamata vera: "
                       "il primo video è la prova. Se il servizio lo rifiuta, l'errore lo dice."),
            "costo": "non ancora misurato, nessun video fatto",
            "modi": [{"id": k, "nome": n, "spiega": d, "minimo": modulo_video.QUANTE[k][0],
                      "massimo": modulo_video.QUANTE[k][1]} for k, (n, d) in modulo_video.MODI.items()],
            "movimenti": [{"id": k, "nome": n} for k, (n, _testo) in modulo_video.MOVIMENTI.items()],
            "durate": list(config.VIDEO_DURATE_SECONDI),
            "risoluzioni": list(config.VIDEO_RISOLUZIONI),
            "origine": config.SCELTA,
        }

    def carica_immagine_video(self, dati: bytes, nome_originale: str = "") -> dict:
        """Un render caricato per un video: JPEG o PNG, sotto il peso che si manda al servizio."""
        massimo = config.COMFY_INVIO_MASSIMO_MB
        if len(dati) > massimo * _BYTE_PER_MB:
            raise RichiestaStudioNonValida(
                f"L'immagine pesa {_numero(len(dati) / _BYTE_PER_MB, 1)} MB, ne mandiamo al massimo {massimo}.",
                "Riducila o salvala in JPEG, poi caricala di nuovo.",
            )
        tipo = comfy.tipo_mime(dati)
        if tipo not in ("image/png", "image/jpeg"):
            raise RichiestaStudioNonValida("Per il video serve un JPEG o un PNG.",
                                           "Salva il render in JPEG o PNG, poi caricalo di nuovo.")
        larghezza, altezza = modulo_immagine.dimensioni(dati)
        estensione = ".jpg" if tipo == "image/jpeg" else ".png"
        nome = f"vid-{impronta(dati)[:16]}{estensione}"  # numero-non-configurabile: 64 bit di impronta bastano a non confondere due immagini
        cartella = modulo_video.cartelle(self.cartella)[modulo_video.IMMAGINI]
        if not (cartella / nome).exists():
            modulo_coda.scrivi_atomico(cartella / nome, dati)
        return {"nome": nome, "da": nome_originale, "larghezza": larghezza, "altezza": altezza}

    def percorso_immagine_video(self, nome: str) -> Path:
        if not re.fullmatch(r"vid-[0-9a-f]{16}\.(jpg|png)", nome or ""):
            raise RichiestaStudioNonValida(f"\"{nome}\" non e' un'immagine caricata per un video.",
                                           "Caricala di nuovo con «Carica un render…».")
        percorso = modulo_video.cartelle(self.cartella)[modulo_video.IMMAGINI] / nome
        if not percorso.is_file():
            raise FileNonTrovato(f"L'immagine {nome} non c'e' piu'.", "Caricala di nuovo.")
        return percorso

    def _immagine_video(self, voce: object) -> Path:
        """Un posto della scheda Video: un render dello Studio o un'immagine caricata."""
        if isinstance(voce, dict) and voce.get("render"):
            return self.file_render(str(voce["render"]))
        if isinstance(voce, dict) and voce.get("caricata"):
            return self.percorso_immagine_video(str(voce["caricata"]))
        raise RichiestaStudioNonValida("Un posto della scheda Video e' vuoto.",
                                       "Carica un render, oppure togli il posto vuoto.")

    def _richiesta_video(self, dati: dict) -> tuple[list[Path], dict]:
        immagini = [self._immagine_video(v) for v in (dati.get("immagini") or [])]
        try:
            durata = int(dati.get("durata") or config.VIDEO_DURATE_SECONDI[0])
        except (TypeError, ValueError):
            durata = -1
        scelte = {
            "modo": str(dati.get("modo") or "primo"),
            "movimento": str(dati.get("movimento") or "avanza"),
            "testo": str(dati.get("testo") or ""),
            "durata": durata,
            "risoluzione": str(dati.get("risoluzione") or config.VIDEO_RISOLUZIONI[0]),
            "audio": bool(dati.get("audio")),
        }
        return immagini, scelte

    def prova_a_secco_video(self, dati: dict) -> dict:
        """Cosa partirebbe e cosa lo fermerebbe, senza mandare."""
        problemi = []
        catalogo = self.catalogo_video()
        prompt, quante = "", 0
        try:
            immagini, scelte = self._richiesta_video(dati)
            quante = len(immagini)
            if scelte["modo"] == "sequenza":
                # Due tratti primo-ultimo: il prompt e' lo stesso per entrambi.
                if quante != 3:  # numero-non-configurabile: inizio, intermezzo, fine
                    raise modulo_video.VideoNonValido(
                        f"«{modulo_video.MODI['sequenza'][0]}» vuole 3 immagini, ne hai scelte {quante}.",
                        "Scegli il render di inizio, quello di mezzo e quello di fine.")
                richiesta = modulo_video.RichiestaVideo(identificativo="prova", immagini=tuple(map(str, immagini[:2])),
                                                        **{**scelte, "modo": "primo-ultimo"})
            else:
                richiesta = modulo_video.RichiestaVideo(identificativo="prova", immagini=tuple(map(str, immagini)), **scelte)
            prompt = richiesta.prompt()
            motore = self._crea_provider(comfy.ProviderComfy.nome)
            motore.controlla_video([percorso.read_bytes() for percorso in immagini])
            if not catalogo["fa_video"]:
                problemi.append({"fatto": f"{motore.destinazione} non fa video.", "cosa_fare": "Usa il servizio comfy."})
        except ErroreAirender as errore:
            problemi.append(_errore_dict(errore))
        if not self._coda_attiva():
            problemi.append(_CODA_FERMA)
        return {"inviato": False, "prompt": prompt, "caratteri": len(prompt), "immagini": quante,
                "destinazione": catalogo["destinazione"], "problemi": problemi}

    def invia_video(self, dati: dict) -> dict:
        """Mette un video in coda. Solo se la destinazione e' quella che la pagina ha mostrato (regola 5)."""
        catalogo = self.catalogo_video()
        if dati.get("destinazione_mostrata") != catalogo["destinazione"]:
            raise RichiestaStudioNonValida(
                f"La pagina ha mostrato come destinazione {dati.get('destinazione_mostrata')!r}, ma le "
                f"immagini partirebbero verso {catalogo['destinazione']}. Non ho inviato niente.",
                "Ricarica lo Studio: la destinazione si rilegge e si mostra di nuovo.",
            )
        immagini, scelte = self._richiesta_video(dati)
        if scelte["modo"] == "sequenza":
            tratti = modulo_video.metti_in_coda_sequenza(self.cartella, immagini, **{k: v for k, v in scelte.items() if k != "modo"})
            return {"identificativo": tratti[0].identificativo, "tratti": [t.identificativo for t in tratti],
                    "destinazione": catalogo["destinazione"], "coda_attiva": self._coda_attiva()}
        richiesta = modulo_video.metti_in_coda(self.cartella, immagini, **scelte)
        return {"identificativo": richiesta.identificativo, "destinazione": catalogo["destinazione"],
                "coda_attiva": self._coda_attiva()}

    def video(self) -> list[dict]:
        """I video della cartella, il piu' recente per primo, come li mostra la scheda."""
        voci = []
        for voce in modulo_video.elenco(self.cartella):
            richiesta = voce.get("richiesta") or {}
            voci.append({
                "identificativo": voce.get("identificativo"),
                "stato": voce.get("stato"),
                "aggiornato_il": voce.get("aggiornato_il"),
                "fatto": voce.get("fatto"),
                "cosa_fare": voce.get("cosa_fare"),
                "pronto": voce.get("stato") == modulo_video.FATTO and bool(voce.get("video")),
                "crediti_usati": voce.get("crediti_usati"),
                "modo": modulo_video.MODI.get(richiesta.get("modo"), ("",))[0],
                "movimento": modulo_video.MOVIMENTI.get(richiesta.get("movimento"), ("",))[0],
                "durata": richiesta.get("durata"),
                "risoluzione": richiesta.get("risoluzione"),
                "immagini": len(richiesta.get("immagini") or []),
                "sequenza": richiesta.get("sequenza") or None,
                "tratto": richiesta.get("tratto") or None,
            })
        return voci

    def file_video(self, identificativo: str) -> Path:
        if not re.fullmatch(r"[0-9A-Za-z-]+", identificativo or ""):
            raise RichiestaStudioNonValida("Questo video non esiste.", "Ricarica la scheda Video.")
        percorso = modulo_video.cartelle(self.cartella)["video"] / f"{identificativo}.mp4"
        if not percorso.is_file():
            raise FileNonTrovato(f"Il video {identificativo} non c'e' nella cartella video.",
                                 "Forse e' ancora in lavorazione, o e' stato spostato.")
        return percorso

    def annulla_video(self, identificativo: str) -> dict:
        if modulo_video.annulla(self.cartella, identificativo):
            return {"annullato": True}
        raise RichiestaStudioNonValida("Il video e' gia' partito: il servizio lo fa comunque.",
                                       "Aspetta che finisca; il costo e' gia' preso.")

    def apri_cartella(self, quale: str) -> dict:
        if quale == "esportati":
            percorso = self.cartella_esportati()
            percorso.mkdir(parents=True, exist_ok=True)
        elif quale == "video":
            percorso = modulo_video.cartelle(self.cartella)["video"]
        else:
            percorso = self.percorsi[modulo_coda.FATTO_DIR] if quale == "render" else self.cartella
        try:
            self._apri(percorso)
        except OSError as errore:
            raise RichiestaStudioNonValida(
                f"Il sistema non ha aperto la cartella {percorso}: {errore}.",
                "Aprila a mano dall'esplora file.",
            ) from None
        return {"aperta": str(percorso)}


def _nome_livello(passo: dict) -> str:
    """Il nome di un livello del PSD: il numero del passo e cosa e' stato chiesto."""
    if passo.get("aree"):
        cosa = "ritocco per aree"
    elif passo.get("richieste"):
        cosa = modulo_passi.nome_breve("; ".join(passo["richieste"]))
    elif passo.get("preset") in blocchi.PRESET_STILE:
        cosa = blocchi.PRESET_STILE[passo["preset"]].nome
    else:
        cosa = "scelte libere"
    return f"{passo.get('numero', '?')} · {cosa}"


def _miniatura_dict(preset: str, voce: dict | None) -> dict | None:
    """Cosa la pagina sa di una miniatura vera: dove prenderla e da quando e' un render vero."""
    if voce is None:
        return None
    try:
        quando = datetime.fromisoformat(str(voce.get("data"))).strftime("%d/%m/%Y")
    except ValueError:
        quando = str(voce.get("data") or "")
    return {"url": f"/file/miniatura/{preset}", "data": quando, "modello": voce.get("modello")}


def _richieste_del_passo(passo: dict) -> list[str]:
    """Le richieste a parole di un passo; per un ritocco, le sue note."""
    if passo.get("aree"):
        return [str(a.get("nota") or "") for a in passo["aree"] if isinstance(a, dict)]
    return list(passo.get("richieste") or [])


# Come lo storico chiama ogni immagine: una o due parole.
_ETICHETTE_STORICO = {"stile": "Render", "pulito": "Render", "passo": "Cambia", "ritocco": "Ritocco"}


def _tipo_passo(passo: dict) -> str:
    """stile (dalla vista), passo (da un render), ritocco (aree e note su un render),
    pulito (dalla vista con le richieste di una strada)."""
    if passo.get("aree"):
        return "ritocco"
    if (passo.get("partenza") or {}).get("passo", modulo_passi.VISTA) != modulo_passi.VISTA:
        return "passo"
    return "pulito" if passo.get("richieste") else "stile"


def _nome_stile(passo: dict) -> str:
    preset = blocchi.PRESET_STILE.get(passo.get("preset") or "")
    return preset.nome if preset else "Scelte libere"


def _nome_passo(passo: dict) -> str:
    """Il nome breve della riga: dalle scelte, o dalla richiesta."""
    tipo = _tipo_passo(passo)
    if tipo == "ritocco":
        note = _richieste_del_passo(passo)
        quante = "1 nota" if len(note) == 1 else f"{len(note)} note"
        return modulo_passi.nome_breve(f"Ritocco · {quante} · {note[0] if note else ''}")
    if tipo == "passo":
        breve = modulo_passi.nome_breve((passo.get("richieste") or [""])[0])
        return breve[:1].upper() + breve[1:] if breve else "Passo senza richiesta"
    if tipo == "pulito":
        return f"Tutto dalla vista · {_nome_stile(passo)}"
    return _nome_stile(passo)


def _riassunto_passo(passo: dict, padre: dict | None) -> str:
    """La richiesta del passo, in italiano, come la legge l'utente nella ricetta."""
    tipo = _tipo_passo(passo)
    richieste = passo.get("richieste") or []
    if tipo == "ritocco":
        numero = padre.get("numero") if padre else "?"
        note = _richieste_del_passo(passo)
        return f"Ritocco del passo {numero}: " + "; ".join(
            f"area {i}, {n}" for i, n in enumerate(note, start=1))
    if tipo == "passo":
        numero = padre.get("numero") if padre else "?"
        return f"Dal passo {numero}: " + "; ".join(richieste)
    try:
        testo = riassunto(blocchi.Scelte.da_dizionario(passo.get("scelte") or {}), passo.get("preset"))
    except ErroreAirender:
        testo = _nome_stile(passo)
    if tipo == "pulito":
        testo += " Più le richieste della strada: " + "; ".join(richieste) + "."
    return testo


def _costo_passo(passo: dict, modello: Modello | None) -> str:
    """Il costo letto dal servizio, se c'e'; altrimenti la stima del modello, detta come stima."""
    crediti = passo.get("costo_crediti")
    if isinstance(crediti, (int, float)):
        return f"{_numero(float(crediti))} crediti"
    if passo.get("stato") in STATI_ATTIVI:
        if modello is None or modello.costo_crediti is None:
            return "non misurato"
        return f"circa {round(modello.costo_crediti)} crediti (stima, il servizio non l'ha ancora detto)"
    return "non letto dal servizio"


def numero_varianti(valore: object) -> int:
    """Quante varianti: un intero da 1 a VARIANTI_MASSIME, altrimenti si rifiuta."""
    massimo = config.VARIANTI_MASSIME
    try:
        quante = int(valore)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        quante = 0
    if isinstance(valore, bool) or str(valore).strip() != str(quante) or not 1 <= quante <= massimo:
        raise RichiestaStudioNonValida(
            f"\"{valore}\" non e' un numero di varianti: lo Studio ne fa da 1 a {massimo} per invio.",
            f"Scegli 1, 2, 3 o {massimo} varianti.",
        )
    return quante


def testo_costo(modello: Modello, varianti: int = 1) -> str:
    """Il costo da scrivere prima di Genera: per uno, o N volte uno, mai un numero non misurato."""
    if modello.costo_crediti is None:
        return "non misurato: nessuna generazione con questo modello ha copiato i crediti"
    data = f"misurato il {modello.costo_misurato_il}"
    if varianti == 1:
        return (f"circa {round(modello.costo_crediti)} crediti per immagine · {data} "
                f"({_numero(modello.costo_crediti)} crediti)")
    totale = modello.costo_crediti * varianti
    return (f"circa {round(totale)} crediti per {varianti} immagini "
            f"({varianti} × {_numero(modello.costo_crediti)}) · {data}")


_CODA_FERMA = {
    "fatto": "La coda dei lavori non sta girando: il lavoro resterebbe in attesa.",
    "cosa_fare": (
        "Chiudi e riapri lo Studio, che la fa partire; oppure lanciala a mano "
        "con python -m core.coda --cartella <la cartella delle viste>."
    ),
}


def _e_numero(valore: object) -> bool:
    try:
        float(valore)  # type: ignore[arg-type]
        return True
    except (TypeError, ValueError):
        return False


def _prompt_a_mano(dati: dict) -> str | None:
    testo = dati.get("prompt_a_mano")
    if isinstance(testo, str) and testo.strip():
        return testo.strip()
    return None


def _riassunto_finale(finale: dict) -> str:
    """«Finale», in italiano, sempre con le stesse parole."""
    tipo = NOMI_TIPI_FINALE.get(str(finale.get("tipo")), str(finale.get("tipo"))).lower()
    return f"Finale: render ingrandito {finale.get('ingrandimento')} volte, con più dettaglio, come {tipo}."


def _prompt_genera(a_mano: str | None, scelte, contesto, stile: int, esempi: int, cambi: tuple, inserti: int,
                   geometria: bool = False) -> str:
    """Il prompt di Genera: blocchi (o testo a mano), stile, materiali, Rif. Un posto solo per componi e prova a secco."""
    if a_mano:
        prompt = a_mano
    else:
        prompt = contesto.prompt(scelte.materiali) if contesto else blocchi.componi(scelte)
    if stile and not contesto:
        prompt = blocchi.aggiungi_riferimento(prompt, esempi=esempi)
    if not a_mano:
        prompt = modulo_materiali.prompt(prompt, cambi, prima_immagine=modulo_materiali.prima_immagine(stile))
    if geometria and not contesto:
        prompt = f"{prompt}\n\n{modulo_geometria.REGOLA_PROMPT}"
    return blocchi.aggiungi_inserti(prompt, modulo_coda.prima_immagine_inserti(
        False, stile, modulo_materiali.quante_immagini(cambi)), inserti)


def _geometria_dict(varianti: int, provider: str = "") -> dict:
    """La prima passata di «Tieni la geometria»: dove va e cosa costa, prima del clic (regola 5)."""
    try:
        dove, errore, cosa_fare = modulo_geometria.destinazione(provider), None, None
    except ErroreAirender as problema:
        dove, errore, cosa_fare = None, problema.fatto, problema.cosa_fare
    return {
        "destinazione": dove,
        "errore": errore,
        "cosa_fare": cosa_fare,
        "workflow": modulo_geometria.NOME_WORKFLOW,
        "cosa_parte": ("Prima la vista va da sola al workflow col ControlNet sugli spigoli; "
                       "poi il suo render parte verso il modello al posto della vista."),
        "costo": _costo_geometria(varianti, provider),
    }


def _costo_geometria(varianti: int, provider: str) -> str:
    """Coi crediti AIRENDER il listino dice quanto; con la chiave propria nessun numero (regola 3)."""
    if provider == modulo_geometria.PROVIDER_AIRENDER:
        peso = modulo_geometria.peso_airender() * varianti
        prime = "la prima passata" if varianti == 1 else f"{varianti} prime passate"
        return (f"{peso} render AIRENDER in più per {prime} (prezzo provvisorio), "
                "scalati solo se il workflow riesce")
    # Un workflow con la chiave propria si paga a secondi di GPU del deployment, non a immagine.
    return ("a secondi di GPU del deployment" if varianti == 1
            else f"{varianti} prime passate, a secondi di GPU del deployment")


def _cosa_parte(riferimento: bool, contesto: bool, materiali: int = 0, inserti: int = 0, esempi: int = 0) -> str:
    """Quante immagini partono e quali, nelle stesse parole ogni volta (regola 5)."""
    if esempi and riferimento:
        pezzi = ["la vista", f"{1 + esempi} esempi di stile"]
        if materiali:
            pezzi.append("1 immagine dei materiali" if materiali == 1 else f"{materiali} immagini dei materiali")
        if inserti:
            pezzi.append("1 Rif. di oggetti e persone" if inserti == 1 else f"{inserti} Rif. di oggetti e persone")
        quante = 2 + esempi + materiali + inserti
        return f"Partono {quante} immagini: " + ", ".join(pezzi[:-1]) + " e " + pezzi[-1] + "."
    if inserti:
        pezzi = ["la vista o il render di partenza"]
        if riferimento:
            pezzi.append("il riferimento per lo stile")
        if materiali:
            pezzi.append("1 immagine dei materiali" if materiali == 1 else f"{materiali} immagini dei materiali")
        pezzi.append("1 Rif. di oggetti e persone" if inserti == 1 else f"{inserti} Rif. di oggetti e persone")
        quante = 1 + int(riferimento) + materiali + inserti
        return f"Partono {quante} immagini: " + ", ".join(pezzi[:-1]) + " e " + pezzi[-1] + "."
    if materiali:
        prima = "la vista e il riferimento per lo stile" if riferimento else "la vista"
        quante = (2 if riferimento else 1) + materiali
        immagini = "1 immagine" if materiali == 1 else f"{materiali} immagini"
        return (f"Partono {quante} immagini: {prima}, poi {immagini} dei materiali da cambiare "
                "(campioni dei materiali e foto di riferimento).")
    if contesto:
        return ("Partono due immagini: prima il contesto con l'area segnata in magenta, "
                "poi la vista.")
    if riferimento:
        return "Partono due immagini: la vista e il riferimento per lo stile."
    return "Parte una immagine: la vista."


def riassunto_contesto(contesto: modulo_contesto.Contesto, materiali: str = "") -> str:
    """Cosa parte con «Fotoinserimento», in italiano."""
    pezzi = ["Fotoinserimento", blocchi.INQUADRATURE[contesto.inquadratura].nome.lower()]
    pezzi.append(f"materiali: {materiali.strip()}" if materiali and materiali.strip()
                 else "materiali: li sceglie il modello")
    if contesto.luogo:
        pezzi.append(f"luogo: {contesto.luogo}")
    pezzi.append("lo screenshot diventa una foto" if contesto.pulisci_mappa
                 else "fuori dall'area il contesto resta com'è")
    return " · ".join(pezzi)


def riassunto(scelte: blocchi.Scelte, preset: str | None = None) -> str:
    """Le scelte in italiano, nell'ordine in cui partono i blocchi."""
    fedelta = scelte.fedelta or blocchi.FEDELTA_PREDEFINITA
    regola = "Regola fissa" if fedelta == blocchi.FEDELTA_PREDEFINITA \
        else f"Fedeltà al disegno {blocchi.blocco('fedelta', fedelta, scelte.scena).nome.lower()}"
    pezzi = [regola, blocchi.SCENA[scelte.scena].nome.lower() if scelte.scena in blocchi.SCENA else scelte.scena]
    resa = blocchi.resa_valida(scelte.resa)
    via = blocchi.SPENTI_DA_RESA[resa]
    if scelte.materiali.strip() and "materiali" not in via:
        pezzi.append("i tuoi materiali")
    origine = blocchi.PRESET_STILE.get(preset or "")
    if origine is not None:
        pezzi.append(f"preset {origine.nome}")
    etichette = {
        "look": "{}",
        "luce": "{}",
        "cielo": "cielo {}",
        "fuori": "{}",
        "arredo": "{}",
        "sfondo": "{}",
        "intorno": "intorno: {}",
        "verde": "verde: {}",
        "persone": "persone: {}",
        "qualita": "qualità {}",
    }
    if resa != blocchi.FOTO:
        pezzi.append(f"resa {blocchi.NOMI_RESE[resa].lower()}")
    for asse, forma in etichette.items():
        valore = getattr(scelte, asse)
        if valore and asse not in via:
            nome = blocchi.blocco(asse, valore, scelte.scena).nome
            pezzi.append(forma.format(nome if asse == "look" else nome.lower()))
    pezzi.append("cosa evitare")
    return " · ".join(pezzi) + "."
