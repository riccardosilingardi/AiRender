"""I materiali del progetto Allplan: l'elenco letto dalla palette e quelli da cambiare.

Decisione di Riccardo (2026-11-02): AIRENDER non cambia mai i materiali di
Allplan. Quando si cattura una vista, la palette legge i materiali del
progetto aperto e li scrive accanto alla vista (`<vista>.materiali.json`), con
l'anteprima che Allplan tiene dentro ogni file .surf (il cubetto del catalogo
materiali). Nello Studio l'utente spunta quelli da cambiare, scrive cosa
diventano e, se vuole, aggiunge una foto di riferimento. Al modello partono la
vista e, per ogni materiale spuntato, l'anteprima e la foto.

Il modello riconosce il materiale dal suo aspetto nella vista: due materiali
che nella vista sembrano uguali si possono confondere (PRD, sezione 9).

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

from . import config
from .errori import ErroreAirender, FileNonTrovato

SUFFISSO = ".materiali.json"
CARTELLA_ANTEPRIME = "materiali"
FORMATO_ELENCO = 1  # numero-non-configurabile: versione del file dei materiali di una vista


class MaterialeNonValido(ErroreAirender):
    """Un materiale da cambiare che non si puo' mandare."""


def percorso_elenco(vista: Path) -> Path:
    vista = Path(vista)
    return vista.with_name(vista.stem + SUFFISSO)


def cartella_anteprime(radice: Path) -> Path:
    return Path(radice) / CARTELLA_ANTEPRIME


def anteprima_da_surf(dati: bytes) -> bytes:
    """L'anteprima che Allplan tiene in un file .surf, in PNG.

    Il .surf di Allplan 2027 e' un TIFF: l'immagine e' il cubetto 120×120 del
    catalogo materiali, il resto sono dati della superficie (verificato sui 27
    .surf del progetto 4253, 2026-11-02).
    """
    from PIL import Image  # pylint: disable=import-outside-toplevel

    with Image.open(io.BytesIO(dati)) as immagine:
        uscita = io.BytesIO()
        immagine.convert("RGB").save(uscita, format="PNG")
    return uscita.getvalue()


@dataclass(frozen=True)
class MaterialeModello:
    """Un materiale del progetto, come lo ha letto la palette."""

    chiave: str  # il valore letto da Allplan: percorso della superficie o nome
    nome: str
    elementi: int
    anteprima: str | None = None  # nome del PNG nella cartella delle anteprime

    def a_dizionario(self) -> dict:
        return {"chiave": self.chiave, "nome": self.nome, "elementi": self.elementi,
                "anteprima": self.anteprima}


