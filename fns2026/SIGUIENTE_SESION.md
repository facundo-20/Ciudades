# Para la próxima sesión

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
