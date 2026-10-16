"""
Vistas para hornear un capítulo del Triásico en Gaussian splats.

La idea: Cycles calcula la luz "de verdad" (rebotes, sombras suaves, translucidez de las hojas)
pero no corre en vivo; un Gaussian splat entrenado con cientos de renders de Cycles se ve casi
igual y se dibuja en tiempo real en Unity (UnityGaussianSplatting) y en la web (Spark). Acá sale el
conjunto de entrenamiento:

    blender -b --factory-startup -P vistas_blender.py -- SALIDA --capitulo bosque [opciones]
    (o con el bpy de pip:  python3 vistas_blender.py -- SALIDA --capitulo bosque ...)

En SALIDA/<capitulo>/:
    images/0000.png ...     las vistas, RGBA: el cielo y lo lejano quedan transparentes (los pone el
                            motor en vivo) y el splat aprende sólo lo cercano
    transforms.json         cámaras en el formato de Nerfstudio (las lee Brush, gsplat y Nerfstudio)
    transforms_test.json    una de cada 12 vistas, para medir la calidad (PSNR) sin entrenarlas
    puntos_iniciales.ply    nube inicial muestreada de la geometría de la escena (mejor que al azar)
    region.json             el recorrido, el radio y el cambio de ejes a Unity y a la web

Qué se hornea: el terreno y la flora del capítulo con su sol. NO van los dinosaurios (son mallas
animadas en vivo), el agua (sistema de agua de HDRP), la bruma, el horizonte ni el volcán.

Coordenadas: el splat queda en el mundo de Blender (z arriba). Unity = (x, z, y) de Blender, o sea
rotación (-90°, 0, 0) con escala (1, -1, 1); la web (three.js, y arriba) = (x, z, -y).
"""

import argparse
import json
import math
import os
import random
import sys
import time

import bpy
import numpy as np
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, os.path.join(FNS, "escenas", "hiperreal"))
import triasico_cycles as T  # noqa: E402

CALIDADES = {
    # vistas, ancho, alto, muestras
    "prueba": (48, 320, 180, 16),       # para probar el circuito en la nube (CPU)
    "media": (240, 1280, 720, 64),      # M4 (Metal) u OMEN (OptiX): ~1 h
    "final": (400, 1600, 900, 128),     # OMEN con OptiX: la de la sala
}


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--capitulo", default="bosque", choices=[c for c in T.CAPITULOS if c != "hoy"])
    ap.add_argument("--calidad", default="media", choices=list(CALIDADES))
    ap.add_argument("--vistas", type=int, help="cantidad de vistas (si no, la de la calidad)")
    ap.add_argument("--radio", type=float, default=45.0, help="radio (m) alrededor del recorrido que se hornea")
    ap.add_argument("--fov", type=float, default=75.0, help="campo horizontal de las vistas (grados)")
    ap.add_argument("--semilla", type=int, default=231)
    ap.add_argument("--assets", default=os.path.join(FNS, "escenas", "triasico", "salida", "assets"))
    ap.add_argument("--modelos", default=os.path.join(FNS, "modelos"))
    return ap.parse_args(argv)


def suelo(p):
    return T.altura(p.x, -p.y)


def mirar(desde, hacia):
    return (hacia - desde).to_track_quat("-Z", "Y")


def poses(cap, n, rng):
    """Dónde se para cada vista. Tres de cada cuatro, desde la sala: sobre el recorrido (con ±3 m
    a los costados), a la altura de los ojos de chicos y grandes y mirando para cualquier lado,
    también hacia abajo (el piso LED muestra el suelo). El resto, desde afuera, a 12-30 m, mirando
    al recorrido: dan paralaje y le fijan la forma a lo cercano."""
    desde, hasta = T.web_a_blender(cap["desde"]), T.web_a_blender(cap["hasta"])
    eje = (hasta - desde)
    eje.z = 0
    largo = max(eje.length, 1e-3)
    eje.normalize()
    lado = Vector((-eje.y, eje.x, 0))
    salida = []
    n_sala = int(n * 0.75)
    for i in range(n):
        if i < n_sala:
            p = desde.lerp(hasta, rng.random()) + lado * rng.uniform(-3, 3) + eje * rng.uniform(-2, 2)
            p.z = suelo(p) + rng.uniform(0.5, 2.8)
            giro = rng.uniform(0, 2 * math.pi)
            inclinacion = math.radians(rng.uniform(-50, 12))
            d = Vector((math.cos(inclinacion) * math.cos(giro), math.cos(inclinacion) * math.sin(giro), math.sin(inclinacion)))
            salida.append((p, d.to_track_quat("-Z", "Y")))
        else:
            centro = desde.lerp(hasta, rng.random())
            a = rng.uniform(0, 2 * math.pi)
            r = rng.uniform(12, 30)
            p = centro + Vector((math.cos(a) * r, math.sin(a) * r, 0))
            p.z = suelo(p) + rng.uniform(2, 9)
            objetivo = centro + lado * rng.uniform(-3, 3)
            objetivo.z = suelo(objetivo) + 1.0
            salida.append((p, mirar(p, objetivo)))
    return salida, desde, hasta, largo


