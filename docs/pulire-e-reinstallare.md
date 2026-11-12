# Rifare la prova sul PC con le versioni vecchie (Allplan 2027)

Per la prova come cliente **non serve lo ZIP del repository**: si usa solo
`AIRENDER-2027.allep` (versione 1.0.15, aggiornata alla PR #84). Lo ZIP serve
solo per l'installazione da sviluppatore (in fondo).

## 1. Chiudi tutto

Chiudi Allplan e la finestra di Edge dello Studio.

## 2. Se avevi trascinato un .allep vecchio

Apri Allplan, **Plugin Manager**, disinstalla AIRENDER, chiudi Allplan.
Se non c'è nell'elenco, salta questo passo.

## 3. Pulisci con PowerShell

Apri PowerShell (non serve da amministratore) e incolla un blocco alla volta.

Ferma Studio e coda di AIRENDER, se sono ancora accesi:

```powershell
Get-CimInstance Win32_Process -Filter "Name like 'python%'" |
  Where-Object { $_.CommandLine -match 'core\.(studio|coda)' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force; "fermato $($_.ProcessId)" }
```

Trova la cartella Usr di Allplan 2027:

```powershell
$usr = @(
  "$env:USERPROFILE\Documents\Nemetschek\Allplan\2027\Usr\Local",
  "$env:OneDrive\Documents\Nemetschek\Allplan\2027\Usr\Local",
  "$env:OneDrive\Documenti\Nemetschek\Allplan\2027\Usr\Local",
  "C:\Data\Allplan\Allplan 2027\Usr\Local"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
"Usr: $usr"
```

Se scrive `Usr:` vuoto, trova la cartella a mano (quella che contiene
`PythonParts-site-packages`) e scrivi `$usr = "il percorso"`.

Togli i file vecchi di AIRENDER:

```powershell
$vecchi = @(
  "$usr\PythonPartsScripts\airender",
  "$usr\PythonPartsScripts\riccardo_silingardi\airender",
  "$usr\PythonPartsActionbar\riccardo_silingardi\airender",
  "$usr\Library\AIRENDER"
)
foreach ($v in $vecchi) { if (Test-Path $v) { Remove-Item $v -Recurse -Force; "tolto $v" } }
```

**Non** si toccano `$usr\AIRENDER` (le viste catturate e i render) né i materiali o i progetti di Allplan.

### Facoltativo: provare come un PC davvero pulito

Per vedere se basta il Pillow dentro il pacchetto, metti da parte quello
installato con l'SDK (si rimette rinominandolo di nuovo):

```powershell
$sp = "$usr\PythonParts-site-packages"
Get-ChildItem $sp -Directory | Where-Object { $_.Name -eq 'PIL' -or $_.Name -like 'pillow-*' } |
  ForEach-Object { Rename-Item $_.FullName "$($_.Name).accantonato"; "accantonato $($_.Name)" }
```

Per rimetterlo: stesso comando con `-like '*.accantonato'` e il nome senza
`.accantonato`. Finché è accantonato, gli altri PythonParts che usano Pillow
non lo trovano: rimettilo a fine prova.

Per provare anche l'inserimento del codice licenza da zero, metti da parte
quello salvato (si rimette rinominandolo di nuovo):

```powershell
if (Test-Path "$env:APPDATA\AIRENDER") { Rename-Item "$env:APPDATA\AIRENDER" "AIRENDER.accantonato" }
```

## 4. Installa e prova

Segui `prova-pc-pulito.md` dal passo 0: controlla l'impronta con
`Get-FileHash`, trascina l'.allep in Allplan, riavvia, nel Plugin Manager deve
comparire **AIRENDER 1.0.15**. In `avvio.txt` la riga «Pillow scelto» dice se
usa il Pillow del pacchetto o quello di Allplan.

## In alternativa: da sviluppatore, dallo ZIP

Scompatta lo ZIP del repository, apri PowerShell nella cartella e:

```powershell
py allplan\v2027\pacchetto.py --installa
```

Ferma da solo Studio e coda, toglie le versioni vecchie e copia la nuova nella
Usr. Non è la prova del cliente: salta il drag & drop.
