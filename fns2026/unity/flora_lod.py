"""
Niveles de detalle (LOD) de la flora para Unity: el mismo GLB de la web, simplificado al 30 % y
al 8 % con el Decimate de Blender. En el bosque hay miles de plantas: de cerca se dibuja la
original, a media distancia la del 30 % y en el horizonte la del 8 %.

    python3 flora_lod.py        (bpy de pip)  →  ParqueTriasico/Datos/lod/<planta>_lod{1,2}.glb

Sólo geometría con sus UV: el material (texturas) sale del GLB original, así los tres niveles se
ven iguales y comparten material en Unity.
"""
import os
import sys

import bpy

AQUI = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(AQUI, "..", "experiencia", "public", "assets")
SALIDA = os.path.join(AQUI, "ParqueTriasico", "Datos", "lod")
NIVELES = {"lod1": 0.30, "lod2": 0.08}


def main():
    os.makedirs(SALIDA, exist_ok=True)
    for archivo in sorted(os.listdir(ORIGEN)):
        if not archivo.endswith(".glb") or "quemado" in archivo:
            continue
        nombre = archivo[:-4]
        for nivel, proporcion in NIVELES.items():
            bpy.ops.wm.read_factory_settings(use_empty=True)
            bpy.ops.import_scene.gltf(filepath=os.path.join(ORIGEN, archivo))
            mallas = [o for o in bpy.data.objects if o.type == "MESH"]
            for o in mallas:
                m = o.modifiers.new("simplificar", "DECIMATE")
                m.ratio = proporcion
                m.use_collapse_triangulate = True
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.modifier_apply(modifier=m.name)
            antes = sum(len(o.data.polygons) for o in mallas)
            ruta = os.path.join(SALIDA, f"{nombre}_{nivel}.glb")
            bpy.ops.export_scene.gltf(filepath=ruta, export_format="GLB", export_materials="NONE")
            print(f"  {nombre} {nivel}: {antes} caras · {os.path.getsize(ruta) // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
