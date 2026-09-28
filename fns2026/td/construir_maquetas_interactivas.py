"""
Maquetas interactivas en TouchDesigner: el giro de cada lugar se recorre con el cuerpo.
Se pega en el Textport del proyecto Ischigualasto Inmersivo:

    exec(open('/Users/Facundo/Documents/Ciudades/fns2026/td/construir_maquetas_interactivas.py').read())

Qué arma en /project1/maquetas:
  osc_cuerpo     OSC In CHOP en 10000: el mismo que usa el proyecto (/body/x, /body/present).
                 Si el TD ya tiene uno escuchando en 10000, este script lo reusa (dos no pueden).
  lugar_<n>      Movie File In TOP con la secuencia PNG del giro (con alfa), index = cuadro
  control        CHOP que decide el cuadro:
                    · nadie → gira solo (loop del giro, como el modo atractor)
                    · alguien → la maqueta gira siguiendo /body/x (izquierda-derecha = 360°),
                      con lag para que no tiemble
  selector       Switch TOP: qué lugar se ve (parámetro Lugar en la página FNS, o cada 45 s solo)
  sobre_sol      Over TOP: la maqueta con alfa sobre el fondo del sol (lo que haya en fondo_in)

Por qué PNG y no MP4: en una secuencia de imágenes todos los cuadros son clave; ir para
atrás o saltar al cuadro 300 es instantáneo. Un H.264 tironea al recorrerlo al revés.
Para el show: pasar las carpetas frames/ a HAP con Alley y cambiar el `file` del Movie File In.

NO PROBADO EN TOUCHDESIGNER (escrito sin TD a mano): cada parámetro va en un try y al final
lista lo que quedó para hacer a mano, como los otros td_*.py.
"""

import os

CARPETA_MAQUETAS = "/Users/Facundo/Documents/Ciudades/fns2026/escenas/render"   # la salida de maquetas_ischigualasto.py
LUGARES = ["hongo", "submarino", "bochas", "valle_pintado", "barrancas"]
PUERTO = 10000
CAMBIO_SOLO_S = 45

pendientes = []


def poner(o, par, v):
    try:
        setattr(o.par, par, v)
    except Exception as e:
        pendientes.append(f"{o.path}.par.{par} = {v!r} ({e.__class__.__name__})")


def crear(padre, tipo, nombre, x, y):
    if padre.op(nombre):
        padre.op(nombre).destroy()
    o = padre.create(tipo, nombre)
    o.nodeX, o.nodeY = x, y
    return o


raiz = op("/project1")
base = crear(raiz, baseCOMP, "maquetas", 0, -600)
pag = base.appendCustomPage("FNS")
pag.appendMenu("Lugar")
base.par.Lugar.menuNames = LUGARES
base.par.Lugar.menuLabels = ["El Hongo", "El Submarino", "Cancha de Bochas", "Valle Pintado", "Barrancas Coloradas"]
pag.appendToggle("Automatico", label="Cambiar solo cada 45 s")
base.par.Automatico = True

# entrada del cuerpo: reusar el OSC In del proyecto si ya escucha en 10000
existente = [o for o in raiz.findChildren(type=oscinCHOP) if getattr(o.par, "port", None) and o.par.port.eval() == PUERTO]
if existente:
    osc = crear(base, selectCHOP, "osc_cuerpo", 0, 0)
    poner(osc, "chops", existente[0].path)
else:
    osc = crear(base, oscinCHOP, "osc_cuerpo", 0, 0)
    poner(osc, "port", PUERTO)

# control: cuadro a mostrar (0..1 del giro)
ctl = crear(base, scriptCHOP, "control", 200, 0)
cb = crear(base, textDAT, "control_cb", 200, 150)
cb.text = '''
import math
estado = {"fase": 0.0, "x": 0.5}
def onCook(scriptOp):
    osc = op("osc_cuerpo")
    val = {c.name.strip("/"): c.eval() for c in osc.chans()}
    presente = val.get("body/present", 0) > 0.5
    dt = absTime.stepSeconds
    if presente:
        # lag: la maqueta sigue a la persona sin temblar (~0,25 s)
        estado["x"] += (val.get("body/x", 0.5) - estado["x"]) * min(1.0, dt * 4)
        objetivo = estado["x"]
        # camino más corto en el círculo, para que no dé la vuelta entera al cruzar 0/1
        d = (objetivo - estado["fase"] + 0.5) % 1.0 - 0.5
        estado["fase"] = (estado["fase"] + d * min(1.0, dt * 6)) % 1.0
    else:
        estado["fase"] = (estado["fase"] + dt / 15.0) % 1.0     # giro solo: 15 s por vuelta
    scriptOp.clear()
    scriptOp.appendChan("fase")[0] = estado["fase"]
    scriptOp.appendChan("presente")[0] = 1.0 if presente else 0.0
'''
poner(ctl, "callbacks", cb.name)

movs = []
for i, lugar in enumerate(LUGARES):
    m = crear(base, moviefileinTOP, f"lugar_{lugar}", 400, 200 - i * 120)
    carpeta = os.path.join(CARPETA_MAQUETAS, lugar, "frames")
    poner(m, "file", os.path.join(carpeta, "0001.png"))
    poner(m, "playmode", "specify")        # el índice lo manda el cuerpo, no el reloj
    poner(m, "indexunit", "fraction")
    m.par.index.expr = "op('control')['fase']"
    if not os.path.isdir(carpeta):
        pendientes.append(f"no está {carpeta}: renderizar con maquetas_ischigualasto.py --calidad final")
    movs.append(m)

sw = crear(base, switchTOP, "selector", 650, 0)
for i, m in enumerate(movs):
    sw.inputConnectors[i].connect(m)
sw.par.index.expr = (f"int(absTime.seconds / {CAMBIO_SOLO_S}) % {len(LUGARES)} "
                     f"if parent().par.Automatico else parent().par.Lugar.menuIndex")

fondo = crear(base, inTOP, "fondo_in", 650, -150)
over = crear(base, overTOP, "sobre_sol", 850, 0)
over.inputConnectors[0].connect(sw)
over.inputConnectors[1].connect(fondo)
salida = crear(base, outTOP, "salida", 1050, 0)
salida.inputConnectors[0].connect(over)

print("\n=== maquetas interactivas en", base.path, "===")
if pendientes:
    print("Para hacer a mano:")
    for p in pendientes:
        print("  ·", p)
print("""
Verificación:
 1. Sin nadie: la maqueta gira sola (15 s por vuelta) y cambia de lugar cada 45 s.
 2. python3 osc_simulador.py demo  → al aparecer /body/present, la maqueta sigue a /body/x.
 3. Con el puente del LiDAR (puente_tracker_ischigualasto.py): caminar de izquierda a derecha gira 360°.
 4. Conectar el fondo del sol a fondo_in y la salida a la pantalla.
""")
