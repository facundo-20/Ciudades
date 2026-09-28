"""
Copia los dinosaurios refinados (nivel medio) a la experiencia web y arma su lista.json.

    python3 fns2026/pipeline/modelos_a_web.py

Por qué el nivel medio: el alto (60.000 triángulos, texturas 2K) es para Blender y el LED;
en el navegador, con 30 animales en pantalla, el medio mantiene los 60 fps en la OMEN i5.
Sólo entran las especies que la web conoce (ESPECIES en src/fauna.js); el resto se avisa.
"""

import json
import os
import re
import shutil

AQUI = os.path.dirname(os.path.abspath(__file__))
FNS = os.path.dirname(AQUI)
MODELOS = os.path.join(FNS, "modelos")
WEB = os.path.join(FNS, "experiencia", "public", "modelos")
FAUNA = os.path.join(FNS, "experiencia", "src", "fauna.js")
TOPE_MB = 15          # arriba de esto no va a git ni a la web


def especies_web():
    texto = open(FAUNA, encoding="utf-8").read()
    bloque = texto[texto.index("export const ESPECIES"):]
    bloque = bloque[:bloque.index("\n};")]
    return re.findall(r"^  ([a-z_]+): \{", bloque, re.M)


def main():
    os.makedirs(WEB, exist_ok=True)
    conocidas = especies_web()
    puestas = []
    for especie in conocidas:
        glb = os.path.join(MODELOS, especie, f"{especie}_medio.glb")
        if not os.path.exists(glb):
            continue
        mb = os.path.getsize(glb) / 1e6
        if mb > TOPE_MB:
            print(f"  {especie}: {mb:.1f} MB, pasa el tope de {TOPE_MB} MB; no se copia")
            continue
        shutil.copyfile(glb, os.path.join(WEB, f"{especie}.glb"))
        puestas.append(especie)
        print(f"  {especie}: {mb:.1f} MB")
    for d in sorted(os.listdir(MODELOS)) if os.path.isdir(MODELOS) else []:
        if os.path.isdir(os.path.join(MODELOS, d)) and d not in conocidas and not d.endswith("_meshy") \
                and os.path.exists(os.path.join(MODELOS, d, f"{d}_medio.glb")):
            print(f"  {d}: hay modelo pero la web no tiene la especie (agregarla en ESPECIES de fauna.js)")
    with open(os.path.join(WEB, "lista.json"), "w", encoding="utf-8") as f:
        json.dump(puestas, f)
    print(f"lista.json: {puestas}")


if __name__ == "__main__":
    main()
