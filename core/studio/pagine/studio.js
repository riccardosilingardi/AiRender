// Lo Studio: Genera, Risultato, Passi, Ritocca, Video.
// Niente framework e niente CDN: deve funzionare offline. Lo stato sta in S,
// render() ridisegna la schermata, le richieste passano da api().
// Gli stati di ogni schermata sono quelli di DESIGN.md: vuoto, in corso,
// errore, pieno. Lo stato vuoto non mostra dati finti.
"use strict";

// La web app serve lo Studio sotto /studio/ (scripts/scrivi_web.py): li' la
// cartella sta nel browser, non c'e' Allplan accanto e non c'e' Windows.
const SUL_WEB = location.pathname.startsWith("/studio/");

const S = {
  scheda: "genera",
  miei: { preset: [], problema: null, scelto: "", nota: null },  // I miei preset
  ricette: { elenco: [], problema: null, scelta: "", dest: null, nota: null, errore: null },  // Le mie ricette
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
  riferimento: null,      // immagine di riferimento per lo stile: { nome, da, larghezza, altezza }
  geometria: false,       // «Tieni la geometria»: prima un workflow col ControlNet, poi il modello
  controlliGeometria: ["spigoli"], // quali guide tiene il ControlNet: spigoli, profondita, linee
  esempi: [],             // «Stile da esempi»: render d'esempio oltre al riferimento, stessa forma
  inserti: [],            // Rif. 1-4 di oggetti e persone da mettere nella vista, stessa forma del riferimento
  // Materiali di questo progetto: l'elenco letto dalla palette con la vista,
  // quelli spuntati ({ chiave: { diventa, riferimento } }), la ricerca.
  // Senza l'elenco di Allplan (web app, immagini da altri programmi) i
  // materiali si scelgono con la selezione libera sulla vista: `zone` tiene
  // contorno, campione ritagliato, «diventa» e foto; `lazo` dice se si disegna.
  mat: { dati: null, scelti: {}, cerca: "", tutti: false, errore: null, zone: [], lazo: false, punti: false },
  // Inserisci nel contesto: l'immagine del luogo portata dall'utente, il
  // rettangolo dove va l'edificio (coordinate da 0 a 1), l'inquadratura,
  // «pulisci la mappa» e il luogo a parole.
  contesto: null,         // { nome, da, larghezza, altezza, area, inquadratura, pulisci, luogo }
  // Genera ha due modi: "vista" (il render della vista) e "contesto"
  // (inserisci l'edificio in una foto del luogo). Passando a "vista" il
  // contesto resta da parte in contestoTenuto e torna quando si rientra.
  modo: "vista",
  contestoTenuto: null,
  // «Da un'immagine»: il pannello per caricare una foto, un render gia' fatto
  // o uno schizzo (DESIGN.md, Studio · Da un'immagine). tipo e cosa sono le
  // due scelte prima del file. tieni: la regola scelta in Genera per
  // un'immagine caricata (blocchi.PARTENZE); null = quella predefinita.
  daImmagine: { aperto: false, tipo: null, cosa: null, scena: null, caricando: false, errore: null },
  tieni: null,
  inFila: [],             // le altre varianti dello stesso Genera, ancora da seguire
  ultimoEsito: null,      // ultimo lavoro finito in errore o annullato, per Genera
  // Licenza e saldo: cosa dice /api/licenza, e il modulo per incollare il codice.
  licenza: null,
  attiva: { codice: "", inCorso: false, errore: null, cambia: false },
  errore: null,           // errore di una richiesta, con fatto e cosa_fare
  secco: null,            // risposta della prova a secco
  viste_viste: new Set(),
  risultato: { lavori: [], scelto: null, confronto: "vista", modo: "scorri", x: 50, ricetta: null, rifai: false, caricato: false,
               esporta: false, formato: "jpg", esportato: null, esportando: false },
  // Studio · Passi: l'albero letto dal server, il passo scelto ("0" e' la
  // vista), il confronto e i tre pannelli che si aprono a destra.
  passi: { dati: null, errore: null, caricato: false, scelto: null, confronto: "vista", modo: "scorri", x: 50,
           nuovo: null, pulito: null, rifai: false, dest: {} },
  // Studio · Ritocca: il passo il cui render si ritocca, lo strumento, le
  // aree con le loro note (coordinate da 0 a 1), il lavoro mandato e,
  // finito, il passo nato. Il modello e le destinazioni sono quelli dei Passi.
  ritocca: { da: null, strumento: "rettangolo", aree: [], testo: "", spessore: null, modello: null, composto: null, errore: null,
             inviato: null, esito: null, x: 50, popola: null, arreda: null },
  // Punto di vista dalla pianta: da quale immagine (un passo, o "0" la vista),
  // dove sta la camera e verso dove guarda (da 0 a 1), tipo, stile, modello.
  punto: null,
  // Studio · Video: il catalogo letto dal server, come partire, i posti
  // delle immagini ({ render } o { caricata }), il movimento e i video fatti.
  video: { catalogo: null, voci: [], caricato: false, modo: "primo", posti: [null], movimento: "avanza", testo: "",
           durata: null, risoluzione: null, audio: false, secco: null, errore: null, caricando: false, scegliPer: null },
  // Lo storico: tutte le immagini di tutte le viste, nella colonna a sinistra.
  // Una cattura nuova si aggiunge; niente di quello che c'era sparisce.
  // aperte: le viste aperte o chiuse a mano (nome -> true/false); senza una
  // scelta a mano e' aperta la vista su cui si lavora. ridotta: la colonna
  // chiusa, per dare spazio all'immagine.
  storico: { gruppi: [], firma: "", disegnata: "", aperte: {}, ridotta: leggiRidotta(), vistaMostrata: null },
  // Le azioni sotto l'immagine in Risultato: per quale render, il video in un clic.
  azioni: { per: null, video: false, movimento: null, mandato: false, errore: null },
};

// --- attrezzi ---------------------------------------------------------------

// Cosa fa ogni pulsante d'azione, al passaggio del mouse (Riccardo,
// 2026-11-04). Un posto solo, così la stessa azione si spiega sempre allo
// stesso modo. Un pulsante che ha già il suo title tiene il suo.
const SPIEGA_PULSANTI = {
  "Usa un'altra vista…": "Scegli un'altra cattura dalla cartella delle viste.",
  "Avanzate: mostra e modifica il prompt completo": "Mostra il testo in inglese che parte al modello. Lo puoi riscrivere a mano.",
  "Ricomponi dalle scelte": "Butta il testo scritto a mano e rifà il prompt dalle scelte.",
  "Salva queste scelte": "Salva le scelte di questa pagina fra I miei preset, per riusarle.",
  "Rinomina": "Cambia il nome di questo preset.",
  "Elimina": "Toglie questo preset da I miei preset.",
  "+ Riferimento": "Aggiungi una foto del materiale che vuoi: parte insieme alla vista.",
  "Scegli la foto": "Carica la foto del luogo dal computer.",
  "Prova a secco": "Mostra cosa partirebbe, senza inviare niente e senza spendere crediti.",
  "Genera render": "Manda la vista al servizio scritto sopra, con lo stile scelto.",
  "Annulla": "Ferma il lavoro.",
  "Prima / dopo": "Le due immagini una sopra l'altra, con una linea da trascinare.",
  "Affiancati": "Le due immagini una accanto all'altra.",
  "Solo render": "Solo il render, grande.",
  "Misura ora": "Misura quanti spigoli della vista Allplan si ritrovano nel render.",
  "Apri cartella": "Apre la cartella in Esplora file.",
  "Copia immagine": "Copia il render negli appunti, da incollare dove vuoi.",
  "Esporta per il cliente": "Salva il render in JPEG, PNG o PSD a livelli, senza prompt né ricetta.",
  "Esporta": "Salva il file nella cartella «esportati».",
  "Azzera": "Riporta tutti i cursori a 0 e la curva diritta.",
  "Chiudi": "Chiude il riquadro. Non parte niente.",
  "Applica": "Manda questa immagine e la richiesta al servizio scritto sopra. Esce un passo nuovo.",
  "Genera video": "Manda le immagini al servizio video scritto sopra.",
  "Porta su questa vista": "Manda la vista scelta con lo stesso stile e le stesse richieste, e questa immagine come riferimento.",
  "Rifai tutto dalla vista": "Un solo invio dalla vista Allplan con tutte le richieste dei passi: gli spigoli tornano quelli della vista.",
  "Conferma e invia": "Manda il prompt qui sopra, dalla vista Allplan.",
  "Rettangolo": "Disegna un'area trascinando da un angolo all'altro.",
  "Selezione libera": "Disegna un'area a mano libera, come il lazo di Photoshop.",
  "Togli": "Lo toglie da qui. I file nella cartella restano.",
  "Dai render": "Scegli fra i render già fatti, di tutte le viste.",
  "Da file…": "Scegli un'immagine dal computer.",
  "Vai a Genera": "Apre Genera, dove scegli lo stile e mandi la vista.",
  "Vedi nei Passi": "Apre l'albero dei passi di questa vista.",
  "Ritocca questo render": "Apre Ritocca su questo render.",
  "Torna al render di prima": "Torna all'immagine da cui era partito questo ritocco.",
};

function testoPulsante(figli) {
  return figli.flat().filter((f) => typeof f === "string").join("").trim();
}

