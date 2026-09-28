# Modelos de Meshy — informe (28/09/2026)

## Resumen

- **Créditos:** había 1.533. Se gastaron unos 261 y quedan 1.272 (más lo que consuma el helecho, que seguía en proceso al cierre).
- **Modelos:** Meshy generó los 8 modelos pedidos, pero ninguno se pudo bajar todavía.
  - La red del entorno bloquea `assets.meshy.ai`, que es donde Meshy guarda los archivos.
  - La API (`api.meshy.ai`) sí responde.
- **Lo que falta para tenerlos:**
  1. Habilitar `assets.meshy.ai` en **Network access** del entorno.
  2. Volver a correr lo mismo:

     ```bash
     python3 fns2026/pipeline/correr_todo.py --destino flora --no-abrir
     python3 fns2026/pipeline/correr_todo.py --destino dinosaurio --no-abrir
     ```

- **No se gasta de nuevo:** cada modelo tiene sus id de tarea en `fns2026/modelos_meshy/<nombre>/tareas.json`, que están versionados en git. El script retoma esas tareas y sólo baja. Lo único nuevo que se paga es el **rig** de los dinosaurios.

## Estado por modelo

| Modelo | Camino | Estado en Meshy |
|---|---|---|
| panphagia | vistas → multi-imagen a 3D | listo, falta bajar |
| sanjuansaurus | vistas → multi-imagen a 3D | listo, falta bajar |
| ischigualastia | vistas → multi-imagen a 3D | listo, falta bajar |
| hyperodapedon | multi-imagen **falló en Meshy** (error interno), cayó a texto a 3D | listo por texto, falta bajar |
| dicroidium_meshy | vistas → multi-imagen a 3D | listo, falta bajar |
| neocalamites_meshy | vistas → multi-imagen a 3D | listo, falta bajar |
| helecho_meshy | vistas → multi-imagen a 3D | en proceso al cierre |
| conifera_meshy | las vistas **fallaron en Meshy** (error interno), cayó a texto a 3D | listo por texto, falta bajar |

- **Existen en la Mac, no se regeneraron:**
  - herrerasaurus
  - eoraptor
  - eodromaeus (el "raptor": hay que revisar su anatomía)

## Rigor científico en los prompts

Se agregó a todos los dinosaurios: *"scaly reptilian skin, no feathers, no fur"*.

- No hay evidencia de plumas en estos animales de Ischigualasto.
- Los generadores de imagen las agregan solos si no se les dice.

Correcciones por especie:
- **Ischigualastia:** antes decía *"tusked beak"*. Ahora es *"toothless turtle-like horny beak and NO tusks"*, porque es un dicinodonte sin colmillos.
- **Hyperodapedon:** ahora dice *"rhynchosaur (archosauromorph reptile, not a dinosaur)"*, con pico ganchudo y patas semiextendidas.

## Pendiente de revisar cuando se bajen

- **Vistas previas:** `fns2026/modelos/<especie>/<especie>_vista.png`. Descartar lo que tenga plumas o pasto, o una anatomía mala, y regenerarlo con `--rehacer`.
- **Rig de Meshy:** está pensado para bípedos.
  - En Hyperodapedon e Ischigualastia (cuadrúpedos) puede fallar.
  - El script sigue igual y deja el modelo sin esqueleto.
