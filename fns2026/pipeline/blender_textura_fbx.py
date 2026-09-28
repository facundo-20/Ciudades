"""
Forma en Blender, textura con Meshy, salida FBX a escala real. Es el camino por defecto desde
el 28/09: la IA ya no inventa la forma (salieron un Submarino de metal y un arco romano); la
geometría se arma acá con las medidas publicadas y Meshy sólo la pinta con el color original.

    python3 fns2026/pipeline/blender_textura_fbx.py                       # sólo Blender → FBX (gratis)
    python3 fns2026/pipeline/blender_textura_fbx.py --tope 40             # + textura de Meshy (~10 c/u)
    python3 fns2026/pipeline/blender_textura_fbx.py --solo cardon --tope 10
    python3 fns2026/pipeline/blender_textura_fbx.py --glb ruta/result.glb # Hongo + Submarino de la Mac

Sale en fns2026/modelos/<nombre>/: <nombre>_alto.fbx (+ medio y bajo, + GLB para la web) por
blender_refinar.py, igual que todo lo demás.
"""

import argparse
import json
import os
import subprocess
import sys

import bpy  # noqa: F401  (antes que bmesh y que los módulos del proyecto)

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(FNS, "escenas", "sanjuan"))
sys.path.insert(0, AQUI)

# Qué se arma en Blender y con qué color original se pinta. Los prompts describen el material
# real (fotos y video de referencia); las medidas salen del armado, no del prompt.
ACTIVOS = {
    "teatro_bicentenario": dict(
        armar=lambda P: P.arco_procedural(0, 0),
        prompt=("pale cream San Juan travertine marble cladding in large rectangular plates with fine joints on the arch, "
                "light grey exposed concrete on the building, dark tinted glass facade, clean modern architecture")),
    "catedral_san_juan": dict(
        armar=lambda P: P.catedral_procedural(0, 0),
        prompt=("side walls clad in dark reddish-brown natural slate stone from the Pie de Palo range, recessed smooth white "
                "plastered wall between them, nave in warm reddish exposed brick, 1979 modernist church")),
    "cardon": dict(
        armar=lambda P: P.molde_cardon(),
        prompt=("cardon cactus Trichocereus terscheckii: grey-green columnar cactus with deep vertical ribs and rows of "
                "yellowish-brown spines, dusty, older base slightly woody and pale")),
    "jarilla": dict(
        armar=lambda P: P.molde_jarilla(),
        prompt=("jarilla desert shrub Larrea: dense tiny resinous olive-green leaves on dark grey twigs, dusty, "
                "sparse gaps showing branches")),
}


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*", help="nombres de ACTIVOS")
    ap.add_argument("--tope", type=int, default=0, help="créditos de Meshy para las texturas (0 = sólo Blender)")
    ap.add_argument("--glb", help="un GLB propio (p. ej. result.glb de la Mac) para texturar y pasar a FBX")
    ap.add_argument("--nombre", help="nombre para el --glb")
    ap.add_argument("--largo", type=float, help="largo real en metros para el --glb")
    ap.add_argument("--prompt", help="color original para el --glb")
    return ap.parse_args(argv)


def escena_vacia():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def preparar_para_textura():
    """Todo lo armado a un solo objeto, en el origen, con UV (Meshy respeta las UV originales)."""
    mallas = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in mallas:
        o.hide_render = False
        o.hide_viewport = False
        o.location.z = o.location.z if o.location.z > -500 else 0.0     # los moldes viven en z = -1000
        bpy.context.view_layer.objects.active = o
        o.select_set(True)
        for m in list(o.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError:
                pass
    bpy.ops.object.select_all(action="DESELECT")
    for o in mallas:
        o.select_set(True)
    bpy.context.view_layer.objects.active = mallas[0]
    if len(mallas) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    ob.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    d = ob.dimensions
    return ob, max(d.x, d.y), d.z


def exportar_glb(ruta):
    bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", use_selection=True)
    return ruta


def refinar(entrada, nombre, largo):
    """Mismo paso final que todos los modelos: escala real, limpieza, niveles, FBX + GLB, vista."""
    salida = os.path.join(FNS, "modelos", nombre)
    cmd = [sys.executable, os.path.join(AQUI, "blender_refinar.py"), "--", entrada, salida,
           "--largo", str(largo), "--destino", "hito", "--nombre", nombre]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("blender_refinar falló:\n" + r.stdout[-800:] + r.stderr[-800:])
    return os.path.join(salida, f"{nombre}_alto.fbx")


def texturar(nombre, glb, prompt, tope):
    """Con tope > 0: Meshy pinta el modelo de Blender. Sin tope: queda el material de Blender."""
    if tope <= 0:
        return glb
    os.environ["MESHY_TOPE"] = str(tope)
    import meshy_a_fbx
    salidas = meshy_a_fbx.retexturar(glb, prompt, os.path.join(FNS, "modelos_meshy", nombre), nombre)
    return salidas.get("glb") or salidas.get("fbx")


def main():
    a = argumentos()
    hechos = {}
    if a.glb:
        if not (a.nombre and a.largo):
            sys.exit("--glb necesita --nombre y --largo (metros reales)")
        glb = texturar(a.nombre, os.path.abspath(a.glb), a.prompt or "", a.tope)
        hechos[a.nombre] = refinar(glb, a.nombre, a.largo)
    else:
        import postales_sanjuan as P
        for nombre, act in ACTIVOS.items():
            if a.solo and nombre not in a.solo:
                continue
            escena_vacia()
            act["armar"](P)
            ob, largo, alto = preparar_para_textura()
            tmp = os.path.join("/tmp", f"{nombre}_blender.glb")
            exportar_glb(tmp)
            glb = texturar(nombre, tmp, act["prompt"], a.tope)
            hechos[nombre] = refinar(glb, nombre, round(largo, 2))
            print(f"   {nombre}: {largo:.1f} m de largo · {alto:.1f} m de alto → {os.path.relpath(hechos[nombre], FNS)}", flush=True)
    print(json.dumps({k: os.path.relpath(v, FNS) for k, v in hechos.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
