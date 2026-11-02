"""AIRENDER sonda elenco materiali: legge i materiali del modello, non cambia niente.

Non e' il prodotto: e' una prova usa e getta. Un pulsante «Leggi i materiali»
salva la vista, legge il materiale di ogni elemento 3D, trova il file .surf di
ogni materiale e ne fa un campione (texture o colore). Tutto finisce in
`Usr\\...\\AIRENDER\\sonda-elenco\\`.

SOLO LETTURA. Decisione di Riccardo (2026-11-02): AIRENDER non cambia mai i
materiali di Allplan. Qui non c'e' nessuna chiamata che modifica il modello o
le superfici: `SurfaceDefinition.LoadSurfaceData` riempie un oggetto Python, il
.surf si legge come file e se ne salva una copia nella cartella della sonda.

Niente selezione a mano: con la palette aperta Allplan non lascia selezionare
(provato da Riccardo il 2026-11-02). La logica che non ha bisogno di Allplan
sta in `sonda_elenco.py` e si prova con pytest.
"""

from __future__ import annotations

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

try:
    # Esc chiude la palette e fa tornare la Library, come nelle altre palette (#40).
    from ScriptObjectInteractors.OnCancelFunctionResult import OnCancelFunctionResult
except ImportError:  # un framework senza questo modulo: resta il comportamento di Allplan
    OnCancelFunctionResult = None

_CARTELLA = Path(__file__).resolve().parent
if str(_CARTELLA) not in sys.path:
    sys.path.insert(0, str(_CARTELLA))

import sonda_elenco as sonda  # noqa: E402  pylint: disable=wrong-import-position
import sonda_materiali as base  # noqa: E402  pylint: disable=wrong-import-position

EVENTO_LEGGI = 3201
EVENTO_CARTELLA = 3202

print("Load AirenderSondaElenco.py")

_VERSIONE_ALLPLAN = {"valore": "sconosciuta"}


def check_allplan_version(_build_ele: BuildingElement, version: str) -> bool:
    _VERSIONE_ALLPLAN["valore"] = str(version)
    return True


def create_script_object(build_ele: BuildingElement,
                         script_object_data: BaseScriptObjectData) -> BaseScriptObject:
    return AirenderSondaElenco(build_ele, script_object_data)


