# Arquitectura · Parque Triásico con TouchDesigner + Resolume Arena

Qué decidió Facu (27/09):
1. **Todo por TouchDesigner y Arena.** La app web del piso se retira del show. Sus juegos pasan a Python dentro de TD, con el mismo contrato (`update`, `estado`, `instancias`, `reset`, `accion`).
2. **Sin Cesium.** Nada de 3D de Google: todos los modelos son propios. Se generan con **Meshy**, se terminan en **Blender** y se usan como **FBX** en TD.
3. **Herramientas de contenido:** Blender, Meshy, Higgsfield, After Effects, Illustrator, Premiere y DaVinci Resolve.
4. **Máquinas:** Mac M4, HP OMEN i7 y HP OMEN i5.

Lo que **no** cambia: **el tracker sigue afuera de los motores gráficos** (MANUAL, punto 2). Manda OSC y TUIO, y TD lo toma igual que antes. Es lo que permite probar la lógica sin sensores ni pantallas.

---

## 1. Cadena de señal

```
LiDAR (RPLIDAR/Hokuyo) ─┐
Kinect 360 ─────────────┤                 ┌──────────── OMEN i7 · TouchDesigner ────────────┐
Cámara cenital (pose) ──┼─► TRACKER ─OSC─►│ juegos_td.py (Excavación, 7 del amanecer...)    │
PTZ (VISCA) ◄───────────┘   (OMEN i5)     │ FBX COMP: Herrerasaurus riggeado                │
                                          │ instancing: arena + huesos (OBJ de Blender)     │
                                          └──┬───────────────┬──────────────────────────────┘
                                             │ Window COMP   │ NDI "TD_FNS_Paredes"
                                             ▼ (directo)     ▼
                                    Novastar PISO    ┌──────── Mac M4 · Resolume Arena ─────────┐
                                                     │ capas: loops DXV3 + TD en vivo + overlays │
                                    OSC eventos ────►│ Advanced Output: paredes rectas + curvas  │
                                                     └──────────────┬────────────────────────────┘
                                                                    ▼
                                                          Novastar PAREDES / CURVAS
```

**Por qué el piso no pasa por Arena.** El RPLIDAR gira a 10 Hz y solo con eso la cadena ya está en unos 115 ms. Llevar el piso por NDI hasta Arena suma 2 a 4 cuadros, y se pasa el umbral de 150 ms del MANUAL: la gente pisa, no pasa nada y pisa más fuerte. **El piso sale directo desde TD** con un Window COMP, igual que antes salía directo del navegador. A Arena llegan los **eventos** del piso (hueso descubierto, ronda completa) por OSC, no los píxeles.

## 2. Qué hace cada máquina

| Máquina | Rol | Por qué esa |
|---|---|---|
| **HP OMEN i7** (Windows, placa NVIDIA) | **TouchDesigner**: piso, dinosaurio 1:1 riggeado, sala triásica. Kinect 360 | Es la más potente en GPU para el render en vivo. **El Kinect 360 sólo tiene drivers en Windows** (SDK 1.8): en la Mac no anda. Spout nativo |
| **Mac M4** | **Resolume Arena**: mezcla, cues, mapping de paredes rectas y curvas con Advanced Output. Contenido: After Effects, DaVinci, Illustrator, Premiere. Render de Blender con Metal | Arena y DXV3 andan muy bien en Apple Silicon. La M4 es silenciosa y estable para estar toda la noche. Es la máquina de producción de contenido antes de la fiesta |
| **HP OMEN i5** (Windows) | **Tracker** lidarwall (LiDAR, cámara cenital con pose), control de la PTZ, servidor de fotos QR, Stream Deck | Al tracker le sobra CPU (0,6 % de un núcleo). La pose con MoveNet en CPU o DirectML entra holgada. Así, si se cuelga la IA, no arrastra al render |

**Entre máquinas:**
- Todo por **NDI** en la misma red cableada gigabit. Spout y Syphon sólo sirven dentro de una misma máquina.
- **Syphon es de Mac y Spout es de Windows.** El `Syphon Spout Out TOP` de TD elige solo según el sistema, así que el mismo `.toe` abre en las dos.
- OSC por la misma red: tracker (OMEN i5) → TD (OMEN i7, puerto 7001) → Arena (Mac, puerto 7000). La Stream Deck se conecta al tracker, puerto 7400, y el tracker reparte los cues.

