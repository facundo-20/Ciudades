"""
El Triásico de San Juan (Formación Ischigualasto, Carniano, ~231 millones de años):
flora, terrenos y escenas, modelados y con TEXTURAS HORNEADAS A 2K, listos para interacción
en TouchDesigner, Unreal, three.js o cualquier motor, en FBX y GLB.

    blender -b --factory-startup -P construir_triasico.py -- SALIDA [--solo assets|escenas|<nombre>] [--res 2048]
    (o con el módulo bpy de pip:  python3 construir_triasico.py -- SALIDA)

Por qué hornear: los materiales procedurales de Blender (nodos de ruido, Voronoi, etc.) NO
viajan en FBX ni GLB; el motor recibe una malla gris. Horneando color, rugosidad y normal a
imágenes de 2K, el modelo se ve igual en cualquier lado.

Qué sale en SALIDA/:
  assets/<planta>/<planta>_{alto,medio,bajo}.{glb,fbx} + texturas 2K + vista.png
  escenas/<escena>/<escena>.{glb,fbx,blend} + terreno horneado 2K + vista.png
  Cada escena trae PUNTOS DE DINOSAURIOS (empties "SLOT_<especie>_<n>", con posición y hacia
  dónde mira). meshy_a_escenas.py (en la Mac) pone ahí los dinosaurios de Meshy.

Rigor científico (a validar con un paleontólogo de la UNSJ antes de la fiesta):
  · Clima estacional, ríos meandrosos y llanuras de inundación, lluvia de ceniza volcánica
    (las capas de toba de Ischigualasto son las que dan la edad de 231 millones de años).
  · Flora: Dicroidium (pteridosperma de frondas bifurcadas, la planta que domina la formación),
    coníferas, Neocalamites (equisetal, "cola de caballo" gigante), helechos (Cladophlebis).
  · NO HAY PASTO: las gramíneas aparecen más de 150 millones de años después. El suelo es
    barro, arena, hojarasca y helechos. Es el error más común en las recreaciones.
"""

import argparse
import math
import os
import random
import sys

import bpy
import bmesh  # noqa: E402  (después de bpy: con el bpy de pip, bmesh existe cuando bpy cargó)
from mathutils import Matrix, Vector, noise

RES = 2048
AZAR = random.Random(231)          # 231 millones de años: la semilla de todo

# paleta (verdes oliva y azulados: la flora mesozoica no tenía el verde brillante del pasto)
VERDE_DICROIDIUM = (0.20, 0.27, 0.10)
VERDE_OSCURO = (0.10, 0.16, 0.07)
VERDE_EQUISETO = (0.28, 0.33, 0.14)
CORTEZA = (0.22, 0.15, 0.10)
CORTEZA_CLARA = (0.36, 0.28, 0.20)
BARRO = (0.20, 0.15, 0.11)
BARRO_HUMEDO = (0.11, 0.08, 0.06)
ARENA = (0.55, 0.45, 0.33)
CENIZA = (0.52, 0.51, 0.49)
ARENISCA = (0.58, 0.40, 0.28)


# =========================================================================================
# utilidades
# =========================================================================================

def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--solo", nargs="*", help="assets, escenas, o nombres puntuales")
    ap.add_argument("--res", type=int, default=2048, help="resolución de las texturas horneadas")
    ap.add_argument("--muestras-vista", type=int, default=24)
    return ap.parse_args(argv)


def limpiar():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def fbm(p, octavas=5, escala=1.0):
    t, a, f, n = 0.0, 1.0, escala, 0.0
    for _ in range(octavas):
        t += a * noise.noise(p * f)
        n += a
        a *= 0.5
        f *= 2.03
    return t / n


def objeto_desde_bmesh(nombre, bm):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def marco(direccion):
    """Dos vectores perpendiculares a una dirección (para armar tubos y hojas)."""
    d = direccion.normalized()
    ref = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    u = d.cross(ref).normalized()
    v = d.cross(u).normalized()
    return u, v


def tubo(bm, puntos, radios, lados=8, mat=0):
    """Tubo por una polilínea (troncos, ramas, tallos). Cierra la punta."""
    anillos = []
    for i, p in enumerate(puntos):
        d = (puntos[min(i + 1, len(puntos) - 1)] - puntos[max(i - 1, 0)])
        u, v = marco(d if d.length > 1e-6 else Vector((0, 0, 1)))
        r = radios[i]
        anillos.append([bm.verts.new(p + (u * math.cos(a) + v * math.sin(a)) * r)
                        for a in (2 * math.pi * k / lados for k in range(lados))])
    caras = []
    for i in range(len(anillos) - 1):
        for k in range(lados):
            k2 = (k + 1) % lados
            caras.append(bm.faces.new((anillos[i][k], anillos[i][k2], anillos[i + 1][k2], anillos[i + 1][k])))
    punta = bm.verts.new(puntos[-1] + (puntos[-1] - puntos[-2]).normalized() * radios[-1] * 0.5)
    for k in range(lados):
        caras.append(bm.faces.new((anillos[-1][k], anillos[-1][(k + 1) % lados], punta)))
    for f in caras:
        f.material_index = mat
    return caras


