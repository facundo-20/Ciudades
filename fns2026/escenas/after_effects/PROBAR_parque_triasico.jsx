/*  PROBAR: Parque Triásico en el LED (5760 × 1080).
    After Effects › Archivo › Scripts › Ejecutar archivo de script… › este archivo.
    Arma los 6 capítulos (título, río, bosque, llanura, ceniza, hoy) con la transición de los
    231 millones de años. Usa las panorámicas del LED (fns2026/escenas/hiperreal/led) si ya
    están; si no, los renders 16:9 de calidad media (se ven recortados en el LED).
*/
(function () {
    var aqui = new File($.fileName).parent;                  // fns2026/escenas/after_effects
    var raiz = aqui.parent.parent.parent;                    // la carpeta del repo
    var led = new Folder(raiz.fsName + "/fns2026/escenas/hiperreal/led");
    var media = new Folder(raiz.fsName + "/fns2026/escenas/hiperreal/pruebas_media");
    var hayLed = led.exists && led.getFiles("*.jpg").length >= 6;
    $.global.FNS_CARPETA = (hayLed ? led : media).fsName;
    try {
        $.evalFile(new File(aqui.fsName + "/parque_triasico_ae.jsx"));
    } finally {
        $.global.FNS_CARPETA = null;
    }
})();
