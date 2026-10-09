"""
Vista de control del capítulo "hoy" (el Valle de la Luna real) en Cycles, con los MISMOS datos que
usa Unity: alturas de Datos/valle, capas de suelo, texturas de Datos/suelo con el tinte del satélite
y el paredón. Sirve para revisar el relieve, la cámara y los colores desde la nube (sin Unity).

    python3 vista_valle.py SALIDA.jpg [--ancho 1600 --alto 900 --muestras 48]
"""
import argparse
import gzip
import json
import math
import os
import sys

import bpy
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "..", "ParqueTriasico", "Datos")


def alturas(t, paso):
    r = np.frombuffer(gzip.open(os.path.join(DATOS, t["alturas"])).read(), dtype="<u2").reshape(t["res"], t["res"]).astype(np.int64)
    a = np.cumsum(np.cumsum(r, 0), 1) % 65536
    h = a / 65535 * (t["hmax"] - t["hmin"]) + t["hmin"]
    return h[::paso, ::paso]


def malla_terreno(nombre, t, paso):
    h = alturas(t, paso)
    n = h.shape[0]
    d = t["lado"] / (t["res"] - 1) * paso
    xs = t["x0"] + np.arange(n) * d
    zs = t["z0"] + np.arange(n) * d
    X, Z = np.meshgrid(xs, zs)
    # Unity (x este, y arriba, z norte) → Blender (x, y = z de Unity, z = y de Unity)
    verts = np.stack([X.ravel(), Z.ravel(), h.ravel()], 1)
    i = np.arange(n - 1)
    I, J = np.meshgrid(i, i)
    a = (J * n + I).ravel()
    caras = np.stack([a, a + 1, a + n + 1, a + n], 1)
    me = bpy.data.meshes.new(nombre)
    me.vertices.add(len(verts))
    me.vertices.foreach_set("co", verts.astype(np.float32).ravel())
    me.loops.add(len(caras) * 4)
    me.loops.foreach_set("vertex_index", caras.ravel())
    me.polygons.add(len(caras))
    me.polygons.foreach_set("loop_start", np.arange(0, len(caras) * 4, 4))
    me.polygons.foreach_set("loop_total", np.full(len(caras), 4))
    uv = me.uv_layers.new(name="uv")
    u = ((verts[:, 0] - t["x0"]) / t["lado"])
    v = ((verts[:, 1] - t["z0"]) / t["lado"])
    uv.data.foreach_set("uv", np.stack([u, v], 1)[caras.ravel()].astype(np.float32).ravel())
    me.update()
    me.polygons.foreach_set("use_smooth", np.ones(len(caras), bool))
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def nodo(nt, tipo, **kw):
    n = nt.nodes.new(tipo)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def imagen(ruta, datos=False):
    im = bpy.data.images.load(ruta, check_existing=True)
    if datos:
        im.colorspace_settings.name = "Non-Color"
    return im


