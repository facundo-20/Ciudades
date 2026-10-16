"""
El sonido de la sala, sintetizado: nada grabado ni bajado (es nuestro, sin licencias de terceros).

    python3 sonido_triasico.py [--salida DIR] [--segundos 48]

Sale en unity/ParqueTriasico/Datos/sonido/ (OGG Vorbis, 48 kHz):
  ambiente_<capitulo>.ogg     loop estéreo por capítulo, sin costura: el ruido se sintetiza en el
                              dominio de la frecuencia (es periódico) y todas las modulaciones dan
                              vueltas enteras en el loop
  volcan.ogg                  retumbe del volcán (mono, va como fuente 3D en el cono)
  voz_<especie>_<n>.ogg       vocalizaciones (mono, 3D, en cada animal)
  pisada_<peso>_<suelo>_<n>.ogg   pisadas (liviano/medio/pesado × barro/seco)
  informe_sonido.json

Criterio científico (a validar con la UNSJ/MuPa, como el resto):
  · En el Triásico no hay aves ni ranas que canten: el fondo vivo son insectos que estridulan
    (ortópteros como Archaboilus, cuyo canto se reconstruyó: tonos puros de ~6 kHz en pulsos).
  · Los dinosaurios y los pseudosuquios (Saurosuchus) vocalizan "a boca cerrada": retumbes graves
    como los de cocodrilos y aves grandes (Riede et al. 2016). Más grande, más grave.
  · Los cinodontes (Exaeretodon) y dicinodontes (Ischigualastia) son de la línea de los mamíferos:
    gruñidos y resoplidos nasales.
"""
import argparse
import json
import math
import os

import numpy as np
import soundfile as sf
from scipy import signal

SR = 48000
AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.abspath(os.path.join(AQUI, "..", ".."))
SALIDA = os.path.join(FNS, "unity", "ParqueTriasico", "Datos", "sonido")


# ---------------------------------------------------------------------------------------------
# piezas
# ---------------------------------------------------------------------------------------------

def ruido_periodico(n, rng, pendiente=-1.0, banda=(20, 20000)):
    """Ruido de n muestras que da la vuelta sin costura (espectro con fase al azar → irfft).
    pendiente: 0 blanco, -1 rosa, -2 marrón (en potencia)."""
    f = np.fft.rfftfreq(n, 1 / SR)
    mag = np.zeros_like(f)
    ok = (f >= banda[0]) & (f <= banda[1])
    mag[ok] = f[ok] ** (pendiente / 2)
    # bordes de banda suaves (sin "ring")
    for borde, sube in ((banda[0], True), (banda[1], False)):
        d = np.abs(np.log2(np.maximum(f, 1) / borde))
        suave = (d < 0.5) & (~ok if sube else ok)
        mag[suave] *= 0.5 * (1 + np.cos(np.pi * d[suave] / 0.5)) if not sube else 1
    fase = rng.uniform(0, 2 * np.pi, len(f))
    x = np.fft.irfft(mag * np.exp(1j * fase), n)
    return x / (np.abs(x).max() + 1e-12)


def lfo(n, vueltas, rng, armonicos=3):
    """Modulación lenta periódica (vueltas enteras en el loop), entre 0 y 1."""
    t = np.arange(n) / n
    y = np.zeros(n)
    for k in range(1, armonicos + 1):
        y += rng.uniform(0.3, 1.0) / k * np.sin(2 * np.pi * vueltas * k * t + rng.uniform(0, 2 * np.pi))
    y -= y.min()
    return y / (y.max() + 1e-12)


def _filtro_circular(x, sos):
    """Filtra en el dominio de la frecuencia con la magnitud del Butterworth: el resultado es
    exactamente periódico (el loop no tiene costura) y sin corrimiento de fase."""
    n = len(x)
    _, h = signal.sosfreqz(sos, worN=np.fft.rfftfreq(n, 1 / SR), fs=SR)
    return np.fft.irfft(np.fft.rfft(x) * np.abs(h), n)


def pasabanda(x, f1, f2, orden=2, circular=True):
    sos = signal.butter(orden, [f1, f2], btype="band", fs=SR, output="sos")
    return _filtro_circular(x, sos) if circular else signal.sosfilt(sos, x)


