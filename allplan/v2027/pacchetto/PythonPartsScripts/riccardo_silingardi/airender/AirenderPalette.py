"""AIRENDER — la palette v1 (il telecomando) per Allplan 2027.

Copia dell'adattatore 2026 (regola 2 di CLAUDE.md): le chiamate usate
(SaveWindowToImageFile, GetViewWorldProjection, BaseScriptObject,
AllplanPaths.GetUsrPath) sono negli esempi ufficiali del ramo 2027. Un test
(tests/test_pacchetto_2027.py) controlla che resti uguale a quello 2026 sotto
questa intestazione: quando la 2027 chiedera' una differenza, si toglie il test
e la si scrive qui.

Unico file della palette che importa Allplan. Fa solo quello che esiste
soltanto dentro Allplan: cattura la finestra, legge la camera e i materiali,
legge e scrive i campi della palette (AirenderPalette.pyp), mostra i
messaggi. Tutto il resto e' in `telecomando.py`, che sta accanto e si prova
con pytest.

Dal 2026-11-04 la palette cattura e basta: stile, invio, render e ritocchi
si fanno nello Studio, che gira in un processo a parte.
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Utility as AllplanUtil

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult

try:
    # Esc chiude la palette e fa tornare la Library: on_cancel_function piu' sotto.
    from ScriptObjectInteractors.OnCancelFunctionResult import OnCancelFunctionResult
except ImportError:  # un framework senza questo modulo: resta il comportamento di Allplan
    OnCancelFunctionResult = None

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

# Se un import fallisce (Pillow mancante, file non copiato, Python diverso)
# Allplan non apre la palette e spesso non dice niente. L'errore si tiene qui,
# si scrive in Usr\AIRENDER\avvio.txt e si mostra al primo clic.
_ERRORE_AVVIO = ""
try:
    # pylint: disable=wrong-import-position
    import ponte  # noqa: E402
    import telecomando  # noqa: E402
    from core import config  # noqa: E402
    from core.errori import ErroreAirender  # noqa: E402
    from core.studio import servizio  # noqa: E402
except Exception:  # pylint: disable=broad-exception-caught
    _ERRORE_AVVIO = traceback.format_exc()

EVENTO_CATTURA = 1001
EVENTO_APRI_STUDIO = 1006
EVENTO_APRI_CARTELLA = 1007
EVENTO_VEDI_TAGLIO = 1008

# Le dimensioni del radio «Dimensione», nell'ordine del .pyp.
DIMENSIONI = (None, (1920, 1080), (3840, 2160))


print("Load AirenderPalette.py, Python", sys.version.split()[0])


def _file_avvio() -> Path:
    return Path(AllplanSettings.AllplanPaths.GetUsrPath()) / "AIRENDER" / "avvio.txt"


def _scrivi_avvio(errore: str) -> str:
    """Scrive cosa ha visto la palette all'avvio. Restituisce il percorso, o il motivo per cui non c'e'."""
    try:
        try:
            import PIL  # pylint: disable=import-outside-toplevel
            pillow = f"{PIL.__version__} in {Path(PIL.__file__).parent}"
        except ImportError as mancante:
            pillow = f"NON TROVATO ({mancante})"
        righe = [
            f"AIRENDER, avvio della palette: {datetime.now():%Y-%m-%d %H:%M:%S}",
            f"Python {sys.version}",
            f"eseguibile {sys.executable}",
            f"cartella dello script {_CARTELLA}",
            f"file accanto: {sorted(p.name for p in _CARTELLA.iterdir())}",
            f"Pillow {pillow}",
            "sys.path:", *[f"  {voce}" for voce in sys.path],
            "", "ERRORE:" if errore else "Nessun errore.", errore,
        ]
        percorso = _file_avvio()
        percorso.parent.mkdir(parents=True, exist_ok=True)
        percorso.write_text("\n".join(righe), encoding="utf-8")
        return str(percorso)
    except Exception as non_scritto:  # pylint: disable=broad-exception-caught
        return f"(avvio.txt non scritto: {non_scritto})"


