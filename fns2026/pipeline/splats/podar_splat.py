"""
Poda un splat horneado (salida de Brush, formato .ply de 3DGS) para usarlo en Unity y en la web:

  · el suelo: los splats a menos de 12 cm del terreno (el suelo lo dibuja el terreno de HDRP, que
    recibe las sombras de los dinosaurios, las pisadas y la ceniza)
  · lo de abajo del terreno (flotantes enterrados)
  · lo que queda lejos del recorrido (más allá del radio + 3 m: ahí sigue la vegetación de mallas)
  · lo casi transparente (opacidad < 1 %) y lo gigante (> 4 m: fondo mal aprendido)

    python3 podar_splat.py ENTRADA.ply SALIDA.ply --region region.json [--sin-podar-suelo]

Lee la altura del terreno con las mismas fórmulas que la escena (escenas/hiperreal/triasico_cycles.py),
así que corre con el Python de Blender o con el bpy de pip.
"""
import argparse
import json
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "..", "escenas", "hiperreal"))


def leer_ply(ruta):
    with open(ruta, "rb") as f:
        cab = []
        while True:
            linea = f.readline().decode("ascii").strip()
            cab.append(linea)
            if linea == "end_header":
                break
        if not any("binary_little_endian" in c for c in cab):
            raise SystemExit(f"{ruta}: sólo .ply binario little-endian (el de Brush, gsplat o 3DGS)")
        tipos = {"float": "<f4", "float32": "<f4", "double": "<f8", "uchar": "u1", "uint8": "u1",
                 "int": "<i4", "uint": "<u4", "short": "<i2", "ushort": "<u2"}
        props, n, en_vertices = [], 0, False
        for c in cab:
            p = c.split()
            if p[:2] == ["element", "vertex"]:
                n, en_vertices = int(p[2]), True
            elif p and p[0] == "element":
                en_vertices = False
            elif p and p[0] == "property" and en_vertices:
                props.append((p[2], tipos[p[1]]))
        datos = np.frombuffer(f.read(n * np.dtype(props).itemsize), dtype=np.dtype(props), count=n)
    return cab, datos


# el orden de propiedades del 3DGS original: Brush las escribe en orden alfabético (f_rest_0,
# f_rest_1, f_rest_10…). Unity las busca por nombre, pero algunos lectores asumen este orden.
ORDEN = (["x", "y", "z", "nx", "ny", "nz", "f_dc_0", "f_dc_1", "f_dc_2"] + [f"f_rest_{i}" for i in range(45)]
         + ["opacity", "scale_0", "scale_1", "scale_2", "rot_0", "rot_1", "rot_2", "rot_3"])
NOMBRE_TIPO = {"<f4": "float", "<f8": "double", "|u1": "uchar", "<i4": "int", "<u4": "uint", "<i2": "short", "<u2": "ushort"}


def escribir_ply(ruta, cab, datos):
    nombres = [n for n in ORDEN if n in datos.dtype.names] + [n for n in datos.dtype.names if n not in ORDEN]
    tipo = np.dtype([(n, datos.dtype[n]) for n in nombres])
    salida = np.empty(len(datos), dtype=tipo)
    for n in nombres:
        salida[n] = datos[n]
    lineas = ["ply", "format binary_little_endian 1.0",
              # el mundo es el de Blender (z arriba): sin el "Vertical axis: y" de Brush, que hace que
              # algunos visores lo den vuelta
              "comment FNS 2026: mundo de Blender (z arriba), podado con pipeline/splats/podar_splat.py",
              f"element vertex {len(salida)}"]
    lineas += [f"property {NOMBRE_TIPO[salida.dtype[n].str]} {n}" for n in nombres] + ["end_header"]
    with open(ruta, "wb") as f:
        f.write(("\n".join(lineas) + "\n").encode("ascii"))
        f.write(salida.tobytes())


def distancia_al_recorrido(P, a, b):
    a, b = np.asarray(a[:2], float), np.asarray(b[:2], float)
    ab = b - a
    t = np.clip(((P[:, :2] - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
    return np.linalg.norm(P[:, :2] - (a + t[:, None] * ab), axis=1)


def podar(datos, region, podar_suelo=True, margen=3.0):
    P = np.stack([datos["x"], datos["y"], datos["z"]], axis=1).astype(np.float64)
    quedan = np.ones(len(P), bool)
    motivos = {}

    def sacar(mascara, motivo):
        nuevos = mascara & quedan
        motivos[motivo] = int(nuevos.sum())
        quedan[nuevos] = False

    if region:
        sacar(distancia_al_recorrido(P, region["desde_blender"], region["hasta_blender"]) > region["radio_m"] + margen, "lejos del recorrido")
    if "opacity" in datos.dtype.names:
        sacar(1 / (1 + np.exp(-datos["opacity"].astype(np.float64))) < 0.01, "casi transparentes")
    if "scale_0" in datos.dtype.names:
        escala = np.exp(np.max(np.stack([datos[f"scale_{i}"] for i in range(3)], axis=1), axis=1))
        sacar(escala > 4.0, "gigantes")
    if podar_suelo:
        import triasico_cycles as T     # necesita mathutils (Blender o bpy de pip)
        idx = np.nonzero(quedan)[0]
        suelo = np.array([T.altura(P[i, 0], -P[i, 1]) for i in idx])
        sobre = P[idx, 2] - suelo
        m = np.zeros(len(P), bool)
        m[idx[sobre < -0.3]] = True
        sacar(m, "debajo del terreno")
        m = np.zeros(len(P), bool)
        m[idx[(sobre >= -0.3) & (sobre < 0.12)]] = True
        sacar(m, "suelo (lo dibuja el terreno de HDRP)")
    return datos[quedan], motivos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--region", help="region.json de vistas_blender.py")
    ap.add_argument("--sin-podar-suelo", action="store_true")
    # también con Blender: blender -b -P podar_splat.py -- ENTRADA SALIDA ...
    a = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    region = json.load(open(a.region, encoding="utf-8")) if a.region else None
    cab, datos = leer_ply(a.entrada)
    podado, motivos = podar(datos, region, not a.sin_podar_suelo)
    escribir_ply(a.salida, cab, podado)
    for k, v in motivos.items():
        print(f"  - {v:>9,} {k}")
    print(f"{len(datos):,} → {len(podado):,} splats · {os.path.getsize(a.salida) / 1048576:.1f} MB → {a.salida}")


if __name__ == "__main__":
    main()
