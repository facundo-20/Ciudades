# Hunyuan3D-2 en Blender (OMEN)

Hunyuan3D-2 es el generador de modelos 3D de Tencent: arma un modelo a partir de una foto.

- **Forma:** con 6 GB de memoria de video.
- **Forma y textura:** con 16 GB.

Corre en la OMEN, en local: las fotos no salen de la PC.

## Instalar (una vez)

Doble clic en **`INSTALAR_HUNYUAN.bat`**:

1. Baja el paquete portable para Windows ([YanWenKun/Hunyuan3D-2-WinPortable](https://github.com/YanWenKun/Hunyuan3D-2-WinPortable), GPL-3.0) a `%USERPROFILE%\Hunyuan3D2_WinPortable`. Trae Python, PyTorch con CUDA y el código oficial.
   - Para RTX 50 elige el de CUDA 12.9; si no, el de 12.6.
   - Hace falta el driver de NVIDIA 576.57 o más nuevo y 7-Zip (lo instala con winget si falta).
2. Deja **`HUNYUAN_SERVIDOR.bat`**: el servidor oficial (`api_server.py`) en `http://localhost:8080`, el puerto que espera el plugin. La primera vez baja los modelos (~10 GB).
3. Instala y habilita el **plugin oficial** en tu Blender. Solo suma el plugin y no toca el resto de tus preferencias. Queda en el panel lateral (N) → "Hunyuan3D-2".

## Usar

**En Blender:**

1. Abrí `HUNYUAN_SERVIDOR.bat` y dejalo abierto.
2. En el panel "Hunyuan3D-2" elegí una foto (o escribí un texto) y apretá generar.
3. Con un objeto seleccionado, el plugin lo puede texturizar.

**Por lotes** (una carpeta de fotos, un modelo por foto): `HUNYUAN_LOTE.bat CARPETA`.

- El nombre de cada foto es el nombre del modelo.
- `el_hongo.jpg` → `fns2026/modelos/el_hongo/el_hongo_alto.glb`. Ahí lo busca el Constructor de Unity para ubicar el Hongo en el capítulo "hoy". Lo mismo con `el_submarino.jpg`.
- Opciones:
  - `--textura`: pinta el modelo.
  - `--caras 60000`
  - `--octree 384`: más alto, más detalle.
  - `--rehacer`

**Fotos que funcionan mejor:** el objeto entero, de frente, con luz pareja. El servidor saca el fondo solo.

## Textura

La forma sale siempre. Para que Hunyuan además pinte el modelo, hace falta compilar su rasterizador una vez. Pide CUDA Toolkit 12.9 y Visual Studio Build Tools 2022 ("Desarrollo de escritorio con C++"). El portable lo hace desde su `RUN.bat` → Hunyuan3D 2.0 → opción de texturas.

Para las formaciones de roca no hace falta: en Unity llevan el material triplanar de estratos del paredón, que calza con el resto del valle.

## Licencia

Los modelos de Hunyuan3D-2 tienen la **Tencent Hunyuan 3D 2.0 Community License** (`LICENSE` del repo oficial, revisada).

- **Territorio:** vale en todo el mundo menos la Unión Europea, el Reino Unido y Corea del Sur.
- **Uso comercial:** permitido mientras el licenciatario no supere 1 millón de usuarios activos por mes.
- **Lo generado:** Tencent no reclama derechos sobre los modelos que se generan; son nuestros.
  - Lo generado tampoco se puede mostrar fuera del territorio permitido. Por eso los modelos de Hunyuan van en la sala (San Juan). La versión web pública, que se puede abrir desde cualquier país, sigue con los de Meshy y los propios.
  - No se puede usar para entrenar o mejorar otro modelo de IA. Hornear un Gaussian splat no es eso: es una representación de la escena, no un modelo de IA.
- **Si se redistribuye Hunyuan:** va con su licencia y su aviso.
- **Créditos:** Tencent sugiere "Powered by Tencent Hunyuan".

## Probado en la nube

- **Plugin:** se instala y se habilita en un Blender sin tocar, y sigue habilitado al reabrir Blender (panel `Hunyuan3DPanel`). Si al Python de Blender le falta `requests`, el instalador lo agrega.
- **Lote:** probado contra un servidor que imita al oficial (`/generate` con la foto en base64 y los mismos parámetros que el plugin). Guarda los GLB donde los busca Unity y no repite los que ya existen.
- **Lo que solo se puede probar en la OMEN:** la generación de verdad (necesita una placa NVIDIA).
