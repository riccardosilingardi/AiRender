// L'email col codice licenza, via Resend (resend.com: una chiamata REST, piano
// gratuito sufficiente al pilota). Scelta di questa sessione, non decisa con
// Riccardo: qualunque servizio con un'API va bene. MAI ESEGUITO.

import { serve } from "./ambiente.mjs";
import { listino } from "./listino.mjs";

export function testoEmail(codice, nomePiano, sito) {
  return [
    "Grazie per aver scelto AIRENDER.",
    "",
    `Il tuo codice licenza (${nomePiano}):`,
    "",
    `    ${codice}`,
    "",
    "Incollalo una volta nel plugin per Allplan o nella web app: da li' in poi",
    "i render si scalano dal tuo saldo. Il codice e' tuo: non condividerlo,",
    "chi lo ha usa i tuoi crediti. Non lo conserviamo in chiaro, quindi tieni",
    "questa email.",
    "",
    `Hai gia' ${listino.benvenuto.render} render di benvenuto, validi ${listino.benvenuto.validita_mesi} mesi.`,
    "",
    `Prezzi, ricariche e abbonamento: ${sito}`,
  ].join("\n");
}

export function creaEmail(ambiente = process.env, chiama = fetch) {
  async function inviaCodice(destinatario, codice, nomePiano) {
    const r = await chiama("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${serve("RESEND_API_KEY", ambiente)}`, "content-type": "application/json" },
      body: JSON.stringify({
        from: serve("EMAIL_MITTENTE", ambiente),
        to: [destinatario],
        subject: "Il tuo codice licenza AIRENDER",
        text: testoEmail(codice, nomePiano, serve("SITO_URL", ambiente)),
      }),
    });
    if (!r.ok) throw new Error(`Email: ${r.status} ${(await r.text()).slice(0, 300)}`);
  }
  return { inviaCodice };
}