function h(tag, attributi, ...figli) {
  if (tag === "button" && !(attributi && attributi.title)) {
    const testo = testoPulsante(figli);
    const spiegazione = SPIEGA_PULSANTI[testo] || (testo.startsWith("Applica ") ? SPIEGA_PULSANTI.Applica : null);
    if (spiegazione) attributi = { ...attributi, title: spiegazione };
  }
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

// Il programma dello Studio si è chiuso (per esempio pacchetto.py --installa
// lo ferma prima di copiare i file). La pagina resta aperta e lo dice;
// controllaStudio la ricarica appena lo Studio riparte sulla stessa porta.
function studioSpento() {
  return new ErroreStudio(
    "Lo Studio non risponde: il suo programma si è chiuso, per esempio dopo un aggiornamento di AIRENDER.",
    "Premi «Apri nello Studio» nella palette di Allplan. Questa pagina si ricollega da sola appena lo Studio riparte.");
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
    S.spento = true;
    throw studioSpento();
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
// Una spiegazione che non occupa la pagina: un «?» accanto all'etichetta,
// il testo al passaggio del mouse o con il tasto Tab (proposta 5, 2026-11-02).
function spiega(testo) {
  return h("span", { classe: "spiega", tabindex: "0", role: "note", title: testo, "aria-label": testo }, "?");
}
// Una riga breve con la spiegazione intera dietro il «?».
function nota(breve, testo) {
  return h("p", { classe: "tenue piccolo" }, breve, " ", spiega(testo));
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
  if (sc.scena === "pianta") {
    // Un piano visto dall'alto: muri, una porta, gli arredi; o un lotto con edifici e verde.
    const COLORI = { materica: ["#E9DCC4", "#C9A57A", "#2C2C2C"], concorso: ["#F2EEE6", "#D8CDB8", "#5A5A5A"],
      biancoenero: ["#FFFFFF", "#E6E6E6", "#111111"], assonometria: ["#ECE7DE", "#C9B79C", "#3A3A3A"],
      plastico: ["#F4F1EA", "#E2D6C0", "#CFCAC2"], drone: ["#8FA27A", "#A9A39A", "#6E6458"], acquerello: ["#F7F3EA", "#B9CFC0", "#4B5563"] };
    const [fondo, pavimento, muro] = COLORI[sc.look] || COLORI.materica;
    const ombra = sc.luce === "diffusa" ? 0 : (sc.luce === "radente" ? 6 : 2.5);
    if (sc.tipo === "sito" || sc.tipo === "volumi") {
      const tetto = sc.look === "plastico" ? "#FFFFFF" : (sc.look === "drone" ? "#9B5A43" : muro);
      corpo = `<rect width="128" height="72" fill="${sc.look === "drone" ? "#7F9466" : "#DCE5D1"}"/>
        <path d="M0 50 H128 V60 H0 Z" fill="${sc.look === "plastico" ? "#E2D6C0" : "#B8B3AA"}"/>
        ${[[14, 14, 26, 22], [52, 10, 22, 30], [86, 18, 28, 18]].map(([x, y, w, hh]) =>
          `<rect x="${x + ombra}" y="${y + ombra}" width="${w}" height="${hh}" fill="#000" opacity=".18"/><rect x="${x}" y="${y}" width="${w}" height="${hh}" fill="${tetto}"/>`).join("")}
        ${[[44, 44], [80, 42], [118, 40], [8, 44]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="4" fill="${sc.look === "plastico" ? "#FFFFFF" : "#5E7F4F"}" opacity=".9"/>`).join("")}`;
    } else {
      corpo = `<rect width="128" height="72" fill="${fondo}"/>
        <rect x="14" y="8" width="100" height="56" fill="${pavimento}"/>
        <path d="M14 8 H114 V64 H14 Z M64 8 V40 M64 48 V64 M14 36 H50" stroke="${muro}" stroke-width="3" fill="none"/>
        <path d="M64 40 A8 8 0 0 1 72 48" stroke="${muro}" stroke-width=".8" fill="none"/>
        <rect x="22" y="44" width="26" height="12" rx="2" fill="#FFFFFF" opacity=".75"/>
        <rect x="78" y="16" width="26" height="18" rx="1" fill="#FFFFFF" opacity=".75"/>
        ${ombra ? `<path d="M17 11 H111 V14 H17 Z" fill="#000" opacity=".12"/>` : ""}`;
    }
  } else if (sc.scena === "prodotto") {
    // Un pezzo solo su un fondo da studio: una sedia stilizzata.
    const FONDI = { bianco: "#F7F7F5", grigio: "#CFCAC2", calce: "#E8E2D6", scuro: "#2E3033", vista: "#D9D2C5", ambiente: "#BFB6A8" };
    const fondo = FONDI[sc.sfondo] || FONDI.grigio;
    const scuro = sc.sfondo === "scuro" || sc.luce === "controluce";
    const legno = scuro ? "#6B4A2E" : "#A9774A";
    corpo = `<rect width="128" height="72" fill="${scuro ? "#2E3033" : fondo}"/>
      ${sc.sfondo === "ambiente" ? `<rect x="8" y="10" width="34" height="30" fill="#D8CFC0" opacity=".7"/><rect x="92" y="18" width="26" height="40" fill="#A99E8E" opacity=".6"/>` : ""}
      <ellipse cx="64" cy="62" rx="26" ry="3.5" fill="#000" opacity="${sc.luce === "softbox" ? ".12" : ".22"}"/>
      ${sc.luce === "sole" ? `<path d="M70 62 L112 62 L104 52 L76 52 Z" fill="#000" opacity=".12"/>` : ""}
      <rect x="46" y="20" width="5" height="42" rx="1" fill="${legno}"/>
      <rect x="46" y="38" width="36" height="5" rx="1" fill="${legno}"/>
      <rect x="77" y="38" width="5" height="24" rx="1" fill="${legno}"/>
      <rect x="50" y="40" width="4" height="22" rx="1" fill="${legno}" opacity=".7"/>
      <rect x="48" y="22" width="3" height="16" fill="#8A5A34" opacity=".5"/>
      ${sc.luce === "controluce" ? `<path d="M46 20 V62 M46 38 H82" stroke="#F3E3C0" stroke-width="1" opacity=".8"/>` : ""}`;
  } else if (sc.scena === "interno") {
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
// Il giudizio sulla vista per la scena scelta: una pianta e' fatta di linee,
// e il controllo del wireframe vale solo per una vista in prospettiva.
function giudizioVista() {
  const d = S.descrizione;
  if (!d) return null;
  if (S.scelte && S.scelte.scena === "pianta" && d.leggibile !== false) {
    return { idonea: !!d.idonea_pianta, fatto: (d.pianta || {}).fatto || d.fatto, cosa_fare: (d.pianta || {}).cosa_fare || d.cosa_fare };
  }
  return { idonea: !!d.idonea, fatto: d.fatto, cosa_fare: d.cosa_fare };
}
function asse(id) { return S.catalogo.scene[S.scelte.scena].assi.find((a) => a.id === id); }
function nomeVoce(idAsse, valore) {
  const a = asse(idAsse);
  const v = a && a.voci.find((x) => x.id === valore);
  return v ? v.nome : "";
}
// Il prompt in inglese si vede (e si riscrive) solo coi piani Pro e Studio, o
// con una chiave propria: lo dice il server dello Studio (prompt_completo).
function vedePrompt() { return !!(S.catalogo && S.catalogo.prompt_completo); }
function modelloScelto() { return S.catalogo.modelli.find((m) => m.id === S.modello); }

// --- I miei preset -------------------------------------------------------

async function caricaMiei() {
  try {
    const r = await get("/api/miei-preset");
    S.miei.preset = r.preset; S.miei.problema = r.problema;
  } catch (e) { S.miei.problema = e.fatto; }
}

async function operaMiei(indirizzo, corpo) {
  try {
    const r = await post(indirizzo, corpo);
    S.miei.preset = r.preset; S.miei.problema = r.problema; S.errore = null;
    return true;
  } catch (e) { S.errore = e; render(); return false; }
}

async function salvaMio() {
  const nome = window.prompt("Nome del preset (per esempio «Notte cliente Rossi»):", S.miei.scelto || "");
  if (nome === null) return;
  const corpo = { nome, scelte: S.scelte, modello: S.modello, prompt_a_mano: S.promptAMano };
  const doppio = S.miei.preset.some((p) => p.nome.toLowerCase() === nome.trim().toLowerCase());
  if (doppio && !window.confirm(`Hai già un preset «${nome.trim()}». Lo sostituisco con le scelte di adesso?`)) return;
  if (await operaMiei("/api/miei-preset", { ...corpo, sovrascrivi: doppio })) {
    S.miei.scelto = nome.trim(); S.miei.nota = `Salvato «${nome.trim()}».`; render();
  }
}

async function rinominaMio() {
  const vecchio = S.miei.scelto;
  const nuovo = window.prompt(`Nuovo nome per «${vecchio}»:`, vecchio);
  if (nuovo === null) return;
  if (await operaMiei("/api/miei-preset/rinomina", { nome: vecchio, nuovo })) {
    S.miei.scelto = nuovo.trim(); S.miei.nota = null; render();
  }
}

async function eliminaMio() {
  const nome = S.miei.scelto;
  if (!window.confirm(`Elimino il preset «${nome}»? Non si può annullare.`)) return;
  if (await operaMiei("/api/miei-preset/elimina", { nome })) { S.miei.scelto = ""; S.miei.nota = `Eliminato «${nome}».`; render(); }
}

function caricaMio(nome) {
  S.miei.scelto = nome; S.miei.nota = null;
  const p = S.miei.preset.find((x) => x.nome === nome);
  if (!p) { render(); return; }
  S.preset = null;
  S.scelte = { ...p.scelte, fedelta: undefined };  // Fedeltà al disegno tolta (2026-11-06): vale sempre la regola predefinita
  if (p.modello && S.catalogo.modelli.some((m) => m.id === p.modello)) S.modello = p.modello;
  S.promptAMano = vedePrompt() ? (p.prompt_a_mano || null) : null;
  if (p.blocchi_cambiati || p.perse.length) {
    S.miei.nota = p.perse.length
      ? `Salvato con i blocchi ${p.versione_blocchi || "di prima"}: ${p.perse.join("; ")}. Il resto è caricato.`
      : `Salvato con i blocchi ${p.versione_blocchi || "di prima"}: le scelte ci sono tutte, ma il testo dei blocchi può essere cambiato.`;
  }
  caricaDestinazione().then(() => aggiornaComposto(S.promptAMano === null)).then(render);
}

function pannelloMiei() {
  const m = S.miei;
  const scelta = h("select", { "aria-label": "I miei preset" },
    h("option", { value: "", selected: !m.scelto }, m.preset.length ? "Nessuno — scelte libere" : "Nessuno salvato — scelte libere"),
    m.preset.map((p) => h("option", { value: p.nome, selected: p.nome === m.scelto }, p.nome)));
  scelta.addEventListener("change", () => caricaMio(scelta.value));
  return [
    h("span", { classe: "etichetta" }, "I miei preset"),
    h("div", { classe: "riga" }, scelta,
      h("button", { classe: "btn", onclick: salvaMio }, "Salva queste scelte"),
      m.scelto ? h("button", { classe: "btn", onclick: rinominaMio }, "Rinomina") : null,
      m.scelto ? h("button", { classe: "btn", onclick: eliminaMio }, "Elimina") : null),
    m.problema ? avviso("errore", m.problema, "I preset nuovi si salvano in un file nuovo.") : null,
    m.nota ? h("p", { classe: "tenue piccolo" }, m.nota) : null,
  ];
}

function scegliPreset(id) {
  const p = presetDi(S.scelte.scena).find((x) => x.id === id);
  if (!p) return;
  S.preset = id;
  S.scelte = { ...p.scelte, materiali: S.scelte.materiali, qualita: S.scelte.qualita, fedelta: undefined,
               resa: p.scelte.scena === "pianta" ? "foto" : S.scelte.resa, risoluzione: S.scelte.risoluzione };
  aggiornaComposto();
  render();
}
function scegliScena(scena) {
  if (scena === S.scelte.scena) return;
  const p = presetDi(scena)[0];
  S.preset = p.id;
  // Una pianta non prende le rese: lo stile della tavola fa già da resa.
  S.scelte = { ...p.scelte, materiali: S.scelte.materiali, qualita: S.scelte.qualita, fedelta: undefined,
               resa: scena === "pianta" ? "foto" : S.scelte.resa, risoluzione: S.scelte.risoluzione };
  aggiornaComposto();
  render();
}
function cambiaAsse(idAsse, valore) {
  S.scelte = { ...S.scelte, [idAsse]: valore };
  aggiornaComposto();
  render();
}

// Le scelte che partono da Genera: con un'immagine caricata, anche cosa
// tenere (la regola delle foto). Senza, il server mette la predefinita.
function scelteGenera() {
  return S.tieni && S.modo !== "contesto" ? { ...S.scelte, partenza: S.tieni } : S.scelte;
}
// Che cos'e' la vista scelta: null per una vista di Allplan (core/partenza.py).
function tipoVista() { return S.descrizione ? S.descrizione.tipo || null : null; }
function nomePrima() {
  const t = tipoVista();
  return t === "foto" ? "Foto di partenza" : t === "schizzo" ? "Schizzo di partenza" : t === "render" ? "Immagine caricata" : "Vista Allplan";
}

let attesaComponi = null;
function aggiornaComposto(subito) {
  clearTimeout(attesaComponi);
  const fai = async () => {
    try {
      S.composto = await post("/api/componi", { vista: S.vista, scelte: scelteGenera(), preset: S.preset, riferimento: S.modo !== "contesto" && S.riferimento && S.riferimento.nome, contesto: contestoPerServer(), materiali: materialiPerServer(), inserti: insertiGenera(), esempi: esempiGenera(), geometria: geometriaGenera() });
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
  S.mat = { dati: null, scelti: {}, cerca: "", tutti: false, errore: null, zone: [], lazo: false, punti: false };
  S.tieni = null;
  S.inserti = [];
  S.esempi = [];
  if (!nome) { render(); return; }
  try { S.descrizione = await get(`/api/viste/${enc(nome)}`); } catch (e) { S.errore = e; }
  // Da una foto o da uno schizzo non si parte con un pezzo d'arredo (blocchi.SCENE_PARTENZA).
  if (tipoVista() && S.scelte && (S.scelte.scena === "prodotto" || S.scelte.scena === "pianta")) scegliScena(S.scelte.scena === "pianta" ? "esterno" : "interno");
  try { S.mat.dati = await get(`/api/viste/${enc(nome)}/materiali`); } catch (e) { S.mat.errore = e; }
  await caricaDestinazione();
  aggiornaComposto();
  await caricaRender();
  if (S.scheda === "passi") await caricaPassi();
  render();
}

async function caricaDestinazione() {
  try { S.destinazione = await get(`/api/destinazione?modello=${enc(S.modello)}&varianti=${S.varianti}&riferimento=${S.riferimento && S.modo !== "contesto" ? 1 : 0}&contesto=${S.modo === "contesto" ? 1 : 0}&materiali=${immaginiMateriali()}&inserti=${insertiGenera().length}&esempi=${esempiGenera().length}&geometria=${geometriaGenera() ? 1 : 0}`); } catch (e) { S.errore = e; }
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
  if (scelto && scelto.modello) await destinazioneDi(scelto.modello);
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
      if (cambiato) await caricaStorico();
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
        if (S.licenza && S.licenza.provider === "airender") caricaLicenza().then(render);
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

// Un invio alla volta: un doppio clic su Genera, Applica o Porta mandava due
// lavori (e pagava due render). Finché la prima richiesta non torna, il
// secondo clic non fa niente.
let invioInCorso = false;
function unInvioAllaVolta(fn) {
  return async function (...argomenti) {
    if (invioInCorso) return;
    invioInCorso = true;
    try { return await fn(...argomenti); } finally { invioInCorso = false; }
  };
}

async function genera() {
  S.errore = null; S.secco = null;
  try {
    const risposta = await post("/api/invia", {
      vista: S.vista, scelte: scelteGenera(), preset: S.preset, modello: S.modello, varianti: S.varianti,
      prompt_a_mano: S.promptAMano, destinazione_mostrata: S.destinazione && S.destinazione.destinazione,
      riferimento: S.modo !== "contesto" && S.riferimento && S.riferimento.nome, contesto: contestoPerServer(),
      materiali: materialiPerServer(), inserti: insertiGenera(), esempi: esempiGenera(),
      geometria: geometriaGenera(),
      controlli_geometria: geometriaGenera() ? S.controlliGeometria : undefined,
      destinazione_geometria_mostrata: S.destinazione && S.destinazione.geometria && S.destinazione.geometria.destinazione,
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
      vista: S.vista, scelte: scelteGenera(), preset: S.preset, modello: S.modello, varianti: S.varianti,
      prompt_a_mano: S.promptAMano, riferimento: S.modo !== "contesto" && S.riferimento && S.riferimento.nome,
      contesto: contestoPerServer(), materiali: materialiPerServer(), inserti: insertiGenera(), esempi: esempiGenera(),
      geometria: geometriaGenera(),
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
    if (S.scheda === "passi") await caricaPassi();
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
    SUL_WEB ? null : h("span", { classe: "tenue" }, "·"),
    SUL_WEB ? null : h("span", { classe: "tenue" }, "Cartella delle viste: "),
    SUL_WEB ? null : h("span", { classe: "mono", title: S.studio.cartella }, S.studio.cartella),
    S.descrizione && S.descrizione.camera ? h("span", { classe: "tenue" }, `· ${S.descrizione.camera}`) : null,
  ].filter(Boolean));
  const posto = document.getElementById("licenza-testata");
  if (posto) posto.replaceChildren(...[pastigliaLicenza()].filter(Boolean));
  for (const voce of document.querySelectorAll("[data-scheda]")) {
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
          : `${l.preset_nome} · ${l.modello_nome}.${SUL_WEB ? "" : " Allplan resta libero."}`),
      h("button", { classe: "btn", onclick: annulla }, "Annulla")));
}

// --- Genera --------------------------------------------------------------------

function sezioneVista() {
  const d = S.descrizione;
  const figura = h("figure", { classe: "riquadro-vista" });
  if (!S.vista) {
    figura.append(h("div", { classe: "vista-vuota" },
      h("h2", {}, "Nessuna vista ancora."),
      SUL_WEB
        ? h("p", {}, S.scelte && S.scelte.scena === "pianta"
          ? "Scegli un'immagine della pianta con Usa un'altra vista…: un export di Allplan, una pianta scansionata o una pianta già resa."
          : "Parti da un'immagine: una foto, un render già fatto o uno schizzo. Resta in questo browser finché non la mandi al servizio.")
        : h("p", {}, S.scelte && S.scelte.scena === "pianta"
          ? "In Allplan metti la vista in pianta (dall'alto, per la planimetria anche le ombre) e catturala dalla palette, oppure scegli un'immagine di pianta con Usa un'altra vista…"
          : "Catturala dalla palette in Allplan, oppure parti da un'immagine: una foto, un render già fatto o uno schizzo."),
      S.daImmagine.aperto ? null : h("div", { classe: "azioni" },
        h("button", { classe: "btn primario", onclick: () => apriDaImmagine() }, "Da un'immagine…")),
      SUL_WEB ? null : h("p", { classe: "tenue piccolo" }, "Cartella delle viste: ", h("span", { classe: "mono" }, S.studio.cartella))));
  } else {
    figura.append(S.mat.lazo || S.mat.punti || S.mat.zone.length ? telaZone()
      : h("img", { src: `/file/vista/${enc(S.vista)}`, alt: `Vista di partenza ${S.vista}` }));
    if (S.lavoroAttivo) figura.append(striscia());
  }
  const sotto = h("div", { classe: "riga tra" });
  const g = giudizioVista();
  if (d && d.tipo) {
    sotto.append(d.idonea
      ? h("span", {}, h("b", { stile: "color:var(--ok)" }, d.tipo_nome), h("span", { classe: "tenue" }, ` · ${d.larghezza}×${d.altezza} · ${d.nome}`))
      : h("span", {}, h("b", { stile: "color:var(--errore)" }, "Immagine troppo piccola"), h("span", { classe: "tenue" }, ` · ${d.nome}`)));
  } else if (d) {
    if (g.idonea && S.scelte.scena === "pianta") {
      sotto.append(h("span", {}, h("b", { stile: "color:var(--ok)" }, "Pianta adatta"),
        h("span", { classe: "tenue" }, ` · linee e colori piatti vanno bene · ${d.larghezza}×${d.altezza} · ${d.nome}`)),
        h("button", { classe: "btn", "aria-expanded": String(!!(S.punto && S.punto.da === "0")),
          onclick: () => apriPunto("0", `/file/vista/${enc(S.vista)}`, S.scelte.tipo),
          title: "Se la pianta è già fatta: clicca dove stai e trascina verso dove guardi, esce la foto di quella camera." }, "Punto di vista"));
    } else if (g.idonea) {
      sotto.append(h("span", {}, h("b", { stile: "color:var(--ok)" }, "Vista adatta"),
        h("span", { classe: "tenue" }, ` · ${d.toni} toni di grigio, sfondo uniforme al ${Math.round(d.quota_sfondo * 100)}% · ${d.larghezza}×${d.altezza} · ${d.nome}`)));
    } else {
      sotto.append(h("span", {}, h("b", { stile: "color:var(--errore)" }, "Vista non adatta"), h("span", { classe: "tenue" }, ` · ${d.nome}`)));
    }
  }
  sotto.append(h("div", { classe: "riga" },
    h("button", { classe: "btn", onclick: () => apriDaImmagine(), "aria-expanded": String(S.daImmagine.aperto) }, "Da un'immagine…"),
    h("button", { classe: "btn", onclick: () => { S.mostraViste = !S.mostraViste; render(); }, "aria-expanded": String(S.mostraViste) }, "Usa un'altra vista…")));
  const blocco = h("section", { classe: "pannello", "aria-label": "Vista di partenza" }, figura, sotto);
  if (S.daImmagine.aperto) blocco.append(pannelloDaImmagine());
  if (d && d.tipo && d.idonea) blocco.append(pannelloTieni(d));
  if (d && !g.idonea) blocco.append(avviso("errore", g.fatto, g.cosa_fare));
  if (d && d.colori_come_materiali) {
    blocco.append(avviso("attenzione", "Il modello legge i colori della vista come materiali.",
      "Per colori veri, salva la vista con colori neutri."));
  }
  if (S.mostraViste) blocco.append(pannelloViste());
  if (S.punto && S.punto.da === "0" && S.scelte.scena === "pianta") blocco.append(pannelloPunto());
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
    h("span", { classe: "etichetta" }, "Oppure un file", spiega("Lo Studio ne mette una copia nella cartella delle viste, con un nome nuovo.")),
    file);
}

// --- Da un'immagine (2026-11-09, flussi 2, 8, 9 e 10) -------------------------
// Una partenza accanto a «Cattura vista»: si carica una foto, un render gia'
// fatto o uno schizzo, e si dice cosa farne. Niente parte finche' non si
// preme un invio, e prima di ogni invio si vede dove va (regola 5). Le
// scelte riusano quello che c'e': Genera con la regola delle foto, il
// risultato con la sua barra (Cambia, Ritocca, Popola, Finale, Regola),
// «Inserisci nel contesto» per mettere il progetto nella foto.

const TIPI_IMMAGINE = [
  ["render", "Un render già fatto", "Tuo, di AIRENDER o di un altro programma. Salta Stile e Render: va dritto al risultato, con Cambia, Ritocca, Popola, Finale e Regola."],
  ["foto", "Una foto", "Del luogo o di una stanza. Ne cambi il look, gli arredi e i materiali, oppure ci metti dentro il progetto."],
  ["schizzo", "Uno schizzo o un plastico", "Uno schizzo a mano o la foto di un modello. Passa da Genera come una vista: tiene le linee, aggiunge materiali e luce."],
];
const COSE_FOTO = [
  ["look", "Cambia il look", "Stessa stanza, stesse pareti e finestre, stile nuovo da un preset o da un'immagine di riferimento. Si fa in Genera."],
  ["arredi", "Cambia arredi o materiali", "Riquadro dove va il pezzo con la sua foto di riferimento, o un materiale da cambiare. Si fa in Ritocca."],
  ["contesto", "Metti il progetto qui", "La foto è il luogo, la vista di Allplan è l'edificio. È «Fotoinserimento» in Genera."],
];

function apriDaImmagine() {
  S.daImmagine = { ...S.daImmagine, aperto: !S.daImmagine.aperto, errore: null,
                   scena: S.daImmagine.scena || (S.scelte && S.scelte.scena === "esterno" ? "esterno" : "interno") };
  S.mostraViste = false;
  render();
}

// «Metti il progetto qui» ha bisogno della vista del progetto: una vista di
// Allplan (o un'immagine del progetto caricata con «Usa un'altra vista»).
function perchéContestoSpento() {
  if (!S.vista) return "Prima serve la vista del progetto: catturala da Allplan o caricala con «Usa un'altra vista».";
  if (tipoVista()) return "La vista scelta ora è un'immagine caricata, non il progetto: scegli prima la vista del progetto con «Usa un'altra vista».";
  return null;
}

async function caricaDaImmagine(file) {
  const di = S.daImmagine;
  if (!file || !di.tipo) return;
  di.caricando = true; di.errore = null; render();
  try {
    if (di.tipo === "foto" && di.cosa === "contesto") {
      await cambiaModo("contesto");
      await scegliContesto(file);
      S.daImmagine = { aperto: false, tipo: null, cosa: null, scena: di.scena, caricando: false, errore: null };
      if (location.hash !== "#genera") location.hash = "#genera"; else render();
      return;
    }
    const r = await post("/api/viste", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name),
                                               "X-Tipo-Immagine": di.tipo, "X-Scena": di.scena });
    S.studio = await get("/api/studio");
    if (S.modo === "contesto") await cambiaModo("vista");
    const tipo = di.tipo, cosa = di.cosa;
    if (S.scelte.scena !== di.scena) scegliScena(di.scena);
    S.daImmagine = { aperto: false, tipo: null, cosa: null, scena: di.scena, caricando: false, errore: null };
    await caricaVista(r.nome);
    await caricaStorico();
    if (r.lavoro && (tipo === "render" || cosa === "arredi")) {
      S.risultato.scelto = r.lavoro; S.risultato.confronto = "vista"; S.passi.scelto = r.lavoro;
      if (cosa === "arredi") {
        await caricaPassi();
        ritoccaDa({ identificativo: r.lavoro });
        return;
      }
      await caricaRicetta();
      if (location.hash !== "#risultato") location.hash = "#risultato"; else render();
      return;
    }
    if (location.hash !== "#genera") location.hash = "#genera"; else render();
  } catch (e) {
    S.daImmagine.caricando = false;
    S.daImmagine.errore = e;
    render();
  }
}

function pannelloDaImmagine() {
  const di = S.daImmagine;
  const scegliTipo = (id) => { di.tipo = id; di.cosa = id === "foto" ? (di.cosa || "look") : null; di.errore = null; render(); };
  const tipi = h("div", { classe: "scelta-modo", role: "group", "aria-label": "Che immagine è" },
    TIPI_IMMAGINE.map(([id, nome, testo]) => h("button", { classe: "modo", "aria-pressed": String(di.tipo === id), onclick: () => scegliTipo(id) },
      h("b", {}, nome), h("span", { classe: "tenue piccolo" }, testo))));
  const contestoNo = perchéContestoSpento();
  const cose = di.tipo === "foto" ? h("div", { classe: "scelta-modo", role: "group", "aria-label": "Cosa vuoi fare con la foto" },
    COSE_FOTO.map(([id, nome, testo]) => {
      const no = id === "contesto" && contestoNo;
      return h("button", { classe: "modo", "aria-pressed": String(di.cosa === id), disabled: no || null, title: no || null,
        onclick: () => { di.cosa = id; render(); } },
        h("b", {}, nome), h("span", { classe: "tenue piccolo" }, no || testo));
    })) : null;
  const dopo = !di.tipo ? "Scegli che immagine è: serve a saltare i passi che non servono."
    : di.tipo === "render" ? "Diventa subito un risultato: nessun invio, nessun credito finché non scegli Cambia, Ritocca, Popola o Finale."
    : di.tipo === "schizzo" ? "Si apre Genera: scegli un preset e premi Genera."
    : di.cosa === "look" ? "Si apre Genera con la foto come partenza: scegli un preset o un'immagine di riferimento, e cosa tenere."
    : di.cosa === "arredi" ? "Si apre Ritocca sulla foto: disegna un riquadro, scrivi cosa diventa e aggiungi il Rif. del pezzo."
    : "Si apre «Fotoinserimento» con la foto come luogo: segni dove va l'edificio e premi Genera.";
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", hidden: true, "aria-label": "Scegli l'immagine",
    onchange: (e) => caricaDaImmagine(e.target.files && e.target.files[0]) });
  return h("div", { classe: "pannello da-immagine", "aria-label": "Da un'immagine" },
    h("div", { classe: "riga tra" }, h("h2", {}, "Da un'immagine"),
      h("button", { classe: "btn link piccolo", onclick: () => apriDaImmagine() }, "Chiudi")),
    h("span", { classe: "etichetta" }, "Che immagine è?"), tipi,
    cose ? h("span", { classe: "etichetta" }, "Cosa vuoi fare?") : null, cose,
    di.tipo && di.cosa !== "contesto" ? h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Che cosa si vede?"),
      h("div", { classe: "switch", role: "group", "aria-label": "Esterno o interno" },
        [["esterno", "Un esterno"], ["interno", "Un interno"]].map(([id, nome]) =>
          h("button", { classe: "seg", "aria-pressed": String(di.scena === id), onclick: () => { di.scena = id; render(); } }, nome))),
      h("span", { classe: "piccolo tenue" }, "Decide le voci di Cambia, Popola e dei preset.")) : null,
    h("p", { classe: "piccolo tenue" }, dopo),
    h("div", { classe: "riga" },
      h("button", { classe: "btn primario", disabled: !di.tipo || di.caricando || null, onclick: () => file.click() },
        di.caricando ? "Carico l'immagine…" : "Scegli l'immagine…"), file,
      h("span", { classe: "piccolo tenue" }, SUL_WEB
        ? "PNG o JPEG. Resta in questo browser: non parte niente finché non premi un invio."
        : "PNG o JPEG. Lo Studio ne mette una copia nella cartella delle viste: non parte niente finché non premi un invio.")),
    di.errore ? avviso("errore", di.errore.fatto, di.errore.cosa_fare) : null);
}

// Con un'immagine caricata, in Genera: cosa tenere. Prende il posto della
// fedelta' al disegno, che parla di una vista di Allplan.
function pannelloTieni(d) {
  if (S.modo === "contesto") return null;
  const scelta = S.tieni || d.partenza_predefinita;
  const testi = {
    "foto": "Rifà arredi, finiture e materiali; pareti, finestre, porte e prospettiva restano.",
    "foto-arredi": "Cambia solo luce, colori e materiali: pareti, arredi e oggetti restano dove sono.",
    "schizzo": "Tiene ogni linea: stessa inquadratura, volumi e aperture. Aggiunge materiali veri e luce.",
  };
  const nomi = { "foto": "Muri e finestre", "foto-arredi": "Anche gli arredi", "schizzo": "Le linee dello schizzo" };
  const cambia = async (id) => { S.tieni = id; S.secco = null; aggiornaComposto(true); render(); };
  return h("div", { classe: "riga tieni" },
    h("span", { classe: "etichetta" }, "Cosa tenere", spiega("La foto è vera: la regola fissa tiene la prospettiva della fotocamera, le pareti, i serramenti e la luce che c'è. Scritta, non ancora provata col modello.")),
    d.partenze.length > 1
      ? h("div", { classe: "switch", role: "group", "aria-label": "Cosa tenere" },
          d.partenze.map((p) => h("button", { classe: "seg", "aria-pressed": String(scelta === p.id), onclick: () => cambia(p.id) }, nomi[p.id] || p.nome)))
      : h("b", {}, nomi[scelta] || scelta),
    h("span", { classe: "piccolo tenue" }, testi[scelta] || ""));
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

// Le rese: quella scelta e cosa spegne. Un asse spento resta visibile, in
// grigio, con la ragione: nasconderlo farebbe credere che non esista.
function resaScelta() { return S.catalogo.rese.find((r) => r.id === (S.scelte.resa || "foto")) || S.catalogo.rese[0]; }
function spento(idAsse) { return resaScelta().spegne.includes(idAsse); }
function notaSpento(idAsse) {
  return spento(idAsse) ? h("p", { classe: "tenue piccolo" }, `Spento con la resa ${resaScelta().nome}: non parte. Torna a Fotorealistico per usarlo.`) : null;
}
const FILTRI_RESA = {
  plastico: "grayscale(1) brightness(1.35) contrast(.8)", schizzo: "grayscale(1) contrast(1.5) brightness(1.1)",
  acquerello: "saturate(.65) brightness(1.12) blur(.5px)", cinema: "contrast(1.3) saturate(1.25) sepia(.15)",
};
function illustrazioneResa(id) {
  const svg = illustrazione(S.scelte);
  if (FILTRI_RESA[id]) svg.style.filter = FILTRI_RESA[id];
  return svg;
}
function scegliResa(id) { cambiaAsse("resa", id); }

function chipAsse(idAsse) {
  const a = asse(idAsse);
  const via = spento(idAsse);
  return h("div", {}, h("div", { classe: "scelte-chip", role: "group", "aria-label": a.titolo },
    a.voci.map((v) => h("button", {
      classe: "chip", "aria-pressed": String(S.scelte[idAsse] === v.id), disabled: !v.attivo || via,
      title: v.attivo ? (v.descrizione || null) : `In arrivo: ${v.nota}`,
      onclick: v.attivo ? () => cambiaAsse(idAsse, v.id) : null,
    }, v.nome))), descrizioneScelta(a, S.scelte[idAsse]), notaSpento(idAsse));
}

// Una riga sotto le scelte: cosa cambia la voce scelta, in parole semplici.
function descrizioneScelta(a, valore) {
  const v = a.voci.find((x) => x.id === valore);
  return v && v.descrizione ? h("p", { classe: "tenue piccolo" }, `${v.nome}: ${v.descrizione.charAt(0).toLowerCase()}${v.descrizione.slice(1)}`) : null;
}

function tessereAsse(idAsse) {
  const a = asse(idAsse);
  const via = spento(idAsse);
  return h("div", {}, h("div", { classe: "griglia", role: "group", "aria-label": a.titolo },
    a.voci.map((v) => tessera(v.nome, S.scelte[idAsse] === v.id,
      v.attivo && !via ? () => cambiaAsse(idAsse, v.id) : null,
      v.attivo ? illustrazione({ ...S.scelte, [idAsse]: v.id }) : null, v.attivo ? null : v.nota))), notaSpento(idAsse));
}

function sintesi() {
  const s = S.scelte;
  if (s.scena === "pianta") return [nomeVoce("tipo", s.tipo || "edificio"), nomeVoce("look", s.look), nomeVoce("luce", s.luce)].filter(Boolean).join(" · ");
  const pezzi = [resaScelta().nome, spento("look") ? null : (nomeVoce("look", s.look) || "").split(" · ")[0], spento("luce") ? null : nomeVoce("luce", s.luce)];
  if (s.scena === "esterno") pezzi.push(nomeVoce("cielo", s.cielo), `intorno: ${(nomeVoce("intorno", s.intorno) || "—").toLowerCase()}`,
    `verde: ${(nomeVoce("verde", s.verde) || "—").toLowerCase()}`);
  else if (s.scena === "prodotto") pezzi.push(spento("sfondo") ? null : nomeVoce("sfondo", s.sfondo));
  else pezzi.push(nomeVoce("fuori", s.fuori), nomeVoce("arredo", s.arredo));
  if (s.scena !== "prodotto") pezzi.push(`persone: ${(nomeVoce("persone", s.persone) || "—").toLowerCase()}`);
  return pezzi.filter(Boolean).join(" · ");
}

const SCENE = [["esterno", "Esterno"], ["interno", "Interno"], ["prodotto", "Arredo"], ["pianta", "Pianta"]];

function colonnaStile() {
  const interno = S.scelte.scena === "interno";
  const prodotto = S.scelte.scena === "prodotto";
  const scena = h("div", { classe: "riga" },
    h("span", { classe: "etichetta" }, "Scena"),
    h("div", { classe: "switch", role: "group", "aria-label": "Scena" },
      SCENE.map(([id, nome]) => {
        const no = (id === "prodotto" || id === "pianta") && tipoVista();
        return h("button", { classe: "seg", "aria-pressed": String(S.scelte.scena === id), disabled: no || null,
          title: no ? "Da una foto o da uno schizzo si parte con un esterno o un interno. Per un pezzo d'arredo o una pianta: una vista di Allplan, o la pianta con «Usa un'altra vista»." : null,
          onclick: () => scegliScena(id) }, nome);
      })));
  const preset = h("section", { classe: "pannello", "aria-label": "Parti da un preset" },
    h("h2", {}, "Parti da un preset"),
    h("p", { classe: "tenue piccolo" }, rigaMiniature(presetDi(S.scelte.scena))),
    h("div", { classe: "griglia" }, presetDi(S.scelte.scena).map((p) =>
      tessera(p.nome, S.preset === p.id, () => scegliPreset(p.id), miniatura(p), null,
        p.miniatura ? `render vero del ${p.miniatura.data}` : null))));

  const dettagli = h("details", { classe: "pannello dettagli", open: S.dettagliAperti });
  dettagli.addEventListener("toggle", () => { S.dettagliAperti = dettagli.open; });
  if (S.scelte.scena === "pianta") {
    dettagli.append(
      h("summary", {}, h("h2", {}, "Dettagli del preset"),
        h("span", { classe: "tenue piccolo", id: "sintesi" }, sintesi()),
        h("span", { classe: "tenue piccolo" }, "· cambi un pezzo, il resto resta com'è")),
      h("div", { classe: "gruppo" }, h("h3", {}, "1 · Che disegno è",
        spiega("Planimetria e planivolumetrico partono da una vista zenitale di Allplan. Nel planivolumetrico le ombre seguono le altezze dei volumi.")),
        tessereAsse("tipo")),
      h("div", { classe: "gruppo" }, h("h3", {}, "2 · Stile della tavola",
        spiega("Prende il posto del look fotografico e della resa · muri, aperture e impronte restano dove li hai disegnati")),
        chipAsse("look")),
      h("div", { classe: "gruppo" }, h("h3", {}, "3 · Luce e ombre"), tessereAsse("luce")),
      h("p", { classe: "tenue piccolo" }, "Verde, alberi, persone e auto si aggiungono dopo, sul render, con i pennelli del Ritocca. Le stanze si arredano con Arreda."));
    return h("div", { classe: "colonna-stile" }, scena, preset, dettagli);
  }
  dettagli.append(
    h("summary", {}, h("h2", {}, "Dettagli del preset"),
      h("span", { classe: "tenue piccolo", id: "sintesi" }, sintesi()),
      h("span", { classe: "tenue piccolo" }, "· cambi un pezzo, il resto resta com'è")),
    h("div", { classe: "gruppo" }, h("h3", {}, "1 · Resa"),
      h("p", { classe: "tenue piccolo" }, resaScelta().spegne.length
        ? `${resaScelta().nome} spegne: ${resaScelta().spegne_testo}.`
        : "Miniature illustrative."),
      h("div", { classe: "griglia", role: "group", "aria-label": "Resa" }, S.catalogo.rese.map((r) => tessera(r.nome,
        (S.scelte.resa || "foto") === r.id, () => scegliResa(r.id), illustrazioneResa(r.id), null)))),
    h("div", { classe: "gruppo" }, h("h3", {}, "2 · Look fotografico", spiega("Colore, contrasto e grana · l’inquadratura resta quella di Allplan · solo per le rese fotografiche")),
      chipAsse("look")),
    h("div", { classe: "gruppo" }, h("h3", {}, S.scelte.scena === "esterno" ? "3 · Ora / Luce" : "3 · Luce"), tessereAsse("luce")),
    prodotto
      ? h("div", { classe: "gruppo" }, h("h3", {}, "4 · Sfondo", spiega("Prende il posto di tutto quello che non è il pezzo · il primo piano lo dà la vista di Allplan")),
          tessereAsse("sfondo"))
      : interno
      ? h("div", { classe: "gruppo" }, h("h3", {}, "4 · Fuori dalle finestre e arredo"),
          h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Fuori dalle finestre"), chipAsse("fuori")),
          h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Arredo"), chipAsse("arredo")))
      : h("div", { classe: "gruppo" }, h("h3", {}, "4 · Cielo e stagione"), tessereAsse("cielo")),
    prodotto ? null : h("div", { classe: "gruppo" }, h("h3", {}, interno ? "5 · Persone" : "5 · Cosa può aggiungere il modello"),
      interno ? null : h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Intorno all'edificio"), chipAsse("intorno")),
      interno ? null : h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Verde"), chipAsse("verde")),
      h("div", { classe: "sotto-gruppo" }, h("span", { classe: "etichetta" }, "Persone"), chipAsse("persone"))));
  return h("div", { classe: "colonna-stile" }, scena, preset, dettagli);
}

function colonnaInvio() {
  const interno = S.scelte.scena === "interno";
  const materiali = h("textarea", {
    id: "materiali", rows: "3", "aria-label": "Materiali a parole",
    placeholder: S.scelte.scena === "pianta" ? "es. pavimenti in rovere chiaro, bagni in gres grande formato, tetti in coppi"
      : S.scelte.scena === "prodotto" ? "es. struttura in rovere naturale, seduta in cuoio cognac, piedini in ottone spazzolato"
      : interno ? "es. pavimento in rovere chiaro, pareti in calce bianca, cucina in acciaio"
      : "es. intonaco bianco, infissi in rovere scuro, zoccolo in pietra grigia",
  });
  materiali.value = S.scelte.materiali || "";
  materiali.addEventListener("input", () => { S.scelte.materiali = materiali.value; aggiornaComposto(); });

  const mappa = pannelloMateriali();

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
    h("p", { id: "riassunto" }, S.modo === "contesto" && !contestoPerServer()
      ? "Il prompt si compone quando la foto del luogo e l'area ci sono (passo 1)."
      : S.composto ? S.composto.riassunto : "…"),
    !vedePrompt() ? null : h("button", { classe: "btn link", "aria-expanded": String(S.mostraPrompt), onclick: () => { S.mostraPrompt = !S.mostraPrompt; render(); } },
      S.mostraPrompt ? "Nascondi il prompt" : "Avanzate: mostra e modifica il prompt completo"),
    S.mostraPrompt && vedePrompt() ? h("div", { classe: "sotto-gruppo" },
      h("p", { classe: "tenue piccolo" }, "Testo vero che parte al modello, in inglese. Se lo modifichi, i comandi a sinistra non lo toccano più finché non premi «Ricomponi»."),
      prompt,
      h("div", { classe: "riga tra" },
        h("span", { classe: "tenue piccolo mono", id: "caratteri" },
          S.promptAMano !== null ? `${S.promptAMano.length} caratteri · scritto a mano` : `${S.composto ? S.composto.caratteri : 0} caratteri`),
        h("button", { classe: "btn", onclick: () => { S.promptAMano = null; aggiornaComposto(true).then(render); } }, "Ricomponi dalle scelte")),
      h("p", { id: "nota-prompt", classe: S.promptAMano !== null ? "piccolo" : "piccolo nascosto", stile: "color:var(--attenzione)" },
        "Prompt modificato a mano: parte questo testo, non le scelte a sinistra.")) : null);

  const modelli = schedeModello("genera", S.modello,
    S.modo === "contesto" || !!S.riferimento || immaginiMateriali() > 0 || S.inserti.length > 0,
    async (id) => { S.modello = id; S.secco = null; await caricaDestinazione(); render(); });

  const qualita = h("div", { classe: "switch", role: "group", "aria-label": "Qualità" },
    asse("qualita").voci.map((v) => h("button", {
      classe: "seg", "aria-pressed": String(S.scelte.qualita === v.id), onclick: () => cambiaAsse("qualita", v.id),
    }, v.id === "32k" ? "Altissima definizione (32k)" : v.nome)));

  const risoluzione = h("div", { classe: "switch", role: "group", "aria-label": "Risoluzione del render" },
    S.catalogo.risoluzioni.map((r) => h("button", {
      classe: "seg", "aria-pressed": String((S.scelte.risoluzione || "1k") === r.id),
      onclick: () => { S.scelte = { ...S.scelte, risoluzione: r.id }; render(); },
    }, r.nome)));

  const scelteInvio = h("section", { classe: "pannello", "aria-label": "Modello e qualità" },
    ...pannelloMiei(),
    ...(S.modo === "contesto" ? [] : pannelloRicette()),
    h("span", { classe: "etichetta" }, "Modello"), modelli,
    S.modo === "contesto" ? null : h("span", { classe: "etichetta" }, "Qualità"), S.modo === "contesto" ? null : qualita,
    h("span", { classe: "etichetta" }, "Risoluzione del render"), risoluzione,
    h("span", { classe: "etichetta" }, "Varianti per invio"),
    h("div", { classe: "switch", role: "group", "aria-label": "Varianti per invio" },
      Array.from({ length: S.catalogo.varianti_massime }, (_, i) => i + 1).map((n) => h("button", {
        classe: "seg", "aria-pressed": String(S.varianti === n),
        onclick: async () => { S.varianti = n; S.secco = null; await caricaDestinazione(); render(); },
      }, String(n)))),
    S.varianti > 1 ? h("p", { classe: "tenue piccolo" }, `${S.varianti} lavori in coda con le stesse scelte, uno dopo l'altro: ogni variante è un invio.`) : null,
    ...pannelloRiferimento(),
    S.modo === "contesto" ? null : pannelloGeometria(),
    S.modo === "contesto" ? null : pannelloInserti(S.inserti, modelloScelto(), "Genera", async () => {
      S.secco = null; await caricaDestinazione(); aggiornaComposto(true); render();
    }));

  return h("div", { classe: "colonna-invio" },
    S.modo === "contesto" ? null : h("section", { classe: "pannello", "aria-label": "Materiali" },
      h("span", { classe: "etichetta" }, "Materiali a parole"),
      h("p", { classe: "tenue piccolo" }, "Passano al modello come li scrivi, anche in italiano."), materiali,
      spento("materiali") ? h("p", { classe: "piccolo", stile: "color:var(--attenzione)" }, `Con la resa ${resaScelta().nome} i materiali non partono.`) : null),
    S.modo === "contesto" ? null : mappa, cosaParte, scelteInvio, pannelloInvio());
}

// --- materiali di questo progetto -----------------------------------------
// L'elenco lo scrive la palette quando cattura la vista, leggendo Allplan
// senza cambiare niente. Ogni riga spuntata parte con l'anteprima di Allplan,
// il testo e, se c'e', la foto di riferimento.

function materialiPerServer() {
  if (S.modo === "contesto") return [];
  return Object.entries(S.mat.scelti).map(([chiave, v]) => ({ chiave, diventa: v.diventa || "", riferimento: v.riferimento ? v.riferimento.nome : null }))
    .concat(S.mat.zone.map((z) => ({ campione: z.campione.nome, diventa: z.diventa || "", riferimento: z.riferimento ? z.riferimento.nome : null })));
}
function immaginiMateriali() {
  if (S.modo === "contesto") return 0;
  const daZone = S.mat.zone.reduce((n, z) => n + 1 + (z.riferimento ? 1 : 0), 0);
  if (!S.mat.dati) return daZone;
  return daZone + Object.entries(S.mat.scelti).reduce((n, [chiave, v]) => {
    const m = S.mat.dati.materiali.find((x) => x.chiave === chiave);
    return n + (m && m.anteprima ? 1 : 0) + (v.riferimento ? 1 : 0);
  }, 0);
}
async function materialiCambiati() {
  S.secco = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}
async function spuntaMateriale(chiave, acceso) {
  if (acceso) S.mat.scelti[chiave] = S.mat.scelti[chiave] || { diventa: "", riferimento: null };
  else delete S.mat.scelti[chiave];
  await materialiCambiati();
}
async function riferimentoMateriale(chiave, file) {
  if (!file) return;
  try {
    S.mat.scelti[chiave].riferimento = await post("/api/riferimenti", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name) });
    S.errore = null;
  } catch (e) { S.errore = e; }
  await materialiCambiati();
}
function pannelloMateriali() {
  const d = S.mat.dati;
  const testa = h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Materiali di questo progetto"));
  if (!S.vista) return h("section", { classe: "pannello", "aria-label": "Materiali di questo progetto" }, testa,
    h("p", { classe: "piccolo tenue" }, "Cattura una vista dalla palette."));
  if (S.mat.errore) return h("section", { classe: "pannello" }, testa, avviso("errore", S.mat.errore.fatto, S.mat.errore.cosa_fare));
  if (!d) return h("section", { classe: "pannello" }, testa, h("p", { classe: "piccolo tenue" }, "Leggo i materiali…"));
  if (!d.letti) return pannelloZone(d.massimo);
  if (d.errore) return h("section", { classe: "pannello" }, testa,
    avviso("errore", `I materiali non si sono letti: ${d.errore}`, "Cattura di nuovo la vista. Se si ripete, manda diario-materiali.txt."));
  if (!d.materiali.length) return h("section", { classe: "pannello" }, testa,
    h("p", { classe: "piccolo tenue" }, "Nessun materiale nel progetto. Scrivili a parole."));
  const scelti = Object.keys(S.mat.scelti).length;
  const filtro = S.mat.cerca.trim().toLowerCase();
  const trovati = d.materiali.filter((m) => !filtro || m.nome.toLowerCase().includes(filtro));
  const mostrati = S.mat.tutti || filtro ? trovati : trovati.slice(0, 8);  // numero-non-configurabile: righe visibili prima di «Mostra tutti»
  const cerca = h("input", { classe: "campo", type: "search", placeholder: "Cerca un materiale…", "aria-label": "Cerca un materiale", value: S.mat.cerca });
  cerca.addEventListener("input", () => { S.mat.cerca = cerca.value; render(); const c = document.querySelector("[aria-label='Cerca un materiale']"); if (c) { c.focus(); c.setSelectionRange(c.value.length, c.value.length); } });
  const righe = mostrati.map((m) => {
    const scelta = S.mat.scelti[m.chiave];
    const cubo = m.anteprima ? h("img", { classe: "cubo", src: m.anteprima, alt: `Anteprima di Allplan: ${m.nome}` })
      : h("div", { classe: "cubo vuoto" }, "nessuna anteprima");
    const pieno = Object.keys(S.mat.scelti).length >= d.massimo && !scelta;
    const spunta = h("input", { type: "checkbox", checked: !!scelta, disabled: pieno, onchange: (e) => spuntaMateriale(m.chiave, e.target.checked) });
    let sotto = null;
    if (scelta) {
      const diventa = h("input", { classe: "campo", placeholder: "diventa…", "aria-label": `${m.nome} diventa`, value: scelta.diventa });
      diventa.addEventListener("input", () => { scelta.diventa = diventa.value; S.secco = null; aggiornaComposto(); });
      const file = h("input", { type: "file", accept: "image/jpeg,image/png", hidden: true, onchange: (e) => riferimentoMateriale(m.chiave, e.target.files[0]) });
      const rif = scelta.riferimento
        ? h("span", { classe: "riga" }, h("img", { classe: "rif-materiale", src: `/file/riferimento/${enc(scelta.riferimento.nome)}`, alt: "Foto di riferimento" }),
            h("button", { classe: "btn link piccolo", onclick: () => { scelta.riferimento = null; materialiCambiati(); } }, "Togli"))
        : h("button", { classe: "btn piccolo", onclick: () => file.click() }, "+ Riferimento");
      sotto = h("div", { classe: "diventa" }, diventa, rif, file);
    }
    return h("div", { classe: scelta ? "materiale scelto" : "materiale" }, cubo,
      h("div", { classe: "nome-materiale" }, h("b", { title: m.chiave }, m.nome), h("span", { classe: "tenue piccolo" }, `${m.elementi} elementi`)),
      h("label", { classe: "piccolo riga" }, spunta, "Cambia"), sotto);
  });
  const conRif = Object.values(S.mat.scelti).filter((v) => v.riferimento).length;
  return h("section", { classe: "pannello materiali", "aria-label": "Materiali di questo progetto" }, testa,
    h("p", { classe: "piccolo tenue" }, `${d.materiali.length} materiali · letti ${data(d.letto_il)} · max ${d.massimo} da cambiare`),
    cerca, righe,
    !S.mat.tutti && !filtro && trovati.length > mostrati.length
      ? h("button", { classe: "btn link piccolo", onclick: () => { S.mat.tutti = true; render(); } }, `Mostra tutti i ${trovati.length}`) : null,
    d.senza_materiale.some((s) => /facciata/i.test(s))
      ? h("p", { classe: "piccolo", stile: "color:var(--attenzione)" }, "Facciate: scrivile in «Materiali a parole».") : null,
    h("p", { classe: "piccolo tenue", title: "Al modello partono la vista e, per ogni riga spuntata, l'anteprima di Allplan, il testo e la foto. Due materiali che nella vista sembrano uguali possono confondersi." }, "Allplan non viene toccato. ⓘ"),
    scelti ? h("p", { classe: "piccolo" }, h("b", {}, `${scelti === 1 ? "1 materiale" : `${scelti} materiali`} da cambiare`), conRif ? ` · ${conRif === 1 ? "1 foto" : `${conRif} foto`} di riferimento` : "") : null);
}

// --- materiali scelti sulla vista ----------------------------------------------
// Senza l'elenco di Allplan (web app, render e foto da altri programmi) un
// materiale si indica con la selezione libera: si disegna il contorno attorno
// a una superficie della vista, la pagina ritaglia quel pezzo (fuori dal
// contorno grigio piatto) e lo salva fra i riferimenti. Il ritaglio parte come
// campione, al posto dell'anteprima di Allplan; il resto della riga e' uguale.
// Il modello riconosce il materiale dall'aspetto: due superfici che sembrano
// uguali si possono confondere (Trappole note in CLAUDE.md).

// Lato massimo del campione ritagliato, in pixel: basta a leggere grana e colore.
const CAMPIONE_LATO_MASSIMO = 512;
const GRIGIO_FUORI = "#808080";  // numero-non-configurabile: grigio medio, fuori dal contorno del campione

async function ritagliaCampione(img, punti) {
  const W = img.naturalWidth, H = img.naturalHeight;
  const xs = punti.map((p) => p[0] * W), ys = punti.map((p) => p[1] * H);
  const x0 = Math.floor(Math.min(...xs)), y0 = Math.floor(Math.min(...ys));
  const w = Math.max(1, Math.ceil(Math.max(...xs)) - x0), hh = Math.max(1, Math.ceil(Math.max(...ys)) - y0);
  const scala = Math.min(1, CAMPIONE_LATO_MASSIMO / Math.max(w, hh));
  const tela = document.createElement("canvas");
  tela.width = Math.max(1, Math.round(w * scala)); tela.height = Math.max(1, Math.round(hh * scala));
  const c = tela.getContext("2d");
  c.fillStyle = GRIGIO_FUORI;
  c.fillRect(0, 0, tela.width, tela.height);
  c.beginPath();
  punti.forEach(([px, py], i) => { const x = (px * W - x0) * scala, y = (py * H - y0) * scala; if (i) c.lineTo(x, y); else c.moveTo(x, y); });
  c.closePath();
  c.clip();
  c.drawImage(img, x0, y0, w, hh, 0, 0, tela.width, tela.height);
  return new Promise((ok, no) => tela.toBlob((b) => (b ? ok(b) : no(new Error("ritaglio vuoto"))), "image/png"));
}

// «Punti» (flusso 8): un clic su una superficie = un campione di quel
// materiale. Il campione e' un quadrato di questo lato attorno al clic, in
// frazione del lato lungo dell'immagine: SCELTA, abbastanza per leggere grana
// e colore senza prendere la superficie accanto. Non misurata.
const PUNTO_LATO = 0.05;

function quadratoAttorno([x, y], img) {
  const W = img.naturalWidth || 1, H = img.naturalHeight || 1, lungo = Math.max(W, H);
  const mx = (PUNTO_LATO * lungo / W) / 2, my = (PUNTO_LATO * lungo / H) / 2;
  const x0 = Math.max(0, Math.min(1 - 2 * mx, x - mx)), y0 = Math.max(0, Math.min(1 - 2 * my, y - my));
  const f = (v) => Number(v.toFixed(4));
  return [[f(x0), f(y0)], [f(x0 + 2 * mx), f(y0)], [f(x0 + 2 * mx), f(y0 + 2 * my)], [f(x0), f(y0 + 2 * my)]];
}

async function aggiungiZona(img, punti) {
  try {
    const blob = await ritagliaCampione(img, punti);
    const campione = await post("/api/riferimenti", blob, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(`campione-${S.mat.zone.length + 1}.png`) });
    S.mat.zone.push({ punti, campione, diventa: "", riferimento: null });
    S.errore = null;
  } catch (e) {
    S.errore = e && e.fatto ? e : { fatto: "Il pezzo selezionato non si è potuto ritagliare dalla vista.", cosa_fare: "Ricarica la pagina e disegna di nuovo il contorno." };
  }
  if (S.mat.zone.length >= (S.mat.dati ? S.mat.dati.massimo : 0)) { S.mat.lazo = false; S.mat.punti = false; }
  await materialiCambiati();
  const campo = document.getElementById(`zona-diventa-${S.mat.zone.length - 1}`);
  if (campo) campo.focus();
}

async function togliZona(i) {
  S.mat.zone.splice(i, 1);
  await materialiCambiati();
}

async function riferimentoZona(i, file) {
  if (!file) return;
  try {
    S.mat.zone[i].riferimento = await post("/api/riferimenti", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name) });
    S.errore = null;
  } catch (e) { S.errore = e; }
  await materialiCambiati();
}

function telaZone() {
  const img = h("img", { src: `/file/vista/${enc(S.vista)}`, alt: `Vista di partenza ${S.vista}`, draggable: "false" });
  const contenitore = h("div");
  contenitore.innerHTML = `<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" class="aree-svg" aria-hidden="true">${
    S.mat.zone.map((z) => `<polygon class="contorno-area" points="${attributoPunti(z.punti)}"></polygon>`).join("")
  }<polyline class="contorno-area in-corso" points=""></polyline></svg>`;
  const disegno = contenitore.firstElementChild;
  const traccia = disegno.querySelector("polyline");
  const numeri = S.mat.zone.map((z, i) => {
    const [x, y] = z.punti[0];
    return h("span", { classe: "numero-area", stile: `left:${x * 100}%;top:${y * 100}%`, "aria-hidden": "true" }, String(i + 1));
  });
  const tela = h("div", { classe: `tela-ritocco${S.mat.lazo || S.mat.punti ? "" : " bloccata"}` }, img, disegno, ...numeri);
  if (!S.mat.lazo && !S.mat.punti) return tela;
  let tratto = null;
  const punto = (ev) => {
    const b = img.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (ev.clientX - b.left) / b.width)), Math.min(1, Math.max(0, (ev.clientY - b.top) / b.height))];
  };
  if (S.mat.punti) {
    // Un clic, non un trascinamento: il quadrato attorno al clic e' il campione.
    tela.addEventListener("pointerup", (ev) => {
      if (ev.button !== 0) return;
      aggiungiZona(img, quadratoAttorno(punto(ev), img));
    });
    return tela;
  }
  tela.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    ev.preventDefault();
    tela.setPointerCapture(ev.pointerId);
    tratto = [punto(ev)];
  });
  tela.addEventListener("pointermove", (ev) => {
    if (!tratto || !tela.hasPointerCapture(ev.pointerId)) return;
    const p = punto(ev), ultimo = tratto[tratto.length - 1];
    if (Math.hypot(p[0] - ultimo[0], p[1] - ultimo[1]) >= LAZO_PASSO_MINIMO) tratto.push(p);
    traccia.setAttribute("points", attributoPunti(tratto));
  });
  const chiudi = () => {
    if (!tratto) return;
    const t = tratto; tratto = null;
    traccia.setAttribute("points", "");
    if (t.length < 3) return;
    const xs = t.map((p) => p[0]), ys = t.map((p) => p[1]);
    if (Math.max(...xs) - Math.min(...xs) < AREA_MINIMA || Math.max(...ys) - Math.min(...ys) < AREA_MINIMA) return;
    aggiungiZona(img, t.map(([x, y]) => [Number(x.toFixed(4)), Number(y.toFixed(4))]));
  };
  tela.addEventListener("pointerup", chiudi);
  tela.addEventListener("pointercancel", () => { tratto = null; traccia.setAttribute("points", ""); });
  return tela;
}

