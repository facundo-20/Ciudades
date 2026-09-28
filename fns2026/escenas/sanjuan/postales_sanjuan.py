"""
Recorrido por San Juan: los dinosaurios de Ischigualasto muestran los lugares más icónicos
de la provincia hoy. Una "postal" por lugar, hiperrealista en Cycles, con el mismo motor que
el Triásico (cielo físico, sol real, AgX) y los modelos de Meshy a escala real.

    python3 postales_sanjuan.py -- salida/ [--postales hongo bochas ...] [--calidad prueba|media|led]
        [--modelos ../../modelos]

Qué hay en cada postal y de dónde sale:
  · el hito: modelo de Meshy si está (modelos/<hito>/<hito>_alto.glb), si no una versión hecha
    acá a medida con las medidas publicadas (el arco del Bicentenario de 63 m de luz, las
    bochas de hasta 90 cm, el campanario…). Así la postal siempre sale.
  · el guía: Sanjuansaurus gordilloi ("lagarto de San Juan") en primer plano, girado hacia el
    hito, a su escala real (3 m). Un segundo animal acompaña según el lugar.
  · el terreno, el agua, las montañas y la luz: procedurales, con los colores reales del lugar
    (arcilla gris del Valle de la Luna, pampa blanca del Leoncito, lago turquesa de Cuesta del
    Viento, precordillera parda con nieve arriba).
  · Nada de fotos de Google ni de terceros: se estudiaron para las formas y los colores, pero
    no se copian (derechos y términos de uso).
"""

import argparse
import math
import os
import random
import sys

import bpy  # antes que bmesh: con el bpy de pip, bmesh existe recién después
import bmesh
from mathutils import Vector, noise

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "hiperreal"))
import triasico_cycles as T  # noqa: E402  (mismo cielo, render, arcilla, estratos e instancias)

CALIDADES = T.CALIDADES

# ------------------------------------------------------------------------------------------
# las postales
# ------------------------------------------------------------------------------------------
# ojo / mira en metros (x, y, z con z arriba). sol = (elevación, azimut). guia = (x, y) del
# Sanjuansaurus; mira hacia el hito. extra = (especie, x, y, rumbo en grados, cantidad).
POSTALES = {
    "hongo": dict(
        titulo="El Hongo · Valle de la Luna", terreno="arcilla", sol=(38, 250),
        ojo=(-14, -4, 1.7), mira=(22, 6, 4.5), hito=("el_hongo", (22, 6), 0),
        barrancas=True, extra=[("ischigualastia", 26, -16, 1)]),
    "bochas": dict(
        titulo="Cancha de Bochas · Valle de la Luna", terreno="arcilla", sol=(28, 230),
        ojo=(-9, -6, 1.5), mira=(8, 4, 0.2), hito=("bochas", (6, 3), 0),
        barrancas=True, extra=[("hyperodapedon", 13, -12, 2)]),
    "alcazar": dict(
        titulo="Cerro Alcázar · Barreal, Calingasta", terreno="ripio", sol=(24, 280),
        ojo=(-260, -40, 1.8), mira=(120, 30, 55), hito=("cerro_alcazar", (120, 20), 10),
        andes=True, extra=[("panphagia", 16, -8, 2)]),
    "leoncito": dict(
        titulo="Pampa El Leoncito · Calingasta", terreno="pampa", sol=(13, 262),
        ojo=(-30, -8, 1.6), mira=(60, 10, 4), hito=("carro_velero", (24, 4), 90),
        andes=True, observatorio=(900, 2200), extra=[("exaeretodon", 18, -14, 2)]),
    "cuesta": dict(
        titulo="Dique Cuesta del Viento · Rodeo, Iglesia", terreno="ripio", sol=(40, 200),
        ojo=(-40, -30, 1.8), mira=(900, 420, -10), hito=None, lago=(700, 420, 380), mirador=28,
        andes=True, extra=[("exaeretodon", 15, -12, 3)]),
    "catedral": dict(
        titulo="Catedral de San Juan · Plaza 25 de Mayo", terreno="plaza", sol=(55, 20),
        ojo=(-95, -45, 1.7), mira=(12, 10, 18), hito=("campanario_catedral", (12, 10), 0),
        sierras=True, catedral=True, extra=[("panphagia", 14, -10, 2)]),
    "bicentenario": dict(
        titulo="Teatro del Bicentenario · San Juan", terreno="plaza", sol=(22, 290),
        ojo=(-6, -60, 1.7), mira=(0, 20, 5), hito=("arco_bicentenario", (0, 18), 0),
        sierras=True, extra=[("hyperodapedon", 14, -12, 2)]),
}

