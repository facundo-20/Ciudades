"""
El Triásico de Ischigualasto, HIPERREALISTA, en Blender + Cycles.

Es el mismo mundo y los mismos 6 capítulos que la experiencia web (fns2026/experiencia): la
geografía sale de las mismas fórmulas (río meandroso al oeste, bosque en el medio, llanura con
volcán al este), así un fondo renderizado acá calza con la interacción en vivo de TD o la web.

    blender -b --factory-startup -P triasico_cycles.py -- SALIDA [--capitulos rio bosque ...]
            [--calidad prueba|media|final|led] [--animar] [--assets CARPETA] [--modelos CARPETA]
    (o con el bpy de pip:  python3 triasico_cycles.py -- SALIDA ...)

Por capítulo sale en SALIDA/<capitulo>/:
    <capitulo>.png           el cuadro hiperrealista (AgX, Cycles, denoise)
    <capitulo>_profundidad.png   niebla/distancia normalizada: para montar la interacción encima
    frames/####.png          (--animar) el recorrido de cámara del capítulo, para el LED
    <capitulo>.blend         la escena, para retocar a mano

Qué lo hace "hiperreal" (y dónde se paga):
  · Cielo físico con dispersión múltiple + sol con disco del tamaño real (sombras con penumbra).
  · Niebla volumétrica en el aire (rayos de luz entre las copas del Dicroidium).  → costo alto
  · Terreno con desplazamiento real + barro, arena, charcos y hojarasca por máscara de hábitat.
  · Agua con transmisión, IOR 1,33, absorción volumétrica (río turbio de llanura) y ondas.
  · Vegetación por instancias con Geometry Nodes: miles de plantas sin duplicar memoria.
  · Cámara de 35 mm a la altura de los ojos, con profundidad de campo real.
  · Los dinosaurios son los GLB de Meshy (o los de la Mac) puestos en sus lugares. Sin modelo,
    queda el lugar marcado: un dinosaurio procedural rompería el hiperrealismo.

Calidades:
  prueba  960×540,   24 muestras, sin niebla volumétrica   (CPU en la nube: ~1–3 min por cuadro)
  media   1920×1080, 128 muestras                          (M4 Metal / OMEN OptiX)
  final   1920×1080, 512 muestras
  led     5760×1080, 384 muestras  (las 3 pantallas del proyecto de la Mac)
"""

import argparse
import math
import os
import random
import sys

import bpy
import bmesh  # noqa: E402  (después de bpy)
from mathutils import Vector, noise

AQUI = os.path.dirname(os.path.abspath(__file__))
CALIDADES = {
    "prueba": (960, 540, 24, False),
    "media": (1920, 1080, 128, True),
    "final": (1920, 1080, 512, True),
    "led": (5760, 1080, 384, True),
}

# ------------------------------------------------------------------------------------------
# la misma geografía que la experiencia web (ver experiencia/src/mundo.js)
# web (x, y, z) con y arriba  →  Blender (x, -z, y) con z arriba
# ------------------------------------------------------------------------------------------

NIVEL_AGUA = -1.1


