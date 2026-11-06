// Il motore di AIRENDER nel browser: Python (Pyodide) in un Web Worker.
//
// Fa girare lo stesso codice dello Studio sul PC (core/, impacchettato in
// motore.zip da scripts/scrivi_web.py) attraverso web/ponte.py. Riceve le
// richieste della pagina dal service worker (sw.js) su una MessagePort e
// risponde come avrebbe risposto lo Studio su 127.0.0.1.
//
// La cartella delle viste vive in IndexedDB (IDBFS): resta fra una visita e
// l'altra, solo in questo browser. Nessuna immagine sta sul server AIRENDER.
//
// Python non deve bloccare il worker mentre aspetta il servizio (un render
// dura decine di secondi): le chiamate di rete e le attese passano da
// run_sync, che con JSPI sospende Python e lascia rispondere alle altre
// richieste. Serve Chrome o Edge recenti: senza JSPI lo si dice e ci si ferma.

/* global loadPyodide */
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/";
const CASA = "/home/pyodide/airender";
const INTERVALLO_CODA_MS = 1000; // come CODA_INTERVALLO_SECONDI in core/config.py (scelta)
const INTERVALLO_SALVA_MS = 5000; // ogni quanto si salva la cartella mentre un lavoro gira (scelta)

let py = null;
let rispondi = null;
let giroCoda = null;
let codaInCorso = false;
let sporco = false;
let salvataggio = Promise.resolve();

const dimmi = (messaggio, trasferisci) => self.postMessage(messaggio, trasferisci || []);
const avanzamento = (testo) => dimmi({ tipo: "avanzamento", testo });

function salva() {
  // Uno alla volta: due syncfs insieme si rovinano a vicenda.
  salvataggio = salvataggio.then(() => new Promise((fatto) => {
    sporco = false;
    py.FS.syncfs(false, (errore) => {
      if (errore) dimmi({ tipo: "avviso", testo: "Il browser non ha salvato la cartella dello Studio: se chiudi la pagina, l'ultimo render può andare perso." });
      fatto();
    });
  }));
  return salvataggio;
}

function carica() {
  return new Promise((fatto, fallito) => py.FS.syncfs(true, (e) => (e ? fallito(e) : fatto())));
}

// fetch() per urllib (web/ponte.py, installa_rete). Torna stato, intestazioni, byte.
async function chiamaRete(url, metodo, intestazioniJson, corpo) {
  const risposta = await fetch(url, {
    method: metodo,
    headers: JSON.parse(intestazioniJson || "{}"),
    body: corpo ? corpo : undefined,
    cache: "no-store",
  });
  const intestazioni = {};
  risposta.headers.forEach((valore, nome) => { intestazioni[nome] = valore; });
  return { stato: risposta.status, intestazioni: JSON.stringify(intestazioni), corpo: new Uint8Array(await risposta.arrayBuffer()) };
}

const dormi = (secondi) => new Promise((fatto) => setTimeout(fatto, Math.max(0, secondi) * 1000));

const AVVIO = `
import json, os, sys
from pathlib import Path
sys.path.insert(0, "/home/pyodide/motore")
os.environ["HOME"] = CASA          # il codice licenza finisce in ~/.config/airender, dentro IDBFS
os.environ.pop("APPDATA", None)
os.environ["AIRENDER_SERVER"] = SERVER   # il server della pagina: anche le anteprime di Netlify usano il proprio
from pyodide.ffi import run_sync, to_js
from js import Object
from web import ponte as modulo_ponte

def _chiama(url, metodo, intestazioni, corpo):
    r = run_sync(chiama_js(url, metodo, json.dumps(intestazioni), to_js(corpo) if corpo else None))
    return int(r.stato), json.loads(r.intestazioni), r.corpo.to_bytes()

modulo_ponte.installa_rete(_chiama)
modulo_ponte.installa_attesa(lambda secondi: run_sync(dormi_js(secondi)))
ponte = modulo_ponte.Ponte(Path(CASA) / "viste", postazione=POSTAZIONE)

def rispondi(metodo, percorso, intestazioni_json, corpo):
    # Da JavaScript un corpo assente arriva come null (JsNull in Pyodide), non come None.
    dati = corpo.to_bytes() if hasattr(corpo, "to_bytes") else b""
    stato, intestazioni, risposta = ponte.rispondi(metodo, percorso, json.loads(intestazioni_json), dati)
    file = ponte.prendi_da_scaricare()
    return to_js({
        "stato": stato,
        "intestazioni": {k: str(v) for k, v in intestazioni.items()},
        "corpo": to_js(risposta),
        "scarica": None if file is None else {"nome": file[0], "corpo": to_js(file[1])},
    }, dict_converter=Object.fromEntries)

def giro_coda():
    return ponte.giro_coda()
`;

