"""Il banco di prova dei blocchi: confronti sulla stessa vista che cambiano una cosa sola.

Nessun blocco di prompt e' mai stato provato con un modello, e non sappiamo
se Nano Banana 2 rispetta aree e note. Il banco lo misura, un piano alla
volta:

- qualita   Base contro Altissima definizione (32k), stesso preset;
- look      ogni look contro il preset «Rivista d'architettura»;
- preset    ogni preset della scena una volta (diventano le miniature vere);
- catena    un render, due passi uno sull'altro, poi «rifai pulito» dalla
            vista con le stesse richieste: quanto si spostano gli spigoli
            dopo tre generazioni rispetto a una;
- aree      due aree con due note sulla stessa immagine, mandate (a) con i
            contorni numerati disegnati sopra e (b) con una maschera come
            immagine in piu': fuori dalle aree i pixel restano quelli di prima?

Ogni invio e' a pagamento. Il banco dice prima quanti sono, dove vanno e
quanto costano (regola 5); a secco prepara tutto e non manda niente. Alla
fine scrive nella cartella del banco `banco.json`, una pagina `banco.html`
con le coppie affiancate, i prompt e le misure («non misurato» dove non ce
ne sono), e i giudizi di Riccardo in `giudizi.json`.

Qui non c'e' nessuna rete: il provider lo passa chi chiama.
"""

from __future__ import annotations

import html
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from . import blocchi, grana as modulo_grana, immagine as modulo_immagine
from .cli import _salva
from .errori import ErroreAirender
from .provider.base import Provider, RichiestaGenerazione

PIANI = ("qualita", "look", "preset", "catena", "aree")
VISTA = "vista"
FORMATO = 1  # numero-non-configurabile: versione del formato di banco.json
FILE_BANCO = "banco.json"
FILE_PAGINA = "banco.html"
FILE_GIUDIZI = "giudizi.json"
GIUDIZI = ("meglio A", "uguali", "meglio B", "da rifare")
INTESTAZIONE_BANCO = "X-Airender-Banco"

# Stati di un invio del banco.
FATTO = "fatto"
ERRORE = "errore"
SALTATO = "saltato"
NON_INVIATO = "non inviato"

# Misure.
SPIGOLI = "spigoli"
FUORI_AREE = "fuori-aree"

FORME = ("rettangolo", "libera")


class PianoNonValido(ErroreAirender):
    """Un piano che non esiste o che non si puo' preparare."""


@dataclass(frozen=True)
class Area:
    """Un'area del piano aree, in coordinate da 0 a 1 sull'immagine.

    Un rettangolo ha due punti (due angoli opposti); una selezione libera ne
    ha almeno tre, nell'ordine del lazo.
    """

    forma: str
    punti: tuple[tuple[float, float], ...]
    nota: str

    def __post_init__(self) -> None:
        if self.forma not in FORME:
            raise PianoNonValido(
                f"\"{self.forma}\" non e' una forma di area.",
                "Le forme sono rettangolo e libera.",
            )
        minimo = 2 if self.forma == "rettangolo" else 3  # numero-non-configurabile: punti di un poligono
        if len(self.punti) < minimo or not all(
            len(p) == 2 and all(0 <= c <= 1 for c in p) for p in self.punti
        ):
            raise PianoNonValido(
                f"Un'area {self.forma} ha punti che non tornano: {list(self.punti)}.",
                "Un rettangolo ha due punti, una selezione libera almeno tre; "
                "ogni punto e' [x, y] fra 0 e 1.",
            )
        if not " ".join(self.nota.split()):
            raise PianoNonValido(
                "Un'area senza nota non dice al modello cosa fare.",
                "Scrivi la nota dell'area.",
            )

    def in_pixel(self, larghezza: int, altezza: int) -> list[tuple[float, float]]:
        punti = [(x * larghezza, y * altezza) for x, y in self.punti]
        if self.forma == "rettangolo":
            (x0, y0), (x1, y1) = punti[0], punti[1]
            return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return punti

    @classmethod
    def da_dizionario(cls, dati: object) -> "Area":
        if not isinstance(dati, dict):
            raise PianoNonValido("Un'area del file non e' un oggetto.", "Ogni area e' {forma, punti, nota}.")
        try:
            punti = tuple(tuple(float(c) for c in p) for p in dati.get("punti") or ())
        except (TypeError, ValueError):
            punti = ()
        return cls(str(dati.get("forma") or ""), punti, str(dati.get("nota") or ""))

    def a_dizionario(self) -> dict:
        return {"forma": self.forma, "punti": [list(p) for p in self.punti], "nota": self.nota}


