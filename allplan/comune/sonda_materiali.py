"""La sonda dei materiali: le parti che si provano senza Allplan.

Prompt 15, fase A. Prima di costruire la mappa dei materiali (PRD sezione 8)
bisogna sapere, sul PC vero e con Allplan 2027:

1. quali funzioni dell'API parlano di superfici, texture, materiali e colori;
2. se da un elemento del modello si legge il materiale assegnato (la
   superficie, la texture) e con quale nome;
3. se la finestra salvata in «color map» da' un colore pieno per materiale,
   alla stessa grandezza della vista normale.

Qui non c'e' nessun import di Allplan. L'adattatore (`AirenderSondaMateriali.py`)
fa le chiamate e passa a queste funzioni quello che riceve. La sonda non
decide niente: scrive quello che ha visto in un file che Riccardo rimanda.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

FILE_RISULTATI = "risultati-materiali.txt"
FILE_ELEMENTI = "elementi.json"
FILE_API = "api.txt"
FILE_DIARIO = "diario-lettura.txt"
VISTA_NORMALE = "vista-normale.png"
VISTA_COLORMAP = "vista-colormap.png"

# Le parole che fanno guardare una funzione o un metodo. Inglese e tedesco,
# perche' l'API di Allplan usa tutte e due.
PAROLE = re.compile(
    r"surf|textur|materi|colou?r|farb|oberfl|shad|render|bitmap|select|visib|attrib|propert",
    re.IGNORECASE)
# Solo i metodi con questi nomi si chiamano: leggono e basta.
LETTURA = re.compile(r"(Get|Is|Has)[A-Z]")
# Letture che restituiscono geometria o il documento intero: pesanti e senza materiali dentro.
SALTA = re.compile(r"Geometr|Document|Parent|Child|Polyhedron|Vertic|Faces|Edges", re.IGNORECASE)

# Quanti elementi descrivere al massimo: abbastanza per un modello di prova,
# non tanti da bloccare Allplan per minuti su un progetto vero.
# Il 2026-11-01 la lettura di tutto un progetto vero ha fatto chiudere Allplan:
# si leggono pochi elementi, scegliendoli fra quelli selezionati se ce ne sono.
MASSIMO_ELEMENTI = 30  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Quanti colori elencare per immagine: una vista con piu' materiali di cosi' e' gia' una risposta.
COLORI_ELENCATI = 24  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Oltre questa lunghezza un valore letto si tronca: serve vederlo, non archiviarlo.
LUNGHEZZA_VALORE = 300  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Quanto si scende negli oggetti annidati (proprieta' di proprieta').
PROFONDITA = 2  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto


class Registro:
    """Il file di testo, una riga per fatto, e il JSON degli elementi accanto."""

    def __init__(self, cartella: Path, adesso: Callable[[], datetime] = datetime.now):
        self.cartella = cartella
        self.percorso = cartella / FILE_RISULTATI
        self._adesso = adesso

    def scrivi(self, passo: str, testo: str) -> str:
        riga = f"[{self._adesso():%Y-%m-%d %H:%M:%S}] {passo} · {testo}"
        self.cartella.mkdir(parents=True, exist_ok=True)
        with self.percorso.open("a", encoding="utf-8") as file:
            file.write(riga + "\n")
        return riga

    def scrivi_file(self, nome: str, contenuto: str) -> Path:
        self.cartella.mkdir(parents=True, exist_ok=True)
        percorso = self.cartella / nome
        percorso.write_text(contenuto, encoding="utf-8")
        return percorso


# Gli elementi 2D: non hanno materiale. La prima lettura (2026-11-01) ha preso
# i primi 30 di 13570 ed erano quasi tutti linee e punti.
NOMI_2D = re.compile(
    r"^(linea|punto|testo|cerchio|arco|polilinea|polilinea 2d|spline|curva|retino|campitura|"
    r"riempimento|quota|quotatura|simbolo|smart symbol|etichetta|freccia|testo variabile|"
    r"line|point|text|circle|polyline|hatch(ing)?|pattern|fill(ing)?|dimension( line)?|label)$",
    re.IGNORECASE)
# Quanti elementi leggere per ogni tipo, per vedere tipi diversi e non 30 muri uguali.
PER_TIPO = 3  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto


def conta_tipi(nomi: list[str]) -> list[tuple[str, int]]:
    """I tipi di elemento del modello col loro numero, il piu' frequente per primo."""
    return Counter(nomi).most_common()


def scegli_elementi(nomi: list[str], per_tipo: int = PER_TIPO, massimo: int | None = None) -> list[int]:
    """Gli indici da leggere: pochi per ogni tipo che non e' 2D, fino a `massimo`."""
    massimo = MASSIMO_ELEMENTI if massimo is None else massimo
    presi: Counter = Counter()
    scelti: list[int] = []
    for indice, nome in enumerate(nomi):
        pulito = nome.strip().strip("'\"")
        if not pulito or NOMI_2D.match(pulito) or presi[pulito] >= per_tipo:
            continue
        presi[pulito] += 1
        scelti.append(indice)
        if len(scelti) >= massimo:
            break
    return scelti


