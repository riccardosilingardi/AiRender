import { deflateSync } from "node:zlib";
// I dati compressi di una riga di un pixel: bastano a fare un IDAT vero.
export const zlibSync = () => deflateSync(Buffer.from([0, 0, 0, 0]));
