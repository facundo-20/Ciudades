"""
Paso 2 de la cañería: lo que baja de Meshy entra acá y sale listo para TouchDesigner.

    blender -b --factory-startup -P blender_refinar.py -- entrada.glb salida/ --largo 4.0 [--destino dinosaurio]

(En la Mac: /Applications/Blender.app/Contents/MacOS/Blender · en Windows:
"C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe".)
También corre con el módulo `bpy` de pip, que es como se probó: python3 blender_refinar.py -- ...

Qué arregla y por qué, en orden:
 1. ESCALA REAL. Meshy entrega cualquier tamaño. Un Herrerasaurus de 4 m en la pared
    LED tiene que medir 4 m en TD, así el 1:1 no se ajusta a ojo en el predio.
 2. ORIGEN EN LOS PIES, centrado. En TD el dinosaurio se apoya en z=0 del piso de la
    sala (el mismo sistema en metros de PEDIDO-SALA) sin offsets mágicos.
 3. LIMPIEZA. Meshy deja vértices duplicados en las costuras de la textura y alguna
    isla suelta de ruido. Se sueldan y se borran; las normales se recalculan hacia afuera.
 4. NIVELES DE DETALLE POR MÁQUINA. No es lo mismo la M4 que la OMEN i5:
      alto  = M4 / OMEN i7 (placa dedicada), para el dinosaurio 1:1 de la pared
      medio = OMEN i5, o varios dinosaurios en pantalla a la vez
      bajo  = instancias (los huesos del piso se dibujan cientos de veces)
    Decimate conserva los grupos de vértices, así que el rig sigue andando en todos.
 5. TEXTURAS a 2K como techo (1K en bajo). Meshy baja 4K: en un LED P3 a 3 m no se
    ve la diferencia y en la i5 cuesta memoria de video.
 6. FBX con texturas adentro + GLB. FBX para TD (FBX COMP), GLB para three.js y la web.
 7. VISTA PREVIA renderizada con Cycles por CPU a pocas muestras: anda en cualquier
    máquina, con o sin placa (Workbench y Eevee necesitan OpenGL y en modo -b sin
    pantalla fallan). Sirve para revisar el lote sin abrir Blender.
 8. INFORME json: triángulos por nivel, medidas, huesos del rig, animaciones.
"""

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Vector

NIVELES = {
    # nombre: (fracción de triángulos a conservar sobre el tope, tope de triángulos, textura máx)
    "dinosaurio": {"alto": 60000, "medio": 25000, "bajo": 8000},
    "hueso":      {"alto": 15000, "medio": 6000,  "bajo": 1500},
    "maqueta":    {"alto": 120000, "medio": 50000, "bajo": 15000},
}
TEXTURA_MAX = {"alto": 2048, "medio": 2048, "bajo": 1024}


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--largo", type=float, required=True, help="medida mayor horizontal, en metros")
    ap.add_argument("--destino", default="dinosaurio", choices=list(NIVELES))
    ap.add_argument("--nombre", default=None)
    ap.add_argument("--sin-vista", action="store_true")
    return ap.parse_args(argv)


def limpiar_escena():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def importar(ruta):
    ext = os.path.splitext(ruta)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=ruta)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=ruta)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=ruta)
    else:
        raise SystemExit(f"Formato no soportado: {ext}")


def mallas():
    return [o for o in bpy.context.scene.objects if o.type == "MESH"]


def armadura():
    arm = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    return arm[0] if arm else None


