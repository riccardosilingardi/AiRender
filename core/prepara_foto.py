"""«Prepara la foto»: il passo facoltativo prima del Fotoinserimento.

Richiesta di Riccardo del 2026-11-23 (thread «Preparare la foto prima del
fotoinserimento»): uno screenshot di Google Earth o Maps va prima pulito e
portato in alta risoluzione, poi ci si mette sopra la velina e l'aggancio, e
solo dopo si inserisce l'edificio. Per una foto da drone o da terra di solito
non serve, e lo Studio lo dice.

Due invii, uno dopo l'altro, dalla stessa coda delle immagini:

1. Nano Banana 2 rifa lo screenshot come una foto: toglie scritte, icone e
   logo, rende fotografico il 3D «sciolto» di Google, senza spostare niente.
   La cornice di core/provider/comfy.py rimanda la foto della stessa forma,
   quindi il rettangolo e i punti messi in frazioni dell'immagine restano dove
   sono.
2. Magnific Precision V2 (lo stesso di «Finale») la ingrandisce, se l'utente
   lo chiede e se il servizio scelto lo fa.

Il risultato va nella cartella dei contesti, come una foto caricata: lo
Studio lo mostra in prima/dopo contro l'originale, e l'utente sceglie quale
usare. Se il primo invio riesce e l'ingrandimento no, la foto pulita resta
(e' gia' pagata) e lo stato lo dice.

Un lavoro sta in `lavori/prepara-foto/`, come i video in `lavori/video/`.
MAI ESEGUITO con un invio vero: la prima preparazione e' la prova.

Nessun import di Allplan: si prova con pytest.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import blocchi, config, contesto as modulo_contesto, grana as modulo_grana, immagine as modulo_immagine
from .coda import nuovo_identificativo, scrivi_atomico, scrivi_json
from .errori import ErroreAirender
from .provider import comfy
from .provider.base import Provider, RichiestaGenerazione

CARTELLA_LAVORI = Path("lavori") / "prepara-foto"
IN_ATTESA, STATO = "in-attesa", "stato"

IN_CODA, PULIZIA, INGRANDIMENTO, FATTO, ERRORE, ANNULLATO = (
    "in coda", "pulizia", "ingrandimento", "fatto", "errore", "annullato")
IN_CORSO = (IN_CODA, PULIZIA, INGRANDIMENTO)

MODELLO_PULIZIA = config.NANO_BANANA_2
MODELLO_INGRANDIMENTO = comfy.MODELLO_FINALE
PRESET = "prepara-la-foto"

# Il prompt, in inglese come gli altri. Il pezzo fisso dice cosa non deve
# cambiare: e' quello che tiene validi rettangolo e punti dell'aggancio.
_FISSO = (
    "Keep exactly the same camera: same framing, same perspective, same horizon, same scale. "
    "Do not crop, zoom, rotate or shift the image. Keep every road, building, roof, tree, field, "
    "car, wall and shadow in its exact position, size and orientation; do not add, remove or "
    "move anything, do not add buildings. Same season, time of day and light as the original."
)
_TOGLI = (
    "Remove every interface element: labels, street and place names, pins, icons, logos, "
    "buttons, compass, scale bar, copyright and watermark text, cursor. Fill those spots with "
    "what would realistically be underneath."
)
PROMPT = {
    blocchi.ZENITALE: (
        "This image is a screenshot of a satellite map seen straight down (Google Maps or Google "
        "Earth). Turn it into a clean, sharp, photorealistic, high-resolution orthophoto of the "
        f"same place, still seen straight down. {_TOGLI} Make roofs, roads, trees and fields crisp "
        f"and photographic, without blur or compression artefacts. {_FISSO}"
    ),
    blocchi.VOLO: (
        "This image is a screenshot of a 3D map seen from above at an angle (Google Earth 3D). "
        "Turn it into a clean, sharp, photorealistic, high-resolution aerial photograph taken "
        f"from a drone in exactly that position. {_TOGLI} Fix the melted, blobby look of the 3D "
        "mesh: buildings with straight edges and crisp roofs and facades, trees with real foliage, "
        f"roads with clean edges and markings. {_FISSO}"
    ),
    blocchi.TERRA: (
        "This image is a screenshot of a street-level view (Google Street View). Turn it into a "
        "clean, sharp, photorealistic, high-resolution photograph taken from exactly the same "
        f"spot. {_TOGLI} Remove blur, stitching seams and compression artefacts. {_FISSO}"
    ),
}


class PreparazioneNonValida(ErroreAirender):
    """Una preparazione che non si puo' mandare: lo dice prima, non al servizio."""


def _adesso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def prompt(inquadratura: str) -> str:
    try:
        return PROMPT[blocchi.controlla_inquadratura(inquadratura)]
    except blocchi.SceltaNonValida as errore:
        raise PreparazioneNonValida(errore.fatto, errore.cosa_fare) from None


