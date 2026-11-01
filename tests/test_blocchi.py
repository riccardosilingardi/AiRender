"""La composizione del prompt a blocchi, dalla bozza 7 (docs/ui/blocchi-stile-bozza.md)."""

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
                   blocchi.PERSONE, blocchi.QUALITA, blocchi.FEDELTA,
                   blocchi.RESA, blocchi.EVITARE_DA_RESA,
                   blocchi.FEDELTA_PRODOTTO, blocchi.LOOK_PRODOTTO, blocchi.LUCE_PRODOTTO,
                   blocchi.SFONDO, blocchi.QUALITA_PRODOTTO):
        for blocco in elenco.values():
            nel_codice.add((blocco.identificativo, blocco.testo))
    assert nel_codice == bozza


def test_nessun_blocco_si_presenta_come_provato():
    """Caso: un blocco mai mandato al modello appare a schermo come misurato."""
    tutti = [blocchi.REGOLA_FISSA, blocchi.COSA_EVITARE]
    for elenco in (blocchi.LOOK, blocchi.LUCE_ESTERNI, blocchi.CIELO, blocchi.QUALITA,
                   blocchi.INTORNO, blocchi.VERDE, blocchi.PERSONE, blocchi.FUORI, blocchi.ARREDO,
                   blocchi.FEDELTA, blocchi.RESA, blocchi.EVITARE_DA_RESA,
                   blocchi.FEDELTA_PRODOTTO, blocchi.LOOK_PRODOTTO, blocchi.LUCE_PRODOTTO,
                   blocchi.SFONDO, blocchi.QUALITA_PRODOTTO):
        tutti += list(elenco.values())
    tutti.append(blocchi.COSA_EVITARE_PRODOTTO)
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
        "arredo-catalogo": 1037, "arredo-studio": 1059, "arredo-editoriale": 1023,
        "arredo-dettaglio": 1023, "arredo-controluce": 1010, "arredo-ambientato": 1064,
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


# --- fedelta' al disegno (bozza 6) -------------------------------------------


def test_la_fedelta_predefinita_lascia_il_prompt_di_prima():
    """Caso: la bozza 6 cambia in silenzio tutti i prompt, e i render di prima non si confrontano piu'."""
    assert Scelte().fedelta == blocchi.FEDELTA_PREDEFINITA == "bilanciata"
    assert blocchi.FEDELTA["bilanciata"].testo == blocchi.REGOLA_FISSA.testo
    assert componi(da_preset("rivista")).startswith(blocchi.REGOLA_FISSA.testo + " The subject")


@pytest.mark.parametrize("fedelta", ["rigida", "libera"])
def test_la_fedelta_cambia_solo_la_regola_in_testa(fedelta):
    """Caso: la fedelta' tocca anche gli altri blocchi, e il confronto del banco non dice niente."""
    base = componi(da_preset("ora-blu"))
    altra = componi(da_preset("ora-blu", fedelta=fedelta))
    assert altra.startswith(blocchi.FEDELTA[fedelta].testo + " The subject")
    assert altra[len(blocchi.FEDELTA[fedelta].testo):] == base[len(blocchi.REGOLA_FISSA.testo):]


def test_una_fedelta_che_non_esiste_si_rifiuta_con_le_voci_possibili():
    with pytest.raises(SceltaNonValida) as errore:
        componi(Scelte(fedelta="morbida"))
    assert "rigida" in errore.value.cosa_fare and "libera" in errore.value.cosa_fare


def test_la_fedelta_vale_anche_per_gli_interni():
    assert componi(da_preset("interno-rivista", fedelta="rigida")).startswith(blocchi.FEDELTA["rigida"].testo)


# --- rese (bozza 7) -------------------------------------------------------------


def test_fotorealistico_lascia_il_prompt_di_prima():
    """Caso: aggiungere le rese cambia in silenzio tutti i prompt fotografici."""
    assert Scelte().resa == blocchi.FOTO
    prima = componi(da_preset("ora-blu", materiali="intonaco bianco"))
    assert componi(da_preset("ora-blu", materiali="intonaco bianco", resa="foto")) == prima
    assert prima.endswith(blocchi.COSA_EVITARE.testo)


