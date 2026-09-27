"""
Autotests de los juegos de TD, sin TouchDesigner ni sensores.
Correr con: python3 test_juegos_td.py
"""

import math
import time

from juegos_td import JUEGOS, Excavacion, Toque

DT = 1 / 60


def caminar(juego, recorrido, segundos, t0=0.0):
    """Una persona que recorre una lista de puntos en metros, a velocidad de caminata."""
    t = t0
    pasos = int(segundos / DT)
    for i in range(pasos):
        f = i / pasos * (len(recorrido) - 1)
        a, b = recorrido[int(f)], recorrido[min(int(f) + 1, len(recorrido) - 1)]
        u = f - int(f)
        x, y = a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        juego.update(DT, t, [Toque(1, x, y, vx=1.2, vy=0.0)])
        t += DT
    return t


def barrido_completo(W, H, paso=0.3):
    """Ida y vuelta por todo el piso, como diez personas en una noche movida."""
    pts, y, ida = [], 0.2, True
    while y < H:
        pts += [(0.2, y), (W - 0.2, y)] if ida else [(W - 0.2, y), (0.2, y)]
        ida, y = not ida, y + paso
    return pts


def test_registrado():
    assert "excavacion" in JUEGOS


def test_quieto_no_descubre():
    """Sin gente no se descubre nada: la corriente de la sala sola no alcanza."""
    j = Excavacion()
    t = 0.0
    for _ in range(int(20 / DT)):
        j.update(DT, t, [])
        t += DT
    assert j.estado()["huesos"] == 0, j.estado()


def test_pisar_descubre_donde_se_pisa():
    """Caminar sobre el cráneo lo descubre a él y no a un hueso del otro lado."""
    j = Excavacion()
    craneo = next(h for h in j.huesos if h["nombre"] == "cráneo")
    cola = next(h for h in j.huesos if h["nombre"] == "cola")
    cx, cy = craneo["x"], craneo["y"]
    # ida y vuelta por encima, como alguien que "barre" con los pies
    vaiven = [(cx - 0.5, cy), (cx + 0.5, cy), (cx - 0.5, cy + 0.15), (cx + 0.5, cy - 0.15)] * 4
    caminar(j, vaiven, 15)
    assert craneo["visto"], "el cráneo debería estar descubierto"
    assert not cola["visto"], "la cola está lejos y no debería descubrirse"


def test_barrer_todo_completa_y_reinicia():
    j = Excavacion()
    j.espera_completo = 1e9      # que no se reinicie mientras todavía caminan
    t = caminar(j, barrido_completo(j.W, j.H), 90)
    for _ in range(3):
        if j.fase == "completo":
            break
        t = caminar(j, barrido_completo(j.W, j.H), 60, t)
    assert j.fase == "completo", j.estado()
    ev = [e[0] for e in j.sacar_eventos()]
    assert ev.count("hueso") == len(j.huesos) and "completo" in ev
    j.espera_completo = 2.0
    for _ in range(int(3 / DT)):
        j.update(DT, t, [])
        t += DT
    assert j.fase == "excavando" and j.estado()["huesos"] == 0


def test_granos_no_se_escapan():
    j = Excavacion()
    caminar(j, barrido_completo(j.W, j.H), 20)
    x, y, z = j.p[:, 0], j.p[:, 1], j.p[:, 2]
    assert x.min() >= 0 and x.max() <= j.W and y.min() >= 0 and y.max() <= j.H
    assert z.min() >= 0


def test_zonda_es_bucle():
    """En zonda la arena que sale por un borde entra por el otro: nunca se vacía el piso."""
    j = Excavacion(modo="zonda")
    t = 0.0
    for _ in range(int(30 / DT)):
        j.update(DT, t, [])
        t += DT
    assert len(j.p) == j.granos
    assert j.p[:, 0].min() >= 0 and j.p[:, 0].max() <= j.W
    mitad = (j.p[:, 0] < j.W / 2).mean()
    assert 0.3 < mitad < 0.7, f"la arena se amontonó de un lado: {mitad:.2f}"


def test_hallazgo_rompe_el_bloque():
    j = Excavacion(modo="hallazgo")
    assert not j.bloque_roto
    j.update(DT, 0.0, [Toque(1, j.W / 2, j.H / 2, vx=1.0)])
    assert j.bloque_roto
    assert ("bloque", 1) in j.sacar_eventos()


def test_instancias_largos_iguales():
    j = Excavacion()
    j.accion("revelar_todo")
    inst = j.instancias()
    largos = {len(v) for v in inst.values()}
    assert largos == {j.granos + len(j.huesos)}
    assert inst["tipo"].sum() == len(j.huesos)


def test_costo_por_cuadro():
    """Tiene que entrar holgado en los 16,6 ms de un cuadro a 60 fps."""
    j = Excavacion()
    toques = [Toque(i, 1 + i, 2, vx=1.0) for i in range(6)]
    n, t0 = 300, time.perf_counter()
    for i in range(n):
        j.update(DT, i * DT, toques)
    ms = (time.perf_counter() - t0) / n * 1000
    print(f"    costo: {ms:.2f} ms por cuadro con 6 personas y {j.granos} granos")
    assert ms < 8.0, ms


if __name__ == "__main__":
    pruebas = [v for k, v in dict(globals()).items() if k.startswith("test_")]
    fallas = 0
    for p in pruebas:
        try:
            p()
            print(f"OK    {p.__name__}")
        except AssertionError as e:
            fallas += 1
            print(f"FALLA {p.__name__}: {e}")
    print(f"\n{len(pruebas) - fallas}/{len(pruebas)} pasan")
    raise SystemExit(1 if fallas else 0)
