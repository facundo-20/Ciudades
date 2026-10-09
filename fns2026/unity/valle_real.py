"""
El Valle de la Luna REAL para el capítulo "hoy" de Unity: el relieve satelital de Copernicus,
el color de Sentinel-2 y una simulación de erosión que le da a las bad lands el detalle que el
satélite no ve (cárcavas, surcos y conos de derrubio de metro y medio metro).

    python3 valle_real.py             (numpy + numba + rasterio; baja los datos la primera vez)

Datos abiertos (se pueden usar y modificar con atribución, no son fotos de bancos de imágenes):
  · Relieve: Copernicus DEM GLO-30 (ESA / Airbus), 30 m.
    "Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space
     GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA."
  · Color: Sentinel-2 L2A del 26/09/2026, 0 % de nubes. "Contains modified Copernicus Sentinel data 2026."

Lo que sale (ParqueTriasico/Datos/valle/ y valle_real.json para exportar_mundo.py):
  hoy_cerca.r16d.gz      2048 m × 2048 m a 1 m: la cámara, la arcilla blanca y el pie del paredón
  hoy_lejos.r16d.gz      8192 m × 8192 m a 4 m: la franja blanca entera, las Barrancas Coloradas
                         y la meseta roja
  hoy_*_capas0.png       capas de suelo sacadas del color real del satélite (2 m cerca, 16 m lejos)
  paredon.json.gz        malla del paredón (las caras de más de 38°): en un heightmap la textura se
                         estira en las paredes; la malla lleva mapeo triplanar con estratos horizontales
  satelite_hoy.jpg       la vista de arriba, para revisar

Marco de coordenadas de Unity para "hoy": x = este, z = norte, y = altura sobre 1250 m s. n. m.,
con el origen en el centro del terreno lejano (UTM 19S E 603800, N 6674752).
"""

import gzip
import json
import math
import os
import sys
import time

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
DATOS = os.path.join(AQUI, "ParqueTriasico", "Datos")
CACHE = os.path.join(AQUI, "cache_geo")            # fuera de git
os.environ.setdefault("CURL_CA_BUNDLE", "/root/.ccr/ca-bundle.crt") if os.path.exists("/root/.ccr/ca-bundle.crt") else None
os.environ.setdefault("GDAL_HTTP_TIMEOUT", "60")

CRS = "EPSG:32719"                                    # UTM 19 sur
E0, N0 = 603800.0, 6674752.0                         # centro del terreno lejano
BASE = 1250.0                                        # m s. n. m. que quedan en y = 0
LEJOS = dict(lado=8192.0, res=2049)                  # 4 m
CERCA = dict(lado=2048.0, res=2049, centro=(-56.0, -56.0))   # 1 m, entre la cámara y el paredón
SENTINEL = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/19/J/{t}/2026/9/S2C_19J{t}_20260926_0_L2A/TCI.tif"
DEM = "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_{t}_DEM/Copernicus_DSM_COG_10_{t}_DEM.tif"
CAPAS = ["arcilla_gris", "arcilla_clara", "estratos", "ripio"]

sys.path.insert(0, AQUI)
from exportar_mundo import codificar_predictor, png_rgba  # noqa: E402


def bajar(url, destino):
    if os.path.exists(destino):
        return destino
    import urllib.request
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    print("   bajando", url.split("/")[-1], flush=True)
    req = urllib.request.Request(url, headers={"User-Agent": "fns2026-valle/1.0"})
    with urllib.request.urlopen(req, timeout=600) as r, open(destino + ".parcial", "wb") as f:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            f.write(b)
    os.replace(destino + ".parcial", destino)
    return destino


def grilla_10m():
    """Mosaico Sentinel-2 y DEM en la misma grilla UTM de 10 m que cubre el terreno lejano."""
    import rasterio
    from rasterio.merge import merge
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, reproject
    media = LEJOS["lado"] / 2 + 200
    left, right = E0 - media, E0 + media
    bottom, top = N0 - media, N0 + media
    cache_sat = os.path.join(CACHE, "satelite10.npy")
    cache_dem = os.path.join(CACHE, "dem10.npy")
    tr = from_origin(left, top, 10, 10)
    if os.path.exists(cache_sat) and os.path.exists(cache_dem):
        return np.load(cache_sat), np.load(cache_dem), tr
    fuentes = [rasterio.open("/vsicurl/" + SENTINEL.format(t=t)) for t in ("EG", "FG")]
    sat, tr2 = merge(fuentes, bounds=(left, bottom, right, top), res=10, nodata=0)
    dem = np.full(sat.shape[1:], np.nan, np.float32)
    for t in ("S31_00_W068_00", "S30_00_W068_00"):
        ruta = bajar(DEM.format(t=t), os.path.join(CACHE, f"dem_{t}.tif"))
        with rasterio.open(ruta) as d:
            tmp = np.full(dem.shape, np.nan, np.float32)
            reproject(d.read(1), tmp, src_transform=d.transform, src_crs=d.crs, dst_transform=tr2, dst_crs=CRS,
                      resampling=Resampling.cubic, dst_nodata=np.nan)
            dem = np.where(np.isnan(tmp), dem, tmp)
    os.makedirs(CACHE, exist_ok=True)
    np.save(cache_sat, sat)
    np.save(cache_dem, dem)
    return sat, dem, tr2


