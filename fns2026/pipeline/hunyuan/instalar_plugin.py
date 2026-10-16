"""Instala y habilita el plugin oficial de Hunyuan3D-2 en el Blender de esta máquina.

    blender -b --python instalar_plugin.py -- RUTA/hunyuan3d_blender.py

Se corre SIN --factory-startup: así carga las preferencias del usuario y, al guardarlas, sólo suma
el plugin (con --factory-startup se pisarían todas sus preferencias con las de fábrica).
El plugin habla con el servidor local (HUNYUAN_SERVIDOR.bat) en http://localhost:8080, su valor por
defecto: no hay que configurar nada.
"""
import os
import sys

import bpy
import addon_utils  # noqa: E402  (después de bpy: con el bpy de pip recién ahí está en el path)

# el plugin usa "requests": el Python de Blender suele traerlo; si no, se instala en ese Python
try:
    import requests  # noqa: F401
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "ensurepip"], check=False)
    subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "requests"], check=False)
    import site
    import importlib
    importlib.invalidate_caches()
    for ruta in site.getsitepackages() + [site.getusersitepackages()]:
        if ruta not in sys.path:
            sys.path.append(ruta)

archivo = os.path.abspath(sys.argv[sys.argv.index("--") + 1])
modulo = os.path.splitext(os.path.basename(archivo))[0]
bpy.ops.preferences.addon_install(filepath=archivo, overwrite=True)
addon_utils.enable(modulo, default_set=True, persistent=True)
habilitado = modulo in {m.module for m in bpy.context.preferences.addons}
bpy.ops.wm.save_userpref()
print(f"plugin {modulo}: {'habilitado' if habilitado else 'NO se pudo habilitar'} en Blender {bpy.app.version_string}")
sys.exit(0 if habilitado else 1)
