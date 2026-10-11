#!/usr/bin/env node
// Puente de After Effects por git: deja que una sesión de Claude en la nube maneje el After
// Effects de esta PC. No abre puertos ni pide cuentas nuevas: los dos lados ya llegan a GitHub.
//
//   node fns2026/ae_puente/puente_ae.mjs            (desde la carpeta del repo, con After instalado)
//
// Cómo funciona, en un ciclo cada 20 s:
//   1. git pull de la rama de trabajo.
//   2. Por cada fns2026/ae_puente/cola/<id>.jsx que no tenga resultado todavía, se lo pasa a
//      After envuelto en un "sobre" (sobre_ae.jsx) que atrapa errores y escribe
//      fns2026/ae_puente/hechos/<id>.json con lo que el trabajo informó.
//   3. Las capturas que el trabajo guarde en hechos/<id>/ (JPG chicos) viajan con el resultado.
//   4. git add + commit + push de hechos/.
//
// Seguridad: ejecuta en After cualquier .jsx que aparezca en cola/ de ESTA rama. Sólo tiene
// acceso quien puede pushear a la rama (Facu y la sesión de Claude). Cortalo con Ctrl+C.

import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import os from 'node:os';

const RAMA = process.env.PUENTE_RAMA || 'claude/fiesta-sol-2026-immersive-ph9915';
const CADA_S = Number(process.env.PUENTE_CADA || 20);
const RAIZ = resolve(process.cwd());
const BASE = join(RAIZ, 'fns2026', 'ae_puente');
const COLA = join(BASE, 'cola');
const HECHOS = join(BASE, 'hechos');
const SOBRE = join(BASE, 'sobre_ae.jsx');
const TOPE_MIN = Number(process.env.PUENTE_TOPE_MIN || 30);   // un trabajo colgado no traba el puente
const REINTENTO_MIN = 10;   // un envío fallido (p. ej. modelos pesados) se reintenta cada 10 min, no cada ciclo
let ultimoIntento = 0;

