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
