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
    # El Submarino: columnas de arenisca en capas con la meseta roja de Los Colorados lejos, luz
    # cálida de tarde (foto de referencia de Facu)
    "submarino": dict(
        titulo="El Submarino · Valle de la Luna", terreno="arcilla", sol=(24, 255),
        ojo=(-18, -8, 1.7), mira=(26, 4, 6), hito=("el_submarino", (26, 4), 20),
        barrancas=True, barrancas_lejos=True, nubes=0.12, extra=[("ischigualastia", 30, 16, 1)]),
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
        andes=True, extra=[("exaeretodon", 18, -14, 2)]),
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

# La misma postal hace 231 millones de años: la misma cámara, otra época. Nada de lo que se ve
# hoy existía: las formaciones de Ischigualasto eran barro y arena que un río iba depositando en
# una llanura con bosques y volcanes; los Andes no estaban (se levantaron decenas de millones de
# años después) y en su lugar había volcanes en el borde del continente.
#   rio = (distancia, desvío°, largo, ancho, giro°) de un brazo del río frente a la cámara
#   fauna = (especie, distancia, desvío°, cantidad), como "extra"
#   volcan = desvío° del volcán en el horizonte (a 4,5 km)
TRIASICO = {
    "hongo": dict(titulo="El Hongo · hace 231 millones de años", rio=(60, 20, 140, 18, 70), volcan=-22,
                  fauna=[("ischigualastia", 26, -16, 3), ("hyperodapedon", 18, 10, 3)]),
    "submarino": dict(titulo="El Submarino · hace 231 millones de años", rio=(55, -18, 150, 20, 60), volcan=15,
                      fauna=[("saurosuchus", 34, 14, 1), ("exaeretodon", 18, -12, 3)]),
    "bochas": dict(titulo="Cancha de Bochas · hace 231 millones de años", rio=(45, -10, 160, 16, 95), volcan=25,
                   fauna=[("hyperodapedon", 13, -12, 4), ("exaeretodon", 22, 14, 2)]),
    "alcazar": dict(titulo="Cerro Alcázar · Triásico de la cuenca de Cuyo", rio=(90, 12, 220, 26, 80), volcan=-15,
                    fauna=[("panphagia", 16, -8, 3), ("saurosuchus", 40, 22, 1)]),
    "leoncito": dict(titulo="Donde hoy está El Leoncito, hace 231 millones de años", rio=(70, 5, 260, 30, 100), volcan=10,
                     fauna=[("exaeretodon", 18, -14, 3), ("ischigualastia", 45, 18, 2)]),
    "cuesta": dict(titulo="Donde hoy está Cuesta del Viento: antes de los Andes", rio=(120, 0, 400, 60, 90), volcan=-8,
                   fauna=[("hyperodapedon", 15, -12, 3), ("saurosuchus", 30, 16, 1)]),
    "catedral": dict(titulo="Donde hoy está la ciudad de San Juan, hace 231 millones de años", rio=(55, 15, 180, 20, 75), volcan=18,
                     fauna=[("panphagia", 14, -10, 2), ("exaeretodon", 24, 12, 3)]),
    "bicentenario": dict(titulo="Donde hoy está el Teatro del Bicentenario, hace 231 millones de años", rio=(50, -12, 160, 18, 100), volcan=-20,
                         fauna=[("ischigualastia", 22, -12, 2), ("hyperodapedon", 14, 12, 2)]),
}

