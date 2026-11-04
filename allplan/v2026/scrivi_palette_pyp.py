"""Scrive Library/AIRENDER/AirenderPalette.pyp, la palette v1 per Allplan 2026.

    python allplan/v2026/scrivi_palette_pyp.py

Dal 2026-11-04 la palette cattura e basta: vista, dimensione, formato,
Apri nello Studio. L'elenco dei formati viene da
`allplan/comune/telecomando.voci_palette()`, cioe' dai rapporti che il modello
accetta. Dopo un cambio si rilancia questo script; un test
(tests/test_palette_pyp.py) fallisce finche' il .pyp nel repository non e'
aggiornato.

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
    "ApriStudio": 1006,
    "ApriCartella": 1007,
    "VediTaglio": 1008,
}
# Allplan non mette un pulsante «indietro» nella palette di un PythonPart:
# si chiude con Esc, che fa tornare la Library (on_cancel_function
# nell'adattatore). Lo si scrive in cima, perche' non e' ovvio.
TESTO_CHIUDI = "Per tornare alla Library premi Esc. I render in corso continuano."
TESTO_STUDIO = "Stile, render, ritocchi e video si fanno nello Studio."
# 1002 era «Prova a secco», tolta dalla palette il 2026-10-31; 1003 Genera,
# 1004 Annulla e 1005 Aggiorna, tolti il 2026-11-04 con la sezione Stile.
# Non si riusano, cosi' un .pyp vecchio rimasto in giro non fa partire
# un'altra azione.


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
    # Dal 2026-11-04 la palette serve solo a catturare (scelta di Riccardo):
    # stile, invio, render, ritocchi e video si fanno nello Studio.
    parametri = [
        _nascosto("ImmaginiDaScript", "Integer", "0"),
        _nascosto("UltimaVista", "String", ""),
        _parametro("Chiudi", "Text", TESTO_CHIUDI),
        _espansore(
            "Sezione1", "Vista",
            _sola_lettura("VistaNome", "Vista"),
            _immagine("VistaImmagine"),
            _sola_lettura("VistaEsito", "Esito"),
            _riga("RigaCattura", "Finestra attiva", _pulsante("Cattura", "Cattura vista")),
            _radio("Dimensione", "Dimensione", ["Come la finestra", "1920 × 1080", "3840 × 2160"]),
            _scelta("Formato", "Formato"),
            _riga("RigaTaglio", "Taglio", _pulsante("VediTaglio", "Vedi cosa ha tagliato")),
        ),
        _espansore(
            "Sezione2", "Studio",
            _parametro("NelloStudio", "Text", TESTO_STUDIO),
            _riga("RigaStudio", "Studio",
                  _pulsante("ApriStudio", "Apri nello Studio"),
                  _pulsante("ApriCartella", "Apri cartella")),
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
