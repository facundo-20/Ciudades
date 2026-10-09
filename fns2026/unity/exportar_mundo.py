"""
El mundo del Triásico para Unity: las MISMAS fórmulas que el render de Blender
(escenas/hiperreal/triasico_cycles.py), pasadas a archivos que Unity lee sin Python.

    python3 exportar_mundo.py                 (con el bpy de pip, como en la nube)
    blender -b --factory-startup -P exportar_mundo.py

Sale todo a ParqueTriasico/Datos/ (fuera de Assets: Unity no los importa, los lee el
constructor del editor para armar los Terrain):
    mundo.json             terrenos, capítulos (cámara, sol, bruma), fauna, textos de las fichas
    <terreno>.r16d.gz      alturas de 16 bits (las del RAW de los Terrain de Unity), con predictor
                           y gzip: 1,8 MB en vez de 8,4 (ver codificar_predictor)
    <terreno>_capas*.png   pesos de las capas de suelo (cada PNG RGBA lleva 4 capas)
    flora_<era>.json       cada planta: x, y, z, giro (°), escala, inclinación (rad), seguidos
    barrancas_hoy.json.gz  el paredón rojo del Valle de la Luna (una pared casi vertical no
                           entra en un heightmap: va como malla)

Por qué así: el video de Cycles y la escena en vivo de Unity tienen que calzar (mismo río,
mismo bosque, misma manada) para alternarlos en el LED sin que se note. La geografía vive en
un solo lugar, triasico_cycles.py, y acá sólo se muestrea.

Coordenadas: web (x, y, z) → Unity (x, y, -z) (Unity es de mano izquierda) → Blender (x, -z, y).
"""

import gzip
import json
import math
import multiprocessing as mp
import os
import random
import struct
import sys
import time
import zlib

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.dirname(AQUI)
sys.path.insert(0, os.path.join(FNS, "escenas", "hiperreal"))
import triasico_cycles as T  # noqa: E402  (trae bpy: la geografía y el ruido son los de Blender)
from mathutils import noise  # noqa: E402

DATOS = os.path.join(AQUI, "ParqueTriasico", "Datos")

# El terreno fino mide 512 m a 0,25 m por muestra; el lejano, 8,2 km a 8 m. Los dos comparten
# grilla (8 m = 32 muestras finas) para que la costura caiga sobre puntos comunes.
CERCA = dict(x0=-226.0, z0=-256.0, lado=512.0, res=2049)
LEJOS = dict(x0=-3826.0, z0=-3840.0, lado=8192.0, res=1025)
VOLCAN = (1100.0, -700.0)            # web (x, z): el mismo lugar que en Blender
CENTRO_MUNDO = (20.0, 0.0)

CAPAS = {
    # el orden es el de las TerrainLayer en Unity; los nombres, los de texturas_suelo.py
    "triasico": ["barro", "barro_humedo", "arena", "hojarasca", "loma", "basalto"],
    "hoy": ["arcilla_gris", "arcilla_clara", "estratos", "ripio"],
}


# ------------------------------------------------------------------------------------------
# alturas
# ------------------------------------------------------------------------------------------

PERFIL_VOLCAN = [(0, 232), (83.6, 268.4), (121, 275), (176, 248.6), (242, 209), (330, 149.6),
                 (418, 88), (495, 39.6), (572, 0)]      # el perfil de Blender × 2,2, con fondo de cráter


def volcan_h(x, zw):
    """Altura del volcán en (x, zw) o None fuera de su base. Mismo cono, cárcavas y relieve que
    volcan() de Blender, pero como relieve del terreno lejano."""
    cx, cz = VOLCAN
    r = math.hypot(x - cx, zw - cz)
    if r >= PERFIL_VOLCAN[-1][0]:
        return None
    for (r0, h0), (r1, h1) in zip(PERFIL_VOLCAN, PERFIL_VOLCAN[1:]):
        if r <= r1:
            h = h0 + (h1 - h0) * (r - r0) / (r1 - r0)
            break
    ang = math.atan2(-(zw - cz), x - cx)            # en ejes de Blender (y = -zw), como allá
    surcos = abs(T.fbm2(ang * 9.0, 0.3, 3)) * min(1.0, r / 150) * 18
    return -30 + h + T.fbm2(x * 0.01, -zw * 0.01, 4) * 40 - surcos


