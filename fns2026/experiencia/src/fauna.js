// La fauna de la Formación Ischigualasto (Carniano, ~231 Ma).
//
// Cada animal es PROCEDURAL y articulado (cuello, cola en cadena, patas con muslo y canilla) y
// camina de verdad: el ciclo de paso sale de la velocidad, no de un clip. Así hay animales ya,
// sin esperar a Meshy. Si existe public/modelos/<especie>.glb (Meshy → blender_refinar.py), se
// usa ese modelo con sus animaciones y la lógica de comportamiento es la misma.
//
// Comportamiento amistoso (como en el proyecto de la Mac): pasean, pastan, se acercan a la gente
// sin atacar, se dejan acariciar (bajan la cabeza y mueven la cola) y en la ceniza se vuelven fósil.

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { altura, zona, NIVEL_AGUA, hayRio, distRio, cauceZ } from './mundo.js';

export const ESPECIES = {
  herrerasaurus: {
    nombre: 'Herrerasaurus ischigualastensis', tipo: 'bipedo', largo: 4.0, cadera: 1.05,
    dorso: 0x4a3526, vientre: 0x8a7050, velocidad: 2.2, zona: ['bosque', 'llanura'],
    cuello: 0.7, cola: 0.48, cabeza: 0.42,
  },
  eoraptor: {
    nombre: 'Eoraptor lunensis', tipo: 'bipedo', largo: 1.0, cadera: 0.32,
    dorso: 0x6b5a3a, vientre: 0xb09a74, velocidad: 2.8, zona: ['bosque'], cuello: 0.9, cola: 0.5, cabeza: 0.35,
  },
  eodromaeus: {
    nombre: 'Eodromaeus murphi', tipo: 'bipedo', largo: 1.2, cadera: 0.36,
    dorso: 0x5a4a38, vientre: 0xa99270, velocidad: 3.0, zona: ['bosque'], cuello: 0.8, cola: 0.52, cabeza: 0.36,
  },
  panphagia: {
    nombre: 'Panphagia protos', tipo: 'bipedo', largo: 1.3, cadera: 0.38,
    dorso: 0x5d5a3c, vientre: 0xa8a07a, velocidad: 1.8, zona: ['bosque'], cuello: 1.4, cola: 0.5, cabeza: 0.28,
  },
  hyperodapedon: {
    nombre: 'Hyperodapedon', tipo: 'cuadrupedo', largo: 1.3, cadera: 0.32,
    dorso: 0x5b5043, vientre: 0x8e8068, velocidad: 0.9, zona: ['rio'], cuello: 0.3, cola: 0.35, cabeza: 0.4, pico: true,
  },
  ischigualastia: {
    // 3,5 m y 1-2 t; sin colmillos (sólo procesos caniniformes óseos) — Cox 1962
    nombre: 'Ischigualastia jenseni', tipo: 'cuadrupedo', largo: 3.5, cadera: 0.9,
    dorso: 0x6a5f55, vientre: 0x958878, velocidad: 0.8, zona: ['llanura'], cuello: 0.35, cola: 0.18, cabeza: 0.55, pico: true,
  },
  sanjuansaurus: {
    // herrerasáurido de ~3 m, de la base de la formación (Alcober y Martínez 2010)
    nombre: 'Sanjuansaurus gordilloi', tipo: 'bipedo', largo: 3.0, cadera: 0.85,
    dorso: 0x503a2a, vientre: 0x8c7456, velocidad: 2.4, zona: ['llanura'], cuello: 0.7, cola: 0.5, cabeza: 0.4,
  },
  saurosuchus: {
    // el depredador más grande de Ischigualasto NO era un dinosaurio: un pseudosuquio (línea
    // de los cocodrilos) de 5,5 a 7 m, con las patas rectas debajo del cuerpo
    nombre: 'Saurosuchus galilei', tipo: 'cuadrupedo', largo: 6.0, cadera: 1.2,
    dorso: 0x3f3a30, vientre: 0x7d7260, velocidad: 1.6, zona: ['llanura', 'rio'], cuello: 0.45, cola: 0.5, cabeza: 0.7,
  },
  exaeretodon: {
    // cinodonte traversodóntido (pariente de los mamíferos), de hasta 1,8 m; con Hyperodapedon,
    // lo más abundante de la formación
    nombre: 'Exaeretodon argentinus', tipo: 'cuadrupedo', largo: 1.8, cadera: 0.45,
    dorso: 0x5c4a3a, vientre: 0x9a8468, velocidad: 1.1, zona: ['rio', 'bosque'], cuello: 0.3, cola: 0.2, cabeza: 0.45,
  },
};

