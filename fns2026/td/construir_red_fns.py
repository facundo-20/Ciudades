"""
Arma en TouchDesigner la red del piso del Parque Triásico. Se pega en el Textport:

    exec(open(r'RUTA/fns2026/td/construir_red_fns.py', encoding='utf-8').read())

Qué queda armado, en /project1/fns_triasico:

  oscin_tracker  (OSC In CHOP, 7001)  ← el tracker lidarwall, sin cambios en el tracker
        │
  motor (Text DAT, módulo)  +  al_cuadro (Execute DAT)
        │   lee los toques, los pasa a metros, corre juegos_td.Excavacion a paso fijo
        │
  inst_granos / inst_huesos (Script CHOP)  →  geo_granos / geo_huesos (instancing)
        │
  cam_piso (ortográfica, cenital)  →  render_piso (Render TOP, resolución nativa del LED)
        │
        ├─ out_piso      (Window COMP)          → salida DIRECTA al Novastar del piso
        ├─ spout_piso    (Syphon Spout Out TOP)  → Arena, sólo de espejo/monitoreo
        └─ a_arena       (OSC Out DAT, 7000)     → eventos del juego a Arena (clips, dashboard)

Por qué el piso sale directo y no pasa por Arena: con el RPLIDAR a 10 Hz la cadena ya
anda en ~115 ms. Sumarle Spout + Arena son 1 o 2 cuadros más y se cruza el umbral de
150 ms del MANUAL, donde la gente toca, no pasa nada y toca más fuerte. Las paredes y
las curvas sí van por Arena (ahí no hay pisada que esperar).

NO PROBADO EN TOUCHDESIGNER: se escribió sin TD a mano. Igual que td_piso_scene.py,
cada parámetro va en un try; si alguno cambió de nombre en tu versión el script
termina igual y al final lista qué quedó para hacer a mano. La lógica del juego
(juegos_td.py) sí está probada afuera: 9 autotests.
"""

import os
import sys

# --- lo único que hay que tocar --------------------------------------------------------
CARPETA_FNS = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\FNS2026\fns2026\td"
PISO_ANCHO_M = 6.0
PISO_ALTO_M = 4.0
PITCH_MM = 3.9                 # P3.9 · con P3 poner 3.0
PUERTO_TRACKER = 7001
ARENA_IP, ARENA_PUERTO = "127.0.0.1", 7000     # Arena → Preferences → OSC → Input
MONITOR_PISO = 1               # índice del monitor que va al Novastar del piso
# ------------------------------------------------------------------------------------------

pendientes = []


def poner(o, par, valor):
    try:
        setattr(o.par, par, valor)
    except Exception as e:
        pendientes.append(f"{o.path}.par.{par} = {valor!r}  ({e.__class__.__name__})")


def crear(padre, tipo, nombre, x=0, y=0):
    viejo = padre.op(nombre)
    if viejo:
        viejo.destroy()
    o = padre.create(tipo, nombre)
    o.nodeX, o.nodeY = x, y
    return o


raiz = op("/project1")
fns = crear(raiz, baseCOMP, "fns_triasico")

# parámetros propios: lo que el operador toca en vivo, a mano o mapeado desde Arena
pagina = fns.appendCustomPage("FNS")
pagina.appendMenu("Modo", label="Modo")
fns.par.Modo.menuNames = ["sedimento", "zonda", "hallazgo"]
fns.par.Modo.menuLabels = ["Sedimento", "Zonda", "Hallazgo"]
pagina.appendToggle("Demo", label="Demo (sin sensor)")
pagina.appendPulse("Revelar", label="Revelar todo")
pagina.appendPulse("Reiniciar", label="Reiniciar ronda")
pagina.appendStr("Clipcompleto", label="OSC a Arena al completar")
fns.par.Clipcompleto = "/composition/layers/2/clips/2/connect"

# --- entrada -------------------------------------------------------------------------------
oscin = crear(fns, oscinCHOP, "oscin_tracker", 0, 400)
poner(oscin, "port", PUERTO_TRACKER)

