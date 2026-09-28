// Triásico en San Juan · experiencia inmersiva e interactiva (FNS 2026 · Parque Triásico)
//
// Parámetros en la dirección:
//   ?calidad=0.4..1   cantidad de plantas, sombras y resolución (1 = M4 / OMEN i7; 0.5 = notebook)
//   ?ui=0             sin textos (sólo el mundo), para mandar la imagen a TD o Arena
//   ?ws=host:8765     puente de sensores (por defecto, el mismo host que sirve la página)
//   ?capitulo=0..5    arrancar en un capítulo · ?auto=0 no avanza solo
// Teclas: ← → capítulos · 0–5 ir a uno · P simular una persona · F pantalla completa · H ocultar textos

import * as THREE from 'three';
import { crearTerreno, crearAgua, crearCielo, crearVolcan, crearFlora, altura, NIVEL_AGUA } from './mundo.js';
import { crearFauna, ESPECIES } from './fauna.js';
import { crearEntrada } from './entrada.js';
import { crearEfectos } from './efectos.js';
import { CAPITULOS, FICHAS, crearDirector } from './capitulos.js';
import './estilo.css';

const q = new URLSearchParams(location.search);
const CALIDAD = Math.min(1, Math.max(0.2, parseFloat(q.get('calidad') || '1')));
const AUTO = q.get('auto') !== '0';
if (q.get('ui') === '0') document.body.classList.add('sin-ui');
const WS = q.get('ws') ? `ws://${q.get('ws')}` : `ws://${location.hostname || 'localhost'}:8765`;

const $ = (s) => document.querySelector(s);
const cargando = $('#cargando');
const avisar = (t) => { if (cargando) cargando.querySelector('p').textContent = t; };

// -------------------------------------------------------------------------------------------
// motor
// -------------------------------------------------------------------------------------------

const lienzo = $('#lienzo');
const render = new THREE.WebGLRenderer({ canvas: lienzo, antialias: CALIDAD >= 0.6, powerPreference: 'high-performance' });
render.setPixelRatio(Math.min(window.devicePixelRatio, 2) * (CALIDAD >= 0.8 ? 1 : 0.75));
render.toneMapping = THREE.ACESFilmicToneMapping;
render.toneMappingExposure = 0.75;
render.shadowMap.enabled = CALIDAD >= 0.7;
render.shadowMap.type = THREE.PCFSoftShadowMap;

const escena = new THREE.Scene();
const camara = new THREE.PerspectiveCamera(50, 1, 0.1, 5000);

function ajustar() {
  const w = window.innerWidth, h = window.innerHeight;
  render.setSize(w, h, false);
  camara.aspect = w / h;
  // campo horizontal fijo de ~80°: en una pantalla LED de 5760×1080 no se ve todo estirado
  const vfov = 2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(80) / 2) / camara.aspect);
  camara.fov = THREE.MathUtils.clamp(THREE.MathUtils.radToDeg(vfov), 22, 60);
  camara.updateProjectionMatrix();
}
window.addEventListener('resize', ajustar);
ajustar();

// -------------------------------------------------------------------------------------------
// mundo
// -------------------------------------------------------------------------------------------

avisar('Levantando el valle…');
const terreno = crearTerreno(CALIDAD);
escena.add(terreno.malla);
const agua = crearAgua();
escena.add(agua.malla);
const cielo = crearCielo(escena, CALIDAD);
const volcan = crearVolcan();
escena.add(volcan);
const efectos = crearEfectos(escena);
const pmrem = new THREE.PMREMGenerator(render);
const escenaCielo = new THREE.Scene();
let ambiente = null;
function rehacerAmbiente() {
  // el cielo como luz ambiente y reflejo: sin esto el agua se ve negra y la vegetación plana
  escenaCielo.add(cielo.cielo);
  const nuevo = pmrem.fromScene(escenaCielo, 0.02);
  escena.add(cielo.cielo);
  ambiente?.dispose();
  ambiente = nuevo;
  escena.environment = ambiente.texture;
  escena.environmentIntensity = 0.55;
}

avisar('Plantando el bosque de Dicroidium…');
const flora = await crearFlora(escena, CALIDAD, `${import.meta.env.BASE_URL}assets/`);
avisar('Despertando a los animales…');
const fauna = await crearFauna(escena, `${import.meta.env.BASE_URL}modelos/`);

const entrada = crearEntrada(lienzo, { ws: WS });
const director = crearDirector();
if (q.get('capitulo')) director.ir(parseInt(q.get('capitulo'), 10));

// -------------------------------------------------------------------------------------------
// interfaz
// -------------------------------------------------------------------------------------------