@dataclass(frozen=True)
class Preparazione:
    """Quello che lo Studio chiede, scritto prima di partire."""

    identificativo: str
    # Il file della foto originale, nella cartella dei contesti.
    file: str
    inquadratura: str
    provider: str
    # Regola 5 di CLAUDE.md: le destinazioni si scrivono quando il lavoro
    # nasce, cosi' chi lo crea le ha mostrate prima che la foto parta.
    destinazione: str
    # Vuota: niente ingrandimento.
    destinazione_ingrandimento: str = ""
    ingrandimento: int = 0
    creato_il: str = field(default_factory=_adesso)

    def __post_init__(self) -> None:
        prompt(self.inquadratura)  # solleva se l'inquadratura non esiste
        if self.ingrandimento and self.ingrandimento not in config.FINALE_INGRANDIMENTI:
            raise PreparazioneNonValida(
                f"«Prepara la foto» ingrandisce di {config.PREPARA_FOTO_INGRANDIMENTO} volte, non di {self.ingrandimento}.",
                "Ricarica lo Studio e rifai «Prepara la foto».")
        if bool(self.ingrandimento) != bool(self.destinazione_ingrandimento):
            raise PreparazioneNonValida(
                "L'ingrandimento non dice dove va la foto.",
                "Ricarica lo Studio: la destinazione si rilegge e si mostra di nuovo.")

    def prompt(self) -> str:
        return prompt(self.inquadratura)


# --- cartelle e stato ----------------------------------------------------------


def cartelle(radice: Path) -> dict[str, Path]:
    base = Path(radice) / CARTELLA_LAVORI
    percorsi = {nome: base / nome for nome in (IN_ATTESA, STATO)}
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


