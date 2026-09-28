// El mundo del Triásico de Ischigualasto: un solo terreno continuo que se recorre de oeste a este.
//   x ∈ [-120, 10]  el río meandroso con barras de arena
//   x ∈ [10, 70]    el bosque de Dicroidium y coníferas
//   x ∈ [70, 160]   la llanura aluvial, con el volcán en el horizonte
// Un solo mundo (y no escenas sueltas) para que la cámara viaje sin cortes: el paso del
// río al bosque es un paseo, no un fundido a negro.
//
// Dos "eras" en el mismo terreno: Triásico (uEra = 0) y hoy (uEra = 1, el Valle de la Luna).
// El shader mezcla los colores en la placa: el paso de 231 millones de años es un uniform.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { ImprovedNoise } from 'three/addons/math/ImprovedNoise.js';
import { Sky } from 'three/addons/objects/Sky.js';

const ruido = new ImprovedNoise();
export const LIMITES = { x0: -130, x1: 170, z0: -120, z1: 120 };
export const NIVEL_AGUA = -1.1;

const lisa = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

export function fbm(x, z, octavas = 5) {
  let t = 0, a = 1, f = 1, n = 0;
  for (let i = 0; i < octavas; i++) { t += a * ruido.noise(x * f, z * f, 0.37); n += a; a *= 0.5; f *= 2.03; }
  return t / n;
}

export function cauceZ(x) { return 10 * Math.sin(x * 0.035) + 4 * Math.sin(x * 0.09 + 1.3); }

/** cuánto "río" hay en x: 1 en la zona del río, 0 fuera */
export const hayRio = (x) => lisa(40, 5, x);
export const distRio = (x, z) => Math.abs(z - cauceZ(x));

export function altura(x, z) {
  const d = distRio(x, z);
  const rio = hayRio(x);
  let h = fbm(x * 0.012, z * 0.012, 5) * 7 + fbm(x * 0.08, z * 0.08, 3) * 0.5;
  // cerca del río el valle es más plano: si no, el agua quedaría colgada de las lomas
  h *= 1 - 0.8 * rio * Math.exp(-((d / 30) ** 2));
  h -= rio * 3.0 * Math.exp(-((d / 6) ** 2));                // el cauce
  h += rio * 0.5 * Math.exp(-(((d - 11) / 3) ** 2));          // el albardón (la orilla alta)
  h *= 1 - 0.65 * lisa(60, 95, x);                            // la llanura aluvial
  // charcas de la llanura
  for (const [cx, cz, r] of [[100, 18, 9], [125, -22, 7]]) {
    h -= 1.8 * Math.exp(-(((x - cx) ** 2 + (z - cz) ** 2) / (r * r)));
  }
  // bordes del mundo: se levantan en barrancas (en el Triásico lomas; hoy, los farallones rojos)
  const borde = Math.max(lisa(80, 118, Math.abs(z)), lisa(LIMITES.x1 - 30, LIMITES.x1, x), lisa(LIMITES.x0 + 30, LIMITES.x0, x));
  h += borde * 22 * (0.7 + 0.3 * fbm(x * 0.05, z * 0.05, 2));
  return h;
}

/** zona del mundo para reglas de hábitat */
export function zona(x) { return x < 10 ? 'rio' : x < 70 ? 'bosque' : 'llanura'; }

// -------------------------------------------------------------------------------------------
// terreno con dos eras
// -------------------------------------------------------------------------------------------

function colorTriasico(x, z, h) {
  const d = distRio(x, z), rio = hayRio(x);
  const humedo = rio * Math.exp(-((d / 9) ** 2));
  const arena = rio * Math.exp(-(((d - 7) / 2.2) ** 2)) * (0.6 + 0.4 * fbm(x * 0.2, z * 0.2, 2));
  const veg = THREE.MathUtils.clamp(0.45 + fbm(x * 0.05, z * 0.05, 3) * 1.6 - humedo, 0, 1) * (x > 8 && x < 75 ? 1.0 : 0.55);
  const c = new THREE.Color(0.24, 0.17, 0.11);                          // barro
  c.lerp(new THREE.Color(0.10, 0.08, 0.06), humedo);                    // barro húmedo
  c.lerp(new THREE.Color(0.56, 0.46, 0.33), arena);                     // barras de arena
  // hojarasca y helechos: NO hay pasto en el Triásico (las gramíneas llegan 150 Ma después)
  const hojarasca = 0.5 + 0.5 * fbm(x * 0.6, z * 0.6, 2);
  c.lerp(new THREE.Color().setRGB(0.10 + 0.14 * hojarasca, 0.14 + 0.07 * hojarasca, 0.06), veg * 0.75);
  c.lerp(new THREE.Color(0.38, 0.26, 0.17), THREE.MathUtils.clamp((h - 6) / 14, 0, 1));   // lomas
  return c;
}

