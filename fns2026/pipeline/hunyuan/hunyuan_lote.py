"""
Una foto → un modelo 3D, por lotes, con Hunyuan3D-2 (Tencent) corriendo en la OMEN.

    python hunyuan_lote.py CARPETA_DE_FOTOS [--textura] [--caras 60000] [--octree 384] [--pasos 5]
    (o con Blender: blender -b --factory-startup --python hunyuan_lote.py -- CARPETA ...)

Habla con el servidor oficial (api_server.py) que deja andando HUNYUAN_SERVIDOR.bat en
http://localhost:8080 (el mismo que usa el plugin de Blender). Las fotos no salen de la PC.

El nombre de cada foto es el del modelo: el_hongo.jpg → fns2026/modelos/el_hongo/el_hongo_alto.glb,
que es donde el Constructor de Unity busca el Hongo (y el_submarino.jpg, el Submarino). Fotos con
fondo limpio y el objeto entero dan los mejores resultados; el servidor saca el fondo solo.

Sin --textura sale la forma (en Unity las formaciones llevan el material triplanar de estratos del
paredón); con --textura, Hunyuan la pinta (necesita la extensión compilada: ver LEEME.md).
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.abspath(os.path.join(AQUI, "..", ".."))
EXT = (".jpg", ".jpeg", ".png", ".webp")


def argumentos():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--servidor", default="http://localhost:8080")
    ap.add_argument("--salida", default=os.path.join(FNS, "modelos"))
    ap.add_argument("--textura", action="store_true")
    ap.add_argument("--caras", type=int, default=60000, help="tope de caras al texturizar")
    ap.add_argument("--octree", type=int, default=384, help="resolución de la forma (256-512)")
    ap.add_argument("--pasos", type=int, default=5, help="pasos del modelo turbo (5 alcanza)")
    ap.add_argument("--guia", type=float, default=5.0)
    ap.add_argument("--semilla", type=int, default=1234)
    ap.add_argument("--rehacer", action="store_true", help="volver a generar aunque ya exista")
    return ap.parse_args(argv)


def generar(servidor, foto, a):
    cuerpo = {
        "image": base64.b64encode(open(foto, "rb").read()).decode(),
        "octree_resolution": a.octree, "num_inference_steps": a.pasos, "guidance_scale": a.guia,
        "seed": a.semilla, "texture": a.textura, "face_count": a.caras,
    }
    pedido = urllib.request.Request(servidor.rstrip("/") + "/generate", data=json.dumps(cuerpo).encode(),
                                    headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(pedido, timeout=1800) as r:
            datos = r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"el servidor respondió {e.code}: {e.read()[:200]!r}")
    if datos[:4] != b"glTF":
        raise RuntimeError(f"no volvió un GLB: {datos[:120]!r}")
    return datos


def main():
    a = argumentos()
    fotos = sorted(f for f in os.listdir(a.carpeta) if f.lower().endswith(EXT))
    if not fotos:
        raise SystemExit(f"no hay fotos ({', '.join(EXT)}) en {a.carpeta}")
    try:
        urllib.request.urlopen(a.servidor.rstrip("/") + "/docs", timeout=10).read(10)
    except Exception:
        raise SystemExit(f"no responde el servidor en {a.servidor}: abrí HUNYUAN_SERVIDOR.bat y esperá a que diga que está listo")
    hechos = []
    for f in fotos:
        nombre = os.path.splitext(f)[0].lower().replace(" ", "_")
        destino = os.path.join(a.salida, nombre, f"{nombre}_alto.glb")
        if os.path.exists(destino) and not a.rehacer:
            print(f"   {nombre}: ya está ({destino})")
            continue
        t0 = time.time()
        print(f"   {nombre}: generando{' con textura' if a.textura else ''}…", flush=True)
        try:
            glb = generar(a.servidor, os.path.join(a.carpeta, f), a)
        except Exception as e:
            print(f"   {nombre}: FALLÓ ({e})")
            hechos.append({"modelo": nombre, "ok": False, "error": str(e)})
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        open(destino, "wb").write(glb)
        info = {"modelo": nombre, "ok": True, "foto": f, "glb": os.path.relpath(destino, FNS).replace(os.sep, "/"),
                "mb": round(len(glb) / 1048576, 2), "segundos": round(time.time() - t0), "textura": a.textura,
                "octree": a.octree, "pasos": a.pasos, "semilla": a.semilla,
                "fuente": "Hunyuan3D-2 (Tencent Hunyuan 3D 2.0 Community License)"}
        json.dump(info, open(os.path.join(os.path.dirname(destino), f"{nombre}_hunyuan.json"), "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False)
        hechos.append(info)
        print(f"   {nombre}: listo · {info['mb']} MB · {info['segundos']} s → {destino}")
    ok = sum(1 for h in hechos if h["ok"])
    print(f"listo: {ok} de {len(hechos)} modelos nuevos")
    sys.exit(0 if ok == len(hechos) else 1)


if __name__ == "__main__":
    main()