@dataclass(frozen=True)
class Invio:
    """Un invio del piano: da dove parte, con quale prompt, e come si prepara l'immagine."""

    nome: str
    titolo: str
    prompt: str
    da: str = VISTA
    preset: str | None = None
    scelte: dict | None = None
    contorni: bool = False  # l'immagine parte con le aree disegnate sopra
    maschera: bool = False  # la maschera delle aree parte come seconda immagine


@dataclass(frozen=True)
class Confronto:
    """Una coppia da guardare affiancata. A e B sono "vista" o il nome di un invio."""

    a: str
    b: str
    titolo: str


@dataclass(frozen=True)
class Piano:
    nome: str
    domanda: str
    misura: str
    invii: tuple[Invio, ...]
    confronti: tuple[Confronto, ...]
    aree: tuple[Area, ...] = field(default=())

    def invio(self, nome: str) -> Invio:
        return next(i for i in self.invii if i.nome == nome)


# --- i piani -------------------------------------------------------------------


def _da_preset(nome: str, titolo: str, preset: str, **cambi) -> Invio:
    scelte = blocchi.da_preset(preset, **cambi)
    return Invio(nome, titolo, blocchi.componi(scelte), preset=preset, scelte=scelte.a_dizionario())


def _riferimento(scena: str) -> str:
    return "rivista" if scena == blocchi.ESTERNO else "interno-rivista"


def _passi_catena(scena: str) -> tuple[dict, dict]:
    """Le due richieste della catena: prima qualcosa intorno, poi le persone."""
    if scena == blocchi.ESTERNO:
        return {"verde": "poco"}, {"persone": "poche"}
    return {"arredo": "leggero"}, {"persone": "poche"}


