@echo off
rem Hunyuan3D-2 (Tencent) en la OMEN, con su plugin oficial para Blender. Doble clic, una vez.
rem   1. Baja el paquete portable para Windows (YanWenKun/Hunyuan3D-2-WinPortable, GPL-3.0: Python,
rem      PyTorch con CUDA y el codigo oficial de Hunyuan3D-2) a %USERPROFILE%\Hunyuan3D2_WinPortable
rem   2. Deja HUNYUAN_SERVIDOR.bat: el servidor oficial (api_server.py) en http://localhost:8080
rem   3. Instala y habilita el plugin oficial en tu Blender (panel lateral "Hunyuan3D-2")
rem Los modelos (~10 GB) los baja de Hugging Face la primera vez que arranca el servidor.
rem Licencia de los modelos: Tencent Hunyuan 3D 2.0 Community License (vale en Argentina; no en la
rem UE, el Reino Unido ni Corea del Sur). Ver LEEME.md.
setlocal
set "DESTINO=%USERPROFILE%\Hunyuan3D2_WinPortable"
set "VERSION=v4-cu126"
set "SUFIJO=cu126"
where nvidia-smi >nul 2>&1 || ( echo Hace falta una placa NVIDIA con el driver al dia. & pause & exit /b 1 )
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
rem las RTX 50 (Blackwell) necesitan el paquete de CUDA 12.9
nvidia-smi --query-gpu=name --format=csv,noheader | findstr /c:"RTX 50" >nul && ( set "VERSION=v4-cu129" & set "SUFIJO=cu129" )
if exist "%DESTINO%\python_standalone\python.exe" goto :plugin
where 7z >nul 2>&1 || if not exist "C:\Program Files\7-Zip\7z.exe" winget install --id 7zip.7zip -e --silent --accept-source-agreements --accept-package-agreements
set "SIETEZ=7z"
if exist "C:\Program Files\7-Zip\7z.exe" set "SIETEZ=C:\Program Files\7-Zip\7z.exe"
mkdir "%DESTINO%_bajada" 2>nul
cd /d "%DESTINO%_bajada"
for %%P in (001 002) do (
  if not exist "Hunyuan3D2_WinPortable_%SUFIJO%.7z.%%P" (
    echo Bajando parte %%P...
    curl -L -o "Hunyuan3D2_WinPortable_%SUFIJO%.7z.%%P" "https://github.com/YanWenKun/Hunyuan3D-2-WinPortable/releases/download/%VERSION%/Hunyuan3D2_WinPortable_%SUFIJO%.7z.%%P" || ( echo No pude bajarlo. & pause & exit /b 1 )
  )
)
"%SIETEZ%" x -y "Hunyuan3D2_WinPortable_%SUFIJO%.7z.001" -o"%USERPROFILE%" || ( echo No pude descomprimirlo. & pause & exit /b 1 )
for /d %%D in ("%USERPROFILE%\Hunyuan3D2_WinPortable*") do if exist "%%D\python_standalone\python.exe" if /i not "%%D"=="%DESTINO%" move "%%D" "%DESTINO%" >nul
:plugin
cd /d "%~dp0"
rem el servidor oficial con el codigo sin modificar (Hunyuan3D-2-vanilla), en el puerto que espera el plugin
(
  echo @echo off
  echo rem Servidor de Hunyuan3D-2 para el plugin de Blender y hunyuan_lote.py. Dejarlo abierto mientras se usa.
  echo set "HF_HUB_CACHE=%DESTINO%\HuggingFaceHub"
  echo set "HY3DGEN_MODELS=%DESTINO%\HuggingFaceHub"
  echo set "PATH=%%PATH%%;%DESTINO%\MinGit\cmd;%DESTINO%\python_standalone\Scripts"
  echo cd /d "%DESTINO%\Hunyuan3D-2-vanilla"
  echo "%DESTINO%\python_standalone\python.exe" -s api_server.py --host 127.0.0.1 --port 8080 %%*
  echo pause
) > "%~dp0HUNYUAN_SERVIDOR.bat"
rem el plugin oficial, instalado en el Blender de esta PC (sin tocar el resto de sus preferencias)
set "BLENDER="
for /d %%D in ("C:\Program Files\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
if defined BLENDER (
  copy /y "%DESTINO%\Hunyuan3D-2-vanilla\blender_addon.py" "%~dp0hunyuan3d_blender.py" >nul
  "%BLENDER%" -b --python "%~dp0instalar_plugin.py" -- "%~dp0hunyuan3d_blender.py"
) else ( echo No encontre Blender: el plugin se instala a mano desde %DESTINO%\Hunyuan3D-2-vanilla\blender_addon.py )
echo.
echo Listo. Para usarlo: HUNYUAN_SERVIDOR.bat (dejarlo abierto) y en Blender, panel lateral (N) "Hunyuan3D-2".
echo Por lotes: HUNYUAN_LOTE.bat CARPETA_DE_FOTOS
pause
