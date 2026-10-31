"""Quello che lo Studio sa fare, senza HTTP.

Ogni metodo pubblico prende e restituisce dizionari semplici, quelli che il
server manda alla pagina come JSON. Un errore e' sempre un ErroreAirender,
con il fatto e il gesto successivo: il server lo passa alla pagina com'e'.

La cartella dello Studio e' la cartella delle viste: la palette ci salva le
viste, la coda ci tiene `lavori/`. Lo Studio la legge e ci scrive lavori, e
non tocca nient'altro.
"""

from __future__ import annotations

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
from .. import passi as modulo_passi
from .. import preset_utente
from .. import provider as registro
from ..errori import ErroreAirender, FileNonTrovato
from ..idoneita import valuta
from ..preset import MODELLI_PREDEFINITI
from ..provider import comfy
from ..provider.base import Provider
from ..ricetta import Ricetta, impronta
from . import miniature as modulo_miniature


class RichiestaStudioNonValida(ErroreAirender):
    """La pagina ha chiesto qualcosa che non esiste o non torna."""


ESTENSIONI_VISTA = (".png", ".jpg", ".jpeg")
_BYTE_PER_MB = 1024 * 1024  # numero-non-configurabile: definizione di MB
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


MODELLI = (
    Modello(
        MODELLI_PREDEFINITI["comfy"], "Nano Banana 2", "Google",
        costo_crediti=config.COSTO_NANO_BANANA_2_CREDITI, costo_misurato_il="27/10/2026",
    ),
    Modello("bfl/flux-kontext-pro", "FLUX.1 Kontext Pro", "Black Forest Labs"),
    # Costo non ancora misurato: lo dira' il primo render.
    Modello("vertexai/gemini-3-pro-image", "Nano Banana Pro", "Google"),
)
# Scritti a schermo e non selezionabili: il loro schema non e' verificato.
MODELLI_NON_PROVATI = ("Seedream", "GPT Image")

