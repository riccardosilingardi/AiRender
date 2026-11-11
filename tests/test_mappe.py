"""«Tieni la geometria» a mappe: spigoli e profondita' della vista partono con la vista.

Le mappe le calcola la pagina (studio.js) sul computer di chi lavora: qui
si prova che il motore le prenda solo dalla cartella dei riferimenti, le
mandi per ultime verso lo stesso modello, le conti giuste nel prompt e
rifiuti i lavori del vecchio «Tieni la geometria» col ControlNet.
"""

from __future__ import annotations

import io
import importlib.util
import json
from pathlib import Path

import pytest
from PIL import Image

from core import blocchi, coda as modulo_coda, mappe as modulo_mappe
from core.coda import FATTO, Lavoro, LavoroNonValido, leggi_stato
from core.studio.servizio import MODELLI, RichiestaStudioNonValida, Studio
from test_passi import NANO, VISTA, ProviderCheRende, _dest, cartella, chiamate  # noqa: F401

KONTEXT = MODELLI[1].identificativo


class ProviderConMappe(ProviderCheRende):
    def accetta_piu_immagini(self, modello):
        return modello == NANO


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderConMappe(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate):
    return modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderConMappe(chiamate), dire=lambda _t: None)


def _genera(studio, **altro):
    return studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(),
                         "preset": "rivista", "modello": NANO, "destinazione_mostrata": _dest(studio),
                         **altro})["identificativo"]


def _png(colore) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (320, 200), colore).save(uscita, "PNG")
    return uscita.getvalue()


def _mappe(studio) -> dict:
    """Come fa la pagina: le carica fra i riferimenti e manda i nomi."""
    return {m: studio.carica_riferimento(_png(colore), f"{m}.png")["nome"]
            for m, colore in zip(modulo_mappe.MAPPE, ((255, 255, 255), (90, 90, 90)))}


def test_la_regola_conta_le_mappe_dal_numero_dato():
    testo = modulo_mappe.regola(5)
    assert "Image 5 is an edge map" in testo and "Image 6 is a depth map" in testo
    assert "Images 5-6 are construction guides only" in testo


