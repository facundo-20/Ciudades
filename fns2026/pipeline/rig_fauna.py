"""
Esqueleto y animación automáticos para los animales de Meshy (el rig de Meshy falla con todo lo
que no es una figura humana: "Pose estimation failed").

    python3 rig_fauna.py                      (bpy de pip)  → todos los de experiencia/public/modelos
    python3 rig_fauna.py --solo saurosuchus --vista

Para cada animal:
  1. Lee la malla (escala real, cabeza hacia +Z del glTF = -Y de Blender, patas en el piso).
  2. Encuentra las patas: los vértices que tocan el piso, agrupados en 4 (cuadrúpedos) o 2 (bípedos).
  3. Arma el esqueleto: pelvis, 3 vértebras, cuello, cabeza, 8 de cola y 3 huesos por pata
     (muslo, canilla, pie) con las rodillas como en un arcosaurio (la de atrás hacia adelante).
  4. Pesos propios: la pata se reparte por altura entre sus huesos; el cuerpo, por su posición a lo
     largo de la columna. (El "automatic weights" de Blender falla con las mallas de Meshy.)
  5. Animaciones en el lugar: caminar (andar en secuencia lateral los cuadrúpedos, como los
     reptiles y sinápsidos), quieto (respira, mira) y pastar u olfatear. Unity mueve el animal a
     la velocidad que dice el informe, que sale del largo de la pata: así los pies no patinan.
Sale a unity/ParqueTriasico/Datos/fauna/<especie>/<especie>.fbx (+ informe .json, + vista .jpg).

Validar con un paleontólogo: el andar de cada especie es una aproximación razonable, no una
reconstrucción biomecánica.
"""

import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.dirname(AQUI)
ORIGEN = os.path.join(FNS, "experiencia", "public", "modelos")
SALIDA = os.path.join(FNS, "unity", "ParqueTriasico", "Datos", "fauna")
FPS = 30

# tipo, ciclo de paso (s), amplitud del muslo (°), ondulación lateral (°), cabeza (fracción del largo),
# y qué hace cuando no camina (pastar = herbívoro, olfatear = carnívoro)
ESPECIES = {
    "ischigualastia": dict(tipo="cuadrupedo", ciclo=1.6, muslo=20, ondula=6, cabeza=0.14, quieto="pastar"),
    "hyperodapedon": dict(tipo="cuadrupedo", ciclo=1.0, muslo=22, ondula=5, cabeza=0.16, quieto="pastar"),
    "exaeretodon": dict(tipo="cuadrupedo", ciclo=0.9, muslo=24, ondula=6, cabeza=0.14, quieto="pastar"),
    "saurosuchus": dict(tipo="cuadrupedo", ciclo=1.5, muslo=22, ondula=4, cabeza=0.13, quieto="olfatear"),
    "sanjuansaurus": dict(tipo="bipedo", ciclo=1.1, muslo=30, ondula=3, cabeza=0.12, quieto="olfatear"),
    "panphagia": dict(tipo="bipedo", ciclo=0.8, muslo=30, ondula=3, cabeza=0.08, quieto="pastar"),
    "herrerasaurus": dict(tipo="bipedo", ciclo=1.2, muslo=30, ondula=3, cabeza=0.12, quieto="olfatear"),
    "eoraptor": dict(tipo="bipedo", ciclo=0.7, muslo=32, ondula=3, cabeza=0.1, quieto="olfatear"),
    "eodromaeus": dict(tipo="bipedo", ciclo=0.7, muslo=32, ondula=3, cabeza=0.1, quieto="olfatear"),
}


# ------------------------------------------------------------------------------------------
# análisis de la malla
# ------------------------------------------------------------------------------------------

def kmedias(p, centros, vueltas=20):
    for _ in range(vueltas):
        d = ((p[:, None, :] - centros[None]) ** 2).sum(-1)
        g = d.argmin(1)
        centros = np.array([p[g == k].mean(0) if (g == k).any() else centros[k] for k in range(len(centros))])
    return centros, g


