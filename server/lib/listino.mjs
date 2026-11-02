// Il listino, letto da listino.json (scritto da scripts/scrivi_listino.py a
// partire da core/config.py: non si modifica a mano).

import listino from "../listino.json" with { type: "json" };

export { listino };

export const DIMENSIONI = ["1K", "2K", "4K"];

// La grandezza chiesta la dice il corpo della richiesta, non il client: e'
// il campo che il Router passa a Gemini. Assente vuol dire 1K.
export function dimensioneDaCorpo(corpo) {
  const valore = corpo?.generationConfig?.imageConfig?.imageSize;
  if (valore === undefined || valore === null || valore === "") return "1K";
  const d = String(valore).toUpperCase();
  return DIMENSIONI.includes(d) ? d : null;
}

export function peso(modello, dimensione, l = listino) {
  return l.pesi?.[modello]?.[dimensione] ?? null;
}

export function piano(nome, l = listino) {
  return l.piani[nome] || l.piani.nessuno;
}

// Perche' un invio non e' nel piano, o null se lo e'.
export function fuoriDalPiano(nomePiano, modello, dimensione, canale, l = listino) {
  const p = piano(nomePiano, l);
  if (!p.canali.includes(canale)) {
    return {
      tipo: "canale_non_incluso",
      messaggio: canale === "plugin"
        ? `Il piano ${p.nome} non comprende il plugin per Allplan: e' nella web app.`
        : `Il piano ${p.nome} non comprende la web app.`,
      cosa_fare: "Passa al piano Pro dalla pagina dei prezzi di AIRENDER, o usa la web app.",
    };
  }
  if (!p.modelli.includes(modello)) {
    return {
      tipo: "modello_non_incluso",
      messaggio: `Il piano ${p.nome} non comprende il modello ${modello}.`,
      cosa_fare: "Scegli Nano Banana 2 nel preset, o passa al piano Pro.",
    };
  }
  if (DIMENSIONI.indexOf(dimensione) > DIMENSIONI.indexOf(p.dimensione_massima)) {
    return {
      tipo: "dimensione_non_inclusa",
      messaggio: `Il piano ${p.nome} arriva fino a ${p.dimensione_massima}: questo render e' a ${dimensione}.`,
      cosa_fare: `Scegli una grandezza fino a ${p.dimensione_massima}, o passa al piano Pro.`,
    };
  }
  return null;
}

// Render accreditati da un pagamento di un piano in abbonamento.
export function renderDelPeriodo(nomePiano, intervallo, l = listino) {
  const p = l.piani[nomePiano];
  if (!p || p.tipo !== "abbonamento") return 0;
  return intervallo === "anno" ? p.render_mese * 12 : p.render_mese;
}

export function funzioni(nomePiano, l = listino) {
  const p = piano(nomePiano, l);
  return {
    nome: p.nome,
    modelli: p.modelli,
    dimensione_massima: p.dimensione_massima,
    canali: p.canali,
    studio: p.studio,
    postazioni: p.postazioni,
  };
}
