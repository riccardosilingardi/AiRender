"""Cambia con le miniature (ora e mood) e Popola (2026-11-09, PR 3 dei flussi).

Piu' miniature scelte = un passo per miniatura, tutti figli dello stesso
render; Popola mette persone, alberi o auto dove dipinge l'utente (le note
dei tratti verdi del Ritocca) o dove decide il modello (un passo a parole).
Nessuna rete: il provider e' un finto. Che il modello rispetti ora, mood,
quantita' e scala non lo dice nessun test.
"""

from __future__ import annotations

import pytest

from core import blocchi, config
from core.errori import ErroreAirender
from core.studio.servizio import RichiestaStudioNonValida
from test_passi import NANO, VISTA, _dest, _per_numero, _studio, cartella, chiamate  # noqa: F401
from test_ritocca import base  # noqa: F401  (le fixture si usano per nome)

VERDE = {"forma": "pennello", "azione": "aggiungi", "spessore": 0.05, "punti": [[0.6, 0.7], [0.8, 0.7]]}
ROSSO = {"forma": "pennello", "azione": "togli", "spessore": 0.05, "punti": [[0.2, 0.2]]}
PERSONE = {"cosa": "persone", "quante": "poche", "come": "movimento"}


def _invia(studio, da, **altro):
    return studio.invia_passo({"vista": VISTA, "da": da, "modello": NANO,
                               "destinazione_mostrata": _dest(studio), **altro})


# --- i blocchi ------------------------------------------------------------------


def test_ogni_miniatura_ha_un_nome_un_testo_che_dice_cosa_tenere_e_una_riga():
    for v in blocchi.VARIAZIONI.values():
        assert v.gruppo in blocchi.GRUPPI_VARIAZIONI and v.nome and v.origine == config.SCELTA
        assert "keep" in v.testo and len(v.testo) < 600
    assert {v.nome for v in blocchi.variazioni(blocchi.ESTERNO)} >= {
        "Alba", "Mattino", "Tramonto", "Ora blu", "Notte", "Nuvoloso", "Pioggia", "Neve", "Nebbia",
        "Drammatico", "Nordico", "Luci accese"}


def test_neve_e_nebbia_non_si_offrono_dentro_una_stanza_ne_a_un_arredo():
    interni = {v.identificativo for v in blocchi.variazioni(blocchi.INTERNO)}
    assert "neve" not in interni and "nebbia" not in interni and "ora_blu" in interni
    assert blocchi.variazioni(blocchi.PRODOTTO) == []
    with pytest.raises(blocchi.SceltaNonValida):
        blocchi.variazione("neve", blocchi.INTERNO)


def test_popola_dice_quante_come_e_dove_e_si_rifiuta_fuori_scena():
    nota = blocchi.nota_popola("persone", "poche", "ferme")
    assert nota.startswith("two or three people, standing or sitting still") and "outside the marked area" in nota
    richiesta = blocchi.richiesta_popola("auto", "alcune", "movimento")
    assert "three or four cars" in richiesta and "only on roads" in richiesta
    # Gli alberi non si muovono: «come» non conta.
    assert blocchi.nota_popola("alberi", "molte", "qualunque") == blocchi.nota_popola("alberi", "molte", "")
    for sbagliato in [("auto", "poche", "ferme", blocchi.INTERNO), ("persone", "tante", "ferme", blocchi.ESTERNO),
                      ("persone", "poche", "di corsa", blocchi.ESTERNO), ("gatti", "poche", "ferme", blocchi.ESTERNO)]:
        with pytest.raises(blocchi.SceltaNonValida):
            blocchi.nota_popola(*sbagliato)


def test_il_nome_italiano_si_ritrova_dalla_richiesta_scritta_da_una_miniatura():
    assert blocchi.nome_richiesta(blocchi.VARIAZIONI["ora_blu"].testo) == "Cambia · Ora blu"
    assert blocchi.nome_richiesta(blocchi.richiesta_popola("alberi", "poche", "")) == "Popola · alberi, poche"
    assert blocchi.nome_richiesta(blocchi.nota_popola("persone", "molte", "ferme")) == "Popola · persone, molte, ferme"
    assert blocchi.nome_richiesta("due alberi davanti al fronte") is None


# --- Cambia: piu' miniature, un passo per miniatura --------------------------------