**Datos a confirmar:** el modelo exacto de placa de video de cada OMEN (RTX 3060, 4060, 4070...) y la RAM. Cambia cuántos dinosaurios riggeados entran a la vez y qué nivel de detalle se usa: `alto` en la i7 y `medio` si la i5 tiene que renderizar.

## 3. Arena · cómo se arma la composición

| Capa | Qué | Fuente |
|---|---|---|
| 1 · Fondo | Valle de Ischigualasto en loop (atardecer → Triásico) | DXV3, de Blender o Higgsfield + After Effects |
| 2 · Vivo | Las paredes de TD (dinosaurio 1:1, sala) | NDI `TD_FNS_Paredes` |
| 3 · Eventos | Esqueleto que se arma, rugido, estela del Herrerasaurus cruzando pantallas | DXV3 con alfa, de After Effects o Blender |
| 4 · Info | Fichas científicas, logos del Ministerio y del MuPa, QR | After Effects o Illustrator, DXV3 con alfa |

- **Columnas = momentos del show:** `tarde (atractor)`, `noche`, `recital`, `institucional` (cuando pasa una autoridad) y `cierre` (el mosaico-esqueleto).
- **OSC que manda TD a Arena** (ya está en `construir_red_fns.py`):
  - `/composition/dashboard/link1`: progreso de la excavación, de 0 a 1. Sirve para mapear la opacidad del esqueleto en la pared.
  - Al completar una ronda, el clip del parámetro `Clipcompleto` (por defecto `/composition/layers/2/clips/2/connect`).
  - `/fns/hueso i`, `/fns/completo`, `/fns/bloque`: para otros patches.
- **Advanced Output:** un slice por gabinete de las curvas; soft edge si hay solape; máscara vectorial desde **Illustrator** (SVG o PNG) para los bordes de los LED curvos.

## 4. Cañería de contenido: qué herramienta hace qué

| Paso | Herramienta | Qué sale | En |
|---|---|---|---|
| 1. Vistas del animal (frente, perfil, dorso, 3/4) | **Meshy**, texto a imagen multi-vista | 4 PNG por animal | `pipeline/meshy_a_fbx.py` |
| 2. Modelo 3D a partir de las vistas | **Meshy**, multi-imagen a 3D, quads, PBR | GLB/FBX de unos 60.000 polígonos | ídem |
| 3. Rig + caminar y correr | **Meshy**, rigging | FBX riggeado + animaciones | ídem |
| 4. Terminar el modelo | **Blender** | escala real, apoyado en z=0, limpio, niveles alto/medio/bajo, texturas a 2K, **FBX** para TD, GLB y OBJ para instancing, vista previa, informe | `pipeline/blender_refinar.py` |
| 5. Huesos del piso y efectos | **Blender** (Cycles) | hojas de sprites (`polvo_arenisca`, `huella_teropodo`, `hueso_emerge`, `rugido`) con la cañería de INTEGRAR | `animaciones_piso.py` |
| 6. Fondos, cielos, texturas de roca | **Higgsfield** (imagen y video; `upscale_video`). Si Meshy falla con un animal, Higgsfield también hace imagen a 3D con rig | loops de fondo | conector activo en esta sesión |
| 7. Fichas, títulos, rugido, esqueleto que se arma | **After Effects** | ProRes 4444 con alfa | Mac M4 |
| 8. Logos, máscaras de slices, señalética, QR | **Illustrator** | SVG/PNG | Mac M4 |
| 9. Color de todos los loops | **DaVinci Resolve** | ProRes 4444 igualado a la paleta de Ischigualasto | Mac M4 |
| 10. Codec final | **Resolume Alley** | **DXV3** para Arena y **HAP** para TD | Mac o OMEN |
| 11. Spot y presentación en video para el Ministerio | **Premiere** | MP4 H.264 | Mac M4 |

**La regla del codec (MANUAL, punto 9):** nada en H.264 dentro del show. DaVinci no exporta DXV3, así que la entrega es ProRes 4444 y **Alley** lo convierte. TD lee HAP en las dos plataformas.

**Blender en cada máquina:**
- Mac M4: Cycles con **Metal**.
- OMEN: Cycles con **OptiX**.
- `blender_refinar.py` usa Cycles por CPU **sólo para la vista previa**, así anda igual en las tres máquinas y en el modo sin pantalla (`-b`).

