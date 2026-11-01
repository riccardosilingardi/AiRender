"""AIRENDER sonda materiali: tre domande ad Allplan 2027 prima della mappa dei materiali.

Non e' il prodotto: e' una prova usa e getta (prompt 15, fase A). Ogni pulsante
risponde a una domanda e scrive cosa ha visto in
`Usr\\...\\AIRENDER\\sonda-materiali\\`. La logica che non ha bisogno di
Allplan sta in `sonda_materiali.py` e si prova con pytest.

La sonda non cambia il modello e non cambia la vista: la color map la mette
Riccardo a mano, poi preme il pulsante. L'unica chiamata che tocca qualcosa e'
la selezione di tutti gli elementi, necessaria per leggerli.
"""

from __future__ import annotations

import importlib
import os
import sys
import traceback
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

import sonda_materiali as sonda  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_API = 3001
EVENTO_ELEMENTI = 3002
EVENTO_NORMALE = 3003
EVENTO_COLORMAP = 3004
EVENTO_CARTELLA = 3005

# I moduli dove cercare superfici, texture e colori. Quelli che non si
# importano si scrivono come tali: anche questo e' una risposta.
MODULI = (
    "NemAll_Python_BaseElements",
    "NemAll_Python_BasisElements",
    "NemAll_Python_IFW_ElementAdapter",
    "NemAll_Python_IFW_Input",
    "NemAll_Python_ArchElements",
    "NemAll_Python_AllplanSettings",
)

print("Load AirenderSondaMateriali.py")

_VERSIONE_ALLPLAN = {"valore": "sconosciuta"}


def check_allplan_version(_build_ele: BuildingElement, version: str) -> bool:
    _VERSIONE_ALLPLAN["valore"] = str(version)
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderSondaMateriali(build_ele, script_object_data)


