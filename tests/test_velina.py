"""La velina del Fotoinserimento (2026-11-23): schizzo, posti, aggancio con 4 punti.

Nessuna rete: le immagini partono verso il provider finto della coda.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from conftest import vista_shaded
from core import blocchi, config, velina as modulo_velina
from core.coda import Coda, LavoroNonValido, leggi_stato
from core.contesto import Contesto, ContestoNonValido
from core.velina import Oggetto, Tratto, Velina, VelinaNonValida
from core.aree import Operazione
from test_contesto import NANO, ProviderConDueImmagini, _contesto, _jpeg, _richiesta, _studio, cartella, chiamate  # noqa: F401

QUADRO = [[0.2, 0.5], [0.6, 0.5], [0.65, 0.85], [0.15, 0.85]]
VISTA = [[0.1, 0.3], [0.9, 0.3], [0.9, 0.9], [0.1, 0.9]]
PENNELLATA = {"tipo": "tratto", "spessore": 0.05, "punti": [[0.2, 0.2], [0.8, 0.8]], "gomma": False}


def _tratto(colore="cambia", **altro) -> dict:
    return {"colore": colore, **PENNELLATA, **altro}


def _velina(**altro) -> dict:
    return {"tratti": [_tratto()], "opacita": 0.55, "oggetti": [{"vista": ""}], **altro}


def _apri(dati: bytes) -> Image.Image:
    return Image.open(io.BytesIO(dati)).convert("RGB")


# --- omografia --------------------------------------------------------------


def test_l_omografia_porta_i_4_punti_della_foto_sui_4_della_vista():
    """Caso: i coefficienti girati al contrario mettono l'edificio fuori posto (Pillow vuole uscita -> ingresso)."""
    da = [(10, 20), (200, 30), (220, 180), (5, 160)]
    a = [(0, 0), (100, 0), (100, 80), (0, 80)]
    a0, b0, c0, d0, e0, f0, g0, h0 = modulo_velina.omografia(da, a)
    for (x, y), (u, v) in zip(da, a):
        w = g0 * x + h0 * y + 1
        assert abs((a0 * x + b0 * y + c0) / w - u) < 1e-6
        assert abs((d0 * x + e0 * y + f0) / w - v) < 1e-6


def test_punti_allineati_non_fanno_un_quadrilatero():
    assert not modulo_velina.quadrilatero_valido(((0, 0), (0.5, 0), (1, 0), (0.5, 0.5)))
    assert not modulo_velina.quadrilatero_valido(((0, 0), (1, 1), (1, 0), (0, 1)))  # lati incrociati
    assert modulo_velina.quadrilatero_valido(tuple(tuple(p) for p in QUADRO))


# --- regole ----------------------------------------------------------------


def test_la_velina_va_e_torna_dal_dizionario():
    velina = Velina.da_dizionario(_velina(oggetti=[
        {"vista": "", "posto": [0.4, 0.6]},
        {"vista": "vista-2.png", "punti_luogo": QUADRO, "punti_vista": VISTA, "ritaglio": [PENNELLATA]}]))
    assert Velina.da_dizionario(velina.a_dizionario()) == velina
    assert velina.lettere_posti == ("A",) and velina.lettere_agganciate == ("B",)
    assert velina.quante_immagini() == 4


def test_un_aggancio_senza_ritaglio_si_rifiuta():
    """Caso: senza ritaglio si incollerebbe sulla foto anche il cielo e il prato verde della vista Allplan."""
    with pytest.raises(VelinaNonValida, match="ritaglio"):
        Oggetto(punti_luogo=tuple(map(tuple, QUADRO)), punti_vista=tuple(map(tuple, VISTA)))


def test_i_punti_su_una_sola_immagine_si_rifiutano():
    with pytest.raises(VelinaNonValida, match="una delle due"):
        Oggetto.da_dizionario({"punti_luogo": QUADRO})


def test_tre_punti_non_bastano():
    with pytest.raises(VelinaNonValida, match="esattamente 4"):
        Oggetto.da_dizionario({"punti_luogo": QUADRO[:3], "punti_vista": VISTA[:3]})


def test_un_colore_che_il_prompt_non_nomina_si_rifiuta():
    with pytest.raises(VelinaNonValida):
        Velina.da_dizionario(_velina(tratti=[_tratto("blu")]))


def test_l_opacita_oltre_il_massimo_si_rifiuta():
    """Caso VELINA_OPACITA_MASSIMA: la carta piena copre la foto e lo schizzo non si appoggia piu' a niente."""
    with pytest.raises(VelinaNonValida):
        Velina(opacita=config.VELINA_OPACITA_MASSIMA + 0.01)
    assert Velina().opacita == config.VELINA_OPACITA