class Diario:
    """Una riga scritta su disco PRIMA di ogni chiamata ad Allplan.

    Se Allplan si chiude di colpo (un errore dentro Allplan, che Python non
    puo' fermare), l'ultima riga del diario dice quale chiamata, su quale
    elemento. Ogni riga si forza su disco subito.
    """

    def __init__(self, cartella: Path):
        self.percorso = cartella / FILE_DIARIO
        self.cartella = cartella

    def ricomincia(self) -> None:
        self.cartella.mkdir(parents=True, exist_ok=True)
        self.percorso.write_text("", encoding="utf-8")

    def prima(self, testo: str) -> None:
        self.cartella.mkdir(parents=True, exist_ok=True)
        with self.percorso.open("a", encoding="utf-8") as file:
            file.write(testo + "\n")
            file.flush()
            os.fsync(file.fileno())

    def ultima(self) -> str:
        try:
            righe = self.percorso.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        return righe[-1] if righe else ""


def proprieta(oggetto: Any) -> dict[str, str]:
    """Solo i valori gia' pronti di un oggetto (le proprieta'), senza chiamare nessun metodo.

    E' la lettura prudente: chiamare alla cieca i metodi Get* degli elementi
    di Allplan ha fatto chiudere Allplan su un progetto vero.
    """
    letti: dict[str, str] = {}
    for nome in dir(oggetto):
        if nome.startswith("_") or SALTA.search(nome):
            continue
        ok, valore = prova(lambda n=nome: getattr(oggetto, n))
        if ok and callable(valore):
            continue
        letti[nome] = corto(valore) if ok else valore
    return letti


def corto(valore: Any) -> str:
    """Il valore come Allplan lo restituisce, tagliato se e' lungo."""
    try:
        testo = repr(valore)
    except Exception as errore:  # pylint: disable=broad-exception-caught
        testo = f"<repr fallito: {type(errore).__name__}>"
    if len(testo) > LUNGHEZZA_VALORE:
        testo = testo[:LUNGHEZZA_VALORE] + "…"
    return testo


def prova(chiamata: Callable[[], Any]) -> tuple[bool, Any]:
    """(riuscita, valore o errore come testo). Una sonda non si ferma a un errore."""
    try:
        return True, chiamata()
    except Exception as errore:  # pylint: disable=broad-exception-caught
        return False, f"errore: {type(errore).__name__}: {errore}"


def nomi_interessanti(oggetto: Any) -> list[str]:
    return sorted(n for n in dir(oggetto) if not n.startswith("_") and PAROLE.search(n))


def elenca_api(moduli: dict[str, Any]) -> str:
    """Per ogni modulo: i nomi che parlano di superfici, colori, selezione; con la prima riga del docstring.

    Per le classi si elencano anche i loro membri interessanti: e' li' che
    di solito sta un `GetSurface` o un `TextureID`.
    """
    righe: list[str] = []
    for nome_modulo, modulo in moduli.items():
        if modulo is None:
            righe.append(f"## {nome_modulo}: non importato")
            continue
        righe.append(f"## {nome_modulo}")
        for nome in sorted(n for n in dir(modulo) if not n.startswith("_")):
            oggetto = getattr(modulo, nome, None)
            membri = nomi_interessanti(oggetto) if isinstance(oggetto, type) else []
            if not PAROLE.search(nome) and not membri:
                continue
            righe.append(f"- {nome}: {_prima_riga(oggetto)}")
            for membro in membri:
                righe.append(f"    · {membro}: {_prima_riga(getattr(oggetto, membro, None))}")
    return "\n".join(righe) + "\n"


def _prima_riga(oggetto: Any) -> str:
    documento = (getattr(oggetto, "__doc__", None) or "").strip()
    return documento.splitlines()[0][:LUNGHEZZA_VALORE] if documento else "(senza descrizione)"


def descrivi(oggetto: Any, profondita: int = PROFONDITA) -> dict[str, str | dict]:
    """Chiama ogni metodo senza argomenti dal nome interessante e ogni proprieta', e scrive cosa torna.

    Gli oggetti che tornano (per esempio le proprieta' di un muro) si
    descrivono a loro volta, fino a `profondita`. Un metodo che vuole argomenti
    fallisce e si scrive l'errore: dice comunque che il metodo esiste.
    """
    risultato: dict[str, str | dict] = {}
    for nome in nomi_interessanti(oggetto) + _getter(oggetto):
        if nome in risultato or SALTA.search(nome):
            continue
        ok, valore = prova(lambda n=nome: getattr(oggetto, n))
        if ok and callable(valore):
            if not LETTURA.match(nome):
                # Set*, Select*, Save*: chiamarli cambierebbe il modello o la vista.
                risultato[nome] = "metodo (non chiamato: non e' una lettura)"
                continue
            ok, valore = prova(valore)
        if ok and profondita > 0 and _e_composto(valore):
            risultato[nome] = {"valore": corto(valore), "dentro": descrivi(valore, profondita - 1)}
        else:
            risultato[nome] = valore if not ok else corto(valore)
    return risultato


