// Gaussian splats horneados de cada capítulo (pipeline/splats), dibujados con Spark (MIT, World Labs:
// @sparkjsdev/spark). La flora queda con la luz de Cycles; el suelo, el agua, el cielo y los
// animales siguen siendo los de la escena en vivo.
//
// public/splats/lista.json: [{ "capitulo": "bosque", "archivo": "bosque.sog",
//                              "desde": [x, z], "hasta": [x, z], "radio": 45 }]   (coordenadas web)
// Cada splat se baja recién la primera vez que se entra al capítulo. Donde hay splat, la flora de
// mallas no se dibuja (flora.excluir), para no repetir plantas. Con ?splats=0 no se usan.
export async function crearSplats(escena, render, base, flora) {
  const nada = { capitulo() {}, opacidad() {}, cargados: () => 0, lista: [] };
  if (new URLSearchParams(location.search).get('splats') === '0') return nada;
  let lista = [];
  try { lista = await (await fetch(`${base}lista.json`)).json(); } catch { /* sin splats: todo con mallas */ }
  if (!Array.isArray(lista) || !lista.length) return nada;

  // Spark pesa ~2 MB: se baja sólo si hay splats
  const { SparkRenderer, SplatMesh } = await import('@sparkjsdev/spark');
  escena.add(new SparkRenderer({ renderer: render }));
  const mallas = {};
  let actual = null;

  function capitulo(clave) {
    const sp = lista.find((s) => s.capitulo === clave);
    for (const m of Object.values(mallas)) m.visible = false;
    actual = null;
    if (!sp) { flora?.excluir(null); return; }
    if (!mallas[clave]) {
      // el archivo ya viene en ejes de three.js (y arriba): no hace falta girarlo. Una captura real
      // trae además dónde va (importar_en_blender.py --exportar): posición, cuaternión y escala
      mallas[clave] = new SplatMesh({ url: `${base}${sp.archivo}` });
      if (sp.posicion) mallas[clave].position.fromArray(sp.posicion);
      if (sp.cuaternion) mallas[clave].quaternion.fromArray(sp.cuaternion);
      if (sp.escala) mallas[clave].scale.setScalar(sp.escala);
      mallas[clave].initialized.catch((e) => console.warn(`splats: no se pudo cargar ${sp.archivo}`, e?.message));
      escena.add(mallas[clave]);
    }
    actual = mallas[clave];
    actual.visible = true;
    actual.opacity = 0;
    flora?.excluir(sp);
  }

  // aparece con la mezcla de luz del capítulo (0 → 1 en ~3 s)
  function opacidad(k) {
    if (actual) actual.opacity = Math.max(0, Math.min(1, k));
  }

  return { capitulo, opacidad, cargados: () => Object.keys(mallas).length, lista };
}
