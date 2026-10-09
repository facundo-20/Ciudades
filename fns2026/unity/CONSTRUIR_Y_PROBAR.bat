@echo off
rem Parque Triasico en Unity: instala Unity, arma el proyecto, compila y prueba. Doble clic.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0unity_windows.ps1" %*
pause