def cerros(x, zw):
    return 18 + T.fbm2(x * 0.004, zw * 0.004, 3) * 60


def dentro_de_cerca(x, zu, margen=0.0):
    return (CERCA["x0"] + margen <= x <= CERCA["x0"] + CERCA["lado"] - margen
            and CERCA["z0"] + margen <= zu <= CERCA["z0"] + CERCA["lado"] - margen)


def altura(era, x, zw):
    T.MODO["hoy"] = era == "hoy"
    return T.altura(x, zw)


def altura_lejos(era, x, zw):
    """Más allá del mundo, el relieve se funde en cerros bajos (como el anillo de horizonte de
    Blender) y aparece el volcán. Sin río: allá no llega el plano de agua."""
    r = math.hypot(x - CENTRO_MUNDO[0], zw - CENTRO_MUNDO[1])
    w = T.lisa(380, 1000, r)
    h = altura(era, x, zw) if w < 1 else 0.0
    h = h * (1 - w) + cerros(x, zw) * w
    h = max(h, T.NIVEL_AGUA + 0.3)
    if era == "triasico":
        hv = volcan_h(x, zw)
        if hv is not None:
            # el pie del cono se funde con la llanura en 60 m (si no, queda un escalón)
            borde = T.lisa(572, 512, math.hypot(x - VOLCAN[0], zw - VOLCAN[1]))
            h = max(h, h + (hv - h) * borde)
    return h


def _fila(args):
    """Una fila de muestras (en un proceso aparte: son 4 millones de puntos)."""
    era, cual, j = args
    noise.seed_set(231)
    g = CERCA if cual == "cerca" else LEJOS
    paso = g["lado"] / (g["res"] - 1)
    zu = g["z0"] + j * paso
    out = []
    for i in range(g["res"]):
        x = g["x0"] + i * paso
        if cual == "cerca":
            out.append(altura(era, x, -zu))
        elif dentro_de_cerca(x, zu, margen=paso * 1.5):
            out.append(None)                 # debajo del terreno fino: se hunde después
        elif dentro_de_cerca(x, zu, margen=paso * 0.5):
            # franja entre la costura y el hundido: 30 cm abajo del fino, para que no peleen
            # los dos terrenos por el mismo píxel (parpadeo)
            out.append(altura_lejos(era, x, -zu) - 0.3)
        else:
            out.append(altura_lejos(era, x, -zu))
    return j, out


def muestrear(era, cual, procesos):
    g = CERCA if cual == "cerca" else LEJOS
    filas = [None] * g["res"]
    t0 = time.time()
    with mp.Pool(procesos) as pool:
        for k, (j, fila) in enumerate(pool.imap_unordered(_fila, [(era, cual, j) for j in range(g["res"])], chunksize=8)):
            filas[j] = fila
            if k % 256 == 0:
                print(f"   {era}/{cual}: {k}/{g['res']} filas · {time.time() - t0:.0f} s", flush=True)
    return filas


def guardar_alturas(nombre, filas, cual):
    validos = [h for f in filas for h in f if h is not None]
    hmin, hmax = min(validos), max(validos)
    if cual == "lejos":
        # lo que queda debajo del terreno fino va 6 m abajo de todo: nunca asoma por encima
        hmin -= 6.0
        filas = [[hmin if h is None else h for h in f] for f in filas]
    else:
        # pollera: las dos filas del borde bajan 3 m, así la costura con el lejano no deja
        # ver el cielo por una rendija
        n = len(filas)
        hmin -= 3.0
        for j in range(n):
            for i in range(n):
                if min(i, j, n - 1 - i, n - 1 - j) < 2:
                    filas[j][i] -= 3.0
    rango = max(1e-3, hmax - hmin)
    import numpy as np
    # fila j = z de Unity creciente, columna i = x creciente (lo que pide TerrainData.SetHeights)
    a = np.array([[int(round((h - hmin) / rango * 65535)) for h in f] for f in filas], dtype=np.int64)
    with gzip.open(os.path.join(DATOS, f"{nombre}.r16d.gz"), "wb", compresslevel=9) as z:
        z.write(codificar_predictor(a).tobytes())
    return hmin, hmax


