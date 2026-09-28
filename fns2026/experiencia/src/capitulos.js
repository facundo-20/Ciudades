// El guion: seis capítulos que recorren el mismo mundo. Cada uno define por dónde viaja la
// cámara, la luz, el volcán, la ceniza y la era (Triásico → hoy), y qué dice la pantalla.
// Los textos son de divulgación: validarlos con un paleontólogo de la UNSJ antes de la fiesta.

import * as THREE from 'three';

export const CAPITULOS = [
  {
    clave: 'titulo', duracion: 14,
    titulo: 'ISCHIGUALASTO', subtitulo: 'San Juan, hace 231 millones de años · El amanecer de los dinosaurios',
    camara: { desde: [-120, 26, 60], hasta: [-95, 14, 40], mira: [-60, 0, 0] },
    sol: { elevacion: 6, azimut: 250, color: 0xffb070, bruma: 0xd8b89a, densidad: 0.008 },
    volcan: 0, ceniza: 0, era: 0,
  },
  {
    clave: 'rio', duracion: 45,
    titulo: 'El río', subtitulo: 'Una llanura con ríos que serpentean, lluvias de temporada y mucha vida',
    camara: { desde: [-95, 3.2, 26], hasta: [-30, 2.6, 20], mira: [0, 0, -10] },
    sol: { elevacion: 22, azimut: 230, color: 0xffe2b8, bruma: 0xc9cfd2, densidad: 0.0065 },
    volcan: 0.2, ceniza: 0, era: 0,
    fichas: ['hyperodapedon', 'neocalamites'],
  },
  {
    clave: 'bosque', duracion: 45,
    titulo: 'El bosque de Dicroidium', subtitulo: 'Frondas que se bifurcan, coníferas y helechos. Todavía no existía el pasto',
    camara: { desde: [8, 2.2, 12], hasta: [62, 2.2, -4], mira: [120, 1, -20] },
    sol: { elevacion: 40, azimut: 200, color: 0xfff0dd, bruma: 0xb9c4bf, densidad: 0.009 },
    volcan: 0.35, ceniza: 0, era: 0,
    fichas: ['eoraptor', 'herrerasaurus', 'panphagia', 'dicroidium'],
  },
  {
    clave: 'llanura', duracion: 40,
    titulo: 'La llanura y el volcán', subtitulo: 'Al oeste, volcanes activos en el borde del continente, donde mucho después se levantarían los Andes',
    camara: { desde: [78, 4, 24], hasta: [128, 3.4, 4], mira: [420, 60, -260] },
    sol: { elevacion: 30, azimut: 180, color: 0xffe7c9, bruma: 0xc6c2bb, densidad: 0.005 },
    volcan: 1, ceniza: 0, era: 0,
    fichas: ['ischigualastia', 'herrerasaurus'],
  },
  {
    clave: 'ceniza', duracion: 30,
    titulo: 'La lluvia de ceniza', subtitulo: 'El barro de las crecidas y la ceniza fueron tapando los restos. La ceniza permite fecharlos: 231 millones de años',
    camara: { desde: [128, 3.4, 4], hasta: [118, 5, 16], mira: [104, 0, -4] },
    sol: { elevacion: 14, azimut: 170, color: 0xb88a60, bruma: 0x6f6862, densidad: 0.02 },
    volcan: 1, ceniza: 1, era: 0, fosil: true,
    fichas: ['ceniza'],
  },
  {
    clave: 'hoy', duracion: 40,
    titulo: 'Hoy: el Valle de la Luna', subtitulo: 'Parque Provincial Ischigualasto · Patrimonio de la Humanidad (UNESCO, 2000) · Conocelos en el MuPa',
    camara: { desde: [118, 6, 16], hasta: [60, 34, 70], mira: [30, 2, -20] },
    sol: { elevacion: 48, azimut: 215, color: 0xfff4e6, bruma: 0xd9cdb8, densidad: 0.0012 },
    volcan: 0, ceniza: 0, era: 1, fosil: true,
    fichas: ['hoy'],
  },
];

