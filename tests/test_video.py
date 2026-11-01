"""Studio · Video: Seedance 2.5 da uno o piu' render, senza rete.

Il Router e' finto e il provider della coda e' finto: qui si prova che il
corpo dica i ruoli giusti alle immagini, che una richiesta sbagliata si
fermi prima di partire, che la coda faccia il video e scriva la ricetta senza
immagini ne' chiave, e che lo Studio non mandi niente verso una destinazione
che la pagina non ha mostrato (regola 5).
"""

from __future__ import annotations

import http.client
import json

import pytest

from conftest import TrasportoComfyFinto, provider_comfy, router_in_coda, router_stato, vista_shaded
from core import config, video
from core.errori import ChiaveMancante, ErroreProvider
from core.provider import comfy
from core.studio.server import avvia_in_sottofondo, crea_server
from core.studio.servizio import RichiestaStudioNonValida, Studio
from test_coda import ProviderDiProva

PNG = vista_shaded(320, 200)
MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 32


class ProviderVideoDiProva(ProviderDiProva):
    """Come il finto delle immagini, ma fa anche video."""

    def fa_video(self):
        return True

    def genera_video(self, modello, corpo, immagini):
        self.registro.append((modello, corpo, immagini))
        if self.errore:
            raise self.errore
        return MP4, {"crediti_usati": 12.5, "fallback_provider": comfy.FALLBACK}


def _richiesta(modo="primo", quante=1, **altro):
    return video.RichiestaVideo(identificativo="v1", immagini=tuple(f"/x/{i}.png" for i in range(quante)),
                                modo=modo, **altro)


# --- il corpo -------------------------------------------------------------------

@pytest.mark.parametrize("modo, quante, ruoli", [
    ("primo", 1, ["first_frame"]),
    ("primo-ultimo", 2, ["first_frame", "last_frame"]),
    ("riferimenti", 3, ["reference_image"] * 3),
])
def test_il_corpo_da_a_ogni_immagine_il_suo_ruolo(modo, quante, ruoli):
    corpo = video.corpo(_richiesta(modo, quante), [PNG] * quante)
    immagini = [v for v in corpo["content"] if v["type"] == "image_url"]
    assert [v["role"] for v in immagini] == ruoli
    assert all(v["image_url"]["url"].startswith("data:image/png;base64,") for v in immagini)
    assert corpo["content"][0]["type"] == "text"
    assert corpo["ratio"] == "adaptive"
    assert corpo["watermark"] is False


def test_la_ricetta_non_porta_le_immagini():
    corpo = video.corpo_senza_immagini(video.corpo(_richiesta(), [PNG]))
    assert "base64" not in json.dumps(corpo)


@pytest.mark.parametrize("cambi", [
    {"modo": "primo-ultimo", "quante": 1},
    {"modo": "riferimenti", "quante": config.VIDEO_RIFERIMENTI_MASSIMI + 1},
    {"modo": "inventato"},
    {"movimento": "salta"},
    {"durata": 7},
    {"risoluzione": "4k"},
])
def test_una_richiesta_sbagliata_si_ferma_con_la_ragione(cambi):
    modo = cambi.pop("modo", "primo")
    quante = cambi.pop("quante", 1)
    with pytest.raises(video.VideoNonValido) as errore:
        _richiesta(modo, quante, **cambi)
    assert errore.value.fatto and errore.value.cosa_fare


def test_il_prompt_dice_il_movimento_e_il_testo_libero():
    testo = _richiesta(movimento="drone", testo="le luci si accendono").prompt()
    assert video.MOVIMENTI["drone"][1] in testo
    assert "le luci si accendono" in testo


# --- il provider vero, col Router finto --------------------------------------------

def test_comfy_manda_il_video_senza_ripiego_e_scarica_l_mp4():
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"),
         (200, {}, {"content": {"video_url": "https://consegna.esempio/v.mp4?firma=x"}})],
        immagine=MP4,
    )
    dati, dettagli = provider_comfy(trasporto).genera_video(video.MODELLO, video.corpo(_richiesta(), [PNG]), (PNG,))
    assert dati == MP4
    _metodo, indirizzo, _intestazioni, _corpo = trasporto.poste()[0]
    assert video.MODELLO in indirizzo
    assert "fallback_provider=false" in indirizzo and dettagli["fallback_provider"] == "false"
    assert trasporto.scaricati == ["https://consegna.esempio/v.mp4?firma=x"]