# fauna de hoy que se cruza con el guía (como el guanaco del video de referencia)
GUANACOS = {"submarino": (42, -18, 2), "hongo": (48, 18, 2), "bochas": (40, -20, 2), "alcazar": (60, 12, 3), "cuesta": (35, 16, 2)}

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
    ap.add_argument("--assets", default=os.path.join(AQUI, "..", "triasico", "salida", "assets"),
                    help="flora procedural de respaldo (construir_triasico.py)")
    ap.add_argument("--era", default="hoy", choices=["hoy", "triasico", "ambas"])
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
        lx, ly, rx, ry = LAGO["elipse"][:4]
        giro = math.radians(LAGO["elipse"][4]) if len(LAGO["elipse"]) > 4 else 0.0
        c, s_ = math.cos(-giro), math.sin(-giro)
        qx, qy = (x - lx) * c - (y - ly) * s_, (x - lx) * s_ + (y - ly) * c
        d = (qx / rx) ** 2 + (qy / ry) ** 2
        if d < 1.6:
            base = altura_suelo_sin_lago(tipo, x, y)
            return base - (base + 3.0) * T.lisa(1.6, 0.7, d)    # la costa baja tendida hasta el agua
    return altura_suelo_sin_lago(tipo, x, y)


def altura_suelo_sin_lago(tipo, x, y):
    if tipo == "llanura":
        # llanura de inundación: ondulaciones suaves de metros, albardones y bajos
        return fbm(x * 0.008, y * 0.008, 4) * 2.2 + fbm(x * 0.05, y * 0.05, 2) * 0.35
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


# ------------------------------------------------------------------------------------------
# vegetación y detalles de hoy (video de referencia: jarillas, cardones, alambrado del Hongo)
# ------------------------------------------------------------------------------------------

