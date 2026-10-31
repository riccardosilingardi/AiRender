"""Il banco di prova dei blocchi di stile: un piano di confronti sulla stessa vista.

    python scripts/prova_blocchi.py --immagine vista.png --piano qualita --prova-a-secco
    python scripts/prova_blocchi.py --immagine vista.png --piano preset
    python scripts/prova_blocchi.py --immagine render.png --piano aree --aree aree.json
    python scripts/prova_blocchi.py --giudica C:\\AIRENDER\\vista-banco-preset-20261029-101500

I piani: qualita (2 invii), look (9), preset (8 esterni o 6 interni), catena
(4), aree (2), fedelta (3: rigida, bilanciata, libera). Per il piano aree l'immagine e' quella da ritoccare, di solito
un render; le aree predefinite sono un rettangolo a sinistra e una selezione
libera in basso a destra, con due note: --aree ne legge altre da un file JSON,
[{"forma": "rettangolo" | "libera", "punti": [[x, y], ...], "nota": "..."}]
con x e y fra 0 e 1.

Ogni invio e' a pagamento. Prima di partire il banco dice quanti invii sono,
dove vanno e quanto costano, e chiede conferma. Con --prova-a-secco prepara
la cartella, i prompt e la pagina, e non manda niente.

Alla fine apri banco.html nella cartella del banco. Per salvare i giudizi
accanto alla pagina, aprila con --giudica <cartella>.
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RADICE))

from core import banco, blocchi, immagine as modulo_immagine  # noqa: E402
from core.aree import AreaNonValida  # noqa: E402
from core.cli import USCITA_OK, USCITA_PROVIDER, USCITA_RIFIUTO  # noqa: E402
from core.errori import ErroreAirender, ImmagineNonIdonea  # noqa: E402
from core.idoneita import valuta  # noqa: E402
from core.provider.comfy import ProviderComfy  # noqa: E402
from core.studio.servizio import MODELLI, testo_costo  # noqa: E402

# Due aree di esempio per il piano aree: un rettangolo sulla meta' sinistra
# della facciata e una selezione libera in basso a destra. Sono un punto di
# partenza: su una vista vera conviene passarne di proprie con --aree.
AREE_PREDEFINITE = (
    banco.Area("rettangolo", ((0.18, 0.30), (0.42, 0.62)), "infissi in legno scuro"),
    banco.Area("libera", ((0.62, 0.74), (0.74, 0.68), (0.88, 0.71), (0.90, 0.86), (0.75, 0.92), (0.63, 0.86)),
               "una panchina in pietra chiara"),
)


def costruisci_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/prova_blocchi.py",
        description="Confronti sulla stessa vista che cambiano una cosa sola.",
    )
    parser.add_argument("--immagine", help="la vista salvata da Allplan (per aree: l'immagine da ritoccare)")
    parser.add_argument("--piano", choices=banco.PIANI, help="quale confronto")
    parser.add_argument("--scena", choices=blocchi.SCENE, default=blocchi.ESTERNO,
                        help="esterno o interno: quali preset si usano")
    parser.add_argument("--modello", default=MODELLI[0].identificativo, help="ID del Router")
    parser.add_argument("--aree", help="file JSON con le aree del piano aree")
    parser.add_argument("--uscita", help="dove creare la cartella del banco (predefinita: quella della vista)")
    parser.add_argument("--prova-a-secco", action="store_true", dest="secco",
                        help="prepara tutto e non invia niente")
    parser.add_argument("--giudica", metavar="CARTELLA",
                        help="apre la pagina di un banco gia' fatto e salva i giudizi accanto")
    return parser


def leggi_aree(percorso: str | None) -> tuple[banco.Area, ...]:
    if not percorso:
        return AREE_PREDEFINITE
    try:
        dati = json.loads(Path(percorso).read_text(encoding="utf-8"))
    except (OSError, ValueError) as errore:
        raise banco.PianoNonValido(
            f"Il file delle aree {percorso} non si legge: {errore}.",
            "Scrivilo come [{\"forma\": \"rettangolo\", \"punti\": [[0.1, 0.2], [0.4, 0.6]], \"nota\": \"...\"}].",
        ) from None
    if not isinstance(dati, list):
        raise banco.PianoNonValido(f"Il file delle aree {percorso} non e' un elenco.", "Mettici un elenco di aree.")
    try:
        return tuple(banco.Area.da_dizionario(a) for a in dati)
    except AreaNonValida as errore:
        raise banco.PianoNonValido(f"Nel file delle aree {percorso}: {errore.fatto}", errore.cosa_fare) from None


def _modello(identificativo: str):
    for modello in MODELLI:
        if modello.identificativo == identificativo:
            return modello
    raise banco.PianoNonValido(
        f"Il banco non conosce il modello {identificativo}.",
        f"Scegli fra: {', '.join(m.identificativo for m in MODELLI)}.",
    )


def esegui(argomenti, dire=print, chiedi=input, crea_motore=ProviderComfy, adesso=datetime.now) -> int:
    if argomenti.giudica:
        return giudica(Path(argomenti.giudica), dire)
    if not argomenti.immagine or not argomenti.piano:
        raise banco.PianoNonValido(
            "Servono --immagine e --piano (oppure --giudica con la cartella di un banco).",
            f"Per esempio: --immagine vista.png --piano qualita. I piani: {', '.join(banco.PIANI)}.",
        )
    sorgente = Path(argomenti.immagine)
    dati = modulo_immagine.leggi(sorgente)
    giudizio = valuta(modulo_immagine.misura(dati))
    if not giudizio.idonea:
        raise ImmagineNonIdonea(giudizio.fatto, giudizio.cosa_fare, giudizio.motivo or "")
    aree = leggi_aree(argomenti.aree) if argomenti.piano == "aree" else ()
    scelto = banco.piano(argomenti.piano, argomenti.scena, aree)
    modello = _modello(argomenti.modello)
    motore = crea_motore()
    costo = testo_costo(modello, len(scelto.invii))
    for riga in banco.riepilogo(scelto, motore, modello.identificativo, costo):
        dire(riga)
    if not argomenti.secco:
        if motore.cosa_manca(modello.identificativo):
            dire("Non parto: lo schema di questo modello non e' verificato.")
            return USCITA_RIFIUTO
        risposta = chiedi(f"Mando {len(scelto.invii)} invii? Scrivi si per partire: ")
        if risposta.strip().lower() not in ("si", "sì"):
            dire("Non ho inviato niente.")
            return USCITA_OK
    cartella = banco.cartella_del_banco(sorgente, scelto.nome, argomenti.uscita, adesso())
    risultato = banco.esegui(
        scelto, sorgente, cartella, motore=motore, modello=modello.identificativo,
        costo=costo, a_secco=argomenti.secco, dire=dire, adesso=adesso,
    )
    if argomenti.secco:
        dire("Prova a secco: non ho inviato niente.")
    dire(f"Pagina del banco: {cartella / banco.FILE_PAGINA}")
    dire(f"Per salvare i giudizi: python scripts/prova_blocchi.py --giudica \"{cartella}\"")
    falliti = [v for v in risultato["invii"] if v["stato"] in (banco.ERRORE, banco.SALTATO)]
    return USCITA_PROVIDER if falliti else USCITA_OK


def giudica(cartella: Path, dire=print, apri=webbrowser.open) -> int:
    server = banco.server_giudizi(cartella)
    indirizzo = f"http://127.0.0.1:{server.server_address[1]}/"
    dire(f"Pagina del banco su {indirizzo} · i giudizi vanno in {cartella / banco.FILE_GIUDIZI}")
    dire("Ctrl+C per chiudere.")
    apri(indirizzo)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return USCITA_OK


def main(argv: list[str] | None = None) -> int:
    argomenti = costruisci_parser().parse_args(argv)
    try:
        return esegui(argomenti)
    except ErroreAirender as errore:
        print(str(errore), file=sys.stderr)
        return USCITA_RIFIUTO


if __name__ == "__main__":
    raise SystemExit(main())