def codificar_predictor(a):
    """Alturas de 16 bits → residuo del predictor plano (izquierda + arriba - diagonal), módulo
    65536. Un relieve suave da residuos chicos y gzip los comprime 4 veces mejor que el RAW
    (de 7,7 a 1,8 MB el terreno fino). Sin pérdida: Unity lo deshace en Datos.cs."""
    import numpy as np
    p = np.zeros_like(a)
    p[:, 1:] += a[:, :-1]
    p[1:, :] += a[:-1, :]
    p[1:, 1:] -= a[:-1, :-1]
    return ((a - p) % 65536).astype("<u2")


def decodificar_predictor(r, res):
    """La inversa (para la prueba de ida y vuelta; Unity hace lo mismo en C#)."""
    import numpy as np
    r = r.reshape(res, res).astype(np.int64)
    a = np.zeros_like(r)
    for j in range(res):
        izq = 0
        for i in range(res):
            arriba = a[j - 1, i] if j else 0
            diag = a[j - 1, i - 1] if (i and j) else 0
            izq = (r[j, i] + izq + arriba - diag) % 65536
            a[j, i] = izq
    return a


# ------------------------------------------------------------------------------------------
# capas de suelo (pesos que suman 1, como el color de la web pero por material)
# ------------------------------------------------------------------------------------------

def mezclar(w, i, k):
    """Lleva una fracción k del peso actual hacia la capa i (lo mismo que un lerp de colores)."""
    k = max(0.0, min(1.0, k))
    for c in range(len(w)):
        w[c] *= 1 - k
    w[i] += k


def pesos_triasico(x, zw, h, lejos=False):
    w = [1.0, 0, 0, 0, 0, 0]
    d, rio = T.dist_rio(x, zw), T.hay_rio(x)
    if not lejos:
        humedo = rio * math.exp(-((d / 9) ** 2))
        arena = rio * math.exp(-(((d - 7) / 2.2) ** 2)) * (0.6 + 0.4 * T.fbm2(x * 0.2, zw * 0.2, 2))
        # hojarasca y helechos: NO hay pasto en el Triásico (las gramíneas llegan 150 Ma después)
        veg = max(0.0, min(1.0, 0.45 + T.fbm2(x * 0.05, zw * 0.05, 3) * 1.6 - humedo)) * (1.0 if 8 < x < 75 else 0.55)
        mezclar(w, 1, humedo)
        mezclar(w, 2, arena)
        mezclar(w, 3, veg * 0.75)
        if h < T.NIVEL_AGUA - 0.2:               # el lecho del río: barro húmedo con arena
            mezclar(w, 1, 0.7)
    mezclar(w, 4, (h - 6) / 14)
    if lejos:
        hv = volcan_h(x, zw)
        if hv is not None:
            mezclar(w, 5, T.lisa(560, 480, math.hypot(x - VOLCAN[0], zw - VOLCAN[1])))
    return w


def pesos_hoy(x, zw, h, lejos=False):
    w = [1.0, 0, 0, 0]
    mezclar(w, 1, 0.5 + 0.5 * T.fbm2(x * 0.3, zw * 0.3, 2) - 0.25)
    # las lomas pasan a los estratos rojos: desde 1,5 m ya se ven las bandas
    mezclar(w, 2, (h - 1.5) / 5)
    if not lejos:
        mezclar(w, 3, (T.fbm2(x * 0.08 + 40, zw * 0.08, 3) - 0.12) * 3)   # manchones de ripio
    return w


def _fila_capas(args):
    era, cual, j, res = args
    noise.seed_set(231)
    g = CERCA if cual == "cerca" else LEJOS
    paso = g["lado"] / (res - 1)
    zu = g["z0"] + j * paso
    out = []
    for i in range(res):
        x = g["x0"] + i * paso
        zw = -zu
        h = altura(era, x, zw) if cual == "cerca" else altura_lejos(era, x, zw)
        f = pesos_triasico if era == "triasico" else pesos_hoy
        out.append(f(x, zw, h, lejos=cual == "lejos"))
    return j, out


def png_rgba(ruta, ancho, alto, filas_rgba):
    """PNG RGBA de 8 bits sin dependencias (zlib de la biblioteca estándar)."""
    crudo = b"".join(b"\x00" + bytes(f) for f in filas_rgba)

    def trozo(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    with open(ruta, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + trozo(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0))
                + trozo(b"IDAT", zlib.compress(crudo, 9)) + trozo(b"IEND", b""))


