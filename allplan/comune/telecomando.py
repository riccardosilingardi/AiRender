"""La palette di Allplan, il telecomando: tutto quello che non importa Allplan.

L'adattatore di ogni versione (allplan/v2026/.../AirenderPalette.py) fa solo
quello che esiste soltanto dentro Allplan: cattura della finestra, lettura
della camera e dei materiali, lettura e scrittura dei campi della palette,
finestre di messaggio. Il resto e' qui e si prova con pytest.

Dal 2026-11-04 la palette cattura e basta (scelta di Riccardo): la vista,
nel formato scelto, finisce nella cartella delle viste, e stile, invio,
render, ritocchi e video si fanno nello Studio. «Apri nello Studio» lo avvia
fuori da Allplan, con un Python che non e' Allplan, scelto con la regola
della sonda (`sonda_palette.candidati_python`). Uno Studio e una coda sola
per cartella: lo dice il battito in `lavori/` (core/battito.py).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from core import battito as modulo_battito, blocchi, coda as modulo_coda, config
from core import immagine as modulo_immagine
from core.errori import ErroreAirender
from core.provider import comfy
from core.studio import servizio

import sonda_palette as sonda

COME_LA_FINESTRA = "Come la finestra"
# I formati fissi sono i rapporti che i modelli accettano: con uno di questi
# la vista parte senza cornice e torna della stessa forma.
_NOMI_FORMATO = {"21:9": "21:9 panoramico", "1:1": "1:1 quadrato", "3:4": "3:4 verticale",
                 "2:3": "2:3 verticale", "9:16": "9:16 verticale"}
# Fuori dalla cartella delle viste: lo Studio non le elenca come viste.
CARTELLA_ANTEPRIME = "anteprime"
NESSUNA_VISTA = (
    "Nessuna vista ancora. Clicca una volta nella finestra 3D da rendere "
    "(shaded, con ombre), poi Cattura vista."
)


class PythonNonTrovato(ErroreAirender):
    """Nessun Python fuori da Allplan, con Pillow, che possa far girare lo Studio."""


class StudioNonPartito(ErroreAirender):
    """Lo Studio e' stato lanciato ma il suo battito non e' comparso."""


# --- le voci della palette ---------------------------------------------------


def voci_palette() -> dict[str, list[tuple[str | None, str]]]:
    """Gli elenchi a scelta della palette.

    Il .pyp si genera da qui (allplan/v2026/scrivi_palette_pyp.py), e un test
    controlla che il .pyp nel repository sia aggiornato.
    """
    return {
        "Formato": [(None, COME_LA_FINESTRA)] + [(r, _NOMI_FORMATO.get(r, r)) for r in comfy.RAPPORTI],
    }


def _identificativo(elenco: str, nome: str) -> str | None:
    for identificativo, voce in voci_palette()[elenco]:
        if voce == nome:
            return identificativo
    voci = ", ".join(v for _i, v in voci_palette()[elenco])
    raise blocchi.SceltaNonValida(
        f"Nella palette c'e' una scelta che il motore non conosce: «{nome}».",
        f"Reinstalla la palette e riaprila. Le scelte possibili sono: {voci}.",
    )


@dataclass(frozen=True)
class ValoriPalette:
    """Quello che c'e' scritto nei campi della palette, come lo legge l'adattatore."""

    formato: str = COME_LA_FINESTRA

    def rapporto(self) -> float | None:
        """Il formato fisso come larghezza/altezza; None per «Come la finestra»."""
        formato = _identificativo("Formato", self.formato or COME_LA_FINESTRA)
        if formato is None:
            return None
        a, b = (int(x) for x in formato.split(":"))
        return a / b

    def suffisso_formato(self) -> str:
        formato = _identificativo("Formato", self.formato or COME_LA_FINESTRA)
        return formato.replace(":", "x") if formato else ""


# --- testi ---------------------------------------------------------------------


def _percento(quota: float) -> str:
    return f"{round(quota * 100)}%"  # numero-non-configurabile: da quota a percento


def testo_esito(descrizione: dict) -> str:
    """L'esito dell'idoneita' in una riga, come nel mockup; se non va, cosa risalvare."""
    if not descrizione.get("leggibile"):
        return f"Non si legge: {descrizione.get('fatto')} {descrizione.get('cosa_fare')}"
    if not descrizione.get("idonea"):
        return f"Non adatta: {descrizione.get('fatto')} {descrizione.get('cosa_fare')}"
    testo = (f"Adatta: shaded, {descrizione['toni']} toni, "
             f"sfondo uniforme {_percento(descrizione['quota_sfondo'])}")
    if descrizione.get("colori_come_materiali"):
        testo += (". Il modello legge i colori della vista come materiali: per colori "
                  "veri, salva la vista con colori neutri")
    return testo


