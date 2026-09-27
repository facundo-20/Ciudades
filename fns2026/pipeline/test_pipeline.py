"""
Autotest de la cañería Meshy → Blender → FBX, sin red y sin Meshy.
Arma un modelo "tipo Meshy" (escala y origen cualquiera, costuras duplicadas, textura 4K,
rig con animación), lo pasa por blender_refinar.py y revisa el FBX que sale.

    python3 test_pipeline.py            (con `pip install bpy`)
    blender -b --factory-startup -P test_pipeline.py
"""
import json, os, subprocess, sys, tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def correr(*args):
    r = subprocess.run([PY, *args], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:])
        raise SystemExit(f"falló: {args}")
    return r.stdout


MEDIR = r'''
import bpy, json, sys
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[-1])
m = [o for o in bpy.context.scene.objects if o.type == "MESH"][0]
arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
cajas = []
for f in (1, 15):
    bpy.context.scene.frame_set(f)
    e = m.evaluated_get(bpy.context.evaluated_depsgraph_get())
    ps = [e.matrix_world @ v.co for v in e.data.vertices]
    cajas.append([min(p.x for p in ps), max(p.x for p in ps), min(p.y for p in ps), max(p.y for p in ps), min(p.z for p in ps)])
print("MEDIDA" + json.dumps({"cajas": cajas, "rig": bool(arm), "imagenes": len(bpy.data.images)}))
'''


def medir(fbx):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(MEDIR)
    out = correr(f.name, "--", fbx)
    return json.loads(out.split("MEDIDA", 1)[1].splitlines()[0])


def main():
    tmp = tempfile.mkdtemp(prefix="fns_pipeline_")
    fallas = 0

    def chequear(cond, texto):
        nonlocal fallas
        print(("OK    " if cond else "FALLA ") + texto)
        fallas += not cond

    # 1) modelo estático (GLB, como un hueso de Meshy)
    glb = os.path.join(tmp, "estatico.glb")
    correr(os.path.join(AQUI, "prueba_simular_meshy.py"), "--sin-rig", glb)
    correr(os.path.join(AQUI, "blender_refinar.py"), "--", glb, os.path.join(tmp, "e"),
           "--largo", "0.35", "--destino", "hueso", "--nombre", "hueso", "--sin-vista")
    inf = json.load(open(os.path.join(tmp, "e", "hueso_informe.json")))
    chequear(abs(inf["niveles"]["alto"]["medidas_m"][0] - 0.35) < 0.005, "estático: largo real 0,35 m")
    chequear(inf["niveles"]["bajo"]["triangulos"] <= 1500, "estático: nivel bajo respeta el tope de triángulos")
    med = medir(os.path.join(tmp, "e", "hueso_alto.fbx"))
    chequear(abs(med["cajas"][0][4]) < 0.005, "estático: apoyado en z = 0")
    chequear(med["imagenes"] >= 1, "estático: la textura viaja adentro del FBX")
    chequear(os.path.exists(os.path.join(tmp, "e", "hueso_bajo.obj")), "estático: OBJ para instancing en TD")

    # 2) modelo con rig (FBX, como el rigging de Meshy)
    fbx = os.path.join(tmp, "rig.fbx")
    correr(os.path.join(AQUI, "prueba_simular_meshy.py"), fbx)
    correr(os.path.join(AQUI, "blender_refinar.py"), "--", fbx, os.path.join(tmp, "r"),
           "--largo", "4.0", "--nombre", "dino", "--sin-vista")
    med = medir(os.path.join(tmp, "r", "dino_alto.fbx"))
    c1, c15 = med["cajas"]
    chequear(med["rig"], "rig: la armadura sobrevive")
    chequear(abs((c1[1] - c1[0]) - 4.0) < 0.02, f"rig: largo real 4 m (da {c1[1] - c1[0]:.3f})")
    chequear(abs((c1[0] + c1[1]) / 2) < 0.05, "rig: centrado en x")
    chequear(abs(c1[4]) < 0.02, "rig: apoyado en z = 0")
    chequear(abs(c1[2] - c15[2]) > 0.05 or abs(c1[3] - c15[3]) > 0.05, "rig: la animación deforma la malla")

    print(f"\n{'todo OK' if not fallas else f'{fallas} fallas'}  ·  archivos en {tmp}")
    raise SystemExit(1 if fallas else 0)


if __name__ == "__main__":
    main()
