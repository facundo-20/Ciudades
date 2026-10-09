// La sala inmersiva: piso y paredes LED como UNA ventana continua al Triásico, vista desde los ojos
// del visitante (como la referencia del space&time cube). Cada superficie física tiene su cámara con
// proyección "fuera de eje" (Kooima, "Generalized Perspective Projection"): el frustum va del ojo a
// las cuatro esquinas reales de esa pantalla. Así lo que cruza del piso a la pared sigue derecho,
// sin quiebre, y el dinosaurio que pasa al lado parece estar en la sala.
//
// Medidas, píxeles y lugar de cada superficie en el lienzo: StreamingAssets/sala.json (se edita
// sin recompilar). Mismo atlas que la app del piso LED: el piso al centro y las paredes abatidas
// hacia afuera, cada una con el borde que toca el piso pegado a él.
//
// El ojo: si hay sensor de cuerpo (/body/x del Kinect o del LiDAR), sigue al visitante de lado a lado;
// si no, se queda en el punto dulce de la sala. Con varios visitantes se usa el promedio: la
// imagen es para todos, el ojo sólo corrige la paralaje del que está más cerca del centro.

using System;
using System.Collections.Generic;
using System.IO;
using UnityEngine;

namespace FNS
{
    [Serializable]
    public class SuperficieSala
    {
        public string nombre;
        // esquinas en metros, en la sala: x a lo ancho (izquierda → derecha vista desde el público),
        // y hacia arriba, z hacia el fondo. abajo_izq / abajo_der / arriba_izq son los píxeles
        // (0, alto), (ancho, alto) y (0, 0) de ESA superficie tal como la ve el visitante
        public float[] abajo_izq, abajo_der, arriba_izq;
        public int ancho_px, alto_px;
        // dónde va en el lienzo y girada cuántos grados (0, 90, 180, 270, sentido horario)
        public int lienzo_x, lienzo_y, giro;
    }

    [Serializable]
    public class ConfigSala
    {
        public string modo = "pared";                 // "pared" (LED 16:3) o "cubo" (piso + paredes)
        public int lienzo_ancho = 5760, lienzo_alto = 1080;
        public float[] ojo = { 0f, 1.6f, -4f };        // punto dulce, en metros de sala
        public float ojo_rango_x = 2.5f;               // cuánto se mueve el ojo con /body/x (± m)
        public float escala_mundo = 1f;                // >1 achica la sala frente al mundo (todo más grande)
        public SuperficieSala[] superficies;
    }

    public class Sala : MonoBehaviour
    {
        public ConfigSala config;
        public Sensores sensores;
        public float cerca = 0.05f, lejos = 12000f;
        [Tooltip("Plantilla con el HDAdditionalCameraData ya configurado (la arma el constructor)")]
        public Camera plantilla;

        readonly List<Camera> camaras = new List<Camera>();
        readonly List<RenderTexture> texturas = new List<RenderTexture>();
        bool directo;                                  // una sola superficie: se dibuja directo en pantalla
        Vector3 ojoSuave;

        public IReadOnlyList<Camera> Camaras => camaras;
        public Camera Principal => camaras.Count > 0 ? camaras[0] : null;

        public static ConfigSala Leer(string nombreArchivo)
        {
            string ruta = Path.Combine(Application.streamingAssetsPath, nombreArchivo);
            if (!File.Exists(ruta)) return null;
            return JsonUtility.FromJson<ConfigSala>(File.ReadAllText(ruta));
        }

        public void Armar(ConfigSala c)
        {
            config = c;
            foreach (var cam in camaras) if (cam && cam != plantilla) Destroy(cam.gameObject);
            foreach (var rt in texturas) if (rt) rt.Release();
            camaras.Clear();
            texturas.Clear();
            var sup = c.superficies ?? Array.Empty<SuperficieSala>();
            directo = sup.Length == 1 && sup[0].giro == 0;
            for (int i = 0; i < sup.Length; i++)
            {
                Camera cam = i == 0 && plantilla ? plantilla : Instantiate(plantilla, transform);
                cam.name = "camara_" + sup[i].nombre;
                cam.transform.SetParent(transform, false);
                cam.nearClipPlane = cerca;
                cam.farClipPlane = lejos;
                cam.enabled = true;
                // sólo la primera lleva el AudioListener (si lo hubiera) y la etiqueta de principal
                cam.tag = i == 0 ? "MainCamera" : "Untagged";
                if (directo)
                {
                    cam.targetTexture = null;
                    cam.rect = new Rect(0, 0, 1, 1);
                }
                else
                {
                    var rt = new RenderTexture(sup[i].ancho_px, sup[i].alto_px, 24, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB)
                    { name = "sala_" + sup[i].nombre, antiAliasing = 1 };
                    rt.Create();
                    cam.targetTexture = rt;
                    texturas.Add(rt);
                }
                camaras.Add(cam);
            }
            ojoSuave = V(c.ojo);
        }

