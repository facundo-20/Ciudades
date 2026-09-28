"""
Toda la cañería de una vez: Meshy → Blender → FBX, para toda la lista o una parte.

    python correr_todo.py                     # los modelos de paisaje (lo que se pidió primero)
    python correr_todo.py --destino todos     # los 14 de lista_modelos.json
    python correr_todo.py --solo el_hongo
    python correr_todo.py --simular           # sin Meshy: modelos de prueba, para probar la cadena

Lo que hace solo:
  · encuentra Blender (variable BLENDER, rutas típicas de Windows y Mac, PATH, o el módulo bpy)
  · SALTEA lo que ya está hecho: si se corta la luz o Meshy falla en el 7 de 14, se vuelve a
    correr el mismo comando y sigue desde ahí sin gastar créditos de nuevo
  · deja un registro (correr_todo.log) y una galería (resultados.html) con las vistas previas
  · si un modelo falla, sigue con el resto y al final dice cuáles faltan
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import traceback
import webbrowser

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.dirname(AQUI)
LISTA = os.path.join(AQUI, "lista_modelos.json")
CRUDOS = os.path.join(FNS, "modelos_meshy")
MODELOS = os.path.join(FNS, "modelos")
REGISTRO = os.path.join(FNS, "correr_todo.log")


def log(*partes):
    linea = time.strftime("%H:%M:%S ") + " ".join(str(p) for p in partes)
    print(linea, flush=True)
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def buscar_blender():
    """Devuelve el comando para correr un script de Blender: [ejecutable, ...] o [python] si hay bpy."""
    candidatos = [os.environ.get("BLENDER", "")]
    candidatos += sorted(glob.glob(r"C:\Program Files\Blender Foundation\Blender*\blender.exe"), reverse=True)
    candidatos += ["/Applications/Blender.app/Contents/MacOS/Blender"]
    candidatos += [shutil.which("blender") or ""]
    for c in candidatos:
        if c and os.path.exists(c):
            return [c, "-b", "--factory-startup", "-P"]
    try:
        import bpy  # noqa: F401  (pip install bpy: así se probó en la nube)
        return [sys.executable]
    except ImportError:
        return None


def refinar(blender, entrada, salida, item):
    cmd = blender + [os.path.join(AQUI, "blender_refinar.py"), "--", entrada, salida,
                     "--largo", str(item["largo_m"]),
                     "--destino", item.get("destino", "dinosaurio"),
                     "--nombre", item["nombre"]]
    if item.get("altura_m"):
        cmd += ["--altura", str(item["altura_m"])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(os.path.join(salida, f"{item['nombre']}_informe.json")):
        raise RuntimeError("Blender falló:\n" + (r.stdout[-1500:] + r.stderr[-1500:]))


def crudo_de(item, carpeta):
    """El archivo que baja de Meshy que conviene refinar: el riggeado si hay, si no el modelo."""
    n = item["nombre"]
    for nombre in (f"{n}_rig.fbx", f"{n}_meshy.glb", f"{n}_meshy.fbx"):
        p = os.path.join(carpeta, nombre)
        if os.path.exists(p):
            return p
    return None


def bajar_de_meshy(item, simular):
    carpeta = os.path.join(CRUDOS, item["nombre"])
    ya = crudo_de(item, carpeta)
    if ya:
        log("  ya bajado de Meshy, no se gasta de nuevo:", os.path.relpath(ya, FNS))
        return ya
    if simular:
        os.makedirs(carpeta, exist_ok=True)
        destino = os.path.join(carpeta, f"{item['nombre']}_rig.fbx" if item.get("rig") else f"{item['nombre']}_meshy.glb")
        args = [os.path.join(AQUI, "prueba_simular_meshy.py")] + ([] if item.get("rig") else ["--sin-rig"]) + [destino]
        blender = buscar_blender()
        cmd = (blender + args[:1] + ["--"] + args[1:]) if blender and blender[0] != sys.executable else [sys.executable] + args
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return destino
    sys.path.insert(0, AQUI)
    import meshy_a_fbx
    meshy_a_fbx.hacer(item, CRUDOS)
    p = crudo_de(item, carpeta)
    if not p:
        raise RuntimeError("Meshy terminó pero no bajó ningún GLB/FBX")
    return p


def galeria(hechos, fallidos):
    filas = []
    for item in hechos:
        n = item["nombre"]
        d = os.path.join(MODELOS, n)
        inf = json.load(open(os.path.join(d, f"{n}_informe.json"), encoding="utf-8"))
        alto = inf["niveles"]["alto"]
        filas.append(f"""