def pasabajos(x, f, orden=2, circular=True):
    sos = signal.butter(orden, f, btype="low", fs=SR, output="sos")
    return _filtro_circular(x, sos) if circular else signal.sosfilt(sos, x)


def poner(dest, sonido, inicio, ganancia=1.0, circular=True):
    """Suma un sonido corto en una posición (dando la vuelta si se pasa del final del loop)."""
    n = len(dest)
    idx = (inicio + np.arange(len(sonido))) % n if circular else inicio + np.arange(min(len(sonido), n - inicio))
    np.add.at(dest, idx, sonido[:len(idx)] * ganancia)


def envolvente(n, ataque, caida, forma=2.0):
    t = np.arange(n) / SR
    a = np.clip(t / max(ataque, 1e-4), 0, 1)
    return a * np.exp(-np.maximum(t - ataque, 0) / max(caida, 1e-4)) ** (1 / forma)


def normalizar(x, pico_db=-3.0):
    return x / (np.abs(x).max() + 1e-12) * 10 ** (pico_db / 20)


def nivel_rms_db(x):
    return 20 * math.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)


# ---------------------------------------------------------------------------------------------
# capas del ambiente
# ---------------------------------------------------------------------------------------------

def viento(n, rng, fuerza=1.0, frondas=0.0, vueltas=3):
    """Viento: cuerpo grave con ráfagas; con frondas, el susurro agudo de las hojas en cada ráfaga."""
    rafaga = 0.35 + 0.65 * lfo(n, vueltas, rng)
    cuerpo = pasabanda(ruido_periodico(n, rng, -1.4, (40, 3000)), 70, 900) * (0.4 + 0.6 * rafaga)
    silbido = pasabanda(ruido_periodico(n, rng, -0.6, (300, 4000)), 500 + 300 * rng.random(), 1400) * rafaga ** 2 * 0.25
    x = cuerpo + silbido
    if frondas:
        # el aleteo de las hojas: ruido agudo modulado rápido, más fuerte en la ráfaga
        aleteo = 0.5 + 0.5 * lfo(n, vueltas * 37, rng, 5)
        hojas = pasabanda(ruido_periodico(n, rng, -0.3, (1500, 12000)), 2200, 9000) * aleteo * rafaga ** 1.5
        x += frondas * 0.8 * hojas
    return normalizar(x) * fuerza


def rio(n, rng, fuerza=1.0):
    """Correntada: ruido ancho con remolinos lentos, más burbujas (Minnaert: tono que sube al cerrarse)."""
    base = pasabanda(ruido_periodico(n, rng, -0.8, (80, 9000)), 150, 5000) * (0.7 + 0.3 * lfo(n, 5, rng))
    burbujas = np.zeros(n)
    for _ in range(int(n / SR * 22)):
        dur = rng.uniform(0.012, 0.05)
        t = np.arange(int(dur * SR)) / SR
        f0 = rng.uniform(450, 1600)
        f = f0 * (1 + 2.5 * t / dur)                                   # sube
        b = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (dur / 3))
        poner(burbujas, b, rng.integers(0, n), rng.uniform(0.1, 0.5))
    return normalizar(normalizar(base) + 0.35 * normalizar(burbujas)) * fuerza


def insectos(n, rng, cuantos=5, fuerza=1.0):
    """Ortópteros estridulando: tonos puros de 4,5-8 kHz en pulsos de ~15 ms agrupados en trenes."""
    x = np.zeros((n, 2))
    for _ in range(cuantos):
        f = rng.uniform(4500, 8000)
        pan = rng.uniform(-0.8, 0.8)
        lejos = rng.uniform(0.2, 1.0)
        t_pulso = int(rng.uniform(0.010, 0.020) * SR)
        pulso = np.sin(2 * np.pi * f * np.arange(t_pulso) / SR) * np.hanning(t_pulso)
        pos = rng.integers(0, n)
        while pos < n * 3:          # vuelve a empezar: el loop queda poblado de punta a punta
            tren = rng.integers(3, 12)
            for k in range(tren):
                for c, g in ((0, (1 - pan) / 2), (1, (1 + pan) / 2)):
                    idx = (pos + np.arange(t_pulso)) % n
                    np.add.at(x[:, c], idx, pulso * g * lejos)
                pos += int(t_pulso * rng.uniform(1.6, 2.4))
            pos += int(rng.uniform(0.4, 3.5) * SR)
            if pos > n and rng.random() < 0.6:
                break
    # lo lejano se oye más opaco
    x = np.stack([pasabajos(x[:, c], 9000) for c in range(2)], 1)
    return x / (np.abs(x).max() + 1e-12) * fuerza


