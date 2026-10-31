"""Costruisce e installa AIRENDER per Allplan 2027.

    python allplan/v2027/pacchetto.py              # costruisce dist/AIRENDER-2027.allep
    python allplan/v2027/pacchetto.py --installa   # e copia tutto nella Usr della 2027
    python allplan/v2027/pacchetto.py --installa --usr "D:\\...\\Usr\\Local"

Il pacchetto e' il formato plugin della 2027 (.allep): uno zip con
Library/, PythonPartsScripts/, PythonPartsActionbar/, install-config.yml e
requirements.in, come quello che il PythonParts SDK 3.0.0 di Allplan GmbH
costruisce nella sua release (.github/workflows/release.yml). Installato da
Allplan, mette il pulsante AIRENDER nell'Actionbar/Toolscape.

`--installa` e' la strada sicura, gia' provata con la 2026: copia gli stessi
file, nelle stesse cartelle, nella Usr. AIRENDER si apre allora da
Library › Privato › AIRENDER. Toglie anche i file delle prove vecchie
(AIRENDER prova, AIRENDER sonda), che nella 2027 non servono.

Nessun import di Allplan: gira con un Python qualunque e si prova con pytest.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

QUI = Path(__file__).resolve().parent
RADICE = QUI.parents[1]
PACCHETTO = QUI / "pacchetto"
ANNO = "2027"
NOME = f"AIRENDER-{ANNO}"

SVILUPPATORE = "riccardo_silingardi"
PLUGIN = "airender"
CARTELLA_SCRIPT = Path("PythonPartsScripts") / SVILUPPATORE / PLUGIN

# I file che la palette importa e che vivono fuori dalla cartella della
# versione: si copiano accanto all'adattatore, come faceva installa.ps1.
FILE_COMUNI = ("ponte.py", "telecomando.py", "sonda_palette.py")
# Le voci in cima all'.allep, nell'ordine del workflow del PythonParts SDK.
VOCI_ALLEP = ("Library", "PythonPartsScripts", "PythonPartsActionbar",
              "install-config.yml", "requirements.in")
# Solo nel pacchetto: nella Usr non servono, li legge l'installazione di Allplan.
SOLO_NEL_PACCHETTO = ("install-config.yml", "requirements.in")

# Quello che le installazioni della 2026 (allplan/v2026/installa.ps1) hanno
# lasciato e che nella 2027 confonde: la cartella script vecchia e le palette
# di prova. La cartella delle viste (Usr\AIRENDER) non si tocca mai.
VECCHI_SCRIPT = Path("PythonPartsScripts") / "airender"
VECCHI_NELLA_LIBRERIA = ("AirenderProva.pyp", "AirenderSonda.pyp", "sonda_*.png")


# Coda e Studio girano staccati da Allplan con la cartella dello script come
# cartella di lavoro: finche' sono vivi Windows non la lascia cancellare
# (WinError 32, visto il 2026-10-31). Si fermano prima di copiare; ripartono
# da soli al primo Genera o Apri nello Studio.
FERMA_PROCESSI = (
    "Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
    "Where-Object { $_.CommandLine -match 'core\\.(studio|coda)' } | "
    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force; $_.ProcessId }"
)


def ferma_coda_e_studio(lancia=subprocess.run, sistema: str = os.name) -> list[str]:
    """Ferma coda e Studio di AIRENDER su Windows. Restituisce i PID fermati."""
    if sistema != "nt":
        return []
    try:
        esito = lancia(["powershell", "-NoProfile", "-Command", FERMA_PROCESSI],
                       capture_output=True, text=True, check=False)
    except OSError:
        return []
    return [riga.strip() for riga in (esito.stdout or "").splitlines() if riga.strip()]


def _ignora(_cartella: str, nomi: list[str]) -> list[str]:
    return [n for n in nomi if n == "__pycache__" or n.endswith((".pyc", ".pyo"))]


def costruisci(uscita: Path) -> Path:
    """Scrive in `uscita/AIRENDER-2027/` l'albero completo del plugin e lo restituisce."""
    albero = uscita / NOME
    if albero.exists():
        shutil.rmtree(albero)
    shutil.copytree(PACCHETTO, albero, ignore=_ignora)
    script = albero / CARTELLA_SCRIPT
    for nome in FILE_COMUNI:
        shutil.copy2(RADICE / "allplan" / "comune" / nome, script / nome)
    shutil.copytree(RADICE / "core", script / "core", ignore=_ignora)
    return albero


def comprimi(albero: Path, allep: Path) -> Path:
    """L'.allep: uno zip con le cinque voci in cima, percorsi con la barra normale."""
    allep.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(allep, "w", zipfile.ZIP_DEFLATED) as archivio:
        for voce in VOCI_ALLEP:
            percorso = albero / voce
            file = [percorso] if percorso.is_file() else sorted(p for p in percorso.rglob("*") if p.is_file())
            for singolo in file:
                archivio.write(singolo, singolo.relative_to(albero).as_posix())
    return allep


