// La risposta al cliente quando la riserva dei crediti non va a buon fine.
// Un posto solo: router dei render e «Tieni la geometria» dicono la stessa
// cosa con le stesse parole.

import { errore } from "./risposte.mjs";

// null se la riserva e' andata bene, altrimenti la Response da restituire.
export function rifiutoDellaRiserva(riserva, quanto) {
  if (riserva.esito === "ok") return null;
  if (riserva.esito === "saldo") {
    return errore(402, "insufficient_credits",
      `Il saldo AIRENDER non basta: questo render costa ${quanto} e ne restano ${Math.max(0, riserva.disponibile)}. Non e' partito niente.`,
      "Premi Ricarica (o apri la pagina dei prezzi di AIRENDER), poi rilancia.",
      { saldo: Math.max(0, riserva.disponibile), peso: quanto });
  }
  if (riserva.esito === "postazioni") {
    return errore(403, "postazioni_esaurite",
      `Questa licenza e' gia' usata su ${riserva.usate} postazioni, il massimo del piano.`,
      "Passa al piano Studio (3 postazioni) o scrivi a AIRENDER per liberare una postazione.");
  }
  return errore(403, "licenza_sospesa", "La licenza non e' attiva.", "Scrivi a AIRENDER per riattivarla.");
}
