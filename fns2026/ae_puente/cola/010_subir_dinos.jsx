// Reintento del 009: los dinosaurios de Meshy de esta PC no llegaron a la rama. Lo más probable es
// que el puente haya querido subir los 9 GLB (~320 MB) en un solo envío y GitHub lo haya cortado
// (y el puente no reintenta un envío fallido). Acá se suben DE A UNO, con git preparado para envíos
// grandes, y queda registro de cada paso en hechos/010_subir_dinos/git.txt.
//
//   1. Busca git y lo deja configurado para envíos grandes en esta carpeta del puente
//      (http.postBuffer de 1 GB y HTTP/1.1: los cortes "RPC failed" / "HTTP/2 stream" de Windows).
//   2. Trae la rama. Si quedó un commit local sin subir que SÓLO toca hechos/ y modelos_mac/ (el del
//      009), lo deshace sin tocar los archivos (reset --mixed), para volver a subirlos en partes.
//      Si tocara cualquier otra cosa, no se deshace nada.
//   3. Copia lo que falte de Descargas\dinos_triasico y los Herrerasaurus de Meshy.
//   4. Sube primero los resultados chicos y después cada modelo en su propio commit y envío.
//      Si se pasa de 22 min (el puente corta a los 30), deja el resto para la próxima vuelta.
//
// After queda ocupado mientras sube (unos minutos, según la conexión).

var RAMA = "claude/fiesta-sol-2026-immersive-ph9915";
var raiz = new Folder(PUENTE.raiz).fsName;
var casa = $.getenv("USERPROFILE") || Folder("~").fsName;
var t0 = new Date().getTime();
var TOPE_MS = 22 * 60 * 1000;
var registro = [];

function existe(ruta) { return ruta && new File(ruta).exists; }

function buscarGit() {
    var r = system.callSystem('cmd.exe /c where git 2>nul') || "";
    var lineas = r.split(/[\r\n]+/);
    for (var i = 0; i < lineas.length; i++) { if (/git(\.exe|\.cmd)?$/i.test(lineas[i]) && existe(lineas[i])) { return lineas[i]; } }
    var candidatos = ["C:\\Program Files\\Git\\cmd\\git.exe", "C:\\Program Files (x86)\\Git\\cmd\\git.exe"];
    var local = $.getenv("LOCALAPPDATA");
    if (local) {
        candidatos.push(local + "\\Programs\\Git\\cmd\\git.exe");
        var gd = new Folder(local + "\\GitHubDesktop");
        if (gd.exists) {
            var apps = gd.getFiles("app-*");
            for (var a = apps.length - 1; a >= 0; a--) { candidatos.push(apps[a].fsName + "\\resources\\app\\git\\cmd\\git.exe"); }
        }
    }
    for (var c = 0; c < candidatos.length; c++) { if (existe(candidatos[c])) { return candidatos[c]; } }
    return null;
}

var GIT = buscarGit();
if (!GIT) { throw new Error("No encuentro git en esta PC (ni en el PATH ni en Git / GitHub Desktop)"); }

// corre git en la carpeta del puente; devuelve {ok, salida}
function git(args) {
    var cmd = 'cmd.exe /c ""' + GIT + '" -C "' + raiz + '" -c http.postBuffer=1048576000 -c http.version=HTTP/1.1 ' +
              args + ' 2>&1 && echo __OK__ || echo __FALLA__"';
    var salida = system.callSystem(cmd) || "";
    var ok = salida.indexOf("__OK__") >= 0;
    salida = salida.replace(/__OK__|__FALLA__/g, "").replace(/\s+$/, "");
    registro.push("> git " + args + (ok ? "" : "   [FALLÓ]") + "\n" + salida);
    return { ok: ok, salida: salida };
}

function guardarRegistro() {
    var f = new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/010_subir_dinos/git.txt");
    f.parent.create();
    f.encoding = "UTF-8";
    f.open("w");
    f.write(registro.join("\n\n"));
    f.close();
}

function subir() {
    var r = git("push origin " + RAMA);
    if (!r.ok) {
        // si la nube subió algo mientras tanto: se mezcla y se reintenta una vez
        git("pull --no-rebase --no-edit origin " + RAMA);
        r = git("push origin " + RAMA);
    }
    return r.ok;
}

// 1. git preparado para envíos grandes (queda en esta carpeta: también le sirve al puente)
PUENTE.informar("git: " + GIT);
git("config http.postBuffer 1048576000");
git("config http.version HTTP/1.1");