export const FICHAS = {
  herrerasaurus: {
    titulo: 'Herrerasaurus ischigualastensis',
    dato: 'Uno de los dinosaurios más antiguos del mundo',
    texto: 'Carnívoro bípedo de unos 4 metros, con manos de tres dedos que agarraban. Lleva el nombre de Victorino Herrera, el baqueano que encontró el primer ejemplar en 1959.',
  },
  eoraptor: {
    titulo: 'Eoraptor lunensis',
    dato: '"El ladrón del amanecer" del Valle de la Luna',
    texto: 'Del tamaño de un perro mediano (alrededor de 1 metro), liviano y rápido. Es de los dinosaurios más primitivos que se conocen: casi el retrato del primer dinosaurio.',
  },
  panphagia: {
    titulo: 'Panphagia protos',
    dato: '"El que come de todo"',
    texto: 'Un pariente muy temprano de los grandes saurópodos de cuello largo que aparecerían millones de años después. Medía poco más de un metro.',
  },
  hyperodapedon: {
    titulo: 'Hyperodapedon',
    dato: 'El animal más común de Ischigualasto',
    texto: 'No es un dinosaurio: es un rincosaurio, un reptil herbívoro con pico que cortaba plantas duras. Sus fósiles son los más abundantes de la formación.',
  },
  ischigualastia: {
    titulo: 'Ischigualastia jenseni',
    dato: 'El herbívoro grande del valle',
    texto: 'Un dicinodonte de unos 3 metros, pariente lejano de los mamíferos, con un pico córneo para arrancar vegetación.',
  },
  dicroidium: {
    titulo: 'Dicroidium',
    dato: 'La planta que domina el Triásico del sur',
    texto: 'Un "helecho con semilla" cuyas frondas se bifurcan en forma de Y. Formaba bosques en todo Gondwana, el supercontinente del que San Juan era parte.',
  },
  neocalamites: {
    titulo: 'Neocalamites',
    dato: 'Colas de caballo gigantes',
    texto: 'Tallos articulados con anillos de hojas finas, en las orillas húmedas de los ríos. Sus parientes actuales, los equisetos, miden pocos centímetros.',
  },
  ceniza: {
    titulo: '¿Cómo se fecha un fósil?',
    dato: 'Relojes dentro de la ceniza',
    texto: 'Los restos quedaron enterrados en el barro de ríos y crecidas. Entre esas capas hay ceniza volcánica con cristales que funcionan como relojes radiactivos. Por eso sabemos que Ischigualasto tiene alrededor de 231 millones de años.',
  },
  hoy: {
    titulo: 'Parque Provincial Ischigualasto',
    dato: 'Una ventana única al origen de los dinosaurios',
    texto: 'Muestra casi todo el Triásico en capas continuas. Por eso es Patrimonio de la Humanidad junto con Talampaya. Los fósiles originales se estudian en San Juan.',
  },
};

const v = (a) => new THREE.Vector3(...a);

export function crearDirector() {
  let i = 0, t = 0;
  const estado = { indice: 0, capitulo: CAPITULOS[0], progreso: 0, cambio: true, mezcla: 1 };
  let anterior = CAPITULOS[0];

  function ir(n) {
    anterior = CAPITULOS[i];
    i = (n + CAPITULOS.length) % CAPITULOS.length;
    t = 0;
    estado.cambio = true;
  }

  function update(dt, auto = true) {
    t += dt;
    const cap = CAPITULOS[i];
    if (auto && t > cap.duracion) ir(i + 1);
    estado.indice = i;
    estado.capitulo = CAPITULOS[i];
    estado.progreso = Math.min(1, t / CAPITULOS[i].duracion);
    // mezcla con el capítulo anterior durante 3 s (luz, bruma, ceniza, era)
    estado.mezcla = Math.min(1, t / 3);
    estado.anterior = anterior;
    return estado;
  }

  // posición y mirada de la cámara a lo largo del capítulo (ease in-out)
  function camara(desvio = 0) {
    const cap = CAPITULOS[i];
    const k = estado.progreso;
    const e = k * k * (3 - 2 * k);
    const pos = v(cap.camara.desde).lerp(v(cap.camara.hasta), e);
    const mira = v(cap.camara.mira);
    // el cuerpo del visitante corre la cámara de costado (paralaje): ± 6 m
    const lado = new THREE.Vector3().subVectors(mira, pos).cross(new THREE.Vector3(0, 1, 0)).normalize();
    pos.addScaledVector(lado, desvio * 6);
    return { pos, mira };
  }

  return { estado, update, ir, camara, siguiente: () => ir(i + 1), anteriorCap: () => ir(i - 1) };
}
