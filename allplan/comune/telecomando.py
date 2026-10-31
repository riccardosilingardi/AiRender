"""La palette v1 di Allplan, il telecomando: tutto quello che non importa Allplan.

L'adattatore di ogni versione (allplan/v2026/.../AirenderPalette.py) fa solo
quello che esiste soltanto dentro Allplan: cattura della finestra, lettura
della camera, lettura e scrittura dei campi della palette, finestre di
messaggio. Il resto e' qui e si prova con pytest.

La palette non genera piu' dentro Allplan. Usa lo stesso servizio dello
Studio (`core.studio.servizio.Studio`) sulla stessa cartella delle viste:
stesse scelte, stessi nomi, stessa destinazione e stesso costo, stesso
controllo che la destinazione mostrata sia quella vera prima di scrivere il
lavoro in coda. Poi torna libera: il lavoro lo prende la coda, un processo a
parte.

Se la coda non gira, la palette avvia lo Studio senza finestra (che avvia la
coda) con un Python che non e' Allplan, scelto con la regola della sonda
(`sonda_palette.candidati_python`). Una coda sola per cartella: lo dice il
battito in `lavori/coda-viva.json` (core/battito.py).
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

import ponte
import sonda_palette as sonda

COME_IL_PRESET = "Come il preset"
COME_LA_FINESTRA = "Come la finestra"
# I formati fissi sono i rapporti che i modelli accettano: con uno di questi
# la vista parte senza cornice e torna della stessa forma.
_NOMI_FORMATO = {"21:9": "21:9 panoramico", "1:1": "1:1 quadrato", "3:4": "3:4 verticale",
                 "2:3": "2:3 verticale", "9:16": "9:16 verticale"}
CARTELLA_ANTEPRIME = "anteprime"
NESSUNA_VISTA = (
    "Nessuna vista ancora. Clicca una volta nella finestra 3D da rendere "
    "(shaded, con ombre), poi Cattura."
)
NESSUN_RENDER = "Nessun render ancora."
GENERA = "Genera render"
IN_CORSO = (
    "In corso da {tempo}. Allplan resta libero; l'avanzamento è nello Studio."
)


class PythonNonTrovato(ErroreAirender):
    """Nessun Python fuori da Allplan, con Pillow, che possa far girare la coda."""


class StudioNonPartito(ErroreAirender):
    """Lo Studio e' stato lanciato ma il suo battito non e' comparso."""


# --- le voci della palette ---------------------------------------------------


def _preset(scena: str) -> list[tuple[str, str]]:
    return [(p.identificativo, p.nome) for p in blocchi.PRESET_STILE.values() if p.scelte.scena == scena]


def _voci(asse: str, scena: str) -> list[tuple[str, str]]:
    return [(None, COME_IL_PRESET)] + [
        (b.identificativo, b.nome) for b in blocchi.voci(asse, scena).values()
    ]


def voci_palette() -> dict[str, list[tuple[str | None, str]]]:
    """Gli elenchi a scelta della palette, con gli stessi nomi dello Studio · Genera.

    Il .pyp si genera da qui (allplan/v2026/scrivi_palette_pyp.py): un nome
    cambiato in core/blocchi.py cambia la palette, e un test controlla che il
    .pyp nel repository sia aggiornato.
    """
    return {
        "PresetEsterno": _preset(blocchi.ESTERNO),
        "PresetInterno": _preset(blocchi.INTERNO),
        "LuceEsterno": _voci("luce", blocchi.ESTERNO),
        "LuceInterno": _voci("luce", blocchi.INTERNO),
        "Cielo": _voci("cielo", blocchi.ESTERNO),
        "Intorno": _voci("intorno", blocchi.ESTERNO),
        "Verde": _voci("verde", blocchi.ESTERNO),
        "Persone": _voci("persone", blocchi.ESTERNO),
        "Formato": [(None, COME_LA_FINESTRA)] + [(r, _NOMI_FORMATO.get(r, r)) for r in comfy.RAPPORTI],
        "Modello": [(m.identificativo, m.nome) for m in servizio.MODELLI],
    }


def _identificativo(elenco: str, nome: str) -> str | None:
    for identificativo, voce in voci_palette()[elenco]:
        if voce == nome:
            return identificativo
    voci = ", ".join(v for _i, v in voci_palette()[elenco])
    raise blocchi.SceltaNonValida(
        f"Nella palette c'e' una scelta che il motore non conosce: «{nome}».",
        f"Reinstalla la palette (installa.ps1) e riaprila. Le scelte possibili sono: {voci}.",
    )


@dataclass(frozen=True)
class ValoriPalette:
    """Quello che c'e' scritto nei campi della sezione Stile, come lo legge l'adattatore."""

    interno: bool = False
    preset_esterno: str = ""
    preset_interno: str = ""
    luce_esterno: str = COME_IL_PRESET
    luce_interno: str = COME_IL_PRESET
    cielo: str = COME_IL_PRESET
    intorno: str = COME_IL_PRESET
    verde: str = COME_IL_PRESET
    persone: str = COME_IL_PRESET
    materiali: str = ""
    modello: str = ""
    formato: str = COME_LA_FINESTRA

    def preset(self) -> str:
        if self.interno:
            return _identificativo("PresetInterno", self.preset_interno)
        return _identificativo("PresetEsterno", self.preset_esterno)

    def scelte(self) -> blocchi.Scelte:
        """Le scelte del preset con i cambi della palette sopra, come in Studio · Genera."""
        cambi: dict = {"materiali": " ".join((self.materiali or "").split())}
        if self.interno:
            luce = _identificativo("LuceInterno", self.luce_interno)
        else:
            luce = _identificativo("LuceEsterno", self.luce_esterno)
            cielo = _identificativo("Cielo", self.cielo)
            intorno = _identificativo("Intorno", self.intorno)
            verde = _identificativo("Verde", self.verde)
            if cielo:
                cambi["cielo"] = cielo
            if intorno:
                cambi["intorno"] = intorno
            if verde:
                cambi["verde"] = verde
        persone = _identificativo("Persone", self.persone)
        if persone:
            cambi["persone"] = persone
        if luce:
            cambi["luce"] = luce
        return blocchi.da_preset(self.preset(), **cambi)

    def modello_id(self) -> str:
        return _identificativo("Modello", self.modello)

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


