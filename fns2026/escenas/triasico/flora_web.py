"""
Versión web de la flora: el nivel "medio" con texturas a 1K (la de 2K queda para TD/Unreal).
    python3 flora_web.py -- CARPETA_ASSETS DESTINO
"""
import os, sys
import bpy
origen, destino = sys.argv[sys.argv.index("--") + 1:][:2]
os.makedirs(destino, exist_ok=True)
for nombre in sorted(os.listdir(origen)):
    glb = os.path.join(origen, nombre, f"{nombre}_medio.glb")
    if not os.path.exists(glb):
        continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    for img in bpy.data.images:
        if img.size[0] > 1024:
            img.scale(1024, 1024)
    for o in bpy.context.scene.objects:
        o.select_set(o.type == "MESH")
    bpy.ops.export_scene.gltf(filepath=os.path.join(destino, f"{nombre}.glb"), use_selection=True,
                              export_format="GLB", export_image_format="JPEG", export_jpeg_quality=82)
    print(nombre, os.path.getsize(os.path.join(destino, f"{nombre}.glb")) // 1024, "KB")
