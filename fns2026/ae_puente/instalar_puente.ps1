# Instalador del puente de After Effects (Windows). Una sola línea en PowerShell:
#
#   irm https://raw.githubusercontent.com/facundo-20/Ciudades/claude/fiesta-sol-2026-immersive-ph9915/fns2026/ae_puente/instalar_puente.ps1 | iex
#
# Qué hace, y por qué:
#   1. Instala Git y Node con winget si faltan (el puente usa los dos).
#   2. Clona el repo en Documentos\Ciudades_puente, o lo actualiza si ya está. Es una carpeta
#      aparte: no toca Documentos\Ciudades ni nada tuyo.
#   3. Deja un iniciar_puente.cmd que se reinicia solo si se corta (red, After colgado).
#   4. Lo pone en el Inicio de Windows: cada vez que prendés la PC, el puente arranca solo,
#      minimizado. Así la sesión de Claude en la nube siempre encuentra a After del otro lado.
#   5. Lo arranca ahora.
# Para desinstalar: borrar "Puente AE FNS2026" de shell:startup y la carpeta Ciudades_puente.

$ErrorActionPreference = "Stop"
$rama = "claude/fiesta-sol-2026-immersive-ph9915"
$repo = "https://github.com/facundo-20/Ciudades.git"
$dir  = Join-Path ([Environment]::GetFolderPath("MyDocuments")) "Ciudades_puente"

function Tiene($cmd) { return [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refrescar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}

Write-Host "== Puente de After Effects · FNS 2026 ==" -ForegroundColor Yellow

if (-not (Tiene git))  { Write-Host "Instalando Git…";  winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements | Out-Null; Refrescar-Path }
if (-not (Tiene node)) { Write-Host "Instalando Node…"; winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements | Out-Null; Refrescar-Path }
if (-not (Tiene git) -or -not (Tiene node)) { throw "Faltan Git o Node: cerrá y abrí PowerShell y volvé a pegar la línea." }

if (Test-Path (Join-Path $dir ".git")) {
    Write-Host "Actualizando $dir…"
    git -C $dir fetch origin $rama
    git -C $dir checkout $rama
    git -C $dir pull --ff-only origin $rama
} else {
    Write-Host "Clonando en $dir…"
    git clone -b $rama $repo $dir
}
# identidad sólo para los commits del puente en esta carpeta (no toca la configuración global)
git -C $dir config user.name  "Puente AE (PC de Facu)"
git -C $dir config user.email "puente-ae@fns2026.local"

# el lanzador se reinicia solo si node termina (corte de red, After colgado, etc.)
$cmd = Join-Path $dir "iniciar_puente.cmd"
@"
@echo off
title Puente AE FNS 2026
cd /d "$dir"
:otra_vez
git pull --no-rebase --no-edit origin $rama
node fns2026\ae_puente\puente_ae.mjs
echo El puente se corto. Reintento en 15 segundos... (cerrar esta ventana para apagarlo)
timeout /t 15 /nobreak >nul
goto otra_vez
"@ | Set-Content -Encoding ASCII $cmd

# acceso directo en el Inicio de Windows, minimizado
$inicio = [Environment]::GetFolderPath("Startup")
$lnk = Join-Path $inicio "Puente AE FNS2026.lnk"
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath = $cmd
$sc.WorkingDirectory = $dir
$sc.WindowStyle = 7
$sc.Save()
Write-Host "Queda en el Inicio de Windows: arranca solo al prender la PC." -ForegroundColor Green

# la primera vez git puede pedir iniciar sesión en GitHub (para subir resultados): se hace ahora
Write-Host "Probando que se pueda subir a GitHub (si abre el navegador, iniciá sesión)…"
git -C $dir push origin $rama

Start-Process -FilePath $cmd -WindowStyle Minimized
Write-Host "Listo: el puente está corriendo (ventana minimizada 'Puente AE FNS 2026')." -ForegroundColor Green
Write-Host "Dejá After Effects abierto. Claude le va a mandar los trabajos desde la nube."