const HUESO = new THREE.Color(0xd8cdb4);
const tmp = new THREE.Vector3();

// -------------------------------------------------------------------------------------------
// armado procedural
// -------------------------------------------------------------------------------------------

function elipsoide(rx, ry, rz, mat, seg = 16) {
  const g = new THREE.SphereGeometry(1, seg, Math.round(seg * 0.75));
  g.scale(rx, ry, rz);
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true;
  return m;
}

function segmento(largo, r0, r1, mat) {
  // cilindro que sale del origen hacia +x (así el pivote queda en la articulación)
  const g = new THREE.CylinderGeometry(r1, r0, largo, 10, 1);
  g.rotateZ(-Math.PI / 2);
  g.translate(largo / 2, 0, 0);
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true;
  return m;
}

function pataVertical(largo, r0, r1, mat) {
  const g = new THREE.CylinderGeometry(r1, r0, largo, 8, 1);
  g.translate(0, -largo / 2, 0);
  const m = new THREE.Mesh(g, mat);
  m.castShadow = true;
  return m;
}

function armar(esp) {
  const L = esp.largo, H = esp.cadera;
  const dorso = new THREE.MeshStandardMaterial({ color: esp.dorso, roughness: 0.75 });
  const vientre = new THREE.MeshStandardMaterial({ color: esp.vientre, roughness: 0.8 });
  const raiz = new THREE.Group();
  const cuerpo = new THREE.Group();
  cuerpo.position.y = H;
  raiz.add(cuerpo);
  const cuad = esp.tipo === 'cuadrupedo';
  const torso = elipsoide(L * (cuad ? 0.28 : 0.2), L * (cuad ? 0.13 : 0.085), L * (cuad ? 0.15 : 0.075), dorso);
  torso.position.x = cuad ? 0 : L * 0.06;
  cuerpo.add(torso);
  const panza = elipsoide(L * (cuad ? 0.25 : 0.17), L * (cuad ? 0.1 : 0.065), L * (cuad ? 0.13 : 0.065), vientre);
  panza.position.set(torso.position.x, -L * 0.03, 0);
  cuerpo.add(panza);

  // cuello: cadena de 3 segmentos hacia adelante y arriba
  const cuello = [];
  let padre = new THREE.Group();
  padre.position.x = torso.position.x + L * (cuad ? 0.24 : 0.17);
  cuerpo.add(padre);
  const largoCuello = L * 0.1 * esp.cuello;
  for (let i = 0; i < 3; i++) {
    const art = new THREE.Group();
    if (i > 0) art.position.x = largoCuello;
    art.rotation.z = cuad ? 0.05 : (i === 0 ? 0.55 : -0.15);
    art.add(segmento(largoCuello, L * 0.04 * (1 - i * 0.15), L * 0.035 * (1 - i * 0.15), dorso));
    padre.add(art);
    cuello.push(art);
    padre = art;
  }
  // cabeza
  const cabeza = new THREE.Group();
  cabeza.position.x = largoCuello;
  cabeza.rotation.z = cuad ? -0.1 : -0.45;
  padre.add(cabeza);
  const craneo = elipsoide(L * 0.07 * esp.cabeza * 2.2, L * 0.035 * esp.cabeza * 2.2, L * 0.03 * esp.cabeza * 2.2, dorso);
  craneo.position.x = L * 0.05 * esp.cabeza * 2;
  cabeza.add(craneo);
  const hocico = elipsoide(L * 0.05 * esp.cabeza * 2, L * 0.02 * esp.cabeza * 2, L * 0.022 * esp.cabeza * 2, esp.pico ? vientre : dorso);
  hocico.position.set(L * 0.12 * esp.cabeza * 2, -L * 0.012, 0);
  cabeza.add(hocico);
  const ojoMat = new THREE.MeshStandardMaterial({ color: 0x1a120a, roughness: 0.2 });
  for (const s of [-1, 1]) {
    const ojo = elipsoide(L * 0.008, L * 0.008, L * 0.008, ojoMat, 8);
    ojo.position.set(L * 0.07 * esp.cabeza * 2, L * 0.012, s * L * 0.025 * esp.cabeza * 2);
    cabeza.add(ojo);
  }

  // cola: 8 segmentos hacia atrás (-x), cada uno hijo del anterior: el meneo se propaga
  const cola = [];
  padre = new THREE.Group();
  padre.position.x = torso.position.x - L * (cuad ? 0.26 : 0.18);
  padre.rotation.y = Math.PI;
  cuerpo.add(padre);
  const nCola = 8, largoCola = (L * esp.cola) / nCola;
  for (let i = 0; i < nCola; i++) {
    const art = new THREE.Group();
    if (i > 0) art.position.x = largoCola;
    art.rotation.z = i === 0 ? (cuad ? -0.25 : -0.08) : -0.02;
    const r = L * (cuad ? 0.07 : 0.055) * (1 - i / nCola) + 0.004;
    art.add(segmento(largoCola * 1.05, r, r * 0.82, dorso));
    padre.add(art);
    cola.push(art);
    padre = art;
  }

  // patas: muslo + canilla + pie
  const patas = [];
  const posiciones = cuad
    ? [[L * 0.17, 1], [L * 0.17, -1], [-L * 0.17, 1], [-L * 0.17, -1]]
    : [[0, 1], [0, -1]];
  for (const [px, lado] of posiciones) {
    const muslo = new THREE.Group();
    muslo.position.set(px, 0, lado * L * (cuad ? 0.12 : 0.06));
    const lm = H * 0.52, lc = H * 0.5;
    muslo.add(pataVertical(lm, L * (cuad ? 0.045 : 0.05), L * 0.03, dorso));
    const canilla = new THREE.Group();
    canilla.position.y = -lm;
    canilla.add(pataVertical(lc, L * 0.028, L * 0.018, dorso));
    const pie = elipsoide(L * 0.04, L * 0.012, L * 0.022, dorso, 8);
    pie.position.set(L * 0.02, -lc, 0);
    canilla.add(pie);
    muslo.add(canilla);
    cuerpo.add(muslo);
    patas.push({ muslo, canilla, fase: (cuad ? (px > 0 ? 0 : Math.PI) : 0) + (lado > 0 ? 0 : Math.PI) });
  }
  // brazos cortos de los bípedos (Herrerasaurus tenía manos de 3 dedos que agarraban)
  if (!cuad) {
    for (const lado of [-1, 1]) {
      const brazo = new THREE.Group();
      brazo.position.set(torso.position.x + L * 0.13, -L * 0.02, lado * L * 0.06);
      brazo.rotation.z = -0.9;
      brazo.add(pataVertical(H * 0.35, L * 0.018, L * 0.01, dorso));
      cuerpo.add(brazo);
    }
  }
  for (const m of [dorso, vientre]) m.userData.color0 = m.color.clone();
  return { raiz, cuerpo, cuello, cabeza, cola, patas, materiales: [dorso, vientre] };
}