def hoja(bm, base, direccion, largo, ancho, normal_aprox, mat=0, curva=0.25):
    """Una hoja/pinna: rombo alargado con nervadura central doblada (6 vértices)."""
    d = direccion.normalized()
    lado = d.cross(normal_aprox).normalized()
    if lado.length < 1e-6:
        lado, _ = marco(d)
    arriba = lado.cross(d).normalized()
    punta = base + d * largo + arriba * (-curva * largo)
    medio = base + d * largo * 0.45
    vs = [bm.verts.new(base),
          bm.verts.new(medio + lado * ancho * 0.5 + arriba * ancho * 0.15),
          bm.verts.new(medio + arriba * ancho * 0.05),
          bm.verts.new(medio - lado * ancho * 0.5 + arriba * ancho * 0.15),
          bm.verts.new(punta)]
    caras = [bm.faces.new((vs[0], vs[1], vs[2])), bm.faces.new((vs[0], vs[2], vs[3])),
             bm.faces.new((vs[1], vs[4], vs[2])), bm.faces.new((vs[2], vs[4], vs[3]))]
    for f in caras:
        f.material_index = mat
    return caras


def curva_rama(origen, direccion, largo, segmentos, caida=0.3, torsion=0.2, semilla=0.0):
    """Polilínea que se curva hacia abajo (gravedad) con un poco de ruido."""
    pts = [origen.copy()]
    d = direccion.normalized()
    paso = largo / segmentos
    for i in range(segmentos):
        n = Vector((noise.noise(Vector((semilla, i * 0.7, 0))), noise.noise(Vector((i * 0.7, semilla, 1))), 0))
        d = (d + Vector((0, 0, -caida / segmentos)) + n * torsion / segmentos).normalized()
        pts.append(pts[-1] + d * paso)
    return pts


# =========================================================================================
# materiales procedurales (se hornean después)
# =========================================================================================

def mat_proc(nombre, c1, c2, escala=4.0, grietas=0.0, rug=0.8, bump=0.3, bandas_z=0.0, atributo=None):
    """Material genérico: dos colores mezclados por ruido, opcional grietas (corteza) y
    bandas por altura (nudos del equiseto). `atributo` = color de vértice que manda la mezcla."""
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bs = n.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = rug
    l.new(bs.outputs[0], out.inputs["Surface"])
    tc = n.new("ShaderNodeTexCoord")
    rui = n.new("ShaderNodeTexNoise")
    rui.inputs["Scale"].default_value = escala
    rui.inputs["Detail"].default_value = 8
    l.new(tc.outputs["Object"], rui.inputs["Vector"])
    fac = rui.outputs[0]
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*c1, 1)
    mix.inputs["B"].default_value = (*c2, 1)
    l.new(fac, mix.inputs["Factor"])
    color = mix.outputs["Result"]
    alto = fac
    if grietas:
        vor = n.new("ShaderNodeTexVoronoi"); vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = grietas
        esc = n.new("ShaderNodeMapping")
        esc.inputs["Scale"].default_value = (1.0, 1.0, 0.25)      # grietas alargadas a lo largo
        l.new(tc.outputs["Object"], esc.inputs["Vector"])
        l.new(esc.outputs[0], vor.inputs["Vector"])
        rng = n.new("ShaderNodeMapRange")
        rng.inputs["From Max"].default_value = 0.08
        l.new(vor.outputs["Distance"], rng.inputs["Value"])
        osc = n.new("ShaderNodeMix"); osc.data_type = "RGBA"; osc.blend_type = "MULTIPLY"
        l.new(rng.outputs[0], osc.inputs["Factor"])
        osc.inputs["Factor"].default_value = 1
        rgb = n.new("ShaderNodeCombineColor")
        l.new(rng.outputs[0], rgb.inputs[0]); l.new(rng.outputs[0], rgb.inputs[1]); l.new(rng.outputs[0], rgb.inputs[2])
        l.new(color, osc.inputs["A"]); l.new(rgb.outputs[0], osc.inputs["B"])
        color = osc.outputs["Result"]
        alto = rng.outputs[0]
    if bandas_z:
        sep = n.new("ShaderNodeSeparateXYZ"); l.new(tc.outputs["Object"], sep.inputs[0])
        mul = n.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = bandas_z
        l.new(sep.outputs["Z"], mul.inputs[0])
        fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; l.new(mul.outputs[0], fr.inputs[0])
        nudo = n.new("ShaderNodeMapRange")
        nudo.inputs["From Min"].default_value, nudo.inputs["From Max"].default_value = 0.0, 0.08
        l.new(fr.outputs[0], nudo.inputs["Value"])
        osc = n.new("ShaderNodeMix"); osc.data_type = "RGBA"
        osc.inputs["A"].default_value = (0.08, 0.07, 0.04, 1)
        l.new(nudo.outputs[0], osc.inputs["Factor"])
        l.new(color, osc.inputs["B"])
        color = osc.outputs["Result"]
    if atributo:
        at = n.new("ShaderNodeVertexColor"); at.layer_name = atributo
        sep = n.new("ShaderNodeSeparateColor"); l.new(at.outputs["Color"], sep.inputs[0])
        # R = humedad (barro húmedo), G = arena, B = cobertura vegetal (hojarasca y helechos)
        hum = n.new("ShaderNodeMix"); hum.data_type = "RGBA"
        l.new(sep.outputs[0], hum.inputs["Factor"])
        l.new(color, hum.inputs["A"]); hum.inputs["B"].default_value = (*BARRO_HUMEDO, 1)
        are = n.new("ShaderNodeMix"); are.data_type = "RGBA"
        l.new(sep.outputs[1], are.inputs["Factor"])
        l.new(hum.outputs["Result"], are.inputs["A"]); are.inputs["B"].default_value = (*ARENA, 1)
        veg = n.new("ShaderNodeMix"); veg.data_type = "RGBA"
        l.new(sep.outputs[2], veg.inputs["Factor"])
        l.new(are.outputs["Result"], veg.inputs["A"])
        hojarasca = n.new("ShaderNodeTexVoronoi"); hojarasca.inputs["Scale"].default_value = 40
        l.new(tc.outputs["Object"], hojarasca.inputs["Vector"])
        hmix = n.new("ShaderNodeMix"); hmix.data_type = "RGBA"
        hmix.inputs["A"].default_value = (*VERDE_OSCURO, 1)
        hmix.inputs["B"].default_value = (0.25, 0.20, 0.10, 1)     # hojarasca seca
        l.new(hojarasca.outputs["Distance"], hmix.inputs["Factor"])
        l.new(hmix.outputs["Result"], veg.inputs["B"])
        color = veg.outputs["Result"]
        rug_n = n.new("ShaderNodeMapRange")
        rug_n.inputs["To Min"].default_value, rug_n.inputs["To Max"].default_value = rug, 0.35
        l.new(sep.outputs[0], rug_n.inputs["Value"])
        l.new(rug_n.outputs[0], bs.inputs["Roughness"])
    l.new(color, bs.inputs["Base Color"])
    b = n.new("ShaderNodeBump"); b.inputs["Strength"].default_value = bump
    l.new(alto, b.inputs["Height"])
    l.new(b.outputs["Normal"], bs.inputs["Normal"])
    return m