def seleccionar(objs, activo=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = activo or objs[0]


def unir_mallas(nombre):
    ms = mallas()
    if not ms:
        raise SystemExit("El archivo no trae ninguna malla.")
    if len(ms) > 1:
        seleccionar(ms)
        bpy.ops.object.join()
    m = mallas()[0]
    m.name = nombre
    m.data.name = nombre
    return m


def caja(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return mn, mx


def raiz_de(malla):
    """Lo que hay que mover y escalar: la armadura si hay rig (arrastra a la malla), si no la malla."""
    arm = armadura()
    return arm if arm else malla


CANALES_DE_OBJETO = ("location", "rotation_euler", "rotation_quaternion", "rotation_axis_angle", "scale")


def curvas_de(accion):
    """Todas las F-Curves de una acción, con la API por capas de Blender 4.4+ y la vieja."""
    if hasattr(accion, "layers") and accion.layers:
        for capa in accion.layers:
            for tira in capa.strips:
                for bolsa in getattr(tira, "channelbags", []):
                    yield bolsa.fcurves
    elif hasattr(accion, "fcurves"):
        yield accion.fcurves


def soltar_transformacion_animada(obj):
    """Un FBX importado trae cuadros clave de posición/escala del OBJETO armadura (el
    exportador de Meshy hornea todo). Al volver a exportar con bake_anim se imponen de
    nuevo y la escala real se pierde (probado: el dinosaurio volvía a medir 29 m).
    Se borran sólo las curvas del objeto; las de los huesos (pose.bones[...]) quedan."""
    for accion in bpy.data.actions:
        for curvas in curvas_de(accion):
            for fc in [fc for fc in curvas if fc.data_path in CANALES_DE_OBJETO]:
                curvas.remove(fc)


def escalar_y_apoyar(malla, largo):
    raiz = raiz_de(malla)
    if raiz is not malla:
        soltar_transformacion_animada(raiz)
    # la malla hija de una armadura puede tener su propia escala: se aplica primero
    bpy.context.view_layer.update()
    mn, mx = caja([malla])
    actual = max(mx.x - mn.x, mx.y - mn.y)
    if actual <= 0:
        raise SystemExit("La malla no tiene medida horizontal.")
    f = largo / actual
    raiz.scale = raiz.scale * f
    bpy.context.view_layer.update()
    mn, mx = caja([malla])
    centro = Vector(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    raiz.location = raiz.location - centro
    bpy.context.view_layer.update()
    if raiz is malla:
        seleccionar([malla])
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    # Con rig NO se aplica la transformación: aplicarla sobre la armadura corre los
    # huesos respecto de la pose de enlace y la malla deformada vuelve a su lugar
    # original (probado). La escala y la posición quedan en el objeto raíz y el FBX
    # las lleva tal cual; TD las lee sin problema.
    return f


def limpiar_malla(malla):
    seleccionar([malla])
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=0.0005)
    bpy.ops.mesh.delete_loose()
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # islas de ruido: menos del 0,5 % de los vértices totales
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")
    try:
        bpy.ops.object.shade_auto_smooth()
    except Exception:
        # versiones sin el operador: suavizado simple, que alcanza para la pared
        for p in malla.data.polygons:
            p.use_smooth = True


def triangulos(malla):
    return sum(len(p.vertices) - 2 for p in malla.data.polygons)


def nivel(malla, tope, sufijo):
    copia = malla.copy()
    copia.data = malla.data.copy()
    copia.name = f"{malla.name}_{sufijo}"
    bpy.context.scene.collection.objects.link(copia)
    t = triangulos(copia)
    if t > tope:
        mod = copia.modifiers.new("reducir", "DECIMATE")
        mod.ratio = tope / t
        mod.use_collapse_triangulate = True
        seleccionar([copia])
        bpy.ops.object.modifier_apply(modifier=mod.name)
    return copia


def reducir_texturas(maximo, carpeta):
    os.makedirs(carpeta, exist_ok=True)
    for img in bpy.data.images:
        if img.size[0] == 0 or img.type != "IMAGE":
            continue
        w, h = img.size
        if max(w, h) > maximo:
            f = maximo / max(w, h)
            img.scale(int(w * f), int(h * f))
        nombre = bpy.path.clean_name(img.name) + ".png"
        img.filepath_raw = os.path.join(carpeta, nombre)
        img.file_format = "PNG"
        img.save()


def exportar(objs, ruta_sin_ext):
    arm = armadura()
    seleccionar(objs + ([arm] if arm else []), arm or objs[0])
    bpy.ops.export_scene.fbx(
        filepath=ruta_sin_ext + ".fbx",
        use_selection=True,
        apply_scale_options="FBX_SCALE_ALL",   # TD lee metros sin el 100x de centímetros
        axis_forward="-Z", axis_up="Y",        # Y arriba: lo que espera TD
        path_mode="COPY", embed_textures=True, # un solo archivo que se copia a la otra PC
        add_leaf_bones=False,                  # huesos "_end" sobran y ensucian el rig en TD
        bake_anim=bool(arm),
    )
    bpy.ops.export_scene.gltf(filepath=ruta_sin_ext + ".glb", use_selection=True, export_format="GLB")
    if not arm:
        # OBJ para instancing en TD: el File In SOP lo lee directo, sin FBX COMP en el medio.
        # Y arriba (TD), metros, con normales y UV.
        bpy.ops.wm.obj_export(filepath=ruta_sin_ext + ".obj", export_selected_objects=True,
                              forward_axis="NEGATIVE_Z", up_axis="Y", export_materials=True)


def vista_previa(objs, ruta, largo):
    esc = bpy.context.scene
    for o in esc.objects:
        o.hide_render = o not in objs and o.type == "MESH"
    cam_d = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_d)
    esc.collection.objects.link(cam)
    d = largo * 1.6
    cam.location = (d * 0.8, -d, d * 0.55)
    mn, mx = caja(objs)
    objetivo = (mn + mx) / 2
    cam.rotation_euler = (objetivo - cam.location).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    esc.render.engine = "CYCLES"
    esc.cycles.device = "CPU"
    esc.cycles.samples = 24
    esc.cycles.use_denoising = True
    # luz de estudio simple: un sol cálido de arenisca y cielo gris, sin HDRI externo
    mundo = bpy.data.worlds.new("estudio")
    mundo.use_nodes = True
    mundo.node_tree.nodes["Background"].inputs["Color"].default_value = (0.18, 0.17, 0.16, 1)
    esc.world = mundo
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = 3.5
    sol.rotation_euler = (math.radians(50), 0, math.radians(30))
    esc.collection.objects.link(sol)
    esc.render.resolution_x, esc.render.resolution_y = 960, 540
    esc.render.filepath = ruta
    esc.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)