def guardar_capas(era, cual, res, procesos):
    filas = [None] * res
    with mp.Pool(procesos) as pool:
        for j, fila in pool.imap_unordered(_fila_capas, [(era, cual, j, res) for j in range(res)], chunksize=8):
            filas[j] = fila
    n = len(CAPAS[era])
    archivos = []
    for k in range(0, n, 4):
        png = []
        # PNG va de arriba hacia abajo y Texture2D.LoadImage lo da vuelta: se escribe al revés
        # para que la fila 0 de la textura sea z mínima, igual que las alturas
        for fila in reversed(filas):
            b = bytearray()
            for w in fila:
                for c in range(4):
                    b.append(int(round(255 * w[k + c])) if k + c < n else 0)
            png.append(b)
        nombre = f"{era}_{cual}_capas{k // 4}.png"
        png_rgba(os.path.join(DATOS, nombre), res, res, png)
        archivos.append(nombre)
    return archivos


# ------------------------------------------------------------------------------------------
# flora: las reglas de hábitat de Blender, para todo el mundo y no sólo un capítulo
# ------------------------------------------------------------------------------------------

def segmentos_de_camara():
    seg = []
    for cap in T.CAPITULOS.values():
        seg.append(((cap["desde"][0], cap["desde"][2]), (cap["hasta"][0], cap["hasta"][2])))
    return seg


def cerca_de_camaras(x, zw, segmentos, radio=9.0):
    for (ax, az), (bx, bz) in segmentos:
        vx, vz = bx - ax, bz - az
        t = max(0.0, min(1.0, ((x - ax) * vx + (zw - az) * vz) / max(1e-6, vx * vx + vz * vz)))
        if math.hypot(x - (ax + t * vx), zw - (az + t * vz)) < radio:
            return True
    # el cono de la llanura hacia el volcán (sin árboles altos en ±14°, hasta 220 m)
    cap = T.CAPITULOS["llanura"]
    T.CAMINO["cono"] = ((cap["desde"][0] + cap["hasta"][0]) / 2, (cap["desde"][2] + cap["hasta"][2]) / 2,
                        cap["mira"][0], cap["mira"][2])
    return T.en_el_cono(x, zw)


def sembrar(era, area):
    """Mismas densidades por 100 m² que sembrar() de Blender, en el área dada (x0, z0, x1, z1 web)."""
    noise.seed_set(231)
    T.MODO["hoy"] = era == "hoy"
    azar = random.Random(231)
    x0, z0, x1, z1 = area
    ha = (x1 - x0) * (z1 - z0) / 10000.0
    segmentos = segmentos_de_camara()
    plantas = {}
    for nombre, por_100m2, regla, (e0, e1) in (T.REGLAS_HOY if era == "hoy" else T.REGLAS):
        objetivo = int(por_100m2 * ha * 100)
        hechos = 0
        for _ in range(objetivo * 6):
            if hechos >= objetivo:
                break
            x = x0 + azar.random() * (x1 - x0)
            zw = z0 + azar.random() * (z1 - z0)
            if not regla(x, zw):
                continue
            if nombre not in T.PLANTAS_BAJAS and cerca_de_camaras(x, zw, segmentos):
                continue
            h = altura(era, x, zw)
            if h < T.NIVEL_AGUA + 0.15:
                continue
            giro = azar.uniform(0, 360)
            esc = azar.uniform(e0, e1)
            inc = azar.uniform(-0.06, 0.06)
            # [x, y, z, giro°, escala, inclinación en rad] en coordenadas de Unity
            plantas.setdefault(nombre, []).append([round(x, 2), round(h - 0.05, 3), round(-zw, 2),
                                                   round(giro, 1), round(esc, 3), round(inc, 3)])
            hechos += 1
    return plantas


# ------------------------------------------------------------------------------------------
# hoy: el paredón rojo (barrancas() de Blender, como malla con UV por altura)
# ------------------------------------------------------------------------------------------

