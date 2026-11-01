"""Video da render: Studio · Video, con Seedance attraverso Comfy Router.

Decisione di Riccardo del 2026-10-31: «I video li voglio che possa caricare
i render fatti e costruirlo da quelle», con l'ultimo Seedance. Il modello e
il corpo della richiesta vengono dalla documentazione di Comfy Router (pagina
«code» di byteplus/dreamina-seedance-2-5-260628, letta il 2026-11-01). MAI
ESEGUITO: il primo video vero e' la prova, e lo Studio lo dice prima.

Un video e' un lavoro a parte, nella sua cartella `lavori/video/`, e lo fa
la stessa coda delle immagini quando non ha immagini da fare: una sola coda
per cartella, un solo processo che parla col servizio. Il file finito va in
`video/` nella cartella delle viste, con la sua ricetta accanto (senza
immagini e senza chiave).

Nessun import di Allplan: si prova con pytest.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config
from .coda import nuovo_identificativo, scrivi_atomico, scrivi_json
from .errori import ErroreAirender
from .provider import comfy
from .provider.base import Provider
from .ricetta import impronta

MODELLO = "byteplus/dreamina-seedance-2-5-260628"
NOME_MODELLO = "Seedance 2.5"
FORNITORE = "ByteDance"
DOCUMENTATO_IL = "2026-11-01"

CARTELLA_LAVORI = Path("lavori") / "video"
CARTELLA_VIDEO = "video"
IN_ATTESA, STATO, IMMAGINI = "in-attesa", "stato", "immagini"

IN_CODA, INVIATO, FATTO, ERRORE, ANNULLATO = "in coda", "inviato", "fatto", "errore", "annullato"

# Come si parte. I ruoli sono quelli di Seedance 2.5 (campo role di ogni immagine).
MODI = {
    "primo": ("Da un render", "Il video comincia dal render e la camera si muove."),
    "primo-ultimo": ("Da un render a un altro",
                     "Primo e ultimo fotogramma: il modello inventa il passaggio fra i due."),
    "riferimenti": ("Più render come riferimento",
                    "Il modello li usa per capire l'edificio ma non parte da nessuno: "
                    "è la scelta che tiene meno la geometria."),
}
# Quante immagini vuole ogni modo: (minimo, massimo).
QUANTE = {"primo": (1, 1), "primo-ultimo": (2, 2), "riferimenti": (1, config.VIDEO_RIFERIMENTI_MASSIMI)}  # numero-non-configurabile: primo e ultimo fotogramma sono uno ciascuno

# Il movimento della camera, scritto in inglese come il resto dei prompt.
MOVIMENTI = {
    "avanza": ("Avanza piano", "Slow, steady dolly-in towards the building, at eye level."),
    "gira": ("Gira attorno", "Slow orbit around the building, keeping it centred in the frame."),
    "panoramica": ("Panoramica", "Slow horizontal pan from left to right across the facade."),
    "drone": ("Sale come un drone", "Smooth drone shot rising up and slightly backwards, revealing the surroundings."),
    "ferma": ("Camera ferma", "Locked-off static camera. Only light, clouds, trees and people move."),
}

# La regola fissa: l'edificio non cambia. E' il problema noto dei video
# generati (le forme che si sciolgono), detto al modello in ogni invio.
REGOLA = ("Architectural visualization video. Keep the building exactly as in the images: "
          "same geometry, proportions, openings and materials. No morphing, no melting, "
          "no extra floors or windows. Realistic, physically plausible camera motion.")


class VideoNonValido(ErroreAirender):
    """Una richiesta di video che non si puo' mandare: lo dice prima, non al servizio."""


