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
    # Ischigualasto (Carniano, ~231 Ma): no hay evidencia de plumas en estos animales, y los
    # generadores de imagen las agregan solos si no se les dice; por eso va explícito.
    "dinosaurio": ("scientifically accurate Late Triassic reptile, museum-quality paleoart, "
                   "scaly reptilian skin, no feathers, no fur, natural muted earth colors, "
                   "neutral studio light, plain background, full body side view, no text, no watermark"),
    "hueso": ("real fossil photograph look, Ischigualasto red and grey-green sandstone, "
              "soft overhead light, no text, no watermark"),
    "maqueta": ("miniature diorama, handcrafted scale model look, soft studio light, no text"),
    # El paisaje va a escala real y fotorrealista: PBR con rugosidad y normales de roca
    # de verdad, luz de mediodía dura del desierto sanjuanino, nada de look de maqueta.
    "flora": ("photorealistic plant asset, real botanical scale, PBR materials with detailed albedo roughness "
              "and normal, isolated on plain background, full plant visible, no text, no watermark"),
    "paisaje": ("photorealistic terrain asset, real geological scale, PBR materials with "
                "detailed albedo roughness and normal, harsh midday desert sunlight, "
                "Ischigualasto Provincial Park San Juan Argentina, no text, no watermark"),
}

# Polígonos de salida de Meshy. blender_refinar.py después baja a lo que aguanta cada máquina.
POLIGONOS_MESHY = 60000


_CLAVE_OK = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


def _clave():
    """La clave limpia. Un 400 pelado en TODOS los pedidos suele ser esto: al pegarla se
    cuelan comillas, un espacio o un carácter invisible, y el encabezado Authorization
    queda mal armado. Se deja sólo lo que puede tener una clave de Meshy (msy_...)."""
    cruda = os.environ.get("MESHY_API_KEY", "")
    archivo = os.path.expanduser("~/.meshy_api_key")          # donde la guarda el proyecto de la Mac
    if not cruda and os.path.exists(archivo):
        cruda = open(archivo, encoding="utf-8", errors="replace").read()
        # si el archivo tiene un comando pegado (pasó en la Mac), se busca la clave adentro
        import re
        m = re.search(r"msy_[A-Za-z0-9_-]{16,}", cruda)
        cruda = m.group(0) if m else cruda
    k = "".join(c for c in cruda if c in _CLAVE_OK)
    if not k:
        # Sin clave a la vista: en claude.ai/code la clave va en "Credenciales de API" del entorno
        # y el proxy de la sesión le agrega el Authorization a cada pedido sin que el script la vea.
        return None
    return k


def diagnostico():
    """Revisa la clave (sin mostrarla) y hace un pedido mínimo de sólo lectura."""
    cruda = os.environ.get("MESHY_API_KEY", "") or "(desde ~/.meshy_api_key)"
    k = _clave()
    if not k:
        print("clave: no hay en el entorno ni en ~/.meshy_api_key → uso la credencial del proxy de la sesión")
        r = _llamar("GET", f"{API}/v1/balance")
        print(f"Meshy responde. Créditos: {r.get('balance', r)}")
        return r
    print(f"clave: {len(k)} caracteres, empieza con '{k[:4]}'")
    if cruda != k:
        raros = sorted({repr(c) for c in cruda if c not in _CLAVE_OK})
        print(f"  OJO: la clave guardada tenía caracteres de más que se sacaron: {', '.join(raros)}")
        print("  Conviene volver a guardarla limpia (borrar MESHY_API_KEY y correr el instalador).")
    if not k.startswith("msy_"):
        print("  OJO: las claves de la API de Meshy empiezan con msy_. ¿Es la clave de API y no otra?")
    r = _llamar("GET", f"{API}/v1/balance")
    print(f"Meshy responde. Créditos: {r.get('balance', r)}")
    return r


def _url(tipo, id_tarea=None):
    ver, ruta = PEDIDOS[tipo]
    u = f"{API}/{ver}/{ruta}"
    return f"{u}/{id_tarea}" if id_tarea else u