def piano(nome: str, scena: str = blocchi.ESTERNO, aree: tuple[Area, ...] = ()) -> Piano:
    """Il piano con quel nome, per una vista di quella scena."""
    if scena not in blocchi.SCENE:
        raise PianoNonValido(f"La scena \"{scena}\" non esiste.", "Scegli esterno o interno.")
    riferimento = _riferimento(scena)
    nome_riferimento = blocchi.preset_stile(riferimento).nome
    if nome == "qualita":
        invii = (
            _da_preset("base", f"{nome_riferimento} · qualità Base", riferimento, qualita="base"),
            _da_preset("32k", f"{nome_riferimento} · Altissima definizione (32k)", riferimento, qualita="32k"),
        )
        return Piano(nome, "Il blocco 32k cambia il render rispetto a Base, a parità di tutto il resto?",
                     SPIGOLI, invii, (Confronto("base", "32k", "Base contro 32k"),))
    if nome == "look":
        base = blocchi.preset_stile(riferimento).scelte.look
        invii = [_da_preset(riferimento, f"{nome_riferimento} (look {blocchi.LOOK[base].nome})", riferimento)]
        invii += [
            _da_preset(f"look-{look}", f"{nome_riferimento} con il look {b.nome}", riferimento, look=look)
            for look, b in blocchi.LOOK.items() if look != base
        ]
        confronti = tuple(Confronto(riferimento, i.nome, i.titolo) for i in invii[1:])
        return Piano(nome, f"Cosa cambia ogni look rispetto al preset {nome_riferimento}?",
                     SPIGOLI, tuple(invii), confronti)
    if nome == "preset":
        invii = tuple(
            _da_preset(p.identificativo, p.nome, p.identificativo)
            for p in blocchi.PRESET_STILE.values() if p.scelte.scena == scena
        )
        return Piano(nome, "Ogni preset rende quello che la sua miniatura promette?", SPIGOLI, invii,
                     tuple(Confronto(VISTA, i.nome, i.titolo) for i in invii))
    if nome == "catena":
        primo, secondo = _passi_catena(scena)
        insieme = {**primo, **secondo}
        nomi = {asse: blocchi.blocco(asse, v, scena).nome.lower() for asse, v in insieme.items()}
        scelte_pulito = blocchi.da_preset(riferimento, **insieme)
        invii = (
            _da_preset("passo-1", f"1 · {nome_riferimento}", riferimento),
            Invio("passo-2", f"2 · dal passo 1: {next(iter(primo))} {nomi[next(iter(primo))]}",
                  blocchi.componi_passo(scena, primo), da="passo-1", scelte=primo),
            Invio("passo-3", f"3 · dal passo 2: persone {nomi['persone']}",
                  blocchi.componi_passo(scena, secondo), da="passo-2", scelte=secondo),
            Invio("pulito", "Rifai pulito dalla vista: le tre richieste in un invio",
                  blocchi.componi(scelte_pulito), preset=riferimento, scelte=scelte_pulito.a_dizionario()),
        )
        confronti = (
            Confronto(VISTA, "passo-1", "Vista contro 1 generazione"),
            Confronto(VISTA, "passo-3", "Vista contro 3 generazioni di fila"),
            Confronto(VISTA, "pulito", "Vista contro «rifai pulito» (1 generazione)"),
            Confronto("passo-3", "pulito", "3 generazioni contro rifai pulito"),
        )
        return Piano(nome, "Quanto si spostano gli spigoli dopo tre generazioni di fila, "
                           "rispetto a una sola con le stesse richieste?", SPIGOLI, invii, confronti)
    if nome == "aree":
        if len(aree) < 2:
            raise PianoNonValido(
                "Il piano aree ha bisogno di almeno due aree, ognuna con la sua nota.",
                "Passa un file con --aree, oppure usa le aree predefinite del banco.",
            )
        note = [a.nota for a in aree]
        invii = (
            Invio("contorni", "(a) Aree disegnate sull'immagine, note nel testo",
                  blocchi.componi_aree(blocchi.AREE_CONTORNI, note), contorni=True),
            Invio("maschera", "(b) Maschera come seconda immagine, note nel testo",
                  blocchi.componi_aree(blocchi.AREE_MASCHERA, note), maschera=True),
        )
        confronti = (
            Confronto(VISTA, "contorni", "Partenza contro (a) contorni"),
            Confronto(VISTA, "maschera", "Partenza contro (b) maschera"),
            Confronto("contorni", "maschera", "(a) contro (b)"),
        )
        return Piano(nome, "Fuori dalle aree i pixel restano quelli di prima? Con contorni o con maschera?",
                     FUORI_AREE, invii, confronti, tuple(aree))
    raise PianoNonValido(f"Non esiste un piano chiamato \"{nome}\".", f"I piani sono: {', '.join(PIANI)}.")


# --- prima di partire ------------------------------------------------------------


def riepilogo(piano_scelto: Piano, motore: Provider, modello: str, costo: str) -> list[str]:
    """Le righe da dire prima di chiedere conferma: quanti invii, dove, quanto."""
    righe = [
        f"Piano «{piano_scelto.nome}»: {piano_scelto.domanda}",
        f"Invii: {len(piano_scelto.invii)}, uno dopo l'altro.",
        f"Destinazione di ogni invio: {motore.destinazione_per(modello)}.",
        f"Costo stimato: {costo}.",
    ]
    mancante = motore.cosa_manca(modello)
    if mancante:
        righe.append(f"Attenzione: {mancante}")
    if any(i.maschera for i in piano_scelto.invii):
        righe.append(
            "Attenzione: l'invio (b) porta due immagini, vista e maschera. Il modo in cui "
            "le portiamo a Nano Banana 2 non e' mai stato provato con una chiamata vera: "
            "se il Router lo rifiuta, l'invio (b) finisce fra gli errori e (a) resta valido."
        )
    return righe


# --- esecuzione ------------------------------------------------------------------


def _adesso() -> datetime:
    return datetime.now()