class AirenderSondaElenco(BaseScriptObject):
    """Due pulsanti: leggi i materiali, apri la cartella."""

    def __init__(self, build_ele: BuildingElement, script_object_data: BaseScriptObjectData):
        super().__init__(script_object_data)
        self.build_ele = build_ele
        self.dati = script_object_data
        usr = Path(AllplanSettings.AllplanPaths.GetUsrPath())
        self.cartella = usr / "AIRENDER" / "sonda-elenco"
        self.registro = base.Registro(self.cartella)
        self.diario = base.Diario(self.cartella)
        precedente = self.diario.ultima()
        if precedente and not precedente.startswith("fine"):
            self.registro.scrivi("avvio", f"l'ultima volta Allplan si e' fermato su: {precedente}")
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
        azioni = {EVENTO_LEGGI: self._leggi_tutto, EVENTO_CARTELLA: self._apri_cartella}
        azione = azioni.get(event_id)
        if azione is None:
            return
        try:
            azione()
        except Exception as errore:  # pylint: disable=broad-exception-caught
            self.registro.scrivi(f"errore evento {event_id}", traceback.format_exc())
            _messaggio(f"Errore nella sonda: {type(errore).__name__}: {errore}\n\n"
                       f"E' scritto in {self.registro.percorso}")

    # ------------------------------------------------------------ documento e cartelle

    def _documento(self):
        for leggi in (lambda: self.document, lambda: self.dati.document,
                      lambda: self.coord_input.GetInputViewDocument()):
            ok, documento = base.prova(leggi)
            if ok and documento is not None:
                return documento
        return None

    def _radici(self) -> list[Path]:
        """Le cartelle di Allplan in cui cercare i .surf: progetto, Usr, Std, Etc."""
        radici: list[Path] = []
        percorsi = AllplanSettings.AllplanPaths
        for nome in ("GetCurPrjPath", "GetPrjPath", "GetUsrPath", "GetStdPath", "GetEtcPath"):
            funzione = getattr(percorsi, nome, None)
            ok, valore = base.prova(funzione) if funzione is not None else (False, "assente")
            self.registro.scrivi("cartelle", f"{nome}: {valore if ok else 'non letto: ' + str(valore)}")
            if ok and valore and Path(str(valore)) not in radici:
                radici.append(Path(str(valore)))
        return radici

    # ------------------------------------------------------------ lettura

    def _leggi_tutto(self) -> None:
        documento = self._documento()
        if documento is None:
            _messaggio(self.registro.scrivi("leggi", "documento non trovato"))
            return
        self.diario.ricomincia()
        self._salva_vista()
        letti = self._leggi_elementi(documento)
        if letti is None:
            return
        materiali = sonda.elenca(letti)
        radici = self._radici()
        for posto, materiale in enumerate(materiali):
            self._campione(posto, materiale, radici)
        self.diario.prima("fine: lettura completa")
        self.registro.scrivi_file(sonda.FILE_MATERIALI, sonda.json_materiali(materiali))
        mancanti = sonda.senza_materiale(letti)
        self.registro.scrivi("riassunto", f"{len(letti)} elementi 3D letti · {sonda.riassunto(materiali)} · "
                                          f"senza materiale: {' · '.join(mancanti) or 'nessuno'}")
        elenco = "\n".join(f"  {m.materiale} ({m.elementi}){'' if m.campione else ' - senza campione'}"
                           for m in materiali[:20])
        altri = f"\n  ... e altri {len(materiali) - 20}" if len(materiali) > 20 else ""
        _messaggio(f"Letti {len(letti)} elementi 3D. Il modello non e' stato cambiato.\n\n"
                   f"{sonda.riassunto(materiali)}:\n{elenco}{altri}\n\n"
                   "Premi «Apri la cartella» e mandami la cartella sonda-elenco.")

    def _salva_vista(self) -> None:
        percorso = self.cartella / sonda.VISTA
        self.cartella.mkdir(parents=True, exist_ok=True)
        self.diario.prima("SaveWindowToImageFile")
        ok, riuscita = base.prova(lambda: AllplanBaseEle.DrawingService.SaveWindowToImageFile(str(percorso)))
        esito = "salvata" if ok and riuscita and percorso.exists() else f"non salvata: {base.corto(riuscita)}"
        self.registro.scrivi("vista", esito)

    def _leggi_elementi(self, documento) -> list[dict] | None:
        self.diario.prima("SelectAllElements(documento)")
        ok, tutti = base.prova(lambda: AllplanBaseEle.ElementsSelectService.SelectAllElements(documento))
        elenco = list(tutti) if ok else []
        if not elenco:
            self.diario.prima("fine: nessun elemento")
            _messaggio(self.registro.scrivi("leggi", f"nessun elemento letto: {base.corto(tutti)}"))
            return None
        self.diario.prima(f"GetDisplayName su {len(elenco)} elementi")
        nomi = []
        for adattatore in elenco:
            ok, nome = base.prova(adattatore.GetDisplayName)
            nomi.append(str(nome) if ok else "")
        scelti = base.scegli_elementi(nomi, per_tipo=sonda.MASSIMO_ELEMENTI, massimo=sonda.MASSIMO_ELEMENTI)
        letti = [self._leggi(documento, elenco[indice], indice) for indice in scelti]
        self.registro.scrivi_file(sonda.FILE_ELEMENTI, base.json_elementi(letti))
        self.registro.scrivi("leggi", f"{len(elenco)} elementi nel modello, {len(letti)} 3D letti"
                                      f"{' (limite raggiunto)' if len(letti) >= sonda.MASSIMO_ELEMENTI else ''}")
        return letti

    def _leggi(self, documento, adattatore, indice: int) -> dict:
        dati: dict = {}
        self.diario.prima(f"elemento {indice}: GetDisplayName")
        ok, nome = base.prova(adattatore.GetDisplayName)
        dati["GetDisplayName"] = base.corto(nome)
        self.diario.prima(f"elemento {indice} ({dati['GetDisplayName']}): GetAttributes")
        dati["attributi"] = self._attributi(documento, adattatore)
        superficie: dict = {}
        if not any(str(chiave).startswith("335") for chiave in dati["attributi"]):
            # GetElement solo se l'attributo non basta: e' la chiamata piu' pesante.
            self.diario.prima(f"elemento {indice} ({dati['GetDisplayName']}): GetElement")
            ok, elemento = base.prova(lambda: AllplanBaseEle.GetElement(adattatore))
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

    # ------------------------------------------------------------ campioni

    def _campione(self, posto: int, materiale: sonda.Materiale, radici: list[Path]) -> None:
        """Trova il .surf, ne legge il colore, ne copia il file, fa il campione. Non scrive niente in Allplan."""
        candidati = sonda.candidati_surf(materiale.valore, radici)
        trovato = next((p for p in candidati if p.is_file()), None)
        if trovato is None:
            materiale.note.append(f"surf non trovato fra {len(candidati)} percorsi")
        else:
            materiale.file_surf = str(trovato)
            ok, dati = base.prova(trovato.read_bytes)
            if ok:
                copia = self.cartella / sonda.CARTELLA_SURF / sonda.nome_file(posto, materiale.materiale, ".surf")
                copia.parent.mkdir(parents=True, exist_ok=True)
                copia.write_bytes(dati)
                testo = sonda.testo_surf(dati)
                self._texture(posto, materiale, testo, trovato.parent, radici)
            else:
                materiale.note.append(f"surf non letto: {dati}")
        self._colore_surf(materiale, [materiale.valore] + ([str(trovato)] if trovato else []))
        if not materiale.campione and materiale.colore_surf:
            nome = sonda.nome_file(posto, materiale.materiale, ".png")
            ok, esito = base.prova(lambda: sonda.campione_da_colore(
                materiale.colore_surf, self.cartella / sonda.CARTELLA_CAMPIONI / nome))
            if ok:
                materiale.campione = f"{sonda.CARTELLA_CAMPIONI}/{nome}"
            else:
                materiale.note.append(f"campione dal colore non fatto: {esito}")
        self.registro.scrivi("campione", f"{materiale.materiale} ({materiale.da}, {materiale.elementi}): "
                                         f"surf {materiale.file_surf or '-'} · colore {materiale.colore_surf or '-'} · "
                                         f"texture {materiale.texture or '-'} · {'; '.join(materiale.note)}")

    def _texture(self, posto: int, materiale: sonda.Materiale, testo: str, cartella_surf: Path,
                 radici: list[Path]) -> None:
        nomi = sonda.texture_nel_surf(testo)
        if not nomi:
            materiale.note.append("nessuna texture nominata nel surf")
            return
        for nome in nomi:
            sorgente = next((p for p in sonda.candidati_texture(nome, cartella_surf, radici) if p.is_file()), None)
            if sorgente is None:
                continue
            destinazione = self.cartella / sonda.CARTELLA_CAMPIONI / sonda.nome_file(posto, materiale.materiale, ".png")
            ok, esito = base.prova(lambda s=sorgente: sonda.campione_da_texture(s, destinazione))
            if ok:
                materiale.texture = str(sorgente)
                materiale.campione = f"{sonda.CARTELLA_CAMPIONI}/{destinazione.name}"
                return
            materiale.note.append(f"texture {sorgente.name} non aperta: {esito}")
        materiale.note.append(f"texture nominate ma non trovate: {', '.join(nomi[:3])}")

    def _colore_surf(self, materiale: sonda.Materiale, percorsi: list[str]) -> None:
        """LoadSurfaceData riempie un SurfaceDefinition in memoria: e' una lettura."""
        for percorso in percorsi:
            self.diario.prima(f"LoadSurfaceData {percorso}")
            definizione = AllplanBaseEle.SurfaceDefinition()
            ok, esito = base.prova(lambda p=percorso: definizione.LoadSurfaceData(p))
            if not ok:
                materiale.note.append(f"LoadSurfaceData({percorso}): {esito}")
                continue
            ok, colore = base.prova(lambda: definizione.DiffuseColor)
            rgb = _rgb(colore) if ok else None
            if rgb is not None:
                materiale.colore_surf = sonda.esadecimale(*rgb)
                return
            materiale.note.append(f"DiffuseColor da {percorso}: {base.corto(colore)}")

    def _apri_cartella(self) -> None:
        self.cartella.mkdir(parents=True, exist_ok=True)
        os.startfile(str(self.cartella))  # pylint: disable=no-member  (solo Windows, come Allplan)


def _rgb(colore) -> tuple[int, int, int] | None:
    """Rosso, verde, blu da un ARGB di Allplan: i nomi dei campi non sono verificati, si provano."""
    for nomi in (("Red", "Green", "Blue"), ("R", "G", "B"), ("red", "green", "blue")):
        valori = [getattr(colore, nome, None) for nome in nomi]
        if all(isinstance(v, int) for v in valori):
            return tuple(valori)  # type: ignore[return-value]
    return None


def _messaggio(testo: str) -> None:
    AllplanUtil.ShowMessageBox(testo, AllplanUtil.MB_OK)