def test_genera_con_la_spunta_manda_la_vista_e_poi_le_due_mappe(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    identificativo = _genera(studio, geometria=True, mappe=_mappe(studio))
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_MAPPE and scritto["formato_base"] == modulo_coda.FORMATO
    assert Lavoro.da_dizionario(scritto).mappe == tuple(scritto["mappe"])

    _coda(cartella, chiamate).esegui_uno()
    stato = leggi_stato(cartella, identificativo)
    assert stato["stato"] == FATTO and len(stato["mappe"]) == 2
    (richiesta,) = chiamate
    assert len(richiesta.immagini_in_piu) == 2
    with Image.open(io.BytesIO(richiesta.immagini_in_piu[0])) as spigoli:
        assert spigoli.getpixel((5, 5))[0] == 255  # numero-non-configurabile: il bianco degli spigoli finti
    assert modulo_mappe.regola(2) in richiesta.prompt


def test_con_i_rif_le_mappe_vengono_dopo_e_il_prompt_le_conta_dopo(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    rif = studio.carica_riferimento(_png((200, 10, 10)), "sedia.png")["nome"]
    identificativo = _genera(studio, geometria=True, mappe=_mappe(studio), inserti=[rif])
    lavoro = Lavoro.da_dizionario(json.loads(
        (cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8")))
    assert lavoro.prima_immagine_mappe() == 3
    _coda(cartella, chiamate).esegui_uno()
    (richiesta,) = chiamate
    assert len(richiesta.immagini_in_piu) == 3
    assert modulo_mappe.regola(3) in richiesta.prompt


def test_la_destinazione_dice_che_le_mappe_restano_sul_computer_e_sono_incluse(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    senza, con = studio.destinazione(NANO), studio.destinazione(NANO, geometria=True)
    assert senza["geometria"] is None
    assert con["immagini"] == senza["immagini"] + 2
    assert "misurato una volta" in con["geometria"]["costo"]  # chiave propria: token, regola 3
    assert "calcolate su questo computer" in con["geometria"]["destinazione"]
    assert con["cosa_parte"] == ("Partono 3 immagini: la vista, più le 2 mappe della vista "
                                 "(spigoli e profondità), calcolate sul tuo computer.")
    assert con["destinazione"] == senza["destinazione"]  # nessun servizio in piu'


def test_coi_crediti_airender_le_mappe_non_costano_crediti(cartella, chiamate):
    studio = Studio(cartella, provider="airender", crea_provider=lambda _n: ProviderConMappe(chiamate),
                    coda_attiva=lambda: True, apri=lambda _p: None)
    assert studio.destinazione(NANO, geometria=True)["geometria"]["costo"] == "incluso: nessun credito in più"


def test_il_conto_delle_immagini_con_le_mappe_vale_per_ogni_frase():
    from core.studio.servizio import _con_le_mappe, _cosa_parte  # pylint: disable=import-outside-toplevel
    assert _con_le_mappe(_cosa_parte(True, False), True).startswith("Partono 4 immagini: la vista e il riferimento")
    assert _con_le_mappe(_cosa_parte(False, False, inserti=2), True).startswith("Partono 5 immagini:")
    assert _con_le_mappe("Parte una immagine: la vista.", False) == "Parte una immagine: la vista."


def test_la_composizione_mostra_la_regola_delle_mappe(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    composto = studio.componi({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(), "geometria": True})
    assert modulo_mappe.regola(2) in composto["prompt"]


def test_un_modello_a_una_sola_immagine_non_riceve_le_mappe(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    assert "una sola immagine" in studio.destinazione(KONTEXT, geometria=True)["mappe_non_accettate"]
    assert studio.destinazione(NANO, geometria=True)["mappe_non_accettate"] is None


def test_senza_mappe_genera_non_parte_e_dice_di_aspettarle(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida, match="mappe della vista non sono arrivate"):
        _genera(studio, geometria=True)
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_una_mappa_fuori_dai_riferimenti_si_rifiuta(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida):
        _genera(studio, geometria=True, mappe={"spigoli": "../vista-1.png", "profondita": "../vista-1.png"})


def test_da_un_passo_le_mappe_si_rifiutano(cartella, chiamate):
    with pytest.raises(LavoroNonValido, match="Tieni la geometria"):
        modulo_coda.metti_in_coda(cartella, cartella / VISTA, blocchi.da_preset("rivista"),
                                  provider="prova", modello=NANO, parte_da="x", partenza=cartella / VISTA,
                                  mappe=(cartella / VISTA, cartella / VISTA),
                                  crea_provider=lambda _n: ProviderCheRende([]))


def test_un_file_del_formato_13_rotto_si_rifiuta(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    identificativo = _genera(studio, geometria=True, mappe=_mappe(studio))
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    for guasto in ({"mappe": []}, {"mappe": ["a.png"]}, {"formato_base": modulo_coda.FORMATO_FINALE},
                   {"partenza": "x.png", "parte_da": "y"}):
        with pytest.raises(LavoroNonValido):
            Lavoro.da_dizionario({**scritto, **guasto})


@pytest.mark.parametrize("formato", [modulo_coda.FORMATO_GEOMETRIA, modulo_coda.FORMATO_RIAGGANCIA])
def test_un_lavoro_del_vecchio_controlnet_si_rifiuta_e_dice_come_rifarlo(formato):
    with pytest.raises(LavoroNonValido, match="deployment non c'e' piu'") as errore:
        Lavoro.da_dizionario({"formato": formato, "identificativo": "x"})
    assert "Studio · Genera" in errore.value.cosa_fare


def test_lo_storico_dice_con_quali_mappe_ha_tenuto_la_geometria():
    assert Studio._nomi_controlli({"mappe": ["a", "b"]}) == "Spigoli + Profondità"  # pylint: disable=protected-access
    assert Studio._nomi_controlli({"destinazione_geometria": "x", "controlli_geometria": ["spigoli", "linee"]}) \
        == "Spigoli + Linee dritte (ControlNet)"  # pylint: disable=protected-access
    assert Studio._nomi_controlli({}) is None  # pylint: disable=protected-access


def test_lo_script_di_prova_mette_la_regola_dopo_il_preset():
    percorso = Path(__file__).resolve().parent.parent / "scripts" / "prova_mappe_nano.py"
    spec = importlib.util.spec_from_file_location("prova_mappe_nano", percorso)
    prova = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prova)
    testo = prova.prompt_con_mappe("PRESET")
    assert testo.startswith("PRESET") and modulo_mappe.regola(2) in testo