def cartella_del_banco(vista: Path, nome_piano: str, uscita: Path | None, adesso: datetime) -> Path:
    radice = Path(uscita) if uscita else Path(vista).parent
    return radice / f"{Path(vista).stem}-banco-{nome_piano}-{adesso:%Y%m%d-%H%M%S}"


def _prepara(piano_scelto: Piano, vista: bytes, cartella: Path) -> dict[str, str]:
    """Le immagini preparate (contorni, maschera), scritte nella cartella. Nome -> file."""
    preparate = {}
    if not piano_scelto.aree:
        return preparate
    larghezza, altezza = modulo_immagine.dimensioni(vista)
    poligoni = [a.in_pixel(larghezza, altezza) for a in piano_scelto.aree]
    if any(i.contorni for i in piano_scelto.invii):
        (cartella / "preparata-contorni.png").write_bytes(modulo_immagine.disegna_aree(vista, poligoni))
        preparate["contorni"] = "preparata-contorni.png"
    if any(i.maschera for i in piano_scelto.invii):
        (cartella / "preparata-maschera.png").write_bytes(
            modulo_immagine.maschera_aree((larghezza, altezza), poligoni))
        preparate["maschera"] = "preparata-maschera.png"
    return preparate


def _misura(piano_scelto: Piano, vista: bytes, render: bytes) -> dict:
    if piano_scelto.misura == SPIGOLI:
        return {SPIGOLI: modulo_immagine.spigoli_ritrovati(vista, render)}
    larghezza, altezza = modulo_immagine.dimensioni(vista)
    poligoni = [a.in_pixel(larghezza, altezza) for a in piano_scelto.aree]
    misura = modulo_immagine.differenza_fuori_dalle_aree(vista, render, poligoni)
    misura["dimensioni_render"] = list(modulo_immagine.dimensioni(render))
    return {FUORI_AREE: misura}


def esegui(
    piano_scelto: Piano,
    vista_percorso: Path,
    cartella: Path,
    *,
    motore: Provider,
    modello: str,
    costo: str,
    a_secco: bool,
    dire: Callable[[str], None] = print,
    adesso: Callable[[], datetime] = _adesso,
) -> dict:
    """Prepara, manda (se non a secco), misura e scrive banco.json e banco.html.

    Un invio fallito non ferma gli altri; quelli che partono da lui si saltano.
    """
    vista = modulo_immagine.leggi(vista_percorso)
    cartella.mkdir(parents=True, exist_ok=True)
    nome_vista = "vista" + (Path(vista_percorso).suffix.lower() or ".png")
    shutil.copyfile(vista_percorso, cartella / nome_vista)
    preparate = _prepara(piano_scelto, vista, cartella)
    immagini = {VISTA: vista}
    file_di = {VISTA: nome_vista}
    risultati = []
    for invio in piano_scelto.invii:
        voce = {
            "nome": invio.nome, "titolo": invio.titolo, "prompt": invio.prompt, "da": invio.da,
            "preset": invio.preset, "scelte": invio.scelte,
            "ingresso": preparate["contorni"] if invio.contorni else file_di.get(invio.da),
            "in_piu": [preparate["maschera"]] if invio.maschera else [],
            "render": None, "ricetta": None, "misure": {}, "crediti": None,
        }
        risultati.append(voce)
        if a_secco:
            voce["stato"] = NON_INVIATO
            continue
        if invio.da not in immagini:
            voce["stato"] = SALTATO
            voce["fatto"] = f"Parte da {invio.da}, che non ha un render."
            dire(f"{invio.titolo}: saltato, parte da un invio non riuscito.")
            continue
        ingresso = (cartella / preparate["contorni"]).read_bytes() if invio.contorni else immagini[invio.da]
        in_piu = ((cartella / preparate["maschera"]).read_bytes(),) if invio.maschera else ()
        richiesta = RichiestaGenerazione(
            immagine=ingresso,
            prompt=invio.prompt,
            preset=invio.preset or f"banco-{piano_scelto.nome}",
            preset_versione=blocchi.VERSIONE,
            modello=modello,
            grana=modulo_grana.MEDIA,
            dettaglio_grana=modulo_grana.dettaglio(modulo_grana.MEDIA),
            immagini_in_piu=in_piu,
        )
        dire(f"Invio {len(risultati)} di {len(piano_scelto.invii)}: {invio.titolo}")
        try:
            risultato = motore.genera(richiesta)
        except ErroreAirender as errore:
            # Gli invii gia' fatti sono pagati: non si buttano per colpa di questo.
            voce.update(stato=ERRORE, fatto=errore.fatto, cosa_fare=errore.cosa_fare)
            dire(f"{invio.titolo}: non riuscito. {errore.fatto}")
            continue
        nome_file = f"{invio.nome}.{risultato.formato}"
        ricetta = _salva(risultato, cartella / nome_file)
        immagini[invio.nome] = risultato.immagine
        file_di[invio.nome] = nome_file
        crediti = (risultato.ricetta.parametri or {}).get("crediti_usati")
        voce.update(stato=FATTO, render=nome_file, ricetta=Path(ricetta).name, crediti=crediti,
                    misure=_misura(piano_scelto, vista, risultato.immagine))
    banco = {
        "formato": FORMATO,
        "piano": piano_scelto.nome,
        "domanda": piano_scelto.domanda,
        "misura": piano_scelto.misura,
        "vista": nome_vista,
        "vista_originale": str(Path(vista_percorso).resolve()),
        "modello": modello,
        "destinazione": motore.destinazione_per(modello),
        "costo_stimato": costo,
        "versione_blocchi": blocchi.VERSIONE,
        "creato_il": adesso().isoformat(timespec="seconds"),
        "a_secco": a_secco,
        "aree": [a.a_dizionario() for a in piano_scelto.aree],
        "preparate": preparate,
        "invii": risultati,
        "confronti": [{"a": c.a, "b": c.b, "titolo": c.titolo} for c in piano_scelto.confronti],
    }
    (cartella / FILE_BANCO).write_text(json.dumps(banco, ensure_ascii=False, indent=2), encoding="utf-8")
    (cartella / FILE_PAGINA).write_text(pagina(banco), encoding="utf-8")
    return banco


