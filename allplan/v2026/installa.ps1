# Copia AIRENDER (palette v1), AIRENDER prova e AIRENDER sonda nella cartella utente (Usr) di Allplan 2026.
#
# Uso, da PowerShell nella cartella del repository:
#   powershell -ExecutionPolicy Bypass -File allplan\v2026\installa.ps1
# oppure, se la tua cartella Usr e' altrove:
#   powershell -ExecutionPolicy Bypass -File allplan\v2026\installa.ps1 -Usr "D:\...\Usr\Local"
#
# La cartella Usr giusta e' quella che contiene "PythonParts-site-packages"
# dopo che hai installato Pillow con lo strumento "Install Python Package" del
# PythonParts SDK (destinazione USR).

param(
    [string]$Usr = "$env:USERPROFILE\Documents\Nemetschek\Allplan\2026\Usr\Local"
)

$ErrorActionPreference = "Stop"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")

if (-not (Test-Path $Usr)) {
    Write-Host "Non trovo la cartella Usr di Allplan: $Usr"
    Write-Host "Cosa fare: cerca la cartella 'PythonParts-site-packages' e rilancia con -Usr <la cartella che la contiene>."
    exit 1
}

$script = Join-Path $Usr "PythonPartsScripts\airender"
$libreria = Join-Path $Usr "Library\AIRENDER"
New-Item -ItemType Directory -Force -Path $script, $libreria | Out-Null

# Il motore viene ricopiato da zero: niente file vecchi che restano indietro.
if (Test-Path "$script\core") { Remove-Item -Recurse -Force "$script\core" }
Copy-Item -Recurse (Join-Path $repo "core") "$script\core"
Get-ChildItem -Recurse -Directory -Filter "__pycache__" "$script\core" | Remove-Item -Recurse -Force

Copy-Item (Join-Path $repo "allplan\comune\ponte.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "PythonPartsScripts\airender\AirenderProva.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "Library\AIRENDER\AirenderProva.pyp") $libreria -Force

# La sonda della palette (piano UI del 2026-10-27): script, processo di prova,
# palette e le sue immagini, che devono stare accanto al .pyp.
Copy-Item (Join-Path $repo "allplan\comune\sonda_palette.py") $script -Force
Copy-Item (Join-Path $repo "allplan\comune\sonda_figlio.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "PythonPartsScripts\airender\AirenderSonda.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "Library\AIRENDER\AirenderSonda.pyp") $libreria -Force
Copy-Item (Join-Path $PSScriptRoot "Library\AIRENDER\sonda_*.png") $libreria -Force

# La palette v1 (prompt 7): telecomando, adattatore, .pyp e il segnaposto
# delle immagini, che deve stare accanto al .pyp. Prova e sonda restano
# finche' Riccardo non dice che la v1 le sostituisce.
Copy-Item (Join-Path $repo "allplan\comune\telecomando.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "PythonPartsScripts\airender\AirenderPalette.py") $script -Force
Copy-Item (Join-Path $PSScriptRoot "Library\AIRENDER\AirenderPalette.pyp") $libreria -Force
Copy-Item (Join-Path $PSScriptRoot "Library\AIRENDER\palette_nessuna.png") $libreria -Force

Write-Host "Fatto."
Write-Host "  script:   $script"
Write-Host "  libreria: $libreria"
Write-Host "In Allplan: Libreria > Privato > AIRENDER > AIRENDER (la palette v1; restano AIRENDER prova e AIRENDER sonda)."
