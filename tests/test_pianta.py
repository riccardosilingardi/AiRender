"""Pianta, planimetria e planivolumetrico (2026-11-09, PR 6 dei flussi).

Una quarta scena per i disegni visti dall'alto; «Arreda per zone» nel
Ritocca su una pianta; il punto di vista dalla pianta senza Allplan (la
pianta e la pianta col punto rosso, due immagini). Nessuna rete: il provider
e' un finto. Che il modello tenga muri e aperture, arredi a misura o una
stanza credibile dal punto rosso non lo dice nessun test.
"""

from __future__ import annotations

import io

import pytest
from PIL import Image

from conftest import vista_wireframe
from core import blocchi, coda as modulo_coda, config, idoneita, immagine, punto as modulo_punto
from core.errori import ErroreAirender
from core.studio.servizio import NOME_PUNTO, RichiestaStudioNonValida
from core.studio.servizio import Studio
from test_passi import NANO, ProviderCheRende, _dest, cartella, chiamate  # noqa: F401


class ProviderDueImmagini(ProviderCheRende):
    """Nano Banana 2 riceve piu' immagini: la pianta e la pianta col punto rosso."""

    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderDueImmagini(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate):
    return modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderDueImmagini(chiamate), dire=lambda _t: None)

PIANTA = "pianta-1.png"
PUNTO = {"x": 0.3, "y": 0.6, "verso_x": 0.7, "verso_y": 0.4, "tipo": "edificio", "stile": "giorno"}
ZONA = {"forma": "rettangolo", "punti": [[0.1, 0.1], [0.4, 0.5]], "stanza": "soggiorno"}


