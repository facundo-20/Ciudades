"""Prueba de Proyeccion.FueraDeEje (Sala.cs) con las convenciones de Unity, en numpy:
cada esquina física de cada superficie de sala_*.json tiene que caer en la esquina de su imagen
(-1,-1 abajo-izq, 1,-1 abajo-der, -1,1 arriba-izq), con el ojo en el punto dulce y corrido."""
import json, os, sys
import numpy as np

def look_rotation(fwd, up):
    # Quaternion.LookRotation de Unity como matriz: columnas = derecha, arriba, adelante
    z = fwd / np.linalg.norm(fwd)
    x = np.cross(up, z); x /= np.linalg.norm(x)        # Vector3.Cross de Unity = producto vectorial común
    y = np.cross(z, x)
    return np.stack([x, y, z], 1)

def frustum(l, r, b, t, n, f):                          # Matrix4x4.Frustum (OpenGL)
    return np.array([[2*n/(r-l), 0, (r+l)/(r-l), 0], [0, 2*n/(t-b), (t+b)/(t-b), 0],
                     [0, 0, -(f+n)/(f-n), -2*f*n/(f-n)], [0, 0, -1, 0]])

def fuera_de_eje(pa, pb, pc, pe, n=0.05, f=12000):
    vr = (pb-pa)/np.linalg.norm(pb-pa); vu = (pc-pa)/np.linalg.norm(pc-pa)
    adelante = np.cross(vr, vu); adelante /= np.linalg.norm(adelante)
    va, vb, vc = pa-pe, pb-pe, pc-pe
    d = adelante @ va
    l, r = (vr @ va)*n/d, (vr @ vb)*n/d
    b, t = (vu @ va)*n/d, (vu @ vc)*n/d
    return look_rotation(adelante, vu), frustum(l, r, b, t, n, f)

def ndc(p, pe, R, P):
    local = R.T @ (p - pe)                            # mundo → local de la cámara
    cam = np.array([local[0], local[1], -local[2], 1])  # worldToCameraMatrix invierte Z
    c = P @ cam
    return c[:2] / c[3]

fallas = 0
for archivo in ("sala_pared.json", "sala_cubo.json"):
    cfg = json.load(open(os.path.join(os.path.dirname(__file__), "..", "ParqueTriasico", "Assets", "StreamingAssets", archivo)))
    for corrimiento in (0.0, 1.7, -2.2):
        pe = np.array(cfg["ojo"], float) + np.array([corrimiento, 0, 0])
        for s in cfg["superficies"]:
            pa, pb, pc = (np.array(s[k], float) for k in ("abajo_izq", "abajo_der", "arriba_izq"))
            R, P = fuera_de_eje(pa, pb, pc, pe)
            got = [ndc(p, pe, R, P) for p in (pa, pb, pc, pb + (pc - pa))]
            want = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
            ok = all(np.allclose(g, w, atol=1e-6) for g, w in zip(got, want))
            # la cámara mira hacia adentro de la superficie (no hacia atrás)
            ok &= (R[:, 2] @ (pa - pe)) > 0
            fallas += not ok
            print(f"{'ok   ' if ok else 'FALLA'} {archivo} ojo x{corrimiento:+.1f} {s['nombre']:9s} esquinas → {[tuple(np.round(g, 3)) for g in got]}")
print("fallas:", fallas)
sys.exit(1 if fallas else 0)
