"""Costruisce la web app dello Studio in server/public/studio/.

    python scripts/scrivi_web.py

Lo lancia Netlify a ogni deploy (server/netlify.toml, comando di build): la
cartella costruita non sta nel repository, cosi' non diverge mai dallo
Studio sul PC. Dentro:

- index.html, avvio.js, motore.js, sw.js da web/pagine/ (l'ingresso, il
  motore nel browser, il service worker);
- pagine/studio.css e pagine/studio.js dello Studio sul PC, con gli indirizzi
  /api/ e /file/ spostati sotto /studio/ (sul sito /api/ e' del server di
  vendita);
- motore.zip: core/ e web/ponte.py, il Python che gira nel browser.

Solo libreria standard e niente f-string annidate: gira col Python
dell'immagine di build di Netlify, qualunque versione 3 sia.
"""

from __future__ import annotations

import re
import shutil
import sys
import zipfile
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
PAGINE_STUDIO = RADICE / "core" / "studio" / "pagine"
PAGINE_WEB = RADICE / "web" / "pagine"
USCITA = RADICE / "server" / "public" / "studio"
PREFISSO = "/studio"
SEGNAPOSTO = "<!-- CORPO_STUDIO -->"
# Le strade dello Studio servite dal motore nel browser (web/pagine/sw.js).
STRADE = ("/api/", "/file/", "/pagine/")


def sposta_indirizzi(testo: str) -> str:
    """"/api/..., `/file/... e simili diventano "/studio/api/... nello script e nell'HTML."""
    for strada in STRADE:
        for virgolette in ('"', "'", "`"):
            testo = testo.replace(virgolette + strada, virgolette + PREFISSO + strada)
    return testo


def corpo_studio(html: str) -> str:
    """Il contenuto di <body> dello Studio sul PC, senza lo script (lo carica avvio.js)."""
    trovato = re.search(r"<body>(.*)</body>", html, re.S)
    if not trovato:
        raise SystemExit("Non trovo <body> in core/studio/pagine/index.html")
    corpo = re.sub(r'<script src="[^"]*studio\.js"></script>', "", trovato.group(1))
    return sposta_indirizzi(corpo).strip()


def file_del_motore() -> list[tuple[Path, str]]:
    """Cosa va in motore.zip: il pacchetto core e il ponte, senza cache e senza le pagine."""
    file = []
    for percorso in sorted((RADICE / "core").rglob("*")):
        if not percorso.is_file() or "__pycache__" in percorso.parts or percorso.suffix == ".pyc":
            continue
        if PAGINE_STUDIO in percorso.parents:
            continue  # le pagine le serve Netlify, non Python
        file.append((percorso, percorso.relative_to(RADICE).as_posix()))
    for nome in ("__init__.py", "ponte.py"):
        file.append((RADICE / "web" / nome, "web/" + nome))
    return file


def costruisci(uscita: Path = USCITA) -> list[Path]:
    if uscita.exists():
        shutil.rmtree(uscita)
    (uscita / "pagine").mkdir(parents=True)
    scritti = []

    ingresso = (PAGINE_WEB / "index.html").read_text(encoding="utf-8")
    if SEGNAPOSTO not in ingresso:
        raise SystemExit("web/pagine/index.html non ha il segnaposto " + SEGNAPOSTO)
    corpo = corpo_studio((PAGINE_STUDIO / "index.html").read_text(encoding="utf-8"))
    scritti.append(uscita / "index.html")
    scritti[-1].write_text(ingresso.replace(SEGNAPOSTO, corpo), encoding="utf-8")

    for nome in ("avvio.js", "motore.js", "sw.js"):
        scritti.append(uscita / nome)
        shutil.copyfile(PAGINE_WEB / nome, scritti[-1])

    scritti.append(uscita / "pagine" / "studio.css")
    shutil.copyfile(PAGINE_STUDIO / "studio.css", scritti[-1])
    scritti.append(uscita / "pagine" / "studio.js")
    scritti[-1].write_text(sposta_indirizzi((PAGINE_STUDIO / "studio.js").read_text(encoding="utf-8")),
                           encoding="utf-8")

    scritti.append(uscita / "motore.zip")
    with zipfile.ZipFile(scritti[-1], "w", zipfile.ZIP_DEFLATED) as archivio:
        for percorso, nome in file_del_motore():
            archivio.write(percorso, nome)
    return scritti


def main() -> int:
    for percorso in costruisci():
        print("Scritto " + percorso.relative_to(RADICE).as_posix())
    return 0


if __name__ == "__main__":
    sys.exit(main())
