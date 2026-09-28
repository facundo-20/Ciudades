// Recorrido por San Juan: las 7 postales (fns2026/escenas/sanjuan/pruebas) con títulos, fichas
// y atmósferas. Mismo motor que el Parque Triásico. Capturas de cada postal.
$.global.FNS_MODO = "sanjuan";
PUENTE.proyectoNuevo();
$.global.FNS_CARPETA = PUENTE.raiz + "/fns2026/escenas/sanjuan/pruebas_media";
$.evalFile(new File(PUENTE.raiz + "/fns2026/escenas/after_effects/parque_triasico_ae.jsx"));
$.global.FNS_MODO = null;
var m = $.global.FNS_MAESTRO;
var paso = 12 - 1.5;
var nombres = ["hongo", "bochas", "alcazar", "leoncito", "cuesta", "catedral", "bicentenario"];
for (var i = 0; i < nombres.length; i++) { PUENTE.captura(m, i * paso + 6, "postal_" + (i + 1) + "_" + nombres[i]); }
app.project.save(new File(PUENTE.raiz + "/fns2026/ae_puente/hechos/005_recorrido_san_juan/recorrido_san_juan.aep"));
"recorrido armado"