def test_piu_edifici_del_massimo_si_rifiutano():
    """Caso CONTESTO_OGGETTI_MASSIMO: un quinto edificio non ha lettera e il prompt lo perderebbe."""
    oggetti = [{"vista": ""}] + [{"vista": f"v{i}.png"} for i in range(config.CONTESTO_OGGETTI_MASSIMO)]
    with pytest.raises(VelinaNonValida):
        Velina.da_dizionario(_velina(oggetti=oggetti))


def test_il_primo_edificio_e_sempre_la_vista_del_lavoro():
    with pytest.raises(VelinaNonValida):
        Velina.da_dizionario(_velina(oggetti=[{"vista": "altra.png"}]))


def test_senza_rettangolo_basta_che_la_velina_dica_dove():
    """Caso: con lo schizzo o il posto si doveva disegnare per forza anche il rettangolo."""
    assert Contesto.da_dizionario({"file": "x.png", "velina": _velina()}).area is None
    with pytest.raises(ContestoNonValido, match="Non so dove|Manca l'area"):
        Contesto.da_dizionario({"file": "x.png", "velina": _velina(tratti=[])})


def test_senza_velina_il_prompt_e_quello_di_prima():
    """Caso: la velina cambia anche il prompt di chi non la usa (il risultato di Arceto deve restare)."""
    assert Contesto("x.png", ((0.3, 0.4), (0.6, 0.8))).prompt("legno") == \
        blocchi.componi_contesto("zenitale", materiali="legno")


def test_il_prompt_numera_le_immagini_e_dice_i_colori_usati():
    velina = Velina.da_dizionario(_velina(tratti=[_tratto("verde")], oggetti=[
        {"vista": "", "posto": [0.4, 0.6]}, {"vista": "b.png"}]))
    testo = Contesto("x.png", None, inquadratura="terra", velina=velina).prompt()
    assert "Image 2 is the same site seen through a sheet of tracing paper" in testo
    assert "green marks" in testo and "red marks" not in testo
    assert "image 3 is building A, image 4 is building B" in testo
    assert "no tracing paper, no marks" in testo
    assert blocchi.INQUADRATURE["terra"].testo in testo
    assert "magenta" not in testo


def test_con_schizzo_la_misura_fuori_area_non_si_fa():
    """Caso: lo schizzo chiede di cambiare il luogo, e un numero «fuori area» sarebbe falso (regola 3)."""
    contesto = Contesto("x.png", ((0.3, 0.4), (0.6, 0.8)), velina=Velina.da_dizionario(_velina()))
    assert contesto.misura(_jpeg(), _jpeg()) is None


# --- disegno -----------------------------------------------------------------


def test_la_velina_sbiadisce_la_foto_e_ci_mette_lo_schizzo_e_la_lettera():
    foto = _jpeg(400, 300, (20, 20, 20))
    velina = Velina.da_dizionario(_velina(oggetti=[{"vista": "", "posto": [0.9, 0.1]}]))
    disegnata = _apri(modulo_velina.disegna(foto, velina))
    assert disegnata.size == (400, 300)
    r, g, b = disegnata.getpixel((10, 290))  # lontano da tratto e lettera: solo carta sopra la foto
    assert r > 100 and abs(r - b) < 30
    assert disegnata.getpixel((200, 150))[0] > 150 > disegnata.getpixel((200, 150))[1]  # il tratto rosso
    assert disegnata.getpixel((360, 30)) != disegnata.getpixel((10, 290))  # il cerchio della lettera


def test_l_aggancio_monta_solo_il_ritaglio_e_solo_dentro_i_4_punti():
    foto = _jpeg(400, 300, (40, 120, 200))
    vista = io.BytesIO()
    Image.new("RGB", (200, 200), (250, 250, 250)).save(vista, "PNG")
    ritaglio = {"tipo": "poligono", "punti": [[0, 0], [1, 0], [1, 1], [0, 1]], "gomma": False}
    velina = Velina.da_dizionario({"oggetti": [{"vista": "", "punti_luogo": QUADRO, "punti_vista": VISTA,
                                                "ritaglio": [ritaglio]}]})
    montata = _apri(modulo_velina.aggancia(foto, (vista.getvalue(),), velina))
    assert montata.getpixel((160, 205))[0] > 200  # dentro i 4 punti: la vista bianca
    assert montata.getpixel((20, 20))[2] > 150 and montata.getpixel((20, 20))[0] < 100  # fuori: la foto
    assert modulo_velina.aggancia(foto, (vista.getvalue(),), Velina()) == foto


# --- coda e Studio ------------------------------------------------------------


def _richiesta_velina(studio, nome, velina, **altro):
    dettagli = {"area": False, "velina": True, "edifici": len(velina["oggetti"]),
                "agganciati": sum(1 for o in velina["oggetti"] if o.get("punti_luogo"))}
    richiesta = _richiesta(studio, _contesto(nome, area=None, velina=velina), **altro)
    richiesta["destinazione_mostrata"] = studio.destinazione(NANO, contesto=dettagli)["destinazione"]
    return richiesta


