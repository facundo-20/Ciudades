"""
Gaussian splats en Blender: importar, alinear y mandar la ubicación a Unity y a la web.

Sirve sobre todo para las CAPTURAS REALES (el Valle de la Luna filmado o fotografiado, entrenado con
Brush desde COLMAP): la captura sale en un sistema de coordenadas cualquiera y hay que apoyarla sobre
el terreno real (unity/valle_real.py) a mano. En Blender eso es mover, girar y escalar el objeto.

  · Blender 5.3 o más nuevo: el importador nativo de PLY/SPZ reconoce los splats y los dibuja de
    verdad en EEVEE y Cycles (se ve igual que en Unity).
  · Antes de 5.3: el .ply entra como malla con los atributos del splat; se arma una vista previa de
    puntos con su color (alcanza para alinear).

Uso:
    blender -P importar_en_blender.py -- CAPTURA.ply [--nombre hongo] [--terreno]
        abre Blender con la captura (y, con --terreno, el valle real de referencia). Se alinea a mano.
    blender ESCENA.blend -b -P importar_en_blender.py -- --exportar
        lee cómo quedó cada captura ("splat_*") y escribe Datos/splats/<nombre>.json para Unity
        (posición, rotación como cuaternión, escala) y la línea para la web (public/splats/lista.json).

No usar "Apply Transform" sobre un splat: en Blender 5.3 todavía no corrige la escala, la rotación
ni los armónicos de cada gaussiana y lo arruina (está en las notas de la versión). Se guarda la
transformación del objeto, que es lo que leen Unity y la web.
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Matrix

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.abspath(os.path.join(AQUI, "..", ".."))
UNITY_SPLATS = os.path.join(FNS, "unity", "ParqueTriasico", "Datos", "splats")
SH_C0 = 0.28209479177387814


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo", nargs="?")
    ap.add_argument("--nombre")
    ap.add_argument("--terreno", action="store_true", help="traer el valle real de referencia para alinear")
    ap.add_argument("--exportar", action="store_true")
    ap.add_argument("--capitulo", default="hoy")
    return ap.parse_args(argv)


def existe_operador(op):
    try:
        op.get_rna_type()
        return True
    except Exception:
        return False


def importar(ruta, nombre):
    antes = set(bpy.data.objects)
    if ruta.lower().endswith(".spz"):
        if not existe_operador(bpy.ops.wm.spz_import):
            raise SystemExit("Este Blender no lee .spz (hace falta 5.3): convertilo a .ply con splat-transform")
        bpy.ops.wm.spz_import(filepath=ruta)
    else:
        bpy.ops.wm.ply_import(filepath=ruta)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    if not nuevos:
        raise SystemExit(f"no se importó nada de {ruta}")
    ob = nuevos[0]
    ob.name = f"splat_{nombre}"
    ob["fns_archivo"] = os.path.abspath(ruta)
    if ob.type == "POINTCLOUD":
        print(f"   {ob.name}: splat nativo (Blender {bpy.app.version_string})")
    else:
        vista_previa(ob)
        print(f"   {ob.name}: vista previa de puntos (los splats de verdad se ven desde Blender 5.3)")
    return ob


def vista_previa(ob):
    """Malla con atributos de splat (Blender < 5.3) → puntos del color del splat, del tamaño de cada uno."""
    malla = ob.data
    n = len(malla.vertices)
    dc = np.zeros((n, 3), np.float32)
    for i in range(3):
        a = malla.attributes.get(f"f_dc_{i}")
        if a:
            v = np.empty(n, np.float32)
            a.data.foreach_get("value", v)
            dc[:, i] = v
    col = np.clip(0.5 + SH_C0 * dc, 0, 1)
    atr = malla.color_attributes.new("color_splat", "FLOAT_COLOR", "POINT")
    atr.data.foreach_set("color", np.concatenate([col, np.ones((n, 1), np.float32)], 1).ravel())
    radio = np.full(n, 0.02, np.float32)
    if malla.attributes.get("scale_0"):
        s = np.empty((3, n), np.float32)
        for i in range(3):
            malla.attributes[f"scale_{i}"].data.foreach_get("value", s[i])
        radio = np.clip(np.exp(s).mean(0) * 1.5, 0.004, 0.4).astype(np.float32)
    r = malla.attributes.new("radio_splat", "FLOAT", "POINT")
    r.data.foreach_set("value", radio)

    mat = bpy.data.materials.new("splat_vista_previa")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "color_splat"
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(attr.outputs["Color"], bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 0.6

    gn = bpy.data.node_groups.new("splat_a_puntos", "GeometryNodeTree")
    gn.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    gn.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    entrada, salida = gn.nodes.new("NodeGroupInput"), gn.nodes.new("NodeGroupOutput")
    puntos = gn.nodes.new("GeometryNodeMeshToPoints")
    leer = gn.nodes.new("GeometryNodeInputNamedAttribute")
    leer.data_type = "FLOAT"
    leer.inputs["Name"].default_value = "radio_splat"
    poner = gn.nodes.new("GeometryNodeSetMaterial")
    poner.inputs["Material"].default_value = mat
    gn.links.new(entrada.outputs[0], puntos.inputs["Mesh"])
    gn.links.new(leer.outputs["Attribute"], puntos.inputs["Radius"])
    gn.links.new(puntos.outputs["Points"], poner.inputs["Geometry"])
    gn.links.new(poner.outputs["Geometry"], salida.inputs[0])
    mod = ob.modifiers.new("splat_a_puntos", "NODES")
    mod.node_group = gn


def terreno_de_referencia():
    """El valle real (Copernicus + Sentinel-2) como malla, para apoyar la captura encima."""
    ruta = os.path.join(FNS, "unity", "verificacion", "vista_valle.py")
    if not os.path.exists(ruta):
        print("   (no encuentro vista_valle.py: sin terreno de referencia)")
        return
    sys.path.insert(0, os.path.dirname(ruta))
    try:
        import vista_valle as VV
        if hasattr(VV, "armar_terreno"):
            VV.armar_terreno()
            print("   terreno del valle real de referencia: listo")
        else:
            print("   (vista_valle.py no expone armar_terreno: se alinea sin referencia)")
    except Exception as e:
        print(f"   (no pude armar el terreno de referencia: {e})")


# Blender (z arriba, mano derecha) → Unity (y arriba, mano izquierda): (x, y, z) → (x, z, y)
CAMBIO = Matrix(((1, 0, 0), (0, 0, 1), (0, 1, 0)))


def a_unity(ob):
    """Transformación de Unity para que el splat (leído tal cual del .ply, como hace
    UnityGaussianSplatting) quede donde quedó en Blender: M_unity = CAMBIO · M_blender."""
    m = ob.matrix_world
    lineal = CAMBIO @ m.to_3x3()
    k = m.to_3x3().determinant() ** (1 / 3)               # escala uniforme (la que hay que usar)
    # CAMBIO invierte la orientación: se lleva el signo en la escala Y para que quede una rotación pura
    rot = lineal @ Matrix.Diagonal((1 / k, -1 / k, 1 / k))
    q = rot.to_quaternion()
    pos = CAMBIO @ m.to_translation()
    return {"posicion": [round(v, 4) for v in pos], "rotacion": [round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)],
            "escala": [round(k, 5), round(-k, 5), round(k, 5)]}


def a_web(ob):
    """three.js (y arriba, mano derecha): (x, y, z) de Blender → (x, z, -y)."""
    web = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
    m = ob.matrix_world
    k = m.to_3x3().determinant() ** (1 / 3)
    rot = (web @ m.to_3x3() @ web.transposed()) @ Matrix.Diagonal((1 / k,) * 3)
    q = rot.to_quaternion()
    pos = web @ m.to_translation()
    return {"posicion": [round(v, 4) for v in pos], "cuaternion": [round(q.x, 6), round(q.y, 6), round(q.z, 6), round(q.w, 6)],
            "escala": round(k, 5)}


def exportar(capitulo):
    hechos = 0
    os.makedirs(UNITY_SPLATS, exist_ok=True)
    for ob in bpy.data.objects:
        if not ob.name.startswith("splat_"):
            continue
        nombre = ob.name[len("splat_"):]
        ruta = os.path.join(UNITY_SPLATS, f"{nombre}.json")
        datos = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
        datos.update(capitulo=datos.get("capitulo", capitulo), **a_unity(ob), web=a_web(ob))
        json.dump(datos, open(ruta, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        print(f"   {nombre}: Unity {datos['posicion']} · {ruta}")
        hechos += 1
    print(f"listo: {hechos} capturas exportadas" if hechos else "no hay objetos splat_* en la escena")


def main():
    a = argumentos()
    if a.exportar:
        exportar(a.capitulo)
        return
    if not a.archivo:
        raise SystemExit("falta el archivo .ply o .spz")
    if a.terreno:
        terreno_de_referencia()
    importar(a.archivo, a.nombre or os.path.splitext(os.path.basename(a.archivo))[0])


if __name__ == "__main__":
    main()