function pannelloZone(massimo) {
  const testa = h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Materiali della vista",
    spiega("Con Punti clicchi su una superficie: il quadratino attorno al clic è il campione. Con Contorno disegni a mano libera, come il lazo di Photoshop, attorno a una superficie. Il pezzo parte come campione del materiale, insieme al testo e alla foto. Il modello cambia tutte le superfici che somigliano al campione: due materiali che nella vista sembrano uguali possono confondersi.")));
  const pieno = S.mat.zone.length >= massimo;
  const comando = S.mat.lazo || S.mat.punti
    ? h("button", { classe: "btn piccolo", onclick: () => { S.mat.lazo = false; S.mat.punti = false; render(); } }, "Fine selezione")
    : [h("button", { classe: "btn piccolo", disabled: pieno, title: "Un clic su una superficie: il quadratino attorno al clic è il campione.",
          onclick: () => { S.mat.punti = true; render(); } }, "+ Punti"),
       h("button", { classe: "btn piccolo", disabled: pieno, title: "Disegna il contorno di una superficie tenendo premuto.",
          onclick: () => { S.mat.lazo = true; render(); } }, "+ Contorno")];
  const righe = S.mat.zone.map((z, i) => {
    const diventa = h("input", { classe: "campo", id: `zona-diventa-${i}`, placeholder: "diventa…", "aria-label": `Materiale ${i + 1} diventa`, value: z.diventa });
    diventa.addEventListener("input", () => { z.diventa = diventa.value; S.secco = null; aggiornaComposto(); });
    const file = h("input", { type: "file", accept: "image/jpeg,image/png", hidden: true, onchange: (e) => riferimentoZona(i, e.target.files[0]) });
    const rif = z.riferimento
      ? h("span", { classe: "riga" }, h("img", { classe: "rif-materiale", src: `/file/riferimento/${enc(z.riferimento.nome)}`, alt: "Foto di riferimento" }),
          h("button", { classe: "btn link piccolo", onclick: () => { z.riferimento = null; materialiCambiati(); } }, "Togli"))
      : h("button", { classe: "btn piccolo", onclick: () => file.click() }, "+ Riferimento");
    return h("div", { classe: "materiale scelto" },
      h("img", { classe: "cubo", src: `/file/riferimento/${enc(z.campione.nome)}`, alt: `Campione del materiale ${i + 1}, ritagliato dalla vista` }),
      h("div", { classe: "nome-materiale" }, h("b", {}, `Materiale ${i + 1}`), h("span", { classe: "tenue piccolo" }, "dalla vista")),
      h("button", { classe: "btn link piccolo", onclick: () => togliZona(i) }, "Togli"),
      h("div", { classe: "diventa" }, diventa, rif, file));
  });
  const vuote = S.mat.zone.some((z) => !z.diventa.trim());
  return h("section", { classe: "pannello materiali", "aria-label": "Materiali della vista" }, testa,
    S.mat.punti
      ? h("p", { classe: "piccolo" }, h("b", {}, "Clicca sulla vista"), " su ogni materiale da cambiare: ogni clic diventa una riga qui sotto, col suo numero.")
      : S.mat.lazo
      ? h("p", { classe: "piccolo" }, h("b", {}, "Disegna sulla vista"), " il contorno di una superficie tenendo premuto. Quando lasci, il pezzo diventa una riga qui sotto.")
      : h("p", { classe: "piccolo tenue" }, S.mat.zone.length
          ? `${S.mat.zone.length} di massimo ${massimo} materiali scelti sulla vista.`
          : SUL_WEB ? "Indica sulla vista le superfici da cambiare: per ognuna scrivi cosa diventa."
          : "Questa vista non ha l'elenco dei materiali di Allplan: indica sulla vista le superfici da cambiare."),
    righe, h("div", { classe: "riga" }, comando),
    pieno ? h("p", { classe: "piccolo tenue" }, `Al massimo ${massimo} materiali per invio: gli altri li cambi con un passo dopo.`) : null,
    vuote ? h("p", { classe: "piccolo", stile: "color:var(--attenzione)" }, "Scrivi cosa diventa ogni materiale, o toglilo: senza testo non parte.") : null);
}

// Immagine di riferimento per lo stile: parte come seconda immagine, solo con
// i modelli che ne ricevono piu' di una. Il server la salva con la sua
// impronta; la ricetta tiene l'impronta, non l'immagine.
async function scegliRiferimento(file) {
  if (!file) return;
  try {
    S.riferimento = await post("/api/riferimenti", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name) });
    S.errore = null;
  } catch (e) { S.errore = e; }
  S.secco = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}
// «Stile da esempi»: gli esempi oltre al riferimento, che e' il primo.
// La prima passata gira su un workflow della Comfy Developer Platform: con la
// chiave Comfy propria sempre; coi crediti AIRENDER (PC e web) se il piano la
// comprende (funzioni.tieni_geometria, oggi solo Studio). Il server lo
// ricontrolla comunque prima di riservare.
function geometriaCoiCrediti() {
  const s = S.licenza && S.licenza.presente && S.licenza.saldo;
  return !!(s && s.funzioni && s.funzioni.tieni_geometria);
}
function geometriaPossibile() { return usaComfy() || geometriaCoiCrediti(); }
function perchéGeometriaSpenta() {
  const s = S.licenza && S.licenza.presente && S.licenza.saldo;
  if (s) return `Il piano ${nomePiano(s)} non comprende «Tieni la geometria»: è nel piano Studio, oppure con una chiave Comfy tua.`;
  return "Per sapere se il tuo piano comprende «Tieni la geometria» serve il saldo dal server AIRENDER: apri la scheda Licenza.";
}
function geometriaGenera() { return S.modo !== "contesto" && S.geometria && geometriaPossibile(); }

// I tre controlli di «Tieni la geometria», in parole semplici. Si possono
// spuntare insieme; almeno uno resta acceso.
const CONTROLLI_GEOMETRIA = [
  ["spigoli", "Spigoli", "Il consigliato, basta da solo quasi sempre.",
    "Spigoli (Canny): tiene contorni, finestre e porte esattamente dove sono nella vista. È il più preciso. Difetto: ricalca come righe anche retini, fughe e texture disegnate. Quando: viste esterne e interne con geometria pulita."],
  ["profondita", "Profondità", "Insieme agli Spigoli: da sola perde i tramezzi.",
    "Profondità (depth map): tiene cosa sta davanti e cosa dietro, i volumi e la prospettiva, non i dettagli. Lascia al render più libertà sulle superfici. Quando: interni, masterplan, studi di massa, o insieme agli Spigoli per tenere anche le distanze."],
  ["linee", "Linee dritte", "Se gli Spigoli ricalcano troppo.",
    "Linee dritte (M-LSD): tiene solo i segmenti dritti di muri, solai e serramenti; ignora texture, vegetazione e oggetti curvi. Quando: prospetti con molti retini o alberi, dove gli Spigoli copierebbero anche quelli."],
];

function pannelloGeometria() {
  const possibile = geometriaPossibile();
  const spunta = h("input", { type: "checkbox", id: "tieni-geometria", checked: S.geometria && possibile, disabled: !possibile,
    onchange: async (e) => { S.geometria = e.target.checked; S.secco = null; await caricaDestinazione(); aggiornaComposto(true); render(); } });
  const controlli = S.geometria && possibile ? h("div", { classe: "controlli-geometria" },
    ...CONTROLLI_GEOMETRIA.map(([chiave, nome, breve, testo]) => {
      const acceso = S.controlliGeometria.includes(chiave);
      const ultimo = acceso && S.controlliGeometria.length === 1;
      const id = `geometria-${chiave}`;
      return h("label", { classe: "riga-spunta controllo", for: id, title: ultimo ? "Ne serve almeno uno." : "" },
        h("input", { type: "checkbox", id, checked: acceso, disabled: ultimo,
          onchange: (e) => {
            const scelti = new Set(S.controlliGeometria);
            if (e.target.checked) scelti.add(chiave); else scelti.delete(chiave);
            S.controlliGeometria = CONTROLLI_GEOMETRIA.map(([c]) => c).filter((c) => scelti.has(c));
            S.secco = null; render();
          } }),
        h("span", {}, h("b", {}, nome), " ", spiega(testo), " ", h("span", { classe: "tenue" }, breve)));
    }),
    nota("Più controlli insieme si dividono la stessa forza: non irrigidiscono il render, lo guidano in più modi. Il costo non cambia.",
      "Vale in Genera, sulla vista Allplan, anche con più varianti per invio. I passi dopo (Cambia, Ritocca, Variante) oggi non la usano: la tenuta di quei passi la dice la % di spigoli, sempre misurata contro la vista.")) : null;
  return h("div", { classe: possibile ? "geometria" : "geometria spento" },
    h("label", { classe: "riga-spunta", for: "tieni-geometria" }, spunta,
      h("b", {}, S.scelte && S.scelte.scena === "pianta" ? "Tieni la geometria · muri e aperture" : "Tieni la geometria")),
    possibile ? null : h("p", { classe: "tenue piccolo" }, perchéGeometriaSpenta()),
    h("p", { classe: "tenue piccolo" },
      "Prima la vista va a un modello aperto con un ControlNet (un pezzo che lo obbliga a seguire la vista: spigoli, profondità o linee dritte, quelli che spunti); ",
      "poi il suo render va al modello scelto, che cura luce e materiali senza spostare le linee. Due invii, due costi."),
    controlli);
}

function esempiGenera() { return S.modo === "contesto" || !S.riferimento ? [] : S.esempi.map((r) => r.nome); }

async function aggiungiEsempio(file) {
  if (!file) return;
  try { S.esempi.push(await caricaInserto(file)); S.errore = null; } catch (e) { S.errore = e; }
  S.secco = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}

async function togliEsempio(i) {
  S.esempi.splice(i, 1); S.secco = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}

async function togliRiferimento() {
  // Il secondo esempio, se c'e', diventa il riferimento: gli esempi restano.
  if (S.esempi.length) { S.riferimento = S.esempi.shift(); S.secco = null; await caricaDestinazione(); aggiornaComposto(true); render(); return; }
  S.riferimento = null; S.secco = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}
function pannelloRiferimento() {
  const m = modelloScelto();
  const accetta = !!(m && m.piu_immagini);
  const titolo = h("span", { classe: "etichetta" }, "Immagine di riferimento per lo stile");
  if (S.modo === "contesto") {
    return [titolo, h("p", { classe: "tenue piccolo" },
      "Con «Fotoinserimento» il riferimento non parte: le due immagini sono già il contesto e la vista, e la luce la dà il contesto.")];
  }
  if (!accetta) {
    return [titolo,
      h("p", { classe: "tenue piccolo" }, `${m ? m.nome : "Questo modello"} riceve una sola immagine per invio: il riferimento si usa con Nano Banana 2.`),
      S.riferimento ? h("div", { classe: "riga" },
        h("span", { classe: "piccolo" }, `Caricato: ${S.riferimento.da || S.riferimento.nome}, non partirebbe.`),
        h("button", { classe: "btn", onclick: togliRiferimento }, "Togli")) : null];
  }
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", "aria-label": "Carica un'immagine di riferimento per lo stile" });
  file.addEventListener("change", () => scegliRiferimento(file.files && file.files[0]));
  if (!S.riferimento) {
    return [titolo,
      nota("Solo colori, luce e materiali.", "Una foto da cui prendere solo colori, luce e materiali, non la forma. Parte come seconda immagine, insieme alla vista. JPEG o PNG."),
      file];
  }
  const r = S.riferimento;
  const massimo = S.catalogo.esempi_stile_massimi || 4;
  const tutti = [r, ...S.esempi];
  const altro = h("input", { type: "file", accept: "image/png,image/jpeg", hidden: true, "aria-label": "Aggiungi un altro render d'esempio per lo stile" });
  altro.addEventListener("change", () => aggiungiEsempio(altro.files && altro.files[0]));
  if (tutti.length === 1) {
    return [titolo,
      h("div", { classe: "riga" },
        h("img", { src: `/file/riferimento/${enc(r.nome)}`, alt: "Immagine di riferimento per lo stile", stile: "max-width:96px;max-height:72px;border-radius:4px" }),
        h("span", { classe: "piccolo" }, `${r.da || r.nome} · ${r.larghezza} × ${r.altezza}`),
        h("button", { classe: "btn", onclick: togliRiferimento }, "Togli")),
      nota("Solo palette, luce e materiali.", "Il modello prende solo palette, luce e materiali. La ricetta salva l'impronta del file, non l'immagine."),
      h("span", {}, altro, h("button", { classe: "btn link piccolo", onclick: () => altro.click() }, "+ Un altro esempio (Stile da esempi)"))];
  }
  return [h("span", { classe: "etichetta" }, "Stile da esempi",
      spiega(`Da 2 a ${massimo} render con lo stile che vuoi: il modello prende quello che hanno in comune (colori, luce, materiali, taglio fotografico), non gli edifici. Con 15 o più immagini dello stesso stile arriverà «Crea il mio stile».`)),
    h("div", { classe: "griglia-rif" },
      tutti.map((x, i) => h("div", { classe: "rif" },
        h("img", { src: `/file/riferimento/${enc(x.nome)}`, alt: `Esempio ${i + 1}: ${x.da || x.nome}` }),
        h("span", { classe: "piccolo" }, h("b", {}, `Esempio ${i + 1}`)),
        h("button", { classe: "togli", "aria-label": `Togli l'esempio ${i + 1}`, onclick: () => (i === 0 ? togliRiferimento() : togliEsempio(i - 1)) }, "×"))),
      tutti.length < massimo ? h("button", { classe: "rif rif-nuovo", onclick: () => altro.click() }, `+ Esempio ${tutti.length + 1}`) : null,
      altro),
    h("p", { classe: "tenue piccolo" }, `Partono ${tutti.length} esempi dopo la vista. Testo per il modello scelto, non ancora provato.`)];
}

// Rif. di oggetti e persone: fino a INSERTI_MASSIMO immagini da mettere
// nell'immagine di partenza, citate nel testo come «Rif. 1», «Rif. 2».
// Partono dopo tutte le altre immagini; il server le salva con la loro
// impronta, come il riferimento per lo stile. Solo con i modelli che
// ricevono piu' di un'immagine: con gli altri il server non manda.
function insertiGenera() { return S.modo === "contesto" ? [] : S.inserti.map((r) => r.nome); }

async function caricaInserto(file) {
  return post("/api/riferimenti", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name) });
}

function miniaturaRif(r, numero, togli) {
  return h("div", { classe: "rif" },
    h("img", { src: `/file/riferimento/${enc(r.nome)}`, alt: `Rif. ${numero}: ${r.da || r.nome}` }),
    h("span", { classe: "piccolo" }, h("b", {}, `Rif. ${numero}`)),
    togli ? h("button", { classe: "togli", "aria-label": `Togli il Rif. ${numero}`, onclick: togli }, "×") : null);
}

function pannelloInserti(lista, modello, dove, cambiato, bloccato) {
  const massimo = S.catalogo.inserti_massimi || 4;
  const accetta = !!(modello && modello.piu_immagini);
  const titolo = h("span", { classe: "etichetta" }, "Oggetti e persone da inserire",
    spiega(`Una foto per ogni cosa da mettere nell'immagine: un arredo, una persona, un'auto, una lampada. Nel testo la citi come «Rif. 1», «Rif. 2»: per esempio «metti la poltrona del Rif. 1 accanto alla finestra». Al massimo ${massimo}.`));
  const errore = h("div", {});
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", hidden: true, "aria-label": "Carica la foto di un oggetto o di una persona" });
  file.addEventListener("change", async () => {
    const f = file.files && file.files[0];
    if (!f) return;
    try { lista.push(await caricaInserto(f)); } catch (e) { errore.replaceChildren(avviso("errore", e.fatto, e.cosa_fare)); return; }
    await cambiato();
  });
  const aggiungi = lista.length < massimo && !bloccato
    ? h("button", { classe: "rif rif-nuovo", onclick: () => file.click(), disabled: !accetta || null,
      title: accetta ? "Aggiungi la foto di un oggetto o di una persona" : "" }, `+ Rif. ${lista.length + 1}`) : null;
  return h("div", { classe: "inserti", "aria-label": `Oggetti e persone da inserire · ${dove}` },
    titolo,
    h("div", { classe: "griglia-rif" },
      lista.map((r, i) => miniaturaRif(r, i + 1, bloccato ? null : async () => { lista.splice(i, 1); await cambiato(); })),
      aggiungi, file),
    !accetta ? h("p", { classe: "piccolo", stile: "color:var(--attenzione)" },
      `${modello ? modello.nome : "Questo modello"} riceve una sola immagine per invio: i Rif. si usano con Nano Banana 2.`
      + (lista.length ? ` Con ${lista.length === 1 ? "questo Rif." : "questi Rif."} non manda.` : ""))
      : lista.length ? h("p", { classe: "tenue piccolo" },
        `${lista.length === 1 ? "Il Rif. parte" : `I ${lista.length} Rif. partono`} dopo le altre immagini. Citali nel testo: «Rif. 1»${lista.length > 1 ? ", «Rif. 2»" : ""}. Testo per il modello scelto, non ancora provato.`)
      : null,
    errore);
}

// Inserisci nel contesto: il fotoinserimento. L'utente porta l'immagine del
// luogo (screenshot satellitare, ortofoto, foto da drone), ci disegna un
// rettangolo dove va l'edificio e sceglie l'inquadratura. Partono due
// immagini: prima il contesto con l'area in magenta, poi la vista. Lo Studio
// non scarica immagini da mappe.
function contestoPerServer() {
  const c = S.contesto;
  if (!c || !c.area) return null;
  return { nome: c.nome, area: c.area, inquadratura: c.inquadratura, pulisci_mappa: c.pulisci, luogo: c.luogo };
}
async function dopoCambioContesto() {
  S.secco = null; S.promptAMano = null;
  await caricaDestinazione();
  aggiornaComposto(true);
  render();
}
async function scegliContesto(file) {
  if (!file) return;
  try {
    const caricato = await post("/api/contesti", file, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(file.name) });
    S.contesto = { ...caricato, area: null, inquadratura: S.catalogo.contesto.predefinita, pulisci: false, luogo: "",
                   ...(S.contesto ? { inquadratura: S.contesto.inquadratura, pulisci: S.contesto.pulisci, luogo: S.contesto.luogo } : {}) };
    S.errore = null;
  } catch (e) { S.errore = e; }
  await dopoCambioContesto();
}
async function togliContesto() { S.contesto = null; await dopoCambioContesto(); }
function cambiaContesto(campo, valore) { S.contesto = { ...S.contesto, [campo]: valore }; dopoCambioContesto(); }

function telaContesto() {
  const c = S.contesto;
  const img = h("img", { src: `/file/contesto/${enc(c.nome)}`, alt: "Immagine del contesto", draggable: "false" });
  const contenitore = h("div");
  const rett = c.area ? `<polygon class="contorno-area" points="${attributoPunti(puntiSvg({ forma: "rettangolo", punti: c.area }))}"></polygon>` : "";
  contenitore.innerHTML = `<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" class="aree-svg" aria-hidden="true">${rett}<polyline class="contorno-area in-corso" points=""></polyline></svg>`;
  const disegno = contenitore.firstElementChild;
  const traccia = disegno.querySelector("polyline");
  const numero = c.area ? h("span", { classe: "numero-area", stile: `left:${c.area[0][0] * 100}%;top:${c.area[0][1] * 100}%`, "aria-hidden": "true" }, "1") : null;
  const tela = h("div", { classe: "tela-ritocco tela-contesto", "data-strumento": "rettangolo" }, img, disegno, numero);
  let inizio = null;
  const punto = (ev) => {
    const b = img.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (ev.clientX - b.left) / b.width)), Math.min(1, Math.max(0, (ev.clientY - b.top) / b.height))];
  };
  tela.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    ev.preventDefault();
    tela.setPointerCapture(ev.pointerId);
    inizio = punto(ev);
  });
  tela.addEventListener("pointermove", (ev) => {
    if (!inizio || !tela.hasPointerCapture(ev.pointerId)) return;
    traccia.setAttribute("points", attributoPunti(puntiSvg({ forma: "rettangolo", punti: [inizio, punto(ev)] })) + " " + attributoPunti([inizio]));
  });
  tela.addEventListener("pointerup", (ev) => {
    if (!inizio) return;
    const [ax, ay] = inizio, [bx, by] = punto(ev);
    inizio = null;
    traccia.setAttribute("points", "");
    if (Math.abs(bx - ax) < AREA_MINIMA || Math.abs(by - ay) < AREA_MINIMA) return;
    const area = [[Math.min(ax, bx), Math.min(ay, by)], [Math.max(ax, bx), Math.max(ay, by)]]
      .map(([x, y]) => [Number(x.toFixed(4)), Number(y.toFixed(4))]);
    cambiaContesto("area", area);
  });
  tela.addEventListener("pointercancel", () => { inizio = null; traccia.setAttribute("points", ""); });
  return tela;
}

// Il modo di Genera: render della vista o inserimento in una foto del luogo.
async function cambiaModo(modo) {
  if (modo === S.modo) return;
  if (modo === "vista") { S.contestoTenuto = S.contesto; S.contesto = null; }
  else { S.contesto = S.contestoTenuto; S.contestoTenuto = null; }
  S.modo = modo;
  await dopoCambioContesto();
}

function sceltaModo() {
  return h("div", { classe: "scelta-modo", role: "group", "aria-label": "Cosa vuoi fare" },
    [["vista", "Render della vista", "La vista di Allplan diventa una foto, con lo stile che scegli."],
     ["contesto", "Fotoinserimento", "Quello che hai in Allplan, edificio o arredo, dentro una foto vera: dall'alto, a volo d'uccello o da terra."]]
      .map(([id, nome, spiega]) => h("button", { classe: "modo", "aria-pressed": String(S.modo === id), onclick: () => cambiaModo(id) },
        h("b", {}, nome), h("span", { classe: "tenue piccolo" }, spiega))));
}

function passo(numero, titolo, fatto, ...corpo) {
  return h("div", { classe: "passo-contesto" + (fatto ? " fatto" : "") },
    h("h3", {}, h("span", { classe: "numero-passo", "aria-hidden": "true" }, fatto ? "✓" : String(numero)), `${numero} · ${titolo}`),
    ...corpo);
}

// Che vista catturare in Allplan per ogni inquadratura: la camera della
// vista deve somigliare a quella della foto, il modello non ruota l'edificio
// di 90 gradi.
const VISTA_PER_INQUADRATURA = {
  zenitale: "In Allplan cattura la pianta vista dall'alto, shaded con le ombre.",
  volo: "In Allplan cattura una vista dall'alto e di sbieco, con lo stesso angolo della foto.",
  terra: "In Allplan cattura una prospettiva ad altezza d'occhio (circa 1,6 m), girata come la foto.",
};

function sezioneContesto() {
  const c = S.contesto;
  const cat = S.catalogo.contesto;
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", "aria-label": "Carica la foto" });
  file.addEventListener("change", () => scegliContesto(file.files && file.files[0]));

  // 1 · la foto del luogo, grande: e' dove si disegna.
  const uno = c
    ? passo(1, "Segna dove va", !!c.area,
        h("p", { classe: c.area ? "tenue piccolo" : "piccolo invito" }, c.area
          ? "Fatto. Per cambiare l'area trascina di nuovo. Fuori dal rettangolo la foto deve restare com'è."
          : "Trascina sulla foto un rettangolo, da un angolo all'altro, dove deve stare quello che viene da Allplan."),
        telaContesto(),
        h("p", { classe: "tenue piccolo" }, `${c.da || c.nome} · ${c.larghezza} × ${c.altezza} · `,
          h("label", { classe: "link-file" }, "cambia foto", h("span", { classe: "nascosto" }, file)),
          " · ", h("button", { classe: "link-file come-link", onclick: togliContesto }, "togli")))
    : passo(1, "Carica la foto", false,
        h("label", { classe: "carica-luogo" },
          h("b", {}, "Scegli la foto"),
          h("span", { classe: "tenue piccolo" }, "Uno screenshot di Google Earth, un'ortofoto, una foto da drone o una foto da terra, anche uno Street View. JPEG o PNG."),
          h("span", { classe: "nascosto" }, file)),
        nota("La foto la porti tu.", "AIRENDER non scarica mappe: la foto la porti tu."));

  // 2 · com'e' stata scattata la foto.
  const inq = c ? c.inquadratura : cat.predefinita;
  const due = passo(2, "Com'è stata scattata la foto", !!c,
    h("div", { classe: "switch", role: "group", "aria-label": "Com'è stata scattata la foto" },
      cat.inquadrature.map((i) => h("button", {
        classe: "seg", "aria-pressed": String(inq === i.id), disabled: !c,
        onclick: () => { const cambi = { inquadratura: i.id }; if (i.id === "terra") cambi.pulisci = false; S.contesto = { ...S.contesto, ...cambi }; dopoCambioContesto(); },
      }, i.nome))),
    h("p", { classe: "tenue piccolo" }, {
      zenitale: "Dall'alto, in pianta: Google Earth o un'ortofoto.",
      volo: "Dall'alto e di sbieco: Google Earth inclinato o un drone.",
      terra: "Da terra, ad altezza d'occhio: una foto o uno Street View.",
    }[inq]));

  // 3 · l'edificio: la vista di Allplan, con la camera giusta.
  const tre = passo(3, "Da Allplan", !!(S.vista && S.descrizione && S.descrizione.idonea),
    S.vista
      ? h("img", { classe: "miniatura-vista", src: `/file/vista/${enc(S.vista)}`, alt: `Vista di Allplan ${S.vista}` })
      : h("p", { classe: "piccolo" }, "Nessuna vista ancora: catturala dalla palette."),
    h("p", { classe: "piccolo" }, VISTA_PER_INQUADRATURA[inq]),
    h("div", { classe: "riga" },
      h("button", { classe: "btn", onclick: () => { S.mostraViste = !S.mostraViste; render(); }, "aria-expanded": String(S.mostraViste) }, "Usa un'altra vista…")),
    S.mostraViste ? pannelloViste() : null);

  return h("section", { classe: "pannello sezione-contesto", "aria-label": "Fotoinserimento" },
    h("div", { classe: "griglia-contesto" }, uno, h("div", { classe: "passi-destra" }, due, tre)));
}

function colonnaContesto() {
  const c = S.contesto;
  const cat = S.catalogo.contesto;
  const luogo = h("input", { type: "text", id: "luogo-contesto", maxlength: String(cat.luogo_massimo), "aria-label": "Dove si trova: indirizzo o coordinate",
    placeholder: "es. Via Statale 467, Casalgrande (RE) · 44.5893, 10.7381", disabled: !c });
  luogo.value = (c && c.luogo) || "";
  let attesaLuogo = null;
  luogo.addEventListener("input", () => {
    S.contesto.luogo = luogo.value; S.secco = null;
    clearTimeout(attesaLuogo); attesaLuogo = setTimeout(() => aggiornaComposto(true), 300);
  });
  const materiali = h("textarea", { id: "materiali", rows: "3", "aria-label": "Materiali a parole",
    placeholder: "es. intonaco bianco, infissi in rovere scuro, zoccolo in pietra grigia" });
  materiali.value = S.scelte.materiali || "";
  materiali.addEventListener("input", () => { S.scelte.materiali = materiali.value; aggiornaComposto(); });
  const pulisci = h("input", { type: "checkbox", id: "pulisci-contesto", checked: !!(c && c.pulisci), disabled: !c });
  pulisci.addEventListener("change", () => cambiaContesto("pulisci", pulisci.checked));
  const terra = c && c.inquadratura === "terra";
  return h("div", { classe: "colonna-stile" },
    h("section", { classe: "pannello", "aria-label": "Facoltativo" },
      h("h2", {}, "Facoltativo"),
      h("span", { classe: "etichetta" }, "Materiali a parole", spiega("La vista di Allplan è grigia: senza materiali il modello li sceglie da solo. Scrivili come vuoi, anche in italiano.")),
      materiali,
      h("span", { classe: "etichetta" }, "Dove si trova", spiega("Indirizzo o coordinate: aiutano il modello a capire il posto. Entrano nel prompt come li scrivi.")), luogo,
      terra ? null : h("label", { classe: "riga" }, pulisci,
        h("span", { classe: "piccolo" }, "È uno screenshot con scritte e icone (Google Earth, Maps): toglile e rendilo una foto aerea")),
      c && c.pulisci ? h("p", { classe: "piccolo", stile: "color:var(--attenzione)" }, "Così cambia anche fuori dall'area: la misura «fuori dall'area» non si fa.") : null),
    nota("Luce e cielo dalla foto.", "Qui preset e stile non servono: luce, cielo e colore li prende dalla foto del luogo. Per scegliere lo stile torna a «Render della vista»."));
}

function motivoGeneraSpento() {
  if (!S.vista) return "Serve una vista: catturala dalla palette o scegline una con Usa un'altra vista…";
  if (S.descrizione && !giudizioVista().idonea) return "La vista non è adatta: guarda il motivo sopra.";
  if (S.lavoroAttivo) return "Un lavoro è già in corso: aspetta che finisca o annullalo.";
  const m = modelloScelto();
  if (m && !m.verificato) return "Lo schema di questo modello non è verificato: l'invio si fermerebbe prima di partire.";
  if (!S.destinazione) return "Sto leggendo la destinazione.";
  if (S.modo === "contesto" && !S.contesto) return "Passo 1: carica la foto del luogo.";
  if (S.contesto && !S.contesto.area) return "Passo 1: trascina sulla foto il rettangolo dove va l'edificio.";
  if (S.destinazione.contesto_non_accettato) return S.destinazione.contesto_non_accettato;
  if (S.modo !== "contesto" && S.destinazione.riferimento_non_accettato) return S.destinazione.riferimento_non_accettato;
  if (S.destinazione.geometria && S.destinazione.geometria.errore) return S.destinazione.geometria.errore;
  return null;
}

function pannelloInvio() {
  const d = S.destinazione;
  const spento = motivoGeneraSpento();
  const blocco = h("section", { classe: "pannello", "aria-label": "Invio" });
  if (d && d.geometria) {
    const g = d.geometria;
    blocco.append(
      h("p", { classe: "destinazione" }, "Prima passata: la vista va a ",
        g.destinazione ? h("b", {}, g.destinazione) : "—", "."),
      h("p", { classe: "destinazione" }, "Costo della prima passata: ", h("b", {}, g.costo)));
    if (g.errore) blocco.append(avviso("errore", g.errore, `${g.cosa_fare} Oppure togli la spunta «Tieni la geometria».`));
  }
  if (d) {
    blocco.append(
      h("p", { classe: "destinazione" }, d.geometria ? "Poi il suo render va a " : "La vista va a ", h("b", {}, d.destinazione),
        ` (${d.fornitore}, ${d.modello_nome})`, d.senza_ripiego ? ", senza ripiego su altri servizi." : "."),
      h("p", { classe: "destinazione" }, "Costo: ", h("b", {}, d.costo)));
    if (d.cosa_manca) blocco.append(avviso("errore", `Attenzione: ${d.cosa_manca}`, "Scegli Nano Banana 2, il modello predefinito."));
    blocco.append(h("p", { classe: "destinazione" }, d.cosa_parte));
  }
  if (!S.studio.coda_attiva) {
    blocco.append(avviso("attenzione", "La coda dei lavori non sta girando: un lavoro resterebbe in attesa.",
      "Chiudi e riapri lo Studio, che la fa partire."));
  }
  blocco.append(h("div", { classe: "azioni" },
    h("button", { classe: "btn", onclick: provaASecco, disabled: !S.vista || (S.modo === "contesto" && !contestoPerServer()) }, "Prova a secco"),
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
      saldoFinito(e.fatto) ? h("div", { classe: "riga" }, pulsanteRicarica(), h("a", { classe: "btn link", href: "#licenza" }, "Vedi il saldo")) : null,
      h("span", { classe: "piccolo tenue" }, `Le scelte sono rimaste: ${e.preset_nome} · ${e.modello_nome}. Puoi rifarlo da Risultato con la stessa ricetta.`)));
  }
  if (S.modo === "contesto") {
    return [h("h1", { classe: "nascosto" }, "Genera"), ...sopra, sceltaModo(), sezioneContesto(),
      h("div", { classe: "colonne" }, colonnaContesto(), colonnaInvio())];
  }
  return [h("h1", { classe: "nascosto" }, "Genera"), ...sopra, sceltaModo(), sezioneVista(), h("div", { classe: "colonne" }, colonnaStile(), colonnaInvio())];
}

function disegnaComposto() {
  const r = document.getElementById("riassunto");
  if (r && S.composto && !(S.modo === "contesto" && !contestoPerServer())) r.textContent = S.composto.riassunto;
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

// Nell'elenco dei render: con quali controlli ha tenuto la geometria e la
// quota di spigoli ritrovati, per confrontare i render della stessa vista.
function tenutaBreve(l) {
  const parti = [];
  if (l.controlli_geometria) parti.push(`Tieni: ${l.controlli_geometria}`);
  const q = l.tenuta && l.tenuta.spigoli;
  parti.push(typeof q === "number" ? `Spigoli ${percento(q)}` : "Spigoli: non misurati");
  return parti.join(" · ");
}

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
    // L'anteprima di Regola e' piu' piccola del render: la misura vera la porta data-larghezza.
    const lb = Number(imgB.dataset.larghezza) || imgB.naturalWidth, ab = Number(imgB.dataset.altezza) || imgB.naturalHeight;
    palco.style.aspectRatio = `${lb} / ${ab}`;
    const ra = imgA.naturalWidth / imgA.naturalHeight, rb = lb / ab;
    const scarto = Math.abs(ra - rb) / rb;
    nota.textContent = scarto < 0.005
      ? `${nomeA} riportata a ${lb}×${ab}, la misura del render: stesse proporzioni, gli spigoli si sovrappongono.`
      : `${nomeA} (${imgA.naturalWidth}×${imgA.naturalHeight}) stirata a ${lb}×${ab} per sovrapporla: le proporzioni differiscono del ${(scarto * 100).toFixed(1).replace(".", ",")}%, gli spigoli possono non coincidere per questo.`;
  };
  imgA.addEventListener("load", proporzioni);
  imgB.addEventListener("load", proporzioni);
  return { palco, nota };
}

