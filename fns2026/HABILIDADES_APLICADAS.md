# Habilidades de cada documento, aplicadas al Parque Triásico

Este documento es el complemento de `INVESTIGACION_Y_PROPUESTA.md`.
Cada fila toma una **técnica concreta** de uno de los documentos de Facu y dice en qué se convierte en la FNS 2026.
No se agrega tecnología nueva: todo sale de cosas que ya están hechas o encargadas.

Estado de cada técnica:
- **hecho**: probado según su documento.
- **encargado**: hay un PEDIDO escrito, pero todavía no hay código.
- **nuevo**: es una adaptación para el Triásico.

---

## 1. MANUAL: tracker LiDAR (lidarwall)

| Técnica | En qué se convierte en el Triásico | Estado |
|---|---|---|
| **Fondo con percentil 15** (no el mínimo) | Imprescindible en la fiesta: con 100.000 personas un sábado, **siempre** hay alguien cruzando mientras se captura el fondo. Con el mínimo quedaría un ángulo ciego toda la noche | hecho |
| **Perfiles** `mano`, `pies`, `multitud` | `mano` en la pared del fósil, `pies` en el piso de excavación, `multitud` en la entrada del túnel. Se cambian con el cue, sin reabrir sensores | hecho |
| **Zonas con `dwell`, más `carga`** (el ritual de las velas) | **"Los 7 del amanecer":** 7 zonas, una por dinosaurio sanjuanino (*Herrerasaurus*, *Eoraptor*, *Panphagia*, *Sanjuansaurus*, *Eodromaeus*, *Chromogisaurus* y el *Taytalura*). Mientras la persona se queda, el fósil "se carga" y se ve que algo pasa. A los 3 s aparece el animal vivo. Con el ritual, cambia `/ritual/vela/<i>/carga` por el dinosaurio | nuevo, sobre algo hecho |
| **Estela entre pantallas**: la foto va atrasada, la cola se acorta al frenar y el hueco entre pantallas existe | **Un Herrerasaurus que cruza el stand corriendo** de una pantalla a otra. El destello es el polvo y el animal va atrás. En el hueco de 40 cm entre pantallas no se dibuja, así que parece que pasó por detrás de una roca. Es la mejor excusa para que el hueco sume | hecho |
| **Atlas del cubo en metros** (una onda que nace en el piso cruza a la pared sin cortarse) | La **pisada gigante**: el pie en el piso manda una onda que trepa por la pared y sacude al dinosaurio. **Regla del documento:** el efecto nace en el piso, nunca en una esquina entre paredes | hecho |
| **Fusión de varios sensores con un solo seguimiento** | Una pared de 7,5 m lleva dos LiDAR, y la mano que cepilla el fósil no cambia de identidad en la costura | hecho |
| **Gesto de pasar la hoja** (resorte críticamente amortiguado; se decide por la **velocidad** al perder el track, no por la posición) | **Fichas científicas que se pasan con la mano**, como un libro de paleontología. Lo mismo que el photobook, con capítulos: Triásico, Hallazgo, Hoy | hecho |
| **Libro de firmas**, con perfil `dedo`, `max_missed = 2` y el mosaico que se imprime | **"Libro de los Paleontólogos del Sol":** los chicos firman como si fueran descubridores. El mosaico impreso **se le entrega al MuPa** para su sala temporaria. Es un entregable que se puede cobrar aparte | hecho |
| **15 efectos como presets de un solo motor** | Las 5 estaciones no son 5 proyectos: son **presets del mismo tracker**, con otros perfiles y otras zonas | hecho |
| **Cada efecto con su fallback** | Las 3 noches se pueden perder sin que nadie lo note, porque si falla el sensor el efecto sigue en automático | hecho |
| **Hoja de ruta impresa, modo evento, Stream Deck** (OSC 7400) | Operación en un predio abierto, sin depender de internet | hecho |

## 2. LEEME-OTRA-PC: app del piso + TouchDesigner

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **La regla del reparto**: si tiene reglas o puntaje va a la app; si es un look, a TD | Excavación y los 7 del amanecer en la **app**. El túnel y el dinosaurio vivo en **TD** | hecho |
| **Exportar objetos a TD** (posiciones, no píxeles) + `td_piso_objetos.py` con **File In SOP para un `.fbx`** | Los huesos que se encuentran en el piso aparecen **en 3D real** en la pared, con luz y sombra. Se cambia la esfera por el `.fbx` del hueso | hecho, falta el modelo |
| **Presets de look** (infantil, boda, quince, deporte, corpo, custom) | Preset nuevo `triasico`: paleta de arenisca roja y gris verdosa de Ischigualasto, polvo en vez de brillos | nuevo |
| **4 capas + shaders `.frag` o Shadertoy** | Capa 1 sedimento, capa 2 huesos, capa 3 polvo (en modo *add*), capa 4 un shader de **calor del Zonda** que distorsiona | nuevo |
| **Predicción de 40 a 60 ms** + Novastar en modo Send-Only | Compensa los ~115 ms del RPLIDAR, igual que en el piso de eventos | hecho |
| **Soportes en Fusion 360** (de piso y de pared, en truss o caño Layher) | Se imprimen en 3D: un predio al aire libre necesita el sensor protegido y fijo | hecho, sin probar |
| **Patrón de prueba** (el círculo tiene que verse redondo) | La calibración de cada noche antes de abrir | hecho |

