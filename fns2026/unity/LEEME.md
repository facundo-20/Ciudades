# Parque Triásico en Unity (HDRP)

La versión de máxima calidad: en tiempo real, interactiva y pensada para la sala LED. No es un traspaso de lo de Blender: lo que suma Unity es otra cosa.

- **Sala inmersiva**, como el cubo de la referencia (space&time cube):
  - piso y paredes LED forman una sola ventana al Triásico, vista desde los ojos del visitante;
  - cada superficie tiene su cámara con proyección fuera de eje (Kooima);
  - el ojo sigue al visitante con el Kinect o el LiDAR (`/body/x`).
- **Dinosaurios vivos**: los modelos de Meshy con esqueleto y animaciones (caminar, quieto, pastar u olfatear). En cada capítulo una manada cruza al lado del visitante, a escala real.
- **El Valle de la Luna real** en el capítulo "hoy":
  - relieve de Copernicus de 30 m y color de Sentinel-2 del 26/09/2026;
  - una simulación de erosión que agrega cárcavas a 1 m;
  - el paredón de 280 m de las Barrancas Coloradas, con estratos horizontales.
- **Luz física** con HDRP:
  - sol de 120.000 lux, cielo físico, nubes y niebla volumétricas;
  - río con el sistema de agua, columna del volcán y lluvia de ceniza;
  - en la OMEN con RTX, iluminación global y reflejos por trazado de rayos.

## Cómo se usa

**Windows (OMEN):** doble clic en `CONSTRUIR_Y_PROBAR.bat`.
**Mac M4:** doble clic en `CONSTRUIR_Y_PROBAR_MAC.command`.

El script hace solo:

1. Instala Unity Hub y Unity 6000.3 LTS, si faltan (unos 10 GB).
2. Licencia: la Personal es gratis, pero Unity pide **iniciar sesión una vez** en Unity Hub. Es el único paso a mano, y el script avisa cuándo.
3. Baja las texturas escaneadas CC0 de Poly Haven a 4K, si hay Python. Si no, usa las procedurales de `Datos/suelo`.
4. Unity arma el proyecto entero (`Assets/FNS/Editor/Constructor.cs`) y compila el ejecutable en `Builds/`. La primera vez tarda de 30 a 60 minutos, porque compila los shaders de HDRP.
5. Corre los 6 capítulos en modo capturas y sube las imágenes y el informe a la rama (`pruebas_pc/` o `pruebas_mac/`), para revisarlos desde la nube.

**Lanzadores** (en `Builds/`):

| Archivo | Para qué |
|---|---|
| `PARQUE_PARED_LED.bat` | Pared LED de 5760×1080 |
| `PARQUE_SALA_CUBO.bat` | Sala con piso y tres paredes; lienzo de 3461×2051 con el atlas del piso LED |
| `PARQUE_PRUEBA_VENTANA.bat` | En una ventana, con un visitante simulado |

**Abrirlo a mano:** Unity Hub → Add → `fns2026/unity/ParqueTriasico` → menú **FNS 2026 → Construir todo**.

## Opciones del ejecutable

| Opción | Qué hace |
|---|---|
| `--sala pared` / `--sala cubo` | Usa `StreamingAssets/sala_pared.json` o `sala_cubo.json`. Las medidas se editan ahí, sin recompilar. |
| `--calidad maxima` / `alta` / `media` | `maxima` usa trazado de rayos (si la placa lo tiene). `media` es para la M4 o placas chicas. |
| `--spout NOMBRE` (Windows) / `--syphon NOMBRE` (Mac) | Manda la imagen a TouchDesigner o Resolume Arena. |
| `--osc 7001,10000` | Puertos de los sensores. Los mensajes son los del stand: `/wall/touch/<n>/x\|y\|active`, `/body/x`, `/body/present`, `/touch/u\|v\|down`, `/gesto/<nombre>`. |
| `--simular` | Un visitante inventado, para dejarlo andando sin sensores. |
| `--capitulo N`, `--sin-auto`, `--sin-textos` | Arrancar en un capítulo, no avanzar solo, sin títulos ni fichas. |
| `--capturas CARPETA` | Saca un PNG por capítulo y un `informe.json` con los cuadros por segundo, y se cierra. |

**Teclas:** ← → cambian de capítulo · 0 a 5 van a uno · P simula una persona · H oculta los textos · F11 alterna pantalla completa.

## De dónde sale cada cosa

| Archivo | Qué genera |
|---|---|
| `exportar_mundo.py` | El mundo del Triásico con las mismas fórmulas que el render de Blender: terreno de 512 m a 0,25 m más un lejano de 8 km con el volcán, capas de suelo, 38.000 plantas, cámaras y fauna. |
| `valle_real.py` | El Valle de la Luna real (Copernicus + Sentinel-2 + erosión), el paredón y las piedras. |
| `texturas_suelo.py` | Las texturas PBR procedurales y repetibles: barro, arena, hojarasca de folíolos, arcilla cuarteada, estratos, ripio y basalto. |
| `flora_lod.py` | Los niveles de detalle de la flora, al 30 % y al 8 %. |
| `../pipeline/rig_fauna.py` | El esqueleto y las animaciones de cada animal de Meshy, en `Datos/fauna/`. |

Los modelos de Meshy de la PC (por ejemplo, `Descargas/dinos_triasico`) entran por `Datos/fauna_pc/<especie>/` y reemplazan a los de la web.

**Atribución** (datos abiertos):

- "Copernicus DEM GLO-30 © DLR e.V. 2010-2014 y © Airbus Defence and Space GmbH 2014-2018, provisto bajo COPERNICUS por la Unión Europea y la ESA".
- "Contiene datos modificados de Copernicus Sentinel 2026".

## Qué está probado y qué no

**Probado en la nube:**

- El C# compila (Windows y Mac) contra referencias de UnityEngine/UnityEditor y contra resúmenes de HDRP 17.3, Core RP, KlakSpout y KlakSyphon. Las firmas se copiaron del código fuente real de Unity 6.3 (`verificacion/`).
- Ninguna API usada está obsoleta en 6.3.
- 12 pruebas de lógica pasan:
  - OSC real por UDP;
  - el estado de los sensores, igual al puente de Node;
  - la decodificación de las alturas, idéntica a Python.
- La proyección fuera de eje lleva las esquinas físicas de cada superficie a las esquinas de su imagen, con el visitante en el centro o corrido 2 m.
- Los esqueletos y ciclos de caminar se revisaron en renders de Blender (`Datos/fauna/*/*_caminar.jpg`).

**No probado (no hay Unity ni GPU en la nube):**

- Que el proyecto abra y arme sin errores en la PC. Lo dice el informe que sube el script.
- La calidad final en pantalla y los cuadros por segundo de cada máquina.
- Que los valores de HDRP (exposición, niebla, nubes) queden bien en cada capítulo.
- DLSS: en HDRP 6.3 se configura con la lista de escaladores del asset y no se toca desde el código. Si hace falta más rendimiento en la OMEN, se habilita a mano en el asset de HDRP (Dynamic Resolution → DLSS).

**A validar con un paleontólogo** de la UNSJ o del MuPa:

- los textos de las fichas;
- la anatomía y el andar de cada especie;
- las ubicaciones del Hongo y del Submarino en el valle real. Son aproximadas: no hay coordenadas públicas de cada formación.
