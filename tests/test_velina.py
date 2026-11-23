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

PERIMETRO = [[0.2, 0.5], [0.6, 0.5], [0.65, 0.85], [0.15, 0.85]]
PERIMETRO_B = [[0.7, 0.2], [0.9, 0.2], [0.9, 0.4], [0.7, 0.4]]
PENNELLATA = {"tipo": "tratto", "spessore": 0.05, "punti": [[0.2, 0.2], [0.8, 0.8]], "gomma": False}


def _tratto(colore="cambia", **altro) -> dict:
    return {"colore": colore, **PENNELLATA, **altro}


def _velina(**altro) -> dict:
    return {"tratti": [_tratto()], "opacita": 0.55, "oggetti": [{"vista": ""}], **altro}


def _apri(dati: bytes) -> Image.Image:
    return Image.open(io.BytesIO(dati)).convert("RGB")


# --- regole ----------------------------------------------------------------


def test_la_velina_va_e_torna_dal_dizionario():
    velina = Velina.da_dizionario(_velina(oggetti=[
        {"vista": "", "perimetro": PERIMETRO}, {"vista": "vista-2.png", "perimetro": PERIMETRO_B}]))
    assert Velina.da_dizionario(velina.a_dizionario()) == velina
    assert velina.lettere == ("A", "B") and velina.ha_perimetri and velina.dice_dove
    assert velina.quante_immagini() == 4


def test_un_perimetro_con_due_vertici_si_rifiuta():
    """Caso: un doppio clic sbagliato chiude una linea, e il modello non sa dove sta la base."""
    with pytest.raises(VelinaNonValida, match="meno di 3 vertici"):
        Oggetto.da_dizionario({"perimetro": PERIMETRO[:2]})


def test_un_perimetro_schiacciato_su_una_linea_si_rifiuta():
    """Caso PERIMETRO_AREA_MINIMA: tre clic sulla stessa riga fanno un perimetro senza area."""
    with pytest.raises(VelinaNonValida, match="troppo piccolo"):
        Oggetto.da_dizionario({"perimetro": [[0.1, 0.5], [0.5, 0.5], [0.9, 0.5]]})


def test_un_vertice_fuori_dalla_foto_si_rifiuta():
    with pytest.raises(VelinaNonValida, match="fuori dalla foto"):
        Oggetto.da_dizionario({"perimetro": [[0.1, 0.1], [1.2, 0.1], [0.5, 0.6]]})


def test_con_piu_edifici_ognuno_vuole_il_suo_perimetro():
    """Caso: l'edificio B parte senza perimetro e il modello lo mette dove capita."""
    with pytest.raises(VelinaNonValida, match="edificio B"):
        Velina.da_dizionario(_velina(oggetti=[{"vista": "", "perimetro": PERIMETRO}, {"vista": "b.png"}]))


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


def test_il_perimetro_basta_a_dire_dove_va_senza_rettangolo():
    """Caso: col perimetro si doveva disegnare per forza anche il rettangolo; lo schizzo da solo non dice dove."""
    velina = _velina(oggetti=[{"vista": "", "perimetro": PERIMETRO}])
    assert Contesto.da_dizionario({"file": "x.png", "velina": velina}).area is None
    with pytest.raises(ContestoNonValido, match="perimetro"):
        Contesto.da_dizionario({"file": "x.png", "velina": _velina()})


def test_senza_velina_il_prompt_e_quello_di_prima():
    """Caso: la velina cambia anche il prompt di chi non la usa (il risultato di Arceto deve restare)."""
    assert Contesto("x.png", ((0.3, 0.4), (0.6, 0.8))).prompt("legno") == \
        blocchi.componi_contesto("zenitale", materiali="legno")


def test_il_prompt_numera_le_immagini_e_dice_i_colori_usati():
    velina = Velina.da_dizionario(_velina(tratti=[_tratto("verde")], oggetti=[
        {"vista": "", "perimetro": PERIMETRO}, {"vista": "b.png", "perimetro": PERIMETRO_B}]))
    testo = Contesto("x.png", None, inquadratura="terra", velina=velina).prompt()
    assert "each magenta outline with a letter is the footprint at ground level" in testo
    assert "Image 2 is the same site seen through a sheet of tracing paper" in testo
    assert "green marks" in testo and "red marks" not in testo
    assert "image 3 is building A, image 4 is building B" in testo
    assert "remove every outline and letter, and show no tracing paper and no marks" in testo
    assert blocchi.INQUADRATURE["terra"].testo in testo


