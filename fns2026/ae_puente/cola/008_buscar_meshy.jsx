// Busca en esta PC los modelos 3D bajados de Meshy (dinosaurios, plantas, rocas) para usarlos en
// Unity con su calidad completa. Sólo LISTA (nombre, carpeta, tamaño, fecha): no copia nada todavía.
// Mira sólo archivos de modelos 3D (.glb .gltf .fbx .obj .usdz .blend, y .zip con "meshy" en el
// nombre), en Descargas, Escritorio, Documentos, OneDrive y la raíz de otros discos.

var EXT = /\.(glb|gltf|fbx|obj|usdz|blend)$/i;
var SALTEAR = /^(AppData|node_modules|\.git|\$Recycle\.Bin|Windows|Program Files|Program Files \(x86\)|ProgramData|respaldos|Library|cache|Cache|Temp|tmp)$/i;
var encontrados = [];
var visitadas = 0;
var t0 = new Date().getTime();
var TOPE_MS = 8 * 60 * 1000;

function fecha(d) {
    return d ? d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2) + "-" + ("0" + d.getDate()).slice(-2) : "";
}

function recorrer(carpeta, profundidad) {
    if (profundidad < 0 || new Date().getTime() - t0 > TOPE_MS) { return; }
    var hijos;
    try { hijos = carpeta.getFiles(); } catch (e) { return; }
    if (!hijos) { return; }
    visitadas++;
    for (var i = 0; i < hijos.length; i++) {
        var h = hijos[i];
        if (h instanceof Folder) {
            if (!SALTEAR.test(h.name)) { recorrer(h, profundidad - 1); }
        } else {
            var n = decodeURI(h.name);
            var esZipMeshy = /\.zip$/i.test(n) && /meshy/i.test(n);
            if (EXT.test(n) || esZipMeshy) {
                encontrados.push({ nombre: n, carpeta: decodeURI(h.parent.fsName), mb: Math.round(h.length / 104857.6) / 10,
                                   fecha: fecha(h.modified) });
            }
        }
    }
}

var casa = Folder("~");
var raices = [];
var nombres = ["Downloads", "Descargas", "Desktop", "Escritorio", "Documents", "Documentos", "Videos", "3D Objects"];
for (var k = 0; k < nombres.length; k++) {
    var f = new Folder(casa.fsName + "/" + nombres[k]);
    if (f.exists) { raices.push([f, 7]); }
}
var todo = casa.getFiles();
for (var k2 = 0; k2 < todo.length; k2++) {
    if (todo[k2] instanceof Folder && /^OneDrive/i.test(todo[k2].name)) { raices.push([todo[k2], 7]); }
}
var letras = ["D", "E", "F", "G"];
for (var k3 = 0; k3 < letras.length; k3++) {
    var disco = new Folder(letras[k3] + ":/");
    if (disco.exists) { raices.push([disco, 5]); }
}
for (var r = 0; r < raices.length; r++) { recorrer(raices[r][0], raices[r][1]); }

// la lista va a un JSON aparte en hechos/008_buscar_meshy/ (puede ser larga)
var salida = new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/008_buscar_meshy/modelos_3d.json");
salida.parent.create();
salida.encoding = "UTF-8";
salida.open("w");
var lineas = [];
for (var j = 0; j < encontrados.length; j++) {
    var e = encontrados[j];
    lineas.push('{"nombre":"' + e.nombre.replace(/\\/g, "/").replace(/"/g, "'") + '","carpeta":"' + e.carpeta.replace(/\\/g, "/").replace(/"/g, "'") +
                '","mb":' + e.mb + ',"fecha":"' + e.fecha + '"}');
}
salida.write("[\n" + lineas.join(",\n") + "\n]");
salida.close();
PUENTE.informar("carpetas revisadas: " + visitadas + " · modelos 3D encontrados: " + encontrados.length +
                " · " + Math.round((new Date().getTime() - t0) / 1000) + " s");
encontrados.length + " modelos"