<figure><img src="modelos/{n}/{n}_vista.png" alt="{n}">
<figcaption><b>{n}</b> · {item.get('destino')} · {alto['medidas_m'][0]} × {alto['medidas_m'][1]} × {alto['medidas_m'][2]} m
· {alto['triangulos']:,} triángulos{' · rig ' + str(inf.get('huesos_rig')) + ' huesos' if inf.get('huesos_rig') else ''}
<br><code>modelos/{n}/{n}_alto.fbx</code></figcaption></figure>""")
    malos = "".join(f"<li><b>{i['nombre']}</b>: {e}</li>" for i, e in fallidos)
    html = f"""<!doctype html><meta charset="utf-8"><title>Modelos FNS 2026</title>
<style>body{{background:#1b1512;color:#eee3d6;font:15px system-ui;margin:24px}}
figure{{display:inline-block;margin:8px;width:480px;vertical-align:top}}img{{width:100%;border-radius:8px;background:#2a211c}}
code{{color:#e0a36a}}h1{{font-weight:600}}</style>
<h1>Parque Triásico · modelos listos ({len(hechos)})</h1>{''.join(filas)}
{'<h2>Faltan</h2><ul>' + malos + '</ul><p>Volvé a correr el mismo comando: sigue desde acá.</p>' if fallidos else ''}"""
    ruta = os.path.join(FNS, "resultados.html")
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)
    return ruta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--destino", default="paisaje", help="paisaje | dinosaurio | hueso | todos")
    ap.add_argument("--solo", nargs="*", help="nombres puntuales")
    ap.add_argument("--simular", action="store_true", help="sin Meshy, con modelos de prueba")
    ap.add_argument("--rehacer", action="store_true", help="volver a refinar aunque ya esté hecho")
    ap.add_argument("--no-abrir", action="store_true")
    ap.add_argument("--incluir-existentes", action="store_true",
                    help="regenerar también lo que ya existe en la Mac (por defecto se saltea: no hay doble trabajo)")
    a = ap.parse_args()

    lista = json.load(open(LISTA, encoding="utf-8"))["modelos"]
    if a.solo:
        lista = [m for m in lista if m["nombre"] in a.solo]
    elif a.destino != "todos":
        lista = [m for m in lista if m.get("destino") == a.destino]
    if not a.incluir_existentes:
        for m in [m for m in lista if m.get("existe_en_mac")]:
            print(f"   {m['nombre']}: ya existe en la Mac ({m['existe_en_mac']}), no se regenera")
        lista = [m for m in lista if not m.get("existe_en_mac")]
    if not lista:
        sys.exit("No hay modelos que coincidan.")

    blender = buscar_blender()
    if not blender:
        sys.exit("No encuentro Blender. Instalalo o poné su ruta en la variable BLENDER.")

    if not a.simular:
        # un pedido de sólo lectura antes de arrancar: si la clave o la conexión fallan,
        # se sabe en 1 segundo y con el motivo, no después de 4 modelos fallidos
        sys.path.insert(0, AQUI)
        import meshy_a_fbx
        try:
            meshy_a_fbx.diagnostico()
        except SystemExit as e:
            log("Meshy no acepta la clave o la conexión:\n" + str(e))
            sys.exit("Frenado antes de empezar. Corré: python meshy_a_fbx.py --diagnostico")
    log(f"== {len(lista)} modelos · Blender: {blender[0]} · {'SIMULADO' if a.simular else 'Meshy real'} ==")
    hechos, fallidos = [], []
    for item in lista:
        n = item["nombre"]
        salida = os.path.join(MODELOS, n)
        log(f"-- {n}")
        try:
            if os.path.exists(os.path.join(salida, f"{n}_informe.json")) and not a.rehacer:
                log("  ya refinado, se saltea")
            else:
                crudo = bajar_de_meshy(item, a.simular)
                log("  Blender refinando…")
                refinar(blender, crudo, salida, item)
                log("  listo:", os.path.relpath(os.path.join(salida, f"{n}_alto.fbx"), FNS))
            hechos.append(item)
        except (Exception, SystemExit) as e:
            fallidos.append((item, str(e).splitlines()[0] if str(e) else e.__class__.__name__))
            log("  FALLÓ:", e)
            with open(REGISTRO, "a", encoding="utf-8") as f:
                traceback.print_exc(file=f)

    ruta = galeria(hechos, fallidos)
    log(f"== {len(hechos)} listos, {len(fallidos)} fallidos · galería: {ruta}")
    if not a.no_abrir:
        webbrowser.open("file://" + ruta)
    sys.exit(1 if fallidos else 0)


if __name__ == "__main__":
    main()