def barrancas_malla(ruta, ojo, mira, distancia=230.0, abertura=130.0, columnas=520):
    noise.seed_set(231)
    T.MODO["hoy"] = True
    ox, oz = ojo
    rumbo = math.atan2(mira[1] - oz, mira[0] - ox)
    perfil = [(-50, 0.0), (-26, 0.07), (-12, 0.15), (-2, 0.22), (0, 0.45), (1, 0.72), (2, 0.95), (4, 1.0), (90, 0.97)]
    # perfil más denso (Blender subdivide una vez): entre cada par de puntos, uno intermedio
    denso = []
    for (a, fa), (b, fb) in zip(perfil, perfil[1:]):
        denso += [(a, fa), ((a + b) / 2, (fa + fb) / 2)]
    denso.append(perfil[-1])
    verts, uvs = [], []
    arco = 2 * math.radians(abertura) * distancia / columnas
    for c in range(columnas):
        cc = c * 260 / columnas                     # el ruido en las mismas unidades que Blender
        a = rumbo + math.radians(-abertura + 2 * abertura * c / (columnas - 1))
        carcava = abs(T.fbm2(cc * 0.09, 3.3, 3)) * 2.2
        alto = 58 + T.fbm2(cc * 0.012, 9.1, 4) * 55
        r0 = distancia + T.fbm2(cc * 0.02, 1.7, 3) * 60 + carcava * 14
        for dr, fh in denso:
            r = r0 + dr * (1 + 0.4 * carcava)
            x, zw = ox + r * math.cos(a), oz + r * math.sin(a)
            y = T.altura(x, zw) - 1.0 + fh * alto * (1 - 0.18 * carcava * (fh < 0.99))
            # relieve de roca a escala de metros (el mismo desplazamiento que en Blender)
            dx = T.fbm2(-zw * 0.3, y * 0.3, 3) * 1.8
            dz = T.fbm2(x * 0.3, y * 0.3 + 5, 3) * 1.8
            verts += [round(x + dx, 3), round(y, 3), round(-(zw - dz), 3)]
            # UV: una vuelta de textura cada 20 m, V por altura absoluta: los estratos quedan horizontales
            uvs += [round(c * arco / 20.0, 4), round(y / 20.0, 4)]
    filas = len(denso)
    tris = []
    for c in range(columnas - 1):
        for k in range(filas - 1):
            a_, b_ = c * filas + k, (c + 1) * filas + k
            # vista desde el centro del arco: (c,k) abajo-izquierda, (c+1,k+1) arriba-derecha;
            # en sentido horario = cara de frente en Unity
            tris += [a_, a_ + 1, b_ + 1, a_, b_ + 1, b_]
    with gzip.open(ruta, "wt", encoding="utf-8") as f:
        json.dump({"vertices": verts, "uv": uvs, "triangulos": tris}, f, separators=(",", ":"))
    return len(verts) // 3, len(tris) // 3


# ------------------------------------------------------------------------------------------
# mundo.json
# ------------------------------------------------------------------------------------------

TEXTOS = {
    # títulos, duraciones y fichas de la experiencia web (capitulos.js): el mismo guion
    "titulo": ("ISCHIGUALASTO", "San Juan, hace 231 millones de años · El amanecer de los dinosaurios", 14, []),
    "rio": ("El río", "Una llanura con ríos que serpentean, lluvias de temporada y mucha vida", 45, ["hyperodapedon", "neocalamites"]),
    "bosque": ("El bosque de Dicroidium", "Frondas que se bifurcan, coníferas y helechos. Todavía no existía el pasto", 45,
               ["eoraptor", "herrerasaurus", "panphagia", "dicroidium"]),
    "llanura": ("La llanura y el volcán", "Al oeste, volcanes activos en el borde del continente, donde mucho después se levantarían los Andes", 40,
                ["ischigualastia", "herrerasaurus"]),
    "ceniza": ("La lluvia de ceniza", "El barro de las crecidas y la ceniza fueron tapando los restos. La ceniza permite fecharlos: 231 millones de años", 30,
               ["ceniza"]),
    "hoy": ("Hoy: el Valle de la Luna", "Parque Provincial Ischigualasto · Patrimonio de la Humanidad (UNESCO, 2000) · Conocelos en el MuPa", 40,
            ["hoy"]),
}

