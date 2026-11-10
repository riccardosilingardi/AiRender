# Workflow di AIRENDER per la Comfy Developer Platform

`tieni-geometria.json` è il workflow di «Tieni la geometria» in formato API
(Z-Image-Turbo con il ControlNet Fun Union, dal modello comfy.org
`image_z_image_turbo_fun_union_controlnet`). È il file da caricare così com'è
sulla Developer Platform:

1. Developer Platform → nuovo workflow → carica `tieni-geometria.json`.
2. Build: la piattaforma fissa ComfyUI e i modelli che il file nomina
   (z_image_turbo_bf16, qwen_3_4b, ae, Z-Image-Turbo-Fun-Controlnet-Union).
3. Endpoint Serverless: scegli GPU e worker, copia l'indirizzo
   `https://<nome>.run.comfy.app`.
4. Sul PC: `setx AIRENDER_COMFY_WORKFLOW_URL https://<nome>.run.comfy.app`,
   poi riapri lo Studio. La chiave resta `COMFY_API_KEY`.

Dal 2026-11-09 il file ha tre controlli, che l'utente spunta nello Studio:
**Spigoli** (nodi 3 Canny e 8), **Profondità** (17 `DepthAnythingV2Preprocessor`
e 18) e **Linee dritte** (19 `M-LSDPreprocessor` e 20). Il motore toglie dal
grafo quelli non spuntati e incatena gli altri sul modello. Profondità e Linee
dritte vengono dal custom node **comfyui_controlnet_aux** (e dal modello
`depth_anything_v2_vitl.pth`): la build deve installarlo. Va rifatta la build
col file nuovo, anche se il deployment c'era già.

Dal 2026-11-10 ci sono anche i nodi 21 (`LoadImage` del render), 22
(`ImageScale` alla misura della vista) e 23 (`VAEEncode`), usati solo da
«Riaggancia alla vista»: il campionatore parte dal render invece che dal
latente vuoto (nodo 14) e ne rifà una parte. Per gli altri invii il motore li
toglie. Anche questi vanno nella build.

Il motore riempie a ogni invio i nodi 1 (la vista caricata come asset), 2 (lato
massimo), 6 (prompt), 8 (forza del ControlNet) e 9 (seme e passi), coi valori
di `core/config.py`. I valori scritti nel file servono solo alla build.