def scrivi_elenco(vista: Path, materiali: list[MaterialeModello], senza_materiale: list[str],
                  letto_il: str, errore: str | None = None) -> Path:
    destinazione = percorso_elenco(vista)
    destinazione.write_text(json.dumps({
        "formato": FORMATO_ELENCO,
        "letto_il": letto_il,
        "materiali": [m.a_dizionario() for m in materiali],
        "senza_materiale": senza_materiale,
        "errore": errore,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return destinazione


def leggi_elenco(vista: Path) -> dict | None:
    """L'elenco dei materiali di una vista, o None se la palette non l'ha scritto."""
    try:
        dati = json.loads(percorso_elenco(vista).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(dati, dict) or dati.get("formato") != FORMATO_ELENCO:
        return None
    materiali = []
    for voce in dati.get("materiali") or []:
        try:
            materiali.append(MaterialeModello(str(voce["chiave"]), str(voce["nome"]),
                                              int(voce["elementi"]), voce.get("anteprima") or None))
        except (KeyError, TypeError, ValueError):
            continue
    return {"letto_il": dati.get("letto_il"), "materiali": materiali,
            "senza_materiale": [str(s) for s in dati.get("senza_materiale") or []],
            "errore": dati.get("errore")}


def controlla_anteprima(radice: Path, nome: str) -> Path:
    """Il file di un'anteprima, solo dalla cartella delle anteprime."""
    if not nome or "/" in nome or "\\" in nome or nome.startswith("."):
        raise MaterialeNonValido(f"\"{nome}\" non e' il nome di un'anteprima di materiale.",
                                 "Cattura di nuovo la vista dalla palette.")
    percorso = cartella_anteprime(radice) / nome
    if not percorso.is_file():
        raise FileNonTrovato(f"L'anteprima del materiale {nome} non c'e' piu'.",
                             "Cattura di nuovo la vista dalla palette.")
    return percorso


@dataclass(frozen=True)
class Cambio:
    """Un materiale di Allplan da rendere come un altro."""

    nome: str
    diventa: str
    anteprima: str | None = None  # percorso del PNG
    riferimento: str | None = None  # percorso della foto di riferimento

    def __post_init__(self) -> None:
        if not self.diventa.strip():
            raise MaterialeNonValido(
                f"Per «{self.nome}» manca cosa deve diventare.",
                "Scrivi il nuovo materiale nella riga, oppure togli la spunta da Cambia.",
            )

    def immagini(self) -> list[str]:
        return [p for p in (self.anteprima, self.riferimento) if p]

    def a_dizionario(self) -> dict:
        return {"nome": self.nome, "diventa": self.diventa,
                "anteprima": self.anteprima, "riferimento": self.riferimento}

    @classmethod
    def da_dizionario(cls, dati: object) -> "Cambio":
        if not isinstance(dati, dict):
            raise MaterialeNonValido("Un materiale da cambiare non e' scritto bene.",
                                     "Rimetti il lavoro in coda dallo Studio.")
        return cls(str(dati.get("nome") or ""), str(dati.get("diventa") or ""),
                   dati.get("anteprima") or None, dati.get("riferimento") or None)


def controlla_cambi(cambi: tuple[Cambio, ...]) -> tuple[Cambio, ...]:
    massimo = config.MATERIALI_CAMBIATI_MASSIMI
    if len(cambi) > massimo:
        raise MaterialeNonValido(
            f"Hai spuntato {len(cambi)} materiali da cambiare, in un invio ne partono al massimo {massimo}.",
            "Togli la spunta da qualcuno: gli altri li cambi con un passo dopo.",
        )
    nomi = [c.nome for c in cambi]
    if len(set(nomi)) != len(nomi):
        raise MaterialeNonValido("Lo stesso materiale compare due volte fra quelli da cambiare.",
                                 "Ricarica lo Studio.")
    return cambi


def prima_immagine(riferimenti: int | bool) -> int:
    """Il numero della prima immagine dei materiali: dopo la vista e le immagini per lo stile.

    `riferimenti` e' quante immagini per lo stile partono (il riferimento e
    gli esempi di «Stile da esempi»); True vale una.
    """
    return 2 + int(riferimenti)  # numero-non-configurabile: posizioni delle immagini nell'invio


def quante_immagini(cambi: tuple[Cambio, ...]) -> int:
    return sum(len(c.immagini()) for c in cambi)


def prompt(base: str, cambi: tuple[Cambio, ...], prima_immagine: int) -> str:
    """Il prompt con una frase per materiale. `prima_immagine` e' il numero della prima immagine dei materiali."""
    if not cambi:
        return base
    righe = ["Material changes. Image 1 is the view to render. Keep the geometry of image 1 exactly."]
    numero = prima_immagine
    for cambio in cambi:
        if cambio.anteprima:
            frase = (f"Image {numero} is a sample of the material «{cambio.nome}» as the CAD model shows it: "
                     f"every surface in image 1 that looks like this sample becomes: {cambio.diventa.strip()}.")
            numero += 1
        else:
            frase = (f"The surfaces of the material «{cambio.nome}» (no sample available) become: "
                     f"{cambio.diventa.strip()}.")
        if cambio.riferimento:
            frase += f" Image {numero} is a photo of the new material: match its colour, texture and finish."
            numero += 1
        righe.append(frase)
    righe.append("Do not change the surfaces of the other materials.")
    return f"{base.strip()} {' '.join(righe)}"
