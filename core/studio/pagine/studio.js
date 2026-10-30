// Lo Studio: Genera, Risultato, Passi, Ritocca.
// Niente framework e niente CDN: deve funzionare offline. Lo stato sta in S,
// render() ridisegna la schermata, le richieste passano da api().
// Gli stati di ogni schermata sono quelli di DESIGN.md: vuoto, in corso,
// errore, pieno. Lo stato vuoto non mostra dati finti.
"use strict";

const S = {
  scheda: "genera",
  studio: null,
  catalogo: null,
  vista: null,            // nome del file nella cartella
  descrizione: null,      // esito di idoneita' della vista
  scelte: null,
  preset: null,
  modello: null,
  destinazione: null,
  composto: null,
  promptAMano: null,      // testo scritto a mano: i comandi non lo toccano piu'
  mostraPrompt: false,
  dettagliAperti: true,
  mostraViste: false,
  lavoroAttivo: null,
  varianti: 1,            // quanti lavori con le stesse scelte per un Genera
  inFila: [],             // le altre varianti dello stesso Genera, ancora da seguire
  ultimoEsito: null,      // ultimo lavoro finito in errore o annullato, per Genera
  errore: null,           // errore di una richiesta, con fatto e cosa_fare
  secco: null,            // risposta della prova a secco
  viste_viste: new Set(),
  risultato: { lavori: [], scelto: null, confronto: "vista", modo: "scorri", x: 50, ricetta: null, rifai: false, caricato: false },
  // Studio · Passi: l'albero letto dal server, il passo scelto ("0" e' la
  // vista), il confronto e i tre pannelli che si aprono a destra.
  passi: { dati: null, errore: null, caricato: false, scelto: null, confronto: "vista", modo: "scorri", x: 50,
           nuovo: null, pulito: null, rifai: false, dest: {} },
  // Studio · Ritocca: il passo il cui render si ritocca, lo strumento, le
  // aree con le loro note (coordinate da 0 a 1), il lavoro mandato e,
  // finito, il passo nato. Il modello e le destinazioni sono quelli dei Passi.
  ritocca: { da: null, strumento: "rettangolo", aree: [], modello: null, composto: null, errore: null,
             inviato: null, esito: null, x: 50 },
};

// --- attrezzi ---------------------------------------------------------------

function h(tag, attributi, ...figli) {
  const nodo = document.createElement(tag);
  for (const [chiave, valore] of Object.entries(attributi || {})) {
    if (valore === null || valore === undefined || valore === false) continue;
    if (chiave.startsWith("on")) nodo.addEventListener(chiave.slice(2), valore);
    else if (chiave === "classe") nodo.className = valore;
    else if (chiave === "stile") nodo.setAttribute("style", valore);
    else if (valore === true) nodo.setAttribute(chiave, "");
    else nodo.setAttribute(chiave, valore);
  }
  for (const figlio of figli.flat()) {
    if (figlio === null || figlio === undefined || figlio === false) continue;
    nodo.append(figlio instanceof Node ? figlio : document.createTextNode(String(figlio)));
  }
  return nodo;
}

class ErroreStudio extends Error {
  constructor(fatto, cosaFare) { super(fatto); this.fatto = fatto; this.cosa_fare = cosaFare; }
}

async function api(metodo, indirizzo, corpo, intestazioni) {
  let risposta;
  try {
    risposta = await fetch(indirizzo, {
      method: metodo,
      headers: metodo === "POST" ? { "X-Airender": "1", "Content-Type": "application/json", ...(intestazioni || {}) } : {},
      body: corpo === undefined ? undefined : (corpo instanceof Blob ? corpo : JSON.stringify(corpo)),
    });
  } catch (e) {
    throw new ErroreStudio("Lo Studio non risponde: il server locale è chiuso.", "Riapri lo Studio con python -m core.studio.");
  }
  const dati = await risposta.json().catch(() => ({}));
  if (!risposta.ok) {
    const e = dati.errore || {};
    throw new ErroreStudio(e.fatto || `Il server dello Studio ha risposto ${risposta.status}.`, e.cosa_fare || "Ricarica la pagina.");
  }
  return dati;
}
const get = (u) => api("GET", u);
const post = (u, c, i) => api("POST", u, c, i);
const enc = encodeURIComponent;

function tempo(secondi) {
  const s = Math.max(0, secondi || 0);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}
function data(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d) ? iso : d.toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
}
function avviso(tipo, fatto, cosaFare) {
  return h("div", { classe: `avviso ${tipo}`, role: tipo === "errore" ? "alert" : null },
    h("b", {}, fatto), cosaFare ? h("span", { classe: "cosa-fare" }, cosaFare) : null);
}
function presto(testo) { return h("span", { classe: "presto" }, testo || "In arrivo"); }

// --- miniature illustrative --------------------------------------------------
// Disegnate qui, non generate: rendono l'idea, non sono render del modello.

const CIELI = {
  mezzogiorno: ["#3F86DA", "#BFDDF7"], estate: ["#5FA6EA", "#E3F1FB"], giorno: ["#8DB8E0", "#DDE9F3"],
  oro: ["#E98F48", "#F7D9A8"], blu: ["#14234A", "#4B5F8E"], notte: ["#070B18", "#232C45"],
  mattino: ["#BFD9F2", "#F2F6FA"], pomeriggio: ["#F0B26E", "#F8E2C2"], coperto_int: ["#B8BEC6", "#DDE0E4"],
  sera: ["#1F2C55", "#5A6A96"], notte_int: ["#080A12", "#1C2133"],
};
function illustrazione(sc) {
  const luce = sc.luce || (sc.scena === "interno" ? "mattino" : "giorno");
  let [alto, basso] = CIELI[luce] || CIELI.giorno;
  const cielo = sc.cielo || "sereno";
  if (sc.scena !== "interno" && (cielo === "coperto" || cielo === "pioggia")) [alto, basso] = ["#7F8894", "#C3C8CF"];
  if (sc.scena !== "interno" && cielo === "autunno") [alto, basso] = ["#A99A86", "#DCCDB7"];
  if (sc.scena !== "interno" && cielo === "neve") [alto, basso] = ["#AEB9C6", "#E9EDF2"];
  const buio = ["blu", "notte", "sera", "notte_int"].includes(luce);
  const finestra = buio ? "#F3C46A" : "#7FA4C8";
  const id = "g" + Math.random().toString(36).slice(2, 8);
  let corpo;
  if (sc.scena === "interno") {
    const parete = buio ? "#3A3530" : "#E9E4DC";
    corpo = `<rect width="128" height="72" fill="${parete}"/>
      <path d="M0 72 L28 50 H100 L128 72 Z" fill="${buio ? "#2A241F" : "#C9B79C"}"/>
      <path d="M28 8 V50 M100 8 V50 M0 0 L28 8 H100 L128 0" stroke="${buio ? "#4B443C" : "#CFC8BD"}" fill="none"/>
      <rect x="44" y="14" width="40" height="28" fill="url(#${id})" stroke="${buio ? "#5A5248" : "#BDB5A8"}"/>
      ${buio ? `<circle cx="34" cy="30" r="10" fill="#F3C46A" opacity=".35"/>` : ""}`;
  } else {
    const terra = cielo === "neve" ? "#F2F4F7" : (cielo === "autunno" ? "#8E7656" : (buio ? "#1D2420" : "#8FA27A"));
    const facciata = buio ? "#3C4150" : "#ECE8E1";
    corpo = `<rect width="128" height="72" fill="url(#${id})"/>
      <rect y="56" width="128" height="16" fill="${terra}"/>
      <rect x="30" y="22" width="68" height="36" fill="${facciata}"/>
      <path d="M26 22 L64 8 L102 22 Z" fill="${buio ? "#2A2E39" : "#B9B2A6"}"/>
      ${[38, 54, 70, 86].map((x) => `<rect x="${x - 4}" y="30" width="8" height="10" fill="${finestra}"/>`).join("")}
      <rect x="58" y="44" width="12" height="14" fill="${buio ? "#F3C46A" : "#6E6458"}"/>
      ${cielo === "pioggia" ? Array.from({ length: 14 }, (_, i) => `<path d="M${i * 9 + 4} ${4 + (i % 3) * 6} l-3 8" stroke="#E6EBF0" opacity=".7"/>`).join("") : ""}
      ${luce === "notte" ? `<circle cx="106" cy="12" r="5" fill="#E9EDF5"/>` : ""}
      ${["mezzogiorno", "estate", "oro"].includes(luce) && cielo === "sereno" ? `<circle cx="108" cy="12" r="6" fill="${luce === "oro" ? "#FFD08A" : "#FFF4C2"}"/>` : ""}`;
  }
  const svg = `<svg viewBox="0 0 128 72" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${alto}"/><stop offset="1" stop-color="${basso}"/></linearGradient></defs>${corpo}</svg>`;
  const t = document.createElement("template");
  t.innerHTML = svg;
  return t.content.firstChild;
}

// --- dati --------------------------------------------------------------------

function presetDi(scena) { return S.catalogo.scene[scena].preset; }
function asse(id) { return S.catalogo.scene[S.scelte.scena].assi.find((a) => a.id === id); }
function nomeVoce(idAsse, valore) {
  const a = asse(idAsse);
  const v = a && a.voci.find((x) => x.id === valore);
  return v ? v.nome : "";
}
function modelloScelto() { return S.catalogo.modelli.find((m) => m.id === S.modello); }

function scegliPreset(id) {
  const p = presetDi(S.scelte.scena).find((x) => x.id === id);
  if (!p) return;
  S.preset = id;
  S.scelte = { ...p.scelte, materiali: S.scelte.materiali, qualita: S.scelte.qualita };
  aggiornaComposto();
  render();
}
function scegliScena(scena) {
  if (scena === S.scelte.scena) return;
  const p = presetDi(scena)[0];
  S.preset = p.id;
  S.scelte = { ...p.scelte, materiali: S.scelte.materiali, qualita: S.scelte.qualita };
  aggiornaComposto();
  render();
}
function cambiaAsse(idAsse, valore) {
  S.scelte = { ...S.scelte, [idAsse]: valore };
  aggiornaComposto();
  render();
}

let attesaComponi = null;
function aggiornaComposto(subito) {
  clearTimeout(attesaComponi);
  const fai = async () => {
    try {
      S.composto = await post("/api/componi", { scelte: S.scelte, preset: S.preset });
      S.errore = null;
    } catch (e) { S.errore = e; }
    disegnaComposto();
  };
  if (subito) return fai();
  attesaComponi = setTimeout(fai, 150);
}

async function caricaVista(nome) {
  S.vista = nome;
  S.viste_viste.add(nome);
  S.descrizione = null;
  S.secco = null;
  S.risultato = { ...S.risultato, lavori: [], scelto: null, ricetta: null, caricato: false, confronto: "vista", rifai: false };
  S.passi = { ...S.passi, dati: null, errore: null, caricato: false, scelto: null, nuovo: null, pulito: null, rifai: false };
  if (!nome) { render(); return; }
  try { S.descrizione = await get(`/api/viste/${enc(nome)}`); } catch (e) { S.errore = e; }
  await caricaRender();
  if (S.scheda === "passi") await caricaPassi();
  render();
}

async function caricaDestinazione() {
  try { S.destinazione = await get(`/api/destinazione?modello=${enc(S.modello)}&varianti=${S.varianti}`); } catch (e) { S.errore = e; }
}

async function caricaRender() {
  if (!S.vista) return;
  try {
    const lavori = await get(`/api/viste/${enc(S.vista)}/render`);
    S.risultato.lavori = lavori;
    S.risultato.caricato = true;
    const ancora = lavori.find((l) => l.identificativo === S.risultato.scelto);
    if (!ancora) {
      const primo = lavori.find((l) => !l.attivo);
      S.risultato.scelto = primo ? primo.identificativo : null;
    }
    await caricaRicetta();
  } catch (e) { S.errore = e; }
}

async function caricaRicetta() {
  const scelto = lavoroScelto();
  S.risultato.ricetta = null;
  if (scelto && scelto.render) {
    try { S.risultato.ricetta = await get(`/api/lavori/${scelto.identificativo}/ricetta`); } catch (e) { S.risultato.ricetta = { errore: e }; }
  }
}

function lavoroScelto() { return S.risultato.lavori.find((l) => l.identificativo === S.risultato.scelto) || null; }

// --- lavoro in corso -----------------------------------------------------------

let giroStato = null;
function seguiLavoro(lavoro) {
  S.lavoroAttivo = lavoro;
  clearInterval(giroStato);
  giroStato = setInterval(async () => {
    try {
      const ora = await get(`/api/lavori/${S.lavoroAttivo.identificativo}`);
      const cambiato = ora.stato !== S.lavoroAttivo.stato;
      S.lavoroAttivo = ora;
      // In Passi il passo che nasce e' gia' nell'albero: il suo stato si aggiorna li'.
      if (cambiato && (S.scheda === "passi" || S.scheda === "ritocca")) await caricaPassi();
      if (!ora.attivo && S.ritocca.inviato === ora.identificativo) {
        // Un ritocco: si resta in Ritocca, sul passo appena nato o sulle aree da rifare.
        clearInterval(giroStato);
        S.lavoroAttivo = null;
        S.risultato.scelto = ora.identificativo;
        await Promise.all([caricaRender(), fineRitocco(ora)]);
      } else if (!ora.attivo && S.inFila.length) {
        // Un'altra variante dello stesso Genera aspetta: si segue quella.
        S.lavoroAttivo = await get(`/api/lavori/${S.inFila.shift()}`);
        await caricaRender();
      } else if (!ora.attivo) {
        clearInterval(giroStato);
        S.lavoroAttivo = null;
        S.risultato.scelto = ora.identificativo;
        if (S.scheda === "passi") {
          // Chi lavora per passi resta nell'albero, sul passo appena nato.
          S.passi.scelto = ora.identificativo;
          S.ultimoEsito = ora.stato === "fatto" ? null : ora;
          await Promise.all([caricaRender(), caricaPassi()]);
        } else if (ora.stato === "fatto") {
          S.ultimoEsito = null;
          await caricaRender();
          location.hash = "#risultato";
        } else {
          S.ultimoEsito = ora;
          await caricaRender();
        }
      }
    } catch (e) { S.errore = e; }
    render();
  }, 1000);
}

