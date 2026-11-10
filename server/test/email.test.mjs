import { test } from "node:test";
import assert from "node:assert/strict";
import { creaEmail, mittente } from "../lib/email.mjs";

function registra() {
  const chiamate = [];
  const chiama = async (url, opzioni) => { chiamate.push({ url, ...opzioni, corpo: JSON.parse(opzioni.body) }); return new Response("{}", { status: 200 }); };
  return { chiamate, chiama };
}

test("il mittente si legge con o senza nome", () => {
  assert.deepEqual(mittente("AIRENDER <a@b.it>"), { nome: "AIRENDER", indirizzo: "a@b.it" });
  assert.deepEqual(mittente("a@b.it"), { nome: "", indirizzo: "a@b.it" });
});

test("con le chiavi Mailjet l'email parte da Mailjet, con l'autenticazione Basic", async () => {
  const { chiamate, chiama } = registra();
  const ambiente = { MAILJET_API_KEY: "k", MAILJET_SECRET_KEY: "s", EMAIL_MITTENTE: "AIRENDER <a@b.it>", SITO_URL: "https://x" };
  await creaEmail(ambiente, chiama).inviaCodice("c@d.it", "AIR-0000-1111-2222-3333", "Prova");
  assert.equal(chiamate.length, 1);
  assert.equal(chiamate[0].url, "https://api.mailjet.com/v3.1/send");
  assert.equal(chiamate[0].headers.authorization, `Basic ${Buffer.from("k:s").toString("base64")}`);
  const m = chiamate[0].corpo.Messages[0];
  assert.deepEqual(m.From, { Email: "a@b.it", Name: "AIRENDER" });
  assert.deepEqual(m.To, [{ Email: "c@d.it" }]);
  assert.match(m.TextPart, /AIR-0000-1111-2222-3333/);
});

test("senza Mailjet resta Resend", async () => {
  const { chiamate, chiama } = registra();
  await creaEmail({ RESEND_API_KEY: "r", EMAIL_MITTENTE: "a@b.it", SITO_URL: "https://x" }, chiama).inviaCodice("c@d.it", "AIR-X", "Pro");
  assert.equal(chiamate[0].url, "https://api.resend.com/emails");
});

test("una risposta di errore del servizio fa fallire l'invio", async () => {
  const chiama = async () => new Response("no", { status: 401 });
  const ambiente = { MAILJET_API_KEY: "k", MAILJET_SECRET_KEY: "s", EMAIL_MITTENTE: "a@b.it", SITO_URL: "https://x" };
  await assert.rejects(creaEmail(ambiente, chiama).inviaCodice("c@d.it", "AIR-X", "Pro"), /Email: 401/);
});

test("l'email del link elenca una riga per licenza, con la durata", async () => {
  const { chiamate, chiama } = registra();
  const ambiente = { MAILJET_API_KEY: "k", MAILJET_SECRET_KEY: "s", EMAIL_MITTENTE: "a@b.it" };
  await creaEmail(ambiente, chiama).inviaLink("c@d.it", [
    { nomePiano: "Pro", ultime_cifre: "3333", render: 19, link: "https://x/studio/#accesso=abc" },
    { nomePiano: "Prova", ultime_cifre: "7777", render: 1, link: "https://x/studio/#accesso=def" },
  ], 15);
  const m = chiamate[0].corpo.Messages[0];
  assert.equal(m.Subject, "Il tuo link per entrare in AIRENDER Studio");
  assert.match(m.TextPart, /hai 2 licenze, ognuna col suo saldo/);
  assert.match(m.TextPart, /Licenza Pro, codice che finisce con 3333, 19 render disponibili:\n {4}https:\/\/x\/studio\/#accesso=abc/);
  assert.match(m.TextPart, /Licenza Prova, codice che finisce con 7777, 1 render disponibile:/);
  assert.match(m.TextPart, /15 minuti e una volta sola/);
});
