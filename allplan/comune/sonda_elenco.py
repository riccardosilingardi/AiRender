"""La sonda dell'elenco dei materiali: le parti che si provano senza Allplan.

Decisione di Riccardo (2026-11-02): AIRENDER non cambia mai i materiali di
Allplan, nemmeno per un momento. Legge l'elenco dei materiali del modello; poi
e' l'utente che sceglie quali cambiare e, per quelli, scrive cosa diventano e
mette un'immagine di riferimento. Al modello vanno la vista e, per ogni
materiale scelto, la coppia «campione di Allplan -> riferimento».

La sonda prova la prima meta', solo in lettura:

1. legge il materiale di ogni elemento 3D (SurfacePath, poi gli attributi
   335 Nome_aspetto e 508 Materiale, come la sonda 2);
2. trova il file .surf di ogni materiale e ne fa un campione: la texture,
   se il .surf ne nomina una che si trova sul disco, altrimenti il colore.

Qui non c'e' nessun import di Allplan. L'adattatore
(`AirenderSondaElenco.py`) fa le chiamate e passa a queste funzioni quello che
riceve. La sonda non decide niente: scrive quello che ha visto.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any

from core.colormap import TAVOLOZZA, nome_materiale

FILE_MATERIALI = "materiali.json"
FILE_ELEMENTI = "elementi-letti.json"
VISTA = "vista.png"
CARTELLA_CAMPIONI = "campioni"
CARTELLA_SURF = "surf"
SENZA_MATERIALE = "(senza materiale)"

# Quanti elementi 3D leggere al massimo. Con la palette aperta Allplan non
# lascia selezionare (2026-11-02), quindi la sonda prende tutto il progetto e
# salta il 2D. Il diario e' scritto prima di ogni chiamata.
MASSIMO_ELEMENTI = 4000  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Quanti elementi leggere per ogni tipo: il 2026-11-02 sul 4253 i primi 2000
# erano per meta' «Sub-elemento facciata» (1040), tutti senza materiale, e il
# limite e' arrivato prima di leggere il resto. 2000 elementi in 8 secondi.
PER_TIPO = 150  # numero-non-configurabile: limite della sonda usa e getta, non del prodotto
# Per i tipi senza materiale si scrivono tutti gli attributi dei primi elementi:
# servono a capire dove facciate e macro tengono il loro materiale.
ATTRIBUTI_COMPLETI_PER_TIPO = 3  # numero-non-configurabile: limite della sonda usa e getta
# Valori dell'attributo 335 che non sono un materiale.
NON_MATERIALI = ("*varia*",)
# Lato del campione quadrato, in pixel: basta per riconoscere un materiale.
LATO_CAMPIONE = 256  # numero-non-configurabile: misura della sonda usa e getta
# Le sottocartelle in cui Allplan tiene le superfici, dentro Std, Usr e il progetto.
SOTTOCARTELLE_SURF = ("design", "")
ESTENSIONI_IMMAGINE = re.compile(r"[^\"'<>|\r\n\t=\x00]*?\.(?:jpe?g|png|bmp|tiff?|tga)", re.IGNORECASE)


@dataclass
class Materiale:
    """Un materiale di Allplan, quanti elementi lo portano, e cosa la sonda ne ha trovato."""

    materiale: str
    da: str  # dove si e' letto: SurfacePath, 335, 508
    valore: str  # il valore letto, tale e quale
    elementi: int = 0
    colore: str = ""  # il colore che AIRENDER gli associa, si potra' cambiare
    file_surf: str = ""
    colore_surf: str = ""  # il DiffuseColor letto dal .surf, se letto
    texture: str = ""
    campione: str = ""  # percorso relativo del PNG, vuoto se non fatto
    note: list[str] = field(default_factory=list)


def pulisci(valore: Any) -> str:
    """Il valore come Allplan lo ha dato: senza apici e senza le barre raddoppiate da repr().

    Il 2026-11-02 i valori sono arrivati come "'nemetschek\\\\_aspetti\\\\metallo.surf'"
    e "'A.03.SETTO IN C.A.\\\\'".
    """
    testo = str(valore or "").strip().strip("'\"")
    while "\\\\" in testo:
        testo = testo.replace("\\\\", "\\")
    return testo.rstrip("\\").strip()


def materiale_di(letto: dict[str, Any]) -> tuple[str, str, str]:
    """(nome leggibile, valore originale, da dove) del materiale di un elemento letto."""
    superficie = pulisci((letto.get("superficie") or {}).get("SurfacePath", ""))
    nome = nome_materiale(superficie)
    if nome and not str(superficie).startswith("errore"):
        return nome, superficie, "SurfacePath"
    attributi = letto.get("attributi") or {}
    for numero in ("335", "508"):
        for chiave, valore in attributi.items():
            if str(chiave).split(" ", 1)[0] == numero:
                pulito = pulisci(valore)
                nome = nome_materiale(pulito)
                if nome and pulito.lower() not in NON_MATERIALI:
                    return nome, pulito, numero
    return SENZA_MATERIALE, "", ""


def elenca(letti: list[dict[str, Any]]) -> list[Materiale]:
    """Un materiale per riga, il piu' frequente per primo, con un colore della tavolozza."""
    per_nome: dict[str, Materiale] = {}
    for letto in letti:
        nome, valore, da = materiale_di(letto)
        if nome == SENZA_MATERIALE:
            continue
        per_nome.setdefault(nome, Materiale(materiale=nome, da=da, valore=valore)).elementi += 1
    ordinati = sorted(per_nome.values(), key=lambda m: (-m.elementi, m.materiale))
    for posto, materiale in enumerate(ordinati):
        materiale.colore = TAVOLOZZA[posto] if posto < len(TAVOLOZZA) else ""
    return ordinati


