// Le variabili d'ambiente del sito Netlify. Nessuna chiave sta nel
// repository: se manca, la funzione lo dice per nome e non parte.

export class VariabileMancante extends Error {}

export function serve(nome, ambiente = process.env) {
  const valore = (ambiente[nome] || "").trim();
  if (!valore) throw new VariabileMancante(`Manca la variabile d'ambiente ${nome} nel sito Netlify.`);
  return valore;
}

export function facoltativa(nome, ambiente = process.env) {
  return (ambiente[nome] || "").trim();
}
