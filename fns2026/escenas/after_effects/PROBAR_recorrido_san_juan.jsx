/*  PROBAR: Recorrido por San Juan en el LED (5760 × 1080).
    After Effects › Archivo › Scripts › Ejecutar archivo de script… › este archivo.
    Arma la pieza completa con las 7 panorámicas de fns2026/escenas/sanjuan/led: el Sanjuansaurus
    muestra El Hongo, la Cancha de Bochas, el Cerro Alcázar, la Pampa El Leoncito, Cuesta del
    Viento, la Catedral y el Teatro del Bicentenario. Deja el render en la cola de After.
    Sin diálogos: la carpeta se busca sola a partir de dónde está este archivo en el repo.
*/
(function () {
    var aqui = new File($.fileName).parent;                  // fns2026/escenas/after_effects
    var raiz = aqui.parent.parent.parent;                    // la carpeta del repo
    var led = new Folder(raiz.fsName + "/fns2026/escenas/sanjuan/led");
    var media = new Folder(raiz.fsName + "/fns2026/escenas/sanjuan/pruebas_media");
    $.global.FNS_MODO = "sanjuan";
    $.global.FNS_CARPETA = (led.exists ? led : media).fsName;
    try {
        $.evalFile(new File(aqui.fsName + "/parque_triasico_ae.jsx"));
    } finally {
        $.global.FNS_MODO = null;
        $.global.FNS_CARPETA = null;
    }
})();
