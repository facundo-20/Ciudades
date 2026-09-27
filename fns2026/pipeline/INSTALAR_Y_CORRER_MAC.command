#!/bin/bash
# FNS 2026 en la Mac M4: doble clic. Instala Python, Git y Blender con Homebrew si faltan,
# pide la clave de Meshy una vez (la guarda en el Llavero) y corre la cañería completa.
# Para todos los modelos: ./INSTALAR_Y_CORRER_MAC.command --destino todos
set -e
RAMA="claude/fiesta-sol-2026-immersive-ph9915"
REPO="https://github.com/facundo-20/Ciudades.git"
AQUI="$(cd "$(dirname "$0")" && pwd)"

echo "== 1/4 Programas"
if ! command -v brew >/dev/null; then
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  eval "$(/opt/homebrew/bin/brew shellenv)"
fi
command -v python3 >/dev/null || brew install python
command -v git >/dev/null || brew install git
[ -d /Applications/Blender.app ] || brew install --cask blender

echo "== 2/4 Proyecto"
if [ -f "$AQUI/correr_todo.py" ]; then
  PIPE="$AQUI"; RAIZ="$(cd "$AQUI/../.." && pwd)"
  [ -d "$RAIZ/.git" ] && git -C "$RAIZ" pull --ff-only origin "$RAMA" || true
else
  RAIZ="$HOME/Documents/Ciudades"
  if [ -d "$RAIZ/.git" ]; then git -C "$RAIZ" fetch origin "$RAMA" && git -C "$RAIZ" checkout "$RAMA" && git -C "$RAIZ" pull --ff-only origin "$RAMA"
  else git clone -b "$RAMA" "$REPO" "$RAIZ"; fi
  PIPE="$RAIZ/fns2026/pipeline"
fi

echo "== 3/4 Clave de Meshy"
# en el Llavero de macOS, no en un archivo: no queda en el repo ni en el historial
if ! MESHY_API_KEY="$(security find-generic-password -s meshy_api_key -w 2>/dev/null)"; then
  echo "   Sacala de meshy.ai → tu perfil → API."
  read -r -s -p "   Pegá la clave (no se ve mientras escribís): " MESHY_API_KEY; echo
  security add-generic-password -s meshy_api_key -a "$USER" -w "$MESHY_API_KEY"
fi
export MESHY_API_KEY

echo "== 4/4 Meshy → Blender → FBX"
cd "$PIPE"
python3 correr_todo.py "$@" && echo "Listo. Los FBX están en $RAIZ/fns2026/modelos" \
  || echo "Algunos fallaron: mirá $RAIZ/fns2026/correr_todo.log y volvé a correr (sigue desde donde quedó)."