# --- motor: el juego de juegos_td.py corriendo adentro de TD ---------------------------------
motor = crear(fns, textDAT, "motor", 200, 400)
motor.text = f'''
# Puente entre TD y juegos_td.py. Estado del módulo: vive mientras no se recompile el DAT.
import sys, math, time
CARPETA = r"{CARPETA_FNS}"
if CARPETA not in sys.path:
    sys.path.insert(0, CARPETA)
import juegos_td
from juegos_td import Toque

W, H = {PISO_ANCHO_M}, {PISO_ALTO_M}
DT = 1 / 60
juego = juegos_td.Excavacion(W, H)
_acum = 0.0
_prev = {{}}          # id → (x, y) del cuadro anterior, para la velocidad
_t = 0.0

def _toques_osc():
    chop = op("oscin_tracker")
    val = {{c.name.strip("/"): c.eval() for c in chop.chans()}}
    salida = []
    for n in range(32):
        base = f"wall/touch/{{n}}/"
        if val.get(base + "active", 0) < 0.5:
            _prev.pop(n, None)
            continue
        x = val.get(base + "x", 0.0) * W
        y = val.get(base + "y", 0.0) * H
        px, py = _prev.get(n, (x, y))
        _prev[n] = (x, y)
        salida.append(Toque(n, x, y, (x - px) / DT, (y - py) / DT, nuevo=(px, py) == (x, y)))
    return salida, val.get("show/fallback", 0) > 0.5

def _toques_demo(t):
    # tres visitantes que recorren el piso: lo que se ve si el sensor se cae
    out = []
    for i in range(3):
        a = t * (0.25 + i * 0.07) + i * 2.1
        x = W / 2 + math.cos(a) * W * (0.2 + 0.1 * i)
        y = H / 2 + math.sin(a * 1.3) * H * 0.3
        out.append(Toque(100 + i, x, y, -math.sin(a) * 1.2, math.cos(a) * 1.2))
    return out

def paso():
    global _acum, _t
    fns = parent()
    modo = fns.par.Modo.eval()
    if modo != juego.modo:
        juego.cambiar_modo(modo)
    toques, caido = _toques_osc()
    if fns.par.Demo.eval() or caido:
        toques = _toques_demo(_t)
    # física a paso fijo, separada del render (como engine.js): si TD se atrasa un
    # cuadro, se hacen dos pasos y la arena no se mueve más lento
    _acum += min(absTime.stepSeconds, 0.1)
    while _acum >= DT:
        juego.update(DT, _t, toques)
        _t += DT
        _acum -= DT
    for tipo, valor in juego.sacar_eventos():
        _avisar(tipo, valor)

def _avisar(tipo, valor):
    osc = op("a_arena")
    est = juego.estado()
    try:
        osc.sendOSC("/fns/" + tipo, [valor])
        osc.sendOSC("/composition/dashboard/link1", [float(est["progreso"])])
        if tipo == "completo" and parent().par.Clipcompleto.eval():
            osc.sendOSC(parent().par.Clipcompleto.eval(), [1])
    except Exception as e:
        debug("OSC a Arena:", e)

def instancias(tipo):
    inst = juego.instancias()
    sel = inst["tipo"] == tipo
    return {{k: v[sel] for k, v in inst.items()}}
'''

reloj = crear(fns, executeDAT, "al_cuadro", 200, 250)
reloj.text = '''
def onFrameStart(frame):
    op("motor").module.paso()

def onValueChange(par, prev):
    pass
'''
poner(reloj, "framestart", True)
poner(reloj, "active", True)

# pulsos del panel → acciones del juego
pulsos = crear(fns, parameterexecuteDAT, "pulsos", 400, 250)
pulsos.text = '''
def onPulse(par):
    j = op("motor").module.juego
    if par.name == "Revelar":
        j.accion("revelar_todo")
    elif par.name == "Reiniciar":
        j.reset()
'''
poner(pulsos, "op", fns.path)
poner(pulsos, "pars", "Revelar Reiniciar")

# --- instancias -----------------------------------------------------------------------------
for i, (nombre, tipo) in enumerate((("inst_granos", 0), ("inst_huesos", 1))):
    cb = crear(fns, textDAT, nombre + "_cb", 400, 400 - i * 60)
    cb.text = f'''
def onCook(scriptOp):
    d = op("motor").module.instancias({tipo})
    scriptOp.clear()
    scriptOp.numSamples = max(len(d["tx"]), 1)
    for k in ("tx", "ty", "tz", "rot", "esc"):
        scriptOp.appendChan(k).vals = d[k].tolist() or [0.0]
'''
    sc = crear(fns, scriptCHOP, nombre, 600, 400 - i * 60)
    poner(sc, "callbacks", cb.name)
    poner(sc, "cooktype", "always")

