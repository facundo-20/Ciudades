#!/bin/bash
# Parque Triásico en Unity (Mac M4): instala Unity Hub y el editor 6000.3 LTS, arma el proyecto,
# compila Builds/Mac/ParqueTriasico.app, saca capturas de los 6 capítulos y las sube a la rama.
# Doble clic. La primera vez tarda (Unity compila los shaders de HDRP): 30 a 60 minutos.
set -u
AQUI="$(cd "$(dirname "$0")" && pwd)"
PROYECTO="$AQUI/ParqueTriasico"
BUILDS="$AQUI/Builds"
RAIZ="$(cd "$AQUI/../.." && pwd)"
RAMA="claude/fiesta-sol-2026-immersive-ph9915"
HUB="/Applications/Unity Hub.app/Contents/MacOS/Unity Hub"
paso() { printf "\n\033[33m== %s\033[0m\n" "$1"; }
mkdir -p "$BUILDS"

# dinosaurios de Meshy bajados en esta Mac (Descargas/dinos_triasico): suben a la rama para armarles
# el esqueleto en la nube (pipeline/rig_fauna.py --carpeta modelos_mac/pc)
DINOS_PC="$RAIZ/fns2026/modelos_mac/pc"
for f in "$HOME/Downloads/dinos_triasico"/*.glb "$HOME/Downloads"/Meshy_AI_herrerasaurus_*_image-to-3d-texture.glb; do
  [ -f "$f" ] || continue
  mkdir -p "$DINOS_PC"
  cmp -s "$f" "$DINOS_PC/$(basename "$f")" || cp "$f" "$DINOS_PC/"
done

paso "1/5 Unity Hub y editor"
if [ ! -x "$HUB" ]; then
  echo "   bajando Unity Hub…"
  curl -L -o /tmp/UnityHub.dmg "https://public-cdn.cloud.unity3d.com/hub/prod/UnityHubSetup-arm64.dmg"
  hdiutil attach /tmp/UnityHub.dmg -nobrowse -quiet -mountpoint /tmp/unityhub_dmg
  cp -R "/tmp/unityhub_dmg/Unity Hub.app" /Applications/
  hdiutil detach /tmp/unityhub_dmg -quiet
fi
VERSION="$(grep m_EditorVersion: "$PROYECTO/ProjectSettings/ProjectVersion.txt" | head -1 | awk '{print $2}')"
EDITORES="/Applications/Unity/Hub/Editor"
INSTALADO="$(ls -d "$EDITORES"/6000.3.* 2>/dev/null | sort -V | tail -1)"
if [ -n "$INSTALADO" ]; then
  VERSION="$(basename "$INSTALADO")"
else
  echo "   instalando Unity $VERSION (unos 10 GB)…"
  CAMBIO="$(curl -s "https://services.api.unity.com/unity/editor/release/v1/releases?version=$VERSION&limit=1" | python3 -c 'import json,sys; print(json.load(sys.stdin)["results"][0]["shortRevision"])' 2>/dev/null)"
  if [ -n "$CAMBIO" ]; then "$HUB" -- --headless install --version "$VERSION" --changeset "$CAMBIO" --architecture arm64
  else "$HUB" -- --headless install --version "$VERSION" --architecture arm64; fi
fi
UNITY="$EDITORES/$VERSION/Unity.app/Contents/MacOS/Unity"
[ -x "$UNITY" ] || { echo "No encuentro $UNITY: abrí Unity Hub → Installs y agregá Unity $VERSION."; exit 1; }
echo "m_EditorVersion: $VERSION" > "$PROYECTO/ProjectSettings/ProjectVersion.txt"

paso "2/5 Texturas escaneadas CC0 (opcional)"
CC0="$RAIZ/fns2026/escenas/hiperreal/texturas_cc0"
if [ ! -d "$CC0" ] && command -v python3 >/dev/null; then python3 "$RAIZ/fns2026/escenas/hiperreal/bajar_texturas_cc0.py" --res 4k; else echo "   ya están o no hay Python"; fi

paso "3/5 Unity arma el Parque Triásico"
LOG="$BUILDS/unity_construir.log"
correr() { "$UNITY" -batchmode -quit -projectPath "$PROYECTO" -buildTarget OSXUniversal \
             -executeMethod FNS.Editor.Constructor.DesdeConsola -fnsCompilar -logFile "$LOG"; }
correr; CODIGO=$?
if [ $CODIGO -ne 0 ] && grep -qi "license" "$LOG"; then
  echo "Unity necesita la licencia (la Personal es gratis): iniciá sesión en Unity Hub →"
  echo "Preferencias → Licencias → Agregar → 'Obtener una licencia Personal gratuita'."
  open -a "Unity Hub"
  read -r -p "Cuando esté, apretá Enter acá " _
  correr; CODIGO=$?
fi
[ -f "$BUILDS/informe_constructor.txt" ] && cat "$BUILDS/informe_constructor.txt"
[ $CODIGO -ne 0 ] && { echo "Unity terminó con error ($CODIGO): ver $LOG"; grep -E "error CS|Exception|ERROR" "$LOG" | head -25; }

APP="$BUILDS/Mac/ParqueTriasico.app"
cat > "$BUILDS/PARQUE_PARED_LED.command" <<EOS
#!/bin/bash
open -n "$APP" --args --sala pared --calidad alta -screen-width 5760 -screen-height 1080 -popupwindow --syphon ParqueTriasico "\$@"
EOS
chmod +x "$BUILDS/PARQUE_PARED_LED.command"

paso "4/5 Capturas de los 6 capítulos"
CAPT="$BUILDS/capturas"
if [ -d "$APP" ]; then
  rm -rf "$CAPT"
  "$APP/Contents/MacOS/ParqueTriasico" --capturas "$CAPT" --calidad media --sala pared -screen-width 2880 -screen-height 540 -screen-fullscreen 0 &
  PID=$!; ( sleep 900; kill $PID 2>/dev/null ) & wait $PID
fi

paso "5/5 Subir el informe y las capturas a la rama"
DEST="$AQUI/pruebas_mac/$(date +%Y%m%d_%H%M)"
mkdir -p "$DEST"
cp "$BUILDS/informe_constructor.txt" "$CAPT/informe.json" "$DEST/" 2>/dev/null
grep -E "error CS|Exception|ERROR|\[FNS" "$LOG" > "$DEST/errores_unity.txt" 2>/dev/null
tail -300 "$LOG" > "$DEST/log_final.txt" 2>/dev/null
for f in "$CAPT"/*.png; do [ -f "$f" ] && sips -s format jpeg -Z 1920 "$f" --out "$DEST/$(basename "${f%.png}").jpg" >/dev/null; done
cd "$RAIZ" && git add "$AQUI/pruebas_mac" && { [ -d "$DINOS_PC" ] && git add "$DINOS_PC"; true; } && git commit -m "Unity: informe y capturas de la Mac" && \
  git pull --no-rebase --no-edit origin "$RAMA" && git push origin "$RAMA"
echo "Listo. App y lanzador en $BUILDS"