def test_un_edificio_col_perimetro_e_senza_schizzo_manda_due_immagini():
    """Caso: la velina vuota parte lo stesso e il modello copia il suo aspetto slavato."""
    velina = Velina.da_dizionario({"oggetti": [{"vista": "", "perimetro": PERIMETRO}]})
    contesto = Contesto("x.png", None, velina=velina)
    testo = contesto.prompt()
    assert "the magenta outline marked A is the footprint of the new building" in testo
    assert "tracing paper" not in testo and "Image 2 is a view of the new building" in testo
    assert contesto.quante_immagini() == 2


def test_con_schizzo_o_perimetri_la_misura_fuori_area_non_si_fa():
    """Caso: lo schizzo cambia il luogo apposta, e il perimetro e' solo la base: l'edificio sale sopra di lui.
    Un numero «fuori area» sarebbe falso (regola 3)."""
    contesto = Contesto("x.png", ((0.3, 0.4), (0.6, 0.8)), velina=Velina.da_dizionario(_velina()))
    assert contesto.misura(_jpeg(), _jpeg()) is None
    col_perimetro = Contesto("x.png", None, velina=Velina.da_dizionario({"oggetti": [{"vista": "", "perimetro": PERIMETRO}]}))
    assert col_perimetro.misura(_jpeg(), _jpeg()) is None


# --- disegno -----------------------------------------------------------------


def test_la_velina_sbiadisce_la_foto_e_ci_mette_lo_schizzo():
    foto = _jpeg(400, 300, (20, 20, 20))
    disegnata = _apri(modulo_velina.disegna(foto, Velina.da_dizionario(_velina())))
    assert disegnata.size == (400, 300)
    r, g, b = disegnata.getpixel((10, 290))  # lontano dal tratto: solo carta sopra la foto
    assert r > 100 and abs(r - b) < 30
    assert disegnata.getpixel((200, 150))[0] > 150 > disegnata.getpixel((200, 150))[1]  # il tratto rosso


def test_la_gomma_toglie_lo_schizzo_anche_nell_immagine_che_parte():
    """Caso: Riccardo, 2026-11-23, «gomma non funziona»: a schermo cancella, ma il modello vede ancora il segno."""
    foto = _jpeg(400, 300, (20, 20, 20))
    gomma = {"colore": "profilo", "tipo": "tratto", "spessore": 0.12, "punti": [[0.5, 0.5]], "gomma": True}
    con_gomma = _apri(modulo_velina.disegna(foto, Velina.da_dizionario(_velina(tratti=[_tratto(), gomma]))))
    senza = _apri(modulo_velina.disegna(foto, Velina.da_dizionario(_velina(tratti=[]))))
    assert con_gomma.getpixel((200, 150)) == senza.getpixel((200, 150))  # al centro il rosso non c'e' piu'
    assert con_gomma.getpixel((100, 75))[0] > 150 > con_gomma.getpixel((100, 75))[1]  # fuori dalla gomma resta


def test_il_perimetro_parte_magenta_con_la_lettera_sulla_foto_pulita():
    foto = _jpeg(400, 300, (40, 120, 200))
    velina = Velina.da_dizionario({"oggetti": [{"vista": "", "perimetro": PERIMETRO}]})
    segnata = _apri(modulo_velina.perimetri(foto, velina))
    assert segnata.size == (400, 300)
    r, g, b = segnata.getpixel((int(0.2 * 400), int(0.5 * 300)))  # un vertice
    assert r > 200 and b > 200 and g < 100
    assert segnata.getpixel((20, 20)) == _apri(foto).getpixel((20, 20))  # lontano: la foto com'e'
    assert modulo_velina.perimetri(foto, Velina()) == foto


# --- coda e Studio ------------------------------------------------------------