def analizar(V, tipo, cabeza_frac):
    H = V[:, 2].max()
    y0, y1 = V[:, 1].min(), V[:, 1].max()          # y0 = punta del hocico, y1 = punta de la cola
    L = y1 - y0
    pies = V[V[:, 2] < 0.06 * H]
    # la cola puede arrastrar: los "pies" se buscan sólo en la mitad delantera y el centro
    pies = pies[pies[:, 1] < y0 + 0.75 * L]
    xs = np.abs(pies[:, 0]).max()
    if tipo == "cuadrupedo":
        ya, yb = np.percentile(pies[:, 1], 15), np.percentile(pies[:, 1], 85)
        ini = np.array([[xs / 2, ya], [-xs / 2, ya], [xs / 2, yb], [-xs / 2, yb]])
    else:
        ym = np.median(pies[:, 1])
        ini = np.array([[xs / 2, ym], [-xs / 2, ym]])
    centros, _ = kmedias(pies[:, :2], ini)

    def rebanada(y, ancho=0.04):
        s = V[np.abs(V[:, 1] - y) < ancho * L]
        return s if len(s) else V[np.argsort(np.abs(V[:, 1] - y))[:50]]

    def vientre_y_lomo(y):
        s = rebanada(y)
        centro = s[np.abs(s[:, 0]) < 0.5 * np.abs(s[:, 0]).max() + 1e-6]
        cuerpo = centro[centro[:, 2] > 0.1 * H]
        if len(cuerpo) < 5:
            cuerpo = s
        return np.percentile(cuerpo[:, 2], 8), s[:, 2].max()

    patas = []
    for cx, cy in centros:
        vi, lo = vientre_y_lomo(cy)
        cadera_z = vi + 0.35 * (lo - vi)
        delantera = tipo == "cuadrupedo" and cy < np.mean(centros[:, 1])
        lado = "izq" if cx > 0 else "der"            # mira hacia -Y: su izquierda es +X
        patas.append(dict(nombre=("del_" if delantera else "tra_") + lado, pie=(float(cx), float(cy)),
                          cadera=(float(cx) * 0.6, float(cy), float(cadera_z)), delantera=delantera))
    tras = [p for p in patas if not p["delantera"]]
    dela = [p for p in patas if p["delantera"]]
    pelvis_y = float(np.mean([p["pie"][1] for p in tras]))
    hombro_y = float(np.mean([p["pie"][1] for p in dela])) if dela else pelvis_y - 0.22 * L
    cabeza_y = y0 + cabeza_frac * L
    cuello_y = hombro_y - (0.05 if tipo == "cuadrupedo" else 0.03) * L
    if cuello_y <= cabeza_y + 0.02 * L:
        cuello_y = cabeza_y + 0.04 * L

    def eje(y):
        s = rebanada(y)
        # sin las patas: el eje del cuerpo, no el del muslo
        lejos = np.ones(len(s), bool)
        for p in patas:
            lejos &= (np.hypot(s[:, 0] - p["pie"][0], s[:, 1] - p["pie"][1]) > 0.12 * L) | (s[:, 2] > p["cadera"][2])
        s2 = s[lejos] if lejos.sum() > 10 else s
        return Vector((float(np.mean(s2[:, 0])) * 0.3, y, float((s2[:, 2].min() + s2[:, 2].max()) / 2)))

    cadena = {
        "columna": [eje(pelvis_y + (hombro_y - pelvis_y) * k / 3) for k in range(4)],
        "cuello": [eje(cuello_y + (cabeza_y - cuello_y) * k / 2) for k in range(3)],
        "cabeza": [eje(cabeza_y), eje(y0 + 0.01 * L)],
        "cola": [eje(pelvis_y + 0.03 * L + (y1 - 0.01 * L - pelvis_y - 0.03 * L) * k / 8) for k in range(9)],
    }
    return dict(H=float(H), L=float(L), y0=float(y0), y1=float(y1), patas=patas, cadena=cadena)


# ------------------------------------------------------------------------------------------
# esqueleto
# ------------------------------------------------------------------------------------------

