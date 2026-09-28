/*  Sobre del puente de After Effects: corre un trabajo de la cola y deja su resultado en JSON.
    Lo llama puente_ae.mjs; no hace falta abrirlo a mano.

    El trabajo (un .jsx de fns2026/ae_puente/cola/) puede usar:
      PUENTE.informar("texto")               → queda en el resultado
      PUENTE.captura(comp, segundos, "nombre") → JPG de un cuadro en hechos/<id>/nombre.jpg
      PUENTE.raiz                            → carpeta del repo en esta PC
    y lo que devuelva la última expresión queda en "valor".
*/
(function () {
    var base = new File($.fileName).parent;
    var f = new File(base.fsName + "/trabajo_actual.json");
    f.encoding = "UTF-8";
    f.open("r");
    var datos = eval("(" + f.read() + ")");
    f.close();

    var informe = [];
    $.global.PUENTE = {
        raiz: datos.raiz,
        // proyectos armados: se quedan en la PC (proyectos/ no va a git; un .aep pesa 12 MB)
        proyectos: datos.raiz + "/fns2026/ae_puente/proyectos",
        informar: function (t) { informe.push(String(t)); },
        // un cuadro a JPG chico (la mitad del ancho, tope 1920) para revisarlo desde la nube
        captura: function (comp, segundos, nombre) {
            var png = new File(datos.capturas + "/" + nombre + ".png");
            try {
                // a un tercio: el LED entero (5760 px) pesaría ~10 MB por captura en git
                var chica = app.project.items.addComp("_captura", Math.round(comp.width / 3), Math.round(comp.height / 3),
                                                      1, comp.duration, comp.frameRate);
                var capa = chica.layers.add(comp);
                capa.property("ADBE Transform Group").property("ADBE Scale").setValue([100 / 3, 100 / 3]);
                capa.property("ADBE Transform Group").property("ADBE Position").setValue([chica.width / 2, chica.height / 2]);
                chica.saveFrameToPng(segundos, png);
                // After 2026 escribe el cuadro en segundo plano: se espera a que el archivo exista y
                // deje de crecer (hasta 2 min). Con 30 s llegaban 2 capturas de 7.
                var previo = -1;
                for (var t = 0; t < 240; t++) {
                    if (png.exists && png.length > 0 && png.length === previo) { break; }
                    previo = png.exists ? png.length : -1;
                    $.sleep(500);
                }
                chica.remove();
                informe.push("captura: " + nombre + ".png");
            } catch (e) {
                informe.push("captura falló (" + nombre + "): " + e.toString());
            }
        }
    };
    // Proyecto nuevo sin perder nada: si hay algo abierto, se guarda antes. Con archivo, en su
    // lugar; sin archivo, como respaldo en ae_puente/respaldos/ (sólo en la PC, no va a git).
    // Antes el trabajo se frenaba, y un sólido de prueba del propio puente lo trababa (28/09).
    $.global.PUENTE.proyectoNuevo = function () {
        if (app.project && app.project.numItems > 0) {
            if (app.project.file) {
                app.project.save();
                informe.push("guardado antes de seguir: " + app.project.file.fsName);
            } else {
                var carpeta = new Folder(datos.raiz + "/fns2026/ae_puente/respaldos");
                if (!carpeta.exists) { carpeta.create(); }
                var d = new Date();
                var nombre = "respaldo_" + d.getFullYear() + ("0" + (d.getMonth() + 1)).slice(-2) + ("0" + d.getDate()).slice(-2) +
                             "_" + ("0" + d.getHours()).slice(-2) + ("0" + d.getMinutes()).slice(-2) + ("0" + d.getSeconds()).slice(-2) + ".aep";
                app.project.save(new File(carpeta.fsName + "/" + nombre));
                informe.push("proyecto sin guardar respaldado en ae_puente/respaldos/" + nombre);
            }
        }
        app.newProject();
    };
    $.global.FNS_PUENTE = true;          // los scripts del proyecto no abren diálogos ni alertas

    function json(v) {
        if (v === null || v === undefined) { return "null"; }
        if (typeof v === "number" || typeof v === "boolean") { return String(v); }
        if (v instanceof Array) {
            var a = [];
            for (var i = 0; i < v.length; i++) { a.push(json(v[i])); }
            return "[" + a.join(",") + "]";
        }
        if (typeof v === "object") {
            var o = [];
            for (var k in v) { if (v.hasOwnProperty(k)) { o.push(json(String(k)) + ":" + json(v[k])); } }
            return "{" + o.join(",") + "}";
        }
        return '"' + String(v).replace(/\\/g, "\\\\").replace(/"/g, '\\"').replace(/\r?\n/g, "\\n") + '"';
    }

    var res = { ok: true, informe: informe, valor: null, error: null, version_ae: app.version };
    try {
        app.beginSuppressDialogs();
        res.valor = String($.evalFile(new File(datos.trabajo)));
    } catch (e) {
        res.ok = false;
        res.error = e.toString() + (e.line ? " (línea " + e.line + ")" : "");
    } finally {
        try { app.endSuppressDialogs(false); } catch (e2) {}
    }
    var out = new File(datos.salida);
    out.encoding = "UTF-8";
    out.open("w");
    out.write(json(res));
    out.close();
})();