def muestrear(img, tr, xs, zs, orden=3):
    """Valores de la grilla de 10 m en puntos del marco de Unity (x este, z norte, en metros desde
    E0, N0). Interpolación cúbica (orden 3) para el relieve, lineal para colores."""
    from scipy_free import mapa_coordenadas
    col = (E0 + xs - tr.c) / tr.a - 0.5
    fil = (N0 + zs - tr.f) / tr.e - 0.5
    return mapa_coordenadas(img, fil, col, orden)


# ------------------------------------------------------------------------------------------
# ruido y erosión
# ------------------------------------------------------------------------------------------

def fbm_espectral(n, cel_m, longitudes_m, rng):
    """Ruido con energía sólo entre las longitudes de onda pedidas (en metros), desvío 1."""
    f = np.fft.fftfreq(n, d=cel_m)
    fx, fy = np.meshgrid(f, f)
    k = np.sqrt(fx * fx + fy * fy) + 1e-9
    lmin, lmax = longitudes_m
    filtro = np.where((k >= 1 / lmax) & (k <= 1 / lmin), k ** -1.0, 0.0)
    campo = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * filtro))
    return (campo - campo.mean()) / (campo.std() + 1e-9)


def erosionar(h, cel_m, gotas, semilla, fuerza=1.0):
    """Erosión hidráulica por gotas (el método de Hans Theobald Beyer, el de los juegos): cada
    gota baja por la pendiente, arranca sedimento donde acelera y lo deja donde frena. Así salen
    cárcavas que se ramifican y conos de derrubio al pie, como en las bad lands de verdad."""
    from numba import njit

    @njit(cache=False)
    def _correr(H, n_gotas, semilla, cel, fuerza):
        np.random.seed(semilla)
        n = H.shape[0]
        inercia, capacidad, cap_min, erosion, deposito, evapora, gravedad = 0.05, 4.0, 0.01, 0.3 * fuerza, 0.3, 0.02, 4.0
        radio = 2
        for _ in range(n_gotas):
            x = np.random.random() * (n - 3) + 1
            y = np.random.random() * (n - 3) + 1
            dx = 0.0
            dy = 0.0
            vel = 1.0
            agua = 1.0
            sed = 0.0
            for _p in range(80):
                i = int(x)
                j = int(y)
                if i < 1 or j < 1 or i >= n - 2 or j >= n - 2:
                    break
                u = x - i
                v = y - j
                h00 = H[j, i]; h10 = H[j, i + 1]; h01 = H[j + 1, i]; h11 = H[j + 1, i + 1]
                gx = ((h10 - h00) * (1 - v) + (h11 - h01) * v) / cel
                gy = ((h01 - h00) * (1 - u) + (h11 - h10) * u) / cel
                altura = h00 * (1 - u) * (1 - v) + h10 * u * (1 - v) + h01 * (1 - u) * v + h11 * u * v
                dx = dx * inercia - gx * (1 - inercia)
                dy = dy * inercia - gy * (1 - inercia)
                largo = math.sqrt(dx * dx + dy * dy)
                if largo < 1e-9:
                    break
                dx /= largo
                dy /= largo
                nx = x + dx
                ny = y + dy
                ni = int(nx)
                nj = int(ny)
                if ni < 1 or nj < 1 or ni >= n - 2 or nj >= n - 2:
                    break
                nu = nx - ni
                nv = ny - nj
                nueva = (H[nj, ni] * (1 - nu) * (1 - nv) + H[nj, ni + 1] * nu * (1 - nv)
                         + H[nj + 1, ni] * (1 - nu) * nv + H[nj + 1, ni + 1] * nu * nv)
                dh = nueva - altura
                cap = max(-dh / cel * vel * agua * capacidad, cap_min)
                if sed > cap or dh > 0:
                    deja = min(dh, sed) if dh > 0 else (sed - cap) * deposito
                    sed -= deja
                    H[j, i] += deja * (1 - u) * (1 - v)
                    H[j, i + 1] += deja * u * (1 - v)
                    H[j + 1, i] += deja * (1 - u) * v
                    H[j + 1, i + 1] += deja * u * v
                else:
                    saca = min((cap - sed) * erosion, -dh)
                    peso_total = 0.0
                    for bj in range(-radio, radio + 1):
                        for bi in range(-radio, radio + 1):
                            d = math.sqrt(bi * bi + bj * bj)
                            if d <= radio:
                                peso_total += radio - d
                    for bj in range(-radio, radio + 1):
                        for bi in range(-radio, radio + 1):
                            d = math.sqrt(bi * bi + bj * bj)
                            if d <= radio:
                                jj = j + bj
                                ii = i + bi
                                if 0 <= jj < n and 0 <= ii < n:
                                    H[jj, ii] -= saca * (radio - d) / peso_total
                    sed += saca
                vel = math.sqrt(max(0.0, vel * vel + dh / cel * gravedad))
                agua *= 1 - evapora
                x = nx
                y = ny
        return H

    t0 = time.time()
    H = _correr(h.astype(np.float64).copy(), int(gotas), int(semilla), float(cel_m), float(fuerza))
    print(f"   erosión: {gotas:,} gotas en {time.time() - t0:.0f} s", flush=True)
    return H.astype(np.float32)