ESPECIES = {
    # largo real (m), velocidad de paseo (m/s), zona donde anda (para el paseo en Unity)
    "herrerasaurus": (4.0, 2.2, ["bosque", "llanura"]), "eoraptor": (1.0, 2.8, ["bosque"]),
    "eodromaeus": (1.2, 3.0, ["bosque"]), "panphagia": (1.3, 1.8, ["bosque"]),
    "hyperodapedon": (1.3, 0.9, ["rio"]), "ischigualastia": (3.5, 0.8, ["llanura"]),
    "sanjuansaurus": (3.0, 2.4, ["llanura"]), "saurosuchus": (6.0, 1.6, ["llanura", "rio"]),
    "exaeretodon": (1.8, 1.1, ["rio", "bosque"]),
}


def leer_fichas():
    """Las fichas salen de capitulos.js (una sola versión de los textos a validar con la UNSJ)."""
    ruta = os.path.join(FNS, "experiencia", "src", "capitulos.js")
    txt = open(ruta, encoding="utf-8").read()
    fichas = {}
    bloque = txt[txt.index("export const FICHAS"):]
    import re
    for m in re.finditer(r"(\w+): \{\s*titulo: '([^']*)',\s*dato: '([^']*)',\s*texto: '([^']*)',\s*\}", bloque):
        fichas[m.group(1)] = {"titulo": m.group(2), "dato": m.group(3), "texto": m.group(4)}
    return fichas


def a_unity(p):
    return [round(p[0], 3), round(p[1], 3), round(-p[2], 3)]


def sol_unity(elev, az):
    """Dirección HACIA el sol en Unity, con la convención de la lámpara de Blender (azimut desde
    +X hacia +Y de Blender, que es +Z de Unity)."""
    e, a = math.radians(elev), math.radians(az)
    return [round(math.cos(e) * math.cos(a), 5), round(math.sin(e), 5), round(math.cos(e) * math.sin(a), 5)]


def capitulos(valle=None):
    out = []
    for clave, cap in T.CAPITULOS.items():
        titulo, sub, dur, fichas = TEXTOS[clave]
        elev, az = cap["sol"]
        bruma = cap["bruma"]
        out.append({
            "clave": clave, "titulo": titulo, "subtitulo": sub, "duracion": dur, "fichas": fichas,
            "desde": a_unity(cap["desde"]), "hasta": a_unity(cap["hasta"]), "mira": a_unity(cap["mira"]),
            "sol_elevacion": elev, "sol_azimut": az, "hacia_sol": sol_unity(elev, az),
            # la bruma de Blender es densidad por metro; HDRP pide el recorrido medio (1/densidad)
            "bruma_recorrido_m": round(min(6000.0, 1.0 / bruma), 1) if bruma > 0 else 6000.0,
            "ceniza": cap["ceniza"], "volcan": cap["volcan"], "era": "hoy" if cap.get("hoy") else "triasico",
            "exposicion": cap.get("exposicion", 0.0), "foco_m": cap.get("foco", 12.0), "diafragma": cap.get("f", 4.0),
        })
        if clave == "hoy" and valle and "camara_hoy" in valle:
            # hoy: el Valle de la Luna real, con su propio marco (x este, z norte, y sobre 1250 m s. n. m.)
            c, sol = valle["camara_hoy"], valle["sol_hoy"]
            out[-1].update({"desde": c["desde"], "hasta": c["hasta"], "mira": c["mira"], "hacia_sol": sol["hacia_sol"],
                            "sol_elevacion": sol["elevacion"], "sol_azimut": sol["azimut_brujula"], "exposicion": -0.6})
    return out


def fauna():
    noise.seed_set(231)
    T.MODO["hoy"] = False
    out = []
    for especie, lugares in T.ESPECIES_LUGARES.items():
        for (x, zw, rumbo) in lugares:
            if zw is None:
                zw = T.cauce(x) + 9.5
            # el modelo de Meshy mira a +Z (glTF), en Blender a -Y: rumbo θ de Blender = 180° - θ en Unity
            out.append({"especie": especie, "pos": [round(x, 2), round(T.altura(x, zw), 3), round(-zw, 2)],
                        "giro": round(180 - math.degrees(rumbo), 1)})
    return out


