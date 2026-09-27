# Conectar las herramientas

Hay dos lugares donde trabaja Claude, y cada uno tiene sus conexiones:

**1. Esta sesión en la nube (claude.ai/code).** Corre en un contenedor, no en tus máquinas.
- **Ya conectados:** Higgsfield (imagen, video, imagen a 3D con rig, upscale), Adobe (imágenes, stock con licencia, fuentes, PDF) y Canva.
- **Blender:** corre acá en modo consola (`pip install bpy`, versión 5.0.1). Así se probó la cañería.
- **Meshy:** bloqueado. Hacen falta dos cosas:
  1. Agregar `api.meshy.ai` a los dominios permitidos. En el menú del entorno, en la barra de título de la sesión: **Editar → Network access**.
  2. Cargar tu clave como variable del entorno `MESHY_API_KEY`, en la misma pantalla, en la sección de variables. Nunca en el chat ni en el repo.
- **No se puede desde la nube:** After Effects, Illustrator, Premiere, DaVinci y TouchDesigner, porque son apps de escritorio. Se controlan con Claude Code o Claude Desktop **en tu Mac o en las OMEN** (punto 2).

**2. Claude Code o Desktop en tus máquinas.** Conectores MCP locales a instalar.
Son de la comunidad: revisá cada repo antes de instalarlo (regla de tu skill). Los nombres de los repos están **a verificar**: no los pude chequear desde acá.

| App | Conector | Máquina |
|---|---|---|
| Blender | `blender-mcp` (addon + servidor) | Mac M4 y OMEN i7 |
| TouchDesigner | `touchdesigner-mcp` (ya lo tenés en `C:\Users\Facundo\mcp-servers\touchdesigner-mcp`: falta importar `mcp_webserver_base.tox`) | OMEN i7 |
| Resolume Arena | REST API propia de Arena (Preferences → Webserver) + OSC. Tu skill ya lo usa | Mac M4 |
| DaVinci Resolve | API de scripting de Python (`DaVinciResolveScript`), en Studio. Hay MCP de la comunidad que la envuelven | Mac M4 |
| After Effects / Premiere / Illustrator | Scripting ExtendScript/UXP por terminal. Hay MCP de la comunidad para AE. Premiere: reiniciar una vez para el panel CEP (pendiente de tu skill) | Mac M4 |
| Meshy | Por API con `meshy_a_fbx.py`, sin MCP: son llamadas HTTP y un script es más confiable que un conector | cualquiera |

## Correr la cañería en tus máquinas

```bash
# Mac M4
export MESHY_API_KEY=...                  # tu clave de meshy.ai → API
python3 fns2026/pipeline/meshy_a_fbx.py fns2026/pipeline/lista_modelos.json fns2026/modelos_meshy --solo herrerasaurus
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
  -P fns2026/pipeline/blender_refinar.py -- \
  fns2026/modelos_meshy/herrerasaurus/herrerasaurus_rig.fbx fns2026/modelos/herrerasaurus --largo 4.0
```

```bat
:: OMEN (Windows)
set MESHY_API_KEY=...
python fns2026\pipeline\meshy_a_fbx.py fns2026\pipeline\lista_modelos.json fns2026\modelos_meshy --solo herrerasaurus
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b --factory-startup -P fns2026\pipeline\blender_refinar.py -- fns2026\modelos_meshy\herrerasaurus\herrerasaurus_rig.fbx fns2026\modelos\herrerasaurus --largo 4.0
```

Autotest de la cañería, sin Meshy: `python3 fns2026/pipeline/test_pipeline.py` (con `pip install bpy`, o dentro de Blender con `-P`).
