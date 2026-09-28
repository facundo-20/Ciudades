// Recorrido por San Juan: las 7 postales (fns2026/escenas/sanjuan/pruebas) con títulos, fichas
// y atmósferas. Mismo motor que el Parque Triásico. Capturas de cada postal.
if (app.project && app.project.numItems > 0) {
    if (app.project.file) { app.project.save(); }
    else { throw new Error("Hay un proyecto sin guardar abierto en After: guardalo o cerralo y el puente lo reintenta."); }
}
app.newProject();
$.global.FNS_MODO = "sanjuan";
$.global.FNS_CARPETA = PUENTE.raiz + "/fns2026/escenas/sanjuan/pruebas";
$.evalFile(new File(PUENTE.raiz + "/fns2026/escenas/after_effects/parque_triasico_ae.jsx"));
$.global.FNS_MODO = null;
var m = $.global.FNS_MAESTRO;
var paso = 12 - 1.5;
var nombres = ["hongo", "bochas", "alcazar", "leoncito", "cuesta", "catedral", "bicentenario"];
for (var i = 0; i < nombres.length; i++) { PUENTE.captura(m, i * paso + 6, "postal_" + (i + 1) + "_" + nombres[i]); }
app.project.save(new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/003_recorrido_san_juan/recorrido_san_juan.aep"));
"recorrido armado"
