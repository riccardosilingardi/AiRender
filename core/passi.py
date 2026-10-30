"""L'albero dei passi di una vista (Studio · Passi).

Ogni render di una vista e' un passo. Il passo "0" e' la vista Allplan; ogni
altro passo parte da un passo (`da`) ed e' il figlio di quello. Un passo
nuovo fatto da un passo che ha gia' figli apre un ramo li' sotto. Decisione
di Riccardo del 2026-10-28 (PRD, sezione 5): un albero solo, in una colonna,
niente grafo a nodi.

L'albero si salva accanto alla vista, in `<nome della vista>.passi.json`,
scritto atomico e leggibile a mano. Ogni passo porta la sua ricetta completa:
immagine di partenza, scelte, testo, aree (nessuna finche' non c'e' Ritocca),
modello, versione dei blocchi, costo, data.

Chi scrive cosa:
- la coda dei lavori non sa che l'albero esiste: fa lavori, come prima;
- lo Studio allinea l'albero ai lavori della vista ogni volta che lo legge
  (`allinea`). Un lavoro che l'albero non ha ancora diventa un passo: cosi'
  i render gia' fatti prima di questo file diventano figli della vista, e
  un render mandato dalla palette o da `python -m core.coda --aggiungi` non
  si perde;
- un passo non si cancella mai da qui. Se la cartella dei lavori viene
  pulita, il passo resta con l'ultimo stato che si conosceva.

Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import blocchi, coda as modulo_coda
from .errori import ErroreAirender

FORMATO = 1  # numero-non-configurabile: versione del formato del file dell'albero
SUFFISSO = ".passi.json"
VISTA = "0"  # il passo 0: la vista Allplan

# Lunghezza del nome breve di un passo fatto a parole, in caratteri.
_NOME_BREVE = 48  # numero-non-configurabile: misura della riga nell'albero, non una soglia

STATI_ATTIVI = (modulo_coda.IN_CODA, modulo_coda.INVIATO, modulo_coda.IN_LAVORAZIONE)


class AlberoNonValido(ErroreAirender):
    """Il file dell'albero non si legge: non si riscrive, per non perdere passi."""


class PassoNonValido(ErroreAirender):
    """Un passo che non c'e', o da cui non si puo' partire."""


def percorso(vista: Path) -> Path:
    """Il file dell'albero di una vista: accanto alla vista, con lo stesso nome."""
    vista = Path(vista)
    return vista.with_name(vista.stem + SUFFISSO)


def nome_breve(testo: str) -> str:
    """La richiesta di un passo, accorciata per stare in una riga dell'albero."""
    testo = " ".join((testo or "").split())
    if len(testo) <= _NOME_BREVE:
        return testo
    return testo[: _NOME_BREVE - 1].rstrip() + "…"


