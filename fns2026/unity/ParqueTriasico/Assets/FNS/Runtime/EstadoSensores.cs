// El estado unificado de los sensores: la misma lógica que recibir() y paquete() del puente de
// Node (experiencia/server/puente.mjs), para que la web y Unity reaccionen igual a los mismos
// mensajes. Sin Unity adentro: se prueba con dotnet en la nube.
//
//   :7001  tracker lidarwall   /wall/touch/<n>/x|y|active, /wall/count
//   :10000 cuerpo / TD         /body/x, /body/present, /touch/u, /touch/v, /touch/down
//   gestos en cualquiera       /gesto/<nombre> (brazos_arriba, salto, siguiente, anterior)

using System;
using System.Collections.Generic;

namespace FNS
{
    public struct Toque
    {
        public string id;
        public float u, v;      // 0..1 sobre la pantalla, (0,0) arriba a la izquierda
        public bool nuevo;      // el primer cuadro del toque: ahí se dispara la acción
    }

    public sealed class EstadoSensores
    {
        sealed class ToqueMuro { public float u, v; public bool activo, nuevo; }

        readonly Dictionary<string, ToqueMuro> muro = new Dictionary<string, ToqueMuro>();
        readonly Queue<string> gestos = new Queue<string>();
        float tdU = 0.5f, tdV = 0.5f;
        bool tdAbajo, tdNuevo;
        bool cuerpoPresente;
        float cuerpoX = 0.5f;
        double ultimo = double.NegativeInfinity;

        /// <summary>Segundos sin mensajes para dar al tracker por caído (sin dedos fantasma).</summary>
        public double silencioMaximo = 1.5;

        public void Recibir(string direccion, object[] valores, double ahora)
        {
            ultimo = ahora;
            var p = direccion.TrimStart('/').Split('/');
            var m = new OscMensaje { direccion = direccion, valores = valores };
            float v = m.Numero();
            if (p.Length == 4 && p[0] == "wall" && p[1] == "touch")
            {
                if (!muro.TryGetValue(p[2], out var t)) muro[p[2]] = t = new ToqueMuro();
                if (p[3] == "active") { bool a = v != 0; if (a && !t.activo) t.nuevo = true; t.activo = a; }
                else if (p[3] == "x") t.u = v;
                else if (p[3] == "y") t.v = v;
            }
            else if (p[0] == "body" && p.Length > 1)
            {
                if (p[1] == "x") cuerpoX = v;
                if (p[1] == "present") cuerpoPresente = v != 0;
            }
            else if (p[0] == "touch" && p.Length > 1)
            {
                if (p[1] == "u") tdU = v;
                if (p[1] == "v") tdV = v;
                if (p[1] == "down") { bool d = v != 0; tdNuevo = d && !tdAbajo; tdAbajo = d; }
            }
            else if (p[0] == "gesto" && p.Length > 1 && p[1].Length > 0)
            {
                gestos.Enqueue(p[1]);
            }
        }

        /// <summary>Lo que hay ahora: toques activos (y "nuevo" sólo una vez) y el cuerpo.</summary>
        public void Leer(double ahora, List<Toque> toques, out bool presente, out float x)
        {
            toques.Clear();
            bool vivo = ahora - ultimo < silencioMaximo;
            if (vivo)
            {
                foreach (var kv in muro)
                {
                    var t = kv.Value;
                    if (!t.activo) continue;
                    toques.Add(new Toque { id = "s" + kv.Key, u = t.u, v = t.v, nuevo = t.nuevo });
                    t.nuevo = false;
                }
                if (tdAbajo) { toques.Add(new Toque { id = "td", u = tdU, v = tdV, nuevo = tdNuevo }); tdNuevo = false; }
            }
            presente = vivo && (cuerpoPresente || toques.Count > 0);
            x = cuerpoX;
        }

        public bool TomarGesto(out string gesto)
        {
            if (gestos.Count > 0) { gesto = gestos.Dequeue(); return true; }
            gesto = null;
            return false;
        }

        public bool Vivo(double ahora) => ahora - ultimo < silencioMaximo;

        /// <summary>Un visitante inventado (--simular): camina de lado a lado, toca la pared cada 5 s y
        /// levanta los brazos cada 40 s. Igual que simular() del puente de Node.</summary>
        public void Simular(double t, bool conGestos, ref double proximoGesto)
        {
            double ciclo = t % 60;
            bool presente = ciclo < 45;
            Recibir("/body/present", new object[] { presente ? 1 : 0 }, t);
            Recibir("/body/x", new object[] { (float)(0.5 + 0.4 * Math.Sin(t * 0.25)) }, t);
            bool tocando = presente && (t % 5) < 0.4;
            Recibir("/wall/touch/0/active", new object[] { tocando ? 1 : 0 }, t);
            Recibir("/wall/touch/0/x", new object[] { (float)(0.3 + 0.4 * Math.Abs(Math.Sin(t * 0.13))) }, t);
            Recibir("/wall/touch/0/y", new object[] { 0.72f }, t);
            if (conGestos && t >= proximoGesto)
            {
                if (proximoGesto > 0) gestos.Enqueue("brazos_arriba");
                proximoGesto = t + 40;
            }
        }
    }
}