# --- geometría ------------------------------------------------------------------------------
def geo_instanciada(nombre, inst, y, sop_tipo, color, escala, archivo_obj=None):
    g = crear(fns, geometryCOMP, nombre, 800, y)
    for hijo in list(g.children):
        hijo.destroy()
    if archivo_obj and os.path.exists(archivo_obj):
        s = g.create(fileinSOP, "forma")
        poner(s, "file", archivo_obj)
    else:
        s = g.create(sop_tipo, "forma")
        if archivo_obj:
            pendientes.append(f"no está {archivo_obj}: uso una forma provisoria (correr la cañería Meshy → Blender)")
    s.render = s.display = True
    mat = crear(fns, pbrMAT, nombre + "_mat", 1000, y)
    poner(mat, "basecolorr", color[0]); poner(mat, "basecolorg", color[1]); poner(mat, "basecolorb", color[2])
    poner(mat, "roughness", 0.9)
    poner(g, "material", mat.name)
    poner(g, "instancing", True)
    poner(g, "instanceop", inst)
    # el juego usa x ancho, y fondo, z arriba; la cámara mira desde arriba en Y de TD
    poner(g, "instancetx", "tx"); poner(g, "instancetz", "ty"); poner(g, "instancety", "tz")
    poner(g, "instancery", "rot")
    for eje in ("x", "y", "z"):
        poner(g, "instances" + eje, "esc")
    poner(g, "scale", escala)
    return g

geo_instanciada("geo_granos", "inst_granos", 400, sphereSOP, (0.62, 0.30, 0.20), 0.035)
geo_instanciada("geo_huesos", "inst_huesos", 250, boxSOP, (0.86, 0.80, 0.68), 1.0,
                os.path.join(CARPETA_FNS, "..", "modelos", "hueso_craneo", "hueso_craneo_bajo.obj"))

# --- cámara, luz, render ----------------------------------------------------------------------
cam = crear(fns, cameraCOMP, "cam_piso", 800, 100)
poner(cam, "projection", "ortho")
poner(cam, "orthowidth", PISO_ANCHO_M)
poner(cam, "tx", PISO_ANCHO_M / 2); poner(cam, "ty", 10); poner(cam, "tz", PISO_ALTO_M / 2)
poner(cam, "rx", -90)

luz = crear(fns, lightCOMP, "sol_triasico", 800, -20)
poner(luz, "lighttype", "directional")
poner(luz, "rx", -55); poner(luz, "ry", 30)
poner(luz, "dimmer", 1.4)
poner(luz, "shadowtype", "soft2d")

ancho_px = int(PISO_ANCHO_M * 1000 / PITCH_MM)
alto_px = int(PISO_ALTO_M * 1000 / PITCH_MM)
render = crear(fns, renderTOP, "render_piso", 1000, 100)
poner(render, "camera", cam.name)
poner(render, "geometry", "geo_granos geo_huesos")
poner(render, "lights", luz.name)
poner(render, "outputresolution", "custom")
poner(render, "resolutionw", ancho_px); poner(render, "resolutionh", alto_px)
poner(render, "bgcolorr", 0.36); poner(render, "bgcolorg", 0.17); poner(render, "bgcolorb", 0.11)

# --- salidas ------------------------------------------------------------------------------------
ventana = crear(fns, windowCOMP, "out_piso", 1200, 100)
poner(ventana, "winop", render.path)
poner(ventana, "monitor", MONITOR_PISO)
poner(ventana, "borders", False)
poner(ventana, "size", "fill")          # 1:1 sin escalar: el Novastar lo toma píxel a píxel

spout = crear(fns, syphonspoutoutTOP, "spout_piso", 1200, -20)
spout.inputConnectors[0].connect(render)
poner(spout, "sendername", "TD_FNS_Piso")   # en Mac sale como Syphon, en Windows como Spout

arena = crear(fns, oscoutDAT, "a_arena", 1200, 250)
poner(arena, "address", ARENA_IP)
poner(arena, "port", ARENA_PUERTO)

# --- informe ------------------------------------------------------------------------------------
print("\n=== FNS 2026 · red del piso armada en", fns.path, "===")
print(f"piso {PISO_ANCHO_M}×{PISO_ALTO_M} m a P{PITCH_MM} → render {ancho_px}×{alto_px} px")
if pendientes:
    print("\nQuedó para hacer a mano (el nombre del parámetro cambió en tu versión):")
    for p in pendientes:
        print("  ·", p)
print("""
Verificación, en orden:
 1. Prender Demo en fns_triasico (página FNS): tres visitantes barren la arena en render_piso.
 2. Apagar Demo y mandar el tracker a 7001: oscin_tracker muestra wall/touch/0/x|y|active.
 3. Pisar (o el mouse del simulador del tracker): la arena se aparta donde se pisa, no espejada.
    Si sale espejada, invertir tz de cam_piso o el signo de y en motor._toques_osc.
 4. Revelar todo: aparecen los 9 huesos y Arena recibe /composition/dashboard/link1 = 1.
 5. Perform mode + out_piso abierta en el monitor del Novastar: la grilla del Patrón de prueba
    del tracker se ve 1:1, sin escalar.
 6. En Arena: fuente Spout/Syphon 'TD_FNS_Piso' aparece en Sources (sólo espejo).
""")