## 3. INTEGRAR: animaciones en Blender como hojas de sprites

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **Hojas de sprites procedurales** (`ef_*` en el diccionario `EFECTOS`), en versión cruda y con halo | Efectos nuevos: `polvo_arenisca` (el pie levanta polvo), `huella_teropodo` (la huella de 3 dedos que se hunde), `hueso_emerge` (el fósil que asoma) y `rugido` (anillos de onda sonora) | nuevo, misma cañería |
| **`PISO.Anim.bucle`, con `vel` que sigue a la velocidad** (como la pelota) | El *Eoraptor* que corre por el piso anima más rápido cuanto más rápido se mueve | hecho |
| **`soltar` para el efecto que dispara una pisada** | Cada pisada suelta `polvo_arenisca` | hecho |

## 4. LEEME del stand: maquetas y experiencias

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **El mallado dorado aparece primero y después la textura** | Tiene una lectura paleontológica directa: **el mallado es el esqueleto y la textura es la carne**. El dinosaurio aparece como fósil y "revive". Es la metáfora central del stand, y ya está programada | hecho |
| **Modo atractor a los 25 s sin gente** | Con 320.000 personas casi nunca se activa de noche, pero sí de tarde, cuando abre el predio | hecho |
| **Seguir el cuerpo con la cámara web**: posición, mano arriba | Es el respaldo del Kinect en la estación 4 | hecho |
| **"Vuelta a San Juan"**, pedalear con ranking | **"Corré como un Eoraptor":** 45 s corriendo en el lugar y el ranking por velocidad. El Eoraptor era chico y rápido, así que tiene sentido | nuevo, sobre algo hecho |
| **Foto recortada con QR** | "Yo en el Triásico" | hecho |
| **Presets de la PTZ por VISCA** (`publico`, `foto`, `vuelta`) | Se suma el preset `show` | a sumar |
| **Control desde el celular** | El joystick del celular mueve al dinosaurio en la pantalla grande | hecho |

## 5. PEDIDO-IA: las cuatro fases

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **Fase 2: cámara cenital con pose y gestos por reglas** | En la **sala triásica** (ver el punto 6), `brazos_arriba` hace **rugir** al dinosaurio del fondo, `salto` hace **temblar la tierra** (la pisada gigante), `quieto` 2 s en el centro trae al dinosaurio a olerte, y `de_la_mano` hace que aparezca una **manada** para las familias | encargado |
| **Unir cada pisada con su cuerpo** (`tc.cuerpo`) | Contar **personas reales** y no pies. Es el dato que el Ministerio quiere en el informe final | encargado |
| **Licencia: YOLOv8 es AGPL** | **Es crítico para un contrato con el Gobierno, que es un uso comercial.** Hay que ir con **MoveNet** (Apache 2.0) o RTMPose (Apache 2.0) desde el principio | decisión |
| **Fase 3: director automático** (estados `vacia` a `explotada` con histéresis, aprende con media móvil, micrófono con BPM) | Clave en un predio con flujo muy variable: de tarde, *vacía*, pasa al atractor o a "Huellas"; a la noche, *explotada*, pasa a "Excavación" en modo multitud. Con el micrófono, **el dinosaurio se sincroniza con el recital** del escenario del Estadio | encargado |
| **El operador manda siempre**: un cambio manual pausa el director 5 minutos | Así se puede cortar a un modo institucional cuando pasa el Gobernador o una autoridad | encargado |
| **Fase 4: fotos por QR, filtro NSFW y moderación manual por defecto** | Una fiesta pública con menores exige **moderación manual siempre**. Las fotos de la gente en Ischigualasto entran al mosaico. Sin EXIF ni GPS | encargado |
| **Fase 1: encuadre inteligente por caras + control de calidad** (Laplaciano, dHash, fotos oscuras) | Las fotos "Yo en el Triásico" se recortan sin cortar cabezas, y el mosaico queda sin fotos repetidas | encargado |
| **Métricas de la noche** (el director registra cuánta gente se suma tras cada cambio) | **Un informe para el Ministerio**: personas por hora y por estación, y qué experiencia atrajo más. Es un argumento para la próxima edición y para el MuPa | nuevo, sobre lo encargado |

