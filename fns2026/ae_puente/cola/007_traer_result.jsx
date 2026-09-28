// Trae el result.glb de Descargas al repo para usarlo en el Submarino (y el Hongo).
var carpetas = [Folder("~/Downloads"), Folder("~/Descargas"), Folder(Folder.myDocuments.parent.fsName + "/Downloads")];
var hallado = null;
for (var i = 0; i < carpetas.length && !hallado; i++) {
    if (!carpetas[i].exists) { continue; }
    var fs = carpetas[i].getFiles("result*");
    for (var j = 0; j < fs.length; j++) { if (fs[j] instanceof File) { hallado = fs[j]; break; } }
}
if (!hallado) { throw new Error("No encuentro result.* en Descargas"); }
var destino = new Folder(PUENTE.raiz + "/fns2026/modelos_mac");
if (!destino.exists) { destino.create(); }
var ext = hallado.name.indexOf(".") >= 0 ? hallado.name.substring(hallado.name.lastIndexOf(".")) : ".glb";
var copia = new File(destino.fsName + "/result" + ext);
if (!hallado.copy(copia)) { throw new Error("No pude copiar " + hallado.fsName); }
PUENTE.informar("copiado " + hallado.fsName + " → fns2026/modelos_mac/" + copia.name + " (" + Math.round(copia.length / 1048576) + " MB)");
"result traído"
