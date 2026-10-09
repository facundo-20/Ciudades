// Cómo arranca el ejecutable en cada máquina, por línea de comandos (los .bat de Builds/ ya los traen):
//
//   --sala pared|cubo         pared LED 5760×1080 (por defecto) o sala piso + paredes (sala_cubo.json)
//   --calidad maxima|alta|media   maxima: OMEN con RTX (trazado de rayos si la placa lo tiene);
//                             alta: por defecto; media: Mac M4 o placas chicas
//   --capitulo N --sin-auto   arrancar en un capítulo / no avanzar solo
//   --sin-textos              sin títulos ni fichas (para mandar la imagen limpia a TD o Arena)
//   --simular                 visitante inventado (sin sensores)
//   --osc 7001,10000          puertos de los sensores
//   --spout NOMBRE            (Windows) comparte la imagen por Spout a TD / Resolume
//   --syphon NOMBRE           (Mac) lo mismo por Syphon
//   --capturas CARPETA        recorre los capítulos, guarda un PNG de cada uno y se cierra
//   --fps 60                  tope de cuadros
// Además valen los de Unity: -screen-width 5760 -screen-height 1080 -popupwindow -monitor 2

using System;
using UnityEngine;

namespace FNS
{
    [DefaultExecutionOrder(-1000)]
    public class Arranque : MonoBehaviour
    {
        public Sensores sensores;
        public Sala sala;
        public Interfaz interfaz;
        public Calidad calidad;
        [Tooltip("Componentes de salida (Spout en Windows, Syphon en Mac) que pone el constructor")]
        public Behaviour salidaVideo;

        static string[] args;

        static string[] Args => args ??= Environment.GetCommandLineArgs();

        public static bool Tiene(string clave) => Array.IndexOf(Args, clave) >= 0;

        public static string Texto(string clave, string siNo = null)
        {
            int i = Array.IndexOf(Args, clave);
            return i >= 0 && i + 1 < Args.Length ? Args[i + 1] : siNo;
        }

        public static int Entero(string clave, int siNo) => int.TryParse(Texto(clave), out int v) ? v : siNo;

        void Awake()
        {
            Application.runInBackground = true;
            QualitySettings.vSyncCount = 0;
            Application.targetFrameRate = Entero("--fps", 60);
            if (Tiene("--simular")) sensores.simular = true;
            string osc = Texto("--osc");
            if (!string.IsNullOrEmpty(osc))
            {
                var partes = osc.Split(',');
                var puertos = new int[partes.Length];
                for (int i = 0; i < partes.Length; i++) int.TryParse(partes[i].Trim(), out puertos[i]);
                sensores.puertosOsc = puertos;
            }
            if (Tiene("--sin-textos")) interfaz.mostrarTextos = false;

            string modo = Texto("--sala", "pared");
            var cfg = Sala.Leer($"sala_{modo}.json") ?? Sala.Leer("sala_pared.json");
            if (cfg == null)
            {
                Debug.LogWarning("[FNS] no encuentro StreamingAssets/sala_*.json: uso una pared de 5760×1080");
                cfg = new ConfigSala();
            }
            sala.Armar(cfg);
            interfaz.config = cfg;
            calidad.Aplicar(Texto("--calidad", "alta"), sala);

            string nombre = Texto("--spout") ?? Texto("--syphon");
            if (salidaVideo)
            {
                salidaVideo.enabled = nombre != null;
                // el nombre del emisor: la propiedad se llama distinto en Spout y Syphon; se pone por
                // reflexión para no atar este código a los dos paquetes
                if (nombre != null)
                {
                    var tipo = salidaVideo.GetType();
                    var p = tipo.GetProperty("spoutName") ?? tipo.GetProperty("ServerName");
                    p?.SetValue(salidaVideo, nombre);
                }
            }
        }
    }
}
