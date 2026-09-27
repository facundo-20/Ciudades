@echo off
rem FNS 2026: doble clic. Instala Python, Git y Blender si faltan, pide la clave de Meshy
rem una sola vez y corre la cañería completa. Para todos los modelos: INSTALAR_Y_CORRER.bat --destino todos
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0instalar_windows.ps1" %*
pause
