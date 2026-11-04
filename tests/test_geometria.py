"""«Tieni la geometria»: un workflow col ControlNet sugli spigoli prima di Nano Banana.

Nessuna rete: l'API v2 dei workflow di Comfy e' un finto che registra le
chiamate e torna un PNG. Il workflow vero non e' mai partito (PRD, NON
VERIFICATO): qui si prova solo che il motore lo mandi com'e' scritto, che
le due destinazioni si mostrino prima dell'invio e che il render della prima
passata parta verso il modello al posto della vista.
"""

from __future__ import annotations

import io
import json

import pytest
from PIL import Image

from core import blocchi, coda as modulo_coda, config
from core.coda import ERRORE, FATTO, Lavoro, LavoroNonValido, leggi_stato
from core.errori import ErroreProvider
from core.provider import geometria as modulo_geometria
from core.studio.servizio import RichiestaStudioNonValida, Studio
from test_passi import NANO, VISTA, ProviderCheRende, _dest, cartella, chiamate  # noqa: F401

BASE = "https://airender-geometria.run.comfy.app"


def _png(colore=(10, 200, 10)) -> bytes:
    uscita = io.BytesIO()
    Image.new("RGB", (320, 200), colore).save(uscita, "PNG")
    return uscita.getvalue()


class ComfyFinto:
    """L'API v2: asset, job, due letture prima di «succeeded», un'uscita da scaricare con la chiave."""

    def __init__(self, finale="succeeded", letture=2, uscite=True):
        self.chiamate, self.finale, self.letture, self.uscite = [], finale, letture, uscite

    def manda_byte(self, url, intestazioni, dati):
        self.chiamate.append(("ASSET", url, intestazioni, dati))
        return 201, {}, {"id": "asset-1", "url": f"{BASE}/api/v2/assets/asset-1/content"}

    def chiama(self, metodo, url, intestazioni, corpo=None):
        self.chiamate.append((metodo, url, intestazioni, corpo))
        if metodo == "POST" and url.endswith("/api/v2/jobs"):
            return 201, {}, {"id": "job-1", "status": "queued", "outputs": [],
                             "urls": {"self": "/api/v2/jobs/job-1", "cancel": "/api/v2/jobs/job-1/cancel"}}
        if metodo == "GET":
            self.letture -= 1
            if self.letture > 0:
                return 200, {}, {"id": "job-1", "status": "running", "outputs": []}
            uscite = [{"node_id": "16", "url": "/api/v2/assets/out-1/content"}] if self.uscite else []
            return 200, {}, {"id": "job-1", "status": self.finale, "outputs": uscite,
                             "error": {"code": "node_execution_error", "message": "modello mancante"}}
        return 200, {}, {}

    def scarica_con(self, url, intestazioni):
        self.chiamate.append(("SCARICA", url, intestazioni, None))
        return _png()


def _client(finto, **altro):
    return modulo_geometria.Geometria(finto, chiave="comfyui-prova", base=BASE, dormi=lambda _s: None, **altro)


def _studio(cartella, chiamate):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderCheRende(chiamate),
                  coda_attiva=lambda: True, apri=lambda _p: None)


def _coda(cartella, chiamate, finto):
    return modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderCheRende(chiamate), dire=lambda _t: None,
                            crea_geometria=lambda controlla: _client(finto, controlla=controlla))


def _genera(studio, **altro):
    dest = studio.destinazione(NANO, geometria=True)
    return studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(),
                         "preset": "rivista", "modello": NANO, "destinazione_mostrata": dest["destinazione"],
                         "geometria": True,
                         "destinazione_geometria_mostrata": dest["geometria"]["destinazione"], **altro})["identificativo"]


# --- il workflow ------------------------------------------------------------------


def test_il_workflow_e_in_formato_api_coi_valori_di_config_e_senza_la_nota():
    grafo = modulo_geometria.workflow("asset-9", "a house", 42)
    assert all("class_type" in n and "inputs" in n for n in grafo.values())
    assert grafo["1"]["inputs"]["image"] == {"__type": "core/ASSET", "info": {"id": "asset-9"}}
    assert grafo["6"]["inputs"]["text"] == "a house"
    assert grafo["8"]["inputs"]["strength"] == config.GEOMETRIA_FORZA
    assert grafo["9"]["inputs"]["seed"] == 42 and grafo["9"]["inputs"]["steps"] == config.GEOMETRIA_PASSI
    assert grafo["2"]["inputs"]["largest_size"] == config.GEOMETRIA_LATO_MASSIMO
    # Ogni collegamento punta a un nodo che c'e'.
    for nodo in grafo.values():
        for valore in nodo["inputs"].values():
            if isinstance(valore, list):
                assert valore[0] in grafo
    # Nessun valore lasciato da riempire.
    assert None not in [v for n in grafo.values() for v in n["inputs"].values()]


