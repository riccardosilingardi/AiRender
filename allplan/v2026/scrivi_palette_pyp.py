"""Scrive Library/AIRENDER/AirenderPalette.pyp, la palette v1 per Allplan 2026.

    python allplan/v2026/scrivi_palette_pyp.py

Gli elenchi a scelta (preset, ora, cielo, intorno, verde, persone, formato, modello) vengono da
`allplan/comune/telecomando.voci_palette()`, cioe' da core/blocchi.py e dai
modelli dello Studio: la palette chiama ogni cosa come lo Studio. Dopo un
cambio dei blocchi si rilancia questo script; un test (tests/test_palette_pyp.py)
fallisce finche' il .pyp nel repository non e' aggiornato.

Lo schema della palette e' della versione di Allplan (regola 2 di CLAUDE.md).
La 2027 usa gli stessi campi: allplan/v2027/scrivi_palette_pyp.py chiama
pyp() con il suo percorso dello script.
Nessun import di Allplan: gira con un Python qualunque.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

QUI = Path(__file__).resolve().parent
RADICE = QUI.parents[1]
for percorso in (RADICE, RADICE / "allplan" / "comune"):
    if str(percorso) not in sys.path:
        sys.path.insert(0, str(percorso))

import telecomando  # noqa: E402  pylint: disable=wrong-import-position

DESTINAZIONE = QUI / "Library" / "AIRENDER" / "AirenderPalette.pyp"
IMMAGINE_VUOTA = "palette_nessuna.png"

# Gli eventi dei pulsanti: AirenderPalette.py usa gli stessi numeri.
EVENTI = {
    "Cattura": 1001,
    "Genera": 1003,
    "Annulla": 1004,
    "Aggiorna": 1005,
    "ApriStudio": 1006,
    "ApriCartella": 1007,
    "VediTaglio": 1008,
}
# 1002 era «Prova a secco», tolta dalla palette il 2026-10-31: non si riusa,
# cosi' un .pyp vecchio rimasto in giro non fa partire un'altra azione.


def _parametro(nome: str, tipo: str, testo: str = "", valore: str | None = None, *,
               elenco: list[str] | None = None, visibile: str | None = None,
               attivo: str | None = None, evento: int | None = None,
               figli: list[str] | None = None, extra: str = "") -> str:
    righe = [f"<Name>{nome}</Name>"]
    if testo:
        righe.append(f"<Text>{escape(testo)}</Text>")
    if valore is not None:
        righe.append(f"<Value>{escape(valore)}</Value>")
    if elenco is not None:
        righe.append(f"<ValueList>{escape('|'.join(elenco))}</ValueList>")
    if evento is not None:
        righe.append(f"<EventId>{evento}</EventId>")
    if extra:
        righe.append(extra)
    righe.append(f"<ValueType>{tipo}</ValueType>")
    if visibile is not None:
        righe.append(f"<Visible>{visibile}</Visible>")
    if attivo is not None:
        righe.append(f"<Enable>{attivo}</Enable>")
    if figli:
        righe.append("<Parameters>\n" + "\n".join(figli) + "\n</Parameters>")
    return "<Parameter>\n" + "\n".join(righe) + "\n</Parameter>"


def _sola_lettura(nome: str, testo: str, visibile: str | None = None) -> str:
    return _parametro(nome, "String", testo, "", attivo="False", visibile=visibile)


def _nascosto(nome: str, tipo: str, valore: str) -> str:
    return _parametro(nome, tipo, "", valore, visibile="False")


def _pulsante(nome: str, testo: str, visibile: str | None = None) -> str:
    return _parametro(nome, "Button", testo, evento=EVENTI[nome], visibile=visibile)


def _riga(nome: str, testo: str, *pulsanti: str) -> str:
    return _parametro(nome, "Row", testo, figli=list(pulsanti))


def _scelta(nome: str, testo: str, visibile: str | None = None) -> str:
    voci = [n for _i, n in telecomando.voci_palette()[nome]]
    return _parametro(nome, "StringComboBox", testo, voci[0], elenco=voci, visibile=visibile)


def _radio(nome: str, testo: str, voci: list[str]) -> str:
    figli = [_parametro(f"{nome}{i}", "RadioButton", v, str(i)) for i, v in enumerate(voci)]
    return _parametro(nome, "RadioButtonGroup", testo, "0", figli=figli)


def _immagine(nome: str) -> str:
    return _parametro(nome, "Picture", "", IMMAGINE_VUOTA, visibile="ImmaginiDaScript == 1",
                      extra="<Orientation>Middle</Orientation>")


def _espansore(nome: str, testo: str, *figli: str) -> str:
    return _parametro(nome, "Expander", testo, figli=list(figli))


# Chi chiama pyp() senza argomenti ottiene il .pyp della 2026, come prima.
# La 2027 (allplan/v2027/scrivi_palette_pyp.py) passa il suo anno dello
# schema, il percorso dello script nel pacchetto plugin e il suo nome.
SCRIPT_2026 = "airender\\AirenderPalette.py"


def pyp(anno_schema: str = "2026", script: str = SCRIPT_2026,
        generato_da: str = "allplan/v2026/scrivi_palette_pyp.py") -> str:
    esterno, interno = "Interno == 0", "Interno == 1"
    parametri = [
        _nascosto("ImmaginiDaScript", "Integer", "0"),
        _nascosto("InCorso", "Integer", "0"),
        _nascosto("LavoroAttivo", "String", ""),
        _nascosto("UltimaVista", "String", ""),
        _nascosto("UltimoRender", "String", ""),
        _espansore(
            "Sezione1", "1 · Vista",
            _sola_lettura("VistaNome", "Vista"),
            _immagine("VistaImmagine"),
            _sola_lettura("VistaEsito", "Esito"),
            _riga("RigaCattura", "Finestra attiva", _pulsante("Cattura", "Cattura vista")),
            _radio("Dimensione", "Dimensione", ["Come la finestra", "1920 × 1080", "3840 × 2160"]),
            _scelta("Formato", "Formato"),
            _riga("RigaTaglio", "Taglio", _pulsante("VediTaglio", "Vedi cosa taglia")),
        ),
        _espansore(
            "Sezione2", "2 · Stile",
            _sola_lettura("Resa", "Resa"),
            _radio("Interno", "Vista", ["Esterno", "Interno"]),
            _scelta("PresetEsterno", "Preset", esterno),
            _scelta("PresetInterno", "Preset", interno),
            _scelta("LuceEsterno", "Ora", esterno),
            _scelta("LuceInterno", "Luce", interno),
            _scelta("Cielo", "Cielo", esterno),
            _scelta("Intorno", "Intorno", esterno),
            _scelta("Verde", "Verde, alberi", esterno),
            _scelta("Persone", "Persone"),
            _parametro("Materiali", "String", "Materiali", ""),
            _scelta("Modello", "Modello"),
        ),
        _espansore(
            "Sezione3", "3 · Invio",
            _sola_lettura("Destinazione", "La vista va a"),
            _sola_lettura("NotaInvio", "Ripiego"),
            _sola_lettura("Costo", "Costo"),
            _sola_lettura("Stato", "Stato"),
            _riga("RigaInvio", "Motore",
                  _pulsante("Genera", "Genera render", "InCorso == 0"),
                  _pulsante("Annulla", "Annulla", "InCorso == 1")),
            _riga("RigaAggiorna", "Stato del lavoro", _pulsante("Aggiorna", "Aggiorna")),
        ),
        _espansore(
            "Sezione4", "4 · Ultimo render",
            _sola_lettura("Ultimo", "Ultimo"),
            _immagine("UltimoImmagine"),
            _riga("RigaStudio", "Studio",
                  _pulsante("ApriStudio", "Apri nello Studio"),
                  _pulsante("ApriCartella", "Apri cartella")),
        ),
        _espansore(
            "Sezione5", "In arrivo",
            *[_parametro(f"InArrivo{i}", "Text", f"{voce}: in arrivo, non ancora attivo")
              for i, voce in enumerate(("Cambia materiale", "Annota aree", "Livelli", "Video"))],
        ),
        _parametro("Cartella", "String", "Cartella delle viste (vuota = Usr\\AIRENDER\\viste)", ""),
    ]
    corpo = "\n".join(parametri)
    return (
        "<?xml version='1.0' encoding='UTF-8'?>\n"
        f"<!-- Generato da {generato_da}: non modificare a mano. -->\n"
        '<Element xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:noNamespaceSchemaLocation="https://pythonparts.allplan.com/{anno_schema}/schemas/PythonPart.xsd">\n'
        f"<Script>\n<Name>{escape(script)}</Name>\n<Title>AIRENDER</Title>\n"
        "<Version>1.0</Version>\n</Script>\n"
        "<Page>\n<Name>Pagina</Name>\n<Text>AIRENDER</Text>\n<Parameters>\n"
        f"{corpo}\n</Parameters>\n</Page>\n</Element>\n"
    )


def scrivi_immagine_vuota(cartella: Path) -> Path:
    """Il segnaposto delle due immagini: un rettangolo grigio chiaro, 16:9."""
    from PIL import Image  # solo qui: il resto dello script non ha bisogno di Pillow

    percorso = cartella / IMMAGINE_VUOTA
    Image.new("RGB", (160, 90), (240, 240, 240)).save(percorso, format="PNG")
    return percorso


if __name__ == "__main__":
    DESTINAZIONE.write_text(pyp(), encoding="utf-8")
    scrivi_immagine_vuota(DESTINAZIONE.parent)
    print(f"Scritto {DESTINAZIONE}")