async function genera() {
  S.errore = null; S.secco = null;
  try {
    const risposta = await post("/api/invia", {
      vista: S.vista, scelte: S.scelte, preset: S.preset, modello: S.modello, varianti: S.varianti,
      prompt_a_mano: S.promptAMano, destinazione_mostrata: S.destinazione && S.destinazione.destinazione,
    });
    S.ultimoEsito = null;
    S.inFila = risposta.identificativi.slice(1);
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
  } catch (e) { S.errore = e; }
  render();
}

async function provaASecco() {
  S.errore = null;
  try {
    S.secco = await post("/api/prova-a-secco", {
      vista: S.vista, scelte: S.scelte, preset: S.preset, modello: S.modello, varianti: S.varianti,
      prompt_a_mano: S.promptAMano,
    });
  } catch (e) { S.errore = e; S.secco = null; }
  render();
}

async function annulla() {
  if (!S.lavoroAttivo) return;
  // Annulla ferma anche le varianti dello stesso Genera che aspettano in coda.
  const tutti = [S.lavoroAttivo.identificativo, ...S.inFila];
  S.inFila = [];
  try { for (const id of tutti) await post(`/api/lavori/${id}/annulla`, {}); } catch (e) { S.errore = e; }
  render();
}

async function rifai(lavoro) {
  S.errore = null;
  try {
    const dest = await get(`/api/destinazione?modello=${enc(lavoro.modello)}`);
    const risposta = await post(`/api/lavori/${lavoro.identificativo}/rifai`, { destinazione_mostrata: dest.destinazione });
    S.risultato.rifai = false;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaRender();
  } catch (e) { S.errore = e; }
  render();
}

// --- testata -------------------------------------------------------------------

function disegnaTestata() {
  const c = document.getElementById("collegamento");
  c.replaceChildren();
  if (!S.studio) return;
  const attiva = S.studio.coda_attiva;
  c.append(...[
    h("span", { classe: attiva ? "punto" : "punto fermo", "aria-hidden": "true" }),
    h("span", {}, attiva ? "Coda dei lavori attiva" : "Coda dei lavori ferma"),
    h("span", { classe: "tenue" }, "·"),
    h("span", { classe: "tenue" }, "Cartella delle viste: "),
    h("span", { classe: "mono", title: S.studio.cartella }, S.studio.cartella),
    S.descrizione && S.descrizione.camera ? h("span", { classe: "tenue" }, `· ${S.descrizione.camera}`) : null,
  ].filter(Boolean));
  for (const voce of document.querySelectorAll(".voce-rotaia[data-scheda]")) {
    voce.classList.toggle("attiva", voce.dataset.scheda === S.scheda);
    if (voce.dataset.scheda === S.scheda) voce.setAttribute("aria-current", "page"); else voce.removeAttribute("aria-current");
  }
}

function striscia() {
  const l = S.lavoroAttivo;
  const servizio = (l.destinazione || "").split(" (")[0] || "Il servizio";
  return h("div", { classe: "striscia", role: "status" },
    h("div", { classe: "riga tra" },
      h("span", {}, h("b", {}, l.stato === "in coda" ? "In coda" : `${servizio} sta lavorando`), ` · ${l.stato}`),
      h("span", { classe: "mono" }, tempo(l.secondi))),
    h("div", { classe: "barra" }, h("span")),
    h("div", { classe: "riga tra" },
      h("span", { classe: "piccolo", stile: "color:#A1A4AB" },
        l.stato === "in coda" && !S.studio.coda_attiva
          ? "La coda dei lavori è ferma: il lavoro aspetta che riparta."
          : `${l.preset_nome} · ${l.modello_nome}. Allplan resta libero.`),
      h("button", { classe: "btn", onclick: annulla }, "Annulla")));
}

// --- Genera --------------------------------------------------------------------

function sezioneVista() {
  const d = S.descrizione;
  const figura = h("figure", { classe: "riquadro-vista" });
  if (!S.vista) {
    figura.append(h("div", { classe: "vista-vuota" },
      h("h2", {}, "Nessuna vista ancora."),
      h("p", {}, "Catturala dalla palette in Allplan, oppure scegli un file con Usa un'altra vista…"),
      h("p", { classe: "tenue piccolo" }, "Cartella delle viste: ", h("span", { classe: "mono" }, S.studio.cartella))));
  } else {
    figura.append(h("img", { src: `/file/vista/${enc(S.vista)}`, alt: `Vista di partenza ${S.vista}` }));
    if (S.lavoroAttivo) figura.append(striscia());
  }
  const sotto = h("div", { classe: "riga tra" });
  if (d) {
    if (d.idonea) {
      sotto.append(h("span", {}, h("b", { stile: "color:var(--ok)" }, "Vista adatta"),
        h("span", { classe: "tenue" }, ` · ${d.toni} toni di grigio, sfondo uniforme al ${Math.round(d.quota_sfondo * 100)}% · ${d.larghezza}×${d.altezza} · ${d.nome}`)));
    } else {
      sotto.append(h("span", {}, h("b", { stile: "color:var(--errore)" }, "Vista non adatta"), h("span", { classe: "tenue" }, ` · ${d.nome}`)));
    }
  }
  sotto.append(h("button", { classe: "btn", onclick: () => { S.mostraViste = !S.mostraViste; render(); }, "aria-expanded": String(S.mostraViste) }, "Usa un'altra vista…"));
  const blocco = h("section", { classe: "pannello", "aria-label": "Vista di partenza" }, figura, sotto);
  if (d && !d.idonea) blocco.append(avviso("errore", d.fatto, d.cosa_fare));
  if (d && d.colori_come_materiali) {
    blocco.append(avviso("attenzione", "Il modello legge i colori della vista come materiali.",
      "Per colori veri, salva la vista con colori neutri."));
  }
  if (S.mostraViste) blocco.append(pannelloViste());
  return blocco;
}

function pannelloViste() {
  const elenco = h("div", { classe: "elenco-viste" },
    S.studio.viste.map((v) => h("button", {
      "aria-current": String(v.nome === S.vista),
      onclick: () => { S.mostraViste = false; caricaVista(v.nome); },
    }, v.nome, h("span", { classe: "tenue piccolo" }, `  ${data(v.modificata_il)}`))));
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", "aria-label": "Carica una vista da un file" });
  file.addEventListener("change", async () => {
    const scelto = file.files && file.files[0];
    if (!scelto) return;
    try {
      const r = await post("/api/viste", scelto, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(scelto.name) });
      S.studio = await get("/api/studio");
      S.mostraViste = false;
      await caricaVista(r.nome);
    } catch (e) { S.errore = e; render(); }
  });
  return h("div", { classe: "pannello" },
    h("span", { classe: "etichetta" }, "Viste nella cartella"),
    S.studio.viste.length ? elenco : h("p", { classe: "tenue" }, "La cartella non ha ancora viste."),
    h("span", { classe: "etichetta" }, "Oppure un file"),
    h("p", { classe: "tenue piccolo" }, "Lo Studio ne mette una copia nella cartella delle viste, con un nome nuovo."),
    file);
}

function tessera(nome, scelto, onclick, disegno, nota, origine) {
  return h("button", { classe: "tessera", "aria-pressed": String(!!scelto), disabled: !onclick, onclick, title: nota || null },
    disegno || h("span", { classe: "segnaposto" }, "In arrivo"),
    h("span", { classe: "didascalia" }, nome, nota ? h("small", {}, "In arrivo") : null, origine ? h("small", {}, origine) : null));
}

// Una miniatura vera (render del banco di prova) se il preset ce l'ha, altrimenti l'illustrazione.
function miniatura(p) {
  return p.miniatura ? h("img", { src: p.miniatura.url, alt: "" }) : illustrazione(p.scelte);
}
function rigaMiniature(elenco) {
  const vere = elenco.filter((p) => p.miniatura).length;
  if (!vere) return "Miniature illustrative: rendono l'idea, non sono render del modello";
  if (vere === elenco.length) return "Miniature: render veri del banco di prova, con la data sotto";
  return `${vere} miniature sono render veri (data sotto), le altre ${elenco.length - vere} illustrazioni: rendono l'idea, non sono render del modello`;
}

function chipAsse(idAsse) {
  const a = asse(idAsse);
  return h("div", { classe: "scelte-chip", role: "group", "aria-label": a.titolo },
    a.voci.map((v) => h("button", {
      classe: "chip", "aria-pressed": String(S.scelte[idAsse] === v.id), disabled: !v.attivo,
      title: v.attivo ? null : `In arrivo: ${v.nota}`,
      onclick: v.attivo ? () => cambiaAsse(idAsse, v.id) : null,
    }, v.nome)));
}

function tessereAsse(idAsse) {
  const a = asse(idAsse);
  return h("div", { classe: "griglia", role: "group", "aria-label": a.titolo },
    a.voci.map((v) => tessera(v.nome, S.scelte[idAsse] === v.id,
      v.attivo ? () => cambiaAsse(idAsse, v.id) : null,
      v.attivo ? illustrazione({ ...S.scelte, [idAsse]: v.id }) : null, v.attivo ? null : v.nota)));
}

function sintesi() {
  const s = S.scelte;
  const pezzi = ["Fotorealistico", (nomeVoce("look", s.look) || "").split(" · ")[0], nomeVoce("luce", s.luce)];
  if (s.scena === "esterno") pezzi.push(nomeVoce("cielo", s.cielo), `intorno: ${(nomeVoce("intorno", s.intorno) || "—").toLowerCase()}`,
    `verde: ${(nomeVoce("verde", s.verde) || "—").toLowerCase()}`);
  else pezzi.push(nomeVoce("fuori", s.fuori), nomeVoce("arredo", s.arredo));
  pezzi.push(`persone: ${(nomeVoce("persone", s.persone) || "—").toLowerCase()}`);
  return pezzi.filter(Boolean).join(" · ");
}