function confronto(l) {
  const r = S.risultato;
  const altro = r.confronto !== "vista" && r.lavori.find((x) => x.identificativo === r.confronto && x.render);
  const srcA = altro ? `/file/render/${altro.identificativo}` : `/file/vista/${enc(S.vista)}`;
  const nomeA = altro ? altro.modello_nome : nomePrima();
  const srcB = srcRender(l);
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
  segnaRegolato(palco, srcB, l);
  return h("div", { classe: "palco" },
    h("div", { classe: "riga tra" }, h("h1", { title: sottotitolo }, l.immaginata ? "La foto dal punto di vista" : "È ancora il tuo edificio?"), modi),
    l.immaginata ? avvisoImmaginata() : null,
    regolaAttiva(l) ? h("p", { classe: "piccolo", role: "status" },
      h("span", { classe: "regola-gratis" }, "Con le regolazioni"), " · le vedi qui, il file le prende quando esporti. Tieni premuto «Senza regolazioni» per vedere com'era.") : null,
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Confronta con"), h("div", { stile: "min-width:260px" }, scegliA)),
    l.importata && !altro ? h("p", { classe: "piccolo", role: "status" },
      "Questa è l'immagine che hai caricato: prima e dopo sono uguali. Il confronto si accende col primo Cambia, Ritocca o Popola, che arriva qui accanto già scelto.") : null,
    palco,
    r.modo === "scorri" ? h("div", { classe: "riga tra" },
      h("span", { classe: "tenue piccolo" }, "Trascina la linea, oppure tasti ← → (con Maiusc il passo è più lungo)"),
      h("span", { classe: "mono", id: "valore-linea" }, `${Math.round(r.x)}%`)) : null,
    r.modo === "scorri" ? nota : null);
}

function elencoRender() {
  const r = S.risultato;
  return h("section", { classe: "pannello", "aria-label": "Render di questa vista" },
    h("span", { classe: "etichetta" }, "Render di questa vista", spiega("Per un A/B fra modelli: genera la stessa vista con un altro modello, poi scegli «Confronta con».")),
    r.lavori.length ? h("div", { classe: "elenco-render" }, r.lavori.map((l) => h("button", {
      "aria-current": String(l.identificativo === r.scelto),
      disabled: l.attivo,
      onclick: async () => { r.scelto = l.identificativo; r.rifai = false; r.esportato = null; if (r.confronto === l.identificativo) r.confronto = "vista"; await caricaRicetta(); render(); },
    },
    l.render ? h("img", { src: `/file/render/${l.identificativo}`, alt: "" }) : h("span", { classe: "segnaposto", stile: "width:64px;height:40px" }),
    h("span", {}, nomeRender(l), h("span", { classe: "stato-lavoro", stile: "display:block" }, l.stato),
      l.render ? h("span", { classe: "tenue piccolo", stile: "display:block" }, tenutaBreve(l)) : null)))) : h("p", { classe: "tenue" }, "Nessun render da questa vista."));
}

// La misura degli spigoli: un numero solo se il motore l'ha fatta, altrimenti
// «Non misurata» e perché (regola 3). La spiegazione dice che è grezza.
const SPIEGA_SPIGOLI = "Quota degli spigoli della vista Allplan ritrovati nel render, sempre contro la vista. Misura grezza: ombre nuove, neve e vegetazione davanti contano come spigoli persi. Il giudizio resta tuo sul prima/dopo.";

function percento(q) { return `${Math.round(q * 100)}%`; }

function corpoTenuta(t, identificativo, nota) {
  const figli = [h("span", { classe: "etichetta" }, "Tenuta della geometria", nota ? null : spiega(SPIEGA_SPIGOLI))];
  if (!t) {
    figli.push(h("span", { classe: "misura" }, "Non misurata"), h("p", { classe: "tenue piccolo" }, "Si misura quando il render è pronto."));
  } else if (t.spigoli === null || t.spigoli === undefined) {
    figli.push(h("span", { classe: "misura" }, "Non misurata"), h("p", { classe: "tenue piccolo" }, `Perché: ${t.motivo}.`));
    if (t.da_misurare && identificativo) {
      figli.push(h("button", { classe: "btn", onclick: () => misuraOra(identificativo) }, "Misura ora"));
    }
  } else {
    figli.push(h("span", { classe: "misura" }, `Spigoli ritrovati: ${percento(t.spigoli)}`));
    if (t.avvisa) {
      figli.push(avviso("attenzione", `Sotto il ${percento(t.soglia)}: la geometria può essersi mossa.`, "Guardalo con la linea del prima/dopo."));
    }
  }
  if (nota) figli.push(h("p", { classe: "tenue piccolo" }, nota));
  return h("section", { classe: "pannello", "aria-label": "Tenuta della geometria" }, ...figli);
}

async function misuraOra(identificativo) {
  try {
    await post(`/api/lavori/${enc(identificativo)}/misura`, {});
    await caricaRender();
  } catch (e) { S.errore = e; }
  render();
}

// --- Riaggancia alla vista (2026-11-10) --------------------------------------
// Nano Banana non ha un ControlNet: a ogni passata le linee possono muoversi.
// Questa spunta, quando la % di spigoli scende, ripassa il render leggero nel
// ControlNet guidato dalla vista Allplan: le linee tornano al loro posto, luce
// e materiali restano in gran parte. Costa solo quando si usa.

function statoRiaggancia(l) {
  if (!S.riaggancio || S.riaggancio.per !== l.identificativo) {
    S.riaggancio = { per: l.identificativo, acceso: false, controlli: ["spigoli"], composto: null, errore: null };
  }
  return S.riaggancio;
}

async function componiRiaggancia(l) {
  const q = statoRiaggancia(l);
  try {
    q.composto = await post("/api/riaggancia/componi", { vista: S.vista, da: l.identificativo, controlli_geometria: q.controlli });
    q.errore = null;
  } catch (e) { q.composto = null; q.errore = e; }
  render();
}

async function applicaRiaggancia(l) {
  const q = statoRiaggancia(l);
  q.errore = null;
  try {
    const dest = await post("/api/riaggancia/componi", { vista: S.vista, da: l.identificativo, controlli_geometria: q.controlli });
    const risposta = await post("/api/riaggancia/invia", {
      vista: S.vista, da: l.identificativo, controlli_geometria: q.controlli, destinazione_mostrata: dest.destinazione,
    });
    S.riaggancio = null;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
    if (S.scheda === "risultato") await caricaRender();
  } catch (e) { q.errore = e; }
  render();
}

function pannelloRiaggancia(l) {
  if (!l || !l.render || l.modello === "caricata") return null;
  const q = statoRiaggancia(l);
  const possibile = geometriaPossibile();
  const t = l.tenuta;
  const bassa = t && typeof t.spigoli === "number" && t.avvisa;
  const spunta = h("input", { type: "checkbox", id: "riaggancia", checked: q.acceso && possibile, disabled: !possibile,
    onchange: (e) => { q.acceso = e.target.checked; q.composto = null; if (q.acceso) componiRiaggancia(l); else render(); } });
  const figli = [
    h("label", { classe: "riga-spunta", for: "riaggancia" }, spunta, h("b", {}, "Riaggancia alla vista"), " ",
      spiega("Nano Banana non ha un ControlNet: a ogni passata (Genera, Cambia, Ritocca, Variante) le linee possono spostarsi un po'. Riaggancia ripassa questo render, leggero, nel ControlNet guidato dalla vista Allplan: spigoli e aperture tornano al loro posto, luce e materiali restano in gran parte. Esce un passo nuovo; confrontalo col prima/dopo e con la % di spigoli.")),
    h("p", { classe: "tenue piccolo" }, bassa
      ? "La % di spigoli è bassa: questo render può essersi spostato dalla vista."
      : "Da usare quando la % di spigoli scende o il prima/dopo mostra linee spostate."),
  ];
  if (!possibile) figli.push(h("p", { classe: "tenue piccolo" }, perchéGeometriaSpenta()));
  if (q.acceso && possibile) {
    const c = q.composto;
    figli.push(h("div", { classe: "controlli-geometria" },
      ...CONTROLLI_GEOMETRIA.map(([chiave, nome, breve, testo]) => {
        const acceso = q.controlli.includes(chiave);
        const ultimo = acceso && q.controlli.length === 1;
        const id = `riaggancia-${chiave}`;
        return h("label", { classe: "riga-spunta controllo", for: id, title: ultimo ? "Ne serve almeno uno." : "" },
          h("input", { type: "checkbox", id, checked: acceso, disabled: ultimo,
            onchange: (e) => {
              const scelti = new Set(q.controlli);
              if (e.target.checked) scelti.add(chiave); else scelti.delete(chiave);
              q.controlli = CONTROLLI_GEOMETRIA.map(([k]) => k).filter((k) => scelti.has(k));
              componiRiaggancia(l);
            } }),
          h("span", {}, h("b", {}, nome), " ", spiega(testo), " ", h("span", { classe: "tenue" }, breve)));
      })));
    if (c && c.destinazione) {
      figli.push(h("p", { classe: "destinazione" }, "Vanno a ", h("b", {}, c.destinazione), `. Costo: ${c.costo}.`),
        h("p", { classe: "tenue piccolo" }, c.cosa_parte));
    }
    if (c && c.errore) figli.push(avviso("errore", c.errore, c.cosa_fare));
    if (q.errore) figli.push(avviso("errore", q.errore.fatto, q.errore.cosa_fare));
    figli.push(h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => applicaRiaggancia(l),
        disabled: !c || !c.destinazione || !!S.lavoroAttivo || null }, "Riaggancia"),
      S.lavoroAttivo ? h("span", { classe: "tenue piccolo" }, "Un lavoro è in corso: Riaggancia si accende quando finisce.") : null),
      nota("Scelta, non provata.", `Rifà il ${c ? c.quanto_rifa : "–"}% del render (valore scelto, non misurato). Nessun riaggancio è ancora stato fatto col workflow vero: il primo è la prova.`));
  }
  return h("section", { classe: "pannello", "aria-label": "Riaggancia alla vista" }, ...figli);
}

function tenuta(l) {
  return corpoTenuta(l ? l.tenuta : null, l ? l.identificativo : null);
}

function ricettaPannello(l) {
  const ric = S.risultato.ricetta;
  if (l.importata) {
    const righe = [["Che cos'è", "L'immagine che hai caricato, così com'è"], ["Servizio", "Nessun invio"], ["Costo", "nessuno: non è partito niente"]];
    if (ric && !ric.errore) righe.push(["File", h("span", { classe: "mono" }, ric.percorso_render)]);
    return h("section", { classe: "pannello", "aria-label": "Com'è stato fatto" },
      h("span", { classe: "etichetta" }, "Com'è stato fatto"),
      h("dl", { classe: "ricetta" }, righe.flatMap(([k, v]) => [h("dt", {}, k), h("dd", {}, v)])));
  }
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
      h("button", { classe: "btn", onclick: () => post("/api/apri-cartella", { quale: "render" }).catch((e) => { S.errore = e; render(); }) }, "Apri cartella"),
      l.render ? h("button", { classe: "btn", onclick: copia }, "Copia immagine") : null,
      l.render ? h("button", { classe: "btn", "aria-expanded": String(r.esporta), onclick: () => { r.esporta = !r.esporta; r.esportato = null; render(); } }, "Esporta per il cliente") : null),
    r.esporta && l.render ? pannelloEsporta(l) : null);
}

// Esporta per il cliente: JPEG, PNG o PSD con un livello per passaggio, nella
// cartella «esportati» accanto alle viste. Solo i pixel: niente prompt dentro.
const FORMATI_ESPORTA = [
  ["jpg", "JPEG", "Leggero, per mail e presentazioni."],
  ["png", "PNG", "Senza perdita, pesa di più."],
  ["psd", "PSD a livelli", "In basso la vista di Allplan, sopra un livello per ogni passo fino a questo render."],
];
async function esportaRender(l) {
  const r = S.risultato;
  r.esportando = true; r.esportato = null; render();
  const corpo = { formato: r.formato };
  if (regolaAttiva(l)) corpo.regola = regolaPerServer(regolaDi(l.identificativo));
  try { r.esportato = await post(`/api/lavori/${l.identificativo}/esporta`, corpo); S.errore = null; }
  catch (e) { S.errore = e; }
  r.esportando = false;
  render();
}
function pannelloEsporta(l) {
  const r = S.risultato;
  const e = r.esportato;
  return h("div", { classe: "sotto-gruppo" },
    pannelloRegola(l),
    h("span", { classe: "etichetta" }, "Formato"),
    h("div", { classe: "switch", role: "group", "aria-label": "Formato" },
      FORMATI_ESPORTA.map(([id, nome]) => h("button", {
        classe: "seg", "aria-pressed": String(r.formato === id), onclick: () => { r.formato = id; r.esportato = null; render(); },
      }, nome))),
    h("p", { classe: "tenue piccolo" }, FORMATI_ESPORTA.find((f) => f[0] === r.formato)[2],
      " Si salva nella cartella «esportati», accanto alle viste. Nel file ci sono solo le immagini: niente prompt, niente ricetta."),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => esportaRender(l), disabled: r.esportando }, r.esportando ? "Esporto…" : "Esporta"),
      e ? h("button", { classe: "btn", onclick: () => post("/api/apri-cartella", { quale: "esportati" }).catch((x) => { S.errore = x; render(); }) }, "Apri cartella") : null),
    e ? h("div", { classe: "avviso", role: "status" },
      h("b", {}, `Salvato: ${e.nome}`),
      h("span", {}, `${e.larghezza} × ${e.altezza} px · ${String(e.peso_mb).replace(".", ",")} MB` +
        (e.livelli ? ` · ${e.livelli.length} livelli: ${e.livelli.join(", ")}` : "")),
      h("span", {}, e.regolazioni && e.regolazioni.length
        ? `Con le regolazioni: ${e.regolazioni.join(", ")}.`
        : "Senza regolazioni: i pixel del render come sono.")) : null);
}

// --- Regola: luce e colore prima di esportare (DESIGN.md, Regola) -----------------
// Sei cursori e una curva, come in Photoshop. I numeri li calcola core/regola.py
// (sul PC o, nella web app, nel browser): qui c'e' solo l'interfaccia. Nessuna
// immagine parte, non costa crediti. Le regolazioni restano a ogni render
// finche' lo Studio e' aperto; il file le prende quando si esporta.

const CURVA_DIRITTA = [[0, 0], [255, 255]];
const LATO_CURVA = 200;           // px della curva a schermo (scelta di disegno)
const ATTESA_ANTEPRIMA_MS = 90;   // si chiede l'anteprima quando il cursore si ferma un attimo (scelta)
const regole = {};                 // identificativo -> { valori, curva, anteprima, ... }

function regolaDi(id) {
  if (!regole[id]) {
    const valori = {};
    for (const c of S.studio.regola.cursori) valori[c.id] = 0;
    regole[id] = { valori, curva: CURVA_DIRITTA.map((p) => p.slice()), anteprima: null, tabella: null,
                   larghezza: null, altezza: null, senza: false, errore: null, numero: 0, timer: null, curvaAperta: false };
  }
  return regole[id];
}
function curvaDiritta(curva) { return curva.length === 2 && curva.every(([x, y], i) => x === y && x === CURVA_DIRITTA[i][0]); }
function regolaNeutra(g) { return Object.values(g.valori).every((v) => v === 0) && curvaDiritta(g.curva); }
function regolaAttiva(l) { return !!(l && regole[l.identificativo] && !regolaNeutra(regole[l.identificativo])); }
function regolaPerServer(g) { return { ...g.valori, curva: curvaDiritta(g.curva) ? [] : g.curva }; }
function srcRender(l) {
  const g = regole[l.identificativo];
  return g && g.anteprima && !g.senza && !regolaNeutra(g) ? g.anteprima : `/file/render/${l.identificativo}`;
}
function segnaRegolato(nodo, src, l) {
  // Le immagini del render sul palco: si cambiano sul posto mentre si muovono i cursori.
  for (const img of nodo.querySelectorAll("img")) {
    if (img.getAttribute("src") !== src) continue;
    img.dataset.regolato = l.identificativo;
    const g = regole[l.identificativo];
    if (g && g.larghezza) { img.dataset.larghezza = g.larghezza; img.dataset.altezza = g.altezza; }
  }
}
function aggiornaPalcoRegola(l) {
  const src = srcRender(l);
  const g = regolaDi(l.identificativo);
  for (const img of document.querySelectorAll(`img[data-regolato="${l.identificativo}"]`)) {
    if (g.larghezza) { img.dataset.larghezza = g.larghezza; img.dataset.altezza = g.altezza; }
    if (img.getAttribute("src") !== src) img.setAttribute("src", src);
  }
}
function segno(v) { return v > 0 ? `+${v}` : v < 0 ? `−${-v}` : "0"; }

function chiediAnteprima(l) {
  const g = regolaDi(l.identificativo);
  clearTimeout(g.timer);
  if (regolaNeutra(g)) { g.errore = null; aggiornaPalcoRegola(l); return; }
  g.timer = setTimeout(async () => {
    const numero = ++g.numero;
    try {
      const esito = await post(`/api/lavori/${l.identificativo}/regola`, { regola: regolaPerServer(g) });
      if (numero !== g.numero) return;   // e' gia' partita una richiesta piu' nuova
      Object.assign(g, { anteprima: esito.immagine, tabella: esito.curva, larghezza: esito.larghezza, altezza: esito.altezza, errore: null });
      aggiornaPalcoRegola(l);
      disegnaCurva(l);
    } catch (e) {
      if (numero !== g.numero) return;
      g.errore = e; render();
    }
  }, ATTESA_ANTEPRIMA_MS);
}

function cambiaRegola(l) {
  chiediAnteprima(l);
  // Il palco dice «Con le regolazioni» appena qualcosa cambia; il ridisegno
  // aspetta che si lasci il cursore (vedi «trascinando»).
  render();
}

function cursoreRegola(l, c) {
  const g = regolaDi(l.identificativo);
  const m = S.studio.regola.massimo;
  const valore = h("output", { classe: "mono valore-regola", id: `regola-${c.id}-valore`, for: `regola-${c.id}` }, segno(g.valori[c.id]));
  const campo = h("input", { type: "range", id: `regola-${c.id}`, min: String(-m), max: String(m), step: "1", value: String(g.valori[c.id]),
    title: "Doppio clic: torna a 0" });
  campo.addEventListener("input", () => { g.valori[c.id] = Number(campo.value); valore.textContent = segno(g.valori[c.id]); chiediAnteprima(l); });
  campo.addEventListener("change", () => cambiaRegola(l));
  campo.addEventListener("dblclick", () => { g.valori[c.id] = 0; cambiaRegola(l); });
  return h("div", { classe: "cursore-regola" }, h("label", { for: `regola-${c.id}` }, c.nome), campo, valore);
}

// La curva: punti da 0 a 255 su un quadrato. Clic dove non c'e' un punto lo
// aggiunge, trascinare lo sposta, doppio clic (o Canc sul punto) lo toglie.
// Con la tastiera: Tab sul punto, frecce per spostarlo (Maiusc: di 10).
function curvaInSvg(v) { return LATO_CURVA - (v / 255) * LATO_CURVA; }
function disegnaCurva(l) {
  const svg = document.getElementById("curva-regola");
  if (!svg) return;
  const g = regolaDi(l.identificativo);
  const linea = svg.querySelector(".linea-curva");
  // Sotto i punti la curva vera, quella che ha calcolato il motore; mentre si
  // trascina, finche' non arriva, una spezzata fra i punti.
  const punti = g.tabella && !g.trascinoCurva
    ? g.tabella.map((y, x) => `${(x / 255) * LATO_CURVA},${curvaInSvg(y)}`)
    : [[0, g.curva[0][1]], ...g.curva, [255, g.curva[g.curva.length - 1][1]]].map(([x, y]) => `${(x / 255) * LATO_CURVA},${curvaInSvg(y)}`);
  linea.setAttribute("points", punti.join(" "));
  g.curva.forEach(([x, y], i) => {
    const p = svg.querySelector(`[data-punto="${i}"]`);
    if (p) {
      p.setAttribute("cx", (x / 255) * LATO_CURVA); p.setAttribute("cy", curvaInSvg(y));
      p.setAttribute("aria-label", `Punto ${i + 1}: entra ${x}, esce ${y}. Frecce per spostarlo, Canc per toglierlo.`);
    }
  });
}
function editorCurva(l) {
  const g = regolaDi(l.identificativo);
  // L'SVG si scrive come testo, come le aree di Ritocca: niente indirizzi dello spazio dei nomi.
  const griglia = [1, 2, 3].map((q) => { const t = (q / 4) * LATO_CURVA; return `<line x1="${t}" y1="0" x2="${t}" y2="${LATO_CURVA}" class="griglia-curva"/><line x1="0" y1="${t}" x2="${LATO_CURVA}" y2="${t}" class="griglia-curva"/>`; }).join("");
  const cerchi = g.curva.map(([x, y], i) => `<circle r="6" class="punto-curva" tabindex="0" data-punto="${i}" aria-label="Punto ${i + 1}: entra ${x}, esce ${y}. Frecce per spostarlo, Canc per toglierlo."/>`).join("");
  const contenitore = h("div", { classe: "contenitore-curva" });
  contenitore.innerHTML = `<svg id="curva-regola" viewBox="-6 -6 ${LATO_CURVA + 12} ${LATO_CURVA + 12}" role="group" aria-label="Curva dei toni: a sinistra i neri, a destra i bianchi"><rect x="0" y="0" width="${LATO_CURVA}" height="${LATO_CURVA}" class="fondo-curva"/>${griglia}<line x1="0" y1="${LATO_CURVA}" x2="${LATO_CURVA}" y2="0" class="diagonale-curva"/><polyline class="linea-curva" points=""/>${cerchi}</svg>`;
  const svg = contenitore.firstChild;
  const daPuntatore = (ev) => {
    const b = svg.getBoundingClientRect();
    const scala = (LATO_CURVA + 12) / b.width;
    const x = ((ev.clientX - b.left) * scala - 6) / LATO_CURVA * 255;
    const y = 255 - ((ev.clientY - b.top) * scala - 6) / LATO_CURVA * 255;
    return [Math.round(Math.max(0, Math.min(255, x))), Math.round(Math.max(0, Math.min(255, y)))];
  };
  // Un punto resta fra il vicino di sinistra e quello di destra: la curva non torna indietro.
  const sposta = (i, x, y) => {
    const minimo = i > 0 ? g.curva[i - 1][0] + 1 : 0;
    const massimo = i < g.curva.length - 1 ? g.curva[i + 1][0] - 1 : 255;
    g.curva[i] = [Math.max(minimo, Math.min(massimo, x)), Math.max(0, Math.min(255, y))];
  };
  const togli = (i) => { if (g.curva.length > 2) { g.curva.splice(i, 1); g.tabella = null; cambiaRegola(l); } };
  g.curva.forEach((_punto, i) => {
    const p = svg.querySelector(`[data-punto="${i}"]`);
    p.addEventListener("pointerdown", (ev) => {
      ev.stopPropagation(); p.setPointerCapture(ev.pointerId); g.trascinoCurva = true;
      const muovi = (e2) => { sposta(i, ...daPuntatore(e2)); disegnaCurva(l); chiediAnteprima(l); };
      const fine = () => { p.removeEventListener("pointermove", muovi); g.trascinoCurva = false; g.tabella = null; cambiaRegola(l); };
      p.addEventListener("pointermove", muovi);
      p.addEventListener("pointerup", fine, { once: true });
    });
    p.addEventListener("dblclick", (ev) => { ev.stopPropagation(); togli(i); });
    p.addEventListener("keydown", (ev) => {
      const passo = ev.shiftKey ? 10 : 1;
      const [px, py] = g.curva[i];
      const mosse = { ArrowLeft: [-passo, 0], ArrowRight: [passo, 0], ArrowUp: [0, passo], ArrowDown: [0, -passo] };
      if (mosse[ev.key]) { sposta(i, px + mosse[ev.key][0], py + mosse[ev.key][1]); g.tabella = null; disegnaCurva(l); chiediAnteprima(l); ev.preventDefault(); }
      if (ev.key === "Delete" || ev.key === "Backspace") { togli(i); ev.preventDefault(); }
    });
    p.addEventListener("keyup", (ev) => { if (ev.key.startsWith("Arrow")) cambiaRegola(l); });
  });
  svg.addEventListener("pointerdown", (ev) => {
    if (g.curva.length >= S.studio.regola.curva_punti) return;
    const [x, y] = daPuntatore(ev);
    if (g.curva.some(([px]) => px === x)) return;
    g.curva.push([x, y]); g.curva.sort((a, b) => a[0] - b[0]); g.tabella = null;
    cambiaRegola(l);
  });
  setTimeout(() => disegnaCurva(l), 0);
  return contenitore;
}

function pannelloRegola(l) {
  const g = regolaDi(l.identificativo);
  const neutra = regolaNeutra(g);
  const dove = SUL_WEB ? "in questo browser" : "su questo computer";
  const senza = h("button", { classe: "btn", disabled: neutra || null, "aria-pressed": String(g.senza),
    title: "Tieni premuto per vedere il render senza regolazioni" }, "Senza regolazioni");
  const premi = (su) => { g.senza = su; senza.setAttribute("aria-pressed", String(su)); aggiornaPalcoRegola(l); };
  senza.addEventListener("pointerdown", () => premi(true));
  for (const t of ["pointerup", "pointerleave", "pointercancel", "blur"]) senza.addEventListener(t, () => { if (g.senza) premi(false); });
  senza.addEventListener("keydown", (ev) => { if ((ev.key === " " || ev.key === "Enter") && !ev.repeat) { premi(true); ev.preventDefault(); } });
  senza.addEventListener("keyup", (ev) => { if (ev.key === " " || ev.key === "Enter") premi(false); });
  const azzera = () => {
    for (const k of Object.keys(g.valori)) g.valori[k] = 0;
    g.curva = CURVA_DIRITTA.map((p) => p.slice()); g.tabella = null; g.anteprima = null;
    cambiaRegola(l);
  };
  const punti = S.studio.regola.curva_punti;
  return h("div", { classe: "sotto-gruppo regola", role: "group", "aria-label": "Regola" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Regola"), h("span", { classe: "piccolo regola-gratis" }, `${dove} · gratis`)),
    S.studio.regola.cursori.map((c) => cursoreRegola(l, c)),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn", "aria-expanded": String(g.curvaAperta), onclick: () => { g.curvaAperta = !g.curvaAperta; render(); } },
        curvaDiritta(g.curva) ? "Curva" : `Curva (${g.curva.length} punti)`),
      senza,
      h("button", { classe: "btn", disabled: neutra || null, onclick: azzera }, "Azzera")),
    g.curvaAperta ? h("div", { classe: "editor-curva" }, editorCurva(l),
      h("p", { classe: "tenue piccolo" }, `Clic sulla curva per aggiungere un punto (al massimo ${punti}), trascinalo per spostarlo, doppio clic per toglierlo. A sinistra i neri, a destra i bianchi: un punto alzato schiarisce quei toni.`)) : null,
    g.errore ? avviso("errore", g.errore.fatto, g.errore.cosa_fare) : null,
    h("p", { classe: "tenue piccolo" },
      `Nessuna immagine parte: tutto resta ${dove}. Luci e Ombre cambiano i toni chiari e scuri su tutta l'immagine, come una curva: non schiariscono solo le zone in ombra. Doppio clic su un cursore lo riporta a 0.`));
}

// --- da questa immagine: Ritocca · Variante · Video (proposte 3 e 4) ---------------
// Sotto l'immagine, le stesse tre azioni per ogni render. Il risultato nasce
// accanto a questa immagine nello storico e, finito, e' gia'
// quello scelto. Il video chiede solo il movimento della camera: durata e
// risoluzione sono le prime della scheda Video, dove si cambiano.

function palcoConAzioni(l) {
  const palco = confronto(l);
  palco.append(barraAzioni(l));
  return palco;
}

function barraAzioni(l) {
  if (S.azioni.per !== l.identificativo) S.azioni = { per: l.identificativo, video: false, movimento: null, testo: "", mandato: false, errore: null, porta: null, finale: null, popola: null };
  const az = S.azioni;
  const pianta = scenaDi(l) === "pianta";
  const d = S.passi.dest[l.modello];
  const m = S.catalogo.modelli.find((x) => x.id === l.modello);
  const occupato = !!S.lavoroAttivo;
  const righe = [h("div", { classe: "azioni" },
    h("button", { classe: "btn", "aria-expanded": String(cambiaAperto(l)), onclick: () => apriCambia(l),
      title: "Cambia tutta l'immagine a parole: luce, ora, tempo, atmosfera. Spigoli e arredo restano." }, "Cambia"),
    h("button", { classe: "btn", onclick: () => ritoccaDa({ identificativo: l.identificativo }),
      title: "Disegna un'area e scrivi cosa cambiare. Fuori dall'area resta tutto com'è." }, "Ritocca"),
    pianta ? [
      h("button", { classe: "btn", onclick: () => ritoccaDa({ identificativo: l.identificativo }, null, { stile: S.catalogo.pianta.stili_arreda[0].id }),
        title: "Disegna un rettangolo per stanza e di' che stanza è: il modello la arreda vista dall'alto. Muri e aperture restano." }, "Arreda"),
      h("button", { classe: "btn", "aria-expanded": String(!!(S.punto && S.punto.da === l.identificativo)),
        onclick: () => apriPunto(l.identificativo, `/file/render/${l.identificativo}`, (l.scelte || {}).tipo),
        title: "Clicca sulla pianta dove stai e trascina verso dove guardi: esce la foto che farebbe quella camera." }, "Punto di vista"),
    ] : h("button", { classe: "btn", "aria-expanded": String(!!az.popola), onclick: () => apriPopola(l),
      title: "Persone, alberi o auto: dove dipingi tu col pennello verde, o dove decide il modello." }, "Popola"),
    l.importata ? null : h("button", { classe: "btn", onclick: () => rifai(l), disabled: occupato || !d || (m && !m.verificato) || null,
      title: occupato ? "Un lavoro è in corso: Variante si accende quando finisce." : "Stessa ricetta, un'altra immagine. Arriva accanto a questa, già scelta." }, "Variante"),
    h("button", { classe: "btn", "aria-expanded": String(az.video), onclick: apriVideoVeloce,
      title: "Un video che parte da questa immagine." }, "Video"),
    l.importata ? null : h("button", { classe: "btn", "aria-expanded": String(!!az.porta), onclick: () => apriPorta(l),
      title: "Rifà i passi di questa immagine su altre viste catturate in Allplan: stesso stile, stessi ritocchi. Si salva per dopo." }, "Ricetta"),
    h("button", { classe: "btn", "aria-expanded": String(!!az.finale), onclick: () => apriFinale(l),
      title: "Ingrandisce questa immagine e aggiunge dettaglio, senza cambiare il disegno. Per la tavola o la stampa." }, "Finale"))];
  // Variante non dice niente da sola (test del 2026-11-04): si scrive da dove
  // riparte e con cosa, prima che parta.
  const da = l.parte_da ? "dall'immagine da cui era nata questa" : tipoVista() ? `dalla ${nomePrima().toLowerCase()}` : "dalla vista Allplan";
  const cosa = l.parte_da ? "la stessa richiesta" : `lo stesso stile (${l.preset_nome})`;
  righe.push(l.importata
    ? h("p", { classe: "dove" }, "È l'immagine che hai caricato: da qui partono Cambia, Ritocca, Popola, Video e Finale. Ognuno ti dice dove va e quanto costa prima di partire.")
    : h("p", { classe: "dove" },
      `Variante: un'altra versione di questa immagine. Riparte ${da}, con ${cosa} e lo stesso modello (${l.modello_nome}).`,
      d ? [" Va a ", h("b", {}, d.destinazione), d.costo ? ` · ${d.costo}` : ""] : null));
  if (cambiaAperto(l) && S.scheda === "risultato") righe.push(pannelloNuovoPasso());
  if (az.video) righe.push(videoVeloce(l));
  if (az.porta) righe.push(pannelloPorta(l));
  if (az.finale) righe.push(pannelloFinale(l));
  if (az.popola) righe.push(pannelloPopola(l));
  if (S.punto && S.punto.da === l.identificativo) righe.push(pannelloPunto());
  if (az.errore) righe.push(avviso("errore", az.errore.fatto, az.errore.cosa_fare));
  return h("section", { classe: "barra-azioni", "aria-label": "Da questa immagine" }, ...righe);
}

// --- Cambia: tutta l'immagine a parole (2026-11-04) ---------------------------
// E' il passo a parole che prima stava solo in Passi («Nuovo passo da qui»).

// Un passo dell'albero visto come un lavoro di Risultato, per la stessa barra.
function comeLavoro(passo) {
  return { identificativo: passo.identificativo, modello: passo.modello, modello_nome: passo.modello_nome,
           parte_da: passo.da === "0" ? null : passo.da, preset_nome: passo.nome };
}

function cambiaAperto(l) { return !!(S.passi.nuovo && S.passi.nuovo.da === l.identificativo); }

async function apriCambia(l) {
  if (cambiaAperto(l)) { S.passi.nuovo = null; render(); return; }
  if (!passoDa(l.identificativo)) await caricaPassi();
  const passo = passoDa(l.identificativo);
  if (!passo) { S.azioni.errore = new ErroreStudio("Questa immagine non è fra i passi della vista.", "Ricarica la pagina dello Studio."); render(); return; }
  if (!passo.si_parte) { S.azioni.errore = new ErroreStudio(passo.motivo_non_si_parte || "Da questa immagine non si parte.", "Scegli un render riuscito."); render(); return; }
  await apriNuovoPasso(passo);
}