def test_tre_miniature_sono_tre_passi_fratelli_con_il_testo_libero_in_ognuno(base, cartella):
    studio, coda, uno = base
    composto = studio.componi_passo({"vista": VISTA, "da": uno, "variazioni": ["alba", "ora_blu", "nebbia"],
                                     "testo": "luci del portico", "modello": NANO})
    assert composto["invii"] == 3 and [p["nome"] for p in composto["prompts"]] == [
        "Cambia · Alba", "Cambia · Ora blu", "Cambia · Nebbia"]
    assert all("luci del portico" in p["prompt"] for p in composto["prompts"])
    assert "3 immagini" in composto["costo"] or composto["costo"].startswith("non misurato")

    risposta = _invia(studio, uno, variazioni=["alba", "ora_blu", "nebbia"], testo="luci del portico")
    assert len(risposta["identificativi"]) == 3 and risposta["identificativo"] == risposta["identificativi"][0]
    for _ in range(3):
        coda.esegui_uno()
    dati = studio.passi(VISTA)
    figli = [p for p in dati["passi"] if p["da"] == uno]
    assert [p["nome"] for p in figli] == ["Cambia · Alba + luci del portico",
                                          "Cambia · Ora blu + luci del portico",
                                          "Cambia · Nebbia + luci del portico"]
    assert all(p["render"] for p in figli)
    assert "Cambia · Ora blu" in _per_numero(dati, "3")["riassunto"]


def test_una_miniatura_sola_senza_testo_e_un_passo_col_suo_nome(base):
    studio, coda, uno = base
    due = _invia(studio, uno, variazioni=["tramonto"])["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == due)
    assert passo["nome"] == "Cambia · Tramonto"
    assert passo["richieste"] == [blocchi.VARIAZIONI["tramonto"].testo]


@pytest.mark.parametrize("scelte, parola", [
    (["alba", "alba"], "doppie"),
    (["alba", "sconosciuta"], "miniatura"),
    (list(blocchi.VARIAZIONI)[: config.CAMBIA_SCELTE_MASSIME + 1], "al massimo"),
])
def test_miniature_doppie_sconosciute_o_troppe_non_mandano_niente(base, chiamate, scelte, parola):
    studio, _coda, uno = base
    prima = len(chiamate)
    with pytest.raises(ErroreAirender) as errore:
        _invia(studio, uno, variazioni=scelte)
    assert parola in errore.value.fatto
    assert len(chiamate) == prima
    assert [p for p in studio.passi(VISTA)["passi"] if p["da"] == uno] == []


def test_senza_miniature_resta_la_richiesta_a_parole_di_sempre(base):
    studio, _coda, uno = base
    composto = studio.componi_passo({"vista": VISTA, "da": uno, "testo": "cielo al tramonto"})
    assert composto["invii"] == 1 and "cielo al tramonto" in composto["prompt"] and "costo" not in composto


# --- Popola ------------------------------------------------------------------------


def test_popola_decide_il_modello_e_un_passo_a_parole_su_tutta_l_immagine(base):
    studio, coda, uno = base
    composto = studio.componi_passo({"vista": VISTA, "da": uno, "popola": PERSONE})
    assert "never in front of the main facade" in composto["prompt"]
    due = _invia(studio, uno, popola=PERSONE)["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == due)
    assert passo["nome"] == "Popola · persone, poche, in movimento" and passo["aree"] is None


def test_popola_dipingo_io_mette_la_frase_in_ogni_tratto_verde(base):
    studio, coda, uno = base
    altro = {"vista": VISTA, "da": uno, "aree": [VERDE, {**VERDE, "punti": [[0.1, 0.8]]}], "popola": PERSONE}
    composto = studio.componi_ritocco(altro)
    assert composto["note"] == 2 and composto["note_aree"][0] == composto["note_aree"][1]
    assert "Area 2 (add this inside the area" in composto["prompt"]
    rit = studio.invia_ritocco({**altro, "modello": NANO, "destinazione_mostrata": _dest(studio)})["identificativo"]
    coda.esegui_uno()
    passo = next(p for p in studio.passi(VISTA)["passi"] if p["identificativo"] == rit)
    assert passo["nome"] == "Popola · persone, poche, in movimento · 2 aree"


@pytest.mark.parametrize("aree, parola", [([], "tratto verde"), ([VERDE, ROSSO], "pennello verde")])
def test_popola_dipingo_io_senza_verde_o_con_altre_aree_si_ferma(base, aree, parola):
    studio, _coda, uno = base
    with pytest.raises(RichiestaStudioNonValida) as errore:
        studio.componi_ritocco({"vista": VISTA, "da": uno, "aree": aree, "popola": PERSONE})
    assert parola in errore.value.fatto


def test_il_catalogo_dice_miniature_massime_e_cosa_si_popola(base):
    studio, *_ = base
    catalogo = studio.catalogo()
    assert catalogo["cambia"]["massime"] == config.CAMBIA_SCELTE_MASSIME
    assert {g["id"] for g in catalogo["cambia"]["gruppi"]} == {blocchi.ORA, blocchi.MOOD}
    assert [c["id"] for c in catalogo["popola"]["cose"]] == ["persone", "alberi", "auto"]
    assert next(c for c in catalogo["popola"]["cose"] if c["id"] == "alberi")["si_muove"] is False
