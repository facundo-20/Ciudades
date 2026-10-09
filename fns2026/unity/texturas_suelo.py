"""
Texturas PBR del suelo para las capas de los Terrain de Unity, hechas acá (procedurales y
"tileables": se repiten sin costura). Son el piso de calidad garantizado; si en la PC se bajaron
las escaneadas CC0 de Poly Haven (escenas/hiperreal/bajar_texturas_cc0.py), Unity usa ésas.

    python3 texturas_suelo.py              (numpy + el bpy de pip, para guardar JPG)
    python3 texturas_suelo.py --res 2048

Sale a ParqueTriasico/Datos/suelo/<capa>_{color,normal,hra}.jpg:
    color    albedo en sRGB
    normal   mapa de normales en convención OpenGL (+Y arriba), la que espera Unity
    hra      R = altura, G = oclusión, B = rugosidad. El constructor de Unity lo empaqueta en el
             "mask map" de HDRP (metal, oclusión, altura, lisura = 1 - rugosidad)

Cada capa dice cuántos metros cubre una vuelta de la textura (mundo_m): Unity lo usa de tileSize.
Todo con FFT y Voronoi periódicos: lo que sale por un borde entra por el otro.
"""

import argparse
import json
import os

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(AQUI, "ParqueTriasico", "Datos", "suelo")


# ------------------------------------------------------------------------------------------
# herramientas periódicas
# ------------------------------------------------------------------------------------------

def frecuencias(n):
    f = np.fft.fftfreq(n) * n
    fx, fy = np.meshgrid(f, f)
    return np.sqrt(fx * fx + fy * fy)


def espectral(n, beta, rng, f_min=1.0, f_max=None):
    """Ruido fractal periódico: ruido blanco filtrado por 1/f^(beta/2). beta 2 = terreno suave,
    beta 1 = más grano. Normalizado a media 0 y desvío 1."""
    k = frecuencias(n)
    filtro = np.where(k >= f_min, 1.0 / np.maximum(k, 1e-6) ** (beta / 2), 0.0)
    if f_max:
        filtro *= np.exp(-((k / f_max) ** 2))
    campo = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * filtro))
    return (campo - campo.mean()) / (campo.std() + 1e-9)


def desenfocar(img, sigma_px):
    k = frecuencias(img.shape[0])
    g = np.exp(-2 * (np.pi * sigma_px * k / img.shape[0]) ** 2)
    return np.real(np.fft.ifft2(np.fft.fft2(img) * g))


def malla_uv(n):
    v, u = np.meshgrid((np.arange(n) + 0.5) / n, (np.arange(n) + 0.5) / n, indexing="ij")
    return u, v


def voronoi(n, celdas, rng, deformar=None, aniso=None):
    """Distancias F1 y F2 a puntos al azar (uno por celda) con vuelta periódica, más el índice
    del punto más cercano (para darle a cada celda su propio color o tamaño).
    aniso: (angulo[celdas,celdas], estiramiento[celdas,celdas]) → hojas y ramitas alargadas."""
    u, v = malla_uv(n)
    if deformar is not None:
        u = u + deformar[0]
        v = v + deformar[1]
    pu, pv = u * celdas, v * celdas
    ci, cj = np.floor(pu).astype(int), np.floor(pv).astype(int)
    jit = rng.random((celdas, celdas, 2))
    f1 = np.full((n, n), 9.0)
    f2 = np.full((n, n), 9.0)
    ide = np.zeros((n, n), dtype=np.int64)
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            ii, jj = ci + di, cj + dj
            im, jm = ii % celdas, jj % celdas
            dx = ii + jit[jm, im, 0] - pu
            dy = jj + jit[jm, im, 1] - pv
            if aniso is not None:
                ang, est = aniso[0][jm, im], aniso[1][jm, im]
                c, s = np.cos(ang), np.sin(ang)
                dx, dy = (dx * c + dy * s), (-dx * s + dy * c) * est
            d = np.sqrt(dx * dx + dy * dy)
            mas_cerca = d < f1
            f2 = np.where(mas_cerca, f1, np.minimum(f2, d))
            ide = np.where(mas_cerca, jm * celdas + im, ide)
            f1 = np.where(mas_cerca, d, f1)
    return f1, f2, ide


