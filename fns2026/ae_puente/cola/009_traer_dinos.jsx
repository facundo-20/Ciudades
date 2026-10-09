// Trae a la rama los dinosaurios de Meshy bajados en esta PC (los de alta calidad, para Unity):
// Descargas\dinos_triasico\*.glb (7, ~30 MB c/u) y los dos Herrerasaurus de Meshy en GLB. Van a
// fns2026/modelos_mac/pc/ (el puente sube esa carpeta). En la nube se les arma el esqueleto y las
// animaciones (pipeline/rig_fauna.py) y vuelven livianos para Unity.
// Además lista (sólo nombres) el proyecto Documents\ValleLunaUnity, para no pisar lo que ya hay.

var casa = Folder("~").fsName;
var destino = new Folder(PUENTE.raiz + "/fns2026/modelos_mac/pc");
if (!destino.exists) { destino.create(); }
var traidos = [];

function copiar(f) {
    var copia = new File(destino.fsName + "/" + decodeURI(f.name));
    if (copia.exists && copia.length === f.length) { traidos.push(decodeURI(f.name) + " (ya estaba)"); return; }
    if (!f.copy(copia)) { throw new Error("No pude copiar " + f.fsName); }
    traidos.push(decodeURI(f.name) + " · " + Math.round(f.length / 1048576) + " MB");
}

var carpeta = new Folder(casa + "/Downloads/dinos_triasico");
if (carpeta.exists) {
    var fs = carpeta.getFiles("*.glb");
    for (var i = 0; i < fs.length; i++) { copiar(fs[i]); }
} else { PUENTE.informar("no está Downloads/dinos_triasico"); }

var descargas = new Folder(casa + "/Downloads");
var herr = descargas.getFiles("Meshy_AI_herrerasaurus_*_image-to-3d-texture.glb");
for (var h = 0; h < herr.length; h++) { copiar(herr[h]); }

// el proyecto de Unity que ya existe en esta PC: sólo la lista de archivos (sin Library ni Temp)
var lista = [];
function recorrer(c, prof, rel) {
    if (prof < 0) { return; }
    var hijos = c.getFiles();
    for (var k = 0; k < hijos.length; k++) {
        var n = decodeURI(hijos[k].name);
        if (/^(Library|Temp|Logs|obj|UserSettings|\.git|\.vs)$/i.test(n)) { continue; }
        if (hijos[k] instanceof Folder) { lista.push(rel + n + "/"); recorrer(hijos[k], prof - 1, rel + n + "/"); }
        else { lista.push(rel + n + " · " + Math.round(hijos[k].length / 1024) + " KB"); }
    }
}
var unityPc = new Folder(casa + "/Documents/ValleLunaUnity");
if (unityPc.exists) { recorrer(unityPc, 5, ""); }
var out = new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/009_traer_dinos/valle_luna_unity.txt");
out.parent.create();
out.encoding = "UTF-8";
out.open("w");
out.write(lista.join("\n"));
out.close();

for (var t = 0; t < traidos.length; t++) { PUENTE.informar(traidos[t]); }
PUENTE.informar("ValleLunaUnity: " + lista.length + " archivos y carpetas listados");
traidos.length + " modelos"