// --- Popola: persone, alberi, auto (2026-11-09) ------------------------------
// «Dipingo io» apre il Ritocca col pennello verde: ogni tratto prende la frase
// di Popola. «Decide il modello» e' un passo a parole su tutta l'immagine.
// Testi per il modello scelti, non provati: la scala delle persone e' il
// punto dove Nano Banana sbaglia di piu'.

async function apriPopola(l) {
  const az = S.azioni;
  if (az.popola) { az.popola = null; render(); return; }
  if (!passoDa(l.identificativo)) await caricaPassi();
  const passo = passoDa(l.identificativo);
  if (!passo || !passo.si_parte) { az.errore = new ErroreStudio((passo && passo.motivo_non_si_parte) || "Questa immagine non è fra i passi della vista.", "Scegli un render riuscito."); render(); return; }
  const cose = S.catalogo.popola.cose.filter((c) => c.scene.includes(passo.scena || "esterno"));
  if (!cose.length) { az.errore = new ErroreStudio(passo.scena === "pianta" ? "Popola non vale su una pianta vista dall'alto." : "Popola non vale per un pezzo d'arredo fotografato da solo.", passo.scena === "pianta" ? "Su una pianta usa Arreda, oppure Punto di vista." : "Per un arredo usa Ritocca con un'area."); render(); return; }
  az.errore = null;
  az.popola = { da: passo.identificativo, scena: passo.scena || "esterno", cosa: cose[0].id, quante: "alcune", come: "ferme",
                dove: "dipingo", modello: modelloVerificato(passo.modello), composto: null, errore: null };
  await destinazioneDi(az.popola.modello);
  componiPopola();
}

function sceltePopola(q) { return { cosa: q.cosa, quante: q.quante, come: q.come }; }

async function componiPopola() {
  const q = S.azioni.popola;
  if (!q) return;
  if (q.dove === "dipingo") { q.composto = null; render(); return; }
  try { q.composto = await post("/api/passi/componi", { vista: S.vista, da: q.da, popola: sceltePopola(q) }); q.errore = null; }
  catch (e) { q.composto = null; q.errore = e; }
  render();
}

async function applicaPopola() {
  const q = S.azioni.popola;
  if (q.dove === "dipingo") {
    const voce = S.catalogo.popola.cose.find((c) => c.id === q.cosa);
    ritoccaDa({ identificativo: q.da }, { ...sceltePopola(q), nome: nomePopola(q, voce) });
    S.azioni.popola = null;
    return;
  }
  q.errore = null;
  try {
    const dest = await destinazioneDi(q.modello);
    const risposta = await post("/api/passi/invia", { vista: S.vista, da: q.da, popola: sceltePopola(q), modello: q.modello,
      destinazione_mostrata: dest && dest.destinazione });
    S.azioni.popola = null;
    S.passi.scelto = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
    if (S.scheda === "risultato") await caricaRender();
  } catch (e) { q.errore = e; }
  render();
}

function nomePopola(q, voce) {
  const quante = S.catalogo.popola.quante.find((x) => x.id === q.quante);
  const come = S.catalogo.popola.come.find((x) => x.id === q.come);
  return [voce.nome, quante && quante.nome.toLowerCase(), voce.si_muove && come ? come.nome.toLowerCase() : null].filter(Boolean).join(", ");
}

function segPopola(etichetta, voci, valore, cambia, spento) {
  return h("div", { classe: "riga-popola" }, h("span", { classe: "etichetta" }, etichetta),
    h("div", { classe: "switch", role: "group", "aria-label": etichetta },
      voci.map(([id, nome]) => h("button", { classe: "seg", "aria-pressed": String(valore === id), disabled: spento || null,
        onclick: () => { cambia(id); componiPopola(); } }, nome))));
}

function pannelloPopola(l) {
  const q = S.azioni.popola;
  const cat = S.catalogo.popola;
  const cose = cat.cose.filter((c) => c.scene.includes(q.scena));
  const voce = cose.find((c) => c.id === q.cosa) || cose[0];
  const occupato = !!S.lavoroAttivo;
  const prompt = h("textarea", { classe: "prompt", readonly: true, "aria-label": "Prompt di Popola" });
  prompt.value = q.composto ? q.composto.prompt : "";
  const dipingo = q.dove === "dipingo";
  return h("section", { classe: "pannello evidenziato", "aria-label": "Popola" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Popola"),
      h("button", { classe: "btn link", onclick: () => { S.azioni.popola = null; render(); } }, "Chiudi")),
    segPopola("Cosa", cose.map((c) => [c.id, c.nome]), q.cosa, (id) => { q.cosa = id; }),
    segPopola("Quante", cat.quante.map((x) => [x.id, x.nome]), q.quante, (id) => { q.quante = id; }),
    voce.si_muove ? segPopola("Come", cat.come.map((x) => [x.id, x.nome]), q.come, (id) => { q.come = id; }) : null,
    segPopola("Dove", [["dipingo", "Dipingo io"], ["modello", "Decide il modello"]], q.dove, (id) => { q.dove = id; }),
    h("p", { classe: "piccolo" }, dipingo
      ? "Passi il pennello verde dove le vuoi, nel Ritocca. Fuori dal verde l'immagine resta quella di prima, pixel per pixel."
      : `Il modello le mette ${voce.dove[q.scena] || ""}. Fuori da lì non dovrebbe cambiare niente, ma ridisegna tutta l'immagine: guarda il prima/dopo.`),
    h("p", { classe: "tenue piccolo" }, "La grandezza delle persone si lega a porte e piani: è il punto dove il modello sbaglia di più. Testi scelti, non ancora provati."),
    dipingo ? null : [
      vedePrompt() && q.composto ? h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"),
        h("span", { classe: "tenue piccolo" }, `${q.composto.caratteri} caratteri`)), prompt) : null,
      h("div", { classe: "gruppo-scelta-modello" }, h("span", { classe: "etichetta" }, "Modello"), h("div", {}, sceltaModello(q, render, "popola", false))),
      rigaDestinazione(q.modello)],
    q.errore ? avviso("errore", q.errore.fatto, q.errore.cosa_fare) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: applicaPopola, disabled: (!dipingo && (occupato || !q.composto)) || null },
        dipingo ? "Dipingi dove, nel Ritocca" : "Applica"),
      !dipingo && occupato ? h("span", { classe: "tenue piccolo" }, "Un lavoro è in corso: Applica si accende quando finisce.") : null));
}

// --- Punto di vista dalla pianta (flusso 7, 2026-11-09) ------------------------
// Si clicca dove si sta e si trascina verso dove si guarda. Partono due
// immagini: la pianta, e la pianta col punto e il cono rossi (li disegna il
// motore, uguali a questi). Senza Allplan la stanza e' immaginata dal modello:
// lo si scrive prima di Rendi e sull'immagine che esce.

function scenaDi(l) {
  const passo = passoDa(l.identificativo);
  return (passo && passo.scena) || (l.scelte || {}).scena || "esterno";
}

function metri(valore) { return `${String(valore).replace(".", ",")} m`; }

function avvisoImmaginata() {
  const p = S.catalogo.pianta;
  return h("div", { classe: "avviso attenzione", role: "note" },
    h("b", {}, "Stanza immaginata dalla pianta."),
    h("span", {}, `Altezze (occhi a ${metri(p.altezza_occhi)}, soffitto a ${metri(p.altezza_soffitto)}, scelte), arredi e finestre che la pianta non disegna li ha immaginati il modello. Non è il tuo modello Allplan.`));
}

async function apriPunto(da, src, tipo) {
  if (S.punto && S.punto.da === da) { S.punto = null; render(); return; }
  const passo = da !== "0" ? passoDa(da) : null;
  S.punto = { da, src, tipo: tipo === "edificio" ? "edificio" : tipo === "volumi" ? "volumi" : tipo === "sito" ? "sito" : "edificio",
              stile: S.catalogo.pianta.stili_punto[0].id, x: null, y: null, verso_x: null, verso_y: null,
              modello: modelloPiuImmagini(passo ? passo.modello : null), composto: null, errore: null };
  await destinazioneDi(S.punto.modello);
  render();
}

// Il punto parte con due immagini: serve un modello che ne riceve piu' d'una.
function modelloPiuImmagini(id) {
  const tutti = S.catalogo.modelli;
  const m = tutti.find((x) => x.id === id);
  if (m && m.verificato && m.piu_immagini) return m.id;
  const predefinito = tutti.find((x) => x.id === S.studio.modello_predefinito);
  if (predefinito && predefinito.piu_immagini) return predefinito.id;
  const altro = tutti.find((x) => x.verificato && x.piu_immagini);
  return altro ? altro.id : S.studio.modello_predefinito;
}

function corpoPunto(q) {
  return { vista: S.vista, da: q.da, punto: { x: q.x, y: q.y, verso_x: q.verso_x, verso_y: q.verso_y, tipo: q.tipo, stile: q.stile } };
}

function puntoCompleto(q) {
  return q.x !== null && q.verso_x !== null && Math.hypot(q.verso_x - q.x, q.verso_y - q.y) >= S.catalogo.pianta.trascina_minimo;
}

async function componiPunto() {
  const q = S.punto;
  if (!q) return;
  if (!puntoCompleto(q)) { q.composto = null; render(); return; }
  try { q.composto = await post("/api/punto/componi", { ...corpoPunto(q), modello: q.modello }); q.errore = null; }
  catch (e) { q.composto = null; q.errore = e; }
  render();
}

async function rendiPunto() {
  const q = S.punto;
  q.errore = null;
  try {
    const dest = await destinazioneDi(q.modello);
    const risposta = await post("/api/punto/invia", { ...corpoPunto(q), modello: q.modello, destinazione_mostrata: dest && dest.destinazione });
    S.punto = null;
    S.passi.scelto = risposta.identificativo;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
    if (S.scheda === "risultato") await caricaRender();
  } catch (e) { q.errore = e; }
  render();
}

// La pianta con il punto e il cono: le coordinate sono frazioni dell'immagine,
// il cono si disegna in pixel dell'immagine perche' l'angolo resti vero.
function telaPunto(q) {
  const img = h("img", { src: q.src, alt: "La pianta: clicca dove stai, trascina verso dove guardi", draggable: "false",
    stile: "display:block; max-width:100%; max-height:55vh; user-select:none" });
  // L'SVG nasce da un pezzo di testo: la pagina non scrive indirizzi web.
  const scatola = document.createElement("div");
  scatola.innerHTML = '<svg class="segno-punto" aria-hidden="true"></svg>';
  const svg = scatola.firstChild;
  const tela = h("div", { classe: "tela-punto", stile: "position:relative; display:inline-block; max-width:100%; touch-action:none; cursor:crosshair" }, img, svg);
  svg.style.cssText = "position:absolute; inset:0; width:100%; height:100%; pointer-events:none";
  const disegna = () => {
    const w = img.naturalWidth || 1000, a = img.naturalHeight || 1000;
    svg.setAttribute("viewBox", `0 0 ${w} ${a}`);
    svg.setAttribute("preserveAspectRatio", "none");
    if (q.x === null) { svg.innerHTML = ""; return; }
    const c = S.catalogo.pianta, rosso = `rgb(${c.rosso.join(",")})`;
    const lato = Math.max(w, a), cx = q.x * w, cy = q.y * a;
    const raggio = Math.max(4, lato * c.raggio);
    let cono = "";
    if (q.verso_x !== null && (q.verso_x !== q.x || q.verso_y !== q.y)) {
      const angolo = Math.atan2(q.verso_y * a - cy, q.verso_x * w - cx);
      const mezza = (c.apertura_gradi / 2) * Math.PI / 180, lungo = lato * c.cono_lato;
      const v = [-mezza, mezza].map((d) => `${cx + lungo * Math.cos(angolo + d)},${cy + lungo * Math.sin(angolo + d)}`);
      cono = `<polygon points="${cx},${cy} ${v.join(" ")}" fill="${rosso}" fill-opacity="${c.cono_opacita / 255}" stroke="${rosso}"/>`;
    }
    svg.innerHTML = `${cono}<circle cx="${cx}" cy="${cy}" r="${raggio}" fill="${rosso}" stroke="#fff" stroke-width="${Math.max(1, raggio / 3)}"/>`;
  };
  img.addEventListener("load", disegna);
  const frazione = (ev) => {
    const r = img.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)), Math.min(1, Math.max(0, (ev.clientY - r.top) / r.height))];
  };
  let premuto = false;
  tela.addEventListener("pointerdown", (ev) => {
    premuto = true; tela.setPointerCapture(ev.pointerId);
    [q.x, q.y] = frazione(ev); q.verso_x = null; q.verso_y = null; q.composto = null; disegna();
  });
  tela.addEventListener("pointermove", (ev) => { if (!premuto) return; [q.verso_x, q.verso_y] = frazione(ev); disegna(); });
  const fine = () => { if (!premuto) return; premuto = false; componiPunto(); };
  tela.addEventListener("pointerup", fine);
  tela.addEventListener("pointercancel", fine);
  disegna();
  return tela;
}

function motivoRendiPunto(q) {
  if (S.lavoroAttivo) return "Un lavoro è in corso: Rendi si accende quando finisce.";
  if (q.x === null) return "Clicca sulla pianta dove stai.";
  if (!puntoCompleto(q)) return "Trascina un po' più in là, verso dove guardi.";
  if (q.errore) return q.errore.cosa_fare || q.errore.fatto;
  if (!q.composto) return "Preparo il testo che parte…";
  const d = S.passi.dest[q.modello];
  if (d && d.cosa_manca) return d.cosa_manca;
  return "";
}

function pannelloPunto() {
  const q = S.punto;
  const cat = S.catalogo.pianta;
  const prompt = h("textarea", { classe: "prompt", readonly: true, "aria-label": "Prompt del punto di vista" });
  prompt.value = q.composto ? q.composto.prompt : "";
  const motivo = motivoRendiPunto(q);
  const seg = (etichetta, voci, valore, cambia) => h("div", { classe: "riga-popola" }, h("span", { classe: "etichetta" }, etichetta),
    h("div", { classe: "switch", role: "group", "aria-label": etichetta },
      voci.map(([id, nome, spento, titolo]) => h("button", { classe: "seg", "aria-pressed": String(valore === id), disabled: spento || null, title: titolo || null,
        onclick: () => { cambia(id); componiPunto(); } }, nome, spento ? presto() : null))));
  return h("section", { classe: "pannello evidenziato", "aria-label": "Punto di vista" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Punto di vista"),
      h("button", { classe: "btn link", onclick: () => { S.punto = null; render(); } }, "Chiudi")),
    h("p", { classe: "piccolo" }, "Clicca sulla pianta dove stai e trascina verso dove guardi. Esce la foto che farebbe quella camera, a altezza d'occhi."),
    telaPunto(q),
    seg("Dove", [["edificio", "Dentro la casa"], [q.tipo === "volumi" ? "volumi" : "sito", "Fuori, nel lotto"]], q.tipo, (id) => { q.tipo = id; }),
    seg("Luce", cat.stili_punto.map((x) => [x.id, x.nome]), q.stile, (id) => { q.stile = id; }),
    seg("Camera", [["senza", "Senza Allplan"], ["allplan", "In Allplan", true,
      "Arriva quando la sonda di PythonParts legge la camera vera dal modello: altezze e arredi veri."]], cat.allplan ? "allplan" : "senza", () => {}),
    avvisoImmaginata(),
    vedePrompt() && q.composto ? h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"),
      h("span", { classe: "tenue piccolo" }, `${q.composto.caratteri} caratteri`)), prompt) : null,
    h("div", { classe: "gruppo-scelta-modello" }, h("span", { classe: "etichetta" }, "Modello"),
      h("div", {}, sceltaModello(q, () => { componiPunto(); }, "punto", true))),
    rigaDestinazione(q.modello, "La pianta, e la stessa pianta col punto e il cono rossi,"),
    q.errore ? avviso("errore", q.errore.fatto, q.errore.cosa_fare) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: rendiPunto, disabled: !!motivo || null }, "Rendi il punto di vista"),
      motivo ? h("span", { classe: "tenue piccolo" }, motivo) : null),
    h("p", { classe: "tenue piccolo" }, "Esce un passo nuovo sotto la pianta, col prima/dopo come gli altri. Testi per il modello scelti, non ancora provati."));
}

// --- Finale: ingrandire con piu' dettaglio (2026-11-04) -----------------------
// Magnific Precision V2 dal Router: nessun prompt, il render esce N volte piu'
// grande. Il risultato e' un passo nuovo sotto questa immagine.

async function apriFinale(l) {
  const az = S.azioni;
  if (az.finale) { az.finale = null; render(); return; }
  const f = S.catalogo.finale;
  az.finale = { ingrandimento: f.predefinito, tipo: "foto", composto: null, errore: null };
  await componiFinale(l);
}

async function componiFinale(l) {
  const q = S.azioni.finale;
  try { q.composto = await post("/api/finale/componi", { vista: S.vista, da: l.identificativo, ingrandimento: q.ingrandimento, tipo: q.tipo }); q.errore = null; }
  catch (e) { q.composto = null; q.errore = e; }
  render();
}

async function applicaFinale(l) {
  const q = S.azioni.finale;
  q.errore = null;
  try {
    const dest = await post("/api/finale/componi", { vista: S.vista, da: l.identificativo, ingrandimento: q.ingrandimento, tipo: q.tipo });
    const risposta = await post("/api/finale/invia", {
      vista: S.vista, da: l.identificativo, ingrandimento: q.ingrandimento, tipo: q.tipo,
      destinazione_mostrata: dest.destinazione.destinazione,
    });
    S.azioni.finale = null;
    S.inFila = [];
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    await caricaPassi();
    if (S.scheda === "risultato") await caricaRender();
  } catch (e) { q.errore = e; }
  render();
}

function pannelloFinale(l) {
  const q = S.azioni.finale;
  const f = S.catalogo.finale;
  const c = q.composto;
  const d = c && c.destinazione;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Finale" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Finale · ingrandisci con più dettaglio"),
      h("button", { classe: "btn link", onclick: () => { S.azioni.finale = null; render(); } }, "Chiudi")),
    h("p", { classe: "piccolo" }, `${f.modello.nome} di ${f.modello.fornitore}: ingrandisce e aggiunge dettaglio, senza cambiare il disegno e senza prompt.`),
    h("span", { classe: "etichetta" }, "Quanto più grande"),
    h("div", { classe: "switch", role: "group", "aria-label": "Quanto più grande" },
      f.ingrandimenti.map((n) => h("button", { classe: "seg", "aria-pressed": String(q.ingrandimento === n),
        onclick: () => { q.ingrandimento = n; componiFinale(l); } }, `×${n}`))),
    h("span", { classe: "etichetta" }, "Che immagine è"),
    h("div", { classe: "switch", role: "group", "aria-label": "Che immagine è" },
      f.tipi.map((t) => h("button", { classe: "seg", "aria-pressed": String(q.tipo === t.id),
        onclick: () => { q.tipo = t.id; componiFinale(l); } }, t.nome))),
    nota("Scelta, non provata.", "Foto per i render fotografici; Illustrazione per schizzi, acquerelli e rese non fotografiche. Nessun Finale è ancora stato fatto con il servizio vero: il primo è la prova."),
    c ? h("p", { classe: "piccolo" }, `Da ${c.partenza} a `, h("b", {}, c.uscita), " pixel.") : null,
    d ? h("p", { classe: "destinazione" }, "Il render va a ", h("b", {}, d.destinazione),
      d.senza_ripiego ? ", senza ripiego su altri servizi" : "", `. Costo: ${d.costo}.`) : null,
    d && d.avviso ? h("p", { classe: "tenue piccolo" }, d.avviso) : null,
    q.errore ? avviso("errore", q.errore.fatto, q.errore.cosa_fare) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => applicaFinale(l), disabled: !c || !!S.lavoroAttivo || null }, "Applica"),
      S.lavoroAttivo ? h("span", { classe: "tenue piccolo" }, "Un lavoro è in corso: Applica si accende quando finisce.") : null),
    h("p", { classe: "tenue piccolo" }, "Esce un passo nuovo sotto questa immagine."));
}

// --- Ricetta: i passi di questa immagine su altre viste (2026-11-09) ----------
// Era «Altra vista» (2026-11-04), per i fotogrammi di un video. Ora si
// spuntano piu' viste e la ricetta si salva con un nome per rifarla dopo, da
// Genera, sulle viste catturate piu' tardi. Ogni vista e' un render: stile e
// modello del primo render, le richieste e le note di tutti i passi a parole,
// e questa immagine come seconda immagine perche' materiali e oggetti restino
// gli stessi.

async function apriPorta(l) {
  const az = S.azioni;
  if (az.porta) { az.porta = null; render(); return; }
  az.porta = { dati: null, dest: null, viste: [], mandato: null, errore: null, nome: "", salvata: null };
  render();
  try {
    const dati = await get(`/api/lavori/${enc(l.identificativo)}/porta`);
    az.porta.dati = dati;
    az.porta.viste = dati.viste.slice(0, 1);
    az.porta.nome = nomeRicetta(dati.passi);
    az.porta.dest = await get(`/api/destinazione?modello=${enc(dati.modello)}&riferimento=1`);
  } catch (e) { if (az.porta) az.porta.errore = e; }
  render();
}

// Il nome proposto: gli ultimi due passi, solo la loro ultima parte
// («Ora blu», non «Cambia · Ora blu»), tagliato a parola intera entro 60.
function nomeRicetta(passi) {
  const corti = (passi || []).map((p) => p.split(" · ").pop().replace(/…$/, ""));
  let nome = (corti.length > 1 ? corti.slice(1) : corti).slice(-2).join(" + ");
  if (nome.length > 60) nome = nome.slice(0, 60).replace(/\s+\S*$/, "");
  return nome;
}

function elencoPassiRicetta(passi) {
  return h("ol", { classe: "piccolo passi-ricetta" }, passi.map((x) => h("li", {}, x)));
}

function costoViste(costi, n) {
  return n >= 1 && costi && costi[n - 1] ? costi[n - 1] : "";
}

function pannelloPorta(l) {
  const p = S.azioni.porta;
  if (p.errore && !p.dati) return avviso("errore", p.errore.fatto, p.errore.cosa_fare);
  if (!p.dati || !p.dest) return h("p", { classe: "tenue piccolo" }, "Leggo i passi di questa immagine…");
  if (p.mandato) {
    const n = p.mandato.length;
    return h("div", { classe: "video-veloce", role: "status" },
      h("b", {}, n === 1 ? `In coda sulla vista ${p.mandato[0]}.` : `In coda su ${n} viste: ${p.mandato.join(", ")}.`),
      h("span", { classe: "piccolo tenue" }, "Le trovi nello storico a sinistra, ognuna sotto la sua vista. Aprila: il prima/dopo la confronta con la sua vista Allplan."));
  }
  const d = p.dati;
  const salva = h("div", { classe: "riga" },
    h("input", { type: "text", "aria-label": "Nome della ricetta", maxlength: "60", value: p.nome,
      placeholder: "Per esempio: Ora blu con persone",
      oninput: (e) => { p.nome = e.target.value; } }),
    h("button", { classe: "btn", onclick: () => salvaRicetta(l), disabled: !d.passi.length || null,
      title: "La ritrovi in Genera › Le mie ricette, per rifarla sulle viste che catturi dopo." }, "Salva ricetta"));
  const testa = [
    h("span", { classe: "etichetta" }, "Ricetta di questa immagine"),
    elencoPassiRicetta(d.passi),
    h("p", { classe: "piccolo tenue" }, `Modello ${d.modello_nome}. I pennelli e le aree dei ritocchi non si portano: sono disegnati su questa inquadratura, passano a parole.`),
    salva,
    p.salvata ? h("p", { classe: "piccolo", role: "status" }, p.salvata) : null,
    p.errore ? avviso("errore", p.errore.fatto, p.errore.cosa_fare) : null,
  ];
  if (!d.viste.length) {
    return h("div", { classe: "video-veloce" }, ...testa,
      h("b", {}, "Non c'è un'altra vista."),
      h("span", { classe: "piccolo" }, "In Allplan inquadra un altro punto di vista e cattura dalla palette: comparirà qui. Intanto puoi salvare la ricetta."));
  }
  const n = p.viste.length;
  const troppe = n > d.massime;
  const spunte = h("div", { classe: "spunte-viste", role: "group", "aria-label": "Viste su cui rifare la ricetta" },
    d.viste.map((v) => h("label", { classe: "riga piccolo" },
      h("input", { type: "checkbox", checked: p.viste.includes(v) || null,
        onchange: (e) => { p.viste = e.target.checked ? [...p.viste, v] : p.viste.filter((x) => x !== v); render(); } }),
      v)));
  const spento = S.lavoroAttivo ? "Un lavoro è in corso: si accende quando finisce."
    : p.dest.cosa_manca || p.dest.riferimento_non_accettato
    || (!n ? "Spunta almeno una vista." : troppe ? `Al massimo ${d.massime} viste per clic.` : null);
  return h("div", { classe: "video-veloce" }, ...testa,
    h("span", { classe: "etichetta" }, "Rifalla su"),
    spunte,
    h("p", { classe: "dove" }, "Va a ", h("b", {}, p.dest.destinazione),
      n ? ` · ${costoViste(d.costi, n)} · un render per vista` : ""),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => porta(l), disabled: !!spento || null },
        n > 1 ? `Rifai su ${n} viste` : "Rifai su 1 vista"),
      spento ? h("span", { classe: "piccolo tenue" }, spento) : null));
}

async function porta(l) {
  const p = S.azioni.porta;
  p.errore = null;
  try {
    const r = await post(`/api/lavori/${enc(l.identificativo)}/porta`, { viste: p.viste, destinazione_mostrata: p.dest.destinazione });
    p.mandato = r.viste;
    await caricaStorico();
  } catch (e) { p.errore = e; }
  render();
}

async function salvaRicetta(l) {
  const p = S.azioni.porta;
  const nome = (p.nome || "").trim();
  p.errore = null; p.salvata = null;
  const doppio = S.ricette.elenco.some((r) => r.nome.toLowerCase() === nome.toLowerCase());
  if (doppio && !window.confirm(`Hai già una ricetta «${nome}». La sostituisco con i passi di questa immagine?`)) return;
  try {
    const r = await post("/api/mie-ricette", { lavoro: l.identificativo, nome, sovrascrivi: doppio });
    S.ricette.elenco = r.ricette; S.ricette.problema = r.problema;
    p.salvata = `Salvata «${nome}». La ritrovi in Genera › Le mie ricette.`;
  } catch (e) { p.errore = e; }
  render();
}

// --- Le mie ricette, in Genera ------------------------------------------------
// Una ricetta salvata si rifa' sulla vista di Genera: la vista catturata dopo.

async function caricaRicette() {
  try {
    const r = await get("/api/mie-ricette");
    S.ricette.elenco = r.ricette; S.ricette.problema = r.problema;
  } catch (e) { S.ricette.problema = e.fatto; }
}

async function scegliRicetta(nome) {
  const q = S.ricette;
  q.scelta = nome; q.dest = null; q.nota = null; q.errore = null;
  const r = q.elenco.find((x) => x.nome === nome);
  render();
  if (r && r.usabile) {
    try { q.dest = await get(`/api/destinazione?modello=${enc(r.modello)}&riferimento=1`); } catch (e) { q.errore = e; }
  }
  render();
}

function pannelloRicette() {
  const q = S.ricette;
  if (!q.elenco.length) {
    return [h("span", { classe: "etichetta" }, "Le mie ricette"),
      h("p", { classe: "tenue piccolo" }, "Nessuna ricetta salvata. Sotto un render riuscito apri Ricetta e premi Salva ricetta: qui la rifai sulle viste che catturi dopo."),
      q.problema ? avviso("errore", q.problema, "Le ricette nuove si salvano in un file nuovo.") : null];
  }
  const scelta = h("select", { "aria-label": "Le mie ricette" },
    h("option", { value: "", selected: !q.scelta }, "Nessuna"),
    q.elenco.map((r) => h("option", { value: r.nome, selected: r.nome === q.scelta }, r.usabile ? r.nome : `${r.nome} (non si usa più)`)));
  scelta.addEventListener("change", () => scegliRicetta(scelta.value));
  const r = q.elenco.find((x) => x.nome === q.scelta);
  const righe = [h("span", { classe: "etichetta" }, "Le mie ricette"),
    h("div", { classe: "riga" }, scelta,
      r ? h("button", { classe: "btn", onclick: () => eliminaRicetta(r.nome) }, "Elimina") : null)];
  if (q.problema) righe.push(avviso("errore", q.problema, "Le ricette nuove si salvano in un file nuovo."));
  if (q.nota) righe.push(h("p", { classe: "piccolo", role: "status" }, q.nota));
  if (q.errore) righe.push(avviso("errore", q.errore.fatto, q.errore.cosa_fare));
  if (!r) return righe;
  righe.push(elencoPassiRicetta(r.passi || []));
  if (!r.usabile) { righe.push(avviso("attenzione", "Questa ricetta non si usa più.", r.perche_no)); return righe; }
  const stessa = r.vista === S.vista;
  const spento = !S.vista ? "Serve una vista." : stessa ? "È la vista da cui viene la ricetta: qui serve Variante."
    : S.lavoroAttivo ? "Un lavoro è in corso: si accende quando finisce."
    : !q.dest ? "Leggo dove va…" : q.dest.cosa_manca || q.dest.riferimento_non_accettato || null;
  righe.push(h("p", { classe: "piccolo tenue" }, `Viene da un render di ${r.vista}, che parte come seconda immagine. Stile e modello (${r.modello_nome}) sono i suoi: le scelte di questa pagina non contano.`));
  if (q.dest) righe.push(h("p", { classe: "dove" }, "Va a ", h("b", {}, q.dest.destinazione), ` · ${costoViste(r.costi, 1)}`));
  righe.push(h("div", { classe: "azioni" },
    h("button", { classe: "btn", onclick: () => usaRicetta(r), disabled: !!spento || null }, "Rifalla su questa vista"),
    spento ? h("span", { classe: "piccolo tenue" }, spento) : null));
  return righe;
}

async function usaRicetta(r) {
  const q = S.ricette;
  q.errore = null; S.errore = null;
  try {
    const risposta = await post("/api/mie-ricette/usa", { nome: r.nome, viste: [S.vista], destinazione_mostrata: q.dest.destinazione });
    q.nota = `«${r.nome}» in coda su ${S.vista}.`;
    S.inFila = risposta.identificativi.slice(1);
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
  } catch (e) { q.errore = e; }
  render();
}

async function eliminaRicetta(nome) {
  if (!window.confirm(`Elimino la ricetta «${nome}»? Le immagini già fatte restano.`)) return;
  try {
    const r = await post("/api/mie-ricette/elimina", { nome });
    S.ricette = { ...S.ricette, elenco: r.ricette, problema: r.problema, scelta: "", dest: null, nota: `Eliminata «${nome}».` };
  } catch (e) { S.ricette.errore = e; }
  render();
}

async function apriVideoVeloce() {
  const az = S.azioni;
  az.video = !az.video; az.errore = null;
  if (az.video && !S.video.catalogo) {
    try { S.video.catalogo = await get("/api/video/catalogo"); } catch (e) { az.errore = e; }
  }
  render();
}

function videoInCorso() {
  return S.storico.gruppi.some((g) => g.voci.some((v) => v.tipo === "video" && v.attivo));
}

function videoVeloce(l) {
  const az = S.azioni;
  const c = S.video.catalogo;
  if (!c) return h("p", { classe: "tenue piccolo" }, "Leggo dove va il video…");
  if (az.mandato) {
    return h("div", { classe: "video-veloce", role: "status" }, h("b", {}, "Video in coda."),
      h("span", { classe: "piccolo tenue" }, "Lo trovi nello storico a sinistra, accanto a questa immagine."));
  }
  const spento = !c.fa_video ? "Il servizio scelto non fa video."
    : videoInCorso() ? "Un video è già in lavorazione: aspetta che finisca."
    : !az.movimento ? "Scegli il movimento." : null;
  return h("div", { classe: "video-veloce" },
    h("span", { classe: "etichetta" }, "Movimento della camera"),
    h("div", { classe: "scelte-chip", role: "group", "aria-label": "Movimento della camera" },
      c.movimenti.map((x) => h("button", { classe: "chip", "aria-pressed": String(az.movimento === x.id),
        onclick: () => { az.movimento = x.id; render(); } }, x.nome))),
    h("span", { classe: "etichetta" }, "Cosa succede", spiega("Facoltativo. Entra nel prompt del video com'è scritto, dopo il movimento della camera.")),
    testoVideoVeloce(),
    h("p", { classe: "dove" }, "Va a ", h("b", {}, c.destinazione), ` · ${c.modello_nome} · ${c.durate[0]} s · ${c.risoluzioni[0]}`,
      spiega("Durata e risoluzione si cambiano nella scheda Video.")),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: () => videoInUnClic(l), disabled: !!spento || null }, "Genera video"),
      spento ? h("span", { classe: "piccolo tenue" }, spento) : null));
}

function testoVideoVeloce() {
  const az = S.azioni;
  const campo = h("textarea", { id: "testo-video-veloce", rows: "2", "aria-label": "Cosa succede, a parole",
    placeholder: "Per esempio: si accendono le luci delle finestre, passa qualche persona" }, az.testo || "");
  campo.addEventListener("input", () => { az.testo = campo.value; });
  return campo;
}

