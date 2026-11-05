# Workflow di AIRENDER per la Comfy Developer Platform

`tieni-geometria.json` è il workflow di «Tieni la geometria» in formato API
(Z-Image-Turbo con il ControlNet Fun Union sugli spigoli, dal modello comfy.org
`image_z_image_turbo_fun_union_controlnet`). È il file da caricare così com'è
sulla Developer Platform:

1. Developer Platform → nuovo workflow → carica `tieni-geometria.json`.
2. Build: la piattaforma fissa ComfyUI e i modelli che il file nomina
   (z_image_turbo_bf16, qwen_3_4b, ae, Z-Image-Turbo-Fun-Controlnet-Union).
3. Endpoint Serverless: scegli GPU e worker, copia l'indirizzo
   `https://<nome>.run.comfy.app`.
4. Sul PC: `setx AIRENDER_COMFY_WORKFLOW_URL https://<nome>.run.comfy.app`,
   poi riapri lo Studio. La chiave resta `COMFY_API_KEY`.

Il motore riempie a ogni invio i nodi 1 (la vista caricata come asset), 2 (lato
massimo), 6 (prompt), 8 (forza del ControlNet) e 9 (seme e passi), coi valori
di `core/config.py`. I valori scritti nel file servono solo alla build.
