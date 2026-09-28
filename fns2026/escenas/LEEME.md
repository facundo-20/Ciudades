# Escenas y maquetas · Parque Triásico

## Las 5 maquetas de Ischigualasto

`maquetas_ischigualasto.py` arma, ilumina, anima y renderiza **El Hongo, El Submarino,
Cancha de Bochas, Valle Pintado y Barrancas Coloradas**. Cada una va sobre un pedestal
redondo, como las maquetas del stand.

Qué pasa en cada giro de 360°, que empalma en loop:
1. Aparece una **grilla dorada** que sube desde el pedestal. Es el "mallado" del stand.
2. La **textura real** revela la maqueta de abajo hacia arriba.
3. La maqueta gira. Los PNG tienen **alfa**, así que se montan sobre el sol de la Fiesta.

```bash
# prueba rápida (640×360, 24 cuadros), anda en cualquier máquina, incluso sin placa
blender -b --factory-startup -P maquetas_ischigualasto.py -- render
# final en la Mac M4 (1920×1080, 450 cuadros = 15 s, Cycles con Metal)
FNS_GPU=1 blender -b --factory-startup -P maquetas_ischigualasto.py -- render --calidad final
# una sola
... -- render --solo hongo --calidad final
```

Sale en `render/<lugar>/`:
- `.blend` para retocar;
- `.glb` y `.fbx` para TD;
- una vista fija;
- `frames/` (PNG con alfa);
- `<lugar>_giro.mp4` para mirar.

### Con Meshy
Si `../modelos/<nombre>/<nombre>_alto.glb` existe, la maqueta usa **el modelo de Meshy en vez
de la forma procedural**. Ese archivo es la salida de `pipeline/correr_todo.py`.
- Mantiene pedestal, suelo, luz, giro y grilla dorada.
- El revelado se le agrega solo a los materiales PBR de Meshy.
- En la Cancha de Bochas, el modelo de Meshy se copia en cada posición de las bochas.

| Maqueta | Modelo de Meshy que la reemplaza |
|---|---|
| hongo | `el_hongo` |
| submarino | `el_submarino` |
| bochas | `bochas` |

Orden de trabajo: `pipeline/correr_todo.py --solo el_hongo el_submarino bochas` y después este script.

### Interactivo
En TD: `td/construir_maquetas_interactivas.py`.
- Recorre los `frames/` con el cuerpo: `/body/x` gira la maqueta.
- Sin nadie, gira sola.
- Cambia de lugar cada 45 s.

En Arena: pasar `frames/` a DXV3 con Alley. Los clips son todos cuadros clave.

## Tiempos medidos
- **Prueba, en la nube, con CPU de 4 núcleos:** unos 3 s por cuadro. Un giro de 24 cuadros tarda unos 75 s.
- **Final en la M4, sin medir:** con 96 muestras a 1080p por Metal, calculo entre 10 y 30 s por cuadro. Son unas 2 horas por lugar para los 450 cuadros. Conviene dejarlo corriendo de noche, o bajar a `--calidad media`: 720p y 180 cuadros.