def candidati_usr(casa: Path, anno: str = ANNO) -> list[Path]:
    """Dove di solito sta la Usr di Allplan: Documenti (anche sotto OneDrive) o C:\\Data\\Allplan."""
    documenti = [casa / "Documents", casa / "Documenti",
                 casa / "OneDrive" / "Documents", casa / "OneDrive" / "Documenti"]
    candidati = [d / "Nemetschek" / "Allplan" / anno / "Usr" / "Local" for d in documenti]
    candidati.append(Path("C:/Data/Allplan") / f"Allplan {anno}" / "Usr" / "Local")
    return candidati


def trova_usr(casa: Path, anno: str = ANNO) -> Path | None:
    esistenti = [c for c in candidati_usr(casa, anno) if c.is_dir()]
    # Prima quella dove l'SDK ha gia' installato pacchetti: e' di sicuro quella giusta.
    for candidato in esistenti:
        if (candidato / "PythonParts-site-packages").is_dir():
            return candidato
    return esistenti[0] if esistenti else None


@dataclass
class Esito:
    usr: Path
    copiati: list[str] = field(default_factory=list)
    tolti: list[str] = field(default_factory=list)
    avvisi: list[str] = field(default_factory=list)


def installa(albero: Path, usr: Path, ferma=ferma_coda_e_studio) -> Esito:
    """Copia l'albero del plugin nella Usr e toglie le prove della 2026."""
    esito = Esito(usr=usr)
    fermati = ferma()
    if fermati:
        esito.avvisi.append(f"Ho fermato coda e Studio di AIRENDER (processi {', '.join(fermati)}): "
                            "ripartono da soli al prossimo Genera.")
    vecchi = usr / VECCHI_SCRIPT
    if vecchi.is_dir():
        shutil.rmtree(vecchi)
        esito.tolti.append(str(vecchi))
    libreria = usr / "Library" / "AIRENDER"
    for schema in VECCHI_NELLA_LIBRERIA:
        for vecchio in sorted(libreria.glob(schema)) if libreria.is_dir() else []:
            vecchio.unlink()
            esito.tolti.append(str(vecchio))

    script = usr / CARTELLA_SCRIPT
    if script.is_dir():
        try:
            shutil.rmtree(script)  # niente file vecchi del motore che restano indietro
        except PermissionError as errore:
            raise SystemExit(
                f"Non riesco a togliere la versione vecchia in {script}: {errore}.\n"
                "Cosa fare: chiudi Allplan e la finestra dello Studio, poi rilancia il comando.") from None
    for voce in VOCI_ALLEP:
        if voce in SOLO_NEL_PACCHETTO:
            continue
        shutil.copytree(albero / voce, usr / voce, dirs_exist_ok=True)
        esito.copiati.append(str(usr / voce))

    if not (usr / "PythonParts-site-packages" / "PIL").is_dir():
        esito.avvisi.append(
            "Non vedo Pillow per la 2027 (manca PythonParts-site-packages\\PIL nella Usr). "
            "In Allplan 2027: PythonParts SDK › Install Python Package › pillow, destinazione USR, "
            "poi riavvia Allplan.")
    return esito


def _stampa_esito(esito: Esito) -> None:
    print(f"Installato nella Usr: {esito.usr}")
    for tolto in esito.tolti:
        print(f"  tolto (prova vecchia): {tolto}")
    for avviso in esito.avvisi:
        print(f"ATTENZIONE: {avviso}")
    print("Riavvia Allplan 2027, poi: Library › Privato › AIRENDER › AIRENDER.")


def main(argomenti: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Costruisce (e installa) AIRENDER per Allplan 2027.")
    parser.add_argument("--uscita", type=Path, default=RADICE / "dist",
                        help="dove scrivere il pacchetto (predefinita: dist/ nel repository)")
    parser.add_argument("--installa", action="store_true",
                        help="copia AIRENDER nella cartella Usr di Allplan 2027")
    parser.add_argument("--usr", type=Path,
                        help="la cartella Usr\\Local di Allplan 2027, se non e' trovata da sola")
    scelte = parser.parse_args(argomenti)

    albero = costruisci(scelte.uscita)
    allep = comprimi(albero, scelte.uscita / f"{NOME}.allep")
    print(f"Pacchetto plugin: {allep}")
    if not scelte.installa:
        return 0

    usr = scelte.usr or trova_usr(Path(os.path.expanduser("~")))
    if usr is None or not usr.is_dir():
        print("Non trovo la cartella Usr di Allplan 2027.")
        print("Cosa fare: in Allplan 2027, Menu › Servizi › Esplora file › «Miei documenti CAD» "
              "(o la cartella che contiene PythonParts-site-packages), copia il percorso e rilancia con "
              "--usr \"<quel percorso>\".")
        for candidato in candidati_usr(Path(os.path.expanduser("~"))):
            print(f"  cercata: {candidato}")
        return 1
    _stampa_esito(installa(albero, usr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
