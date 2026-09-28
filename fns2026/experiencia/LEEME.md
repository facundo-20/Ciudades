# Triásico en San Juan · experiencia inmersiva e interactiva

Ischigualasto hace 231 millones de años, para la **FNS 2026 · Parque Triásico**. Un solo mundo 3D
que se recorre en 6 capítulos:

**título → el río → el bosque de *Dicroidium* → la llanura y el volcán → la lluvia de ceniza → hoy (el Valle de la Luna)**

Se maneja con el cuerpo, con la mano o con el mouse.

## Probarlo (5 minutos)

```bash
cd fns2026/experiencia
npm install
npm run build
npm run simular -- --servir dist      # sirve la experiencia + visitantes simulados
# abrir http://localhost:8080 en Chrome · F = pantalla completa
```

Para desarrollar, con recarga en vivo: `npm run dev` (abre en :5173) y, en otra terminal, `npm run simular`.

Autotest de punta a punta: `npm run build && npm run probar`. Abre Chromium sin pantalla, recorre los 6
capítulos, toca un animal, verifica la ficha y la conexión con los sensores, y deja capturas en
`capturas/`. En la Mac: `CHROMIUM="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" npm run probar`.

## En el evento

```bash
npm run puente -- --servir dist        # sin --simular: escucha los sensores reales
```

Chrome en modo kiosco en la pantalla LED: `http://localhost:8080/?ui=0`, sin textos si los pone Arena, o con los textos.

| Parámetro | Para qué |
|---|---|
| `?calidad=1` | M4 / OMEN i7: todas las plantas, sombras, 2x |
| `?calidad=0.5` | notebook u OMEN i5 |
| `?ui=0` | sólo el mundo (para capturarlo en TD o Arena) |
| `?capitulo=2` | arrancar en el bosque |
| `?auto=0` | no avanza solo (lo maneja el operador) |
| `?ws=192.168.1.20:8765` | puente de sensores en otra máquina |

Teclas del operador: **← →** capítulos · **0–5** ir directo · **P** simular una persona · **F** pantalla completa · **H** ocultar textos.

## Qué hace la gente

| Acción | Qué pasa |
|---|---|
| **Moverse de izquierda a derecha** (LiDAR o cámara → `/body/x`) | La cámara se corre: paralaje del paisaje |
| **Estar presente** (`/body/present`) | Los animales se acercan sin atacar, se frenan a distancia prudente y miran. Si la persona corre, la siguen más rápido |
| **Tocar un animal** (pantalla táctil, pared LiDAR `/wall/touch`, mouse) | Lo acaricia: baja la cabeza y menea la cola. Aparece la ficha científica |
| **Tocar el suelo** | Huella tridáctila de terópodo con polvo. En el agua, una onda |
| **Arrastrar** | Mirar alrededor |
| **Brazos arriba** (`/gesto/brazos_arriba`), mantener apretado o → | Siguiente capítulo |
| **Nadie** | El recorrido sigue solo: modo atractor |

## Cómo está hecho (y por qué)

- **three.js + Vite, sin React.** En una instalación a pantalla completa, React no suma y cuesta por cuadro.
  - three.js lee los GLB de Blender nativo y corre en Chrome, en la M4 y en las OMEN, sin instalar nada.
  - Se puede meter en TouchDesigner con un **Web Render TOP**, o capturar con NDI.
- **Node (`server/puente.mjs`)** hace de puente, porque el navegador no puede escuchar UDP.
  - Recibe OSC del tracker (`:7001`, `/wall/*`) y del cuerpo (`:10000`, `/body/*`, `/touch/*`).
  - Lo manda por WebSocket (`:8765`) 60 veces por segundo, siempre con el estado completo.
  - Si el tracker se calla 1,5 s, lo da por caído: no quedan dedos fantasma.
- **Un solo mundo continuo** (río → bosque → llanura) en lugar de escenas sueltas: la cámara viaja sin cortes.
- **Dos eras en el mismo terreno.** El shader mezcla el suelo del Triásico con el del Valle de la Luna (arcilla cuarteada y estratos rojos) según un uniform. Pasar de una era a otra no tiene costo de carga.
- **Flora:** son los GLB horneados en Blender (`escenas/triasico/`), con texturas de 1K para web. Se dibujan con `InstancedMesh`: cientos de plantas, una llamada de dibujo por especie.
- **Fauna procedural y articulada:** cuello, cola en cadena y patas que caminan según la velocidad. Hay 6 especies de la formación.
  - Si ponés un GLB de Meshy en `public/modelos/<especie>.glb` y el nombre en `public/modelos/lista.json`, se usa ese modelo, con sus animaciones y el mismo comportamiento.
  - Nombres válidos: `herrerasaurus`, `eoraptor`, `eodromaeus`, `panphagia`, `hyperodapedon`, `ischigualastia`.

## Rigor

- **No hay pasto:** las gramíneas aparecen más de 150 millones de años después.
- **Flora:** *Dicroidium*, coníferas, *Neocalamites* y helechos.
- **Fauna:** *Herrerasaurus*, *Eoraptor*, *Eodromaeus*, *Panphagia*, *Hyperodapedon* (el más abundante) e *Ischigualastia*.
- **Fechado:** los restos quedaron enterrados en el barro de ríos y crecidas, y las capas de ceniza volcánica permiten fecharlos.
- **Los textos de las fichas están en `src/capitulos.js`.** Antes de la fiesta, que los valide un paleontólogo de la UNSJ.

## Probado y pendiente

**Probado en este repo** (Chromium sin placa de video, `npm run probar`): los 14 chequeos pasan.
- Carga la flora y la fauna.
- Recorre los 6 capítulos.
- Tocar un animal lo acaricia y muestra la ficha.
- La conexión con el puente anda y llegan los datos del cuerpo simulado.
- No hay errores en la consola.

A calidad 0,35 y en CPU pura corre a 21 fps. Con una placa de video real va a andar mucho mejor, pero **en la M4 y en las OMEN no está medido**.

**Pendiente:**
- Modelos de Meshy de los dinosaurios: por ahora son procedurales.
- Sonido ambiente.
- Prueba con el LiDAR real y en la pantalla LED real.
- Validación científica de los textos.
