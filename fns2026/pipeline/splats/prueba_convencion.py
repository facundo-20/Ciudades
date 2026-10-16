"""Prueba de que las cámaras que escribe vistas_blender.py son las que Brush/Nerfstudio esperan:
una esfera roja en un lugar conocido, vista desde cámaras al azar, tiene que caer en el píxel que
predice transforms.json (convención OpenGL: la cámara mira a -Z, arriba +Y).

    python3 prueba_convencion.py
"""
import math
import os
import random
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vistas_blender as V  # noqa: E402


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    esc = bpy.context.scene
    esc.render.engine = "CYCLES"
    esc.cycles.samples = 4
    esc.cycles.use_denoising = False
    esc.render.film_transparent = True
    esc.view_settings.view_transform = "Standard"
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25, location=(3.0, -2.0, 1.2))
    esfera = bpy.context.active_object
    mat = bpy.data.materials.new("rojo")
    mat.use_nodes = True
    nodos = mat.node_tree.nodes
    for n in list(nodos):
        nodos.remove(n)
    em = nodos.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 0, 0, 1)
    em.inputs["Strength"].default_value = 5
    out = nodos.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(em.outputs[0], out.inputs[0])
    esfera.data.materials.append(mat)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    esc.collection.objects.link(cam)
    esc.camera = cam
    ancho, alto, fov = 160, 90, 75.0
    V.preparar_camara(cam, ancho, alto, fov)
    intr = V.intrinsecos(ancho, alto, fov)
    rng = random.Random(1)
    centro = Vector((3.0, -2.0, 1.2))
    errores = []
    carpeta = tempfile.mkdtemp()
    for i in range(6):
        # cámaras a 3-6 m que miran cerca de la esfera (no justo al centro: así el punto cae fuera del centro)
        a = rng.uniform(0, 2 * math.pi)
        p = centro + Vector((math.cos(a) * rng.uniform(3, 6), math.sin(a) * rng.uniform(3, 6), rng.uniform(-1, 2)))
        objetivo = centro + Vector((rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), rng.uniform(-0.5, 0.5)))
        cam.location = p
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = V.mirar(p, objetivo)
        bpy.context.view_layer.update()
        ruta = os.path.join(carpeta, f"{i}.png")
        esc.render.filepath = ruta
        bpy.ops.render.render(write_still=True)
        # predicción con la matriz tal como va a transforms.json
        c2w = np.array([list(f) for f in cam.matrix_world])
        x = np.linalg.inv(c2w) @ np.array([*centro, 1.0])
        u = intr["cx"] + intr["fl_x"] * (x[0] / -x[2])
        v = intr["cy"] - intr["fl_y"] * (x[1] / -x[2])          # la imagen crece hacia abajo
        img = bpy.data.images.load(ruta)
        px = np.array(img.pixels[:]).reshape(alto, ancho, 4)[::-1]   # Blender guarda de abajo hacia arriba
        rojo = (px[..., 0] > 0.5) & (px[..., 1] < 0.3) & (px[..., 3] > 0.5)
        ys, xs = np.nonzero(rojo)
        if not len(xs):
            errores.append(f"vista {i}: la esfera no se ve")
            continue
        du, dv = xs.mean() + 0.5 - u, ys.mean() + 0.5 - v
        print(f"vista {i}: predicho ({u:6.1f}, {v:6.1f}) · render ({xs.mean() + 0.5:6.1f}, {ys.mean() + 0.5:6.1f}) · error {math.hypot(du, dv):.2f} px")
        if math.hypot(du, dv) > 1.5:
            errores.append(f"vista {i}: error de {math.hypot(du, dv):.1f} px")
    print("CONVENCIÓN OK" if not errores else "FALLA: " + "; ".join(errores))
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