MATS = {}


def mats():
    if not MATS:
        MATS.update({
            "corteza": mat_proc("corteza", CORTEZA, CORTEZA_CLARA, escala=6, grietas=8, bump=0.6, rug=0.9),
            "hoja": mat_proc("hoja", VERDE_DICROIDIUM, VERDE_OSCURO, escala=9, rug=0.55, bump=0.1),
            "aguja": mat_proc("aguja", (0.12, 0.20, 0.10), (0.07, 0.12, 0.06), escala=12, rug=0.6, bump=0.2),
            "equiseto": mat_proc("equiseto", VERDE_EQUISETO, (0.20, 0.25, 0.10), escala=5, rug=0.5, bandas_z=2.5),
            "helecho": mat_proc("helecho", (0.18, 0.28, 0.09), (0.12, 0.19, 0.06), escala=10, rug=0.55),
            "tronco": mat_proc("tronco", (0.30, 0.26, 0.22), (0.18, 0.14, 0.11), escala=5, grietas=6, bump=0.7),
            "roca": mat_proc("roca", ARENISCA, (0.45, 0.32, 0.24), escala=3, bump=0.8, rug=0.92),
            "quemado": mat_proc("quemado", (0.06, 0.05, 0.05), (0.14, 0.12, 0.11), escala=6, grietas=8, bump=0.6),
        })
    return MATS


# =========================================================================================
# flora
# =========================================================================================

def asignar_mats(ob, nombres):
    # sin materials.clear(): vaciar la lista pone todas las caras en el índice 0 y las hojas
    # quedaban con la corteza (probado). La malla recién hecha no tiene materiales.
    for nm in nombres:
        ob.data.materials.append(mats()[nm])


def planta_dicroidium(semilla=0, alto=6.0, quemado=False):
    """Dicroidium: tronco con copa de frondas que se BIFURCAN en Y (el rasgo que lo identifica)."""
    r = random.Random(semilla)
    bm = bmesh.new()
    tronco = [Vector((0, 0, 0))]
    for i in range(1, 7):
        tronco.append(Vector((fbm(Vector((i, semilla, 0)), 2) * 0.3, fbm(Vector((semilla, i, 0)), 2) * 0.3,
                              alto * 0.72 * i / 6)))
    tubo(bm, tronco, [0.26 - 0.03 * i for i in range(7)], 10, mat=0)
    copa = tronco[-1]
    n_ramas = 14
    for k in range(n_ramas):
        a = 2 * math.pi * k / n_ramas + r.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), r.uniform(0.4, 1.1)))
        rama = curva_rama(copa, d, r.uniform(1.8, 2.6), 6, caida=0.9, torsion=0.3, semilla=k + semilla)
        tubo(bm, rama, [0.07 - 0.012 * i for i in range(len(rama))], 6, mat=0)
        if quemado:
            continue
        # frondas: del extremo y de dos puntos de la rama, cada una se bifurca
        for base_i in (2, 3, 4, 5, 6):
            b = rama[base_i]
            dir_b = (rama[min(base_i + 1, len(rama) - 1)] - rama[base_i - 1]).normalized()
            for lado in (-1, 1):
                u, _ = marco(dir_b)
                d_fork = (dir_b + u * 0.55 * lado + Vector((0, 0, -0.15))).normalized()
                raquis = curva_rama(b, d_fork, r.uniform(0.9, 1.4), 8, caida=0.8, semilla=semilla + k * 3 + lado + base_i)
                tubo(bm, raquis, [0.012] * len(raquis), 4, mat=1)
                for j in range(1, len(raquis)):
                    p = raquis[j]
                    dj = (raquis[j] - raquis[j - 1]).normalized()
                    uu, vv = marco(dj)
                    for s in (-1, 1):
                        hoja(bm, p, (uu * s + dj * 0.4).normalized(), 0.22 - j * 0.015, 0.075, vv, mat=1, curva=0.2)
    ob = objeto_desde_bmesh("dicroidium_quemado" if quemado else "dicroidium", bm)
    asignar_mats(ob, ["quemado" if quemado else "corteza", "hoja"])
    return ob