async function videoInUnClic(l) {
  const az = S.azioni;
  const c = S.video.catalogo;
  az.errore = null;
  try {
    await post("/api/video/invia", {
      immagini: [{ render: l.identificativo }], modo: "primo", movimento: az.movimento, testo: az.testo || "",
      durata: c.durate[0], risoluzione: c.risoluzioni[0], audio: false, destinazione_mostrata: c.destinazione,
    });
    az.mandato = true;
    await caricaStorico();
  } catch (e) { az.errore = e; }
  render();
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
      palcoConAzioni(l),
      h("div", { classe: "lato" }, elencoRender(), tenuta(l), pannelloRiaggancia(l), ricettaPannello(l), adesso(l),
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
  r.da = id; r.aree = []; r.testo = ""; r.composto = null; r.errore = null; r.esito = null;
  render();
}

function ritoccoBloccato() {
  return !!(S.lavoroAttivo && S.ritocca.inviato && S.lavoroAttivo.identificativo === S.ritocca.inviato);
}

// Ogni nota puo' avere la sua foto: i Rif. sono quelli delle note, nell'ordine
// delle note, e la nota porta il numero del suo.
function insertiRitocco() { return S.ritocca.aree.filter((a) => a.rif).map((a) => a.rif); }

// Le aree come le vuole il server: senza la nota (la scrive il server dalla
// frase, core/aree.py da_testo) e senza il contorno del pennello, che il
// server ricalcola dai punti.
function areePerIlServer() {
  let numero = 0;
  return S.ritocca.aree.map((a) => {
    const area = { forma: a.forma, punti: a.punti };
    if (a.azione && a.azione !== "cambia") area.azione = a.azione;
    if (a.forma === "pennello") area.spessore = a.spessore;
    if (a.rif) area.inserto = ++numero;
    if (S.ritocca.arreda) area.stanza = a.stanza || "soggiorno";
    return area;
  });
}

function numeroRif(i) { return S.ritocca.aree.slice(0, i + 1).filter((a) => a.rif).length; }

async function immagineNota(i, file) {
  const r = S.ritocca;
  if (!file) return;
  try { r.aree[i].rif = await caricaInserto(file); r.errore = null; } catch (e) { r.errore = e; }
  componiRitocco();
  render();
}

function togliImmagineNota(i) { S.ritocca.aree[i].rif = null; componiRitocco(); render(); }

function bottoneImmagineNota(a, i, bloccato) {
  if (S.ritocca.popola || S.ritocca.arreda) return null;
  const m = S.catalogo.modelli.find((x) => x.id === S.ritocca.modello);
  if (a.rif) {
    return h("div", { classe: "riga nota-rif" },
      h("img", { src: `/file/riferimento/${enc(a.rif.nome)}`, alt: `Rif. ${numeroRif(i)} dell'area ${i + 1}` }),
      h("span", { classe: "piccolo" }, h("b", {}, `Rif. ${numeroRif(i)}`), ` · ${a.rif.da || a.rif.nome}`),
      bloccato ? null : h("button", { classe: "btn link piccolo", onclick: () => togliImmagineNota(i) }, "Togli"));
  }
  if (bloccato) return null;
  const pieni = insertiRitocco().length >= (S.catalogo.inserti_massimi || 4);
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", hidden: true, "aria-label": `Immagine di riferimento per l'area ${i + 1}` });
  file.addEventListener("change", () => immagineNota(i, file.files && file.files[0]));
  const spento = pieni || !(m && m.piu_immagini);
  return h("span", {}, file, h("button", {
    classe: "btn link piccolo", onclick: () => file.click(), disabled: spento || null,
    title: pieni ? "Ci sono già 4 Rif. in questo ritocco." : !(m && m.piu_immagini) ? `${m ? m.nome : "Questo modello"} riceve una sola immagine: scegli Nano Banana 2.` : "Una foto di riferimento per quest'area: un materiale, un arredo, una persona",
  }, "+ Rif."));
}

// Il testo serve se c'e' un'area che non e' un «togli»: togliere si spiega da solo.
function testoServe() { return !S.ritocca.popola && !S.ritocca.arreda && S.ritocca.aree.some((a) => a.azione !== "togli"); }

// Cosa parte per il server: la frase con le @, oppure le scelte di Popola.
function corpoRitocco() {
  const r = S.ritocca;
  const corpo = { vista: S.vista, da: r.da, aree: areePerIlServer(), inserti: insertiRitocco().map((x) => x.nome) };
  if (r.arreda) corpo.arreda = { stile: r.arreda.stile };
  else if (r.popola) corpo.popola = { cosa: r.popola.cosa, quante: r.popola.quante, come: r.popola.come };
  else corpo.testo = r.testo;
  return corpo;
}

function motivoApplicaRitoccoSpento() {
  const r = S.ritocca;
  if (S.lavoroAttivo) return "Un lavoro è in corso: Applica si accende quando finisce, così un doppio clic non si paga due volte.";
  if (!r.aree.length && r.arreda) return "Disegna un rettangolo su ogni stanza da arredare, poi scegli che stanza è.";
  if (!r.aree.length) return r.popola ? "Passa il pennello verde dove le vuoi." : "Disegna un'area sul render, poi scrivi cosa cambiare chiamandola @1.";
  if (testoServe() && !r.testo.trim()) return "Scrivi cosa cambiare, e chiama le aree con @1, @2.";
  if (r.errore) return r.errore.cosa_fare || r.errore.fatto;
  if (!r.composto) return "Preparo il testo che parte…";
  const d = S.passi.dest[r.modello];
  if (d && d.cosa_manca) return d.cosa_manca;
  return "";
}

let attesaRitocco = null;
function componiRitocco() {
  const r = S.ritocca;
  clearTimeout(attesaRitocco);
  r.composto = null;
  if (!r.aree.length || (testoServe() && !r.testo.trim())) { r.errore = null; disegnaApplicaRitocco(); return; }
  disegnaApplicaRitocco();
  attesaRitocco = setTimeout(async () => {
    try {
      r.composto = await post("/api/ritocca/componi", corpoRitocco());
      r.errore = null;
    } catch (e) { r.composto = null; r.errore = e; }
    disegnaApplicaRitocco();
  }, 250);
}

function etichettaApplica() {
  const n = S.ritocca.aree.length;
  if (S.ritocca.arreda) return n ? `Arreda · ${n === 1 ? "1 zona" : `${n} zone`}` : "Arreda";
  if (S.ritocca.popola) return n ? `Applica Popola · ${n === 1 ? "1 tratto" : `${n} tratti`}` : "Applica Popola";
  return n ? `Applica il ritocco · ${n === 1 ? "1 area" : `${n} aree`}` : "Applica il ritocco";
}

// Aggiorna Applica, il prompt, le note delle aree e gli avvisi mentre si
// scrive, senza ridisegnare: il testo non perde il cursore.
function disegnaApplicaRitocco() {
  const r = S.ritocca;
  const bottone = document.getElementById("applica-ritocco");
  if (bottone) { bottone.disabled = !!motivoApplicaRitoccoSpento(); bottone.textContent = etichettaApplica(); }
  const motivo = document.getElementById("motivo-ritocco");
  if (motivo) motivo.textContent = motivoApplicaRitoccoSpento();
  const prompt = document.getElementById("prompt-ritocco");
  if (prompt) prompt.value = r.composto ? r.composto.prompt : "";
  const car = document.getElementById("caratteri-ritocco");
  if (car) car.textContent = r.composto ? `${r.composto.caratteri} caratteri` : "";
  const err = document.getElementById("errore-ritocco");
  if (err) err.replaceChildren(r.errore ? avviso("errore", r.errore.fatto, r.errore.cosa_fare) : "");
  const note = r.composto ? r.composto.note_aree || [] : [];
  r.aree.forEach((_a, i) => {
    const el = document.getElementById(`nota-area-${i}`);
    if (el) el.textContent = note[i] ? `«${note[i]}»` : "La sua parte del testo compare qui.";
  });
}

// Una @N nel testo, dove sta il cursore (o in fondo), con uno spazio prima e dopo.
function inserisciMenzione(numero) {
  const r = S.ritocca;
  const campo = document.getElementById("testo-ritocco");
  const parola = `@${numero}`;
  const inizio = campo ? campo.selectionStart : r.testo.length;
  const fine = campo ? campo.selectionEnd : r.testo.length;
  const prima = r.testo.slice(0, inizio), dopo = r.testo.slice(fine);
  const pezzo = `${prima && !/\s$/.test(prima) ? " " : ""}${parola}${dopo && /^\s/.test(dopo) ? "" : " "}`;
  r.testo = prima + pezzo + dopo;
  if (campo) {
    campo.value = r.testo;
    campo.focus();
    const dove = prima.length + pezzo.length;
    campo.setSelectionRange(dove, dove);
  }
  componiRitocco();
}

// Togliendo l'area i (da 0), la sua @ sparisce dal testo e quelle dopo scalano di uno.
function rinumeraTesto(testo, i) {
  const tolta = i + 1;
  return testo.replace(/\s?@(\d+)\b/g, (tutto, cifre) => {
    const n = Number(cifre);
    if (n === tolta) return "";
    return n > tolta ? tutto.replace(`@${cifre}`, `@${n - 1}`) : tutto;
  });
}

function togliArea(i) {
  const r = S.ritocca;
  r.aree.splice(i, 1);
  r.testo = rinumeraTesto(r.testo, i);
  r.composto = null;
  render();
  componiRitocco();
}

// Il contorno di un tratto di pennello, come core/aree.py contorno_tratto:
// in pixel, per non deformarlo su un render non quadrato.
const PUNTI_MEZZO_CERCHIO = 8;
function contornoTratto(punti, raggio) {
  const t = [punti[0]];
  for (const p of punti.slice(1)) if (Math.hypot(p[0] - t[t.length - 1][0], p[1] - t[t.length - 1][1]) > 1e-6) t.push(p);
  if (t.length === 1) {
    const n = 2 * PUNTI_MEZZO_CERCHIO;
    return Array.from({ length: n }, (_x, i) => [t[0][0] + raggio * Math.cos(2 * Math.PI * i / n), t[0][1] + raggio * Math.sin(2 * Math.PI * i / n)]);
  }
  const normale = (a, b) => { const dx = b[0] - a[0], dy = b[1] - a[1], l = Math.hypot(dx, dy); return [-dy / l, dx / l]; };
  const normali = t.map((_p, i) => {
    const prima = i > 0 ? normale(t[i - 1], t[i]) : null;
    const dopo = i < t.length - 1 ? normale(t[i], t[i + 1]) : null;
    const [nx, ny] = prima && dopo ? [(prima[0] + dopo[0]) / 2, (prima[1] + dopo[1]) / 2] : (prima || dopo);
    const l = Math.hypot(nx, ny) || 1;
    return [nx / l, ny / l];
  });
  const mezzo = (c, v) => {
    const a = Math.atan2(v[1], v[0]);
    return Array.from({ length: PUNTI_MEZZO_CERCHIO - 1 }, (_x, k) => {
      const ang = a + Math.PI / 2 - Math.PI * (k + 1) / PUNTI_MEZZO_CERCHIO;
      return [c[0] + raggio * Math.cos(ang), c[1] + raggio * Math.sin(ang)];
    });
  };
  const sinistra = t.map((p, i) => [p[0] + normali[i][0] * raggio, p[1] + normali[i][1] * raggio]);
  const destra = t.map((p, i) => [p[0] - normali[i][0] * raggio, p[1] - normali[i][1] * raggio]);
  const ultimo = normali[normali.length - 1];
  return [...sinistra, ...mezzo(t[t.length - 1], [ultimo[1], -ultimo[0]]), ...destra.reverse(), ...mezzo(t[0], [-normali[0][1], normali[0][0]])];
}

// Il contorno di un tratto in coordinate da 0 a 1, dall'immagine com'e' davvero.
function contornoNormalizzato(punti, spessore, img) {
  const w = img.naturalWidth || 1000, hh = img.naturalHeight || 1000;
  return contornoTratto(punti.map(([x, y]) => [x * w, y * hh]), spessore * w / 2).map(([x, y]) => [x / w, y / hh]);
}

function puntiSvg(a) {
  if (a.forma === "rettangolo") {
    const [[x0, y0], [x1, y1]] = a.punti;
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
  }
  if (a.forma === "pennello") return a.contorno || a.punti;
  return a.punti;
}
function attributoPunti(punti) { return punti.map(([x, y]) => `${(x * 1000).toFixed(1)},${(y * 1000).toFixed(1)}`).join(" "); }

const NOMI_AREA = { rettangolo: "rettangolo", libera: "selezione libera", aggiungi: "pennello aggiungi", togli: "pennello togli" };
function nomeArea(a) { return a.forma === "pennello" ? NOMI_AREA[a.azione] : NOMI_AREA[a.forma]; }
function spessorePennello() {
  const r = S.ritocca;
  if (!r.spessore) r.spessore = (S.studio && S.studio.ritocco && S.studio.ritocco.pennello) || 0.04;
  return r.spessore;
}

function telaRitocco(base) {
  const r = S.ritocca;
  const bloccato = ritoccoBloccato();
  const img = h("img", { src: `/file/render/${base.identificativo}`, alt: `Render del passo ${base.numero}`, draggable: "false" });
  // L'SVG si scrive come testo: il parser HTML lo mette da solo nel suo
  // spazio dei nomi, e i punti sono solo numeri.
  const contenitore = h("div");
  contenitore.innerHTML = `<svg viewBox="0 0 1000 1000" preserveAspectRatio="none" class="aree-svg" aria-hidden="true">${
    r.aree.map((a) => `<polygon class="contorno-area ${a.azione || "cambia"}" points="${attributoPunti(puntiSvg(a))}"></polygon>`).join("")
  }<polyline class="contorno-area in-corso" points=""></polyline><polygon class="contorno-area in-corso tratto" points=""></polygon></svg>`;
  const disegno = contenitore.firstElementChild;
  const traccia = disegno.querySelector("polyline");
  const pennellata = disegno.querySelector("polygon.tratto");
  const numeri = r.aree.map((a, i) => {
    const [x, y] = a.forma === "pennello" ? a.punti[0] : puntiSvg(a)[0];
    return h("span", { classe: `numero-area ${a.azione || "cambia"}`, stile: `left:${x * 100}%;top:${y * 100}%`, "aria-hidden": "true" }, String(i + 1));
  });
  const tela = h("div", { classe: `tela-ritocco${bloccato ? " bloccata" : ""}`, "data-strumento": r.strumento },
    img, disegno, ...numeri);
  if (bloccato) return tela;

  // Il disegno: rettangolo da un angolo all'altro, lazo che si chiude da solo
  // al rilascio, o tratto di pennello (aggiungi o togli) largo `spessore`.
  let tratto = null;
  const pennello = r.strumento === "aggiungi" || r.strumento === "togli";
  const punto = (ev) => {
    const b = img.getBoundingClientRect();
    return [Math.min(1, Math.max(0, (ev.clientX - b.left) / b.width)), Math.min(1, Math.max(0, (ev.clientY - b.top) / b.height))];
  };
  tela.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    ev.preventDefault();
    tela.setPointerCapture(ev.pointerId);
    tratto = { inizio: punto(ev), punti: [punto(ev)] };
    if (pennello) pennellata.setAttribute("points", attributoPunti(contornoNormalizzato(tratto.punti, spessorePennello(), img)));
  });
  tela.addEventListener("pointermove", (ev) => {
    if (!tratto || !tela.hasPointerCapture(ev.pointerId)) return;
    const p = punto(ev);
    if (r.strumento === "rettangolo") {
      tratto.punti = [tratto.inizio, p];
      traccia.setAttribute("points", attributoPunti(puntiSvg({ forma: "rettangolo", punti: tratto.punti })) + " " + attributoPunti([tratto.inizio]));
      return;
    }
    const ultimo = tratto.punti[tratto.punti.length - 1];
    if (Math.hypot(p[0] - ultimo[0], p[1] - ultimo[1]) < LAZO_PASSO_MINIMO) return;
    tratto.punti.push(p);
    if (pennello) pennellata.setAttribute("points", attributoPunti(contornoNormalizzato(tratto.punti, spessorePennello(), img)));
    else traccia.setAttribute("points", attributoPunti(tratto.punti));
  });
  const chiudi = () => {
    if (!tratto) return;
    const t = tratto; tratto = null;
    traccia.setAttribute("points", "");
    pennellata.setAttribute("points", "");
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
    } else if (pennello) {
      // Anche un clic e' un tratto: un cerchio largo quanto il pennello.
      area = { forma: "pennello", azione: r.strumento, spessore: spessorePennello(), punti: t.punti };
    }
    if (!area) return;
    area.punti = area.punti.map(([x, y]) => [Number(x.toFixed(4)), Number(y.toFixed(4))]);
    if (area.forma === "pennello") area.contorno = contornoNormalizzato(area.punti, area.spessore, img);
    if (!area.azione) area.azione = "cambia";
    if (r.arreda) area.stanza = "soggiorno";
    r.aree.push(area);
    r.composto = null;
    r.esito = null;
    render();
    // L'area nuova entra nel testo come @N, dove si scrive. In Popola non c'e' testo.
    if (r.popola || r.arreda) componiRitocco(); else inserisciMenzione(r.aree.length);
  };
  tela.addEventListener("pointerup", chiudi);
  tela.addEventListener("pointercancel", () => { tratto = null; traccia.setAttribute("points", ""); pennellata.setAttribute("points", ""); });
  return tela;
}

// Il compositore: una frase sola, le aree chiamate con @1, @2. Sotto, un
// bottone per area che mette la sua @ dove sta il cursore.
function compositoreRitocco(bloccato) {
  const r = S.ritocca;
  if (r.arreda) {
    const stili = S.catalogo.pianta.stili_arreda;
    return h("section", { classe: "pannello compositore-ritocco", "aria-label": "Arreda per zone" },
      h("div", { classe: "riga tra" },
        h("span", {}, h("b", {}, "Arreda per zone")),
        bloccato ? null : h("button", { classe: "btn link piccolo", onclick: () => { r.arreda = null; r.aree = []; r.composto = null; r.strumento = "rettangolo"; render(); } }, "Esci da Arreda")),
      h("div", { classe: "switch", role: "group", "aria-label": "Stile dell'arredo" },
        stili.map((x) => h("button", { classe: "seg", "aria-pressed": String(r.arreda.stile === x.id), disabled: bloccato || null,
          onclick: () => { r.arreda.stile = x.id; componiRitocco(); render(); } }, x.nome))),
      h("span", { classe: "tenue piccolo" }, "Un rettangolo o una selezione libera per stanza, poi a destra dici che stanza è. Muri, porte e finestre restano come sono; fuori dalle zone la pianta resta quella di prima."));
  }
  if (r.popola) {
    return h("section", { classe: "pannello compositore-ritocco", "aria-label": "Popola" },
      h("div", { classe: "riga tra" },
        h("span", {}, h("b", {}, `Popola · ${r.popola.nome}`)),
        bloccato ? null : h("button", { classe: "btn link piccolo", onclick: () => { r.popola = null; r.aree = []; r.composto = null; r.strumento = "rettangolo"; render(); } }, "Esci da Popola")),
      h("span", { classe: "tenue piccolo" }, "Passa il pennello verde dove le vuoi. Ogni tratto prende la stessa frase; fuori dal verde l'immagine resta quella di prima."));
  }
  const campo = h("textarea", {
    id: "testo-ritocco", rows: "2", classe: "compositore", "aria-label": "Cosa cambiare, con le aree chiamate @1, @2",
    placeholder: r.aree.length ? "Rivesti @1 di legno chiaro, metti persone che passeggiano in @2, togli il palo in @3" : "Prima disegna un'area sul render",
    readonly: bloccato || null, disabled: (!r.aree.length && !r.testo) || null,
  });
  campo.value = r.testo;
  campo.addEventListener("input", () => { r.testo = campo.value; componiRitocco(); });
  return h("section", { classe: "pannello compositore-ritocco", "aria-label": "Cosa cambiare" },
    campo,
    h("div", { classe: "riga menzioni" },
      r.aree.map((a, i) => h("button", {
        classe: `btn piccolo menzione ${a.azione || "cambia"}`, disabled: bloccato || null,
        title: `Mette @${i + 1} nel testo: ${nomeArea(a)}`, onclick: () => inserisciMenzione(i + 1),
      }, `@${i + 1}`)),
      h("span", { classe: "tenue piccolo" }, r.aree.length
        ? "Ogni pezzo della frase va alle aree che chiama. Un tratto «togli» che il testo non chiama toglie e basta."
        : "Disegna un'area: entra nel testo come @1.")));
}

function strumentiRitocco(spenti, ragione) {
  const r = S.ritocca;
  const voci = [["rettangolo", "Rettangolo"], ["libera", "Selezione libera"], ["aggiungi", "Pennello aggiungi"], ["togli", "Pennello togli"]];
  const aiuti = {
    rettangolo: "Rettangolo: trascina da un angolo all'altro. L'area entra nel testo come @N.",
    libera: "Selezione libera, come il lazo di Photoshop: disegna il contorno tenendo premuto; quando lasci si chiude da sola.",
    aggiungi: "Pennello aggiungi (verde): dipingi dove va una cosa nuova, come persone, alberi o un'auto.",
    togli: "Pennello togli (rosso): dipingi sopra quello che deve sparire. Il modello ricostruisce quello che sta dietro.",
  };
  const pennello = r.strumento === "aggiungi" || r.strumento === "togli";
  const [sottile, grosso] = (S.studio && S.studio.ritocco && S.studio.ritocco.pennelli) || [0.01, 0.15];
  const cursore = h("input", { type: "range", min: String(sottile), max: String(grosso), step: "0.005", value: String(spessorePennello()),
    "aria-label": "Spessore del pennello", disabled: spenti || null });
  cursore.addEventListener("input", () => { r.spessore = Number(cursore.value); });
  return h("div", { classe: "strumenti-ritocco" },
    h("div", { classe: "switch", role: "group", "aria-label": "Strumento" },
      voci.map(([id, nome]) => h("button", {
        classe: `seg strumento-${id}`, "aria-pressed": String(r.strumento === id), disabled: spenti || (r.popola && id !== "aggiungi") || (r.arreda && id !== "rettangolo" && id !== "libera") || null,
        title: r.popola && id !== "aggiungi" ? "In Popola si dipinge solo col pennello verde."
          : r.arreda && id !== "rettangolo" && id !== "libera" ? "In Arreda una zona è un rettangolo o una selezione libera." : null,
        onclick: () => { r.strumento = id; render(); },
      }, nome)),
      h("button", { classe: "seg", disabled: true, title: "Arriva con la mappa materiali di Allplan" }, "Clicca una superficie", presto())),
    pennello ? h("label", { classe: "riga piccolo spessore" }, "Spessore", cursore) : null,
    h("span", { classe: "tenue piccolo" }, spenti ? ragione : aiuti[r.strumento]));
}

function elencoAree(bloccato) {
  const r = S.ritocca;
  if (!r.aree.length) {
    return h("p", { classe: "tenue piccolo" }, "Qui ritrovi le aree, con la parte del testo che va a ognuna e il suo Rif.");
  }
  const note = r.composto ? r.composto.note_aree || [] : [];
  return h("ol", { classe: "elenco-note" }, r.aree.map((a, i) => h("li", {},
    h("div", { classe: "riga tra" },
      h("span", { classe: "piccolo" }, h("b", { classe: `numero-elenco ${a.azione || "cambia"}` }, String(i + 1)), ` ${nomeArea(a)}`),
      bloccato ? null : h("button", { classe: "btn link piccolo", onclick: () => togliArea(i) }, "Togli")),
    r.arreda ? sceltaStanza(a, bloccato) : null,
    h("span", { classe: "piccolo tenue", id: `nota-area-${i}` }, note[i] ? `«${note[i]}»` : r.arreda ? "La frase della stanza compare qui." : "La sua parte del testo compare qui."),
    bottoneImmagineNota(a, i, bloccato))));
}

// In Arreda ogni zona dice che stanza e': la frase per il modello viene da li'.
function sceltaStanza(a, bloccato) {
  const scegli = h("select", { "aria-label": "Che stanza è", disabled: bloccato || null },
    S.catalogo.pianta.stanze.map((x) => h("option", { value: x.id, selected: (a.stanza || "soggiorno") === x.id }, x.nome)));
  scegli.addEventListener("change", () => { a.stanza = scegli.value; componiRitocco(); });
  return h("label", { classe: "riga piccolo" }, "Stanza", scegli);
}

function daVerificare() {
  const modo = S.studio.ritocco;
  return h("section", { classe: "pannello", "aria-label": "Da verificare prima" },
    h("span", { classe: "etichetta" }, "Da verificare prima"),
    h("ol", { classe: "piccolo elenco-verifiche" },
      h("li", {}, "Fuori dalle aree resta il render di prima: lo Studio incolla il risultato solo nelle aree. Da vedere su un ritocco vero: che il bordo sfumato non si noti."),
      h("li", {}, `Le aree partono come ${modo.modo_nome}`, modo.origine === "SCELTA" ? ": scelta provvisoria, la fissa il piano «aree»." : "."),
      h("li", {}, "Pennelli aggiungi e togli: le parole che li spiegano al modello non sono ancora state provate su un render vero."),
      h("li", {}, "Luce e riflessi fuori dalle aree non seguono il ritocco: per un cambio di materiale grande conviene rifare il render da Genera.")));
}

function pannelloApplica(base, bloccato) {
  const r = S.ritocca;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Applica il ritocco" },
    h("span", { classe: "etichetta" }, `Aree · dal passo ${base.numero}`),
    elencoAree(bloccato),
    insertiRitocco().length ? h("p", { classe: "tenue piccolo" },
      `Partono ${1 + insertiRitocco().length} immagini: il render e ${insertiRitocco().length === 1 ? "1 Rif." : `${insertiRitocco().length} Rif.`} delle aree. Testo per il modello scelto, non ancora provato.`) : null,
    !vedePrompt() ? null : h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"), h("span", { classe: "tenue piccolo", id: "caratteri-ritocco" })),
      h("textarea", { classe: "prompt", id: "prompt-ritocco", readonly: true, "aria-label": "Prompt del ritocco" })),
    h("div", { classe: "gruppo-scelta-modello" }, h("span", { classe: "etichetta" }, "Modello"), h("div", {}, sceltaModello(r, render, "ritocca", insertiRitocco().length > 0))),
    rigaDestinazione(r.modello, S.studio.ritocco.modo === "maschera" ? "Il render, con la maschera delle aree," : "Il render, con le aree disegnate sopra,"),
    h("div", { id: "errore-ritocco" }),
    bloccato ? null : h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", id: "applica-ritocco", onclick: applicaRitocco, disabled: true }, etichettaApplica()),
      h("span", { classe: "tenue piccolo", id: "motivo-ritocco" })),
    h("p", { classe: "tenue piccolo" }, `Esce un passo nuovo sotto il passo ${base.numero}.`));
}

async function applicaRitocco() {
  const r = S.ritocca;
  r.errore = null;
  try {
    const dest = await destinazioneDi(r.modello);
    const risposta = await post("/api/ritocca/invia", { ...corpoRitocco(), modello: r.modello, destinazione_mostrata: dest && dest.destinazione });
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
    // Il prossimo ritocco parte da qui, dall'ultima immagine: non da quella
    // di prima, che non ha ancora quello che questo ritocco ha messo.
    r.da = ora.identificativo;
    r.aree = []; r.testo = ""; r.composto = null; r.errore = null; r.popola = null; r.arreda = null;
  } else {
    r.errore = { fatto: ora.stato === "annullato" ? "Il ritocco è stato annullato." : (ora.fatto || "Il ritocco non è riuscito."),
      cosa_fare: ora.stato === "annullato" ? "Aree e testo sono rimasti: puoi applicarli di nuovo." : `${ora.cosa_fare || ""} Aree e testo sono rimasti come erano: Applica li rimanda.`.trim() };
  }
}

function esitoRitocco() {
  const r = S.ritocca;
  const passo = r.esito && passoDa(r.esito);
  if (!passo || !passo.render) return null;
  const padre = passoDa(passo.da);
  const { palco, nota } = primaDopo(r, padre ? `/file/render/${padre.identificativo}` : `/file/vista/${enc(S.vista)}`,
    padre ? `Passo ${padre.numero}` : nomePrima(), `/file/render/${passo.identificativo}`, `Passo ${passo.numero}`);
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
          h("button", { classe: "btn primario", onclick: () => { r.esito = null; cambiaBaseRitocco(passo.identificativo); render(); } }, "Ritocca questo render"),
          h("button", { classe: "btn", onclick: () => { r.esito = null; r.da = padre ? padre.identificativo : null; render(); } }, "Torna al render di prima"),
          h("a", { classe: "btn", href: "#passi" }, "Vedi nei Passi"))),
      passo.avviso ? h("div", { classe: "avviso attenzione", role: "note" },
        h("b", {}, `Questo passo è la ${passo.generazioni}ª generazione di fila: gli spigoli possono spostarsi un poco a ogni giro.`),
        h("span", {}, "Se vedi l'edificio cambiare, in Passi usa «Rifai tutto dalla vista».")) : null));
}

// La misura fuori dalle aree, accanto al risultato: si legge dallo stato del
// lavoro, «non misurato» se il motore non l'ha potuta fare.
function pannelloFuoriAree(passo) {
  const m = passo.fuori_aree;
  return h("section", { classe: "pannello", "aria-label": "Fuori dalle aree" },
    h("span", { classe: "etichetta" }, "Fuori dalle aree"),
    h("span", { classe: m && m.differenza_media !== null && m.differenza_media !== undefined ? "" : "misura" }, passo.fuori_aree_testo || "Fuori dalle aree: non misurato."),
    m && m.incollato
      ? h("p", { classe: "tenue piccolo", title: "Il modello ridisegna tutta l'immagine: il suo risultato si incolla solo nelle aree, con il bordo sfumato, sul render da cui parte. Il risultato intero del modello resta nella cartella dei lavori, accanto al render." },
        "Cambiano solo le aree.")
      : nota("Confronto con il render da cui parte.", "Confronto pixel per pixel con il render da cui parte, senza le aree e una fascia stretta intorno. Serve a vedere se il modello ha toccato il resto, il giudizio resta tuo sul prima/dopo."),
    passo.modo_aree_nome ? h("p", { classe: "tenue piccolo" }, `Aree mandate come ${passo.modo_aree_nome}.`) : null);
}

// Con `popola` (da Popola · Dipingo io) si dipinge solo col verde, senza testo:
// ogni tratto prende la frase di Popola. Con `arreda` (da una pianta) ogni zona
// e' un rettangolo o una selezione libera con la sua stanza.
function ritoccaDa(passo, popola, arreda) {
  const r = S.ritocca;
  if (r.da !== passo.identificativo || popola || r.popola || arreda || r.arreda) { r.aree = []; r.testo = ""; r.composto = null; r.errore = null; }
  r.popola = popola || null;
  r.arreda = arreda || null;
  if (popola) r.strumento = "aggiungi";
  if (arreda) r.strumento = "rettangolo";
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
      strumentiRitocco(bloccato, "Bloccati mentre il ritocco è in corso: aree e testo restano come li hai mandati."),
      attivo ? h("div", { classe: "striscia in-riga", role: "status" },
        h("div", { classe: "riga tra" }, h("span", {}, h("b", {}, (attivo.destinazione || "").split(" (")[0]), ` · ${attivo.stato}`), h("span", { classe: "mono" }, tempo(attivo.secondi))),
        h("div", { classe: "barra" }, h("span")),
        h("div", { classe: "riga tra" }, h("span", { classe: "piccolo" }, "Allplan e il resto dello Studio restano liberi."), h("button", { classe: "btn", onclick: annulla }, "Annulla"))) : null,
      telaRitocco(base),
      compositoreRitocco(bloccato)),
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
  if (!modello || modello === "caricata") return null;  // l'immagine caricata non va da nessuna parte
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
  p.nuovo = { da: passo.identificativo, testo: "", scelte: [], modello: modelloVerificato(passo.modello), composto: null, errore: null, inserti: [] };
  await destinazioneDi(p.nuovo.modello);
  render();
  const campo = document.getElementById("testo-passo");
  if (campo) campo.focus();
}

let attesaPasso = null;
function componiNuovoPasso() {
  const n = S.passi.nuovo;
  clearTimeout(attesaPasso);
  if (!n || (!n.testo.trim() && !n.scelte.length)) { if (n) { n.composto = null; disegnaNuovoPasso(); } return; }
  attesaPasso = setTimeout(async () => {
    try {
      n.composto = await post("/api/passi/componi", { vista: S.vista, da: n.da, testo: n.testo, variazioni: n.scelte, modello: n.modello, inserti: n.inserti.map((r) => r.nome) });
      n.errore = null;
    }
    catch (e) { n.composto = null; n.errore = e; }
    disegnaNuovoPasso();
  }, 250);
}

// Aggiorna solo il prompt e il pulsante mentre si scrive, senza ridisegnare
// la pagina: il campo di testo non perde il cursore.
function disegnaNuovoPasso() {
  const n = S.passi.nuovo;
  if (!n) return;
  const c = n.composto;
  const prompt = document.getElementById("prompt-passo");
  if (prompt) prompt.value = !c ? "" : c.prompts.length > 1 ? c.prompts.map((x) => `— ${x.nome} —\n${x.prompt}`).join("\n\n") : c.prompt;
  const car = document.getElementById("caratteri-passo");
  if (car) car.textContent = !c ? "" : c.prompts.length > 1 ? `${c.prompts.length} prompt` : `${c.caratteri} caratteri`;
  const costo = document.getElementById("costo-cambia");
  if (costo) costo.textContent = c && c.invii > 1 && c.costo ? `Partono ${c.invii} invii, uno per scelta. Costo: ${c.costo}.` : "";
  const err = document.getElementById("errore-passo");
  if (err) err.replaceChildren(n.errore ? avviso("errore", n.errore.fatto, n.errore.cosa_fare) : "");
  const bottone = document.getElementById("applica-passo");
  if (bottone) { bottone.disabled = (!n.testo.trim() && !n.scelte.length) || !!S.lavoroAttivo; bottone.textContent = n.scelte.length > 1 ? `Applica ${n.scelte.length}` : "Applica"; }
  const motivo = document.getElementById("motivo-applica");
  if (motivo) motivo.textContent = motivoApplicaSpento();
}

function motivoApplicaSpento() {
  const n = S.passi.nuovo;
  if (S.lavoroAttivo) return "Un lavoro è in corso: Applica si accende quando finisce, così un doppio clic non si paga due volte.";
  if (!n || (!n.testo.trim() && !n.scelte.length)) return "Scegli una miniatura o scrivi cosa cambiare: un passo senza richiesta non cambia niente.";
  return "";
}