# dónde entra el guía: a GUIA_M metros de la cámara, desviado GUIA_GRADOS a la izquierda
# (tercio izquierdo del cuadro) y girado hacia el hito. Relativo a la cámara para que
# nunca quede fuera de cuadro, que es lo que pasaba con posiciones fijas.
GUIA_M, GUIA_GRADOS = 11.0, 13.0

ALTURA_GUIA = {"sanjuansaurus": 3.0}


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--postales", nargs="*", default=list(POSTALES))
    ap.add_argument("--calidad", default="prueba", choices=list(CALIDADES))
    ap.add_argument("--modelos", default=os.path.join(AQUI, "..", "..", "modelos"))
    return ap.parse_args(argv)


# ------------------------------------------------------------------------------------------
# relieve
# ------------------------------------------------------------------------------------------

def fbm(x, y, o=5):
    return T.fbm2(x, y, o)


def cresta(x, y, o=6):
    """Ruido de crestas: montañas con filos, no lomas de algodón."""
    t, a, f, n = 0.0, 1.0, 1.0, 0.0
    for _ in range(o):
        v = 1 - abs(noise.noise(Vector((x * f, y * f, 3.1))))
        t += a * v * v
        n += a
        a *= 0.5
        f *= 2.1
    return t / n


LAGO = {"elipse": None}      # (cx, cy, rx, ry): el vaso del dique hunde el terreno
MIRADOR = {"loma": None}     # (x, y, alto, radio): la loma desde donde se mira (camino de cornisa)


def altura_suelo(tipo, x, y):
    extra = 0.0
    if MIRADOR["loma"]:
        mx, my, mh, mr = MIRADOR["loma"]
        extra = mh * math.exp(-((x - mx) ** 2 + (y - my) ** 2) / (mr * mr))
    return extra + altura_suelo_lago(tipo, x, y)


def altura_suelo_lago(tipo, x, y):
    if LAGO["elipse"]:
        lx, ly, rx, ry = LAGO["elipse"]
        d = ((x - lx) / rx) ** 2 + ((y - ly) / ry) ** 2
        if d < 1.6:
            base = altura_suelo_sin_lago(tipo, x, y)
            return base - (base + 3.0) * T.lisa(1.6, 0.7, d)    # la costa baja tendida hasta el agua
    return altura_suelo_sin_lago(tipo, x, y)


def altura_suelo_sin_lago(tipo, x, y):
    if tipo == "arcilla":
        return T.altura_hoy(x, -y) * 0.35
    if tipo == "pampa":
        return fbm(x * 0.004, y * 0.004, 2) * 0.3          # la pampa es plana como una mesa
    if tipo == "ripio":
        return fbm(x * 0.006, y * 0.006, 4) * 6 + fbm(x * 0.05, y * 0.05, 2) * 0.4
    return 0.0                                               # plaza