def durata(secondi: int | None) -> str:
    if secondi is None:
        return "un tempo che non so dire"
    minuti, resto = divmod(int(secondi), 60)  # numero-non-configurabile: secondi in un minuto
    return f"{minuti}:{resto:02d}"


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


@dataclass(frozen=True)
class Riepilogo:
    """Quello che la palette scrive dopo ogni evento: Invio e Ultimo render."""

    stato: str
    ultimo: str
    lavoro_attivo: str
    render: str


class Telecomando:
    """La palette su una cartella delle viste."""

    def __init__(self, cartella: Path, avviatore: "Avviatore | None" = None,
                 studio: servizio.Studio | None = None) -> None:
        self.cartella = Path(cartella)
        self.studio = studio or servizio.Studio(
            self.cartella, coda_attiva=lambda: modulo_coda.coda_viva(self.cartella) is not None)
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

    def anteprima(self, vista: str, valori: ValoriPalette) -> str:
        """L'immagine da mostrare nella palette: la vista, o la vista con scurito cio' che il formato taglia."""
        vista = (vista or "").strip()
        rapporto = valori.rapporto()
        if not vista or rapporto is None or not Path(vista).is_file():
            return vista
        cartella = self.cartella / CARTELLA_ANTEPRIME
        cartella.mkdir(parents=True, exist_ok=True)
        uscita = cartella / f"{Path(vista).stem}-{valori.suffisso_formato()}.png"
        if not uscita.exists():
            uscita.write_bytes(modulo_immagine.anteprima_taglio(modulo_immagine.leggi(vista), rapporto))
        return str(uscita)

    def vista_al_formato(self, vista: str, valori: ValoriPalette) -> str:
        """La vista che parte davvero: con un formato fisso, una vista nuova tagliata al centro.

        E' una vista a tutti gli effetti, accanto all'originale: lo Studio
        confronta il render con quella, non con la finestra intera.
        """
        rapporto = valori.rapporto()
        if rapporto is None:
            return vista
        originale = Path(vista)
        tagliata = originale.with_name(f"{originale.stem}-{valori.suffisso_formato()}{originale.suffix}")
        if not tagliata.exists():
            tagliata.write_bytes(modulo_immagine.ritaglia_a_rapporto(modulo_immagine.leggi(originale), rapporto))
            camera = originale.with_name(originale.stem + ponte.SUFFISSO_CAMERA)
            if camera.is_file():
                shutil.copyfile(camera, tagliata.with_name(tagliata.stem + ponte.SUFFISSO_CAMERA))
        return str(tagliata)

    # --- invio ---------------------------------------------------------

    def invio(self, valori: ValoriPalette) -> tuple[str, str, str]:
        """Dove va la vista, cosa sapere sull'invio e quanto costa, da scrivere prima di Genera (regola 5).

        Il primo testo e' la destinazione nuda: Genera la confronta con quella
        vera, e se non coincide non parte niente.
        """
        destinazione = self.studio.destinazione(valori.modello_id())
        nota = "Senza ripiego su altri servizi." if destinazione["senza_ripiego"] else (
            "Attenzione: il servizio puo' ripiegare su un altro fornitore.")
        if destinazione["cosa_manca"]:
            nota += f" Non parte: {destinazione['cosa_manca']}"
        if destinazione.get("avviso"):
            nota += f" {destinazione['avviso']}"
        return destinazione["destinazione"], nota, destinazione["costo"]

    def _dati(self, vista: str, valori: ValoriPalette, destinazione_mostrata: str = "") -> dict:
        return {
            "vista": self._nome(vista),
            "scelte": valori.scelte().a_dizionario(),
            "preset": valori.preset(),
            "modello": valori.modello_id(),
            "destinazione_mostrata": destinazione_mostrata,
        }

    def prova_a_secco(self, vista: str, valori: ValoriPalette) -> str:
        """Tutto quello che farebbe Genera, tranne mandare. Il testo per la finestra di messaggio."""
        if not (vista or "").strip():
            return "Non c'e' ancora una vista da usare.\n\nCosa fare: premi prima Cattura vista."
        try:
            esito = self.studio.prova_a_secco(self._dati(vista, valori))
        except ErroreAirender as errore:
            return _errore(errore)
        righe = [
            "Prova a secco: non ho mandato niente.",
            f"La vista andrebbe a: {esito['destinazione']['destinazione']}.",
            f"Costo: {esito['destinazione']['costo']}.",
            f"Prompt ({esito['caratteri']} caratteri):\n{esito['prompt']}",
        ]
        # La coda ferma non ferma Genera della palette: Genera la fa partire.
        problemi = [p for p in esito["problemi"] if p != servizio._CODA_FERMA]  # pylint: disable=protected-access
        if problemi:
            righe.append("Genera si fermerebbe per:")
            righe += [f"- {p['fatto']} {p['cosa_fare']}" for p in problemi]
        else:
            righe.append("Genera partirebbe.")
        return "\n\n".join(righe)

    def genera(self, vista: str, valori: ValoriPalette, destinazione_mostrata: str) -> str:
        """Scrive il lavoro in coda e torna. Se la coda non gira, la fa partire.

        `destinazione_mostrata` e' quello che la palette ha scritto in
        «La vista va a»: se non e' la destinazione vera, non parte niente.
        """
        if not (vista or "").strip():
            return "Non c'e' ancora una vista da usare.\n\nCosa fare: premi prima Cattura vista."
        try:
            self._nome(vista)  # prima di scrivere una vista tagliata fuori posto
            vista = self.vista_al_formato(vista, valori)
            risposta = self.studio.invia(self._dati(vista, valori, destinazione_mostrata))
        except ErroreAirender as errore:
            return _errore(errore)
        testo = f"In coda, verso {risposta['destinazione']}. Allplan resta libero."
        if modulo_coda.coda_viva(self.cartella) is None:
            if self.avviatore is None:
                return f"{testo}\n\n{_CODA_FERMA['fatto']}\n\nCosa fare: {_CODA_FERMA['cosa_fare']}"
            try:
                self.avviatore.assicura_coda()
            except ErroreAirender as errore:
                return testo + "\n\nMa la coda dei lavori non gira, e il lavoro resta in attesa.\n" + _errore(errore)
        return testo

    def annulla(self, identificativo: str) -> str:
        if not identificativo:
            return "Non c'e' un lavoro in corso da annullare."
        try:
            self.studio.annulla(identificativo)
        except ErroreAirender as errore:
            return _errore(errore)
        return ("Chiesto l'annullamento. Se la vista era gia' partita, il servizio "
                "puo' averla gia' fatta e addebitata: lo dice lo stato del lavoro.")

    # --- dopo ogni evento --------------------------------------------------

    def riepilogo(self) -> Riepilogo:
        """Lo stato dell'ultimo lavoro e il riassunto dell'ultimo render, letti dal disco."""
        try:
            ultimo = self.studio.ultimo_lavoro()
        except ErroreAirender as errore:
            return Riepilogo(_errore(errore), NESSUN_RENDER, "", "")
        if ultimo is None:
            return Riepilogo("", NESSUN_RENDER, "", "")
        stato = ultimo["stato"]
        titolo = f"{ultimo['preset_nome']} · {ultimo['modello_nome']}"
        if ultimo["attivo"]:
            testo = IN_CORSO.format(tempo=durata(ultimo["secondi"]))
            if stato == modulo_coda.IN_CODA and modulo_coda.coda_viva(self.cartella) is None:
                testo = f"{_CODA_FERMA['fatto']} {_CODA_FERMA['cosa_fare']}"
            return Riepilogo(testo, f"{titolo} · {stato}", ultimo["identificativo"], "")
        if stato == modulo_coda.FATTO and ultimo["render"]:
            render = str(self.studio.file_render(ultimo["identificativo"]))
            try:
                crediti = self.studio.ricetta(ultimo["identificativo"]).get("crediti")
            except ErroreAirender:
                crediti = None
            riga = f"{titolo} · {crediti or 'crediti non letti dal servizio'}"
            return Riepilogo("Render pronto.", riga, "", render)
        if stato == modulo_coda.ERRORE:
            testo = (f"Non e' andato: {ultimo['fatto']} {ultimo['cosa_fare'] or ''} "
                     "Apri nello Studio per i dettagli.").replace("  ", " ")
            return Riepilogo(testo, f"{titolo} · errore", "", "")
        return Riepilogo(f"Ultimo lavoro: {stato}.", f"{titolo} · {stato}", "", "")

    def testo_genera(self, riepilogo: Riepilogo) -> str:
        return "Annulla" if riepilogo.lavoro_attivo else GENERA


_CODA_FERMA = {
    "fatto": "La coda dei lavori non sta girando: il lavoro resta in attesa.",
    "cosa_fare": "Premi Apri nello Studio: lo Studio la fa partire.",
}


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