function colonnaStile() {
  const interno = S.scelte.scena === "interno";
  const scena = h("div", { classe: "riga" },
    h("span", { classe: "etichetta" }, "Scena"),
    h("div", { classe: "switch", role: "group", "aria-label": "Scena" },
      h("button", { classe: "seg", "aria-pressed": String(!interno), onclick: () => scegliScena("esterno") }, "Esterno"),
      h("button", { classe: "seg", "aria-pressed": String(interno), onclick: () => scegliScena("interno") }, "Interno")));
  const preset = h("section", { classe: "pannello", "aria-label": "Parti da un preset" },
    h("div", { classe: "riga tra" }, h("h2", {}, "Parti da un preset"),
      h("span", { classe: "tenue piccolo" }, "Ogni preset ha un prompt curato e imposta i comandi qui sotto")),
    h("p", { classe: "tenue piccolo" }, rigaMiniature(presetDi(S.scelte.scena))),
    h("div", { classe: "griglia" }, presetDi(S.scelte.scena).map((p) =>
      tessera(p.nome, S.preset === p.id, () => scegliPreset(p.id), miniatura(p), null,
        p.miniatura ? `render vero del ${p.miniatura.data}` : null))));

  const dettagli = h("details", { classe: "pannello dettagli", open: S.dettagliAperti });
  dettagli.addEventListener("toggle", () => { S.dettagliAperti = dettagli.open; });
  dettagli.append(
    h("summary", {}, h("h2", {}, "Dettagli del preset"),
      h("span", { classe: "tenue piccolo", id: "sintesi" }, sintesi()),
      h("span", { classe: "tenue piccolo" }, "· cambi un pezzo, il resto resta com'è")),
    h("div", { classe: "gruppo" }, h("h3", {}, "1 · Resa"),
      h("p", { classe: "tenue piccolo" }, "Le altre rese arrivano quando avranno il loro blocco di prompt."),
      h("div", { classe: "griglia" }, S.catalogo.rese.map((r) => tessera(r.nome, r.attivo, r.attivo ? () => {} : null,
        r.attivo ? illustrazione(S.scelte) : null, r.attivo ? null : r.nota)))),
    h("div", { classe: "gruppo" }, h("h3", {}, "2 · Look fotografico"),
      h("p", { classe: "tenue piccolo" }, "Colore, contrasto, pellicola o digitale · solo per le rese fotografiche"),
      chipAsse("look")),
    h("div", { classe: "gruppo" }, h("h3", {}, interno ? "3 · Luce" : "3 · Ora / Luce"), tessereAsse("luce")),
    interno
      ? h("div", { classe: "gruppo" }, h("h3", {}, "4 · Fuori dalle finestre e arredo"),
          h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Fuori dalle finestre"), chipAsse("fuori")),
          h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Arredo"), chipAsse("arredo")))
      : h("div", { classe: "gruppo" }, h("h3", {}, "4 · Cielo e stagione"), tessereAsse("cielo")),
    h("div", { classe: "gruppo" }, h("h3", {}, interno ? "5 · Persone" : "5 · Cosa può aggiungere il modello"),
      interno ? null : h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Intorno all'edificio"), chipAsse("intorno")),
      interno ? null : h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Verde"), chipAsse("verde")),
      h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Persone"), chipAsse("persone"))));
  return h("div", { classe: "colonna-stile" }, scena, preset, dettagli);
}

function colonnaInvio() {
  const interno = S.scelte.scena === "interno";
  const materiali = h("textarea", {
    id: "materiali", rows: "3", "aria-label": "Materiali a parole",
    placeholder: interno ? "es. pavimento in rovere chiaro, pareti in calce bianca, cucina in acciaio"
      : "es. intonaco bianco, infissi in rovere scuro, zoccolo in pietra grigia",
  });
  materiali.value = S.scelte.materiali || "";
  materiali.addEventListener("input", () => { S.scelte.materiali = materiali.value; aggiornaComposto(); });

  const esempi = interno
    ? [["#E8C547", "Intonaco interno", "calce bianca opaca"], ["#8B5A2B", "Pavimento legno", "rovere chiaro a plance larghe"], ["#5DA9E9", "Vetro", "vetro chiaro"]]
    : [["#E8C547", "Intonaco esterno", "intonaco a calce bianco"], ["#C8553D", "Copertura", "lamiera aggraffata antracite"], ["#5DA9E9", "Vetro", "vetro chiaro, riflette il cielo"]];
  const mappa = h("div", { classe: "pannello grigio", "aria-disabled": "true" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Dalla mappa materiali di Allplan"), presto()),
    h("p", { classe: "piccolo tenue" }, "Righe di esempio, non calcolato."),
    h("div", { classe: "mappa" }, h("span"), h("span", {}, "Allplan"), h("span", {}, "diventa"), h("span", {}, "rif."),
      esempi.flatMap(([c, n, d]) => [h("span", { classe: "tinta", stile: `background:${c}` }), h("span", {}, n), h("span", {}, d), h("span", {}, "+")])),
    h("p", { classe: "piccolo tenue" }, "Ogni riga: materiale di Allplan, il suo colore nella mappa, cosa deve diventare a parole e, se vuoi, una foto del materiale. Serve prima: verificare che Allplan dia una vista colorata per materiale con la stessa camera (PRD §9)."));

  const prompt = h("textarea", { id: "prompt", classe: "prompt", "aria-label": "Prompt completo, in inglese" });
  prompt.value = S.promptAMano !== null ? S.promptAMano : (S.composto ? S.composto.prompt : "");
  prompt.addEventListener("input", () => {
    S.promptAMano = prompt.value;
    document.getElementById("caratteri").textContent = `${prompt.value.length} caratteri · scritto a mano`;
    const nota = document.getElementById("nota-prompt");
    if (nota) nota.classList.remove("nascosto");
  });
  const cosaParte = h("section", { classe: "pannello", "aria-label": "Cosa parte" },
    h("span", { classe: "etichetta" }, "Cosa parte, in breve"),
    h("p", { id: "riassunto" }, S.composto ? S.composto.riassunto : "…"),
    h("p", { classe: "tenue piccolo" }, `Blocchi di prompt ${S.catalogo.versione_blocchi}: testi scelti, non ancora provati con il modello.`),
    h("button", { classe: "btn link", "aria-expanded": String(S.mostraPrompt), onclick: () => { S.mostraPrompt = !S.mostraPrompt; render(); } },
      S.mostraPrompt ? "Nascondi il prompt" : "Mostra e modifica il prompt completo"),
    S.mostraPrompt ? h("div", { classe: "sotto-gruppo" },
      h("p", { classe: "tenue piccolo" }, "Testo vero che parte al modello, in inglese. Se lo modifichi, i comandi a sinistra non lo toccano più finché non premi «Ricomponi»."),
      prompt,
      h("div", { classe: "riga tra" },
        h("span", { classe: "tenue piccolo mono", id: "caratteri" },
          S.promptAMano !== null ? `${S.promptAMano.length} caratteri · scritto a mano` : `${S.composto ? S.composto.caratteri : 0} caratteri`),
        h("button", { classe: "btn", onclick: () => { S.promptAMano = null; aggiornaComposto(true).then(render); } }, "Ricomponi dalle scelte")),
      h("p", { id: "nota-prompt", classe: S.promptAMano !== null ? "piccolo" : "piccolo nascosto", stile: "color:var(--attenzione)" },
        "Prompt modificato a mano: parte questo testo, non le scelte a sinistra.")) : null);

  const modelli = h("select", { id: "modello", "aria-label": "Modello" },
    S.catalogo.modelli.map((m) => h("option", { value: m.id, selected: m.id === S.modello, disabled: !m.verificato },
      m.nome + (m.id === S.studio.modello_predefinito ? " — predefinito" : "") + (m.verificato ? "" : " — schema non verificato"))),
    S.catalogo.modelli_non_provati.map((n) => h("option", { disabled: true }, `${n} — non ancora provato`)));
  modelli.addEventListener("change", async () => { S.modello = modelli.value; S.secco = null; await caricaDestinazione(); render(); });

  const qualita = h("div", { classe: "switch", role: "group", "aria-label": "Qualità" },
    asse("qualita").voci.map((v) => h("button", {
      classe: "seg", "aria-pressed": String(S.scelte.qualita === v.id), onclick: () => cambiaAsse("qualita", v.id),
    }, v.id === "32k" ? "Altissima definizione (32k) — da confrontare" : v.nome)));

  const scelteInvio = h("section", { classe: "pannello", "aria-label": "Modello e qualità" },
    h("span", { classe: "etichetta" }, "I miei preset"),
    h("div", { classe: "riga" }, h("select", { "aria-label": "I miei preset", disabled: true }, h("option", {}, "Nessuno — scelte libere")),
      h("button", { classe: "btn", disabled: true }, "Salva queste scelte ", presto())),
    h("span", { classe: "etichetta" }, "Modello"), modelli,
    h("span", { classe: "etichetta" }, "Qualità"), qualita,
    h("div", { classe: "riga" }, h("button", { classe: "btn", disabled: true }, "Fedeltà al disegno: rigida / bilanciata / libera ", presto("Da provare"))),
    h("span", { classe: "etichetta" }, "Varianti per invio"),
    h("div", { classe: "switch", role: "group", "aria-label": "Varianti per invio" },
      Array.from({ length: S.catalogo.varianti_massime }, (_, i) => i + 1).map((n) => h("button", {
        classe: "seg", "aria-pressed": String(S.varianti === n),
        onclick: async () => { S.varianti = n; S.secco = null; await caricaDestinazione(); render(); },
      }, String(n)))),
    S.varianti > 1 ? h("p", { classe: "tenue piccolo" }, `${S.varianti} lavori in coda con le stesse scelte, uno dopo l'altro: ogni variante è un invio.`) : null,
    h("div", { classe: "riga" }, h("button", { classe: "btn", disabled: true }, "Immagine di riferimento per lo stile ", presto())));

  return h("div", { classe: "colonna-invio" },
    h("section", { classe: "pannello", "aria-label": "Materiali" },
      h("span", { classe: "etichetta" }, "Materiali a parole"),
      h("p", { classe: "tenue piccolo" }, "Passano al modello come li scrivi, anche in italiano."), materiali),
    mappa, cosaParte, scelteInvio, pannelloInvio());
}

function motivoGeneraSpento() {
  if (!S.vista) return "Serve una vista: catturala dalla palette o scegline una con Usa un'altra vista…";
  if (S.descrizione && !S.descrizione.idonea) return "La vista non è adatta: guarda il motivo sopra.";
  if (S.lavoroAttivo) return "Un lavoro è già in corso: aspetta che finisca o annullalo.";
  const m = modelloScelto();
  if (m && !m.verificato) return "Lo schema di questo modello non è verificato: l'invio si fermerebbe prima di partire.";
  if (!S.destinazione) return "Sto leggendo la destinazione.";
  return null;
}

function pannelloInvio() {
  const d = S.destinazione;
  const spento = motivoGeneraSpento();
  const blocco = h("section", { classe: "pannello", "aria-label": "Invio" });
  if (d) {
    blocco.append(
      h("p", { classe: "destinazione" }, "La vista va a ", h("b", {}, d.destinazione),
        ` (${d.fornitore}, ${d.modello_nome})`, d.senza_ripiego ? ", senza ripiego su altri servizi." : "."),
      h("p", { classe: "destinazione" }, "Costo: ", h("b", {}, d.costo)));
    if (d.cosa_manca) blocco.append(avviso("errore", `Attenzione: ${d.cosa_manca}`, "Scegli Nano Banana 2, il modello predefinito."));
  }
  if (!S.studio.coda_attiva) {
    blocco.append(avviso("attenzione", "La coda dei lavori non sta girando: un lavoro resterebbe in attesa.",
      "Chiudi e riapri lo Studio, che la fa partire."));
  }
  blocco.append(h("div", { classe: "azioni" },
    h("button", { classe: "btn", onclick: provaASecco, disabled: !S.vista }, "Prova a secco"),
    h("button", { classe: "btn primario", onclick: genera, disabled: !!spento, id: "genera" },
      S.lavoroAttivo ? "In corso…" : (S.varianti > 1 ? `Genera ${S.varianti} render` : "Genera render"))));
  if (spento) blocco.append(h("p", { classe: "tenue piccolo" }, spento));
  if (S.secco) {
    const s = S.secco;
    blocco.append(h("div", { classe: "avviso" + (s.problemi.length ? " attenzione" : ""), role: "status" },
      h("b", {}, "Prova a secco: non ho inviato niente."),
      h("span", {}, `Partirebbe${s.varianti > 1 ? ` ${s.varianti} volte` : ""} verso ${s.destinazione.destinazione}, ${s.caratteri} caratteri di prompt.`),
      s.problemi.length
        ? s.problemi.map((p) => h("span", {}, `Fermerebbe l'invio: ${p.fatto} `, h("span", { classe: "cosa-fare" }, p.cosa_fare)))
        : h("span", {}, "Niente fermerebbe l'invio.")));
  }
  return blocco;
}

function schermataGenera() {
  const sopra = [];
  if (S.errore) sopra.push(avviso("errore", S.errore.fatto, S.errore.cosa_fare));
  const e = S.ultimoEsito;
  if (e && !S.lavoroAttivo) {
    sopra.push(h("div", { classe: "avviso errore", role: "alert" },
      h("b", {}, e.stato === "annullato" ? "Lavoro annullato." : "L'invio non è andato."),
      h("span", {}, e.fatto || ""), e.cosa_fare ? h("span", { classe: "cosa-fare" }, e.cosa_fare) : null,
      h("span", { classe: "piccolo tenue" }, `Le scelte sono rimaste: ${e.preset_nome} · ${e.modello_nome}. Puoi rifarlo da Risultato con la stessa ricetta.`)));
  }
  return [h("h1", { classe: "nascosto" }, "Genera"), ...sopra, sezioneVista(), h("div", { classe: "colonne" }, colonnaStile(), colonnaInvio())];
}

function disegnaComposto() {
  const r = document.getElementById("riassunto");
  if (r && S.composto) r.textContent = S.composto.riassunto;
  const s = document.getElementById("sintesi");
  if (s) s.textContent = sintesi();
  const p = document.getElementById("prompt");
  if (p && S.promptAMano === null && S.composto && document.activeElement !== p) p.value = S.composto.prompt;
  const c = document.getElementById("caratteri");
  if (c && S.promptAMano === null && S.composto) c.textContent = `${S.composto.caratteri} caratteri`;
  if (S.errore && S.scheda === "genera" && !document.querySelector(".avviso.errore")) render();
}

// --- Risultato -----------------------------------------------------------------

function nomeRender(l) { return `${l.modello_nome} · ${l.preset_nome} · ${data(l.creato_il)}`; }

// La linea del prima/dopo, uguale in Risultato e in Passi. `st` tiene la
// posizione della linea (st.x, da 0 a 100) fra un disegno e l'altro.
function primaDopo(st, srcA, nomeA, srcB, nomeB, altB) {
  const nota = h("p", { classe: "tenue piccolo", id: "nota-proporzioni" });
  const imgA = h("img", { src: srcA, alt: nomeA, draggable: "false" });
  const imgB = h("img", { src: srcB, alt: altB || nomeB, classe: "sopra", draggable: "false" });
  const linea = h("div", {
    classe: "linea", role: "slider", tabindex: "0", "aria-label": "Sposta la linea fra prima e dopo",
    "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": String(Math.round(st.x)),
  }, h("span", { classe: "maniglia", "aria-hidden": "true" }, "⇔"));
  const palco = h("div", { classe: "confronto", stile: `--x:${st.x}%; aspect-ratio:16/9` },
    imgA, imgB, linea,
    h("span", { classe: "nome-lato sinistra" }, nomeA), h("span", { classe: "nome-lato destra" }, nomeB));
  const sposta = (x) => {
    st.x = Math.max(0, Math.min(100, x));
    palco.style.setProperty("--x", `${st.x}%`);
    linea.setAttribute("aria-valuenow", String(Math.round(st.x)));
    const valore = document.getElementById("valore-linea");
    if (valore) valore.textContent = `${Math.round(st.x)}%`;
  };
  const daPuntatore = (ev) => { const b = palco.getBoundingClientRect(); sposta(((ev.clientX - b.left) / b.width) * 100); };
  palco.addEventListener("pointerdown", (ev) => { palco.setPointerCapture(ev.pointerId); daPuntatore(ev); linea.focus(); });
  palco.addEventListener("pointermove", (ev) => { if (palco.hasPointerCapture(ev.pointerId)) daPuntatore(ev); });
  linea.addEventListener("keydown", (ev) => {
    const passo = ev.shiftKey ? 10 : 2;
    if (ev.key === "ArrowLeft") { sposta(st.x - passo); ev.preventDefault(); }
    if (ev.key === "ArrowRight") { sposta(st.x + passo); ev.preventDefault(); }
    if (ev.key === "Home") { sposta(0); ev.preventDefault(); }
    if (ev.key === "End") { sposta(100); ev.preventDefault(); }
  });
  const proporzioni = () => {
    if (!imgA.naturalWidth || !imgB.naturalWidth) return;
    palco.style.aspectRatio = `${imgB.naturalWidth} / ${imgB.naturalHeight}`;
    const ra = imgA.naturalWidth / imgA.naturalHeight, rb = imgB.naturalWidth / imgB.naturalHeight;
    const scarto = Math.abs(ra - rb) / rb;
    nota.textContent = scarto < 0.005
      ? `${nomeA} riportata a ${imgB.naturalWidth}×${imgB.naturalHeight}, la misura del render: stesse proporzioni, gli spigoli si sovrappongono.`
      : `${nomeA} (${imgA.naturalWidth}×${imgA.naturalHeight}) stirata a ${imgB.naturalWidth}×${imgB.naturalHeight} per sovrapporla: le proporzioni differiscono del ${(scarto * 100).toFixed(1).replace(".", ",")}%, gli spigoli possono non coincidere per questo.`;
  };
  imgA.addEventListener("load", proporzioni);
  imgB.addEventListener("load", proporzioni);
  return { palco, nota };
}

function confronto(l) {
  const r = S.risultato;
  const altro = r.confronto !== "vista" && r.lavori.find((x) => x.identificativo === r.confronto && x.render);
  const srcA = altro ? `/file/render/${altro.identificativo}` : `/file/vista/${enc(S.vista)}`;
  const nomeA = altro ? altro.modello_nome : "Vista Allplan";
  const srcB = `/file/render/${l.identificativo}`;
  const sottotitolo = {
    scorri: "Una sola immagine: a sinistra della linea il prima, a destra il render.",
    affiancati: "Le due immagini una accanto all'altra, stesso zoom.",
    solo: "Solo il render, grande.",
  }[r.modo];
  const modi = h("div", { classe: "switch", role: "group", "aria-label": "Modo di confronto" },
    [["scorri", "Prima / dopo"], ["affiancati", "Affiancati"], ["solo", "Solo render"]].map(([id, n]) =>
      h("button", { classe: "seg", "aria-pressed": String(r.modo === id), onclick: () => { r.modo = id; render(); } }, n)));
  const altri = r.lavori.filter((x) => x.render && x.identificativo !== l.identificativo);
  const scegliA = h("select", { "aria-label": "Confronta con" },
    h("option", { value: "vista", selected: r.confronto === "vista" }, "Vista di partenza"),
    altri.map((x) => h("option", { value: x.identificativo, selected: r.confronto === x.identificativo }, `Render ${nomeRender(x)}`)));
  scegliA.addEventListener("change", () => { r.confronto = scegliA.value; render(); });

  let palco, nota;
  if (r.modo === "scorri") {
    ({ palco, nota } = primaDopo(r, srcA, nomeA, srcB, l.modello_nome, `Render ${l.modello_nome}`));
  } else if (r.modo === "affiancati") {
    palco = h("div", { classe: "affiancati" },
      h("figure", {}, h("img", { src: srcA, alt: nomeA }), h("figcaption", { classe: "tenue piccolo" }, nomeA)),
      h("figure", {}, h("img", { src: srcB, alt: `Render ${l.modello_nome}` }), h("figcaption", { classe: "tenue piccolo" }, `Render · ${l.modello_nome}`)));
  } else {
    palco = h("div", { classe: "solo" }, h("img", { src: srcB, alt: `Render ${l.modello_nome}` }));
  }
  return h("div", { classe: "palco" },
    h("div", { classe: "riga tra" }, h("div", {}, h("h1", {}, "È ancora il tuo edificio?"), h("p", { classe: "tenue" }, sottotitolo)), modi),
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Confronta con"), h("div", { stile: "min-width:260px" }, scegliA)),
    palco,
    r.modo === "scorri" ? h("div", { classe: "riga tra" },
      h("span", { classe: "tenue piccolo" }, "Trascina la linea, oppure tasti ← → (con Maiusc il passo è più lungo)"),
      h("span", { classe: "mono", id: "valore-linea" }, `${Math.round(r.x)}%`)) : null,
    r.modo === "scorri" ? nota : null);
}

function elencoRender() {
  const r = S.risultato;
  return h("section", { classe: "pannello", "aria-label": "Render di questa vista" },
    h("span", { classe: "etichetta" }, "Render di questa vista"),
    r.lavori.length ? h("div", { classe: "elenco-render" }, r.lavori.map((l) => h("button", {
      "aria-current": String(l.identificativo === r.scelto),
      disabled: l.attivo,
      onclick: async () => { r.scelto = l.identificativo; r.rifai = false; if (r.confronto === l.identificativo) r.confronto = "vista"; await caricaRicetta(); render(); },
    },
    l.render ? h("img", { src: `/file/render/${l.identificativo}`, alt: "" }) : h("span", { classe: "segnaposto", stile: "width:64px;height:40px" }),
    h("span", {}, nomeRender(l), h("span", { classe: "stato-lavoro", stile: "display:block" }, l.stato))))) : h("p", { classe: "tenue" }, "Nessun render da questa vista."),
    h("p", { classe: "tenue piccolo" }, "Per un A/B fra modelli: genera la stessa vista con un altro modello, poi scegli «Confronta con»."));
}

function tenuta() {
  return h("section", { classe: "pannello", "aria-label": "Tenuta della geometria" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Tenuta della geometria"), presto("Misura in arrivo")),
    h("span", { classe: "misura" }, "Non misurata"),
    h("p", { classe: "tenue piccolo" }, "Il controllo automatico degli spigoli non c'è ancora. Per ora giudica tu, confrontando le due immagini."));
}

function ricettaPannello(l) {
  const ric = S.risultato.ricetta;
  const scelte = l.scelte || {};
  const righe = [
    ["Stile", `${l.preset_nome}${l.prompt_a_mano ? " · prompt scritto a mano" : ""}`],
    ["Scelte", l.riassunto || "—"],
    ["Modello", l.modello_nome],
    ["Le tue parole", scelte.materiali ? scelte.materiali : "nessuna"],
  ];
  if (scelte.scena === "esterno" && !l.parte_da) righe.push(["Intorno", scelte.intorno ? (nomeVoceScena("esterno", "intorno", scelte.intorno) || scelte.intorno).toLowerCase() : "non indicato"]);
  righe.push(["Servizio", `${l.destinazione}${ric && ric.fallback === "false" ? ", senza ripiego" : ""}`]);
  if (ric && !ric.errore) {
    righe.push(["Costo", ric.crediti || "non letto dal servizio"]);
    righe.push(["Seme", ric.seme === null || ric.seme === undefined ? "nessuno: il modello non ne usa uno" : String(ric.seme)]);
    righe.push(["Render", h("span", { classe: "mono" }, ric.percorso_render)]);
    righe.push(["Ricetta", h("span", { classe: "mono" }, ric.percorso_ricetta)]);
  } else if (ric && ric.errore) {
    righe.push(["Ricetta", ric.errore.fatto]);
  } else {
    righe.push(["Costo", "nessun render: niente da leggere"]);
  }
  return h("section", { classe: "pannello", "aria-label": "Com'è stato fatto" },
    h("span", { classe: "etichetta" }, "Com'è stato fatto"),
    h("dl", { classe: "ricetta" }, righe.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])));
}

function nomeVoceScena(scena, idAsse, valore) {
  const a = S.catalogo.scene[scena].assi.find((x) => x.id === idAsse);
  const v = a && a.voci.find((x) => x.id === valore);
  return v ? v.nome : "";
}

function adesso(l) {
  const r = S.risultato;
  const dest = S.catalogo.modelli.find((m) => m.id === l.modello);
  const conferma = r.rifai ? h("div", { classe: "avviso" },
    h("b", {}, "Rifai con la stessa ricetta"),
    h("span", {}, `La vista va di nuovo a ${l.destinazione}. ${S.destinazione && S.destinazione.modello === l.modello ? `Costo: ${S.destinazione.costo}.` : ""}`),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => rifai(l), disabled: !!S.lavoroAttivo || (dest && !dest.verificato) }, "Conferma e rifai"),
      h("button", { classe: "btn", onclick: () => { r.rifai = false; render(); } }, "Lascia stare"))) : null;
  const copia = async () => {
    try {
      const blob = await (await fetch(`/file/render/${l.identificativo}`)).blob();
      await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
      S.errore = null;
    } catch (e) {
      S.errore = new ErroreStudio("Il browser non ha copiato l'immagine.", "Apri la cartella e copia il file da lì.");
    }
    render();
  };
  return h("section", { classe: "pannello", "aria-label": "Adesso" },
    h("span", { classe: "etichetta" }, "Adesso"),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => { r.rifai = true; render(); }, disabled: !!S.lavoroAttivo }, "Rifai con la stessa ricetta"),
      h("button", { classe: "btn", onclick: () => post("/api/apri-cartella", { quale: "render" }).catch((e) => { S.errore = e; render(); }) }, "Apri cartella"),
      l.render ? h("button", { classe: "btn", onclick: copia }, "Copia immagine") : null,
      h("button", { classe: "btn", disabled: true }, "Esporta per il cliente ", presto())),
    conferma);
}

