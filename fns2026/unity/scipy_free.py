"""Interpolación en grillas con numpy solo (en la nube no hay scipy): bilineal y bicúbica
Catmull-Rom, con los bordes repetidos. La usan valle_real.py y las pruebas."""

import numpy as np


def mapa_coordenadas(img, filas, cols, orden=3):
    """img[filas, cols] con filas/cols fraccionarias (arrays de la misma forma)."""
    img = np.asarray(img, dtype=np.float64)
    n, m = img.shape
    f = np.asarray(filas, dtype=np.float64)
    c = np.asarray(cols, dtype=np.float64)
    f0 = np.floor(f).astype(np.int64)
    c0 = np.floor(c).astype(np.int64)
    tf, tc = f - f0, c - c0

    def g(j, i):
        return img[np.clip(j, 0, n - 1), np.clip(i, 0, m - 1)]

    if orden == 1:
        return ((g(f0, c0) * (1 - tc) + g(f0, c0 + 1) * tc) * (1 - tf)
                + (g(f0 + 1, c0) * (1 - tc) + g(f0 + 1, c0 + 1) * tc) * tf)

    def pesos(t):
        t2, t3 = t * t, t * t * t
        return (-0.5 * t3 + t2 - 0.5 * t, 1.5 * t3 - 2.5 * t2 + 1, -1.5 * t3 + 2 * t2 + 0.5 * t, 0.5 * t3 - 0.5 * t2)

    wf, wc = pesos(tf), pesos(tc)
    out = np.zeros_like(f)
    for a in range(4):
        fila = np.zeros_like(f)
        for b in range(4):
            fila += g(f0 - 1 + a, c0 - 1 + b) * wc[b]
        out += fila * wf[a]
    return out