async function applicaPasso() {
  const n = S.passi.nuovo;
  S.errore = null;
  try {
    const dest = await destinazioneDi(n.modello);
    const risposta = await post("/api/passi/invia", {
      vista: S.vista, da: n.da, testo: n.testo, variazioni: n.scelte, modello: n.modello, destinazione_mostrata: dest && dest.destinazione,
      inserti: n.inserti.map((r) => r.nome),
    });
    S.passi.nuovo = null;
    S.passi.scelto = risposta.identificativo;
    // Piu' scelte: si seguono una dopo l'altra e si confrontano nella griglia dei Passi.
    S.inFila = risposta.identificativi.slice(1);
    seguiLavoro(await get(`/api/lavori/${risposta.identificativo}`));
    if (risposta.identificativi.length > 1) { S.passi.modo = "griglia"; if (S.scheda !== "passi") location.hash = "#passi"; }
    await caricaPassi();
    if (S.scheda === "risultato") await caricaRender();
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
      h("div", { classe: "riga tra" }, h("span", { classe: "piccolo" }, SUL_WEB ? "" : "Allplan resta libero."), h("button", { classe: "btn", onclick: annulla }, "Annulla"))) : null,
    h("button", {
      classe: "btn link piccolo", disabled: !passo.si_parte, title: passo.motivo_non_si_parte || null,
      onclick: () => apriNuovoPasso(passo),
    }, "Cambia"));
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
          h("span", { classe: "testo-passo" }, h("span", {}, h("b", { classe: "numero" }, "0"), ` ${nomePrima()}`),
            h("small", {}, dati ? `cattura del ${data(dati.catturata_il)}` : ""))),
        h("a", { classe: "btn link piccolo", href: "#genera", title: "Dalla vista si parte da Genera: lì scegli lo stile." }, "Genera")),
      passi.map(rigaPasso)),
    passi.length
      ? nota("Ogni passo parte da quello sopra.", "Ogni passo parte da quello sopra di lui. Un passo nuovo fatto da un punto qualsiasi apre un ramo lì sotto.")
      : h("div", { classe: "vuoto-passi" },
        h("p", {}, "Nessun passo ancora. Genera un render da Genera: sarà il passo 1."),
        h("a", { classe: "btn", href: "#genera" }, "Vai a Genera")));
}

function palcoPassi(passo) {
  const p = S.passi;
  if (!passo) {
    return h("div", { classe: "palco" },
      h("h1", {}, `${nomePrima()} · passo 0`),
      h("p", { classe: "tenue" }, "Il punto di partenza di tutti i passi. Da qui si parte da Genera."),
      h("figure", { classe: "riquadro-vista" }, h("img", { src: `/file/vista/${enc(S.vista)}`, alt: nomePrima(), stile: "max-height:none" })));
  }
  const titolo = h("div", {}, h("h1", {}, `Passo ${passo.numero} · ${passo.nome}`), passo.immaginata ? avvisoImmaginata() : null);
  const confronto = modiConfronto(passo);
  if (confronto.modo === "griglia") return palcoGriglia(passo, confronto.fratelli, titolo, confronto.modi);
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
  const nomeA = contro === "prima" ? `Passo ${padre.numero}` : nomePrima();
  const srcB = `/file/render/${passo.identificativo}`;
  const nomeB = `Passo ${passo.numero}`;
  const { fratelli, modo, modi } = modiConfronto(passo);
  const scegliA = h("select", { "aria-label": "Confronta con" },
    h("option", { value: "vista", selected: contro === "vista" }, `${nomePrima()} (passo 0)`),
    h("option", { value: "prima", selected: contro === "prima", disabled: !primaPossibile },
      padre ? `Passo prima (passo ${padre.numero})${primaPossibile ? "" : ": il suo render non c'è più"}` : "Passo prima: è la vista"));
  scegliA.addEventListener("change", () => { p.confronto = scegliA.value; render(); });
  let palco, nota = null;
  if (modo === "scorri") ({ palco, nota } = primaDopo(p, srcA, nomeA, srcB, nomeB));
  else {
    palco = h("div", { classe: "affiancati" },
      h("figure", {}, h("img", { src: srcA, alt: nomeA }), h("figcaption", { classe: "tenue piccolo" }, nomeA)),
      h("figure", {}, h("img", { src: srcB, alt: nomeB }), h("figcaption", { classe: "tenue piccolo" }, nomeB)));
  }
  return h("div", { classe: "palco" },
    h("div", { classe: "riga tra" }, titolo, modi),
    h("div", { classe: "riga" }, h("span", { classe: "etichetta" }, "Confronta con"), h("div", { stile: "min-width:240px" }, scegliA)),
    palco,
    modo === "scorri" ? h("div", { classe: "riga tra" },
      h("span", { classe: "tenue piccolo" }, "Trascina la linea, oppure tasti ← → (con Maiusc il passo è più lungo)"),
      h("span", { classe: "mono", id: "valore-linea" }, `${Math.round(p.x)}%`)) : null,
    nota);
}

// I fratelli: i passi nati dallo stesso render, come le scelte di un Cambia.
// Con piu' d'uno, il confronto ha anche la griglia.
function modiConfronto(passo) {
  const p = S.passi;
  const fratelli = p.dati.passi.filter((x) => x.da === passo.da);
  const modo = p.modo === "griglia" && fratelli.length < 2 ? "scorri" : p.modo;
  const voci = [["scorri", "Prima / dopo"], ["affiancati", "Affiancati"]];
  if (fratelli.length > 1) voci.push(["griglia", `Griglia (${fratelli.length})`]);
  const modi = h("div", { classe: "switch", role: "group", "aria-label": "Modo di confronto" },
    voci.map(([id, n]) =>
      h("button", { classe: "seg", "aria-pressed": String(modo === id), onclick: () => { p.modo = id; render(); } }, n)));
  return { fratelli, modo, modi };
}

// La griglia: il render di partenza e tutti i passi nati da lui, affiancati.
// Un clic sceglie quello da tenere per andare avanti; gli altri restano
// nell'albero, niente si perde.
function palcoGriglia(passo, fratelli, titolo, modi) {
  const p = S.passi;
  const padre = passo.da !== "0" ? passoDa(passo.da) : null;
  const partenza = padre && padre.render ? `/file/render/${padre.identificativo}` : `/file/vista/${enc(S.vista)}`;
  const cella = (x) => {
    const attivo = S.lavoroAttivo && S.lavoroAttivo.identificativo === x.identificativo;
    return h("button", { classe: "cella-griglia", "aria-current": String(x.identificativo === passo.identificativo),
      // Il clic apre subito il prima/dopo di quella scelta: la griglia serve a
      // scegliere, il confronto A/B col render di partenza resta quello di sempre.
      onclick: () => { p.scelto = x.identificativo; p.confronto = "prima"; p.modo = "scorri"; render(); } },
      x.render ? h("img", { src: `/file/render/${x.identificativo}`, alt: x.nome })
        : h("span", { classe: "posto-griglia" }, attivo || x.attivo ? `${x.stato}…` : x.stato === "errore" ? "non riuscito" : x.stato || "—"),
      h("span", { classe: "piccolo" }, h("b", { classe: "numero" }, x.numero), " ", x.nome));
  };
  return h("div", { classe: "palco" },
    h("div", { classe: "riga tra" }, titolo, modi),
    h("p", { classe: "tenue piccolo" }, `Partono tutti da ${padre ? `passo ${padre.numero}` : nomePrima()}. Clic su uno per vederlo in prima/dopo col render di partenza e andare avanti da lì: gli altri restano nell'albero.`),
    h("div", { classe: "griglia-confronto" },
      h("figure", { classe: "cella-griglia partenza" }, h("img", { src: partenza, alt: "Partenza" }),
        h("figcaption", { classe: "piccolo tenue" }, padre ? `Partenza · passo ${padre.numero}` : `Partenza · ${nomePrima()}`)),
      fratelli.map(cella)));
}

function rigaDestinazione(modello, cosaParte) {
  const d = S.passi.dest[modello];
  if (!d) return h("p", { classe: "tenue piccolo" }, "Leggo la destinazione…");
  return h("p", { classe: "destinazione" }, `${cosaParte || "La vista"} va a `, h("b", {}, d.destinazione),
    d.senza_ripiego ? ", senza ripiego su altri servizi" : "", `. Costo: ${d.costo}.`);
}

function sceltaModello(stato, onCambio, dove, piuImmagini) {
  return schedeModello(dove || "passi", stato.modello, !!piuImmagini,
    async (id) => { stato.modello = id; await destinazioneDi(stato.modello); onCambio(); });
}

// La scelta del modello: schede raggruppate per categoria, ognuna con una riga
// su a cosa serve e la spunta su quella scelta. Chiusa mostra solo la scelta.
// Le righe sono giudizi (SCELTA), non confronti misurati: lo si scrive.
// Un modello a una sola immagine resta visibile ma spento quando l'invio ne
// manda piu' d'una, con il perche' scritto sulla scheda.
const modelliAperti = new Set();
function schedeModello(dove, sceltoId, servePiuImmagini, onScegli) {
  const aperta = modelliAperti.has(dove);
  const tutti = S.catalogo.modelli;
  const scelto = tutti.find((m) => m.id === sceltoId);
  const scheda = (m) => {
    const perche = !m.verificato ? "Questo modello non è ancora disponibile per l'invio."
      : servePiuImmagini && !m.piu_immagini ? "Riceve una sola immagine: questo invio ne manda più d'una." : "";
    const attiva = m.id === sceltoId;
    return h("button", {
      classe: "scheda-modello", role: "radio", "aria-checked": String(attiva), disabled: (!!perche && !attiva) || null,
      onclick: async () => { modelliAperti.delete(dove); if (!attiva) await onScegli(m.id); else render(); },
    },
      h("span", { classe: "spunta", "aria-hidden": "true" }, attiva ? "✓" : ""),
      h("span", { classe: "corpo-modello" },
        h("span", { classe: "riga-modello" }, h("b", {}, m.nome), h("span", { classe: "tenue piccolo" }, ` · ${m.fornitore}`),
          m.id === S.studio.modello_predefinito ? h("span", { classe: "etichetta-modello" }, "predefinito") : null),
        h("span", { classe: "piccolo" }, m.spiega),
        h("span", { classe: "tenue piccolo" }, m.piu_immagini ? "Più immagini per invio" : "Una sola immagine per invio",
          m.costo && m.costo.startsWith("circa") ? ` · ${m.costo.split(" · ")[0]}` : " · costo non misurato"),
        perche ? h("span", { classe: "piccolo", stile: "color:var(--attenzione)" }, perche) : null));
  };
  if (!aperta) {
    return h("div", { classe: "scelta-modello", role: "radiogroup", "aria-label": "Modello" },
      scelto ? scheda(scelto) : h("p", { classe: "tenue piccolo" }, "Nessun modello scelto."),
      h("button", { classe: "btn link piccolo", onclick: () => { modelliAperti.add(dove); render(); } },
        `Cambia modello (${tutti.length - (scelto ? 1 : 0)} altri)`));
  }
  const categorie = S.catalogo.categorie_modelli || [];
  return h("div", { classe: "scelta-modello aperta", role: "radiogroup", "aria-label": "Modello" },
    categorie.map((c) => {
      const del_gruppo = tutti.filter((m) => m.categoria === c.id);
      if (!del_gruppo.length) return null;
      return h("div", { classe: "gruppo-modelli" },
        h("span", { classe: "etichetta" }, c.nome, spiega(c.spiega)),
        del_gruppo.map(scheda));
    }),
    tutti.filter((m) => !categorie.some((c) => c.id === m.categoria)).map(scheda),
    S.catalogo.modelli_non_provati.map((n) => h("p", { classe: "tenue piccolo" }, `${n} · non ancora provato`)),
    h("button", { classe: "btn link piccolo", onclick: () => { modelliAperti.delete(dove); render(); } }, "Chiudi"));
}

// Cambia: miniature disegnate in due righe, «Ora del giorno» e «Tempo e mood»
// (bozza «flussi», 2026-11-09). Piu' scelte insieme = un passo per scelta,
// fratelli nell'albero, da confrontare nella griglia. Il campo libero si
// aggiunge a ogni scelta, o da solo fa un passo come prima. Le miniature sono
// disegni, non render: dicono l'idea. Testi per il modello scelti, non provati.
const DISEGNO_CAMBIA = {
  alba: { c1: "#F2B8A0", c2: "#F8E3C8", ombra: 0.12 },
  mattino: {},
  mezzogiorno: { c1: "#5E9DD8", ombra: 0.35 },
  tramonto: { c1: "#E58A5B", c2: "#F6C98F", ombra: 0.2 },
  ora_blu: { c1: "#1E2E5A", c2: "#5C6F9C", luci: true, sole: false, ombra: 0.05, terra: "#4B5A48", muro: "#B9B6C4" },
  notte: { c1: "#0B1020", c2: "#1E2740", luci: true, sole: false, ombra: 0, terra: "#2B3328", muro: "#6C6A72" },
  nuvoloso: { c1: "#A9B1BA", c2: "#D3D7DB", sole: false, ombra: 0.06 },
  pioggia: { c1: "#7D8790", c2: "#A9B0B6", sole: false, ombra: 0.03, terra: "#6E7E66", pioggia: true },
  neve: { c1: "#C9D2DA", c2: "#EEF1F4", sole: false, terra: "#F2F4F6", ombra: 0.05, tetto: "#F2F4F6" },
  nebbia: { c1: "#C9CDD1", c2: "#E2E4E6", sole: false, nebbia: 0.45, ombra: 0.03 },
  drammatico: { c1: "#3D4654", c2: "#C98C5A", ombra: 0.5 },
  nordico: { c1: "#9FB8CC", c2: "#E4ECF1", ombra: 0.15, terra: "#7F9472" },
  luci_accese: { luci: true },
};
let gradientiCambia = 0;
function disegnoCambia(id) {
  const o = Object.assign({ c1: "#8DB7DE", c2: "#DCE8F0", muro: "#E9E4DA", tetto: "#5B5F66", vetro: "#7E99B0", terra: "#8FA67A",
    luci: false, ombra: 0.25, nebbia: 0, sole: true, pioggia: false }, DISEGNO_CAMBIA[id] || {});
  const g = `cielo-cambia-${gradientiCambia++}`;
  const vetri = o.luci ? "#F4C66A" : o.vetro;
  return `<svg viewBox="0 0 640 400" aria-hidden="true"><defs><linearGradient id="${g}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${o.c1}"/><stop offset="1" stop-color="${o.c2}"/></linearGradient></defs>`
    + `<rect width="640" height="400" fill="url(#${g})"/>`
    + (o.sole ? `<circle cx="520" cy="80" r="26" fill="#FFF3C4" opacity=".85"/>` : "")
    + `<rect y="300" width="640" height="100" fill="${o.terra}"/><rect y="292" width="640" height="10" fill="#C9C2B4"/>`
    + `<polygon points="170,300 470,300 520,330 140,330" fill="#000" opacity="${o.ombra}"/>`
    + `<rect x="170" y="170" width="300" height="130" fill="${o.muro}"/><rect x="300" y="110" width="170" height="60" fill="${o.muro}"/>`
    + `<rect x="290" y="100" width="190" height="12" fill="${o.tetto}"/><rect x="160" y="160" width="140" height="12" fill="${o.tetto}"/>`
    + `<rect x="200" y="200" width="70" height="70" fill="${vetri}"/><rect x="320" y="200" width="120" height="100" fill="${vetri}"/>`
    + `<rect x="330" y="125" width="110" height="34" fill="${vetri}"/><rect x="380" y="200" width="3" height="100" fill="#3A3D44"/>`
    + `<ellipse cx="90" cy="250" rx="46" ry="62" fill="#4E7044"/><rect x="86" y="280" width="8" height="24" fill="#5A4636"/>`
    + `<ellipse cx="560" cy="262" rx="36" ry="48" fill="#557A4A"/><rect x="556" y="288" width="8" height="16" fill="#5A4636"/>`
    + (o.pioggia ? `<g stroke="#E6ECF2" stroke-width="2" opacity=".6">${Array.from({ length: 24 }, (_x, i) => `<line x1="${i * 28}" y1="${(i * 53) % 260}" x2="${i * 28 - 8}" y2="${(i * 53) % 260 + 30}"/>`).join("")}</g>` : "")
    + (o.nebbia ? `<rect width="640" height="400" fill="#E6E9EC" opacity="${o.nebbia}"/>` : "")
    + `</svg>`;
}

function miniaturaCambia(voce, n) {
  const scelta = n.scelte.includes(voce.id);
  const pieno = !scelta && n.scelte.length >= S.catalogo.cambia.massime;
  const quadro = h("span", { classe: "quadro-mini" });
  quadro.innerHTML = disegnoCambia(voce.id);
  return h("button", {
    classe: "mini-cambia", "aria-pressed": String(scelta), disabled: pieno || null,
    title: pieno ? `Al massimo ${S.catalogo.cambia.massime} scelte per clic.` : null,
    onclick: () => {
      n.scelte = scelta ? n.scelte.filter((x) => x !== voce.id) : [...n.scelte, voce.id];
      componiNuovoPasso(); render();
    },
  }, quadro, h("span", {}, voce.nome));
}

function pannelloNuovoPasso() {
  const n = S.passi.nuovo;
  const da = passoDa(n.da);
  if (!da) return null;
  const cambia = S.catalogo.cambia;
  const voci = cambia.voci.filter((v) => v.scene.includes(da.scena || "esterno"));
  const campo = h("textarea", { id: "testo-passo", rows: "2",
    placeholder: n.scelte.length ? "In più, in ognuna (facoltativo): «con le luci del portico accese»" : "Oppure a parole: «di notte, con le luci accese»" });
  campo.value = n.testo;
  campo.addEventListener("input", () => { n.testo = campo.value; componiNuovoPasso(); disegnaNuovoPasso(); });
  const quante = n.scelte.length;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Cambia" },
    h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "Cambia tutta l'immagine"),
      h("button", { classe: "btn link", onclick: () => { S.passi.nuovo = null; render(); } }, "Chiudi")),
    h("p", { classe: "piccolo" }, `Spigoli, arredo e inquadratura restano, cambiano luce e atmosfera. Escono passi nuovi sotto il passo ${da.numero}.`),
    voci.length ? cambia.gruppi.map((g) => {
      const del_gruppo = voci.filter((v) => v.gruppo === g.id);
      return del_gruppo.length ? h("div", { classe: "gruppo-mini", role: "group", "aria-label": g.nome },
        h("span", { classe: "etichetta" }, g.nome),
        h("div", { classe: "miniature-cambia" }, del_gruppo.map((v) => miniaturaCambia(v, n)))) : null;
    }) : h("p", { classe: "tenue piccolo" }, "Per un pezzo d'arredo non ci sono miniature: scrivi cosa cambiare."),
    voci.length ? h("p", { classe: "tenue piccolo" },
      `Miniature disegnate, non render: dicono l'idea. Puoi sceglierne fino a ${cambia.massime}; ognuna è un passo e un invio. Alla fine le confronti nella griglia dei Passi.`) : null,
    campo,
    h("p", { classe: "tenue piccolo" }, quante ? "Il testo, se lo scrivi, si aggiunge a ogni scelta." : "Solo una parte? Usa Ritocca."),
    pannelloInserti(n.inserti, S.catalogo.modelli.find((m) => m.id === n.modello), "Cambia", () => { componiNuovoPasso(); render(); }),
    !vedePrompt() ? null : h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, "Il prompt che parte, in inglese"), h("span", { classe: "tenue piccolo", id: "caratteri-passo" })),
      h("textarea", { classe: "prompt", id: "prompt-passo", readonly: true, "aria-label": "Prompt del passo" })),
    h("div", { classe: "gruppo-scelta-modello" }, h("span", { classe: "etichetta" }, "Modello"), h("div", {}, sceltaModello(n, () => { componiNuovoPasso(); render(); }, "cambia", n.inserti.length > 0))),
    rigaDestinazione(n.modello),
    h("p", { classe: "destinazione", id: "costo-cambia" }),
    h("div", { id: "errore-passo" }),
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", id: "applica-passo", onclick: applicaPasso, disabled: true }, quante > 1 ? `Applica ${quante}` : "Applica"),
      h("span", { classe: "tenue piccolo", id: "motivo-applica" })));
}

function pannelloPulito(passo) {
  const q = S.passi.pulito;
  const c = q.composto;
  if (q.errore && !c) {
    return h("section", { classe: "pannello evidenziato" }, avviso("errore", q.errore.fatto, q.errore.cosa_fare),
      h("button", { classe: "btn", onclick: () => { S.passi.pulito = null; render(); } }, "Chiudi"));
  }
  if (!c) return h("section", { classe: "pannello evidenziato" }, h("p", { classe: "tenue" }, "Unisco le richieste della strada…"));
  const prompt = h("textarea", { classe: "prompt", readonly: true, "aria-label": "Prompt di Rifai tutto dalla vista" });
  prompt.value = c.prompt;
  return h("section", { classe: "pannello evidenziato", "aria-label": "Rifai tutto dalla vista" },
    h("span", { classe: "etichetta" }, `Rifai tutto dalla vista · strada ${c.strada.join(" › ")}`),
    h("p", { classe: "piccolo" }, `Un solo invio dalla vista Allplan, una generazione invece di ${c.generazioni}. Il risultato è un ramo nuovo sotto lo 0.`),
    h("dl", { classe: "ricetta" },
      h("dt", {}, "Stile"), h("dd", {}, c.riassunto),
      h("dt", {}, "Richieste"), h("dd", {}, c.richieste.join(" · "))),
    c.senza_aree && c.senza_aree.length ? avviso("attenzione",
      `Le note del ritocco ${c.senza_aree.length === 1 ? "al passo" : "ai passi"} ${c.senza_aree.join(", ")} entrano come richieste a parole, senza le loro aree.`,
      "Dalla vista le aree non valgono più: erano disegnate su un render. Il modello non sa più dove fare quelle modifiche; se servono lì, ritocca dopo.") : null,
    vedePrompt() ? h("span", { classe: "piccolo tenue" }, `Il prompt che parte, in inglese · ${c.caratteri} caratteri`) : null,
    vedePrompt() ? prompt : null,
    h("div", { classe: "gruppo-scelta-modello" }, h("span", { classe: "etichetta" }, "Modello"), h("div", {}, sceltaModello(q, render, "pulito", false))),
    rigaDestinazione(q.modello),
    q.errore ? avviso("errore", q.errore.fatto, q.errore.cosa_fare) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", onclick: inviaPulito, disabled: !!S.lavoroAttivo }, "Conferma e invia"),
      h("button", { classe: "btn", onclick: () => { S.passi.pulito = null; render(); } }, "Chiudi")),
    S.lavoroAttivo ? h("span", { classe: "tenue piccolo" }, "Un lavoro è in corso: si può inviare quando finisce.") : null);
}

function ricettaPasso(passo) {
  const padre = passo.da !== "0" ? passoDa(passo.da) : null;
  const righe = [
    ["Strada", passo.strada.join(" › ")],
    ["Parte da", passo.da === "0" ? `${nomePrima()} (passo 0)`
      : `Passo ${passo.da_numero}${passo.partenza_mancante ? ": il punto di partenza non c'è più" : ""}`],
    ["Richiesta", passo.riassunto],
    ["Modello", passo.modello_nome],
    ["Servizio", passo.destinazione || "—"],
    ["Costo", passo.costo],
    ["Data", data(passo.creato_il)],
    ["Blocchi", passo.versione_blocchi || "—"],
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
    passo.prompt && vedePrompt() ? h("details", { classe: "dettagli" }, h("summary", {}, h("span", { classe: "piccolo" }, `Il prompt, in inglese${passo.prompt_a_mano ? " · scritto a mano" : ""}`)), prompt) : null,
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
      h("span", {}, "Se vedi l'edificio cambiare, usa «Rifai tutto dalla vista» qui sotto.")));
  }
  if (passo.partenza_mancante) {
    blocchi.push(avviso("errore", "Il punto di partenza non c'è più: il render del passo prima è stato tolto dalla cartella.",
      "Usa «Rifai tutto dalla vista»: riparte dalla vista Allplan con le stesse richieste."));
  }
  blocchi.push(corpoTenuta(passo.tenuta, null,
    "Si misura sempre contro la vista Allplan, non contro il passo prima: così lo spostamento che si accumula passo dopo passo si vede tutto. Misura grezza: ombre e vegetazione nuove contano come spigoli persi."));
  if (passo.aree && passo.aree.length && passo.render) blocchi.push(pannelloFuoriAree(passo));
  if (p.pulito && p.pulito.passo === passo.identificativo) blocchi.push(pannelloPulito(passo));
  // La stessa barra di Risultato (2026-11-04): Cambia · Ritocca · Variante ·
  // Ricetta · Video. «Rifai tutto dalla vista» solo quando serve.
  const serve = passo.avviso || passo.partenza_mancante;
  blocchi.push(h("section", { classe: "pannello", "aria-label": "Da questa immagine" },
    passo.render ? barraAzioni(comeLavoro(passo)) : null,
    serve && passo.generazioni > 1 ? h("div", { classe: "azioni" },
      h("button", { classe: "btn primario", disabled: !!S.lavoroAttivo || null, onclick: () => apriPulito(passo) }, "Rifai tutto dalla vista"),
      spiega(`Unisce le richieste dei passi ${passo.strada.slice(1).join(", ")} in un solo invio dalla vista Allplan: una generazione invece di ${passo.generazioni}, gli spigoli tornano quelli della vista.`)) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: "btn link piccolo", onclick: () => post("/api/apri-cartella", { quale: "render" }).catch((e) => { S.errore = e; render(); }) }, "Apri cartella"))));
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


// --- Studio · Video ------------------------------------------------------------
// Un video da uno o piu' render: si caricano o arrivano da Risultato. Il modello
// e' Seedance 2.5 via Comfy Router, mai provato con una chiamata vera: lo si dice.

let giroVideo = null;
async function caricaVideo() {
  const v = S.video;
  try {
    if (!v.catalogo) {
      v.catalogo = await get("/api/video/catalogo");
      v.durata = v.durata || v.catalogo.durate[0];
      v.risoluzione = v.risoluzione || v.catalogo.risoluzioni[0];
    }
    v.voci = await get("/api/video");
    v.caricato = true;
  } catch (e) { v.errore = e; }
  clearInterval(giroVideo);
  if (v.voci.some((x) => x.stato === "in coda" || x.stato === "inviato")) {
    giroVideo = setInterval(async () => {
      if (S.scheda !== "video") return;
      try { S.video.voci = await get("/api/video"); } catch (e) { return; }
      if (!S.video.voci.some((x) => x.stato === "in coda" || x.stato === "inviato")) clearInterval(giroVideo);
      render();
    }, 3000);
  }
}

function videoModo() { return S.video.catalogo && S.video.catalogo.modi.find((m) => m.id === S.video.modo); }

function postiPer(modo, posti) {
  const m = S.video.catalogo.modi.find((x) => x.id === modo);
  const pieni = posti.filter(Boolean);
  const quanti = Math.max(m.minimo, Math.min(m.massimo, pieni.length || 1));
  return Array.from({ length: quanti }, (_, i) => pieni[i] || null);
}

async function videoDa(identificativo) {
  location.hash = "#video";
  await caricaVideo();
  const v = S.video;
  const voce = { render: identificativo };
  const vuoto = v.posti.indexOf(null);
  if (vuoto >= 0) v.posti[vuoto] = voce; else v.posti = [voce];
  v.secco = null;
  render();
}

function srcPosto(voce) {
  if (!voce) return null;
  return voce.render ? `/file/render/${enc(voce.render)}` : `/file/immagine-video/${enc(voce.caricata)}`;
}

function postoVideo(indice, titolo) {
  const v = S.video;
  const voce = v.posti[indice];
  const file = h("input", { type: "file", accept: "image/png,image/jpeg", classe: "nascosto", "aria-label": `Carica un render: ${titolo}` });
  file.addEventListener("change", async () => {
    const scelto = file.files[0];
    if (!scelto) return;
    v.errore = null; v.caricando = true; render();
    try {
      const r = await post("/api/video/immagini", scelto, { "Content-Type": "application/octet-stream", "X-Nome-File": encodeURIComponent(scelto.name) });
      v.posti[indice] = { caricata: r.nome, da: r.da || scelto.name };
      v.secco = null;
    } catch (e) { v.errore = e; }
    v.caricando = false;
    render();
  });
  const togli = () => { v.posti[indice] = null; if (v.modo === "riferimenti" && v.posti.length > 1) v.posti.splice(indice, 1); v.secco = null; render(); };
  return h("div", { classe: "posto-video" },
    h("span", { classe: "etichetta" }, titolo),
    voce ? h("img", { src: srcPosto(voce), alt: titolo }) : h("div", { classe: "posto-vuoto" }, "Nessuna immagine"),
    voce ? h("span", { classe: "piccolo tenue" }, voce.render ? `Render ${voce.render}` : (voce.da || voce.caricata)) : null,
    h("div", { classe: "azioni" },
      h("button", { classe: v.scegliPer === indice ? "btn primario" : "btn", "aria-expanded": String(v.scegliPer === indice),
        onclick: () => { v.scegliPer = v.scegliPer === indice ? null : indice; render(); } }, "Dai render"),
      h("button", { classe: "btn", onclick: () => file.click(), disabled: v.caricando }, "Da file…"),
      voce ? h("button", { classe: "btn", onclick: togli }, "Togli") : null),
    file);
}

// I render fatti, di tutte le viste, da scegliere per un posto del video:
// le stesse immagini dello storico, senza viste e video.
function sceltaDaiRender(indice) {
  const v = S.video;
  const voci = S.storico.gruppi.flatMap((g) => g.voci).filter((x) => x.immagine && x.tipo !== "cattura" && x.tipo !== "video");
  if (!voci.length) return h("p", { classe: "tenue piccolo" }, "Nessun render ancora: generane uno da Genera.");
  return h("div", { classe: "griglia-render-video", role: "group", "aria-label": "Scegli un render" },
    voci.slice().reverse().map((x) => h("button", {
      classe: "voce-storico", title: `${x.etichetta}${x.numero ? " " + x.numero : ""} · ${x.vista}`,
      "aria-current": String(!!(v.posti[indice] && v.posti[indice].render === x.identificativo)),
      onclick: () => { v.posti[indice] = { render: x.identificativo }; v.scegliPer = null; v.secco = null; render(); },
    }, h("span", { classe: "quadro" }, h("img", { src: `/file/render/${enc(x.identificativo)}`, alt: "", loading: "lazy" })),
      h("span", { classe: "didascalia" }, x.numero ? `${x.etichetta} ${x.numero}` : x.etichetta))));
}

function corpoVideo() {
  const v = S.video;
  return { immagini: v.posti.filter(Boolean), modo: v.modo, movimento: v.movimento, testo: v.testo,
           durata: v.durata, risoluzione: v.risoluzione, audio: v.audio };
}

function motivoVideoSpento() {
  const v = S.video;
  const m = videoModo();
  const pieni = v.posti.filter(Boolean).length;
  if (!pieni) return "Carica il render da cui partire, oppure in Risultato premi Video sotto l'immagine.";
  if (m && pieni < m.minimo) return `«${m.nome}» vuole ${m.minimo} immagini: ne manca ${m.minimo - pieni}.`;
  if (!v.catalogo.fa_video) return "Il servizio scelto non fa video.";
  if (v.voci.some((x) => x.stato === "in coda" || x.stato === "inviato")) return "Un video è già in lavorazione: aspetta che finisca o annullalo.";
  return null;
}

async function provaASeccoVideo() {
  S.video.errore = null;
  try { S.video.secco = await post("/api/video/prova-a-secco", corpoVideo()); } catch (e) { S.video.errore = e; S.video.secco = null; }
  render();
}

async function generaVideo() {
  const v = S.video;
  v.errore = null; v.secco = null;
  try {
    await post("/api/video/invia", { ...corpoVideo(), destinazione_mostrata: v.catalogo.destinazione });
    await caricaVideo();
  } catch (e) { v.errore = e; }
  render();
}

async function annullaVideo(id) {
  try { await post(`/api/video/${enc(id)}/annulla`, {}); await caricaVideo(); } catch (e) { S.video.errore = e; }
  render();
}

function colonnaImmaginiVideo() {
  const v = S.video;
  const c = v.catalogo;
  const m = videoModo();
  const titoli = v.modo === "primo-ultimo" ? ["Primo fotogramma", "Ultimo fotogramma"]
    : v.modo === "sequenza" ? ["Inizio", "Intermezzo", "Fine"]
    : v.modo === "primo" ? ["Il render da cui parte"] : v.posti.map((_, i) => `Riferimento ${i + 1}`);
  return h("div", { classe: "colonna-stile" },
    h("section", { classe: "pannello", "aria-label": "Come partire" },
      h("span", { classe: "etichetta" }, "Come partire", m ? spiega(m.spiega) : null),
      h("div", { classe: "switch", role: "group", "aria-label": "Come partire" },
        c.modi.map((x) => h("button", { classe: "seg", "aria-pressed": String(v.modo === x.id),
          onclick: () => { v.modo = x.id; v.posti = postiPer(x.id, v.posti); v.secco = null; render(); } }, x.nome))),
      h("div", { classe: "posti-video" }, titoli.map((t, i) => postoVideo(i, t))),
      v.scegliPer !== null && v.scegliPer < titoli.length
        ? [h("span", { classe: "etichetta" }, `Scegli: ${titoli[v.scegliPer]}`), sceltaDaiRender(v.scegliPer)] : null,
      v.modo === "riferimenti" && v.posti.length < m.massimo
        ? h("div", { classe: "azioni" }, h("button", { classe: "btn", onclick: () => { v.posti.push(null); render(); } }, `Aggiungi un riferimento (fino a ${m.massimo})`))
        : null,
      nota("JPEG o PNG.", "JPEG o PNG, anche fatti fuori da AIRENDER. Il video prende la forma della prima immagine.")));
}