def planta_conifera(semilla=0, alto=12.0):
    """Conífera triásica: tronco recto, verticilos de ramas y follaje en masas (no pino actual)."""
    r = random.Random(semilla)
    bm = bmesh.new()
    tronco = [Vector((0, 0, alto * i / 8)) for i in range(9)]
    tubo(bm, tronco, [0.38 * (1 - i / 9) + 0.04 for i in range(9)], 12, mat=0)
    for piso in range(9):
        z = alto * (0.35 + 0.62 * piso / 9)
        largo = (1.0 - piso / 10) * 2.6 + 0.4
        for k in range(5):
            a = 2 * math.pi * k / 5 + piso * 0.7 + r.uniform(-0.3, 0.3)
            d = Vector((math.cos(a), math.sin(a), 0.25))
            rama = curva_rama(Vector((0, 0, z)), d, largo, 4, caida=0.6, semilla=piso * 7 + k)
            tubo(bm, rama, [0.06, 0.05, 0.04, 0.03, 0.02], 5, mat=0)
            for p in rama[1:]:
                # masa de follaje: icoesfera deformada (miles de agujas leídas como volumen)
                res = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.45 * (1 - piso / 14))
                for v in res["verts"]:
                    v.co = v.co * Vector((1.3, 1.3, 0.6)) + p
                    v.co += v.co.normalized() * 0 + Vector((0, 0, 0))
                for f in {f for v in res["verts"] for f in v.link_faces}:
                    f.material_index = 1
    ob = objeto_desde_bmesh("conifera", bm)
    asignar_mats(ob, ["corteza", "aguja"])
    rugosear(ob, 0.08, 3.0, solo_mat=1)
    return ob


def planta_neocalamites(semilla=0):
    """Neocalamites: mata de tallos articulados de 2–3 m con verticilos de hojas finas en los nudos."""
    r = random.Random(semilla)
    bm = bmesh.new()
    for t in range(16):
        base = Vector((r.gauss(0, 0.35), r.gauss(0, 0.35), 0))
        alto = r.uniform(1.6, 3.0)
        d = Vector((base.x * 0.3, base.y * 0.3, 1)).normalized()
        tallo = curva_rama(base, d, alto, 8, caida=-0.1, torsion=0.15, semilla=t + semilla)
        tubo(bm, tallo, [0.035] * len(tallo), 6, mat=0)
        for j in range(1, len(tallo) - 1):
            p = tallo[j]
            for k in range(10):
                a = 2 * math.pi * k / 10
                dir_h = Vector((math.cos(a), math.sin(a), 0.35)).normalized()
                hoja(bm, p, dir_h, 0.22 - j * 0.015, 0.012, Vector((0, 0, 1)), mat=0, curva=0.35)
    ob = objeto_desde_bmesh("neocalamites", bm)
    asignar_mats(ob, ["equiseto"])
    return ob


def planta_helecho(semilla=0):
    """Helecho (tipo Cladophlebis): roseta de frondas arqueadas con pinnas."""
    r = random.Random(semilla)
    bm = bmesh.new()
    for k in range(13):
        a = 2 * math.pi * k / 13 + r.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), r.uniform(1.2, 2.2)))
        fr = curva_rama(Vector((0, 0, 0.05)), d, r.uniform(0.8, 1.3), 10, caida=2.2, semilla=k + semilla)
        tubo(bm, fr, [0.01] * len(fr), 4, mat=0)
        for j in range(1, len(fr)):
            dj = (fr[j] - fr[j - 1]).normalized()
            u, v = marco(dj)
            for s in (-1, 1):
                largo = 0.16 * math.sin(math.pi * j / len(fr)) + 0.03
                hoja(bm, fr[j], (u * s + dj * 0.3).normalized(), largo, 0.035, v, mat=0, curva=0.15)
    ob = objeto_desde_bmesh("helecho", bm)
    asignar_mats(ob, ["helecho"])
    return ob


def tronco_caido(semilla=0):
    bm = bmesh.new()
    pts = [Vector((x, fbm(Vector((x, semilla, 0)), 2) * 0.3, 0.32)) for x in [i * 0.6 - 3 for i in range(11)]]
    tubo(bm, pts, [0.35 - 0.012 * i for i in range(11)], 14, mat=0)
    ob = objeto_desde_bmesh("tronco_caido", bm)
    asignar_mats(ob, ["tronco"])
    rugosear(ob, 0.05, 2.5)
    return ob


def roca(semilla=0):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=0.6)
    ob = objeto_desde_bmesh("roca_arenisca", bm)
    ob.data.transform(Matrix.Diagonal((1.4, 1.0, 0.7, 1)))
    asignar_mats(ob, ["roca"])
    rugosear(ob, 0.18, 1.6)
    return ob


def rugosear(ob, fuerza, escala, solo_mat=None):
    me = ob.data
    idx = None
    if solo_mat is not None:
        idx = {v for p in me.polygons if p.material_index == solo_mat for v in p.vertices}
    for v in me.vertices:
        if idx is not None and v.index not in idx:
            continue
        v.co += v.normal * fbm(Vector(v.co) * 1.0, 4, escala) * fuerza


FLORA = {
    "dicroidium": lambda: planta_dicroidium(1),
    "dicroidium_quemado": lambda: planta_dicroidium(2, quemado=True),
    "conifera": lambda: planta_conifera(3),
    "neocalamites": lambda: planta_neocalamites(4),
    "helecho": lambda: planta_helecho(5),
    "tronco_caido": lambda: tronco_caido(6),
    "roca_arenisca": lambda: roca(7),
}
TOPES = {"alto": 1.0, "medio": 0.4, "bajo": 0.12}   # fracción de triángulos por nivel


# =========================================================================================
# horneado a 2K y exportación
# =========================================================================================

def preparar_cycles(muestras=4):
    esc = bpy.context.scene
    esc.render.engine = "CYCLES"
    esc.cycles.device = "GPU" if os.environ.get("FNS_GPU") else "CPU"
    esc.cycles.samples = muestras
    esc.render.bake.margin = 8


def uv(ob):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004)
    bpy.ops.object.mode_set(mode="OBJECT")