def _errore(errore: ErroreAirender) -> str:
    return f"{errore.fatto}\n\nCosa fare: {errore.cosa_fare}"


# --- il telecomando --------------------------------------------------------------


class Telecomando:
    """La palette su una cartella delle viste."""

    def __init__(self, cartella: Path, avviatore: "Avviatore | None" = None,
                 studio: servizio.Studio | None = None) -> None:
        self.cartella = Path(cartella)
        self.studio = studio or servizio.Studio(self.cartella)
        self.cartella = self.studio.cartella
        self.avviatore = avviatore

    # --- vista ---------------------------------------------------------

    def vista(self, percorso: str) -> tuple[str, str]:
        """Nome e dimensioni, ed esito. Senza vista, la frase dello stato vuoto."""
        percorso = (percorso or "").strip()
        if not percorso:
            return NESSUNA_VISTA, ""
        try:
            descrizione = self.studio.descrivi_vista(self._nome(percorso))
        except ErroreAirender as errore:
            return Path(percorso).name, _errore(errore)
        dimensioni = (f" {descrizione['larghezza']}×{descrizione['altezza']}"
                      if descrizione.get("leggibile") else "")
        return f"{Path(percorso).name}{dimensioni}", testo_esito(descrizione)

    def _nome(self, percorso: str) -> str:
        vista = Path(percorso)
        if vista.parent.resolve() != self.cartella:
            raise servizio.RichiestaStudioNonValida(
                f"La vista {vista.name} non sta nella cartella delle viste ({self.cartella}).",
                "Cattura di nuovo la vista: si salva nella cartella giusta.",
            )
        return vista.name

    # --- formato fisso ---------------------------------------------------

    def _taglio(self, vista: str) -> Path:
        return self.cartella / CARTELLA_ANTEPRIME / f"{Path(vista).stem}-taglio.png"

    def taglia_cattura(self, vista: str, valori: ValoriPalette) -> bool:
        """Con un formato fisso, la vista appena catturata diventa la sua parte centrale al formato.

        Nella cartella delle viste resta solo la vista tagliata: e' quella che
        lo Studio usa e confronta con il render. In anteprime/ resta la
        finestra intera con scurito quello che e' stato tagliato, per «Vedi
        cosa ha tagliato». Restituisce se ha tagliato.
        """
        rapporto = valori.rapporto()
        taglio = self._taglio(vista)
        if rapporto is None:
            taglio.unlink(missing_ok=True)  # una cattura nuova con lo stesso nome non e' tagliata
            return False
        intera = modulo_immagine.leggi(vista)
        taglio.parent.mkdir(parents=True, exist_ok=True)
        taglio.write_bytes(modulo_immagine.anteprima_taglio(intera, rapporto))
        Path(vista).write_bytes(modulo_immagine.ritaglia_a_rapporto(intera, rapporto))
        return True

    def anteprima(self, vista: str) -> str:
        """La finestra intera con scurito quello che il formato ha tagliato; la vista se non e' stata tagliata."""
        vista = (vista or "").strip()
        if not vista:
            return vista
        taglio = self._taglio(vista)
        return str(taglio) if taglio.is_file() else vista


# --- processi: la coda, lo Studio, Edge -----------------------------------------


