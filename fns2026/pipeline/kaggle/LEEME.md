# Kaggle: GPU gratis para hornear sin la PC

Kaggle da GPU gratis: una T4 o una P100, unas 30 horas por semana y sesiones de hasta 12 horas.

Con esto, la sesión de Claude en la nube hornea los splats sola, aunque la OMEN y la Mac estén apagadas:

- Cycles renderiza las vistas en la GPU de Kaggle.
- gsplat entrena.
- Los resultados vuelven a la rama.

| Archivo | Qué hace |
|---|---|
| `hornear_splats.py` | El kernel que corre en Kaggle: clona la rama (el repo es público), baja Blender 5.0.1 para Linux, renderiza con CUDA, entrena con gsplat 1.5.3 (Apache-2.0) y poda igual que en la PC. |
| `hornear_en_kaggle.sh` | Desde la nube o cualquier Linux o Mac: sube el kernel (privado), espera a que termine, baja los `.ply` a Unity y arma los `.sog` de la web. |
| `../splats/entrenar_gsplat.py` | El entrenador con gsplat, para máquinas con NVIDIA sin Vulkan (Kaggle, Colab). Mismas entradas y misma salida que Brush. |

## Para habilitarlo (una vez, lo hace Facu)

1. **La credencial:** en kaggle.com → Settings → API → **Create New Token**. Baja un `kaggle.json` con `username` y `key`. No va al repo ni al chat.
2. **El entorno de Claude Code:** menú del entorno en la barra de título → Edit.
   - Cargar los dos valores del `kaggle.json` como `KAGGLE_USERNAME` y `KAGGLE_KEY`, en "Network secrets" (o "API credentials", o como variables de entorno).
   - En Network access, agregar `www.kaggle.com` a los dominios permitidos.
3. Una sesión nueva ya los toma. La CLI de Kaggle (`pip install kaggle`, versión 2.2.4) ya está probada en este entorno.

## Uso

```bash
fns2026/pipeline/kaggle/hornear_en_kaggle.sh bosque                  # un capítulo, calidad final
CALIDAD=media PASOS=15000 fns2026/pipeline/kaggle/hornear_en_kaggle.sh rio llanura
```

Con la calidad final (400 vistas de 1600×900, 30.000 pasos) cada capítulo tarda unas 3 o 4 horas en una T4. Entran 2 o 3 capítulos por sesión.

## Qué está probado y qué no

- **Probado acá:**
  - la sintaxis y la configuración que el lanzador inyecta en el kernel;
  - la convención de cámaras del entrenador con gsplat, contra la misma prueba de la esfera que usa Brush;
  - que Cycles, si no encuentra una GPU de verdad, lo avisa y usa la CPU (antes elegía OptiX aunque no hubiera placa).
- **No probado:** la corrida en Kaggle. Hace falta la credencial y el dominio permitido. Con eso la primera corrida la sigo yo y corrijo lo que falle.