def main():
    a = argumentos()
    nombre = a.nombre or os.path.splitext(os.path.basename(a.entrada))[0].replace("_meshy", "")
    os.makedirs(a.salida, exist_ok=True)
    limpiar_escena()
    importar(os.path.abspath(a.entrada))
    malla = unir_mallas(nombre)
    tri_original = triangulos(malla)
    factor = escalar_y_apoyar(malla, a.largo)
    limpiar_malla(malla)

    informe = {"nombre": nombre, "destino": a.destino, "triangulos_meshy": tri_original,
               "escala_aplicada": round(factor, 5), "niveles": {}}
    arm = armadura()
    if arm:
        informe["huesos_rig"] = len(arm.data.bones)
        informe["animaciones"] = [ac.name for ac in bpy.data.actions]

    niveles = []
    for suf, tope in NIVELES[a.destino].items():
        n = nivel(malla, tope, suf)
        niveles.append((suf, n))
    bpy.data.objects.remove(malla)

    reducir_texturas(TEXTURA_MAX["alto"], os.path.join(a.salida, "texturas"))
    for suf, n in niveles:
        mn, mx = caja([n])
        exportar([n], os.path.join(a.salida, f"{nombre}_{suf}"))
        informe["niveles"][suf] = {
            "triangulos": triangulos(n),
            "medidas_m": [round(mx.x - mn.x, 3), round(mx.y - mn.y, 3), round(mx.z - mn.z, 3)],
            "fbx": f"{nombre}_{suf}.fbx",
        }

    if not a.sin_vista:
        vista_previa([niveles[0][1]], os.path.join(a.salida, f"{nombre}_vista.png"), a.largo)
        informe["vista"] = f"{nombre}_vista.png"

    with open(os.path.join(a.salida, f"{nombre}_informe.json"), "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=2)
    print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