def retumbe(n, rng, fuerza=1.0, explosiones=4, chisporroteo=0.0):
    """El volcán: retumbe infrasónico continuo + estallidos graves y, en erupción, piroclastos."""
    fondo = pasabajos(ruido_periodico(n, rng, -2.0, (15, 400)), 110, 4) * (0.6 + 0.4 * lfo(n, 2, rng))
    x = normalizar(fondo)
    for _ in range(explosiones):
        dur = rng.uniform(1.5, 4.0)
        t = np.arange(int(dur * SR)) / SR
        f = rng.uniform(22, 38)
        golpe = (np.sin(2 * np.pi * f * t) + 0.5 * pasabajos(rng.standard_normal(len(t)), 180, 2, False)) * envolvente(len(t), 0.05, dur / 3)
        poner(x, golpe, rng.integers(0, n), rng.uniform(0.5, 1.0))
    if chisporroteo:
        c = np.zeros(n)
        for _ in range(int(n / SR * 40 * chisporroteo)):
            k = int(rng.uniform(0.002, 0.008) * SR)
            poner(c, rng.standard_normal(k) * np.hanning(k), rng.integers(0, n), rng.uniform(0.1, 1))
        x += 0.25 * normalizar(pasabanda(c, 800, 7000))
    return normalizar(x) * fuerza


def ceniza_cae(n, rng, fuerza=1.0):
    """Lluvia de ceniza fina: siseo muy suave y tic-tic de granos sobre las hojas."""
    siseo = pasabanda(ruido_periodico(n, rng, -0.5, (2000, 9000)), 3000, 7000) * 0.3
    tics = np.zeros(n)
    for _ in range(int(n / SR * 90)):
        k = int(0.002 * SR)
        poner(tics, rng.standard_normal(k) * np.hanning(k), rng.integers(0, n), rng.uniform(0.05, 0.4))
    return normalizar(siseo + pasabanda(tics, 2500, 7000)) * fuerza


def trueno_lejano(n, rng, cuantos=2, fuerza=1.0):
    x = np.zeros(n)
    for _ in range(cuantos):
        dur = rng.uniform(4, 7)
        m = int(dur * SR)
        rodar = pasabajos(rng.standard_normal(m), 300, 2, False) * envolvente(m, 0.4, dur / 2.5)
        rodar *= 0.6 + 0.4 * np.sin(2 * np.pi * np.arange(m) / SR * rng.uniform(1.5, 3))
        poner(x, rodar, rng.integers(0, n))
    return normalizar(x) * fuerza


def estereo(mono, rng, ancho=0.6):
    """Mono → estéreo ancho: el otro canal es el mismo con una demora corta (decorrelado)."""
    d = int(rng.uniform(0.008, 0.02) * SR)
    otro = np.roll(mono, d)
    return np.stack([mono + ancho * 0.3 * otro, otro + ancho * 0.3 * mono], 1)


# ---------------------------------------------------------------------------------------------
# capítulos
# ---------------------------------------------------------------------------------------------