def test_comfy_rifiuta_un_file_che_non_e_un_video():
    trasporto = TrasportoComfyFinto(
        [router_in_coda(), router_stato("COMPLETED"), (200, {}, {"content": {"video_url": "https://x/v.mp4"}})],
        immagine=b"<html>non un video</html>",
    )
    with pytest.raises(ErroreProvider):
        provider_comfy(trasporto).genera_video(video.MODELLO, {}, (PNG,))


def test_senza_chiave_il_video_non_parte():
    trasporto = TrasportoComfyFinto()
    with pytest.raises(ChiaveMancante):
        comfy.ProviderComfy(chiave=None, trasporto=trasporto).genera_video(video.MODELLO, {}, (PNG,))
    assert not trasporto.chiamate


# --- la coda ------------------------------------------------------------------------

def test_la_coda_fa_il_video_e_scrive_la_ricetta_senza_immagini(tmp_path):
    (tmp_path / "r.png").write_bytes(PNG)
    chiamate = []
    richiesta = video.metti_in_coda(tmp_path, [tmp_path / "r.png"], movimento="gira")
    coda = video.CodaVideo(tmp_path, crea_provider=lambda _n: ProviderVideoDiProva(chiamate), dire=lambda _t: None)
    assert coda.esegui_uno() == richiesta.identificativo
    assert coda.esegui_uno() is None
    voce = video.elenco(tmp_path)[0]
    assert voce["stato"] == video.FATTO and voce["crediti_usati"] == 12.5
    file = tmp_path / video.CARTELLA_VIDEO / f"{richiesta.identificativo}.mp4"
    assert file.read_bytes() == MP4
    ricetta = (file.parent / (file.name + ".ricetta.json")).read_text(encoding="utf-8")
    assert "base64" not in ricetta and "chiave_idempotenza" not in ricetta
    assert json.loads(ricetta)["modello"] == video.MODELLO


def test_un_errore_del_servizio_resta_sul_video(tmp_path):
    (tmp_path / "r.png").write_bytes(PNG)
    video.metti_in_coda(tmp_path, [tmp_path / "r.png"])
    errore = ErroreProvider("Crediti finiti.", "Ricarica i crediti.")
    video.CodaVideo(tmp_path, crea_provider=lambda _n: ProviderVideoDiProva([], errore=errore),
                    dire=lambda _t: None).esegui_uno()
    voce = video.elenco(tmp_path)[0]
    assert (voce["stato"], voce["fatto"], voce["cosa_fare"]) == (video.ERRORE, "Crediti finiti.", "Ricarica i crediti.")


def test_un_video_inviato_e_abbandonato_non_si_rimanda(tmp_path):
    (tmp_path / "r.png").write_bytes(PNG)
    richiesta = video.metti_in_coda(tmp_path, [tmp_path / "r.png"])
    video.scrivi_stato(tmp_path, richiesta.identificativo, video.INVIATO)
    coda = video.CodaVideo(tmp_path, crea_provider=lambda _n: ProviderVideoDiProva([]), dire=lambda _t: None)
    assert coda.recupera_abbandonati() == [richiesta.identificativo]
    assert "crediti" in video.elenco(tmp_path)[0]["cosa_fare"]


def test_annulla_toglie_solo_un_video_ancora_in_coda(tmp_path):
    (tmp_path / "r.png").write_bytes(PNG)
    richiesta = video.metti_in_coda(tmp_path, [tmp_path / "r.png"])
    assert video.annulla(tmp_path, richiesta.identificativo) is True
    assert video.annulla(tmp_path, richiesta.identificativo) is False
    assert video.elenco(tmp_path)[0]["stato"] == video.ANNULLATO


# --- lo Studio ----------------------------------------------------------------------

def _studio(cartella, chiamate, coda_attiva=True):
    return Studio(cartella, provider="prova", crea_provider=lambda _n: ProviderVideoDiProva(chiamate),
                  coda_attiva=lambda: coda_attiva, apri=lambda _p: None)


