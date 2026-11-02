"""AIRENDER sonda color map: la color map fatta dai materiali di Allplan, sulla copia di un progetto.

Non e' il prodotto: e' una prova usa e getta. Due pulsanti: «Colora» (salva la
vista normale, legge tutti gli elementi 3D, colora per materiale) e «Salva e
rimetti» (salva la color map, rimette le superfici). Tutto finisce in
`Usr\\...\\AIRENDER\\sonda-colormap\\`.

Niente selezione a mano: con la palette aperta Allplan non lascia selezionare
(provato da Riccardo il 2026-11-02). La sonda prende tutti gli elementi. La logica che
non ha bisogno di Allplan sta in `sonda_colormap.py` e si prova con pytest.

QUESTA SONDA CAMBIA IL MODELLO: assegna superfici nuove agli elementi
selezionati. Per questo parte solo con la casella «Ho aperto una COPIA»
spuntata, scrive come rimettere tutto prima di cambiare, e ha un pulsante che
rimette le superfici di prima. Non modifica mai un file .surf esistente.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle
import NemAll_Python_IFW_ElementAdapter as AllplanEleAdapter
import NemAll_Python_Utility as AllplanUtil

from BaseScriptObject import BaseScriptObject, BaseScriptObjectData
from BuildingElement import BuildingElement
from CreateElementResult import CreateElementResult

try:
    # Esc chiude la palette e fa tornare la Library, come nelle altre palette (#40).
    from ScriptObjectInteractors.OnCancelFunctionResult import OnCancelFunctionResult
except ImportError:  # un framework senza questo modulo: resta il comportamento di Allplan
    OnCancelFunctionResult = None

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

import sonda_colormap as sonda  # noqa: E402  pylint: disable=wrong-import-position
import sonda_materiali as base  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_COLORA = 3101
EVENTO_SALVA_E_RIMETTI = 3102
EVENTO_CARTELLA = 3103

print("Load AirenderSondaColormap.py")

_VERSIONE_ALLPLAN = {"valore": "sconosciuta"}


def check_allplan_version(_build_ele: BuildingElement, version: str) -> bool:
    _VERSIONE_ALLPLAN["valore"] = str(version)
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderSondaColormap(build_ele, script_object_data)


class AirenderSondaColormap(BaseScriptObject):
    """Tre pulsanti: colora, salva e rimetti, apri la cartella."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.dati = script_object_data
        usr = Path(AllplanSettings.AllplanPaths.GetUsrPath())
        self.cartella = usr / "AIRENDER" / "sonda-colormap"
        self.registro = base.Registro(self.cartella)
        self.diario = base.Diario(self.cartella)
        precedente = self.diario.ultima()
        if precedente and not precedente.startswith("fine"):
            self.registro.scrivi("avvio", f"l'ultima volta Allplan si e' fermato su: {precedente}")
        self.elementi: list = []  # gli adattatori letti, nello stesso ordine di self.letti
        self.letti: list[dict] = []
        self.gruppi: list[sonda.Gruppo] = []
        self.registro.scrivi(
            "avvio", f"Allplan {_VERSIONE_ALLPLAN['valore']} · Python {sys.version.split()[0]} · "
                     f"cartella {self.cartella}")

    def execute(self) -> CreateElementResult:
        return CreateElementResult()

    def on_cancel_function(self):
        """Esc: chiude la palette e torna alla Library."""
        if OnCancelFunctionResult is None:
            return super().on_cancel_function()
        return OnCancelFunctionResult.CANCEL_INPUT

    def on_control_event(self, event_id: int) -> None:
        azioni = {
            EVENTO_COLORA: self._colora_tutto,
            EVENTO_SALVA_E_RIMETTI: self._salva_e_rimetti,
            EVENTO_CARTELLA: self._apri_cartella,
        }
        azione = azioni.get(event_id)
        if azione is None:
            return
        try:
            azione()
        except Exception as errore:  # pylint: disable=broad-exception-caught
            self.registro.scrivi(f"errore evento {event_id}", traceback.format_exc())
            _messaggio(f"Errore nella sonda: {type(errore).__name__}: {errore}\n\n"
                       f"E' scritto in {self.registro.percorso}")

    # ------------------------------------------------------------ documento

    def _documento(self):
        for leggi in (lambda: self.document, lambda: self.dati.document,
                      lambda: self.coord_input.GetInputViewDocument()):
            ok, documento = base.prova(leggi)
            if ok and documento is not None:
                return documento
        return None

    def _e_una_copia(self) -> bool:
        ok, valore = base.prova(lambda: bool(self.build_ele.Copia.value))
        return ok and valore

    # ------------------------------------------------------------ passo 2

    def _colora_tutto(self) -> None:
        """Vista normale, lettura di tutti gli elementi 3D, una superficie a tinta unita per materiale."""
        if not self._e_una_copia():
            _messaggio("Fermato: la casella «Ho aperto una COPIA» non e' spuntata.\n\n"
                       "Questa prova cambia le superfici degli elementi. Apri una COPIA del "
                       "progetto, spunta la casella, poi premi di nuovo «Colora».")
            return
        documento = self._documento()
        if documento is None:
            _messaggio(self.registro.scrivi("colora", "documento non trovato"))
            return
        if not self._salva(sonda.VISTA_NORMALE, "1 vista normale"):
            return
        if not self._leggi_materiali(documento):
            return
        self._colora(documento)

    def _leggi_materiali(self, documento) -> bool:
        self.diario.ricomincia()
        self.diario.prima("SelectAllElements(documento)")
        ok, tutti = base.prova(lambda: AllplanBaseEle.ElementsSelectService.SelectAllElements(documento))
        elenco = list(tutti) if ok else []
        if not elenco:
            self.diario.prima("fine: nessun elemento")
            _messaggio(self.registro.scrivi("2 leggi", f"nessun elemento letto: {base.corto(tutti)}"))
            return False
        self.diario.prima(f"GetDisplayName su {len(elenco)} elementi")
        nomi = []
        for adattatore in elenco:
            ok, nome = base.prova(adattatore.GetDisplayName)
            nomi.append(str(nome) if ok else "")
        scelti = base.scegli_elementi(nomi, per_tipo=sonda.MASSIMO_ELEMENTI, massimo=sonda.MASSIMO_ELEMENTI)
        self.elementi, self.letti = [], []
        for indice in scelti:
            self.elementi.append(elenco[indice])
            self.letti.append(self._leggi(documento, elenco[indice], indice))
        self.diario.prima("fine: lettura completa")
        self.gruppi = sonda.raggruppa(self.letti)
        self.registro.scrivi_file(sonda.FILE_MATERIALI, sonda.json_gruppi(self.gruppi))
        self.registro.scrivi_file("elementi-letti.json", base.json_elementi(self.letti))
        for gruppo in self.gruppi:
            self.registro.scrivi("2 materiale", f"{gruppo.colore or 'senza colore'} {gruppo.materiale} "
                                                f"({gruppo.da}, {len(gruppo.indici)} elementi)")
        mancanti = sonda.senza_materiale(self.letti)
        self.registro.scrivi("2 leggi", f"{len(elenco)} elementi, {len(self.letti)} 3D letti, "
                                        f"{len(self.gruppi)} materiali; senza materiale: "
                                        f"{' · '.join(mancanti) or 'nessuno'}")
        if not self.gruppi:
            _messaggio(f"Letti {len(self.letti)} elementi 3D, ma nessuno ha un materiale leggibile.\n\n"
                       "Premi «Apri la cartella» e mandami la cartella.")
            return False
        return True

    def _leggi(self, documento, adattatore, indice: int) -> dict:
        dati: dict = {}
        self.diario.prima(f"elemento {indice}: GetDisplayName")
        ok, nome = base.prova(adattatore.GetDisplayName)
        dati["GetDisplayName"] = base.corto(nome)
        self.diario.prima(f"elemento {indice} ({dati['GetDisplayName']}): GetAttributes")
        dati["attributi"] = self._attributi(documento, adattatore)
        self.diario.prima(f"elemento {indice} ({dati['GetDisplayName']}): GetElement")
        ok, elemento = base.prova(lambda: AllplanBaseEle.GetElement(adattatore))
        superficie: dict = {}
        if ok and elemento is not None and hasattr(elemento, "GetTextureDefinition"):
            self.diario.prima(f"elemento {indice} ({dati['GetDisplayName']}): GetTextureDefinition")
            ok, texture = base.prova(elemento.GetTextureDefinition)
            if ok and texture is not None:
                ok, percorso = base.prova(lambda: texture.SurfacePath)
                superficie["SurfacePath"] = base.corto(percorso)
        dati["superficie"] = superficie
        return dati

    def _attributi(self, documento, adattatore) -> dict:
        stato = None
        for nome in ("eAttibuteReadState", "eAttributeReadState"):  # Allplan scrive la prima, con l'errore
            enum = getattr(AllplanBaseEle, nome, None)
            stato = getattr(enum, "ReadAll", None) if enum is not None else None
            if stato is not None:
                break
        ok, attributi = base.prova(lambda: adattatore.GetAttributes(stato) if stato is not None
                                   else adattatore.GetAttributes())
        if not ok:
            return {"errore": attributi}
        letti: dict = {}
        for voce in list(attributi):
            ok, coppia = base.prova(lambda v=voce: (v[0], v[1]))
            if not ok:
                continue
            identificativo, valore = coppia
            if str(identificativo) not in ("335", "508"):
                continue  # qui servono solo i due attributi di materiale
            ok, nome = base.prova(
                lambda i=identificativo: AllplanBaseEle.AttributeService.GetAttributeName(documento, i))
            letti[f"{identificativo} {nome if ok else ''}".strip()] = base.corto(valore)
        return letti

    # ------------------------------------------------------------ passo 3

    def _colora(self, documento) -> None:
        # Prima di cambiare qualcosa: come rimetterlo.
        self.registro.scrivi_file(sonda.FILE_RIPRISTINO, sonda.json_gruppi(self.gruppi))
        superfici = self.cartella / "superfici"
        superfici.mkdir(parents=True, exist_ok=True)
        self.diario.ricomincia()
        colorati = 0
        for posto, gruppo in enumerate(self.gruppi):
            if not gruppo.colore:
                self.registro.scrivi("3 colora", f"{gruppo.materiale}: niente colore, tavolozza finita")
                continue
            nome = sonda.nome_superficie(posto)
            self.diario.prima(f"CreateSurface {nome} {gruppo.colore} per {gruppo.materiale}")
            ok, percorso = base.prova(lambda n=nome, c=gruppo.colore: self._crea_superficie(documento, superfici, n, c))
            if not ok:
                self.registro.scrivi("3 colora", f"{gruppo.materiale}: CreateSurface non riuscita: {percorso}")
                continue
            gruppo.superficie_nuova = str(percorso)
            self.diario.prima(f"ModifySurface {percorso} su {len(gruppo.indici)} elementi ({gruppo.materiale})")
            ok, esito = base.prova(lambda p=percorso, g=gruppo: AllplanBaseEle.ElementsPropertyService.ModifySurface(
                str(p), self._lista(g.indici)))
            riuscita = ok and esito is not None
            colorati += 1 if riuscita else 0
            self.registro.scrivi("3 colora", f"{gruppo.colore} {gruppo.materiale}: superficie {percorso}, "
                                             f"ModifySurface {'ok' if riuscita else 'non riuscita'}: {base.corto(esito)}")
        self.diario.prima("fine: colora")
        self.registro.scrivi_file(sonda.FILE_RIPRISTINO, sonda.json_gruppi(self.gruppi))
        elenco = "\n".join(f"  {g.colore}  {g.materiale}" for g in self.gruppi if g.colore)
        _messaggio(f"Colorati {colorati} materiali su {len(self.gruppi)}:\n{elenco}\n\n"
                   "Guarda la finestra 3D: ogni materiale dovrebbe avere un colore pieno.\n"
                   "Senza muovere la camera, premi «Salva e rimetti».")

    def _crea_superficie(self, documento, cartella: Path, nome: str, colore: str) -> str:
        definizione = AllplanBaseEle.SurfaceDefinition()
        rosso, verde, blu = sonda.rgb(colore)
        definizione.DiffuseColor = _argb(rosso, verde, blu)
        return AllplanBaseEle.DocumentResourceService.CreateSurface(
            documento, str(cartella), nome, definizione)

    def _lista(self, indici: list[int]):
        return AllplanEleAdapter.BaseElementAdapterList([self.elementi[i] for i in indici])

    # ------------------------------------------------------------ passi 1 e 4

    def _salva(self, nome: str, passo: str) -> bool:
        percorso = self.cartella / nome
        self.cartella.mkdir(parents=True, exist_ok=True)
        riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(percorso))
        if not riuscita or not percorso.exists():
            riga = self.registro.scrivi(passo, f"SaveWindowToImageFile ha restituito {riuscita}, file assente")
            _messaggio(f"{riga}\n\nClicca una volta dentro la finestra 3D, poi premi di nuovo.")
            return False
        ok, analisi = base.prova(lambda: base.colori(percorso))
        self.registro.scrivi(passo, base.descrivi_colori(analisi) if ok else f"colori non letti: {analisi}")
        return True

    def _salva_e_rimetti(self) -> None:
        if not any(g.superficie_nuova for g in self.gruppi):
            _messaggio("Prima premi «Colora».")
            return
        if not self._salva(sonda.VISTA_COLORMAP, "4 color map"):
            return
        percorso = self.cartella / sonda.VISTA_COLORMAP
        ok, vicini = base.prova(lambda: sonda.vicini_alla_tavolozza(percorso, [g.colore for g in self.gruppi]))
        if ok:
            self.registro.scrivi("4 tavolozza", sonda.descrivi_vicini(vicini))
        self.registro.scrivi_file(sonda.FILE_LEGENDA, sonda.legenda(self.gruppi, vicini if ok else None))
        self._rimetti()

    # ------------------------------------------------------------ passo 5

    def _rimetti(self) -> None:
        if not self.gruppi:
            ok, testo = base.prova(lambda: (self.cartella / sonda.FILE_RIPRISTINO).read_text(encoding="utf-8"))
            if not ok:
                _messaggio("Non ho niente da rimettere: la sonda non ha colorato niente in questa sessione.")
                return
            self.gruppi = sonda.gruppi_da_json(testo)
        if not self.elementi:
            _messaggio("Gli elementi colorati non sono piu' in memoria (la palette e' stata chiusa).\n\n"
                       "Cosa fare: chiudi la COPIA senza salvare. L'originale non e' mai stato toccato.")
            return
        self.diario.ricomincia()
        rimessi, non_rimessi = 0, []
        for gruppo in self.gruppi:
            if not gruppo.superficie_nuova:
                continue
            if not gruppo.superficie_originale:
                non_rimessi.append(gruppo.materiale)
                continue
            self.diario.prima(f"ModifySurface {gruppo.superficie_originale} su {len(gruppo.indici)} elementi")
            ok, esito = base.prova(lambda g=gruppo: AllplanBaseEle.ElementsPropertyService.ModifySurface(
                g.superficie_originale, self._lista(g.indici)))
            if ok and esito is not None:
                rimessi += 1
            else:
                non_rimessi.append(gruppo.materiale)
            self.registro.scrivi("5 rimetti", f"{gruppo.materiale} ({gruppo.da}) <- {gruppo.superficie_originale}: "
                                              f"{'ok' if ok else 'non riuscita'} {base.corto(esito)}")
        self.diario.prima("fine: rimetti")
        avviso = (f"\n\nNon rimessi: {', '.join(non_rimessi)}. Chiudi la COPIA senza salvare."
                  if non_rimessi else "")
        _messaggio(f"Color map salvata. Rimesse le superfici di {rimessi} materiali.{avviso}\n\n"
                   "Guarda se la vista e' tornata com'era, poi premi «Apri la cartella» "
                   "e mandami la cartella sonda-colormap.")

    def _apri_cartella(self) -> None:
        self.cartella.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.cartella))  # pylint: disable=no-member  (solo Windows, come Allplan)


def _argb(rosso: int, verde: int, blu: int):
    """ARGB sta in BaseElements o in BasisElements secondo la versione: si prova dove c'e'."""
    import importlib  # pylint: disable=import-outside-toplevel

    for modulo in ("NemAll_Python_BaseElements", "NemAll_Python_BasisElements"):
        classe = getattr(importlib.import_module(modulo), "ARGB", None)
        if classe is not None:
            return classe(rosso, verde, blu, 255)
    raise RuntimeError("classe ARGB non trovata in BaseElements ne' in BasisElements")


def _messaggio(testo: str) -> None:
    AllplanUtil.ShowMessageBox(testo, AllplanUtil.MB_OK)
