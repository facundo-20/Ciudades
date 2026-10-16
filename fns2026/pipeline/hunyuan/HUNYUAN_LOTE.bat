@echo off
rem Genera un modelo 3D por cada foto de una carpeta con Hunyuan3D-2 (servidor local: HUNYUAN_SERVIDOR.bat).
rem   HUNYUAN_LOTE.bat CARPETA [--textura] [--caras 60000]
rem Las fotos no salen de esta PC. Ej.: fotos del Hongo y del Submarino -> fns2026\modelos\el_hongo\...
setlocal
set "BLENDER="
for /d %%D in ("C:\Program Files\Blender Foundation\Blender*") do if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
if defined BLENDER (
  "%BLENDER%" -b --factory-startup --python "%~dp0hunyuan_lote.py" -- %*
) else (
  python "%~dp0hunyuan_lote.py" %*
)
pause
