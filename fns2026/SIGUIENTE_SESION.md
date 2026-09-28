# Para la próxima sesión (Meshy ya configurado en el entorno)

Estado al 28/09:
- Red del entorno: `api.meshy.ai` habilitado (probado: Meshy responde).
- Credencial de Meshy cargada en "Credenciales de API": la toma recién una sesión NUEVA.
  En la sesión vieja Meshy respondía `Invalid API key` porque la credencial no se inyectaba.

## Orden de trabajo (sin doble trabajo)

1. `python3 fns2026/pipeline/meshy_a_fbx.py --diagnostico` → tiene que decir "Meshy responde. Créditos: N".
   Si dice `Invalid API key`: revisar en el entorno que la credencial sea para `api.meshy.ai`,
   encabezado `Authorization`, valor `Bearer msy_…`.
2. `pip install bpy numpy` (Blender 5.0 en modo consola; así se trabajó).
3. `python3 fns2026/pipeline/correr_todo.py --destino todos --no-abrir`
   Saltea lo que YA EXISTE EN LA MAC (Herrerasaurus, Eoraptor, "raptor", Hongo, Submarino: ver
   `existe_en_mac` en lista_modelos.json). Genera con Meshy: Panphagia, Sanjuansaurus,
   Hyperodapedon, Ischigualastia, los 3 huesos, bochas, suelo, barranca.
4. `python3 fns2026/escenas/triasico/construir_triasico.py -- /tmp/tri2k` (flora + 4 escenas, 2K, ~15 min en CPU).
5. Pendiente de código: poner los dinosaurios de Meshy en los `SLOT_<especie>_<n>` de cada escena
   (script `meshy_a_escenas.py`, todavía no escrito).
6. Mejoras vistas en las previas: suelo muy parejo (la máscara de hojarasca casi no se ve) y hojas
   del Dicroidium muy geométricas.

Los binarios (~200 MB) no van al repo: se regeneran con los scripts. Las vistas previas están en
`fns2026/escenas/triasico/vistas/`.