@pytest.mark.parametrize("resa", ["plastico", "schizzo", "acquerello", "cinema"])
def test_una_resa_mette_la_sua_frase_e_spegne_quello_che_non_ha_senso(resa):
    scelte = da_preset("ora-blu", materiali="intonaco bianco", resa=resa)
    prompt = componi(scelte)
    assert blocchi.RESA[resa].testo in prompt
    for asse in ("look", "luce", "cielo", "intorno", "verde", "persone", "qualita"):
        testo = blocchi.blocco(asse, getattr(scelte, asse), "esterno").testo
        assert (testo in prompt) == (asse not in blocchi.SPENTI_DA_RESA[resa]), asse
    assert ("Materials:" in prompt) == ("materiali" not in blocchi.SPENTI_DA_RESA[resa])
    assert prompt.endswith(blocchi._evitare(resa).testo)


def test_il_plastico_non_si_dice_di_evitare_il_plastico():
    """Caso: «cosa evitare» chiede di evitare proprio il look della resa scelta."""
    assert "plastic" not in componi(da_preset("rivista", resa="plastico")).split("Avoid:")[1]


def test_una_resa_che_non_esiste_si_rifiuta():
    with pytest.raises(SceltaNonValida) as errore:
        componi(Scelte(resa="olio"))
    assert "schizzo" in errore.value.cosa_fare


def test_richieste_e_riferimento_entrano_prima_del_cosa_evitare_della_resa():
    base = componi(da_preset("rivista", resa="schizzo"))
    con = blocchi.aggiungi_riferimento(blocchi.aggiungi_richieste(base, ["due alberi"]))
    assert con.endswith(f"{blocchi.RIFERIMENTO_STILE.testo} {blocchi.EVITARE_DA_RESA['evitare-schizzo'].testo}")


# --- arredo come prodotto (bozza 8) ----------------------------------------


def test_l_esempio_dell_arredo_della_bozza_esce_identico():
    """Caso: l'ordine dei blocchi dell'arredo cambia nel codice e non nella bozza."""
    testo = BOZZA.read_text(encoding="utf-8").split("Esempio intero: arredo")[1]
    atteso = testo.split("\n> ", 1)[1].split("\n")[0]
    scelte = da_preset("arredo-dettaglio", materiali="natural oak frame, cognac leather seat")
    assert componi(scelte) == atteso


def test_ogni_scena_ha_i_suoi_preset():
    """Caso: lo switch della scena mostra preset di un'altra scena, o una scena resta senza."""
    per_scena = {s: [p for p in blocchi.PRESET_STILE.values() if p.scelte.scena == s] for s in blocchi.SCENE}
    assert {s: len(v) for s, v in per_scena.items()} == {"esterno": 8, "interno": 6, "prodotto": 6}


def test_un_arredo_tiene_il_pezzo_e_non_l_architettura():
    """Caso: un prodotto parte con la regola degli edifici e il modello non cambia lo sfondo."""
    prompt = componi(da_preset("arredo-catalogo"))
    assert prompt.startswith(blocchi.FEDELTA_PRODOTTO["bilanciata"].testo)
    assert blocchi.REGOLA_FISSA.testo not in prompt
    assert prompt.endswith(blocchi.COSA_EVITARE_PRODOTTO.testo)
    assert "architectural photography" not in prompt
    rigida = componi(da_preset("arredo-catalogo", fedelta="rigida"))
    assert rigida.startswith(blocchi.FEDELTA_PRODOTTO["rigida"].testo)


def test_un_arredo_rifiuta_persone_e_assi_delle_altre_scene():
    """Caso: persone o cielo compilati su un arredo spariscono in silenzio."""
    for cambio in ({"persone": "poche"}, {"cielo": "neve"}, {"fuori": "verde"}, {"luce": "notte"}):
        with pytest.raises(SceltaNonValida):
            componi(da_preset("arredo-catalogo", **cambio))
    with pytest.raises(SceltaNonValida):
        componi(da_preset("interno-rivista", sfondo="bianco"))


def test_il_plastico_spegne_lo_sfondo_dell_arredo():
    """Caso: il plastico ha il suo fondo grigio e lo sfondo scelto lo contraddice."""
    prompt = componi(da_preset("arredo-catalogo", resa="plastico"))
    assert blocchi.SFONDO["bianco"].testo not in prompt
    assert blocchi.RESA["plastico"].testo in prompt