def test_il_catalogo_dice_dove_va_e_che_non_e_provato(tmp_path):
    catalogo = _studio(tmp_path, []).catalogo_video()
    assert video.MODELLO in catalogo["destinazione"]
    assert "non e' ancora stato provato" in catalogo["avviso"]
    assert catalogo["costo"].startswith("non misurato")
    assert catalogo["durate"] == list(config.VIDEO_DURATE_SECONDI)
    assert {m["id"] for m in catalogo["modi"]} == set(video.MODI)


def test_un_render_caricato_entra_e_un_file_che_non_e_immagine_no(tmp_path):
    studio = _studio(tmp_path, [])
    caricata = studio.carica_immagine_video(PNG, "notte.png")
    assert studio.percorso_immagine_video(caricata["nome"]).read_bytes() == PNG
    with pytest.raises(RichiestaStudioNonValida):
        studio.carica_immagine_video(b"non un'immagine", "x.txt")
    with pytest.raises(RichiestaStudioNonValida):
        studio.percorso_immagine_video("../../segreto.png")


def test_la_prova_a_secco_non_mette_niente_in_coda(tmp_path):
    studio = _studio(tmp_path, [])
    nome = studio.carica_immagine_video(PNG)["nome"]
    secco = studio.prova_a_secco_video({"immagini": [{"caricata": nome}], "movimento": "ferma"})
    assert secco["inviato"] is False and secco["immagini"] == 1 and not secco["problemi"]
    assert video.MOVIMENTI["ferma"][1] in secco["prompt"]
    assert video.elenco(tmp_path) == []


def test_la_prova_a_secco_dice_cosa_fermerebbe(tmp_path):
    secco = _studio(tmp_path, [], coda_attiva=False).prova_a_secco_video({"immagini": [], "modo": "primo"})
    assert len(secco["problemi"]) == 2  # nessuna immagine, coda ferma


def test_invia_non_manda_se_la_destinazione_mostrata_e_un_altra(tmp_path):
    studio = _studio(tmp_path, [])
    nome = studio.carica_immagine_video(PNG)["nome"]
    with pytest.raises(RichiestaStudioNonValida):
        studio.invia_video({"immagini": [{"caricata": nome}], "destinazione_mostrata": "altrove"})
    assert video.elenco(tmp_path) == []
    destinazione = studio.catalogo_video()["destinazione"]
    risposta = studio.invia_video({"immagini": [{"caricata": nome}], "destinazione_mostrata": destinazione})
    assert studio.video()[0]["identificativo"] == risposta["identificativo"]
    assert studio.video()[0]["stato"] == video.IN_CODA


def test_le_rotte_video_del_server(tmp_path):
    studio = _studio(tmp_path, [])
    servito = crea_server(studio)
    avvia_in_sottofondo(servito)
    porta = servito.server_address[1]

    def chiedi(metodo, percorso, corpo=None, intestazioni=None):
        connessione = http.client.HTTPConnection("127.0.0.1", porta, timeout=5)
        connessione.request(metodo, percorso, body=corpo,
                            headers={"Host": f"127.0.0.1:{porta}", "X-Airender": "1", **(intestazioni or {})})
        risposta = connessione.getresponse()
        return risposta.status, risposta.getheader("Content-Type"), risposta.read()

    try:
        stato, _tipo, corpo = chiedi("GET", "/api/video/catalogo")
        assert stato == 200 and json.loads(corpo)["modello"] == video.MODELLO
        stato, _tipo, corpo = chiedi("POST", "/api/video/immagini", PNG, {"X-Nome-File": "r.png"})
        nome = json.loads(corpo)["nome"]
        stato, tipo, corpo = chiedi("GET", f"/file/immagine-video/{nome}")
        assert stato == 200 and tipo == "image/png"
        destinazione = studio.catalogo_video()["destinazione"]
        stato, _tipo, corpo = chiedi("POST", "/api/video/invia", json.dumps(
            {"immagini": [{"caricata": nome}], "destinazione_mostrata": destinazione}).encode())
        identificativo = json.loads(corpo)["identificativo"]
        stato, _tipo, corpo = chiedi("GET", "/api/video")
        assert json.loads(corpo)[0]["identificativo"] == identificativo
        stato, _tipo, corpo = chiedi("GET", f"/file/video/{identificativo}")
        assert stato == 404  # non ancora fatto
        stato, _tipo, corpo = chiedi("POST", f"/api/video/{identificativo}/annulla", b"{}")
        assert json.loads(corpo) == {"annullato": True}
    finally:
        servito.shutdown()
        servito.server_close()
