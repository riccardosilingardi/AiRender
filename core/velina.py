"""La velina del Fotoinserimento: carta da forno sopra la foto del luogo.

Richiesta di Riccardo del 2026-11-20, approvata il 2026-11-23 (thread
«Aggiungere la velina al fotoinserimento»). Sopra la foto si stende uno strato
chiaro che la sbiadisce, e ci si schizza a mano libera:

- rosso: cosa cambiare o togliere nel luogo;
- verde: alberi, siepi e verde nuovi, col loro profilo;
- nero: profili e sagome degli edifici nuovi.

Gli oggetti da inserire sono una o piu' viste di Allplan (edificio A, B, ...).
Ognuno puo' avere un posto, una lettera cerchiata sulla velina, e puo' essere
«agganciato» con 4 punti: 4 angoli a terra sulla foto e gli stessi 4 sulla
vista. Con l'aggancio AIRENDER deforma la vista sulla foto prima dell'invio
(omografia), cosi' il modello riceve l'edificio gia' al suo posto. I punti sono
facoltativi: senza, il modello piazza l'edificio come ha sempre fatto.

Cosa parte, nell'ordine: (1) la foto del luogo pulita, senza velina, con gli
edifici agganciati gia' montati; (2) la stessa foto sotto la velina con lo
schizzo, se c'e' uno schizzo o un posto; (3...) una vista per oggetto. La
foto pulita va per prima: il realismo del risultato viene da li', e la velina
e' solo un foglio di istruzioni.

L'omografia e' esatta sul piano del terreno (i 4 punti) e approssimata per
quello che sta piu' in alto: tetti e facciate tornano bene solo se la vista
di Allplan e' presa da un punto simile alla foto. Lo Studio lo dice.

Le coordinate sono frazioni dell'immagine, da 0 a 1, con l'origine in alto a
sinistra. Qui non c'e' nessun import di Allplan, come in tutto core/.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

from . import aree as modulo_aree, config, immagine as modulo_immagine
from .errori import ErroreAirender

Punto = tuple[float, float]

CAMBIA = "cambia"
VERDE = "verde"
PROFILO = "profilo"
COLORI = (CAMBIA, VERDE, PROFILO)
# I colori dello schizzo, uguali nello Studio (studio.js, COLORI_VELINA): il
# prompt li nomina, quindi devono restare rosso, verde e nero.
RGB = {CAMBIA: (214, 50, 43), VERDE: (47, 138, 58), PROFILO: (20, 20, 20)}  # numero-non-configurabile: i colori che il prompt nomina (rosso, verde, nero), uguali in studio.js
# Come l'interfaccia chiama ogni colore, sempre con le stesse parole.
NOMI_COLORI = {CAMBIA: "Cambia o togli", VERDE: "Alberi e verde", PROFILO: "Profili"}
# Il colore della carta da forno.
CARTA = (247, 244, 236)  # numero-non-configurabile: il colore della carta da forno, solo aspetto
LETTERE = "ABCD"


class VelinaNonValida(ErroreAirender):
    """Una velina che non si puo' mandare: tratti, oggetti o punti che non tornano."""


def _punto(p: object, che_cosa: str) -> Punto:
    try:
        x, y = (float(c) for c in p)  # type: ignore[union-attr]
    except (TypeError, ValueError):
        raise VelinaNonValida(f"{che_cosa}: un punto non e' [x, y].", "Rimetti il punto sull'immagine.") from None
    if not (0 <= x <= 1 and 0 <= y <= 1):
        raise VelinaNonValida(f"{che_cosa}: un punto sta fuori dall'immagine.", "Rimetti il punto sull'immagine.")
    return (x, y)


def _quattro(punti: object, che_cosa: str) -> tuple[Punto, ...] | None:
    if punti in (None, [], ()):
        return None
    if not isinstance(punti, (list, tuple)) or len(punti) != 4:  # numero-non-configurabile: l'aggancio e' un quadrilatero: 4 punti per definizione
        raise VelinaNonValida(f"{che_cosa}: servono esattamente 4 punti, nell'ordine 1, 2, 3, 4.",
                              "Metti i 4 punti sugli angoli a terra dell'edificio.")
    return tuple(_punto(p, che_cosa) for p in punti)


