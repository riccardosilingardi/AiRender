"""La sonda della color map da Allplan: le parti che si provano senza Allplan.

Decisione di Riccardo (2026-11-01): la color map si fa dai materiali di
Allplan, non dalla segmentazione. La sonda prova la strada sulla COPIA di un
progetto:

1. legge il materiale di ogni elemento selezionato (SurfacePath, poi gli
   attributi 335 Nome_aspetto e 508 Materiale, come la sonda 2);
2. crea una superficie NUOVA a tinta unita per ogni materiale
   (DocumentResourceService.CreateSurface) e la assegna ai suoi elementi
   (ElementsPropertyService.ModifySurface). Un file .surf esistente non si
   tocca mai: e' condiviso fra tutti i progetti;
3. salva la finestra: e' la color map;
4. rimette le superfici di prima, dove le conosce.

Qui non c'e' nessun import di Allplan. L'adattatore
(`AirenderSondaColormap.py`) fa le chiamate e passa a queste funzioni quello
che riceve. La sonda non decide niente: scrive quello che ha visto.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from core.colormap import NON_ASSEGNATO, TAVOLOZZA, nome_materiale

FILE_MATERIALI = "materiali.json"
FILE_RIPRISTINO = "ripristino.json"
FILE_LEGENDA = "legenda.json"
VISTA_NORMALE = "vista-normale.png"
VISTA_COLORMAP = "vista-colormap.png"
SENZA_MATERIALE = "(senza materiale)"
PREFISSO_SUPERFICIE = "airender_colormap"

# Quanti elementi selezionati leggere al massimo. La sonda 2 ne ha letti 30
# senza problemi; la sonda 1 ha fatto chiudere Allplan su 150 elementi di un
# progetto vero con chiamate alla cieca. Qui le chiamate hanno un nome e il
# diario e' scritto prima di ognuna, ma si resta prudenti.
MASSIMO_ELEMENTI = 300  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Distanza (somma delle differenze R, G, B) entro cui un pixel conta come
# «colore della tavolozza»: luce e bordi sfumati lo spostano un po'.
VICINO_ALLA_TAVOLOZZA = 60  # numero-non-configurabile: soglia a occhio della sonda usa e getta


@dataclass
class Gruppo:
    """Un materiale di Allplan e gli elementi che lo portano."""

    materiale: str
    colore: str
    da: str  # dove si e' letto: SurfacePath, 335, 508
    indici: list[int] = field(default_factory=list)
    superficie_originale: str = ""  # il valore letto, per rimetterlo
    superficie_nuova: str = ""  # il percorso che restituisce CreateSurface


def materiale_di(letto: dict[str, Any]) -> tuple[str, str, str]:
    """(nome leggibile, valore originale, da dove) del materiale di un elemento letto.

    Prima la superficie 3D (SurfacePath), poi l'attributo 335 Nome_aspetto,
    poi il 508 Materiale: e' l'ordine in cui la sonda 2 li ha trovati piu' precisi.
    """
    superficie = (letto.get("superficie") or {}).get("SurfacePath", "")
    nome = nome_materiale(superficie)
    if nome and not str(superficie).startswith("errore"):
        return nome, str(superficie).strip("'\""), "SurfacePath"
    attributi = letto.get("attributi") or {}
    for numero in ("335", "508"):
        for chiave, valore in attributi.items():
            if str(chiave).split(" ", 1)[0] == numero:
                nome = nome_materiale(valore)
                if nome:
                    return nome, str(valore).strip("'\""), numero
    return SENZA_MATERIALE, "", ""


def raggruppa(letti: list[dict[str, Any]]) -> list[Gruppo]:
    """Un gruppo per materiale, il piu' frequente per primo, un colore della tavolozza ciascuno.

    Gli elementi senza materiale restano fuori: non si colorano e si contano.
    Oltre i colori della tavolozza i materiali restano senza colore, e lo si dice.
    """
    per_nome: dict[str, Gruppo] = {}
    for indice, letto in enumerate(letti):
        nome, originale, da = materiale_di(letto)
        if nome == SENZA_MATERIALE:
            continue
        gruppo = per_nome.setdefault(nome, Gruppo(materiale=nome, colore="", da=da,
                                                  superficie_originale=originale))
        gruppo.indici.append(indice)
    ordinati = sorted(per_nome.values(), key=lambda g: (-len(g.indici), g.materiale))
    for posto, gruppo in enumerate(ordinati):
        gruppo.colore = TAVOLOZZA[posto] if posto < len(TAVOLOZZA) else ""
    return ordinati


def senza_materiale(letti: list[dict[str, Any]]) -> list[str]:
    """I tipi di elemento rimasti senza materiale, col loro numero."""
    conta = Counter(str(letto.get("GetDisplayName", "?")) for letto in letti
                    if materiale_di(letto)[0] == SENZA_MATERIALE)
    return [f"{nome} {quanti}" for nome, quanti in conta.most_common()]


def rgb(colore: str) -> tuple[int, int, int]:
    return tuple(int(colore[i:i + 2], 16) for i in (1, 3, 5))  # numero-non-configurabile: posizioni delle cifre in '#rrggbb'


def nome_superficie(posto: int) -> str:
    return f"{PREFISSO_SUPERFICIE}_{posto + 1:02d}"


def json_gruppi(gruppi: list[Gruppo]) -> str:
    return json.dumps([asdict(g) for g in gruppi], ensure_ascii=False, indent=1)


def gruppi_da_json(testo: str) -> list[Gruppo]:
    return [Gruppo(**voce) for voce in json.loads(testo)]


def legenda(gruppi: list[Gruppo], analisi: dict[str, Any] | None) -> str:
    """Colore -> materiale Allplan, con la parte di immagine che il colore copre davvero."""
    parti = {}
    if analisi:
        parti = {voce["colore"]: voce["parte"] for voce in analisi.get("vicini", [])}
    zone = [{"colore": g.colore, "materiale_allplan": g.materiale, "da": g.da,
             "elementi": len(g.indici), "parte_immagine": parti.get(g.colore)}
            for g in gruppi if g.colore]
    return json.dumps({"zone": zone, "non_assegnato": NON_ASSEGNATO}, ensure_ascii=False, indent=1)


def vicini_alla_tavolozza(percorso: Path, colori: list[str],
                          distanza: int = VICINO_ALLA_TAVOLOZZA) -> dict[str, Any]:
    """Quanta parte dell'immagine e' vicina a ciascun colore chiesto.

    Luce, ombre e bordi sfumati di Allplan spostano i colori: se la parte
    vicina e' alta, la color map si pulisce assegnando ogni pixel al colore
    piu' vicino; se e' bassa, Allplan ombreggia troppo e serve un'altra vista.
    """
    from PIL import Image  # pylint: disable=import-outside-toplevel

    voluti = [(colore, rgb(colore)) for colore in colori if colore]
    with Image.open(percorso) as immagine:
        quadro = immagine.convert("RGB")
        totale = quadro.size[0] * quadro.size[1]
        conteggio = quadro.getcolors(maxcolors=totale)
    vicini = Counter()
    for quanti, pixel in conteggio:
        migliore = min(voluti, key=lambda voce: _distanza(pixel, voce[1]), default=None)
        if migliore is not None and _distanza(pixel, migliore[1]) <= distanza:
            vicini[migliore[0]] += quanti
    coperta = sum(vicini.values())
    return {
        "parte_vicina": round(coperta / totale, 4) if totale else 0.0,
        "vicini": [{"colore": colore, "parte": round(vicini[colore] / totale, 4)} for colore, _ in voluti],
    }


def descrivi_vicini(analisi: dict[str, Any]) -> str:
    dettaglio = ", ".join(f"{v['colore']} {v['parte']:.1%}" for v in analisi["vicini"])
    return f"{analisi['parte_vicina']:.1%} dell'immagine vicino ai colori chiesti · {dettaglio}"


def _distanza(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum(abs(x - y) for x, y in zip(a, b))