class AirenderSondaMateriali(BaseScriptObject):
    """Cinque pulsanti: API, elementi, vista normale, color map, cartella."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.dati = script_object_data
        usr = Path(AllplanSettings.AllplanPaths.GetUsrPath())
        self.cartella = usr / "AIRENDER" / "sonda-materiali"
        self.registro = sonda.Registro(self.cartella)
        self.diario = sonda.Diario(self.cartella)
        precedente = self.diario.ultima()
        if precedente and not precedente.startswith("fine"):
            # L'ultima volta Allplan si e' chiuso a meta' lettura: questa e' la chiamata che l'ha fatto.
            self.registro.scrivi("2 elementi", f"la lettura precedente si e' fermata su: {precedente}")
        self.analisi: dict[str, dict] = {}
        self.registro.scrivi(
            "avvio", f"Allplan {_VERSIONE_ALLPLAN['valore']} · Python {sys.version.split()[0]} · "
                     f"cartella {self.cartella}")

    def execute(self) -> CreateElementResult:
        return CreateElementResult()

    def on_control_event(self, event_id: int) -> None:
        azioni = {
            EVENTO_API: self._api,
            EVENTO_ELEMENTI: self._elementi,
            EVENTO_NORMALE: lambda: self._salva(sonda.VISTA_NORMALE, "3 vista normale"),
            EVENTO_COLORMAP: lambda: self._salva(sonda.VISTA_COLORMAP, "4 color map"),
            EVENTO_CARTELLA: self._apri_cartella,
        }
        azione = azioni.get(event_id)
        if azione is None:
            return
        try:
            azione()
        except Exception as errore:  # pylint: disable=broad-exception-caught
            # Una sonda che si zittisce non serve: l'errore si scrive com'e'.
            self.registro.scrivi(f"errore evento {event_id}", traceback.format_exc())
            _messaggio(f"Errore nella sonda: {type(errore).__name__}: {errore}\n\n"
                       f"E' scritto in {self.registro.percorso}")

    # ---------------------------------------------------------- domanda 1

    def _api(self) -> None:
        moduli = {}
        for nome in MODULI:
            ok, modulo = sonda.prova(lambda n=nome: importlib.import_module(n))
            moduli[nome] = modulo if ok else None
        percorso = self.registro.scrivi_file(sonda.FILE_API, sonda.elenca_api(moduli))
        importati = sum(1 for m in moduli.values() if m is not None)
        riga = self.registro.scrivi("1 api", f"{importati} moduli su {len(MODULI)} letti, elenco in {percorso.name}")
        _messaggio(f"{riga}\n\nOra premi «Leggi gli elementi».")

    # ---------------------------------------------------------- domanda 2

    def _documento(self):
        for leggi in (lambda: self.document, lambda: self.dati.document,
                      lambda: self.coord_input.GetInputViewDocument()):
            ok, documento = sonda.prova(leggi)
            if ok and documento is not None:
                return documento
        return None

    def _elementi(self) -> None:
        documento = self._documento()
        if documento is None:
            riga = self.registro.scrivi("2 elementi", "documento non trovato: nessuna lettura possibile")
            _messaggio(riga)
            return
        self.diario.ricomincia()
        # Prima gli elementi selezionati da Riccardo; se non ce ne sono, tutti.
        self.diario.prima("GetSelectedElements(documento)")
        ok, elementi = sonda.prova(lambda: AllplanBaseEle.ElementsSelectService.GetSelectedElements(documento))
        da = "selezionati"
        if not ok or not list(elementi):
            self.diario.prima("SelectAllElements(documento)")
            ok, elementi = sonda.prova(lambda: AllplanBaseEle.ElementsSelectService.SelectAllElements(documento))
            da = "tutti"
        if not ok:
            self.diario.prima("fine: nessun elemento letto")
            riga = self.registro.scrivi("2 elementi", f"lettura degli elementi ({da}): {elementi}")
            _messaggio(riga)
            return
        elenco = list(elementi)
        # Il nome di ogni elemento (GetDisplayName ha retto 30 volte su 30 il
        # 2026-11-01): serve a contare i tipi e a scegliere quelli 3D.
        self.diario.prima(f"GetDisplayName su tutti i {len(elenco)} elementi")
        nomi = []
        for adattatore in elenco:
            ok, nome = sonda.prova(adattatore.GetDisplayName)
            nomi.append(str(nome) if ok else "")
        tipi = sonda.conta_tipi(nomi)
        self.registro.scrivi("2 tipi", " · ".join(f"{n or '?'} {q}" for n, q in tipi[:40]))
        scelti = sonda.scegli_elementi(nomi)
        letti = []
        for indice in scelti:
            letti.append(self._leggi(documento, elenco[indice], indice))
            # Scritto a ogni elemento: se Allplan si chiude, quelli gia' letti restano.
            self.registro.scrivi_file(sonda.FILE_ELEMENTI, sonda.json_elementi(letti))
        self.diario.prima("fine: lettura completa")
        self.registro.scrivi("2 elementi", f"{len(elenco)} elementi ({da}), {len(tipi)} tipi, "
                                           f"descritti {len(letti)} non 2D in {sonda.FILE_ELEMENTI}")
        trovati = sonda.valori_di_materiale(letti)
        if trovati:
            for campo, valori in trovati.items():
                self.registro.scrivi("2 materiali", f"{campo}: {len(valori)} valori diversi · {valori[:12]}")
            esito = f"Trovati {len(trovati)} campi che parlano di materiali o superfici."
        else:
            self.registro.scrivi("2 materiali", "nessun campo da materiale letto con successo")
            esito = "Nessun campo da materiale letto: va cercata un'altra strada (elenco in api.txt)."
        _messaggio(f"{len(elenco)} elementi ({da}), letti {len(letti)}. {esito}\n\n"
                   "Se dopo resta selezionato tutto, clicca nel vuoto. "
                   "Poi metti la finestra 3D com'e' di solito e premi «Salva vista normale».")

    def _leggi(self, documento, adattatore, indice: int) -> dict:
        """Poche letture con nome, ognuna annotata nel diario prima di farla.

        Niente chiamate alla cieca ai metodi Get*: il 2026-11-01 hanno fatto
        chiudere Allplan su un progetto vero.
        """
        dati: dict = {}
        for nome in ("GetDisplayName", "GetElementAdapterType"):
            self.diario.prima(f"elemento {indice}: {nome}")
            ok, valore = sonda.prova(getattr(adattatore, nome))
            dati[nome] = sonda.corto(valore) if ok else valore
        self.diario.prima(f"elemento {indice} ({dati.get('GetDisplayName', '')}): GetCommonProperties")
        ok, comuni = sonda.prova(adattatore.GetCommonProperties)
        dati["proprieta_comuni"] = sonda.proprieta(comuni) if ok else comuni
        self.diario.prima(f"elemento {indice} ({dati.get('GetDisplayName', '')}): GetAttributes")
        dati["attributi"] = self._attributi(documento, adattatore)
        dati["superficie"] = self._superficie(adattatore, indice, dati.get("GetDisplayName", ""))
        return dati

    def _superficie(self, adattatore, indice: int, nome: str) -> dict:
        """Il materiale Allplan dell'elemento: TextureDefinition.SurfacePath (api.txt, ModelElement3D).

        GetElement e' l'ultima lettura di ogni elemento, annotata nel diario:
        se e' lei a far chiudere Allplan, lo si vede e gli elementi gia' letti
        sono salvati.
        """
        self.diario.prima(f"elemento {indice} ({nome}): GetElement")
        ok, elemento = sonda.prova(lambda: AllplanBaseEle.GetElement(adattatore))
        if not ok or elemento is None:
            return {"GetElement": sonda.corto(elemento)}
        risultato: dict = {"tipo_python": type(elemento).__name__}
        if hasattr(elemento, "GetTextureDefinition"):
            self.diario.prima(f"elemento {indice} ({nome}): GetTextureDefinition")
            ok, texture = sonda.prova(elemento.GetTextureDefinition)
            if ok and texture is not None:
                ok, percorso = sonda.prova(lambda: texture.SurfacePath)
                risultato["SurfacePath"] = sonda.corto(percorso)
            else:
                risultato["GetTextureDefinition"] = sonda.corto(texture)
        # Muri, solai, tetti: le proprieta' dell'elemento architettonico, solo valori.
        if hasattr(elemento, "Properties"):
            self.diario.prima(f"elemento {indice} ({nome}): Properties")
            ok, proprieta = sonda.prova(lambda: elemento.Properties)
            risultato["Properties"] = sonda.proprieta(proprieta) if ok else proprieta
        return risultato

    def _attributi(self, documento, adattatore) -> dict:
        """Gli attributi per nome. La superficie potrebbe stare qui, come attributo."""
        stato = None
        for nome in ("eAttibuteReadState", "eAttributeReadState"):  # Allplan scrive la prima, con l'errore
            enum = getattr(AllplanBaseEle, nome, None)
            stato = getattr(enum, "ReadAll", None) if enum is not None else None
            if stato is not None:
                break
        ok, attributi = sonda.prova(lambda: adattatore.GetAttributes(stato) if stato is not None
                                    else adattatore.GetAttributes())
        if not ok:
            return {"errore": attributi}
        letti: dict = {}
        for voce in list(attributi):
            ok, coppia = sonda.prova(lambda v=voce: (v[0], v[1]))
            if not ok:
                letti[sonda.corto(voce)] = ""
                continue
            identificativo, valore = coppia
            ok, nome = sonda.prova(
                lambda i=identificativo: AllplanBaseEle.AttributeService.GetAttributeName(documento, i))
            letti[f"{identificativo} {nome if ok else ''}".strip()] = sonda.corto(valore)
        return letti

    # ---------------------------------------------------------- domanda 3

    def _salva(self, nome: str, passo: str) -> None:
        percorso = self.cartella / nome
        self.cartella.mkdir(parents=True, exist_ok=True)
        riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(percorso))
        if not riuscita or not percorso.exists():
            riga = self.registro.scrivi(passo, f"SaveWindowToImageFile ha restituito {riuscita}, file assente")
            _messaggio(f"{riga}\n\nClicca una volta dentro la finestra 3D, poi premi di nuovo.")
            return
        ok, analisi = sonda.prova(lambda: sonda.colori(percorso))
        if not ok:
            riga = self.registro.scrivi(passo, f"salvata, ma i colori non si leggono: {analisi}")
            _messaggio(riga)
            return
        self.analisi[nome] = analisi
        riga = self.registro.scrivi(passo, sonda.descrivi_colori(analisi))
        if nome == sonda.VISTA_NORMALE:
            _messaggio(f"{riga}\n\nOra, SENZA muovere la camera, metti la finestra in color map "
                       "(un colore per materiale) e premi «Salva color map».")
            return
        confronto = self.registro.scrivi(
            "4 confronto", sonda.confronta_viste(self.analisi.get(sonda.VISTA_NORMALE), analisi))
        _messaggio(f"{riga}\n\n{confronto}\n\nFinito. Rimetti la finestra com'era, poi premi "
                   "«Apri la cartella» e mandami tutta la cartella sonda-materiali.")

    def _apri_cartella(self) -> None:
        self.cartella.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.cartella))  # pylint: disable=no-member  (solo Windows, come Allplan)


def _messaggio(testo: str) -> None:
    AllplanUtil.ShowMessageBox(testo, AllplanUtil.MB_OK)