def _richiesta_velina(studio, nome, velina, **altro):
    dettagli = {"area": False, "velina": any(not t.get("gomma") for t in velina.get("tratti", [])),
                "edifici": len(velina["oggetti"]), "perimetri": any(o.get("perimetro") for o in velina["oggetti"])}
    richiesta = _richiesta(studio, _contesto(nome, area=None, velina=velina), **altro)
    richiesta["destinazione_mostrata"] = studio.destinazione(NANO, contesto=dettagli)["destinazione"]
    return richiesta


def test_due_edifici_partono_nell_ordine_foto_pulita_velina_viste(cartella, chiamate):
    """Caso: la velina sbiadita va per prima e il render esce slavato, o una vista si perde."""
    (cartella / "vista-2.png").write_bytes(vista_shaded(500, 400))
    studio = _studio(cartella, chiamate)
    foto = _jpeg()
    nome = studio.carica_contesto(foto)["nome"]
    velina = _velina(oggetti=[{"vista": "", "perimetro": PERIMETRO}, {"vista": "vista-2.png", "perimetro": PERIMETRO_B}])
    risposta = studio.invia(_richiesta_velina(studio, nome, velina))
    lavoro = json.loads((cartella / "lavori" / "in-attesa" / f"{risposta['identificativo']}.json").read_text("utf-8"))
    assert lavoro["contesto"]["velina"]["oggetti"][1]["vista"] == str(cartella / "vista-2.png")
    Coda(cartella, crea_provider=lambda _n: ProviderConDueImmagini(chiamate), dire=lambda _t: None).esegui_uno()
    (richiesta,) = chiamate
    pulita = _apri(richiesta.immagine)
    assert pulita.size == (400, 300) and pulita.tobytes() != _apri(foto).tobytes()  # la foto coi perimetri
    assert pulita.getpixel((20, 20)) == _apri(foto).getpixel((20, 20))  # fuori dai perimetri resta com'e'
    seconda, *viste = richiesta.immagini_in_piu
    assert _apri(seconda).size == (400, 300) and seconda != richiesta.immagine
    assert viste == [(cartella / "vista-1.png").read_bytes(), (cartella / "vista-2.png").read_bytes()]
    assert "image 3 is building A, image 4 is building B" in richiesta.prompt
    assert leggi_stato(cartella, risposta["identificativo"])["stato"] == "fatto"


def test_la_destinazione_conta_le_immagini_della_velina(cartella, chiamate):
    """Caso: lo Studio annuncia due immagini e ne partono quattro (regola 5)."""
    studio = _studio(cartella, chiamate)
    dest = studio.destinazione(NANO, contesto={"area": False, "velina": True, "edifici": 2, "perimetri": True})
    assert dest["immagini"] == 4
    assert dest["cosa_parte"].startswith("Partono 4 immagini: prima la foto del luogo pulita, "
                                         "con i perimetri alla base segnati in magenta")
    assert "velina" in dest["cosa_parte"] and "edifici A e B" in dest["cosa_parte"]
    assert studio.destinazione(NANO, contesto=True)["immagini"] == 2


def test_un_edificio_in_piu_che_non_e_una_vista_si_rifiuta(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    velina = _velina(oggetti=[{"vista": "", "perimetro": PERIMETRO}, {"vista": "../segreto.png", "perimetro": PERIMETRO_B}])
    with pytest.raises(Exception, match="non e' il nome di una vista"):
        studio.invia(_richiesta_velina(studio, nome, velina))


def test_una_vista_in_piu_sparita_ferma_il_lavoro_prima_di_partire(cartella, chiamate):
    (cartella / "vista-2.png").write_bytes(vista_shaded(500, 400))
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    risposta = studio.invia(_richiesta_velina(studio, nome, _velina(oggetti=[{"vista": "", "perimetro": PERIMETRO}, {"vista": "vista-2.png", "perimetro": PERIMETRO_B}])))
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
    """Caso: il prima/dopo del passo 4 fa partire un render, o mostra una foto diversa da quella che parte."""
    studio = _studio(cartella, chiamate)
    nome = studio.carica_contesto(_jpeg())["nome"]
    velina = {"oggetti": [{"vista": "", "perimetro": PERIMETRO}]}
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
