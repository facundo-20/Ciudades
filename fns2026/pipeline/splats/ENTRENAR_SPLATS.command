#!/bin/bash
# Hornea los capítulos del Triásico en Gaussian splats (Mac M4: Cycles con Metal, Brush con Metal).
# Doble clic. La primera vez tarda horas. Se puede cortar y volver a correr: lo hecho se saltea.
set -e
AQUI="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$(cd "$AQUI/../../.." && pwd)"
BLENDER="$(ls -d /Applications/Blender*.app 2>/dev/null | sort -V | tail -1)/Contents/MacOS/Blender"
if [ ! -x "$BLENDER" ]; then
  if command -v brew >/dev/null; then brew install --cask blender; fi
  BLENDER="$(ls -d /Applications/Blender*.app 2>/dev/null | sort -V | tail -1)/Contents/MacOS/Blender"
fi
[ -x "$BLENDER" ] || { echo "No encuentro Blender: instalalo desde blender.org"; read -r; exit 1; }
echo "Blender: $BLENDER"
cd "$AQUI"
"$BLENDER" -b --factory-startup -P entrenar_splats.py -- "$@"
cd "$RAIZ"
git config http.postBuffer 1048576000
git config http.version HTTP/1.1
git add fns2026/experiencia/public/splats fns2026/unity/ParqueTriasico/Datos/splats/*.json 2>/dev/null || true
git commit -m "Splats horneados de la Mac" && git pull --no-rebase --no-edit origin claude/fiesta-sol-2026-immersive-ph9915 \
  && git push origin claude/fiesta-sol-2026-immersive-ph9915 || true
echo "Listo. Ahora CONSTRUIR_Y_PROBAR_MAC.command (fns2026/unity) arma Unity con los splats."
