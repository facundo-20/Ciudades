# FNS 2026 · instala todo y corre la cañería Meshy → Blender → FBX, sin tocar nada a mano.
#
# Doble clic en INSTALAR_Y_CORRER.bat (que llama a este archivo), o en PowerShell:
#   irm https://raw.githubusercontent.com/facundo-20/Ciudades/claude/fiesta-sol-2026-immersive-ph9915/fns2026/pipeline/instalar_windows.ps1 | iex
#
# Qué hace, y se puede correr las veces que haga falta (lo que ya está, lo saltea):
#   1. Python, Git y Blender con winget, si faltan
#   2. baja o actualiza el proyecto en Documentos\Ciudades
#   3. pide la clave de Meshy UNA vez (oculta) y la guarda en tu usuario de Windows
#   4. corre correr_todo.py y abre la galería con las vistas previas
#
# Argumentos opcionales que pasan a correr_todo.py, por ejemplo:
#   .\instalar_windows.ps1 --destino todos
#   .\instalar_windows.ps1 --solo el_hongo bochas

$ErrorActionPreference = "Stop"
$RAMA = "claude/fiesta-sol-2026-immersive-ph9915"
$REPO = "https://github.com/facundo-20/Ciudades.git"

function Paso($t) { Write-Host "`n== $t" -ForegroundColor Yellow }
function RefrescarPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Instalar($id, $prueba) {
    if (& $prueba) { Write-Host "   $id ya está"; return }
    Write-Host "   instalando $id…"
    winget install --id $id -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
    RefrescarPath
}

Paso "1/4 Programas"
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "Falta winget. Instalá 'App Installer' desde Microsoft Store y volvé a correr esto."
}
Instalar "Python.Python.3.12" { Get-Command py -ErrorAction SilentlyContinue }
Instalar "Git.Git" { Get-Command git -ErrorAction SilentlyContinue }
Instalar "BlenderFoundation.Blender" { Test-Path "C:\Program Files\Blender Foundation\Blender*\blender.exe" }
$python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

Paso "2/4 Proyecto"
# si este script ya está adentro del repo (doble clic en el .bat), se usa ése
$aqui = if ($PSScriptRoot) { $PSScriptRoot } else { "" }
if ($aqui -and (Test-Path (Join-Path $aqui "correr_todo.py"))) {
    $pipeline = $aqui
    $raiz = (Resolve-Path (Join-Path $aqui "..\..")).Path
    if (Test-Path (Join-Path $raiz ".git")) { git -C $raiz pull --ff-only origin $RAMA | Out-Host }
} else {
    $raiz = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Ciudades"
    if (Test-Path (Join-Path $raiz ".git")) {
        git -C $raiz fetch origin $RAMA | Out-Host
        git -C $raiz checkout $RAMA | Out-Host
        git -C $raiz pull --ff-only origin $RAMA | Out-Host
    } else {
        git clone -b $RAMA $REPO $raiz | Out-Host
    }
    $pipeline = Join-Path $raiz "fns2026\pipeline"
}
Write-Host "   proyecto en $raiz"

Paso "3/4 Clave de Meshy"
$clave = [Environment]::GetEnvironmentVariable("MESHY_API_KEY", "User")
if (-not $clave) {
    Write-Host "   Sacala de meshy.ai → tu perfil → API. Se guarda sólo en tu usuario de Windows."
    $seg = Read-Host "   Pegá la clave (no se ve mientras escribís)" -AsSecureString
    $clave = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($seg))
    if (-not $clave) { throw "No se cargó ninguna clave." }
    [Environment]::SetEnvironmentVariable("MESHY_API_KEY", $clave, "User")
    Write-Host "   guardada. Para cambiarla: borrá la variable MESHY_API_KEY de tu usuario."
} else {
    Write-Host "   ya está guardada"
}
$env:MESHY_API_KEY = $clave

Paso "4/4 Meshy → Blender → FBX"
Set-Location $pipeline
& $python correr_todo.py @args
$codigo = $LASTEXITCODE
Write-Host ""
if ($codigo -eq 0) {
    Write-Host "Listo. Los FBX están en $raiz\fns2026\modelos" -ForegroundColor Green
} else {
    Write-Host "Algunos modelos fallaron. El detalle está en $raiz\fns2026\correr_todo.log" -ForegroundColor Red
    Write-Host "Volvé a correr lo mismo: sigue desde donde quedó sin gastar créditos de nuevo."
}