function colorHoy(x, z, h) {
  // Valle de la Luna: arcilla gris blanquecina abajo, estratos rojos en las barrancas
  const c = new THREE.Color(0.66, 0.63, 0.57);
  c.lerp(new THREE.Color(0.58, 0.55, 0.50), 0.5 + 0.5 * fbm(x * 0.3, z * 0.3, 2));
  const banda = 0.5 + 0.5 * Math.sin(h * 1.1 + fbm(x * 0.02, z * 0.02, 2) * 3);
  const rojo = new THREE.Color(0.42 + 0.1 * banda, 0.14 + 0.05 * banda, 0.08);
  // las lomas y barrancas pasan a los estratos rojos: desde 1,5 m ya se ven las bandas
  c.lerp(rojo, THREE.MathUtils.clamp((h - 1.5) / 5, 0, 1));
  return c;
}

export function crearTerreno(calidad) {
  const ancho = LIMITES.x1 - LIMITES.x0, largo = LIMITES.z1 - LIMITES.z0;
  const seg = Math.round(300 * Math.max(0.5, calidad));
  const g = new THREE.PlaneGeometry(ancho, largo, seg, Math.round(seg * largo / ancho));
  g.rotateX(-Math.PI / 2);
  g.translate((LIMITES.x0 + LIMITES.x1) / 2, 0, (LIMITES.z0 + LIMITES.z1) / 2);
  const p = g.attributes.position;
  const tri = new Float32Array(p.count * 3), hoy = new Float32Array(p.count * 3);
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i), h = altura(x, z);
    p.setY(i, h);
    colorTriasico(x, z, h).toArray(tri, i * 3);
    colorHoy(x, z, h).toArray(hoy, i * 3);
  }
  g.setAttribute('color', new THREE.BufferAttribute(tri, 3));
  g.setAttribute('colorHoy', new THREE.BufferAttribute(hoy, 3));
  g.computeVertexNormals();

  const uniforms = { uEra: { value: 0 }, uCeniza: { value: 0 }, uTiempo: { value: 0 } };
  const m = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.93, metalness: 0 });
  m.onBeforeCompile = (sh) => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nattribute vec3 colorHoy;\nuniform float uEra;\nvarying vec3 vPosMundo;')
      .replace('#include <color_vertex>', '#include <color_vertex>\nvColor = mix(vColor, colorHoy, uEra);')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvPosMundo = (modelMatrix * vec4(transformed, 1.0)).xyz;');
    sh.fragmentShader = sh.fragmentShader
      .replace('#include <common>', `#include <common>
uniform float uCeniza; uniform float uEra; varying vec3 vPosMundo;
float h21(vec2 p){ return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float vn(vec2 p){ vec2 i = floor(p), f = fract(p); f = f*f*(3.0-2.0*f);
  return mix(mix(h21(i), h21(i+vec2(1,0)), f.x), mix(h21(i+vec2(0,1)), h21(i+vec2(1,1)), f.x), f.y); }
// grietas de barro seco (hoy): distancia al borde de celdas de Voronoi
float grietas(vec2 p){ vec2 i = floor(p), f = fract(p); float d1 = 8.0, d2 = 8.0;
  for (int y=-1; y<=1; y++) for (int x=-1; x<=1; x++){ vec2 g = vec2(x,y);
    vec2 o = vec2(h21(i+g), h21(i+g+17.3)); float d = length(g + o - f);
    if (d < d1){ d2 = d1; d1 = d; } else if (d < d2) d2 = d; }
  return d2 - d1; }`)
      .replace('#include <color_fragment>', `#include <color_fragment>
float detalle = 0.82 + 0.36 * vn(vPosMundo.xz * 1.7) * vn(vPosMundo.xz * 0.23);
diffuseColor.rgb *= detalle;
float gr = smoothstep(0.0, 0.05, grietas(vPosMundo.xz * 0.9));
diffuseColor.rgb *= mix(1.0, mix(0.35, 1.0, gr), uEra);
float capa = smoothstep(0.25, 0.75, uCeniza + (vn(vPosMundo.xz * 0.35) - 0.5) * 0.6);
diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.50, 0.49, 0.47) * (0.85 + 0.3 * vn(vPosMundo.xz * 3.0)), capa * (1.0 - uEra));`);
  };
  const malla = new THREE.Mesh(g, m);
  malla.receiveShadow = true;
  malla.name = 'terreno';
  return { malla, uniforms };
}