def _mostra_errore_avvio(errore: str) -> None:
    dove = _scrivi_avvio(errore)
    ultime = "\n".join(errore.strip().splitlines()[-4:])
    _messaggio(f"AIRENDER non si apre.\n\n{ultime}\n\nTutti i dettagli sono in:\n{dove}\n"
               "Mandalo a chi ti segue AIRENDER.")


def check_allplan_version(_build_ele: BuildingElement, _version: str) -> bool:
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    if _ERRORE_AVVIO:
        _mostra_errore_avvio(_ERRORE_AVVIO)
        raise RuntimeError("AIRENDER: import fallito, vedi Usr\\AIRENDER\\avvio.txt")
    try:
        palette = AirenderPalette(build_ele, script_object_data)
    except Exception:
        _mostra_errore_avvio(traceback.format_exc())
        raise
    _scrivi_avvio("")
    return palette


def _cartella_pillow() -> str | None:
    """Dove «Install Python Package» ha messo Pillow: serve al Python di Allplan fuori da Allplan."""
    try:
        import PIL  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None
    return str(Path(PIL.__file__).resolve().parents[1])


class AirenderPalette(BaseScriptObject):
    """Vista e Apri nello Studio."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.build_ele.ImmaginiDaScript.value = 1 if config.PALETTE_IMMAGINI_DA_SCRIPT else 0
        self.telecomando = None
        self._apri()

    def execute(self) -> CreateElementResult:
        # Questo PythonPart non crea elementi.
        return CreateElementResult()

    def on_cancel_function(self):
        """Esc: chiude la palette senza creare niente e torna alla Library.

        I lavori gia' in coda continuano: li fa girare lo Studio, un processo a parte.
        """
        if OnCancelFunctionResult is None:
            return super().on_cancel_function()
        return OnCancelFunctionResult.CANCEL_INPUT

    # ------------------------------------------------------------ cartella

    def _cartella(self) -> Path:
        scelta = (self.build_ele.Cartella.value or "").strip()
        if scelta:
            cartella = Path(scelta)
        else:
            cartella = Path(AllplanSettings.AllplanPaths.GetUsrPath()) / "AIRENDER" / "viste"
        cartella.mkdir(parents=True, exist_ok=True)
        return cartella

    def _apri(self) -> None:
        """Crea il telecomando sulla cartella scelta e scrive tutti i campi."""
        try:
            cartella = self._cartella()
            avviatore = telecomando.Avviatore(
                cartella, _CARTELLA,
                prefissi=[sys.prefix, sys.base_prefix, str(Path(sys.executable).parent)],
                eseguibile=sys.executable,
                cartella_pillow=_cartella_pillow(),
            )
            self.telecomando = telecomando.Telecomando(cartella, avviatore=avviatore)
        except (ErroreAirender, OSError) as errore:
            self.telecomando = None
            self.build_ele.VistaEsito.value = f"La palette non si apre: {errore}"
            return
        self._aggiorna()

    # ------------------------------------------------------------ eventi

    def on_control_event(self, event_id: int) -> None:
        if self.telecomando is None or Path(self.telecomando.cartella) != self._cartella().resolve():
            self._apri()  # cartella cambiata nel campo in fondo, o primo avvio fallito
        if self.telecomando is None:
            return
        azioni = {
            EVENTO_CATTURA: self._cattura,
            EVENTO_APRI_STUDIO: self._apri_studio,
            EVENTO_APRI_CARTELLA: self._apri_cartella,
            EVENTO_VEDI_TAGLIO: self._vedi_taglio,
        }
        azione = azioni.get(event_id)
        if azione is None:
            return
        try:
            azione()
        except ErroreAirender as errore:
            _messaggio(f"{errore.fatto}\n\nCosa fare: {errore.cosa_fare}")
        except Exception as errore:  # pylint: disable=broad-exception-caught
            # La palette non deve mai restare muta: l'imprevisto si mostra com'e'.
            _messaggio(f"Errore imprevisto della palette: {type(errore).__name__}: {errore}")
        self._aggiorna()

    def _cattura(self) -> None:
        vista = ponte.percorso_vista(self.telecomando.cartella)
        dimensione = DIMENSIONI[int(self.build_ele.Dimensione.value or 0)]
        if dimensione:
            riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(
                str(vista), pixelWidth=dimensione[0], pixelHeight=dimensione[1])
        else:
            riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(vista))
        if not riuscita or not vista.exists():
            _messaggio(
                "Allplan non ha salvato l'immagine della finestra.\n\n"
                "Cosa fare: clicca una volta dentro la finestra 3D che vuoi catturare, "
                "poi premi di nuovo Cattura vista.")
            return
        tagliata = self.telecomando.taglia_cattura(str(vista), self._valori())
        ponte.scrivi_camera(vista, self._camera())
        self.build_ele.UltimaVista.value = str(vista)
        self._leggi_materiali(vista)
        if tagliata:
            self._vedi_taglio()  # con un formato fisso, si vede subito cosa e' rimasto fuori

    def _leggi_materiali(self, vista: Path) -> None:
        """I materiali del progetto, accanto alla vista, per la tabella dello Studio. Solo lettura.

        Un errore qui non ferma la cattura: lo Studio scrive che i materiali
        non si sono letti.
        """
        try:
            import lettore_materiali  # pylint: disable=import-outside-toplevel
            documento = None
            # Come la sonda dell'elenco, che ha letto il 4253 il 2026-11-02.
            for leggi in (lambda: self.document, lambda: self.coord_input.GetInputViewDocument()):
                try:
                    documento = leggi()
                except Exception:  # pylint: disable=broad-exception-caught
                    continue
                if documento is not None:
                    break
            lettore_materiali.leggi_e_scrivi(documento, vista)
        except Exception:  # pylint: disable=broad-exception-caught
            pass  # lo scrive leggi_e_scrivi nel file dei materiali; lo Studio lo mostra

    def _camera(self) -> dict:
        """Da dove guarda la finestra. Ogni voce che fallisce resta scritta come errore."""
        proiezione = self.coord_input.GetViewWorldProjection()
        letture = {
            "occhio": lambda: _punto(proiezione.GetEyePoint()),
            "punto_guardato": lambda: _punto(proiezione.GetViewPoint()),
            "prospettiva_centrale": proiezione.IsCentralProjection,
        }
        camera = {}
        for nome, leggi in letture.items():
            try:
                camera[nome] = leggi()
            except Exception as errore:  # pylint: disable=broad-exception-caught
                camera[nome] = f"errore: {type(errore).__name__}: {errore}"
        return camera

    def _valori(self) -> telecomando.ValoriPalette:
        return telecomando.ValoriPalette(formato=self.build_ele.Formato.value)

    def _vedi_taglio(self) -> None:
        vista = self.build_ele.UltimaVista.value or ""
        if not vista:
            _messaggio("Non c'e' ancora una vista.\n\nCosa fare: premi prima Cattura vista.")
            return
        anteprima = self.telecomando.anteprima(vista)
        if anteprima == vista:
            _messaggio("Questa vista non e' stata tagliata: e' stata catturata con il formato "
                       "«Come la finestra».")
            return
        servizio.apri_nel_sistema(Path(anteprima))

    def _apri_studio(self) -> None:
        self.telecomando.avviatore.apri_studio()

    def _apri_cartella(self) -> None:
        servizio.apri_nel_sistema(self.telecomando.cartella)

    # ------------------------------------------------------------ campi

    def _aggiorna(self) -> None:
        """Dopo ogni evento: nome ed esito della vista, letti dal disco."""
        e = self.build_ele
        nome, esito = self.telecomando.vista(e.UltimaVista.value or "")
        e.VistaNome.value, e.VistaEsito.value = nome, esito
        if config.PALETTE_IMMAGINI_DA_SCRIPT and e.UltimaVista.value and os.path.exists(e.UltimaVista.value):
            # Il secondo dei due modi provati dalla sonda: percorso assoluto nel valore.
            e.VistaImmagine.value = self.telecomando.anteprima(e.UltimaVista.value)


def _messaggio(testo: str) -> None:
    AllplanUtil.ShowMessageBox(testo, AllplanUtil.MB_OK)


def _punto(punto) -> list[float]:
    return [round(punto.X, 3), round(punto.Y, 3), round(punto.Z, 3)]