// 2. traer la rama; si hay un commit local sin subir sólo de hechos/ y modelos_mac/, deshacerlo
git("pull --no-rebase --no-edit origin " + RAMA);
var adelante = parseInt(git("rev-list --count origin/" + RAMA + "..HEAD").salida, 10) || 0;
if (adelante > 0) {
    var dif = git("diff --name-only origin/" + RAMA + " HEAD").salida.split(/[\r\n]+/);
    var soloNuestro = true;
    for (var d = 0; d < dif.length; d++) {
        if (dif[d] && !/^fns2026\/(ae_puente\/hechos|modelos_mac)\//.test(dif[d])) { soloNuestro = false; }
    }
    if (soloNuestro) {
        git("reset --mixed origin/" + RAMA);
        PUENTE.informar(adelante + " commits locales sin subir (sólo resultados y modelos): se vuelven a subir en partes");
    } else {
        PUENTE.informar("hay " + adelante + " commits locales que tocan otras cosas: no se deshacen, se suben como están");
    }
}

// 3. copiar lo que falte (mismo criterio que el 009)
var destino = new Folder(raiz + "/fns2026/modelos_mac/pc");
if (!destino.exists) { destino.create(); }
var origenes = [];
var carpeta = new Folder(casa + "/Downloads/dinos_triasico");
if (carpeta.exists) { origenes = origenes.concat(carpeta.getFiles("*.glb")); }
var descargas = new Folder(casa + "/Downloads");
if (descargas.exists) { origenes = origenes.concat(descargas.getFiles("Meshy_AI_herrerasaurus_*_image-to-3d-texture.glb")); }
for (var i = 0; i < origenes.length; i++) {
    var copia = new File(destino.fsName + "/" + decodeURI(origenes[i].name));
    if (!(copia.exists && copia.length === origenes[i].length)) {
        if (!origenes[i].copy(copia)) { PUENTE.informar("no pude copiar " + origenes[i].fsName); }
    }
}
PUENTE.informar("modelos en Descargas: " + origenes.length);

// el listado del proyecto de Unity de esta PC, si el 009 no llegó a escribirlo
var lista = new File(raiz + "/fns2026/ae_puente/hechos/009_traer_dinos/valle_luna_unity.txt");
if (!lista.exists) {
    var items = [];
    var recorrer = function (c, prof, rel) {
        if (prof < 0) { return; }
        var hijos = c.getFiles();
        for (var k = 0; k < hijos.length; k++) {
            var n = decodeURI(hijos[k].name);
            if (/^(Library|Temp|Logs|obj|UserSettings|\.git|\.vs)$/i.test(n)) { continue; }
            if (hijos[k] instanceof Folder) { items.push(rel + n + "/"); recorrer(hijos[k], prof - 1, rel + n + "/"); }
            else { items.push(rel + n + " · " + Math.round(hijos[k].length / 1024) + " KB"); }
        }
    };
    var unityPc = new Folder(casa + "/Documents/ValleLunaUnity");
    if (unityPc.exists) { recorrer(unityPc, 5, ""); }
    lista.parent.create();
    lista.encoding = "UTF-8";
    lista.open("w");
    lista.write(items.join("\n"));
    lista.close();
}

// 4a. primero lo chico: resultados del 009 y el listado
git("add fns2026/ae_puente/hechos");
if (!git("diff --cached --quiet").ok) {
    git('commit -m "puente AE: resultados del 009 (reintento)"');
    PUENTE.informar("resultados del 009: " + (subir() ? "subidos" : "NO se pudieron subir"));
}

// 4b. cada modelo en su propio commit y envío
// una copia que no llega a subirse se saca de modelos_mac/pc (el original sigue en Descargas): si no,
// el puente la metería en su commit de resultados y el envío volvería a ser enorme
function quitarCopia(f) {
    var n = decodeURI(f.name);
    if (new File(casa + "/Downloads/dinos_triasico/" + n).exists || new File(casa + "/Downloads/" + n).exists) { f.remove(); }
}
var glbs = destino.getFiles("*.glb");
var subidos = 0, yaEstaban = 0, pendientes = [], fallo = false;
for (var g = 0; g < glbs.length; g++) {
    var nombre = decodeURI(glbs[g].name);
    var rel = "fns2026/modelos_mac/pc/" + nombre;
    if (git("cat-file -e \"origin/" + RAMA + ":" + rel + "\"").ok) { yaEstaban++; continue; }
    if (fallo || new Date().getTime() - t0 > TOPE_MS) {
        pendientes.push(nombre);
        quitarCopia(glbs[g]);
        continue;
    }
    git("add \"" + rel + "\"");
    git('commit -m "puente AE: ' + nombre + ' (' + Math.round(glbs[g].length / 1048576) + ' MB)"');
    if (subir()) {
        subidos++;
        PUENTE.informar("subido: " + nombre);
    } else {
        // se deshace el commit local (HEAD ya contiene la rama remota: no se pierde nada de ella)
        fallo = true;
        git("reset --mixed origin/" + RAMA);
        pendientes.push(nombre);
        quitarCopia(glbs[g]);
        PUENTE.informar("NO se pudo subir " + nombre + ": el detalle está en hechos/010_subir_dinos/git.txt");
    }
}
if (pendientes.length) { PUENTE.informar("quedan para la próxima vuelta: " + pendientes.join(", ")); }
guardarRegistro();
subidos + " subidos ahora, " + yaEstaban + " ya estaban, " + pendientes.length + " pendientes"
