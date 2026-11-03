// Le operazioni di vendita, usate dal webhook di Stripe e dall'attivazione
// manuale (rivendita Serteco). Tutte si possono ripetere sullo stesso
// riferimento senza accreditare o fatturare due volte.

import { generaCodice, hashCodice, ultimeCifre } from "./codice.mjs";
import { listino, piano as pianoDi } from "./listino.mjs";

export function traMesi(mesi, da = new Date()) {
  const d = new Date(da);
  d.setUTCMonth(d.getUTCMonth() + mesi);
  return d.toISOString();
}

// Crea la licenza (se non c'e' gia' per quel riferimento), accredita il
// benvenuto e manda il codice per email. Restituisce { id, codice? }: il
// codice c'e' solo se e' stato generato adesso.
export async function nuovaLicenza({ db, email }, dati, casuale) {
  const codice = generaCodice(casuale);
  const p = pianoDi(dati.piano);
  const creata = await db.rpc("airender_crea_licenza", {
    p_hash: hashCodice(codice), p_ultime_cifre: ultimeCifre(codice), p_email: dati.email,
    p_piano: dati.piano, p_origine: dati.origine, p_postazioni_max: p.postazioni,
    p_riferimento: dati.riferimento || null, p_stripe_cliente: dati.stripe_cliente || null,
    p_stripe_abbonamento: dati.stripe_abbonamento || null, p_rivenditore: dati.rivenditore || null,
    p_codice_sconto: dati.codice_sconto || null, p_dati_fiscali: dati.dati_fiscali || {},
  });
  await db.rpc("airender_accredita", {
    p_licenza: creata.id, p_origine: "benvenuto", p_quantita: listino.benvenuto.render,
    p_scade_il: traMesi(listino.benvenuto.validita_mesi), p_riferimento: `benvenuto:${creata.id}`,
  });

  let codiceDaMandare = creata.nuova ? codice : null;
  if (!creata.nuova) {
    // Stripe ha ripetuto l'evento. Se l'email era gia' partita non si fa
    // niente; se no il codice di allora e' perso (c'e' solo il suo hash) e se
    // ne genera uno nuovo, che sostituisce il vecchio.
    const [licenza] = await db.select("licenze", `id=eq.${creata.id}&select=email_inviata_il`);
    if (!licenza?.email_inviata_il) {
      await db.aggiorna("licenze", `id=eq.${creata.id}`, { hash_codice: hashCodice(codice), ultime_cifre: ultimeCifre(codice) });
      codiceDaMandare = codice;
    }
  }
  if (codiceDaMandare && email && dati.manda_email !== false) {
    await email.inviaCodice(dati.email, codiceDaMandare, p.nome);
    await db.aggiorna("licenze", `id=eq.${creata.id}`, { email_inviata_il: new Date().toISOString() });
  }
  return { id: creata.id, nuova: creata.nuova, codice: codiceDaMandare };
}

// Un codice nuovo per una licenza esistente (codice perso o finito in mani
// sbagliate): il vecchio smette di funzionare subito.
export async function nuovoCodice({ db, email }, licenza, casuale) {
  const codice = generaCodice(casuale);
  await db.aggiorna("licenze", `id=eq.${licenza.id}`, { hash_codice: hashCodice(codice), ultime_cifre: ultimeCifre(codice) });
  if (email) await email.inviaCodice(licenza.email, codice, pianoDi(licenza.piano).nome);
  return codice;
}

export async function accredita({ db }, licenzaId, origine, quantita, scadeIl, riferimento) {
  return db.rpc("airender_accredita", {
    p_licenza: licenzaId, p_origine: origine, p_quantita: quantita, p_scade_il: scadeIl, p_riferimento: riferimento,
  });
}

export async function cambiaPiano({ db }, licenzaId, piano) {
  await db.aggiorna("licenze", `id=eq.${licenzaId}`, { piano, postazioni_max: pianoDi(piano).postazioni });
}