async function prepara({ postazione, server }) {
  try {
    avanzamento("Scarico Python per il browser (la prima volta circa 20 MB, poi resta in memoria)…");
    importScripts(`${PYODIDE}pyodide.js`);
    py = await loadPyodide({ indexURL: PYODIDE });
    avanzamento("Scarico Pillow, la libreria per le immagini…");
    await py.loadPackage(["pillow"]);
    avanzamento("Apro la cartella dello Studio salvata in questo browser…");
    py.FS.mkdirTree(CASA);
    py.FS.mount(py.FS.filesystems.IDBFS, {}, CASA);
    await carica();
    avanzamento("Carico il motore AIRENDER…");
    const zip = await (await fetch("motore.zip", { cache: "no-cache" })).arrayBuffer();
    py.unpackArchive(zip, "zip", { extractDir: "/home/pyodide/motore" });
    py.globals.set("CASA", CASA);
    py.globals.set("SERVER", server);
    py.globals.set("POSTAZIONE", postazione);
    py.globals.set("chiama_js", chiamaRete);
    py.globals.set("dormi_js", dormi);
    await py.runPythonAsync(AVVIO);
    rispondi = py.globals.get("rispondi");
    giroCoda = py.globals.get("giro_coda");
    if (typeof rispondi.callPromising !== "function" || !(await senzaBlocchi())) {
      dimmi({ tipo: "errore", fatto: "Questo browser non sa sospendere il motore mentre aspetta il render.",
        cosa_fare: "Apri la web app con Chrome o Edge aggiornati." });
      return;
    }
    setInterval(girandoLaCoda, INTERVALLO_CODA_MS);
    setInterval(() => { if (sporco || codaInCorso) salva(); }, INTERVALLO_SALVA_MS);
    dimmi({ tipo: "pronto" });
  } catch (e) {
    dimmi({ tipo: "errore", fatto: `Il motore non è partito nel browser: ${e && e.message ? e.message.split("\n").slice(-2).join(" ") : e}.`,
      cosa_fare: "Ricarica la pagina. Se si ripete, prova con Chrome o Edge aggiornati e scrivi a AIRENDER." });
  }
}

// JSPI c'e' davvero? Una chiamata che dorme 1 ms deve tornare senza errori.
async function senzaBlocchi() {
  try {
    await py.runPythonAsync("def _prova():\n    run_sync(dormi_js(0.001))\n    return True");
    return Boolean(await py.globals.get("_prova").callPromising());
  } catch (e) {
    return false;
  }
}

async function girandoLaCoda() {
  if (codaInCorso) return;
  codaInCorso = true;
  try {
    const fatto = await giroCoda.callPromising();
    if (fatto) await salva();
  } catch (e) {
    dimmi({ tipo: "avviso", testo: `La coda dei lavori si è fermata un momento: ${causa(e)}` });
    console.error("AIRENDER coda", e);
  } finally {
    codaInCorso = false;
  }
}

// Le richieste della pagina passano una alla volta: lo Studio ne manda molte
// insieme all'avvio. Solo la coda dei lavori gira accanto a loro.
let fila = Promise.resolve();
function inFila(lavoro) {
  const turno = fila.then(lavoro, lavoro);
  fila = turno.catch(() => {});
  return turno;
}

// L'ultima riga utile di un errore Python o JavaScript, per dirla a schermo.
function causa(e) {
  const testo = String((e && (e.message || e)) || "errore sconosciuto");
  const righe = testo.split("\n").map((r) => r.trim()).filter(Boolean);
  return righe.slice(-1)[0].slice(0, 300);
}

async function richiesta(porta, dati) {
  return inFila(() => esegui(porta, dati));
}

async function esegui(porta, { id, metodo, url, intestazioni, corpo }) {
  try {
    const esito = await rispondi.callPromising(metodo, url, JSON.stringify(intestazioni || {}), corpo ? new Uint8Array(corpo) : undefined);
    if (metodo === "POST") { sporco = true; salva(); }
    if (esito.scarica) dimmi({ tipo: "scarica", nome: esito.scarica.nome, corpo: esito.scarica.corpo }, [esito.scarica.corpo.buffer]);
    porta.postMessage({ id, stato: esito.stato, intestazioni: esito.intestazioni, corpo: esito.corpo.buffer }, [esito.corpo.buffer]);
  } catch (e) {
    console.error("AIRENDER motore", metodo, url, e);
    const corpo = new TextEncoder().encode(JSON.stringify({ errore: {
      fatto: `Il motore dello Studio nel browser ha avuto un problema con ${metodo} ${url}: ${causa(e)}`,
      cosa_fare: "Ricarica la pagina; se si ripete, manda questo messaggio a AIRENDER." } })).buffer;
    porta.postMessage({ id, stato: 500, intestazioni: { "Content-Type": "application/json; charset=utf-8" }, corpo }, [corpo]);
  }
}

self.onmessage = (evento) => {
  const m = evento.data || {};
  if (m.tipo === "prepara") prepara(m);
  if (m.tipo === "porta-sw") {
    const porta = evento.ports[0];
    porta.onmessage = (e) => {
      if (!rispondi) {
        const corpo = new TextEncoder().encode(JSON.stringify({ errore: { fatto: "Lo Studio si sta ancora preparando.", cosa_fare: "Aspetta qualche secondo." } })).buffer;
        porta.postMessage({ id: e.data.id, stato: 503, intestazioni: { "Content-Type": "application/json; charset=utf-8" }, corpo }, [corpo]);
        return;
      }
      richiesta(porta, e.data);
    };
  }
};
