// La flora del Triásico dibujada por instancias en la GPU: 38.000 plantas (helechos, colas de
// caballo, Dicroidium, coníferas, troncos y rocas) sin un GameObject por planta. Las posiciones
// salen de flora_<era>.json (las mismas reglas de hábitat que el render de Blender).
//
// Por trozos de 32 m: cada trozo elige su nivel de detalle por distancia a la sala (el modelo
// completo de cerca, el del 30 % a media distancia, el del 8 % en el horizonte) y los que quedan
// lejos no se dibujan. Las plantas cercanas se mecen con el viento (todo el modelo, un par de
// grados: los de Meshy no traen huesos para mover cada fronda).

using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace FNS
{
    [Serializable]
    public class EspecieFlora
    {
        public string nombre;
        public Mesh[] lods;                    // 0 = completo
        public Material material;
        public float[] hasta = { 40f, 140f, 700f };   // metros hasta donde se usa cada nivel
        public float meceo = 1f;               // grados de vaivén con viento 1
        public bool sombra = true;
    }

    public class Vegetacion : MonoBehaviour
    {
        public TextAsset datos;
        public EspecieFlora[] especies;
        public Transform centro;               // la sala
        public float factorDistancia = 1f;     // Calidad lo baja en máquinas chicas
        public float viento = 1f;
        public Vector3 direccionViento = new Vector3(1f, 0f, 0.3f);

        const float Trozo = 32f;
        const int Lote = 1023;

        class Grupo
        {
            public EspecieFlora esp;
            public Matrix4x4[] baseM;          // posición, giro, escala e inclinación de cada planta
            public float[] fase;
            public readonly Dictionary<Vector2Int, List<int>> trozos = new Dictionary<Vector2Int, List<int>>();
            public Matrix4x4[][] buffer;
            public int[] cuenta;
        }

        readonly List<Grupo> grupos = new List<Grupo>();
        public int Dibujadas { get; private set; }

        void Start()
        {
            if (!datos) return;
            var era = JsonUtility.FromJson<FloraEra>(datos.text);
            foreach (var e in era.especies)
            {
                var esp = Array.Find(especies, x => x.nombre == e.nombre);
                if (esp == null || esp.lods == null || esp.lods.Length == 0 || !esp.material) continue;
                esp.material.enableInstancing = true;
                int n = e.Cantidad;
                var g = new Grupo { esp = esp, baseM = new Matrix4x4[n], fase = new float[n] };
                for (int i = 0; i < n; i++)
                {
                    int k = i * FloraEspecie.Paso;
                    var pos = new Vector3(e.datos[k], e.datos[k + 1], e.datos[k + 2]);
                    float giro = e.datos[k + 3], esc = e.datos[k + 4], inc = e.datos[k + 5] * Mathf.Rad2Deg;
                    var rot = Quaternion.Euler(inc, giro, inc * 0.5f);
                    g.baseM[i] = Matrix4x4.TRS(pos, rot, Vector3.one * esc);
                    g.fase[i] = (pos.x * 0.37f + pos.z * 0.71f) % 6.283f;
                    var t = new Vector2Int(Mathf.FloorToInt(pos.x / Trozo), Mathf.FloorToInt(pos.z / Trozo));
                    if (!g.trozos.TryGetValue(t, out var lista)) g.trozos[t] = lista = new List<int>();
                    lista.Add(i);
                }
                g.buffer = new Matrix4x4[esp.lods.Length][];
                g.cuenta = new int[esp.lods.Length];
                for (int l = 0; l < esp.lods.Length; l++) g.buffer[l] = new Matrix4x4[Lote];
                grupos.Add(g);
            }
        }

        void Update()
        {
            if (!centro) return;
            Vector3 ojo = centro.position;
            float t = Time.time;
            Vector3 eje = Vector3.Cross(Vector3.up, direccionViento.normalized);
            var limites = new Bounds(ojo, Vector3.one * 4000f);
            Dibujadas = 0;
            foreach (var g in grupos)
            {
                var esp = g.esp;
                var rp = new RenderParams(esp.material)
                {
                    shadowCastingMode = esp.sombra ? ShadowCastingMode.On : ShadowCastingMode.Off,
                    receiveShadows = true,
                    layer = gameObject.layer,
                    worldBounds = limites,
                    lightProbeUsage = LightProbeUsage.BlendProbes,
                };
                for (int l = 0; l < g.cuenta.Length; l++) g.cuenta[l] = 0;
                float lejos = esp.hasta[esp.hasta.Length - 1] * factorDistancia;
                foreach (var kv in g.trozos)
                {
                    var c = new Vector3((kv.Key.x + 0.5f) * Trozo, ojo.y, (kv.Key.y + 0.5f) * Trozo);
                    float d = Vector2.Distance(new Vector2(c.x, c.z), new Vector2(ojo.x, ojo.z)) - Trozo * 0.7f;
                    if (d > lejos) continue;
                    int lod = esp.lods.Length - 1;
                    for (int l = 0; l < esp.lods.Length && l < esp.hasta.Length; l++)
                        if (d < esp.hasta[l] * factorDistancia) { lod = l; break; }
                    bool mecer = d < 90f && esp.meceo > 0f;
                    foreach (int i in kv.Value)
                    {
                        Matrix4x4 m = g.baseM[i];
                        if (mecer)
                        {
                            float ang = esp.meceo * viento * (Mathf.Sin(t * 1.3f + g.fase[i]) * 0.8f + Mathf.Sin(t * 2.9f + 2f * g.fase[i]) * 0.35f);
                            // girar sobre el pie de la planta: trasladar al origen, girar, volver
                            Vector3 pie = m.GetColumn(3);
                            m = Matrix4x4.Translate(pie) * Matrix4x4.Rotate(Quaternion.AngleAxis(ang, eje)) * Matrix4x4.Translate(-pie) * m;
                        }
                        g.buffer[lod][g.cuenta[lod]++] = m;
                        if (g.cuenta[lod] == Lote)
                        {
                            Graphics.RenderMeshInstanced(rp, esp.lods[lod], 0, g.buffer[lod], Lote);
                            Dibujadas += Lote;
                            g.cuenta[lod] = 0;
                        }
                    }
                }
                for (int l = 0; l < g.cuenta.Length; l++)
                {
                    if (g.cuenta[l] == 0) continue;
                    Graphics.RenderMeshInstanced(rp, esp.lods[l], 0, g.buffer[l], g.cuenta[l]);
                    Dibujadas += g.cuenta[l];
                }
            }
        }
    }
}