function cambiaParte() {
  return h("section", { classe: "pannello grigio", "aria-label": "Cambia una parte" },
    h("span", { classe: "etichetta" }, "Cambia una parte"),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn", disabled: true }, "Cambia un materiale ", presto()),
      h("button", { classe: "btn", disabled: true }, "Annota per aree ", presto()),
      h("button", { classe: "btn", disabled: true }, "Fai un video da qui ", presto("Dopo la v1"))));
}

function schermataRisultato() {
  const r = S.risultato;
  const sopra = S.errore ? [avviso("errore", S.errore.fatto, S.errore.cosa_fare)] : [];
  const attivo = S.lavoroAttivo && S.lavoroAttivo.vista === S.vista ? S.lavoroAttivo : null;
  if (!S.vista || (r.caricato && !r.lavori.length && !attivo)) {
    return [...sopra, h("section", { classe: "pannello" },
      h("h1", {}, "È ancora il tuo edificio?"),
      h("p", {}, "Nessun render ancora. Scegli uno stile in Genera e premi Genera."),
      h("div", { classe: "azioni" }, h("a", { classe: "btn", href: "#genera" }, "Vai a Genera")))];
  }
  if (attivo) {
    return [...sopra, h("div", { classe: "layout-risultato" },
      h("div", { classe: "palco" },
        h("h1", {}, "È ancora il tuo edificio?"),
        h("p", { classe: "tenue" }, "Il render arriva qui appena il servizio lo manda."),
        h("figure", { classe: "riquadro-vista" }, h("img", { src: `/file/vista/${enc(S.vista)}`, alt: "Vista di partenza", stile: "max-height:none" }), striscia())),
      h("div", { classe: "lato" }, elencoRender(), tenuta()))];
  }
  const l = lavoroScelto();
  if (!l) return [...sopra, h("p", { classe: "tenue" }, "Sto leggendo i render…")];
  const avvisiTesta = (l.avvisi || []).filter((a) => a.includes("diverso da quello annunciato"));
  const altriAvvisi = (l.avvisi || []).filter((a) => !avvisiTesta.includes(a));
  if (!l.render) {
    return [...sopra, h("div", { classe: "layout-risultato" },
      h("div", { classe: "palco" },
        h("h1", {}, "È ancora il tuo edificio?"),
        h("div", { classe: "avviso errore", role: "alert" },
          h("b", {}, l.stato === "annullato" ? "Questo lavoro è stato annullato." : "Questo lavoro non ha prodotto un render."),
          h("span", {}, l.fatto || ""), l.cosa_fare ? h("span", { classe: "cosa-fare" }, l.cosa_fare) : null),
        h("figure", { classe: "riquadro-vista" }, h("img", { src: `/file/vista/${enc(S.vista)}`, alt: "Vista di partenza" }))),
      h("div", { classe: "lato" }, elencoRender(), ricettaPannello(l), adesso(l)))];
  }
  return [...sopra,
    avvisiTesta.map((a) => avviso("errore", a)),
    h("div", { classe: "layout-risultato" },
      confronto(l),
      h("div", { classe: "lato" }, elencoRender(), tenuta(), ricettaPannello(l), adesso(l), cambiaParte(),
        altriAvvisi.length ? h("section", { classe: "pannello" }, h("span", { classe: "etichetta" }, "Note del motore"),
          altriAvvisi.map((a) => h("p", { classe: "piccolo tenue" }, a))) : null))];
}

// --- Ritocca -------------------------------------------------------------------
// Aree e note su un render (DESIGN.md, Studio · Ritocca). Si disegna con il
// rettangolo o con la selezione libera; a ogni area si attacca una nota
// adesiva numerata. Tutte le note partono in un invio solo, e il risultato e'
// un passo nuovo nell'albero, figlio del render ritoccato. Le coordinate
// vanno da 0 a 1 sull'immagine, come in core/aree.py.

// Un punto del lazo entra solo se dista almeno questo dal precedente (in
// frazione del lato): un contorno di poche decine di punti basta, e la
// richiesta resta piccola.
const LAZO_PASSO_MINIMO = 0.004;
// Sotto questa misura (frazione del lato) un trascinamento e' un clic sbagliato, non un'area.
const AREA_MINIMA = 0.01;

function passoRitoccabile(id) {
  const x = passoDa(id);
  return x && x.si_parte ? x : null;
}

