"""
Meshy → modelos para el stand. Paso 1 de la cañería (el 2 es blender_refinar.py).

    vistas (Meshy texto→imagen, multi-vista)  →  modelo (Meshy multi-imagen→3D)
        →  rig + animaciones (Meshy rigging)  →  descarga GLB/FBX  →  blender_refinar.py

Por qué por API y no desde la web de Meshy: los 9 huesos, los 7 dinosaurios y las
maquetas son decenas de modelos. A mano es una tarde por modelo y cada uno sale con
otros ajustes; por script salen todos iguales y se pueden regenerar el día antes.

Sólo biblioteca estándar: corre igual en la Mac M4 y en las OMEN sin instalar nada.
La clave va en la variable MESHY_API_KEY, nunca en el archivo ni en el repo.

    python3 meshy_a_fbx.py lista.json salida/          # todo lo de la lista
    python3 meshy_a_fbx.py lista.json salida/ --solo herrerasaurus
    python3 meshy_a_fbx.py --probar                     # sin red: valida la lista y arma los pedidos

NO PROBADO CONTRA LA API REAL: desde el entorno donde se escribió no había salida a
api.meshy.ai. Los nombres de campos siguen la documentación pública de Meshy
(docs.meshy.ai). Si Meshy cambió alguno, el error de la API lo dice textual y se
corrige en PEDIDOS, abajo, sin tocar el resto.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

API = "https://api.meshy.ai/openapi"

# Un lugar para todos los endpoints: si Meshy cambia una versión se toca acá.
PEDIDOS = {
    "vistas":      ("v1", "text-to-image"),
    "texto_3d":    ("v2", "text-to-3d"),
    "imagen_3d":   ("v1", "image-to-3d"),
    "multi_3d":    ("v1", "multi-image-to-3d"),
    "rig":         ("v1", "rigging"),
    "animacion":   ("v1", "animations"),
}

# Estilo común a todo el stand. Se agrega a cada prompt para que los 7 dinosaurios
# parezcan de la misma colección y no de siete artistas distintos.
ESTILO = {
    "dinosaurio": ("scientifically accurate Late Triassic reptile, museum-quality paleoart, "
                   "neutral studio light, plain background, full body, no text, no watermark"),
    "hueso": ("real fossil photograph look, Ischigualasto red and grey-green sandstone, "
              "soft overhead light, no text, no watermark"),
    "maqueta": ("miniature diorama, handcrafted scale model look, soft studio light, no text"),
}

# Polígonos de salida de Meshy. blender_refinar.py después baja a lo que aguanta cada máquina.
POLIGONOS_MESHY = 60000


def _clave():
    k = os.environ.get("MESHY_API_KEY", "").strip()
    if not k:
        sys.exit("Falta MESHY_API_KEY. En Mac: export MESHY_API_KEY=... · En Windows: set MESHY_API_KEY=...")
    return k


def _url(tipo, id_tarea=None):
    ver, ruta = PEDIDOS[tipo]
    u = f"{API}/{ver}/{ruta}"
    return f"{u}/{id_tarea}" if id_tarea else u


def _llamar(metodo, url, cuerpo=None, intentos=4):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    req = urllib.request.Request(url, data=datos, method=metodo, headers={
        "Authorization": f"Bearer {_clave()}",
        "Content-Type": "application/json",
    })
    espera = 2
    for i in range(intentos):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            texto = e.read().decode(errors="replace")
            # 429 y 5xx se reintentan; un 400 es un campo mal armado y reintentar no sirve.
            if e.code in (429, 500, 502, 503, 504) and i < intentos - 1:
                time.sleep(espera)
                espera *= 2
                continue
            raise SystemExit(f"Meshy respondió {e.code} en {url}:\n{texto}")
        except urllib.error.URLError as e:
            if i < intentos - 1:
                time.sleep(espera)
                espera *= 2
                continue
            raise SystemExit(f"Sin conexión con Meshy ({e.reason}).")


def crear(tipo, cuerpo):
    r = _llamar("POST", _url(tipo), cuerpo)
    return r.get("result") or r.get("id")


def esperar(tipo, id_tarea, cada=8, tope_min=30):
    """Espera a que termine. Las tareas de Meshy tardan de 1 a 10 minutos."""
    t0 = time.time()
    while True:
        r = _llamar("GET", _url(tipo, id_tarea))
        estado = r.get("status")
        prog = r.get("progress", 0)
        print(f"   {tipo} {id_tarea[:8]}… {estado} {prog}%", flush=True)
        if estado == "SUCCEEDED":
            return r
        if estado in ("FAILED", "CANCELED", "EXPIRED"):
            raise SystemExit(f"La tarea {tipo} terminó en {estado}: {r.get('task_error')}")
        if time.time() - t0 > tope_min * 60:
            raise SystemExit(f"La tarea {tipo} pasó los {tope_min} minutos. Revisala en meshy.ai.")
        time.sleep(cada)


def bajar(url, destino):
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with urllib.request.urlopen(url, timeout=300) as r, open(destino, "wb") as f:
        f.write(r.read())
    print(f"   ↓ {destino}")
    return destino


# ---------------------------------------------------------------------------
# Armado de pedidos (sin red; se prueban con --probar)
# ---------------------------------------------------------------------------

def pedido_vistas(item):
    return {
        "ai_model": item.get("modelo_imagen", "nano-banana"),
        "prompt": f"{item['prompt']}, {ESTILO[item.get('destino', 'dinosaurio')]}",
        "generate_multi_view": True,
    }


def pedido_multi_3d(urls_vistas, item):
    return {
        "image_urls": urls_vistas[:4],
        "should_remesh": True,
        "topology": "quad",                  # quads: Blender los suaviza y riggea mejor que triángulos
        "target_polycount": item.get("poligonos", POLIGONOS_MESHY),
        "should_texture": True,
        "enable_pbr": True,
    }


def pedido_texto_3d(item):
    return {
        "mode": "preview",
        "prompt": f"{item['prompt']}, {ESTILO[item.get('destino', 'dinosaurio')]}",
        "art_style": "realistic",
        "should_remesh": True,
        "topology": "quad",
        "target_polycount": item.get("poligonos", POLIGONOS_MESHY),
    }


def pedido_rig(id_modelo, item):
    return {"input_task_id": id_modelo, "height_meters": item["alto_m"]}


# ---------------------------------------------------------------------------
# Un ítem de la lista, de punta a punta
# ---------------------------------------------------------------------------

def hacer(item, salida):
    nombre = item["nombre"]
    carpeta = os.path.join(salida, nombre)
    print(f"\n== {nombre} ==")

    # 1) vistas. Si el ítem trae imágenes propias (fotos de un fósil real cedidas por
    #    el MuPa, o un dibujo de Illustrator), se usan ésas y no se generan.
    if item.get("vistas"):
        urls = item["vistas"]
    else:
        id_v = crear("vistas", pedido_vistas(item))
        r = esperar("vistas", id_v)
        urls = r.get("image_urls") or []
        for i, u in enumerate(urls):
            bajar(u, os.path.join(carpeta, f"vista_{i}.png"))
    if not urls:
        raise SystemExit(f"{nombre}: Meshy no devolvió vistas.")

    # 2) modelo: multi-vista da mejor geometría que una sola imagen
    tipo = "multi_3d" if len(urls) > 1 else "imagen_3d"
    cuerpo = pedido_multi_3d(urls, item)
    if tipo == "imagen_3d":
        cuerpo = {**cuerpo, "image_url": urls[0]}
        cuerpo.pop("image_urls")
    id_m = crear(tipo, cuerpo)
    r = esperar(tipo, id_m)
    urls_modelo = r.get("model_urls", {})
    for fmt in ("glb", "fbx"):
        if urls_modelo.get(fmt):
            bajar(urls_modelo[fmt], os.path.join(carpeta, f"{nombre}_meshy.{fmt}"))

    # 3) rig + animaciones básicas, sólo para lo que se mueve (dinosaurios, no huesos)
    if item.get("rig"):
        id_r = crear("rig", pedido_rig(id_m, item))
        r = esperar("rig", id_r)
        res = r.get("result", {})
        if res.get("rigged_character_fbx_url"):
            bajar(res["rigged_character_fbx_url"], os.path.join(carpeta, f"{nombre}_rig.fbx"))
        for anim, url in (res.get("basic_animations") or {}).items():
            if anim.endswith("_fbx_url") and url:
                bajar(url, os.path.join(carpeta, f"{nombre}_{anim.replace('_fbx_url', '')}.fbx"))

    return carpeta


def main():
    ap = argparse.ArgumentParser(description="Meshy → GLB/FBX para el stand")
    ap.add_argument("lista", nargs="?", default=os.path.join(os.path.dirname(__file__), "lista_modelos.json"))
    ap.add_argument("salida", nargs="?", default="modelos_meshy")
    ap.add_argument("--solo", help="hacer sólo el ítem con este nombre")
    ap.add_argument("--probar", action="store_true", help="sin red: valida la lista y muestra los pedidos")
    a = ap.parse_args()

    with open(a.lista, encoding="utf-8") as f:
        lista = json.load(f)["modelos"]
    if a.solo:
        lista = [m for m in lista if m["nombre"] == a.solo]
        if not lista:
            sys.exit(f"No hay ningún modelo llamado {a.solo}")

    if a.probar:
        for m in lista:
            assert m.get("prompt") or m.get("vistas"), f"{m['nombre']}: falta prompt o vistas"
            if m.get("rig"):
                assert m.get("alto_m"), f"{m['nombre']}: un modelo con rig necesita alto_m"
            print(m["nombre"], json.dumps(pedido_vistas(m) if m.get("prompt") else {"vistas": m["vistas"]},
                                          ensure_ascii=False)[:140])
        print(f"\n{len(lista)} modelos OK, sin llamar a la API.")
        return

    for m in lista:
        hacer(m, a.salida)


if __name__ == "__main__":
    main()
