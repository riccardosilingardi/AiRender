// Risposte JSON. Un errore porta sempre il fatto e il gesto successivo, in
// italiano, come gli errori del motore: il plugin li mostra cosi' come sono.

export function json(stato, corpo, intestazioni = {}) {
  return new Response(JSON.stringify(corpo), {
    status: stato,
    headers: { "content-type": "application/json; charset=utf-8", ...intestazioni },
  });
}

export function errore(stato, tipo, messaggio, cosaFare, extra = {}) {
  return json(stato, { error: { type: tipo, message: messaggio }, cosa_fare: cosaFare, ...extra });
}

// Ogni funzione passa da qui: un'eccezione imprevista (Supabase giu', una
// variabile d'ambiente mancante, una risposta strana di Stripe) diventa un
// errore JSON in italiano, che il plugin mostra cosi' com'e', e una riga nel
// log di Netlify con il nome della funzione. Senza, Netlify risponde con un
// 500 vuoto e il plugin non sa cosa dire. Nel log non va mai il corpo della
// richiesta (porta il codice licenza e la vista).
export function protetto(nome, gestore, log = console.error) {
  return async (req, ...resto) => {
    try {
      return await gestore(req, ...resto);
    } catch (e) {
      const percorso = (() => { try { return new URL(req.url).pathname; } catch { return "?"; } })();
      log(JSON.stringify({ funzione: nome, percorso, metodo: req.method, tipo: e?.constructor?.name, errore: String(e?.message || e) }));
      if (e?.name === "VariabileMancante" || e?.constructor?.name === "VariabileMancante") {
        return errore(503, "servizio_non_configurato",
          "Il server AIRENDER non e' configurato del tutto e non ha fatto niente.",
          "Riprova piu' tardi; se dura, scrivi a AIRENDER.");
      }
      return errore(500, "errore_interno",
        "Il server AIRENDER ha avuto un problema interno e si e' fermato.",
        "Riprova fra un minuto; se si ripete, scrivi a AIRENDER con l'ora dell'errore.");
    }
  };
}