def ambiente(capitulo, n, rng):
    v = lambda **k: estereo(viento(n, rng, **k), rng)          # noqa: E731
    if capitulo == "titulo":           # amanecer: brisa, los primeros insectos, el volcán muy lejos
        capas = [(v(fuerza=0.6, frondas=0.3), -20), (insectos(n, rng, 3), -30), (estereo(retumbe(n, rng, explosiones=1), rng), -32)]
    elif capitulo == "rio":
        capas = [(estereo(rio(n, rng), rng, 0.9), -16), (insectos(n, rng, 6), -27), (v(fuerza=0.5, frondas=0.4), -26)]
    elif capitulo == "bosque":
        capas = [(v(fuerza=0.9, frondas=1.0, vueltas=4), -17), (insectos(n, rng, 8), -25)]
    elif capitulo == "llanura":
        capas = [(v(fuerza=1.0, frondas=0.15, vueltas=2), -17), (estereo(retumbe(n, rng, explosiones=3), rng), -24), (insectos(n, rng, 2), -33)]
    elif capitulo == "ceniza":
        capas = [(estereo(retumbe(n, rng, explosiones=6, chisporroteo=1.0), rng), -15), (estereo(ceniza_cae(n, rng), rng, 1.0), -31),
                 (v(fuerza=0.7), -27), (estereo(trueno_lejano(n, rng), rng), -22)]
    else:                              # hoy: el viento seco del Valle de la Luna y casi nada más
        capas = [(v(fuerza=1.0, vueltas=2), -18)]
    x = np.zeros((n, 2))
    for capa, db in capas:
        c = capa if capa.ndim == 2 else np.stack([capa, capa], 1)
        x += c / (np.sqrt(np.mean(c ** 2)) + 1e-12) * 10 ** (db / 20)
    return x


# ---------------------------------------------------------------------------------------------
# animales
# ---------------------------------------------------------------------------------------------

# especie: (largo m, tipo de voz)
ESPECIES = {
    "eoraptor": (1.0, "arrullo"), "eodromaeus": (1.2, "arrullo"), "pisanosaurus": (1.0, "arrullo"),
    "panphagia": (1.3, "arrullo"), "chromogisaurus": (2.0, "arrullo"),
    "herrerasaurus": (4.0, "retumbe"), "sanjuansaurus": (3.0, "retumbe"),
    "saurosuchus": (6.0, "bramido"), "hyperodapedon": (1.3, "siseo"),
    "exaeretodon": (1.8, "resoplido"), "ischigualastia": (3.5, "grunido"),
}


def voz(tipo, largo, rng):
    """Una vocalización. f0 baja con el tamaño (≈ 1/largo): arrullos de 150-300 Hz en los chicos,
    retumbes de 25-60 Hz en los grandes."""
    if tipo in ("arrullo", "retumbe", "bramido"):
        f0 = {"arrullo": 260, "retumbe": 95, "bramido": 70}[tipo] / largo ** 0.7 * rng.uniform(0.9, 1.1)
        dur = {"arrullo": 0.6, "retumbe": 1.6, "bramido": 2.2}[tipo] * rng.uniform(0.8, 1.3)
        m = int(dur * SR)
        t = np.arange(m) / SR
        # glissando suave (sube y cae, como un arrullo de boca cerrada) y un temblor lento
        f = f0 * (1 + 0.12 * np.sin(np.pi * t / dur) + 0.02 * np.sin(2 * np.pi * 7 * t))
        fase = 2 * np.pi * np.cumsum(f) / SR
        x = sum((0.7 ** k) * np.sin(k * fase) for k in range(1, 7))
        # el cuerpo resuena (boca cerrada): formantes graves, casi sin agudos
        x = pasabajos(x, min(900, f0 * 6), 2, False)
        if tipo == "bramido":         # el cocodrilo: aspereza (ruido modulado por la fundamental)
            x += 0.4 * pasabajos(rng.standard_normal(m), 400, 2, False) * (0.5 + 0.5 * np.sin(fase))
        x *= envolvente(m, dur * 0.15, dur * 0.5)
    elif tipo == "siseo":             # rincosaurio: siseo corto y un chasquido del pico
        dur = rng.uniform(0.5, 0.9)
        m = int(dur * SR)
        x = pasabanda(rng.standard_normal(m), 1500, 7000, circular=False) * envolvente(m, 0.03, dur / 2)
        k = int(0.004 * SR)
        poner(x, rng.standard_normal(k) * np.hanning(k) * 3, int(rng.uniform(0.0, 0.1) * SR), circular=False)
    else:                             # línea de los mamíferos: resoplidos y gruñidos nasales
        dur = {"resoplido": 0.5, "grunido": 1.0}[tipo] * rng.uniform(0.8, 1.3)
        m = int(dur * SR)
        t = np.arange(m) / SR
        f0 = (140 if tipo == "resoplido" else 70) / largo ** 0.5
        tono = np.sin(2 * np.pi * f0 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 11 * t))
        aire = pasabanda(rng.standard_normal(m), 300, 2500, circular=False)
        x = (0.5 * tono + aire) * envolvente(m, 0.04, dur / 2.5)
    return normalizar(x, -3)