// Il render su cui si ritocca: quello scelto prima, o il passo scelto nei
// Passi, o il render piu' recente.
function baseRitocco() {
  const r = S.ritocca;
  if (!S.passi.dati) return null;
  if (r.da && passoRitoccabile(r.da)) return passoDa(r.da);
  const scelto = passoRitoccabile(S.passi.scelto);
  const fatti = S.passi.dati.passi.filter((x) => x.si_parte).sort((a, b) => (b.creato_il || "").localeCompare(a.creato_il || ""));
  const base = scelto || fatti[0] || null;
  r.da = base ? base.identificativo : null;
  return base;
}

// Entrando in Ritocca: il render da ritoccare, il modello e la sua destinazione, da mostrare prima di Applica.
async function prontoRitocca() {
  const base = baseRitocco();
  if (!base) return;
  if (!S.ritocca.modello) S.ritocca.modello = modelloVerificato(base.modello);
  await destinazioneDi(S.ritocca.modello);
  componiRitocco();
}

function cambiaBaseRitocco(id) {
  const r = S.ritocca;
  if (r.da === id) return;
  r.da = id; r.aree = []; r.composto = null; r.errore = null; r.esito = null;
  render();
}

function ritoccoBloccato() {
  return !!(S.lavoroAttivo && S.ritocca.inviato && S.lavoroAttivo.identificativo === S.ritocca.inviato);
}

function areePerIlServer() {
  return S.ritocca.aree.map((a) => ({ forma: a.forma, punti: a.punti, nota: a.nota }));
}

function noteVuote() { return S.ritocca.aree.map((a, i) => (a.nota.trim() ? null : i + 1)).filter(Boolean); }

function motivoApplicaRitoccoSpento() {
  const r = S.ritocca;
  if (S.lavoroAttivo) return "Un lavoro è in corso: Applica si accende quando finisce, così un doppio clic non si paga due volte.";
  if (!r.aree.length) return "Disegna un'area, poi scrivi cosa cambiare nella sua nota.";
  const vuote = noteVuote();
  if (vuote.length) return `${vuote.length === 1 ? "L'area" : "Le aree"} ${vuote.join(", ")} ${vuote.length === 1 ? "non ha" : "non hanno"} una nota: scrivila, oppure togli l'area.`;
  const d = S.passi.dest[r.modello];
  if (d && d.cosa_manca) return d.cosa_manca;
  return "";
}

let attesaRitocco = null;
function componiRitocco() {
  const r = S.ritocca;
  clearTimeout(attesaRitocco);
  if (!r.aree.length || noteVuote().length) { r.composto = null; disegnaApplicaRitocco(); return; }
  attesaRitocco = setTimeout(async () => {
    try { r.composto = await post("/api/ritocca/componi", { vista: S.vista, da: r.da, aree: areePerIlServer() }); r.errore = null; }
    catch (e) { r.composto = null; r.errore = e; }
    disegnaApplicaRitocco();
  }, 250);
}

// Aggiorna Applica, il prompt e gli avvisi delle note mentre si scrive,
// senza ridisegnare: la nota non perde il cursore.
function disegnaApplicaRitocco() {
  const r = S.ritocca;
  const n = r.aree.length;
  const bottone = document.getElementById("applica-ritocco");
  if (bottone) {
    bottone.disabled = !!motivoApplicaRitoccoSpento();
    bottone.textContent = n ? `Applica ${n === 1 ? "la nota" : `le ${n} note`} · un invio` : "Applica · un invio";
  }
  const motivo = document.getElementById("motivo-ritocco");
  if (motivo) motivo.textContent = motivoApplicaRitoccoSpento();
  const prompt = document.getElementById("prompt-ritocco");
  if (prompt) prompt.value = r.composto ? r.composto.prompt : "";
  const car = document.getElementById("caratteri-ritocco");
  if (car) car.textContent = r.composto ? `${r.composto.caratteri} caratteri` : "";
  const err = document.getElementById("errore-ritocco");
  if (err) err.replaceChildren(r.errore ? avviso("errore", r.errore.fatto, r.errore.cosa_fare) : "");
  r.aree.forEach((a, i) => {
    for (const id of [`manca-nota-${i}`, `manca-elenco-${i}`]) {
      const el = document.getElementById(id);
      if (el) el.hidden = !!a.nota.trim();
    }
  });
}

function scriviNota(i, testo, da) {
  const a = S.ritocca.aree[i];
  if (!a) return;
  a.nota = testo;
  // La stessa nota sta sull'immagine e nell'elenco: si tengono uguali.
  const altro = document.getElementById(da === "foglietto" ? `elenco-nota-${i}` : `foglietto-nota-${i}`);
  if (altro && altro.value !== testo) altro.value = testo;
  componiRitocco();
  disegnaApplicaRitocco();
}

function togliArea(i) {
  S.ritocca.aree.splice(i, 1);
  S.ritocca.composto = null;
  render();
  componiRitocco();
}

function puntiSvg(a) {
  if (a.forma === "rettangolo") {
    const [[x0, y0], [x1, y1]] = a.punti;
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
  }
  return a.punti;
}
function attributoPunti(punti) { return punti.map(([x, y]) => `${(x * 1000).toFixed(1)},${(y * 1000).toFixed(1)}`).join(" "); }

// Dove si attacca la nota di un'area appena chiusa: a destra dell'area se
// c'e' posto, altrimenti a sinistra; mai fuori dall'immagine.
function posizioneNota(punti) {
  const xs = punti.map((p) => p[0]), ys = punti.map((p) => p[1]);
  const destra = Math.max(...xs), sinistra = Math.min(...xs), alto = Math.min(...ys);
  const x = destra + 0.02 < 0.72 ? destra + 0.02 : Math.max(0, sinistra - 0.27);
  return { x, y: Math.min(Math.max(0, alto), 0.8) };
}

function telaRitocco(base) {
  const r = S.ritocca;
  const bloccato = ritoccoBloccato();
  const img = h("img", { src: `/file/render/${base.identificativo}`, alt: `Render del passo ${base.numero}`, draggable: "false" });
  // L'SVG si scrive come testo: il parser HTML lo mette da solo nel suo
  // spazio dei nomi, e i punti sono solo numeri.
  const contenitore = h("div");
  contenitore.innerHTML = `<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" class="aree-svg" aria-hidden="true">${
    r.aree.map((a) => `<polygon class="contorno-area" points="${attributoPunti(puntiSvg(a))}"></polygon>`).join("")
  }<polyline class="contorno-area in-corso" points=""></polyline></svg>`;
  const disegno = contenitore.firstElementChild;
  const traccia = disegno.querySelector("polyline");
  const numeri = r.aree.map((a, i) => {
    const [x, y] = puntiSvg(a)[0];
    return h("span", { classe: "numero-area", stile: `left:${x * 100}%;top:${y * 100}%`, "aria-hidden": "true" }, String(i + 1));
  });
  const note = r.aree.map((a, i) => foglietto(a, i, bloccato));
  const tela = h("div", { classe: `tela-ritocco${bloccato ? " bloccata" : ""}`, "data-strumento": r.strumento },
    img, disegno, ...numeri, ...note);
  if (bloccato) return tela;

  // Il disegno: rettangolo da un angolo all'altro, o lazo che si chiude da solo al rilascio.
  let tratto = null;
  const punto = (ev) => {
    const b = img.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (ev.clientX - b.left) / b.width)), Math.min(1, Math.max(0, (ev.clientY - b.top) / b.height))];
  };
  tela.addEventListener("pointerdown", (ev) => {
    if (ev.target.closest(".foglietto") || ev.button !== 0) return;
    ev.preventDefault();
    tela.setPointerCapture(ev.pointerId);
    tratto = { inizio: punto(ev), punti: [punto(ev)] };
  });
  tela.addEventListener("pointermove", (ev) => {
    if (!tratto || !tela.hasPointerCapture(ev.pointerId)) return;
    const p = punto(ev);
    if (r.strumento === "rettangolo") {
      tratto.punti = [tratto.inizio, p];
      traccia.setAttribute("points", attributoPunti(puntiSvg({ forma: "rettangolo", punti: tratto.punti })) + " " + attributoPunti([tratto.inizio]));
    } else {
      const ultimo = tratto.punti[tratto.punti.length - 1];
      if (Math.hypot(p[0] - ultimo[0], p[1] - ultimo[1]) >= LAZO_PASSO_MINIMO) tratto.punti.push(p);
      traccia.setAttribute("points", attributoPunti(tratto.punti));
    }
  });
  const chiudi = () => {
    if (!tratto) return;
    const t = tratto; tratto = null;
    traccia.setAttribute("points", "");
    let area = null;
    if (r.strumento === "rettangolo" && t.punti.length === 2) {
      const [[ax, ay], [bx, by]] = t.punti;
      if (Math.abs(bx - ax) >= AREA_MINIMA && Math.abs(by - ay) >= AREA_MINIMA) {
        area = { forma: "rettangolo", punti: [[Math.min(ax, bx), Math.min(ay, by)], [Math.max(ax, bx), Math.max(ay, by)]] };
      }
    } else if (r.strumento === "libera" && t.punti.length >= 3) {
      const xs = t.punti.map((p) => p[0]), ys = t.punti.map((p) => p[1]);
      if (Math.max(...xs) - Math.min(...xs) >= AREA_MINIMA && Math.max(...ys) - Math.min(...ys) >= AREA_MINIMA) {
        area = { forma: "libera", punti: t.punti };
      }
    }
    if (!area) return;
    area.punti = area.punti.map(([x, y]) => [Number(x.toFixed(4)), Number(y.toFixed(4))]);
    area.nota = "";
    area.posNota = posizioneNota(puntiSvg(area));
    r.aree.push(area);
    r.composto = null;
    r.esito = null;
    render();
    const campo = document.getElementById(`foglietto-nota-${r.aree.length - 1}`);
    if (campo) campo.focus();
    disegnaApplicaRitocco();
  };
  tela.addEventListener("pointerup", chiudi);
  tela.addEventListener("pointercancel", () => { tratto = null; traccia.setAttribute("points", ""); });
  return tela;
}

// La nota adesiva di un'area: si sposta trascinando la sua testata, l'area no.
function foglietto(a, i, bloccato) {
  const campo = h("textarea", {
    id: `foglietto-nota-${i}`, rows: "2", "aria-label": `Nota dell'area ${i + 1}`,
    placeholder: "Cosa cambiare qui", readonly: bloccato || null,
  });
  campo.value = a.nota;
  campo.addEventListener("input", () => scriviNota(i, campo.value, "foglietto"));
  const testata = h("div", { classe: "testata-foglietto", title: "Trascina per spostare la nota" },
    h("b", {}, `${i + 1} · ${a.forma === "rettangolo" ? "rettangolo" : "selezione libera"}`),
    bloccato ? null : h("button", { classe: "togli", "aria-label": `Togli l'area ${i + 1} e la sua nota`, onclick: () => togliArea(i) }, "×"));
  const nota = h("div", { classe: "foglietto", stile: `left:${a.posNota.x * 100}%;top:${a.posNota.y * 100}%` },
    testata, campo,
    h("span", { classe: "manca-nota", id: `manca-nota-${i}`, hidden: !!a.nota.trim() }, "Scrivi la nota, oppure togli l'area."));
  if (!bloccato) {
    testata.addEventListener("pointerdown", (ev) => {
      if (ev.target.closest("button")) return;
      ev.preventDefault();
      testata.setPointerCapture(ev.pointerId);
      const tela = nota.parentElement.getBoundingClientRect();
      const b = nota.getBoundingClientRect();
      const presa = [ev.clientX - b.left, ev.clientY - b.top];
      const muovi = (e) => {
        a.posNota = {
          x: Math.min(1 - b.width / tela.width, Math.max(0, (e.clientX - presa[0] - tela.left) / tela.width)),
          y: Math.min(1 - b.height / tela.height, Math.max(0, (e.clientY - presa[1] - tela.top) / tela.height)),
        };
        nota.style.left = `${a.posNota.x * 100}%`;
        nota.style.top = `${a.posNota.y * 100}%`;
      };
      const lascia = () => { testata.removeEventListener("pointermove", muovi); testata.removeEventListener("pointerup", lascia); };
      testata.addEventListener("pointermove", muovi);
      testata.addEventListener("pointerup", lascia);
    });
  }
  return nota;
}

function strumentiRitocco(spenti, ragione) {
  const r = S.ritocca;
  const voci = [["rettangolo", "Rettangolo"], ["libera", "Selezione libera"]];
  const aiuti = {
    rettangolo: "Rettangolo: trascina da un angolo all'altro. Quando lasci, si attacca una nota.",
    libera: "Selezione libera, come il lazo di Photoshop: disegna il contorno tenendo premuto. Quando lasci, la forma si chiude da sola e si attacca una nota.",
  };
  return h("div", { classe: "strumenti-ritocco" },
    h("div", { classe: "switch", role: "group", "aria-label": "Strumento" },
      voci.map(([id, nome]) => h("button", {
        classe: "seg", "aria-pressed": String(r.strumento === id), disabled: spenti || null,
        onclick: () => { r.strumento = id; render(); },
      }, nome)),
      h("button", { classe: "seg", disabled: true, title: "Arriva con la mappa materiali di Allplan" }, "Clicca una superficie", presto())),
    h("span", { classe: "tenue piccolo" }, spenti ? ragione : aiuti[r.strumento]));
}