def _llamar(metodo, url, cuerpo=None, intentos=4):
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    clave = _clave()
    encabezados = {"Authorization": f"Bearer {clave}"} if clave else {}
    req = urllib.request.Request(url, data=datos, method=metodo, headers={
        **encabezados,
        "Content-Type": "application/json",
        "Accept": "application/json",
        # sin esto urllib manda "Python-urllib/3.x", que algunos firewalls rechazan con un 400/403 pelado
        "User-Agent": "fns2026-pipeline/1.0 (+https://github.com/facundo-20/Ciudades)",
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
            enviado = json.dumps(cuerpo, ensure_ascii=False)[:600] if cuerpo is not None else "-"
            servidor = f"{e.headers.get('Server', '?')} · {e.headers.get('Content-Type', '?')}"
            raise SystemExit(f"Meshy respondió {e.code} en {url}:\n{texto.strip()[:800]}\n"
                             f"Servidor: {servidor}\nPedido enviado: {enviado}")
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

def _diario(carpeta):
    """Los id de tarea de Meshy de este modelo. Se guardan ANTES de esperar: si se corta la
    red, se bloquea la descarga o se reinicia la máquina, la próxima corrida retoma la
    misma tarea en vez de pagar otra."""
    ruta = os.path.join(carpeta, "tareas.json")
    datos = json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else {}
    return ruta, datos


def paso(carpeta, clave, tipo, cuerpo):
    ruta, datos = _diario(carpeta)
    id_t = datos.get(clave)
    if id_t:
        r = _llamar("GET", _url(tipo, id_t))
        if r.get("status") not in ("FAILED", "CANCELED", "EXPIRED"):
            print(f"   retomo {tipo} {id_t[:8]}… (ya pagada)")
            return id_t, esperar(tipo, id_t)
    id_t = crear(tipo, cuerpo)
    datos[clave] = id_t
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=1)
    return id_t, esperar(tipo, id_t)


def vistas_ya_hechas(prompt):
    """Busca en la cuenta una tarea de vistas con el mismo prompt que ya haya salido bien
    (pasó el 28/09: las vistas se generaron pero la bajada de imágenes estaba bloqueada)."""
    try:
        r = _llamar("GET", _url("vistas") + "?page_size=50&sort_by=-created_at")
    except SystemExit:
        return None
    for t in (r if isinstance(r, list) else r.get("result", [])):
        if t.get("status") == "SUCCEEDED" and t.get("prompt") == prompt and t.get("image_urls"):
            return t
    return None


def bajar_opcional(url, destino):
    """Las vistas bajadas son sólo para mirarlas; Meshy trabaja con sus propias URLs."""
    try:
        return bajar(url, destino)
    except Exception as e:  # noqa: BLE001
        print(f"   (no pude bajar {os.path.basename(destino)}: {e}; sigo igual)")
        return None


def por_vistas(item, carpeta):
    """Camino A: vistas multi-ángulo → multi-imagen a 3D. Da mejor geometría."""
    if item.get("vistas"):
        urls = item["vistas"]
    else:
        cuerpo_v = pedido_vistas(item)
        ruta, datos = _diario(carpeta)
        previa = None if datos.get("vistas") else vistas_ya_hechas(cuerpo_v["prompt"])
        if previa:
            print(f"   reuso vistas ya generadas {previa['id'][:8]}…")
            datos["vistas"] = previa["id"]
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, indent=1)
        _, r = paso(carpeta, "vistas", "vistas", cuerpo_v)
        urls = r.get("image_urls") or []
        for i, u in enumerate(urls):
            if not os.path.exists(os.path.join(carpeta, f"vista_{i}.png")):
                bajar_opcional(u, os.path.join(carpeta, f"vista_{i}.png"))
    if not urls:
        raise SystemExit("Meshy no devolvió vistas.")
    tipo = "multi_3d" if len(urls) > 1 else "imagen_3d"
    cuerpo = pedido_multi_3d(urls, item)
    if tipo == "imagen_3d":
        cuerpo = {**cuerpo, "image_url": urls[0]}
        cuerpo.pop("image_urls")
    return paso(carpeta, tipo, tipo, cuerpo)