def quadrilatero_valido(punti: tuple[Punto, ...]) -> bool:
    """4 punti che fanno un quadrilatero convesso, nell'ordine: niente tre in fila, niente lati incrociati."""
    segno = 0
    for i in range(4):  # numero-non-configurabile: i 4 lati del quadrilatero
        (ax, ay), (bx, by), (cx, cy) = punti[i], punti[(i + 1) % 4], punti[(i + 2) % 4]  # numero-non-configurabile: i 4 vertici del quadrilatero
        z = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(z) < 1e-4:  # numero-non-configurabile: tre punti quasi in fila, in frazioni dell'immagine
            return False
        s = 1 if z > 0 else -1
        if segno and s != segno:
            return False
        segno = s
    return True


def _operazioni(voci: object, che_cosa: str) -> tuple[modulo_aree.Operazione, ...]:
    if not voci:
        return ()
    if not isinstance(voci, list):
        raise VelinaNonValida(f"{che_cosa} non e' un elenco di tratti.", "Ridisegna.")
    try:
        return tuple(modulo_aree.Operazione.da_dizionario(v) for v in voci)
    except modulo_aree.AreaNonValida as errore:
        raise VelinaNonValida(f"{che_cosa}: {errore.fatto}", errore.cosa_fare) from None


@dataclass(frozen=True)
class Tratto:
    """Un pezzo dello schizzo: un'operazione di pennello (core/aree.py) con il suo colore."""

    colore: str
    operazione: modulo_aree.Operazione

    def __post_init__(self) -> None:
        if self.colore not in COLORI:
            raise VelinaNonValida(f"\"{self.colore}\" non e' un colore della velina.",
                                  "Usa rosso (cambia), verde (alberi) o nero (profili).")

    def a_dizionario(self) -> dict:
        return {"colore": self.colore, **self.operazione.a_dizionario()}


@dataclass(frozen=True)
class Oggetto:
    """Una vista da inserire. `vista` vuota = la vista del lavoro; le altre sono file della cartella delle viste."""

    vista: str = ""
    posto: Punto | None = None
    punti_luogo: tuple[Punto, ...] | None = None
    punti_vista: tuple[Punto, ...] | None = None
    # Cosa della vista si incolla con l'aggancio: una pittura come quella del
    # Ritocca. Senza, si incollerebbe anche lo sfondo e il terreno della vista.
    ritaglio: tuple[modulo_aree.Operazione, ...] = ()

    def __post_init__(self) -> None:
        if bool(self.punti_luogo) != bool(self.punti_vista):
            raise VelinaNonValida(
                "L'aggancio ha i 4 punti solo su una delle due immagini.",
                "Metti gli stessi 4 punti sia sulla foto sia sulla vista, oppure togli l'aggancio.",
            )
        if self.punti_luogo:
            for punti, dove in ((self.punti_luogo, "sulla foto"), (self.punti_vista, "sulla vista")):
                if not quadrilatero_valido(punti):  # type: ignore[arg-type]
                    raise VelinaNonValida(
                        f"I 4 punti {dove} non fanno un quadrilatero: tre sono quasi in fila, o i lati si incrociano.",
                        "Mettili in ordine 1, 2, 3, 4 attorno all'impronta dell'edificio, a terra.",
                    )
            if not any(not o.gomma for o in self.ritaglio):
                raise VelinaNonValida(
                    "L'aggancio non sa cosa incollare: manca il ritaglio dell'edificio sulla vista.",
                    "Ripassa l'edificio col pennello «Ritaglia» sulla vista, oppure togli l'aggancio.",
                )

    @property
    def agganciato(self) -> bool:
        return bool(self.punti_luogo)

    def a_dizionario(self) -> dict:
        voce: dict = {"vista": self.vista}
        if self.posto:
            voce["posto"] = list(self.posto)
        if self.agganciato:
            voce["punti_luogo"] = [list(p) for p in self.punti_luogo]  # type: ignore[union-attr]
            voce["punti_vista"] = [list(p) for p in self.punti_vista]  # type: ignore[union-attr]
        if self.ritaglio:
            voce["ritaglio"] = [o.a_dizionario() for o in self.ritaglio]
        return voce

    @classmethod
    def da_dizionario(cls, dati: object) -> "Oggetto":
        if not isinstance(dati, dict):
            raise VelinaNonValida("Un oggetto da inserire non e' un oggetto.", "Ricarica lo Studio.")
        posto = dati.get("posto")
        return cls(
            vista=str(dati.get("vista") or ""),
            posto=_punto(posto, "Il posto dell'edificio") if posto else None,
            punti_luogo=_quattro(dati.get("punti_luogo"), "L'aggancio sulla foto"),
            punti_vista=_quattro(dati.get("punti_vista"), "L'aggancio sulla vista"),
            ritaglio=_operazioni(dati.get("ritaglio"), "Il ritaglio dell'edificio"),
        )