def main():
    os.makedirs(DATOS, exist_ok=True)
    procesos = max(1, (os.cpu_count() or 2))
    solo = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    hacer = set(solo) or {"alturas", "capas", "flora", "barrancas", "json"}
    t0 = time.time()
    terrenos = []
    meta_path = os.path.join(DATOS, "terrenos.json")
    previos = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    for era in ("triasico",):                # "hoy" es el Valle de la Luna real: valle_real.py
        for cual in ("cerca", "lejos"):
            g = CERCA if cual == "cerca" else LEJOS
            nombre = f"{era}_{cual}"
            if "alturas" in hacer:
                print(f"== alturas {nombre} ({g['res']}²)", flush=True)
                hmin, hmax = guardar_alturas(nombre, muestrear(era, cual, procesos), cual)
            else:
                hmin, hmax = previos[nombre]["hmin"], previos[nombre]["hmax"]
            capas_res = 1025 if cual == "cerca" else 513
            if "capas" in hacer:
                print(f"== capas {nombre} ({capas_res}²)", flush=True)
                archivos = guardar_capas(era, cual, capas_res, procesos)
            else:
                archivos = previos[nombre]["capas_png"]
            previos[nombre] = {"nombre": nombre, "era": era, "cual": cual, "x0": g["x0"], "z0": g["z0"], "lado": g["lado"],
                               "res": g["res"], "hmin": round(hmin, 4), "hmax": round(hmax, 4),
                               "alturas": f"{nombre}.r16d.gz", "capas": CAPAS[era], "capas_png": archivos, "capas_res": capas_res}
            terrenos.append(previos[nombre])
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(previos, f, ensure_ascii=False, indent=1)
    if "flora" in hacer:
        print("== flora", flush=True)
        for era in ("triasico",):            # las piedras de hoy las pone valle_real.py, en su marco
            plantas = sembrar(era, (-180, -160, 230, 160))
            # formato que entiende JsonUtility de Unity: listas de objetos, sin diccionarios ni
            # listas anidadas (cada planta son 6 números seguidos)
            salida = {"especies": [{"nombre": k, "datos": [n for p in v for n in p]} for k, v in plantas.items()]}
            with open(os.path.join(DATOS, f"flora_{era}.json"), "w", encoding="utf-8") as f:
                json.dump(salida, f, separators=(",", ":"))
            print("   ", era, {k: len(v) for k, v in plantas.items()}, flush=True)
    if "barrancas" in hacer:
        cap = T.CAPITULOS["hoy"]
        ojo = ((cap["desde"][0] + cap["hasta"][0]) / 2, (cap["desde"][2] + cap["hasta"][2]) / 2)
        nv, nc = barrancas_malla(os.path.join(DATOS, "barrancas_hoy.json.gz"), ojo, (cap["mira"][0], cap["mira"][2]))
        print(f"== barrancas: {nv} vértices, {nc} triángulos", flush=True)
    if "json" in hacer:
        ruta_valle = os.path.join(DATOS, "valle_real.json")
        valle = json.load(open(ruta_valle, encoding="utf-8")) if os.path.exists(ruta_valle) else {}
        if not valle:
            print("   OJO: falta valle_real.json (correr valle_real.py): 'hoy' queda sin terreno", flush=True)
        mundo = {
            "_nota": "Generado por fns2026/unity/exportar_mundo.py desde triasico_cycles.py. No editar a mano.",
            "nivel_agua": T.NIVEL_AGUA,
            "mundo": {"x0": -130, "x1": 170, "z0": -120, "z1": 120},
            "rio": {"x_max": 40.0, "nota": "cauce: z_web = 10 sen(0,035 x) + 4 sen(0,09 x + 1,3); en Unity z = -z_web"},
            "volcan": [VOLCAN[0], 245.0, -VOLCAN[1]],
            "terrenos": [previos[f"triasico_{c}"] for c in ("cerca", "lejos")] + valle.get("terrenos", []),
            "capitulos": capitulos(valle),
            "fauna": fauna(),
            "especies": [{"clave": k, "largo": v[0], "velocidad": v[1], "zonas": v[2]} for k, v in ESPECIES.items()],
            "fichas": [dict(clave=k, **v) for k, v in leer_fichas().items()],
        }
        with open(os.path.join(DATOS, "mundo.json"), "w", encoding="utf-8") as f:
            json.dump(mundo, f, ensure_ascii=False, indent=1)
    print(f"listo en {time.time() - t0:.0f} s → {DATOS}", flush=True)


if __name__ == "__main__":
    mp.set_start_method("fork", force=True)
    main()
