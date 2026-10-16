@echo off
rem Hornea los capitulos del Triasico en Gaussian splats (OMEN con RTX). Doble clic.
rem   Cycles renderiza las vistas en la placa, Brush entrena los splats, y quedan en Unity
rem   (Datos\splats) y en la web (public\splats). La primera vez tarda horas: dejarlo de noche.
rem   Se puede cortar y volver a correr: lo hecho se saltea.
setlocal
cd /d "%~dp0"
set "BLENDER="
for /d %%D in ("C:\Program Files\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
if not defined BLENDER (
  echo Instalando Blender con winget...
  winget install --id BlenderFoundation.Blender -e --silent --accept-source-agreements --accept-package-agreements
  for /d %%D in ("C:\Program Files\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
if not defined BLENDER ( echo No encuentro Blender. Instalalo desde blender.org y volve a correr esto. & pause & exit /b 1 )
echo Blender: %BLENDER%
"%BLENDER%" -b --factory-startup -P entrenar_splats.py -- %*
if errorlevel 1 ( echo. & echo Algo fallo: el detalle esta arriba. & pause & exit /b 1 )
rem a la rama: los .sog de la web, la lista y los .json de Unity (los .ply pesan demasiado para git)
cd /d "%~dp0\..\..\.."
git config http.postBuffer 1048576000
git config http.version HTTP/1.1
git add fns2026/experiencia/public/splats fns2026/unity/ParqueTriasico/Datos/splats/*.json 2>nul
git commit -m "Splats horneados de la PC" && git pull --no-rebase --no-edit origin claude/fiesta-sol-2026-immersive-ph9915 && git push origin claude/fiesta-sol-2026-immersive-ph9915
echo.
echo Listo. Ahora CONSTRUIR_Y_PROBAR.bat (fns2026\unity) arma Unity con los splats.
pause
