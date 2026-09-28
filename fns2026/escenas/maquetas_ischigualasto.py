"""
Maquetas de los lugares icónicos de Ischigualasto, para el stand de la FNS 2026.

    blender -b --factory-startup -P maquetas_ischigualasto.py -- SALIDA [--solo hongo] [--calidad prueba|final] [--sin-video]
    (o con el módulo bpy de pip:  python3 maquetas_ischigualasto.py -- SALIDA ...)

Por cada lugar sale, en SALIDA/<lugar>/:
    <lugar>.blend              la escena, para retocar a mano
    <lugar>.glb / .fbx         la maqueta sola, para TD (girarla en vivo con el cuerpo)
    <lugar>_vista.png          una imagen fija
    frames/####.png            el giro de 360° con ALFA (se monta sobre el sol de la Fiesta)
    <lugar>_giro.mp4           vista previa del giro sobre fondo oscuro (sólo para mirar)

Qué hace el giro, cuadro por cuadro (es el lenguaje del stand de maquetas que ya existía):
  · primer 25 %: la maqueta aparece como MALLADO DORADO que sube desde el pedestal
  · después la textura real "revela" de abajo hacia arriba
  · todo el tiempo gira 360° y el último cuadro empalma con el primero (loop sin salto)

Los frames PNG son todos clave: en TD (Movie File In con el índice mapeado a /body/x) o en
Arena se pueden recorrer para adelante y para atrás con el cuerpo: ése es el "video interactivo".
Para el show se convierten con Alley a DXV3 (Arena) o HAP (TD), que respetan el alfa.

Todo es procedural (sin fotos ni modelos de terceros): la geología sale de ruido y de
perfiles, igual que el shader de estratos del proyecto de la Mac (coordenadas Object, no
Generated: con desplazamiento, Generated da un solo color). Cuando lleguen los modelos de
Meshy (el Hongo real, etc.), se reemplaza la forma y se mantiene pedestal, luz y giro.

Probado con Blender 5.0.1 en modo consola (CPU). En la Mac M4 usar --calidad final (Metal).
"""

import argparse
import math
import os
import sys

import bpy
import bmesh  # después de bpy: con el módulo de pip, bmesh existe recién cuando bpy cargó
from mathutils import Vector, noise

CALIDAD = {
    #          ancho, alto, muestras, cuadros (a 30 fps)
    "prueba": (640, 360, 12, 24),
    "media":  (1280, 720, 32, 180),
    "final":  (1920, 1080, 96, 450),     # 15 s, como los clips del stand
}

# Paleta de Ischigualasto (tomada de las capturas del valle de la Mac y de fotos de referencia)
ARCILLA = (0.64, 0.61, 0.56)
ARENISCA_CLARA = (0.72, 0.62, 0.50)
ARENISCA_GRIS = (0.55, 0.52, 0.47)
OCRE = (0.66, 0.44, 0.24)
ROJO_BARRANCA = (0.42, 0.13, 0.07)
ROJO_OSCURO = (0.26, 0.08, 0.05)
VERDE_GRIS = (0.47, 0.50, 0.43)
LILA = (0.50, 0.40, 0.45)
DORADO = (1.0, 0.52, 0.10)


# ---------------------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------------------

def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("salida")
    ap.add_argument("--solo", nargs="*")
    ap.add_argument("--calidad", default="prueba", choices=list(CALIDAD))
    ap.add_argument("--sin-video", action="store_true")
    ap.add_argument("--sin-giro", action="store_true", help="sólo la imagen fija")
    ap.add_argument("--meshy", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "modelos"),
                    help="carpeta con los modelos de Meshy ya refinados (correr_todo.py los deja ahí)")
    return ap.parse_args(argv)


def salida_nodo(nodo, *nombres):
    """Blender cambia nombres de sockets entre versiones (Fac → Factor en 5.2)."""
    for n in nombres:
        if n in nodo.outputs:
            return nodo.outputs[n]
    return nodo.outputs[0]


def entrada_nodo(nodo, *nombres):
    for n in nombres:
        if n in nodo.inputs:
            return nodo.inputs[n]
    raise KeyError(f"{nodo.name}: ninguna entrada {nombres}")


def fbm(p, octavas=5, escala=1.0):
    """Ruido fractal en [-1, 1] aprox. mathutils.noise, sin dependencias."""
    total, amp, frec, norm = 0.0, 1.0, escala, 0.0
    for _ in range(octavas):
        total += amp * noise.noise(p * frec)
        norm += amp
        amp *= 0.5
        frec *= 2.03
    return total / norm


