"""
Texturas PBR escaneadas, CC0 (dominio público), de Poly Haven, para el suelo hiperrealista.
CC0 cumple la regla del proyecto: nada de fotos bajadas de la web con derechos; CC0 se puede
usar comercialmente sin atribución (igual dejamos anotado de dónde sale cada una).

    python3 bajar_texturas_cc0.py            # baja a texturas_cc0/<rol>/ en 2K
    python3 bajar_texturas_cc0.py --res 4k

Roles que usa triasico_cycles.py (si la carpeta existe, reemplaza al material procedural):
    barro      suelo de barro de llanura de inundación
    hojarasca  suelo de bosque con hojas
    arena      barras de arena del río
    arcilla    arcilla seca cuarteada (el Valle de la Luna de hoy)
    roca       roca / arenisca

NO PROBADO CONTRA LA API REAL: desde la sesión donde se escribió, api.polyhaven.com estaba
bloqueado. Si la API cambió los nombres de los mapas, el script lo dice y sigue con los demás.
"""

import argparse
import json
import os
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
API = "https://api.polyhaven.com"
ROLES = {
    "barro": ["brown_mud", "mud_forest", "muddy", "mud"],
    "hojarasca": ["forest_leaves", "forest_ground", "leaves_forest", "forest_floor"],
    "arena": ["coast_sand", "sand"],
    "arcilla": ["cracked_ground", "dry_ground", "cracked", "mud_cracked"],
    "roca": ["sandstone", "rock_face", "rock"],
}
MAPAS = {  # nombre en Poly Haven → nombre nuestro
    "Diffuse": "color", "diff": "color",
    "Rough": "rugosidad", "rough": "rugosidad",
    "nor_gl": "normal", "Normal": "normal",
    "Displacement": "desplaz", "disp": "desplaz",
}


def leer(url):
    req = urllib.request.Request(url, headers={"User-Agent": "fns2026-triasico/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def elegir(assets, claves):
    """El asset más descargado cuyo id contiene alguna de las claves (en orden de preferencia)."""
    for clave in claves:
        candidatos = [(i, a) for i, a in assets.items() if clave in i]
        if candidatos:
            candidatos.sort(key=lambda x: -x[1].get("download_count", 0))
            return candidatos[0][0]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", default="2k")
    ap.add_argument("--salida", default=os.path.join(AQUI, "texturas_cc0"))
    a = ap.parse_args()
    assets = json.loads(leer(f"{API}/assets?t=textures"))
    print(f"Poly Haven: {len(assets)} texturas")
    for rol, claves in ROLES.items():
        ident = elegir(assets, claves)
        if not ident:
            print(f"  {rol}: no encontré ninguna con {claves}")
            continue
        archivos = json.loads(leer(f"{API}/files/{ident}"))
        carpeta = os.path.join(a.salida, rol)
        os.makedirs(carpeta, exist_ok=True)
        bajados = []
        for suyo, nuestro in MAPAS.items():
            if suyo not in archivos or nuestro in bajados:
                continue
            res = archivos[suyo].get(a.res) or next(iter(archivos[suyo].values()))
            fmt = res.get("jpg") or res.get("png")
            if not fmt:
                continue
            ext = ".jpg" if "jpg" in res else ".png"
            # primero se baja y después se escribe: si la red corta, no queda un .jpg vacío
            # que después Cycles intenta cargar (pasó el 28/09 con dl.polyhaven.org bloqueado)
            datos = leer(fmt["url"])
            with open(os.path.join(carpeta, nuestro + ext), "wb") as f:
                f.write(datos)
            bajados.append(nuestro)
        with open(os.path.join(carpeta, "LICENCIA.txt"), "w", encoding="utf-8") as f:
            f.write(f"CC0 · Poly Haven · https://polyhaven.com/a/{ident}\n")
        print(f"  {rol}: {ident} → {', '.join(bajados) or 'NINGÚN mapa (¿cambió la API?)'}")


if __name__ == "__main__":
    main()