def pisada(peso, suelo, rng):
    """Golpe grave (más pesado, más grave y largo) + el suelo: chapoteo en barro, crujido en seco."""
    f = {"liviano": 90, "medio": 60, "pesado": 38}[peso] * rng.uniform(0.9, 1.1)
    dur = {"liviano": 0.12, "medio": 0.2, "pesado": 0.35}[peso]
    m = int((dur + 0.15) * SR)
    t = np.arange(m) / SR
    golpe = np.sin(2 * np.pi * f * t * (1 - 0.3 * t / (dur + 0.15))) * envolvente(m, 0.004, dur / 2)
    if suelo == "barro":
        chap = pasabanda(rng.standard_normal(m), 300, 2500, circular=False) * envolvente(m, 0.01, 0.06)
        x = golpe + 0.35 * chap
    else:
        cruj = pasabanda(rng.standard_normal(m), 1500, 8000, circular=False) * envolvente(m, 0.002, 0.03)
        x = golpe + 0.25 * cruj
    return normalizar(x, -3)


# ---------------------------------------------------------------------------------------------

def guardar(ruta, x):
    """OGG Vorbis escrito de a trozos: libsndfile se cae (segfault) si el codificador de Vorbis
    recibe un bloque grande de una sola vez."""
    x = np.clip(x, -1, 1).astype(np.float32)
    canales = 1 if x.ndim == 1 else x.shape[1]
    with sf.SoundFile(ruta, "w", SR, canales, format="OGG", subtype="VORBIS") as f:
        for i in range(0, len(x), 8192):
            f.write(x[i:i + 8192])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=SALIDA)
    ap.add_argument("--segundos", type=float, default=48.0)
    a = ap.parse_args()
    os.makedirs(a.salida, exist_ok=True)
    rng = np.random.default_rng(231)
    n = int(a.segundos * SR)
    informe = {"frecuencia_muestreo": SR, "loops_s": a.segundos, "archivos": []}

    for cap in ("titulo", "rio", "bosque", "llanura", "ceniza", "hoy"):
        x = ambiente(cap, n, rng)
        x = normalizar(x, -6)
        ruta = os.path.join(a.salida, f"ambiente_{cap}.ogg")
        guardar(ruta, x)
        # costura: la diferencia entre la última y la primera muestra (en un loop sin costura es chica)
        salto = float(np.abs(x[-1] - x[0]).max())
        informe["archivos"].append({"archivo": os.path.basename(ruta), "rms_db": round(nivel_rms_db(x), 1), "salto_costura": round(salto, 4)})
        print(f"  ambiente {cap}: {nivel_rms_db(x):.1f} dB RMS · salto en la costura {salto:.4f}")

    v = retumbe(n, rng, explosiones=5, chisporroteo=0.6)
    guardar(os.path.join(a.salida, "volcan.ogg"), normalizar(v, -3))
    informe["archivos"].append({"archivo": "volcan.ogg", "rms_db": round(nivel_rms_db(v), 1)})

    for esp, (largo, tipo) in ESPECIES.items():
        for i in range(3):
            guardar(os.path.join(a.salida, f"voz_{esp}_{i}.ogg"), voz(tipo, largo, rng))
        informe["archivos"].append({"archivo": f"voz_{esp}_*.ogg", "tipo": tipo, "largo_m": largo})
    for peso in ("liviano", "medio", "pesado"):
        for suelo in ("barro", "seco"):
            for i in range(3):
                guardar(os.path.join(a.salida, f"pisada_{peso}_{suelo}_{i}.ogg"), pisada(peso, suelo, rng))
    total = sum(os.path.getsize(os.path.join(a.salida, f)) for f in os.listdir(a.salida) if f.endswith(".ogg"))
    informe["mb"] = round(total / 1048576, 2)
    json.dump(informe, open(os.path.join(a.salida, "informe_sonido.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"listo: {len([f for f in os.listdir(a.salida) if f.endswith('.ogg')])} archivos · {informe['mb']} MB → {a.salida}")


if __name__ == "__main__":
    main()