const ui = {
  titulo: $('#cap-titulo'), sub: $('#cap-sub'), portada: $('#portada'), ficha: $('#ficha'),
  fichaT: $('#ficha h2'), fichaD: $('#ficha .dato'), fichaX: $('#ficha p.texto'), puntos: $('#puntos'), sensor: $('#sensor'),
};
CAPITULOS.forEach((c, i) => {
  const b = document.createElement('button');
  b.title = c.titulo;
  b.addEventListener('click', () => director.ir(i));
  ui.puntos.appendChild(b);
});
let fichaHasta = 0, fichaActual = null;
function mostrarFicha(clave, segundos = 11) {
  const f = FICHAS[clave];
  if (!f) return;
  fichaActual = clave;
  ui.fichaT.textContent = f.titulo;
  ui.fichaD.textContent = f.dato;
  ui.fichaX.textContent = f.texto;
  ui.ficha.classList.add('visible');
  fichaHasta = reloj.elapsedTime + segundos;
}

// -------------------------------------------------------------------------------------------
// interacción: tocar un animal lo acaricia; tocar el suelo deja una huella; el agua, una onda
// -------------------------------------------------------------------------------------------

const rayo = new THREE.Raycaster();
const ndc = new THREE.Vector2();
const cuerposFauna = fauna.map((a) => a.grupo);
function tocar(t) {
  ndc.set(t.u * 2 - 1, -(t.v * 2 - 1));
  rayo.setFromCamera(ndc, camara);
  const golpe = rayo.intersectObjects(cuerposFauna, true)[0];
  if (golpe && golpe.distance < 60) {
    const a = golpe.object.userData.animal;
    if (a && !a.fosil) { a.acariciar(); mostrarFicha(a.clave); return; }
  }
  const suelo = rayo.intersectObjects([agua.malla, terreno.malla], false)[0];
  if (suelo && suelo.distance < 120) {
    const p = suelo.point.clone();
    if (suelo.object === agua.malla && agua.malla.visible) p.y = NIVEL_AGUA - 1;
    efectos.tocarSuelo(p, Math.atan2(p.x - camara.position.x, p.z - camara.position.z));
  }
}

// -------------------------------------------------------------------------------------------
// bucle
// -------------------------------------------------------------------------------------------

const reloj = new THREE.Clock();
const suave = { pos: new THREE.Vector3(), mira: new THREE.Vector3(), desvio: 0, mirarX: 0, mirarY: 0, era: 0, ceniza: 0, volcan: 0 };
const visitante = { presente: false, punto: new THREE.Vector3(), corre: false };
const mezclarColor = (a, b, k) => new THREE.Color(a).lerp(new THREE.Color(b), k);
let ambienteEn = 0.5, primero = true, fpsAcum = 0, fpsCuadros = 0, fps = 0, capMostrado = -1, fichaAuto = 0;

