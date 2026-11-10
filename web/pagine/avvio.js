// L'ingresso della web app: accesso con email e codice licenza, poi lo Studio.
//
// 1. una sola scheda alla volta (la cartella nel browser e' una sola);
// 2. il service worker (sw.js) che fa da server locale dello Studio;
// 3. il motore (motore.js) che parte subito, mentre si compila l'accesso;
// 4. l'accesso: di solito un link via email (/api/link-accesso lo manda,
//    /api/accedi lo scambia con una chiave di questo browser); oppure email
//    e codice licenza. Poi lo Studio salva la chiave come il codice sul PC;
// 5. lo Studio: la stessa pagina e lo stesso studio.js dello Studio sul PC.

(() => {
  const $ = (id) => document.getElementById(id);
  const statoMotore = { pronto: false, errore: null, attesa: [] };
  let motore = null;

  function avviso(dove, fatto, cosaFare) {
    const box = $(dove);
    box.hidden = false;
    box.className = "avviso errore";
    box.setAttribute("role", "alert");
    box.replaceChildren();
    const b = document.createElement("b"); b.textContent = fatto;
    const s = document.createElement("span"); s.className = "cosa-fare"; s.textContent = cosaFare || "";
    box.append(b, s);
  }
  const nascondi = (dove) => { $(dove).hidden = true; };

  function memoria(chiave, valore) {
    try {
      if (valore === undefined) return localStorage.getItem(chiave);
      localStorage.setItem(chiave, valore);
    } catch (e) { /* senza localStorage si vive lo stesso */ }
    return null;
  }

  // Un'impronta di questo browser: il server conta le postazioni con questa.
  function postazione() {
    let id = memoria("airender-postazione");
    if (!id) {
      id = (self.crypto && crypto.randomUUID) ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      memoria("airender-postazione", id);
    }
    return id;
  }

  function motorePronto() {
    if (statoMotore.pronto) return Promise.resolve();
    if (statoMotore.errore) return Promise.reject(statoMotore.errore);
    return new Promise((fatto, fallito) => statoMotore.attesa.push([fatto, fallito]));
  }

  function collega() {
    const canale = new MessageChannel();
    motore.postMessage({ tipo: "porta-sw" }, [canale.port1]);
    navigator.serviceWorker.controller.postMessage({ tipo: "collega" }, [canale.port2]);
  }

  function scarica(nome, corpo) {
    const url = URL.createObjectURL(new Blob([corpo]));
    const a = document.createElement("a");
    a.href = url; a.download = nome; document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  }

  async function avviaMotore() {
    await navigator.serviceWorker.register("/studio/sw.js", { scope: "/studio/" });
    await navigator.serviceWorker.ready;
    if (!navigator.serviceWorker.controller) {
      await new Promise((fatto) => navigator.serviceWorker.addEventListener("controllerchange", fatto, { once: true }));
    }
    navigator.serviceWorker.addEventListener("message", (e) => { if (e.data && e.data.tipo === "ricollega") collega(); });
    motore = new Worker("/studio/motore.js");
    motore.onmessage = (e) => {
      const m = e.data || {};
      if (m.tipo === "avanzamento") $("motore") && ($("motore").textContent = m.testo);
      if (m.tipo === "scarica") scarica(m.nome, m.corpo);
      if (m.tipo === "avviso") console.warn(m.testo);
      if (m.tipo === "pronto") {
        statoMotore.pronto = true;
        if ($("motore")) $("motore").textContent = "Studio pronto.";
        statoMotore.attesa.forEach(([fatto]) => fatto());
      }
      if (m.tipo === "errore") {
        statoMotore.errore = m;
        if ($("motore")) { $("motore").hidden = true; avviso("errore-motore", m.fatto, m.cosa_fare); }
        statoMotore.attesa.forEach(([, fallito]) => fallito(m));
      }
    };
    collega();
    motore.postMessage({ tipo: "prepara", postazione: postazione(), server: location.origin });
  }

  async function leggi(metodo, url, corpo) {
    const r = await fetch(url, {
      method: metodo,
      headers: metodo === "POST" ? { "Content-Type": "application/json", "X-Airender": "1" } : {},
      body: corpo ? JSON.stringify(corpo) : undefined,
    });
    return { ok: r.ok, dati: await r.json().catch(() => ({})) };
  }

  // Questo browser ha gia' una licenza salvata nello Studio: alla prossima
  // apertura il modulo di accesso non si mostra, si aspetta il motore.
  const COLLEGATO = "airender-collegato";
  // L'utente ha scelto di entrare con un link o un codice: la licenza gia'
  // salvata non deve aprire lo Studio da sola mentre aspetta l'email.
  let cambio = false;

  function apriStudio() {
    memoria(COLLEGATO, "1");
    const corpo = $("corpo-studio").content.cloneNode(true);
    document.body.replaceChildren(corpo);
    const script = document.createElement("script");
    script.src = "/studio/pagine/studio.js";
    document.body.append(script);
  }

  let colCodice = false;
  function modoCodice(si) {
    colCodice = si;
    $("riga-codice").hidden = !si;
    $("entra").textContent = si ? "Entra" : "Mandami il link";
    $("col-codice").textContent = si ? "Mandami un link invece" : "Ho il codice licenza";
    $("spiega-accesso").firstChild.textContent = si
      ? "Il codice è nell'email che hai ricevuto dopo l'acquisto. Non hai una licenza? "
      : "Ti mandiamo un link all'email con cui hai comprato AIRENDER: lo apri in questo browser e sei dentro. Non hai una licenza? ";
    nascondi("errore-accesso");
    $("stato-accesso").textContent = "";
  }

  function rifiuto(dati, campi) {
    const e = dati.error || {};
    for (const c of campi) $(c).setAttribute("aria-invalid", "true");
    avviso("errore-accesso", e.message || "Il server AIRENDER non ha accettato l'accesso.", dati.cosa_fare || "Riprova.");
  }

  // Il codice (o la chiave del link) va allo Studio nel browser, che lo salva.
  async function salvaEdApri(codice) {
    $("stato-accesso").textContent = "Licenza trovata. Aspetto che lo Studio sia pronto nel browser…";
    await motorePronto();
    const salvata = await leggi("POST", "/studio/api/licenza", { codice });
    if (!salvata.ok) {
      const e = salvata.dati.errore || {};
      avviso("errore-accesso", e.fatto || "Lo Studio non ha salvato il codice.", e.cosa_fare || "Riprova.");
      return false;
    }
    apriStudio();
    return true;
  }

  async function entra(evento) {
    evento.preventDefault();
    cambio = true;
    nascondi("errore-accesso");
    const email = $("email").value.trim();
    const codice = $("codice").value.trim();
    $("email").removeAttribute("aria-invalid");
    $("codice").removeAttribute("aria-invalid");
    $("entra").disabled = true;
    let messaggio = "";
    try {
      if (!colCodice) {
        $("stato-accesso").textContent = `Chiedo al server AIRENDER (${location.host}) di mandarti il link.`;
        const r = await leggi("POST", "/api/link-accesso", { email });
        if (!r.ok) { rifiuto(r.dati, ["email"]); return; }
        messaggio = `${r.dati.messaggio} Se non arriva, guarda nella posta indesiderata.`;
        return;
      }
      $("stato-accesso").textContent = `Chiedo al server AIRENDER (${location.host}) se email e codice sono di una licenza.`;
      const accesso = await leggi("POST", "/api/accedi", { email, codice });
      if (!accesso.ok) { rifiuto(accesso.dati, ["email", "codice"]); return; }
      await salvaEdApri(codice);
    } catch (e) {
      if (e && e.fatto) avviso("errore-accesso", e.fatto, e.cosa_fare);
      else avviso("errore-accesso", "Il server AIRENDER non ha risposto.", "Controlla la connessione e riprova.");
    } finally {
      if ($("entra")) $("entra").disabled = false;
      if ($("stato-accesso")) $("stato-accesso").textContent = messaggio;
    }
  }

  // Il link dell'email: https://.../studio/#accesso=<gettone>. Il gettone
  // sparisce subito dall'indirizzo (e dalla cronologia) e vale una volta sola.
  function gettoneNelLink() {
    const m = /^#accesso=([A-Za-z0-9_-]+)$/.exec(location.hash);
    return m ? m[1] : null;
  }
  const togliGettone = () => history.replaceState(null, "", location.pathname + location.search);
  function gettoneDalLink() {
    const g = gettoneNelLink();
    if (g) togliGettone();
    return g;
  }

  // Lo Studio e' gia' aperto in questa scheda e arriva un link da un'altra:
  // si scambia il link con la chiave, la si salva e si ricarica lo Studio.
  async function linkNelloStudio(gettone) {
    const accesso = await leggi("POST", "/api/accedi", { link: gettone });
    if (!accesso.ok) {
      const e = accesso.dati.error || {};
      return { ok: false, fatto: e.message || "Il server AIRENDER non ha accettato il link.", cosa_fare: accesso.dati.cosa_fare || "Chiedine un altro." };
    }
    const salvata = await leggi("POST", "/studio/api/licenza", { codice: accesso.dati.codice });
    if (!salvata.ok) {
      const e = salvata.dati.errore || {};
      return { ok: false, fatto: e.fatto || "Lo Studio non ha salvato la licenza.", cosa_fare: e.cosa_fare || "Riprova." };
    }
    return { ok: true };
  }

  // Le due strade dell'ingresso: il modulo, o «gia' collegato» mentre il
  // motore parte.
  function mostraModulo() {
    $("gia-collegato").hidden = true;
    $("modulo").hidden = false;
  }

  async function entraColLink(gettone) {
    $("entra").disabled = true;
    $("stato-accesso").textContent = `Controllo il link con il server AIRENDER (${location.host})…`;
    try {
      const accesso = await leggi("POST", "/api/accedi", { link: gettone });
      if (!accesso.ok) { rifiuto(accesso.dati, []); $("stato-accesso").textContent = ""; return false; }
      if (accesso.dati.email) $("email").value = accesso.dati.email;
      return await salvaEdApri(accesso.dati.codice);
    } catch (e) {
      if (e && e.fatto) avviso("errore-accesso", e.fatto, e.cosa_fare);
      else avviso("errore-accesso", "Il server AIRENDER non ha risposto.", "Controlla la connessione e chiedi un altro link.");
      return false;
    } finally {
      if ($("entra")) $("entra").disabled = false;
    }
  }

  async function avvia() {
    if (!("serviceWorker" in navigator) || !self.Worker) {
      avviso("errore-motore", "Questo browser non può far girare lo Studio.", "Apri la web app con Chrome o Edge aggiornati.");
      $("motore").hidden = true;
      return;
    }
    $("modulo").addEventListener("submit", entra);
    $("col-codice").addEventListener("click", () => modoCodice(!colCodice));
    $("altra-licenza").addEventListener("click", () => { cambio = true; mostraModulo(); $("email").focus(); });
    // Il link aperto nella stessa scheda (cambia solo il #) o in un'altra
    // scheda mentre questa tiene lo Studio: si entra qui.
    window.addEventListener("hashchange", () => {
      const g = gettoneDalLink();
      if (g && $("modulo")) { cambio = true; mostraModulo(); entraColLink(g); }
    });
    if (self.BroadcastChannel) {
      const canale = new BroadcastChannel("airender-accesso");
      canale.onmessage = async (e) => {
        const g = e.data && e.data.gettone;
        if (!g) return;
        window.focus();
        if ($("modulo")) {
          cambio = true; mostraModulo();
          const ok = await entraColLink(g);
          canale.postMessage({ risposta: ok ? "entrato" : "rifiutato" });
          return;
        }
        let esito;
        try { esito = await linkNelloStudio(g); } catch (err) {
          esito = { ok: false, fatto: "Il server AIRENDER non ha risposto.", cosa_fare: "Controlla la connessione e chiedi un altro link." };
        }
        canale.postMessage({ risposta: esito.ok ? "entrato" : "rifiutato", fatto: esito.fatto, cosa_fare: esito.cosa_fare });
        if (esito.ok) location.reload();
      };
    }
    const gettone = gettoneDalLink();
    if (gettone) cambio = true;
    else if (memoria(COLLEGATO)) {
      $("modulo").hidden = true;
      $("gia-collegato").hidden = false;
    }
    const colLink = gettone ? entraColLink(gettone) : Promise.resolve(false);
    try {
      await avviaMotore();
      await motorePronto();
      // Codice gia' salvato in questo browser: si entra senza ripetere l'accesso.
      // Col link si entra da entraColLink; se il link non vale piu' ma questo
      // browser ha gia' una licenza salvata, si entra con quella.
      if (await colLink) return;
      const licenza = await leggi("GET", "/studio/api/licenza");
      const presente = licenza.ok && licenza.dati.presente;
      if (presente && !cambio) { apriStudio(); return; }
      if (!presente) { try { localStorage.removeItem(COLLEGATO); } catch (e) { /* niente */ } }
      mostraModulo();
    } catch (e) {
      if (!statoMotore.errore) {
        $("motore").hidden = true;
        avviso("errore-motore", "Lo Studio non è partito nel browser.", "Ricarica la pagina. Se si ripete, prova con Chrome o Edge aggiornati.");
      }
    }
  }

  const unaScheda = navigator.locks && navigator.locks.request;
  if (!unaScheda) { avvia(); return; }
  navigator.locks.request("airender-studio", { ifAvailable: true }, (blocco) => {
    if (!blocco) {
      $("modulo").hidden = true;
      $("motore").hidden = true;
      const gettone = gettoneNelLink();
      if (gettone && self.BroadcastChannel) {
        // Il link dell'email si e' aperto in una scheda nuova: lo passa a
        // quella dove lo Studio e' gia' aperto, che lo usa e risponde. Si
        // dice com'e' andata solo dopo la risposta.
        const canale = new BroadcastChannel("airender-accesso");
        const stato = $("motore");
        stato.hidden = false;
        stato.textContent = "AIRENDER Studio è già aperto in un'altra scheda: gli passo il link…";
        const attesa = setTimeout(() => {
          canale.close();
          stato.hidden = true;
          avviso("errore-motore", "L'altra scheda di AIRENDER Studio non ha risposto.",
            "Chiudi l'altra scheda e ricarica questa pagina: il link non è ancora stato usato.");
        }, 20000); // numero-non-configurabile: attesa della risposta dell'altra scheda, compresa la chiamata al server
        canale.onmessage = (e) => {
          const m = e.data || {};
          if (!m.risposta) return;
          clearTimeout(attesa);
          canale.close();
          togliGettone();
          stato.hidden = true;
          if (m.risposta === "entrato") {
            const box = $("errore-motore");
            box.hidden = false;
            box.className = "avviso";
            box.setAttribute("role", "status");
            box.replaceChildren();
            const b = document.createElement("b"); b.textContent = "Fatto: la licenza del link è collegata nell'altra scheda, che si è riaperta.";
            const sp = document.createElement("span"); sp.className = "cosa-fare"; sp.textContent = "Torna a quella scheda. Questa puoi chiuderla.";
            box.append(b, sp);
          } else {
            avviso("errore-motore", m.fatto || "Il link non è stato accettato.", m.cosa_fare || "Chiedine un altro dalla pagina di accesso.");
          }
        };
        canale.postMessage({ gettone });
        return null;
      }
      avviso("errore-motore", "Lo Studio è già aperto in un'altra scheda di questo browser.",
        "Usa quella scheda, oppure chiudila e ricarica questa pagina.");
      return null;
    }
    avvia();
    return new Promise(() => {}); // tenuto finche' la scheda resta aperta
  });
})();