def _getter(oggetto: Any) -> list[str]:
    """I Get* senza parole chiave: GetDisplayName, GetElementAdapterType e simili dicono che cos'e'."""
    return sorted(n for n in dir(oggetto) if LETTURA.match(n) and not PAROLE.search(n))


def _e_composto(valore: Any) -> bool:
    if valore is None or isinstance(valore, (str, bytes, int, float, bool, list, tuple, dict)):
        return False
    return bool(nomi_interessanti(valore) or _getter(valore))


def colori(percorso: Path, quanti: int = COLORI_ELENCATI) -> dict[str, Any]:
    """Grandezza, quanti colori diversi, e i piu' frequenti con la loro parte dell'immagine.

    In una color map vera ci si aspettano pochi colori che coprono quasi tutto
    (piu' quelli dei bordi, mescolati); in una vista normale, migliaia.
    """
    from PIL import Image  # pylint: disable=import-outside-toplevel

    with Image.open(percorso) as immagine:
        rgb = immagine.convert("RGB")
        larghezza, altezza = rgb.size
        # getcolors c'e' in ogni Pillow, anche in quello vecchio installato in Allplan.
        conteggio = Counter({colore: n for n, colore in rgb.getcolors(maxcolors=larghezza * altezza)})
    totale = larghezza * altezza
    frequenti = conteggio.most_common(quanti)
    coperta = sum(n for _colore, n in frequenti) / totale if totale else 0.0
    return {
        "file": str(percorso),
        "larghezza": larghezza,
        "altezza": altezza,
        "colori_diversi": len(conteggio),
        "parte_coperta_dai_primi": round(coperta, 4),
        "primi": [{"colore": "#%02x%02x%02x" % colore, "parte": round(n / totale, 4)} for colore, n in frequenti],
    }


def descrivi_colori(analisi: dict[str, Any]) -> str:
    primi = ", ".join(f"{c['colore']} {c['parte']:.1%}" for c in analisi["primi"][:8])
    return (f"{Path(analisi['file']).name}: {analisi['larghezza']}×{analisi['altezza']}, "
            f"{analisi['colori_diversi']} colori diversi, i primi {len(analisi['primi'])} "
            f"coprono {analisi['parte_coperta_dai_primi']:.1%} · {primi}")


def confronta_viste(normale: dict[str, Any] | None, colormap: dict[str, Any] | None) -> str:
    """Le due viste vanno sovrapposte pixel per pixel: devono avere la stessa grandezza."""
    if not normale or not colormap:
        return "manca una delle due viste: salva prima la vista normale, poi la color map"
    stessa = (normale["larghezza"], normale["altezza"]) == (colormap["larghezza"], colormap["altezza"])
    grandezza = "stessa grandezza" if stessa else "GRANDEZZE DIVERSE: non si sovrappongono"
    return (f"{grandezza}; colori diversi {normale['colori_diversi']} nella normale, "
            f"{colormap['colori_diversi']} nella color map")


def json_elementi(elementi: list[dict[str, Any]]) -> str:
    return json.dumps(elementi, ensure_ascii=False, indent=1, default=corto)


MATERIALE = re.compile(r"surf|textur|materi|oberfl", re.IGNORECASE)


def valori_di_materiale(elementi: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Ogni campo dal nome «da materiale» trovato negli elementi, con i valori diversi letti (riusciti).

    E' la risposta alla domanda 2 in una riga: se qui compaiono nomi di
    superfici o id di texture diversi da elemento a elemento, il materiale si
    legge dal modello.
    """
    trovati: dict[str, set[str]] = {}

    def visita(dati: Any, percorso: str) -> None:
        if isinstance(dati, dict):
            for chiave, valore in dati.items():
                dove = f"{percorso}.{chiave}" if percorso else str(chiave)
                testo = valore.get("valore") if isinstance(valore, dict) else valore
                if (MATERIALE.search(str(chiave)) and isinstance(testo, str)
                        and not testo.startswith(("errore:", "metodo ("))):
                    trovati.setdefault(dove, set()).add(testo)
                if isinstance(valore, (dict, list)):
                    visita(valore, dove)
        elif isinstance(dati, list):
            for voce in dati:
                visita(voce, percorso)

    for elemento in elementi:
        visita(elemento, "")
    return {chiave: sorted(valori) for chiave, valori in sorted(trovati.items())}