def _adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class RichiestaVideo:
    identificativo: str
    immagini: tuple[str, ...]
    modo: str = "primo"
    movimento: str = "avanza"
    testo: str = ""
    durata: int = config.VIDEO_DURATE_SECONDI[0]
    risoluzione: str = config.VIDEO_RISOLUZIONI[0]
    audio: bool = False
    modello: str = MODELLO
    creato_il: str = field(default_factory=_adesso)

    def __post_init__(self) -> None:
        if self.modo not in MODI:
            raise VideoNonValido(f"Il modo «{self.modo}» non esiste.", f"Scegli fra {', '.join(MODI)}.")
        if self.movimento not in MOVIMENTI:
            raise VideoNonValido(f"Il movimento «{self.movimento}» non esiste.",
                                 f"Scegli fra {', '.join(MOVIMENTI)}.")
        if self.durata not in config.VIDEO_DURATE_SECONDI:
            raise VideoNonValido(f"Una durata di {self.durata} secondi non c'e'.",
                                 f"Scegli fra {', '.join(str(d) for d in config.VIDEO_DURATE_SECONDI)} secondi.")
        if self.risoluzione not in config.VIDEO_RISOLUZIONI:
            raise VideoNonValido(f"La risoluzione {self.risoluzione} non c'e'.",
                                 f"Scegli fra {', '.join(config.VIDEO_RISOLUZIONI)}.")
        minimo, massimo = QUANTE[self.modo]
        if not minimo <= len(self.immagini) <= massimo:
            serve = str(minimo) if minimo == massimo else f"da {minimo} a {massimo}"
            raise VideoNonValido(
                f"«{MODI[self.modo][0]}» vuole {serve} immagini, ne hai scelte {len(self.immagini)}.",
                "Carica o togli un render, oppure cambia come partire.",
            )

    def prompt(self) -> str:
        parti = [REGOLA, MOVIMENTI[self.movimento][1]]
        if self.modo == "primo-ultimo":
            parti.append("Transition smoothly from the first frame to the last frame.")
        if self.testo.strip():
            parti.append(self.testo.strip())
        return " ".join(parti)


def corpo(richiesta: RichiestaVideo, immagini: list[bytes]) -> dict:
    """Il corpo di Seedance 2.5 come lo scrive la documentazione del Router.

    Le immagini sono data-URI con il formato in minuscolo. Con un primo
    fotogramma il rapporto dev'essere «adaptive»: il video prende la forma
    del render (un rapporto fisso darebbe un 400).
    """
    ruoli = {"primo": ("first_frame",), "primo-ultimo": ("first_frame", "last_frame")}.get(richiesta.modo)
    contenuto: list[dict] = [{"type": "text", "text": richiesta.prompt()}]
    for indice, dati in enumerate(immagini):
        ruolo = ruoli[indice] if ruoli else "reference_image"
        contenuto.append({"type": "image_url", "image_url": {"url": comfy.immagine_data_uri(dati)},
                          "role": ruolo})
    return {
        "content": contenuto,
        "duration": richiesta.durata,
        "resolution": richiesta.risoluzione,
        "ratio": "adaptive",
        "generate_audio": richiesta.audio,
        "watermark": False,
    }


def corpo_senza_immagini(dati: dict) -> dict:
    """Il corpo da salvare nella ricetta: le immagini diventano la loro impronta."""
    copia = json.loads(json.dumps(dati))
    for voce in copia.get("content", []):
        if voce.get("type") == "image_url":
            voce["image_url"] = {"url": "<immagine>"}
    return copia


# --- cartelle e stato ----------------------------------------------------------


def cartelle(radice: Path) -> dict[str, Path]:
    base = Path(radice) / CARTELLA_LAVORI
    percorsi = {nome: base / nome for nome in (IN_ATTESA, STATO, IMMAGINI)}
    percorsi["video"] = Path(radice) / CARTELLA_VIDEO
    for percorso in percorsi.values():
        percorso.mkdir(parents=True, exist_ok=True)
    return percorsi