export function crearAgua() {
  const g = new THREE.PlaneGeometry(140, 240, 140, 240);
  g.rotateX(-Math.PI / 2);
  g.translate(-60, NIVEL_AGUA, 0);
  const m = new THREE.MeshStandardMaterial({ color: 0x4d5a45, roughness: 0.06, metalness: 0.35, transparent: true, opacity: 0.86 });
  const uniforms = { uTiempo: { value: 0 } };
  m.onBeforeCompile = (sh) => {
    sh.uniforms.uTiempo = uniforms.uTiempo;
    sh.vertexShader = sh.vertexShader
      .replace('#include <common>', '#include <common>\nuniform float uTiempo;')
      .replace('#include <begin_vertex>', `#include <begin_vertex>
transformed.y += sin(position.x * 0.8 + uTiempo * 1.3) * 0.03 + sin(position.z * 1.3 - uTiempo * 0.9) * 0.02;`);
  };
  const malla = new THREE.Mesh(g, m);
  malla.name = 'agua';
  return { malla, uniforms };
}

// -------------------------------------------------------------------------------------------
// cielo, luz, volcán
// -------------------------------------------------------------------------------------------

export function crearCielo(escena, calidad) {
  const cielo = new Sky();
  cielo.scale.setScalar(4000);
  const u = cielo.material.uniforms;
  u.turbidity.value = 6; u.rayleigh.value = 1.6; u.mieCoefficient.value = 0.006; u.mieDirectionalG.value = 0.85;
  escena.add(cielo);
  const sol = new THREE.DirectionalLight(0xfff0dd, 2.6);
  sol.castShadow = calidad >= 0.7;
  sol.shadow.mapSize.set(2048, 2048);
  Object.assign(sol.shadow.camera, { left: -50, right: 50, top: 50, bottom: -50, near: 1, far: 300 });
  sol.shadow.bias = -0.0005;
  escena.add(sol, sol.target);
  const relleno = new THREE.HemisphereLight(0xbfd2e6, 0x4a3a2a, 0.9);
  escena.add(relleno);
  escena.fog = new THREE.FogExp2(0xc9cfd2, 0.006);

  const dirSol = new THREE.Vector3();
  function ponerSol(elevacion, azimut, color = 0xfff0dd, bruma = 0xc9cfd2, densidad = 0.006) {
    const fi = THREE.MathUtils.degToRad(90 - elevacion), th = THREE.MathUtils.degToRad(azimut);
    dirSol.setFromSphericalCoords(1, fi, th);
    u.sunPosition.value.copy(dirSol);
    sol.color.set(color);
    escena.fog.color.set(bruma);
    escena.fog.density = densidad;
  }
  function seguir(camara) {        // la sombra acompaña al visitante (una caja de 100 m, no el mundo entero)
    sol.position.copy(camara.position).addScaledVector(dirSol, 150);
    sol.target.position.copy(camara.position);
  }
  return { cielo, sol, relleno, ponerSol, seguir, uniforms: u };
}

export function crearVolcan() {
  const perfil = [[260, 0], [190, 40], [110, 95], [55, 125], [38, 122]].map(([r, h]) => new THREE.Vector2(r, h));
  const g = new THREE.LatheGeometry(perfil, 64);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i);
    p.setY(i, p.getY(i) + fbm(x * 0.02, z * 0.02, 3) * 14);
  }
  g.computeVertexNormals();
  const m = new THREE.MeshStandardMaterial({ color: 0x2a2523, roughness: 1 });
  const v = new THREE.Mesh(g, m);
  v.position.set(420, -12, -260);
  v.name = 'volcan';
  return v;
}

// -------------------------------------------------------------------------------------------
// flora: GLB horneados de Blender, dibujados con InstancedMesh (cientos de plantas, 1 draw call c/u)
// -------------------------------------------------------------------------------------------

const REGLAS = [
  // nombre, cantidad base, regla de hábitat, escala
  ['neocalamites', 260, (x, z) => hayRio(x) > 0.5 && distRio(x, z) > 6.5 && distRio(x, z) < 15, [0.8, 1.3]],
  ['dicroidium', 90, (x, z) => (hayRio(x) > 0.5 && distRio(x, z) > 16), [0.8, 1.2]],
  ['dicroidium', 170, (x) => zona(x) === 'bosque', [0.8, 1.35]],
  ['dicroidium', 18, (x) => zona(x) === 'llanura', [0.7, 1.0]],
  ['conifera', 55, (x, z) => zona(x) === 'bosque' || (zona(x) === 'llanura' && Math.abs(z) > 35), [0.8, 1.2]],
  ['helecho', 600, (x, z) => (zona(x) !== 'llanura' && distRio(x, z) > 8) || fbm(x * 0.3, z * 0.3, 1) > 0.3, [0.6, 1.4]],
  ['tronco_caido', 30, (x, z) => zona(x) === 'bosque' || (hayRio(x) > 0.5 && distRio(x, z) > 8 && distRio(x, z) < 14), [0.8, 1.3]],
  ['roca_arenisca', 70, (x) => zona(x) === 'llanura', [0.5, 1.8]],
];

