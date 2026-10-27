"""La sonda della palette, provata senza Allplan.

Quello che solo il PC di Riccardo puo' dire (immagini nella palette, Edge,
Allplan libero) resta fuori. Qui si prova che la sonda scelga gli interpreti
giusti, che il processo di prova parta, serva la pagina e dica di essere vivo.
"""

from __future__ import annotations

import http.client
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "allplan" / "comune"))

import sonda_palette as sonda  # noqa: E402  pylint: disable=wrong-import-position

FIGLIO = Path(__file__).resolve().parents[1] / "allplan" / "comune" / "sonda_figlio.py"


def test_allplan_exe_non_viene_mai_lanciato_come_python(tmp_path):
    """Caso: dentro Allplan sys.executable e' Allplan.exe; lanciarlo aprirebbe un secondo Allplan."""
    candidati = sonda.candidati_python([], r"C:\Programmi\Allplan\Prg\Allplan_2026.exe", lambda _n: None)
    assert candidati == []


def test_prima_il_python_di_allplan_poi_quello_di_sistema(tmp_path):
    (tmp_path / "python.exe").write_text("")
    trovati = {"py": r"C:\Windows\py.exe", "python": r"C:\Python311\python.exe"}
    candidati = sonda.candidati_python([str(tmp_path), str(tmp_path)], "Allplan.exe", trovati.get)
    assert [origine for origine, _ in candidati] == [
        f"Python di Allplan ({tmp_path})", "py di sistema", "python di sistema"]
    assert candidati[1][1] == [r"C:\Windows\py.exe", "-3"]


def test_il_python_di_sistema_parte_senza_le_variabili_di_allplan():
    """Caso: PYTHONHOME di Allplan fa fallire un Python di sistema all'avvio."""
    base = {"PYTHONHOME": r"C:\Allplan\Python", "PYTHONPATH": "x", "PATH": "p"}
    assert sonda.ambiente_per("py di sistema", base) == {"PATH": "p"}
    assert sonda.ambiente_per("Python di Allplan (C:\\x)", base) == base


def test_una_risposta_strana_resta_scritta_com_e():
    assert sonda.interpreta_identita("3.11.9|C:\\py\\python.exe|True\n") == {
        "letto": True, "versione": "3.11.9", "eseguibile": "C:\\py\\python.exe", "pillow": True}
    strana = sonda.interpreta_identita("Fatal Python error: init_fs_encoding")
    assert strana["letto"] is False
    assert "init_fs_encoding" in strana["uscita"]


def test_il_registro_aggiunge_senza_cancellare(tmp_path):
    orologio = iter([datetime(2026, 10, 27, 20, 0, 0), datetime(2026, 10, 27, 20, 0, 5)])
    registro = sonda.Registro(tmp_path / "sonda", adesso=lambda: next(orologio))
    assert "Ancora niente" in registro.leggi()
    registro.scrivi("1 immagine", "mostra B")
    registro.scrivi("3 python", "py di sistema")
    assert registro.leggi().splitlines() == [
        "[2026-10-27 20:00:00] 1 immagine · mostra B",
        "[2026-10-27 20:00:05] 3 python · py di sistema",
    ]


def test_un_processo_mai_partito_si_dice_chiaro(tmp_path):
    assert sonda.leggi_stato(tmp_path) is None
    assert "non ha scritto niente" in sonda.descrivi_stato(None, time.time())


def test_edge_si_cerca_nei_percorsi_soliti():
    ambiente = {"ProgramFiles(x86)": r"C:\Program Files (x86)"}
    percorsi = sonda.percorsi_edge(ambiente, lambda _n: None)
    assert percorsi == [str(Path(r"C:\Program Files (x86)") / "Microsoft" / "Edge" / "Application" / "msedge.exe")]
    assert sonda.comando_edge("msedge", "http://127.0.0.1:5000/")[1] == "--app=http://127.0.0.1:5000/"


def test_il_processo_di_prova_parte_staccato_serve_la_pagina_e_batte(tmp_path):
    """Il percorso dello Studio vero, in piccolo: processo a parte, pagina locale, battito."""
    comando = sonda.comando_figlio([sys.executable], FIGLIO, tmp_path, secondi=4)
    processo = subprocess.Popen(comando, **sonda.opzioni_staccato())  # pylint: disable=consider-using-with
    try:
        stato = None
        scadenza = time.time() + 10
        while time.time() < scadenza:
            stato = sonda.leggi_stato(tmp_path)
            if stato and stato.get("battiti", 0) >= 2:
                break
            time.sleep(0.2)
        assert stato and stato["battiti"] >= 2, "il processo di prova non ha battuto"
        assert stato["pid"] == processo.pid
        assert sonda.descrivi_stato(stato, time.time()).startswith("vivo")

        # Solo localhost: la regola "niente rete" dei test riguarda l'uscita verso fuori.
        connessione = http.client.HTTPConnection("127.0.0.1", stato["porta"], timeout=5)
        connessione.request("GET", "/")
        risposta = connessione.getresponse()
        assert risposta.status == 200
        assert "AIRENDER" in risposta.read().decode("utf-8")
        connessione.close()

        processo.wait(timeout=15)
        finale = sonda.leggi_stato(tmp_path)
        assert finale["finito"] is True
        assert sonda.descrivi_stato(finale, time.time()).startswith("fermo")
    finally:
        if processo.poll() is None:
            processo.kill()
