@echo off
rem Puente de After Effects: deja que la sesión de Claude en la nube maneje este After.
rem Doble clic con After Effects instalado. Ctrl+C para cortar.
cd /d "%~dp0\..\.."
git checkout claude/fiesta-sol-2026-immersive-ph9915
git pull
node fns2026\ae_puente\puente_ae.mjs
pause
