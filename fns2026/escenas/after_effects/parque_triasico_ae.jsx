/*  Parque Triásico — FNS 2026 · armado automático en After Effects
    ------------------------------------------------------------------
    Arma la pieza del LED (5760 × 1080, las 3 pantallas) a partir de los renders de Blender:
    6 capítulos con movimiento de cámara, atmósfera viva (ceniza, calor, rayos de sol, polvo),
    corrección de color, títulos animados letra por letra, fichas de las especies, transiciones
    y la cola de render. Un solo paso: Archivo › Scripts › Ejecutar archivo de script…

    Por qué así:
    · Todo lo nativo se toca por "matchName" e índice, NO por el nombre que se ve en pantalla:
      el After de Facu puede estar en castellano y ahí "Glow" se llama "Resplandor".
    · Los plugins de primer nivel (Deep Glow, Optical Flares, RSMB) se usan SI ESTÁN
      instalados; si no, cae a lo nativo y la pieza sale igual. El resumen final dice qué usó.
    · Las partículas de ceniza, polen y polvo son capas con expresiones deterministas
      (seedRandom): se ven idénticas en cada render y en cada máquina, que para un show
      es más importante que la comodidad de un plugin.
    · Curvas de velocidad tipo "expo" (lo que hacen Flow / Ease and Wizz): se escriben acá
      mismo con influencias altas, así no hace falta abrir el panel.

    ExtendScript = JavaScript viejo (ES3): nada de let/const/flechas.
*/

