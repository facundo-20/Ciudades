# Parque Triásico en After Effects

Arma solo la pieza del LED: **5760 × 1080** (las 3 pantallas), 30 fps y unos 64 s. Parte de los renders de Blender.

## Cómo se usa

1. Renderizá los capítulos en Blender. Sirve cualquiera de las tres salidas:
   ```bash
   # lo mejor: el recorrido de cámara animado, a la resolución del LED
   FNS_GPU=1 blender -b --factory-startup -P ../hiperreal/triasico_cycles.py -- render --calidad led --animar --segundos 12
   ```
   - Con cuadros fijos (`render/<capitulo>/<capitulo>.png`) el script les pone él mismo un movimiento lento de cámara.
   - Para probar el armado alcanzan las pruebas de `../hiperreal/pruebas/*.jpg`, aunque son chicas para el LED y el script avisa.
2. En After Effects: **Archivo › Scripts › Ejecutar archivo de script…** → `parque_triasico_ae.jsx`.
3. Elegí la carpeta de renders. Al terminar, el script muestra un resumen: qué plugins encontró y qué falta.
4. Cola de render: sale sin pérdida a `<carpeta>/AE_salida/`. Para Resolume, pasalo a **DXV** con Alley o Media Encoder.

## Recorrido por San Juan

Con `$.global.FNS_MODO = "sanjuan"` el mismo script arma la pieza con las 7 postales de `../sanjuan/`: Hongo, Cancha de Bochas, Cerro Alcázar, Pampa El Leoncito, Cuesta del Viento, Catedral y Teatro del Bicentenario.

- **Qué lleva cada postal:** título, dato, la ficha del *Sanjuansaurus* guía y la de su acompañante.
- **Cómo se dispara:** desde el puente, es el trabajo `ae_puente/cola/003_recorrido_san_juan.jsx`.

## Qué arma

- **`FNS2026_PARQUE_TRIASICO_LED`:** la pieza completa.
  - Tiene un marcador por capítulo; sirve de punto de cue.
  - Entre capítulos, fundido con desenfoque que se abre.
- **La transición estrella, Ceniza → Hoy:**
  - Un contador baja de **231.000.000 años** a **HOY**.
  - La imagen de hoy se abre en franjas horizontales, como estratos de roca.
  - Hay un zoom radial y un destello de sol.
- **`CAP_<capitulo>`:** un capítulo, con estas capas de abajo hacia arriba:
  - **Render de Blender:** cubre las 3 pantallas. Si es un cuadro fijo, lleva acercamiento y deriva con curva expo.
  - **Atmósfera propia de cada capítulo:**

    | Capítulo | Atmósfera |
    |---|---|
    | título | destello del amanecer + bruma cálida + insectos a contraluz |
    | río | polen y esporas en dos planos de foco |
    | bosque | rayos de sol entre las copas (que se mueven) + polvo en la luz |
    | llanura | reverberación de calor en el suelo + resplandor del cráter que late + polvo |
    | ceniza | ceniza en dos planos (cerca, grande y desenfocada) + brasas que suben + cielo que se oscurece + temblor de tierra |
    | hoy | polvo del viento zonda + calor suave |

  - **Color:** tono partido (sombras frías, luces cálidas), contraste, brillo suave en las luces, grano fino y viñeta.
  - **Título:** en la pantalla del centro, sin cruzar las uniones del LED. Entra letra por letra: opacidad, desenfoque y espaciado que se cierra.
  - **Fichas de especies:** en las pantallas de los costados.
    - Hyperodapedon (rincosaurio, no dinosaurio), Eoraptor, Herrerasaurus, Ischigualastia (pico sin colmillos) y Sanjuansaurus.
    - Los textos son los mismos de la web. Validarlos con un paleontólogo de la UNSJ.
- **`particulas/`:** ceniza, brasas, polen y polvo como capas con expresiones deterministas. Se ven iguales en cada render y en cada máquina.

## Plugins de primer nivel

El script los usa **si están instalados**. Si no, cae a lo nativo y la pieza sale igual.

| Plugin | Dónde entra | Sin él |
|---|---|---|
| **Deep Glow** (aescripts) | brillo de las luces altas y de las brasas | Resplandor nativo |
| **Optical Flares** (Video Copilot) | sol del amanecer | Destello de lente nativo, óptica 35 mm |
| **RSMB Pro** (RE:Vision) | desenfoque de movimiento de las partículas | desenfoque de movimiento nativo |

Las curvas "expo" que hacen **Flow** o **Ease and Wizz** ya van escritas en los keyframes, así que no hace falta abrir esos paneles.

Los efectos nativos se tocan por su nombre interno (matchName) y no por el nombre que se ve en pantalla, para que el script ande con After en castellano o en inglés.

### Para llevarlo un escalón más arriba, a mano (5 minutos cada uno)

- **Trapcode Particular** en la ceniza: reemplaza `ceniza_cerca`.
  - Emisor Box de 6000 × 100 × 3000 px arriba del cuadro.
  - Gravedad 40, viento X 60, turbulencia de aire 150.
  - Sprite con textura de copo y profundidad de campo desde la cámara de la composición.
- **Optical Flares:** si está, el script lo pone con su destello por defecto. Elegí un preset cálido y bajo (por ejemplo "Sunrise") y animá Brightness de 60 a 110.
- **Deep Glow:** subí Radius en la capa `color_llanura` para que la columna de ceniza tenga aire.

## Estado

- **Probado:** la sintaxis del script (con node) y la lógica de las expresiones del contador y de las partículas, fuera de After.
- **Sin probar:** en la nube no hay After Effects, así que el script **todavía no se corrió dentro de After**.
  - La primera corrida en la PC de Facu es la prueba real.
  - Si algo falla, el mensaje de After dice la línea exacta.
