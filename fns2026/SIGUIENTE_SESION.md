# Para la próxima sesión

## PRIMERO (sesión nueva, con `assets.meshy.ai` y `dl.polyhaven.org` habilitados)

1. **Bajar los modelos ya pagos y pasarlos a FBX.**
   ```bash
   pip install bpy numpy pillow
   python3 fns2026/pipeline/correr_todo.py --destino todos --no-abrir
   ```
   - Retoma por `fns2026/modelos_meshy/*/tareas.json`: sólo baja, no paga de nuevo.
   - Incluye Saurosuchus y Exaeretodon.
2. **Maqueta anatómica: mejora pedida por Facu, empezar por Herrerasaurus, Saurosuchus e Ischigualastia.**
   - Blockout en Blender (Skin modifier sobre un esqueleto de puntos) con las medidas publicadas.
   - De ahí salen vistas ortográficas propias.
   - Esas vistas van a Meshy `v1/image-to-image`, que existe (probado el 28/09), para una vista realista que respete la silueta.
   - Después `v1/multi-image-to-3d` → FBX.
   - `v1/retexture` también existe: sirve para texturizar la malla de la maqueta tal cual.
   - Las vistas se validan con un paleontólogo antes de gastar créditos.
3. **Resto:**
   - Texturas CC0 → re-render de los 6 capítulos con los dinosaurios.
   - GLB medios a `experiencia/public/modelos` + `npm run probar`.
   - Script de After: `fns2026/escenas/after_effects/`.

## Estado real al 28/09 (noche)

### Probado y funcionando

- **Meshy responde** con la credencial del entorno. Quedan 1.272 créditos.
- **Los 8 modelos nuevos ya están generados en Meshy:**
  - dinosaurios: Panphagia, Sanjuansaurus, Hyperodapedon, Ischigualastia;
  - plantas: Dicroidium, Neocalamites, helecho, conífera.
  - Detalle en `fns2026/modelos/INFORME.md`.
- **Flora procedural de respaldo:** `construir_triasico.py --solo assets` tarda 3 min en CPU.
- **Render Cycles de los 6 capítulos en calidad prueba.**
  - Las pruebas están en `fns2026/escenas/hiperreal/pruebas/`.
  - **Llanura:** ahora se ve el volcán con la columna de ceniza.
  - **Hoy:** ahora se ve el Valle de la Luna: arcilla cuarteada, barrancas rojas con estratos, cielo limpio y sol alto.

### Bloqueado por la red del entorno (no es código)

Faltan dos dominios en **Network access** del entorno:
- **`assets.meshy.ai`:** Meshy baja de ahí los GLB/FBX y las imágenes. Sin esto, los modelos quedan hechos pero no se pueden bajar.
- **`dl.polyhaven.org`:** Poly Haven baja de ahí las texturas CC0. `api.polyhaven.com` ya anda.

## Qué correr cuando estén los dos dominios

```bash
pip install bpy numpy pillow
python3 fns2026/pipeline/correr_todo.py --destino flora --no-abrir        # retoma: sólo baja
python3 fns2026/pipeline/correr_todo.py --destino dinosaurio --no-abrir   # baja + rig (el rig sí gasta)
python3 fns2026/escenas/hiperreal/bajar_texturas_cc0.py
python3 fns2026/escenas/triasico/construir_triasico.py -- fns2026/escenas/triasico/salida --solo assets
python3 fns2026/escenas/hiperreal/triasico_cycles.py -- /tmp/hiper \
    --assets fns2026/escenas/triasico/salida/assets --modelos fns2026/modelos
```

**Reanudable:** los id de cada tarea de Meshy están en `fns2026/modelos_meshy/*/tareas.json`, versionados en git. Nada se paga dos veces. Las vistas ya hechas se reusan también buscándolas por el prompt.

## Todavía sin probar (depende de los modelos bajados)

- **Dinosaurios de Meshy en el render.** `poner_dinosaurios` los carga desde `modelos/<especie>/<especie>_alto.glb` como instancias de colección. Falta revisar tres cosas:
  - que queden bien de escala y de orientación;
  - que miren para donde deben (el rumbo está en `ESPECIES_LUGARES`);
  - que la manada de Ischigualastia quede en cuadro en la llanura.
- **Web:**
  1. Copiar los GLB `_medio` a `fns2026/experiencia/public/modelos/<especie>.glb` y listarlos en `lista.json`.
  2. Correr `npm install && npm run build && npm run probar`.
- **Vistas previas** de cada modelo: revisar la anatomía (sin plumas, Ischigualastia sin colmillos).

## Mejoras vistas en las pruebas

- **Título:** la cámara aérea mira una loma oscura y deja poco cielo. Se ve un hueco claro en el terreno (el borde del agua, más allá del terreno fino).
- **Ceniza:** en calidad prueba queda plana porque la niebla volumétrica sólo se activa desde `media`.
- **Conífera y Dicroidium procedurales:** muy geométricos. Los de Meshy los reemplazan solos cuando estén bajados.
- **Pase de profundidad:** sigue sin salir en Blender 5.0 (cambió el compositor).

Los binarios no van al repo: se regeneran con los scripts. Van sólo las vistas previas, las pruebas en JPG y los id de tarea.
