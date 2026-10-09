// Todo lo que entra, en un solo lugar: sensores por OSC (tracker de la pared, Kinect/LiDAR del
// cuerpo, gestos de TD), el mouse y el teclado para probar sin sensores, y un visitante simulado
// (--simular) para dejar la sala andando sola. El resto de la experiencia sólo lee esto.
//
// Teclas: ← → capítulo · 0–5 ir a uno · P simular una persona · H ocultar textos · F11 pantalla completa

using System.Collections.Generic;
using UnityEngine;

namespace FNS
{
    public class Sensores : MonoBehaviour
    {
        public int[] puertosOsc = { 7001, 10000 };
        public bool simular;
        public bool simularGestos = true;

        public readonly List<Toque> Toques = new List<Toque>();
        public bool CuerpoPresente { get; private set; }
        public float CuerpoX { get; private set; } = 0.5f;
        public bool CuerpoCorre { get; private set; }
        public float SinUso { get; private set; } = 999f;       // segundos desde la última interacción
        public bool OscVivo { get; private set; }
        public string Estado { get; private set; } = "";

        readonly EstadoSensores estado = new EstadoSensores();
        readonly Queue<string> gestos = new Queue<string>();
        OscReceptor receptor;
        double proximoGesto;
        bool personaTeclado;
        float xAnterior = 0.5f;
        int idMouse;

        void OnEnable()
        {
            receptor = new OscReceptor(puertosOsc);
            Estado = receptor.errores.Count > 0 ? string.Join(" · ", receptor.errores) : "OSC en " + string.Join(", ", puertosOsc);
            Debug.Log("[FNS] " + Estado);
        }

        void OnDisable()
        {
            receptor?.Dispose();
            receptor = null;
        }

        public bool TomarGesto(out string g)
        {
            if (gestos.Count > 0) { g = gestos.Dequeue(); return true; }
            g = null;
            return false;
        }

        void Update()
        {
            double ahora = Time.realtimeSinceStartupAsDouble;
            if (receptor != null)
                while (receptor.TomarMensaje(out var m)) estado.Recibir(m.direccion, m.valores, ahora);
            if (simular) estado.Simular(ahora, simularGestos, ref proximoGesto);
            OscVivo = estado.Vivo(ahora);

            estado.Leer(ahora, Toques, out bool presente, out float x);
            while (estado.TomarGesto(out var g)) { gestos.Enqueue(g == "brazos_arriba" ? "siguiente" : g); SinUso = 0; }
            LeerMouseYTeclado(ref presente, ref x);

            float dt = Mathf.Max(1e-3f, Time.unscaledDeltaTime);
            CuerpoCorre = Mathf.Abs(x - xAnterior) / dt > 0.35f;
            xAnterior = x;
            CuerpoPresente = presente;
            CuerpoX = x;
            if (presente || Toques.Count > 0) SinUso = 0; else SinUso += Time.unscaledDeltaTime;
        }

        void LeerMouseYTeclado(ref bool presente, ref float x)
        {
#if ENABLE_LEGACY_INPUT_MANAGER
            if (Input.GetKeyDown(KeyCode.RightArrow) || Input.GetKeyDown(KeyCode.Space)) gestos.Enqueue("siguiente");
            if (Input.GetKeyDown(KeyCode.LeftArrow)) gestos.Enqueue("anterior");
            for (int i = 0; i <= 5; i++)
                if (Input.GetKeyDown(KeyCode.Alpha0 + i)) gestos.Enqueue("capitulo_" + i);
            if (Input.GetKeyDown(KeyCode.P)) personaTeclado = !personaTeclado;
            if (Input.GetKeyDown(KeyCode.H)) gestos.Enqueue("textos");
            if (Input.GetKeyDown(KeyCode.F11)) Screen.fullScreen = !Screen.fullScreen;
            if (Input.GetMouseButtonDown(0)) idMouse++;
            if (Input.GetMouseButton(0))
            {
                float u = Input.mousePosition.x / Mathf.Max(1, Screen.width);
                float v = 1f - Input.mousePosition.y / Mathf.Max(1, Screen.height);
                Toques.Add(new Toque { id = "m" + idMouse, u = u, v = v, nuevo = Input.GetMouseButtonDown(0) });
                if (!presente) { presente = true; x = u; }
            }
            if (Input.anyKeyDown) SinUso = 0;
#endif
            if (personaTeclado && !presente) { presente = true; x = 0.5f + 0.35f * Mathf.Sin(Time.time * 0.3f); }
        }
    }
}