function azar(semilla) { let s = semilla >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

export async function crearFlora(escena, calidad, base = 'assets/') {
  const cargador = new GLTFLoader();
  const moldes = {};
  const nombres = [...new Set(REGLAS.map((r) => r[0]))];
  await Promise.all(nombres.map(async (n) => {
    try {
      const gltf = await cargador.loadAsync(`${base}${n}.glb`);
      let malla = null;
      gltf.scene.traverse((o) => { if (o.isMesh && !malla) malla = o; });
      moldes[n] = { geometria: malla.geometry, material: malla.material };
    } catch (e) {
      console.warn(`flora: no se pudo cargar ${n}.glb, uso una forma simple`, e?.message);
      moldes[n] = moldeSimple(n);
    }
  }));

  const aleatorio = azar(231);
  const porNombre = {};
  for (const [nombre, cant, regla, [e0, e1]] of REGLAS) {
    const objetivo = Math.round(cant * calidad);
    let hechos = 0, intentos = 0;
    while (hechos < objetivo && intentos < objetivo * 40) {
      intentos++;
      const x = LIMITES.x0 + 20 + aleatorio() * (LIMITES.x1 - LIMITES.x0 - 40);
      const z = -85 + aleatorio() * 170;
      if (!regla(x, z)) continue;
      const y = altura(x, z);
      if (y < NIVEL_AGUA + 0.2) continue;
      (porNombre[nombre] ||= []).push({ x, y, z, rot: aleatorio() * Math.PI * 2, esc: e0 + aleatorio() * (e1 - e0) });
      hechos++;
    }
  }
  const instancias = [];
  const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), pos = new THREE.Vector3(), eje = new THREE.Vector3(0, 1, 0);
  for (const [nombre, lista] of Object.entries(porNombre)) {
    const { geometria, material } = moldes[nombre];
    const im = new THREE.InstancedMesh(geometria, material, lista.length);
    im.castShadow = calidad >= 0.7 && nombre !== 'helecho';
    im.receiveShadow = true;
    im.name = `flora_${nombre}`;
    lista.forEach((p, i) => {
      q.setFromAxisAngle(eje, p.rot); s.setScalar(p.esc); pos.set(p.x, p.y - 0.05, p.z);
      im.setMatrixAt(i, m4.compose(pos, q, s));
    });
    im.userData.lista = lista;
    escena.add(im);
    instancias.push(im);
  }
  // para "hoy": la flora se hunde y desaparece (231 millones de años de erosión)
  function era(t) {
    const k = 1 - THREE.MathUtils.smoothstep(t, 0.05, 0.6);
    for (const im of instancias) {
      im.visible = k > 0.01;
      if (!im.visible) continue;
      im.userData.lista.forEach((p, i) => {
        q.setFromAxisAngle(eje, p.rot); s.setScalar(p.esc * k); pos.set(p.x, p.y - 0.05 - (1 - k) * 2, p.z);
        im.setMatrixAt(i, m4.compose(pos, q, s));
      });
      im.instanceMatrix.needsUpdate = true;
    }
  }
  return { instancias, era, conteo: Object.fromEntries(Object.entries(porNombre).map(([k, v]) => [k, v.length])) };
}

function moldeSimple(nombre) {
  const verde = new THREE.MeshStandardMaterial({ color: 0x3a4a22, roughness: 0.8 });
  const marron = new THREE.MeshStandardMaterial({ color: 0x5a4030, roughness: 0.9 });
  if (nombre === 'roca_arenisca') return { geometria: new THREE.DodecahedronGeometry(0.8), material: marron };
  if (nombre === 'tronco_caido') return { geometria: new THREE.CylinderGeometry(0.3, 0.35, 6).rotateZ(Math.PI / 2).translate(0, 0.3, 0), material: marron };
  if (nombre === 'helecho') return { geometria: new THREE.ConeGeometry(0.8, 0.6, 7).translate(0, 0.3, 0), material: verde };
  if (nombre === 'neocalamites') return { geometria: new THREE.CylinderGeometry(0.5, 0.4, 2.6, 8).translate(0, 1.3, 0), material: verde };
  return { geometria: new THREE.ConeGeometry(2.6, 6, 9).translate(0, 5, 0), material: verde };
}