def leggi_stato(radice: Path, identificativo: str) -> dict | None:
    if not identificativo or not all(c.isalnum() or c == "-" for c in identificativo):
        return None
    try:
        return json.loads((cartelle(radice)[STATO] / f"{identificativo}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def metti_in_coda(radice: Path, file: Path, inquadratura: str, *, provider: str, destinazione: str,
                  destinazione_ingrandimento: str = "", ingrandimento: int = 0) -> Preparazione:
    """Scrive la preparazione in lavori/prepara-foto/in-attesa e lo stato «in coda»."""
    percorso = modulo_contesto.controlla_file(radice, Path(file))
    preparazione = Preparazione(
        identificativo=nuovo_identificativo(), file=str(percorso), inquadratura=inquadratura,
        provider=provider, destinazione=destinazione,
        destinazione_ingrandimento=destinazione_ingrandimento, ingrandimento=ingrandimento)
    scrivi_json(cartelle(radice)[IN_ATTESA] / f"{preparazione.identificativo}.json", asdict(preparazione))
    scrivi_stato(radice, preparazione.identificativo, IN_CODA, originale=percorso.name,
                 ingrandimento=ingrandimento)
    return preparazione


def annulla(radice: Path, identificativo: str) -> bool:
    """Toglie una preparazione ancora in coda. Una gia' partita non si ferma: il servizio la fa comunque."""
    percorso = cartelle(radice)[IN_ATTESA] / f"{identificativo}.json"
    try:
        percorso.unlink()
    except FileNotFoundError:
        return False
    scrivi_stato(radice, identificativo, ANNULLATO, fatto="Annullata prima di partire: non e' stato inviato niente.")
    return True


def _come_contesto(dati: bytes) -> bytes:
    """La foto pronta da salvare fra i contesti: sotto il limite d'invio, marcata come generata."""
    massimo = config.COMFY_INVIO_MASSIMO_MB
    if modulo_immagine.dimensione_mb(dati) > massimo:
        # Un PNG a 5K pesa 20 MB: in JPEG, stessi pixel, pochi MB.
        leggera = modulo_immagine.alleggerisci(dati, massimo, (config.RIFERIMENTO_LATO_RIDOTTO_PX,))
        if leggera is None:
            raise PreparazioneNonValida(
                "La foto preparata non sta sotto il limite d'invio neanche in JPEG.",
                "Rifai «Prepara la foto» senza ingrandire.")
        dati = leggera
    return modulo_immagine.marca_generata(dati)


class CodaPreparazioni:
    """Fa le preparazioni una alla volta. La chiama la coda delle immagini quando e' libera."""

    def __init__(self, radice: Path, crea_provider: Callable[[str], Provider],
                 dire: Callable[[str], None] = print) -> None:
        self.radice = Path(radice)
        self._crea_provider = crea_provider
        self._dire = dire

    def recupera_abbandonati(self) -> list[str]:
        """Una preparazione partita senza processo vivo non si rimanda: il servizio puo' averla gia' fatta e addebitata."""
        persi = []
        for percorso in cartelle(self.radice)[STATO].glob("*.json"):
            try:
                voce = json.loads(percorso.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if voce.get("stato") in (PULIZIA, INGRANDIMENTO):
                scrivi_stato(self.radice, voce["identificativo"], ERRORE,
                             fatto="La coda si e' fermata mentre la foto era al servizio.",
                             cosa_fare="Controlla i crediti prima di rifarla: se sono scesi, la foto era partita.")
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
            try:
                self._fai(percorso.stem, preso)
            finally:
                preso.unlink(missing_ok=True)
            return percorso.stem
        return None

    def _invia(self, preparazione: Preparazione, modello: str, destinazione: str, immagine: bytes,
               **richiesta) -> tuple[bytes, dict]:
        motore = self._crea_provider(preparazione.provider)
        annunciata = motore.destinazione_per(modello)
        if annunciata != destinazione:
            raise PreparazioneNonValida(
                f"La preparazione dice che la foto va a {destinazione}, ma partirebbe verso {annunciata}. "
                "Non ho inviato niente.",
                "Rifai «Prepara la foto»: la destinazione si rilegge e si mostra di nuovo.")
        motore.controlla_prima_dell_invio(modello, immagine)
        livello = modulo_grana.MEDIA
        risultato = motore.genera(RichiestaGenerazione(
            immagine=immagine, preset=PRESET, preset_versione=blocchi.VERSIONE, modello=modello,
            grana=livello, dettaglio_grana=modulo_grana.dettaglio(livello), **richiesta))
        return risultato.immagine, risultato.ricetta.a_dizionario()

    def _fai(self, identificativo: str, preso: Path) -> None:
        try:
            preparazione = Preparazione(**json.loads(preso.read_text(encoding="utf-8")))
            originale = modulo_contesto.controlla_file(self.radice, Path(preparazione.file)).read_bytes()
            modulo_immagine.misura(originale)  # solleva se non e' un'immagine
            scrivi_stato(self.radice, identificativo, PULIZIA)
            self._dire(f"Prepara la foto {identificativo}: pulizia verso {preparazione.destinazione}.")
            pulita, ricetta_pulizia = self._invia(
                preparazione, MODELLO_PULIZIA, preparazione.destinazione, originale,
                prompt=preparazione.prompt(), dimensione_render=config.PREPARA_FOTO_RISOLUZIONE)
        except ErroreAirender as errore:
            scrivi_stato(self.radice, identificativo, ERRORE, fatto=errore.fatto, cosa_fare=errore.cosa_fare)
            self._dire(f"Prepara la foto {identificativo}: errore. {errore.fatto}")
            return
        except (OSError, TypeError, ValueError) as errore:
            scrivi_stato(self.radice, identificativo, ERRORE,
                         fatto=f"La foto non e' partita: {type(errore).__name__}: {errore}.",
                         cosa_fare="Carica di nuovo la foto, poi rifai «Prepara la foto».")
            return
        ricette, avviso, finita = [ricetta_pulizia], None, pulita
        if preparazione.ingrandimento:
            try:
                scrivi_stato(self.radice, identificativo, INGRANDIMENTO)
                self._dire(f"Prepara la foto {identificativo}: ingrandimento verso "
                           f"{preparazione.destinazione_ingrandimento}.")
                finita, ricetta_ingrandimento = self._invia(
                    preparazione, MODELLO_INGRANDIMENTO, preparazione.destinazione_ingrandimento, pulita,
                    prompt="", ingrandimento=preparazione.ingrandimento, tipo_finale="foto")
                ricette.append(ricetta_ingrandimento)
            except ErroreAirender as errore:
                # La pulizia e' gia' pagata: si tiene, e si dice cosa non e' andato.
                avviso = f"Pulita ma non ingrandita: {errore.fatto}"
                self._dire(f"Prepara la foto {identificativo}: {avviso}")
        try:
            dati = _come_contesto(finita)
            nome = modulo_contesto.salva(self.radice, dati)
        except ErroreAirender as errore:
            scrivi_stato(self.radice, identificativo, ERRORE, fatto=errore.fatto, cosa_fare=errore.cosa_fare)
            return
        larghezza, altezza = modulo_immagine.dimensioni(dati)
        cartella = modulo_contesto.cartella_contesti(self.radice)
        scrivi_atomico(cartella / f"{nome}.ricetta.json", json.dumps({
            "prepara_la_foto": identificativo,
            "originale": Path(preparazione.file).name,
            "inquadratura": preparazione.inquadratura,
            "invii": ricette,
        }, ensure_ascii=False, indent=2))
        scrivi_stato(self.radice, identificativo, FATTO, preparata=nome, larghezza=larghezza, altezza=altezza,
                     ingrandita=len(ricette) > 1, avviso=avviso,
                     crediti_usati=[r.get("parametri", {}).get("crediti_usati") for r in ricette])
        self._dire(f"Prepara la foto {identificativo}: pronta, {nome} ({larghezza} x {altezza}).")
