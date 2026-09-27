"""
Puente OSC: tracker lidarwall (/wall/...) → Ischigualasto Inmersivo en TD (/touch, /body).

Por qué hace falta: el proyecto de TD de la Mac escucha en el puerto 10000 un formato
propio (/touch/u /touch/v /touch/down /body/x /body/present), y el tracker del LiDAR
manda el suyo (/wall/touch/<n>/x|y|active, /wall/count). En vez de tocar cualquiera de
los dos (los dos andan y tienen sus tests), se traduce en el medio.

    python3 puente_tracker_ischigualasto.py                       # 7001 → 127.0.0.1:10000
    python3 puente_tracker_ischigualasto.py --entrada 7001 --destino 192.168.1.20:10000
    python3 puente_tracker_ischigualasto.py --probar              # autotest, sin red externa

Reglas de la traducción:
  · /touch/u,v,down = el toque MÁS VIEJO que siga activo. Es el que "manda" (igual que el
    gesto de pasar la hoja del MANUAL): si entra una segunda mano no le roba el control a
    la primera y el pincel de la excavación no salta de un lado al otro.
  · /body/present = hay alguien (count > 0 o algún toque activo). /body/x = el promedio de
    x de los toques activos: con el LiDAR de piso, es "dónde está parada la gente".
  · Se manda a 60 Hz aunque no llegue nada nuevo: si el tracker se cae, TD recibe
    down=0 / present=0 y no queda un dedo fantasma apretado toda la noche (MANUAL §5).

Sólo biblioteca estándar: corre en la Mac M4 y en las OMEN sin instalar nada.
"""

import argparse
import socket
import struct
import threading
import time


# --- OSC mínimo (lo justo para mensajes con i/f/s) -----------------------------------

def _pad(b):
    return b + b"\0" * (4 - len(b) % 4)


def osc_codificar(direccion, *valores):
    tipos, datos = ",", b""
    for v in valores:
        if isinstance(v, bool) or isinstance(v, int):
            tipos += "i"; datos += struct.pack(">i", int(v))
        elif isinstance(v, float):
            tipos += "f"; datos += struct.pack(">f", v)
        else:
            tipos += "s"; datos += _pad(str(v).encode())
    return _pad(direccion.encode()) + _pad(tipos.encode()) + datos


def _cadena(b, i):
    fin = b.index(b"\0", i)
    return b[i:fin].decode(errors="replace"), (fin // 4 + 1) * 4


def osc_decodificar(paquete):
    """Devuelve una lista de (dirección, [valores]). Soporta bundles (#bundle)."""
    if paquete.startswith(b"#bundle"):
        out, i = [], 16
        while i < len(paquete):
            n = struct.unpack(">i", paquete[i:i + 4])[0]
            out += osc_decodificar(paquete[i + 4:i + 4 + n])
            i += 4 + n
        return out
    direccion, i = _cadena(paquete, 0)
    tipos, i = _cadena(paquete, i)
    vals = []
    for t in tipos[1:]:
        if t == "i":
            vals.append(struct.unpack(">i", paquete[i:i + 4])[0]); i += 4
        elif t == "f":
            vals.append(struct.unpack(">f", paquete[i:i + 4])[0]); i += 4
        elif t == "s":
            s, i = _cadena(paquete, i); vals.append(s)
        elif t in "TF":
            vals.append(t == "T")
    return [(direccion, vals)]


# --- traducción -------------------------------------------------------------------------

class Traductor:
    def __init__(self, espejar_x=False, invertir_y=False):
        self.toques = {}          # n → {"x", "y", "activo", "desde"}
        self.count = 0
        self.espejar_x, self.invertir_y = espejar_x, invertir_y
        self.ultimo = 0.0

    def recibir(self, direccion, vals):
        self.ultimo = time.time()
        partes = direccion.strip("/").split("/")
        if partes[:2] == ["wall", "count"] and vals:
            self.count = int(vals[0])
        elif len(partes) == 4 and partes[:2] == ["wall", "touch"] and vals:
            n, campo = partes[2], partes[3]
            t = self.toques.setdefault(n, {"x": 0.0, "y": 0.0, "activo": False, "desde": 0.0})
            if campo == "active":
                activo = bool(vals[0])
                if activo and not t["activo"]:
                    t["desde"] = time.time()
                t["activo"] = activo
            elif campo in ("x", "y"):
                t[campo] = float(vals[0])

    def salida(self, ahora=None):
        ahora = ahora or time.time()
        # si el tracker lleva 1 s callado se da por caído: todo a cero (no dedos fantasma)
        vivo = ahora - self.ultimo < 1.0
        activos = [t for t in self.toques.values() if t["activo"]] if vivo else []
        msgs = []
        if activos:
            jefe = min(activos, key=lambda t: t["desde"])
            u = 1.0 - jefe["x"] if self.espejar_x else jefe["x"]
            v = 1.0 - jefe["y"] if self.invertir_y else jefe["y"]
            msgs += [("/touch/u", u), ("/touch/v", v), ("/touch/down", 1)]
        else:
            msgs += [("/touch/down", 0)]
        presente = vivo and (self.count > 0 or bool(activos))
        msgs.append(("/body/present", 1 if presente else 0))
        if activos:
            xs = [(1.0 - t["x"]) if self.espejar_x else t["x"] for t in activos]
            msgs.append(("/body/x", sum(xs) / len(xs)))
        return msgs


def correr(entrada, destino, espejar_x, invertir_y, hz=60):
    tr = Traductor(espejar_x, invertir_y)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("0.0.0.0", entrada))
    tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    host, puerto = destino.rsplit(":", 1)
    dest = (host, int(puerto))

    def escuchar():
        while True:
            datos, _ = rx.recvfrom(65536)
            try:
                for d, v in osc_decodificar(datos):
                    tr.recibir(d, v)
            except Exception:
                pass    # un paquete roto no puede tirar el puente en medio del evento

    threading.Thread(target=escuchar, daemon=True).start()
    print(f"puente: tracker :{entrada} → Ischigualasto {host}:{puerto} a {hz} Hz (Ctrl+C para salir)")
    while True:
        for d, v in tr.salida():
            tx.sendto(osc_codificar(d, v), dest)
        time.sleep(1 / hz)