function git(...args) {
  return execFileSync('git', args, { cwd: RAIZ, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim();
}

// Dónde está After Effects. Variable AE_EXE si hace falta forzarlo.
function buscarAfter() {
  if (process.env.AE_EXE) return process.env.AE_EXE;
  if (os.platform() === 'win32') {
    const base = 'C:\\Program Files\\Adobe';
    if (!existsSync(base)) return null;
    const versiones = readdirSync(base).filter((d) => /^Adobe After Effects/.test(d)).sort().reverse();
    for (const v of versiones) {
      const exe = join(base, v, 'Support Files', 'AfterFX.exe');
      if (existsSync(exe)) return exe;
    }
    return null;
  }
  if (os.platform() === 'darwin') {
    const apps = readdirSync('/Applications').filter((d) => /^Adobe After Effects/.test(d)).sort().reverse();
    return apps.length ? apps[0].replace(/^Adobe /, 'Adobe ') : null;   // nombre de la app para AppleScript
  }
  return null;
}

// Le pasa un script a After. En Windows AfterFX.exe -r lo corre en la instancia abierta (o la
// abre); en Mac se usa AppleScript DoScriptFile. Se espera a que el sobre escriba el resultado.
function correrEnAfter(ae, scriptAbs) {
  if (os.platform() === 'win32') {
    spawnSync(ae, ['-r', scriptAbs], { stdio: 'ignore', timeout: TOPE_MIN * 60000 });
  } else {
    spawnSync('osascript', ['-e', `tell application "${ae}" to DoScriptFile "${scriptAbs}"`],
      { stdio: 'ignore', timeout: TOPE_MIN * 60000 });
  }
}

function esperar(ms) { return new Promise((r) => setTimeout(r, ms)); }

async function ciclo(ae) {
  // merge y no fast-forward: la PC sube resultados y la nube sube trabajos al mismo tiempo, y con
  // --ff-only el puente quedaba trabado para siempre en cuanto las dos historias divergían
  try { git('pull', '--no-rebase', '--no-edit', 'origin', RAMA); } catch (e) { console.log('pull falló (sigo):', e.message.split('\n')[0]); }
  if (!existsSync(COLA)) return;
  mkdirSync(HECHOS, { recursive: true });
  const trabajos = readdirSync(COLA).filter((f) => f.endsWith('.jsx')).sort();
  let hubo = false;
  for (const f of trabajos) {
    const id = f.replace(/\.jsx$/, '');
    const salida = join(HECHOS, `${id}.json`);
    if (existsSync(salida)) continue;
    console.log(`→ ${id}`);
    mkdirSync(join(HECHOS, id), { recursive: true });
    // el sobre lee qué trabajo correr y dónde escribir desde este archivo (ExtendScript no
    // recibe argumentos por línea de comando)
    writeFileSync(join(BASE, 'trabajo_actual.json'), JSON.stringify({
      trabajo: join(COLA, f), salida, capturas: join(HECHOS, id), raiz: RAIZ,
    }));
    const t0 = Date.now();
    correrEnAfter(ae, SOBRE);
    while (!existsSync(salida) && Date.now() - t0 < TOPE_MIN * 60000) await esperar(1000);
    if (!existsSync(salida)) {
      writeFileSync(salida, JSON.stringify({ ok: false, error: `sin respuesta de After en ${TOPE_MIN} min` }));
    }
    console.log(`  ${readFileSync(salida, 'utf8').slice(0, 200)}`);
    hubo = true;
  }
  // ¿quedó algo sin subir de antes? (un envío cortado): antes se perdía hasta el próximo trabajo
  let adelante = 0;
  try { adelante = Number(git('rev-list', '--count', `origin/${RAMA}..HEAD`)); } catch { /* sin rama remota todavía */ }
  if (!hubo && adelante > 0 && Date.now() - ultimoIntento > REINTENTO_MIN * 60000) {
    ultimoIntento = Date.now();
    try { git('push', 'origin', RAMA); console.log(`  ${adelante} commit(s) pendientes subidos`); }
    catch (e) { console.log('push pendiente falló (reintento en 10 min):', e.message.split('\n')[0]); }
  }
  if (hubo) {
    try {
      git('add', 'fns2026/ae_puente/hechos');
      if (existsSync(join(RAIZ, 'fns2026', 'modelos_mac'))) git('add', 'fns2026/modelos_mac');   // p. ej. result.glb traído de Descargas
      git('commit', '-m', 'puente AE: resultados');
      try { git('push', 'origin', RAMA); } catch {
        // si la nube subió algo mientras After trabajaba: se mezcla y se reintenta una vez
        git('pull', '--no-rebase', '--no-edit', 'origin', RAMA);
        git('push', 'origin', RAMA);
      }
      console.log('  resultados subidos');
    } catch (e) { console.log('push falló (reintento en el próximo ciclo):', e.message.split('\n')[0]); }
  }
}

const ae = buscarAfter();
if (!ae) {
  console.error('No encuentro After Effects. Poné su ruta en AE_EXE (Windows: …\\Support Files\\AfterFX.exe;'
    + ' Mac: el nombre de la app, p. ej. "Adobe After Effects 2025").');
  process.exit(1);
}
// envíos grandes (modelos 3D de decenas de MB): sin esto, GitHub suele cortar con "RPC failed"
try { git('config', 'http.postBuffer', '1048576000'); git('config', 'http.version', 'HTTP/1.1'); } catch { /* sigue igual */ }
console.log(`Puente AE listo · After: ${ae} · rama ${RAMA} · cada ${CADA_S} s · Ctrl+C para cortar`);
// el puente se anuncia: así la sesión de Claude sabe que del otro lado hay alguien
mkdirSync(HECHOS, { recursive: true });
writeFileSync(join(HECHOS, '_puente_vivo.json'), JSON.stringify({ desde: new Date().toISOString(), after: ae, so: os.platform() }));
try { git('add', 'fns2026/ae_puente/hechos/_puente_vivo.json'); git('commit', '-m', 'puente AE: conectado'); git('push', 'origin', RAMA); } catch { /* nada que subir */ }
for (;;) {
  await ciclo(ae);
  await esperar(CADA_S * 1000);
}
