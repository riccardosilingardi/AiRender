// L'email col codice licenza. Due servizi, una chiamata REST ciascuno:
// - Mailjet (Sinch Mailjet SAS, Francia, dati in UE), se ci sono
//   MAILJET_API_KEY e MAILJET_SECRET_KEY: Riccardo ha gia' l'account
//   (2026-11-06) ed e' il preferito per il GDPR;
// - Resend (resend.com, USA) altrimenti, con RESEND_API_KEY.
// EMAIL_MITTENTE e' "Nome <indirizzo>" o solo l'indirizzo; su Mailjet
// l'indirizzo va verificato come mittente.

import { facoltativa, serve } from "./ambiente.mjs";
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

export function mittente(testo) {
  const m = /^\s*(.*?)\s*<([^>]+)>\s*$/.exec(testo || "");
  return m ? { nome: m[1].replace(/^"|"$/g, ""), indirizzo: m[2].trim() } : { nome: "", indirizzo: (testo || "").trim() };
}

export function creaEmail(ambiente = process.env, chiama = fetch) {
  const oggetto = "Il tuo codice licenza AIRENDER";

  async function viaMailjet(destinatario, testo) {
    const da = mittente(serve("EMAIL_MITTENTE", ambiente));
    const credenziali = Buffer.from(`${serve("MAILJET_API_KEY", ambiente)}:${serve("MAILJET_SECRET_KEY", ambiente)}`).toString("base64");
    return chiama("https://api.mailjet.com/v3.1/send", {
      method: "POST",
      headers: { authorization: `Basic ${credenziali}`, "content-type": "application/json" },
      body: JSON.stringify({
        Messages: [{
          From: { Email: da.indirizzo, ...(da.nome ? { Name: da.nome } : {}) },
          To: [{ Email: destinatario }],
          Subject: oggetto,
          TextPart: testo,
        }],
      }),
    });
  }

  async function viaResend(destinatario, testo) {
    return chiama("https://api.resend.com/emails", {
      method: "POST",
      headers: { authorization: `Bearer ${serve("RESEND_API_KEY", ambiente)}`, "content-type": "application/json" },
      body: JSON.stringify({ from: serve("EMAIL_MITTENTE", ambiente), to: [destinatario], subject: oggetto, text: testo }),
    });
  }

  async function inviaCodice(destinatario, codice, nomePiano) {
    const testo = testoEmail(codice, nomePiano, serve("SITO_URL", ambiente));
    const r = facoltativa("MAILJET_API_KEY", ambiente)
      ? await viaMailjet(destinatario, testo)
      : await viaResend(destinatario, testo);
    if (!r.ok) throw new Error(`Email: ${r.status} ${(await r.text()).slice(0, 300)}`);
  }
  return { inviaCodice };
}