# ------------------------------------------------------------------------------------------
# capas de suelo desde el color del satélite
# ------------------------------------------------------------------------------------------

def a_lineal(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def paleta_real(sat):
    """Colores reales de cada capa, medidos en la imagen: los píxeles más blancos (arcilla clara),
    los grises (arcilla gris), los más rojos (Los Colorados) y los pardos oscuros (ripio).
    TCI de Sentinel-2: 255 = 30 % de reflectancia, lineal → albedo = TCI/255 × 0,3."""
    px = sat.reshape(3, -1).T.astype(np.float32) / 255.0
    px = px[px.sum(1) > 0.05]
    brillo = px.mean(1)
    rojez = px[:, 0] - 0.5 * (px[:, 1] + px[:, 2])
    sel = {
        "arcilla_clara": px[brillo > np.percentile(brillo, 93)],
        "arcilla_gris": px[(brillo > np.percentile(brillo, 60)) & (brillo < np.percentile(brillo, 85)) & (rojez < np.percentile(rojez, 40))],
        "estratos": px[rojez > np.percentile(rojez, 92)],
        "ripio": px[(brillo < np.percentile(brillo, 25)) & (rojez < np.percentile(rojez, 60))],
    }
    return {k: v.mean(0) for k, v in sel.items()}


def pesos_desde_satelite(color, pendiente, paleta):
    """Peso de cada capa = parecido al color medido (en el satélite) + reglas de pendiente:
    las paredes empinadas son estratos expuestos, lo plano y claro es arcilla."""
    # el color del satélite se suaviza (~3 píxeles de 10 m): un píxel mezcla roca roja y derrubio gris,
    # y clasificado tal cual daba manchas de camuflaje en el paredón
    from texturas_suelo import desenfocar
    n0 = color.shape[0]
    color = np.stack([desenfocar(np.pad(color[..., c], ((0, n0 % 2),) * 2, mode="edge"), 3.0)[:n0, :n0] for c in range(3)], -1)
    centros = np.stack([paleta[c] for c in CAPAS])            # (4, 3)
    d2 = ((color[..., None, :] - centros[None, None]) ** 2).sum(-1) / 0.012
    w = np.exp(-d2)
    # las paredes empinadas son estratos expuestos (Los Colorados); lo plano y claro, arcilla
    w[..., CAPAS.index("estratos")] *= 1 + 5.0 * np.clip((pendiente - 0.35) / 0.5, 0, 1)
    w[..., CAPAS.index("arcilla_gris")] *= 1 + 0.6 * np.clip(1 - pendiente / 0.3, 0, 1)
    return w / (w.sum(-1, keepdims=True) + 1e-9)


# ------------------------------------------------------------------------------------------
# terrenos
# ------------------------------------------------------------------------------------------

def coords(g):
    n = g["res"]
    cx, cz = g.get("centro", (0.0, 0.0))
    x0, z0 = cx - g["lado"] / 2, cz - g["lado"] / 2
    paso = g["lado"] / (n - 1)
    xs = x0 + np.arange(n) * paso
    zs = z0 + np.arange(n) * paso
    return x0, z0, paso, xs, zs


def guardar_terreno(nombre, h, x0, z0, g, capas_w, hmin_extra=0.0):
    hmin, hmax = float(h.min()) - hmin_extra, float(h.max())
    a = np.round((h - hmin) / (hmax - hmin) * 65535).astype(np.int64)
    os.makedirs(os.path.join(DATOS, "valle"), exist_ok=True)
    with gzip.open(os.path.join(DATOS, "valle", f"{nombre}.r16d.gz"), "wb", compresslevel=9) as z:
        z.write(codificar_predictor(a).tobytes())
    res_c = capas_w.shape[0]
    filas = []
    for fila in capas_w[::-1]:             # PNG de arriba abajo; Unity lo da vuelta al cargar
        filas.append(np.clip(np.round(fila * 255), 0, 255).astype(np.uint8).ravel().tobytes())
    png_rgba(os.path.join(DATOS, "valle", f"{nombre}_capas0.png"), res_c, res_c, filas)
    return {"nombre": nombre, "era": "hoy", "cual": nombre.split("_")[1], "x0": round(x0, 3), "z0": round(z0, 3),
            "lado": g["lado"], "res": g["res"], "hmin": round(hmin, 4), "hmax": round(hmax, 4),
            "alturas": f"valle/{nombre}.r16d.gz", "capas": CAPAS, "capas_png": [f"valle/{nombre}_capas0.png"],
            "capas_res": res_c}


def malla_paredon(h, x0, z0, paso, umbral_grados=50.0, margen=2, cada=2):
    """Las paredes del terreno fino como malla aparte (cada 2 m), levantada 4 cm por la normal.
    Lleva material triplanar en Unity: los estratos quedan horizontales en la pared.
    La pendiente se mide sobre el relieve suavizado a 8 m: así entran el paredón y las paredes de
    las cárcavas grandes, no cada surquito de la erosión (eso lo resuelve la textura)."""
    h = h[::cada, ::cada]
    paso = paso * cada
    from texturas_suelo import desenfocar
    n0 = h.shape[0]
    pad = np.pad(h, ((0, 1 if n0 % 2 else 0),) * 2, mode="edge")
    liso = desenfocar(pad, 8.0 / paso)[:n0, :n0]
    gz, gx = np.gradient(liso, paso)
    pend = np.degrees(np.arctan(np.hypot(gx, gz)))
    gz, gx = np.gradient(h, paso)
    mask = pend > umbral_grados
    # agrandar la máscara unas celdas para que la malla tape el borde del terreno
    for _ in range(margen):
        m2 = mask.copy()
        m2[1:] |= mask[:-1]; m2[:-1] |= mask[1:]; m2[:, 1:] |= mask[:, :-1]; m2[:, :-1] |= mask[:, 1:]
        mask = m2
    n = h.shape[0]
    idx = -np.ones((n, n), np.int64)
    usados = np.zeros((n, n), bool)
    usados[:-1, :-1] |= mask[:-1, :-1]
    usados[1:, :-1] |= mask[:-1, :-1]
    usados[:-1, 1:] |= mask[:-1, :-1]
    usados[1:, 1:] |= mask[:-1, :-1]
    jj, ii = np.nonzero(usados)
    idx[jj, ii] = np.arange(len(jj))
    nrm = np.stack([-gx, np.ones_like(h), -gz], -1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    vx = x0 + ii * paso + nrm[jj, ii, 0] * 0.04
    vy = h[jj, ii] + nrm[jj, ii, 1] * 0.04
    vz = z0 + jj * paso + nrm[jj, ii, 2] * 0.04
    cj, ci = np.nonzero(mask[:-1, :-1])
    a = idx[cj, ci]; b = idx[cj, ci + 1]; c = idx[cj + 1, ci]; d = idx[cj + 1, ci + 1]
    # Unity: cara de frente = sentido horario visto desde arriba (y+), con x este y z norte
    tris = np.stack([a, c, d, a, d, b], 1).ravel()
    verts = np.stack([vx, vy, vz], 1).round(3).ravel()
    with gzip.open(os.path.join(DATOS, "valle", "paredon.json.gz"), "wt", encoding="utf-8") as f:
        json.dump({"vertices": verts.tolist(), "triangulos": tris.tolist()}, f, separators=(",", ":"))
    return len(jj), len(tris) // 3


def sembrar_piedras(h, x0, z0, paso, pend, cada_100m2=1.2):
    """Piedras de arenisca en lo plano (en lo empinado ruedan): mismo formato que flora_<era>.json."""
    azar = np.random.default_rng(232)
    centro = np.array([-380.0, -360.0])               # a mitad del recorrido de la cámara
    radio = 420.0
    n = int(math.pi * radio * radio / 100 * cada_100m2)
    ang = azar.uniform(0, 2 * math.pi, n)
    r = radio * np.sqrt(azar.uniform(0, 1, n))
    xs, zs = centro[0] + r * np.cos(ang), centro[1] + r * np.sin(ang)
    i = np.clip(((xs - x0) / paso).astype(int), 0, h.shape[1] - 1)
    j = np.clip(((zs - z0) / paso).astype(int), 0, h.shape[0] - 1)
    ok = pend[j, i] < 0.45
    datos = []
    for x, z, ii, jj in zip(xs[ok], zs[ok], i[ok], j[ok]):
        datos += [round(float(x), 2), round(float(h[jj, ii]) - 0.05, 3), round(float(z), 2),
                  round(float(azar.uniform(0, 360)), 1), round(float(azar.uniform(0.15, 0.6)), 3), round(float(azar.uniform(-0.1, 0.1)), 3)]
    with open(os.path.join(DATOS, "flora_hoy.json"), "w", encoding="utf-8") as f:
        json.dump({"especies": [{"nombre": "roca_arenisca", "datos": datos}]}, f, separators=(",", ":"))
    print(f"   piedras de hoy: {len(datos) // 6}", flush=True)


def main():
    t0 = time.time()
    sat, dem, tr = grilla_10m()
    print(f"== satélite {sat.shape} · relieve {np.nanmin(dem):.0f}–{np.nanmax(dem):.0f} m", flush=True)
    color10 = np.transpose(sat, (1, 2, 0)).astype(np.float32) / 255.0 * 0.3      # albedo lineal
    paleta = paleta_real(sat)
    print("   paleta real (albedo lineal):", {k: [round(float(c), 3) for c in v * 0.3] for k, v in paleta.items()}, flush=True)
    paleta = {k: v * 0.3 for k, v in paleta.items()}
    rng = np.random.default_rng(231)
    salida = {"terrenos": []}

    # --- lejos: 8 km a 4 m
    x0, z0, paso, xs, zs = coords(LEJOS)
    X, Z = np.meshgrid(xs, zs)
    n = LEJOS["res"]
    h = muestrear(dem, tr, X, Z, 3) - BASE
    # el DEM de 30 m es liso por debajo de los 30 m: ruido de 12–120 m y erosión a 4 m le dan las
    # cárcavas grandes que el satélite promedia
    h = h + fbm_espectral(n, paso, (12, 120), rng) * 1.6
    h = erosionar(h, paso, 1_400_000, 231, fuerza=0.8)
    col = np.stack([muestrear(color10[..., k], tr, X, Z, 1) for k in range(3)], -1)
    gz, gx = np.gradient(h, paso)
    pend = np.hypot(gx, gz)
    w = pesos_desde_satelite(col[:2048:4, :2048:4], pend[:2048:4, :2048:4], paleta)     # 16 m
    salida["terrenos"].append(guardar_terreno("hoy_lejos", h, x0, z0, LEJOS, w, hmin_extra=8.0))
    h_lejos, xs_l, zs_l = h, xs, zs
    print(f"   hoy_lejos listo · {time.time() - t0:.0f} s", flush=True)

    # --- cerca: 2 km a 1 m. La forma grande sale del lejano (así la costura calza); encima,
    # detalle de 0,5–14 m y una erosión fina con el doble de gotas: surcos y conos de derrubio
    from scipy_free import mapa_coordenadas
    x0, z0, paso, xs, zs = coords(CERCA)
    X, Z = np.meshgrid(xs, zs)
    n = CERCA["res"]
    base = mapa_coordenadas(h_lejos, (Z - zs_l[0]) / (zs_l[1] - zs_l[0]), (X - xs_l[0]) / (xs_l[1] - xs_l[0]), 3)
    detalle = fbm_espectral(n, paso, (2, 14), rng) * 0.35 + fbm_espectral(n, paso, (0.5, 2.5), rng) * 0.06
    h_ero = erosionar(base + detalle, paso, 2_600_000, 232, fuerza=1.0)
    # en los últimos 60 m hacia el borde se vuelve a la forma del lejano (sin escalón en la costura)
    borde = np.minimum.reduce([X - xs[0], xs[-1] - X, Z - zs[0], zs[-1] - Z])
    k = np.clip(borde / 60.0, 0, 1)
    h = base * (1 - k) + h_ero * k
    # pollera de 3 m en el borde, como en el Triásico
    h[:2, :] -= 3; h[-2:, :] -= 3; h[:, :2] -= 3; h[:, -2:] -= 3
    col = np.stack([muestrear(color10[..., c], tr, X, Z, 1) for c in range(3)], -1)
    gz, gx = np.gradient(h, paso)
    pend = np.hypot(gx, gz)
    w = pesos_desde_satelite(col[:2048:2, :2048:2], pend[:2048:2, :2048:2], paleta)     # 2 m: el color real viene de 10 m
    salida["terrenos"].append(guardar_terreno("hoy_cerca", h, x0, z0, CERCA, w))
    nv, nt = malla_paredon(h, x0, z0, paso)
    print(f"   hoy_cerca listo · paredón: {nv:,} vértices, {nt:,} triángulos · {time.time() - t0:.0f} s", flush=True)

    # --- piedras sueltas y concreciones sobre la arcilla, a la vista del recorrido (400 m alrededor)
    sembrar_piedras(h, x0, z0, paso, pend)

    # --- cámara del capítulo "hoy": parado en la arcilla blanca, mirando el paredón con sol de tarde
    def suelo(x, z):
        return float(mapa_coordenadas(h, np.array([(z - zs[0]) / paso]), np.array([(x - xs[0]) / paso]), 1)[0])
    desde = (-460.0, -440.0)
    hasta = (-300.0, -280.0)
    mira = (300.0, 380.0)
    ojo = suelo(*desde) + 1.7
    salida["camara_hoy"] = {
        "desde": [desde[0], round(ojo, 2), desde[1]],
        "hasta": [hasta[0], round(suelo(*hasta) + 22.0, 2), hasta[1]],
        # a 1 km, 90 m arriba del ojo: el paredón de 280 m entra entero con cielo arriba
        "mira": [mira[0], round(ojo + 90.0, 2), mira[1]],
    }
    # sol de una tarde de febrero (la Fiesta del Sol): 25° de alto, desde el oeste-sudoeste
    elev, az = 25.0, 255.0
    e, a = math.radians(elev), math.radians(az)
    salida["sol_hoy"] = {"elevacion": elev, "azimut_brujula": az,
                         "hacia_sol": [round(math.sin(a) * math.cos(e), 5), round(math.sin(e), 5), round(math.cos(a) * math.cos(e), 5)]}
    salida["paleta_albedo_lineal"] = {k: [round(float(c), 4) for c in v] for k, v in paleta.items()}
    salida["origen_utm"] = {"crs": CRS, "este": E0, "norte": N0, "base_msnm": BASE}
    salida["referencias"] = {"centro_visitantes": [-67.8422, -30.1633], "valle_pintado_aprox": [-67.8775, -30.1372]}
    salida["atribucion"] = ["Copernicus DEM GLO-30 © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, "
                            "provisto bajo COPERNICUS por la Unión Europea y la ESA",
                            "Contiene datos modificados de Copernicus Sentinel 2026 (Sentinel-2 L2A, 26/09/2026)"]
    with open(os.path.join(DATOS, "valle_real.json"), "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)
    vista_satelite(color10, tr)
    print(f"listo en {time.time() - t0:.0f} s", flush=True)


def vista_satelite(color10, tr):
    """JPG de la zona del terreno lejano (para el informe y para revisar la ubicación)."""
    try:
        import bpy
    except ImportError:
        return
    x0, z0, paso, xs, zs = coords(dict(LEJOS, res=1024))
    X, Z = np.meshgrid(xs, zs)
    col = np.stack([muestrear(color10[..., c], tr, X, Z, 1) for c in range(3)], -1) / 0.3
    col = np.clip(col, 0, 1)
    img = bpy.data.images.new("sat", 1024, 1024, alpha=False)
    img.pixels.foreach_set(np.concatenate([col, np.ones((1024, 1024, 1))], -1).astype(np.float32).ravel())
    img.file_format = "JPEG"
    img.save(filepath=os.path.join(DATOS, "valle", "satelite_hoy.jpg"), quality=88)


if __name__ == "__main__":
    main()