@pytest.fixture
def pianta(cartella, chiamate):
    """Una pianta a linee nere su fondo bianco, resa dalla vista con il preset materico (passo 1)."""
    (cartella / PIANTA).write_bytes(vista_wireframe(800, 600))
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    scelte = blocchi.da_preset("pianta-materica").a_dizionario()
    uno = studio.invia({"vista": PIANTA, "scelte": scelte, "preset": "pianta-materica", "modello": NANO,
                        "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    return studio, coda, uno


# --- i blocchi ------------------------------------------------------------------


def test_ogni_tipo_di_pianta_ha_i_suoi_preset_e_tiene_il_disegno():
    tipi = {p.scelte.tipo for p in blocchi.PRESET_STILE.values() if p.scelte.scena == blocchi.PIANTA}
    assert tipi == {blocchi.EDIFICIO, blocchi.SITO, blocchi.VOLUMI}
    for p in blocchi.PRESET_STILE.values():
        if p.scelte.scena != blocchi.PIANTA:
            assert p.scelte.tipo is None
            continue
        prompt = blocchi.componi(p.scelte)
        assert prompt.startswith(blocchi.FEDELTA_PIANTA["bilanciata"].testo)
        assert blocchi.TIPI_PIANTA[p.scelte.tipo].testo in prompt
        assert prompt.endswith(blocchi.COSA_EVITARE_PIANTA.testo)
        assert blocchi.REGOLA_FISSA.testo not in prompt and "architectural photography" not in prompt


def test_il_tipo_vale_solo_per_una_pianta_e_una_pianta_non_prende_le_rese():
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi(blocchi.Scelte(scena=blocchi.ESTERNO, tipo=blocchi.SITO))
    with pytest.raises(blocchi.SceltaNonValida) as errore:
        blocchi.componi(blocchi.da_preset("pianta-materica", resa="schizzo"))
    assert "stile della tavola" in errore.value.fatto
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi(blocchi.da_preset("pianta-materica", tipo="sezione"))


def test_l_assonometria_e_l_unico_stile_che_alza_la_vista():
    assert "unless the style below asks for an axonometric view" in blocchi.FEDELTA_PIANTA["bilanciata"].testo
    assert "isometric" in blocchi.componi(blocchi.da_preset("pianta-assonometria"))
    assert "45 degrees" not in blocchi.componi(blocchi.da_preset("pianta-materica"))


def test_un_passo_su_una_pianta_chiude_con_il_cosa_evitare_della_pianta():
    prompt = blocchi.componi_richieste(blocchi.PIANTA, ["alberi lungo il confine"])
    assert blocchi.SCENA[blocchi.PIANTA].testo in prompt and prompt.endswith(blocchi.COSA_EVITARE_PIANTA.testo)
    con = blocchi.aggiungi_richieste(blocchi.componi(blocchi.da_preset("planimetria-drone")), ["un viale"])
    assert con.endswith(blocchi.COSA_EVITARE_PIANTA.testo) and "un viale" in con


def test_arreda_dice_stanza_stile_misure_e_cosa_non_toccare():
    nota = blocchi.nota_arreda("camera", "nordico")
    assert "double bed" in nota and "Scandinavian" in nota and "80 cm" in nota
    assert nota.endswith("keep walls, openings and every other area unchanged")
    assert blocchi.nome_richiesta(nota) == "Arreda · camera, nordico"
    for stanza, stile in [("garage", "nordico"), ("camera", "barocco"), (None, "nordico")]:
        with pytest.raises(blocchi.SceltaNonValida):
            blocchi.nota_arreda(stanza, stile)


def test_il_punto_di_vista_da_una_pianta_e_un_interno_da_una_planimetria_un_esterno():
    assert blocchi.scena_punto(blocchi.EDIFICIO) == blocchi.INTERNO
    assert blocchi.scena_punto(blocchi.SITO) == blocchi.ESTERNO == blocchi.scena_punto(blocchi.VOLUMI)
    interno = blocchi.componi_punto_di_vista(blocchi.EDIFICIO, "sera", "parquet di rovere")
    assert interno.startswith(blocchi.PUNTO_DI_VISTA.testo) and "Materials: parquet di rovere." in interno
    assert f"{config.PUNTO_DI_VISTA_ALTEZZA_OCCHI_M} m" in interno and "red dot" in interno
    assert blocchi.componi_punto_di_vista(blocchi.SITO, "giorno").startswith(blocchi.PUNTO_DI_VISTA_SITO.testo)
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.componi_punto_di_vista(blocchi.EDIFICIO, "nebbia")


# --- idoneita': una pianta e' fatta di linee ----------------------------------------


def test_una_pianta_a_linee_non_e_un_wireframe_ma_una_vista_si():
    statistiche = immagine.misura(vista_wireframe(800, 600))
    assert not idoneita.valuta(statistiche).idonea
    assert idoneita.valuta(statistiche, blocchi.PIANTA).idonea
    piccola = immagine.misura(vista_wireframe(200, 150))
    assert not idoneita.valuta(piccola, blocchi.PIANTA).idonea


def test_lo_studio_dice_se_la_vista_va_bene_come_pianta(pianta):
    studio, *_ = pianta
    descrizione = studio.descrivi_vista(PIANTA)
    assert descrizione["idonea"] is False and descrizione["idonea_pianta"] is True
    assert studio.descrivi_vista(PIANTA, blocchi.PIANTA)["idonea"] is True


def test_la_stessa_pianta_con_un_preset_esterno_si_ferma_prima_di_partire(pianta, chiamate):
    studio, *_ = pianta
    prima = len(chiamate)
    scelte = blocchi.da_preset("rivista").a_dizionario()
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.invia({"vista": PIANTA, "scelte": scelte, "preset": "rivista", "modello": NANO,
                      "destinazione_mostrata": _dest(studio)})
    assert "wireframe" in errore.value.fatto and len(chiamate) == prima


def test_la_pianta_resa_e_un_passo_della_scena_pianta(pianta, chiamate):
    studio, _coda, uno = pianta
    passo = next(p for p in studio.passi(PIANTA)["passi"] if p["identificativo"] == uno)
    assert passo["scena"] == blocchi.PIANTA and passo["render"] and passo["nome"] == "Pianta, resa materica"
    assert chiamate[-1].prompt.startswith(blocchi.FEDELTA_PIANTA["bilanciata"].testo)


# --- Arreda per zone -----------------------------------------------------------------


def test_arreda_scrive_la_nota_di_ogni_zona_e_il_passo_si_chiama_arreda(pianta):
    studio, coda, uno = pianta
    zone = [ZONA, {"forma": "libera", "punti": [[0.5, 0.1], [0.9, 0.1], [0.9, 0.5]], "stanza": "cucina"}]
    altro = {"vista": PIANTA, "da": uno, "aree": zone, "arreda": {"stile": "contemporaneo"}}
    composto = studio.componi_ritocco(altro)
    assert composto["note"] == 2 and "living room" in composto["note_aree"][0] and "kitchen" in composto["note_aree"][1]
    rit = studio.invia_ritocco({**altro, "modello": NANO, "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(PIANTA)["passi"] if p["identificativo"] == rit)
    assert passo["nome"] == "Arreda · 2 zone" and passo["render"]


@pytest.mark.parametrize("zone, parola", [
    ([], "zone"),
    ([{**ZONA, "stanza": "garage"}], "Zona 1"),
    ([{"forma": "pennello", "azione": "aggiungi", "spessore": 0.05, "punti": [[0.5, 0.5]], "stanza": "bagno"}],
     "rettangolo"),
])
def test_arreda_senza_zone_con_una_stanza_sconosciuta_o_col_pennello_si_ferma(pianta, chiamate, zone, parola):
    studio, _coda, uno = pianta
    prima = len(chiamate)
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.componi_ritocco({"vista": PIANTA, "da": uno, "aree": zone, "arreda": {"stile": "nordico"}})
    assert parola in errore.value.fatto and len(chiamate) == prima


def test_arreda_non_vale_su_un_render_in_prospettiva(cartella, chiamate):
    from test_passi import VISTA, _genera
    studio, coda = _studio(cartella, chiamate), _coda(cartella, chiamate)
    uno = _genera(studio); coda.esegui_uno()
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.componi_ritocco({"vista": VISTA, "da": uno, "aree": [ZONA], "arreda": {"stile": "nordico"}})
    assert "pianta" in errore.value.fatto


# --- punto di vista dalla pianta -----------------------------------------------------


def test_il_punto_rosso_si_disegna_dove_si_sta_e_lascia_il_resto_com_e():
    pianta = Image.new("RGB", (400, 300), (255, 255, 255))
    uscita = io.BytesIO(); pianta.save(uscita, format="PNG")
    disegnata = Image.open(io.BytesIO(modulo_punto.disegna(uscita.getvalue(), modulo_punto.da_dizionario(PUNTO))))
    assert disegnata.size == (400, 300)
    r, g, b = disegnata.getpixel((120, 180))  # il punto: 0.3 x 400, 0.6 x 300
    assert r > 200 and g < 80 and b < 80
    assert disegnata.getpixel((390, 10)) == (255, 255, 255)  # lontano dal cono, bianco come prima


@pytest.mark.parametrize("sbagliato, parola", [
    ({**PUNTO, "x": 1.5}, "fra 0 e 1"),
    ({**PUNTO, "verso_x": 0.3, "verso_y": 0.6}, "troppo corto"),
    ({**PUNTO, "tipo": "sezione"}, "tipo"),
    ({**PUNTO, "stile": "nebbia"}, "stile"),
    (None, "non e' arrivato"),
])
def test_un_punto_di_vista_che_non_dice_dove_guardi_si_ferma(sbagliato, parola):
    with pytest.raises(ErroreAirender) as errore:
        modulo_punto.da_dizionario(sbagliato)
    assert parola in errore.value.fatto


def test_il_punto_di_vista_manda_la_pianta_e_la_pianta_col_punto_rosso(pianta, chiamate):
    studio, coda, uno = pianta
    composto = studio.componi_punto({"vista": PIANTA, "da": uno, "punto": PUNTO, "modello": NANO})
    assert composto["scena"] == blocchi.INTERNO and composto["prompt"].startswith(blocchi.PUNTO_DI_VISTA.testo)
    due = studio.invia_punto({"vista": PIANTA, "da": uno, "punto": PUNTO, "modello": NANO,
                              "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    inviata = chiamate[-1]
    assert len(inviata.immagini_in_piu) == 1 and inviata.prompt == composto["prompt"]
    assert inviata.immagini_in_piu[0] != inviata.immagine
    passo = next(p for p in studio.passi(PIANTA)["passi"] if p["identificativo"] == due)
    assert passo["nome"] == NOME_PUNTO and passo["immaginata"] is True and passo["scena"] == blocchi.INTERNO
    assert passo["da"] == uno and "immaginati il modello" in passo["riassunto"]
    lavoro = modulo_coda.Lavoro.da_dizionario(modulo_coda.Lavoro.da_dizionario(
        {**_lavoro_scritto(studio, due)}).a_dizionario())
    assert lavoro.formato == modulo_coda.FORMATO_PUNTO and lavoro.punto_di_vista.stile == "giorno"


def test_il_punto_di_vista_parte_anche_dalla_vista_se_e_gia_una_pianta(pianta, chiamate):
    studio, coda, _uno = pianta
    tre = studio.invia_punto({"vista": PIANTA, "da": "0", "punto": {**PUNTO, "tipo": "sito"}, "modello": NANO,
                              "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(PIANTA)["passi"] if p["identificativo"] == tre)
    assert passo["render"] and passo["scena"] == blocchi.ESTERNO and passo["da"] == "0"
    assert chiamate[-1].prompt.startswith(blocchi.PUNTO_DI_VISTA_SITO.testo)


def test_variante_di_un_punto_di_vista_rimanda_il_punto_rosso(pianta, chiamate):
    studio, coda, uno = pianta
    due = studio.invia_punto({"vista": PIANTA, "da": uno, "punto": PUNTO, "modello": NANO,
                              "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    studio.rifai(due, {"destinazione_mostrata": _dest(studio)})
    coda.esegui_uno()
    assert len(chiamate[-1].immagini_in_piu) == 1 and chiamate[-1].prompt.startswith(blocchi.PUNTO_DI_VISTA.testo)


def test_il_punto_di_vista_da_un_render_in_prospettiva_si_rifiuta(pianta, chiamate):
    studio, coda, uno = pianta
    due = studio.invia_punto({"vista": PIANTA, "da": uno, "punto": PUNTO, "modello": NANO,
                              "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.componi_punto({"vista": PIANTA, "da": due, "punto": PUNTO})
    assert "pianta" in errore.value.fatto


def test_un_lavoro_punto_con_altro_dentro_non_si_legge():
    dati = {"formato": modulo_coda.FORMATO_PUNTO, "identificativo": "x", "vista": "v.png", "provider": "prova",
            "modello": NANO, "destinazione": "d", "punto_di_vista": PUNTO, "richieste": ["e anche questo"]}
    with pytest.raises(modulo_coda.LavoroNonValido):
        modulo_coda.Lavoro.da_dizionario(dati)


def test_il_catalogo_dice_stanze_stili_e_che_in_allplan_non_c_e_ancora(pianta):
    studio, *_ = pianta
    catalogo = studio.catalogo()
    assert [p["id"] for p in catalogo["scene"]["pianta"]["preset"]][:2] == ["pianta-materica", "pianta-assonometria"]
    assi = {a["id"]: a for a in catalogo["scene"]["pianta"]["assi"]}
    assert assi["tipo"]["titolo"] == "Che disegno è" and assi["look"]["titolo"] == "Stile della tavola"
    assert "cielo" not in assi and "persone" not in assi
    piante = catalogo["pianta"]
    assert {s["id"] for s in piante["stanze"]} == set(blocchi.STANZE_ARREDA)
    assert piante["allplan"] is False


def _lavoro_scritto(studio, identificativo):
    lavoro, _cartella = studio._lavoro(identificativo)
    return lavoro.a_dizionario()