def piedritas(n, celdas, rng, ocupacion=0.6, radio=(0.15, 0.42), achatar=0.6):
    """Guijarros redondeados: una cúpula por celda de Voronoi (algunas celdas vacías)."""
    deform = (espectral(n, 2.5, rng) * 0.004, espectral(n, 2.5, rng) * 0.004)
    f1, _, ide = voronoi(n, celdas, rng, deformar=deform)
    tam = rng.uniform(*radio, size=celdas * celdas)[ide]
    hay = (rng.random(celdas * celdas) < ocupacion)[ide]
    h = np.sqrt(np.clip(tam * tam - f1 * f1, 0, None)) * hay
    return h * achatar / radio[1], ide, hay & (f1 < tam)


def normalizar(x):
    return (x - x.min()) / (x.max() - x.min() + 1e-9)


def normal_desde_altura(h, fuerza):
    """Normales en convención OpenGL. h en [0,1]; fuerza = cuántos píxeles de relieve por unidad."""
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * fuerza
    # filas de la imagen hacia abajo = V hacia abajo: la derivada en V cambia de signo
    dv = -(np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * fuerza
    nx, ny, nz = -dx, -dv, np.ones_like(h)
    largo = np.sqrt(nx * nx + ny * ny + nz * nz)
    return np.stack([nx / largo, ny / largo, nz / largo], axis=-1) * 0.5 + 0.5


def oclusion(h, sigma, fuerza):
    """Oclusión de cavidad: lo que queda más bajo que su entorno recibe menos luz del cielo."""
    return np.clip(1.0 - (desenfocar(h, sigma) - h) * fuerza, 0.25, 1.0)


def srgb(c):
    return np.array(c, dtype=np.float64) / 255.0


def teñir(base, variacion, mapa):
    """Color base con manchas: mapa en ~[-2, 2] mueve el color hacia ± variación."""
    return np.clip(base[None, None, :] * (1 + variacion * mapa[..., None]), 0, 1)


def mezcla(a, b, t):
    return a * (1 - t[..., None]) + b * t[..., None]


# ------------------------------------------------------------------------------------------
# las capas
# ------------------------------------------------------------------------------------------

def barro(n, rng, humedo=False):
    """Barro de llanura de inundación: limo con ondulaciones blandas, grietas finas apenas
    insinuadas (se seca y se moja con cada crecida) y alguna piedrita."""
    ond = espectral(n, 3.0, rng)
    grano = espectral(n, 1.2, rng, f_min=60)
    f1, f2, _ = voronoi(n, 9, rng, deformar=(espectral(n, 2.5, rng) * 0.01, espectral(n, 2.5, rng) * 0.01))
    grieta = np.clip((f2 - f1) / 0.04, 0, 1)
    pie, _, sobre = piedritas(n, 34, rng, ocupacion=0.18, radio=(0.05, 0.22))
    h = 0.55 + ond * 0.12 + grano * 0.004 - (1 - grieta) * (0.0 if humedo else 0.06) + pie * 0.35
    h = normalizar(h)
    if humedo:
        col = teñir(srgb((60, 49, 39)), 0.18, ond * 0.6 + grano * 0.2)
        rug = np.clip(0.32 + 0.12 * normalizar(ond) - 0.1 * (h < 0.45), 0.15, 0.6)
    else:
        col = teñir(srgb((104, 82, 62)), 0.16, ond * 0.6 + grano * 0.25)
        col *= (0.86 + 0.14 * grieta)[..., None]
        rug = np.clip(0.82 + 0.1 * grano * 0.3 - 0.25 * (1 - normalizar(ond)) ** 3, 0.5, 0.95)
    gris = teñir(srgb((112, 104, 94)), 0.12, grano)
    col = mezcla(col, gris, sobre.astype(float) * 0.85)
    rug = np.where(sobre, 0.6, rug)
    return col, h, rug, 3.0 if humedo else 2.0


def arena(n, rng):
    """Barra de arena del río: ondulitas de corriente (ripples) torcidas por el ruido, grano fino."""
    u, v = malla_uv(n)
    torcer = espectral(n, 2.6, rng) * 0.035
    ondas = np.sin((v + torcer + 0.02 * np.sin(u * 2 * np.pi * 3)) * 2 * np.pi * 26)
    ondas = np.sign(ondas) * np.abs(ondas) ** 0.7                 # cresta aguda, valle suave
    grano = espectral(n, 0.6, rng, f_min=120)
    manchas = espectral(n, 3.0, rng)
    h = normalizar(ondas * 0.25 + manchas * 0.18 + grano * 0.01)
    col = teñir(srgb((168, 142, 108)), 0.10, manchas * 0.7 + grano * 0.35)
    # minerales oscuros que se juntan en los valles de las ondulitas
    col *= (0.88 + 0.12 * h)[..., None]
    rug = np.clip(0.9 - 0.05 * grano, 0.75, 0.98)
    return col, h, rug, 2.0


def hojarasca(n, rng):
    """Suelo del bosque de Dicroidium: folíolos redondeados, pínulas de helecho y ramitas sobre
    tierra oscura. Ni pasto ni hojas de árboles con flor: no existían."""
    suelo = espectral(n, 2.4, rng)
    col = teñir(srgb((56, 43, 31)), 0.2, suelo)
    h = 0.25 + 0.05 * suelo
    rug = np.full((n, n), 0.85)
    paleta = [srgb(c) for c in ((112, 82, 50), (146, 116, 70), (86, 84, 46), (128, 98, 60), (70, 58, 36), (160, 132, 86))]
    capas = [(46, (1.5, 2.4), 0.95), (38, (1.3, 2.0), 0.9), (30, (2.0, 3.2), 0.8), (24, (1.4, 2.2), 0.7), (60, (6.0, 10.0), 0.4)]
    for k, (celdas, estir, ocup) in enumerate(capas):
        ang = rng.uniform(0, np.pi, (celdas, celdas))
        est = rng.uniform(*estir, (celdas, celdas))
        f1, _, ide = voronoi(n, celdas, rng, aniso=(ang, est))
        radio = (0.48 if k < 4 else 0.45)
        tam = rng.uniform(0.65, 1.0, celdas * celdas)[ide] * radio
        hay = (rng.random(celdas * celdas) < ocup)[ide] & (f1 < tam)
        perfil = np.sqrt(np.clip(1 - (f1 / tam) ** 2, 0, 1))
        # nervadura central: una línea más clara a lo largo de la hoja
        tono = np.stack([paleta[i] for i in rng.integers(0, len(paleta), celdas * celdas)])[ide]
        tono *= (0.85 + 0.3 * rng.random(celdas * celdas)[ide])[..., None]
        altura_hoja = 0.4 + 0.1 * k + perfil * 0.06
        encima = hay & (altura_hoja > h)
        col = np.where(encima[..., None], tono, col)
        h = np.where(encima, altura_hoja, h)
        rug = np.where(encima, 0.62 + 0.2 * rng.random(celdas * celdas)[ide], rug)
    h = normalizar(desenfocar(h, 0.7))
    return col, h, rug, 1.5


def loma(n, rng):
    """Lomas de limolita rojiza: superficie con surcos de escorrentía y costra fina."""
    u, v = malla_uv(n)
    surcos = np.abs(np.sin((u + espectral(n, 2.8, rng) * 0.05) * 2 * np.pi * 7)) ** 0.5
    base = espectral(n, 2.2, rng)
    grano = espectral(n, 1.0, rng, f_min=80)
    pie, _, sobre = piedritas(n, 22, rng, ocupacion=0.25, radio=(0.08, 0.3))
    h = normalizar(base * 0.3 + surcos * 0.25 + grano * 0.012 + pie * 0.6)
    col = teñir(srgb((142, 98, 72)), 0.14, base * 0.6 + grano * 0.3)
    col = mezcla(col, teñir(srgb((120, 104, 90)), 0.1, grano), sobre.astype(float) * 0.8)
    rug = np.clip(0.88 - 0.05 * grano, 0.7, 0.97)
    return col, h, rug, 4.0


def basalto(n, rng):
    """Ladera del volcán: basalto y escoria oscura, porosa."""
    f1, f2, ide = voronoi(n, 14, rng)
    bloques = np.clip((f2 - f1) / 0.12, 0, 1)
    poros = espectral(n, 0.8, rng, f_min=90)
    base = espectral(n, 2.0, rng)
    h = normalizar(bloques * 0.5 + base * 0.2 - np.clip(poros - 1.2, 0, None) * 0.3)
    col = teñir(srgb((52, 49, 47)), 0.18, base * 0.6 + poros * 0.2)
    col *= (0.8 + 0.2 * bloques)[..., None]
    rug = np.clip(0.92 - 0.05 * bloques, 0.8, 0.98)
    return col, h, rug, 6.0


def arcilla(n, rng, clara=False):
    """Valle de la Luna hoy: arcilla gris blanquecina cuarteada en polígonos (como el barro seco
    del shader de la web, pero con bordes curvados y costra)."""
    deform = (espectral(n, 2.6, rng) * 0.012, espectral(n, 2.6, rng) * 0.012)
    f1, f2, ide = voronoi(n, 7 if not clara else 4, rng, deformar=deform)
    borde = np.clip((f2 - f1) / (0.05 if not clara else 0.03), 0, 1)
    placa = espectral(n, 2.0, rng)
    grano = espectral(n, 1.0, rng, f_min=90)
    # las placas se curvan hacia arriba en los bordes (el barro seco se enrula)
    rulo = np.clip(1 - borde, 0, 1) ** 2 * (0.0 if clara else 0.25)
    h = normalizar(borde ** 0.35 * (0.6 if not clara else 0.25) + rulo + placa * 0.08 + grano * 0.005)
    tono = 1 + 0.06 * rng.standard_normal(ide.max() + 1)[ide]
    if clara:
        col = teñir(srgb((198, 188, 168)), 0.06, placa * 0.6 + grano * 0.3)
    else:
        col = teñir(srgb((178, 170, 154)), 0.07, placa * 0.5 + grano * 0.3)
    col = col * tono[..., None]
    col *= (0.45 + 0.55 * borde ** 0.5)[..., None]               # la grieta es oscura y honda
    rug = np.clip(0.9 + 0.04 * grano, 0.8, 0.99)
    return np.clip(col, 0, 1), h, rug, 3.0


def estratos(n, rng):
    """Limolitas y areniscas rojas de la Formación Los Colorados vistas desde arriba: costra rojiza
    con bandas que asoman, surcos y piedritas."""
    u, v = malla_uv(n)
    bandas = np.sin((v + espectral(n, 2.8, rng) * 0.06) * 2 * np.pi * 5) * 0.5 + 0.5
    base = espectral(n, 2.2, rng)
    grano = espectral(n, 1.0, rng, f_min=80)
    pie, _, sobre = piedritas(n, 26, rng, ocupacion=0.22, radio=(0.06, 0.26))
    h = normalizar(base * 0.25 + bandas * 0.2 + grano * 0.012 + pie * 0.5)
    col = mezcla(teñir(srgb((150, 78, 52)), 0.1, base), teñir(srgb((176, 104, 70)), 0.08, grano), bandas)
    col = mezcla(col, teñir(srgb((132, 120, 108)), 0.1, grano), sobre.astype(float) * 0.7)
    rug = np.clip(0.88 - 0.04 * grano, 0.75, 0.97)
    return col, h, rug, 5.0


def ripio(n, rng):
    """Ripio del desierto: guijarros de colores sobre arcilla."""
    col0, h0, rug0, _ = arcilla(n, rng, clara=True)
    pie, ide, sobre = piedritas(n, 30, rng, ocupacion=0.75, radio=(0.12, 0.45))
    pie2, ide2, sobre2 = piedritas(n, 55, rng, ocupacion=0.6, radio=(0.1, 0.38))
    paleta = np.array([srgb(c) for c in ((120, 110, 100), (150, 120, 96), (96, 88, 82), (170, 150, 120), (128, 84, 64))])
    t1 = paleta[rng.integers(0, len(paleta), 30 * 30)][ide]
    t2 = paleta[rng.integers(0, len(paleta), 55 * 55)][ide2]
    col = mezcla(col0, t2, sobre2.astype(float))
    col = mezcla(col, t1, sobre.astype(float))
    h = normalizar(h0 * 0.2 + np.maximum(pie, pie2 * 0.8))
    rug = np.where(sobre | sobre2, 0.7, rug0)
    return col, h, rug, 1.5


CAPAS = {
    "barro": lambda n, r: barro(n, r),
    "barro_humedo": lambda n, r: barro(n, r, humedo=True),
    "arena": arena,
    "hojarasca": hojarasca,
    "loma": loma,
    "basalto": basalto,
    "arcilla_gris": lambda n, r: arcilla(n, r),
    "arcilla_clara": lambda n, r: arcilla(n, r, clara=True),
    "estratos": estratos,
    "ripio": ripio,
}
FUERZA_NORMAL = {"hojarasca": 5.0, "arena": 3.0, "arcilla_gris": 6.0, "arcilla_clara": 3.0, "ripio": 7.0, "basalto": 6.0}


def guardar_jpg(ruta, rgb, calidad=92):
    """JPG con el bpy de pip (no hay PIL en la nube). rgb en [0,1], filas de arriba a abajo."""
    import bpy
    n = rgb.shape[0]
    img = bpy.data.images.new(os.path.basename(ruta), n, n, alpha=False)
    rgba = np.concatenate([rgb[::-1], np.ones(rgb.shape[:2] + (1,))], axis=-1)   # Blender: fila 0 abajo
    # imagen de 8 bits: los números se guardan tal cual, sin gestión de color (probado: 0,5 → 128)
    img.pixels.foreach_set(rgba.astype(np.float32).ravel())
    img.file_format = "JPEG"
    img.save(filepath=ruta, quality=calidad)
    bpy.data.images.remove(img)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", type=int, default=1024)
    ap.add_argument("--solo", nargs="*")
    a = ap.parse_args()
    os.makedirs(SALIDA, exist_ok=True)
    indice = {}
    for k, (nombre, fn) in enumerate(CAPAS.items()):
        if a.solo and nombre not in a.solo:
            continue
        rng = np.random.default_rng(231 + k)
        col, h, rug, mundo_m = fn(a.res, rng)
        ao = oclusion(h, a.res / 256, 2.2)
        col = np.clip(col * (0.75 + 0.25 * ao)[..., None], 0, 1)   # la cavidad también oscurece el albedo, apenas
        nrm = normal_desde_altura(h, FUERZA_NORMAL.get(nombre, 4.0) * a.res / 256)
        hra = np.stack([h, ao, rug], axis=-1)
        guardar_jpg(os.path.join(SALIDA, f"{nombre}_color.jpg"), col)
        guardar_jpg(os.path.join(SALIDA, f"{nombre}_normal.jpg"), nrm, 95)
        guardar_jpg(os.path.join(SALIDA, f"{nombre}_hra.jpg"), hra, 95)
        indice[nombre] = {"mundo_m": mundo_m, "fuente": "procedural (texturas_suelo.py)"}
        print(f"  {nombre}: {mundo_m} m por vuelta", flush=True)
    previo = os.path.join(SALIDA, "capas.json")
    if os.path.exists(previo):
        viejo = {c["nombre"]: c for c in json.load(open(previo, encoding="utf-8")).get("capas", [])}
        viejo.update({k: dict(nombre=k, **v) for k, v in indice.items()})
        lista = list(viejo.values())
    else:
        lista = [dict(nombre=k, **v) for k, v in indice.items()]
    # lista de objetos (no diccionario): así la lee JsonUtility de Unity
    with open(previo, "w", encoding="utf-8") as f:
        json.dump({"capas": lista}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