def malla_grilla(nombre, cx, cy, lado, paso, fz):
    n = int(lado / paso)
    bm = bmesh.new()
    filas = []
    for j in range(n + 1):
        fila = []
        for i in range(n + 1):
            x, y = cx - lado / 2 + i * paso, cy - lado / 2 + j * paso
            fila.append(bm.verts.new((x, y, fz(x, y))))
        filas.append(fila)
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((filas[j][i], filas[j][i + 1], filas[j + 1][i + 1], filas[j + 1][i]))
            f.smooth = True
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def cordillera(cx, cy, rumbo_grados, distancia, alto, ancho_grados=110, nieve=True):
    """Un cordón de montañas lejano en el sector que mira la cámara: la Precordillera y los
    Andes de Calingasta e Iglesia, pardos y violáceos con nieve arriba de cierta altura."""
    bm = bmesh.new()
    cols, filas = 260, 22
    grilla = []
    for c in range(cols):
        a = math.radians(rumbo_grados - ancho_grados / 2 + ancho_grados * c / (cols - 1))
        # cada tramo del cordón tiene su propia altura: cerros altos y portezuelos
        tramo = 0.45 + 0.55 * cresta(c * 0.035, 7.7, 3)
        fila = []
        for k in range(filas):
            t = k / (filas - 1)
            r = distancia * (0.55 + 1.1 * t)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            # pie de monte largo y tendido, cumbres hacia el 60 % de la profundidad
            perfil = math.exp(-((t - 0.6) / 0.28) ** 2)
            h = alto * tramo * perfil * (0.4 + 0.6 * cresta(x * 0.0006, y * 0.0006))
            fila.append(bm.verts.new((x, y, h - 40)))
        grilla.append(fila)
    for c in range(cols - 1):
        for k in range(filas - 1):
            bm.faces.new((grilla[c][k], grilla[c + 1][k], grilla[c + 1][k + 1], grilla[c][k + 1]))
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
    me = bpy.data.meshes.new("cordillera")
    bm.to_mesh(me)
    bm.free()
    for v in me.vertices:
        v.co.z += (cresta(v.co.x * 0.0012, v.co.y * 0.0012, 4) - 0.5) * alto * 0.18
    ob = bpy.data.objects.new("cordillera", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    ob.data.materials.append(material_montana(alto * 0.62 if nieve else 1e9))
    return ob


# ------------------------------------------------------------------------------------------
# materiales con los colores reales
# ------------------------------------------------------------------------------------------

def mat_base(nombre):
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def ruido(nt, escala, detalle=6, rug=0.55, coord="Object"):
    tc = T.nodo(nt, "ShaderNodeTexCoord")
    r = T.nodo(nt, "ShaderNodeTexNoise")
    r.inputs["Scale"].default_value = escala
    r.inputs["Detail"].default_value = detalle
    r.inputs["Roughness"].default_value = rug
    nt.links.new(tc.outputs[coord], r.inputs["Vector"])
    return r


def mezcla(nt, fac, a, b, tipo="MIX"):
    x = T.nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type=tipo)
    if isinstance(fac, float):
        x.inputs["Factor"].default_value = fac
    else:
        nt.links.new(fac, x.inputs["Factor"])
    for sock, val in (("A", a), ("B", b)):
        if isinstance(val, tuple):
            x.inputs[sock].default_value = (*val, 1)
        else:
            nt.links.new(val, x.inputs[sock])
    return x.outputs["Result"]


def relieve(nt, bs, altura_out, fuerza=0.4, dist=0.03):
    b = T.nodo(nt, "ShaderNodeBump")
    b.inputs["Strength"].default_value = fuerza
    b.inputs["Distance"].default_value = dist
    nt.links.new(altura_out, b.inputs["Height"])
    nt.links.new(b.outputs["Normal"], bs.inputs["Normal"])