# Come lo Studio chiama quello che una resa spegne.
_NOMI_SPENTI = {
    "materiali": "materiali a parole", "look": "look fotografico", "luce": "luce",
    "cielo": "cielo", "fuori": "fuori dalle finestre", "intorno": "intorno",
    "verde": "verde", "persone": "persone", "qualita": "qualità",
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
    ) -> None:
        self.cartella = Path(cartella).resolve()
        self.cartella.mkdir(parents=True, exist_ok=True)
        self.provider = provider
        self._crea_provider = crea_provider
        self._coda_attiva = coda_attiva
        self._apri = apri
        self._adesso = adesso
        self.cartella_miniature = Path(cartella_miniature)
        self.percorsi = modulo_coda.cartelle(self.cartella)
        # Il server risponde a piu' richieste insieme: l'albero dei passi lo
        # allinea e lo scrive una richiesta alla volta.
        self._blocco_albero = threading.Lock()

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
            "ritocco": {
                "modo": config.RITOCCO_MODO_AREE,
                "modo_nome": modulo_aree.NOMI_MODI[config.RITOCCO_MODO_AREE],
                "origine": config.costante("RITOCCO_MODO_AREE").origine,
            },
        }

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
            "modelli": [self._modello_dict(m) for m in MODELLI],
            "modelli_non_provati": list(MODELLI_NON_PROVATI),
            "risoluzioni": [
                {"id": r, "nome": r.upper() + ("" if r == config.RISOLUZIONE_RENDER_PREDEFINITA else " · da provare")}
                for r in config.RISOLUZIONI_RENDER
            ],
        }

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
                {"id": b.identificativo, "nome": b.nome, "attivo": True, "origine": b.origine}
                for b in blocchi.voci(asse, scena).values()
            ]
            titolo = _TITOLI_ASSI[asse]
            if asse == "luce" and scena == blocchi.INTERNO:
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
        prompt = blocchi.componi(scelte)
        if dati.get("riferimento"):
            prompt = blocchi.aggiungi_riferimento(prompt)
        return {
            "prompt": prompt,
            "caratteri": len(prompt),
            "riassunto": riassunto(scelte, dati.get("preset")),
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
        for modello in MODELLI:
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
            "verificato": motore.cosa_manca(modello.identificativo) is None,
            "piu_immagini": motore.accetta_piu_immagini(modello.identificativo),
        }

    def destinazione(self, identificativo_modello: str, varianti: object = 1,
                     riferimento: bool = False) -> dict:
        """Dove va la vista e quanto costa, da mostrare prima di Genera (regola 5).

        Con N varianti il costo e' N volte quello di un render, e lo si dice
        cosi'. Se il costo del modello non e' misurato resta "non misurato".
        """
        modello = self._modello(identificativo_modello)
        quante = numero_varianti(varianti)
        motore = self._crea_provider(self.provider)
        senza_ripiego = self.provider == comfy.ProviderComfy.nome and comfy.FALLBACK == "false"
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
            "immagini": 2 if riferimento else 1,
            "cosa_parte": ("Partono due immagini: la vista e il riferimento per lo stile."
                           if riferimento else "Parte una immagine: la vista."),
            "riferimento_non_accettato": (
                f"{modello.nome} riceve una sola immagine per invio: il riferimento non partirebbe. "
                "Toglilo, oppure scegli Nano Banana 2."
                if riferimento and not motore.accetta_piu_immagini(modello.identificativo) else None),
            "avviso_riferimento": motore.avviso_piu_immagini(modello.identificativo) if riferimento else None,
        }

    # --- prova a secco e invio -------------------------------------------

    def prova_a_secco(self, dati: dict) -> dict:
        """Tutto quello che farebbe Genera, tranne mandare. Elenca cosa lo fermerebbe."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        scelte = self._scelte(dati.get("scelte"))
        riferimento = self._riferimento_scelto(dati)
        destinazione = self.destinazione(str(dati.get("modello") or ""), dati.get("varianti", 1),
                                         riferimento=riferimento is not None)
        prompt = _prompt_a_mano(dati) or blocchi.componi(scelte)
        if riferimento is not None:
            prompt = blocchi.aggiungi_riferimento(prompt)
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

    def invia(self, dati: dict) -> dict:
        """Scrive in coda un lavoro per variante. Solo se la destinazione e' quella che la pagina ha mostrato.

        Le varianti sono lavori con le stesse scelte: la coda li fa uno dopo
        l'altro, e ognuno e' un invio pagato. Il costo per N l'ha mostrato
        destinazione() prima del clic.
        """
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        scelte = self._scelte(dati.get("scelte"))
        riferimento = self._riferimento_scelto(dati)
        destinazione = self.destinazione(str(dati.get("modello") or ""), dati.get("varianti", 1),
                                         riferimento=riferimento is not None)
        return self._metti_in_coda(
            vista, scelte, destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=dati.get("preset") or None,
            prompt_a_mano=_prompt_a_mano(dati),
            varianti=destinazione["varianti"],
            riferimento=riferimento,
        )

    def _riferimento_scelto(self, dati: dict) -> Path | None:
        nome = dati.get("riferimento")
        return self.percorso_riferimento(str(nome)) if nome else None

    def _metti_in_coda(self, vista, scelte, destinazione, mostrata, preset, prompt_a_mano,
                       varianti: int = 1, parte_da: str | None = None,
                       partenza: Path | None = None, richieste=(), aree=(),
                       modo_aree: str | None = None, riferimento: Path | None = None) -> dict:
        if mostrata != destinazione["destinazione"]:
            raise RichiestaStudioNonValida(
                f"La pagina ha mostrato come destinazione {mostrata!r}, ma la vista "
                f"partirebbe verso {destinazione['destinazione']}. Non ho inviato niente.",
                "Ricarica lo Studio: la destinazione si rilegge e si mostra di nuovo.",
            )
        if destinazione["cosa_manca"]:
            raise RichiestaStudioNonValida(
                f"Non mando: {destinazione['cosa_manca']}",
                "Scegli Nano Banana 2, il modello predefinito, il cui schema e' verificato.",
            )
        if destinazione.get("riferimento_non_accettato"):
            raise RichiestaStudioNonValida(f"Non mando: {destinazione['riferimento_non_accettato']}",
                                           "Togli il riferimento, oppure scegli Nano Banana 2.")
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
                "Usa «Rifai pulito dalla vista»: riparte dalla vista Allplan con le "
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
        destinazione = self.destinazione(lavoro.modello, riferimento=riferimento is not None)
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
        modello = next((m for m in MODELLI if m.identificativo == dati.get("modello")), None)
        preset = blocchi.PRESET_STILE.get(dati.get("preset") or "")
        render = self._render(identificativo, stato)
        richieste = [r for r in (dati.get("richieste") or []) if isinstance(r, str)]
        try:
            scelte = blocchi.Scelte.da_dizionario(dati.get("scelte") or {})
            testo_riassunto = riassunto(scelte, dati.get("preset"))
        except ErroreAirender:
            testo_riassunto = ""
        if dati.get("partenza"):
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
                "Passo: " + modulo_passi.nome_breve(richieste[0]) if dati.get("partenza") and richieste
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

    def _albero(self, vista: Path) -> modulo_passi.Albero:
        """L'albero della vista, allineato ai lavori della cartella e scritto se e' cambiato."""
        with self._blocco_albero:
            albero = modulo_passi.Albero.leggi(vista)
            lavori = self._lavori_della_vista(vista)
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
        destinazione = self.destinazione(str(dati.get("modello") or ""))
        return self._metti_in_coda(
            vista, blocchi.Scelte(scena=self._scena(albero, passo)), destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=None, prompt_a_mano=None,
            parte_da=passo["identificativo"], partenza=render,
            richieste=[str(dati.get("testo") or "")],
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
                "Per rifarlo uguale usa «Rifai questo passo».",
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
        """Vista, albero, passo da ritoccare, il suo render e le aree della richiesta."""
        vista = self.percorso_vista(str(dati.get("vista") or ""))
        albero = self._albero(vista)
        passo, render = self._passo_di_partenza(albero, dati.get("da"))
        try:
            aree = modulo_aree.da_elenco(dati.get("aree"))
        except modulo_aree.AreaNonValida as errore:
            raise RichiestaStudioNonValida(errore.fatto, errore.cosa_fare) from None
        return vista, albero, passo, render, aree

    def componi_ritocco(self, dati: dict) -> dict:
        """Il prompt di un ritocco, da mostrare prima di Applica."""
        _vista, albero, passo, _render, aree = self._ritocco(dati)
        prompt = modulo_aree.prompt(config.RITOCCO_MODO_AREE, aree)
        return {
            "prompt": prompt,
            "caratteri": len(prompt),
            "note": len(aree),
            "modo": config.RITOCCO_MODO_AREE,
            "modo_nome": modulo_aree.NOMI_MODI[config.RITOCCO_MODO_AREE],
            "da_numero": str(passo.get("numero")),
            "ramo_nuovo": bool(albero.figli(passo["identificativo"])),
            "generazioni": albero.generazioni(passo["identificativo"]) + 1,
        }

    def invia_ritocco(self, dati: dict) -> dict:
        """Tutte le note in un invio solo, sul render del passo: il risultato e' un passo figlio."""
        vista, albero, passo, render, aree = self._ritocco(dati)
        destinazione = self.destinazione(str(dati.get("modello") or ""))
        return self._metti_in_coda(
            vista, blocchi.Scelte(scena=self._scena(albero, passo)), destinazione,
            mostrata=dati.get("destinazione_mostrata"),
            preset=None, prompt_a_mano=None,
            parte_da=passo["identificativo"], partenza=render,
            aree=aree, modo_aree=config.RITOCCO_MODO_AREE,
        )

    # --- cartella --------------------------------------------------------

    def apri_cartella(self, quale: str) -> dict:
        percorso = self.percorsi[modulo_coda.FATTO_DIR] if quale == "render" else self.cartella
        try:
            self._apri(percorso)
        except OSError as errore:
            raise RichiestaStudioNonValida(
                f"Il sistema non ha aperto la cartella {percorso}: {errore}.",
                "Aprila a mano dall'esplora file.",
            ) from None
        return {"aperta": str(percorso)}


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
        return f"Pulito dalla vista · {_nome_stile(passo)}"
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


def riassunto(scelte: blocchi.Scelte, preset: str | None = None) -> str:
    """Le scelte in italiano, nell'ordine in cui partono i blocchi."""
    fedelta = scelte.fedelta or blocchi.FEDELTA_PREDEFINITA
    regola = "Regola fissa" if fedelta == blocchi.FEDELTA_PREDEFINITA \
        else f"Fedeltà al disegno {blocchi.FEDELTA[fedelta].nome.lower()}"
    pezzi = [regola, scelte.scena]
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
