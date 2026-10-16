# Gaussian Splatting: la luz de Cycles, en vivo

Cycles calcula la luz completa: rebotes, sombras suaves y hojas translúcidas. Pero tarda minutos por cuadro.

Un **Gaussian splat** entrenado con cientos de renders de Cycles se ve casi igual y se dibuja en tiempo real:

- en Unity HDRP, con UnityGaussianSplatting;
- en la web, con Spark;
- en Blender 5.3, que ya los importa y renderiza de forma nativa.

Este pipeline hornea así la flora de cada capítulo del Triásico.

## Uso: un doble clic

| Máquina | Archivo | Qué usa |
|---|---|---|
| OMEN (RTX) | `ENTRENAR_SPLATS.bat` | Cycles con OptiX y Brush |
| Mac M4 | `ENTRENAR_SPLATS.command` | Cycles con Metal y Brush |

El lanzador:

1. Busca Blender (en Windows lo instala con winget si falta).
2. Baja Brush v0.3.0 y verifica su suma SHA-256.
3. Hornea los capítulos `titulo`, `rio`, `bosque`, `llanura` y `ceniza`.

Para cada capítulo:

1. **Vistas** (`vistas_blender.py`): 400 renders de 1600×900 desde donde puede estar el visitante (sobre el recorrido, a 0,5–2,8 m, mirando a cualquier lado y también al piso LED), más vistas desde afuera.
2. **Entrenamiento** con Brush: 30.000 pasos.
3. **Poda** (`podar_splat.py`): se van el suelo (lo dibuja el terreno de HDRP, que recibe sombras, pisadas y ceniza), lo que está bajo tierra, lo lejano, lo casi transparente y los flotantes.
4. **Entrega**:
   - Unity: `unity/ParqueTriasico/Datos/splats/<capitulo>.ply` + `.json`.
   - Web: `experiencia/public/splats/<capitulo>.sog` + `lista.json`. Hace falta Node.

Al final sube a la rama lo liviano: los `.sog`, la lista, los `.json` y el informe. Los `.ply` quedan en la PC, porque pesan cientos de MB y Unity se compila en la misma máquina.

**Tiempos:** tarda horas, así que conviene dejarlo de noche. Se puede cortar y volver a correr, porque lo que ya está hecho se saltea.

**Opciones** (se agregan al lanzador):

- `--capitulos bosque rio`
- `--calidad media`: 240 vistas de 1280×720, más rápido.
- `--pasos 15000`
- `--sin-web`

## Cómo conviven con lo demás

**En Unity** (`Assets/FNS/Runtime/Splats.cs`):

- Se dibujan después del posproceso, porque ya traen el look de Cycles. Antes del posproceso, la exposición automática de HDRP los quemaba o los apagaba.
- Se tapan con lo opaco: un dinosaurio delante de un helecho horneado lo tapa, y uno detrás queda tapado.
- Donde hay splat, la vegetación de mallas no se dibuja, para no repetir plantas.
- El fundido entre capítulos baja su opacidad.
- `--sin-splats` los apaga, para comparar o si una máquina no da.

**En la web** (`src/splats.js`): igual. Spark (unos 2 MB) se baja solo si hay splats. `?splats=0` los apaga.

**Ejes:** el splat queda en el mundo de Blender (z arriba).

- Unity = (x, z, y) de Blender: rotación (-90, 0, 0) y escala (1, -1, 1).
- Web = (x, z, -y): el `.sog` ya sale girado.

## Capturas reales (el Valle de la Luna de verdad)

Fotos o un video del Hongo, del Submarino o de las Barrancas:

1. Pasan por COLMAP o GLOMAP y se entrenan con Brush (`brush_app CARPETA_COLMAP`). Las fotos no salen de la PC.
2. `importar_en_blender.py` las trae a Blender:
   - con 5.3 o más nuevo, como splat nativo;
   - antes, como vista previa de puntos.
3. Con `--terreno` se suma el valle real de referencia, para apoyar la captura a mano.
4. `blender ESCENA.blend -b -P importar_en_blender.py -- --exportar` escribe dónde quedó: `Datos/splats/<nombre>.json` para Unity (posición, cuaternión, escala) y la ubicación para la web.

No usar "Apply Transform" sobre un splat. En Blender 5.3 todavía arruina la escala, la rotación y los armónicos de cada gaussiana (está en las notas de la versión). Se guarda la transformación del objeto, que es lo que leen Unity y la web.

## Probado en la nube

- **Convención de cámaras** (`prueba_convencion.py`): una esfera roja vista desde cámaras al azar cae donde predice `transforms.json`, con un error menor a 0,1 px.
- **Bosque de punta a punta**, en chico: 48 vistas de 320×180 y 2500 pasos, en CPU con un Vulkan por software.
  - Brush llegó a 25,3 dB de PSNR en vistas que no vio, y la estructura del bosque cae en su lugar.
  - Se ve borroso, como corresponde a esa escala. La calidad de la sala sale de la corrida completa en la RTX.
- **Poda:** reordenar las propiedades no cambia ningún valor.
- **Ubicación a Unity y a la web:** las matrices exportadas llevan cada gaussiana al mismo lugar que en Blender, con un error de 2e-5 m.
- **Unity:** el C# compila contra las firmas de HDRP 17.3, y el pase de splats usa APIs que existen en Unity 6.3.
- **Web:** con three.js 0.180 la prueba de punta a punta pasa entera.

## Repos libres que usa

| Repo | Licencia | Para qué |
|---|---|---|
| [aras-p/UnityGaussianSplatting](https://github.com/aras-p/UnityGaussianSplatting) v1.1.1 | MIT | Dibujar los splats en Unity (embebido en `Packages/`) |
| [sparkjsdev/spark](https://github.com/sparkjsdev/spark) 2.3.1 | MIT | Dibujarlos en la web (three.js) |
| [ArthurBrussee/brush](https://github.com/ArthurBrussee/brush) v0.3.0 | Apache-2.0 | Entrenarlos en NVIDIA, AMD, Intel y Apple |
| [playcanvas/splat-transform](https://github.com/playcanvas/splat-transform) 3.10.1 | MIT | PLY → SOG para la web |