def malla_desde_bmesh(nombre, bm):
    me = bpy.data.meshes.new(nombre)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(nombre, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def suavizar(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


# ---------------------------------------------------------------------------------------
# materiales
# ---------------------------------------------------------------------------------------

def _revelado(nt, base_shader, salida):
    """Mezcla el shader real con un mallado dorado según la altura mundial y un umbral
    animado (FNS_revelar). Por debajo del umbral: textura. Por encima y cerca: mallado dorado.
    Más arriba: invisible (la maqueta "se construye")."""
    n, l = nt.nodes, nt.links
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(geo.outputs["Position"], sep.inputs[0])

    umbral = n.new("ShaderNodeValue")
    umbral.name = umbral.label = "FNS_revelar"          # se anima desde afuera
    frente = n.new("ShaderNodeValue")
    frente.name = frente.label = "FNS_mallado"          # el mallado va adelante de la textura

    # t_textura: 1 donde ya se reveló la textura
    rt = n.new("ShaderNodeMapRange")
    l.new(sep.outputs["Z"], rt.inputs["Value"])
    l.new(umbral.outputs[0], rt.inputs["From Min"])
    sum_ = n.new("ShaderNodeMath"); sum_.operation = "ADD"; sum_.inputs[1].default_value = -0.35
    l.new(umbral.outputs[0], sum_.inputs[0])
    l.new(sum_.outputs[0], rt.inputs["From Max"])
    rt.inputs["To Min"].default_value, rt.inputs["To Max"].default_value = 0.0, 1.0

    # t_mallado: 1 donde el mallado ya llegó
    rm = n.new("ShaderNodeMapRange")
    l.new(sep.outputs["Z"], rm.inputs["Value"])
    l.new(frente.outputs[0], rm.inputs["From Min"])
    sum2 = n.new("ShaderNodeMath"); sum2.operation = "ADD"; sum2.inputs[1].default_value = -0.2
    l.new(frente.outputs[0], sum2.inputs[0])
    l.new(sum2.outputs[0], rm.inputs["From Max"])
    rm.inputs["To Min"].default_value, rm.inputs["To Max"].default_value = 0.0, 1.0

    # mallado dorado: emisión en las aristas, transparente en el resto
    # "mallado": grilla de líneas cada 35 cm en coordenadas del objeto. El Wireframe real
    # de una malla densa se ve sólido; la grilla se lee igual a cualquier resolución.
    tc = n.new("ShaderNodeTexCoord")
    div = n.new("ShaderNodeVectorMath"); div.operation = "DIVIDE"
    div.inputs[1].default_value = (0.35, 0.35, 0.35)
    l.new(tc.outputs["Object"], div.inputs[0])
    frc = n.new("ShaderNodeVectorMath"); frc.operation = "FRACTION"
    l.new(div.outputs[0], frc.inputs[0])
    uno = n.new("ShaderNodeVectorMath"); uno.operation = "SUBTRACT"
    uno.inputs[0].default_value = (1, 1, 1)
    l.new(frc.outputs[0], uno.inputs[1])
    mn = n.new("ShaderNodeVectorMath"); mn.operation = "MINIMUM"
    l.new(frc.outputs[0], mn.inputs[0]); l.new(uno.outputs[0], mn.inputs[1])
    sx = n.new("ShaderNodeSeparateXYZ"); l.new(mn.outputs[0], sx.inputs[0])
    m1 = n.new("ShaderNodeMath"); m1.operation = "MINIMUM"
    l.new(sx.outputs[0], m1.inputs[0]); l.new(sx.outputs[1], m1.inputs[1])
    # las líneas horizontales sólo en paredes empinadas: en el piso casi plano, el terreno
    # cruza los planos z = k·35 cm y dejaba manchones en vez de líneas
    gn = n.new("ShaderNodeNewGeometry")
    sn = n.new("ShaderNodeSeparateXYZ"); l.new(gn.outputs["Normal"], sn.inputs[0])
    absn = n.new("ShaderNodeMath"); absn.operation = "ABSOLUTE"; l.new(sn.outputs[2], absn.inputs[0])
    zlin = n.new("ShaderNodeMath"); zlin.operation = "ADD"
    l.new(sx.outputs[2], zlin.inputs[0]); l.new(absn.outputs[0], zlin.inputs[1])
    m2 = n.new("ShaderNodeMath"); m2.operation = "MINIMUM"
    l.new(m1.outputs[0], m2.inputs[0]); l.new(zlin.outputs[0], m2.inputs[1])
    wire = n.new("ShaderNodeMath"); wire.operation = "LESS_THAN"
    wire.inputs[1].default_value = 0.045
    l.new(m2.outputs[0], wire.inputs[0])
    emi = n.new("ShaderNodeEmission")
    emi.inputs["Color"].default_value = (*DORADO, 1)
    emi.inputs["Strength"].default_value = 3.0   # más fuerte se satura a blanco con AgX
    transp = n.new("ShaderNodeBsdfTransparent")
    mix_w = n.new("ShaderNodeMixShader")
    l.new(wire.outputs[0], mix_w.inputs[0])
    l.new(transp.outputs[0], mix_w.inputs[1])
    l.new(emi.outputs[0], mix_w.inputs[2])

    # invisible → mallado → textura
    mix_a = n.new("ShaderNodeMixShader")
    l.new(rm.outputs[0], mix_a.inputs[0])
    l.new(transp.outputs[0], mix_a.inputs[1])
    l.new(mix_w.outputs[0], mix_a.inputs[2])
    mix_b = n.new("ShaderNodeMixShader")
    l.new(rt.outputs[0], mix_b.inputs[0])
    l.new(mix_a.outputs[0], mix_b.inputs[1])
    l.new(base_shader, mix_b.inputs[2])
    l.new(mix_b.outputs[0], salida.inputs["Surface"])


def material_estratos(nombre, bandas, escala_z=1.0, grietas=0.0, rugosidad=0.92, bump=0.35, ondulacion=0.6):
    """Estratos por altura (Object Z, repetidos con fract) + ruido que los ondula
    + opcional grietas de barro (Voronoi distancia al borde) + relieve."""
    m = bpy.data.materials.new(nombre)
    m.use_nodes = True
    nt = m.node_tree
    n, l = nt.nodes, nt.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rugosidad

    coord = n.new("ShaderNodeTexCoord")
    ruido = n.new("ShaderNodeTexNoise")
    ruido.inputs["Scale"].default_value = 0.35
    ruido.inputs["Detail"].default_value = 6
    l.new(coord.outputs["Object"], ruido.inputs["Vector"])
    sep = n.new("ShaderNodeSeparateXYZ")
    l.new(coord.outputs["Object"], sep.inputs[0])

    # z ondulada: estratos que no son líneas perfectas
    ond = n.new("ShaderNodeMath"); ond.operation = "MULTIPLY_ADD"
    l.new(salida_nodo(ruido, "Factor", "Fac"), ond.inputs[0])
    ond.inputs[1].default_value = ondulacion
    l.new(sep.outputs["Z"], ond.inputs[2])
    esc = n.new("ShaderNodeMath"); esc.operation = "MULTIPLY"; esc.inputs[1].default_value = escala_z
    l.new(ond.outputs[0], esc.inputs[0])
    fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"
    l.new(esc.outputs[0], fr.inputs[0])

    rampa = n.new("ShaderNodeValToRGB")
    cr = rampa.color_ramp
    cr.interpolation = "EASE"
    while len(cr.elements) > 1:
        cr.elements.remove(cr.elements[-1])
    for i, col in enumerate(bandas):
        e = cr.elements[0] if i == 0 else cr.elements.new(i / len(bandas))
        e.color = (*col, 1)
    l.new(fr.outputs[0], rampa.inputs["Fac"])

    # variación fina de color (laminaciones)
    ondas = n.new("ShaderNodeTexWave")
    ondas.wave_type = "BANDS"; ondas.bands_direction = "Z"
    ondas.inputs["Scale"].default_value = 6.0
    ondas.inputs["Distortion"].default_value = 4.0
    l.new(coord.outputs["Object"], ondas.inputs["Vector"])
    mezcla_col = n.new("ShaderNodeMix"); mezcla_col.data_type = "RGBA"; mezcla_col.blend_type = "MULTIPLY"
    mezcla_col.inputs["Factor"].default_value = 0.18
    l.new(rampa.outputs["Color"], mezcla_col.inputs["A"])
    l.new(salida_nodo(ondas, "Color"), mezcla_col.inputs["B"])
    color_final = mezcla_col.outputs["Result"]
    altura = salida_nodo(ondas, "Factor", "Fac")

    if grietas > 0:
        vor = n.new("ShaderNodeTexVoronoi")
        vor.feature = "DISTANCE_TO_EDGE"
        vor.inputs["Scale"].default_value = grietas
        # coordenadas deformadas: grietas irregulares, no celdas perfectas
        defo = n.new("ShaderNodeVectorMath"); defo.operation = "MULTIPLY_ADD"
        defo.inputs[1].default_value = (0.45, 0.45, 0.45)
        l.new(ruido.outputs["Color"], defo.inputs[0])
        l.new(coord.outputs["Object"], defo.inputs[2])
        l.new(defo.outputs[0], vor.inputs["Vector"])
        borde = n.new("ShaderNodeMapRange")
        borde.inputs["From Min"].default_value = 0.0
        borde.inputs["From Max"].default_value = 0.025
        l.new(salida_nodo(vor, "Distance"), borde.inputs["Value"])
        oscuro = n.new("ShaderNodeMix"); oscuro.data_type = "RGBA"
        oscuro.inputs["B"].default_value = (*ARCILLA, 1)
        oscuro.inputs["A"].default_value = (0.22, 0.19, 0.16, 1)
        l.new(borde.outputs[0], oscuro.inputs["Factor"])
        final = n.new("ShaderNodeMix"); final.data_type = "RGBA"; final.blend_type = "MULTIPLY"
        final.inputs["Factor"].default_value = 1.0
        l.new(color_final, final.inputs["A"])
        l.new(oscuro.outputs["Result"], final.inputs["B"])
        color_final = final.outputs["Result"]
        altura = borde.outputs[0]

    l.new(color_final, bsdf.inputs["Base Color"])
    rel = n.new("ShaderNodeBump")
    rel.inputs["Strength"].default_value = bump
    l.new(altura, rel.inputs["Height"])
    l.new(rel.outputs["Normal"], bsdf.inputs["Normal"])
    _revelado(nt, bsdf.outputs[0], out)
    return m


_pedestal_cache = {}


def _MAT_PEDESTAL():
    if "m" not in _pedestal_cache:
        _pedestal_cache["m"] = material_pedestal()
    return _pedestal_cache["m"]


def material_pedestal():
    """El costado del pedestal: tierra oscura con estratos, como el corte de una maqueta."""
    return material_estratos("pedestal", [(0.16, 0.09, 0.06), (0.22, 0.12, 0.07), (0.12, 0.07, 0.05)],
                             escala_z=3.0, rugosidad=0.95, bump=0.2)


# ---------------------------------------------------------------------------------------
# geometría
# ---------------------------------------------------------------------------------------

def terreno_circular(nombre, radio, altura_fn, anillos=90, segmentos=220, profundidad=1.2):
    """Disco de terreno (polar) con faldón y base: la maqueta recortada en redondo.
    Devuelve (objeto_superficie, objeto_pedestal) para darles materiales distintos."""
    bm = bmesh.new()
    centro = bm.verts.new((0, 0, altura_fn(0.0, 0.0)))
    filas = []
    for i in range(1, anillos + 1):
        r = radio * i / anillos
        fila = []
        for j in range(segmentos):
            a = 2 * math.pi * j / segmentos
            x, y = r * math.cos(a), r * math.sin(a)
            fila.append(bm.verts.new((x, y, altura_fn(x, y))))
        filas.append(fila)
    for j in range(segmentos):
        bm.faces.new((centro, filas[0][j], filas[0][(j + 1) % segmentos]))
    for i in range(anillos - 1):
        for j in range(segmentos):
            k = (j + 1) % segmentos
            bm.faces.new((filas[i][j], filas[i + 1][j], filas[i + 1][k], filas[i][k]))
    sup = malla_desde_bmesh(nombre, bm)
    suavizar(sup)

    # pedestal: faldón desde el borde del terreno hasta la base, y la base
    bm = bmesh.new()
    borde = [Vector(v.co) for v in sup.data.vertices][-segmentos:]
    arriba = [bm.verts.new(p) for p in borde]
    abajo = [bm.verts.new((p.x * 1.02, p.y * 1.02, -profundidad)) for p in borde]
    for j in range(segmentos):
        k = (j + 1) % segmentos
        bm.faces.new((arriba[j], abajo[j], abajo[k], arriba[k]))
    bm.faces.new(list(reversed(abajo)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ped = malla_desde_bmesh(nombre + "_pedestal", bm)
    asignar(ped, _MAT_PEDESTAL())
    return sup, ped


def torneado(nombre, perfil, segmentos=96, eje="Z"):
    """Sólido de revolución a partir de [(radio, altura), ...] de abajo hacia arriba."""
    bm = bmesh.new()
    anillos = []
    for r, h in perfil:
        fila = []
        for j in range(segmentos):
            a = 2 * math.pi * j / segmentos
            p = (r * math.cos(a), r * math.sin(a), h)
            if eje == "X":
                p = (h, r * math.cos(a), r * math.sin(a))
            fila.append(bm.verts.new(p))
        anillos.append(fila)
    for i in range(len(anillos) - 1):
        for j in range(segmentos):
            k = (j + 1) % segmentos
            bm.faces.new((anillos[i][j], anillos[i][k], anillos[i + 1][k], anillos[i + 1][j]))
    # tapas en abanico hacia un vértice central (un n-gono subdividido deja picos)
    for fila, extremo in ((anillos[0], perfil[0][1]), (anillos[-1], perfil[-1][1])):
        c = bm.verts.new((extremo, 0, 0) if eje == "X" else (0, 0, extremo))
        for j in range(segmentos):
            bm.faces.new((c, fila[j], fila[(j + 1) % segmentos]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = malla_desde_bmesh(nombre, bm)
    return ob


def subdividir(ob, cortes=2):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cortes, use_grid_fill=True)
    bm.to_mesh(ob.data)
    bm.free()


def erosionar(ob, fuerza, escala, surcos=0.0, semilla=0.0, surcos_hasta=1e9):
    """Desplaza cada vértice por su normal: ruido fractal + surcos horizontales de viento
    (lo que le da al Hongo y al Submarino esas acanaladuras)."""
    me = ob.data
    me.calc_loop_triangles()
    for v in me.vertices:
        p = Vector(v.co) + Vector((semilla, semilla * 0.7, 0))
        d = fbm(p, 5, escala) * fuerza
        if surcos and v.co.z < surcos_hasta:
            d += surcos * math.sin(v.co.z * 9.0 + fbm(p, 2, 0.8) * 3.0) * 0.5
        v.co += v.normal * d
    suavizar(ob)


def asignar(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)


# ---------------------------------------------------------------------------------------
# los lugares
# ---------------------------------------------------------------------------------------

def piso_ischigualasto(x, y, rugo=0.25):
    return fbm(Vector((x, y, 0)), 4, 0.12) * rugo


def lugar_hongo():
    """El Hongo: pie fino y erosionado de arenisca clara, sombrero ancho de roca más dura."""
    suelo = material_estratos("arcilla_hongo", [ARCILLA, (0.74, 0.72, 0.66)], escala_z=0.5, grietas=1.1)
    # el Hongo real es gris beige, con el sombrero apenas más oscuro: bandas sutiles
    roca = material_estratos("arenisca_hongo", [(0.66, 0.60, 0.52), ARENISCA_GRIS, (0.62, 0.56, 0.48),
                                                (0.58, 0.50, 0.40)], escala_z=1.2, bump=0.7)
    sup, ped = terreno_circular("hongo_terreno", 7.0, lambda x, y: piso_ischigualasto(x, y, 0.3))
    asignar(sup, suelo)
    perfil = [(1.6, -0.3), (1.3, 0.2), (0.95, 0.9), (0.62, 1.6), (0.55, 2.2), (0.66, 2.8),
              (1.1, 3.25), (2.1, 3.55), (2.6, 3.9), (2.5, 4.35), (1.9, 4.7), (0.9, 4.9), (0.3, 4.97)]
    hongo = torneado("el_hongo", perfil, 96)
    subdividir(hongo, 2)
    erosionar(hongo, 0.16, 0.9, surcos=0.10, semilla=3.1, surcos_hasta=3.2)
    hongo.scale = (1.0, 0.82, 1.0)          # no es redondo: sección ovalada
    hongo.rotation_euler.z = 0.4
    asignar(hongo, roca)
    rocas(9, 6.2, roca, semilla=11)
    return [sup, ped, hongo], 5.0


def lugar_submarino():
    """El Submarino: casco alargado de arenisca con la "torre" arriba, sobre base erosionada."""
    suelo = material_estratos("arcilla_sub", [ARCILLA, (0.73, 0.70, 0.64)], escala_z=0.5, grietas=1.0)
    roca = material_estratos("arenisca_sub", [ARENISCA_GRIS, (0.60, 0.55, 0.48), (0.52, 0.47, 0.41),
                                              (0.58, 0.49, 0.38)], escala_z=1.1, bump=0.7)
    sup, ped = terreno_circular("sub_terreno", 8.0, lambda x, y: piso_ischigualasto(x, y, 0.35))
    asignar(sup, suelo)
    base = torneado("sub_base", [(2.4, -0.3), (2.0, 0.6), (1.2, 1.4), (1.0, 1.9)], 80)
    base.scale = (2.4, 1.0, 1.0)
    casco = torneado("sub_casco", [(0.05, -4.2), (0.9, -3.4), (1.3, -1.5), (1.35, 1.2),
                                   (1.1, 3.0), (0.5, 4.0), (0.05, 4.3)], 64, eje="X")
    casco.location = (0, 0, 2.6)
    casco.scale = (1.0, 0.85, 1.0)
    torre = torneado("sub_torre", [(0.7, 0), (0.55, 1.0), (0.45, 1.8), (0.1, 2.0)], 48)
    torre.location = (0.8, 0, 3.5)
    torre.scale = (1.6, 0.7, 1.0)
    for o in (base, casco, torre):
        subdividir(o, 2)
        erosionar(o, 0.22, 1.0, surcos=0.08, semilla=len(o.name))
        asignar(o, roca)
    rocas(12, 7.0, roca, semilla=5)
    return [sup, ped, base, casco, torre], 6.0


def lugar_bochas():
    """Cancha de Bochas: arcilla cuarteada con concreciones esféricas de todos los tamaños,
    agrupadas (no en grilla), algunas medio enterradas y alguna partida."""
    suelo = material_estratos("arcilla_bochas", [ARCILLA, (0.75, 0.72, 0.66)], escala_z=0.4, grietas=0.9)
    piedra = material_estratos("bocha", [(0.30, 0.27, 0.24), (0.36, 0.31, 0.26), (0.27, 0.24, 0.22)],
                               escala_z=4.0, bump=0.8, rugosidad=0.85)
    sup, ped = terreno_circular("bochas_terreno", 7.0, lambda x, y: piso_ischigualasto(x, y, 0.12))
    asignar(sup, suelo)
    objs = [sup, ped]
    # grupos: la cancha real tiene manchones densos y claros vacíos
    grupos = [(-2.5, 1.5, 2.2, 22), (2.0, -1.0, 2.6, 28), (0.5, 3.8, 1.6, 12), (-1.0, -3.5, 2.0, 16)]
    k = 0
    for gx, gy, gr, cant in grupos:
        for i in range(cant):
            a = noise.random() * 2 * math.pi
            r = gr * math.sqrt(noise.random())
            x, y = gx + r * math.cos(a), gy + r * math.sin(a)
            if x * x + y * y > 6.3 ** 2:
                continue
            radio = 0.12 + (noise.random() ** 2) * 0.55
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=radio,
                                                 location=(x, y, piso_ischigualasto(x, y, 0.12) + radio * (-0.25 + 0.6 * noise.random())))
            b = bpy.context.object
            b.name = f"bocha_{k}"; k += 1
            b.scale = (1.0, 0.9 + 0.2 * noise.random(), 0.85 + 0.2 * noise.random())
            erosionar(b, radio * 0.08, 6.0, semilla=k)
            asignar(b, piedra)
            objs.append(b)
    return objs, 2.0


def lugar_valle_pintado():
    """Valle Pintado: lomas de badlands con bandas de colores (verde gris, lila, ocre, rojo)."""
    lomas = material_estratos("valle_pintado", [(0.36, 0.38, 0.32), (0.40, 0.30, 0.34), OCRE, ROJO_BARRANCA, (0.48, 0.30, 0.20), (0.34, 0.36, 0.30)],
                              escala_z=1.3, bump=0.5, ondulacion=0.15)

    def relieve(x, y):
        p = Vector((x, y, 0))
        crestas = 1.0 - abs(fbm(p, 4, 0.14))          # crestas de erosión medianas
        caida = max(0.0, 1.0 - (math.hypot(x, y) / 8.0) ** 4)   # bajan hacia el borde de la maqueta
        return (3.0 * crestas ** 2.6 + fbm(p, 5, 0.7) * 0.18) * caida
    sup, ped = terreno_circular("valle_pintado_terreno", 8.0, relieve, anillos=120, segmentos=280)
    asignar(sup, lomas)
    return [sup, ped], 2.5


def lugar_barrancas():
    """Barrancas Coloradas: farallón rojo en arco con estratos horizontales y cárcavas."""
    suelo = material_estratos("arcilla_barranca", [ARCILLA, (0.70, 0.62, 0.55)], escala_z=0.5, grietas=1.0)
    roja = material_estratos("barranca", [ROJO_BARRANCA, (0.36, 0.11, 0.06), (0.48, 0.20, 0.10),
                                           ROJO_OSCURO, (0.44, 0.16, 0.08)],
                             escala_z=0.55, bump=0.8, ondulacion=0.25)

    def relieve(x, y):
        ang = math.atan2(y, x)
        r = math.hypot(x, y)
        # media luna detrás (de -20° a 200°): sube como farallón vertical y baja en ladera
        dentro = -0.35 < ang < 3.5
        peso = 1.0 if dentro else max(0.0, 1.0 - min(abs(ang + 0.35), abs(ang - 3.5 + 2 * math.pi * (ang < 0))) * 1.5)
        cima = 5.0 + fbm(Vector((ang * 2.5, 0, 0)), 3, 1.0) * 1.0
        frente = min(1.0, max(0.0, (r - 3.6) / 0.7)) ** 0.5          # pared casi vertical
        ladera = min(1.0, max(0.0, (7.8 - r) / 2.2))                  # baja hacia atrás
        h = cima * frente * ladera * peso
        carcavas = abs(math.sin(ang * 13 + fbm(Vector((x, y, 0)), 2, 0.5) * 2.5)) * 0.7 * min(1.0, h / 2)
        return h - carcavas + fbm(Vector((x, y, 0)), 4, 0.3) * 0.15
    sup, ped = terreno_circular("barranca_terreno", 8.0, relieve, anillos=130, segmentos=300)
    # dos materiales por altura: arcilla abajo, barranca arriba
    sup.data.materials.append(suelo)
    sup.data.materials.append(roja)
    for p in sup.data.polygons:
        z = sum(sup.data.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        p.material_index = 1 if z > 0.35 else 0
    return [sup, ped], 3.0


def rocas(cant, radio_max, mat, semilla=0):
    for i in range(cant):
        a = (i * 2.399 + semilla) % (2 * math.pi)
        r = radio_max * (0.45 + 0.5 * ((i * 0.618 + semilla * 0.1) % 1))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=0.15 + 0.25 * ((i * 0.37) % 1),
                                              location=(r * math.cos(a), r * math.sin(a), 0.0))
        o = bpy.context.object
        o.name = f"roca_{semilla}_{i}"
        o.scale = (1.0, 0.8, 0.6)
        erosionar(o, 0.06, 4.0, semilla=i + semilla)
        asignar(o, mat)


# qué modelo de Meshy reemplaza a qué forma procedural (nombres de lista_modelos.json)
MESHY_DE = {"hongo": "el_hongo", "submarino": "el_submarino", "bochas": "bochas"}
FORMAS_PROCEDURALES = {"hongo": ("el_hongo",), "submarino": ("sub_base", "sub_casco", "sub_torre"),
                       "bochas": ("bocha_",)}


def buscar_meshy(carpeta, nombre):
    for nivel in ("alto", "medio"):
        p = os.path.join(carpeta, nombre, f"{nombre}_{nivel}.glb")
        if os.path.exists(p):
            return p
    return None


def envolver_revelado(mat):
    """Le pone el mallado dorado + revelado a un material que viene de Meshy (PBR)."""
    if not mat or not mat.node_tree or "FNS_revelar" in mat.node_tree.nodes:
        return
    nt = mat.node_tree
    out = next((x for x in nt.nodes if x.type == "OUTPUT_MATERIAL"), None)
    if not out or not out.inputs["Surface"].links:
        return
    base = out.inputs["Surface"].links[0].from_socket
    nt.links.remove(out.inputs["Surface"].links[0])
    _revelado(nt, base, out)


def importar_meshy(ruta, alto_objetivo=None):
    antes = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=ruta)
    nuevos = [o for o in bpy.context.scene.objects if o not in antes]
    mallas = [o for o in nuevos if o.type == "MESH"]
    for o in mallas:
        for m in o.data.materials:
            envolver_revelado(m)
    return nuevos, mallas


def reemplazar_con_meshy(clave, objs, carpeta_meshy):
    """Si Meshy ya generó el lugar, saca la forma procedural y pone el modelo real. El modelo
    viene de blender_refinar.py: escala real, apoyado en z=0, centrado. Así que entra justo."""
    nombre = MESHY_DE.get(clave)
    ruta = buscar_meshy(carpeta_meshy, nombre) if nombre else None
    if not ruta:
        return objs, False
    prefijos = FORMAS_PROCEDURALES[clave]
    viejos = [o for o in objs if any(o.name.startswith(p) for p in prefijos)]
    if clave == "bochas":
        # las bochas procedurales quedan como posiciones: en cada una va una copia del modelo real
        puestos = [(o.location.copy(), max(o.dimensions)) for o in viejos]
        for o in viejos:
            bpy.data.objects.remove(o)
        _, mallas = importar_meshy(ruta)
        molde = mallas[0]
        tam = max(molde.dimensions) or 1.0
        nuevos = []
        for loc, d in puestos:
            c = molde.copy()
            bpy.context.scene.collection.objects.link(c)
            c.location = loc
            c.scale = [d / tam] * 3
            c.rotation_euler.z = loc.x * 3.1
            nuevos.append(c)
        bpy.data.objects.remove(molde)
        return [o for o in objs if o not in viejos] + nuevos, True
    for o in viejos:
        bpy.data.objects.remove(o)
    nuevos, mallas = importar_meshy(ruta)
    return [o for o in objs if o not in viejos] + mallas, True


LUGARES = {
    "hongo": ("El Hongo", lugar_hongo),
    "submarino": ("El Submarino", lugar_submarino),
    "bochas": ("Cancha de Bochas", lugar_bochas),
    "valle_pintado": ("Valle Pintado", lugar_valle_pintado),
    "barrancas": ("Barrancas Coloradas", lugar_barrancas),
}


# ---------------------------------------------------------------------------------------
# luz, cámara, animación, render
# ---------------------------------------------------------------------------------------

def luz_y_mundo():
    esc = bpy.context.scene
    mundo = bpy.data.worlds.new("cielo_sanjuan")
    mundo.use_nodes = True
    fondo = mundo.node_tree.nodes["Background"]
    fondo.inputs["Color"].default_value = (0.55, 0.62, 0.75, 1)   # cielo del desierto, luz de relleno
    fondo.inputs["Strength"].default_value = 0.45
    esc.world = mundo
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.data.energy = 3.2
    sol.data.angle = math.radians(1.2)           # sombras duras: sol alto de mediodía sanjuanino
    sol.data.color = (1.0, 0.95, 0.86)
    sol.rotation_euler = (math.radians(38), 0, math.radians(35))
    esc.collection.objects.link(sol)


def camara_orbital(radio_escena, alto_centro, cuadros):
    esc = bpy.context.scene
    eje = bpy.data.objects.new("orbita", None)
    esc.collection.objects.link(eje)
    cam = bpy.data.objects.new("camara", bpy.data.cameras.new("camara"))
    cam.data.lens = 40
    esc.collection.objects.link(cam)
    cam.parent = eje
    d = radio_escena * 3.1
    cam.location = (0, -d, d * 0.55)
    obj = Vector((0, 0, alto_centro * 0.28))
    cam.rotation_euler = (obj - cam.location).to_track_quat("-Z", "Y").to_euler()
    esc.camera = cam
    # giro de 360° que empalma: el cuadro N+1 sería igual al 1, por eso termina en 360*(N-1)/N
    eje.rotation_euler.z = 0
    eje.keyframe_insert("rotation_euler", index=2, frame=1)
    eje.rotation_euler.z = 2 * math.pi * (cuadros - 1) / cuadros
    eje.keyframe_insert("rotation_euler", index=2, frame=cuadros)
    lineal(eje)
    return cam


def lineal(ob):
    ad = ob.animation_data
    if not ad or not ad.action:
        return
    acc = ad.action
    capas = getattr(acc, "layers", None)
    curvas = []
    if capas:
        for c in capas:
            for t in c.strips:
                for b in getattr(t, "channelbags", []):
                    curvas += list(b.fcurves)
    else:
        curvas = list(acc.fcurves)
    for fc in curvas:
        for k in fc.keyframe_points:
            k.interpolation = "LINEAR"


def animar_revelado(z_max, cuadros):
    """El mallado sube en el primer 25 % y la textura lo sigue hasta el 45 %."""
    f_mallado, f_textura = max(2, int(cuadros * 0.25)), max(3, int(cuadros * 0.45))
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        n = m.node_tree.nodes
        if "FNS_revelar" not in n:
            continue
        rev, mal = n["FNS_revelar"].outputs[0], n["FNS_mallado"].outputs[0]
        for sock, f0, f1 in ((mal, 1, f_mallado), (rev, int(f_mallado * 0.6), f_textura)):
            sock.default_value = -1.5
            sock.keyframe_insert("default_value", frame=f0)
            sock.default_value = z_max + 1.0
            sock.keyframe_insert("default_value", frame=f1)


def configurar_render(ancho, alto, muestras, cuadros):
    esc = bpy.context.scene
    esc.render.engine = "CYCLES"
    esc.cycles.device = "GPU" if os.environ.get("FNS_GPU") else "CPU"
    esc.cycles.samples = muestras
    esc.cycles.use_denoising = True
    esc.render.resolution_x, esc.render.resolution_y = ancho, alto
    esc.render.film_transparent = True          # alfa: se monta sobre el sol de la Fiesta
    esc.frame_start, esc.frame_end = 1, cuadros
    esc.render.fps = 30
    try:
        esc.view_settings.view_transform = "AgX"
        esc.view_settings.look = "AgX - Medium High Contrast"
        esc.view_settings.exposure = -0.55     # el sol duro quemaba la arcilla a blanco
    except TypeError:
        pass


def exportar_modelo(objs, ruta_base):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=ruta_base + ".glb", use_selection=True, export_format="GLB",
                              export_animations=False)
    bpy.ops.export_scene.fbx(filepath=ruta_base + ".fbx", use_selection=True, axis_forward="-Z",
                             axis_up="Y", apply_scale_options="FBX_SCALE_ALL", bake_anim=False)


def video_previa(carpeta_frames, cuadros, ancho, alto, destino):
    """Arma un MP4 de vista previa (frames con alfa sobre fondo oscuro) con el editor de
    video de Blender: no hace falta ffmpeg instalado."""
    esc = bpy.data.scenes.new("previa")
    esc.render.resolution_x, esc.render.resolution_y = ancho, alto
    esc.render.fps = 30
    esc.frame_start, esc.frame_end = 1, cuadros
    sed = esc.sequence_editor_create()
    tiras = sed.strips if hasattr(sed, "strips") else sed.sequences   # 4.4+ se llama strips
    fondo = tiras.new_effect("fondo", "COLOR", channel=1, frame_start=1, length=cuadros) \
        if hasattr(tiras, "new_effect") else None
    if fondo is not None:
        fondo.color = (0.09, 0.05, 0.04)
    primero = os.path.join(carpeta_frames, "0001.png")
    img = tiras.new_image("giro", primero, channel=2, frame_start=1)
    for i in range(2, cuadros + 1):
        img.elements.append(f"{i:04d}.png")
    img.blend_type = "ALPHA_OVER"
    if hasattr(esc.render.image_settings, "media_type"):
        esc.render.image_settings.media_type = "VIDEO"     # Blender 5: sin esto FFMPEG no aparece
    esc.render.image_settings.file_format = "FFMPEG"
    esc.render.ffmpeg.format = "MPEG4"
    esc.render.ffmpeg.codec = "H264"
    esc.render.ffmpeg.constant_rate_factor = "HIGH"
    esc.render.filepath = destino
    bpy.context.window_manager  # noqa
    with bpy.context.temp_override(scene=esc):
        bpy.ops.render.render(animation=True, scene=esc.name)


def hacer(clave, salida, calidad, sin_video, sin_giro, carpeta_meshy=""):
    titulo, construir = LUGARES[clave]
    ancho, alto, muestras, cuadros = CALIDAD[calidad]
    carpeta = os.path.join(salida, clave)
    os.makedirs(carpeta, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _pedestal_cache.clear()       # la escena nueva borró el material anterior
    noise.seed_set(7)

    objs, alto_centro = construir()
    objs, con_meshy = reemplazar_con_meshy(clave, objs, carpeta_meshy)
    print(f"   forma: {'MESHY' if con_meshy else 'procedural'}", flush=True)
    radio = max(max(abs(v) for v in o.dimensions) for o in objs[:1]) / 2
    luz_y_mundo()
    camara_orbital(radio, alto_centro, cuadros)
    z_max = max((o.matrix_world @ Vector(c)).z for o in objs for c in o.bound_box)
    animar_revelado(z_max, cuadros)
    configurar_render(ancho, alto, muestras, cuadros)

    exportar_modelo(objs, os.path.join(carpeta, clave))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(carpeta, clave + ".blend"))

    esc = bpy.context.scene
    if hasattr(esc.render.image_settings, "media_type"):
        esc.render.image_settings.media_type = "IMAGE"
    esc.render.image_settings.file_format = "PNG"
    esc.render.image_settings.color_mode = "RGBA"
    # imagen fija: ya revelada, a 1/8 del giro
    esc.frame_set(max(1, int(cuadros * 0.6)))
    esc.render.filepath = os.path.join(carpeta, f"{clave}_vista.png")
    bpy.ops.render.render(write_still=True)
    if sin_giro:
        return
    esc.render.filepath = os.path.join(carpeta, "frames", "")
    esc.render.use_file_extension = True
    bpy.ops.render.render(animation=True)
    if not sin_video:
        video_previa(os.path.join(carpeta, "frames"), cuadros, ancho, alto,
                     os.path.join(carpeta, f"{clave}_giro.mp4"))


def main():
    a = argumentos()
    claves = a.solo or list(LUGARES)
    for c in claves:
        print(f"== {LUGARES[c][0]} ({a.calidad})", flush=True)
        hacer(c, os.path.abspath(a.salida), a.calidad, a.sin_video, a.sin_giro, os.path.abspath(a.meshy))
    print("listo:", os.path.abspath(a.salida))


if __name__ == "__main__":
    main()
