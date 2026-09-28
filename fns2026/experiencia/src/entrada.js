// Todo lo que entra, unificado en un solo estado. Da igual si viene del mouse, de una pantalla
// táctil, del teclado o de los sensores (LiDAR, cámara, Kinect) a través del puente de Node:
// la experiencia sólo lee `entrada.estado`.
//
//   estado.toques      [{ id, u, v, nuevo }]  u, v en 0..1 sobre la pantalla (0,0 = arriba izquierda)
//   estado.cuerpo      { presente, x (0..1), corre }
//   estado.gestos      cola de gestos para consumir: 'siguiente', 'anterior', 'brazos_arriba', 'salto'
//   estado.ultimoUso   segundos desde la última interacción (para el modo atractor)

export function crearEntrada(lienzo, { ws } = {}) {
  const estado = {
    toques: [], cuerpo: { presente: false, x: 0.5, corre: false }, gestos: [], ultimoUso: 999,
    arrastre: { dx: 0, dy: 0 }, conectado: false, fuente: 'mouse',
  };
  const punteros = new Map();
  let xAnterior = 0.5, tAnterior = performance.now();

  const uv = (e) => {
    const r = lienzo.getBoundingClientRect();
    return { u: (e.clientX - r.left) / r.width, v: (e.clientY - r.top) / r.height };
  };
  lienzo.addEventListener('pointerdown', (e) => {
    lienzo.setPointerCapture(e.pointerId);
    const p = { id: `p${e.pointerId}`, ...uv(e), nuevo: true, t0: performance.now(), x0: e.clientX, y0: e.clientY };
    punteros.set(e.pointerId, p);
    estado.ultimoUso = 0; estado.fuente = 'mouse';
  });
  lienzo.addEventListener('pointermove', (e) => {
    const p = punteros.get(e.pointerId);
    if (!p) return;
    const a = uv(e);
    estado.arrastre.dx += a.u - p.u;
    estado.arrastre.dy += a.v - p.v;
    Object.assign(p, a);
    estado.ultimoUso = 0;
  });
  const soltar = (e) => {
    const p = punteros.get(e.pointerId);
    punteros.delete(e.pointerId);
    // toque largo (más de 1,2 s casi sin moverse) = siguiente capítulo, para pantallas sin teclado
    if (p && performance.now() - p.t0 > 1200 && Math.hypot(e.clientX - p.x0, e.clientY - p.y0) < 20) estado.gestos.push('siguiente');
  };
  lienzo.addEventListener('pointerup', soltar);
  lienzo.addEventListener('pointercancel', soltar);

  window.addEventListener('keydown', (e) => {
    estado.ultimoUso = 0;
    if (e.key === 'ArrowRight' || e.key === ' ') estado.gestos.push('siguiente');
    if (e.key === 'ArrowLeft') estado.gestos.push('anterior');
    if (/^[0-5]$/.test(e.key)) estado.gestos.push(`capitulo_${e.key}`);
    if (e.key === 'p') { estado.cuerpo.presente = !estado.cuerpo.presente; estado.fuente = 'teclado'; }
    if (e.key === 'f') document.documentElement.requestFullscreen?.();
    if (e.key === 'h') document.body.classList.toggle('sin-ui');
  });

  // sensores por el puente (node server/puente.mjs): ws://host:8765
  let socket = null, reintento = 1000;
  const toquesSensor = new Map();
  function conectar() {
    if (!ws) return;
    try { socket = new WebSocket(ws); } catch { return; }
    socket.onopen = () => { estado.conectado = true; reintento = 1000; };
    socket.onclose = () => { estado.conectado = false; setTimeout(conectar, (reintento = Math.min(reintento * 2, 15000))); };
    socket.onerror = () => socket.close();
    socket.onmessage = (m) => {
      let d; try { d = JSON.parse(m.data); } catch { return; }
      if (d.tipo === 'estado') {
        toquesSensor.clear();
        for (const t of d.toques || []) toquesSensor.set(t.id, { id: `s${t.id}`, u: t.u, v: t.v, nuevo: !!t.nuevo });
        if (d.cuerpo) {
          const ahora = performance.now();
          const vx = Math.abs(d.cuerpo.x - xAnterior) / Math.max(0.001, (ahora - tAnterior) / 1000);
          xAnterior = d.cuerpo.x; tAnterior = ahora;
          estado.cuerpo = { presente: !!d.cuerpo.presente, x: d.cuerpo.x ?? 0.5, corre: vx > 0.35 };
        }
        if ((d.toques || []).length || d.cuerpo?.presente) { estado.ultimoUso = 0; estado.fuente = 'sensor'; }
      } else if (d.tipo === 'gesto') {
        estado.gestos.push(d.nombre === 'brazos_arriba' ? 'siguiente' : d.nombre);
        estado.ultimoUso = 0;
      }
    };
  }
  conectar();

  function actualizar(dt) {
    estado.ultimoUso += dt;
    estado.toques = [...punteros.values(), ...toquesSensor.values()].map((p) => ({ ...p }));
    for (const p of punteros.values()) p.nuevo = false;
    for (const p of toquesSensor.values()) p.nuevo = false;
    // sin sensor de cuerpo, el mouse hace de visitante: si se mueve, "hay alguien"
    if (estado.fuente === 'mouse' && punteros.size) {
      const p = [...punteros.values()][0];
      estado.cuerpo = { presente: true, x: p.u, corre: false };
    } else if (estado.fuente === 'mouse' && estado.ultimoUso > 6) {
      estado.cuerpo = { ...estado.cuerpo, presente: false };
    }
  }
  function consumirArrastre() { const a = { ...estado.arrastre }; estado.arrastre.dx = estado.arrastre.dy = 0; return a; }
  return { estado, actualizar, consumirArrastre };
}
