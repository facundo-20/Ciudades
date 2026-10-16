"""
Kernel de Kaggle (GPU gratis: T4 o P100, ~30 h por semana): hornea capítulos del Triásico en
Gaussian splats sin necesitar la PC de Facu. Lo sube y lo maneja hornear_en_kaggle.sh.

En la máquina de Kaggle:
  1. clona la rama del proyecto (el repo es público)
  2. baja Blender 5.0.1 para Linux y renderiza las vistas con Cycles en la GPU (CUDA)
  3. entrena cada splat con gsplat (Apache-2.0)
  4. lo poda con las mismas reglas que en la PC (sin suelo, sin flotantes)
  5. deja <capitulo>.ply y <capitulo>.json en /kaggle/working/salida (los baja el lanzador)

Una sesión de Kaggle dura hasta 12 h: con calidad "final" entran 2 o 3 capítulos.
"""
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

# --- lo completa hornear_en_kaggle.sh antes de subirlo -------------------------------------
CONFIG = {"capitulos": ["bosque"], "calidad": "final", "pasos": 30000,
          "rama": "claude/fiesta-sol-2026-immersive-ph9915", "repo": "https://github.com/facundo-20/Ciudades"}
# --------------------------------------------------------------------------------------------

TRABAJO = "/kaggle/temp" if os.path.isdir("/kaggle") else "/tmp/kaggle_prueba"
SALIDA = "/kaggle/working/salida" if os.path.isdir("/kaggle") else "/tmp/kaggle_prueba/salida"
BLENDER_URL = "https://download.blender.org/release/Blender5.0/blender-5.0.1-linux-x64.tar.xz"


def correr(cmd, **kw):
    print("$ " + " ".join(map(str, cmd)), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, **kw)


def main():
    t0 = time.time()
    os.makedirs(TRABAJO, exist_ok=True)
    os.makedirs(SALIDA, exist_ok=True)
    repo = os.path.join(TRABAJO, "Ciudades")
    if not os.path.isdir(repo):
        correr(["git", "clone", "--depth", "1", "-b", CONFIG["rama"], CONFIG["repo"], repo])
    splats = os.path.join(repo, "fns2026", "pipeline", "splats")

    blender = os.path.join(TRABAJO, "blender-5.0.1-linux-x64", "blender")
    if not os.path.exists(blender):
        tar = os.path.join(TRABAJO, "blender.tar.xz")
        print(f"bajando Blender: {BLENDER_URL}", flush=True)
        urllib.request.urlretrieve(BLENDER_URL, tar)
        with tarfile.open(tar) as t:
            t.extractall(TRABAJO)
        os.remove(tar)

    # gsplat compila su parte de CUDA la primera vez que se usa (unos minutos)
    correr([sys.executable, "-m", "pip", "install", "-q", "gsplat==1.5.3", "pillow"])
    subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"])

    informe = []
    entorno = dict(os.environ, FNS_GPU="1")
    for cap in CONFIG["capitulos"]:
        tc = time.time()
        vistas = os.path.join(TRABAJO, "vistas")
        if not os.path.exists(os.path.join(vistas, cap, "transforms.json")):
            correr([blender, "-b", "--factory-startup", "-P", os.path.join(splats, "vistas_blender.py"), "--",
                    vistas, "--capitulo", cap, "--calidad", CONFIG["calidad"]], env=entorno)
        crudo = os.path.join(TRABAJO, f"{cap}_crudo.ply")
        correr([sys.executable, os.path.join(splats, "entrenar_gsplat.py"), os.path.join(vistas, cap), crudo,
                "--pasos", CONFIG["pasos"]])
        # la poda necesita las fórmulas del terreno (mathutils): con el Python de Blender
        correr([blender, "-b", "--factory-startup", "-P", os.path.join(splats, "podar_splat.py"), "--",
                crudo, os.path.join(SALIDA, f"{cap}.ply"), "--region", os.path.join(vistas, cap, "region.json")])
        region = json.load(open(os.path.join(vistas, cap, "region.json"), encoding="utf-8"))
        json.dump(dict(region, capitulo=cap, entrenado_en="Kaggle (gsplat)"),
                  open(os.path.join(SALIDA, f"{cap}.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        informe.append({"capitulo": cap, "minutos": round((time.time() - tc) / 60, 1),
                        "mb": round(os.path.getsize(os.path.join(SALIDA, f"{cap}.ply")) / 1048576, 1)})
        print(f"== {cap} listo en {informe[-1]['minutos']} min", flush=True)
        shutil.rmtree(os.path.join(vistas, cap), ignore_errors=True)       # /kaggle/temp tiene lugar limitado
    json.dump({"capitulos": informe, "horas": round((time.time() - t0) / 3600, 2), "config": CONFIG},
              open(os.path.join(SALIDA, "informe_kaggle.json"), "w"), indent=1)
    print("listo:", informe, flush=True)


if __name__ == "__main__":
    main()