function elencoNote(bloccato) {
  const r = S.ritocca;
  if (!r.aree.length) {
    return h("p", { classe: "tenue piccolo" }, "Le note che scrivi sui foglietti attaccati alle aree le ritrovi qui in elenco, per rileggerle e correggerle.");
  }
  return h("ol", { classe: "elenco-note" }, r.aree.map((a, i) => {
    const campo = h("textarea", { id: `elenco-nota-${i}`, rows: "2", "aria-label": `Nota ${i + 1}`, readonly: bloccato || null });
    campo.value = a.nota;
    campo.addEventListener("input", () => scriviNota(i, campo.value, "elenco"));
    return h("li", {},
      h("div", { classe: "riga tra" }, h("span", { classe: "piccolo" }, h("b", { classe: "numero-elenco" }, String(i + 1)), a.forma === "rettangolo" ? " rettangolo" : " selezione libera"),
        bloccato ? null : h("button", { classe: "btn link piccolo", onclick: () => togliArea(i) }, "Togli")),
      campo,
      h("span", { classe: "manca-nota", id: `manca-elenco-${i}`, hidden: !!a.nota.trim() }, "Un'area senza nota non dice al modello cosa fare."));
  }));
}

function daVerificare() {
  const modo = S.studio.ritocco;
  return h("section", { classe: "pannello", "aria-label": "Da verificare prima" },
    h("span", { classe: "etichetta" }, "Da verificare prima"),
    h("ol", { classe: "piccolo elenco-verifiche" },
      h("li", {}, "Che Nano Banana 2 rispetti le aree e lasci uguale il resto: lo dice il piano «aree» del banco di prova, non ancora lanciato. Per ogni ritocco lo Studio misura quanto è cambiato fuori dalle aree."),
      h("li", {}, `Le aree partono come ${modo.modo_nome}`, modo.origine === "SCELTA" ? ": scelta provvisoria, la fissa il piano «aree»." : "."),
      h("li", {}, "Il modello rifà tutta l'immagine anche con le aree: per un cambio di materiale grande conviene rifare il render da Genera."),
      h("li", {}, "«Clicca una superficie» arriva con la mappa dei materiali da Allplan.")));
}

function pannelloApplica(base, bloccato) {
  const r = S.ritocca;
  const n = r.aree.length;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Applica le note" },
    h("span", { classe: "etichetta" }, `Note sull'immagine · dal passo ${base.numero}`),
    elencoNote(bloccato),
    h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"), h("span", { classe: "tenue piccolo", id: "caratteri-ritocco" })),
      h("textarea", { classe: "prompt", id: "prompt-ritocco", readonly: true, "aria-label": "Prompt del ritocco" })),
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Modello"), h("div", { stile: "min-width:200px" }, sceltaModello(r, render))),
    rigaDestinazione(r.modello, S.studio.ritocco.modo === "maschera" ? "Il render, con la maschera delle aree," : "Il render, con le aree disegnate sopra,"),
    h("div", { id: "errore-ritocco" }),
    bloccato ? null : h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", id: "applica-ritocco", onclick: applicaRitocco, disabled: true },
        n ? `Applica ${n === 1 ? "la nota" : `le ${n} note`} · un invio` : "Applica · un invio"),
      h("span", { classe: "tenue piccolo", id: "motivo-ritocco" })),
    h("p", { classe: "tenue piccolo" }, base.figli
      ? `Il risultato è un passo nuovo nell'albero, figlio del passo ${base.numero}, accanto ai rami che ha già.`
      : `Il risultato è un passo nuovo nell'albero, figlio del passo ${base.numero}.`));
}

async function applicaRitocco() {
  const r = S.ritocca;
  r.errore = null;
  try {
    const dest = await destinazioneDi(r.modello);
    const risposta = await post("/api/ritocca/invia", {
      vista: S.vista, da: r.da, aree: areePerIlServer(), modello: r.modello, destinazione_mostrata: dest && dest.destinazione,
    });
    r.inviato = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
  } catch (e) { r.errore = e; }
  render();
}

// Quando il lavoro finisce: riuscito, il passo nuovo e' scelto e le aree si
// svuotano; non riuscito, aree e note restano come erano per rifare.
async function fineRitocco(ora) {
  const r = S.ritocca;
  r.inviato = null;
  await caricaPassi();
  if (ora.stato === "fatto") {
    S.passi.scelto = ora.identificativo;
    r.esito = ora.identificativo;
    r.aree = []; r.composto = null; r.errore = null;
  } else {
    r.errore = { fatto: ora.stato === "annullato" ? "Il ritocco è stato annullato." : (ora.fatto || "Il ritocco non è riuscito."),
      cosa_fare: ora.stato === "annullato" ? "Aree e note sono rimaste: puoi applicarle di nuovo." : `${ora.cosa_fare || ""} Aree e note sono rimaste come erano: Applica le rimanda.`.trim() };
  }
}

function esitoRitocco() {
  const r = S.ritocca;
  const passo = r.esito && passoDa(r.esito);
  if (!passo || !passo.render) return null;
  const padre = passoDa(passo.da);
  const { palco, nota } = primaDopo(r, padre ? `/file/render/${padre.identificativo}` : `/file/vista/${enc(S.vista)}`,
    padre ? `Passo ${padre.numero}` : "Vista Allplan", `/file/render/${passo.identificativo}`, `Passo ${passo.numero}`);
  return h("div", { classe: "layout-ritocca" },
    h("div", { classe: "palco" },
      h("h1", {}, `Ritocco fatto · passo ${passo.numero}`),
      palco,
      h("div", { classe: "riga tra" }, h("span", { classe: "tenue piccolo" }, "Trascina la linea, oppure tasti ← →"), h("span", { classe: "mono", id: "valore-linea" }, `${Math.round(r.x)}%`)),
      nota),
    h("div", { classe: "lato" },
      pannelloFuoriAree(passo),
      h("section", { classe: "pannello" },
        h("span", { classe: "etichetta" }, "Le note applicate"),
        h("ol", { classe: "piccolo" }, (passo.aree || []).map((a) => h("li", {}, a.nota)))),
      h("section", { classe: "pannello", "aria-label": "Adesso" },
        h("span", { classe: "etichetta" }, "Adesso"),
        h("div", { classe: "azioni" },
          h("button", { classe: "btn primario", onclick: () => { r.esito = null; cambiaBaseRitocco(passo.identificativo); } }, "Ritocca questo render"),
          h("button", { classe: "btn", onclick: () => { r.esito = null; r.da = padre ? padre.identificativo : null; render(); } }, "Torna al render di prima"),
          h("a", { classe: "btn", href: "#passi" }, "Vedi nei Passi"))),
      passo.avviso ? h("div", { classe: "avviso attenzione", role: "note" },
        h("b", {}, `Questo passo è la ${passo.generazioni}ª generazione di fila: gli spigoli possono spostarsi un poco a ogni giro.`),
        h("span", {}, "Se vedi l'edificio cambiare, rifai pulito dalla vista dai Passi.")) : null));
}

// La misura fuori dalle aree, accanto al risultato: si legge dallo stato del
// lavoro, «non misurato» se il motore non l'ha potuta fare.
function pannelloFuoriAree(passo) {
  const m = passo.fuori_aree;
  return h("section", { classe: "pannello", "aria-label": "Fuori dalle aree" },
    h("span", { classe: "etichetta" }, "Fuori dalle aree"),
    h("span", { classe: m && m.differenza_media !== null && m.differenza_media !== undefined ? "" : "misura" }, passo.fuori_aree_testo || "Fuori dalle aree: non misurato."),
    h("p", { classe: "tenue piccolo" }, "Confronto pixel per pixel con il render da cui parte, senza le aree e una fascia stretta intorno. Soglie scelte, non tarate: serve a vedere se il modello ha toccato il resto, il giudizio resta tuo sul prima/dopo."),
    passo.modo_aree_nome ? h("p", { classe: "tenue piccolo" }, `Aree mandate come ${passo.modo_aree_nome}.`) : null);
}

function ritoccaDa(passo) {
  const r = S.ritocca;
  if (r.da !== passo.identificativo) { r.aree = []; r.composto = null; r.errore = null; }
  r.da = passo.identificativo; r.esito = null;
  location.hash = "#ritocca";
}

function schermataRitocca() {
  const r = S.ritocca;
  const sopra = S.errore ? [avviso("errore", S.errore.fatto, S.errore.cosa_fare)] : [];
  if (!S.vista) {
    return [...sopra, h("section", { classe: "pannello" }, h("h1", {}, "Ritocca"),
      h("p", {}, "Nessuna vista ancora. Catturala dalla palette in Allplan, oppure scegline una in Genera con Usa un'altra vista…"),
      h("div", { classe: "azioni" }, h("a", { classe: "btn", href: "#genera" }, "Vai a Genera")))];
  }
  if (S.passi.errore) return [...sopra, h("h1", {}, "Ritocca"), avviso("errore", S.passi.errore.fatto, S.passi.errore.cosa_fare)];
  if (!S.passi.dati) return [...sopra, h("p", { classe: "tenue" }, "Leggo i render di questa vista…")];
  if (r.esito && passoDa(r.esito) && passoDa(r.esito).render) return [...sopra, esitoRitocco()];
  const base = baseRitocco();
  if (!base) {
    return [...sopra, h("h1", {}, "Ritocca"),
      strumentiRitocco(true, "Spenti: non c'è un render da ritoccare."),
      h("section", { classe: "pannello vuoto-ritocco" },
        h("p", {}, "Prima serve un render. Generane uno da Genera."),
        h("div", { classe: "azioni" }, h("a", { classe: "btn primario", href: "#genera" }, "Vai a Genera"))),
      daVerificare()];
  }
  if (!r.modello) r.modello = modelloVerificato(base.modello);
  const bloccato = ritoccoBloccato();
  const ritoccabili = S.passi.dati.passi.filter((x) => x.si_parte);
  const scegliBase = h("select", { "aria-label": "Render da ritoccare", disabled: bloccato || null },
    ritoccabili.map((x) => h("option", { value: x.identificativo, selected: x.identificativo === base.identificativo }, `Passo ${x.numero} · ${x.nome}`)));
  scegliBase.addEventListener("change", () => cambiaBaseRitocco(scegliBase.value));
  const attivo = bloccato ? S.lavoroAttivo : null;
  return [...sopra, h("div", { classe: "layout-ritocca" },
    h("div", { classe: "palco" },
      h("div", { classe: "riga tra" }, h("h1", {}, `Ritocca · passo ${base.numero}`),
        h("div", { stile: "min-width:260px" }, scegliBase)),
      strumentiRitocco(bloccato, "Bloccati mentre il ritocco è in corso: aree e note restano come le hai mandate."),
      attivo ? h("div", { classe: "striscia in-riga", role: "status" },
        h("div", { classe: "riga tra" }, h("span", {}, h("b", {}, (attivo.destinazione || "").split(" (")[0]), ` · ${attivo.stato}`), h("span", { classe: "mono" }, tempo(attivo.secondi))),
        h("div", { classe: "barra" }, h("span")),
        h("div", { classe: "riga tra" }, h("span", { classe: "piccolo" }, "Allplan e il resto dello Studio restano liberi."), h("button", { classe: "btn", onclick: annulla }, "Annulla"))) : null,
      telaRitocco(base),
      r.aree.length ? null : h("p", { classe: "tenue" }, "Disegna un'area, poi scrivi cosa cambiare nella sua nota.")),
    h("div", { classe: "lato" }, pannelloApplica(base, bloccato), daVerificare()))];
}

// --- Passi ---------------------------------------------------------------------
// L'albero dei passi di una vista (DESIGN.md, Studio · Passi). Lo 0 e' la
// vista Allplan; ogni passo parte da quello sopra di lui. Lo Studio non
// inventa passi: li legge da /api/viste/<vista>/passi, che li allinea ai
// lavori della cartella.

function passoScelto() {
  const p = S.passi;
  return (p.dati && p.dati.passi.find((x) => x.identificativo === p.scelto)) || null;
}
function passoDa(id) { return (S.passi.dati && S.passi.dati.passi.find((x) => x.identificativo === id)) || null; }

async function caricaPassi() {
  if (!S.vista) return;
  const p = S.passi;
  try {
    p.dati = await get(`/api/viste/${enc(S.vista)}/passi`);
    p.errore = null;
  } catch (e) { p.dati = null; p.errore = e; }
  p.caricato = true;
  if (p.dati && !passoScelto()) {
    // Il piu' recente con un render; se non ce n'e', la vista.
    const fatti = p.dati.passi.filter((x) => x.render).sort((a, b) => (b.creato_il || "").localeCompare(a.creato_il || ""));
    p.scelto = fatti.length ? fatti[0].identificativo : (p.dati.passi[0] ? p.dati.passi[0].identificativo : "0");
  }
}

async function destinazioneDi(modello) {
  const p = S.passi;
  if (!p.dest[modello]) {
    try { p.dest[modello] = await get(`/api/destinazione?modello=${enc(modello)}`); } catch (e) { S.errore = e; }
  }
  return p.dest[modello];
}

function modelloVerificato(id) { const m = S.catalogo.modelli.find((x) => x.id === id); return m && m.verificato ? m.id : S.studio.modello_predefinito; }

async function apriNuovoPasso(passo) {
  const p = S.passi;
  p.scelto = passo.identificativo;
  p.rifai = false; p.pulito = null;
  p.nuovo = { da: passo.identificativo, testo: "", modello: modelloVerificato(passo.modello), composto: null, errore: null };
  await destinazioneDi(p.nuovo.modello);
  render();
  const campo = document.getElementById("testo-passo");
  if (campo) campo.focus();
}

let attesaPasso = null;
function componiNuovoPasso() {
  const n = S.passi.nuovo;
  clearTimeout(attesaPasso);
  if (!n || !n.testo.trim()) { if (n) { n.composto = null; disegnaNuovoPasso(); } return; }
  attesaPasso = setTimeout(async () => {
    try { n.composto = await post("/api/passi/componi", { vista: S.vista, da: n.da, testo: n.testo }); n.errore = null; }
    catch (e) { n.composto = null; n.errore = e; }
    disegnaNuovoPasso();
  }, 250);
}