def material_pampa():
    """Pampa El Leoncito: barreal blanco (arcilla y limo de un lago seco), grietas finas."""
    m, nt, bs = mat_base("pampa_leoncito")
    mac = ruido(nt, 0.03, 4)
    col = mezcla(nt, T.sal(mac, "Factor", "Fac"), (0.70, 0.67, 0.61), (0.80, 0.77, 0.71))
    grietas = T.nodo(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    grietas.inputs["Scale"].default_value = 1.2
    nt.links.new(T.nodo(nt, "ShaderNodeTexCoord").outputs["Object"], grietas.inputs["Vector"])
    borde = T.nodo(nt, "ShaderNodeMapRange")
    borde.inputs["From Max"].default_value = 0.02
    borde.inputs["To Min"].default_value, borde.inputs["To Max"].default_value = 1.0, 0.0
    nt.links.new(T.sal(grietas, "Distance"), borde.inputs["Value"])
    col = mezcla(nt, borde.outputs[0], col, (0.45, 0.42, 0.38))
    nt.links.new(col, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.85
    relieve(nt, bs, T.sal(grietas, "Distance"), 0.25)
    return m


def material_ripio():
    """Ripio del desierto andino: grava parda y ocre con piedras sueltas oscuras."""
    m, nt, bs = mat_base("ripio_andino")
    mac = ruido(nt, 0.02, 5)
    gr = ruido(nt, 6.0, 8, 0.7)
    col = mezcla(nt, T.sal(mac, "Factor", "Fac"), (0.36, 0.28, 0.20), (0.52, 0.42, 0.30))
    piedras = T.nodo(nt, "ShaderNodeTexVoronoi")
    piedras.inputs["Scale"].default_value = 9
    nt.links.new(T.nodo(nt, "ShaderNodeTexCoord").outputs["Object"], piedras.inputs["Vector"])
    col = mezcla(nt, T.sal(piedras, "Distance"), (0.18, 0.15, 0.13), col)
    col = mezcla(nt, T.sal(gr, "Factor", "Fac"), col, (0.6, 0.55, 0.5), "MULTIPLY")
    nt.links.new(col, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.93
    relieve(nt, bs, T.sal(gr, "Factor", "Fac"), 0.6, 0.05)
    return m


def material_plaza():
    """Baldosas de plaza sanjuanina: calcáreas gris cálido en damero, juntas oscuras."""
    m, nt, bs = mat_base("plaza")
    tc = T.nodo(nt, "ShaderNodeTexCoord")
    lad = T.nodo(nt, "ShaderNodeTexBrick")
    lad.inputs["Scale"].default_value = 1.0
    lad.inputs["Color1"].default_value = (0.52, 0.48, 0.43, 1)
    lad.inputs["Color2"].default_value = (0.44, 0.41, 0.37, 1)
    lad.inputs["Mortar"].default_value = (0.20, 0.19, 0.18, 1)
    lad.inputs["Mortar Size"].default_value = 0.012
    lad.inputs["Brick Width"].default_value = 0.4
    lad.inputs["Row Height"].default_value = 0.4
    lad.offset = 0.0
    nt.links.new(tc.outputs["Object"], lad.inputs["Vector"])
    sucio = ruido(nt, 0.4, 6)
    col = mezcla(nt, 0.25, lad.outputs["Color"], T.sal(sucio, "Color"), "MULTIPLY")
    nt.links.new(col, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.7
    relieve(nt, bs, lad.outputs["Fac"], 0.3, 0.01)
    return m


def material_montana(cota_nieve):
    """Roca parda-violácea de la precordillera, más clara en los filos, y nieve arriba."""
    m, nt, bs = mat_base("montana")
    tc = T.nodo(nt, "ShaderNodeTexCoord")
    mac = ruido(nt, 0.0015, 6)
    col = mezcla(nt, T.sal(mac, "Factor", "Fac"), (0.20, 0.15, 0.14), (0.42, 0.33, 0.26))
    sep = T.nodo(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Object"], sep.inputs[0])
    ruido_n = ruido(nt, 0.004, 4)
    cota = T.nodo(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    nt.links.new(T.sal(ruido_n, "Factor", "Fac"), cota.inputs[0])
    cota.inputs[1].default_value = cota_nieve * 0.35
    nt.links.new(sep.outputs["Z"], cota.inputs[2])
    nieve = T.nodo(nt, "ShaderNodeMapRange")
    nieve.inputs["From Min"].default_value = cota_nieve
    nieve.inputs["From Max"].default_value = cota_nieve * 1.08 + 1
    nt.links.new(cota.outputs[0], nieve.inputs["Value"])
    # la nieve sólo se queda en lo que no es pared
    geo = T.nodo(nt, "ShaderNodeNewGeometry")
    sepn = T.nodo(nt, "ShaderNodeSeparateXYZ")
    nt.links.new(geo.outputs["Normal"], sepn.inputs[0])
    plano = T.nodo(nt, "ShaderNodeMapRange")
    plano.inputs["From Min"].default_value, plano.inputs["From Max"].default_value = 0.55, 0.8
    nt.links.new(sepn.outputs["Z"], plano.inputs["Value"])
    por = T.nodo(nt, "ShaderNodeMath", operation="MULTIPLY")
    nt.links.new(nieve.outputs[0], por.inputs[0])
    nt.links.new(plano.outputs[0], por.inputs[1])
    col = mezcla(nt, por.outputs[0], col, (0.88, 0.90, 0.94))
    nt.links.new(col, bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.9
    # perspectiva aérea sin volumen (que en "prueba" está apagado): cuanto más lejos, más se
    # mezcla con el azul del aire. Es lo que hace que una montaña a 10 km parezca a 10 km.
    camd = T.nodo(nt, "ShaderNodeCameraData")
    lejos = T.nodo(nt, "ShaderNodeMapRange")
    lejos.inputs["From Min"].default_value, lejos.inputs["From Max"].default_value = 1500, 16000
    lejos.inputs["To Min"].default_value, lejos.inputs["To Max"].default_value = 0.0, 0.62
    nt.links.new(camd.outputs["View Distance"], lejos.inputs["Value"])
    aire = T.nodo(nt, "ShaderNodeEmission")
    aire.inputs["Color"].default_value = (0.52, 0.64, 0.82, 1)
    aire.inputs["Strength"].default_value = 1.1
    mx = T.nodo(nt, "ShaderNodeMixShader")
    nt.links.new(lejos.outputs[0], mx.inputs[0])
    nt.links.new(bs.outputs[0], mx.inputs[1])
    nt.links.new(aire.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], nt.nodes["Material Output"].inputs["Surface"])
    relieve(nt, bs, T.sal(ruido(nt, 0.05, 8), "Factor", "Fac"), 0.5, 3.0)
    return m


def material_lago():
    """Agua del dique: turquesa por el limo glaciar en suspensión, con olas del viento."""
    m, nt, bs = mat_base("lago_turquesa")
    # el turquesa intenso de Cuesta del Viento: con poco color y mucho reflejo salía gris cielo
    bs.inputs["Base Color"].default_value = (0.01, 0.42, 0.44, 1)
    bs.inputs["Roughness"].default_value = 0.08
    bs.inputs["IOR"].default_value = 1.33
    try:
        bs.inputs["Specular IOR Level"].default_value = 0.3
    except KeyError:
        pass
    olas = T.nodo(nt, "ShaderNodeTexWave")
    olas.inputs["Scale"].default_value = 0.4
    olas.inputs["Distortion"].default_value = 6
    olas.inputs["Detail"].default_value = 6
    nt.links.new(T.nodo(nt, "ShaderNodeTexCoord").outputs["Object"], olas.inputs["Vector"])
    relieve(nt, bs, olas.outputs["Fac"], 0.25, 0.05)
    return m


def material_liso(nombre, color, rug=0.6):
    m, nt, bs = mat_base(nombre)
    bs.inputs["Base Color"].default_value = (*color, 1)
    bs.inputs["Roughness"].default_value = rug
    return m


# ------------------------------------------------------------------------------------------
# hitos: el de Meshy si está, si no uno hecho acá con las medidas publicadas
# ------------------------------------------------------------------------------------------

def caja(nombre, centro, medidas, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=centro)
    ob = bpy.context.object
    ob.name = nombre
    ob.scale = medidas
    ob.data.materials.append(material)
    return ob


def hongo_procedural(x, y):
    """El Hongo: sombrero de arenisca dura sobre pie fino de arcilla (erosión diferencial).
    Alto total ~5 m [a confirmar con el parque]."""
    arena = material_liso("arenisca", (0.50, 0.40, 0.30), 0.9)
    arcilla = material_liso("arcilla_pie", (0.44, 0.40, 0.35), 0.95)
    bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=1.6, radius2=0.55, depth=3.4, location=(x, y, 1.7))
    pie = bpy.context.object
    pie.data.materials.append(arcilla)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1.0, location=(x + 0.3, y, 4.2))
    som = bpy.context.object
    som.scale = (2.6, 2.1, 1.1)
    som.data.materials.append(arena)
    for o in (pie, som):
        d = o.modifiers.new("roca", "DISPLACE")
        tex = bpy.data.textures.new("roca_" + o.name, "CLOUDS")
        tex.noise_scale = 0.6
        d.texture = tex
        d.strength = 0.35
        o.modifiers.new("suave", "SUBSURF").levels = 2
        bpy.ops.object.shade_smooth()


def bochas_procedurales(cx, cy, cantidad=38):
    """Cancha de Bochas: concreciones esféricas de 5 cm a 90 cm sobre la arcilla plana."""
    azar = random.Random(225)
    mat = material_liso("concrecion", (0.24, 0.20, 0.16), 0.85)
    for i in range(cantidad):
        d = azar.choice([0.08, 0.12, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9])
        a, r = azar.uniform(0, 6.283), azar.uniform(0, 9) ** 0.9
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=d / 2,
                                             location=(x, y, altura_suelo("arcilla", x, y) + d * 0.42))
        o = bpy.context.object
        o.data.materials.append(mat)
        bpy.ops.object.shade_smooth()


def arco_procedural(x, y):
    """Arco del Teatro del Bicentenario: 63 m de luz libre y 6 m de alto, revestido en 9.000
    placas de travertino sanjuanino. Detrás, el volumen del teatro."""
    trav = material_liso("travertino", (0.72, 0.66, 0.56), 0.55)
    bm = bmesh.new()
    luz, alto, esp, prof = 63.0, 6.0, 0.9, 3.0
    arr = []
    for k in range(65):
        t = k / 64
        xx = -luz / 2 + luz * t
        z = alto * (1 - (2 * t - 1) ** 2)
        arr.append((xx, z))
    # banda con espesor y profundidad
    caras = []
    for dz in (0, esp):
        for dy in (0, prof):
            caras.append([bm.verts.new((x + xx, y + dy, max(0.0, z + dz - (esp if dz == 0 else 0) * 0))) for xx, z in arr])
    for i in range(len(arr) - 1):
        for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):
            bm.faces.new((caras[a][i], caras[a][i + 1], caras[b][i + 1], caras[b][i]))
    me = bpy.data.meshes.new("arco_bicentenario")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("arco_bicentenario", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(trav)
    ob.modifiers.new("espesor", "SOLIDIFY").thickness = 0.3
    # el teatro atrás: volumen de hormigón claro y vidrio
    caja("teatro", (x, y + 28, 11), (70, 40, 22), material_liso("hormigon", (0.62, 0.60, 0.57), 0.6))
    caja("vidriado", (x, y + 7.8, 4), (50, 0.3, 7), material_liso("vidrio", (0.05, 0.07, 0.08), 0.05))


def catedral_procedural(x, y):
    """Catedral de San Juan (1979): fachada al este con dos muros de laja de la sierra de
    Pie de Palo y un muro blanco retirado entre ambos; nave de ladrillo."""
    laja = material_liso("laja_pie_de_palo", (0.30, 0.20, 0.16), 0.85)
    blanco = material_liso("muro_blanco", (0.82, 0.80, 0.76), 0.6)
    ladrillo = material_liso("ladrillo", (0.45, 0.22, 0.14), 0.85)
    caja("nave", (x + 19, y + 6, 11), (48, 26, 22), ladrillo)
    caja("fachada_laja_n", (x - 5.5, y - 2, 10), (1.2, 8, 20), laja)
    caja("fachada_laja_s", (x - 5.5, y + 14, 10), (1.2, 8, 20), laja)
    caja("fachada_blanca", (x - 7.5, y + 6, 9), (0.8, 8, 18), blanco)


def campanario_procedural(x, y):
    """Campanario separado: ladrillo y laja rojiza, columnas blancas rectas. 50 m [a confirmar]."""
    ladrillo = material_liso("ladrillo_campanario", (0.47, 0.23, 0.15), 0.85)
    blanco = material_liso("columna_blanca", (0.85, 0.83, 0.80), 0.5)
    caja("torre", (x, y, 21), (7, 7, 42), ladrillo)
    for dx in (-3.6, 3.6):
        for dy in (-3.6, 3.6):
            caja("columna", (x + dx, y + dy, 46), (0.5, 0.5, 8), blanco)
    caja("techo", (x, y, 50.4), (7.8, 7.8, 0.8), ladrillo)


def carro_procedural(x, y, rumbo):
    """Carro velero: tres ruedas, chasis de caño y vela alta. Se arma alrededor del origen y
    se gira entero con un vacío padre (la vela quedaba de canto a la cámara)."""
    antes = set(bpy.data.objects)
    _carro(0.0, 0.0)
    padre = bpy.data.objects.new("carro_velero", None)
    bpy.context.scene.collection.objects.link(padre)
    for o in bpy.data.objects:
        if o not in antes and o is not padre:
            o.parent = padre
    padre.location = (x, y, 0)
    padre.rotation_euler.z = math.radians(rumbo)


def _carro(x, y):
    caño = material_liso("cano", (0.6, 0.6, 0.62), 0.3)
    vela = material_liso("vela", (0.9, 0.35, 0.12), 0.7)
    caja("chasis", (x, y, 0.4), (4.5, 0.12, 0.12), caño)
    caja("eje", (x - 1.2, y, 0.4), (0.12, 2.6, 0.12), caño)
    caja("mastil", (x - 0.5, y, 3.8), (0.1, 0.1, 6.5), caño)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(x - 1.6, y, 3.6), rotation=(math.pi / 2, 0, 0))
    v = bpy.context.object
    v.scale = (2.2, 5.6, 1)
    v.data.materials.append(vela)
    for px, py in ((x + 2.1, y), (x - 1.2, y - 1.3), (x - 1.2, y + 1.3)):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.3, depth=0.14, location=(px, py, 0.3), rotation=(math.pi / 2, 0, 0))
        bpy.context.object.data.materials.append(material_liso("goma", (0.03, 0.03, 0.03), 0.8))


def observatorio_procedural(x, y, z):
    blanco = material_liso("observatorio", (0.86, 0.86, 0.84), 0.4)
    domo = material_liso("domo", (0.75, 0.76, 0.78), 0.2)
    bpy.ops.mesh.primitive_cylinder_add(radius=12, depth=14, location=(x, y, z + 7))
    bpy.context.object.data.materials.append(blanco)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=12, location=(x, y, z + 14))
    bpy.context.object.data.materials.append(domo)


