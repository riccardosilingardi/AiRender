// GET /api/listino: il listino pubblico, per la pagina dei prezzi.
import { listino } from "../../lib/listino.mjs";
import { json, protetto } from "../../lib/risposte.mjs";

export default protetto("listino", () => json(200, listino, { "cache-control": "public, max-age=300" }));

export const config = { path: "/api/listino" };
