"""La web app: lo Studio nel browser (web/ponte.py) e la sua costruzione (scripts/scrivi_web.py).

Pyodide qui non c'e': il ponte si prova con CPython, che esegue lo stesso
codice. Quello che fa solo il browser (service worker, IDBFS, JSPI) non e'
coperto da questi test.
"""

from __future__ import annotations

import importlib.util
import io
import json
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from core import licenza
from web import ponte as modulo_ponte

RADICE = Path(__file__).resolve().parent.parent


def _png() -> bytes:
    dati = io.BytesIO()
    Image.new("RGB", (640, 480), (150, 160, 170)).save(dati, "PNG")
    return dati.getvalue()


@pytest.fixture
def ponte(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "casa"))
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.delenv("AIRENDER_LICENZA", raising=False)
    monkeypatch.delenv("AIRENDER_CANALE", raising=False)
    monkeypatch.delenv("AIRENDER_POSTAZIONE", raising=False)
    p = modulo_ponte.Ponte(tmp_path / "viste", postazione="browser-di-prova")
    yield p


def test_il_ponte_risponde_come_lo_studio_sul_pc(ponte):
    """Caso: la pagina chiede /studio/api/... e il ponte non toglie il prefisso."""
    stato, intestazioni, corpo = ponte.rispondi("GET", "/studio/api/catalogo", {})
    assert stato == 200
    assert intestazioni["Content-Type"].startswith("application/json")
    assert json.loads(corpo)["modelli"]


def test_una_vista_caricata_dal_browser_si_rilegge(ponte):
    """Caso: il caricamento passa per il ponte ma il file non si ritrova."""
    stato, _i, corpo = ponte.rispondi("POST", "/studio/api/viste", {"X-Airender": "1", "X-Nome-File": "prova.png"}, _png())
    assert stato == 200
    nome = json.loads(corpo)["nome"]
    stato, intestazioni, immagine = ponte.rispondi("GET", f"/studio/file/vista/{nome}", {})
    assert stato == 200 and intestazioni["Content-Type"] == "image/png"
    assert immagine == _png()


def test_post_senza_intestazione_dello_studio_e_rifiutato(ponte):
    """Caso: la difesa dello Studio (X-Airender) sparisce nel browser."""
    stato, _i, _c = ponte.rispondi("POST", "/studio/api/viste", {}, _png())
    assert stato == 403


def test_apri_cartella_nel_browser_lo_dice(ponte):
    """Caso: «Apri cartella» prova a lanciare un esplora file che nel browser non c'e'."""
    stato, _i, corpo = ponte.rispondi("POST", "/studio/api/apri-cartella", {"X-Airender": "1"}, b'{"quale": "render"}')
    assert stato == 400
    assert "browser" in json.loads(corpo)["errore"]["fatto"]


def test_la_web_app_si_presenta_come_web_e_col_suo_browser(ponte):
    """Caso: il server conta il browser come la macchina di chi ha installato il plugin."""
    intestazioni = licenza.intestazioni("AIR-0000-0000-0000-0000")
    assert intestazioni[licenza.INTESTAZIONE_CANALE] == "web"
    assert intestazioni[licenza.INTESTAZIONE_POSTAZIONE] == licenza.postazione()
    assert len(licenza.postazione()) == 32


def test_senza_variabili_il_plugin_resta_plugin(monkeypatch):
    """Caso: le variabili della web app cambiano il plugin di Allplan."""
    monkeypatch.delenv("AIRENDER_CANALE", raising=False)
    monkeypatch.delenv("AIRENDER_POSTAZIONE", raising=False)
    intestazioni = licenza.intestazioni("AIR-0000-0000-0000-0000")
    assert intestazioni[licenza.INTESTAZIONE_CANALE] == "plugin"


def test_la_rete_del_browser_si_comporta_come_urllib(monkeypatch):
    """Caso: un 402 del server arriva al motore come risposta invece che come HTTPError."""
    originale = urllib.request.urlopen
    chiamate = []

    def chiama(url, metodo, intestazioni, corpo):
        chiamate.append((url, metodo, intestazioni, corpo))
        if url.endswith("/rotto"):
            raise OSError("rete giu'")
        if url.endswith("/saldo-finito"):
            return 402, {"content-type": "application/json"}, b'{"error": {}}'
        return 200, {"content-type": "application/json"}, b'{"ok": true}'

    try:
        modulo_ponte.installa_rete(chiama)
        richiesta = urllib.request.Request("https://s.prova/v2", data=b"{}", method="POST", headers={"X-A": "1"})
        with urllib.request.urlopen(richiesta, timeout=5) as risposta:
            assert risposta.status == 200 and risposta.read() == b'{"ok": true}'
            assert risposta.headers["content-type"] == "application/json"
        assert chiamate[0][1] == "POST" and chiamate[0][3] == b"{}"
        with pytest.raises(urllib.error.HTTPError) as errore:
            urllib.request.urlopen("https://s.prova/saldo-finito")
        assert errore.value.code == 402 and errore.value.read() == b'{"error": {}}'
        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen("https://s.prova/rotto")
    finally:
        monkeypatch.setattr(urllib.request, "urlopen", originale)


def _costruttore():
    spec = importlib.util.spec_from_file_location("scrivi_web", RADICE / "scripts" / "scrivi_web.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_la_web_app_costruita_non_chiede_niente_fuori_da_studio(tmp_path):
    """Caso: uno /api/ dello Studio resta senza prefisso e finisce sul server di vendita."""
    costruttore = _costruttore()
    costruttore.costruisci(tmp_path)
    script = (tmp_path / "pagine" / "studio.js").read_text(encoding="utf-8")
    for strada in ("/api/", "/file/"):
        for virgolette in ('"', "'", "`"):
            assert virgolette + strada not in script, f"{virgolette}{strada} senza /studio davanti"
    pagina = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert costruttore.SEGNAPOSTO not in pagina
    assert 'id="principale"' in pagina and "studio.js" not in pagina.split('<template id="corpo-studio">')[1].split("</template>")[0]
    with zipfile.ZipFile(tmp_path / "motore.zip") as archivio:
        nomi = set(archivio.namelist())
    assert {"core/studio/servizio.py", "core/coda.py", "web/ponte.py", "core/provider/workflow/tieni-geometria.json"} <= nomi
    assert not any("__pycache__" in n or n.startswith("core/studio/pagine/") for n in nomi)
