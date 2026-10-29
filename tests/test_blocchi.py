"""La composizione del prompt a blocchi, dalla bozza 4 (docs/ui/blocchi-stile-bozza.md)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from core import blocchi, config
from core.blocchi import Scelte, SceltaNonValida, componi, da_preset

BOZZA = Path(__file__).resolve().parent.parent / "docs" / "ui" / "blocchi-stile-bozza.md"


def _righe_bozza() -> set[tuple[str, str]]:
    """(id, testo per il modello), letti dalle tabelle della bozza. Lo stesso id
    puo' stare in due assi (citta' e' un intorno e una vista dalle finestre)."""
    righe = set()
    for riga in BOZZA.read_text(encoding="utf-8").splitlines():
        trovata = re.match(r"\| `([^`]+)` \| [^|]+ \| (.+?) \| (\d+) \|$", riga)
        if trovata:
            assert len(trovata.group(2)) == int(trovata.group(3)), trovata.group(1)
            righe.add((trovata.group(1), trovata.group(2)))
    return righe


def test_i_testi_dei_blocchi_sono_quelli_della_bozza():
    """Caso: un blocco riscritto nel codice e non nella bozza, e i due documenti divergono."""
    bozza = _righe_bozza()
    nel_codice = set()
    for elenco in (blocchi.SCENA, blocchi.LOOK, blocchi.LUCE_ESTERNI, blocchi.CIELO,
                   blocchi.INTORNO, blocchi.VERDE, blocchi.LUCE_INTERNI, blocchi.FUORI, blocchi.ARREDO,
                   blocchi.PERSONE, blocchi.QUALITA):
        for blocco in elenco.values():
            nel_codice.add((blocco.identificativo, blocco.testo))
    assert nel_codice == bozza


def test_nessun_blocco_si_presenta_come_provato():
    """Caso: un blocco mai mandato al modello appare a schermo come misurato."""
    tutti = [blocchi.REGOLA_FISSA, blocchi.COSA_EVITARE]
    for elenco in (blocchi.LOOK, blocchi.LUCE_ESTERNI, blocchi.CIELO, blocchi.QUALITA,
                   blocchi.INTORNO, blocchi.VERDE, blocchi.PERSONE, blocchi.FUORI, blocchi.ARREDO):
        tutti += list(elenco.values())
    assert {b.origine for b in tutti} == {config.SCELTA}


def test_l_esempio_completo_della_bozza_esce_identico():
    """Caso: l'ordine dei blocchi cambia nel codice e il prompt non e' piu' quello deciso."""
    testo = BOZZA.read_text(encoding="utf-8").split("Esempio completo")[1]
    atteso = testo.split("\n> ", 1)[1].split("\n")[0]
    scelte = da_preset(
        "ora-blu",
        materiali="white lime plaster walls, dark oak window frames, light grey stone base",
    )
    assert componi(scelte) == atteso


def test_le_lunghezze_dei_preset_sono_quelle_misurate_nella_bozza():
    """Caso: un preset compone blocchi diversi da quelli della tabella."""
    attese = {
        "rivista": 832, "luce-calda": 896, "pellicola-morbida": 784, "urbano": 921,
        "ora-blu": 904, "notte-luna": 904, "pioggia": 945, "autunno": 991,
        "interno-rivista": 825, "interno-caldo": 834, "interno-pellicola": 803,
        "interno-sera": 835, "interno-notte": 804, "interno-vissuto": 925,
    }
    misurate = {k: len(componi(p.scelte)) for k, p in blocchi.PRESET_STILE.items()}
    assert misurate == attese


def test_ordine_fisso_regola_in_testa_e_cosa_evitare_in_coda():
    """Caso: i materiali finiscono dopo la luce e il modello li pesa meno."""
    prompt = componi(da_preset("interno-sera", materiali="parquet di rovere"))
    assert prompt.startswith(blocchi.REGOLA_FISSA.testo)
    assert prompt.endswith(blocchi.COSA_EVITARE.testo)
    posizioni = [prompt.index(t) for t in (
        "interior space", "Materials: parquet di rovere.", "Leica", "Early evening",
        "city view", "Do not add furniture", "No people", "natural detail",
    )]
    assert posizioni == sorted(posizioni)


def test_un_blocco_cambiato_non_disfa_gli_altri():
    """Caso: cambiare il cielo riporta la luce a quella predefinita."""
    prima = componi(da_preset("ora-blu"))
    dopo = componi(da_preset("ora-blu", cielo="neve"))
    assert prima.replace("Clear sky.", blocchi.CIELO["neve"].testo) == dopo


def test_la_qualita_32k_e_un_blocco_solo():
    """Caso: «Altissima definizione» tocca altro oltre alla qualita' e il confronto A/B non vale."""
    base = componi(da_preset("rivista"))
    alta = componi(da_preset("rivista", qualita="32k"))
    assert base.replace(blocchi.QUALITA["base"].testo, blocchi.QUALITA["32k"].testo) == alta


def test_il_cielo_di_un_interno_si_rifiuta_con_cosa_fare():
    """Caso: un asse dell'altra scena sparisce in silenzio e l'utente crede di averlo mandato."""
    with pytest.raises(SceltaNonValida) as errore:
        componi(da_preset("interno-rivista", cielo="neve"))
    assert "interno" in errore.value.fatto
    assert "Togli cielo" in errore.value.cosa_fare


