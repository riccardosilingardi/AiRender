// Il service worker della web app: fa da «127.0.0.1» dello Studio.
//
// La pagina dello Studio chiede /studio/api/... e /studio/file/... come se
// avesse il server locale accanto (fetch, <img src>, <video src>). Qui quelle
// richieste si girano al motore (motore.js, un Web Worker della pagina) su una
// MessagePort che la pagina consegna con «collega». Tutto il resto (pagine,
// server AIRENDER, Pyodide) va in rete come sempre.

const STRADE = ["/studio/api/", "/studio/file/"];
const ATTESA_PORTA_MS = 10000; // quanto si aspetta che la pagina si ricolleghi dopo un riavvio del service worker (scelta)
const porte = new Map(); // id della scheda -> MessagePort verso il suo motore
const inAttesa = new Map(); // id della scheda -> [funzioni da chiamare quando arriva la porta]
let numero = 0;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

self.addEventListener("message", (evento) => {
  if (!evento.data || evento.data.tipo !== "collega" || !evento.source) return;
  const id = evento.source.id;
  const porta = evento.ports[0];
  const risposte = new Map();
  porta.onmessage = (e) => {
    const fatto = risposte.get(e.data.id);
    if (fatto) { risposte.delete(e.data.id); fatto(e.data); }
  };
  porta.risposte = risposte;
  porte.set(id, porta);
  (inAttesa.get(id) || []).forEach((f) => f(porta));
  inAttesa.delete(id);
});

// Dopo un riavvio il service worker non ha piu' le porte: le chiede alla scheda.
async function portaDi(idScheda) {
  if (porte.has(idScheda)) return porte.get(idScheda);
  const scheda = await self.clients.get(idScheda);
  if (!scheda) return null;
  const arriva = new Promise((fatto) => {
    inAttesa.set(idScheda, [...(inAttesa.get(idScheda) || []), fatto]);
    setTimeout(() => fatto(null), ATTESA_PORTA_MS);
  });
  scheda.postMessage({ tipo: "ricollega" });
  return arriva;
}

function rispostaErrore(stato, fatto, cosaFare) {
  return new Response(JSON.stringify({ errore: { fatto, cosa_fare: cosaFare } }), {
    status: stato, headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}

async function alMotore(richiesta, idScheda) {
  const porta = await portaDi(idScheda);
  if (!porta) {
    return rispostaErrore(503, "Lo Studio nel browser non risponde.", "Ricarica la pagina.");
  }
  const id = ++numero;
  const corpo = richiesta.method === "POST" ? await richiesta.arrayBuffer() : null;
  const intestazioni = {};
  richiesta.headers.forEach((valore, nome) => { intestazioni[nome] = valore; });
  const risposta = await new Promise((fatto) => {
    porta.risposte.set(id, fatto);
    porta.postMessage({ id, metodo: richiesta.method, url: new URL(richiesta.url).pathname + new URL(richiesta.url).search, intestazioni, corpo },
      corpo ? [corpo] : []);
  });
  return new Response(risposta.corpo, { status: risposta.stato, headers: risposta.intestazioni });
}

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (url.origin !== self.location.origin || !STRADE.some((s) => url.pathname.startsWith(s))) return;
  evento.respondWith(alMotore(evento.request, evento.clientId));
});
