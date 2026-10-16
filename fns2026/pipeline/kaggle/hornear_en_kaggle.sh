#!/bin/bash
# Hornea capítulos en Gaussian splats con la GPU gratis de Kaggle, de punta a punta, sin la PC.
#
#   ./hornear_en_kaggle.sh [capitulos...]          (por defecto: bosque)
#   CALIDAD=media PASOS=15000 ./hornear_en_kaggle.sh rio llanura
#
# Necesita la CLI de Kaggle (pip install kaggle) y la credencial en el entorno: KAGGLE_USERNAME y
# KAGGLE_KEY (en Claude Code en la nube: los "secretos" del entorno; nunca en el repo ni en el chat),
# y salida a www.kaggle.com. Sube el kernel (privado), espera a que termine, baja los .ply a Unity
# (Datos/splats) y arma los .sog de la web.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
FNS="$(cd "$AQUI/../.." && pwd)"
CAPS=("${@:-bosque}")
CALIDAD="${CALIDAD:-final}"
PASOS="${PASOS:-30000}"
: "${KAGGLE_USERNAME:?falta KAGGLE_USERNAME (secreto del entorno)}"
: "${KAGGLE_KEY:?falta KAGGLE_KEY (secreto del entorno)}"
SLUG="fns2026-hornear-splats"
ID="$KAGGLE_USERNAME/$SLUG"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# el kernel con la configuración de esta corrida
python3 - "$AQUI/hornear_splats.py" "$TMP/hornear_splats.py" "$CALIDAD" "$PASOS" "${CAPS[@]}" <<'EOF'
import json, re, sys
src, dst, calidad, pasos, *caps = sys.argv[1:]
s = open(src, encoding="utf-8").read()
config = {"capitulos": caps, "calidad": calidad, "pasos": int(pasos),
          "rama": "claude/fiesta-sol-2026-immersive-ph9915", "repo": "https://github.com/facundo-20/Ciudades"}
s = re.sub(r"^CONFIG = \{.*?\}\n", "CONFIG = " + json.dumps(config) + "\n", s, count=1, flags=re.S | re.M)
open(dst, "w", encoding="utf-8").write(s)
EOF
cat > "$TMP/kernel-metadata.json" <<EOF
{
  "id": "$ID",
  "title": "FNS2026 hornear splats",
  "code_file": "hornear_splats.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": true,
  "enable_gpu": true,
  "enable_internet": true,
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": []
}
EOF
echo "== subiendo el kernel $ID (${CAPS[*]}, calidad $CALIDAD, $PASOS pasos)"
kaggle kernels push -p "$TMP"

echo "== esperando a que Kaggle termine (puede tardar horas)"
while true; do
  sleep 300
  estado="$(kaggle kernels status "$ID" 2>&1 | tail -1)"
  echo "   $(date -u +%H:%M) $estado"
  case "$estado" in
    *complete*|*COMPLETE*) break ;;
    *error*|*ERROR*|*cancel*|*CANCEL*) kaggle kernels output "$ID" -p "$TMP/salida" >/dev/null 2>&1 || true
                                       tail -40 "$TMP/salida/"*.log 2>/dev/null; exit 1 ;;
  esac
done

echo "== bajando los splats"
kaggle kernels output "$ID" -p "$TMP/salida"
mkdir -p "$FNS/unity/ParqueTriasico/Datos/splats" "$FNS/experiencia/public/splats"
for cap in "${CAPS[@]}"; do
  ply="$(find "$TMP/salida" -name "$cap.ply" | head -1)"
  js="$(find "$TMP/salida" -name "$cap.json" | head -1)"
  [ -n "$ply" ] || { echo "   $cap: no vino el .ply"; continue; }
  cp "$ply" "$js" "$FNS/unity/ParqueTriasico/Datos/splats/"
  # la web: girado a los ejes de three.js
  npx -y @playcanvas/splat-transform@3.10.1 "$ply" -r -90,0,0 "$FNS/experiencia/public/splats/$cap.sog"
  python3 - "$js" "$FNS/experiencia/public/splats/lista.json" "$cap" <<'EOF'
import json, os, sys
region, ruta, cap = json.load(open(sys.argv[1])), sys.argv[2], sys.argv[3]
lista = json.load(open(ruta)) if os.path.exists(ruta) else []
lista = [s for s in lista if s.get("capitulo") != cap]
d, h = region["desde_blender"], region["hasta_blender"]
lista.append({"capitulo": cap, "archivo": f"{cap}.sog", "desde": [d[0], -d[1]], "hasta": [h[0], -h[1]], "radio": region["radio_m"]})
json.dump(lista, open(ruta, "w"), indent=1)
EOF
  echo "   $cap: Unity y web listos"
done
find "$TMP/salida" -name "informe_kaggle.json" -exec cat {} \;