## 6. PEDIDO-SALA: la sala entera (piso + 3 paredes)

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **Un solo mundo en metros, `PISO.Sala.aLienzo(x,y,z)`, que se dobla 90° en los bordes** | **"El Cañón": un cubo abierto** (piso más 3 paredes) que reproduce un rincón de Ischigualasto. El piso es el lecho del río del Triásico y las paredes, los farallones. **Es la estación central del stand** y reemplaza al túnel curvo si hay LED para eso | encargado |
| **Atlas en cruz + `atlas.json`** | Se mapea en Novastar sin adivinar | encargado |
| **El modo `piso` con "ambiente derivado"**: las paredes nunca quedan en negro | Cualquier juego del piso, aunque no esté adaptado, tiene los farallones vivos | encargado |
| **Partículas en la placa sin estado** (50.000, vida con `fract(t/vida+fase)`, remolinos con senos cruzados) | **La tormenta de arena del Zonda**: cada pisada suelta miles de granos que el viento lleva hacia el farallón del fondo | encargado |
| **Mosaico de fotos** (cada partícula con su lugar fijo y las últimas 16 pisadas como uniform) | **Un esqueleto de Herrerasaurus armado con miles de fotos del público.** Al pisar se desarma en remolino y vuelve a armarse. Es la imagen de cierre de la fiesta | encargado |
| **Siluetas de la pose como partículas en la pared** | **Tu silueta se vuelve dinosaurio**: los puntos del cuerpo se reordenan en la forma de un terópodo que imita tus movimientos | nuevo, sobre lo encargado |

## 7. VALS y ROSAS: fotos reales convertidas en sprites

| Técnica | En qué se convierte | Estado |
|---|---|---|
| **Fotos reales recortadas sobre cartas curvas, renderizadas en Cycles, con borde matemático** (sin halo que delate el recorte) | **Fósiles con fotos reales.** Si el MuPa o la UNSJ ceden fotos de piezas reales, con permiso escrito, los huesos del piso son fotos verdaderas y no dibujos. Esto es lo que diferencia el stand de un juego genérico | técnica hecha, faltan las fotos |
| **Un juego con 4 modos** (`alfombra`, `lluvia`, `ramo`, `rosas`), que se cambian con 1 a 4 o por código | `excavacion.js` con 4 modos: **`sedimento`** (el piso tapado de arena y cada paso barre y descubre huesos), **`zonda`** (lluvia de arena en bucle perfecto), **`hallazgo`** (el bloque de roca espera en el centro; al pisarlo estalla y salen los huesos, que quedan como sedimento) y **`huevos`** (nidos sueltos que al pisarlos eclosionan) | nuevo, sobre algo hecho |
| **Física de 3 fuerzas**: corriente de la sala; el pie con empuje radial, remolino y **empujón hacia arriba**; y rozamiento casi nulo en el aire y alto apoyado | Se aplica tal cual a la arena: el grano **despega** en vez de resbalar ("es el 80% de que se vea real") y el piso queda **"peinado" por donde pasó la gente**, como un yacimiento excavado | hecho, se reusa |
| **Altura falsa** (`o.z` como escala más sombra corrida) | Los granos de arena y los huesos que saltan, vistos desde arriba en el piso LED | hecho |
| **`mezcla: 'normal'` para foto y `'add'` para luz** | Huesos y arena, que son foto, en *normal*. El polvo con brillo y el rugido, en *add* | regla |
| **Encadenar `bucle` → `soltarlo` → `soltar`** (el ramo que espera, estalla y abajo sigue la lluvia) | El bloque de roca respira en bucle, alguien lo pisa, estalla en huesos, y abajo sigue el Zonda | hecho |
| **El costo de render** (Cycles a 512 px, unos 15 s por cuadro; a 384 px va el doble de rápido) | Presupuesto de tiempo: unas 6 hojas de 40 a 50 cuadros son **unas 1,5 horas de render** a 384 px. Entra en el cronograma | dato |

---

## Cómo queda el stand con todo esto

```
                    ┌─────────────────────────────────────┐
                    │   EL CAÑÓN (sala: piso + 3 paredes)  │  ← estación central
                    │   farallón fondo: Herrerasaurus 1:1  │     PEDIDO-SALA + IA fase 2
                    │   piso: excavacion.js (4 modos)      │     VALS/ROSAS + lidarwall
   ENTRADA          │   cámara cenital: rugido/salto/manada│
   túnel LED curvo  └─────────────────────────────────────┘
   (estela: el dino                 │
   cruza pantallas)   PARED DEL FÓSIL (LiDAR mano, 7 del amanecer)
                      MAQUETAS (mallado = esqueleto → textura = carne)
                      FOTO PTZ + QR → mosaico-esqueleto de cierre
                      DIRECTOR automático + informe de público al Ministerio
```

## Lo que necesito para pasar de papel a código

1. **La carpeta `PISO LED/`**, que sale de `PISO-LED-APP_carrusel.zip`, y el paquete del **tracker lidarwall**. Los PEDIDOS dicen que hay que leer ese código antes de tocarlo, y en esta sesión solo tengo los `.md`.
2. El **stand** (`stand_maquetas.html`, `maquetas/`, `blender/maquetas_sanjuan.py`), para reusar las maquetas.
3. Los datos del LED para la sala: los m² disponibles de paneles curvos y rectos, y si la sala sale por el mismo Novastar.

Con eso, el orden de trabajo sería:
1. Preset `triasico` + `excavacion.js`, con la física del VALS. Se prueba con el mouse.
2. Hojas de Blender: `polvo_arenisca`, `huella_teropodo`, `hueso_emerge` y `rugido`.
3. PEDIDO-SALA fase 1: el atlas.
4. Director (IA fase 3).
5. Mosaico-esqueleto.
6. Pose con MoveNet (IA fase 2).
