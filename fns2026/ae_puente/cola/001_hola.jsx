// Primer contacto: qué After hay, qué fuentes y qué plugins tiene. No toca ningún proyecto.
var r = [];
r.push("After Effects " + app.version + " · " + ($.os || ""));
r.push("proyecto abierto: " + (app.project && app.project.file ? app.project.file.fsName : "(sin guardar)"));
var fuentes = ["Montserrat-SemiBold", "Montserrat-Light", "HelveticaNeue-Medium", "Arial-BoldMT"];
for (var i = 0; i < fuentes.length; i++) {
    var hay = false;
    try { hay = app.fonts.getFontsByPostScriptName(fuentes[i]).length > 0; } catch (e) { hay = "?"; }
    r.push("fuente " + fuentes[i] + ": " + hay);
}
var c = app.project.items.addComp("_prueba_puente", 100, 100, 1, 1, 30);
var s = c.layers.addSolid([0, 0, 0], "p", 100, 100, 1);
var fx = s.property("ADBE Effect Parade");
var buscar = ["Deep Glow 2", "Deep Glow", "Optical Flares", "RSMB Pro", "RSMB", "Particular", "Trapcode Particular",
              "Saber", "Element", "Twitch", "Universe Glow"];
for (var j = 0; j < buscar.length; j++) { r.push("plugin " + buscar[j] + ": " + fx.canAddProperty(buscar[j])); }
c.remove();
PUENTE.informar(r.join("\n"));
"hola desde After"
