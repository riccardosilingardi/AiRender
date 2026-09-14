"""Attrezzi per i test.

Due regole di questa suite:

- niente rete, mai. Una fixture automatica fa saltare qualunque chiamata
  vera, cosi' se un giorno un test dimentica il trasporto finto se ne
  accorge subito;
- niente chiave. I test girano su una macchina che non ne ha una.
"""

from __future__ import annotations

import io
import random
import urllib.request

import pytest
from PIL import Image, ImageDraw

from core.provider.magnific import VARIABILI_CHIAVE


@pytest.fixture(autouse=True)
def niente_rete(monkeypatch):
    def vietato(*_argomenti, **_parametri):
        raise AssertionError("un test ha provato a uscire in rete davvero")

    monkeypatch.setattr(urllib.request, "urlopen", vietato)


@pytest.fixture(autouse=True)
def niente_chiave_nell_ambiente(monkeypatch):
    for nome in VARIABILI_CHIAVE:
        monkeypatch.delenv(nome, raising=False)


def _byte(immagine: Image.Image, formato: str = "PNG") -> bytes:
    deposito = io.BytesIO()
    immagine.save(deposito, format=formato)
    return deposito.getvalue()


def vista_shaded(larghezza: int = 1200, altezza: int = 800, seme: int = 7) -> bytes:
    """Una vista shaded credibile: gradiente, facce diverse, ombre, rumore."""
    caso = random.Random(seme)
    immagine = Image.new("RGB", (larghezza, altezza))
    pixel = immagine.load()
    for y in range(altezza):
        for x in range(larghezza):
            base = 30 + 170 * (y / altezza) + 40 * ((x // max(1, larghezza // 10)) % 3)
            valore = int(base + caso.randint(-10, 10))
            pixel[x, y] = (max(0, min(255, valore)),) * 3
    return _byte(immagine)


def vista_wireframe(larghezza: int = 1200, altezza: int = 800, rumore: int = 0) -> bytes:
    """Linee nere su fondo chiaro: quello che nessuno dovrebbe mandare."""
    caso = random.Random(3)
    immagine = Image.new("RGB", (larghezza, altezza), (252, 252, 252))
    if rumore:
        pixel = immagine.load()
        for y in range(altezza):
            for x in range(larghezza):
                scarto = caso.randint(-rumore, rumore)
                pixel[x, y] = tuple(max(0, min(255, 252 + scarto)) for _ in range(3))
    disegno = ImageDraw.Draw(immagine)
    for indice in range(24):
        disegno.line(
            [(indice * 50, 0), (indice * 50 + 260, altezza)], fill=(0, 0, 0), width=2
        )
        disegno.rectangle(
            [100 + indice * 12, 80 + indice * 6, 900, 600], outline=(0, 0, 0)
        )
    return _byte(immagine)


def vista_piatta(larghezza: int = 1200, altezza: int = 800) -> bytes:
    """Colori pieni senza ombre: shaded senza luci."""
    immagine = Image.new("RGB", (larghezza, altezza), (176, 176, 176))
    disegno = ImageDraw.Draw(immagine)
    disegno.rectangle([100, 100, 1100, 700], fill=(170, 170, 170))
    disegno.rectangle([300, 300, 800, 650], fill=(182, 182, 182))
    return _byte(immagine)


def maschera_netta(larghezza: int = 600, altezza: int = 400) -> bytes:
    """Una maschera col bordo tagliato con l'accetta."""
    immagine = Image.new("L", (larghezza, altezza), 0)
    disegno = ImageDraw.Draw(immagine)
    disegno.rectangle([150, 100, 450, 300], fill=255)
    return _byte(immagine)


class TrasportoFinto:
    """Un servizio finto che risponde quello che gli si dice.

    Registra tutto quello che riceve, cosi' i test possono controllare che
    cosa sarebbe partito davvero.
    """

    def __init__(self, risposte=None, immagine: bytes = b"\x89PNG-finto"):
        self.risposte = list(risposte or [])
        self.immagine = immagine
        self.poste: list[tuple[str, dict, dict]] = []
        self.letture: list[tuple[str, dict]] = []
        self.scaricati: list[str] = []

    def _prossima(self) -> tuple[int, object]:
        if not self.risposte:
            raise AssertionError("il test non ha preparato abbastanza risposte")
        return self.risposte.pop(0)

    def posta(self, url, intestazioni, corpo):
        self.poste.append((url, dict(intestazioni), corpo))
        return self._prossima()

    def leggi(self, url, intestazioni):
        self.letture.append((url, dict(intestazioni)))
        return self._prossima()

    def scarica(self, url):
        self.scaricati.append(url)
        return self.immagine


def risposta_lavoro(stato: str, identificativo: str = "lav-1", prodotti=None):
    corpo = {"data": {"task_id": identificativo, "status": stato}}
    if prodotti is not None:
        corpo["data"]["generated"] = prodotti
    return 200, corpo


class OrologioFinto:
    """Un orologio che va avanti solo quando glielo si dice."""

    def __init__(self) -> None:
        self.adesso = 0.0
        self.attese: list[float] = []

    def leggi(self) -> float:
        return self.adesso

    def attendi(self, secondi: float) -> None:
        self.attese.append(secondi)
        self.adesso += secondi