@dataclass(frozen=True)
class Velina:
    """Lo schizzo sulla carta da forno e gli oggetti da inserire (il primo e' la vista del lavoro)."""

    tratti: tuple[Tratto, ...] = ()
    opacita: float = config.VELINA_OPACITA
    oggetti: tuple[Oggetto, ...] = field(default_factory=lambda: (Oggetto(),))

    def __post_init__(self) -> None:
        if isinstance(self.opacita, bool) or not isinstance(self.opacita, (int, float)) \
                or not 0 <= self.opacita <= config.VELINA_OPACITA_MASSIMA:
            raise VelinaNonValida(
                f"La velina ha un'opacita' che non torna: {self.opacita!r}.",
                f"Va da 0 a {config.VELINA_OPACITA_MASSIMA}: rimettila col cursore.",
            )
        if not self.oggetti or len(self.oggetti) > config.CONTESTO_OGGETTI_MASSIMO:
            raise VelinaNonValida(
                f"Gli edifici da inserire sono {len(self.oggetti)}: ne partono da 1 a {config.CONTESTO_OGGETTI_MASSIMO}.",
                "Togline qualcuno.",
            )
        if self.oggetti[0].vista:
            raise VelinaNonValida("Il primo edificio dev'essere la vista scelta.", "Ricarica lo Studio.")
        if any(not o.vista for o in self.oggetti[1:]):
            raise VelinaNonValida("Un edificio in piu' non dice da che vista viene.", "Scegli di nuovo la vista.")
        punti = sum(len(t.operazione.punti) for t in self.tratti) \
            + sum(len(op.punti) for o in self.oggetti for op in o.ritaglio)
        if punti > config.PITTURA_PUNTI_MASSIMI:
            raise VelinaNonValida(
                f"Lo schizzo ha {punti} punti: ne entrano al massimo {config.PITTURA_PUNTI_MASSIMI}.",
                "Cancella qualche tratto con Annulla o con la gomma.",
            )

    # --- cosa dice ---------------------------------------------------------

    @property
    def ha_schizzo(self) -> bool:
        return any(not t.operazione.gomma for t in self.tratti)

    @property
    def lettere_posti(self) -> tuple[str, ...]:
        return tuple(LETTERE[i] for i, o in enumerate(self.oggetti) if o.posto)

    @property
    def lettere_agganciate(self) -> tuple[str, ...]:
        return tuple(LETTERE[i] for i, o in enumerate(self.oggetti) if o.agganciato)

    @property
    def parte_la_velina(self) -> bool:
        """La seconda immagine parte solo se c'e' qualcosa da leggere sopra: tratti o posti."""
        return self.ha_schizzo or bool(self.lettere_posti)

    @property
    def dice_dove(self) -> bool:
        """Lo schizzo, un posto o un aggancio dicono gia' dove va: il rettangolo diventa facoltativo."""
        return self.parte_la_velina or bool(self.lettere_agganciate)

    @property
    def colori_usati(self) -> tuple[str, ...]:
        usati = {t.colore for t in self.tratti if not t.operazione.gomma}
        return tuple(c for c in COLORI if c in usati)

    def quante_immagini(self) -> int:
        return 1 + int(self.parte_la_velina) + len(self.oggetti)

    # --- dizionario ----------------------------------------------------------

    def a_dizionario(self) -> dict:
        return {
            "tratti": [t.a_dizionario() for t in self.tratti],
            "opacita": self.opacita,
            "oggetti": [o.a_dizionario() for o in self.oggetti],
        }

    @classmethod
    def da_dizionario(cls, dati: object) -> "Velina":
        if not isinstance(dati, dict):
            raise VelinaNonValida("La velina non e' arrivata per intero.", "Ricarica lo Studio.")
        voci = dati.get("tratti") or []
        if not isinstance(voci, list):
            raise VelinaNonValida("Lo schizzo non e' un elenco di tratti.", "Ridisegna.")
        tratti = []
        for voce in voci:
            if not isinstance(voce, dict):
                raise VelinaNonValida("Un tratto dello schizzo non e' un oggetto.", "Ridisegna.")
            operazione = _operazioni([{k: v for k, v in voce.items() if k != "colore"}], "Lo schizzo")[0]
            tratti.append(Tratto(str(voce.get("colore") or ""), operazione))
        oggetti = dati.get("oggetti") or [{}]
        if not isinstance(oggetti, list):
            raise VelinaNonValida("Gli edifici da inserire non sono un elenco.", "Ricarica lo Studio.")
        opacita = dati.get("opacita", config.VELINA_OPACITA)
        return cls(tratti=tuple(tratti), opacita=opacita,
                   oggetti=tuple(Oggetto.da_dizionario(o) for o in oggetti))

    def con_viste(self, viste: tuple[str, ...]) -> "Velina":
        """La stessa velina con i file delle viste in piu' al posto dei nomi (il primo resta vuoto)."""
        oggetti = (self.oggetti[0],) + tuple(
            Oggetto(v, o.posto, o.punti_luogo, o.punti_vista, o.ritaglio) for o, v in zip(self.oggetti[1:], viste))
        return Velina(self.tratti, self.opacita, oggetti)


