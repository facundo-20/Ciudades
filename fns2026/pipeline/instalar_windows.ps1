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
function ClaveValida($k) { return ($k -and $k -match '^msy_[A-Za-z0-9_-]{16,}$') }
$clave = [Environment]::GetEnvironmentVariable("MESHY_API_KEY", "User")
if (-not (ClaveValida $clave)) {
    if ($clave) { Write-Host "   la clave guardada no es válida (se había pegado mal): la reemplazo" -ForegroundColor Red }
    # Se toma del PORTAPAPELES: en el prompt oculto de PowerShell, Ctrl+V no pega el texto,
    # mete un carácter de control (por eso aparecía un solo asterisco y Meshy daba 400).
    Write-Host "   1) En meshy.ai → tu perfil → API, copiá la clave (empieza con msy_)."
    Write-Host "   2) Volvé acá y apretá Enter. No hace falta pegar nada."
    for ($i = 0; $i -lt 3 -and -not (ClaveValida $clave); $i++) {
        Read-Host "   Enter cuando la tengas copiada" | Out-Null
        $clave = -join (("$(Get-Clipboard -Raw)").ToCharArray() | Where-Object { $_ -match '[A-Za-z0-9_-]' })
        if (-not (ClaveValida $clave)) { Write-Host "   lo copiado no parece una clave de Meshy (msy_...). Probá de nuevo." -ForegroundColor Red }
    }
    if (-not (ClaveValida $clave)) { throw "No se pudo leer una clave válida del portapapeles." }
    [Environment]::SetEnvironmentVariable("MESHY_API_KEY", $clave, "User")
    Set-Clipboard -Value " "      # que la clave no quede dando vueltas en el portapapeles
    Write-Host "   guardada ($($clave.Length) caracteres, empieza con $($clave.Substring(0,4)))"
} else {
    Write-Host "   ya está guardada ($($clave.Length) caracteres)"
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
