"""AIRENDER — la palette v1 (il telecomando) per Allplan 2027.

Copia dell'adattatore 2026 (regola 2 di CLAUDE.md): le chiamate usate
(SaveWindowToImageFile, GetViewWorldProjection, BaseScriptObject,
AllplanPaths.GetUsrPath) sono negli esempi ufficiali del ramo 2027. Un test
(tests/test_pacchetto_2027.py) controlla che resti uguale a quello 2026 sotto
questa intestazione: quando la 2027 chiedera' una differenza, si toglie il test
e la si scrive qui.

Unico file della palette v1 che importa Allplan. Fa solo quello che esiste
soltanto dentro Allplan: cattura la finestra, legge la camera, legge e scrive
i campi della palette (AirenderPalette.pyp), mostra i messaggi. Tutto il
resto e' in `telecomando.py`, che sta accanto e si prova con pytest.

Genera non chiama il motore dentro Allplan: scrive un lavoro nella coda e
torna. La coda e lo Studio girano in un processo a parte.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Utility as AllplanUtil

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

# pylint: disable=wrong-import-position
import ponte  # noqa: E402
import telecomando  # noqa: E402
from core import config  # noqa: E402
from core.errori import ErroreAirender  # noqa: E402
from core.studio import servizio  # noqa: E402

EVENTO_CATTURA = 1001
EVENTO_PROVA_A_SECCO = 1002
EVENTO_GENERA = 1003
EVENTO_ANNULLA = 1004
EVENTO_AGGIORNA = 1005
EVENTO_APRI_STUDIO = 1006
EVENTO_APRI_CARTELLA = 1007

# Le dimensioni del radio «Dimensione», nell'ordine del .pyp.
DIMENSIONI = (None, (1920, 1080), (3840, 2160))

RESA = "Fotorealistico · le altre rese aspettano il loro blocco di prompt (vedi lo Studio)"

print("Load AirenderPalette.py, Python", sys.version.split()[0])


def check_allplan_version(_build_ele: BuildingElement, _version: str) -> bool:
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderPalette(build_ele, script_object_data)


def _cartella_pillow() -> str | None:
    """Dove «Install Python Package» ha messo Pillow: serve al Python di Allplan fuori da Allplan."""
    try:
        import PIL  # pylint: disable=import-outside-toplevel
    except ImportError:
        return None
    return str(Path(PIL.__file__).resolve().parents[1])


class AirenderPalette(BaseScriptObject):
    """Vista, Stile, Invio, Ultimo render."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.build_ele.ImmaginiDaScript.value = 1 if config.PALETTE_IMMAGINI_DA_SCRIPT else 0
        self.build_ele.Resa.value = RESA
        self.telecomando = None
        self._apri()

    def execute(self) -> CreateElementResult:
        # Questo PythonPart non crea elementi. Allplan chiama execute anche
        # dopo un cambio in palette: si rileggono destinazione e costo, cosi'
        # un modello cambiato si vede prima di Genera (regola 5).
        self._aggiorna_invio()
        return CreateElementResult()

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
            self.build_ele.Stato.value = f"La palette non si apre: {errore}"
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
            EVENTO_PROVA_A_SECCO: self._prova_a_secco,
            EVENTO_GENERA: self._genera,
            EVENTO_ANNULLA: self._annulla,
            EVENTO_AGGIORNA: lambda: None,
            EVENTO_APRI_STUDIO: self._apri_studio,
            EVENTO_APRI_CARTELLA: self._apri_cartella,
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
        ponte.scrivi_camera(vista, self._camera())
        self.build_ele.UltimaVista.value = str(vista)

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
        e = self.build_ele
        return telecomando.ValoriPalette(
            interno=int(e.Interno.value or 0) == 1,
            preset_esterno=e.PresetEsterno.value,
            preset_interno=e.PresetInterno.value,
            luce_esterno=e.LuceEsterno.value,
            luce_interno=e.LuceInterno.value,
            cielo=e.Cielo.value,
            intorno=e.Intorno.value,
            materiali=e.Materiali.value or "",
            modello=e.Modello.value,
        )

    def _prova_a_secco(self) -> None:
        _messaggio(self.telecomando.prova_a_secco(self.build_ele.UltimaVista.value, self._valori()))

    def _genera(self) -> None:
        mostrata = self.build_ele.Destinazione.value or ""
        _messaggio(self.telecomando.genera(self.build_ele.UltimaVista.value, self._valori(), mostrata))

    def _annulla(self) -> None:
        _messaggio(self.telecomando.annulla(self.build_ele.LavoroAttivo.value or ""))

    def _apri_studio(self) -> None:
        self.telecomando.avviatore.apri_studio()

    def _apri_cartella(self) -> None:
        render = self.build_ele.UltimoRender.value
        servizio.apri_nel_sistema(Path(render).parent if render else self.telecomando.cartella)

    # ------------------------------------------------------------ campi

    def _aggiorna_invio(self) -> None:
        if self.telecomando is None:
            return
        try:
            dove, nota, costo = self.telecomando.invio(self._valori())
        except ErroreAirender as errore:
            dove, nota, costo = "", f"{errore.fatto} {errore.cosa_fare}", ""
        self.build_ele.Destinazione.value = dove
        self.build_ele.NotaInvio.value = nota
        self.build_ele.Costo.value = costo

    def _aggiorna(self) -> None:
        """Dopo ogni evento: vista, invio, stato del lavoro e ultimo render, letti dal disco."""
        e = self.build_ele
        nome, esito = self.telecomando.vista(e.UltimaVista.value or "")
        e.VistaNome.value, e.VistaEsito.value = nome, esito
        self._aggiorna_invio()
        riepilogo = self.telecomando.riepilogo()
        e.Stato.value = riepilogo.stato
        e.Ultimo.value = riepilogo.ultimo
        e.LavoroAttivo.value = riepilogo.lavoro_attivo
        e.InCorso.value = 1 if riepilogo.lavoro_attivo else 0
        e.UltimoRender.value = riepilogo.render
        if config.PALETTE_IMMAGINI_DA_SCRIPT:
            # Il secondo dei due modi provati dalla sonda: percorso assoluto nel valore.
            if e.UltimaVista.value and os.path.exists(e.UltimaVista.value):
                e.VistaImmagine.value = e.UltimaVista.value
            if riepilogo.render:
                e.UltimoImmagine.value = riepilogo.render


def _messaggio(testo: str) -> None:
    AllplanUtil.ShowMessageBox(testo, AllplanUtil.MB_OK)


def _punto(punto) -> list[float]:
    return [round(punto.X, 3), round(punto.Y, 3), round(punto.Z, 3)]

