// Prueba de punta a punta, sin pantalla: levanta el puente (con visitantes simulados) sirviendo
// dist/, abre la experiencia en Chromium, recorre los 6 capítulos, toca un animal y el suelo,
// y revisa que no haya errores. Deja capturas en ./capturas/.
//
//   npm run build && npm run probar
//   CHROMIUM=/ruta/a/chrome npm run probar      (en la Mac: la ruta de Google Chrome)

import { spawn } from 'node:child_process';
import fs from 'node:fs';
import { chromium } from 'playwright-core';

const RUTA = process.env.CHROMIUM
  || ['/opt/pw-browsers/chromium', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'].find((p) => fs.existsSync(p));
const CALIDAD = process.env.CALIDAD || '0.35';
fs.mkdirSync('capturas', { recursive: true });

let exe = RUTA;
if (fs.existsSync(RUTA) && fs.statSync(RUTA).isDirectory()) {
  // carpeta de Playwright: buscar el ejecutable adentro
  const cand = ['chrome-linux/chrome', 'chrome'].map((p) => `${RUTA}/${p}`).find((p) => fs.existsSync(p));
  exe = cand || RUTA;
}

const puente = spawn(process.execPath, ['server/puente.mjs', '--servir', 'dist', '--simular', '--sin-gestos', '--http', '8099', '--ws', '8799', '--osc', '17001,17002'], { stdio: 'pipe' });
puente.stdout.on('data', (d) => process.stdout.write(`  [puente] ${d}`));
await new Promise((r) => setTimeout(r, 800));

const fallas = [];
const ok = (c, t) => { console.log(`${c ? 'OK   ' : 'FALLA'} ${t}`); if (!c) fallas.push(t); };

const nav = await chromium.launch({ executablePath: exe, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const pag = await nav.newPage({ viewport: { width: 1280, height: 540 } });
const errores = [];
pag.on('pageerror', (e) => errores.push(e.message));
pag.on('console', (m) => { if (m.type() === 'error') errores.push(m.text()); });

await pag.goto(`http://localhost:8099/?calidad=${CALIDAD}&auto=0&ws=localhost:8799`);
await pag.waitForFunction(() => window.__triasico, null, { timeout: 120000 });
const info = await pag.evaluate(() => ({ flora: window.__triasico.flora, n: window.__triasico.fauna.length, especies: window.__triasico.especies }));
console.log('  flora:', JSON.stringify(info.flora), '· animales:', info.n);
ok(Object.keys(info.flora).length >= 6, 'la flora cargó (GLB horneados de Blender)');
ok(info.n >= 30, 'hay fauna (6 especies)');

const nombres = ['titulo', 'rio', 'bosque', 'llanura', 'ceniza', 'hoy'];
for (let i = 0; i < 6; i++) {
  await pag.keyboard.press(String(i));
  // esperar al estado, no a un tiempo fijo: sin placa de video un cuadro puede tardar segundos
  const cap = await pag.waitForFunction((n) => window.__triasico.director.estado.capitulo.clave === n && n, nombres[i], { timeout: 30000 })
    .then((h) => h.jsonValue()).catch(() => pag.evaluate(() => window.__triasico.director.estado.capitulo.clave));
  await pag.waitForTimeout(i === 5 ? 12000 : 5000);         // "hoy" tarda en erosionar
  await pag.screenshot({ path: `capturas/${i}_${nombres[i]}.jpg`, quality: 80 });
  ok(cap === nombres[i], `capítulo ${i} (${nombres[i]})`);
}

// tocar un animal: proyectar un Hyperodapedon a la pantalla y "tocarlo"
await pag.keyboard.press('1');
await pag.waitForFunction(() => window.__triasico.director.estado.capitulo.clave === 'rio', null, { timeout: 30000 });
await pag.waitForTimeout(8000);
const tocado = await pag.evaluate(() => {
  const T = window.__triasico;
  // el animal más cercano que esté delante de la cámara: se proyecta a la pantalla y se toca ahí
  const cam = T.camara;
  const candidatos = T.fauna
    .map((a) => { const p = a.grupo.position.clone(); p.y += a.esp.cadera; const d = p.distanceTo(cam.position); const s = p.clone().project(cam); return { a, d, s }; })
    .filter((c) => c.s.z < 1 && Math.abs(c.s.x) < 0.95 && Math.abs(c.s.y) < 0.95 && c.d < 50)
    .sort((x, y) => x.d - y.d);
  for (const { a, s } of candidatos) {
    T.tocar({ u: (s.x + 1) / 2, v: (1 - s.y) / 2, nuevo: true });
    const acariciado = T.fauna.find((x) => x.caricia > 0);
    if (acariciado) return acariciado.clave;
  }
  return candidatos.length ? `ninguno de ${candidatos.length} visibles respondió` : null;
});
ok(!!tocado && !String(tocado).startsWith('ninguno'), `tocar un animal lo acaricia${tocado ? ` (${tocado})` : ''}`);
await pag.waitForTimeout(800);
await pag.screenshot({ path: 'capturas/7_caricia_y_ficha.jpg', quality: 80 });
const ficha = await pag.evaluate(() => document.querySelector('#ficha').classList.contains('visible') && document.querySelector('#ficha h2').textContent);
ok(!!ficha, `aparece la ficha (${ficha})`);

const sensor = await pag.evaluate(() => ({ con: window.__triasico.entrada.estado.conectado, cuerpo: window.__triasico.entrada.estado.cuerpo }));
ok(sensor.con, 'el navegador está conectado al puente de sensores');
ok(typeof sensor.cuerpo.x === 'number', `llega el cuerpo simulado (x=${sensor.cuerpo.x?.toFixed?.(2)}, presente=${sensor.cuerpo.presente})`);
const fps = await pag.evaluate(() => window.__triasico.fps);
console.log(`  fps en este contenedor (CPU, swiftshader, calidad ${CALIDAD}): ${fps} — en una placa de video real es otra historia`);
ok(errores.length === 0, `sin errores en la consola${errores.length ? `: ${errores.slice(0, 3).join(' | ')}` : ''}`);

await nav.close();
puente.kill();
console.log(`\n${fallas.length ? `${fallas.length} fallas` : 'todo OK'} · capturas en ./capturas/`);
process.exit(fallas.length ? 1 : 0);