def lisa(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def fbm2(x, y, octavas=5):
    t, a, f, n = 0.0, 1.0, 1.0, 0.0
    for _ in range(octavas):
        t += a * noise.noise(Vector((x * f, y * f, 0.37)))
        n += a
        a *= 0.5
        f *= 2.03
    return t / n


def cauce(x):
    return 10 * math.sin(x * 0.035) + 4 * math.sin(x * 0.09 + 1.3)


def hay_rio(x):
    return lisa(40, 5, x)


def dist_rio(x, zw):
    return abs(zw - cauce(x))


def altura_web(x, zw):
    d, rio = dist_rio(x, zw), hay_rio(x)
    h = fbm2(x * 0.012, zw * 0.012, 5) * 7 + fbm2(x * 0.08, zw * 0.08, 3) * 0.5
    h *= 1 - 0.8 * rio * math.exp(-((d / 30) ** 2))
    h -= rio * 3.0 * math.exp(-((d / 6) ** 2))
    h += rio * 0.5 * math.exp(-(((d - 11) / 3) ** 2))
    h *= 1 - 0.65 * lisa(60, 95, x)
    for cx, cz, r in ((100, 18, 9), (125, -22, 7)):
        h -= 1.8 * math.exp(-(((x - cx) ** 2 + (zw - cz) ** 2) / (r * r)))
    borde = max(lisa(80, 118, abs(zw)), lisa(140, 170, x) * (1 - quebrada_volcan(x, zw)), lisa(-100, -130, x))
    h += borde * 22 * (0.7 + 0.3 * fbm2(x * 0.05, zw * 0.05, 2))
    return h


# El cordón de 22 m que cierra el mundo por x > 140 tapaba el volcán desde la llanura (el
# problema de las pruebas del 28/09). Acá se le abre una quebrada en la línea de vista hacia
# el cráter: desde la manada se ve la montaña entera y el borde sigue cerrando el resto.
# Sólo en Blender: la web tiene su propia copia del relieve y no se ve el volcán a ras del suelo.
LLANURA_OJO = (103.0, 14.0)
VOLCAN_WEB = (1100.0, -700.0)


def quebrada_volcan(x, zw):
    ox, oz = LLANURA_OJO
    dx, dz = VOLCAN_WEB[0] - ox, VOLCAN_WEB[1] - oz
    largo = math.hypot(dx, dz)
    ux, uz = dx / largo, dz / largo
    t = (x - ox) * ux + (zw - oz) * uz          # avance sobre la línea de vista
    d = abs((x - ox) * uz - (zw - oz) * ux)     # distancia a esa línea
    return lisa(20, 45, t) * math.exp(-((d / (18 + 0.25 * max(t, 0))) ** 2))


MODO = {"hoy": False}


def altura_hoy(x, zw):
    """Valle de la Luna hoy: lomas bajas y redondeadas de arcilla gris (la Formación
    Ischigualasto erosionada), sin el río ni el cordón del Triásico."""
    lomas = max(0.0, fbm2(x * 0.035 + 11, zw * 0.035, 4)) ** 1.6 * 9
    return fbm2(x * 0.012, zw * 0.012, 4) * 2.5 + lomas


def altura(x, zw):
    if MODO["hoy"]:
        return altura_hoy(x, zw)
    return altura_web(x, zw)


def zona(x):
    return "rio" if x < 10 else "bosque" if x < 70 else "llanura"


def web_a_blender(p):
    x, y, z = p
    return Vector((x, -z, y))


# los capítulos: mismas cámaras que la web + la luz de cada momento
CAPITULOS = {
    "titulo":  dict(desde=(-120, 26, 60), hasta=(-95, 14, 40), mira=(-60, 0, 0), sol=(6, 250), bruma=0.0025, ceniza=0, volcan=0.2),
    "rio":     dict(desde=(-95, 3.2, 26), hasta=(-30, 2.6, 20), mira=(0, 0, -10), sol=(22, 230), bruma=0.0018, ceniza=0, volcan=0.3),
    "bosque":  dict(desde=(8, 2.2, 12), hasta=(62, 2.2, -4), mira=(120, 1, -20), sol=(40, 200), bruma=0.0035, ceniza=0, volcan=0.4),
    # llanura: la cámara a la altura de los ojos junto a la manada, mirando por la quebrada
    # al volcán; el punto de mira baja al tercio inferior del cono para que entre la columna
    "llanura": dict(desde=(92, 3.4, 19), hasta=(114, 3.6, 9), mira=(1100, 150, -700), sol=(30, 160), bruma=0.0012, ceniza=0, volcan=1, foco=16),
    "ceniza":  dict(desde=(128, 3.4, 4), hasta=(118, 5, 16), mira=(104, 0, -4), sol=(14, 170), bruma=0.012, ceniza=1, volcan=1),
    # hoy: parado en la arcilla gris cuarteada, las barrancas rojas al fondo, sol alto y
    # cielo limpio de San Juan (sin bruma: el aire del desierto es seco y transparente)
    "hoy":     dict(desde=(118, 2.2, 16), hasta=(100, 2.6, 22), mira=(-120, 25, 40), sol=(62, 120), bruma=0.0, ceniza=0, volcan=0, hoy=True, foco=40, f=8),
}

ESPECIES_LUGARES = {
    # especie: [(x_web, z_web, rumbo)]  (mismos lugares que la población de la web)
    "hyperodapedon": [(-60, None, 0.3), (-57, None, 1.2), (-63, None, 2.4), (-20, None, 0.8), (-24, None, 1.9)],
    "herrerasaurus": [(35, -8, 2.8), (110, 10, 3.6)],
    "eoraptor": [(28, 6, 0.4), (31, 3, 0.9), (26, 9, 5.9)],
    "panphagia": [(45, 15, 1.1)],
    "ischigualastia": [(114, 6.5, 2.4), (118.5, 4.5, 2.1), (121, 8.5, 2.6)],
    "eodromaeus": [(50, -10, 4.0)],
    "sanjuansaurus": [(128, -2.5, 5.4)],
}


# ------------------------------------------------------------------------------------------
# utilidades
# ------------------------------------------------------------------------------------------

def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--capitulos", nargs="*", default=list(CAPITULOS))
    ap.add_argument("--calidad", default="prueba", choices=list(CALIDADES))
    ap.add_argument("--animar", action="store_true", help="renderizar el recorrido de cámara (frames)")
    ap.add_argument("--segundos", type=float, default=10.0)
    ap.add_argument("--assets", default=os.path.join(AQUI, "..", "triasico", "salida", "assets"),
                    help="flora horneada (salida de construir_triasico.py)")
    ap.add_argument("--modelos", default=os.path.join(AQUI, "..", "..", "modelos"),
                    help="modelos de Meshy refinados (salida de correr_todo.py)")
    return ap.parse_args(argv)


def nodo(nt, tipo, **kw):
    n = nt.nodes.new(tipo)
    for k, v in kw.items():
        setattr(n, k, v)
    return n


def sal(n, *nombres):
    for x in nombres:
        if x in n.outputs:
            return n.outputs[x]
    return n.outputs[0]


# ------------------------------------------------------------------------------------------
# terreno hiperreal
# ------------------------------------------------------------------------------------------

def terreno(centro_x, centro_zw, lado=220.0, paso=0.5, hoy=False, ceniza=0.0):
    """Terreno alrededor del capítulo (no el mundo entero: a 0,5 m por vértice, el mundo
    entero serían 290.000 caras que no se ven). Máscaras de hábitat en un color de vértice."""
    n = int(lado / paso)
    bm = bmesh.new()
    capa = bm.loops.layers.color.new("habitat")
    verts, datos = [], {}
    for j in range(n + 1):
        fila = []
        for i in range(n + 1):
            x = centro_x - lado / 2 + i * paso
            zw = centro_zw - lado / 2 + j * paso
            h = altura(x, zw)
            d, rio = dist_rio(x, zw), hay_rio(x)
            humedo = rio * math.exp(-((d / 9) ** 2))
            arena = rio * math.exp(-(((d - 7) / 2.2) ** 2)) * (0.6 + 0.4 * fbm2(x * 0.2, zw * 0.2, 2))
            veg = max(0.0, min(1.0, 0.45 + fbm2(x * 0.05, zw * 0.05, 3) * 1.6 - humedo)) * (1.0 if 8 < x < 75 else 0.55)
            fila.append(bm.verts.new((x, -zw, h)))
            datos[(i, j)] = (humedo, arena, veg)
        verts.append(fila)
    for j in range(n):
        for i in range(n):
            f = bm.faces.new((verts[j][i], verts[j + 1][i], verts[j + 1][i + 1], verts[j][i + 1]))
            f.smooth = True
            for lp, k in zip(f.loops, ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))):
                h_, a_, v_ = datos[k]
                lp[capa] = (h_, a_, v_, 1.0)
    me = bpy.data.meshes.new("terreno")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("terreno", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material_suelo(hoy, ceniza))
    return ob


