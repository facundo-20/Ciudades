# Ischigualasto Inmersivo · estado del proyecto de la Mac (27/09)

Proyecto hecho en la Mac M4 (`~/Documents/Ischigualasto/`, **no está en este repo**): valle 360°
en Blender, excavación táctil, manada de 15 dinosaurios amistosos, Zonda con Navier–Stokes en GPU,
título de After Effects, director automático. Entrada por mouse/táctil u OSC en el puerto 10000.

## Cómo encaja en el stand de la FNS 2026

| Pieza | Dónde | Entrada |
|---|---|---|
| **Ischigualasto Inmersivo** (valle, manada, excavación táctil) | Paredes: 3 pantallas 5760×1080, TD en la Mac M4 | táctil / cuerpo por OSC :10000 |
| Excavación de piso (`td/juegos_td.py`) | Piso LED, TD en la OMEN i7 | LiDAR de piso por OSC :7001 |
| Tracker lidarwall | OMEN i5 | — |
| **Puente** `td/puente_tracker_ischigualasto.py` | OMEN i5 (junto al tracker) | traduce `/wall/*` → `/touch/*`, `/body/*` |

Con el puente, **el LiDAR del piso maneja la manada**: donde está parada la gente es `/body/x`,
así los dinosaurios se acercan y siguen a quien está de verdad frente a la pared, sin Kinect
(que en la Mac no anda). Probado: 7 autotests, incluido el viaje por UDP.

    python3 td/puente_tracker_ischigualasto.py --destino IP_DE_LA_MAC:10000

## Revisión: lo que hay que resolver antes de la fiesta

1. **Licencia de TouchDesigner en la Mac (bloqueante).** La Non-Commercial corta a 1280 px y la
   salida es 5760×1080. Facu tiene TD Pro (LEEME-OTRA-PC): hay que pasar esa licencia a la Mac o
   correr esta pieza en la OMEN i7.
2. **Clave de Meshy de la Mac.** `~/.meshy_api_key` tiene el texto de un comando, no la clave (el
   mismo problema que en Windows). Copiar la clave `msy_…` limpia.
3. **Escala ×1,8 y el "raptor".** Para un evento del Ministerio con el aval del MuPa conviene
   escala 1:1 (el Herrerasaurus ya mide 4–6 m, alcanza) o decirlo en la ficha. El "raptor" de
   Meshy tiene anatomía de dromeosáurido (de 150 millones de años después): regenerarlo como
   *Eodromaeus* con el prompt de `pipeline/lista_modelos.json` antes de que lo vea un paleontólogo.
4. **Puente Claude ↔ TD por `/tmp/claude_td/inbox.py`.** Ejecuta cualquier `.py` que aparezca en
   `/tmp`: sirve para desarrollar, pero **se apaga en el evento** (desactivar el Execute DAT) para
   que nada externo pueda correr código en la máquina del show.
5. **Marcha por shader → rig real.** El `blender_refinar.py` de este repo ya conserva rig y
   animaciones de Meshy con escala real (probado); los FBX de `dinos/` pueden pasar por ahí.
6. **Sonido:** "ronronea" está bien para chicos, pero en la ficha no presentarlo como dato:
   no se sabe qué sonidos hacían.
7. **Llevar el proyecto al repo** (sin los render pesados): hoy existe sólo en la Mac.
