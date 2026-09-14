"""Le regole che tengono in piedi il progetto, controllate a ogni giro.

Non provano una funzione: provano che il motore sia rimasto quello che deve
essere. Sono le prime a rompersi quando qualcuno ha fretta.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from core import config

RADICE = Path(__file__).resolve().parent.parent
MOTORE = RADICE / "core"

# 0, 1 e 2 non sono soglie: sono indici, confini di lista, divisioni per due.
NUMERI_INNOCENTI = {0, 1, 2}
MARCATORE = "numero-non-configurabile"


def file_del_motore() -> list[Path]:
    return sorted(MOTORE.rglob("*.py"))


def test_il_motore_non_sa_che_allplan_esiste():
    """Caso: un import di comodo, e il motore non gira piu' fuori dal CAD."""
    colpevoli = []
    for percorso in file_del_motore():
        albero = ast.parse(percorso.read_text(encoding="utf-8"))
        for nodo in ast.walk(albero):
            if isinstance(nodo, ast.Import):
                nomi = [alias.name for alias in nodo.names]
            elif isinstance(nodo, ast.ImportFrom):
                nomi = [nodo.module or ""]
            else:
                continue
            if any(nome.startswith("NemAll_Python") for nome in nomi):
                colpevoli.append(f"{percorso.relative_to(RADICE)}:{nodo.lineno}")
    assert not colpevoli, f"il motore importa Allplan in: {colpevoli}"


def test_nessuna_soglia_vive_fuori_da_config():
    """Caso: lo stesso numero in due file, e la divergenza non se ne accorge nessuno."""
    cablati = []
    for percorso in file_del_motore():
        if percorso.name == "config.py":
            continue
        testo = percorso.read_text(encoding="utf-8")
        righe = testo.splitlines()
        for nodo in ast.walk(ast.parse(testo)):
            if not isinstance(nodo, ast.Constant):
                continue
            if isinstance(nodo.value, bool) or not isinstance(nodo.value, (int, float)):
                continue
            if nodo.value in NUMERI_INNOCENTI:
                continue
            if MARCATORE in righe[nodo.lineno - 1]:
                continue
            cablati.append(
                f"{percorso.relative_to(RADICE)}:{nodo.lineno} -> {nodo.value}"
            )
    assert not cablati, (
        "numeri cablati fuori da core/config.py: "
        + ", ".join(cablati)
        + f". Spostali in config.py, o spiegali in riga con '{MARCATORE}: <ragione>'."
    )


def test_ogni_costante_dice_come_e_nata_e_perche():
    """Caso: un numero senza provenienza finisce a schermo come se fosse misurato."""
    for nome, costante in config.REGISTRO.items():
        assert costante.origine in config.ORIGINI, nome
        assert len(costante.ragione) > 40, f"{nome} ha una ragione troppo corta"
        assert costante.nome == nome


def test_un_valore_scelto_non_si_puo_stampare_come_misurato():
    """Caso: la forza della struttura appare nella palette come un dato certo."""
    scelte = [c for c in config.REGISTRO.values() if c.origine == config.SCELTA]
    assert scelte
    for costante in scelte:
        assert "non ancora misurato" in costante.etichetta()


def test_una_costante_senza_ragione_non_entra_in_config():
    """Caso: si aggiunge una soglia di fretta, senza dire perche' vale cosi'."""
    with pytest.raises(ValueError):
        config.Costante(nome="X", valore=1, origine=config.SCELTA, ragione="   ")


def test_una_costante_con_un_origine_inventata_non_entra():
    """Caso: "ovvio" non e' una provenienza."""
    with pytest.raises(ValueError):
        config.Costante(nome="X", valore=1, origine="OVVIO", ragione="perche' si")


def test_nessuna_chiave_nel_repository():
    """Caso: una chiave finisce in un preset o in un file di esempio.

    La chiave e' del cliente e vive in una variabile d'ambiente. Qui dentro
    non ci sono nemmeno esempi che le somiglino.
    """
    # Il nome si compone a pezzi, altrimenti questo file inciampa su se stesso.
    marcatore = "MAGNIFIC" + "_API_KEY="
    sospetti = []
    for percorso in sorted(RADICE.rglob("*")):
        if not percorso.is_file() or ".git/" in str(percorso):
            continue
        if percorso.suffix not in (".py", ".md", ".json", ".txt", ".ini", ".example", ""):
            continue
        testo = percorso.read_text(encoding="utf-8", errors="ignore")
        for riga in testo.splitlines():
            nuda = riga.strip()
            if nuda.startswith("#") or marcatore not in nuda:
                continue
            valore = nuda.split(marcatore, 1)[1].strip().strip('"').strip("'")
            if valore:
                sospetti.append(f"{percorso.relative_to(RADICE)}: {nuda}")
    assert not sospetti, f"sembra esserci una chiave nel repository: {sospetti}"


def test_il_file_env_non_e_tracciato_da_git():
    """Caso: `cp .env.example .env`, poi `git add .` e la chiave e' pubblica."""
    ignorati = (RADICE / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env" in [riga.strip() for riga in ignorati]
