// Efectos: huellas tridáctilas y polvo al tocar el suelo, ondas en el agua, humo del volcán
// y la lluvia de ceniza. Todo con pocos objetos reciclados (nada de crear y tirar por cuadro).

import * as THREE from 'three';
import { altura, NIVEL_AGUA } from './mundo.js';

function texturaHuella() {
  // huella de terópodo de tres dedos, dibujada en un canvas: sin imágenes externas
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  g.fillStyle = 'rgba(0,0,0,0)';
  g.fillRect(0, 0, 128, 128);
  g.fillStyle = 'rgba(25,16,10,0.85)';
  g.beginPath(); g.ellipse(64, 86, 16, 20, 0, 0, Math.PI * 2); g.fill();          // talón
  for (const [ang, lar] of [[-0.45, 44], [0, 52], [0.45, 44]]) {                   // tres dedos
    g.save(); g.translate(64, 76); g.rotate(ang);
    g.beginPath(); g.ellipse(0, -lar / 2 - 6, 7, lar / 2, 0, 0, Math.PI * 2); g.fill();
    g.beginPath(); g.moveTo(-4, -lar - 4); g.lineTo(0, -lar - 16); g.lineTo(4, -lar - 4); g.fill();   // uña
    g.restore();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function texturaSuave() {
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  gr.addColorStop(0, 'rgba(255,255,255,1)');
  gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr;
  g.fillRect(0, 0, 64, 64);
  return new THREE.CanvasTexture(c);
}

export function crearEfectos(escena) {
  const suave = texturaSuave();

  // huellas (reciclo 40)
  const matHuella = new THREE.MeshBasicMaterial({ map: texturaHuella(), transparent: true, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -4 });
  const huellas = Array.from({ length: 40 }, () => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.55, 0.55).rotateX(-Math.PI / 2), matHuella.clone());
    m.visible = false; m.userData.vida = 0; escena.add(m); return m;
  });
  let iHuella = 0;

  // polvo (sprites reciclados)
  const polvo = Array.from({ length: 60 }, () => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: suave, color: 0xb59a78, transparent: true, depthWrite: false, opacity: 0 }));
    s.userData = { vida: 0, v: new THREE.Vector3() }; escena.add(s); return s;
  });
  let iPolvo = 0;

  // ondas en el agua
  const ondas = Array.from({ length: 12 }, () => {
    const m = new THREE.Mesh(new THREE.RingGeometry(0.8, 1, 48).rotateX(-Math.PI / 2),
      new THREE.MeshBasicMaterial({ color: 0xd9e2d0, transparent: true, opacity: 0, depthWrite: false }));
    m.userData.vida = 0; escena.add(m); return m;
  });
  let iOnda = 0;

  // humo del volcán: columna de sprites que suben y se abren
  const humo = Array.from({ length: 70 }, (_, i) => {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: suave, color: 0x4a4540, transparent: true, depthWrite: false, opacity: 0, fog: false }));
    s.userData = { t: i / 70 }; escena.add(s); return s;
  });

  // ceniza: nube de puntos alrededor de la cámara
  const nCeniza = 6000;
  const posCeniza = new Float32Array(nCeniza * 3);
  for (let i = 0; i < nCeniza; i++) { posCeniza[i * 3] = (Math.random() - 0.5) * 80; posCeniza[i * 3 + 1] = Math.random() * 30; posCeniza[i * 3 + 2] = (Math.random() - 0.5) * 80; }
  const gCeniza = new THREE.BufferGeometry();
  gCeniza.setAttribute('position', new THREE.BufferAttribute(posCeniza, 3));
  const ceniza = new THREE.Points(gCeniza, new THREE.PointsMaterial({ color: 0x9a9690, size: 0.09, transparent: true, opacity: 0, depthWrite: false }));
  ceniza.frustumCulled = false;
  escena.add(ceniza);

  function tocarSuelo(p, rumbo = Math.random() * Math.PI * 2) {
    if (p.y < NIVEL_AGUA + 0.05) {
      const o = ondas[iOnda++ % ondas.length];
      o.position.set(p.x, NIVEL_AGUA + 0.03, p.z); o.userData.vida = 1; o.scale.setScalar(0.2);
      return;
    }
    const h = huellas[iHuella++ % huellas.length];
    h.position.set(p.x, altura(p.x, p.z) + 0.03, p.z);
    h.rotation.y = rumbo;
    h.visible = true; h.userData.vida = 1; h.material.opacity = 0.9;
    for (let k = 0; k < 6; k++) {
      const s = polvo[iPolvo++ % polvo.length];
      s.position.copy(p).add(new THREE.Vector3((Math.random() - 0.5) * 0.4, 0.1, (Math.random() - 0.5) * 0.4));
      s.userData.vida = 1;
      s.userData.v.set((Math.random() - 0.5) * 1.2, 0.5 + Math.random() * 0.8, (Math.random() - 0.5) * 1.2);
      s.scale.setScalar(0.4);
    }
  }

  function update(dt, t, { camara, volcan = 0, cenizaCant = 0, volcanPos }) {
    for (const h of huellas) {
      if (!h.visible) continue;
      h.userData.vida -= dt / 25;               // la huella dura 25 s
      h.material.opacity = Math.max(0, h.userData.vida) * 0.9;
      if (h.userData.vida <= 0) h.visible = false;
    }
    for (const s of polvo) {
      if (s.userData.vida <= 0) { s.material.opacity = 0; continue; }
      s.userData.vida -= dt * 0.7;
      s.position.addScaledVector(s.userData.v, dt);
      s.userData.v.multiplyScalar(1 - dt * 1.5);
      s.scale.setScalar(0.4 + (1 - s.userData.vida) * 1.6);
      s.material.opacity = Math.max(0, s.userData.vida) * 0.5;
    }
    for (const o of ondas) {
      if (o.userData.vida <= 0) { o.material.opacity = 0; continue; }
      o.userData.vida -= dt * 0.5;
      o.scale.setScalar(0.2 + (1 - o.userData.vida) * 3);
      o.material.opacity = o.userData.vida * 0.6;
    }
    // humo: cada sprite sube por la columna y vuelve a empezar (loop continuo)
    for (const s of humo) {
      const u = (s.userData.t + t * 0.02) % 1;
      s.position.set(volcanPos.x + Math.sin(u * 7 + s.userData.t * 30) * 20 * u + u * 60, volcanPos.y + 115 + u * 260, volcanPos.z + Math.cos(u * 5 + s.userData.t * 20) * 20 * u);
      s.scale.setScalar(40 + u * 160);
      s.material.opacity = volcan * 0.55 * Math.sin(u * Math.PI);
    }
    // ceniza: cae y se recicla alrededor de la cámara
    ceniza.material.opacity = cenizaCant * 0.85;
    ceniza.visible = cenizaCant > 0.01;
    if (ceniza.visible) {
      ceniza.position.set(camara.position.x, camara.position.y - 8, camara.position.z);
      const p = gCeniza.attributes.position;
      for (let i = 0; i < nCeniza; i++) {
        let y = p.getY(i) - dt * (1.2 + (i % 7) * 0.12);
        if (y < 0) y += 30;
        p.setY(i, y);
        p.setX(i, p.getX(i) + Math.sin(t * 0.5 + i) * dt * 0.3);
      }
      p.needsUpdate = true;
    }
  }
  return { tocarSuelo, update };
}
