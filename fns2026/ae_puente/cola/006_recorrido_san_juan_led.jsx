// Recorrido por San Juan con las panorámicas del LED (5760 × 1080, fns2026/escenas/sanjuan/led).
// Guarda el proyecto en tu PC (ae_puente/proyectos) y deja el render en la cola de After.
$.global.FNS_MODO = "sanjuan";
PUENTE.proyectoNuevo();
$.global.FNS_CARPETA = PUENTE.raiz + "/fns2026/escenas/sanjuan/led";
$.evalFile(new File(PUENTE.raiz + "/fns2026/escenas/after_effects/parque_triasico_ae.jsx"));
$.global.FNS_MODO = null;
var m = $.global.FNS_MAESTRO;
var paso = 12 - 1.5;
var nombres = ["hongo", "bochas", "alcazar", "leoncito", "cuesta", "catedral", "bicentenario"];
for (var i = 0; i < nombres.length; i++) { PUENTE.captura(m, i * paso + 6, "postal_" + (i + 1) + "_" + nombres[i]); }
var carpeta = new Folder(PUENTE.proyectos);
if (!carpeta.exists) { carpeta.create(); }
app.project.save(new File(carpeta.fsName + "/FNS2026_Recorrido_San_Juan_LED.aep"));
PUENTE.informar("proyecto: " + carpeta.fsName + "\\FNS2026_Recorrido_San_Juan_LED.aep");
"recorrido LED armado"