# --- disegno ---------------------------------------------------------------


def _apri(dati: bytes) -> Image.Image:
    with Image.open(io.BytesIO(dati)) as aperta:
        return aperta.convert("RGB")


def _png(immagine: Image.Image) -> bytes:
    uscita = io.BytesIO()
    immagine.save(uscita, format="PNG")
    return uscita.getvalue()


def disegna(luogo: bytes, velina: Velina) -> bytes:
    """La foto sotto la carta da forno, con lo schizzo e le lettere dei posti: la seconda immagine che parte.

    I tratti si dipingono in ordine su uno strato trasparente: la gomma toglie
    quello che c'era sotto, di qualunque colore, come fa lo Studio.
    """
    foto = _apri(luogo)
    larghezza, altezza = foto.size
    carta = Image.new("RGB", foto.size, CARTA)
    base = Image.blend(foto, carta, float(velina.opacita))
    strato = Image.new("RGBA", foto.size, (0, 0, 0, 0))
    disegno = ImageDraw.Draw(strato)
    for tratto in velina.tratti:
        pezzo = tratto.operazione.in_pixel(larghezza, altezza)
        modulo_immagine._dipingi(disegno, pezzo, (*RGB[tratto.colore], 255), (0, 0, 0, 0))  # numero-non-configurabile: alfa pieno
    base = base.convert("RGBA")
    base.alpha_composite(strato)
    raggio = max(12, round(min(larghezza, altezza) * 0.03))  # numero-non-configurabile: lettera leggibile, 3% del lato corto
    disegno = ImageDraw.Draw(base)
    carattere = modulo_immagine._carattere(round(raggio * 1.3))  # numero-non-configurabile: la lettera un po' piu' grande del raggio, solo aspetto
    for i, oggetto in enumerate(velina.oggetti):
        if not oggetto.posto:
            continue
        x, y = oggetto.posto[0] * larghezza, oggetto.posto[1] * altezza
        disegno.ellipse((x - raggio, y - raggio, x + raggio, y + raggio), fill=(*RGB[PROFILO], 255),  # numero-non-configurabile: bianco e alfa pieno
                        outline=(255, 255, 255, 255), width=max(2, raggio // 6))  # numero-non-configurabile: bordo bianco, solo aspetto
        disegno.text((x, y), LETTERE[i], fill=(255, 255, 255, 255), font=carattere, anchor="mm")  # numero-non-configurabile: bianco e alfa pieno
    return _png(base.convert("RGB"))


def _risolvi(matrice: list[list[float]], termini: list[float]) -> list[float] | None:
    """Gauss con pivot parziale, in Python puro: gira uguale nel plugin e nel browser (Pyodide)."""
    n = len(termini)
    righe = [r[:] + [termini[i]] for i, r in enumerate(matrice)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(righe[r][c]))
        righe[c], righe[p] = righe[p], righe[c]
        if abs(righe[c][c]) < 1e-12:  # numero-non-configurabile: sistema singolare, punti allineati
            return None
        for r in range(n):
            if r != c:
                f = righe[r][c] / righe[c][c]
                righe[r] = [a - f * b for a, b in zip(righe[r], righe[c])]
    return [righe[i][n] / righe[i][i] for i in range(n)]


def omografia(da: list[Punto], a: list[Punto]) -> tuple[float, ...] | None:
    """Gli 8 coefficienti che portano i 4 punti `da` sui 4 punti `a` (come vuole Image.transform PERSPECTIVE).

    Pillow chiede, per ogni pixel dell'uscita, dove leggere nell'ingresso:
    quindi `da` sono i punti sull'uscita (la foto) e `a` quelli sull'ingresso (la vista).
    """
    matrice, termini = [], []
    for (x, y), (u, v) in zip(da, a):
        matrice.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        termini.append(u)
        matrice.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        termini.append(v)
    soluzione = _risolvi(matrice, termini)
    return tuple(soluzione) if soluzione else None


def aggancia(luogo: bytes, viste: tuple[bytes, ...], velina: Velina) -> bytes:
    """La foto con gli edifici agganciati gia' montati, prima dal piu' lontano. Senza aggancio, la foto com'e'."""
    if not velina.lettere_agganciate:
        return luogo
    foto = _apri(luogo)
    larghezza, altezza = foto.size
    ordine = sorted((i for i, o in enumerate(velina.oggetti) if o.agganciato),
                    key=lambda i: max(y for _, y in velina.oggetti[i].punti_luogo))  # type: ignore[union-attr]
    for indice in ordine:
        oggetto = velina.oggetti[indice]
        vista = _apri(viste[indice])
        lv, av = vista.size
        coeff = omografia([(x * larghezza, y * altezza) for x, y in oggetto.punti_luogo],  # type: ignore[union-attr]
                          [(x * lv, y * av) for x, y in oggetto.punti_vista])  # type: ignore[union-attr]
        if coeff is None:
            raise VelinaNonValida("I 4 punti dell'aggancio sono allineati: non so dove mettere l'edificio.",
                                  "Rimetti i punti agli angoli a terra dell'edificio.")
        maschera = modulo_immagine._maschera_pittura(
            (lv, av), [op.in_pixel(lv, av) for op in oggetto.ritaglio])
        deformata = vista.transform(foto.size, Image.Transform.PERSPECTIVE, coeff, Image.Resampling.BICUBIC)
        maschera = maschera.transform(foto.size, Image.Transform.PERSPECTIVE, coeff, Image.Resampling.BILINEAR)
        foto.paste(deformata, (0, 0), maschera)
    return _png(foto)
