"""AIRENDER — adattatore per Allplan 2026: cattura la vista e la passa al motore.

E' l'unico file del progetto che importa Allplan. Fa tre cose che esistono solo
dentro Allplan:

1. salva il contenuto della finestra attiva in un'immagine, con
   `DrawingService.SaveWindowToImageFile` (stessa chiamata dell'esempio
   ufficiale ServiceExamples/SaveWindowToImage dei PythonPartsExamples, ramo 2026);
2. legge da dove la finestra guarda la scena (`GetViewWorldProjection`) e lo
   salva accanto all'immagine;
3. passa l'immagine al motore attraverso `ponte.py`, che sta in questa stessa
   cartella insieme alla copia di `core/`.

Tutto il resto vive nel motore, che non sa che Allplan esiste.
"""

from __future__ import annotations

import sys
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_Utility as AllplanUtil

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult

# Il motore e il ponte sono copiati accanto a questo file dallo script di
# installazione: li rendiamo importabili senza toccare altro.
_CARTELLA = str(Path(__file__).resolve().parent)
if _CARTELLA not in sys.path:
    sys.path.insert(0, _CARTELLA)

import ponte  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_CATTURA = 1001
EVENTO_PROVA_A_SECCO = 1002
EVENTO_GENERA = 1003

print("Load AirenderProva.py")


def check_allplan_version(_build_ele: BuildingElement, _version: str) -> bool:
    """Questo adattatore e' scritto per la 2026; la 2027 avra' il suo file."""
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderProva(build_ele, script_object_data)


class AirenderProva(BaseScriptObject):
    """Palette minima: cattura, prova a secco, genera."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.ultima_vista: Path | None = None
        # Prima di ogni invio si dice dove va l'immagine (regola 5 di CLAUDE.md).
        self.build_ele.Destinazione.value = ponte.destinazione_predefinita()

    def execute(self) -> CreateElementResult:
        # Questo PythonPart non crea elementi nel disegno.
        return CreateElementResult()

    # ------------------------------------------------------------ eventi

    def on_control_event(self, event_id: int) -> None:
        if event_id == EVENTO_CATTURA:
            self._cattura()
        elif event_id in (EVENTO_PROVA_A_SECCO, EVENTO_GENERA):
            self._motore(a_secco=event_id == EVENTO_PROVA_A_SECCO)

    def _cartella(self) -> Path:
        scelta = (self.build_ele.Cartella.value or "").strip()
        if scelta:
            cartella = Path(scelta)
        else:
            cartella = Path(AllplanSettings.AllplanPaths.GetUsrPath()) / "AIRENDER" / "viste"
        cartella.mkdir(parents=True, exist_ok=True)
        return cartella

    def _cattura(self) -> None:
        vista = ponte.percorso_vista(self._cartella())

        if self.build_ele.UsaDimensione.value:
            larghezza, altezza = self.build_ele.Dimensione.value
            riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(
                str(vista), pixelWidth=larghezza, pixelHeight=altezza)
        else:
            riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(vista))

        if not riuscita or not vista.exists():
            AllplanUtil.ShowMessageBox(
                "Allplan non ha salvato l'immagine della finestra.\n"
                "Cosa fare: clicca una volta dentro la finestra 3D che vuoi catturare, "
                "poi premi di nuovo Cattura.", AllplanUtil.MB_OK)
            return

        camera_file = ponte.scrivi_camera(vista, self._camera())
        self.ultima_vista = vista
        self.build_ele.UltimaVista.value = str(vista)
        AllplanUtil.ShowMessageBox(
            f"Vista salvata in\n{vista}\n\nCamera salvata in\n{camera_file}", AllplanUtil.MB_OK)

    def _camera(self) -> dict:
        """Da dove guarda la finestra. Ogni voce che fallisce resta scritta come errore."""
        proiezione = self.coord_input.GetViewWorldProjection()
        letture = {
            "occhio": lambda: _punto(proiezione.GetEyePoint()),
            "punto_guardato": lambda: _punto(proiezione.GetViewPoint()),
            "prospettiva_centrale": proiezione.IsCentralProjection,
            "angolo_vista": lambda: str(proiezione.GetViewAngle()),
            "dimensione_vista": lambda: str(proiezione.GetViewSize()),
        }
        camera = {}
        for nome, leggi in letture.items():
            try:
                camera[nome] = leggi()
            except Exception as errore:  # pylint: disable=broad-exception-caught
                camera[nome] = f"errore: {type(errore).__name__}: {errore}"
        return camera

    def _motore(self, a_secco: bool) -> None:
        percorso = (self.build_ele.UltimaVista.value or "").strip()
        if not percorso or not Path(percorso).exists():
            AllplanUtil.ShowMessageBox(
                "Non c'e' ancora una vista da usare.\nCosa fare: premi prima Cattura vista.",
                AllplanUtil.MB_OK)
            return

        argomenti = ponte.argomenti_motore(
            Path(percorso), self.build_ele.Preset.value, self.build_ele.Testo.value, a_secco)
        _codice, testo = ponte.esegui_motore(argomenti)
        AllplanUtil.ShowMessageBox(testo or "Il motore non ha detto niente.", AllplanUtil.MB_OK)


def _punto(punto) -> list[float]:
    return [round(punto.X, 3), round(punto.Y, 3), round(punto.Z, 3)]