function colonnaInvioVideo() {
  const v = S.video;
  const c = v.catalogo;
  const testo = h("textarea", { id: "testo-video", rows: "3", placeholder: "Per esempio: le luci delle finestre si accendono, passa qualche persona", "aria-label": "Cosa succede, a parole" }, v.testo);
  testo.addEventListener("input", () => { v.testo = testo.value; v.secco = null; });
  const audio = h("input", { type: "checkbox", checked: v.audio || null });
  audio.addEventListener("change", () => { v.audio = audio.checked; v.secco = null; });
  const spento = motivoVideoSpento();
  const pieni = v.posti.filter(Boolean).length;
  const invio = h("section", { classe: "pannello", "aria-label": "Invio del video" },
    h("p", { classe: "destinazione" }, `${pieni === 1 ? "L'immagine va" : pieni ? `Le ${pieni} immagini vanno` : "Le immagini vanno"} a `, h("b", {}, c.destinazione),
      ` (${c.fornitore}, ${c.modello_nome})`, c.senza_ripiego ? ", senza ripiego su altri servizi." : "."),
    h("p", { classe: "destinazione" }, "Costo: ", h("b", {}, c.costo)),
  );
  if (!S.studio.coda_attiva) invio.append(avviso("attenzione", "La coda dei lavori non sta girando: il video resterebbe in attesa.", "Chiudi e riapri lo Studio, che la fa partire."));
  invio.append(h("div", { classe: "azioni" },
    h("button", { classe: "btn", onclick: provaASeccoVideo, disabled: !pieni }, "Prova a secco"),
    h("button", { classe: "btn primario", onclick: generaVideo, disabled: !!spento }, "Genera video")));
  if (spento) invio.append(h("p", { classe: "tenue piccolo" }, spento));
  if (v.secco) {
    const s = v.secco;
    invio.append(h("div", { classe: "avviso" + (s.problemi.length ? " attenzione" : ""), role: "status" },
      h("b", {}, "Prova a secco: non ho inviato niente."),
      h("span", {}, `Partirebbero ${s.immagini} immagini verso ${s.destinazione}, ${s.caratteri} caratteri di prompt.`),
      s.problemi.length
        ? s.problemi.map((p) => h("span", {}, `Fermerebbe l'invio: ${p.fatto} `, h("span", { classe: "cosa-fare" }, p.cosa_fare)))
        : h("span", {}, "Niente fermerebbe l'invio."),
      s.prompt ? h("span", { classe: "mono piccolo" }, s.prompt) : null));
  }
  return h("div", { classe: "colonna-invio" },
    h("section", { classe: "pannello", "aria-label": "Movimento" },
      h("span", { classe: "etichetta" }, "Movimento della camera"),
      h("div", { classe: "scelte-chip", role: "group", "aria-label": "Movimento della camera" },
        c.movimenti.map((x) => h("button", { classe: "chip", "aria-pressed": String(v.movimento === x.id),
          onclick: () => { v.movimento = x.id; v.secco = null; render(); } }, x.nome))),
      h("span", { classe: "etichetta" }, "Cosa succede, a parole (facoltativo)"), testo,
      h("span", { classe: "etichetta" }, "Durata"),
      h("div", { classe: "switch", role: "group", "aria-label": "Durata" },
        c.durate.map((d) => h("button", { classe: "seg", "aria-pressed": String(v.durata === d),
          onclick: () => { v.durata = d; v.secco = null; render(); } }, `${d} secondi`))),
      h("span", { classe: "etichetta" }, "Risoluzione"),
      h("div", { classe: "switch", role: "group", "aria-label": "Risoluzione del video" },
        c.risoluzioni.map((r) => h("button", { classe: "seg", "aria-pressed": String(v.risoluzione === r),
          onclick: () => { v.risoluzione = r; v.secco = null; render(); } }, r))),
      h("label", { classe: "riga" }, audio, h("span", { classe: "piccolo" }, "Audio (per un render d'architettura di solito non serve)"))),
    invio);
}

// Un lettore per video, tenuto fra un disegno e l'altro. La pagina si ridisegna
// ogni pochi secondi: un <video> rifatto da capo ricarica il file (lampeggia) e
// perde il punto in cui era; uno spostato nel DOM nello stesso giro continua.
const lettoriVideo = new Map();
function lettoreVideo(chiave, attributi, prepara) {
  let nodo = lettoriVideo.get(chiave);
  if (!nodo) {
    nodo = h("video", attributi);
    if (prepara) prepara(nodo);
    lettoriVideo.set(chiave, nodo);
  }
  return nodo;
}
// Uno solo suona: premere play su un video ferma gli altri.
document.addEventListener("play", (evento) => {
  for (const altro of document.querySelectorAll("video")) if (altro !== evento.target && !altro.paused) altro.pause();
}, true);

function voceVideo(x) {
  const attivo = x.stato === "in coda" || x.stato === "inviato";
  const righe = [
    h("div", { classe: "riga tra" },
      h("b", {}, `${x.movimento || "Video"} · ${x.durata || "?"} s · ${x.risoluzione || ""}`),
      h("span", { classe: "tag-stato" }, x.stato)),
    h("span", { classe: "piccolo tenue" }, `${x.modo} · ${x.immagini} ${x.immagini === 1 ? "immagine" : "immagini"} · ${data(x.aggiornato_il)}`),
  ];
  if (x.pronto) righe.push(lettoreVideo(`voce:${x.identificativo}`, { src: `/file/video/${enc(x.identificativo)}`, controls: true, preload: "metadata", classe: "lettore-video" }),
    h("span", { classe: "piccolo tenue" }, x.crediti_usati !== null && x.crediti_usati !== undefined ? `Costo letto dal servizio: ${String(x.crediti_usati).replace(".", ",")} crediti` : "Costo: il servizio non l'ha detto"));
  if (attivo) righe.push(h("span", { classe: "piccolo" }, x.stato === "in coda" ? "In coda: parte appena la coda lo prende." : "Seedance ci lavora: di solito qualche minuto. Lo Studio e Allplan restano liberi."),
    x.stato === "in coda" ? h("div", { classe: "azioni" }, h("button", { classe: "btn", onclick: () => annullaVideo(x.identificativo) }, "Annulla")) : null);
  if (x.stato === "errore") righe.push(avviso("errore", x.fatto || "Il video non è andato.", x.cosa_fare));
  return h("div", { classe: "pannello voce-video" }, ...righe);
}

// «Inizio, intermezzo, fine» sono due video: si mostrano come una voce sola,
// con un lettore che passa dal primo tratto al secondo.
function vociVideo(voci) {
  const fatte = new Set();
  const uscita = [];
  for (const x of voci) {
    if (!x.sequenza) { uscita.push(voceVideo(x)); continue; }
    if (fatte.has(x.sequenza)) continue;
    fatte.add(x.sequenza);
    const tratti = voci.filter((y) => y.sequenza === x.sequenza).sort((a, b) => (a.tratto || 0) - (b.tratto || 0));
    uscita.push(voceSequenza(tratti));
  }
  return uscita;
}

function voceSequenza(tratti) {
  const pronti = tratti.every((t) => t.pronto);
  const primo = tratti[0];
  const righe = [
    h("div", { classe: "riga tra" },
      h("b", {}, `Inizio, intermezzo, fine · ${primo.movimento || "Video"} · ${tratti.length} × ${primo.durata || "?"} s · ${primo.risoluzione || ""}`),
      h("span", { classe: "tag-stato" }, pronti ? "fatto" : tratti.map((t) => t.stato).join(" · "))),
  ];
  if (pronti) {
    const indirizzi = tratti.map((t) => `/file/video/${enc(t.identificativo)}`);
    const lettore = lettoreVideo(`sequenza:${primo.sequenza}`, { src: indirizzi[0], controls: true, preload: "metadata", classe: "lettore-video" }, (nodo) => {
      let quale = 0;
      nodo.addEventListener("ended", () => {
        quale = (quale + 1) % indirizzi.length;
        nodo.src = indirizzi[quale];
        if (quale) nodo.play();
      });
    });
    righe.push(lettore, nota("Due file, uno per tratto.", "Seedance non ha un fotogramma di mezzo: sono due video, il secondo parte da dove finisce il primo. Lo Studio li suona uno dopo l'altro; nella cartella dei video sono due file."));
  }
  for (const t of tratti) {
    if (t.stato === "errore") righe.push(avviso("errore", `Tratto ${t.tratto}: ${t.fatto || "non è andato."}`, t.cosa_fare));
    if (t.stato === "in coda") righe.push(h("div", { classe: "azioni" }, h("button", { classe: "btn", onclick: () => annullaVideo(t.identificativo) }, `Annulla il tratto ${t.tratto}`)));
  }
  return h("div", { classe: "pannello voce-video" }, ...righe);
}

function schermataVideo() {
  const v = S.video;
  const sopra = v.errore ? [avviso("errore", v.errore.fatto, v.errore.cosa_fare)] : [];
  if (!v.catalogo) return [h("h1", { classe: "nascosto" }, "Video"), ...sopra, h("p", { classe: "tenue" }, v.errore ? "" : "Apro la scheda Video…")];
  return [h("h1", { classe: "nascosto" }, "Video"), ...sopra,
    h("div", { classe: "colonne" }, colonnaImmaginiVideo(), colonnaInvioVideo()),
    h("section", { classe: "pannello", "aria-label": "I video fatti" },
      h("div", { classe: "riga tra" }, h("span", { classe: "etichetta" }, "I video fatti"),
        h("button", { classe: "btn", onclick: () => post("/api/apri-cartella", { quale: "video" }).catch((e) => { v.errore = e; render(); }) }, "Apri cartella")),
      v.voci.length ? h("div", { classe: "elenco-video" }, vociVideo(v.voci)) : h("p", { classe: "tenue" }, "Nessun video ancora."))];
}

// --- storico --------------------------------------------------------------------
// La colonna a sinistra, uguale in ogni scheda: un gruppo per vista, che si
// apre e si chiude, e dentro una tessera per immagine su due colonne. Si
// scorre in verticale: con molte viste la pagina non si allunga di lato.
// Un clic porta all'immagine: la cattura in Genera, un render o un ritocco in
// Risultato, un video in Video.

function leggiRidotta() {
  try { return localStorage.getItem("airender.storico.ridotta") === "1"; } catch (e) { return false; }
}

function riduciStorico(si) {
  S.storico.ridotta = si;
  try { localStorage.setItem("airender.storico.ridotta", si ? "1" : "0"); } catch (e) { /* resta per questa volta */ }
  S.storico.disegnata = "";
  disegnaStorico();
}

function gruppoAperto(g) {
  const scelta = S.storico.aperte[g.vista || ""];
  if (scelta !== undefined) return scelta;
  if (!g.vista) return false;
  return g.vista === S.vista || !S.viste_viste.has(g.vista);
}

function apriChiudiGruppo(g) {
  S.storico.aperte[g.vista || ""] = !gruppoAperto(g);
  S.storico.disegnata = "";
  disegnaStorico();
}

function nomeVista(nome) {
  return nome.replace(/\.[^.]+$/, "");
}

function gruppoStorico(g) {
  const aperto = gruppoAperto(g);
  const nome = g.vista ? nomeVista(g.vista) : "Video da immagini caricate";
  const nuova = g.vista && !S.viste_viste.has(g.vista);
  const conta = g.voci.filter((v) => v.tipo !== "cattura").length;
  const qui = g.vista && g.vista === S.vista;
  const corpo = `corpo-storico-${(g.vista || "video").replace(/[^A-Za-z0-9_-]/g, "_")}`;
  return h("section", { classe: `gruppo-storico${qui ? " qui" : ""}`, "aria-label": g.vista ? `Vista ${g.vista}` : nome, "data-vista": g.vista || "" },
    h("button", { classe: "testa-gruppo", "aria-expanded": String(aperto), "aria-controls": corpo,
      title: aperto ? `Chiudi ${nome}` : `Apri ${nome}`, onclick: () => apriChiudiGruppo(g) },
      h("span", { classe: "freccia", "aria-hidden": "true" }, aperto ? "▾" : "▸"),
      g.vista ? h("img", { classe: "miniatura-gruppo", src: `/file/vista/${enc(g.vista)}`, alt: "", loading: "lazy", decoding: "async" }) : null,
      h("span", { classe: "nome-gruppo" }, nome),
      nuova ? h("span", { classe: "segno-testa" }, "Nuova") : null,
      h("span", { classe: "conta tenue", title: conta === 1 ? "1 immagine fatta" : `${conta} immagini fatte` }, String(conta))),
    aperto ? h("div", { classe: "tessere-gruppo", id: corpo }, g.voci.map(tesseraStorico)) : null);
}

async function caricaStorico() {
  try { S.storico.gruppi = (await get("/api/storico")).gruppi; } catch (e) { /* la prossima volta */ }
}

// Quello che, se cambia, vuol dire che lo storico va riletto.
function firmaStudio(ora) {
  return JSON.stringify([ora.viste.map((v) => v.nome), (ora.lavori_attivi || []).map((l) => [l.identificativo, l.stato])]);
}

function voceScelta(v) {
  if (v.tipo === "cattura") return S.scheda === "genera" && S.vista === v.vista;
  if (v.tipo === "video") return false;
  if (S.vista !== v.vista) return false;
  if (S.scheda === "risultato") return S.risultato.scelto === v.identificativo;
  if (S.scheda === "passi") return S.passi.scelto === v.identificativo;
  if (S.scheda === "ritocca") return (S.ritocca.esito || S.ritocca.da) === v.identificativo;
  return false;
}

async function apriDalloStorico(v) {
  if (v.tipo === "video") { location.hash = "#video"; return; }
  if (v.vista && v.vista !== S.vista) await caricaVista(v.vista);
  if (v.tipo === "cattura") {
    if (location.hash !== "#genera") location.hash = "#genera"; else render();
    return;
  }
  S.risultato.scelto = v.identificativo; S.risultato.rifai = false; S.risultato.esportato = null;
  if (S.risultato.confronto === v.identificativo) S.risultato.confronto = "vista";
  S.passi.scelto = v.identificativo;
  await caricaRicetta();
  if (location.hash !== "#risultato") location.hash = "#risultato"; else render();
}

function tesseraStorico(v) {
  let quadro;
  if (v.tipo === "cattura") quadro = h("img", { src: `/file/vista/${enc(v.vista)}`, alt: "", loading: "lazy", decoding: "async" });
  else if (v.tipo === "video" && v.immagine) quadro = lettoreVideo(`striscia:${v.identificativo}`, { src: `/file/video/${enc(v.identificativo)}`, preload: "metadata", muted: true });
  else if (v.immagine) quadro = h("img", { src: `/file/render/${enc(v.identificativo)}`, alt: "", loading: "lazy", decoding: "async" });
  else quadro = h("span", { classe: "piccolo" }, v.attivo ? "…" : "—");
  const nuova = v.tipo === "cattura" && !S.viste_viste.has(v.vista);
  const fallito = v.stato === "errore" || v.stato === "annullato";
  const titolo = [v.etichetta, v.numero ? `passo ${v.numero}` : null, v.stato !== "fatto" ? v.stato : null, data(v.creato_il)].filter(Boolean).join(" · ");
  const voce = h("button", {
    classe: `voce-storico${v.attivo ? " attivo" : ""}`, title: titolo,
    "aria-current": String(voceScelta(v)), "aria-label": titolo,
    onclick: () => apriDalloStorico(v),
  },
    h("span", { classe: "quadro" }, quadro),
    nuova ? h("span", { classe: "segno" }, "Nuova") : fallito ? h("span", { classe: "segno errore" }, v.stato === "errore" ? "Errore" : "Annullato") : null,
    h("span", { classe: "didascalia" }, v.numero ? `${v.etichetta} ${v.numero}` : v.etichetta));
  return voce;
}

function disegnaStorico() {
  const nav = document.getElementById("storico");
  if (!nav) return;
  const gruppi = S.storico.gruppi || [];
  // Si ridisegna solo se e' cambiato qualcosa: le immagini non si ricaricano
  // a ogni giro e la colonna non salta.
  const firma = JSON.stringify([gruppi, S.scheda, S.vista, S.risultato.scelto, S.passi.scelto, S.ritocca.da, S.ritocca.esito, [...S.viste_viste]]);
  if (firma === S.storico.disegnata) return;
  S.storico.disegnata = firma;
  nav.classList.toggle("ridotta", S.storico.ridotta);
  if (!gruppi.length) { nav.replaceChildren(); return; }
  if (S.storico.ridotta) {
    nav.replaceChildren(h("button", { classe: "apri-storico", onclick: () => riduciStorico(false),
      title: "Apri lo storico: tutte le immagini, vista per vista." },
      h("span", { "aria-hidden": "true" }, "▸"), h("span", { classe: "verticale" }, "Storico")));
    return;
  }
  const elenco = nav.querySelector(".elenco-storico");
  const scorrimento = elenco ? elenco.scrollTop : 0;
  const nuovoElenco = h("div", { classe: "elenco-storico" }, gruppi.map(gruppoStorico));
  nav.replaceChildren(
    h("div", { classe: "testa-storico" },
      h("span", { classe: "etichetta" }, "Storico"),
      h("button", { classe: "btn link piccolo", onclick: () => riduciStorico(true),
        title: "Chiudi la colonna: l'immagine prende tutta la larghezza." }, "Chiudi")),
    nuovoElenco);
  nuovoElenco.scrollTop = scorrimento;
  // Quando cambia la vista su cui si lavora, la si porta in vista nella colonna.
  if (S.vista !== S.storico.vistaMostrata) {
    S.storico.vistaMostrata = S.vista;
    const qui = nuovoElenco.querySelector(".gruppo-storico.qui");
    if (qui) qui.scrollIntoView({ block: "nearest" });
  }
}

// Mentre si trascina (un'area, il rettangolo del fotoinserimento, un
// foglietto) la pagina non si ridisegna: rifare la tela a meta' gesto le
// toglieva il puntatore e il disegno saltava (test del 2026-11-04). Il
// ridisegno chiesto nel frattempo parte appena si lascia.
let trascinando = false;
let ridisegnoInAttesa = false;
window.addEventListener("pointerdown", (ev) => { if (ev.button === 0) trascinando = true; }, true);
for (const tipo of ["pointerup", "pointercancel"]) {
  window.addEventListener(tipo, () => {
    trascinando = false;
    if (ridisegnoInAttesa) { ridisegnoInAttesa = false; setTimeout(render, 0); }
  }, true);
}

// --- Licenza e saldo ------------------------------------------------------------
// Bozza A scelta il 2026-11-05: una scheda intera, il saldo in breve in
// testata. Quattro stati (DESIGN.md): vuoto, in corso, errore, pieno.

async function caricaLicenza() {
  try { S.licenza = await get("/api/licenza"); } catch (e) { S.licenza = { presente: false, errore: { fatto: e.fatto, cosa_fare: e.cosa_fare } }; }
}

// La stessa frase che scrive il server quando il saldo non copre il render.
function saldoFinito(fatto) { return /saldo AIRENDER non basta/.test(fatto || ""); }

function pulsanteRicarica() {
  const l = S.licenza;
  const url = l && l.saldo && l.saldo.ricarica_url;
  return url
    ? h("a", { classe: "btn primario", href: url, target: "_blank", rel: "noopener" }, "Ricarica")
    : h("button", { classe: "btn primario", disabled: true, title: "Il link per ricaricare arriva dal server AIRENDER: riapri la scheda Licenza." }, "Ricarica");
}

function nomeServer() {
  try { return new URL(S.licenza.server).host; } catch (e) { return "server AIRENDER"; }
}

function nomePiano(saldo) { return (saldo.funzioni && saldo.funzioni.nome) || saldo.piano || ""; }

// La pastiglia in testata: quello che conta, sempre visibile.
function pastigliaLicenza() {
  const l = S.licenza;
  if (!l) return null;
  if (usaComfy()) return h("a", { classe: "pastiglia", href: "#licenza" }, "Chiave Comfy tua");
  if (!l.presente) return h("a", { classe: "pastiglia attenzione", href: "#licenza" }, "Nessuna licenza");
  if (!l.saldo) return h("a", { classe: "pastiglia attenzione", href: "#licenza", title: l.errore ? l.errore.fatto : "" }, "Saldo non letto");
  return h("a", { classe: "pastiglia ok", href: "#licenza" }, h("b", {}, String(l.saldo.saldo)), ` render · ${nomePiano(l.saldo)}`);
}

async function attivaLicenza(evento) {
  if (evento) evento.preventDefault();
  if (S.attiva.inCorso) return;
  S.attiva.inCorso = true; S.attiva.errore = null; render();
  try {
    S.licenza = await post("/api/licenza", { codice: S.attiva.codice });
    S.attiva = { codice: "", inCorso: false, errore: null, cambia: false };
    S.catalogo = await get("/api/catalogo");  // il piano decide se il prompt si vede
    if (S.vista) await caricaDestinazione();
  } catch (e) {
    S.attiva.inCorso = false; S.attiva.errore = e;
  }
  render();
}

async function usaServizio(provider) {
  try {
    S.licenza = await post("/api/licenza/servizio", { provider });
    S.attiva.errore = null;
    S.catalogo = await get("/api/catalogo");  // il piano decide se il prompt si vede
    if (S.vista) await caricaDestinazione();
  } catch (e) { S.attiva.errore = e; }
  render();
}

function moduloCodice() {
  const a = S.attiva;
  const campo = h("input", {
    id: "codice-licenza", classe: "codice" + (a.errore ? " sbagliato" : ""), placeholder: "AIR-XXXX-XXXX-XXXX-XXXX",
    autocomplete: "off", spellcheck: "false", disabled: a.inCorso, value: a.codice,
    "aria-describedby": "dove-va-il-codice", oninput: (e) => { S.attiva.codice = e.target.value; },
  });
  return h("form", { classe: "modulo-codice", onsubmit: attivaLicenza },
    h("label", { for: "codice-licenza", classe: "etichetta-campo" }, "Codice licenza"),
    h("div", { classe: "riga" }, campo,
      h("button", { classe: "btn primario", type: "submit", disabled: a.inCorso }, a.errore && a.errore.fatto.includes("non risponde") ? "Riprova" : "Attiva")),
    a.inCorso
      ? h("div", { classe: "riga", role: "status" }, h("span", { classe: "giro", "aria-hidden": "true" }),
          h("span", { classe: "tenue" }, `Chiedo al server AIRENDER (${nomeServer()}) se il codice è valido.`))
      : h("p", { id: "dove-va-il-codice", classe: "tenue piccolo" }, `Il codice si controlla con il server AIRENDER: `, h("span", { classe: "mono" }, nomeServer()),
          SUL_WEB ? ". Se va, resta salvato solo in questo browser." : ". Se va, resta salvato solo su questo PC."),
    a.errore ? avviso("errore", a.errore.fatto, a.errore.cosa_fare) : null);
}

// La chiave Comfy propria vale solo se c'e' davvero sul PC.
function usaComfy() { return !!(S.licenza && S.licenza.provider === "comfy" && S.licenza.chiave_comfy); }

function pannelloComfy() {
  const l = S.licenza;
  if (usaComfy()) {
    return h("div", { classe: "pannello" },
      h("p", {}, h("b", {}, "I render usano la tua chiave Comfy."), " Paghi Comfy direttamente; i crediti AIRENDER non si toccano."),
      l.presente ? h("div", { classe: "riga" }, h("button", { classe: "btn", onclick: () => usaServizio("airender") }, "Torna ai crediti AIRENDER")) : null);
  }
  return h("div", { classe: "pannello" },
    h("p", {}, h("b", {}, "Hai una chiave Comfy tua?"), " Puoi usarla al posto dei crediti AIRENDER: paghi Comfy direttamente."),
    l.chiave_comfy ? h("div", { classe: "riga" }, h("button", { classe: "btn", onclick: () => usaServizio("comfy") }, "Usa la mia chiave Comfy")) : null,
    l.chiave_comfy ? null : h("p", { classe: "tenue piccolo" }, "Su questo PC non c'è ancora: va messa nella variabile d'ambiente COMFY_API_KEY di Windows, poi si riapre lo Studio."));
}

function tabellaCosti(saldo) {
  const righe = [];
  for (const [modello, perDimensione] of Object.entries(saldo.pesi || {})) {
    const m = (S.catalogo.modelli || []).find((x) => x.id === modello);
    for (const [dimensione, render] of Object.entries(perDimensione)) {
      righe.push(h("tr", {}, h("td", {}, `${m ? m.nome : modello}, ${dimensione}`), h("td", {}, String(render))));
    }
  }
  if (!righe.length) return null;
  return h("table", { classe: "costi" },
    h("thead", {}, h("tr", {}, h("th", {}, "Quanto costa un render"), h("th", {}, "render"))),
    h("tbody", {}, ...righe));
}

function giorno(iso) {
  const d = new Date(iso);
  return isNaN(d) ? String(iso).split("T")[0] : d.toLocaleDateString("it-IT", { day: "numeric", month: "short", year: "numeric" });
}

function pannelloSaldo() {
  const l = S.licenza, s = l.saldo;
  const scadenza = s.prossima_scadenza;
  const post_ = s.postazioni || {};
  return h("div", { classe: "pannello" },
    h("h2", {}, `Piano ${nomePiano(s)}`),
    h("div", { classe: "riga saldo" }, h("span", { classe: "numero" }, String(s.saldo)),
      h("span", { classe: "tenue" }, `render disponibili${s.in_attesa ? `, più ${s.in_attesa} in corso` : ""}`)),
    h("dl", { classe: "dati" },
      scadenza ? [h("dt", {}, "Scadenza"), h("dd", {}, `${scadenza.quantita} render scadono il ${giorno(scadenza.il)}`)] : null,
      post_.massimo ? [h("dt", {}, "Postazioni"), h("dd", {}, `${post_.usate} di ${post_.massimo} usate`)] : null,
      h("dt", {}, "Licenza"), h("dd", {}, `…${s.ultime_cifre || l.ultime_cifre}${s.email ? ` · ${s.email}` : ""}`)),
    h("div", { classe: "riga" }, pulsanteRicarica(),
      s.gestisci_url ? h("a", { classe: "btn", href: s.gestisci_url, target: "_blank", rel: "noopener" }, "Gestisci abbonamento") : null),
    h("p", { classe: "tenue piccolo" }, SUL_WEB ? "Ricarica e Gestisci aprono una nuova scheda; i link valgono un'ora." : "Ricarica e Gestisci aprono il browser; i link valgono un'ora."),
    tabellaCosti(s),
    h("div", { classe: "riga" }, h("button", { classe: "btn link", onclick: () => { S.attiva.cambia = true; render(); } }, "Cambia codice")));
}

function schermataLicenza() {
  const l = S.licenza;
  const titolo = h("h1", {}, "Licenza e saldo");
  if (!l) return [titolo, h("p", { classe: "tenue" }, "Leggo la licenza…")];
  const blocchi = [titolo];
  // Vuoto, in corso, errore del codice: il modulo.
  if (!l.presente || S.attiva.cambia) {
    blocchi.push(h("div", { classe: "pannello" },
      h("h2", {}, S.attiva.cambia ? "Cambia codice" : "Attiva AIRENDER"),
      h("p", {}, "Incolla il codice licenza che hai ricevuto per email dopo l'acquisto. Senza codice i render con i crediti AIRENDER non partono."),
      moduloCodice(),
      S.attiva.cambia
        ? h("div", { classe: "riga" }, h("button", { classe: "btn link", onclick: () => { S.attiva = { codice: "", inCorso: false, errore: null, cambia: false }; render(); } }, "Lascia il codice di prima"))
        : (!l.presente ? h("div", { classe: "riga" }, h("a", { classe: "btn link", href: `${l.server}/#prezzi`, target: "_blank", rel: "noopener" }, "Non hai una licenza? Vedi i piani")) : null)));
  } else if (l.saldo) {
    // Pieno.
    blocchi.push(pannelloSaldo());
  } else if (l.errore) {
    // Codice salvato, ma il server non ha dato il saldo.
    blocchi.push(h("div", { classe: "pannello" },
      h("h2", {}, `Licenza …${l.ultime_cifre}`),
      avviso("errore", l.errore.fatto, l.errore.cosa_fare),
      h("div", { classe: "riga" },
        h("button", { classe: "btn", onclick: async () => { await caricaLicenza(); render(); } }, "Riprova"),
        h("button", { classe: "btn link", onclick: () => { S.attiva.cambia = true; render(); } }, "Cambia codice"))));
  }
  if (S.attiva.errore && l.presente && !S.attiva.cambia) blocchi.push(avviso("errore", S.attiva.errore.fatto, S.attiva.errore.cosa_fare));
  if (!SUL_WEB) blocchi.push(pannelloComfy());  // sul web non c'e' dove mettere COMFY_API_KEY
  return h("div", { classe: "schermata-licenza" }, ...blocchi);
}

function render() {
  if (trascinando) { ridisegnoInAttesa = true; return; }
  disegnaTestata();
  disegnaStorico();
  const main = document.getElementById("principale");
  if (!S.studio || !S.catalogo || !S.scelte) {
    main.replaceChildren(S.errore ? avviso("errore", S.errore.fatto, S.errore.cosa_fare) : h("p", { classe: "tenue" }, "Apro lo Studio…"));
    return;
  }
  const attivo = document.activeElement && document.activeElement.id;
  // La pagina si ridisegna ogni pochi secondi: chi sta scrivendo deve
  // ritrovare il cursore dov'era, non in fondo (test del 2026-11-04 sulle note).
  const prima = attivo ? document.activeElement : null;
  const cursore = prima && typeof prima.selectionStart === "number"
    ? { inizio: prima.selectionStart, fine: prima.selectionEnd, direzione: prima.selectionDirection, alto: prima.scrollTop } : null;
  const scorrimento = window.scrollY;
  const contenuto = S.scheda === "licenza" ? schermataLicenza()
    : S.scheda === "video" ? schermataVideo()
    : S.scheda === "risultato" ? schermataRisultato()
    : S.scheda === "passi" ? schermataPassi()
    : S.scheda === "ritocca" ? schermataRitocca() : schermataGenera();
  main.replaceChildren(...[contenuto].flat(2).filter(Boolean));
  const dopo = attivo && document.getElementById(attivo);
  if (dopo) {
    dopo.focus();
    if (cursore && typeof dopo.setSelectionRange === "function") {
      try { dopo.setSelectionRange(cursore.inizio, cursore.fine, cursore.direzione || "none"); } catch (e) { /* un campo senza cursore */ }
      dopo.scrollTop = cursore.alto;
    }
  }
  if (S.scheda === "passi" || S.scheda === "risultato") { disegnaNuovoPasso(); }
  if (S.scheda === "ritocca") { disegnaApplicaRitocco(); }
  window.scrollTo(0, scorrimento);
}

function leggiScheda() {
  const s = (location.hash || "#genera").slice(1);
  S.scheda = ["genera", "risultato", "passi", "ritocca", "video", "licenza"].includes(s) ? s : "genera";
}

window.addEventListener("hashchange", async () => {
  leggiScheda();
  if (S.scheda !== "genera" && S.vista) await caricaRender();
  if ((S.scheda === "passi" || S.scheda === "ritocca") && S.vista) await caricaPassi();
  if (S.scheda === "ritocca") await prontoRitocca();
  if (S.scheda === "video") await caricaVideo();
  if (S.scheda === "licenza") await caricaLicenza();
  render();
  window.scrollTo(0, 0);
});

// Ogni pochi secondi: la coda e' viva? la palette ha salvato una vista nuova?
async function controllaStudio() {
  try {
    const ora = await get("/api/studio");
    // Di nuovo raggiungibile dopo un silenzio: si riparte da capo, perché
    // quello che la pagina sapeva può non valere più (lavori, viste, cartella).
    if (S.spento || !S.catalogo) { location.reload(); return; }
    const prima = S.studio ? S.studio.viste.map((v) => v.nome) : [];
    const nuove = ora.viste.filter((v) => !prima.includes(v.nome));
    const cambiato = !S.studio || ora.coda_attiva !== S.studio.coda_attiva || ora.viste.length !== S.studio.viste.length;
    S.studio = ora;
    const firma = firmaStudio(ora);
    const videoInCorso = S.storico.gruppi.some((g) => g.voci.some((v) => v.tipo === "video" && v.attivo));
    if (firma !== S.storico.firma || videoInCorso) { S.storico.firma = firma; await caricaStorico(); }
    if (!S.vista && ora.viste.length) { await caricaVista(ora.viste[0].nome); return; }
    // Una cattura nuova dalla palette: in Genera, senza lavori in corso, la
    // si apre subito. Altrove resta nello storico con «Nuova», e quello
    // su cui si sta lavorando non cambia.
    if (nuove.length && S.scheda === "genera" && !S.lavoroAttivo) { await caricaVista(nuove[0].nome); return; }
    render();
  } catch (e) {
    // Lo si dice subito, non al prossimo clic; poi si riprova al giro dopo.
    if (S.spento && !(S.errore && S.errore.fatto === e.fatto)) { S.errore = e; render(); }
  }
}

async function avvia() {
  leggiScheda();
  try {
    [S.studio, S.catalogo] = await Promise.all([get("/api/studio"), get("/api/catalogo")]);
    await Promise.all([caricaMiei(), caricaRicette(), caricaLicenza()]);
    // Senza codice e senza una chiave Comfy propria non parte niente: lo
    // Studio si apre sulla scheda Licenza (bozza A, 2026-11-05).
    if (S.licenza && !S.licenza.presente && !S.licenza.chiave_comfy && S.scheda !== "licenza") {
      history.replaceState(null, "", "#licenza");
      S.scheda = "licenza";
    }
    const primo = S.catalogo.scene.esterno.preset[0];
    S.preset = primo.id;
    S.scelte = { ...primo.scelte, fedelta: undefined };
    S.modello = S.studio.modello_predefinito;
    await Promise.all([caricaDestinazione(), aggiornaComposto(true)]);
    const attivo = S.studio.lavori_attivi[0];
    const vistaAttiva = attivo && S.studio.viste.find((v) => v.nome === attivo.vista);
    await caricaVista(vistaAttiva ? vistaAttiva.nome : (S.studio.viste[0] ? S.studio.viste[0].nome : null));
    if (attivo) seguiLavoro(attivo);
    // Le viste che c'erano gia' all'apertura non sono «nuove».
    for (const v of S.studio.viste) S.viste_viste.add(v.nome);
    S.storico.firma = firmaStudio(S.studio);
    await caricaStorico();
    if (S.scheda === "ritocca") { await caricaPassi(); await prontoRitocca(); }
    if (S.scheda === "video") await caricaVideo();
    if (S.scheda === "passi") {
      const modelli = [...new Set((S.passi.dati ? S.passi.dati.passi : []).map((x) => x.modello).filter(Boolean))];
      await Promise.all(modelli.map(destinazioneDi));
    }
  } catch (e) { S.errore = e; }
  render();
  setInterval(controllaStudio, 3000);
}

// Ogni gesto che manda un lavoro passa da qui: vedi unInvioAllaVolta.
genera = unInvioAllaVolta(genera);
rifai = unInvioAllaVolta(rifai);
porta = unInvioAllaVolta(porta);
usaRicetta = unInvioAllaVolta(usaRicetta);
applicaRitocco = unInvioAllaVolta(applicaRitocco);
applicaPasso = unInvioAllaVolta(applicaPasso);
inviaPulito = unInvioAllaVolta(inviaPulito);
rifaiPasso = unInvioAllaVolta(rifaiPasso);
generaVideo = unInvioAllaVolta(generaVideo);
applicaFinale = unInvioAllaVolta(applicaFinale);

// La colonna dello storico e' alta quanto la finestra meno la testata.
(() => {
  const testata = document.querySelector(".testata");
  if (!testata || typeof ResizeObserver === "undefined") return;
  new ResizeObserver(() => document.documentElement.style.setProperty("--alto-testata", `${testata.offsetHeight}px`)).observe(testata);
})();

avvia();