def leggi_banco(cartella: Path) -> dict:
    try:
        banco = json.loads((Path(cartella) / FILE_BANCO).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PianoNonValido(
            f"Nella cartella {cartella} non c'e' un {FILE_BANCO} leggibile.",
            "Indica la cartella che il banco ha scritto, quella con banco.html dentro.",
        ) from None
    if not isinstance(banco, dict) or banco.get("formato") != FORMATO:
        raise PianoNonValido(
            f"Il {FILE_BANCO} di {cartella} e' di un altro formato.",
            "Rilancia il piano con questa versione del banco.",
        )
    return banco


# --- la pagina ---------------------------------------------------------------------


def _numero(valore: float, cifre: int = 1) -> str:
    return f"{valore:.{cifre}f}".replace(".", ",")


def _percento(quota: float) -> str:
    return f"{_numero(quota * 100)}%"  # numero-non-configurabile: da quota a percento


def testo_misura(voce: dict | None, misura: str) -> str:
    """La misura di un invio in una frase, o «non misurato». Sempre con lo stesso arrotondamento."""
    if voce is None:
        return "vista di partenza"
    valore = (voce.get("misure") or {}).get(misura)
    if misura == SPIGOLI:
        if valore is None:
            return "Spigoli della vista ritrovati: non misurato."
        return (f"Spigoli della vista ritrovati: {_percento(valore)} · misura grezza con soglie "
                "scelte, non validata: serve a confrontare le generazioni di questo banco, "
                "giudica con l'occhio.")
    if not valore or valore.get("differenza_media") is None:
        return "Fuori dalle aree: non misurato."
    testo = (f"Fuori dalle aree: differenza media {_numero(valore['differenza_media'])} su 255 · "
             f"{_percento(valore['quota_cambiata'])} dei pixel cambiati in modo visibile.")
    if valore.get("ridimensionata"):
        larghezza, altezza = valore.get("dimensioni_render") or ("?", "?")
        testo += (f" Il render e' {larghezza}x{altezza}, non della dimensione di partenza: "
                  "la misura conta anche il ricampionamento.")
    return testo


def _figura(banco: dict, nome: str) -> str:
    if nome == VISTA:
        file, titolo = banco["vista"], ("Vista di partenza" if banco["piano"] != "aree" else "Immagine di partenza")
    else:
        voce = next(v for v in banco["invii"] if v["nome"] == nome)
        file, titolo = voce.get("render"), voce["titolo"]
        if not file:
            stato = voce.get("stato", NON_INVIATO)
            motivo = voce.get("fatto") or ("prova a secco: niente inviato" if stato == NON_INVIATO else "")
            return (f"<figure class='vuota'><div>{html.escape(stato)}</div>"
                    f"<figcaption>{html.escape(titolo)}<br><small>{html.escape(motivo)}</small>"
                    f"</figcaption></figure>")
    return (f"<figure><img src='{html.escape(file)}' alt='{html.escape(titolo)}'>"
            f"<figcaption>{html.escape(titolo)}</figcaption></figure>")


def _dettagli(banco: dict, nome: str) -> str:
    if nome == VISTA:
        return ""
    voce = next(v for v in banco["invii"] if v["nome"] == nome)
    crediti = f" · {html.escape(str(voce['crediti']))} crediti" if voce.get("crediti") else ""
    ingresso = f"Parte da: {html.escape(str(voce.get('ingresso') or voce['da']))}"
    if voce.get("in_piu"):
        ingresso += " + " + ", ".join(html.escape(f) for f in voce["in_piu"])
    return (f"<details><summary>Prompt di «{html.escape(voce['titolo'])}»{crediti}</summary>"
            f"<p class='piccolo'>{ingresso}</p><pre>{html.escape(voce['prompt'])}</pre></details>"
            f"<p class='misura'>{html.escape(testo_misura(voce, banco['misura']))}</p>")


def pagina(banco: dict) -> str:
    """La pagina locale del banco: coppie affiancate, prompt, misure, campo del giudizio."""
    stato = ("Prova a secco: non ho inviato niente. Le immagini preparate e i prompt sono quelli che "
             "partirebbero." if banco["a_secco"] else
             f"Inviato a {banco['destinazione']}. Costo stimato prima di partire: {banco['costo_stimato']}.")
    schede = []
    for indice, confronto in enumerate(banco["confronti"]):
        scelte = "".join(
            f"<label><input type='radio' name='g{indice}' value='{html.escape(g)}'> {html.escape(g)}</label>"
            for g in GIUDIZI)
        schede.append(
            f"<section class='coppia' data-chiave='{html.escape(confronto['a'])}|{html.escape(confronto['b'])}'>"
            f"<h2>{html.escape(confronto['titolo'])}</h2>"
            f"<div class='affiancate'>{_figura(banco, confronto['a'])}{_figura(banco, confronto['b'])}</div>"
            f"<div class='dettagli'><div>{_dettagli(banco, confronto['a'])}</div>"
            f"<div>{_dettagli(banco, confronto['b'])}</div></div>"
            f"<fieldset><legend>Il tuo giudizio (A a sinistra, B a destra)</legend>{scelte}"
            f"<textarea rows='2' placeholder='Cosa vedi: spigoli, materiali, cosa è cambiato'></textarea>"
            f"</fieldset></section>")
    preparate = "".join(
        f"<figure><img src='{html.escape(f)}' alt='{html.escape(n)}'><figcaption>Preparata: {html.escape(n)}"
        f"</figcaption></figure>" for n, f in (banco.get("preparate") or {}).items())
    note = "".join(f"<li>Area {n} ({html.escape(a['forma'])}): {html.escape(a['nota'])}</li>"
                   for n, a in enumerate(banco.get("aree") or [], start=1))
    return _MODELLO_PAGINA.format(
        titolo=html.escape(f"Banco di prova · {banco['piano']}"),
        domanda=html.escape(banco["domanda"]),
        stato=html.escape(stato),
        modello=html.escape(banco["modello"]),
        versione=html.escape(banco["versione_blocchi"]),
        creato=html.escape(banco["creato_il"]),
        aree=f"<ul>{note}</ul><div class='affiancate'>{preparate}</div>" if note else "",
        schede="".join(schede),
        file_giudizi=FILE_GIUDIZI,
        intestazione=INTESTAZIONE_BANCO,
    )


_MODELLO_PAGINA = """<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titolo}</title>
<style>
:root {{ color-scheme: light dark; --fondo: #F6F5F2; --testo: #1C1C1E; --tenue: #66666B; --bordo: #DADAD6; --carta: #FFFFFF; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fondo: #141518; --testo: #EDEDEF; --tenue: #A0A0A6; --bordo: #34353A; --carta: #1D1E22; }} }}
body {{ margin: 0; padding: 24px; background: var(--fondo); color: var(--testo); font: 15px/1.5 "Segoe UI", system-ui, sans-serif; }}
h1 {{ font-size: 22px; margin: 0 0 4px; }} h2 {{ font-size: 17px; margin: 0 0 12px; }}
.tenue, .piccolo, small {{ color: var(--tenue); font-size: 13px; }}
.coppia {{ background: var(--carta); border: 1px solid var(--bordo); border-radius: 12px; padding: 16px; margin: 16px 0; }}
.affiancate {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
.dettagli {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 8px; }}
figure {{ margin: 0; }} img {{ width: 100%; display: block; border-radius: 8px; }}
figure.vuota div {{ aspect-ratio: 16/9; display: grid; place-items: center; border: 1px dashed var(--bordo); border-radius: 8px; color: var(--tenue); }}
figcaption {{ font-size: 13px; margin-top: 4px; }}
pre {{ white-space: pre-wrap; font: 12px/1.45 ui-monospace, Consolas, monospace; background: var(--fondo); padding: 8px; border-radius: 6px; }}
.misura {{ font-size: 13px; }}
fieldset {{ border: 1px solid var(--bordo); border-radius: 8px; margin-top: 12px; }}
label {{ margin-right: 16px; }} textarea {{ width: 100%; box-sizing: border-box; margin-top: 8px; font: inherit; }}
button {{ font: inherit; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--bordo); background: var(--carta); color: var(--testo); cursor: pointer; }}
@media (max-width: 720px) {{ .affiancate, .dettagli {{ grid-template-columns: 1fr; }} body {{ padding: 16px; }} }}
</style></head>
<body>
<h1>{titolo}</h1>
<p>{domanda}</p>
<p class="tenue">{stato}<br>Modello {modello} · blocchi {versione} · {creato}</p>
{aree}
{schede}
<p><button id="salva">Salva i giudizi</button> <span id="esito" class="tenue"></span></p>
<p class="tenue">Aperta con <code>python scripts/prova_blocchi.py --giudica &lt;questa cartella&gt;</code>, i giudizi
si salvano in {file_giudizi} accanto a questa pagina. Aperta come file, il pulsante scarica {file_giudizi}:
mettilo in questa cartella.</p>
<script>
"use strict";
const coppie = [...document.querySelectorAll(".coppia")];
function raccogli() {{
  return {{ giudizi: coppie.map((c) => {{
    const scelto = c.querySelector("input[type=radio]:checked");
    const [a, b] = c.dataset.chiave.split("|");
    return {{ a, b, giudizio: scelto ? scelto.value : null, note: c.querySelector("textarea").value }};
  }}) }};
}}
function riempi(dati) {{
  for (const g of (dati && dati.giudizi) || []) {{
    const c = coppie.find((x) => x.dataset.chiave === `${{g.a}}|${{g.b}}`);
    if (!c) continue;
    const r = [...c.querySelectorAll("input[type=radio]")].find((x) => x.value === g.giudizio);
    if (r) r.checked = true;
    c.querySelector("textarea").value = g.note || "";
  }}
}}
const servita = location.protocol.startsWith("http");
if (servita) fetch("{file_giudizi}").then((r) => r.ok ? r.json() : null).then(riempi).catch(() => {{}});
document.getElementById("salva").addEventListener("click", async () => {{
  const esito = document.getElementById("esito");
  const dati = raccogli();
  if (servita) {{
    const r = await fetch("/giudizi", {{ method: "POST", headers: {{ "Content-Type": "application/json", "{intestazione}": "1" }}, body: JSON.stringify(dati) }});
    esito.textContent = r.ok ? "Salvati in {file_giudizi}." : "Non salvati: " + await r.text();
  }} else {{
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([JSON.stringify(dati, null, 2)], {{ type: "application/json" }}));
    a.download = "{file_giudizi}";
    a.click();
    esito.textContent = "Scaricato {file_giudizi}: mettilo nella cartella di questa pagina.";
  }}
}});
</script>
</body></html>
"""


# --- i giudizi ------------------------------------------------------------------


def salva_giudizi(cartella: Path, dati: object) -> Path:
    """Scrive giudizi.json accanto alla pagina, dopo aver controllato che parli di questo banco."""
    banco = leggi_banco(cartella)
    coppie = {(c["a"], c["b"]) for c in banco["confronti"]}
    voci = dati.get("giudizi") if isinstance(dati, dict) else None
    if not isinstance(voci, list):
        raise PianoNonValido("I giudizi non sono arrivati.", "Ricarica la pagina del banco e salva di nuovo.")
    pulite = []
    for voce in voci:
        if not isinstance(voce, dict) or (voce.get("a"), voce.get("b")) not in coppie:
            raise PianoNonValido("Un giudizio parla di una coppia che questo banco non ha.",
                                 "Ricarica la pagina del banco e salva di nuovo.")
        if voce.get("giudizio") not in (*GIUDIZI, None):
            raise PianoNonValido(f"\"{voce.get('giudizio')}\" non e' un giudizio.",
                                 f"I giudizi sono: {', '.join(GIUDIZI)}.")
        pulite.append({"a": voce["a"], "b": voce["b"], "giudizio": voce.get("giudizio"),
                       "note": str(voce.get("note") or "")})
    percorso = Path(cartella) / FILE_GIUDIZI
    percorso.write_text(json.dumps({"piano": banco["piano"], "giudizi": pulite}, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return percorso


def server_giudizi(cartella: Path, porta: int = 0) -> ThreadingHTTPServer:
    """Un server solo su 127.0.0.1 che serve la cartella del banco e salva i giudizi."""
    cartella = Path(cartella).resolve()
    leggi_banco(cartella)

    class Gestore(BaseHTTPRequestHandler):
        def _rispondi(self, stato: int, corpo: bytes, tipo: str) -> None:
            self.send_response(stato)
            self.send_header("Content-Type", tipo)
            self.send_header("Content-Length", str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

        def do_GET(self):  # noqa: N802 (nome imposto da http.server)
            nome = self.path.split("?", 1)[0].lstrip("/") or FILE_PAGINA
            percorso = (cartella / nome).resolve()
            if percorso.parent != cartella or not percorso.is_file():
                self._rispondi(HTTPStatus.NOT_FOUND, b"", "text/plain")
                return
            tipi = {".html": "text/html; charset=utf-8", ".json": "application/json",
                    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
            self._rispondi(HTTPStatus.OK, percorso.read_bytes(),
                           tipi.get(percorso.suffix.lower(), "application/octet-stream"))

        def do_POST(self):  # noqa: N802 (nome imposto da http.server)
            if self.path != "/giudizi" or self.headers.get(INTESTAZIONE_BANCO) != "1":
                self._rispondi(HTTPStatus.FORBIDDEN, b"", "text/plain")
                return
            lunghezza = int(self.headers.get("Content-Length") or 0)
            try:
                salva_giudizi(cartella, json.loads(self.rfile.read(lunghezza) or b"null"))
            except (ValueError, ErroreAirender) as errore:
                testo = getattr(errore, "fatto", str(errore))
                self._rispondi(HTTPStatus.BAD_REQUEST, testo.encode("utf-8"), "text/plain; charset=utf-8")
                return
            self._rispondi(HTTPStatus.OK, b"{}", "application/json")

        def log_message(self, *_argomenti):  # niente console da riempire
            return

    return ThreadingHTTPServer(("127.0.0.1", porta), Gestore)