class Avviatore:
    """Avvia lo Studio (e con lui la coda) fuori da Allplan, staccato.

    Tutto quello che tocca il sistema arriva da fuori, cosi' si prova senza
    Windows: chi cerca un programma, chi esegue, chi lancia, chi aspetta.
    """

    def __init__(
        self,
        cartella: Path,
        cartella_script: Path,
        *,
        prefissi: list[str],
        eseguibile: str,
        cartella_pillow: str | None = None,
        ambiente: dict[str, str] | None = None,
        trova: Callable[[str], str | None] = shutil.which,
        esegui: Callable = subprocess.run,
        lancia: Callable = subprocess.Popen,
        aspetta: Callable[[float], None] = time.sleep,
        orologio: Callable[[], float] = time.monotonic,
        apri_url: Callable[[str], object] = webbrowser.open,
        esiste: Callable[[str], bool] = os.path.exists,
    ) -> None:
        self.cartella = Path(cartella)
        self.cartella_script = Path(cartella_script)
        self.prefissi = prefissi
        self.eseguibile = eseguibile
        self.cartella_pillow = cartella_pillow
        self.ambiente = dict(os.environ if ambiente is None else ambiente)
        self._trova, self._esegui, self._lancia = trova, esegui, lancia
        self._aspetta, self._orologio, self._apri_url, self._esiste = aspetta, orologio, apri_url, esiste
        self._python: tuple[str, list[str], dict[str, str]] | None = None
        self.provati: list[str] = []
        self._ultimo_lancio = ""

    # --- quale Python ----------------------------------------------------

    def _ambiente(self, origine: str) -> dict[str, str]:
        ambiente = sonda.ambiente_per(origine, self.ambiente)
        # Senza console Python scriverebbe nella codifica di Windows (cp1252):
        # la coda e lo Studio scrivono in UTF-8, come i loro file.
        ambiente["PYTHONIOENCODING"] = "utf-8"
        if "sistema" not in origine and self.cartella_pillow:
            # Il Python di Allplan fuori da Allplan non vede la cartella dove
            # «Install Python Package» ha messo Pillow: gliela si indica.
            ambiente["PYTHONPATH"] = os.pathsep.join(
                p for p in (self.cartella_pillow, ambiente.get("PYTHONPATH", "")) if p)
        return ambiente

    def python(self) -> tuple[str, list[str], dict[str, str]]:
        """Il primo Python, fuori da Allplan, che risponde e ha Pillow. Si cerca una volta."""
        if self._python is not None:
            return self._python
        self.provati = []
        for origine, comando in sonda.candidati_python(self.prefissi, self.eseguibile, self._trova):
            ambiente = self._ambiente(origine)
            try:
                risultato = self._esegui(
                    [*comando, "-c", sonda.CODICE_IDENTITA], capture_output=True, text=True,
                    timeout=config.PALETTE_SECONDI_ATTESA_STUDIO * 2, env=ambiente,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                identita = sonda.interpreta_identita(risultato.stdout + risultato.stderr)
            except (OSError, subprocess.SubprocessError) as errore:
                identita = {"letto": False, "uscita": f"{type(errore).__name__}: {errore}"}
            self.provati.append(f"{origine}: {identita}")
            if identita.get("letto") and identita.get("pillow"):
                self._python = (origine, comando, ambiente)
                return self._python
        raise PythonNonTrovato(
            "Non trovo un Python, fuori da Allplan, con Pillow, che faccia girare la coda dei lavori. "
            "Provati: " + ("; ".join(self.provati) or "nessuno"),
            "Installa Python 3 da python.org con l'opzione «py launcher», poi in un "
            "prompt: py -m pip install pillow. Riapri la palette.",
        )

    # --- Studio e coda ---------------------------------------------------

    def studio_vivo(self) -> dict | None:
        return modulo_battito.leggi(modulo_battito.percorso(self.cartella, modulo_battito.FILE_STUDIO))

    def avvia_studio(self, finestra: bool) -> None:
        """Lancia python -m core.studio sulla cartella, staccato da Allplan."""
        origine, comando, ambiente = self.python()
        argomenti = [*comando, "-m", "core.studio", "--cartella", str(self.cartella)]
        if not finestra:
            argomenti.append("--senza-finestra")
        self._lancia(argomenti, cwd=str(self.cartella_script), env=ambiente, **sonda.opzioni_staccato())
        self._ultimo_lancio = f"{origine}: {' '.join(argomenti)}"

    def _attendi(self, vivo: Callable[[], object]) -> bool:
        limite = self._orologio() + config.PALETTE_SECONDI_ATTESA_STUDIO
        while self._orologio() < limite:
            if vivo():
                return True
            self._aspetta(config.BATTITO_INTERVALLO_SECONDI)
        return bool(vivo())

    def assicura_coda(self) -> None:
        """Se sulla cartella non gira una coda, avvia lo Studio senza finestra, che la avvia."""
        if modulo_coda.coda_viva(self.cartella) is not None:
            return
        self.avvia_studio(finestra=False)
        if not self._attendi(lambda: modulo_coda.coda_viva(self.cartella)):
            raise StudioNonPartito(
                f"Ho avviato lo Studio ({self._ultimo_lancio}), ma dopo "
                f"{config.PALETTE_SECONDI_ATTESA_STUDIO} secondi la coda non batte ancora.",
                "Riprova fra qualche secondo con Aggiorna. Se resta ferma, lancia a mano "
                f"in un prompt, dalla cartella {self.cartella_script}: "
                f"py -m core.studio --cartella \"{self.cartella}\", e mandami cosa scrive.",
            )

    def apri_studio(self) -> str:
        """Riporta davanti lo Studio se gira, altrimenti lo avvia con la sua finestra."""
        vivo = self.studio_vivo()
        if vivo and vivo.get("indirizzo"):
            edge = next((p for p in sonda.percorsi_edge(self.ambiente, self._trova) if self._esiste(p)), None)
            if edge:
                self._lancia(sonda.comando_edge(edge, vivo["indirizzo"]), **sonda.opzioni_staccato())
                return f"Studio aperto in Edge su {vivo['indirizzo']}."
            self._apri_url(vivo["indirizzo"])
            return f"Studio aperto nel browser predefinito su {vivo['indirizzo']} (Edge non trovato)."
        self.avvia_studio(finestra=True)
        return "Studio avviato: la sua finestra si apre fra qualche secondo."
