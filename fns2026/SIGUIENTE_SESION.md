# Para la próxima sesión

## Estado real (09/10/2026)

### Unity HDRP (nuevo, `fns2026/unity/`; ver `unity/LEEME.md`)

- **Qué es:** la versión de máxima calidad en tiempo real, pedida por Facu ("si tenés que hacerlo en Unity para que sea realismo, hacelo"). Referencia: el video del space&time cube, con piso y paredes LED, dinosaurios a escala que pasan pegados y avance por el paisaje.
- **Hecho y probado en la nube:**
  - El proyecto Unity 6000.3 LTS (HDRP 17.3) está escrito: sala inmersiva fuera de eje (pared 5760×1080 o cubo piso + 3 paredes), sensores OSC, director de capítulos, ambiente HDRP, vegetación instanciada, fauna con Animator y encuentros, textos, perfiles de calidad, modo capturas y constructor en batchmode.
  - Compila contra referencias de Unity y resúmenes de HDRP verificados en el código fuente (`unity/verificacion/`). Ninguna API obsoleta en 6.3.
  - Pasan las 12 pruebas de lógica y la de proyección fuera de eje.
  - **El Valle de la Luna real** (`valle_real.py`): DEM Copernicus de 30 m, color de Sentinel-2 del 26/09 y erosión de 4 millones de gotas. Vista de control en `unity/verificacion/vista_valle_hoy.jpg`.
  - **Esqueleto y animaciones** de los 6 animales de la web (`pipeline/rig_fauna.py`): caminar, quieto y pastar u olfatear. Tiras de control en `unity/ParqueTriasico/Datos/fauna/*/`.
- **NO probado:** que Unity abra, arme y compile en la PC, y la calidad en pantalla. Lo dice el informe que sube `CONSTRUIR_Y_PROBAR.bat` a `unity/pruebas_pc/`.
- **Pendiente:**
  1. Que Facu corra `fns2026\unity\CONSTRUIR_Y_PROBAR.bat`. Tiene que iniciar sesión una vez en Unity Hub por la licencia Personal.
  2. Leer `unity/pruebas_pc/<fecha>/` (informe, errores y capturas) y corregir.
  3. **Dinos de Meshy de la PC**: están en `Descargas\dinos_triasico` (7 GLB de 30 MB: Chromogisaurus, Eodromaeus, Panphagia, Pisanosaurus, Sanjuansaurus, Teropodo_grande, Dino_extra) más 2 Herrerasaurus. El trabajo 009 del puente los copia a `modelos_mac/pc/`. Después: `rig_fauna.py` sobre esos modelos → `Datos/fauna_pc/<especie>/`, que el constructor usa antes que los de la web.
  4. En la PC hay un proyecto `Documents\ValleLunaUnity` (de hoy) con esos dinos en FBX. La lista de archivos llega con el 009: revisar si conviene sumar algo.
- **Privacidad:** el repo es PÚBLICO. Las fotos personales de la PC NO van por el puente. Facu elige: pasar el repo a privado o subir las referencias a una carpeta de Drive "FNS2026 referencias".


## Estado real (28/09, madrugada)

### Probado y funcionando

- **Meshy:** 19 modelos bajados y refinados a escala real. Detalle en `fns2026/modelos/INFORME.md`. Quedan 882 créditos.
- **Triásico, los 6 capítulos en Cycles** con la flora y la fauna de Meshy (`escenas/hiperreal/pruebas/`):
  - la llanura con la manada de *Ischigualastia* rumbo al volcán en erupción;
  - "hoy" con el Valle de la Luna.
- **Recorrido por San Juan:** 7 postales (`escenas/sanjuan/pruebas/`).
  - El *Sanjuansaurus* muestra El Hongo, la Cancha de Bochas, el Cerro Alcázar, la Pampa El Leoncito, Cuesta del Viento, la Catedral y el Teatro del Bicentenario.
- **Web:** 6 especies de Meshy a escala real. `npm run probar` da **todo OK**.
- **Calidad media** (1920×1080, 128 muestras, niebla volumétrica): unos 4–5 min por cuadro en CPU. Se renderizaron en `/tmp/media` y las JPG van a `pruebas_media/`.

### Armado pero todavía sin probar del lado de After

- **Puente de After Effects por git** (`fns2026/ae_puente/`):
  - Facu corre `node fns2026\ae_puente\puente_ae.mjs` en su PC, desde un clon del repo (`Documents\Ciudades_puente`).
  - La sesión en la nube deja trabajos `.jsx` en `cola/` y recibe resultado y capturas en `hechos/`.
- **Trabajos esperando en la cola:**
  - `001_hola`: versión, fuentes y plugins;
  - `002_parque_triasico`: la pieza del LED;
  - `003_recorrido_san_juan`: las 7 postales.
- **Cómo ver si conectó:** aparece `hechos/_puente_vivo.json`.

## Qué sigue

1. **Con el puente vivo:** leer `hechos/001_hola.json` (plugins que hay), revisar las capturas de 002 y 003 y corregir con trabajos nuevos. Facu quiere retocar todo en After.
2. **Renders LED** (5760×1080) en GPU en la M4 o las OMEN:
   ```bash
   FNS_GPU=1 blender -b --factory-startup -P triasico_cycles.py -- render --calidad led --animar
   ```
   Hace lo mismo `postales_sanjuan.py --calidad led`.
3. **Mejoras vistas:**
   - **Modelos a medida:** Teatro del Bicentenario y nave de la Catedral son bloques simples → Meshy o modelado a medida.
   - **Modelos de Meshy a corregir:** el cráneo de *Saurosuchus* es más chato que el real y la cola de *Exaeretodon* es larga de más → rehacer con maqueta anatómica, si se aprueba el gasto.
   - **Ceniza:** plana en calidad prueba; con niebla (media/led) y la ceniza de After cambia.
   - **Pase de profundidad:** sigue sin salir en Blender 5.0.
4. **Pendientes de red:** `dl.polyhaven.org` sigue bloqueado (texturas CC0); el suelo es procedural.
5. **Validación:** con un paleontólogo (UNSJ o MuPa) de textos, anatomía y medidas marcadas **[a confirmar]**.