(function parqueTriasicoAE() {

    // ----------------------------------------------------------------------------------------
    // configuración
    // ----------------------------------------------------------------------------------------
    var CFG = {
        ancho: 5760, alto: 1080, fps: 30,
        pantalla: 1920,              // cada una de las 3 pantallas del LED
        segCapitulo: 12,
        solape: 1.5,                 // transición entre capítulos
        fuentes: ["Montserrat-SemiBold", "Montserrat-Bold", "HelveticaNeue-Medium", "Arial-BoldMT"],
        fuenteFina: ["Montserrat-Light", "Montserrat-Regular", "HelveticaNeue-Light", "ArialMT"],
        crema: [0.96, 0.92, 0.85],
        ocre: [0.88, 0.58, 0.32]
    };

    // Los mismos textos que la experiencia web (fns2026/experiencia/src/capitulos.js).
    // Validarlos con un paleontólogo de la UNSJ antes de la fiesta.
    var CAPITULOS = [
        { clave: "titulo", titulo: "ISCHIGUALASTO",
          sub: "San Juan, hace 231 millones de años · El amanecer de los dinosaurios",
          atm: "amanecer", look: { negro: [0.06, 0.05, 0.08], blanco: [1.0, 0.86, 0.70], tinte: 30, brillo: 4, contraste: 12 },
          fichas: [] },
        { clave: "rio", titulo: "El río",
          sub: "Una llanura con ríos que serpentean, lluvias de temporada y mucha vida",
          atm: "polen", look: { negro: [0.04, 0.07, 0.08], blanco: [1.0, 0.95, 0.86], tinte: 22, brillo: 2, contraste: 10 },
          fichas: [["Hyperodapedon sanjuanensis", "Rincosaurio · no es un dinosaurio · 1,3 m"]] },
        { clave: "bosque", titulo: "El bosque de Dicroidium",
          sub: "Frondas que se bifurcan, coníferas y helechos. Todavía no existía el pasto",
          atm: "rayos", look: { negro: [0.03, 0.07, 0.05], blanco: [1.0, 0.96, 0.84], tinte: 24, brillo: 0, contraste: 14 },
          fichas: [["Eoraptor lunensis", "Dinosaurio · 1 m"], ["Herrerasaurus ischigualastensis", "Dinosaurio carnívoro · 4 m"]] },
        { clave: "llanura", titulo: "La llanura y el volcán",
          sub: "Al oeste, volcanes activos en el borde del continente, donde mucho después se levantarían los Andes",
          atm: "calor", look: { negro: [0.07, 0.05, 0.05], blanco: [1.0, 0.90, 0.76], tinte: 26, brillo: 2, contraste: 14 },
          fichas: [["Ischigualastia jenseni", "Dicinodonte · pico sin colmillos · 3 m"], ["Sanjuansaurus gordilloi", "Dinosaurio carnívoro · 3 m"]] },
        { clave: "ceniza", titulo: "La lluvia de ceniza",
          sub: "El barro de las crecidas y la ceniza fueron tapando los restos. La ceniza permite fecharlos: 231 millones de años",
          atm: "ceniza", look: { negro: [0.05, 0.05, 0.05], blanco: [0.92, 0.86, 0.80], tinte: 55, brillo: -6, contraste: 8 },
          fichas: [] },
        { clave: "hoy", titulo: "Hoy: el Valle de la Luna",
          sub: "Parque Provincial Ischigualasto · Patrimonio de la Humanidad (UNESCO, 2000) · Conocelos en el MuPa",
          atm: "viento", look: { negro: [0.03, 0.05, 0.09], blanco: [1.0, 0.95, 0.88], tinte: 18, brillo: 3, contraste: 12 },
          fichas: [] }
    ];

    // Recorrido por San Juan (fns2026/escenas/sanjuan): el Sanjuansaurus muestra la provincia hoy.
    // Se activa con $.global.FNS_MODO = "sanjuan" (lo usa el trabajo 003 del puente).
    var GUIA = ["Sanjuansaurus gordilloi", "«Lagarto de San Juan» · dinosaurio de Ischigualasto · 3 m"];
    var CALIDO = { negro: [0.05, 0.05, 0.08], blanco: [1.0, 0.93, 0.82], tinte: 20, brillo: 2, contraste: 12 };
    var RECORRIDO = [
        { clave: "hongo", titulo: "El Hongo", sub: "Parque Provincial Ischigualasto · Valle de la Luna · Patrimonio de la Humanidad",
          atm: "viento", look: CALIDO, fichas: [GUIA] },
        { clave: "bochas", titulo: "Cancha de Bochas", sub: "Concreciones de 5 a 90 cm de diámetro, de más de 220 millones de años",
          atm: "viento", look: CALIDO, fichas: [GUIA, ["Hyperodapedon sanjuanensis", "Rincosaurio · 1,3 m"]] },
        { clave: "alcazar", titulo: "Cerro Alcázar", sub: "Barreal, Calingasta · sedimentos del Triásico tallados por el viento y el agua",
          atm: "calor", look: CALIDO, fichas: [GUIA, ["Panphagia protos", "Dinosaurio · 1,3 m"]] },
        { clave: "leoncito", titulo: "Pampa El Leoncito", sub: "Calingasta · carrovelismo en el barreal y los cielos más limpios del país (CASLEO)",
          atm: "amanecer", look: { negro: [0.06, 0.05, 0.09], blanco: [1.0, 0.84, 0.66], tinte: 30, brillo: 2, contraste: 12 },
          fichas: [GUIA, ["Exaeretodon argentinus", "Cinodonte, pariente de los mamíferos · 1,8 m"]] },
        { clave: "cuesta", titulo: "Dique Cuesta del Viento", sub: "Rodeo, Iglesia · uno de los mejores lugares del mundo para el windsurf y el kitesurf",
          atm: "viento", look: CALIDO, fichas: [GUIA, ["Exaeretodon argentinus", "Cinodonte · 1,8 m"]] },
        { clave: "catedral", titulo: "Catedral de San Juan", sub: "Plaza 25 de Mayo · inaugurada en 1979, una de las catedrales más modernas del país",
          atm: "polen", look: CALIDO, fichas: [GUIA, ["Panphagia protos", "Dinosaurio · 1,3 m"]] },
        { clave: "bicentenario", titulo: "Teatro del Bicentenario", sub: "Su arco de 63 m de luz está revestido en 9.000 placas de travertino sanjuanino",
          atm: "polen", look: CALIDO, fichas: [GUIA, ["Hyperodapedon sanjuanensis", "Rincosaurio · 1,3 m"]] }
    ];
    if ($.global.FNS_MODO === "sanjuan") { CAPITULOS = RECORRIDO; }

    var informe = [];
    function anotar(t) { informe.push(t); }

    // ----------------------------------------------------------------------------------------
    // utilidades
    // ----------------------------------------------------------------------------------------
    function efecto(capa, matchName) {
        var p = capa.property("ADBE Effect Parade");
        if (!p.canAddProperty(matchName)) { return null; }
        return p.addProperty(matchName);
    }

    // Busca un plugin por los nombres que puede tener según la versión. Devuelve el que anda.
    var PLUGINS = {};
    function detectarPlugins(comp) {
        var prueba = comp.layers.addSolid([0, 0, 0], "prueba_plugins", 100, 100, 1);
        var fx = prueba.property("ADBE Effect Parade");
        var buscados = {
            glow: ["Deep Glow 2", "Deep Glow", "PEDG"],
            flare: ["Optical Flares", "VC Optical Flares", "VIDEOCOPILOT OpticalFlares"],
            rsmb: ["RSMB Pro", "RSMB", "RE:Vision Effects RSMB Pro", "RE:Vision Effects RSMB"]
        };
        for (var k in buscados) {
            PLUGINS[k] = null;
            for (var i = 0; i < buscados[k].length; i++) {
                if (fx.canAddProperty(buscados[k][i])) { PLUGINS[k] = buscados[k][i]; break; }
            }
        }
        prueba.source.remove();
        anotar("Plugins: Deep Glow " + (PLUGINS.glow ? "SÍ" : "no (uso Glow nativo)") +
               " · Optical Flares " + (PLUGINS.flare ? "SÍ" : "no (uso Destello de lente nativo)") +
               " · RSMB " + (PLUGINS.rsmb ? "SÍ" : "no (uso desenfoque de movimiento nativo)"));
    }

    // Pone un valor sin romper si la propiedad no existe (plugins de otra versión, etc.)
    function poner(grupo, clave, valor) {
        try {
            var p = (typeof clave === "number") ? grupo.property(clave) : grupo.property(clave);
            if (p) { p.setValue(valor); return true; }
        } catch (e) {}
        return false;
    }

    // Curva "expo" en todos los keyframes de una propiedad: arranca y frena largo, sin golpes.
    function suavizar(prop, fuerza) {
        var f = fuerza || 80;
        for (var k = 1; k <= prop.numKeys; k++) {
            var dims = 1;
            try {
                if (prop.propertyValueType === PropertyValueType.TwoD_SPATIAL || prop.propertyValueType === PropertyValueType.ThreeD_SPATIAL) {
                    dims = 1;
                } else if (prop.propertyValueType === PropertyValueType.TwoD) {
                    dims = 2;
                } else if (prop.propertyValueType === PropertyValueType.ThreeD) {
                    dims = 3;
                }
            } catch (e) {}
            var e1 = [], e2 = [];
            for (var d = 0; d < dims; d++) {
                e1.push(new KeyframeEase(0, f));
                e2.push(new KeyframeEase(0, f));
            }
            try { prop.setTemporalEaseAtKey(k, e1, e2); } catch (e) {}
        }
    }

    function fuente(texto, lista) {
        for (var i = 0; i < lista.length; i++) {
            try {
                if (app.fonts && app.fonts.getFontsByPostScriptName) {
                    if (app.fonts.getFontsByPostScriptName(lista[i]).length) { texto.font = lista[i]; return lista[i]; }
                } else {
                    texto.font = lista[i];
                    return lista[i];
                }
            } catch (e) {}
        }
        return null;
    }

    function capaTexto(comp, contenido, tam, lista, color, pos, tracking) {
        var capa = comp.layers.addText(contenido);
        var prop = capa.property("ADBE Text Properties").property("ADBE Text Document");
        var doc = prop.value;
        fuente(doc, lista);
        doc.fontSize = tam;
        doc.fillColor = color;
        doc.applyFill = true;
        doc.applyStroke = false;
        doc.tracking = tracking || 0;
        doc.justification = ParagraphJustification.CENTER_JUSTIFY;
        prop.setValue(doc);
        capa.property("ADBE Transform Group").property("ADBE Position").setValue(pos);
        return capa;
    }

    // Aparición letra por letra: opacidad + desenfoque + tracking que se cierra.
    // Es el "look documental caro" y se arma con animadores de texto nativos.
    function animarEntradaTexto(capa, t0, dur, desenfoque) {
        var animadores = capa.property("ADBE Text Properties").property("ADBE Text Animators");
        var an = animadores.addProperty("ADBE Text Animator");
        var props = an.property("ADBE Text Animator Properties");
        props.addProperty("ADBE Text Opacity").setValue(0);
        try { props.addProperty("ADBE Text Blur").setValue([desenfoque || 30, desenfoque || 30]); } catch (e) {}
        try { props.addProperty("ADBE Text Tracking Amount").setValue(18); } catch (e) {}
        var sel = an.property("ADBE Text Selectors").addProperty("ADBE Text Selector");
        // forma "rampa hacia arriba" + suavidad: cada letra entra con su propia curva
        try {
            var av = sel.property("ADBE Text Range Advanced");
            // Rampa hacia arriba (2): con el desplazamiento de -100 a 100 las letras pasan de
            // "todas afectadas" (invisibles) a "ninguna" (visibles), de izquierda a derecha
            poner(av, "ADBE Text Range Shape", 2);
            poner(av, "ADBE Text Selector Smoothness", 100);
            poner(av, "ADBE Text Levels Min Ease", 60);
        } catch (e) {}
        var off = sel.property("ADBE Text Percent Offset");
        off.setValueAtTime(t0, -100);
        off.setValueAtTime(t0 + dur, 100);
        suavizar(off, 70);
        // la salida: todo baja junto al final del capítulo
        var op = capa.property("ADBE Transform Group").property("ADBE Opacity");
        op.setValueAtTime(CFG.segCapitulo - 2.2, 100);
        op.setValueAtTime(CFG.segCapitulo - 1.2, 0);
        suavizar(op, 60);
    }

    function solido(comp, color, nombre) {
        return comp.layers.addSolid(color, nombre, comp.width, comp.height, 1, comp.duration);
    }

    function ajuste(comp, nombre) {
        var a = comp.layers.addSolid([1, 1, 1], nombre, comp.width, comp.height, 1, comp.duration);
        a.adjustmentLayer = true;
        return a;
    }

    // máscara elíptica/rectangular con calado, para atmósferas localizadas
    function mascara(capa, x0, y0, x1, y1, calado, eliptica) {
        var m = capa.property("ADBE Mask Parade").addProperty("ADBE Mask Atom");
        var s = new Shape();
        if (eliptica) {
            var cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, rx = (x1 - x0) / 2, ry = (y1 - y0) / 2, k = 0.5523;
            s.vertices = [[cx, y0], [x1, cy], [cx, y1], [x0, cy]];
            s.inTangents = [[-rx * k, 0], [0, -ry * k], [rx * k, 0], [0, ry * k]];
            s.outTangents = [[rx * k, 0], [0, ry * k], [-rx * k, 0], [0, -ry * k]];
        } else {
            s.vertices = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]];
        }
        s.closed = true;
        m.property("ADBE Mask Shape").setValue(s);
        m.property("ADBE Mask Feather").setValue([calado, calado]);
        return m;
    }

    // ----------------------------------------------------------------------------------------
    // partículas deterministas (ceniza, polen, polvo, brasas)
    // ----------------------------------------------------------------------------------------
    // Cada partícula es una capa de forma con una expresión: posición = función del tiempo con
    // su semilla. Vuelve a entrar por el otro borde con opacidad 0 en el salto, así el
    // desenfoque de movimiento no dibuja una raya cruzando la pantalla.
    function sistemaParticulas(nombre, c) {
        var comp = app.project.items.addComp(nombre, CFG.ancho, CFG.alto, 1, CFG.segCapitulo, CFG.fps);
        comp.motionBlur = true;
        comp.shutterAngle = 180;
        for (var i = 0; i < c.cantidad; i++) {
            var capa = comp.layers.addShape();
            capa.name = nombre + "_" + (i + 1);
            var grupo = capa.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group");
            var vec = grupo.property("ADBE Vectors Group");
            var elipse = vec.addProperty("ADBE Vector Shape - Ellipse");
            var d = c.tamMin + Math.random() * (c.tamMax - c.tamMin);
            elipse.property("ADBE Vector Ellipse Size").setValue(c.alargada ? [d * 0.55, d] : [d, d * 0.8]);
            var relleno = vec.addProperty("ADBE Vector Graphic - Fill");
            var t = Math.random();
            relleno.property("ADBE Vector Fill Color").setValue([
                c.color1[0] + (c.color2[0] - c.color1[0]) * t,
                c.color1[1] + (c.color2[1] - c.color1[1]) * t,
                c.color1[2] + (c.color2[2] - c.color1[2]) * t]);
            capa.motionBlur = true;
            var tr = capa.property("ADBE Transform Group");
            tr.property("ADBE Position").expression =
                "seedRandom(" + (i + 1) + ", true);\n" +
                "var W = thisComp.width, H = thisComp.height, M = 60;\n" +
                "var x0 = random(0, W), y0 = random(0, H);\n" +
                "var vy = random(" + c.vyMin + ", " + c.vyMax + "), vx = random(" + c.vxMin + ", " + c.vxMax + ");\n" +
                "var fase = random(0, 6.283), frec = random(0.25, 1.1);\n" +
                "var t = time + random(0, 40);\n" +
                "var x = x0 + vx * t + " + c.vaiven + " * Math.sin(t * frec + fase);\n" +
                "var y = y0 + vy * t + " + (c.vaiven * 0.4) + " * Math.cos(t * frec * 0.7 + fase);\n" +
                "x = ((x + M) % (W + 2 * M) + (W + 2 * M)) % (W + 2 * M) - M;\n" +
                "y = ((y + M) % (H + 2 * M) + (H + 2 * M)) % (H + 2 * M) - M;\n" +
                "[x, y]";
            tr.property("ADBE Rotate Z").expression =
                "seedRandom(" + (i + 1) + ", true); random(0, 360) + time * random(-90, 90)";
            // apagado en los bordes (el salto) + parpadeo opcional (brasas)
            tr.property("ADBE Opacity").expression =
                "seedRandom(" + (i + 7) + ", true);\n" +
                "var p = transform.position, W = thisComp.width, H = thisComp.height;\n" +
                "var borde = Math.min(linear(p[1], -60, 20, 0, 1), linear(p[1], H - 20, H + 60, 1, 0),\n" +
                "                     linear(p[0], -60, 20, 0, 1), linear(p[0], W - 20, W + 60, 1, 0));\n" +
                "var base = random(" + c.opMin + ", " + c.opMax + ");\n" +
                (c.parpadeo ? "base *= 0.55 + 0.45 * Math.abs(Math.sin(time * random(3, 9) + random(0, 6)));\n" : "") +
                "base * borde";
        }
        return comp;
    }

    // ----------------------------------------------------------------------------------------
    // importación de los renders de Blender
    // ----------------------------------------------------------------------------------------
    // Acepta cualquiera de las tres salidas del proyecto:
    //   <carpeta>/<capitulo>/frames/0001.png …   (triasico_cycles.py --animar)  → secuencia
    //   <carpeta>/<capitulo>/<capitulo>.png      (render fijo)
    //   <carpeta>/<capitulo>.jpg                 (las pruebas del repo)
    function importar(carpeta, clave) {
        var frames = new Folder(carpeta.fsName + "/" + clave + "/frames");
        if (frames.exists) {
            var lista = frames.getFiles("*.png");
            if (lista.length > 1) {
                lista.sort();
                var op = new ImportOptions(lista[0]);
                op.sequence = true;
                var sec = app.project.importFile(op);
                sec.mainSource.conformFrameRate = CFG.fps;
                sec.name = clave + "_secuencia";
                return { item: sec, fija: false };
            }
        }
        var candidatos = [carpeta.fsName + "/" + clave + "/" + clave + ".png",
                          carpeta.fsName + "/" + clave + ".png",
                          carpeta.fsName + "/" + clave + ".jpg"];
        for (var i = 0; i < candidatos.length; i++) {
            var f = new File(candidatos[i]);
            if (f.exists) {
                var it = app.project.importFile(new ImportOptions(f));
                return { item: it, fija: true };
            }
        }
        return null;
    }

    // ----------------------------------------------------------------------------------------
    // un capítulo
    // ----------------------------------------------------------------------------------------
    function armarCapitulo(cap, fuenteImg, parts) {
        var comp = app.project.items.addComp("CAP_" + cap.clave, CFG.ancho, CFG.alto, 1, CFG.segCapitulo, CFG.fps);
        comp.motionBlur = true;
        var W = CFG.ancho, H = CFG.alto, cx = W / 2;

        // 1) la imagen de Blender, cubriendo las 3 pantallas
        var placa;
        if (fuenteImg) {
            placa = comp.layers.add(fuenteImg.item, CFG.segCapitulo);
            var esc = Math.max(W / fuenteImg.item.width, H / fuenteImg.item.height) * 100;
            var tr = placa.property("ADBE Transform Group");
            if (fuenteImg.fija) {
                // cámara lenta sobre la imagen fija: acercamiento + deriva lateral, curva expo
                tr.property("ADBE Scale").setValueAtTime(0, [esc * 1.02, esc * 1.02]);
                tr.property("ADBE Scale").setValueAtTime(CFG.segCapitulo, [esc * 1.12, esc * 1.12]);
                tr.property("ADBE Position").setValueAtTime(0, [cx + W * 0.02, H / 2]);
                tr.property("ADBE Position").setValueAtTime(CFG.segCapitulo, [cx - W * 0.02, H / 2 - H * 0.01]);
                suavizar(tr.property("ADBE Scale"), 35);
                suavizar(tr.property("ADBE Position"), 35);
                if (fuenteImg.item.width < W * 0.5) {
                    anotar("OJO " + cap.clave + ": la imagen mide " + fuenteImg.item.width + " px de ancho; para el LED renderizá con --calidad led (5760 × 1080).");
                }
            } else {
                tr.property("ADBE Scale").setValue([esc, esc]);
            }
        } else {
            placa = solido(comp, [0.12, 0.09, 0.07], "FALTA_RENDER_" + cap.clave);
            anotar("Falta el render de " + cap.clave + ": quedó un sólido marrón en su lugar.");
        }
        placa.name = "blender_" + cap.clave;
        if (cap.atm === "ceniza") {
            // la tierra tiembla: el volcán está activo
            placa.property("ADBE Transform Group").property("ADBE Position").expression =
                "value + [wiggle(9, 4)[0] - value[0], wiggle(7, 3)[1] - value[1]]";
        }

        // 2) atmósfera propia de cada momento
        if (cap.atm === "amanecer") {
            var capaSol = solido(comp, [0, 0, 0], "sol_amanecer");
            capaSol.blendingMode = BlendingMode.ADD;
            var fl = PLUGINS.flare ? efecto(capaSol, PLUGINS.flare) : null;
            if (fl) {
                poner(fl, "Position XY", [W * 0.18, H * 0.42]);
                poner(fl, "Brightness", 90);
            } else {
                fl = efecto(capaSol, "ADBE Lens Flare");
                if (fl) {
                    fl.property(1).setValue([W * 0.18, H * 0.42]);
                    fl.property(2).setValueAtTime(0, 60);
                    fl.property(2).setValueAtTime(CFG.segCapitulo, 115);
                    suavizar(fl.property(2), 40);
                    fl.property(3).setValue(2);          // 35 mm: el menos "de videojuego"
                }
            }
            capaSol.property("ADBE Transform Group").property("ADBE Opacity").setValue(70);
            // bruma cálida baja, como el aire del amanecer sobre el río
            var bruma = solido(comp, [0.95, 0.66, 0.40], "bruma_amanecer");
            bruma.blendingMode = BlendingMode.SCREEN;
            mascara(bruma, -200, H * 0.45, W + 200, H * 0.95, 260, false);
            bruma.property("ADBE Transform Group").property("ADBE Opacity").setValue(22);
        }
        if (cap.atm === "rayos") {
            // rayos de sol entre las copas: una copia de la placa con CC Light Rays, en Suma
            if (fuenteImg) {
                var rayos = placa.duplicate();
                rayos.name = "rayos_de_sol";    // el duplicado queda justo arriba de la placa: debajo del color y los textos
                rayos.blendingMode = BlendingMode.ADD;
                var lr = efecto(rayos, "CC Light Rays");
                if (lr) {
                    lr.property(1).setValue(140);                    // intensidad
                    lr.property(2).setValue([W * 0.62, -H * 0.12]); // el sol arriba, fuera de cuadro
                    lr.property(3).setValue(160);                    // radio
                    lr.property(4).setValue(40);
                    lr.property(2).expression = "value + [Math.sin(time * 0.35) * 180, 0]";   // las copas se mueven
                }
                var cl = efecto(rayos, "ADBE Brightness & Contrast 2");
                if (cl) { cl.property(1).setValue(-35); cl.property(2).setValue(45); }
                rayos.property("ADBE Transform Group").property("ADBE Opacity").setValue(45);
            }
        }
        if (cap.atm === "calor" || cap.atm === "viento") {
            // reverberación del calor sobre el suelo: sólo en la mitad de abajo, con calado
            var calor = ajuste(comp, "reverberacion_calor");
            var td = efecto(calor, "ADBE Turbulent Displace");
            if (td) {
                // suave: a 14 las barrancas se ondulaban como agua
                td.property(2).setValue(cap.atm === "calor" ? 5 : 3);    // cantidad
                td.property(3).setValue(60);                             // tamaño
                td.property(5).setValue(2.2);                            // complejidad
                td.property(6).expression = "time * 140";                // evolución
            }
            mascara(calor, -100, H * 0.52, W + 100, H + 100, 220, false);
        }
        if (cap.atm === "calor") {
            // resplandor del cráter que late (lava debajo de la columna de ceniza)
            var lava = solido(comp, [1.0, 0.36, 0.10], "resplandor_crater");
            lava.blendingMode = BlendingMode.ADD;
            mascara(lava, cx - 380, H * 0.18, cx + 380, H * 0.52, 240, true);
            lava.property("ADBE Transform Group").property("ADBE Opacity").expression =
                "18 + 10 * Math.abs(Math.sin(time * 1.7)) + wiggle(6, 6) - value";
        }
        if (cap.atm === "ceniza") {
            // cielo cargado: degradado ceniza arriba que baja con el tiempo
            var cielo = solido(comp, [0, 0, 0], "cielo_de_ceniza");
            var rampa = efecto(cielo, "ADBE Ramp");
            if (rampa) {
                rampa.property(1).setValue([cx, 0]);
                rampa.property(2).setValue([0.33, 0.30, 0.28]);
                rampa.property(3).setValue([cx, H * 0.75]);
                rampa.property(4).setValue([0, 0, 0]);
            }
            cielo.blendingMode = BlendingMode.SCREEN;
            cielo.property("ADBE Transform Group").property("ADBE Opacity").setValueAtTime(0, 30);
            cielo.property("ADBE Transform Group").property("ADBE Opacity").setValueAtTime(CFG.segCapitulo, 75);
        }

        // 3) partículas: dos planos (lejos nítido y chico, cerca grande y fuera de foco)
        if (parts[cap.atm]) {
            for (var pi = 0; pi < parts[cap.atm].length; pi++) {
                var pp = parts[cap.atm][pi];
                var capaP = comp.layers.add(pp.comp);
                capaP.name = pp.comp.name;
                capaP.blendingMode = pp.modo || BlendingMode.NORMAL;
                if (pp.desenfoque) {
                    var gb = efecto(capaP, "ADBE Gaussian Blur 2");
                    if (gb) { gb.property(1).setValue(pp.desenfoque); gb.property(3).setValue(1); }
                }
                if (pp.brillo) {
                    var gl = PLUGINS.glow ? efecto(capaP, PLUGINS.glow) : null;
                    if (!gl) {
                        gl = efecto(capaP, "ADBE Glo2");
                        if (gl) { gl.property(2).setValue(40); gl.property(3).setValue(18); gl.property(4).setValue(1.4); }
                    }
                }
                if (PLUGINS.rsmb) { efecto(capaP, PLUGINS.rsmb); }
            }
        }

        // 4) color: tono partido (sombras frías, luces cálidas), contraste, viñeta, grano
        var color = ajuste(comp, "color_" + cap.clave);
        var tinte = efecto(color, "ADBE Tint");
        if (tinte) {
            tinte.property(1).setValue(cap.look.negro);
            tinte.property(2).setValue(cap.look.blanco);
            tinte.property(3).setValue(cap.look.tinte * 0.6);     // a pleno aplanaba el color del render
        }
        var bc = efecto(color, "ADBE Brightness & Contrast 2");
        if (bc) { bc.property(1).setValue(cap.look.brillo); bc.property(2).setValue(cap.look.contraste); }
        var glowFinal = PLUGINS.glow ? efecto(color, PLUGINS.glow) : null;
        if (!glowFinal) {
            // brillo suave en las luces altas: el "aire" de la fotografía de cine
            glowFinal = efecto(color, "ADBE Glo2");
            // el sustituto de Deep Glow se quedaba con todo el cielo (umbral 78 %) y lavaba la imagen
            if (glowFinal) { glowFinal.property(2).setValue(93); glowFinal.property(3).setValue(45); glowFinal.property(4).setValue(0.2); }
        }
        var grano = efecto(color, "ADBE Noise");
        if (grano) { grano.property(1).setValue(1.6); }

        var vineta = solido(comp, [0, 0, 0], "vineta");
        var mv = mascara(vineta, -W * 0.05, -H * 0.35, W * 1.05, H * 1.35, 520, true);
        mv.inverted = true;
        vineta.property("ADBE Transform Group").property("ADBE Opacity").setValue(55);

        // 5) textos: título en la pantalla del centro, zona segura (no cruzan las uniones)
        var titulo = capaTexto(comp, cap.titulo, cap.clave === "titulo" ? 170 : 104, CFG.fuentes, CFG.crema,
                               [cx, H * (cap.clave === "titulo" ? 0.47 : 0.40)], cap.clave === "titulo" ? 420 : 60);
        titulo.name = "titulo";
        animarEntradaTexto(titulo, 0.8, 2.2, 40);
        var sombra = efecto(titulo, "ADBE Drop Shadow");
        if (sombra) { sombra.property(2).setValue(160); sombra.property(4).setValue(0); sombra.property(5).setValue(24); }

        var sub = capaTexto(comp, cap.sub, 34, CFG.fuenteFina, CFG.crema,
                            [cx, H * (cap.clave === "titulo" ? 0.60 : 0.50)], 30);
        sub.name = "subtitulo";
        try {
            // el subtítulo largo se corta en dos líneas dentro de la pantalla del centro
            var doc = sub.property("ADBE Text Properties").property("ADBE Text Document");
            var d = doc.value;
            if (cap.sub.length > 70) {
                var corte = cap.sub.lastIndexOf(" ", Math.floor(cap.sub.length / 2) + 8);
                d.text = cap.sub.substring(0, corte) + "\r" + cap.sub.substring(corte + 1);
                doc.setValue(d);
            }
        } catch (e) {}
        animarEntradaTexto(sub, 1.8, 2.0, 16);

        // línea fina ocre que se dibuja bajo el título
        var linea = comp.layers.addShape();
        linea.name = "linea_titulo";
        var g = linea.property("ADBE Root Vectors Group").addProperty("ADBE Vector Group").property("ADBE Vectors Group");
        var rect = g.addProperty("ADBE Vector Shape - Rect");
        rect.property("ADBE Vector Rect Size").setValue([520, 2]);
        g.addProperty("ADBE Vector Graphic - Fill").property("ADBE Vector Fill Color").setValue(CFG.ocre);
        var ltr = linea.property("ADBE Transform Group");
        ltr.property("ADBE Position").setValue([cx, H * (cap.clave === "titulo" ? 0.555 : 0.455)]);
        ltr.property("ADBE Scale").setValueAtTime(1.2, [0, 100]);
        ltr.property("ADBE Scale").setValueAtTime(2.6, [100, 100]);
        suavizar(ltr.property("ADBE Scale"), 85);
        ltr.property("ADBE Opacity").setValueAtTime(CFG.segCapitulo - 2.2, 100);
        ltr.property("ADBE Opacity").setValueAtTime(CFG.segCapitulo - 1.2, 0);

        // 6) fichas de especies: pantallas de los costados, abajo, entran escalonadas
        for (var fi = 0; fi < cap.fichas.length; fi++) {
            var xF = fi === 0 ? CFG.pantalla * 0.5 : CFG.pantalla * 2.5;
            var nombreSp = capaTexto(comp, cap.fichas[fi][0], 44, CFG.fuentes, CFG.crema, [xF, H * 0.80], 20);
            nombreSp.name = "ficha_" + (fi + 1);
            try {   // el nombre científico va en cursiva si la fuente lo permite
                var dn = nombreSp.property("ADBE Text Properties").property("ADBE Text Document");
                var vn = dn.value; vn.fauxItalic = true; dn.setValue(vn);
            } catch (e) {}
            var datoSp = capaTexto(comp, cap.fichas[fi][1], 28, CFG.fuenteFina, CFG.ocre, [xF, H * 0.855], 40);
            datoSp.name = "ficha_" + (fi + 1) + "_dato";
            var tF = 4.0 + fi * 1.4;
            animarEntradaTexto(nombreSp, tF, 1.4, 20);
            animarEntradaTexto(datoSp, tF + 0.4, 1.2, 12);
        }

        return comp;
    }

    // ----------------------------------------------------------------------------------------
    // la pieza completa
    // ----------------------------------------------------------------------------------------
    function armarMaestro(comps) {
        var paso = CFG.segCapitulo - CFG.solape;
        var dur = paso * (comps.length - 1) + CFG.segCapitulo;
        var m = app.project.items.addComp($.global.FNS_MODO === "sanjuan" ? "FNS2026_RECORRIDO_SAN_JUAN_LED" : "FNS2026_PARQUE_TRIASICO_LED",
                                          CFG.ancho, CFG.alto, 1, dur, CFG.fps);
        m.motionBlur = true;
        var capas = [];
        for (var i = 0; i < comps.length; i++) {
            var c = m.layers.add(comps[i]);
            c.startTime = i * paso;     // cada capa nueva queda arriba: el que entra tapa al que sale
            capas.push(c);
            // marcador por capítulo: sirve de punto de cue si se lo manda a Resolume
            var mk = new MarkerValue(CAPITULOS[i].titulo);
            m.markerProperty.setValueAtTime(i * paso, mk);
        }

        for (var k = 1; k < capas.length; k++) {
            var entra = capas[k];
            var t0 = entra.startTime;
            var op = entra.property("ADBE Transform Group").property("ADBE Opacity");
            if (CAPITULOS[k].clave === "hoy") {
                transicionTiempoProfundo(m, entra, t0);
            } else {
                // fundido con desenfoque que se abre: como un foco que se corre
                op.setValueAtTime(t0, 0);
                op.setValueAtTime(t0 + CFG.solape, 100);
                suavizar(op, 60);
                var bl = efecto(entra, "ADBE Gaussian Blur 2");
                if (bl) {
                    bl.property(1).setValueAtTime(t0, 60);
                    bl.property(1).setValueAtTime(t0 + CFG.solape, 0);
                    bl.property(3).setValue(1);
                    suavizar(bl.property(1), 70);
                }
            }
        }
        // negro al principio y al final (el LED no arranca de golpe)
        var primero = capas[0].property("ADBE Transform Group").property("ADBE Opacity");
        primero.setValueAtTime(0, 0);
        primero.setValueAtTime(1.2, 100);
        var ultimo = capas[capas.length - 1].property("ADBE Transform Group").property("ADBE Opacity");
        ultimo.setValueAtTime(dur - 1.5, 100);
        ultimo.setValueAtTime(dur, 0);
        return m;
    }

    // Ceniza → Hoy: 231 millones de años en 1,5 segundos. Un contador que cae a cero,
    // estratos que se abren (persianas horizontales = capas de roca) y un destello de sol.
    // Es LA transición de la pieza: el salto del Triásico al Valle de la Luna.
    function transicionTiempoProfundo(m, entra, t0) {
        var dur = CFG.solape + 1.0;
        var H = CFG.alto, cx = CFG.ancho / 2;
        var persiana = efecto(entra, "ADBE Venetian Blinds");
        if (persiana) {
            persiana.property(1).setValueAtTime(t0, 100);
            persiana.property(1).setValueAtTime(t0 + dur, 0);
            persiana.property(2).setValue(0);           // bandas horizontales, como estratos
            persiana.property(3).setValue(46);
            persiana.property(4).setValue(18);
            suavizar(persiana.property(1), 75);
        }
        // En After 2026 cambió el orden de parámetros del desenfoque radial (el índice 3 pasó a ser
        // un grupo y la pieza entera se caía). Se busca por nombre interno y, si no está, se sigue.
        var rb = efecto(entra, "ADBE Radial Blur");
        if (rb) {
            try {
                var cant = rb.property("ADBE Radial Blur-0001");
                cant.setValueAtTime(t0, 40);
                cant.setValueAtTime(t0 + dur, 0);
                suavizar(cant, 70);
                poner(rb, "ADBE Radial Blur-0002", [cx, H * 0.45]);
                if (!poner(rb, "ADBE Radial Blur-0003", 2)) { poner(rb, "ADBE Radial Blur-0004", 2); }   // 2 = zoom
            } catch (e) {
                anotar("desenfoque radial de la transición: no se pudo configurar en esta versión (" + e.toString() + ")");
            }
        }
        var cont = capaTexto(m, "231.000.000", 150, CFG.fuentes, CFG.crema, [cx, H * 0.46], 80);
        cont.name = "contador_millones_de_anios";
        cont.startTime = t0 - 0.6;
        cont.outPoint = t0 + dur + 0.4;
        cont.property("ADBE Text Properties").property("ADBE Text Document").expression =
            "var a = " + (t0 - 0.2) + ", b = " + (t0 + dur - 0.2) + ";\n" +
            "var k = ease(time, a, b, 0, 1);\n" +
            "var n = Math.round(231000000 * (1 - k * k));\n" +
            "var s = n.toString().replace(/\\B(?=(\\d{3})+(?!\\d))/g, '.');\n" +
            "time > b ? 'HOY' : s + ' años'";
        var cop = cont.property("ADBE Transform Group").property("ADBE Opacity");
        cop.setValueAtTime(t0 - 0.6, 0);
        cop.setValueAtTime(t0 - 0.2, 100);
        cop.setValueAtTime(t0 + dur, 100);
        cop.setValueAtTime(t0 + dur + 0.4, 0);
        suavizar(cop, 60);
        var csc = cont.property("ADBE Transform Group").property("ADBE Scale");
        csc.setValueAtTime(t0 - 0.6, [92, 92]);
        csc.setValueAtTime(t0 + dur + 0.4, [104, 104]);
        cont.moveToBeginning();

        var flash = m.layers.addSolid([1.0, 0.95, 0.86], "destello_sol", CFG.ancho, CFG.alto, 1, 2);
        flash.startTime = t0 + dur - 0.35;
        flash.blendingMode = BlendingMode.ADD;
        var fo = flash.property("ADBE Transform Group").property("ADBE Opacity");
        fo.setValueAtTime(t0 + dur - 0.35, 0);
        fo.setValueAtTime(t0 + dur - 0.1, 70);
        fo.setValueAtTime(t0 + dur + 0.8, 0);
        suavizar(fo, 50);
        flash.moveToBeginning();
    }

    // ----------------------------------------------------------------------------------------
    // principal
    // ----------------------------------------------------------------------------------------
    if (!app.project) { app.newProject(); }
    // desde el puente (fns2026/ae_puente) no hay nadie para contestar un diálogo
    var carpeta = $.global.FNS_CARPETA ? new Folder($.global.FNS_CARPETA)
                                       : Folder.selectDialog("Elegí la carpeta de renders de Blender (la que tiene titulo/, rio/… o titulo.jpg, rio.jpg…)");
    if (!carpeta) { return; }

    app.beginUndoGroup("Parque Triásico FNS 2026");
    var raiz = app.project.items.addFolder($.global.FNS_MODO === "sanjuan" ? "FNS2026_Recorrido_San_Juan" : "FNS2026_Parque_Triasico");

    var pruebaComp = app.project.items.addComp("_detectar_plugins", 100, 100, 1, 1, CFG.fps);
    detectarPlugins(pruebaComp);
    pruebaComp.remove();

    // sistemas de partículas, uno por atmósfera (se reusan si dos capítulos comparten)
    var P = {};
    P.ceniza = [
        { comp: sistemaParticulas("ceniza_lejos", { cantidad: 160, tamMin: 3, tamMax: 7, color1: [0.62, 0.60, 0.58], color2: [0.42, 0.40, 0.38],
            vyMin: 40, vyMax: 90, vxMin: 20, vxMax: 60, vaiven: 40, opMin: 35, opMax: 80 }) },
        { comp: sistemaParticulas("ceniza_cerca", { cantidad: 45, tamMin: 14, tamMax: 30, color1: [0.55, 0.53, 0.50], color2: [0.35, 0.33, 0.31],
            vyMin: 120, vyMax: 220, vxMin: 50, vxMax: 140, vaiven: 80, opMin: 40, opMax: 75 }), desenfoque: 14 },
        { comp: sistemaParticulas("brasas", { cantidad: 30, tamMin: 3, tamMax: 6, color1: [1.0, 0.55, 0.18], color2: [1.0, 0.30, 0.08], alargada: true,
            vyMin: -140, vyMax: -60, vxMin: 30, vxMax: 110, vaiven: 60, opMin: 60, opMax: 100, parpadeo: true }), modo: BlendingMode.ADD, brillo: true }
    ];
    P.polen = [
        { comp: sistemaParticulas("polen_esporas", { cantidad: 90, tamMin: 3, tamMax: 8, color1: [1.0, 0.94, 0.72], color2: [0.90, 0.82, 0.55],
            vyMin: -12, vyMax: 10, vxMin: 8, vxMax: 30, vaiven: 70, opMin: 20, opMax: 65, parpadeo: true }), modo: BlendingMode.ADD, brillo: true },
        { comp: sistemaParticulas("polen_cerca", { cantidad: 16, tamMin: 12, tamMax: 22, color1: [1.0, 0.92, 0.70], color2: [0.95, 0.85, 0.60],
            vyMin: -10, vyMax: 8, vxMin: 10, vxMax: 35, vaiven: 90, opMin: 15, opMax: 40 }), modo: BlendingMode.ADD, desenfoque: 12 }
    ];
    P.rayos = [
        { comp: sistemaParticulas("polvo_en_la_luz", { cantidad: 120, tamMin: 2, tamMax: 5, color1: [1.0, 0.95, 0.80], color2: [0.95, 0.88, 0.70],
            vyMin: -6, vyMax: 6, vxMin: -6, vxMax: 10, vaiven: 45, opMin: 15, opMax: 60, parpadeo: true }), modo: BlendingMode.ADD }
    ];
    P.calor = [
        { comp: sistemaParticulas("polvo_llanura", { cantidad: 60, tamMin: 3, tamMax: 7, color1: [0.85, 0.72, 0.55], color2: [0.70, 0.58, 0.42],
            vyMin: -4, vyMax: 4, vxMin: 30, vxMax: 80, vaiven: 30, opMin: 10, opMax: 35 }) }
    ];
    P.viento = [
        { comp: sistemaParticulas("polvo_viento_zonda", { cantidad: 110, tamMin: 2, tamMax: 5, color1: [0.90, 0.80, 0.66], color2: [0.75, 0.62, 0.50], alargada: true,
            vyMin: -8, vyMax: 12, vxMin: 260, vxMax: 520, vaiven: 20, opMin: 10, opMax: 40 }) }
    ];
    P.amanecer = [
        { comp: sistemaParticulas("insectos_amanecer", { cantidad: 40, tamMin: 2, tamMax: 4, color1: [1.0, 0.85, 0.60], color2: [1.0, 0.70, 0.45],
            vyMin: -20, vyMax: 20, vxMin: -25, vxMax: 25, vaiven: 120, opMin: 25, opMax: 70, parpadeo: true }), modo: BlendingMode.ADD, brillo: true }
    ];
    var carpetaP = app.project.items.addFolder("particulas");
    carpetaP.parentFolder = raiz;
    for (var kk in P) { for (var q = 0; q < P[kk].length; q++) { P[kk][q].comp.parentFolder = carpetaP; } }

    var carpetaCaps = app.project.items.addFolder("capitulos");
    carpetaCaps.parentFolder = raiz;
    var carpetaRender = app.project.items.addFolder("renders_blender");
    carpetaRender.parentFolder = raiz;
    var comps = [];
    for (var i = 0; i < CAPITULOS.length; i++) {
        var img = importar(carpeta, CAPITULOS[i].clave);
        if (img) { img.item.parentFolder = carpetaRender; }
        var c = armarCapitulo(CAPITULOS[i], img, P);
        c.parentFolder = carpetaCaps;
        comps.push(c);
    }
    var maestro = armarMaestro(comps);
    maestro.parentFolder = raiz;

    // cola de render: sin pérdida, para después pasarlo a DXV (Resolume) o HAP con Alley/AME
    try {
        var salida = new Folder(carpeta.fsName + "/AE_salida");
        if (!salida.exists) { salida.create(); }
        var rq = app.project.renderQueue.items.add(maestro);
        var om = rq.outputModule(1);
        try { om.applyTemplate("High Quality"); } catch (e1) { try { om.applyTemplate("Alta calidad"); } catch (e2) {} }
        om.file = new File(salida.fsName + ($.global.FNS_MODO === "sanjuan" ? "/FNS2026_Recorrido_San_Juan_LED_5760x1080.mov"
                                                                          : "/FNS2026_Parque_Triasico_LED_5760x1080.mov"));
        anotar("En la cola de render: " + om.file.fsName);
    } catch (e) {
        anotar("No pude armar la cola de render (" + e.toString() + "): agregá FNS2026_PARQUE_TRIASICO_LED a mano.");
    }

    maestro.openInViewer();
    app.endUndoGroup();
    var resumen = "Parque Triásico listo.\n\n" + informe.join("\n") +
          "\n\nDuración: " + maestro.duration.toFixed(1) + " s · " + CFG.ancho + " × " + CFG.alto + " @ " + CFG.fps + " fps";
    if ($.global.FNS_PUENTE) {
        $.global.PUENTE.informar(resumen);
        $.global.FNS_MAESTRO = maestro;          // el trabajo del puente saca capturas de acá
    } else {
        alert(resumen);
    }
})();