def hornear(ob, carpeta, res):
    """Hornea color, rugosidad y normal de TODOS los materiales del objeto a 3 imágenes de
    res×res y le deja un único material PBR con esas imágenes (lo que entienden FBX y GLB)."""
    os.makedirs(carpeta, exist_ok=True)
    preparar_cycles()
    uv(ob)
    nombre = ob.name
    mapas = {}
    for pase, tipo, color_space in (("color", "DIFFUSE", "sRGB"), ("rugosidad", "ROUGHNESS", "Non-Color"),
                                    ("normal", "NORMAL", "Non-Color")):
        img = bpy.data.images.new(f"{nombre}_{pase}", res, res, alpha=False)
        img.colorspace_settings.name = color_space
        if pase == "normal":
            img.generated_color = (0.5, 0.5, 1.0, 1.0)
        for m in ob.data.materials:
            nt = m.node_tree
            nodo = nt.nodes.get("FNS_hornear") or nt.nodes.new("ShaderNodeTexImage")
            nodo.name = "FNS_hornear"
            nodo.image = img
            nt.nodes.active = nodo
        kw = {"type": tipo, "margin": 8, "use_clear": True}
        if tipo == "DIFFUSE":
            kw["pass_filter"] = {"COLOR"}
        bpy.ops.object.select_all(action="DESELECT")
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.bake(**kw)
        ext, fmt = (".png", "PNG") if pase == "normal" else (".jpg", "JPEG")
        img.filepath_raw = os.path.join(carpeta, f"{nombre}_{pase}{ext}")
        img.file_format = fmt
        img.save()
        mapas[pase] = img
    # material final, simple y portable
    m = bpy.data.materials.new(f"{nombre}_pbr")
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    tc = nt.nodes.new("ShaderNodeTexImage"); tc.image = mapas["color"]
    tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = mapas["rugosidad"]
    tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = mapas["normal"]
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tc.outputs["Color"], bs.inputs["Base Color"])
    nt.links.new(tr.outputs["Color"], bs.inputs["Roughness"])
    nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bs.inputs["Normal"])
    ob.data.materials.clear()
    ob.data.materials.append(m)
    return m


def triangulos(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def exportar(objs, ruta, instancias=False):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    kw = dict(filepath=ruta + ".glb", use_selection=True, export_format="GLB", export_image_format="AUTO")
    if instancias:
        kw["export_gpu_instances"] = True          # la misma planta repetida no se duplica en el archivo
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError:
        kw.pop("export_gpu_instances", None)
        bpy.ops.export_scene.gltf(**kw)
    bpy.ops.export_scene.fbx(filepath=ruta + ".fbx", use_selection=True, axis_forward="-Z", axis_up="Y",
                             apply_scale_options="FBX_SCALE_ALL", path_mode="COPY", embed_textures=True,
                             object_types={"MESH", "EMPTY"}, bake_anim=False)


def vista(objs, ruta, distancia, alto_mira, muestras=24, altura_cam=None, ancho=960, alto=540):
    esc = bpy.context.scene
    preparar_cycles(muestras)
    esc.cycles.use_denoising = True
    esc.render.resolution_x, esc.render.resolution_y = ancho, alto
    esc.render.film_transparent = False
    mundo = esc.world or bpy.data.worlds.new("cielo")
    esc.world = mundo
    mundo.use_nodes = True
    bg = mundo.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.62, 0.66, 0.70, 1)     # cielo triásico: cálido y brumoso
    bg.inputs["Strength"].default_value = 0.9
    if "sol" not in bpy.data.objects:
        sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
        sol.data.energy = 3.5
        sol.data.color = (1.0, 0.93, 0.82)
        sol.rotation_euler = (math.radians(50), 0, math.radians(-40))
        esc.collection.objects.link(sol)
    cam = bpy.data.objects.get("camara_vista") or bpy.data.objects.new("camara_vista", bpy.data.cameras.new("cv"))
    if cam.name not in esc.collection.objects:
        esc.collection.objects.link(cam)
    cam.data.lens = 35
    cam.location = (distancia * 0.75, -distancia, altura_cam if altura_cam is not None else distancia * 0.45)
    cam.rotation_euler = (Vector((0, 0, alto_mira)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    try:
        esc.view_settings.view_transform = "AgX"
    except TypeError:
        pass
    esc.render.image_settings.file_format = "JPEG"
    esc.render.filepath = ruta
    bpy.ops.render.render(write_still=True)


def hacer_asset(nombre, salida, res, muestras):
    limpiar()
    MATS.clear()
    noise.seed_set(231)
    ob = FLORA[nombre]()
    ob.name = nombre
    carpeta = os.path.join(salida, "assets", nombre)
    os.makedirs(carpeta, exist_ok=True)
    hornear(ob, os.path.join(carpeta, "texturas"), res)
    informe = {}
    total = triangulos(ob)
    for nivel, frac in TOPES.items():
        c = ob.copy(); c.data = ob.data.copy(); c.name = f"{nombre}_{nivel}"
        bpy.context.scene.collection.objects.link(c)
        if frac < 1.0:
            mod = c.modifiers.new("reducir", "DECIMATE"); mod.ratio = frac
            bpy.ops.object.select_all(action="DESELECT"); c.select_set(True)
            bpy.context.view_layer.objects.active = c
            bpy.ops.object.modifier_apply(modifier=mod.name)
        exportar([c], os.path.join(carpeta, f"{nombre}_{nivel}"))
        informe[nivel] = triangulos(c)
        if nivel != "alto":
            bpy.data.objects.remove(c)
    ob.hide_render = True
    alto = ob.dimensions.z
    vista([bpy.data.objects[f"{nombre}_alto"]], os.path.join(carpeta, f"{nombre}_vista.jpg"),
          max(ob.dimensions) * 1.6 + 1, alto * 0.45, muestras)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, f"{nombre}.blend"))
    medidas = [round(d, 2) for d in ob.dimensions]
    print(f"   {nombre}: {total:,} triángulos (alto) · medio {informe['medio']:,} · bajo {informe['bajo']:,} · {medidas} m")
    return informe


