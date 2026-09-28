# Triásico hiperrealista (Blender + Cycles + Meshy)

El mismo mundo y los mismos 6 capítulos de la experiencia web, renderizados con Cycles para usarlos como fondos del LED.

**Cómo se reparte el trabajo:**
- Blender hace la imagen hiperrealista: render offline, no tiempo real.
- TouchDesigner o la web ponen encima la interacción en vivo: dinosaurios que se acercan, huellas y fichas.

## Orden para llegar al hiperrealismo

1. **Modelos de Meshy.**
   - `python3 ../../pipeline/correr_todo.py --destino flora` genera las plantas del Triásico: *Dicroidium*, *Neocalamites*, helecho y conífera.
   - `--destino dinosaurio` genera los animales.
   - El render usa siempre lo mejor que haya: los modelos de Meshy primero y, si no hay, los procedurales.
2. **Texturas escaneadas CC0.**
   - `python3 bajar_texturas_cc0.py` baja de Poly Haven barro, hojarasca, arena, arcilla y roca.
   - Hay que tener habilitados `api.polyhaven.com` y `dl.polyhaven.org`.
3. **Flora procedural de respaldo:** `python3 ../triasico/construir_triasico.py -- ../triasico/salida`.
4. **Render en la M4 (Metal) o en las OMEN (OptiX):**
   ```bash
   FNS_GPU=1 blender -b --factory-startup -P triasico_cycles.py -- render --calidad media
   FNS_GPU=1 blender -b --factory-startup -P triasico_cycles.py -- render --calidad led --animar --segundos 10
   ```
   - La calidad `led` sale a 5760×1080, las 3 pantallas.
   - `--animar` renderiza el recorrido de cámara de cada capítulo como secuencia de cuadros para el LED.

## Qué tiene

- Cielo físico con dispersión múltiple y sol del tamaño real.
- Niebla volumétrica: está desde `media` para arriba; en `prueba` se apaga porque es cara.
- Terreno con máscaras de hábitat: barro, charcos que reflejan, barras de arena y hojarasca.
- Agua con transmisión, IOR 1,33 y absorción volumétrica: el color del río turbio sale de la profundidad.
- Volcán con columna de ceniza volumétrica.
- Anillo de horizonte de 3 km.
- Vegetación por instancias con Geometry Nodes: unas 4.000 plantas por capítulo en la calidad de prueba.
- Cámara de 35 mm a 1,7 m de altura, con profundidad de campo real (f/4, foco a 12 m).
- Lugares marcados `SLOT_<especie>`, donde entran los dinosaurios de Meshy o los de la Mac.

## Estado (28/09, noche)

**Pruebas** (`pruebas/`, 960×540, 24 muestras, CPU en la nube, unos 50 s por cuadro): los 6 capítulos.

**Arreglado:**
- **Llanura:**
  - se abrió una quebrada en el cordón que tapaba el volcán;
  - la cámara quedó a la altura de los ojos junto a la manada;
  - la columna de ceniza no se veía porque la cámara cortaba a 1.000 m; ahora corta a 8 km.
- **Hoy:**
  - arcilla gris clara con grietas oscuras y manchas verdosas y ocres;
  - barrancas rojas con estratos y detrito al pie;
  - cielo sin aerosoles, sol alto y fuerte;
  - no hay animales ni plantas del Triásico, sólo piedras sueltas.
- **Dinosaurios:** entran como instancias de una colección. Así viaja entero el modelo con rig; antes se copiaba sólo la raíz y se perdía la malla.

**Pendiente:** ver `fns2026/SIGUIENTE_SESION.md`.
- Los modelos de Meshy están hechos pero no se pueden bajar: falta habilitar `assets.meshy.ai`.
- Las texturas CC0 tampoco se pueden bajar: falta habilitar `dl.polyhaven.org`.
- El pase de profundidad.
- Los renders finales en GPU.

**Errores encontrados y corregidos:**
- Al crear un atributo nuevo, las rotaciones se escribían encima de las posiciones: todas las plantas terminaban en el origen.
- El sol estaba duplicado (el disco del cielo más la lámpara) y quemaba la imagen.
- Una descarga cortada de Poly Haven dejaba un `.jpg` vacío, y el suelo salía magenta. Ahora primero se baja y después se escribe.
