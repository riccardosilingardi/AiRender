"""Allplan 2027: legge il materiale degli elementi 3D del progetto aperto. Solo lettura.

AIRENDER non cambia mai i materiali di Allplan (Riccardo, 2026-11-02): qui
ci sono solo chiamate che leggono. Le stesse della sonda dell'elenco, provata
sul 4253 il 2026-11-02 (2732 elementi, nessun blocco). Prima di ogni chiamata
si scrive una riga nel diario: se Allplan si chiude, dice dove.

Il raggruppamento, i .surf e le anteprime stanno in `materiali_allplan.py`,
senza Allplan, con i suoi test.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import NemAll_Python_AllplanSettings as AllplanSettings
import NemAll_Python_BaseElements as AllplanBaseEle

import materiali_allplan


def _prova(chiamata):
    try:
        return True, chiamata()
    except Exception as errore:  # pylint: disable=broad-exception-caught
        return False, f"errore: {type(errore).__name__}: {errore}"


def radici() -> list[Path]:
    """Progetto, Usr, Std: dove cercare i .surf. Le funzioni che mancano si saltano."""
    trovate: list[Path] = []
    for nome in ("GetCurPrjPath", "GetUsrPath", "GetStdPath"):
        funzione = getattr(AllplanSettings.AllplanPaths, nome, None)
        ok, valore = _prova(funzione) if funzione is not None else (False, None)
        if ok and valore and Path(str(valore)) not in trovate:
            trovate.append(Path(str(valore)))
    return trovate


def leggi_e_scrivi(documento, vista: Path) -> str:
    """Legge i materiali e li scrive accanto alla vista. Restituisce una riga per la palette."""
    adesso = datetime.now().isoformat(timespec="seconds")
    diario = materiali_allplan.Diario(Path(vista).parent)
    diario.ricomincia()
    try:
        letti = _leggi(documento, diario)
        percorso = materiali_allplan.scrivi_per_vista(vista, letti, radici(), adesso)
    except Exception as errore:  # pylint: disable=broad-exception-caught
        materiali_allplan.scrivi_errore(vista, f"{type(errore).__name__}: {errore}", adesso)
        diario.prima("fine: errore")
        return f"Materiali non letti: {errore}"
    diario.prima("fine")
    import core.materiali as modulo_materiali  # pylint: disable=import-outside-toplevel
    elenco = modulo_materiali.leggi_elenco(vista) or {"materiali": []}
    return f"{len(elenco['materiali'])} materiali letti ({percorso.name})"


def _leggi(documento, diario: materiali_allplan.Diario) -> list[dict]:
    diario.prima("SelectAllElements")
    ok, tutti = _prova(lambda: AllplanBaseEle.ElementsSelectService.SelectAllElements(documento))
    elenco = list(tutti) if ok and tutti is not None else []
    diario.prima(f"GetDisplayName su {len(elenco)} elementi")
    nomi = []
    for adattatore in elenco:
        ok, nome = _prova(adattatore.GetDisplayName)
        nomi.append(str(nome) if ok else "")
    letti = []
    for indice in materiali_allplan.scegli_elementi(nomi):
        letti.append(_leggi_uno(documento, elenco[indice], nomi[indice], indice, diario))
    return letti


def _leggi_uno(documento, adattatore, nome: str, indice: int, diario: materiali_allplan.Diario) -> dict:
    diario.prima(f"elemento {indice} ({nome}): GetAttributes")
    dati = {"GetDisplayName": nome, "attributi": _attributi(documento, adattatore), "superficie": {}}
    if not any(str(chiave).startswith("335") for chiave in dati["attributi"]):
        diario.prima(f"elemento {indice} ({nome}): GetElement")
        ok, elemento = _prova(lambda: AllplanBaseEle.GetElement(adattatore))
        if ok and elemento is not None and hasattr(elemento, "GetTextureDefinition"):
            diario.prima(f"elemento {indice} ({nome}): GetTextureDefinition")
            ok, texture = _prova(elemento.GetTextureDefinition)
            if ok and texture is not None:
                ok, percorso = _prova(lambda: texture.SurfacePath)
                if ok:
                    dati["superficie"]["SurfacePath"] = str(percorso)
    return dati


def _attributi(documento, adattatore) -> dict:
    stato = None
    for nome in ("eAttibuteReadState", "eAttributeReadState"):  # Allplan scrive la prima, con l'errore
        enum = getattr(AllplanBaseEle, nome, None)
        stato = getattr(enum, "ReadAll", None) if enum is not None else None
        if stato is not None:
            break
    ok, attributi = _prova(lambda: adattatore.GetAttributes(stato) if stato is not None
                           else adattatore.GetAttributes())
    if not ok:
        return {}
    letti: dict = {}
    for voce in list(attributi):
        ok, coppia = _prova(lambda v=voce: (v[0], v[1]))
        if not ok or str(coppia[0]) not in ("335", "508"):
            continue
        letti[str(coppia[0])] = str(coppia[1])
    return letti