def distancia_al_recorrido(P, a, b):
    """Distancia horizontal de cada punto (N×3) al segmento a-b."""
    a2, b2 = np.array([a.x, a.y]), np.array([b.x, b.y])
    ab = b2 - a2
    t = np.clip(((P[:, :2] - a2) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(P[:, :2] - (a2 + t[:, None] * ab), axis=1)


def nube_inicial(ruta, desde, hasta, radio, rng, tope=300_000):
    """Puntos sobre la geometría real de la escena (terreno y cada planta instanciada), con un
    color aproximado: tierra para el suelo, verde para la flora. Brush los toma como punto de
    partida (es lo que en una captura real daría COLMAP)."""
    dg = bpy.context.evaluated_depsgraph_get()
    cache = {}
    trozos, colores = [], []
    for inst in dg.object_instances:
        ob = inst.object
        if ob.type != "MESH":
            continue
        malla = ob.data
        clave = malla.name_full
        if clave not in cache:
            n = len(malla.vertices)
            co = np.empty(n * 3, dtype=np.float32)
            malla.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3)
            # una planta aporta como mucho 400 puntos; el terreno, todos los suyos
            es_terreno = ob.name.startswith("terreno") or n > 200_000
            if not es_terreno and n > 400:
                co = co[np.random.default_rng(len(cache)).choice(n, 400, replace=False)]
            cache[clave] = (co, es_terreno)
        co, es_terreno = cache[clave]
        m = np.array(inst.matrix_world, dtype=np.float32)
        P = co @ m[:3, :3].T + m[:3, 3]
        P = P[distancia_al_recorrido(P, desde, hasta) < radio]
        if not len(P):
            continue
        base = np.array([0.42, 0.36, 0.28] if es_terreno else [0.22, 0.30, 0.13], dtype=np.float32)
        trozos.append(P)
        colores.append(np.clip(base + rng.normal(0, 0.04, (len(P), 3)), 0, 1))
    P = np.concatenate(trozos) if trozos else np.zeros((0, 3), np.float32)
    C = np.concatenate(colores) if colores else np.zeros((0, 3), np.float32)
    if len(P) > tope:
        sel = np.random.default_rng(7).choice(len(P), tope, replace=False)
        P, C = P[sel], C[sel]
    escribir_ply_puntos(ruta, P, C)
    return len(P)


def escribir_ply_puntos(ruta, P, C):
    cab = ("ply\nformat binary_little_endian 1.0\n"
           f"element vertex {len(P)}\n"
           "property float x\nproperty float y\nproperty float z\n"
           "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n")
    reg = np.zeros(len(P), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"), ("r", "u1"), ("g", "u1"), ("b", "u1")])
    reg["x"], reg["y"], reg["z"] = P[:, 0], P[:, 1], P[:, 2]
    c8 = np.clip(C * 255 + 0.5, 0, 255).astype(np.uint8)
    reg["r"], reg["g"], reg["b"] = c8[:, 0], c8[:, 1], c8[:, 2]
    with open(ruta, "wb") as f:
        f.write(cab.encode("ascii"))
        f.write(reg.tobytes())


def intrinsecos(ancho, alto, fov_h):
    fl = (ancho / 2) / math.tan(math.radians(fov_h) / 2)
    return dict(camera_model="OPENCV", w=ancho, h=alto, fl_x=fl, fl_y=fl, cx=ancho / 2, cy=alto / 2,
                camera_angle_x=math.radians(fov_h), k1=0.0, k2=0.0, p1=0.0, p2=0.0)


def preparar_camara(cam, ancho, alto, fov_h):
    esc = bpy.context.scene
    esc.render.resolution_x, esc.render.resolution_y = ancho, alto
    esc.render.resolution_percentage = 100
    esc.render.pixel_aspect_x = esc.render.pixel_aspect_y = 1
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36.0
    cam.data.lens = 18.0 / math.tan(math.radians(fov_h) / 2)
    cam.data.shift_x = cam.data.shift_y = 0.0
    cam.data.dof.use_dof = False            # el splat necesita todo nítido
    cam.data.clip_start = 0.05
    cam.animation_data_clear()
    esc.render.use_motion_blur = False


def main():
    a = argumentos()
    n_def, ancho, alto, muestras = CALIDADES[a.calidad]
    n = a.vistas or n_def
    carpeta = os.path.join(os.path.abspath(a.salida), a.capitulo)
    os.makedirs(os.path.join(carpeta, "images"), exist_ok=True)
    rng = random.Random(a.semilla)

    # la escena del capítulo, armada por el mismo código que los renders de Cycles
    ns = argparse.Namespace(calidad="prueba" if a.calidad == "prueba" else "media", salida=os.path.join(carpeta, "_escena"),
                            assets=a.assets, modelos=a.modelos, segundos=1.0, animar=False)
    arm = T.armar_capitulo(a.capitulo, ns, para_splats=True)
    cap, cam = arm["cap"], arm["camara"]
    esc = bpy.context.scene
    esc.cycles.samples = muestras
    esc.render.film_transparent = True       # cielo y lejanía transparentes: el splat aprende lo cercano
    esc.render.image_settings.file_format = "PNG"
    esc.render.image_settings.color_mode = "RGBA"
    esc.render.image_settings.color_depth = "8"
    esc.view_layers[0].use_pass_mist = False
    preparar_camara(cam, ancho, alto, a.fov)

    lista, desde, hasta, largo = poses(cap, n, rng)
    intr = intrinsecos(ancho, alto, a.fov)
    cuadros, prueba = [], []
    t0 = time.time()
    for i, (p, q) in enumerate(lista):
        cam.location = p
        cam.rotation_mode = "QUATERNION"
        cam.rotation_quaternion = q
        bpy.context.view_layer.update()
        nombre = f"images/{i:04d}.png"
        esc.render.filepath = os.path.join(carpeta, nombre)
        bpy.ops.render.render(write_still=True)
        # la matriz de mundo de una cámara de Blender ya es la convención de NeRF/OpenGL
        # (cámara mirando a -Z, arriba +Y): va tal cual
        cuadro = {"file_path": nombre, "transform_matrix": [list(map(float, fila)) for fila in cam.matrix_world]}
        (prueba if i % 12 == 11 else cuadros).append(cuadro)
        if i % 10 == 0:
            print(f"   vista {i + 1}/{len(lista)} · {time.time() - t0:.0f} s", flush=True)

    n_puntos = nube_inicial(os.path.join(carpeta, "puntos_iniciales.ply"), desde, hasta, a.radio, np.random.default_rng(3))
    base = dict(intr, ply_file_path="puntos_iniciales.ply")
    with open(os.path.join(carpeta, "transforms.json"), "w") as f:
        json.dump(dict(base, frames=cuadros), f, indent=1)
    with open(os.path.join(carpeta, "transforms_test.json"), "w") as f:
        json.dump(dict(base, frames=prueba), f, indent=1)
    with open(os.path.join(carpeta, "region.json"), "w", encoding="utf-8") as f:
        json.dump({
            "capitulo": a.capitulo,
            "desde_blender": list(desde), "hasta_blender": list(hasta), "radio_m": a.radio,
            "vistas": len(lista), "resolucion": [ancho, alto], "muestras": muestras, "fov_h": a.fov,
            "sol": cap["sol"], "exposicion": cap.get("exposicion", -0.8),
            "a_unity": "posición Unity = (x, z, y) de Blender: rotación (-90, 0, 0), escala (1, -1, 1)",
            "a_web": "posición three.js = (x, z, -y) de Blender: rotación x = -90°",
        }, f, indent=1, ensure_ascii=False)
    print(f"listo: {len(lista)} vistas ({len(prueba)} de prueba), {n_puntos} puntos iniciales, "
          f"{time.time() - t0:.0f} s → {carpeta}", flush=True)


if __name__ == "__main__":
    main()