# =========================================================================================
# terrenos y escenas
# =========================================================================================

TAM = 40.0          # cada escena es un terreno de 40×40 m (suficiente para una pared LED 1:1)
GRILLA = 256


def cauce_y(x, forma):
    if forma == "rio":
        return 6.0 * math.sin(x * 0.12) + 2.0 * math.sin(x * 0.31 + 1.0)
    if forma == "estanque":
        return None
    return None


def terreno(nombre, forma, ceniza=False):
    """Terreno de 40×40 m. Guarda en un color de vértice: R humedad, G arena, B vegetación."""
    bm = bmesh.new()
    capa = bm.loops.layers.color.new("mascara")
    n = GRILLA
    verts = []
    datos = {}
    for j in range(n + 1):
        fila = []
        for i in range(n + 1):
            x = -TAM / 2 + TAM * i / n
            y = -TAM / 2 + TAM * j / n
            p = Vector((x, y, 0))
            z = fbm(p, 5, 0.04) * 1.4 + fbm(p, 3, 0.3) * 0.12
            hum = are = 0.0
            cy = cauce_y(x, forma)
            if cy is not None:
                d = abs(y - cy)
                z -= 1.3 * math.exp(-(d / 3.2) ** 2)                 # cauce
                z += 0.25 * math.exp(-((d - 5.0) / 1.5) ** 2)         # albardón (orilla alta)
                hum = math.exp(-(d / 6.0) ** 2)
                are = math.exp(-((d - 3.4) / 1.2) ** 2) * (0.6 + 0.4 * fbm(p, 2, 0.2))   # barras de arena
            if forma == "estanque":
                for cx, cyy, rr in ((-8, 6, 5), (10, -9, 4)):
                    d = math.hypot(x - cx, y - cyy)
                    z -= 0.7 * math.exp(-(d / rr) ** 2)
                    hum = max(hum, math.exp(-(d / (rr * 1.5)) ** 2))
            veg = max(0.0, min(1.0, 0.55 + fbm(p, 3, 0.09) * 1.4 - hum * 0.8))
            if ceniza:
                veg *= 0.15
            fila.append(bm.verts.new((x, y, z)))
            datos[(i, j)] = (hum, are, veg)
        verts.append(fila)
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((verts[j][i], verts[j][i + 1], verts[j + 1][i + 1], verts[j + 1][i]))
            for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                h, a, v = datos[(ii, jj)]
                loop[capa] = (h, a, v, 1.0)
    ob = objeto_desde_bmesh(nombre, bm)
    for p in ob.data.polygons:
        p.use_smooth = True
    base = CENIZA if ceniza else BARRO
    base2 = (0.45, 0.44, 0.42) if ceniza else (0.28, 0.21, 0.15)
    m = mat_proc(f"{nombre}_suelo", base, base2, escala=1.5, rug=0.85, bump=0.4, atributo="mascara")
    ob.data.materials.append(m)
    return ob


def agua(nivel=-0.45):
    bpy.ops.mesh.primitive_plane_add(size=TAM, location=(0, 0, nivel))
    a = bpy.context.object
    a.name = "agua"
    m = bpy.data.materials.new("agua_rio")
    m.use_nodes = True
    bs = m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (0.10, 0.12, 0.08, 1)     # río turbio de llanura
    bs.inputs["Roughness"].default_value = 0.08
    for nombre_in in ("Transmission Weight", "Transmission"):
        if nombre_in in bs.inputs:
            bs.inputs[nombre_in].default_value = 0.35
    a.data.materials.append(m)
    return a


def altura_en(ob_terreno, x, y):
    """Altura del terreno en (x, y) por la grilla (sin raycast: más rápido y determinista)."""
    n = GRILLA
    i = int(round((x + TAM / 2) / TAM * n))
    j = int(round((y + TAM / 2) / TAM * n))
    i, j = max(0, min(n, i)), max(0, min(n, j))
    return ob_terreno.data.vertices[j * (n + 1) + i].co.z


def humedad_en(ob_terreno, x, y):
    n = GRILLA
    i = int(round((x + TAM / 2) / TAM * n)); j = int(round((y + TAM / 2) / TAM * n))
    i, j = max(0, min(n, i)), max(0, min(n, j))
    capa = ob_terreno.data.color_attributes.get("mascara")
    idx = j * (n + 1) + i
    # el atributo es por esquina de cara: se busca una esquina que use ese vértice
    for lp in ob_terreno.data.loops:
        if lp.vertex_index == idx:
            return capa.data[lp.index].color[0]
    return 0.0


def repartir(ob_terreno, molde, cantidad, dist_min, condicion, escala=(0.8, 1.25), puestos=None, prefijo=""):
    """Reparto tipo Poisson (rechazo) con reglas de hábitat. Usa COPIAS ENLAZADAS: la misma
    malla, así el GLB y la memoria de video no se multiplican por cada planta."""
    puestos = puestos if puestos is not None else []
    hechos = []
    intentos = 0
    while len(hechos) < cantidad and intentos < cantidad * 60:
        intentos += 1
        x = AZAR.uniform(-TAM / 2 + 1, TAM / 2 - 1)
        y = AZAR.uniform(-TAM / 2 + 1, TAM / 2 - 1)
        if not condicion(x, y):
            continue
        if any((x - px) ** 2 + (y - py) ** 2 < (dist_min + pr) ** 2 for px, py, pr in puestos):
            continue
        c = molde.copy()             # comparte la malla (copia enlazada)
        c.name = f"{prefijo}{molde.name}_{len(hechos):03d}"
        bpy.context.scene.collection.objects.link(c)
        c.location = (x, y, altura_en(ob_terreno, x, y) - 0.05)
        c.rotation_euler.z = AZAR.uniform(0, 2 * math.pi)
        s = AZAR.uniform(*escala)
        c.scale = (s, s, s)
        puestos.append((x, y, dist_min * 0.5))
        hechos.append(c)
    return hechos


