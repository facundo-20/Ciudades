// Puente de sensores → navegador. El navegador no puede escuchar UDP (OSC); esto sí.
//
//   node server/puente.mjs                  escucha OSC y reparte por WebSocket en :8765
//   node server/puente.mjs --servir dist    además sirve la experiencia en http://<ip>:8080 (modo evento)
//   node server/puente.mjs --simular        visitantes inventados (sin sensores), para probar
//
// Qué escucha (los mismos mensajes que ya usa el resto del stand):
//   :7001  tracker lidarwall   /wall/touch/<n>/x|y|active, /wall/count
//   :10000 cuerpo / TD         /body/x, /body/present, /touch/u, /touch/v, /touch/down
//   gestos en cualquiera       /gesto/<nombre> (brazos_arriba, salto, siguiente, anterior)
//
// Qué manda al navegador, 60 veces por segundo:
//   { tipo: 'estado', toques: [{id,u,v,nuevo}], cuerpo: {presente, x} }   y   { tipo: 'gesto', nombre }
// Siempre manda el estado completo (no sólo cambios): si se pierde un mensaje, el siguiente corrige.

import dgram from 'node:dgram';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { WebSocketServer } from 'ws';

const args = process.argv.slice(2);
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const PUERTO_WS = +opt('--ws', 8765);
const PUERTOS_OSC = (opt('--osc', '7001,10000')).split(',').map(Number);
const SERVIR = opt('--servir', null);
const PUERTO_HTTP = +opt('--http', 8080);
const SIMULAR = args.includes('--simular');

// ---------------------------------------------------------------- OSC mínimo (i, f, s, T, F; bundles)
function cadena(b, i) { const fin = b.indexOf(0, i); return [b.toString('utf8', i, fin), (Math.floor(fin / 4) + 1) * 4]; }
export function oscDecodificar(b) {
  if (b.toString('utf8', 0, 7) === '#bundle') {
    const out = []; let i = 16;
    while (i < b.length) { const n = b.readInt32BE(i); out.push(...oscDecodificar(b.subarray(i + 4, i + 4 + n))); i += 4 + n; }
    return out;
  }
  let [dir, i] = cadena(b, 0); let tipos; [tipos, i] = cadena(b, i);
  const vals = [];
  for (const t of tipos.slice(1)) {
    if (t === 'i') { vals.push(b.readInt32BE(i)); i += 4; }
    else if (t === 'f') { vals.push(b.readFloatBE(i)); i += 4; }
    else if (t === 's') { let s; [s, i] = cadena(b, i); vals.push(s); }
    else if (t === 'T' || t === 'F') vals.push(t === 'T');
  }
  return [{ dir, vals }];
}
const pad = (b) => Buffer.concat([b, Buffer.alloc(4 - (b.length % 4))]);
export function oscCodificar(dir, ...vals) {
  let tipos = ','; const datos = [];
  for (const v of vals) {
    if (typeof v === 'string') { tipos += 's'; datos.push(pad(Buffer.from(v))); }
    else if (Number.isInteger(v)) { tipos += 'i'; const x = Buffer.alloc(4); x.writeInt32BE(v); datos.push(x); }
    else { tipos += 'f'; const x = Buffer.alloc(4); x.writeFloatBE(v); datos.push(x); }
  }
  return Buffer.concat([pad(Buffer.from(dir)), pad(Buffer.from(tipos)), ...datos]);
}

// ---------------------------------------------------------------- estado unificado
const estado = { toques: new Map(), cuerpo: { presente: false, x: 0.5 }, ultimo: 0, tdToque: { u: 0.5, v: 0.5, down: false } };
const gestos = [];