def probar():
    """Autotest de punta a punta por UDP local: tracker simulado → puente → TD simulado."""
    fallas = 0

    def ok(c, texto):
        nonlocal fallas
        print(("OK    " if c else "FALLA ") + texto)
        fallas += not c

    # codec
    m = osc_codificar("/wall/touch/0/x", 0.25)
    ok(osc_decodificar(m) == [("/wall/touch/0/x", [0.25])], "OSC ida y vuelta")

    # traducción
    tr = Traductor()
    t0 = time.time()
    for d, v in [("/wall/count", [2]), ("/wall/touch/0/active", [1]), ("/wall/touch/0/x", [0.2]),
                 ("/wall/touch/0/y", [0.7])]:
        tr.recibir(d, v)
    time.sleep(0.01)
    for d, v in [("/wall/touch/1/active", [1]), ("/wall/touch/1/x", [0.8]), ("/wall/touch/1/y", [0.1])]:
        tr.recibir(d, v)
    s = dict(tr.salida())
    ok(abs(s["/touch/u"] - 0.2) < 1e-6 and s["/touch/down"] == 1, "manda el toque más viejo, no el último")
    ok(abs(s["/body/x"] - 0.5) < 1e-6 and s["/body/present"] == 1, "cuerpo: promedio de x y presente")
    tr.recibir("/wall/touch/0/active", [0])
    ok(abs(dict(tr.salida())["/touch/u"] - 0.8) < 1e-6, "si suelta el primero, pasa al segundo")
    s = dict(tr.salida(ahora=time.time() + 2))
    ok(s["/touch/down"] == 0 and s["/body/present"] == 0, "tracker callado 1 s → todo a cero (sin fantasmas)")
    ok(abs(dict(Traductor(espejar_x=True).salida())["/touch/down"]) == 0, "sin datos → down 0")

    # de punta a punta por UDP
    td = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); td.bind(("127.0.0.1", 0)); td.settimeout(2)
    puerto_td = td.getsockname()[1]
    libre = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); libre.bind(("127.0.0.1", 0))
    puerto_in = libre.getsockname()[1]; libre.close()
    threading.Thread(target=correr, args=(puerto_in, f"127.0.0.1:{puerto_td}", False, False), daemon=True).start()
    time.sleep(0.3)
    trk = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for d, v in [("/wall/touch/3/active", 1), ("/wall/touch/3/x", 0.6), ("/wall/touch/3/y", 0.4)]:
        trk.sendto(osc_codificar(d, v), ("127.0.0.1", puerto_in))
    visto = {}
    fin = time.time() + 1.5
    while time.time() < fin and visto.get("/touch/down") != 1:
        for d, v in osc_decodificar(td.recvfrom(4096)[0]):
            visto[d] = v[0]
    ok(visto.get("/touch/down") == 1 and abs(visto.get("/touch/u", 0) - 0.6) < 1e-5,
       "UDP: el toque del tracker llega a TD como /touch/u,v,down")
    print(f"\n{'todo OK' if not fallas else f'{fallas} fallas'}")
    raise SystemExit(1 if fallas else 0)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="tracker lidarwall → Ischigualasto Inmersivo (TD)")
    ap.add_argument("--entrada", type=int, default=7001, help="puerto donde manda el tracker")
    ap.add_argument("--destino", default="127.0.0.1:10000", help="IP:puerto del TD de Ischigualasto")
    ap.add_argument("--espejar-x", action="store_true", help="si el sensor quedó mirando al revés")
    ap.add_argument("--invertir-y", action="store_true")
    ap.add_argument("--probar", action="store_true")
    a = ap.parse_args()
    if a.probar:
        probar()
    correr(a.entrada, a.destino, a.espejar_x, a.invertir_y)