def senza_materiale(letti: list[dict[str, Any]]) -> list[str]:
    """I tipi di elemento rimasti senza materiale, col loro numero."""
    conta = Counter(str(letto.get("GetDisplayName", "?")) for letto in letti
                    if materiale_di(letto)[0] == SENZA_MATERIALE)
    return [f"{nome} {quanti}" for nome, quanti in conta.most_common()]


def candidati_surf(valore: str, radici: list[Path]) -> list[Path]:
    """Dove puo' stare il .surf di un valore letto: assoluto, o relativo a Std, Usr, progetto."""
    parti = PureWindowsPath(valore.strip("'\"")).parts
    if not parti:
        return []
    nomi = [parti]
    if not parti[-1].lower().endswith(".surf"):
        nomi.append((*parti[:-1], parti[-1] + ".surf"))
    if PureWindowsPath(valore).is_absolute():
        return [Path(*p) for p in nomi]
    trovati: list[Path] = []
    for radice in radici:
        for sotto in SOTTOCARTELLE_SURF:
            base = radice / sotto if sotto else radice
            for nome in nomi:
                percorso = base.joinpath(*nome)
                if percorso not in trovati:
                    trovati.append(percorso)
    return trovati


def testo_surf(dati: bytes) -> str:
    """Il .surf come testo, qualunque sia la codifica: serve solo a cercarci nomi di file."""
    if dati.startswith((b"\xff\xfe", b"\xfe\xff")) or dati[1:200:2].count(b"\x00") > 50:
        return dati.decode("utf-16", errors="replace")
    return dati.decode("utf-8", errors="replace")


def texture_nel_surf(testo: str) -> list[str]:
    """I nomi di immagine che compaiono nel .surf, nell'ordine, senza doppioni."""
    visti: list[str] = []
    for trovato in ESTENSIONI_IMMAGINE.findall(testo):
        nome = trovato.strip()
        if nome and nome not in visti:
            visti.append(nome)
    return visti


def candidati_texture(nome: str, cartella_surf: Path, radici: list[Path]) -> list[Path]:
    """Dove puo' stare una texture nominata da un .surf."""
    parti = PureWindowsPath(nome).parts
    if not parti:
        return []
    if PureWindowsPath(nome).is_absolute():
        return [Path(*parti)]
    trovati = [cartella_surf.joinpath(*parti), cartella_surf / parti[-1]]
    for radice in radici:
        for sotto in SOTTOCARTELLE_SURF:
            base = radice / sotto if sotto else radice
            trovati.append(base.joinpath(*parti))
    return list(dict.fromkeys(trovati))


def campione_da_texture(sorgente: Path, destinazione: Path, lato: int = LATO_CAMPIONE) -> None:
    """Il quadrato centrale della texture, ridotto a `lato` pixel."""
    from PIL import Image  # pylint: disable=import-outside-toplevel

    with Image.open(sorgente) as immagine:
        rgb = immagine.convert("RGB")
    larghezza, altezza = rgb.size
    corto = min(larghezza, altezza)
    sinistra, alto = (larghezza - corto) // 2, (altezza - corto) // 2
    quadrato = rgb.crop((sinistra, alto, sinistra + corto, alto + corto)).resize((lato, lato))
    destinazione.parent.mkdir(parents=True, exist_ok=True)
    quadrato.save(destinazione)


def campione_da_colore(colore: str, destinazione: Path, lato: int = LATO_CAMPIONE) -> None:
    from PIL import Image  # pylint: disable=import-outside-toplevel

    destinazione.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (lato, lato), colore).save(destinazione)


def esadecimale(rosso: int, verde: int, blu: int) -> str:
    return "#%02x%02x%02x" % (rosso, verde, blu)


def nome_file(posto: int, materiale: str, estensione: str) -> str:
    """Un nome di file sicuro su Windows: numero e materiale."""
    pulito = re.sub(r"[^A-Za-z0-9_-]+", "_", materiale).strip("_")[:40] or "materiale"
    return f"{posto + 1:02d}-{pulito}{estensione}"


def json_materiali(materiali: list[Materiale]) -> str:
    return json.dumps([asdict(m) for m in materiali], ensure_ascii=False, indent=1)


def riassunto(materiali: list[Materiale]) -> str:
    con_campione = sum(1 for m in materiali if m.campione)
    con_surf = sum(1 for m in materiali if m.file_surf)
    return (f"{len(materiali)} materiali, {con_surf} con il file .surf trovato, "
            f"{con_campione} con il campione")