// -------------------------------------------------------------------------------------------
// un animal
// -------------------------------------------------------------------------------------------

export class Animal {
  constructor(clave, x, z, rumbo = 0) {
    this.clave = clave;
    this.esp = ESPECIES[clave];
    this.partes = armar(this.esp);
    this.grupo = this.partes.raiz;
    this.grupo.userData.animal = this;
    this.grupo.traverse((o) => { o.userData.animal = this; });
    this.pos = new THREE.Vector3(x, altura(x, z), z);
    this.rumbo = rumbo;
    this.vel = 0;
    this.fase = Math.random() * 10;
    this.estado = 'pasear';
    this.tEstado = 0;
    this.destino = this.nuevoDestino();
    this.caricia = 0;
    this.fosil = 0;
    this.mixer = null;
  }

  nuevoDestino() {
    // un punto cerca, dentro de su zona y fuera del agua
    for (let i = 0; i < 30; i++) {
      const x = this.pos.x + (Math.random() - 0.5) * 30;
      const z = this.pos.z + (Math.random() - 0.5) * 30;
      if (!this.esp.zona.includes(zona(x))) continue;
      if (altura(x, z) < NIVEL_AGUA + 0.15) continue;
      if (this.clave === 'hyperodapedon' && hayRio(x) > 0.5 && distRio(x, z) > 14) continue;   // pastan cerca del agua
      return new THREE.Vector3(x, 0, z);
    }
    return this.pos.clone();
  }