## 5. El dinosaurio "con IA interactiva" en TD

El FBX riggeado que sale del paso 4 entra a TD con un **FBX COMP**. Lo que lo hace interactivo no es una IA dentro del modelo: es **qué hueso mueve cada señal**.

| Señal | Del tracker o la cámara | Qué mueve en el FBX |
|---|---|---|
| Posición de la persona frente a la pared | LiDAR `/wall/touch` o zona | La cabeza del Herrerasaurus la sigue (hueso `cuello` y `cabeza`, con lag CHOP) |
| `brazos_arriba` | Pose (IA fase 2) | Clip `rugir`: mezcla de animaciones en el FBX COMP |
| `salto` | Pose | Pisotón: clip `pisar` + onda en el piso (atlas, nace en el piso) |
| Caminar en el lugar | Kinect o pose | Clip `caminar`, con la velocidad según la cadencia |
| `quieto` 2 s | Pose | El dinosaurio se acerca a "olerte" |
| Nadie durante 25 s | Tracker | Modo atractor: pasea solo |

**Modelo de pose:** **MoveNet** o **RTMPose** (Apache 2.0), **no YOLOv8** (AGPL). Un contrato con el Gobierno es uso comercial.

## 6. Qué pasa con lo que ya estaba

| Pieza | Queda / cambia |
|---|---|
| Tracker lidarwall | **Queda igual.** TD lo lee por OSC en el puerto 7001 |
| App web del piso (`index.html`, Pixi, Matter) | **Sale del show.** Sus juegos pasan a `td/juegos_td.py`, que ya tiene el primero, Excavación, con 4 modos previstos y 3 hechos |
| `bridge.py` | Sólo para las fotos QR (`/subir`) y la cámara con pose, como proceso aparte en la OMEN i5 |
| `stand.html` (Cesium, 3D de Google) | **Se va.** También el visor de Buenos Aires del repo: no entra en el proyecto |
| `stand_maquetas.html` (three.js) | Las maquetas `.glb` pasan por `blender_refinar.py` → FBX → TD. El "mallado dorado que aparece antes que la textura" se hace en TD con un GLSL MAT (umbral por altura) |
| Hojas de sprites de Blender | En TD: Movie File In con el PNG de la hoja + GLSL que elige el cuadro. En Arena: se convierten a DXV3 con alfa |

## 7. Qué está probado y qué no

**Probado (en este repo, sin hardware):**
- `td/juegos_td.py`: 9 autotests. Excavación descubre sólo donde se pisa, completa, reinicia; la arena no se escapa; zonda es un bucle; hallazgo rompe el bloque. Cuesta **1,5 ms por cuadro** con 3.000 granos y 6 personas.
- El módulo `motor` de `construir_red_fns.py` corre con simulaciones mínimas de TD: en demo completa la ronda y manda los OSC a Arena.
- `pipeline/blender_refinar.py`, con Blender 5.0.1 en modo consola: 10 chequeos de punta a punta.
  - Modelo estático: escala real, apoyado en z=0, textura adentro del FBX, OBJ para instancing, tope de triángulos.
  - Modelo con rig: 4,000 m exactos, centrado, apoyado, **la animación deforma la malla después de exportar**. Esto destapó y arregló un problema real: el FBX importado traía cuadros clave del objeto que devolvían al dinosaurio a su escala original.
- `pipeline/meshy_a_fbx.py --probar`: arma los 10 pedidos de la lista sin red.

**No probado:**
- **La API real de Meshy.** Desde esta sesión no hay salida a `api.meshy.ai` y falta la clave. Los campos siguen la documentación pública. Si alguno cambió, Meshy devuelve el error textual y se corrige en `PEDIDOS`.
- **`construir_red_fns.py` dentro de TouchDesigner.** Se escribió sin TD a mano. Cada parámetro va en un `try` y al final lista los pendientes, como tus otros `td_*.py`.
- Latencias reales, FPS en las OMEN y la M4, y el Kinect 360 con TD 2025 (hay que confirmar que el Kinect TOP todavía soporta el v1).
- Las MCP locales (Blender, After Effects, DaVinci, TouchDesigner, Meshy) se instalan en tus máquinas, no en esta sesión en la nube (ver `pipeline/CONECTAR.md`).