def armar(datos, tipo):
    arm = bpy.data.armatures.new("esqueleto")
    ob = bpy.data.objects.new("esqueleto", arm)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.edit_bones
    raiz = eb.new("raiz")
    raiz.head, raiz.tail = Vector((0, 0, 0)), Vector((0, 0, 0.25 * datos["H"]))
    c = datos["cadena"]
    pelvis = eb.new("pelvis")
    pelvis.head = c["columna"][0] + Vector((0, 0.04 * datos["L"], 0))
    pelvis.tail = c["columna"][0]
    pelvis.parent = raiz
    pelvis.align_roll(Vector((0, 0, 1)))

    def cadena_huesos(nombre, puntos, padre, conectar=True):
        huesos = []
        for i in range(len(puntos) - 1):
            b = eb.new(f"{nombre}_{i + 1}")
            b.head, b.tail = puntos[i], puntos[i + 1]
            b.parent = padre
            b.use_connect = conectar and i > 0
            b.align_roll(Vector((0, 0, 1)))       # Z arriba → X de costado: pitch en X, yaw en Z
            huesos.append(b)
            padre = b
        return huesos

    columna = cadena_huesos("columna", c["columna"], pelvis, conectar=False)
    cuello = cadena_huesos("cuello", [columna[-1].tail] + c["cuello"][1:], columna[-1])
    cabeza = cadena_huesos("cabeza", [cuello[-1].tail, c["cabeza"][1]], cuello[-1])
    cola = cadena_huesos("cola", c["cola"], pelvis, conectar=False)
    for p in datos["patas"]:
        hx, hy, hz = p["cadera"]
        fx, fy = p["pie"]
        largo = hz
        # rodilla de atrás hacia adelante (-Y), codo de adelante hacia atrás (+Y); tobillo alto en
        # los bípedos (dinosaurios digitígrados)
        rod_dy = (0.12 if p["delantera"] else -0.12) * largo
        tob_z = (0.2 if tipo == "bipedo" and not p["delantera"] else 0.1) * largo
        cadera = Vector((hx, hy, hz))
        rodilla = Vector(((hx + fx) / 2, fy + rod_dy, hz * 0.5))
        tobillo = Vector((fx, fy + 0.05 * largo, tob_z))
        dedos = Vector((fx, fy - 0.18 * largo, 0.01))
        padre = columna[-1] if p["delantera"] else pelvis
        prev = padre
        for nom, a, b in (("muslo", cadera, rodilla), ("canilla", rodilla, tobillo), ("pie", tobillo, dedos)):
            h = eb.new(f"{nom}_{p['nombre']}")
            h.head, h.tail = a, b
            h.parent = prev
            h.use_connect = prev is not padre
            h.align_roll(Vector((0, -1, 0)))      # Z hacia adelante → X de costado: el paso gira en X
            prev = h
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


# ------------------------------------------------------------------------------------------
# pesos
# ------------------------------------------------------------------------------------------