def molde(nombre, objetos):
    """Une objetos en un molde fuera de cuadro para instanciarlo con Geometry Nodes."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objetos:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objetos[0]
    if len(objetos) > 1:
        bpy.ops.object.join()
    m = bpy.context.view_layer.objects.active
    m.name = f"molde_{nombre}"
    m.location = (0, 0, -1000)
    m.hide_render = True
    return m


def molde_jarilla():
    """Jarilla (Larrea): mata redonda de 1-1,5 m, verde oliva grisáceo, ramitas sueltas."""
    verde = material_liso("jarilla", (0.16, 0.19, 0.09), 0.8)
    partes = []
    azar = random.Random(11)
    for i in range(7):
        r = azar.uniform(0.28, 0.5)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=r,
                                              location=(azar.uniform(-0.45, 0.45), azar.uniform(-0.45, 0.45), r * 0.9 + azar.uniform(0, 0.3)))
        o = bpy.context.object
        d = o.modifiers.new("hojas", "DISPLACE")
        d.texture = bpy.data.textures.new(f"jarilla_{i}", "CLOUDS")
        d.texture.noise_scale = 0.12
        d.strength = 0.18
        bpy.ops.object.modifier_apply(modifier="hojas")
        o.data.materials.append(verde)
        partes.append(o)
    return molde("jarilla", partes)


def molde_cardon():
    """Cardón (Trichocereus terscheckii): columna de 4-5 m con dos o tres brazos que suben."""
    verde = material_liso("cardon", (0.13, 0.20, 0.09), 0.55)
    partes = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.24, depth=4.6, location=(0, 0, 2.3))
    partes.append(bpy.context.object)
    for lado, alto_b, largo in ((1, 1.9, 0.55), (-1, 2.5, 0.45)):
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.17, depth=largo,
                                            location=(lado * (0.24 + largo / 2), 0, alto_b), rotation=(0, math.pi / 2, 0))
        partes.append(bpy.context.object)
        bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.17, depth=1.6,
                                            location=(lado * (0.24 + largo), 0, alto_b + 0.8))
        partes.append(bpy.context.object)
    for o in partes:
        o.data.materials.append(verde)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth()
    return molde("cardon", partes)


def alambrado(x0, y0, x1, y1):
    """Alambrado de troncos rojizos como el que rodea El Hongo."""
    madera = material_liso("madera_alambrado", (0.26, 0.10, 0.05), 0.85)
    largo = math.hypot(x1 - x0, y1 - y0)
    ang = math.atan2(y1 - y0, x1 - x0)
    n = int(largo / 2.4) + 1
    for i in range(n):
        t = i / max(1, n - 1)
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        z = altura_suelo("arcilla", x, y)
        bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.07, depth=1.2, location=(x, y, z + 0.55))
        bpy.context.object.data.materials.append(madera)
    for h in (0.5, 0.95):
        zm = altura_suelo("arcilla", (x0 + x1) / 2, (y0 + y1) / 2)
        bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, zm + h))
        riel = bpy.context.object
        riel.scale = (largo, 0.08, 0.1)
        riel.rotation_euler.z = ang
        riel.data.materials.append(madera)


def sembrar_local(moldes, reglas, ox, oy, rumbo, terreno, libres, semilla=5):
    """Siembra alrededor de la cámara, en el sector que ve la panorámica del LED (±70°).
    reglas: (molde, cantidad, dist mín, dist máx, (esc mín, esc máx), alto) — "alto" = planta alta:
    no se siembra en los conos de vista (libres = [(rumbo°, medio ancho°, desde m)]) para que el
    hito, el volcán o la manada no queden tapados."""
    azar = random.Random(semilla)
    total = 0
    for nombre, cant, d0, d1, (e0, e1), alta in reglas:
        if nombre not in moldes:
            continue
        pts = []
        for _ in range(cant * 5):
            if len(pts) >= cant:
                break
            d = math.sqrt(azar.uniform(d0 * d0, d1 * d1))
            desvio = azar.uniform(-70, 70)
            if d < 7 and abs(desvio - GUIA_GRADOS) < 25:
                continue                                      # el lugar del guía
            if alta and any(abs(desvio - (r - rumbo)) < a and d > desde for r, a, desde in libres):
                continue
            ang = math.radians(rumbo + desvio)
            x, y = ox + d * math.cos(ang), oy + d * math.sin(ang)
            if LAGO["elipse"] and altura_suelo(terreno, x, y) < -0.6:
                continue                                      # adentro del agua
            pts.append((x, y, altura_suelo(terreno, x, y) - 0.05, azar.uniform(0, 6.283), azar.uniform(e0, e1),
                        azar.uniform(-0.05, 0.05)))
        if not pts:
            continue
        me = bpy.data.meshes.new(f"puntos_{nombre}")
        me.vertices.add(len(pts))
        me.vertices.foreach_set("co", [c for p_ in pts for c in p_[:3]])
        me.attributes.new("rot", "FLOAT_VECTOR", "POINT")
        me.attributes["rot"].data.foreach_set("vector", [c for p_ in pts for c in (p_[5], p_[5] * 0.5, p_[3])])
        me.attributes.new("esc", "FLOAT", "POINT")
        me.attributes["esc"].data.foreach_set("value", [p_[4] for p_ in pts])
        me.vertices.foreach_set("co", [c for p_ in pts for c in p_[:3]])
        me.update()
        ob = bpy.data.objects.new(f"flora_{nombre}", me)
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new("sembrar", "NODES")
        mod.node_group = T.arbol_gn(moldes[nombre])
        total += len(pts)
    return total


def material_rio():
    """Agua de río de llanura: turbia, verde parda, con poco reflejo."""
    m, nt, bs = mat_base("rio_triasico")
    bs.inputs["Base Color"].default_value = (0.07, 0.09, 0.05, 1)
    bs.inputs["Roughness"].default_value = 0.07
    olas = T.nodo(nt, "ShaderNodeTexNoise")
    olas.inputs["Scale"].default_value = 2.0
    nt.links.new(T.nodo(nt, "ShaderNodeTexCoord").outputs["Object"], olas.inputs["Vector"])
    relieve(nt, bs, T.sal(olas, "Factor", "Fac"), 0.15, 0.03)
    return m


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


def hacer_postal(clave, a, era="hoy"):
    p = POSTALES[clave]
    if era == "triasico":
        return hacer_postal_triasica(clave, a)
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
        # en El Submarino la meseta roja está lejos, como en la foto: al fondo del valle
        lejos = p.get("barrancas_lejos")
        b = T.barrancas((ox, -oy), (p["mira"][0], -p["mira"][1]), distancia=1400 if lejos else 260, abertura=130)
        b.location.z -= 6
    if p.get("andes"):
        # 170°: la panorámica del LED ve ~81° y con 110° se veían los extremos cortados como paredes
        cordillera(ox, oy, rumbo_mira, 9000, 2600, 170)             # la cordillera, 9 km o más
        cordillera(ox, oy, rumbo_mira + 10, 3200, 520, 170, False)  # la precordillera delante
    if p.get("sierras"):
        cordillera(ox, oy, rumbo_mira, 7000, 900, 170, False)       # sierras de Zonda y Chica de Zonda
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

    # vegetación de hoy donde hay suelo natural (la pampa del Leoncito es un barreal pelado)
    if tipo in ("arcilla", "ripio"):
        moldes = {"jarilla": molde_jarilla(), "cardon": molde_cardon()}
        libres = [(rumbo_mira, 10, 12)]
        sembrar_local(moldes, [("jarilla", 140, 6, 260, (0.6, 1.3), False),
                               ("cardon", 22 if tipo == "arcilla" else 12, 14, 260, (0.8, 1.2), True)],
                      ox, oy, rumbo_mira, tipo, libres)
    if clave == "hongo":
        # el alambrado de troncos delante del Hongo, como en la visita
        hx, hy = p["hito"][1]
        mx, my = ox + (hx - ox) * 0.62, oy + (hy - oy) * 0.62
        perp = math.atan2(hy - oy, hx - ox) + math.pi / 2
        alambrado(mx - 12 * math.cos(perp), my - 12 * math.sin(perp), mx + 12 * math.cos(perp), my + 12 * math.sin(perp))
    if clave in GUANACOS:
        gd, gdes, gc = GUANACOS[clave]
        for k in range(gc):
            ex, ey = delante(gd + k * 3.2, gdes + k * 2.5)
            if poner_animal(modelos, "guanaco", ex, ey, rumbo_hacia((ex, ey), (ox, oy)) + 60 + k * 25, tipo):
                otros += 1

    # cielo de Ischigualasto en el video de referencia: cirros sobre azul profundo
    T.cielo(*p["sol"], 0.0, volumetrica, 0.0, limpio=True, nubes=p.get("nubes", 0.55))
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


def hacer_postal_triasica(clave, a):
    """La misma cámara que la postal de hoy, 231 millones de años antes."""
    p, t = POSTALES[clave], TRIASICO[clave]
    ancho, alto, muestras, volumetrica = CALIDADES[a.calidad]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    noise.seed_set(231)
    T.MODO["hoy"] = False
    carpeta = os.path.join(os.path.abspath(a.salida), clave)
    os.makedirs(carpeta, exist_ok=True)
    modelos = os.path.abspath(a.modelos)
    ox, oy, _ = p["ojo"]
    tipo = "llanura"
    rumbo_mira = math.degrees(math.atan2(p["mira"][1] - oy, p["mira"][0] - ox))

    def delante(dist, desvio):
        an = math.radians(rumbo_mira + desvio)
        return ox + dist * math.cos(an), oy + dist * math.sin(an)

    # el brazo del río frente a la cámara
    rd, rdes, rl, rw, rgiro = t["rio"]
    rx_, ry_ = delante(rd, rdes)
    LAGO["elipse"] = (rx_, ry_, rl, rw, rumbo_mira + rgiro)
    MIRADOR["loma"] = None
    paso = 1.2 if a.calidad == "prueba" else 0.6
    cx, cy = ox + (p["mira"][0] - ox) * 0.35, oy + (p["mira"][1] - oy) * 0.35
    mat = T.material_suelo(hoy=False)
    suelo = malla_grilla("suelo", cx, cy, 900.0, paso, lambda x, y: altura_suelo(tipo, x, y))
    suelo.data.materials.append(mat)
    anillo = malla_grilla("suelo_lejos", cx, cy, 9000, 90, lambda x, y: altura_suelo(tipo, x, y) - 0.3)
    anillo.data.materials.append(mat)
    bpy.ops.mesh.primitive_circle_add(vertices=128, radius=1.0, fill_type="NGON", location=(rx_, ry_, -1.2))
    rio = bpy.context.object
    rio.scale = (rl * 1.12, rw * 1.12, 1.0)
    rio.rotation_euler.z = math.radians(rumbo_mira + rgiro)
    rio.data.materials.append(material_rio())

    # lomas bajas y, en el borde del continente, volcanes (todavía no hay Andes)
    cordillera(ox, oy, rumbo_mira, 6000, 320, 170, False)
    T.volcan(1.0)
    base = T.web_a_blender((1100, -30, -700))
    vx, vy = delante(4500, t["volcan"])
    for nombre in ("volcan", "columna_ceniza"):
        o = bpy.data.objects.get(nombre)
        if o:
            o.location.x += vx - base.x
            o.location.y += vy - base.y

    # flora del Triásico: la de Meshy si está, si no la procedural
    moldes = {}
    for nombre in ("dicroidium", "neocalamites", "helecho", "conifera"):
        m = T.cargar_molde(os.path.abspath(a.assets), nombre, modelos)
        if m:
            moldes[nombre] = m
    destino_vista = (rumbo_mira + t["volcan"], 8, 25)
    libres = [(rumbo_mira, 11, 14), destino_vista]
    n_plantas = sembrar_local(moldes, [
        ("helecho", 900, 4, 140, (0.6, 1.4), False),
        ("neocalamites", 260, 8, 220, (0.8, 1.3), True),
        ("dicroidium", 120, 16, 420, (0.8, 1.25), True),
        ("conifera", 40, 80, 700, (0.8, 1.3), True),
    ], ox, oy, rumbo_mira, tipo, libres, semilla=231)

    # el guía y la fauna de Ischigualasto
    gx, gy = delante(GUIA_M, GUIA_GRADOS)
    mira_xy = p["mira"][:2]
    guia = poner_animal(modelos, "sanjuansaurus", gx, gy, rumbo_hacia((gx, gy), mira_xy) - 25, tipo)
    otros = 0
    azar = random.Random(len(clave) + 231)
    for especie, dist, desvio, cant in t["fauna"]:
        for k in range(cant):
            ex, ey = delante(dist + k * 3.0, desvio - k * 3.5)
            if altura_suelo(tipo, ex, ey) < -0.6:
                continue
            if poner_animal(modelos, especie, ex, ey, rumbo_hacia((ex, ey), mira_xy) + azar.uniform(-50, 50), tipo):
                otros += 1

    # cielo húmedo de lluvias estacionales, aire más cargado que el de hoy
    T.cielo(p["sol"][0], p["sol"][1], 0.0015, volumetrica, 0.0, limpio=False, nubes=0.5)
    if volumetrica:
        T.bruma_local(Vector((ox, oy, 0)), 0.0015, 0.0)
    ojo = (ox, oy, altura_suelo(tipo, ox, oy) + p["ojo"][2])
    camara(ojo, p["mira"], GUIA_M)
    T.configurar_render(ancho, alto, muestras, -0.8)
    esc = bpy.context.scene
    esc.render.image_settings.file_format = "PNG"
    esc.render.filepath = os.path.join(carpeta, f"{clave}_triasico.png")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, f"{clave}_triasico.blend"))
    bpy.ops.render.render(write_still=True)
    LAGO["elipse"] = None
    print(f"   {clave} (Triásico): {n_plantas} plantas · guía {'sí' if guia else 'FALTA'} · {otros} animales", flush=True)


def main():
    a = argumentos()
    eras = ["hoy", "triasico"] if a.era == "ambas" else [a.era]
    for c in a.postales:
        for era in eras:
            print(f"== {c} ({era}) · {TRIASICO[c]['titulo'] if era == 'triasico' else POSTALES[c]['titulo']}", flush=True)
            hacer_postal(c, a, era)
    print("listo:", os.path.abspath(a.salida))


if __name__ == "__main__":
    main()
