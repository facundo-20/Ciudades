"""
Hornea los capítulos del Triásico en Gaussian splats, de punta a punta, en la OMEN o en la M4:

    1. vistas: Blender + Cycles (GPU) renderiza cientos de vistas por capítulo (vistas_blender.py)
    2. entrenamiento: Brush (Apache-2.0, corre en NVIDIA, AMD, Intel y Apple con WebGPU)
    3. poda: sin suelo, sin flotantes, sólo alrededor del recorrido (podar_splat.py)
    4. Unity: Datos/splats/<capitulo>.ply + .json (el Constructor los convierte y los ubica)
    5. web: public/splats/<capitulo>.sog + lista.json (con splat-transform de PlayCanvas, MIT)

Corre con el Python de Blender (no hace falta instalar Python):

    blender -b --factory-startup -P entrenar_splats.py -- [--capitulos bosque rio] [--calidad final]
                                                          [--pasos 30000] [--sin-web] [--solo-vistas]

Lo llaman ENTRENAR_SPLATS.bat (Windows) y ENTRENAR_SPLATS.command (Mac). Se puede cortar y volver a
correr: lo que ya está hecho (vistas, entrenamiento) se saltea.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, AQUI)

BRUSH_VERSION = "v0.3.0"
BRUSH_ARCHIVOS = {
    ("Windows", "AMD64"): "brush-app-x86_64-pc-windows-msvc.zip",
    ("Darwin", "arm64"): "brush-app-aarch64-apple-darwin.tar.xz",
    ("Linux", "x86_64"): "brush-app-x86_64-unknown-linux-gnu.tar.xz",
}
TRABAJO = os.path.join(AQUI, "trabajo")            # vistas y salidas de Brush (no van a git)
HERRAMIENTAS = os.path.join(AQUI, "herramientas")
UNITY_SPLATS = os.path.join(FNS, "unity", "ParqueTriasico", "Datos", "splats")
WEB_SPLATS = os.path.join(FNS, "experiencia", "public", "splats")
CAPITULOS = ["titulo", "rio", "bosque", "llanura", "ceniza"]   # "hoy" no: ése sale de capturas reales


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--capitulos", nargs="*", default=CAPITULOS)
    ap.add_argument("--calidad", default="final", choices=["prueba", "media", "final"])
    ap.add_argument("--pasos", type=int, default=30000)
    ap.add_argument("--sin-web", action="store_true")
    ap.add_argument("--solo-vistas", action="store_true")
    ap.add_argument("--brush", help="ruta a brush_app (si no, se baja la versión probada)")
    return ap.parse_args(argv)


def paso(t):
    print(f"\n== {t}", flush=True)


def bajar(url, destino):
    print(f"   bajando {url}", flush=True)
    with urllib.request.urlopen(url, timeout=120) as r, open(destino, "wb") as f:
        shutil.copyfileobj(r, f)


def asegurar_brush():
    clave = (platform.system(), platform.machine())
    if clave not in BRUSH_ARCHIVOS:
        raise SystemExit(f"Brush no tiene versión para {clave}")
    archivo = BRUSH_ARCHIVOS[clave]
    carpeta = os.path.join(HERRAMIENTAS, f"brush-{BRUSH_VERSION}")
    exe_nombre = "brush_app.exe" if clave[0] == "Windows" else "brush_app"
    for raiz, _, fs in os.walk(carpeta):
        if exe_nombre in fs:
            return os.path.join(raiz, exe_nombre)
    os.makedirs(carpeta, exist_ok=True)
    base = f"https://github.com/ArthurBrussee/brush/releases/download/{BRUSH_VERSION}/{archivo}"
    destino = os.path.join(carpeta, archivo)
    bajar(base, destino)
    bajar(base + ".sha256", destino + ".sha256")
    esperado = open(destino + ".sha256").read().split()[0].lower()
    real = hashlib.sha256(open(destino, "rb").read()).hexdigest()
    if esperado != real:
        raise SystemExit(f"Brush: la suma de verificación no coincide ({real} ≠ {esperado}); no lo uso")
    if archivo.endswith(".zip"):
        zipfile.ZipFile(destino).extractall(carpeta)
    else:
        with tarfile.open(destino) as t:
            t.extractall(carpeta)
    for raiz, _, fs in os.walk(carpeta):
        if exe_nombre in fs:
            exe = os.path.join(raiz, exe_nombre)
            os.chmod(exe, 0o755)
            return exe
    raise SystemExit("Brush: no encontré el ejecutable en el paquete")


def blender_exe():
    try:
        import bpy
        if bpy.app.binary_path:
            return bpy.app.binary_path
    except ImportError:
        pass
    return shutil.which("blender") or "blender"


def correr(cmd, env=None):
    print("   $ " + " ".join(f'"{c}"' if " " in str(c) else str(c) for c in cmd), flush=True)
    r = subprocess.run([str(c) for c in cmd], env=env)
    if r.returncode != 0:
        raise SystemExit(f"falló (código {r.returncode})")


def main():
    a = argumentos()
    import podar_splat as P
    calidades = {"prueba": 320, "media": 1280, "final": 1600}
    os.makedirs(TRABAJO, exist_ok=True)
    brush = a.brush or (None if a.solo_vistas else asegurar_brush())
    blender = blender_exe()
    env = dict(os.environ, FNS_GPU="1")          # Cycles en la placa: OptiX (RTX) o Metal (M4)
    hechos = []
    for cap in a.capitulos:
        t0 = time.time()
        carpeta = os.path.join(TRABAJO, cap)
        paso(f"{cap}: vistas de Cycles ({a.calidad})")
        if os.path.exists(os.path.join(carpeta, "transforms.json")):
            print("   ya están")
        else:
            correr([blender, "-b", "--factory-startup", "-P", os.path.join(AQUI, "vistas_blender.py"), "--",
                    TRABAJO, "--capitulo", cap, "--calidad", a.calidad], env)
        if a.solo_vistas:
            continue

        paso(f"{cap}: entrenamiento con Brush ({a.pasos} pasos)")
        salida = os.path.join(TRABAJO, f"{cap}_brush")
        ply = os.path.join(salida, f"{cap}.ply")
        if os.path.exists(ply):
            print("   ya está")
        else:
            correr([brush, carpeta, "--total-steps", a.pasos, "--export-every", a.pasos, "--export-path", salida,
                    "--export-name", f"{cap}.ply", "--max-resolution", calidades[a.calidad],
                    "--eval-every", max(1000, a.pasos // 6), "--eval-save-to-disk"])

        paso(f"{cap}: poda y entrega")
        region = json.load(open(os.path.join(carpeta, "region.json"), encoding="utf-8"))
        cab, datos = P.leer_ply(ply)
        podado, motivos = P.podar(datos, region)
        os.makedirs(UNITY_SPLATS, exist_ok=True)
        destino_unity = os.path.join(UNITY_SPLATS, f"{cap}.ply")
        P.escribir_ply(destino_unity, cab, podado)
        with open(os.path.join(UNITY_SPLATS, f"{cap}.json"), "w", encoding="utf-8") as f:
            json.dump(dict(region, capitulo=cap), f, indent=1, ensure_ascii=False)
        print(f"   Unity: {len(datos):,} → {len(podado):,} splats ({', '.join(f'{v:,} {k}' for k, v in motivos.items() if v)})")

        web = None
        if not a.sin_web:
            npx = shutil.which("npx") or shutil.which("npx.cmd")
            if not npx:
                print("   web: no hay Node (npx); se saltea")
            else:
                os.makedirs(WEB_SPLATS, exist_ok=True)
                web = os.path.join(WEB_SPLATS, f"{cap}.sog")
                # three.js tiene y arriba: (x, y, z) de Blender → (x, z, -y), girando -90° en X
                correr([npx, "-y", "@playcanvas/splat-transform@3.10.1", destino_unity, "-r", "-90,0,0", web])
                lista_ruta = os.path.join(WEB_SPLATS, "lista.json")
                lista = json.load(open(lista_ruta)) if os.path.exists(lista_ruta) else []
                lista = [s for s in lista if s.get("capitulo") != cap]
                d, h = region["desde_blender"], region["hasta_blender"]
                lista.append({"capitulo": cap, "archivo": f"{cap}.sog", "desde": [d[0], -d[1]], "hasta": [h[0], -h[1]],
                              "radio": region["radio_m"]})
                json.dump(sorted(lista, key=lambda s: CAPITULOS.index(s["capitulo"]) if s["capitulo"] in CAPITULOS else 99),
                          open(lista_ruta, "w"), indent=1)
        hechos.append({"capitulo": cap, "splats": len(podado), "minutos": round((time.time() - t0) / 60, 1),
                       "unity_mb": round(os.path.getsize(destino_unity) / 1048576, 1),
                       "web_mb": round(os.path.getsize(web) / 1048576, 1) if web and os.path.exists(web) else None})
    paso("listo")
    for h in hechos:
        print(f"   {h['capitulo']}: {h['splats']:,} splats · Unity {h['unity_mb']} MB · web {h['web_mb']} MB · {h['minutos']} min")
    # el informe va con los datos de Unity: sube a la rama (trabajo/ no) para revisarlo desde la nube
    os.makedirs(UNITY_SPLATS, exist_ok=True)
    with open(os.path.join(UNITY_SPLATS, "informe_splats.json"), "w", encoding="utf-8") as f:
        json.dump(hechos, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