// Aggiorna solo il prompt e il pulsante mentre si scrive, senza ridisegnare
// la pagina: il campo di testo non perde il cursore.
function disegnaNuovoPasso() {
  const n = S.passi.nuovo;
  if (!n) return;
  const prompt = document.getElementById("prompt-passo");
  if (prompt) prompt.value = n.composto ? n.composto.prompt : "";
  const car = document.getElementById("caratteri-passo");
  if (car) car.textContent = n.composto ? `${n.composto.caratteri} caratteri` : "";
  const err = document.getElementById("errore-passo");
  if (err) err.replaceChildren(n.errore ? avviso("errore", n.errore.fatto, n.errore.cosa_fare) : "");
  const bottone = document.getElementById("applica-passo");
  if (bottone) bottone.disabled = !n.testo.trim() || !!S.lavoroAttivo;
  const motivo = document.getElementById("motivo-applica");
  if (motivo) motivo.textContent = motivoApplicaSpento();
}

function motivoApplicaSpento() {
  const n = S.passi.nuovo;
  if (S.lavoroAttivo) return "Un lavoro è in corso: Applica si accende quando finisce, così un doppio clic non si paga due volte.";
  if (!n || !n.testo.trim()) return "Scrivi cosa cambiare: un passo senza richiesta non cambia niente.";
  return "";
}

async function applicaPasso() {
  const n = S.passi.nuovo;
  S.errore = null;
  try {
    const dest = await destinazioneDi(n.modello);
    const risposta = await post("/api/passi/invia", {
      vista: S.vista, da: n.da, testo: n.testo, modello: n.modello, destinazione_mostrata: dest && dest.destinazione,
    });
    S.passi.nuovo = null;
    S.passi.scelto = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
  } catch (e) { n.errore = e; }
  render();
}

async function apriPulito(passo) {
  const p = S.passi;
  p.nuovo = null; p.rifai = false;
  p.pulito = { passo: passo.identificativo, modello: modelloVerificato(passo.modello), composto: null, errore: null };
  try { p.pulito.composto = await post("/api/passi/pulito/componi", { vista: S.vista, passo: passo.identificativo }); }
  catch (e) { p.pulito.errore = e; }
  await destinazioneDi(p.pulito.modello);
  render();
}

async function inviaPulito() {
  const q = S.passi.pulito;
  S.errore = null;
  try {
    const dest = await destinazioneDi(q.modello);
    const risposta = await post("/api/passi/pulito/invia", {
      vista: S.vista, passo: q.passo, modello: q.modello, destinazione_mostrata: dest && dest.destinazione,
    });
    S.passi.pulito = null;
    S.passi.scelto = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
  } catch (e) { q.errore = e; }
  render();
}

async function rifaiPasso(passo) {
  S.errore = null;
  try {
    const dest = await destinazioneDi(passo.modello);
    const risposta = await post(`/api/lavori/${passo.identificativo}/rifai`, { destinazione_mostrata: dest && dest.destinazione });
    S.passi.rifai = false;
    S.passi.scelto = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
  } catch (e) { S.errore = e; }
  render();
}

function etichettaStato(passo) {
  if (passo.attivo) return h("span", { classe: "tag-stato attivo" }, passo.stato);
  if (passo.stato === "errore") return h("span", { classe: "tag-stato errore" }, "non riuscito");
  if (passo.stato === "annullato") return h("span", { classe: "tag-stato" }, "annullato");
  if (!passo.render) return h("span", { classe: "tag-stato" }, "render tolto");
  return null;
}

function rigaPasso(passo) {
  const p = S.passi;
  const scelto = p.scelto === passo.identificativo;
  const attivo = S.lavoroAttivo && S.lavoroAttivo.identificativo === passo.identificativo ? S.lavoroAttivo : null;
  return h("li", { classe: "riga-passo", stile: `--d:${passo.profondita}` },
    h("button", {
      classe: "scegli-passo", "aria-current": String(scelto),
      onclick: () => { p.scelto = passo.identificativo; p.rifai = false; p.pulito = null; if (p.nuovo && p.nuovo.da !== passo.identificativo) p.nuovo = null; render(); },
    },
      passo.render ? h("img", { src: `/file/render/${passo.identificativo}`, alt: "" }) : h("span", { classe: "segnaposto" }),
      h("span", { classe: "testo-passo" },
        h("span", { title: passo.nome }, h("b", { classe: "numero" }, passo.numero), " ", passo.nome),
        h("small", {}, `${passo.modello_nome} · ${data(passo.creato_il)}`, " ", etichettaStato(passo)))),
    attivo ? h("div", { classe: "striscia in-riga", role: "status" },
      h("div", { classe: "riga tra" }, h("span", {}, h("b", {}, (attivo.destinazione || "").split(" (")[0]), ` · ${attivo.stato}`), h("span", { classe: "mono" }, tempo(attivo.secondi))),
      h("div", { classe: "barra" }, h("span")),
      h("div", { classe: "riga tra" }, h("span", { classe: "piccolo" }, "Allplan resta libero."), h("button", { classe: "btn", onclick: annulla }, "Annulla"))) : null,
    h("button", {
      classe: "btn link piccolo", disabled: !passo.si_parte, title: passo.motivo_non_si_parte || null,
      onclick: () => apriNuovoPasso(passo),
    }, "Nuovo passo da qui"));
}

function colonnaAlbero() {
  const p = S.passi;
  const dati = p.dati;
  const passi = dati ? dati.passi : [];
  const zeroScelto = p.scelto === "0";
  return h("section", { classe: "pannello albero-passi", "aria-label": "Passi di questa vista" },
    h("span", { classe: "etichetta" }, "Passi di questa vista"),
    h("span", { classe: "mono piccolo tenue", title: S.vista }, S.vista),
    h("ol", { classe: "albero" },
      h("li", { classe: "riga-passo", stile: "--d:0" },
        h("button", { classe: "scegli-passo", "aria-current": String(zeroScelto), onclick: () => { p.scelto = "0"; p.nuovo = null; p.pulito = null; p.rifai = false; render(); } },
          h("img", { src: `/file/vista/${enc(S.vista)}`, alt: "" }),
          h("span", { classe: "testo-passo" }, h("span", {}, h("b", { classe: "numero" }, "0"), " Vista Allplan"),
            h("small", {}, dati ? `cattura del ${data(dati.catturata_il)}` : ""))),
        h("a", { classe: "btn link piccolo", href: "#genera", title: "Dalla vista si parte da Genera: lì scegli lo stile." }, "Nuovo passo da qui")),
      passi.map(rigaPasso)),
    passi.length
      ? h("p", { classe: "tenue piccolo" }, "Ogni passo parte da quello sopra di lui. Un passo nuovo fatto da un punto qualsiasi apre un ramo lì sotto.")
      : h("div", { classe: "vuoto-passi" },
        h("p", {}, "Nessun passo ancora. Genera un render da Genera: sarà il passo 1."),
        h("a", { classe: "btn", href: "#genera" }, "Vai a Genera")));
}

function palcoPassi(passo) {
  const p = S.passi;
  if (!passo) {
    return h("div", { classe: "palco" },
      h("h1", {}, "Vista Allplan · passo 0"),
      h("p", { classe: "tenue" }, "Il punto di partenza di tutti i passi. Da qui si parte da Genera."),
      h("figure", { classe: "riquadro-vista" }, h("img", { src: `/file/vista/${enc(S.vista)}`, alt: "Vista Allplan", stile: "max-height:none" })));
  }
  const titolo = h("h1", {}, `Passo ${passo.numero} · ${passo.nome}`);
  if (!passo.render) {
    const padre = passo.da !== "0" ? passoDa(passo.da) : null;
    const srcPartenza = padre && padre.render ? `/file/render/${padre.identificativo}` : `/file/vista/${enc(S.vista)}`;
    const testa = passo.attivo
      ? h("p", { classe: "tenue" }, "Il render arriva qui appena il servizio lo manda. Qui sotto, l'immagine da cui parte.")
      : h("div", { classe: "avviso errore", role: "alert" },
        h("b", {}, passo.stato === "errore" ? "Questo passo non è riuscito." : passo.stato === "annullato" ? "Questo passo è stato annullato." : "Il render di questo passo non c'è più nella cartella dei lavori."),
        passo.fatto ? h("span", {}, passo.fatto) : null,
        passo.cosa_fare ? h("span", { classe: "cosa-fare" }, passo.cosa_fare) : null,
        h("span", { classe: "piccolo tenue" }, "Non ha figli e non si può scegliere come punto di partenza."));
    return h("div", { classe: "palco" }, titolo, testa,
      h("figure", { classe: "riquadro-vista" }, h("img", { src: srcPartenza, alt: "Immagine di partenza", stile: "max-height:none" })));
  }
  const padre = passo.da !== "0" ? passoDa(passo.da) : null;
  const primaPossibile = padre && padre.render;
  const contro = p.confronto === "prima" && primaPossibile ? "prima" : "vista";
  const srcA = contro === "prima" ? `/file/render/${padre.identificativo}` : `/file/vista/${enc(S.vista)}`;
  const nomeA = contro === "prima" ? `Passo ${padre.numero}` : "Vista Allplan";
  const srcB = `/file/render/${passo.identificativo}`;
  const nomeB = `Passo ${passo.numero}`;
  const modi = h("div", { classe: "switch", role: "group", "aria-label": "Modo di confronto" },
    [["scorri", "Prima / dopo"], ["affiancati", "Affiancati"]].map(([id, n]) =>
      h("button", { classe: "seg", "aria-pressed": String(p.modo === id), onclick: () => { p.modo = id; render(); } }, n)));
  const scegliA = h("select", { "aria-label": "Confronta con" },
    h("option", { value: "vista", selected: contro === "vista" }, "Vista Allplan (passo 0)"),
    h("option", { value: "prima", selected: contro === "prima", disabled: !primaPossibile },
      padre ? `Passo prima (passo ${padre.numero})${primaPossibile ? "" : ": il suo render non c'è più"}` : "Passo prima: è la vista"));
  scegliA.addEventListener("change", () => { p.confronto = scegliA.value; render(); });
  let palco, nota = null;
  if (p.modo === "scorri") ({ palco, nota } = primaDopo(p, srcA, nomeA, srcB, nomeB));
  else {
    palco = h("div", { classe: "affiancati" },
      h("figure", {}, h("img", { src: srcA, alt: nomeA }), h("figcaption", { classe: "tenue piccolo" }, nomeA)),
      h("figure", {}, h("img", { src: srcB, alt: nomeB }), h("figcaption", { classe: "tenue piccolo" }, nomeB)));
  }
  return h("div", { classe: "palco" },
    h("div", { classe: "riga tra" }, titolo, modi),
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Confronta con"), h("div", { stile: "min-width:240px" }, scegliA)),
    palco,
    p.modo === "scorri" ? h("div", { classe: "riga tra" },
      h("span", { classe: "tenue piccolo" }, "Trascina la linea, oppure tasti ← → (con Maiusc il passo è più lungo)"),
      h("span", { classe: "mono", id: "valore-linea" }, `${Math.round(p.x)}%`)) : null,
    nota);
}

function rigaDestinazione(modello, cosaParte) {
  const d = S.passi.dest[modello];
  if (!d) return h("p", { classe: "tenue piccolo" }, "Leggo la destinazione…");
  return h("p", { classe: "destinazione" }, `${cosaParte || "La vista"} va a `, h("b", {}, d.destinazione),
    d.senza_ripiego ? ", senza ripiego su altri servizi" : "", `. Costo: ${d.costo}.`);
}

function sceltaModello(stato, onCambio) {
  const scegli = h("select", { "aria-label": "Modello" },
    S.catalogo.modelli.map((m) => h("option", { value: m.id, selected: stato.modello === m.id, disabled: !m.verificato }, `${m.nome}${m.verificato ? "" : " · schema non verificato"}`)));
  scegli.addEventListener("change", async () => { stato.modello = scegli.value; await destinazioneDi(stato.modello); onCambio(); });
  return scegli;
}

function pannelloNuovoPasso() {
  const n = S.passi.nuovo;
  const da = passoDa(n.da);
  if (!da) return null;
  const campo = h("textarea", { id: "testo-passo", rows: "3", placeholder: "Cosa cambiare, a parole: «due alberi davanti al fronte, non coprire le finestre»" });
  campo.value = n.testo;
  campo.addEventListener("input", () => { n.testo = campo.value; componiNuovoPasso(); disegnaNuovoPasso(); });
  return h("section", { classe: "pannello evidenziato", "aria-label": "Nuovo passo" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, `Nuovo passo da qui · dal passo ${da.numero}`),
      h("button", { classe: "btn link", onclick: () => { S.passi.nuovo = null; render(); } }, "Lascia stare")),
    h("p", { classe: "piccolo" }, da.figli
      ? `Parte dal passo ${da.numero}: si apre un ramo nuovo accanto a quelli che ci sono già.`
      : `Parte dal passo ${da.numero} e continua il suo ramo.`),
    campo,
    h("div", { classe: "riga" }, h("button", { classe: "chip", onclick: () => ritoccaDa(da) }, "Su un'area…"), h("span", { classe: "tenue piccolo" }, "apre Ritocca su questo render: aree e note")),
    h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"), h("span", { classe: "tenue piccolo", id: "caratteri-passo" })),
      h("textarea", { classe: "prompt", id: "prompt-passo", readonly: true, "aria-label": "Prompt del passo" })),
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Modello"), h("div", { stile: "min-width:200px" }, sceltaModello(n, render))),
    rigaDestinazione(n.modello),
    h("div", { id: "errore-passo" }),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", id: "applica-passo", onclick: applicaPasso, disabled: true }, "Applica"),
      h("span", { classe: "tenue piccolo", id: "motivo-applica" })));
}