function cuadro() {
  const dt = Math.min(0.05, reloj.getDelta());
  const t = reloj.elapsedTime;
  entrada.actualizar(dt);
  const E = entrada.estado;

  for (const g of E.gestos.splice(0)) {
    if (g === 'siguiente') director.siguiente();
    else if (g === 'anterior') director.anteriorCap();
    else if (g.startsWith('capitulo_')) director.ir(parseInt(g.split('_')[1], 10));
  }
  for (const toque of E.toques) if (toque.nuevo) tocar(toque);

  const D = director.update(dt, AUTO);
  const cap = D.capitulo, ant = D.anterior || cap, k = D.mezcla;

  // cámara: recorrido del capítulo + paralaje por el cuerpo + mirar alrededor arrastrando
  const arr = entrada.consumirArrastre();
  suave.mirarX = THREE.MathUtils.clamp(suave.mirarX - arr.dx * 2.5, -1.2, 1.2) * (1 - dt * 0.25);
  suave.mirarY = THREE.MathUtils.clamp(suave.mirarY - arr.dy * 1.5, -0.4, 0.5) * (1 - dt * 0.25);
  const desvioObj = E.cuerpo.presente ? (E.cuerpo.x - 0.5) * 2 : Math.sin(t * 0.07) * 0.3;
  suave.desvio += (desvioObj - suave.desvio) * Math.min(1, dt * 1.5);
  const { pos, mira } = director.camara(suave.desvio);
  pos.y = Math.max(pos.y, altura(pos.x, pos.z) + 1.7);                // nunca bajo tierra: ojos a 1,7 m
  if (primero || D.cambio) { suave.pos.copy(pos); suave.mira.copy(mira); primero = false; D.cambio = false; }
  suave.pos.lerp(pos, Math.min(1, dt * 1.2));
  suave.mira.lerp(mira, Math.min(1, dt * 1.2));
  camara.position.copy(suave.pos);
  camara.lookAt(suave.mira);
  camara.rotateY(suave.mirarX);
  camara.rotateX(suave.mirarY);

  // luz, bruma, era y ceniza: mezcla suave entre capítulos
  const sol = { elev: THREE.MathUtils.lerp(ant.sol.elevacion, cap.sol.elevacion, k), az: THREE.MathUtils.lerp(ant.sol.azimut, cap.sol.azimut, k) };
  cielo.ponerSol(sol.elev, sol.az, mezclarColor(ant.sol.color, cap.sol.color, k), mezclarColor(ant.sol.bruma, cap.sol.bruma, k),
    THREE.MathUtils.lerp(ant.sol.densidad, cap.sol.densidad, k));
  cielo.seguir(camara);
  suave.era += (cap.era - suave.era) * Math.min(1, dt * 0.35);
  suave.ceniza += (cap.ceniza - suave.ceniza) * Math.min(1, dt * 0.4);
  suave.volcan += (cap.volcan - suave.volcan) * Math.min(1, dt * 0.5);
  terreno.uniforms.uEra.value = suave.era;
  terreno.uniforms.uCeniza.value = Math.max(suave.ceniza, cap.fosil ? 1 - suave.era : 0) * (1 - suave.era);
  agua.uniforms.uTiempo.value = t;
  agua.malla.material.opacity = 0.86 * (1 - suave.era);
  agua.malla.visible = suave.era < 0.98;
  flora.era(suave.era);
  cielo.uniforms.turbidity.value = 6 + suave.ceniza * 14;
  render.toneMappingExposure = 0.75 - suave.ceniza * 0.25 + suave.era * 0.05;

  // el visitante: un punto a 7 m delante de la cámara, en el suelo
  const adelante = new THREE.Vector3(); camara.getWorldDirection(adelante); adelante.y = 0; adelante.normalize();
  visitante.punto.copy(camara.position).addScaledVector(adelante, 7);
  visitante.punto.y = altura(visitante.punto.x, visitante.punto.z);
  visitante.presente = E.cuerpo.presente;
  visitante.corre = E.cuerpo.corre;
  for (const a of fauna) {
    a.fosil = cap.fosil ? Math.min(1, a.fosil + dt * 0.25) : 0;
    if (a.pos.distanceTo(camara.position) < 160) a.update(dt, t, visitante);
  }
  efectos.update(dt, t, { camara, volcan: suave.volcan, cenizaCant: suave.ceniza, volcanPos: volcan.position });

  // textos
  if (capMostrado !== D.indice) {
    capMostrado = D.indice;
    ui.titulo.textContent = cap.titulo;
    ui.sub.textContent = cap.subtitulo;
    document.body.dataset.capitulo = cap.clave;
    [...ui.puntos.children].forEach((b, i) => b.classList.toggle('activo', i === D.indice));
    fichaAuto = t + 6;
    fichaHasta = 0;                 // la ficha del capítulo anterior no queda colgada
    ambienteEn = t + 3.2;          // cuando termina la mezcla de luz, rehacer los reflejos
  }
  if (ambienteEn && t > ambienteEn) { ambienteEn = 0; rehacerAmbiente(); }
  // fichas automáticas del capítulo (si nadie tocó un animal)
  if (cap.fichas && t > fichaAuto && t > fichaHasta) {
    const lista = cap.fichas;
    const idx = (lista.indexOf(fichaActual) + 1) % lista.length;
    mostrarFicha(lista[idx], 10);
    fichaAuto = t + 14;
  }
  if (t > fichaHasta) ui.ficha.classList.remove('visible');
  ui.sensor.classList.toggle('conectado', E.conectado);
  ui.sensor.classList.toggle('presente', E.cuerpo.presente);

  render.render(escena, camara);

  fpsAcum += dt; fpsCuadros++;
  if (fpsAcum > 1) { fps = Math.round(fpsCuadros / fpsAcum); fpsAcum = 0; fpsCuadros = 0; }
  requestAnimationFrame(cuadro);
}

cargando?.classList.add('listo');
setTimeout(() => cargando?.remove(), 1200);
requestAnimationFrame(cuadro);

// para las pruebas automáticas y para depurar desde la consola
window.__triasico = {
  director, fauna, flora: flora.conteo, especies: Object.keys(ESPECIES), render, camara,
  get fps() { return fps; }, get info() { return render.info.render; }, tocar, entrada,
};