def slot(nombre, x, y, ob_terreno, mira_a=(0, 0)):
    e = bpy.data.objects.new(nombre, None)
    e.empty_display_type = "SINGLE_ARROW"
    e.empty_display_size = 1.0
    bpy.context.scene.collection.objects.link(e)
    e.location = (x, y, altura_en(ob_terreno, x, y))
    e.rotation_euler.z = math.atan2(mira_a[1] - y, mira_a[0] - x) - math.pi / 2
    return e


def cargar_assets(salida):
    """Trae los assets ya horneados (nivel alto) como moldes, fuera de la vista."""
    moldes = {}
    for nombre in FLORA:
        ruta = os.path.join(salida, "assets", nombre, f"{nombre}_alto.glb")
        if not os.path.exists(ruta):
            raise SystemExit(f"Falta el asset {nombre}: correr primero con --solo assets")
        antes = set(bpy.context.scene.objects)
        bpy.ops.import_scene.gltf(filepath=ruta)
        nuevos = [o for o in bpy.context.scene.objects if o not in antes and o.type == "MESH"]
        m = nuevos[0]
        m.name = nombre
        m.location = (0, 0, -500)     # molde escondido bajo el terreno
        moldes[nombre] = m
    return moldes


def volcan_fondo():
    """Silueta de volcán a 300 m con columna de ceniza: el que dejó las tobas de Ischigualasto."""
    bm = bmesh.new()
    perfil = [(260, 0), (180, 40), (90, 95), (40, 120), (25, 118)]
    anillos = []
    for rr, h in perfil:
        anillos.append([bm.verts.new((rr * math.cos(a), rr * math.sin(a), h))
                        for a in (2 * math.pi * k / 48 for k in range(48))])
    for i in range(len(anillos) - 1):
        for k in range(48):
            k2 = (k + 1) % 48
            bm.faces.new((anillos[i][k], anillos[i][k2], anillos[i + 1][k2], anillos[i + 1][k]))
    ob = objeto_desde_bmesh("volcan_fondo", bm)
    ob.location = (60, 320, -10)
    m = bpy.data.materials.new("volcan")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.16, 0.14, 0.14, 1)
    ob.data.materials.append(m)
    for v in ob.data.vertices:
        v.co += Vector((0, 0, fbm(Vector(v.co) * 0.02, 3) * 12))
    return ob


ESCENAS = {}


def escena(fn):
    ESCENAS[fn.__name__.replace("escena_", "")] = fn
    return fn


@escena
def escena_rio_triasico(moldes):
    """Río meandroso con barras de arena; Neocalamites en las orillas, Dicroidium en el albardón.
    Hyperodapedon (el animal más abundante de la formación) pastando junto al agua."""
    t = terreno("terreno_rio", "rio")
    objs = [t, agua()]
    en_orilla = lambda x, y: 3.5 < abs(y - cauce_y(x, "rio")) < 7.0
    seco = lambda x, y: abs(y - cauce_y(x, "rio")) > 7.0
    p = []
    objs += repartir(t, moldes["neocalamites"], 40, 1.4, en_orilla, (0.8, 1.3), p)
    objs += repartir(t, moldes["dicroidium"], 14, 4.0, seco, (0.8, 1.2), p)
    objs += repartir(t, moldes["conifera"], 4, 6.0, lambda x, y: seco(x, y) and abs(y) > 12, (0.8, 1.1), p)
    objs += repartir(t, moldes["helecho"], 60, 1.2, seco, (0.7, 1.3), p)
    objs += repartir(t, moldes["tronco_caido"], 3, 5.0, en_orilla, (0.9, 1.2), p)
    cy = lambda x: cauce_y(x, "rio")
    slots = [slot(f"SLOT_hyperodapedon_{i}", x, cy(x) + 3.8, t, (x, cy(x))) for i, x in enumerate((-6, -3.5, -1, 2))]
    slots.append(slot("SLOT_herrerasaurus_0", 9, cy(9) + 8, t, (-3, cy(-3) + 4)))
    slots.append(slot("SLOT_ischigualastia_0", -14, cy(-14) - 8, t, (-14, cy(-14))))
    return objs + slots, (18, -26, 6), (0, 0, 1.5)


@escena
def escena_bosque_dicroidium(moldes):
    """Bosque de Dicroidium con coníferas y sotobosque de helechos. Los dinosaurios chicos
    (Eoraptor, Eodromaeus) y el primer sauropodomorfo (Panphagia) se mueven entre los troncos."""
    t = terreno("terreno_bosque", "estanque")
    objs = [t]
    p = []
    seco = lambda x, y: humedad_en(t, x, y) < 0.3
    objs += repartir(t, moldes["dicroidium"], 34, 3.0, seco, (0.8, 1.35), p)
    objs += repartir(t, moldes["conifera"], 10, 5.0, seco, (0.8, 1.2), p)
    objs += repartir(t, moldes["helecho"], 110, 0.9, lambda x, y: True, (0.6, 1.4), p)
    objs += repartir(t, moldes["neocalamites"], 14, 1.2, lambda x, y: humedad_en(t, x, y) > 0.3, (0.8, 1.2), p)
    objs += repartir(t, moldes["tronco_caido"], 6, 3.0, seco, (0.8, 1.3), p)
    slots = [slot("SLOT_eoraptor_0", -2, -4, t, (4, 0)), slot("SLOT_eoraptor_1", -3, -2.5, t, (4, 0)),
             slot("SLOT_eodromaeus_0", 5, -6, t, (0, 5)), slot("SLOT_panphagia_0", 3, 4, t, (-5, 5)),
             slot("SLOT_herrerasaurus_0", -10, 8, t, (0, -2))]
    return objs + slots, (16, -22, 4.5), (0, 0, 2.0)