def test_esegui_carica_manda_aspetta_e_scarica_con_la_chiave_e_i_link_dell_api():
    finto = ComfyFinto()
    immagine, lavoro = _client(finto).esegui(_png((1, 2, 3)), "a house", 7)
    assert lavoro == "job-1" and immagine.startswith(b"\x89PNG")
    tipi = [c[0] for c in finto.chiamate]
    assert tipi == ["ASSET", "POST", "GET", "GET", "SCARICA"]
    assert all(c[2]["Authorization"] == "Bearer comfyui-prova" for c in finto.chiamate)
    asset = finto.chiamate[0]
    assert b'name="file"; filename="vista.png"' in asset[3] and asset[3].index(b'name="file_path"') < asset[3].index(b'name="file"')
    assert finto.chiamate[1][2]["Idempotency-Key"]
    assert finto.chiamate[2][1] == f"{BASE}/api/v2/jobs/job-1"
    assert finto.chiamate[4][1] == f"{BASE}/api/v2/assets/out-1/content"


def test_un_workflow_fallito_si_spiega_e_dice_come_mandare_senza():
    with pytest.raises(ErroreProvider, match="modello mancante") as errore:
        _client(ComfyFinto(finale="failed")).esegui(_png(), "x", 1)
    assert "Togli la spunta" in errore.value.cosa_fare


def test_oltre_l_attesa_massima_il_lavoro_comfy_si_annulla():
    tempo = iter(range(0, 10 ** 6, config.GEOMETRIA_ATTESA_SECONDI))  # noqa: numero-non-configurabile
    finto = ComfyFinto(letture=10 ** 6)  # numero-non-configurabile: non finisce mai
    with pytest.raises(ErroreProvider, match="non ha finito"):
        _client(finto, adesso=lambda: next(tempo)).esegui(_png(), "x", 1)
    assert ("POST", f"{BASE}/api/v2/jobs/job-1/cancel") in [(c[0], c[1]) for c in finto.chiamate]


def test_senza_chiave_non_parte_niente(monkeypatch):
    for nome in ("COMFY_API_KEY", "AIRENDER_COMFY_API_KEY"):
        monkeypatch.delenv(nome, raising=False)
    finto = ComfyFinto()
    with pytest.raises(ErroreProvider, match="Manca la chiave"):
        modulo_geometria.Geometria(finto, base=BASE).esegui(_png(), "x", 1)
    assert not finto.chiamate


def test_un_link_su_un_altro_indirizzo_non_riceve_la_chiave():
    class Altrove(ComfyFinto):
        def chiama(self, metodo, url, intestazioni, corpo=None):
            stato, intest, dati = super().chiama(metodo, url, intestazioni, corpo)
            if isinstance(dati, dict) and dati.get("urls"):
                dati["urls"]["self"] = "https://ladro.example/api/v2/jobs/job-1"
            return stato, intest, dati
    finto = Altrove()
    with pytest.raises(ErroreProvider, match="altro indirizzo"):
        _client(finto).esegui(_png(), "x", 1)
    assert not any("ladro" in c[1] for c in finto.chiamate)


def test_il_file_del_workflow_e_json_api_puro_da_caricare_sulla_developer_platform():
    grezzo = json.loads(modulo_geometria.WORKFLOW.read_text(encoding="utf-8"))
    assert all(k.isdigit() and "class_type" in v for k, v in grezzo.items())
    assert None not in [x for n in grezzo.values() for x in n["inputs"].values()]


def test_senza_indirizzo_del_deployment_si_dice_cosa_fare(monkeypatch):
    monkeypatch.delenv(modulo_geometria.VARIABILE_URL, raising=False)
    with pytest.raises(ErroreProvider, match="Manca l'indirizzo") as errore:
        modulo_geometria.indirizzo()
    assert "setx " + modulo_geometria.VARIABILE_URL in errore.value.cosa_fare


def test_l_indirizzo_viene_dall_ambiente_solo_se_e_https(monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, "https://studio-x.run.comfy.app/")
    assert modulo_geometria.destinazione().endswith("su studio-x.run.comfy.app")
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, "http://studio-x.run.comfy.app")
    with pytest.raises(ErroreProvider, match="https"):
        modulo_geometria.indirizzo()


# --- Studio e coda -------------------------------------------------------------


