// Arma la pieza del LED con las pruebas de Blender que están en el repo y saca capturas:
// la mitad de cada capítulo y la transición de los 231 millones de años.
$.global.FNS_CARPETA = PUENTE.raiz + "/fns2026/escenas/hiperreal/pruebas";
// nunca se pisa trabajo de Facu: si hay un proyecto con contenido, se guarda antes (si tiene
// archivo) o se frena (si nunca se guardó)
if (app.project && app.project.numItems > 0) {
    if (app.project.file) { app.project.save(); }
    else { throw new Error("Hay un proyecto sin guardar abierto en After: guardalo o cerralo y el puente lo reintenta."); }
}
app.newProject();
$.evalFile(new File(PUENTE.raiz + "/fns2026/escenas/after_effects/parque_triasico_ae.jsx"));
var m = $.global.FNS_MAESTRO;
var paso = 12 - 1.5;
var nombres = ["titulo", "rio", "bosque", "llanura", "ceniza", "hoy"];
for (var i = 0; i < nombres.length; i++) { PUENTE.captura(m, i * paso + 6, "cap_" + (i + 1) + "_" + nombres[i]); }
PUENTE.captura(m, 5 * paso + 0.6, "transicion_231_millones");
app.project.save(new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/002_parque_triasico/parque_triasico.aep"));
"pieza armada"
