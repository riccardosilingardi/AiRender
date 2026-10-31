"""La coda dei lavori: il motore come processo a parte.

    python -m core.coda --cartella C:\\...\\AIRENDER

Perche' esiste: la palette di prova chiama il motore dentro Allplan, e Allplan
resta bloccato finche' il render non arriva. Con la coda la palette (e piu'
avanti lo Studio) scrive un lavoro in una cartella e torna libera; questo
processo lo prende, lo manda e lascia il render accanto.

Com'e' fatta la cartella, sotto `<cartella>/lavori/`:

    in-attesa/<id>.json      lavori scritti, non ancora presi
    in-corso/<id>.json       il lavoro che il processo sta facendo
    fatto/<id>.json          il lavoro, e accanto <id>.<formato> e la sua ricetta
    errore/<id>.json         il lavoro che non e' andato, con il perche' nello stato
    annullato/<id>.json      il lavoro fermato con un file <id>.annulla
    stato/<id>.json          lo stato leggibile, sempre qui, qualunque sia la cartella

Lo stato sta in un posto fisso cosi' chi legge (palette, Studio) non deve
inseguire il lavoro da una cartella all'altra mentre si sposta.

Un file `<id>.annulla` accanto al lavoro, in in-attesa/ o in-corso/, lo
ferma. Prima dell'invio lo ferma davvero; durante l'attesa smette di
aspettare, ma il servizio puo' averlo gia' addebitato, e lo stato lo dice.

Ogni file si scrive su un file temporaneo e poi si rinomina: chi legge non
vede mai un JSON a meta'.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import aree as modulo_aree, battito as modulo_battito, blocchi, config, grana as modulo_grana, immagine as modulo_immagine
from . import provider as registro
from .errori import ErroreAirender, FileNonTrovato, ImmagineNonIdonea
from .idoneita import valuta
from .preset import MODELLI_PREDEFINITI
from .provider.base import IN_LAVORAZIONE, INVIATO, Provider, RichiestaGenerazione

FORMATO = 2  # numero-non-configurabile: versione del formato del file di lavoro
# Il formato 2 (2026-10-30) aggiunge il passo di partenza e le richieste a
# parole. Un lavoro del formato 1 si legge ancora: parte dalla vista, senza
# richieste. Un motore vecchio rifiuta il 2 invece di mandare la vista al
# posto del render da cui il passo doveva partire.
FORMATO_RITOCCO = 3  # numero-non-configurabile: versione del formato di un lavoro con aree
# Il formato 3 (prompt 6) aggiunge le aree di Studio · Ritocca e il modo in
# cui partono. Si scrive solo per un ritocco: gli altri lavori restano nel 2,
# cosi' una palette o un motore che legge il 2 non smette di funzionare. Un
# motore vecchio rifiuta il 3 invece di mandare il render senza le aree.
FORMATI_LETTI = (1, 2, 3)  # numero-non-configurabile: i formati che questo motore sa leggere

# Gli stati, nelle parole che lo Studio e la palette mostrano.
IN_CODA = "in coda"
FATTO = "fatto"
ERRORE = "errore"
ANNULLATO = "annullato"
STATI = (IN_CODA, INVIATO, IN_LAVORAZIONE, FATTO, ERRORE, ANNULLATO)

CARTELLA_LAVORI = "lavori"
IN_ATTESA_DIR = "in-attesa"
IN_CORSO_DIR = "in-corso"
FATTO_DIR = "fatto"
ERRORE_DIR = "errore"
ANNULLATO_DIR = "annullato"
STATO_DIR = "stato"
CARTELLE = (IN_ATTESA_DIR, IN_CORSO_DIR, FATTO_DIR, ERRORE_DIR, ANNULLATO_DIR, STATO_DIR)

SUFFISSO_ANNULLA = ".annulla"
PREFISSO_TEMPORANEO = "."

# La ricetta vuole un preset: un lavoro con scelte libere lo dice cosi'.
SCELTE_LIBERE = "scelte-libere"


class LavoroAnnullato(ErroreAirender):
    """Qualcuno ha messo il file .annulla accanto al lavoro."""


class LavoroNonValido(ErroreAirender):
    """Il file del lavoro non si legge, o dice cose che non tornano."""


class CodaGiaAttiva(ErroreAirender):
    """Sulla stessa cartella gira gia' un'altra coda."""


def coda_viva(radice: Path) -> dict | None:
    """Il battito della coda che gira su questa cartella, o None se non ne gira nessuna."""
    return modulo_battito.leggi(modulo_battito.percorso(radice, modulo_battito.FILE_CODA))


def _adesso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- scrittura atomica -------------------------------------------------------


def scrivi_atomico(percorso: Path, contenuto: bytes | str) -> Path:
    """Scrive su un file temporaneo nella stessa cartella, poi rinomina.

    La rinomina nella stessa cartella e' atomica: chi legge trova il file
    vecchio o quello nuovo, mai uno a meta'. Il temporaneo comincia con un
    punto, e chi elenca i lavori salta i file che cominciano col punto.
    """
    percorso = Path(percorso)
    dati = contenuto.encode("utf-8") if isinstance(contenuto, str) else contenuto
    temporaneo = percorso.with_name(
        # pid e caso: due processi che scrivono lo stesso file non si pestano il temporaneo
        f"{PREFISSO_TEMPORANEO}{percorso.name}.{os.getpid()}.{secrets.token_hex()}.tmp"
    )
    try:
        with open(temporaneo, "wb") as uscita:
            uscita.write(dati)
            uscita.flush()
            os.fsync(uscita.fileno())
        os.replace(temporaneo, percorso)
    finally:
        if temporaneo.exists():
            temporaneo.unlink()
    return percorso


def scrivi_json(percorso: Path, dati: dict) -> Path:
    return scrivi_atomico(percorso, json.dumps(dati, ensure_ascii=False, indent=2))


# --- il lavoro ---------------------------------------------------------------


@dataclass(frozen=True)
class Lavoro:
    """Quello che la palette o lo Studio chiedono, scritto prima di partire."""

    identificativo: str
    vista: str
    scelte: blocchi.Scelte
    provider: str
    modello: str
    # Regola 5 di CLAUDE.md: la destinazione si scrive qui, quando il lavoro
    # nasce, cosi' chi lo crea l'ha mostrata prima che l'immagine parta.
    destinazione: str
    preset: str | None = None
    prompt_a_mano: str | None = None
    # Studio · Passi. `parte_da` e' il passo da cui parte (l'id del suo
    # lavoro), `partenza` il file del suo render: l'immagine che parte al
    # posto della vista. Senza, il lavoro parte dalla vista. `vista` resta
    # sempre la vista Allplan: e' contro di lei che si giudica l'edificio.
    parte_da: str | None = None
    partenza: str | None = None
    # Le richieste a parole dei passi: una per un passo nuovo, quelle della
    # strada per «Rifai pulito dalla vista».
    richieste: tuple[str, ...] = ()
    # Studio · Ritocca: le aree con le loro note, disegnate sul render di
    # partenza, e come partono (aree.MODI). Un ritocco parte sempre da un
    # render, e le note prendono il posto delle richieste.
    aree: tuple[modulo_aree.Area, ...] = ()
    modo_aree: str | None = None
    creato_il: str = field(default_factory=_adesso)
    formato: int = FORMATO

    def __post_init__(self) -> None:
        if self.aree:
            object.__setattr__(self, "formato", FORMATO_RITOCCO)

    def prompt(self) -> str:
        """Il testo che parte.

        Un ritocco: come sono indicate le aree e una riga per nota. Da un
        render: solo le richieste, con la regola del passo (lo stile c'e'
        gia'). Dalla vista: il testo scritto a mano se c'e', altrimenti i
        blocchi, piu' le richieste se ce ne sono.
        """
        if self.aree:
            return modulo_aree.prompt(self.modo_aree, self.aree)
        if self.partenza:
            return blocchi.componi_richieste(self.scelte.scena, self.richieste)
        if self.prompt_a_mano and self.prompt_a_mano.strip():
            base = self.prompt_a_mano.strip()
        else:
            base = blocchi.componi(self.scelte)
        return blocchi.aggiungi_richieste(base, self.richieste)

    def a_dizionario(self) -> dict:
        return {
            "formato": self.formato,
            "identificativo": self.identificativo,
            "creato_il": self.creato_il,
            "vista": self.vista,
            "preset": self.preset,
            "scelte": self.scelte.a_dizionario(),
            "prompt_a_mano": self.prompt_a_mano,
            "provider": self.provider,
            "modello": self.modello,
            "destinazione": self.destinazione,
            "parte_da": self.parte_da,
            "partenza": self.partenza,
            "richieste": list(self.richieste),
            **({"aree": [a.a_dizionario() for a in self.aree], "modo_aree": self.modo_aree}
               if self.aree else {}),
        }

    @classmethod
    def da_dizionario(cls, dati: object) -> "Lavoro":
        if not isinstance(dati, dict):
            raise LavoroNonValido(
                "Il file del lavoro non contiene un lavoro.",
                "Rimetti il lavoro in coda dalla palette o dallo Studio.",
            )
        if dati.get("formato") not in FORMATI_LETTI:
            raise LavoroNonValido(
                f"Il file del lavoro e' nel formato {dati.get('formato')!r}, "
                f"questo motore legge il formato {FORMATO}.",
                "Aggiorna il motore e la palette alla stessa versione, poi "
                "rimetti il lavoro in coda.",
            )
        mancanti = [
            k for k in ("identificativo", "vista", "provider", "modello", "destinazione")
            if not dati.get(k)
        ]
        if mancanti:
            raise LavoroNonValido(
                f"Nel file del lavoro manca: {', '.join(mancanti)}.",
                "Rimetti il lavoro in coda dalla palette o dallo Studio.",
            )
        parte_da, partenza = dati.get("parte_da"), dati.get("partenza")
        if bool(parte_da) != bool(partenza):
            raise LavoroNonValido(
                "Il file del lavoro dice da quale passo parte ma non con quale "
                "immagine, o il contrario.",
                "Rimetti il passo in coda dallo Studio · Passi.",
            )
        richieste = dati.get("richieste") or []
        if not isinstance(richieste, list) or not all(isinstance(r, str) for r in richieste):
            raise LavoroNonValido(
                "Nel file del lavoro le richieste non sono un elenco di frasi.",
                "Rimetti il passo in coda dallo Studio · Passi.",
            )
        aree, modo_aree = _aree_del_lavoro(dati, partenza)
        return cls(
            identificativo=str(dati["identificativo"]),
            vista=str(dati["vista"]),
            scelte=blocchi.Scelte.da_dizionario(dati.get("scelte") or {}),
            provider=str(dati["provider"]),
            modello=str(dati["modello"]),
            destinazione=str(dati["destinazione"]),
            preset=dati.get("preset"),
            prompt_a_mano=dati.get("prompt_a_mano"),
            parte_da=str(parte_da) if parte_da else None,
            partenza=str(partenza) if partenza else None,
            richieste=tuple(richieste),
            aree=aree,
            modo_aree=modo_aree,
            creato_il=str(dati.get("creato_il") or _adesso()),
        )


def _aree_del_lavoro(dati: dict, partenza: object) -> tuple[tuple[modulo_aree.Area, ...], str | None]:
    """Le aree di un lavoro del formato 3, o nessuna. Un lavoro con aree che non tornano non parte."""
    if dati.get("formato") != FORMATO_RITOCCO:
        return (), None
    if not partenza:
        raise LavoroNonValido(
            "Il file del lavoro ha delle aree ma non il render su cui sono disegnate.",
            "Rimetti il ritocco in coda dallo Studio · Ritocca.",
        )
    try:
        return modulo_aree.da_elenco(dati.get("aree")), modulo_aree.controlla_modo(dati.get("modo_aree"))
    except modulo_aree.AreaNonValida as errore:
        raise LavoroNonValido(f"Nel file del lavoro: {errore.fatto}", errore.cosa_fare) from None


def nuovo_identificativo(adesso: datetime | None = None) -> str:
    """Ordinabile per data, cosi' la coda prende i lavori nell'ordine in cui sono nati."""
    adesso = adesso or datetime.now()
    return f"{adesso:%Y%m%d-%H%M%S-%f}-{secrets.token_hex(2)}"


def cartelle(radice: Path) -> dict[str, Path]:
    """Le cartelle della coda, create se mancano."""
    base = Path(radice) / CARTELLA_LAVORI
    percorsi = {nome: base / nome for nome in CARTELLE}
    for percorso in percorsi.values():
        percorso.mkdir(parents=True, exist_ok=True)
    return percorsi


def scrivi_stato(radice: Path, identificativo: str, stato: str, **altro) -> dict:
    if stato not in STATI:
        raise ValueError(f"stato sconosciuto: {stato!r}")
    dati = {"identificativo": identificativo, "stato": stato, "aggiornato_il": _adesso(), **altro}
    scrivi_json(cartelle(radice)[STATO_DIR] / f"{identificativo}.json", dati)
    return dati


def leggi_stato(radice: Path, identificativo: str) -> dict | None:
    """Lo stato di un lavoro, o None se non c'e'. Mai un JSON a meta': si scrive atomico."""
    percorso = Path(radice) / CARTELLA_LAVORI / STATO_DIR / f"{identificativo}.json"
    try:
        return json.loads(percorso.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def metti_in_coda(
    radice: Path,
    vista: Path,
    scelte: blocchi.Scelte,
    *,
    preset: str | None = None,
    provider: str = registro.PREDEFINITO,
    modello: str | None = None,
    prompt_a_mano: str | None = None,
    parte_da: str | None = None,
    partenza: Path | None = None,
    richieste: tuple[str, ...] | list[str] = (),
    aree: tuple[modulo_aree.Area, ...] = (),
    modo_aree: str | None = None,
    crea_provider: Callable[[str], Provider] = registro.crea,
) -> Lavoro:
    """Scrive un lavoro in in-attesa/ e il suo stato "in coda".

    Compone il prompt subito: una scelta sbagliata si dice a chi la fa, non
    al processo della coda minuti dopo.
    """
    if bool(parte_da) != bool(partenza):
        raise LavoroNonValido(
            "Un passo ha bisogno sia del passo da cui parte sia del suo render.",
            "Scegli il passo di partenza nell'albero dello Studio · Passi.",
        )
    if aree:
        if not partenza:
            raise LavoroNonValido(
                "Un ritocco per aree parte da un render, non dalla vista.",
                "Genera prima un render da Genera, poi ritoccalo.",
            )
        modulo_aree.controlla_modo(modo_aree)
    if modello is None:
        try:
            modello = MODELLI_PREDEFINITI[provider]
        except KeyError:
            raise LavoroNonValido(
                f"Il servizio {provider} non ha un modello predefinito.",
                "Indica il modello del lavoro.",
            ) from None
    destinazione = crea_provider(provider).destinazione_per(modello)
    lavoro = Lavoro(
        identificativo=nuovo_identificativo(),
        vista=str(Path(vista).resolve()),
        scelte=scelte,
        provider=provider,
        modello=modello,
        destinazione=destinazione,
        preset=preset,
        prompt_a_mano=prompt_a_mano,
        parte_da=parte_da,
        partenza=str(Path(partenza).resolve()) if partenza else None,
        richieste=tuple(richieste),
        aree=tuple(aree),
        modo_aree=modo_aree if aree else None,
    )
    lavoro.prompt()  # solleva SceltaNonValida con la ragione, prima di scrivere
    percorsi = cartelle(radice)
    # Prima lo stato, poi il lavoro: chi trova il lavoro trova anche lo stato.
    scrivi_stato(radice, lavoro.identificativo, IN_CODA, destinazione=destinazione)
    scrivi_json(percorsi[IN_ATTESA_DIR] / f"{lavoro.identificativo}.json", lavoro.a_dizionario())
    return lavoro


def chiedi_annullamento(radice: Path, identificativo: str) -> Path:
    """Mette il file .annulla accanto al lavoro, dov'e' adesso."""
    percorsi = cartelle(radice)
    for nome in (IN_CORSO_DIR, IN_ATTESA_DIR):
        if (percorsi[nome] / f"{identificativo}.json").exists():
            break
    else:
        nome = IN_ATTESA_DIR  # gia' finito o non ancora scritto: non fa danni
    segnale = percorsi[nome] / f"{identificativo}{SUFFISSO_ANNULLA}"
    scrivi_atomico(segnale, b"")
    return segnale


# --- il processo -------------------------------------------------------------


class Coda:
    """Prende un lavoro alla volta da in-attesa/ e lo porta fino in fondo."""

    def __init__(
        self,
        radice: Path,
        crea_provider: Callable[[str], Provider] = registro.crea,
        dire: Callable[[str], None] = print,
        attesa: Callable[[float], None] = time.sleep,
    ) -> None:
        self.radice = Path(radice)
        self.percorsi = cartelle(self.radice)
        self._crea_provider = crea_provider
        self._dire = dire
        self._attesa = attesa

    # --- elenco ------------------------------------------------------------

    def in_attesa(self) -> list[Path]:
        """I lavori da fare, il piu' vecchio per primo. I temporanei non si vedono."""
        return sorted(
            p for p in self.percorsi[IN_ATTESA_DIR].glob("*.json")
            if not p.name.startswith(PREFISSO_TEMPORANEO)
        )

    # --- recupero ----------------------------------------------------------

    def recupera_abbandonati(self) -> list[str]:
        """Al riavvio, un lavoro in in-corso/ e' di un processo morto a meta'.

        Se non era ancora partito, torna in coda. Se era partito non si
        rimanda da solo: il servizio puo' averlo gia' fatto e addebitato, e
        rimandarlo lo farebbe pagare due volte. Va in errore/ e lo dice.
        """
        recuperati = []
        for percorso in sorted(self.percorsi[IN_CORSO_DIR].glob("*.json")):
            if percorso.name.startswith(PREFISSO_TEMPORANEO):
                continue
            identificativo = percorso.stem
            stato = (leggi_stato(self.radice, identificativo) or {}).get("stato", IN_CODA)
            if stato == IN_CODA:
                os.replace(percorso, self.percorsi[IN_ATTESA_DIR] / percorso.name)
                self._sposta_annulla(identificativo, IN_CORSO_DIR, IN_ATTESA_DIR)
                self._dire(f"Lavoro {identificativo}: non era partito, torna in coda.")
            else:
                self._chiudi(
                    percorso, ERRORE_DIR, ERRORE,
                    fatto=(
                        "Il motore si e' chiuso mentre questo lavoro era "
                        f"{stato}: non so se il render e' stato fatto."
                    ),
                    cosa_fare=(
                        "Guarda i crediti del workspace Comfy prima di rifarlo: "
                        "se sono scesi, il servizio l'ha fatto e addebitato, e "
                        "rifacendolo lo paghi due volte. Poi rimettilo in coda "
                        "dallo Studio o dalla palette."
                    ),
                )
                self._dire(f"Lavoro {identificativo}: abbandonato a meta', messo fra gli errori.")
            recuperati.append(identificativo)
        return recuperati

    # --- un lavoro ---------------------------------------------------------

    def esegui_uno(self) -> str | None:
        """Fa il lavoro piu' vecchio. Restituisce il suo id, o None se la coda e' vuota."""
        for percorso in self.in_attesa():
            preso = self.percorsi[IN_CORSO_DIR] / percorso.name
            try:
                # Prenderlo e' rinominarlo: se un altro processo l'ha preso
                # prima, la rinomina fallisce e si passa al successivo.
                os.rename(percorso, preso)
            except OSError:
                continue
            identificativo = preso.stem
            self._sposta_annulla(identificativo, IN_ATTESA_DIR, IN_CORSO_DIR)
            self._lavora(identificativo, preso)
            return identificativo
        return None

    def _lavora(self, identificativo: str, preso: Path) -> None:
        stato_attuale = {"valore": IN_CODA}
        try:
            lavoro = self._leggi(preso)
            self._controlla_annullamento(identificativo, stato_attuale["valore"])
            richiesta, motore = self._prepara(lavoro)
            self._controlla_annullamento(identificativo, stato_attuale["valore"])

            def avanzamento(stato: str) -> None:
                if stato != stato_attuale["valore"]:
                    stato_attuale["valore"] = stato
                    scrivi_stato(
                        self.radice, identificativo, stato, destinazione=lavoro.destinazione
                    )
                self._controlla_annullamento(identificativo, stato)

            motore.avanzamento = avanzamento
            self._dire(
                f"Lavoro {identificativo}: destinazione dell'invio "
                f"{lavoro.destinazione}. 1 immagine lascia questa macchina."
            )
            # Da qui l'immagine parte: lo stato lo dice prima, non dopo.
            avanzamento(INVIATO)
            risultato = motore.genera(richiesta)
        except LavoroAnnullato as annullato:
            self._chiudi(preso, ANNULLATO_DIR, ANNULLATO,
                         fatto=annullato.fatto, cosa_fare=annullato.cosa_fare)
            self._dire(f"Lavoro {identificativo}: annullato.")
            return
        except ErroreAirender as errore:
            self._chiudi(preso, ERRORE_DIR, ERRORE, fatto=errore.fatto, cosa_fare=errore.cosa_fare)
            self._dire(f"Lavoro {identificativo}: errore. {errore.fatto}")
            return
        except Exception as errore:  # pylint: disable=broad-exception-caught
            # Il processo non deve morire per un lavoro: l'imprevisto si scrive
            # com'e' e la coda va avanti col successivo.
            self._chiudi(
                preso, ERRORE_DIR, ERRORE,
                fatto=f"Errore imprevisto del motore: {type(errore).__name__}: {errore}.",
                cosa_fare=(
                    "Non e' un problema della vista. Segnala questo messaggio; "
                    "il lavoro resta in lavori/errore per rifarlo."
                ),
            )
            self._dire(f"Lavoro {identificativo}: errore imprevisto, {errore}")
            return

        render = self.percorsi[FATTO_DIR] / f"{identificativo}.{risultato.formato}"
        ricetta = render.with_name(render.name + ".ricetta.json")
        scrivi_atomico(render, risultato.immagine)
        scrivi_atomico(ricetta, risultato.ricetta.a_json())
        altro = {"fuori_aree": self._misura_fuori_aree(lavoro, risultato.immagine)} if lavoro.aree else {}
        self._chiudi(
            preso, FATTO_DIR, FATTO,
            render=str(render),
            ricetta=str(ricetta),
            scostamento_geometria=risultato.scostamento_geometria,
            avvisi=list(risultato.avvisi),
            **altro,
        )
        self._dire(f"Lavoro {identificativo}: render salvato in {render}")

    def _leggi(self, preso: Path) -> Lavoro:
        try:
            dati = json.loads(preso.read_text(encoding="utf-8"))
        except ValueError as errore:  # JSON rotto o byte che non sono UTF-8
            raise LavoroNonValido(
                f"Il file del lavoro non e' un JSON leggibile ({errore}).",
                "Rimetti il lavoro in coda dalla palette o dallo Studio. Se "
                "succede spesso, chi scrive i lavori non usa la scrittura atomica.",
            ) from None
        lavoro = Lavoro.da_dizionario(dati)
        if lavoro.identificativo != preso.stem:
            raise LavoroNonValido(
                f"Il file {preso.name} dice di essere il lavoro {lavoro.identificativo}.",
                "Rimetti il lavoro in coda dalla palette o dallo Studio.",
            )
        return lavoro

    def _prepara(self, lavoro: Lavoro) -> tuple[RichiestaGenerazione, Provider]:
        if lavoro.partenza:
            dati = self._leggi_partenza(Path(lavoro.partenza))
        else:
            dati = modulo_immagine.leggi(Path(lavoro.vista))
            giudizio = valuta(modulo_immagine.misura(dati))
            if not giudizio.idonea:
                raise ImmagineNonIdonea(giudizio.fatto, giudizio.cosa_fare, giudizio.motivo or "")
        motore = self._crea_provider(lavoro.provider)
        annunciata = motore.destinazione_per(lavoro.modello)
        if annunciata != lavoro.destinazione:
            # Chi ha creato il lavoro ha mostrato un'altra destinazione: mandare
            # comunque renderebbe falso quello che l'utente ha letto.
            raise LavoroNonValido(
                f"Il lavoro dice che la vista va a {lavoro.destinazione}, ma "
                f"partirebbe verso {annunciata}. Non ho inviato niente.",
                "Rimetti il lavoro in coda: la destinazione si rilegge e si "
                "mostra di nuovo prima dell'invio.",
            )
        motore.controlla_prima_dell_invio(lavoro.modello, dati)
        ingresso, in_piu = dati, ()
        if lavoro.aree:
            ingresso, in_piu = modulo_aree.prepara(dati, lavoro.aree, lavoro.modo_aree)
        # La grana non entra nei blocchi: i modelli del Router non hanno un
        # dettaglio della grana, e la ricetta lo scrive come assente.
        livello = modulo_grana.MEDIA
        richiesta = RichiestaGenerazione(
            immagine=ingresso,
            prompt=lavoro.prompt(),
            preset=lavoro.preset or SCELTE_LIBERE,
            preset_versione=blocchi.VERSIONE,
            modello=lavoro.modello,
            grana=livello,
            dettaglio_grana=modulo_grana.dettaglio(livello),
            testo_utente=lavoro.scelte.materiali,
            immagini_in_piu=in_piu,
        )
        return richiesta, motore

    def _misura_fuori_aree(self, lavoro: Lavoro, render: bytes) -> dict | None:
        """Quanto e' cambiato il render fuori dalle aree, contro il render di partenza senza contorni.

        Il render e' gia' pagato e salvato: una misura che non riesce non lo
        butta, resta None e lo Studio scrive «non misurato».
        """
        try:
            return modulo_aree.misura(Path(lavoro.partenza).read_bytes(), render, lavoro.aree)
        except (OSError, ErroreAirender) as errore:
            self._dire(f"Lavoro {lavoro.identificativo}: misura fuori dalle aree non riuscita, {errore}")
            return None

    @staticmethod
    def _leggi_partenza(partenza: Path) -> bytes:
        """Il render da cui parte un passo.

        Non passa dall'idoneita': quella giudica una vista di Allplan
        (shaded, toni, sfondo), e un render non e' una vista. Si controlla
        solo che ci sia e che sia un'immagine.
        """
        if not partenza.is_file():
            raise FileNonTrovato(
                f"Il punto di partenza non c'e' piu': {partenza}. Non ho inviato niente.",
                "Nello Studio · Passi usa «Rifai pulito dalla vista», che riparte "
                "dalla vista Allplan con le stesse richieste.",
            )
        dati = partenza.read_bytes()
        modulo_immagine.misura(dati)  # solleva se non e' un'immagine
        return dati

    # --- annullamento ------------------------------------------------------

    def _segnali_annulla(self, identificativo: str) -> list[Path]:
        return [
            self.percorsi[nome] / f"{identificativo}{SUFFISSO_ANNULLA}"
            for nome in (IN_ATTESA_DIR, IN_CORSO_DIR)
        ]

    def _controlla_annullamento(self, identificativo: str, stato: str) -> None:
        # Si guarda anche in in-attesa/: il file puo' essere stato scritto
        # proprio mentre il lavoro veniva preso.
        if not any(p.exists() for p in self._segnali_annulla(identificativo)):
            return
        if stato == IN_CODA:
            raise LavoroAnnullato(
                "Annullato prima dell'invio: la vista non e' partita.",
                "Niente da fare. Se lo vuoi, rimettilo in coda.",
            )
        raise LavoroAnnullato(
            "Annullato mentre il servizio ci lavorava: ho smesso di aspettare, "
            "ma la vista era gia' partita e il servizio puo' addebitarla.",
            "Guarda i crediti del workspace prima di rimetterlo in coda.",
        )

    def _sposta_annulla(self, identificativo: str, da: str, a: str) -> None:
        segnale = self.percorsi[da] / f"{identificativo}{SUFFISSO_ANNULLA}"
        try:
            os.replace(segnale, self.percorsi[a] / segnale.name)
        except FileNotFoundError:
            pass

    # --- chiusura ----------------------------------------------------------

    def _chiudi(self, preso: Path, cartella: str, stato: str, **altro) -> None:
        """Sposta il lavoro nella cartella finale, poi scrive lo stato finale."""
        identificativo = preso.stem
        finale = self.percorsi[cartella] / preso.name
        os.replace(preso, finale)
        for segnale in self._segnali_annulla(identificativo):
            if segnale.exists():
                segnale.unlink()
        scrivi_stato(self.radice, identificativo, stato, lavoro=str(finale), **altro)

    # --- il ciclo ----------------------------------------------------------

    def gira(self, una_volta: bool = False) -> int:
        """Recupera gli abbandonati, poi fa i lavori uno alla volta.

        Con `una_volta` esce quando la coda e' vuota; altrimenti aspetta il
        prossimo lavoro finche' non lo si ferma (Ctrl+C).
        """
        altra = coda_viva(self.radice)
        if altra is not None and altra.get("pid") != os.getpid():
            # Una seconda coda prenderebbe per abbandonato il lavoro in corso
            # della prima e lo metterebbe fra gli errori mentre e' ancora vivo.
            raise CodaGiaAttiva(
                f"Su {self.radice / CARTELLA_LAVORI} gira gia' una coda dei lavori "
                f"(processo {altra.get('pid')}): ne basta una.",
                "Non serve fare niente: i lavori li prende quella. Per fermarla, "
                "chiudi lo Studio o la finestra da cui l'hai lanciata.",
            )
        with modulo_battito.Battito(
            modulo_battito.percorso(self.radice, modulo_battito.FILE_CODA),
            {"cartella": str(self.radice)},
        ):
            self.recupera_abbandonati()
            fatti = 0
            while True:
                if self.esegui_uno() is not None:
                    fatti += 1
                    continue
                if una_volta:
                    return fatti
                self._attesa(config.CODA_INTERVALLO_SECONDI)


# --- riga di comando ---------------------------------------------------------


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m core.coda",
        description=(
            "Il motore come processo a parte: prende i lavori da "
            "<cartella>/lavori/in-attesa e lascia i render in lavori/fatto."
        ),
    )
    parser.add_argument("--cartella", required=True, help="la cartella che contiene lavori/")
    parser.add_argument(
        "--una-volta", action="store_true", dest="una_volta",
        help="fa i lavori che trova ed esce, invece di restare in attesa",
    )
    parser.add_argument(
        "--aggiungi", metavar="VISTA",
        help="mette in coda questa vista, con --stile, ed esce (per provare senza Studio)",
    )
    parser.add_argument(
        "--stile", default="rivista",
        help=f"il preset di stile per --aggiungi: {', '.join(blocchi.PRESET_STILE)}",
    )
    parser.add_argument("--materiali", default="", help="i materiali a parole, per --aggiungi")
    parser.add_argument("--annulla", metavar="ID", help="annulla il lavoro con questo id ed esce")
    return parser


def main(argv: list[str] | None = None) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    radice = Path(argomenti.cartella)
    try:
        if argomenti.annulla:
            segnale = chiedi_annullamento(radice, argomenti.annulla)
            print(f"Chiesto l'annullamento: {segnale}")
            return 0
        if argomenti.aggiungi:
            scelte = blocchi.da_preset(argomenti.stile, materiali=argomenti.materiali)
            lavoro = metti_in_coda(radice, Path(argomenti.aggiungi), scelte, preset=argomenti.stile)
            print(f"Destinazione dell'invio: {lavoro.destinazione}.")
            print(f"Lavoro {lavoro.identificativo} in coda in {radice / CARTELLA_LAVORI / IN_ATTESA_DIR}")
            return 0
        coda = Coda(radice)
        print(f"Coda dei lavori su {radice / CARTELLA_LAVORI}. Ctrl+C per fermarla.")
        coda.gira(una_volta=argomenti.una_volta)
        return 0
    except ErroreAirender as errore:
        print(str(errore), file=sys.stderr)
        return 2  # numero-non-configurabile: convenzione della shell, come core.cli
    except KeyboardInterrupt:
        print("Coda fermata. I lavori in attesa restano nella cartella.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