def horizonte(cx, czw, material):
    """Anillo de terreno lejano y barato (hasta 3 km) para que el horizonte no muestre el vacío
    debajo del cielo: el terreno detallado mide 240 m y la cámara ve mucho más lejos."""
    bm = bmesh.new()
    anillos = []
    for r in (100, 180, 320, 600, 1100, 3000):
        fila = []
        for k in range(128):
            a = 2 * math.pi * k / 128
            x, zw = cx + r * math.cos(a), czw + r * math.sin(a)
            h = altura(x, zw) if r < 700 else 18 + fbm2(x * 0.004, zw * 0.004, 3) * 60
            fila.append(bm.verts.new((x, -zw, h - (0.8 if r == 100 else 0))))
        anillos.append(fila)
    for i in range(len(anillos) - 1):
        for k in range(128):
            k2 = (k + 1) % 128
            bm.faces.new((anillos[i][k], anillos[i][k2], anillos[i + 1][k2], anillos[i + 1][k]))
    me = bpy.data.meshes.new("horizonte")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("horizonte", me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    ob.data.materials.append(material)
    return ob


def material_suelo(hoy=False, ceniza=0.0):
    m = bpy.data.materials.new("suelo_triasico")
    m.use_nodes = True
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    n.clear()
    out = nodo(nt, "ShaderNodeOutputMaterial")
    bs = nodo(nt, "ShaderNodeBsdfPrincipled")
    l.new(bs.outputs[0], out.inputs["Surface"])
    tc = nodo(nt, "ShaderNodeTexCoord")
    at = nodo(nt, "ShaderNodeVertexColor", layer_name="habitat")
    sep = nodo(nt, "ShaderNodeSeparateColor")
    l.new(at.outputs["Color"], sep.inputs[0])
    hum, are, veg = sep.outputs[0], sep.outputs[1], sep.outputs[2]

    def ruido(escala, detalle=8, rug=0.55):
        r = nodo(nt, "ShaderNodeTexNoise")
        r.inputs["Scale"].default_value = escala
        r.inputs["Detail"].default_value = detalle
        r.inputs["Roughness"].default_value = rug
        l.new(tc.outputs["Object"], r.inputs["Vector"])
        return r

    def mezcla(fac, a, b, tipo="MIX"):
        x = nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type=tipo)
        if isinstance(fac, float):
            x.inputs["Factor"].default_value = fac
        else:
            l.new(fac, x.inputs["Factor"])
        for sock, val in (("A", a), ("B", b)):
            if isinstance(val, tuple):
                x.inputs[sock].default_value = (*val, 1)
            else:
                l.new(val, x.inputs[sock])
        return x.outputs["Result"]

    macro = ruido(0.08, 6)
    micro = ruido(3.5, 12, 0.7)
    grano = ruido(28, 4)
    # barro: variación grande y chica
    barro = mezcla(sal(macro, "Factor", "Fac"), (0.19, 0.13, 0.085), (0.29, 0.21, 0.14))
    barro = mezcla(sal(micro, "Factor", "Fac"), barro, (0.15, 0.10, 0.07), "MULTIPLY")
    # hojarasca: manchones de hojas secas y verdes (Voronoi = hojas sueltas)
    hojas = nodo(nt, "ShaderNodeTexVoronoi")
    hojas.inputs["Scale"].default_value = 22
    l.new(tc.outputs["Object"], hojas.inputs["Vector"])
    color_hoja = mezcla(sal(hojas, "Distance"), (0.30, 0.22, 0.10), (0.12, 0.16, 0.06))
    suelo = mezcla(veg, barro, color_hoja)
    suelo = mezcla(are, suelo, (0.55, 0.45, 0.32))
    suelo = mezcla(hum, suelo, (0.07, 0.055, 0.04))
    if hoy:
        # Valle de la Luna: arcilla gris clara cuarteada. Las grietas se ven por la sombra de
        # adentro (color), no sólo por el relieve: con sol alto el bump solo casi no se nota.
        suelo = mezcla(0.95, suelo, (0.50, 0.47, 0.43))
        manchas = ruido(0.05, 5)
        suelo = mezcla(sal(manchas, "Factor", "Fac"), (0.40, 0.42, 0.38), (0.56, 0.49, 0.40))   # gris verdoso ↔ ocre
        suelo = mezcla(sal(micro, "Factor", "Fac"), suelo, (0.44, 0.41, 0.37), "MULTIPLY")
        placas = nodo(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
        placas.inputs["Scale"].default_value = 2.4
        l.new(tc.outputs["Object"], placas.inputs["Vector"])
        borde = nodo(nt, "ShaderNodeMapRange")
        borde.inputs["From Min"].default_value, borde.inputs["From Max"].default_value = 0.0, 0.035
        borde.inputs["To Min"].default_value, borde.inputs["To Max"].default_value = 1.0, 0.0
        l.new(sal(placas, "Distance"), borde.inputs["Value"])
        suelo = mezcla(borde.outputs[0], suelo, (0.12, 0.105, 0.09))
    if ceniza:
        suelo = mezcla(min(1.0, ceniza) * 0.9, suelo, (0.46, 0.45, 0.43))
    # texturas escaneadas CC0 (bajar_texturas_cc0.py): si están, reemplazan lo procedural
    cc0 = os.path.join(AQUI, "texturas_cc0")
    normales = []
    for rol, mascara in (("barro", None), ("hojarasca", veg), ("arena", are), ("arcilla", "hoy" if hoy else None)):
        tex = imagen_pbr(nt, tc, os.path.join(cc0, rol), escala=0.35)
        if not tex:
            continue
        if mascara is None:
            suelo = mezcla(0.85, suelo, tex["color"])
        elif mascara == "hoy":
            suelo = mezcla(0.95, suelo, tex["color"])
        else:
            suelo = mezcla(mascara, suelo, tex["color"])
        if "normal" in tex:
            normales.append(tex["normal"])
    l.new(suelo, bs.inputs["Base Color"])
    # rugosidad: barro seco mate, húmedo casi espejo (charcos)
    rug = nodo(nt, "ShaderNodeMapRange")
    rug.inputs["To Min"].default_value, rug.inputs["To Max"].default_value = 0.9, 0.08
    l.new(hum, rug.inputs["Value"])
    l.new(rug.outputs[0], bs.inputs["Roughness"])
    # relieve fino: grietas de barro + grano + hojas
    grietas = nodo(nt, "ShaderNodeTexVoronoi", feature="DISTANCE_TO_EDGE")
    grietas.inputs["Scale"].default_value = 1.6 if not hoy else 2.4
    l.new(tc.outputs["Object"], grietas.inputs["Vector"])
    gr = nodo(nt, "ShaderNodeMapRange")
    gr.inputs["From Max"].default_value = 0.05
    l.new(sal(grietas, "Distance"), gr.inputs["Value"])
    suma = nodo(nt, "ShaderNodeMath", operation="ADD")
    l.new(gr.outputs[0], suma.inputs[0])
    l.new(sal(grano, "Factor", "Fac"), suma.inputs[1])
    b = nodo(nt, "ShaderNodeBump")
    b.inputs["Strength"].default_value = 0.45
    b.inputs["Distance"].default_value = 0.02
    l.new(suma.outputs[0], b.inputs["Height"])
    if normales:
        l.new(normales[0], b.inputs["Normal"])       # el relieve fino se suma a la normal escaneada
    l.new(b.outputs["Normal"], bs.inputs["Normal"])
    return m


def imagen_pbr(nt, tc, carpeta, escala=0.5):
    """Color + normal de una textura escaneada, proyectada desde arriba en metros (escala = repeticiones por metro)."""
    if not os.path.isdir(carpeta):
        return None
    def archivo(n):
        for ext in (".jpg", ".png"):
            p = os.path.join(carpeta, n + ext)
            if os.path.exists(p):
                return p
    if not archivo("color"):
        return None
    mp = nodo(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (escala, escala, escala)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    res = {}
    for n in ("color", "normal"):
        p = archivo(n)
        if not p:
            continue
        im = nodo(nt, "ShaderNodeTexImage")
        im.image = bpy.data.images.load(p, check_existing=True)
        if n != "color":
            im.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs[0], im.inputs["Vector"])
        if n == "normal":
            nm = nodo(nt, "ShaderNodeNormalMap")
            nt.links.new(im.outputs["Color"], nm.inputs["Color"])
            res["normal"] = nm.outputs["Normal"]
        else:
            res["color"] = im.outputs["Color"]
    return res


def agua(centro_x, centro_zw, lado=220.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(centro_x, -centro_zw, NIVEL_AGUA - 1.5))
    ob = bpy.context.object
    ob.name = "agua"
    ob.scale = (lado, lado, 3.0)
    m = bpy.data.materials.new("rio_turbio")
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value = (0.8, 0.85, 0.8, 1)
    bs.inputs["Roughness"].default_value = 0.03
    bs.inputs["IOR"].default_value = 1.33
    for k in ("Transmission Weight", "Transmission"):
        if k in bs.inputs:
            bs.inputs[k].default_value = 1.0
    # ondas: ruido estirado en la dirección de la corriente
    tc = nodo(nt, "ShaderNodeTexCoord")
    mp = nodo(nt, "ShaderNodeMapping")
    mp.inputs["Scale"].default_value = (0.4, 1.6, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    ru = nodo(nt, "ShaderNodeTexNoise")
    ru.inputs["Scale"].default_value = 40
    ru.inputs["Detail"].default_value = 6
    nt.links.new(mp.outputs[0], ru.inputs["Vector"])
    bp = nodo(nt, "ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.12
    nt.links.new(sal(ru, "Factor", "Fac"), bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], bs.inputs["Normal"])
    # absorción: el color del río sale de la profundidad, no de pintar la superficie
    vol = nodo(nt, "ShaderNodeVolumeAbsorption")
    vol.inputs["Color"].default_value = (0.35, 0.30, 0.18, 1)
    vol.inputs["Density"].default_value = 0.9
    nt.links.new(vol.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
    ob.data.materials.append(m)
    return ob


# ------------------------------------------------------------------------------------------
# hoy: barrancas coloradas con estratos
# ------------------------------------------------------------------------------------------

def material_estratos():
    """Areniscas y limolitas rojas en capas horizontales (Formación Los Colorados): bandas por
    altura, torcidas apenas con ruido para que no parezcan pintadas con regla."""
    m = bpy.data.materials.new("estratos_colorados")
    m.use_nodes = True
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    bs = n["Principled BSDF"]
    tc = nodo(nt, "ShaderNodeTexCoord")
    sep = nodo(nt, "ShaderNodeSeparateXYZ")
    l.new(tc.outputs["Object"], sep.inputs[0])
    tuerce = nodo(nt, "ShaderNodeTexNoise")
    tuerce.inputs["Scale"].default_value = 0.02
    tuerce.inputs["Detail"].default_value = 3
    l.new(tc.outputs["Object"], tuerce.inputs["Vector"])
    suma = nodo(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
    l.new(sal(tuerce, "Factor", "Fac"), suma.inputs[0])
    suma.inputs[1].default_value = 6.0
    l.new(sep.outputs["Z"], suma.inputs[2])
    capas = nodo(nt, "ShaderNodeTexNoise")          # 1D en altura: bandas de espesor irregular
    capas.noise_dimensions = "1D"
    capas.inputs["Scale"].default_value = 0.09
    capas.inputs["Detail"].default_value = 6
    capas.inputs["Roughness"].default_value = 0.6
    l.new(suma.outputs[0], capas.inputs["W"])
    rampa = nodo(nt, "ShaderNodeValToRGB")
    cr = rampa.color_ramp
    cr.interpolation = "CONSTANT"
    colores = [(0.0, (0.30, 0.075, 0.035)), (0.36, (0.42, 0.12, 0.05)), (0.46, (0.55, 0.28, 0.13)),
               (0.53, (0.36, 0.10, 0.05)), (0.60, (0.62, 0.45, 0.32)), (0.64, (0.40, 0.13, 0.06)),
               (0.75, (0.25, 0.07, 0.04))]
    cr.elements[0].position, cr.elements[0].color = colores[0][0], (*colores[0][1], 1)
    cr.elements[1].position, cr.elements[1].color = colores[1][0], (*colores[1][1], 1)
    for pos, col in colores[2:]:
        e = cr.elements.new(pos)
        e.color = (*col, 1)
    l.new(sal(capas, "Factor", "Fac"), rampa.inputs[0])
    sucio = nodo(nt, "ShaderNodeTexNoise")
    sucio.inputs["Scale"].default_value = 0.6
    sucio.inputs["Detail"].default_value = 10
    l.new(tc.outputs["Object"], sucio.inputs["Vector"])
    mx = nodo(nt, "ShaderNodeMix", data_type="RGBA", blend_type="MULTIPLY")
    mx.inputs["Factor"].default_value = 0.35
    l.new(rampa.outputs["Color"], mx.inputs["A"])
    l.new(sal(sucio, "Color"), mx.inputs["B"])
    l.new(mx.outputs["Result"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.92
    bump = nodo(nt, "ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    l.new(sal(sucio, "Factor", "Fac"), bump.inputs["Height"])
    l.new(bump.outputs["Normal"], bs.inputs["Normal"])
    return m


def barrancas(ojo, mira, distancia=230.0, abertura=80.0):
    """Paredón rojo frente a la cámara: perfil de acantilado (talud, pared, cornisa, meseta)
    con cárcavas verticales de erosión que lo meten y lo sacan."""
    ox, oz = ojo
    rumbo = math.atan2(mira[1] - oz, mira[0] - ox)
    columnas = 260
    bm = bmesh.new()
    filas = []
    perfil = [(-55, 0.0), (-28, 0.10), (-10, 0.22), (0, 0.32), (2, 0.55), (4, 0.80), (7, 0.97), (12, 1.0), (90, 0.93)]
    for c in range(columnas):
        a = rumbo + math.radians(-abertura + 2 * abertura * c / (columnas - 1))
        carcava = abs(fbm2(c * 0.09, 3.3, 3)) * 2.2
        alto = 38 + fbm2(c * 0.025, 9.1, 3) * 26
        r0 = distancia + fbm2(c * 0.02, 1.7, 3) * 60 + carcava * 14
        col = []
        for dr, fh in perfil:
            r = r0 + dr * (1 + 0.4 * carcava)
            x, zw = ox + r * math.cos(a), oz + r * math.sin(a)
            base = altura(x, zw) - 1.0
            col.append(bm.verts.new((x, -zw, base + fh * alto * (1 - 0.18 * carcava * (fh < 0.99)))))
        filas.append(col)
    for c in range(columnas - 1):
        for k in range(len(perfil) - 1):
            f = bm.faces.new((filas[c][k], filas[c + 1][k], filas[c + 1][k + 1], filas[c][k + 1]))
            f.smooth = True
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    me = bpy.data.meshes.new("barrancas")
    bm.to_mesh(me)
    bm.free()
    # un poco de relieve de roca a escala de metros, que la subdivisión deja lugar
    for v in me.vertices:
        v.co += Vector((fbm2(v.co.y * 0.3, v.co.z * 0.3, 3), fbm2(v.co.x * 0.3, v.co.z * 0.3 + 5, 3), 0)) * 1.8
    ob = bpy.data.objects.new("barrancas", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(material_estratos())
    return ob


# ------------------------------------------------------------------------------------------
# cielo, sol, niebla, volcán
# ------------------------------------------------------------------------------------------

def cielo(elevacion, azimut, bruma, volumetrica, ceniza, limpio=False):
    esc = bpy.context.scene
    w = bpy.data.worlds.new("cielo_triasico")
    esc.world = w
    w.use_nodes = True
    nt = w.node_tree
    sky = nodo(nt, "ShaderNodeTexSky")
    for tipo in ("MULTIPLE_SCATTERING", "NISHITA"):
        try:
            sky.sky_type = tipo
            break
        except TypeError:
            continue
    sky.sun_elevation = math.radians(elevacion)
    sky.sun_rotation = math.radians(azimut)
    sky.sun_size = math.radians(0.545)                  # el sol de verdad: medio grado
    sky.sun_disc = False          # el sol lo pone la lámpara: con los dos, la luz se duplica y se quema
    try:
        sky.air_density = 1.0
        sky.aerosol_density = 0.35 if limpio else 1.5 + 6 * ceniza   # la ceniza vuelve el aire lechoso
        if limpio:
            sky.ozone_density = 1.4        # un poco más de ozono = el azul profundo del cielo de altura
    except AttributeError:
        pass
    bg = nt.nodes["Background"]
    bg.inputs["Strength"].default_value = 0.12 * (1 - 0.6 * ceniza)
    nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
    if volumetrica and bruma > 0:
        # niebla en el aire: los rayos de sol entre las copas. Es lo más caro del render.
        pv = nodo(nt, "ShaderNodeVolumePrincipled")
        pv.inputs["Density"].default_value = bruma
        pv.inputs["Color"].default_value = (0.85, 0.82, 0.78, 1) if not ceniza else (0.55, 0.52, 0.5, 1)
        pv.inputs["Anisotropy"].default_value = 0.45
        nt.links.new(pv.outputs[0], nt.nodes["World Output"].inputs["Volume"])
    # el sol como lámpara (sombras nítidas con penumbra real) alineado con el del cielo
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = 3.0 * (1 - 0.65 * ceniza)
    sol.data.angle = math.radians(0.545)
    sol.data.color = (1.0, 0.92, 0.82) if elevacion > 15 else (1.0, 0.72, 0.48)
    sol.rotation_euler = (math.radians(90 - elevacion), 0, math.radians(azimut + 90))
    esc.collection.objects.link(sol)


def volcan(actividad):
    pos = web_a_blender((1100, -30, -700))      # lejos: en el horizonte, no encima del bosque
    bm = bmesh.new()
    perfil = [(r * 2.2, h * 2.2) for r, h in [(260, 0), (225, 18), (190, 40), (150, 68), (110, 95),
                                               (80, 113), (55, 125), (38, 122)]]
    anillos = []
    for r, h in perfil:
        anillos.append([bm.verts.new((pos.x + r * math.cos(a), pos.y + r * math.sin(a), pos.z + h))
                        for a in (2 * math.pi * k / 256 for k in range(256))])
    for i in range(len(anillos) - 1):
        for k in range(256):
            k2 = (k + 1) % 256
            bm.faces.new((anillos[i][k], anillos[i][k2], anillos[i + 1][k2], anillos[i + 1][k]))
    me = bpy.data.meshes.new("volcan")
    bm.to_mesh(me)
    bm.free()
    for v in me.vertices:
        # cárcavas radiales (la lluvia y los lahares bajan por la ladera) + relieve irregular
        ang = math.atan2(v.co.y - pos.y, v.co.x - pos.x)
        r = math.hypot(v.co.x - pos.x, v.co.y - pos.y)
        surcos = abs(fbm2(ang * 9.0, 0.3, 3)) * min(1.0, r / 150) * 18
        v.co.z += fbm2(v.co.x * 0.01, v.co.y * 0.01, 4) * 40 - surcos
    ob = bpy.data.objects.new("volcan", me)
    bpy.context.scene.collection.objects.link(ob)
    mat = bpy.data.materials.new("basalto")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.045, 0.04, 1)
    mat.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    ob.data.materials.append(mat)
    if actividad > 0.1:
        # columna de ceniza: un cono que se abre hacia arriba (la pluma se expande al subir),
        # con ruido en coordenadas generadas (0-1 en la caja del objeto) y no en metros: en
        # metros el ruido era tan fino que se promediaba a casi nada y la columna no se veía.
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=80, radius2=560, depth=1100,
                                        location=(pos.x + 60, pos.y, pos.z + 262 + 550))
        col = bpy.context.object
        col.name = "columna_ceniza"
        # el viento de altura inclina la pluma: la parte de arriba se corre a sotavento
        for v in col.data.vertices:
            k = (v.co.z + 550) / 1100
            v.co.x += 380 * k * k
        mv = bpy.data.materials.new("humo_volcan")
        mv.use_nodes = True
        nt = mv.node_tree
        nt.nodes.remove(nt.nodes["Principled BSDF"])
        pv = nodo(nt, "ShaderNodeVolumePrincipled")
        pv.inputs["Color"].default_value = (0.42, 0.39, 0.36, 1)      # ceniza iluminada: gris pardo
        tc = nodo(nt, "ShaderNodeTexCoord")
        ru = nodo(nt, "ShaderNodeTexNoise")
        ru.inputs["Scale"].default_value = 3.5
        ru.inputs["Detail"].default_value = 10
        ru.inputs["Roughness"].default_value = 0.62
        nt.links.new(tc.outputs["Generated"], ru.inputs["Vector"])
        dens = nodo(nt, "ShaderNodeMapRange")
        dens.inputs["From Min"].default_value, dens.inputs["From Max"].default_value = 0.32, 0.68
        dens.inputs["To Max"].default_value = 0.10 * actividad
        nt.links.new(sal(ru, "Factor", "Fac"), dens.inputs["Value"])
        # más densa abajo, junto al cráter, y rala arriba
        sep = nodo(nt, "ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Generated"], sep.inputs[0])
        caida = nodo(nt, "ShaderNodeMapRange")
        caida.inputs["To Min"].default_value, caida.inputs["To Max"].default_value = 1.0, 0.25
        nt.links.new(sep.outputs["Z"], caida.inputs["Value"])
        por = nodo(nt, "ShaderNodeMath", operation="MULTIPLY")
        nt.links.new(dens.outputs[0], por.inputs[0])
        nt.links.new(caida.outputs[0], por.inputs[1])
        # bordes blandos: la densidad se apaga hacia la pared del cono, así no se ve el embudo
        centro = nodo(nt, "ShaderNodeVectorMath", operation="SUBTRACT")
        centro.inputs[1].default_value = (0.5, 0.5, 0.0)
        nt.links.new(tc.outputs["Generated"], centro.inputs[0])
        plano = nodo(nt, "ShaderNodeVectorMath", operation="MULTIPLY")
        plano.inputs[1].default_value = (1.0, 1.0, 0.0)
        nt.links.new(centro.outputs[0], plano.inputs[0])
        radio = nodo(nt, "ShaderNodeVectorMath", operation="LENGTH")
        nt.links.new(plano.outputs[0], radio.inputs[0])
        # el cono se abre: arriba el borde está en r=0,5, abajo en r≈0,08 → el radio útil crece con Z
        lim = nodo(nt, "ShaderNodeMath", operation="MULTIPLY_ADD")
        nt.links.new(sep.outputs["Z"], lim.inputs[0])
        lim.inputs[1].default_value, lim.inputs[2].default_value = 0.40, 0.08
        rel = nodo(nt, "ShaderNodeMath", operation="DIVIDE")
        nt.links.new(sal(radio, "Value"), rel.inputs[0])
        nt.links.new(lim.outputs[0], rel.inputs[1])
        borde = nodo(nt, "ShaderNodeMapRange")
        borde.inputs["From Min"].default_value, borde.inputs["From Max"].default_value = 0.35, 1.0
        borde.inputs["To Min"].default_value, borde.inputs["To Max"].default_value = 1.0, 0.0
        nt.links.new(rel.outputs[0], borde.inputs["Value"])
        por2 = nodo(nt, "ShaderNodeMath", operation="MULTIPLY")
        nt.links.new(por.outputs[0], por2.inputs[0])
        nt.links.new(borde.outputs[0], por2.inputs[1])
        nt.links.new(por2.outputs[0], pv.inputs["Density"])
        nt.links.new(pv.outputs[0], nt.nodes["Material Output"].inputs["Volume"])
        col.data.materials.append(mv)


# ------------------------------------------------------------------------------------------
# vegetación por instancias (Geometry Nodes)
# ------------------------------------------------------------------------------------------

REGLAS = [
    ("neocalamites", 8.0, lambda x, z: hay_rio(x) > 0.5 and 6.5 < dist_rio(x, z) < 15, (0.8, 1.3)),
    ("dicroidium", 1.2, lambda x, z: hay_rio(x) > 0.5 and dist_rio(x, z) > 16, (0.8, 1.25)),
    ("dicroidium", 4.0, lambda x, z: zona(x) == "bosque", (0.8, 1.4)),     # un árbol cada ~25 m²
    ("dicroidium", 0.08, lambda x, z: zona(x) == "llanura", (0.7, 1.0)),
    ("conifera", 0.8, lambda x, z: zona(x) == "bosque" or (zona(x) == "llanura" and abs(z) > 35), (0.8, 1.3)),
    ("helecho", 22.0, lambda x, z: zona(x) != "llanura" and dist_rio(x, z) > 8, (0.6, 1.5)),
    ("helecho", 1.0, lambda x, z: zona(x) == "llanura", (0.5, 1.0)),
    ("tronco_caido", 0.15, lambda x, z: zona(x) == "bosque" or (hay_rio(x) > 0.5 and 8 < dist_rio(x, z) < 14), (0.8, 1.3)),
    ("roca_arenisca", 0.5, lambda x, z: zona(x) == "llanura", (0.4, 1.8)),
]


def cargar_molde(carpeta, nombre, carpeta_meshy=None):
    """Lo mejor que haya: la planta de Meshy (…/modelos/<nombre>_meshy/) y si no, la procedural."""
    ruta = None
    if carpeta_meshy:
        cand = os.path.join(carpeta_meshy, f"{nombre}_meshy", f"{nombre}_meshy_alto.glb")
        ruta = cand if os.path.exists(cand) else None
    ruta = ruta or os.path.join(carpeta, nombre, f"{nombre}_alto.glb")
    if not os.path.exists(ruta):
        return None
    print(f"   flora {nombre}: {'MESHY' if '_meshy' in ruta else 'procedural'}", flush=True)
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    nuevos = [o for o in bpy.data.objects if o not in antes and o.type == "MESH"]
    for o in bpy.data.objects:
        if o not in antes and o.type != "MESH":
            bpy.data.objects.remove(o)
    m = nuevos[0]
    m.name = f"molde_{nombre}"
    m.location = (0, 0, -1000)
    m.hide_render = True
    return m


def arbol_gn(molde):
    """Árbol de nodos: una instancia del molde por punto, con rotación y escala del punto."""
    t = bpy.data.node_groups.new(f"sembrar_{molde.name}", "GeometryNodeTree")
    t.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    t.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ent = t.nodes.new("NodeGroupInput")
    sal_ = t.nodes.new("NodeGroupOutput")
    info = t.nodes.new("GeometryNodeObjectInfo")
    info.inputs["Object"].default_value = molde
    info.transform_space = "ORIGINAL"
    pts = t.nodes.new("GeometryNodeMeshToPoints")
    inst = t.nodes.new("GeometryNodeInstanceOnPoints")
    rot = t.nodes.new("GeometryNodeInputNamedAttribute")
    rot.data_type = "FLOAT_VECTOR"
    rot.inputs["Name"].default_value = "rot"
    esc = t.nodes.new("GeometryNodeInputNamedAttribute")
    esc.data_type = "FLOAT"
    esc.inputs["Name"].default_value = "esc"
    t.links.new(ent.outputs[0], pts.inputs["Mesh"])
    t.links.new(pts.outputs[0], inst.inputs["Points"])
    t.links.new(info.outputs["Geometry"], inst.inputs["Instance"])
    t.links.new(rot.outputs["Attribute"], inst.inputs["Rotation"])
    t.links.new(esc.outputs["Attribute"], inst.inputs["Scale"])
    t.links.new(inst.outputs[0], sal_.inputs[0])
    return t


def sembrar(moldes, centro_x, centro_zw, lado, densidad_extra=1.0, hoy=False):
    """Puntos por especie (con reglas de hábitat) → un objeto de puntos con Geometry Nodes."""
    if hoy:
        return 0
    azar = random.Random(231)
    total = 0
    area_ha = (lado * lado) / 10000.0
    puntos = {}
    for nombre, por_100m2, regla, (e0, e1) in REGLAS:
        if nombre not in moldes:
            continue
        objetivo = int(por_100m2 * area_ha * 100 * densidad_extra)
        for _ in range(objetivo * 6):
            if len(puntos.get((nombre, regla), [])) >= objetivo:
                break
            x = centro_x - lado / 2 + azar.random() * lado
            zw = centro_zw - lado / 2 + azar.random() * lado
            if not regla(x, zw):
                continue
            h = altura(x, zw)
            if h < NIVEL_AGUA + 0.15:
                continue
            puntos.setdefault((nombre, regla), []).append((x, -zw, h - 0.05, azar.uniform(0, 6.283), azar.uniform(e0, e1),
                                                            azar.uniform(-0.06, 0.06)))
    por_nombre = {}
    for (nombre, _), lista in puntos.items():
        por_nombre.setdefault(nombre, []).extend(lista)
    for nombre, lista in por_nombre.items():
        me = bpy.data.meshes.new(f"puntos_{nombre}")
        me.vertices.add(len(lista))
        me.vertices.foreach_set("co", [c for p in lista for c in p[:3]])
        # OJO: crear un atributo reubica la memoria de los demás; una referencia vieja termina
        # escribiendo sobre las posiciones (pasó: todas las plantas quedaban en el origen).
        # Por eso cada atributo se crea, se toma por nombre y se escribe antes del siguiente.
        me.attributes.new("rot", "FLOAT_VECTOR", "POINT")
        me.attributes["rot"].data.foreach_set("vector", [c for p in lista for c in (p[5], p[5] * 0.5, p[3])])   # un poco torcidas
        me.attributes.new("esc", "FLOAT", "POINT")
        me.attributes["esc"].data.foreach_set("value", [p[4] for p in lista])
        me.vertices.foreach_set("co", [c for p in lista for c in p[:3]])     # y las posiciones al final, por las dudas
        me.update()
        ob = bpy.data.objects.new(f"flora_{nombre}", me)
        bpy.context.scene.collection.objects.link(ob)
        mod = ob.modifiers.new("sembrar", "NODES")
        mod.node_group = arbol_gn(moldes[nombre])
        total += len(lista)
    return total


# ------------------------------------------------------------------------------------------
# dinosaurios (Meshy o Mac) en sus lugares
# ------------------------------------------------------------------------------------------

def modelo_de(carpeta_modelos, especie):
    """El mejor modelo que haya de la especie: el de Meshy refinado (modelos/<especie>/) o el
    que se exportó de la Mac (modelos_mac/)."""
    for cand in (os.path.join(carpeta_modelos, especie, f"{especie}_alto.glb"),
                 os.path.join(carpeta_modelos, "..", "modelos_mac", f"{especie}_rt.glb")):
        if os.path.exists(cand):
            return cand
    return None


def coleccion_de(especie, ruta):
    """Importa el GLB una sola vez en una colección fuera de la escena. Cada lugar la usa como
    instancia: así viaja entera (armadura + malla hija) y no pesa en memoria."""
    antes = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    nuevos = [o for o in bpy.data.objects if o not in antes]
    col = bpy.data.collections.new(f"dino_{especie}")
    for o in nuevos:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    return col


def poner_dinosaurios(carpeta_modelos, cerca_x, radio=90):
    puestos, faltan = 0, set()
    colecciones = {}
    for especie, lugares in ESPECIES_LUGARES.items():
        for (x, zw, rumbo) in lugares:
            if abs(x - cerca_x) > radio:
                continue
            if zw is None:
                zw = cauce(x) + 9.5
            ruta = modelo_de(carpeta_modelos, especie)
            vacio = bpy.data.objects.new(f"SLOT_{especie}", None)
            vacio.empty_display_type = "SINGLE_ARROW"
            vacio.location = (x, -zw, altura(x, zw))
            vacio.rotation_euler.z = rumbo
            bpy.context.scene.collection.objects.link(vacio)
            if not ruta:
                faltan.add(especie)
                continue
            if especie not in colecciones:
                print(f"   {especie}: {os.path.relpath(ruta, carpeta_modelos)}", flush=True)
                colecciones[especie] = coleccion_de(especie, ruta)
            vacio.instance_type = "COLLECTION"
            vacio.instance_collection = colecciones[especie]
            puestos += 1
    return puestos, sorted(faltan)


# ------------------------------------------------------------------------------------------
# cámara y render
# ------------------------------------------------------------------------------------------

def camara(cap, cuadros, animar):
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    bpy.context.scene.collection.objects.link(cam)
    cam.data.lens = 35
    cam.data.sensor_width = 36
    # la cámara nueva corta a 1000 m: se comía la columna de ceniza (a 1,2 km) y el anillo de
    # horizonte (a 3 km). Hasta 8 km entra todo el mundo.
    cam.data.clip_start = 0.1
    cam.data.clip_end = 8000
    mira = web_a_blender(cap["mira"])
    desde, hasta = web_a_blender(cap["desde"]), web_a_blender(cap["hasta"])

    def ubicar(p):
        suelo = altura(p.x, -p.y)
        p.z = max(p.z, suelo + 1.7)
        cam.location = p
        cam.rotation_euler = (mira - p).to_track_quat("-Z", "Y").to_euler()

    if animar:
        for f in range(1, cuadros + 1):
            k = (f - 1) / max(1, cuadros - 1)
            e = k * k * (3 - 2 * k)
            ubicar(desde.lerp(hasta, e))
            cam.keyframe_insert("location", frame=f)
            cam.keyframe_insert("rotation_euler", frame=f)
    else:
        ubicar(desde.lerp(hasta, 0.5))
    # profundidad de campo: foco donde andan los animales cercanos (12 m salvo que el capítulo
    # diga otra cosa), f/4. En "hoy" la cámara mira un paisaje: foco lejos y f/8, todo nítido.
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = cap.get("foco", 12.0)
    cam.data.dof.aperture_fstop = cap.get("f", 4.0)
    bpy.context.scene.camera = cam
    return cam


def configurar_render(ancho, alto, muestras):
    esc = bpy.context.scene
    esc.render.engine = "CYCLES"
    gpu = os.environ.get("FNS_GPU")
    esc.cycles.device = "GPU" if gpu else "CPU"
    if gpu:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for tipo in ("OPTIX", "METAL", "CUDA", "HIP"):
            try:
                prefs.compute_device_type = tipo
                prefs.get_devices()
                for d in prefs.devices:
                    d.use = True
                break
            except TypeError:
                continue
    esc.cycles.samples = muestras
    esc.cycles.use_denoising = True
    esc.cycles.volume_step_rate = 4.0
    esc.cycles.max_bounces = 8
    esc.render.resolution_x, esc.render.resolution_y = ancho, alto
    esc.render.fps = 30
    esc.view_settings.view_transform = "AgX"
    try:
        esc.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    esc.view_settings.exposure = -0.8
    esc.render.film_transparent = False
    vl = esc.view_layers[0]
    vl.use_pass_mist = True
    esc.world.mist_settings.start = 2
    esc.world.mist_settings.depth = 400


def pase_profundidad(ruta):
    """Del pase de niebla (mist) a un PNG de profundidad: blanco = lejos. En TD sirve para que
    un dinosaurio en vivo quede detrás de un árbol del fondo renderizado."""
    esc = bpy.context.scene
    try:
        if hasattr(esc, "compositing_node_group"):          # Blender 5: el compositor es un grupo de nodos
            if esc.compositing_node_group is None:
                esc.compositing_node_group = bpy.data.node_groups.new("compositor", "CompositorNodeTree")
            nt = esc.compositing_node_group
        else:
            esc.use_nodes = True
            nt = esc.node_tree
    except Exception:
        return False
    rl = nt.nodes.new("CompositorNodeRLayers")
    arch = nt.nodes.new("CompositorNodeOutputFile")
    try:
        arch.base_path = os.path.dirname(ruta)
        arch.file_slots[0].path = os.path.basename(ruta).replace(".png", "_")
    except AttributeError:
        return False
    try:
        nt.links.new(rl.outputs["Mist"], arch.inputs[0])
        # la imagen principal también tiene que salir: en Blender 5 el grupo necesita su salida
        if hasattr(esc, "compositing_node_group"):
            if not any(s.name == "Image" for s in nt.interface.items_tree if getattr(s, "in_out", "") == "OUTPUT"):
                nt.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
            go = nt.nodes.new("NodeGroupOutput")
            nt.links.new(rl.outputs["Image"], go.inputs[0])
        else:
            comp = nt.nodes.new("CompositorNodeComposite")
            nt.links.new(rl.outputs["Image"], comp.inputs[0])
    except Exception as e:
        print("   pase de profundidad: no se pudo armar:", e)
        return False
    return True


def hacer_capitulo(clave, a):
    ancho, alto, muestras, volumetrica = CALIDADES[a.calidad]
    cap = CAPITULOS[clave]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    noise.seed_set(231)
    carpeta = os.path.join(os.path.abspath(a.salida), clave)
    os.makedirs(carpeta, exist_ok=True)

    centro = web_a_blender(cap["desde"]).lerp(web_a_blender(cap["hasta"]), 0.5)
    cx, czw = centro.x, -centro.y
    lado = 240.0 if clave != "hoy" else 300.0
    hoy = bool(cap.get("hoy"))
    MODO["hoy"] = hoy
    adelante = -40 if hoy else 40           # el terreno fino, hacia donde mira la cámara
    t = terreno(cx + adelante, czw, lado, 0.6 if a.calidad == "prueba" else 0.35, hoy, cap["ceniza"])
    if hay_rio(cx) > 0.2 and not hoy:
        agua(cx + 40, czw, lado)
    if hoy:
        estratos = barrancas((cx, czw), (cap["mira"][0], cap["mira"][2]))
        horizonte(cx, czw, estratos.data.materials[0])
    else:
        horizonte(cx, czw, t.data.materials[0])
    cielo(*cap["sol"], cap["bruma"], volumetrica, cap["ceniza"], limpio=hoy)
    volcan(cap["volcan"])

    moldes = {}
    for nombre in {r[0] for r in REGLAS}:
        m = cargar_molde(os.path.abspath(a.assets), nombre, os.path.abspath(a.modelos))
        if m:
            moldes[nombre] = m
    densidad = 0.35 if a.calidad == "prueba" else 1.0
    n_plantas = sembrar(moldes, cx + 40, czw, lado * 0.8, densidad, hoy)
    # hoy no hay animales vivos: sólo el paisaje (los fósiles los pone la capa interactiva)
    puestos, faltan = (0, []) if hoy else poner_dinosaurios(os.path.abspath(a.modelos), cx)

    cuadros = int(a.segundos * 30)
    camara(cap, cuadros, a.animar)
    configurar_render(ancho, alto, muestras)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, f"{clave}.blend"))
    esc = bpy.context.scene
    esc.render.image_settings.file_format = "PNG"
    tiene_prof = pase_profundidad(os.path.join(carpeta, f"{clave}_profundidad.png"))
    if a.animar:
        esc.frame_start, esc.frame_end = 1, cuadros
        esc.render.filepath = os.path.join(carpeta, "frames", "")
        bpy.ops.render.render(animation=True)
    else:
        esc.render.filepath = os.path.join(carpeta, f"{clave}.png")
        bpy.ops.render.render(write_still=True)
    print(f"   {clave}: {n_plantas} plantas, {puestos} dinosaurios puestos"
          + (f", SIN MODELO todavía: {', '.join(faltan)} (quedan los SLOT_)" if faltan else "")
          + ("" if tiene_prof else " · sin pase de profundidad en esta versión de Blender"), flush=True)


def main():
    a = argumentos()
    for c in a.capitulos:
        print(f"== {c} ({a.calidad})", flush=True)
        hacer_capitulo(c, a)
    print("listo:", os.path.abspath(a.salida))


if __name__ == "__main__":
    main()