        static Vector3 V(float[] a) => a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero;

        void LateUpdate()
        {
            if (config == null || camaras.Count == 0) return;
            // el ojo del visitante, en metros de sala
            Vector3 ojo = V(config.ojo);
            if (sensores != null && sensores.CuerpoPresente)
                ojo.x += (sensores.CuerpoX - 0.5f) * 2f * config.ojo_rango_x;
            ojoSuave = Vector3.Lerp(ojoSuave, ojo, 1f - Mathf.Exp(-Time.deltaTime * 4f));
            float k = Mathf.Max(0.01f, config.escala_mundo);
            Vector3 pe = transform.TransformPoint(ojoSuave * k);
            for (int i = 0; i < camaras.Count; i++)
            {
                var s = config.superficies[i];
                Vector3 pa = transform.TransformPoint(V(s.abajo_izq) * k);
                Vector3 pb = transform.TransformPoint(V(s.abajo_der) * k);
                Vector3 pc = transform.TransformPoint(V(s.arriba_izq) * k);
                Proyeccion.FueraDeEje(pa, pb, pc, pe, cerca, lejos, out var rot, out var proy);
                var cam = camaras[i];
                cam.transform.SetPositionAndRotation(pe, rot);
                cam.projectionMatrix = proy;
            }
        }

        // el lienzo: cada superficie en su lugar del atlas (sólo si hay más de una)
        void OnGUI()
        {
            if (directo || config == null || Event.current.type != EventType.Repaint) return;
            float ex = Screen.width / (float)config.lienzo_ancho, ey = Screen.height / (float)config.lienzo_alto;
            for (int i = 0; i < texturas.Count; i++)
            {
                var s = config.superficies[i];
                bool acostada = s.giro == 90 || s.giro == 270;
                float w = (acostada ? s.alto_px : s.ancho_px) * ex, h = (acostada ? s.ancho_px : s.alto_px) * ey;
                var destino = new Rect(s.lienzo_x * ex, s.lienzo_y * ey, w, h);
                var previa = GUI.matrix;
                if (s.giro != 0)
                {
                    // se dibuja sin girar, centrado en el mismo punto, y se gira alrededor del centro
                    Vector2 centro = destino.center;
                    float ancho = s.ancho_px * ex, alto = s.alto_px * ey;
                    destino = new Rect(centro.x - ancho / 2, centro.y - alto / 2, ancho, alto);
                    GUIUtility.RotateAroundPivot(s.giro, centro);
                }
                GUI.DrawTexture(destino, texturas[i], ScaleMode.StretchToFill, false);
                GUI.matrix = previa;
            }
        }

        void OnDestroy()
        {
            foreach (var rt in texturas) if (rt) rt.Release();
        }
    }

    public static class Proyeccion
    {
        /// <summary>Proyección generalizada (Kooima 2008): cámara en el ojo pe, mirando perpendicular
        /// a la pantalla de esquinas pa (abajo-izq), pb (abajo-der), pc (arriba-izq), con el frustum
        /// asimétrico que pasa justo por esas esquinas.</summary>
        public static void FueraDeEje(Vector3 pa, Vector3 pb, Vector3 pc, Vector3 pe, float n, float f,
                                      out Quaternion rot, out Matrix4x4 proy)
        {
            Vector3 vr = (pb - pa).normalized;
            Vector3 vu = (pc - pa).normalized;
            Vector3 adelante = Vector3.Cross(vr, vu).normalized;      // hacia adentro de la pantalla
            Vector3 va = pa - pe, vb = pb - pe, vc = pc - pe;
            float d = Vector3.Dot(adelante, va);                      // distancia del ojo al plano
            if (d < 1e-3f)
            {
                // el ojo pasó al otro lado de la pantalla (o la toca): se aleja un poco para no dividir por 0
                pe -= adelante * (1e-3f - d);
                va = pa - pe; vb = pb - pe; vc = pc - pe;
                d = 1e-3f;
            }
            float l = Vector3.Dot(vr, va) * n / d;
            float r = Vector3.Dot(vr, vb) * n / d;
            float b = Vector3.Dot(vu, va) * n / d;
            float t = Vector3.Dot(vu, vc) * n / d;
            rot = Quaternion.LookRotation(adelante, vu);
            proy = Matrix4x4.Frustum(l, r, b, t, n, f);
        }
    }
}
