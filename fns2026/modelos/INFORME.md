# Modelos de Meshy: informe (28/09/2026)

## Resumen

- **Créditos:** había 1.533 y quedan 882. Se gastaron unos 650.
- **Modelos:** 19 bajados y refinados a escala real (FBX y GLB en tres niveles), cada uno con su vista previa en `<nombre>/<nombre>_vista.png`.
- **Qué va a git:** los FBX y GLB completos no. Se regeneran con `correr_todo.py`, que retoma por `modelos_meshy/*/tareas.json` sin pagar de nuevo. Sí van las vistas y, para la web, los GLB de nivel medio.

## Animales (escala por largo real)

| Modelo | Largo | Revisión anatómica |
|---|---|---|
| panphagia | 1,3 m | bien: sauropodomorfo bípedo, cuello largo, escamas, sin plumas |
| sanjuansaurus | 3 m | bien: herrerasáurido, cráneo largo con dientes, brazos cortos |
| ischigualastia | 3,5 m | bien: dicinodonte, pico, **sin colmillos**, cuerpo de barril |
| hyperodapedon | 1,3 m | **rehecho**: el primero parecía un dinosaurio; el segundo es un rincosaurio bajo con cráneo ancho |
| saurosuchus | 6 m | aceptable: patas rectas bajo el cuerpo, dos filas de placas; el cráneo quedó más chato que el real (alto y angosto) |
| exaeretodon | 1,8 m | aceptable: cuadrúpedo con cráneo ancho; la cola es más larga que la de un cinodonte real |

- **Existen en la Mac, no se regeneraron:** herrerasaurus, eoraptor y eodromaeus.
- **Rig:** el de Meshy falla en todos (`Pose estimation failed`), porque está pensado para figuras humanas. Los modelos quedan sin esqueleto: sirven para el render y la web, donde se mueven enteros. Si hace falta animación, la opción es un rig propio en Blender.

## Flora del Triásico

Los cuatro reemplazan a los procedurales en el render: dicroidium, neocalamites, helecho y conífera.

## Lugares de San Juan (escala por medida real; ver `_fuente` en `lista_modelos.json`)

| Modelo | Medida | Revisión |
|---|---|---|
| el_hongo | 6 m **[a confirmar]** | excelente, fiel a la formación |
| el_submarino | 10 m **[a confirmar]** | sin revisar en postal |
| bochas | hasta 0,9 m | bien; en la postal se reparte una cancha entera |
| cerro_alcazar | 120 m de alto **[a confirmar]** | excelente: bandas triásicas de colores |
| observatorio_casleo | 30 m | en la postal queda lejos, arriba de un cerro |
| carro_velero | 5 m | bien |
| campanario_catedral | 50 m **[a confirmar]** | ladrillo, laja y columnas blancas; el techo en punta está **[a confirmar]** |
| arco_bicentenario | 63 m | **descartado**: salió de medio punto. Se usa el arco a medida (63 m de luz, 6 m de alto) |

## Rigor científico en los prompts

- **Dinosaurios:** llevan escamas, sin plumas y sin pelo.
- **Ischigualastia:** sin colmillos, sólo con procesos caniniformes.
- **Hyperodapedon:** es un rincosaurio, no un dinosaurio.
- **Saurosuchus:** es un pseudosuquio, de la línea de los cocodrilos, con las patas rectas.
- **Exaeretodon:** es un cinodonte, pariente de los mamíferos.
- **Pendiente:** validar todo con un paleontólogo de la UNSJ o del MuPa.