def pesar(malla, esq, datos):
    V = np.array([malla.matrix_world @ v.co for v in malla.data.vertices])
    n = len(V)
    huesos = [b.name for b in esq.data.bones if b.name != "raiz"]
    W = np.zeros((n, len(huesos)))
    col = {h: i for i, h in enumerate(huesos)}
    L = datos["L"]
    asignado = np.zeros(n, bool)
    # patas: cada vértice bajo la cadera va a la pata MÁS CERCANA (con dos patas juntas, como en
    # los bípedos, el "primero que lo agarra" dejaba dedos de un pie colgados del otro y se estiraban)
    distancias, alturas, dentro = [], [], []
    for p in datos["patas"]:
        hx, hy, hz = p["cadera"]
        fx, fy = p["pie"]
        s = np.clip(V[:, 2] / hz, 0, 1.2)
        cx = fx + (hx - fx) * np.clip(s, 0, 1)
        dist = np.hypot(V[:, 0] - cx, V[:, 1] - fy)
        radio = max(0.1 * L, 0.35 * hz)
        distancias.append(dist)
        alturas.append(s)
        dentro.append((dist < radio) & (s < 1.05))
    D = np.where(np.array(dentro), np.array(distancias), np.inf)
    cual = D.argmin(0)
    alguna = np.isfinite(D.min(0))

    def rampa(s, a, b):
        return np.clip((s - a) / (b - a), 0, 1)

    for k, p in enumerate(datos["patas"]):
        en = alguna & (cual == k)
        s = alturas[k]
        pie = 1 - rampa(s, 0.12, 0.22)
        canilla = rampa(s, 0.12, 0.22) * (1 - rampa(s, 0.45, 0.6))
        muslo = rampa(s, 0.45, 0.6) * (1 - 0.5 * rampa(s, 0.85, 1.0))
        cuerpo = 0.5 * rampa(s, 0.85, 1.0)
        padre = "columna_3" if p["delantera"] else "pelvis"
        for nom, w in (("pie", pie), ("canilla", canilla), ("muslo", muslo)):
            W[en, col[f"{nom}_{p['nombre']}"]] += w[en]
        W[en, col[padre]] += cuerpo[en]
        asignado |= en
    # el resto: a lo largo de la columna, la cola, el cuello y la cabeza (por Y, con caída suave)
    eje = []
    for b in esq.data.bones:
        if b.name in ("raiz",) or b.name.split("_")[0] in ("muslo", "canilla", "pie"):
            continue
        h, t = esq.matrix_world @ b.head_local, esq.matrix_world @ b.tail_local
        eje.append((b.name, np.array(h), np.array(t)))
    resto = ~asignado
    P = V[resto]
    for nombre, h, t in eje:
        seg = t - h
        largo = np.linalg.norm(seg) + 1e-6
        u = np.clip(((P - h) @ seg) / (largo * largo), 0, 1)
        cerca = h + u[:, None] * seg
        d = np.linalg.norm((P - cerca)[:, [1]], axis=1)       # distancia a lo largo del cuerpo (Y)
        d_lat = np.linalg.norm((P - cerca)[:, [0, 2]], axis=1)
        W[resto, col[nombre]] += np.exp(-((d / (0.9 * largo)) ** 2)) * np.exp(-((d_lat / (0.6 * L)) ** 2))
    # suavizado sobre la malla (promedio con los vecinos por las aristas): sin esto, donde dos
    # huesos se reparten la piel (cuello–cabeza del Hyperodapedon) la malla se abría al girar
    aristas = np.array([e.vertices[:] for e in malla.data.edges], dtype=np.int64)
    if len(aristas):
        grado = np.bincount(aristas.ravel(), minlength=n).astype(float)[:, None] + 1e-9
        for _ in range(10):
            vecinos = np.zeros_like(W)
            np.add.at(vecinos, aristas[:, 0], W[aristas[:, 1]])
            np.add.at(vecinos, aristas[:, 1], W[aristas[:, 0]])
            W = 0.5 * W + 0.5 * vecinos / grado
    # normalizar y quedarse con los 4 mayores (lo que pide Unity por defecto)
    orden = np.argsort(-W, axis=1)
    mascara = np.zeros_like(W, bool)
    np.put_along_axis(mascara, orden[:, :4], True, axis=1)
    W = np.where(mascara, W, 0)
    W /= W.sum(1, keepdims=True) + 1e-12
    for nombre in huesos:
        malla.vertex_groups.new(name=nombre)
    for nombre, i in col.items():
        g = malla.vertex_groups[nombre]
        idx = np.nonzero(W[:, i] > 0.001)[0]
        for v in idx:
            g.add([int(v)], float(W[v, i]), "REPLACE")
    mod = malla.modifiers.new("esqueleto", "ARMATURE")
    mod.object = esq
    malla.parent = esq
    return int(asignado.sum())


# ------------------------------------------------------------------------------------------
# animaciones
# ------------------------------------------------------------------------------------------

def clave(pb, frame, rot):
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = rot
    pb.keyframe_insert("rotation_euler", frame=frame)


def accion(esq, nombre, cuadros, pose):
    """pose(t en 0..1, nombre del hueso) → (x, y, z) en radianes; keys cada 2 cuadros, cíclica."""
    act = bpy.data.actions.new(nombre)
    esq.animation_data_create()
    esq.animation_data.action = act
    for f in range(0, cuadros + 1, 2):
        t = f / cuadros
        for pb in esq.pose.bones:
            r = pose(t, pb.name)
            if r is not None:
                clave(pb, f, r)
    act.use_fake_user = True
    # cada acción en su pista del NLA: así el FBX lleva las tres
    pista = esq.animation_data.nla_tracks.new()
    pista.name = nombre
    pista.strips.new(nombre, 0, act)
    esq.animation_data.action = None
    return act