  acariciar() {
    this.caricia = 3.0;
    this.estado = 'caricia';
    this.tEstado = 0;
  }

  update(dt, t, visitante) {
    const esp = this.esp;
    this.tEstado += dt;
    let objetivo = this.destino, velObjetivo = esp.velocidad * 0.45;

    if (this.fosil > 0) {
      velObjetivo = 0;
    } else if (this.caricia > 0) {
      this.caricia -= dt;
      velObjetivo = 0;
      if (this.caricia <= 0) { this.estado = 'pasear'; this.destino = this.nuevoDestino(); }
    } else if (visitante && visitante.presente && this.pos.distanceTo(visitante.punto) < 28 && this.estado !== 'pastar') {
      // se acercan a la gente, sin atacar: se frenan a una distancia prudente y la miran
      objetivo = visitante.punto;
      const d = tmp.copy(this.pos).setY(0).distanceTo(tmp.set(visitante.punto.x, 0, visitante.punto.z));
      const cerca = 2.2 + esp.largo * 0.8 + (this.orden || 0) * 1.2;
      velObjetivo = d > cerca ? esp.velocidad * (visitante.corre ? 0.9 : 0.5) : 0;
      this.estado = 'acercarse';
    } else {
      if (this.estado === 'acercarse') this.estado = 'pasear';
      if (this.estado === 'pastar') {
        velObjetivo = 0;
        if (this.tEstado > 4 + Math.random() * 3) { this.estado = 'pasear'; this.tEstado = 0; this.destino = this.nuevoDestino(); }
      } else if (tmp.copy(this.pos).setY(0).distanceTo(this.destino.clone().setY(0)) < 1.2) {
        this.estado = Math.random() < 0.6 ? 'pastar' : 'pasear';
        this.tEstado = 0;
        this.destino = this.nuevoDestino();
      }
    }

    // girar hacia el objetivo (suave) y avanzar
    const dx = objetivo.x - this.pos.x, dz = objetivo.z - this.pos.z;
    if (Math.hypot(dx, dz) > 0.3) {
      const deseado = Math.atan2(-dz, dx);
      let dif = ((deseado - this.rumbo + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
      this.rumbo += dif * Math.min(1, dt * 2.2);
    }
    this.vel += (velObjetivo - this.vel) * Math.min(1, dt * 2.5);
    this.pos.x += Math.cos(this.rumbo) * this.vel * dt;
    this.pos.z -= Math.sin(this.rumbo) * this.vel * dt;
    const suelo = altura(this.pos.x, this.pos.z);
    this.pos.y = suelo;

    this.animar(dt, t);
    this.grupo.position.copy(this.pos);
    this.grupo.rotation.y = this.rumbo;
    if (this.mixer) this.mixer.update(dt * Math.max(0.3, this.vel / esp.velocidad * 2));
  }

  animar(dt, t) {
    const p = this.partes, esp = this.esp, L = esp.largo;
    const ritmo = this.vel / (L * 0.35 + 0.1);
    this.fase += dt * ritmo * 2.4;
    const f = this.fase;
    const paso = Math.min(1, this.vel / (esp.velocidad * 0.3));
    for (const pata of p.patas) {
      const s = Math.sin(f + pata.fase);
      pata.muslo.rotation.z = s * 0.55 * paso;
      pata.canilla.rotation.z = (Math.max(0, -Math.cos(f + pata.fase)) * 0.9) * paso;
    }
    // cuerpo: rebote del paso + respiración
    p.cuerpo.position.y = esp.cadera + Math.abs(Math.sin(f)) * 0.03 * L * paso + Math.sin(t * 1.7) * 0.004 * L;
    // cola: onda que viaja por la cadena; con caricia se menea rápido
    const meneo = this.caricia > 0 ? 0.28 : 0.08 + 0.1 * paso;
    const velCola = this.caricia > 0 ? 9 : 2.2;
    p.cola.forEach((art, i) => { art.rotation.y = Math.sin(t * velCola - i * 0.6 + this.fase * 0.3) * meneo; });
    // cabeza: pastar (abajo), caricia (baja y ladea), o mirar alrededor
    let cabeceo = Math.sin(t * 0.7 + this.fase) * 0.08;
    if (this.estado === 'pastar') cabeceo = -0.6 + Math.sin(t * 3) * 0.08;
    if (this.caricia > 0) cabeceo = -0.35 + Math.sin(t * 5) * 0.05;
    p.cuello[0].rotation.y = Math.sin(t * 0.5 + this.fase) * 0.25 * (1 - paso * 0.6);
    p.cuello[1].rotation.z += ((esp.tipo === 'cuadrupedo' ? 0 : -0.15) + cabeceo - p.cuello[1].rotation.z) * Math.min(1, dt * 3);
    // fosilización: se echa de lado, se aplana y toma color de hueso
    if (this.fosil > 0) {
      p.cuerpo.rotation.x = -this.fosil * 1.3;
      p.cuerpo.position.y = esp.cadera * (1 - this.fosil * 0.75);
      for (const m of p.materiales) m.color.lerp(HUESO, Math.min(1, dt * 0.6 * this.fosil));
    } else {
      // al volver al Triásico (el ciclo recomienza) recupera la postura y el color
      p.cuerpo.rotation.x *= 1 - Math.min(1, dt * 2);
      for (const m of p.materiales) m.color.lerp(m.userData.color0, Math.min(1, dt * 1.5));
    }
  }
}

// -------------------------------------------------------------------------------------------
// la manada entera
// -------------------------------------------------------------------------------------------

const POBLACION = [
  // especie, cantidad, centro x, centro z (el z se corrige al cauce para los del río)
  ['hyperodapedon', 9, -60, null],
  ['hyperodapedon', 5, -20, null],
  ['herrerasaurus', 1, 35, -8],
  ['herrerasaurus', 1, 110, 10],
  ['eoraptor', 6, 30, 6],
  ['eodromaeus', 3, 50, -10],
  ['panphagia', 3, 45, 15],
  ['ischigualastia', 5, 105, -5],
  ['exaeretodon', 6, -40, null],
  ['exaeretodon', 3, 20, 12],
  ['sanjuansaurus', 1, 125, 0],
  ['saurosuchus', 1, 90, -25],
];

export async function crearFauna(escena, base = 'modelos/') {
  const animales = [];
  let orden = 0;
  for (const [clave, cant, cx, cz] of POBLACION) {
    for (let i = 0; i < cant; i++) {
      const x = cx + (Math.random() - 0.5) * 16;
      const z = cz === null ? cauceZ(x) + (Math.random() < 0.5 ? -1 : 1) * (9 + Math.random() * 3) : cz + (Math.random() - 0.5) * 16;
      const a = new Animal(clave, x, z, Math.random() * Math.PI * 2);
      a.orden = orden++ % 4;
      escena.add(a.grupo);
      animales.push(a);
    }
  }
  // modelos de Meshy, si están: reemplazan la forma procedural de esa especie
  const cargador = new GLTFLoader();
  // modelos/lista.json dice qué especies tienen modelo (["herrerasaurus", ...]); así no se
  // sondea archivo por archivo y la consola queda limpia en el evento
  let disponibles = [];
  try { disponibles = await (await fetch(`${base}lista.json`)).json(); } catch { /* sin lista: todas procedurales */ }
  await Promise.all(disponibles.filter((c) => ESPECIES[c]).map(async (clave) => {
    try {
      const gltf = await cargador.loadAsync(`${base}${clave}.glb`);
      for (const a of animales.filter((x) => x.clave === clave)) usarModelo(a, gltf);
      console.info(`fauna: ${clave} con el modelo de Meshy`);
    } catch { /* sin modelo: queda la procedural */ }
  }));
  return animales;
}

function usarModelo(animal, gltf) {
  const modelo = gltf.scene.clone(true);
  const caja = new THREE.Box3().setFromObject(modelo);
  const largo = Math.max(caja.max.x - caja.min.x, caja.max.z - caja.min.z) || 1;
  modelo.scale.setScalar(animal.esp.largo / largo);
  modelo.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.userData.animal = animal; } });
  const p = animal.partes;
  p.cuerpo.visible = false;
  animal.grupo.add(modelo);
  if (gltf.animations?.length) {
    animal.mixer = new THREE.AnimationMixer(modelo);
    const clip = gltf.animations.find((c) => /walk|camin|run/i.test(c.name)) || gltf.animations[0];
    animal.mixer.clipAction(clip).play();
  }
}
