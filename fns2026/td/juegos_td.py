"""
Juegos del piso, pasados de la app web a TouchDesigner.

Por qué este archivo no importa nada de TD:
la lógica (física, reglas, puntaje) se prueba afuera, con `python3 test_juegos_td.py`,
igual que el tracker tiene sus autotests sin sensores. Dentro de TD lo usa una
extensión (`ExtJuego`, en construir_red_fns.py) que sólo lee toques y copia arrays a
un Script CHOP. Si mañana cambia TD, esto no se toca.

Mismo contrato que `PISO.registrarJuego` de la app, para que pasar un juego sea copiar
la lógica y no rediseñarla:
    update(dt, t, toques)   física a paso fijo, lo llama el motor
    estado()                dict chico que sale por OSC (a Arena y al panel)
    instancias()            arrays por instancia para el Geometry COMP (tx, ty, tz, rot, esc, tipo)
    reset(), accion(nombre)

Unidades: METROS. Origen en la esquina del piso del lado del público, a la izquierda,
x a lo ancho, y hacia el fondo, z hacia arriba (el mismo sistema que PEDIDO-SALA, así
la sala entera usa estas coordenadas sin traducir).
"""

import math
import numpy as np

JUEGOS = {}


def registrar(cls):
    JUEGOS[cls.id] = cls
    return cls


class Toque:
    """Una pisada ya en metros. La arma la extensión a partir de /wall/touch/<n>/*."""
    __slots__ = ("id", "x", "y", "vx", "vy", "edad", "nuevo")

    def __init__(self, id, x, y, vx=0.0, vy=0.0, edad=0.0, nuevo=False):
        self.id, self.x, self.y = id, x, y
        self.vx, self.vy, self.edad, self.nuevo = vx, vy, edad, nuevo

    @property
    def velocidad(self):
        return math.hypot(self.vx, self.vy)


# ---------------------------------------------------------------------------
# Excavación: el piso de arena de Ischigualasto que se barre y descubre huesos
# ---------------------------------------------------------------------------

# Huesos de un Herrerasaurus, en coordenadas relativas al piso (0..1) y tamaño en metros.
# El orden es el orden de armado del esqueleto en la pared: el cráneo al final,
# para que el remate sea la cabeza y no una vértebra.
HUESOS_HERRERASAURUS = [
    ("vertebras",  0.50, 0.50, 0.60),
    ("cadera",     0.42, 0.55, 0.35),
    ("fémur_izq",  0.36, 0.40, 0.30),
    ("fémur_der",  0.62, 0.64, 0.30),
    ("cola",       0.20, 0.70, 0.55),
    ("costillas",  0.58, 0.40, 0.40),
    ("brazo",      0.72, 0.30, 0.22),
    ("garra",      0.82, 0.22, 0.15),
    ("cráneo",     0.80, 0.72, 0.35),
]


