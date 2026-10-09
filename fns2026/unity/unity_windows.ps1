# Parque Triásico en Unity · instala, arma, compila y prueba, de un doble clic (CONSTRUIR_Y_PROBAR.bat).
#
#   1. Unity Hub y el editor 6000.3 LTS (si faltan; ~10 GB la primera vez)
#   2. Licencia: la Personal es gratis, pero Unity pide iniciar sesión UNA vez en Unity Hub
#   3. Texturas escaneadas CC0 de Poly Haven a 4K (si hay Python; si no, quedan las procedurales)
#   4. Unity arma todo solo (FNS.Editor.Constructor) y compila Builds\Windows\ParqueTriasico.exe
#   5. Corre el ejecutable en modo capturas y sube las imágenes a la rama, para revisarlas desde la nube
#
# Se puede correr las veces que haga falta: lo que ya está, lo saltea. La primera vez tarda (Unity
# compila todos los shaders de HDRP): 30 a 60 minutos. Después, 5 a 10.
param([switch]$SinCompilar, [switch]$SinCapturas, [switch]$SinSubir)

$ErrorActionPreference = "Stop"
$aqui = $PSScriptRoot
$proyecto = Join-Path $aqui "ParqueTriasico"
$builds = Join-Path $aqui "Builds"
$raizRepo = (Resolve-Path (Join-Path $aqui "..\..")).Path
$RAMA = "claude/fiesta-sol-2026-immersive-ph9915"
function Paso($t) { Write-Host "`n== $t" -ForegroundColor Yellow }
function RefrescarPath { $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User") }

# los dinosaurios de Meshy de esta PC (Descargas\dinos_triasico y los Herrerasaurus de Meshy): se suben
# a la rama para armarles el esqueleto en la nube (pipeline/rig_fauna.py --carpeta modelos_mac/pc)
$dinosPc = Join-Path $raizRepo "fns2026\modelos_mac\pc"
$descargas = Join-Path $env:USERPROFILE "Downloads"
$dinos = @()
if (Test-Path (Join-Path $descargas "dinos_triasico")) { $dinos += @(Get-ChildItem (Join-Path $descargas "dinos_triasico") -Filter *.glb) }
# @(): si no hay ninguno queda vacío (sin @ se colaba un $null y la copia fallaba)
$dinos += @(Get-ChildItem $descargas -Filter "Meshy_AI_herrerasaurus_*_image-to-3d-texture.glb" -ErrorAction SilentlyContinue)
$dinosNuevos = 0
foreach ($d in $dinos) {
    New-Item -ItemType Directory -Force -Path $dinosPc | Out-Null
    $copia = Join-Path $dinosPc $d.Name
    if (-not (Test-Path $copia) -or (Get-Item $copia).Length -ne $d.Length) { Copy-Item $d.FullName $copia -Force; $dinosNuevos++ }
}
if ($dinos.Count) { Write-Host "Dinosaurios de Meshy de esta PC: $($dinos.Count) ($dinosNuevos nuevos)" }

Paso "1/5 Unity Hub y editor"
$hub = "C:\Program Files\Unity Hub\Unity Hub.exe"
if (-not (Test-Path $hub)) {
    Write-Host "   instalando Unity Hub…"
    winget install --id Unity.UnityHub -e --silent --accept-source-agreements --accept-package-agreements | Out-Host
}
$version = ((Get-Content (Join-Path $proyecto "ProjectSettings\ProjectVersion.txt")) -match "m_EditorVersion:")[0].Split(":")[1].Trim()
$editores = "C:\Program Files\Unity\Hub\Editor"
# si ya hay un 6000.3 instalado, se usa ése (mismo HDRP 17.3): no hace falta bajar otro
$instalado = $null
if (Test-Path $editores) {
    $instalado = Get-ChildItem $editores -Directory | Where-Object { $_.Name -like "6000.3.*" } | Sort-Object Name -Descending | Select-Object -First 1
}
if ($instalado) {
    $version = $instalado.Name
} else {
    Write-Host "   instalando Unity $version (unos 10 GB)…"
    $cambio = $null
    try {
        $r = Invoke-RestMethod "https://services.api.unity.com/unity/editor/release/v1/releases?version=$version&limit=1"
        $cambio = $r.results[0].shortRevision
    } catch { Write-Host "   no pude leer el número de cambio de $version (sigo sin él)" }
    $argsHub = @("--", "--headless", "install", "--version", $version)
    if ($cambio) { $argsHub += @("--changeset", $cambio) }
    & $hub @argsHub | Out-Host
}
$unity = Join-Path $editores "$version\Editor\Unity.exe"
if (-not (Test-Path $unity)) { throw "No encuentro $unity. Abrí Unity Hub → Installs y agregá Unity $version." }
Set-Content -Path (Join-Path $proyecto "ProjectSettings\ProjectVersion.txt") -Value "m_EditorVersion: $version" -Encoding ASCII
Write-Host "   Unity $version"

Paso "2/5 Texturas escaneadas CC0 (opcional)"
$python = $null
if (Get-Command py -ErrorAction SilentlyContinue) { $python = "py" } elseif (Get-Command python -ErrorAction SilentlyContinue) { $python = "python" }
$cc0 = Join-Path $raizRepo "fns2026\escenas\hiperreal\texturas_cc0"
if ($python -and -not (Test-Path $cc0)) {
    & $python (Join-Path $raizRepo "fns2026\escenas\hiperreal\bajar_texturas_cc0.py") --res 4k | Out-Host
} elseif (Test-Path $cc0) { Write-Host "   ya están" } else { Write-Host "   sin Python: quedan las texturas procedurales" }

function CorrerUnity($metodo, $log, $extra) {
    $a = @("-batchmode", "-quit", "-projectPath", $proyecto, "-buildTarget", "Win64", "-executeMethod", $metodo, "-logFile", $log) + $extra
    $p = Start-Process -FilePath $unity -ArgumentList $a -PassThru -Wait -NoNewWindow
    return $p.ExitCode
}

Paso "3/5 Unity arma el Parque Triásico (la primera vez tarda: compila los shaders de HDRP)"
New-Item -ItemType Directory -Force -Path $builds | Out-Null
$log = Join-Path $builds "unity_construir.log"
$extra = @()
if (-not $SinCompilar) { $extra += "-fnsCompilar" }
$codigo = CorrerUnity "FNS.Editor.Constructor.DesdeConsola" $log $extra
if ($codigo -ne 0 -and (Select-String -Path $log -Pattern "No valid Unity Editor license|License activation|licen" -Quiet)) {
    Write-Host "`nUnity necesita la licencia (la Personal es gratis):" -ForegroundColor Cyan
    Write-Host "  1) Se abre Unity Hub: iniciá sesión con tu cuenta de Unity (o creala)."
    Write-Host "  2) Preferencias (engranaje) → Licencias → Agregar → 'Obtener una licencia Personal gratuita'."
    Start-Process $hub
    Read-Host "  Cuando esté, apretá Enter acá"
    $codigo = CorrerUnity "FNS.Editor.Constructor.DesdeConsola" $log $extra
}
$informe = Join-Path $builds "informe_constructor.txt"
if (Test-Path $informe) { Get-Content $informe | Out-Host }
if ($codigo -ne 0) {
    Write-Host "`nUnity terminó con error ($codigo). El detalle está en $log" -ForegroundColor Red
    Select-String -Path $log -Pattern "error CS|Exception|ERROR" | Select-Object -First 25 | ForEach-Object { Write-Host "   $($_.Line)" }
}

# lanzadores: pared LED 5760×1080 y sala completa (piso + paredes)
$exe = Join-Path $builds "Windows\ParqueTriasico.exe"
if (Test-Path $exe) {
    Set-Content -Path (Join-Path $builds "PARQUE_PARED_LED.bat") -Encoding ASCII -Value "@echo off`r`ncd /d `"%~dp0Windows`"`r`nstart `"`" ParqueTriasico.exe --sala pared --calidad maxima -screen-width 5760 -screen-height 1080 -popupwindow %*`r`n"
    Set-Content -Path (Join-Path $builds "PARQUE_SALA_CUBO.bat") -Encoding ASCII -Value "@echo off`r`ncd /d `"%~dp0Windows`"`r`nstart `"`" ParqueTriasico.exe --sala cubo --calidad maxima -screen-width 3461 -screen-height 2051 -popupwindow %*`r`n"
    Set-Content -Path (Join-Path $builds "PARQUE_PRUEBA_VENTANA.bat") -Encoding ASCII -Value "@echo off`r`ncd /d `"%~dp0Windows`"`r`nstart `"`" ParqueTriasico.exe --sala pared --simular -screen-width 1920 -screen-height 360 -screen-fullscreen 0 %*`r`n"
}

Paso "4/5 Capturas de los 6 capítulos"
$capturas = Join-Path $builds "capturas"
if (-not $SinCapturas -and (Test-Path $exe)) {
    Remove-Item -Recurse -Force $capturas -ErrorAction SilentlyContinue
    $p = Start-Process -FilePath $exe -ArgumentList @("--capturas", $capturas, "--calidad", "maxima", "--sala", "pared", "-screen-width", "2880", "-screen-height", "540", "-screen-fullscreen", "0") -PassThru
    if (-not $p.WaitForExit(15 * 60 * 1000)) { $p.Kill(); Write-Host "   el ejecutable no terminó en 15 min" -ForegroundColor Red }
    Get-ChildItem $capturas -ErrorAction SilentlyContinue | Out-Host
}

Paso "5/5 Subir el informe y las capturas a la rama (para revisarlos desde la nube)"
if (-not $SinSubir -and (Get-Command git -ErrorAction SilentlyContinue)) {
    $destino = Join-Path $aqui ("pruebas_pc\" + (Get-Date -Format "yyyyMMdd_HHmm"))
    New-Item -ItemType Directory -Force -Path $destino | Out-Null
    foreach ($f in @($informe, (Join-Path $capturas "informe.json"))) { if (Test-Path $f) { Copy-Item $f $destino } }
    # el log entero pesa mucho: van los errores y las últimas 300 líneas
    if (Test-Path $log) {
        (Select-String -Path $log -Pattern "error CS|Exception|ERROR|\[FNS" | ForEach-Object { $_.Line }) | Set-Content (Join-Path $destino "errores_unity.txt")
        Get-Content $log -Tail 300 | Set-Content (Join-Path $destino "log_final.txt")
    }
    # capturas a JPG de 1920 px de ancho (las PNG del LED pesan mucho para git)
    Add-Type -AssemblyName System.Drawing
    Get-ChildItem $capturas -Filter *.png -ErrorAction SilentlyContinue | ForEach-Object {
        $img = [System.Drawing.Image]::FromFile($_.FullName)
        $w = [Math]::Min(1920, $img.Width); $h = [int]($img.Height * $w / $img.Width)
        $bmp = New-Object System.Drawing.Bitmap $w, $h
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.DrawImage($img, 0, 0, $w, $h)
        $bmp.Save((Join-Path $destino ($_.BaseName + ".jpg")), [System.Drawing.Imaging.ImageFormat]::Jpeg)
        $g.Dispose(); $bmp.Dispose(); $img.Dispose()
    }
    Push-Location $raizRepo
    try {
        git add (Join-Path $aqui "pruebas_pc") | Out-Null
        if (Test-Path $dinosPc) { git add $dinosPc | Out-Null }
        git commit -m "Unity: informe y capturas de la PC" | Out-Host
        git pull --no-rebase --no-edit origin $RAMA | Out-Host
        git push origin $RAMA | Out-Host
    } catch { Write-Host "   no pude subir (sigue en $destino): $($_.Exception.Message)" }
    Pop-Location
}
Write-Host "`nListo. Ejecutables y lanzadores en $builds" -ForegroundColor Green