def test_la_destinazione_mostra_anche_la_prima_passata_e_come_si_paga(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio = _studio(cartella, chiamate)
    assert studio.destinazione(NANO)["geometria"] is None
    prima = studio.destinazione(NANO, geometria=True)["geometria"]
    assert prima["destinazione"] == ("Comfy Developer Platform, workflow Z-Image-Turbo + ControlNet sugli spigoli "
                                     "su airender-geometria.run.comfy.app")
    assert prima["costo"] == "a secondi di GPU del deployment" and prima["errore"] is None


def test_genera_con_la_spunta_manda_prima_il_workflow_poi_nano_banana_col_suo_render(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio, finto = _studio(cartella, chiamate), ComfyFinto()
    identificativo = _genera(studio)
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    assert scritto["formato"] == modulo_coda.FORMATO_GEOMETRIA and scritto["formato_base"] == modulo_coda.FORMATO
    assert Lavoro.da_dizionario(scritto).destinazione_geometria == scritto["destinazione_geometria"]

    _coda(cartella, chiamate, finto).esegui_uno()
    stato = leggi_stato(cartella, identificativo)
    assert stato["stato"] == FATTO
    (richiesta,) = chiamate
    with Image.open(io.BytesIO(richiesta.immagine)) as partita:
        assert partita.getpixel((5, 5))[1] == 200  # numero-non-configurabile: il verde della bozza finta
    assert modulo_geometria.REGOLA_PROMPT in richiesta.prompt
    prompt_comfy = finto.chiamate[1][3]["workflow"]["6"]["inputs"]["text"]
    assert "Image 1 is a draft" not in prompt_comfy and prompt_comfy
    assert stato["geometria"]["lavoro_comfy"] == "job-1"
    assert (cartella / "lavori" / "fatto" / f"{identificativo}.geometria.png").exists()


def test_senza_indirizzo_genera_si_ferma_col_gesto_da_fare(cartella, chiamate, monkeypatch):
    monkeypatch.delenv(modulo_geometria.VARIABILE_URL, raising=False)
    studio = _studio(cartella, chiamate)
    prima = studio.destinazione(NANO, geometria=True)["geometria"]
    assert prima["destinazione"] is None and "setx" in prima["cosa_fare"]
    with pytest.raises(RichiestaStudioNonValida, match="Manca l'indirizzo"):
        studio.invia({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(), "modello": NANO,
                      "destinazione_mostrata": _dest(studio), "geometria": True})
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_la_composizione_mostra_la_regola_della_bozza(cartella, chiamate):
    studio = _studio(cartella, chiamate)
    composto = studio.componi({"vista": VISTA, "scelte": blocchi.da_preset("rivista").a_dizionario(), "geometria": True})
    assert modulo_geometria.REGOLA_PROMPT in composto["prompt"]


def test_se_la_prima_passata_cambia_indirizzo_dopo_il_clic_non_parte_niente(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio, finto = _studio(cartella, chiamate), ComfyFinto()
    identificativo = _genera(studio)
    coda = modulo_coda.Coda(cartella, crea_provider=lambda _n: ProviderCheRende(chiamate), dire=lambda _t: None,
                            crea_geometria=lambda c: modulo_geometria.Geometria(
                                finto, chiave="k", base="https://altro.run.comfy.app", controlla=c))
    coda.esegui_uno()
    assert leggi_stato(cartella, identificativo)["stato"] == ERRORE
    assert not finto.chiamate and not chiamate


def test_la_destinazione_della_prima_passata_va_mostrata(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    studio = _studio(cartella, chiamate)
    with pytest.raises(RichiestaStudioNonValida, match="prima passata"):
        _genera(studio, destinazione_geometria_mostrata="un altro posto")
    assert not list(cartella.glob("lavori/in-attesa/*.json"))


def test_da_un_passo_la_spunta_si_rifiuta(cartella, chiamate):
    with pytest.raises(LavoroNonValido, match="Tieni la geometria"):
        modulo_coda.metti_in_coda(cartella, cartella / VISTA, blocchi.da_preset("rivista"),
                                  provider="prova", modello=NANO, parte_da="x", partenza=cartella / VISTA,
                                  destinazione_geometria="Comfy",
                                  crea_provider=lambda _n: ProviderCheRende([]))


def test_un_file_del_formato_10_senza_destinazione_o_da_un_passo_si_rifiuta(cartella, chiamate, monkeypatch):
    monkeypatch.setenv(modulo_geometria.VARIABILE_URL, BASE)
    identificativo = _genera(_studio(cartella, chiamate))
    scritto = json.loads((cartella / "lavori" / "in-attesa" / f"{identificativo}.json").read_text("utf-8"))
    for guasto in ({"destinazione_geometria": ""}, {"formato_base": modulo_coda.FORMATO_FINALE},
                   {"partenza": "x.png", "parte_da": "y"}):
        with pytest.raises(LavoroNonValido):
            Lavoro.da_dizionario({**scritto, **guasto})