@registrar
class Excavacion:
    """
    La arena se mueve con las tres fuerzas del VALS (corriente, pie, rozamiento).
    No hay una "máscara de descubrimiento" aparte: un hueso aparece cuando de verdad
    quedó poca arena encima. Así el piso queda peinado por donde pasó la gente y lo
    que se descubre es consecuencia de eso, no un temporizador disfrazado.
    """

    id = "excavacion"
    nombre = "Excavación"
    MODOS = ("sedimento", "zonda", "hallazgo")

    # Ajustes. Los que más se tocan en el predio están arriba.
    granos = 3000
    radio_pie = 0.45          # m: alcance del empuje del pie
    fuerza_pie = 5.0
    remolino = 0.6            # el pie arrastra el aire, no sólo aparta
    empuje_arriba = 1.8       # lo que hace que el grano despegue y no resbale
    umbral_hueso = 0.5        # si queda menos de la mitad de la arena inicial encima, el hueso se ve
    celda = 0.25              # m: resolución del mapa de cobertura
    viento_zonda = 1.4        # m/s en modo zonda
    espera_completo = 20.0    # s con el esqueleto armado antes de volver a tapar

    def __init__(self, ancho_m=6.0, alto_m=4.0, semilla=7, modo="sedimento"):
        self.W, self.H = float(ancho_m), float(alto_m)
        self.rng = np.random.default_rng(semilla)
        self.modo = modo
        self.nx = max(1, int(round(self.W / self.celda)))
        self.ny = max(1, int(round(self.H / self.celda)))
        self.reset()

    # -- ciclo de vida -------------------------------------------------------

    def reset(self):
        n = self.granos
        self.p = np.column_stack([
            self.rng.uniform(0, self.W, n),
            self.rng.uniform(0, self.H, n),
            np.zeros(n),
        ])
        self.v = np.zeros((n, 3))
        self.rot = self.rng.uniform(0, 2 * math.pi, n)
        self.esc = self.rng.uniform(0.6, 1.4, n)
        # Densidad inicial por celda: la referencia para decidir si un hueso está tapado.
        self.base = self._cobertura()
        self.huesos = [
            {"nombre": nom, "x": fx * self.W, "y": fy * self.H, "tam": tam, "visto": False, "cuando": None}
            for nom, fx, fy, tam in HUESOS_HERRERASAURUS
        ]
        self.t = 0.0
        self.fase = "excavando"
        self.t_completo = None
        self.bloque_roto = self.modo != "hallazgo"
        self.eventos = []    # lo que pasó en este cuadro, para OSC (se vacía al leerlo)

    def cambiar_modo(self, modo):
        if modo not in self.MODOS:
            raise ValueError(f"modo desconocido: {modo}")
        self.modo = modo
        self.reset()

    def accion(self, nombre):
        if nombre == "siguiente_modo":
            i = self.MODOS.index(self.modo)
            self.cambiar_modo(self.MODOS[(i + 1) % len(self.MODOS)])
        elif nombre == "revelar_todo":        # para el operador: cerrar la ronda a mano
            for h in self.huesos:
                self._descubrir(h)

    # -- física --------------------------------------------------------------

    def update(self, dt, t, toques):
        self.t = t
        p, v = self.p, self.v
        en_aire = p[:, 2] > 0.002

        # 1) corriente de la sala: nunca quieto del todo
        k, w = 0.9, 0.35
        v[:, 0] += 0.08 * np.sin(p[:, 1] * k + t * w) * dt
        v[:, 1] += 0.08 * np.cos(p[:, 0] * k + t * w * 0.7) * dt
        if self.modo == "zonda":
            v[:, 0] += self.viento_zonda * dt * (0.6 + 0.4 * en_aire)
            v[:, 2] += 0.4 * dt * (self.rng.random(len(p)) < 0.01)

        # 2) el pie: radial + remolino + hacia arriba
        for tq in toques:
            dx = p[:, 0] - tq.x
            dy = p[:, 1] - tq.y
            d = np.hypot(dx, dy) + 1e-4
            cerca = d < self.radio_pie
            if not cerca.any():
                continue
            caida = (1.0 - d[cerca] / self.radio_pie) ** 2
            impulso = self.fuerza_pie * (0.35 + min(tq.velocidad, 3.0))
            ux, uy = dx[cerca] / d[cerca], dy[cerca] / d[cerca]
            v[cerca, 0] += (ux * impulso - uy * self.remolino * impulso) * caida * dt
            v[cerca, 1] += (uy * impulso + ux * self.remolino * impulso) * caida * dt
            v[cerca, 2] += self.empuje_arriba * caida * (0.5 + min(tq.velocidad, 2.0)) * dt * 10
            if not self.bloque_roto and math.hypot(tq.x - self.W / 2, tq.y - self.H / 2) < 0.6:
                self._romper_bloque()

        # 3) gravedad falsa y rozamiento: casi nulo en el aire, alto apoyado
        v[:, 2] -= 9.8 * dt
        roz = np.where(en_aire, 0.3, 6.0)[:, None]
        v[:, :2] *= np.exp(-roz * dt)
        p += v * dt
        suelo = p[:, 2] < 0
        p[suelo, 2] = 0
        v[suelo, 2] = 0
        self.rot += v[:, 0] * dt * 3.0

        # bordes: en zonda la arena que se va entra por el otro lado (bucle sin corte);
        # si no, rebota suave para que el piso no se vacíe hacia afuera
        if self.modo == "zonda":
            p[:, 0] %= self.W
            p[:, 1] %= self.H
        else:
            for eje, lim in ((0, self.W), (1, self.H)):
                fuera = (p[:, eje] < 0) | (p[:, eje] > lim)
                p[:, eje] = np.clip(p[:, eje], 0, lim)
                v[fuera, eje] *= -0.3

        self._revisar_huesos()
        self._revisar_fase(t)

    def _romper_bloque(self):
        """Modo hallazgo: el bloque del centro estalla y reparte arena y huesos."""
        self.bloque_roto = True
        cx, cy = self.W / 2, self.H / 2
        ang = self.rng.uniform(0, 2 * math.pi, len(self.p))
        r = self.rng.uniform(0, 0.4, len(self.p))
        self.p[:, 0] = cx + np.cos(ang) * r
        self.p[:, 1] = cy + np.sin(ang) * r
        vel = self.rng.uniform(1.5, 4.0, len(self.p))
        self.v[:, 0] = np.cos(ang) * vel
        self.v[:, 1] = np.sin(ang) * vel
        self.v[:, 2] = self.rng.uniform(1.0, 3.5, len(self.p))
        self.eventos.append(("bloque", 1))

    # -- reglas --------------------------------------------------------------

    def _cobertura(self):
        apoyados = self.p[self.p[:, 2] < 0.01]
        h, _, _ = np.histogram2d(apoyados[:, 0], apoyados[:, 1],
                                 bins=[self.nx, self.ny], range=[[0, self.W], [0, self.H]])
        return h

    def _revisar_huesos(self):
        if not self.bloque_roto:
            return
        cob = self._cobertura()
        base = self.base
        for h in self.huesos:
            if h["visto"]:
                continue
            r = h["tam"] / 2
            i0, i1 = int((h["x"] - r) / self.celda), int((h["x"] + r) / self.celda) + 1
            j0, j1 = int((h["y"] - r) / self.celda), int((h["y"] + r) / self.celda) + 1
            i0, j0 = max(i0, 0), max(j0, 0)
            ahora = cob[i0:i1, j0:j1].sum()
            antes = base[i0:i1, j0:j1].sum()
            if antes > 0 and ahora / antes < self.umbral_hueso:
                self._descubrir(h)

    def _descubrir(self, h):
        if h["visto"]:
            return
        h["visto"] = True
        h["cuando"] = self.t
        idx = self.huesos.index(h)
        self.eventos.append(("hueso", idx))

    def _revisar_fase(self, t):
        if self.fase == "excavando" and all(h["visto"] for h in self.huesos):
            self.fase = "completo"
            self.t_completo = t
            self.eventos.append(("completo", 1))
        elif self.fase == "completo" and t - self.t_completo > self.espera_completo:
            modo = self.modo
            self.reset()
            self.modo = modo
            self.eventos.append(("reinicio", 1))

    # -- salida --------------------------------------------------------------

    def estado(self):
        vistos = sum(h["visto"] for h in self.huesos)
        return {
            "juego": self.id,
            "modo": self.modo,
            "fase": self.fase,
            "huesos": vistos,
            "total": len(self.huesos),
            "progreso": vistos / len(self.huesos),
        }

    def sacar_eventos(self):
        ev, self.eventos = self.eventos, []
        return ev

    def instancias(self):
        """Arrays del mismo largo para el Script CHOP → Geometry COMP (instancing).
        tipo 0 = grano, 1 = hueso. Los huesos van al final y sólo los descubiertos."""
        vistos = [h for h in self.huesos if h["visto"]]
        n = len(vistos)
        tx = np.concatenate([self.p[:, 0], [h["x"] for h in vistos]])
        ty = np.concatenate([self.p[:, 1], [h["y"] for h in vistos]])
        tz = np.concatenate([self.p[:, 2], np.zeros(n)])
        rot = np.concatenate([self.rot, np.zeros(n)])
        esc = np.concatenate([self.esc, [h["tam"] for h in vistos]])
        tipo = np.concatenate([np.zeros(len(self.p)), np.ones(n)])
        return {"tx": tx, "ty": ty, "tz": tz, "rot": rot, "esc": esc, "tipo": tipo}
