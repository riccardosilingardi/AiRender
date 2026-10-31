"""Esporta per il cliente: il render in JPEG o PNG, o un PSD con un livello per passaggio.

Decisioni di Riccardo del 2026-10-31: formati JPG, PNG o PSD «con i layer dei
vari passaggi». Nel PSD il livello in basso e' la vista di Allplan, sopra ci
sono i render della strada che porta al render scelto, uno per passo, e in
cima il render scelto. Tutti alla grandezza del render scelto.

Nel file non entra niente oltre ai pixel: ne' il prompt, ne' la ricetta, ne'
la chiave (CLAUDE.md, regola 4). I pixel si rileggono e si riscrivono, cosi'
anche quello che il servizio aveva messo nel file resta fuori.

Il PSD e' scritto qui, senza librerie in piu': canali non compressi, 8 bit,
RGB, un canale di trasparenza piena per livello. Pesa (circa 4 byte per pixel
per livello) ma si apre in Photoshop e in Pillow. Nessuna dipendenza da
Allplan: si prova da riga di comando.
"""

from __future__ import annotations

import io
import struct

from PIL import Image

from . import config
from .errori import ErroreAirender

FORMATI = ("jpg", "png", "psd")
ESTENSIONI = {"jpg": ".jpg", "png": ".png", "psd": ".psd"}


class EsportazioneNonValida(ErroreAirender):
    """Un formato che non esiste, un PSD senza livelli, un'immagine che non si legge."""


def _rgb(dati: bytes) -> Image.Image:
    try:
        immagine = Image.open(io.BytesIO(dati))
        immagine.load()
    except Exception as errore:  # Pillow solleva tipi diversi per file diversi
        raise EsportazioneNonValida(
            f"Un'immagine da esportare non si legge ({errore}).",
            "Controlla che il render ci sia ancora nella cartella dei lavori.",
        ) from None
    return immagine.convert("RGB")


def esporta(render: bytes, formato: str, livelli: list[tuple[str, bytes]] | None = None) -> bytes:
    """I byte del file da consegnare. Per il PSD servono i livelli, dal basso in alto, render compreso."""
    if formato not in FORMATI:
        raise EsportazioneNonValida(
            f"Il formato «{formato}» non esiste.",
            f"Scegli fra {', '.join(f.upper() for f in FORMATI)}.",
        )
    if formato == "psd":
        return psd_a_livelli(livelli or [("Render", render)])
    immagine = _rgb(render)
    uscita = io.BytesIO()
    if formato == "jpg":
        immagine.save(uscita, "JPEG", quality=config.ESPORTA_QUALITA_JPEG, subsampling=0, optimize=True)
    else:
        immagine.save(uscita, "PNG", optimize=True)
    return uscita.getvalue()


# --- PSD ------------------------------------------------------------------------


def _nome_pascal(nome: str) -> bytes:
    """Il nome del livello in byte Mac Roman, con la lunghezza davanti, a multipli di 4."""
    grezzo = nome.encode("mac_roman", errors="replace")[:255]  # numero-non-configurabile: limite del formato
    dati = bytes([len(grezzo)]) + grezzo
    return dati + b"\0" * (-len(dati) % 4)  # numero-non-configurabile: formato PSD (Adobe, specifica del file)


def _nome_unicode(nome: str) -> bytes:
    """Il blocco «luni»: il nome vero, con accenti e «·», per Photoshop."""
    testo = nome.encode("utf-16-be")
    corpo = struct.pack(">I", len(nome)) + testo
    corpo += b"\0" * (-len(corpo) % 4)  # numero-non-configurabile: formato PSD (Adobe, specifica del file)
    return b"8BIMluni" + struct.pack(">I", len(corpo)) + corpo


def _canali(immagine: Image.Image) -> list[tuple[int, bytes]]:
    """(id, byte) di ogni canale: R, G, B e la trasparenza (-1, piena).

    L'ordine e' quello che il formato permette e che Pillow legge giusto:
    Pillow abbina i dati ai canali nell'ordine R, G, B, A, qualunque id dica
    il file.
    """
    r, g, b = immagine.split()
    pieno = b"\xff" * (immagine.width * immagine.height)
    return [(0, r.tobytes()), (1, g.tobytes()), (2, b.tobytes()), (-1, pieno)]


def psd_a_livelli(livelli: list[tuple[str, bytes]]) -> bytes:
    """Un PSD RGB a 8 bit con un livello per voce, dal basso in alto; l'ultima voce da' la grandezza."""
    if not livelli:
        raise EsportazioneNonValida("Un PSD senza livelli non ha niente dentro.", "Scegli un render da esportare.")
    immagini = [(nome, _rgb(dati)) for nome, dati in livelli]
    larghezza, altezza = immagini[-1][1].size
    immagini = [
        (nome, im if im.size == (larghezza, altezza) else im.resize((larghezza, altezza), Image.LANCZOS))
        for nome, im in immagini
    ]

    record = io.BytesIO()
    dati_canali = io.BytesIO()
    for nome, immagine in immagini:
        canali = _canali(immagine)
        record.write(struct.pack(">iiiiH", 0, 0, altezza, larghezza, len(canali)))
        for identificativo, byte in canali:
            record.write(struct.pack(">hI", identificativo, 2 + len(byte)))
            dati_canali.write(struct.pack(">H", 0))  # 0 = non compresso
            dati_canali.write(byte)
        record.write(b"8BIMnorm")
        record.write(struct.pack(">BBBB", 255, 0, 0, 0))  # numero-non-configurabile: formato PSD; opacita' piena, ritaglio, visibile, riempitivo
        extra = struct.pack(">I", 0) + struct.pack(">I", 0) + _nome_pascal(nome) + _nome_unicode(nome)
        record.write(struct.pack(">I", len(extra)) + extra)

    info_livelli = struct.pack(">h", len(immagini)) + record.getvalue() + dati_canali.getvalue()
    info_livelli += b"\0" * (len(info_livelli) % 2)
    sezione_livelli = struct.pack(">I", len(info_livelli)) + info_livelli + struct.pack(">I", 0)

    composita = immagini[-1][1]
    uscita = io.BytesIO()
    uscita.write(b"8BPS" + struct.pack(">H", 1) + b"\0" * 6)  # numero-non-configurabile: formato PSD (Adobe, specifica del file)
    uscita.write(struct.pack(">HIIHH", 3, altezza, larghezza, 8, 3))  # numero-non-configurabile: formato PSD; 3 canali, 8 bit, RGB
    uscita.write(struct.pack(">I", 0))  # dati del modo colore
    uscita.write(struct.pack(">I", 0))  # risorse dell'immagine
    uscita.write(struct.pack(">I", len(sezione_livelli)) + sezione_livelli)
    uscita.write(struct.pack(">H", 0))  # immagine composita, non compressa
    for canale in composita.split():
        uscita.write(canale.tobytes())
    return uscita.getvalue()
