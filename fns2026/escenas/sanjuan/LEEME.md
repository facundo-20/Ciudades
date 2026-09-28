# Recorrido por San Juan: los dinosaurios muestran la provincia

Siete postales hiperrealistas (Cycles). En cada una, un *Sanjuansaurus gordilloi*, que quiere decir "lagarto de San Juan", presenta un lugar icónico de hoy. Lo acompaña otra especie de Ischigualasto.

```bash
python3 postales_sanjuan.py -- salida/ [--postales hongo bochas alcazar leoncito cuesta catedral bicentenario] [--calidad prueba|media|led]
```

| Postal | Lugar | Hito |
|---|---|---|
| hongo | El Hongo, Valle de la Luna | Meshy (`el_hongo`) + barrancas con estratos |
| bochas | Cancha de Bochas | concreciones de 5 a 90 cm (Meshy `bochas` o a medida) |
| alcazar | Cerro Alcázar, Barreal | Meshy (`cerro_alcazar`), con la cordillera atrás |
| leoncito | Pampa El Leoncito | carro velero sobre el barreal blanco, CASLEO arriba de un cerro, atardecer |
| cuesta | Dique Cuesta del Viento, Rodeo | lago turquesa desde un mirador, Andes nevados |
| catedral | Catedral y campanario (1979) | Meshy (`campanario_catedral`) o a medida |
| bicentenario | Teatro del Bicentenario | arco de 63 m de luz y 6 m de alto, en travertino |

## Cómo está hecho

- **Medidas y colores:** son los reales, con la fuente anotada en `pipeline/lista_modelos.json`. Donde el dato no está confirmado dice **[a confirmar]**.
- **Imágenes:** Google Maps y las fotos se usaron sólo para estudiar formas y colores. No se copian (derechos y términos de uso).
- **Posición del guía y los acompañantes:** es relativa a la cámara (a 11 m, en el tercio izquierdo) y miran hacia el hito, así siempre entran en cuadro.
- **Montañas:**
  - ruido de crestas y pie de monte tendido;
  - nieve sólo en lo plano y en altura;
  - perspectiva aérea: se azulan con la distancia aunque la niebla volumétrica esté apagada.
- **Hitos:** si todavía no hay modelo de Meshy, el hito se arma en Blender con sus medidas. Así la postal sale igual.
- **Afuera a propósito:** la Difunta Correa, porque es un santuario religioso.

## Dos eras con la misma cámara

- `--era hoy`: el lugar como es hoy. Sigue el video de referencia de Ischigualasto:
  - cirros sobre un azul profundo;
  - suelo de arena y ripio, con grietas sólo en manchones;
  - lomas con bandas gris, lila y rosado;
  - jarillas y cardones;
  - el alambrado de troncos del Hongo;
  - guanacos.
- `--era triasico`: el mismo encuadre hace 231 millones de años.
  - Es una llanura con un brazo del río, bosque de *Dicroidium*, *Neocalamites* y helechos, y lluvias de temporada.
  - Hay volcanes en el horizonte y todavía no hay Andes.
  - Está la fauna de Ischigualasto: *Ischigualastia*, *Hyperodapedon*, *Exaeretodon*, *Saurosuchus*, *Sanjuansaurus* y *Panphagia*.
- `--era ambas`: las dos. La del Triásico sale como `<postal>_triasico.png`.

Con la misma cámara, en After se pasa de una era a la otra con una cortina de estratos.

## Render final en GPU (en la M4 o las OMEN, con Blender 5.2)

En la nube no hay placa de video: Cycles corre en el procesador y cada panorámica del LED tarda entre 8 y 40 minutos. Con GPU son minutos:

```bash
cd fns2026/escenas/sanjuan
FNS_GPU=1 blender -b --factory-startup -P postales_sanjuan.py -- ../../render/postales --era ambas --calidad led
cd ../hiperreal
FNS_GPU=1 blender -b --factory-startup -P triasico_cycles.py -- ../../render/triasico --calidad led
```

En Windows, antes de esos comandos: `set FNS_GPU=1`, y usá la ruta completa de `blender.exe` de 5.2.
