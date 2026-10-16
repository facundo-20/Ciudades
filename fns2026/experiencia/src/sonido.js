// El sonido de la sala en la web: los mismos archivos sintetizados que Unity
// (pipeline/sonido/sonido_triasico.py → public/sonido/). Ambiente por capítulo que se funde, el
// volcán desde el cono y, en cada animal cerca de la cámara, pisadas al ritmo de sus patas y su voz.
//
// El navegador arranca el audio recién después de un gesto (tocar, una tecla). En la sala, Chrome
// se abre con --autoplay-policy=no-user-gesture-required y suena desde el principio. ?sonido=0 lo apaga.
import * as THREE from 'three';

const PESO = {
  eoraptor: 'liviano', eodromaeus: 'liviano', pisanosaurus: 'liviano', panphagia: 'liviano', hyperodapedon: 'liviano',
  exaeretodon: 'medio', chromogisaurus: 'medio', sanjuansaurus: 'medio',
  herrerasaurus: 'pesado', ischigualastia: 'pesado', saurosuchus: 'pesado',
};
const BARRO = new Set(['titulo', 'rio', 'bosque']);

export function crearSonido(camara, base) {
  const nada = { capitulo() {}, update() {}, animal() {}, voz() {}, volcan() {}, activo: false };
  if (new URLSearchParams(location.search).get('sonido') === '0') return nada;
  const oido = new THREE.AudioListener();
  camara.add(oido);
  const ctx = oido.context;
  const destrabar = () => { if (ctx.state !== 'running') ctx.resume().catch(() => {}); };
  for (const e of ['pointerdown', 'keydown', 'touchstart']) window.addEventListener(e, destrabar);
  destrabar();

  const cargador = new THREE.AudioLoader();
  const buffers = {};
  const pedidos = {};
  function cargar(nombre) {
    if (buffers[nombre]) return Promise.resolve(buffers[nombre]);
    pedidos[nombre] ??= cargador.loadAsync(`${base}${nombre}.ogg`).then((b) => (buffers[nombre] = b)).catch(() => null);
    return pedidos[nombre];
  }
  const azar = (lista) => lista[Math.floor(Math.random() * lista.length)];

  // ambiente: dos pistas que se cruzan (igual potencia)
  const pistas = [new THREE.Audio(oido), new THREE.Audio(oido)];
  let actual = 0, mezcla = 1, clave = '';
  async function capitulo(c) {
    if (c === clave) return;
    clave = c;
    const b = await cargar(`ambiente_${c}`);
    if (!b || c !== clave) return;
    actual = 1 - actual;
    const p = pistas[actual];
    if (p.isPlaying) p.stop();
    p.setBuffer(b);
    p.setLoop(true);
    p.setVolume(0);
    p.offset = Math.random() * b.duration * 0.9;
    p.play();
    mezcla = 0;
  }

  // el volcán: fuente en el cono, se oye desde muy lejos
  let fuenteVolcan = null;
  function volcan(objeto) {
    fuenteVolcan = new THREE.PositionalAudio(oido);
    fuenteVolcan.setRefDistance(300);
    fuenteVolcan.setRolloffFactor(1);
    fuenteVolcan.setVolume(0);
    objeto.add(fuenteVolcan);
    cargar('volcan').then((b) => { if (b) { fuenteVolcan.setBuffer(b); fuenteVolcan.setLoop(true); fuenteVolcan.play(); } });
  }

  // animales: una fuente 3D cada uno, creada recién cuando están cerca
  const pesoDe = (a) => PESO[a.clave] || 'medio';
  function fuenteDe(a) {
    if (!a.sonido) {
      a.sonido = new THREE.PositionalAudio(oido);
      a.sonido.setRefDistance(pesoDe(a) === 'pesado' ? 6 : pesoDe(a) === 'liviano' ? 1.5 : 3);
      a.sonido.setRolloffFactor(1.2);
      a.grupo.add(a.sonido);
      a.proximaVoz = performance.now() / 1000 + 8 + Math.random() * 25;
      a.pisoAnterior = null;
    }
    return a.sonido;
  }
  async function tocar(a, nombre, volumen) {
    const b = await cargar(nombre);
    if (!b || ctx.state !== 'running') return;
    const f = fuenteDe(a);
    // PositionalAudio toca un buffer por vez: para superponer (pasos + voz) se usa una fuente corta
    const s = ctx.createBufferSource();
    s.buffer = b;
    s.playbackRate.value = 0.94 + Math.random() * 0.12;
    const g = ctx.createGain();
    g.gain.value = volumen;
    s.connect(g).connect(f.panner);
    s.start();
  }
  function voz(a) { tocar(a, `voz_${a.clave}_${Math.floor(Math.random() * 3)}`, 0.9); }

  function animal(a, distancia) {
    if (distancia > 70) return;                    // lejos: ni se crea la fuente
    fuenteDe(a);
    const ahora = performance.now() / 1000;
    if (ahora > a.proximaVoz) { voz(a); a.proximaVoz = ahora + 14 + Math.random() * 30; }
    // pisadas: cada vez que una pata se apoya (2 por ciclo en bípedos, 4 en cuadrúpedos)
    const porCiclo = a.esp.tipo === 'cuadrupedo' ? 4 : 2;
    const piso = Math.floor(a.fase / (2 * Math.PI / porCiclo));
    if (a.pisoAnterior !== null && piso !== a.pisoAnterior && a.vel > 0.15) {
      tocar(a, `pisada_${pesoDe(a)}_${BARRO.has(clave) ? 'barro' : 'seco'}_${Math.floor(Math.random() * 3)}`, 0.5 + Math.random() * 0.25);
    }
    a.pisoAnterior = piso;
  }

  function update(dt, { volcanActividad = 0, fundido = 0 } = {}) {
    mezcla = Math.min(1, mezcla + dt / 3);
    const general = 0.9 * (1 - 0.75 * fundido);
    pistas[actual].setVolume(general * Math.sin(mezcla * Math.PI / 2));
    const otra = pistas[1 - actual];
    otra.setVolume(general * Math.cos(mezcla * Math.PI / 2));
    if (mezcla >= 1 && otra.isPlaying) otra.stop();
    if (fuenteVolcan) fuenteVolcan.setVolume(0.9 * volcanActividad * (1 - 0.75 * fundido));
  }

  return { capitulo, update, animal, voz, volcan, activo: true, contexto: ctx, cargados: () => Object.keys(buffers).length };
}