function pannelloPulito(passo) {
  const q = S.passi.pulito;
  const c = q.composto;
  if (q.errore && !c) {
    return h("section", { classe: "pannello evidenziato" }, avviso("errore", q.errore.fatto, q.errore.cosa_fare),
      h("button", { classe: "btn", onclick: () => { S.passi.pulito = null; render(); } }, "Lascia stare"));
  }
  if (!c) return h("section", { classe: "pannello evidenziato" }, h("p", { classe: "tenue" }, "Unisco le richieste della strada…"));
  const prompt = h("textarea", { classe: "prompt", readonly: true, "aria-label": "Prompt di Rifai pulito" });
  prompt.value = c.prompt;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Rifai pulito dalla vista" },
    h("span", { classe: "etichetta" }, `Rifai pulito dalla vista · strada ${c.strada.join(" › ")}`),
    h("p", { classe: "piccolo" }, `Un solo invio dalla vista Allplan, una generazione invece di ${c.generazioni}. Il risultato è un ramo nuovo sotto lo 0.`),
    h("dl", { classe: "ricetta" },
      h("dt", {}, "Stile"), h("dd", {}, c.riassunto),
      h("dt", {}, "Richieste"), h("dd", {}, c.richieste.join(" · "))),
    c.senza_aree && c.senza_aree.length ? avviso("attenzione",
      `Le note del ritocco ${c.senza_aree.length === 1 ? "al passo" : "ai passi"} ${c.senza_aree.join(", ")} entrano come richieste a parole, senza le loro aree.`,
      "Dalla vista le aree non valgono più: erano disegnate su un render. Il modello non sa più dove fare quelle modifiche; se servono lì, ritocca dopo.") : null,
    h("span", { classe: "piccolo tenue" }, `Il prompt che parte, in inglese · ${c.caratteri} caratteri`),
    prompt,
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Modello"), h("div", { stile: "min-width:200px" }, sceltaModello(q, render))),
    rigaDestinazione(q.modello),
    q.errore ? avviso("errore", q.errore.fatto, q.errore.cosa_fare) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: inviaPulito, disabled: !!S.lavoroAttivo }, "Conferma e invia"),
      h("button", { classe: "btn", onclick: () => { S.passi.pulito = null; render(); } }, "Lascia stare")),
    S.lavoroAttivo ? h("span", { classe: "tenue piccolo" }, "Un lavoro è in corso: si può inviare quando finisce.") : null);
}

function ricettaPasso(passo) {
  const padre = passo.da !== "0" ? passoDa(passo.da) : null;
  const righe = [
    ["Strada", passo.strada.join(" › ")],
    ["Parte da", passo.da === "0" ? "Vista Allplan (passo 0)"
      : `Passo ${passo.da_numero}${passo.partenza_mancante ? ": il punto di partenza non c'è più" : ""}`],
    ["Richiesta", passo.riassunto],
    ["Modello", passo.modello_nome],
    ["Servizio", passo.destinazione || "—"],
    ["Costo", passo.costo],
    ["Data", data(passo.creato_il)],
    ["Blocchi", passo.versione_blocchi ? `${passo.versione_blocchi} · testi scelti, non ancora provati` : "—"],
    ["Aree", passo.aree && passo.aree.length
      ? h("span", {}, passo.aree.map((a, i) => `${i + 1} · ${a.forma === "rettangolo" ? "rettangolo" : "selezione libera"}: ${a.nota}`).join(" — "),
        passo.modo_aree_nome ? h("span", { classe: "tenue" }, ` (mandate come ${passo.modo_aree_nome})`) : null)
      : "nessuna"],
  ];
  if (passo.percorso_render) righe.push(["Render", h("span", { classe: "mono" }, passo.percorso_render)]);
  if (passo.percorso_ricetta) righe.push(["Ricetta", h("span", { classe: "mono" }, passo.percorso_ricetta)]);
  righe.push(["Albero", h("span", { classe: "mono" }, S.passi.dati.file)]);
  const prompt = h("textarea", { classe: "prompt", readonly: true, "aria-label": "Prompt partito" });
  prompt.value = passo.prompt || "";
  return h("section", { classe: "pannello", "aria-label": "Com'è stato fatto" },
    h("span", { classe: "etichetta" }, "Com'è stato fatto"),
    h("dl", { classe: "ricetta" }, righe.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])),
    passo.prompt ? h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, `Il prompt, in inglese${passo.prompt_a_mano ? " · scritto a mano" : ""}`)), prompt) : null,
    padre === null && passo.da !== "0" ? h("p", { classe: "tenue piccolo" }, "Il passo da cui era partito non c'è più nell'albero.") : null);
}

function latoPassi(passo) {
  const p = S.passi;
  if (!passo) return h("div", { classe: "lato" }, p.nuovo ? pannelloNuovoPasso() : null);
  const blocchi = [];
  if (p.nuovo) blocchi.push(pannelloNuovoPasso());
  blocchi.push(h("section", { classe: "pannello", "aria-label": "La strada" },
    h("span", { classe: "etichetta" }, "La strada"),
    h("span", { classe: "strada" }, passo.strada.join(" › ")),
    h("span", { classe: "tenue piccolo" }, `${passo.generazioni} ${passo.generazioni === 1 ? "generazione" : "generazioni di fila"} dalla vista Allplan.`)));
  if (passo.avviso) {
    blocchi.push(h("div", { classe: "avviso attenzione", role: "note" },
      h("b", {}, `Questo passo è la ${passo.generazioni}ª generazione di fila: gli spigoli possono spostarsi un poco a ogni giro.`),
      h("span", {}, "Se vedi l'edificio cambiare, rifai pulito dalla vista."),
      h("span", { classe: "piccolo tenue" }, `Avviso da ${S.passi.dati.avviso_da_generazione} generazioni: soglia scelta, da tarare con il piano «catena» del banco di prova.`)));
  }
  if (passo.partenza_mancante) {
    blocchi.push(avviso("errore", "Il punto di partenza non c'è più: il render del passo prima è stato tolto dalla cartella.",
      "Rifai pulito dalla vista: riparte dalla vista Allplan con le stesse richieste."));
  }
  blocchi.push(h("section", { classe: "pannello", "aria-label": "Tenuta della geometria" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Tenuta della geometria"), presto("Misura in arrivo")),
    h("span", { classe: "misura" }, "Non misurata"),
    h("p", { classe: "tenue piccolo" }, "Si misura sempre contro la vista Allplan, non contro il passo prima: così lo spostamento che si accumula passo dopo passo si vede tutto. Per ora giudica tu, con la linea del prima/dopo.")));
  if (passo.aree && passo.aree.length && passo.render) blocchi.push(pannelloFuoriAree(passo));
  if (p.pulito && p.pulito.passo === passo.identificativo) blocchi.push(pannelloPulito(passo));
  const dest = S.passi.dest[passo.modello];
  const conferma = p.rifai ? h("div", { classe: "avviso" },
    h("b", {}, "Rifai questo passo"),
    h("span", {}, passo.da === "0" ? "Stessa vista, stesse scelte: un ramo nuovo sotto lo 0." : `Stesso punto di partenza (passo ${passo.da_numero}), stessa richiesta: un ramo nuovo accanto.`),
    rigaDestinazione(passo.modello),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => rifaiPasso(passo), disabled: !!S.lavoroAttivo || !dest || !!dest.cosa_manca }, "Conferma e rifai"),
      h("button", { classe: "btn", onclick: () => { p.rifai = false; render(); } }, "Lascia stare"))) : null;
  const notaPulito = passo.generazioni <= 1
    ? "Un passo solo: niente da unire."
    : `Unisce le richieste dei passi ${passo.strada.slice(1).join(", ")} in un solo invio dalla vista Allplan: una generazione invece di ${passo.generazioni}.`;
  blocchi.push(h("section", { classe: "pannello", "aria-label": "Adesso" },
    h("span", { classe: "etichetta" }, "Adesso"),
    h("div", { classe: "azioni" },
      h("button", { classe: passo.avviso || passo.partenza_mancante ? "btn primario" : "btn", disabled: passo.generazioni <= 1 || !!S.lavoroAttivo, onclick: () => apriPulito(passo) }, "Rifai pulito dalla vista"),
      h("button", { classe: "btn", disabled: passo.partenza_mancante || passo.attivo || !!S.lavoroAttivo, onclick: async () => { p.rifai = true; p.pulito = null; await destinazioneDi(passo.modello); render(); } }, "Rifai questo passo"),
      h("button", { classe: "btn", disabled: !passo.si_parte, title: passo.motivo_non_si_parte || null, onclick: () => ritoccaDa(passo) }, "Ritocca da qui"),
      h("button", { classe: "btn", onclick: () => post("/api/apri-cartella", { quale: "render" }).catch((e) => { S.errore = e; render(); }) }, "Apri cartella")),
    h("p", { classe: "tenue piccolo" }, notaPulito),
    conferma));
  blocchi.push(ricettaPasso(passo));
  return h("div", { classe: "lato" }, blocchi);
}

function schermataPassi() {
  const p = S.passi;
  const sopra = S.errore ? [avviso("errore", S.errore.fatto, S.errore.cosa_fare)] : [];
  if (!S.vista) {
    return [...sopra, h("section", { classe: "pannello" }, h("h1", {}, "Passi"),
      h("p", {}, "Nessuna vista ancora. Catturala dalla palette in Allplan, oppure scegline una in Genera con Usa un'altra vista…"),
      h("div", { classe: "azioni" }, h("a", { classe: "btn", href: "#genera" }, "Vai a Genera")))];
  }
  if (p.errore) return [...sopra, h("h1", {}, "Passi"), avviso("errore", p.errore.fatto, p.errore.cosa_fare)];
  if (!p.dati) return [...sopra, h("p", { classe: "tenue" }, "Leggo i passi…")];
  const passo = p.scelto === "0" ? null : passoScelto();
  const vuoto = !p.dati.passi.length;
  return [...sopra, h("h1", { classe: "nascosto" }, "Passi"),
    h("div", { classe: vuoto ? "layout-passi vuoto" : "layout-passi" },
      colonnaAlbero(),
      vuoto ? null : palcoPassi(passo),
      vuoto ? null : latoPassi(passo))];
}

// --- disegno -------------------------------------------------------------------

function render() {
  disegnaTestata();
  const main = document.getElementById("principale");
  if (!S.studio || !S.catalogo || !S.scelte) {
    main.replaceChildren(S.errore ? avviso("errore", S.errore.fatto, S.errore.cosa_fare) : h("p", { classe: "tenue" }, "Apro lo Studio…"));
    return;
  }
  const attivo = document.activeElement && document.activeElement.id;
  const scorrimento = window.scrollY;
  const contenuto = S.scheda === "risultato" ? schermataRisultato()
    : S.scheda === "passi" ? schermataPassi()
    : S.scheda === "ritocca" ? schermataRitocca() : schermataGenera();
  main.replaceChildren(...[contenuto].flat(2).filter(Boolean));
  if (attivo && document.getElementById(attivo)) document.getElementById(attivo).focus();
  if (S.scheda === "passi") { disegnaNuovoPasso(); }
  if (S.scheda === "ritocca") { disegnaApplicaRitocco(); }
  window.scrollTo(0, scorrimento);
}

function leggiScheda() {
  const s = (location.hash || "#genera").slice(1);
  S.scheda = ["genera", "risultato", "passi", "ritocca"].includes(s) ? s : "genera";
}

window.addEventListener("hashchange", async () => {
  leggiScheda();
  if (S.scheda !== "genera" && S.vista) await caricaRender();
  if ((S.scheda === "passi" || S.scheda === "ritocca") && S.vista) await caricaPassi();
  if (S.scheda === "ritocca") await prontoRitocca();
  render();
  window.scrollTo(0, 0);
});

// Ogni pochi secondi: la coda e' viva? la palette ha salvato una vista nuova?
async function controllaStudio() {
  try {
    const ora = await get("/api/studio");
    const cambiato = !S.studio || ora.coda_attiva !== S.studio.coda_attiva || ora.viste.length !== S.studio.viste.length;
    S.studio = ora;
    if (!S.vista && ora.viste.length) { await caricaVista(ora.viste[0].nome); return; }
    if (cambiato) render();
  } catch (e) { /* la prossima volta */ }
}

async function avvia() {
  leggiScheda();
  try {
    [S.studio, S.catalogo] = await Promise.all([get("/api/studio"), get("/api/catalogo")]);
    const primo = S.catalogo.scene.esterno.preset[0];
    S.preset = primo.id;
    S.scelte = { ...primo.scelte };
    S.modello = S.studio.modello_predefinito;
    await Promise.all([caricaDestinazione(), aggiornaComposto(true)]);
    const attivo = S.studio.lavori_attivi[0];
    const vistaAttiva = attivo && S.studio.viste.find((v) => v.nome === attivo.vista);
    await caricaVista(vistaAttiva ? vistaAttiva.nome : (S.studio.viste[0] ? S.studio.viste[0].nome : null));
    if (attivo) seguiLavoro(attivo);
    if (S.scheda === "ritocca") { await caricaPassi(); await prontoRitocca(); }
    if (S.scheda === "passi") {
      const modelli = [...new Set((S.passi.dati ? S.passi.dati.passi : []).map((x) => x.modello).filter(Boolean))];
      await Promise.all(modelli.map(destinazioneDi));
    }
  } catch (e) { S.errore = e; }
  render();
  setInterval(controllaStudio, 3000);
}

avvia();