def por_texto(item, carpeta):
    """Camino B: texto a 3D, borrador y después refinado con PBR. Es el endpoint más
    viejo y estable de Meshy; se usa si el de vistas no está en el plan o rechaza el pedido."""
    id_p, _ = paso(carpeta, "texto_borrador", "texto_3d", pedido_texto_3d(item))
    return paso(carpeta, "texto_refinado", "texto_3d",
                {"mode": "refine", "preview_task_id": id_p, "enable_pbr": True})


def hacer(item, salida):
    nombre = item["nombre"]
    carpeta = os.path.join(salida, nombre)
    os.makedirs(carpeta, exist_ok=True)
    print(f"\n== {nombre} ==")

    camino = os.environ.get("MESHY_CAMINO", "auto")      # auto | vistas | texto
    if camino == "texto":
        id_m, r = por_texto(item, carpeta)
    else:
        try:
            id_m, r = por_vistas(item, carpeta)
        except SystemExit as e:
            if camino == "vistas" or item.get("vistas"):
                raise
            print(f"   las vistas fallaron, sigo con texto a 3D:\n   {str(e)[:400]}")
            id_m, r = por_texto(item, carpeta)

    urls_modelo = r.get("model_urls", {})
    if r.get("thumbnail_url"):
        bajar_opcional(r["thumbnail_url"], os.path.join(carpeta, f"{nombre}_meshy_vista.png"))
    bajados = 0
    for fmt in ("glb", "fbx"):
        if urls_modelo.get(fmt):
            try:
                bajar(urls_modelo[fmt], os.path.join(carpeta, f"{nombre}_meshy.{fmt}"))
            except urllib.error.URLError as e:
                raise SystemExit(f"{nombre}: el modelo está hecho en Meshy (tarea {id_m}) pero no se pudo "
                                 f"bajar de {urls_modelo[fmt].split('/')[2]}: {e}. Habilitá ese dominio en "
                                 f"la red del entorno y volvé a correr: retoma sin gastar.")
            bajados += 1
    if not bajados:
        raise SystemExit(f"{nombre}: la tarea terminó pero no trae model_urls: {list(r)}")

    # 3) rig + animaciones básicas, sólo para lo que se mueve (dinosaurios, no huesos)
    if item.get("rig"):
        # El rig de Meshy está pensado para bípedos; con los cuadrúpedos (rincosaurio,
        # dicinodonte) puede fallar. El modelo ya está bajado, así que eso no lo invalida.
        try:
            _, r = paso(carpeta, "rig", "rig", pedido_rig(id_m, item))
        except SystemExit as e:
            print(f"   el rig falló, queda el modelo sin esqueleto: {str(e)[:300]}")
            return carpeta
        res = r.get("result", {})
        if res.get("rigged_character_fbx_url"):
            bajar(res["rigged_character_fbx_url"], os.path.join(carpeta, f"{nombre}_rig.fbx"))
        for anim, url in (res.get("basic_animations") or {}).items():
            if anim.endswith("_fbx_url") and url:
                bajar_opcional(url, os.path.join(carpeta, f"{nombre}_{anim.replace('_fbx_url', '')}.fbx"))

    return carpeta


def main():
    ap = argparse.ArgumentParser(description="Meshy → GLB/FBX para el stand")
    ap.add_argument("lista", nargs="?", default=os.path.join(os.path.dirname(__file__), "lista_modelos.json"))
    ap.add_argument("salida", nargs="?", default="modelos_meshy")
    ap.add_argument("--solo", help="hacer sólo el ítem con este nombre")
    ap.add_argument("--probar", action="store_true", help="sin red: valida la lista y muestra los pedidos")
    ap.add_argument("--diagnostico", action="store_true", help="revisa la clave y la conexión con Meshy")
    a = ap.parse_args()
    if a.diagnostico:
        diagnostico()
        return

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