PROCEDURALES = {
    "el_hongo": lambda x, y, r: hongo_procedural(x, y),
    "bochas": lambda x, y, r: bochas_procedurales(x, y),
    "arco_bicentenario": lambda x, y, r: arco_procedural(x, y),
    "campanario_catedral": lambda x, y, r: campanario_procedural(x, y),
    "carro_velero": lambda x, y, r: carro_procedural(x, y, r),
}


def importar_glb(ruta):
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    return [o for o in bpy.data.objects if o not in antes and o.parent is None]


def poner_modelo(ruta, x, y, z, rumbo_grados):
    for raiz in importar_glb(ruta):
        raiz.location = (x, y, z)
        raiz.rotation_mode = "XYZ"
        raiz.rotation_euler = (0, 0, math.radians(rumbo_grados))


# hitos donde la versión a medida es más fiel que la de Meshy: el arco del Bicentenario salió
# de medio punto (romano) y el real es rebajado, 63 m de luz y sólo 6 m de alto (28/09)
PREFERIR_A_MEDIDA = {"arco_bicentenario"}


def poner_hito(carpeta_modelos, hito, terreno):
    nombre, (x, y), rumbo = hito
    ruta = os.path.join(carpeta_modelos, nombre, f"{nombre}_alto.glb")
    if nombre in PREFERIR_A_MEDIDA:
        ruta = ""
    z = altura_suelo(terreno, x, y) - 0.05
    if os.path.exists(ruta):
        poner_modelo(ruta, x, y, z, rumbo)
        if nombre == "bochas":                          # una bocha de Meshy → una cancha entera
            azar = random.Random(7)
            for _ in range(24):
                a, r = azar.uniform(0, 6.283), azar.uniform(1, 9)
                s = azar.choice([0.15, 0.3, 0.5, 0.8, 1.0])
                bx, by = x + r * math.cos(a), y + r * math.sin(a)
                for o in importar_glb(ruta):
                    o.location = (bx, by, altura_suelo(terreno, bx, by) - 0.03)
                    o.scale = (s, s, s)
                    o.rotation_euler.z = azar.uniform(0, 6.283)
        return "MESHY"
    if nombre in PROCEDURALES:
        PROCEDURALES[nombre](x, y, rumbo)
        return "a medida"
    return "falta"