export function recibir(dir, vals) {
  estado.ultimo = Date.now();
  const p = dir.replace(/^\//, '').split('/');
  const v = vals[0];
  if (p[0] === 'wall' && p[1] === 'touch' && p.length === 4) {
    const t = estado.toques.get(p[2]) || { u: 0, v: 0, activo: false, nuevo: false };
    if (p[3] === 'active') { const a = !!v; if (a && !t.activo) t.nuevo = true; t.activo = a; }
    else if (p[3] === 'x') t.u = +v;
    else if (p[3] === 'y') t.v = +v;
    estado.toques.set(p[2], t);
  } else if (p[0] === 'body') {
    if (p[1] === 'x') estado.cuerpo.x = +v;
    if (p[1] === 'present') estado.cuerpo.presente = !!v;
  } else if (p[0] === 'touch') {
    if (p[1] === 'u') estado.tdToque.u = +v;
    if (p[1] === 'v') estado.tdToque.v = +v;
    if (p[1] === 'down') { const d = !!v; estado.tdToque.nuevo = d && !estado.tdToque.down; estado.tdToque.down = d; }
  } else if (p[0] === 'gesto' && p[1]) {
    gestos.push(p[1]);
  }
}

function paquete() {
  const vivo = Date.now() - estado.ultimo < 1500;     // tracker callado 1,5 s = caído: nada de dedos fantasma
  const toques = [];
  if (vivo) {
    for (const [id, t] of estado.toques) if (t.activo) { toques.push({ id, u: t.u, v: t.v, nuevo: t.nuevo }); t.nuevo = false; }
    if (estado.tdToque.down) { toques.push({ id: 'td', u: estado.tdToque.u, v: estado.tdToque.v, nuevo: !!estado.tdToque.nuevo }); estado.tdToque.nuevo = false; }
  }
  const presente = vivo && (estado.cuerpo.presente || toques.length > 0);
  return { tipo: 'estado', toques, cuerpo: { presente, x: estado.cuerpo.x } };
}

// ---------------------------------------------------------------- red
export function arrancar() {
  const wss = new WebSocketServer({ port: PUERTO_WS });
  const enviar = (o) => { const s = JSON.stringify(o); for (const c of wss.clients) if (c.readyState === 1) c.send(s); };
  for (const puerto of PUERTOS_OSC) {
    const sock = dgram.createSocket({ type: 'udp4', reuseAddr: true });
    sock.on('message', (b) => { try { for (const m of oscDecodificar(b)) recibir(m.dir, m.vals); } catch { /* paquete roto: se ignora */ } });
    sock.on('error', (e) => console.error(`OSC :${puerto}`, e.message));
    sock.bind(puerto, () => console.log(`OSC escuchando en :${puerto}`));
  }
  setInterval(() => {
    enviar(paquete());
    while (gestos.length) enviar({ tipo: 'gesto', nombre: gestos.shift() });
  }, 1000 / 60);
  console.log(`WebSocket en ws://0.0.0.0:${PUERTO_WS}`);

  if (SERVIR) servirEstatico(SERVIR);
  if (SIMULAR) simular();
  return wss;
}

function servirEstatico(carpeta) {
  const tipos = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.glb': 'model/gltf-binary', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml' };
  const raiz = path.resolve(carpeta);
  http.createServer((req, res) => {
    const url = decodeURIComponent(req.url.split('?')[0]);
    let f = path.join(raiz, url === '/' ? 'index.html' : url);
    if (!f.startsWith(raiz)) { res.writeHead(403); return res.end(); }        // nada fuera de la carpeta
    fs.stat(f, (err, st) => {
      if (err || !st.isFile()) { res.writeHead(404); return res.end('no está'); }
      res.writeHead(200, { 'Content-Type': tipos[path.extname(f)] || 'application/octet-stream' });
      if (req.method === 'HEAD') return res.end();
      fs.createReadStream(f).pipe(res);
    });
  }).listen(PUERTO_HTTP, () => console.log(`Experiencia en http://localhost:${PUERTO_HTTP}  (abrir en Chrome, F = pantalla completa)`));
}

function simular() {
  // una persona que camina de un lado al otro, toca el suelo cada tanto y levanta los brazos cada 40 s
  console.log('SIMULANDO visitantes (sin sensores)');
  const t0 = Date.now();
  setInterval(() => {
    const t = (Date.now() - t0) / 1000;
    const ciclo = t % 60;
    const presente = ciclo < 45;
    recibir('/body/present', [presente ? 1 : 0]);
    recibir('/body/x', [0.5 + 0.4 * Math.sin(t * 0.25)]);
    const tocando = presente && (t % 5) < 0.4;
    recibir('/wall/touch/0/active', [tocando ? 1 : 0]);
    recibir('/wall/touch/0/x', [0.3 + 0.4 * Math.abs(Math.sin(t * 0.13))]);
    recibir('/wall/touch/0/y', [0.72]);
  }, 1000 / 30);
  if (!args.includes('--sin-gestos')) setInterval(() => gestos.push('brazos_arriba'), 40000);
}

if (import.meta.url === `file://${process.argv[1]}`) arrancar();