def material_suelo(t, paleta, capas_info):
    m = bpy.data.materials.new("suelo_" + t["nombre"])
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tc = nodo(nt, "ShaderNodeTexCoord")
    splat = nodo(nt, "ShaderNodeTexImage", image=imagen(os.path.join(DATOS, t["capas_png"][0]), True), interpolation="Linear")
    uvmap = nodo(nt, "ShaderNodeUVMap", uv_map="uv")
    nt.links.new(uvmap.outputs[0], splat.inputs[0])
    sep = nodo(nt, "ShaderNodeSeparateColor")
    nt.links.new(splat.outputs["Color"], sep.inputs[0])
    canales = [sep.outputs[0], sep.outputs[1], sep.outputs[2], splat.outputs["Alpha"]]
    color_acc = rug_acc = nor_acc = None
    for k, capa in enumerate(t["capas"]):
        metros = capas_info.get(capa, 3.0)
        mp = nodo(nt, "ShaderNodeMapping")
        mp.inputs["Scale"].default_value = (1 / metros, 1 / metros, 1)
        nt.links.new(tc.outputs["Object"], mp.inputs[0])
        col = nodo(nt, "ShaderNodeTexImage", image=imagen(os.path.join(DATOS, "suelo", f"{capa}_color.jpg")))
        hra = nodo(nt, "ShaderNodeTexImage", image=imagen(os.path.join(DATOS, "suelo", f"{capa}_hra.jpg"), True))
        nor = nodo(nt, "ShaderNodeTexImage", image=imagen(os.path.join(DATOS, "suelo", f"{capa}_normal.jpg"), True))
        for x in (col, hra, nor):
            nt.links.new(mp.outputs[0], x.inputs[0])
        # tinte para igualar el albedo medido en el satélite (lo mismo que hace el constructor de Unity)
        tinte = nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
        tinte.inputs["Factor"].default_value = 1.0
        nt.links.new(col.outputs["Color"], tinte.inputs[6])
        objetivo = paleta.get(capa)
        media = capas_info.get(capa + "_media", (0.3, 0.3, 0.3))
        f = [min(2.0, max(0.3, objetivo[i] / max(0.02, media[i]))) for i in range(3)] if objetivo else [1, 1, 1]
        tinte.inputs[7].default_value = (*f, 1)
        sep_h = nodo(nt, "ShaderNodeSeparateColor")
        nt.links.new(hra.outputs["Color"], sep_h.inputs[0])
        w = canales[k]
        def acumular(acc, valor, es_color):
            if acc is None:
                m_ = nodo(nt, "ShaderNodeMix", data_type="RGBA" if es_color else "FLOAT")
                m_.inputs["Factor"].default_value = 1.0
                if es_color:
                    m_.inputs[6].default_value = (0, 0, 0, 1)
                    nt.links.new(valor, m_.inputs[7])
                else:
                    m_.inputs[2].default_value = 0
                    nt.links.new(valor, m_.inputs[3])
                nt.links.new(w, m_.inputs["Factor"])
                return m_
            m_ = nodo(nt, "ShaderNodeMix", data_type="RGBA" if es_color else "FLOAT")
            nt.links.new(w, m_.inputs["Factor"])
            if es_color:
                nt.links.new(acc.outputs[2], m_.inputs[6])
                nt.links.new(valor, m_.inputs[7])
            else:
                nt.links.new(acc.outputs[0], m_.inputs[2])
                nt.links.new(valor, m_.inputs[3])
            return m_
        color_acc = acumular(color_acc, tinte.outputs[2], True)
        rug_acc = acumular(rug_acc, sep_h.outputs[2], False)
        nor_acc = acumular(nor_acc, nor.outputs["Color"], True)
    nt.links.new(color_acc.outputs[2], bs.inputs["Base Color"])
    nt.links.new(rug_acc.outputs[0], bs.inputs["Roughness"])
    nm = nodo(nt, "ShaderNodeNormalMap")
    nt.links.new(nor_acc.outputs[2], nm.inputs["Color"])
    nt.links.new(nm.outputs[0], bs.inputs["Normal"])
    return m


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--ancho", type=int, default=1600)
    ap.add_argument("--alto", type=int, default=900)
    ap.add_argument("--muestras", type=int, default=48)
    ap.add_argument("--fov", type=float, default=55.0, help="campo horizontal en grados")
    a = ap.parse_args(argv)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mundo = json.load(open(os.path.join(DATOS, "mundo.json"), encoding="utf-8"))
    valle = json.load(open(os.path.join(DATOS, "valle_real.json"), encoding="utf-8"))
    capas_info = {c["nombre"]: c["mundo_m"] for c in json.load(open(os.path.join(DATOS, "suelo", "capas.json")))["capas"]}
    # color medio (lineal) de cada textura, para el tinte del satélite
    for capa in ("arcilla_gris", "arcilla_clara", "estratos", "ripio"):
        im = imagen(os.path.join(DATOS, "suelo", f"{capa}_color.jpg"))
        px = np.array(im.pixels[:], np.float32).reshape(-1, 4)[::97, :3]
        capas_info[capa + "_media"] = tuple(px.mean(0))       # Blender ya da los píxeles en lineal
    paleta = valle["paleta_albedo_lineal"]
    for t in mundo["terrenos"]:
        if t["era"] != "hoy":
            continue
        ob = malla_terreno(t["nombre"], t, 2 if t["cual"] == "cerca" else 4)
        ob.data.materials.append(material_suelo(t, paleta, capas_info))
    # paredón
    p = json.loads(gzip.open(os.path.join(DATOS, "valle", "paredon.json.gz"), "rt").read())
    v = np.array(p["vertices"], np.float32).reshape(-1, 3)[:, [0, 2, 1]]
    tri = np.array(p["triangulos"], np.int64).reshape(-1, 3)[:, ::-1]   # el cambio de mano invierte el giro
    me = bpy.data.meshes.new("paredon")
    me.from_pydata(v.tolist(), [], tri.tolist())
    me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new("paredon", me)
    bpy.context.scene.collection.objects.link(ob)
    m = bpy.data.materials.new("estratos")
    m.use_nodes = True
    nt = m.node_tree
    tc = nodo(nt, "ShaderNodeTexCoord")
    mp = nodo(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (1 / 18, 1 / 18, 1 / 18)
    nt.links.new(tc.outputs["Object"], mp.inputs[0])
    col = nodo(nt, "ShaderNodeTexImage", image=imagen(os.path.join(DATOS, "suelo", "estratos_color.jpg")), projection="BOX", projection_blend=0.3)
    nt.links.new(mp.outputs[0], col.inputs[0])
    tinte = nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    tinte.inputs["Factor"].default_value = 1
    f = [min(2, max(0.3, paleta["estratos"][i] / max(0.02, capas_info["estratos_media"][i]))) for i in range(3)]
    tinte.inputs[7].default_value = (*f, 1)
    nt.links.new(col.outputs["Color"], tinte.inputs[6])
    nt.links.new(tinte.outputs[2], nt.nodes["Principled BSDF"].inputs["Base Color"])
    nt.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
    ob.data.materials.append(m)

    # cielo y sol de la tarde (los del capítulo "hoy")
    esc = bpy.context.scene
    w = bpy.data.worlds.new("cielo")
    esc.world = w
    w.use_nodes = True
    sky = nodo(w.node_tree, "ShaderNodeTexSky")
    for tipo in ("MULTIPLE_SCATTERING", "NISHITA"):
        try:
            sky.sky_type = tipo
            break
        except TypeError:
            pass
    hs = valle["sol_hoy"]["hacia_sol"]
    dir_b = np.array([hs[0], hs[2], hs[1]])
    elev = math.asin(dir_b[2])
    azim = math.atan2(dir_b[1], dir_b[0])
    sky.sun_elevation, sky.sun_rotation = elev, azim
    sky.sun_disc = False
    try:
        sky.aerosol_density = 0.4
    except AttributeError:
        pass
    w.node_tree.links.new(sky.outputs[0], w.node_tree.nodes["Background"].inputs[0])
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.15
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = 5.5
    sol.data.angle = math.radians(0.53)
    sol.data.color = (1.0, 0.9, 0.78)
    from mathutils import Vector
    sol.rotation_euler = (-Vector(dir_b.tolist())).to_track_quat("-Z", "Y").to_euler()
    esc.collection.objects.link(sol)

    cap = [c for c in mundo["capitulos"] if c["clave"] == "hoy"][0]
    d, mi = cap["desde"], cap["mira"]
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    esc.collection.objects.link(cam)
    cam.location = (d[0], d[2], d[1])
    cam.rotation_euler = (Vector((mi[0], mi[2], mi[1])) - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.angle = math.radians(a.fov)
    cam.data.clip_end = 12000
    esc.camera = cam
    esc.render.engine = "CYCLES"
    esc.cycles.samples = a.muestras
    esc.cycles.use_denoising = True
    esc.render.resolution_x, esc.render.resolution_y = a.ancho, a.alto
    esc.view_settings.view_transform = "AgX"
    esc.view_settings.exposure = -0.6
    esc.render.image_settings.file_format = "JPEG"
    esc.render.filepath = a.salida
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