def animar(esq, datos, cfg):
    tipo = cfg["tipo"]
    T = cfg["ciclo"]
    A = math.radians(cfg["muslo"])
    U = math.radians(cfg["ondula"])
    fase = {"tra_izq": 0.0, "del_izq": 0.25, "tra_der": 0.5, "del_der": 0.75} if tipo == "cuadrupedo" else {"tra_izq": 0.0, "tra_der": 0.5}
    s2 = lambda x: math.sin(2 * math.pi * x)

    def caminar(t, b):
        partes = b.split("_")
        if partes[0] in ("muslo", "canilla", "pie"):
            p = "_".join(partes[1:])
            ph = t + fase.get(p, 0)
            swing = s2(ph)                                  # + adelante
            vuelo = max(0.0, math.cos(2 * math.pi * ph))   # la pata en el aire flexiona
            if partes[0] == "muslo":
                return (A * swing, 0, 0)
            if partes[0] == "canilla":
                signo = 1 if p.startswith("del") else -1
                return (signo * 0.9 * A * vuelo, 0, 0)
            return (-A * swing * 0.6 + 0.5 * A * vuelo, 0, 0)
        n_pasos = 2                                         # dos pasos por ciclo: el cuerpo ondula dos veces
        if b == "pelvis":
            return (0.02 * s2(n_pasos * t), 0, U * 0.5 * s2(t))
        if b.startswith("columna"):
            i = int(b.split("_")[1])
            return (0.01 * s2(n_pasos * t + 0.1 * i), 0, -U * s2(t - 0.12 * i))
        if b.startswith("cola"):
            i = int(b.split("_")[1])
            return (0.02 * s2(n_pasos * t), 0, (U + math.radians(3)) * s2(t - 0.1 * i - 0.2))
        if b.startswith("cuello"):
            return (-0.03 * s2(n_pasos * t), 0, U * 0.4 * s2(t + 0.3))
        if b.startswith("cabeza"):
            return (0.04 * s2(n_pasos * t + 0.25), 0, -U * 0.5 * s2(t + 0.3))
        return None

    def quieto(t, b):
        # respira (la columna sube y baja apenas), mira a un lado y al otro, la cola se mece
        if b.startswith("columna"):
            return (0.015 * s2(t * 2), 0, 0)
        if b.startswith("cuello"):
            return (0.02 * s2(t * 2 + 0.2), 0, 0.12 * s2(t))
        if b.startswith("cabeza"):
            return (0.03 * s2(t * 2 + 0.4), 0, 0.15 * s2(t - 0.05))
        if b.startswith("cola"):
            i = int(b.split("_")[1])
            return (0, 0, math.radians(4) * s2(t - 0.08 * i))
        return None

    baja = math.radians(38 if cfg["quieto"] == "pastar" else 22)

    def pastar(t, b):
        # baja el cuello y la cabeza al suelo, mordisquea (pastar) u olfatea (carnívoros)
        k = 0.5 - 0.5 * math.cos(2 * math.pi * min(1.0, t * 2.5)) if t < 0.2 else (1.0 if t < 0.8 else 0.5 + 0.5 * math.cos(2 * math.pi * (t - 0.8) * 2.5))
        if b.startswith("cuello"):
            return (-baja * 0.6 * k, 0, 0.05 * s2(t * 3))
        if b.startswith("cabeza"):
            return (-baja * 0.5 * k + 0.06 * k * s2(t * 9), 0, 0.04 * s2(t * 4))
        if b.startswith("columna"):
            return (-0.03 * k + 0.01 * s2(t * 2), 0, 0)
        if b.startswith("cola"):
            i = int(b.split("_")[1])
            return (0.02 * k, 0, math.radians(3) * s2(t - 0.08 * i))
        return None

    accion(esq, "caminar", int(round(T * FPS)), caminar)
    accion(esq, "quieto", int(4 * FPS), quieto)
    accion(esq, "pastar" if cfg["quieto"] == "pastar" else "olfatear", int(5 * FPS), pastar)
    # velocidad sin patinar: la pata de apoyo recorre 2·largo·sen(A) en medio ciclo
    largo = float(np.mean([p["cadera"][2] for p in datos["patas"]]))
    return 4 * largo * math.sin(A) / T


# ------------------------------------------------------------------------------------------