@dataclass
class Albero:
    """I passi di una vista, nell'ordine in cui sono nati."""

    vista: str
    passi: list[dict] = field(default_factory=list)
    formato: int = FORMATO

    # --- lettura e scrittura -----------------------------------------------

    @classmethod
    def leggi(cls, vista: Path) -> "Albero":
        """L'albero della vista, vuoto se non c'e' ancora il file."""
        vista = Path(vista)
        file_albero = percorso(vista)
        try:
            testo = file_albero.read_text(encoding="utf-8")
        except FileNotFoundError:
            return cls(vista=vista.name)
        try:
            dati = json.loads(testo)
        except ValueError as errore:
            raise AlberoNonValido(
                f"Il file dei passi {file_albero} non e' un JSON leggibile ({errore}).",
                "Non l'ho toccato, per non perdere passi. Correggilo a mano, oppure "
                "spostalo altrove: lo Studio ne rifa' uno dai render della cartella.",
            ) from None
        if not isinstance(dati, dict) or dati.get("formato") != FORMATO \
                or not isinstance(dati.get("passi"), list):
            raise AlberoNonValido(
                f"Il file dei passi {file_albero} non e' nel formato {FORMATO}.",
                "Non l'ho toccato. Aggiorna lo Studio, oppure sposta il file altrove: "
                "lo Studio ne rifa' uno dai render della cartella.",
            )
        passi = [p for p in dati["passi"] if isinstance(p, dict) and p.get("identificativo")]
        return cls(vista=str(dati.get("vista") or vista.name), passi=passi)

    def a_dizionario(self) -> dict:
        return {"formato": self.formato, "vista": self.vista, "passi": self.passi}

    def scrivi(self, vista: Path) -> Path:
        return modulo_coda.scrivi_json(percorso(vista), self.a_dizionario())

    # --- forma dell'albero -------------------------------------------------

    def passo(self, identificativo: str) -> dict | None:
        return next((p for p in self.passi if p["identificativo"] == identificativo), None)

    def padre(self, passo: dict) -> str:
        """Da quale passo parte. Se quello non c'e' nell'albero, dalla vista."""
        da = passo.get("da") or VISTA
        return da if da == VISTA or self.passo(da) is not None else VISTA

    def figli(self, identificativo: str) -> list[dict]:
        return [p for p in self.passi if self.padre(p) == identificativo]

    def strada(self, identificativo: str) -> list[dict]:
        """I passi dalla vista fino a questo, lui compreso (la vista no)."""
        strada = []
        corrente = self.passo(identificativo)
        while corrente is not None and corrente not in strada:
            strada.insert(0, corrente)
            da = self.padre(corrente)
            corrente = None if da == VISTA else self.passo(da)
        return strada

    def generazioni(self, identificativo: str) -> int:
        """Quante generazioni di fila ha questa immagine: 1 per un render dalla vista."""
        return len(self.strada(identificativo))

    def in_ordine(self) -> list[tuple[dict, int]]:
        """I passi come si disegnano nella colonna: ogni passo sotto suo padre, con la profondita'."""
        righe: list[tuple[dict, int]] = []

        def visita(identificativo: str, profondita: int) -> None:
            for figlio in self.figli(identificativo):
                if any(figlio is r[0] for r in righe):
                    continue
                righe.append((figlio, profondita))
                visita(figlio["identificativo"], profondita + 1)

        visita(VISTA, 1)
        return righe

    # --- allineamento con i lavori -----------------------------------------

    def allinea(self, lavori: list[dict], stati: dict[str, dict], ricette: dict[str, dict]) -> bool:
        """Aggiunge i lavori che l'albero non ha e aggiorna l'esito di quelli che ha.

        `lavori` sono i file dei lavori di questa vista, `stati` lo stato di
        ognuno, `ricette` la ricetta di quelli fatti. Restituisce True se
        l'albero e' cambiato e va scritto.
        """
        cambiato = False
        noti = {p["identificativo"] for p in self.passi}
        for lavoro in sorted(lavori, key=lambda l: (l.get("creato_il") or "", l["identificativo"])):
            if lavoro["identificativo"] not in noti:
                self.passi.append(_passo_da_lavoro(lavoro, self._prossimo_numero()))
                noti.add(lavoro["identificativo"])
                cambiato = True
        presenti = {l["identificativo"] for l in lavori}
        for passo in self.passi:
            identificativo = passo["identificativo"]
            if identificativo in presenti:
                esito = _esito(stati.get(identificativo) or {}, ricette.get(identificativo))
            elif passo.get("stato") in STATI_ATTIVI:
                # Il lavoro e' sparito mentre era in corso: la cartella e'
                # stata pulita a mano. Non si sa com'e' finito, e lo si dice.
                esito = {
                    "stato": modulo_coda.ERRORE,
                    "fatto": "Il lavoro di questo passo non c'e' piu' nella cartella dei lavori.",
                    "cosa_fare": "Rifai il passo: non so se il servizio l'aveva fatto.",
                }
            else:
                continue
            for chiave, valore in esito.items():
                if passo.get(chiave) != valore:
                    passo[chiave] = valore
                    cambiato = True
        return cambiato

    def _prossimo_numero(self) -> int:
        return max((int(p.get("numero") or 0) for p in self.passi), default=0) + 1


def _passo_da_lavoro(lavoro: dict, numero: int) -> dict:
    """Un passo nuovo dal file del suo lavoro: la ricetta senza l'esito."""
    richieste = list(lavoro.get("richieste") or [])
    scelte = lavoro.get("scelte") or {}
    partenza = lavoro.get("partenza")
    return {
        "identificativo": lavoro["identificativo"],
        "numero": numero,
        "da": lavoro.get("parte_da") or VISTA,
        "creato_il": lavoro.get("creato_il"),
        "scena": scelte.get("scena"),
        # Dalla vista lo stile sta nelle scelte; da un render le scelte
        # dicono solo la scena, e la richiesta e' a parole.
        "scelte": None if partenza else scelte,
        "preset": None if partenza else lavoro.get("preset"),
        "prompt_a_mano": None if partenza else lavoro.get("prompt_a_mano"),
        "richieste": richieste,
        "aree": None,  # le aree arrivano con Ritocca
        "partenza": {"passo": lavoro.get("parte_da") or VISTA, "file": partenza or lavoro.get("vista")},
        "prompt": _prompt(lavoro),
        "versione_blocchi": blocchi.VERSIONE,
        "provider": lavoro.get("provider"),
        "modello": lavoro.get("modello"),
        "destinazione": lavoro.get("destinazione"),
        "stato": modulo_coda.IN_CODA,
    }


def _prompt(lavoro: dict) -> str | None:
    """Il testo che parte, gia' prima dell'invio. La ricetta lo conferma dopo."""
    try:
        return modulo_coda.Lavoro.da_dizionario(lavoro).prompt()
    except ErroreAirender:
        return None


def _esito(stato: dict, ricetta: dict | None) -> dict:
    """Quello che di un passo si sa dopo l'invio: stato, render, costo, prompt partito."""
    esito = {
        "stato": stato.get("stato") or modulo_coda.IN_CODA,
        "fatto": stato.get("fatto"),
        "cosa_fare": stato.get("cosa_fare"),
        "render": stato.get("render") if stato.get("stato") == modulo_coda.FATTO else None,
        "ricetta": stato.get("ricetta") if stato.get("stato") == modulo_coda.FATTO else None,
    }
    if ricetta is not None:
        parametri = ricetta.get("parametri") or {}
        crediti = parametri.get("crediti_usati")
        try:
            esito["costo_crediti"] = float(crediti) if crediti is not None else None
        except (TypeError, ValueError):
            esito["costo_crediti"] = None
        esito["prompt"] = ricetta.get("prompt")
        esito["versione_blocchi"] = ricetta.get("preset_versione")
        esito["impronta_partenza"] = ricetta.get("impronta_sorgente")
        esito["fatto_il"] = ricetta.get("creata_il")
    return esito