def test_due_edifici_partono_nell_ordine_foto_pulita_velina_viste(cartella, chiamate):
    """Caso: la velina sbiadita va per prima e il render esce slavato, o una vista si perde."""
    (cartella / "vista-2.png").write_bytes(vista_shaded(500, 400))
    studio = _studio(cartella, chiamate)
    foto = _jpeg()
    nome = studio.carica_contesto(foto)["nome"]
    velina = _velina(oggetti=[{"vista": "", "posto": [0.3, 0.6]}, {"vista": "vista-2.png", "posto": [0.7, 0.6]}])
    risposta = studio.invia(_richiesta_velina(studio, nome, velina))
    lavoro = json.loads((cartella / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json").read_text("utf-8"))
    assert lavoro["contesto"]["velina"]["oggetti"][1]["vista"] == str(cartella / "vista-2.png")
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    (richiesta,) = chiamate
    assert _apri(richiesta.immagine).tobytes() == _apri(foto).tobytes()  # la foto pulita, senza contorno
    seconda, *viste = richiesta.immagini_in_piu
    assert _apri(seconda).size == (400, 300) and seconda != richiesta.immagine
    assert viste == [(cartella / "vista-1.png").read_bytes(), (cartella / "vista-2.png").read_bytes()]
    assert "image 3 is building A, image 4 is building B" in richiesta.prompt
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "fatto"


def test_la_destinazione_conta_le_immagini_della_velina(cartella, chiamate):
    """Caso: lo Studio annuncia due immagini e ne partono quattro (regola 5)."""
    studio = _studio(cartella, chiamate)
    dest = studio.destinazione(NANO, contesto={"area": False, "velina": True, "edifici": 2, "agganciati": 1})
    assert dest["immagini"] == 4
    assert dest["cosa_parte"].startswith("Partono 4 immagini: prima la foto del luogo pulita, "
                                         "con l'edificio agganciato già montato")
    assert "velina" in dest["cosa_parte"] and "edifici A e B" in dest["cosa_parte"]
    assert studio.destinazione(NANO, contesto=True)["immagini"] == 2


def test_un_edificio_in_piu_che_non_e_una_vista_si_rifiuta(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    velina = _velina(oggetti=[{"vista": ""}, {"vista": "../segreto.png"}])
    with pytest.raises(Exception, match="non e' il nome di una vista"):
        studio.invia(_richiesta_velina(studio, nome, velina))


def test_una_vista_in_piu_sparita_ferma_il_lavoro_prima_di_partire(cartella, chiamate):
    (cartella / "vista-2.png").write_bytes(vista_shaded(500, 400))
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    risposta = studio.invia(_richiesta_velina(studio, nome, _velina(oggetti=[{"vista": ""}, {"vista": "vista-2.png"}])))
    (cartella / "vista-2.png").unlink()
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    assert not chiamate
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "errore"


def test_una_vista_in_piu_fuori_dalla_cartella_si_rifiuta_anche_nella_coda(cartella, tmp_path):
    from core.coda import controlla_vista_in_piu
    fuori = tmp_path / "fuori.png"
    fuori.write_bytes(vista_shaded(100, 100))
    with pytest.raises(LavoroNonValido):
        controlla_vista_in_piu(cartella / "vista-1.png", fuori)


def test_l_anteprima_mostra_la_foto_che_parte_senza_mandare_niente(cartella, chiamate):
    """Caso: il prima/dopo dell'aggancio fa partire un render, o mostra una foto diversa da quella che parte."""
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    ritaglio = {"tipo": "poligono", "punti": [[0, 0], [1, 0], [1, 1], [0, 1]], "gomma": False}
    velina = {"oggetti": [{"vista": "", "punti_luogo": QUADRO, "punti_vista": VISTA, "ritaglio": [ritaglio]}]}
    risposta = studio.anteprima_contesto({"vista": "vista-1.png", "contesto": _contesto(nome, area=None, velina=velina)})
    assert risposta["pulita"].startswith("data:image/png;base64,") and risposta["velina"] is None
    assert risposta["immagini"] == 2
    assert not chiamate


def test_il_catalogo_dice_i_colori_della_velina_come_li_disegna_il_motore(cartella, chiamate):
    """Caso: la matita rossa dello Studio e il rosso che legge il modello non sono lo stesso colore."""
    cat = _studio(cartella, chiamate).catalogo()["contesto"]["velina"]
    assert [c["id"] for c in cat["colori"]] == list(modulo_velina.COLORI)
    assert cat["colori"][0]["rgb"] == "#%02x%02x%02x" % modulo_velina.RGB["cambia"]
    assert cat["edifici_massimi"] == config.CONTESTO_OGGETTI_MASSIMO