def vista(esq, malla, ruta, cfg):
    """Tira de 6 cuadros del caminar, de perfil (para revisar desde la nube)."""
    esc = bpy.context.scene
    esc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "CYCLES"
    esc.render.engine = "CYCLES"
    esc.cycles.samples = 8
    esc.render.resolution_x, esc.render.resolution_y = 640, 360
    esc.world = bpy.data.worlds.new("w")
    esc.world.color = (0.55, 0.55, 0.55)
    sol = bpy.data.objects.new("sol", bpy.data.lights.new("sol", "SUN"))
    sol.rotation_euler = (0.8, 0.2, 0.6)
    esc.collection.objects.link(sol)
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    esc.collection.objects.link(cam)
    cam.data.type = "ORTHO"
    L = max(d for d in malla.dimensions)
    cam.data.ortho_scale = L * 1.15
    cam.location = (L * 3, (malla.bound_box[0][1] + malla.bound_box[6][1]) / 2, malla.dimensions.z * 0.5)
    cam.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    esc.camera = cam
    act = bpy.data.actions["caminar"]
    esq.animation_data.action = act
    cuadros = int(round(cfg["ciclo"] * FPS))
    import tempfile
    tmp = tempfile.mkdtemp()
    imgs = []
    for k in range(6):
        esc.frame_set(int(k * cuadros / 6))
        esc.render.filepath = os.path.join(tmp, f"{k}.png")
        bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(esc.render.filepath)
        imgs.append(np.array(im.pixels[:], np.float32).reshape(360, 640, 4))
    tira = np.concatenate([np.concatenate(imgs[:3], 1), np.concatenate(imgs[3:], 1)], 0)
    h, w, _ = tira.shape
    out = bpy.data.images.new("tira", w, h, alpha=False)
    out.pixels.foreach_set(tira.ravel())
    out.file_format = "JPEG"
    out.save(filepath=ruta, quality=82)
    esq.animation_data.action = None


def hacer(especie, cfg, con_vista):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ORIGEN, f"{especie}.glb"))
    mallas = [o for o in bpy.data.objects if o.type == "MESH"]
    malla = mallas[0]
    for o in [o for o in bpy.data.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o)
    bpy.context.view_layer.objects.active = malla
    malla.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    V = np.array([v.co[:] for v in malla.data.vertices])
    datos = analizar(V, cfg["tipo"], cfg["cabeza"])
    esq = armar(datos, cfg["tipo"])
    en_patas = pesar(malla, esq, datos)
    velocidad = animar(esq, datos, cfg)
    carpeta = os.path.join(SALIDA, especie)
    os.makedirs(carpeta, exist_ok=True)
    # el material del FBX es sólo un nombre: Unity arma el HDRP/Lit con las texturas del GLB
    for m in malla.data.materials:
        m.name = f"{especie}_piel"
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(filepath=os.path.join(carpeta, f"{especie}.fbx"), use_selection=True,
                             object_types={"ARMATURE", "MESH"}, add_leaf_bones=False, bake_anim=True,
                             bake_anim_use_all_actions=False, bake_anim_use_nla_strips=True,
                             bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0.0,
                             axis_forward="-Z", axis_up="Y", apply_scale_options="FBX_SCALE_ALL",
                             path_mode="STRIP", mesh_smooth_type="FACE", use_armature_deform_only=True)
    informe = {"especie": especie, "tipo": cfg["tipo"], "huesos": len(esq.data.bones), "vertices": len(V),
               "vertices_en_patas": en_patas, "patas": [p["nombre"] for p in datos["patas"]],
               "velocidad_caminar_m_s": round(velocidad, 3), "ciclo_s": cfg["ciclo"],
               "animaciones": ["caminar", "quieto", "pastar" if cfg["quieto"] == "pastar" else "olfatear"],
               "largo_m": round(datos["L"], 3), "alto_m": round(datos["H"], 3)}
    with open(os.path.join(carpeta, f"{especie}.json"), "w", encoding="utf-8") as f:
        json.dump(informe, f, ensure_ascii=False, indent=1)
    if con_vista:
        vista(esq, malla, os.path.join(carpeta, f"{especie}_caminar.jpg"), cfg)
    print(f"  {especie}: {informe['huesos']} huesos, patas {informe['patas']}, camina a {informe['velocidad_caminar_m_s']} m/s", flush=True)
    return informe


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--solo", nargs="*")
    ap.add_argument("--vista", action="store_true")
    a = ap.parse_args(argv)
    hechos = []
    for archivo in sorted(os.listdir(ORIGEN)):
        especie = archivo[:-4]
        if not archivo.endswith(".glb") or especie not in ESPECIES or (a.solo and especie not in a.solo):
            continue
        hechos.append(hacer(especie, ESPECIES[especie], a.vista))
    print(f"listo: {len(hechos)} animales con esqueleto y animación → {SALIDA}")


if __name__ == "__main__":
    main()