@escena
def escena_llanura_aluvial(moldes):
    """Llanura de inundación abierta con charcas, arbustos dispersos y el volcán de fondo.
    Una manada de Ischigualastia y un Herrerasaurus que la acecha."""
    t = terreno("terreno_llanura", "estanque")
    objs = [t, agua(-0.35), volcan_fondo()]
    p = []
    seco = lambda x, y: humedad_en(t, x, y) < 0.35
    objs += repartir(t, moldes["dicroidium"], 7, 7.0, seco, (0.7, 1.1), p)
    objs += repartir(t, moldes["helecho"], 45, 1.5, seco, (0.6, 1.2), p)
    objs += repartir(t, moldes["neocalamites"], 18, 1.4, lambda x, y: 0.3 < humedad_en(t, x, y) < 0.8, (0.8, 1.2), p)
    objs += repartir(t, moldes["roca_arenisca"], 12, 2.0, seco, (0.5, 1.6), p)
    slots = [slot(f"SLOT_ischigualastia_{i}", x, y, t, (-8, 6)) for i, (x, y) in enumerate(((-2, 2), (0, 4.5), (2.5, 1)))]
    slots.append(slot("SLOT_herrerasaurus_0", 12, -4, t, (0, 2)))
    slots.append(slot("SLOT_sanjuansaurus_0", 14, 3, t, (0, 2)))
    return objs + slots, (20, -24, 5), (0, 0, 2.0)


@escena
def escena_ceniza_volcanica(moldes):
    """La lluvia de ceniza: suelo gris, árboles quemados y sin hojas. Es el momento que tapó a los
    animales y los conservó; esas capas de ceniza son las que permiten fechar la formación."""
    t = terreno("terreno_ceniza", "estanque", ceniza=True)
    objs = [t, volcan_fondo()]
    p = []
    objs += repartir(t, moldes["dicroidium_quemado"], 16, 4.0, lambda x, y: True, (0.8, 1.2), p)
    objs += repartir(t, moldes["tronco_caido"], 8, 3.0, lambda x, y: True, (0.8, 1.2), p)
    objs += repartir(t, moldes["roca_arenisca"], 10, 2.0, lambda x, y: True, (0.5, 1.4), p)
    slots = [slot("SLOT_herrerasaurus_esqueleto_0", 0, 0, t, (5, 5)),
             slot("SLOT_hyperodapedon_esqueleto_0", 4, -3, t, (0, 0))]
    return objs + slots, (14, -18, 4), (0, 0, 1.0)


def hacer_escena(nombre, salida, res, muestras):
    limpiar()
    MATS.clear()
    noise.seed_set(231)
    AZAR.seed(hash(nombre) % 10000)
    moldes = cargar_assets(salida)
    objs, cam_pos, mira = ESCENAS[nombre](moldes)
    carpeta = os.path.join(salida, "escenas", nombre)
    os.makedirs(carpeta, exist_ok=True)
    # sólo el terreno necesita hornearse acá: las plantas ya vienen horneadas de los assets
    terr = next(o for o in objs if o.name.startswith("terreno_"))
    hornear(terr, os.path.join(carpeta, "texturas"), res)
    for m in moldes.values():
        m.hide_render = True
    exportables = [o for o in objs if o.type in ("MESH", "EMPTY")]
    exportar(exportables, os.path.join(carpeta, nombre), instancias=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, f"{nombre}.blend"))
    # vista a la altura de los ojos de un dinosaurio grande, mirando la escena
    esc = bpy.context.scene
    cam = bpy.data.objects.new("camara_vista", bpy.data.cameras.new("cv"))
    esc.collection.objects.link(cam)
    cam.location = cam_pos
    vista(exportables, os.path.join(carpeta, f"{nombre}_vista.jpg"), 0, mira[2], muestras)
    cam = bpy.data.objects["camara_vista"]
    cam.location = cam_pos
    cam.rotation_euler = (Vector(mira) - Vector(cam_pos)).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.render.render(write_still=True)
    n_slots = sum(1 for o in objs if o.name.startswith("SLOT_"))
    n_plantas = sum(1 for o in objs if o.type == "MESH") - 1
    print(f"   {nombre}: {n_plantas} objetos, {n_slots} lugares para dinosaurios")


def main():
    a = argumentos()
    salida = os.path.abspath(a.salida)
    pedido = set(a.solo or ["assets", "escenas"])
    assets = list(FLORA) if "assets" in pedido else [x for x in FLORA if x in pedido]
    escenas = list(ESCENAS) if "escenas" in pedido else [x for x in ESCENAS if x in pedido]
    for nombre in assets:
        print(f"== asset {nombre}", flush=True)
        hacer_asset(nombre, salida, a.res, a.muestras_vista)
    for nombre in escenas:
        print(f"== escena {nombre}", flush=True)
        hacer_escena(nombre, salida, a.res, a.muestras_vista)
    print("listo:", salida)


if __name__ == "__main__":
    main()