def scrivi_stato(radice: Path, identificativo: str, stato: str, **altro) -> dict:
    percorso = cartelle(radice)[STATO] / f"{identificativo}.json"
    try:
        vecchio = json.loads(percorso.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        vecchio = {}
    dati = {**vecchio, "identificativo": identificativo, "stato": stato, "aggiornato_il": _adesso(), **altro}
    scrivi_json(percorso, dati)
    return dati


def elenco(radice: Path) -> list[dict]:
    """Tutti i video, il piu' recente per primo."""
    voci = []
    for percorso in cartelle(radice)[STATO].glob("*.json"):
        if percorso.name.startswith("."):
            continue
        try:
            voci.append(json.loads(percorso.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return sorted(voci, key=lambda v: v.get("identificativo", ""), reverse=True)


def metti_in_coda(radice: Path, immagini: list[Path], **scelte) -> RichiestaVideo:
    """Scrive la richiesta in lavori/video/in-attesa e lo stato «in coda»."""
    for percorso in immagini:
        if not Path(percorso).is_file():
            raise VideoNonValido(f"L'immagine {percorso} non c'e' piu'.", "Caricala di nuovo.")
    richiesta = RichiestaVideo(identificativo=nuovo_identificativo(),
                               immagini=tuple(str(p) for p in immagini), **scelte)
    percorsi = cartelle(radice)
    scrivi_json(percorsi[IN_ATTESA] / f"{richiesta.identificativo}.json", asdict(richiesta))
    scrivi_stato(radice, richiesta.identificativo, IN_CODA, richiesta=asdict(richiesta),
                 destinazione=f"{comfy.ProviderComfy.destinazione} → {richiesta.modello}")
    return richiesta


def annulla(radice: Path, identificativo: str) -> bool:
    """Toglie un video ancora in coda. Uno gia' partito non si ferma: il servizio lo fa comunque."""
    percorso = cartelle(radice)[IN_ATTESA] / f"{identificativo}.json"
    try:
        percorso.unlink()
    except FileNotFoundError:
        return False
    scrivi_stato(radice, identificativo, ANNULLATO, fatto="Annullato prima di partire: non e' stato inviato niente.")
    return True


class CodaVideo:
    """Fa i video uno alla volta. La chiama la coda delle immagini quando e' libera."""

    def __init__(self, radice: Path, crea_provider: Callable[[str], Provider],
                 dire: Callable[[str], None] = print) -> None:
        self.radice = Path(radice)
        self._crea_provider = crea_provider
        self._dire = dire

    def recupera_abbandonati(self) -> list[str]:
        """Un video «inviato» senza processo vivo non si rimanda: il servizio puo' averlo gia' fatto e addebitato."""
        persi = []
        for voce in elenco(self.radice):
            if voce.get("stato") == INVIATO:
                scrivi_stato(self.radice, voce["identificativo"], ERRORE,
                             fatto="La coda si e' fermata mentre il video era al servizio.",
                             cosa_fare="Controlla i crediti del workspace Comfy prima di rifarlo: "
                                       "se sono scesi, il video era partito.")
                persi.append(voce["identificativo"])
        return persi

    def esegui_uno(self) -> str | None:
        percorsi = cartelle(self.radice)
        for percorso in sorted(p for p in percorsi[IN_ATTESA].glob("*.json") if not p.name.startswith(".")):
            preso = percorso.with_suffix(".preso")
            try:
                os.rename(percorso, preso)
            except OSError:
                continue
            identificativo = percorso.stem
            try:
                self._fai(identificativo, json.loads(preso.read_text(encoding="utf-8")))
            finally:
                preso.unlink(missing_ok=True)
            return identificativo
        return None

    def _fai(self, identificativo: str, dati: dict) -> None:
        try:
            richiesta = RichiestaVideo(**dati)
            immagini = [Path(p).read_bytes() for p in richiesta.immagini]
            corpo_invio = corpo(richiesta, immagini)
            motore = self._crea_provider(comfy.ProviderComfy.nome)
            scrivi_stato(self.radice, identificativo, INVIATO)
            self._dire(f"Video {identificativo}: {len(immagini)} immagini verso "
                       f"{motore.destinazione_per(richiesta.modello)}.")
            video, dettagli = motore.genera_video(richiesta.modello, corpo_invio, tuple(immagini))
        except ErroreAirender as errore:
            scrivi_stato(self.radice, identificativo, ERRORE, fatto=errore.fatto, cosa_fare=errore.cosa_fare)
            self._dire(f"Video {identificativo}: errore. {errore.fatto}")
            return
        except (OSError, TypeError, ValueError) as errore:
            scrivi_stato(self.radice, identificativo, ERRORE,
                         fatto=f"Il video non e' partito: {type(errore).__name__}: {errore}.",
                         cosa_fare="Controlla che le immagini ci siano ancora, poi rifallo.")
            return
        file = cartelle(self.radice)["video"] / f"{identificativo}.mp4"
        scrivi_atomico(file, video)
        ricetta = {
            "modello": richiesta.modello,
            "prompt": richiesta.prompt(),
            "scelte": {k: v for k, v in asdict(richiesta).items() if k not in ("immagini", "identificativo")},
            "immagini": [impronta(d) for d in immagini],
            "corpo": corpo_senza_immagini(corpo_invio),
            "documentato_il": DOCUMENTATO_IL,
            **{k: v for k, v in dettagli.items() if k != "chiave_idempotenza"},
        }
        scrivi_atomico(file.with_name(file.name + ".ricetta.json"),
                       json.dumps(ricetta, ensure_ascii=False, indent=2))
        scrivi_stato(self.radice, identificativo, FATTO, video=str(file),
                     crediti_usati=dettagli.get("crediti_usati"))
        self._dire(f"Video {identificativo}: salvato in {file}")
