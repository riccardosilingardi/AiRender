"""AIRENDER sonda color map: la color map fatta dai materiali di Allplan, sulla copia di un progetto.

Non e' il prodotto: e' una prova usa e getta. Ogni pulsante fa un passo e
scrive cosa ha visto in `Usr\\...\\AIRENDER\\sonda-colormap\\`. La logica che
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

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

import sonda_colormap as sonda  # noqa: E402  pylint: disable=wrong-import-position
import sonda_materiali as base  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_NORMALE = 3101
EVENTO_LEGGI = 3102
EVENTO_COLORA = 3103
EVENTO_COLORMAP = 3104
EVENTO_RIMETTI = 3105
EVENTO_CARTELLA = 3106

print("Load AirenderSondaColormap.py")

_VERSIONE_ALLPLAN = {"valore": "sconosciuta"}


def check_allplan_version(_build_ele: BuildingElement, version: str) -> bool:
    _VERSIONE_ALLPLAN["valore"] = str(version)
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderSondaColormap(build_ele, script_object_data)


class AirenderSondaColormap(BaseScriptObject):
    """Sei pulsanti: vista normale, leggi, colora, color map, rimetti, cartella."""

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

    def on_control_event(self, event_id: int) -> None:
        azioni = {
            EVENTO_NORMALE: lambda: self._salva(sonda.VISTA_NORMALE, "1 vista normale"),
            EVENTO_LEGGI: self._leggi_materiali,
            EVENTO_COLORA: self._colora,
            EVENTO_COLORMAP: lambda: self._salva(sonda.VISTA_COLORMAP, "4 color map"),
            EVENTO_RIMETTI: self._rimetti,
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

    def _leggi_materiali(self) -> None:
        documento = self._documento()
        if documento is None:
            _messaggio(self.registro.scrivi("2 leggi", "documento non trovato"))
            return
        self.diario.ricomincia()
        self.diario.prima("GetSelectedElements(documento)")
        ok, selezionati = base.prova(lambda: AllplanBaseEle.ElementsSelectService.GetSelectedElements(documento))
        elenco = list(selezionati) if ok else []
        if not elenco:
            self.diario.prima("fine: niente selezionato")
            _messaggio("Non c'e' niente di selezionato.\n\nCosa fare: seleziona gli elementi che "
                       "si vedono nella vista (in un progetto piccolo anche tutti), poi premi di nuovo.")
            return
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
        if mancanti:
            self.registro.scrivi("2 senza materiale", " · ".join(mancanti))
        tralasciati = len(elenco) - len(scelti)
        _messaggio(f"{len(elenco)} selezionati, letti {len(self.letti)} non 2D "
                   f"({tralasciati} 2D o oltre il limite). Materiali trovati: {len(self.gruppi)}.\n"
                   f"Senza materiale: {', '.join(mancanti) or 'nessuno'}.\n\n"
                   "Se il progetto aperto e' una COPIA, spunta la casella e premi «Colora per materiale».")

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

    def _colora(self) -> None:
        if not self._e_una_copia():
            _messaggio("Fermato: la casella «Ho aperto una COPIA del progetto» non e' spuntata.\n\n"
                       "Questa prova cambia le superfici degli elementi. Apri una copia del "
                       "progetto, spunta la casella, poi premi di nuovo.")
            return
        if not self.gruppi:
            _messaggio("Prima premi «Leggi i materiali» con gli elementi selezionati.")
            return
        documento = self._documento()
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
        _messaggio(f"Colorati {colorati} materiali su {len(self.gruppi)}.\n\n"
                   "Guarda la finestra 3D: ogni materiale dovrebbe avere un colore pieno. "
                   "Senza muovere la camera, premi «Salva color map».")

    def _crea_superficie(self, documento, cartella: Path, nome: str, colore: str) -> str:
        definizione = AllplanBaseEle.SurfaceDefinition()
        rosso, verde, blu = sonda.rgb(colore)
        definizione.DiffuseColor = _argb(rosso, verde, blu)
        return AllplanBaseEle.DocumentResourceService.CreateSurface(
            documento, str(cartella), nome, definizione)

    def _lista(self, indici: list[int]):
        return AllplanEleAdapter.BaseElementAdapterList([self.elementi[i] for i in indici])

    # ------------------------------------------------------------ passi 1 e 4

    def _salva(self, nome: str, passo: str) -> None:
        percorso = self.cartella / nome
        self.cartella.mkdir(parents=True, exist_ok=True)
        riuscita = AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(percorso))
        if not riuscita or not percorso.exists():
            riga = self.registro.scrivi(passo, f"SaveWindowToImageFile ha restituito {riuscita}, file assente")
            _messaggio(f"{riga}\n\nClicca una volta dentro la finestra 3D, poi premi di nuovo.")
            return
        ok, analisi = base.prova(lambda: base.colori(percorso))
        riga = self.registro.scrivi(passo, base.descrivi_colori(analisi) if ok else f"colori non letti: {analisi}")
        if nome == sonda.VISTA_NORMALE:
            _messaggio(f"{riga}\n\nOra seleziona gli elementi della vista e premi «Leggi i materiali».")
            return
        ok, vicini = base.prova(lambda: sonda.vicini_alla_tavolozza(percorso, [g.colore for g in self.gruppi]))
        if ok:
            self.registro.scrivi("4 tavolozza", sonda.descrivi_vicini(vicini))
        self.registro.scrivi_file(sonda.FILE_LEGENDA, sonda.legenda(self.gruppi, vicini if ok else None))
        _messaggio(f"{riga}\n\n{sonda.descrivi_vicini(vicini) if ok else vicini}\n\n"
                   "Ora premi «Rimetti le superfici», poi «Apri la cartella» e mandami tutta la cartella.")

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
        _messaggio(f"Rimesse le superfici di {rimessi} materiali.{avviso}\n\n"
                   "Guarda se la vista e' tornata com'era e scrivimelo.")

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