# el frente de los modelos de Meshy importados queda mirando a -Y: para mirar hacia el
# ángulo θ se gira θ + 90°
def rumbo_hacia(desde, hacia):
    return math.degrees(math.atan2(hacia[1] - desde[1], hacia[0] - desde[0])) + 90


def poner_animal(carpeta_modelos, especie, x, y, rumbo_grados, terreno):
    ruta = T.modelo_de(carpeta_modelos, especie)
    if not ruta:
        return False
    poner_modelo(ruta, x, y, altura_suelo(terreno, x, y) - 0.03, rumbo_grados)
    return True


# ------------------------------------------------------------------------------------------
# armado
# ------------------------------------------------------------------------------------------

def camara(ojo, mira, foco):
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = 35
    cam.data.sensor_width = 36
    cam.data.clip_start = 0.1
    cam.data.clip_end = 40000
    cam.location = Vector(ojo)
    cam.rotation_euler = (Vector(mira) - Vector(ojo)).to_track_quat("-Z", "Y").to_euler()
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = foco
    cam.data.dof.aperture_fstop = 8.0
    bpy.context.scene.camera = cam


def hacer_postal(clave, a):
    p = POSTALES[clave]
    ancho, alto, muestras, volumetrica = CALIDADES[a.calidad]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    noise.seed_set(231)
    T.MODO["hoy"] = True
    carpeta = os.path.join(os.path.abspath(a.salida), clave)
    os.makedirs(carpeta, exist_ok=True)
    modelos = os.path.abspath(a.modelos)
    ox, oy, _ = p["ojo"]
    tipo = p["terreno"]

    LAGO["elipse"] = None
    MIRADOR["loma"] = (ox, oy, p["mirador"], 70.0) if p.get("mirador") else None
    if p.get("lago"):
        lx, ly, radio = p["lago"]
        LAGO["elipse"] = (lx + radio * 0.3, ly, radio * 1.8, radio)
    lado = 900.0 if tipo != "plaza" else 400.0
    paso = 1.2 if a.calidad == "prueba" else 0.6
    cx, cy = ox + (p["mira"][0] - ox) * 0.35, oy + (p["mira"][1] - oy) * 0.35
    suelo = malla_grilla("suelo", cx, cy, lado, paso if tipo != "pampa" else 3.0, lambda x, y: altura_suelo(tipo, x, y))
    mat = {"arcilla": lambda: T.material_suelo(hoy=True), "pampa": material_pampa,
           "ripio": material_ripio, "plaza": material_plaza}[tipo]()
    suelo.data.materials.append(mat)
    # el horizonte cercano: un anillo del mismo suelo para que no se vea el borde
    anillo = malla_grilla("suelo_lejos", cx, cy, 9000, 90, lambda x, y: altura_suelo(tipo, x, y) - 0.3)
    anillo.data.materials.append(mat)

    rumbo_mira = math.degrees(math.atan2(p["mira"][1] - oy, p["mira"][0] - ox))
    if p.get("barrancas"):
        # barrancas() trabaja en coordenadas de la web (x, z hacia el sur) y apoya sobre el
        # relieve completo de "hoy"; acá el suelo es más bajo, así que se hunde un poco
        b = T.barrancas((ox, -oy), (p["mira"][0], -p["mira"][1]), distancia=260, abertura=130)
        b.location.z -= 6
    if p.get("andes"):
        cordillera(ox, oy, rumbo_mira, 9000, 2600)                 # la cordillera, 9 km o más
        cordillera(ox, oy, rumbo_mira + 10, 3200, 520, 150, False)  # la precordillera delante
    if p.get("sierras"):
        cordillera(ox, oy, rumbo_mira, 7000, 900, 140, False)       # sierras de Zonda y Chica de Zonda
    if p.get("lago"):
        lx, ly, radio = p["lago"]
        bpy.ops.mesh.primitive_circle_add(vertices=128, radius=radio * 1.25, fill_type="NGON", location=(lx + radio * 0.3, ly, -0.8))
        lago = bpy.context.object
        lago.scale = (1.8, 1.0, 1.0)
        lago.data.materials.append(material_lago())
    if p.get("catedral"):
        catedral_procedural(p["hito"][1][0] + 26, p["hito"][1][1] - 6)
    if p.get("observatorio"):
        # CASLEO está arriba de un cerro de la sierra del Tontal: un cerro propio debajo
        tx, ty = p["observatorio"]
        bpy.ops.mesh.primitive_cone_add(vertices=96, radius1=1100, radius2=90, depth=430, location=(ox + tx, oy + ty, 200))
        cerro = bpy.context.object
        d = cerro.modifiers.new("relieve", "DISPLACE")
        d.texture = bpy.data.textures.new("cerro_obs", "CLOUDS")
        d.texture.noise_scale = 180
        d.strength = 60
        cerro.modifiers.new("suave", "SUBSURF").levels = 3
        cerro.data.materials.append(material_montana(1e9))
        ruta = os.path.join(modelos, "observatorio_casleo", "observatorio_casleo_alto.glb")
        if os.path.exists(ruta):
            poner_modelo(ruta, ox + tx, oy + ty, 412, 0)
        else:
            observatorio_procedural(ox + tx, oy + ty, 412)

    hecho = poner_hito(modelos, p["hito"], tipo) if p.get("hito") else "-"
    # el guía mira hacia el hito, girado de tres cuartos hacia la cámara
    def delante(dist, desvio):
        a = math.radians(rumbo_mira + desvio)
        return ox + dist * math.cos(a), oy + dist * math.sin(a)
    gx, gy = delante(GUIA_M, GUIA_GRADOS)
    destino = p["hito"][1] if p.get("hito") else p["mira"][:2]
    guia = poner_animal(modelos, "sanjuansaurus", gx, gy, rumbo_hacia((gx, gy), destino) - 25, tipo)
    otros = 0
    azar = random.Random(len(clave))
    for especie, dist, desvio, cant in p.get("extra", []):
        for k in range(cant):
            ex, ey = delante(dist + k * 2.8, desvio - k * 3.5)
            if poner_animal(modelos, especie, ex, ey, rumbo_hacia((ex, ey), destino) + azar.uniform(-40, 40), tipo):
                otros += 1

    T.cielo(*p["sol"], 0.0, volumetrica, 0.0, limpio=True)
    # el ojo va a su altura sobre el suelo real de ese punto (con altura fija quedaba enterrado)
    ojo = (ox, oy, altura_suelo(tipo, ox, oy) + p["ojo"][2])
    foco = GUIA_M
    camara(ojo, p["mira"], foco)
    T.configurar_render(ancho, alto, muestras, -1.0)
    esc = bpy.context.scene
    esc.render.image_settings.file_format = "PNG"
    esc.render.filepath = os.path.join(carpeta, f"{clave}.png")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, f"{clave}.blend"))
    bpy.ops.render.render(write_still=True)
    print(f"   {clave}: hito {hecho} · guía {'sí' if guia else 'FALTA modelo'} · {otros} acompañantes", flush=True)


def main():
    a = argumentos()
    for c in a.postales:
        print(f"== {c} · {POSTALES[c]['titulo']}", flush=True)
        hacer_postal(c, a)
    print("listo:", os.path.abspath(a.salida))


if __name__ == "__main__":
    main()