def test_una_scelta_che_non_esiste_dice_quali_esistono():
    """Caso: un id scritto male da chi crea il lavoro."""
    with pytest.raises(SceltaNonValida) as errore:
        componi(Scelte(scena="esterno", luce="tramonto"))
    assert "mezzogiorno" in errore.value.cosa_fare


def test_un_preset_che_non_esiste_dice_quali_esistono():
    with pytest.raises(SceltaNonValida) as errore:
        da_preset("barocco")
    assert "ora-blu" in errore.value.cosa_fare


def test_otto_preset_esterni_e_sei_interni():
    """Caso: la griglia dello Studio promette 8 + 6 preset (DESIGN.md)."""
    scene = [p.scelte.scena for p in blocchi.PRESET_STILE.values()]
    assert scene.count("esterno") == 8 and scene.count("interno") == 6


def test_senza_materiali_la_riga_materiali_non_parte():
    """Caso: "Materials: ." finisce nel prompt quando l'utente non ha scritto niente."""
    assert "Materials" not in componi(da_preset("rivista", materiali="   "))


# --- bozza 4: intorno, verde, persone «poche» --------------------------------


def test_intorno_verde_e_persone_hanno_le_voci_del_mockup():
    assert list(blocchi.INTORNO) == ["niente", "citta", "periferia", "campagna"]
    assert list(blocchi.VERDE) == ["nessuno", "poco", "rigoglioso"]
    assert list(blocchi.PERSONE) == ["nessuna", "poche", "movimento"]


def test_ogni_blocco_che_aggiunge_dice_di_non_coprire_l_edificio():
    """Caso: un albero o una persona davanti a una finestra cambiano il disegno."""
    attesi = {"citta", "periferia", "campagna", "poco", "rigoglioso", "poche", "movimento",
              "verde", "leggero"}
    aggiunte = set()
    for elenco in (blocchi.INTORNO, blocchi.VERDE, blocchi.PERSONE, blocchi.FUORI, blocchi.ARREDO):
        for blocco in elenco.values():
            if blocco.aggiunge:
                aggiunte.add(blocco.identificativo)
                assert blocco.testo.endswith(f"; {blocchi.NON_COPRIRE}."), blocco.identificativo
            else:
                assert blocchi.NON_COPRIRE not in blocco.testo
    assert aggiunte == attesi


def test_il_verde_sta_subito_dopo_l_intorno_e_prima_delle_persone():
    prompt = componi(da_preset("rivista", intorno="citta", verde="poco", persone="poche"))
    posizioni = [prompt.index(t) for t in (
        blocchi.CIELO["sereno"].testo, blocchi.INTORNO["citta"].testo,
        blocchi.VERDE["poco"].testo, blocchi.PERSONE["poche"].testo, blocchi.QUALITA["base"].testo,
    )]
    assert posizioni == sorted(posizioni)


@pytest.mark.parametrize("asse,prima,dopo", [
    ("intorno", "niente", "campagna"),
    ("verde", "nessuno", "rigoglioso"),
    ("persone", "nessuna", "poche"),
])
def test_un_asse_nuovo_cambia_solo_il_suo_blocco(asse, prima, dopo):
    """Caso: scegliere «Poche» persone tocca anche il verde o l'intorno."""
    elenco = blocchi.voci(asse, "esterno")
    base = componi(da_preset("rivista"))
    cambiato = componi(da_preset("rivista", **{asse: dopo}))
    assert base.replace(elenco[prima].testo, elenco[dopo].testo) == cambiato


def test_il_verde_di_un_interno_si_rifiuta():
    with pytest.raises(SceltaNonValida) as errore:
        componi(da_preset("interno-rivista", verde="poco"))
    assert "Togli verde" in errore.value.cosa_fare


def test_i_preset_esterni_non_aggiungono_alberi():
    """Caso: «sfondo neutro» senza piu' la parola trees, e il modello torna ad aggiungere alberi."""
    for preset in blocchi.PRESET_STILE.values():
        if preset.scelte.scena == "esterno":
            assert preset.scelte.verde == "nessuno"
            assert blocchi.VERDE["nessuno"].testo in componi(preset.scelte)


def test_un_passo_manda_solo_quello_che_cambia():
    """Caso: il secondo passo della catena rimanda tutto lo stile e il render cambia ancora look."""
    passo = blocchi.componi_passo("esterno", {"persone": "poche", "verde": "poco"})
    assert passo.startswith(blocchi.REGOLA_FISSA.testo)
    assert passo.endswith(blocchi.COSA_EVITARE.testo)
    assert passo.index("A few trees") < passo.index("Two or three people")
    assert "Canon" not in passo and "Materials" not in passo


def test_un_passo_vuoto_o_con_un_asse_sconosciuto_si_rifiuta():
    with pytest.raises(SceltaNonValida):
        blocchi.componi_passo("esterno", {})
    with pytest.raises(SceltaNonValida) as errore:
        blocchi.componi_passo("esterno", {"alberi": "tanti"})
    assert "verde" in errore.value.cosa_fare
    with pytest.raises(SceltaNonValida):
        blocchi.componi_passo("interno", {"verde": "poco"})
