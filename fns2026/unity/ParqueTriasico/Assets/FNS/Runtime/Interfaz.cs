// Los textos sobre la imagen: título y subtítulo de cada capítulo, y las fichas de divulgación
// (las mismas de la web; a validar con un paleontólogo de la UNSJ o del MuPa). En la sala van en
// la pared del fondo; en la pared LED, abajo a la izquierda. --sin-textos los apaga para mandar
// la imagen limpia a TouchDesigner o Arena (que ponen sus propios gráficos).

using UnityEngine;

namespace FNS
{
    public class Interfaz : MonoBehaviour
    {
        public bool mostrarTextos = true;
        public ConfigSala config;
        public Font fuente;

        Capitulo cap;
        Ficha ficha;
        float tCapitulo = 999f, tFicha = 999f, duracionFicha;
        int fichaAuto;
        Mundo mundo;
        GUIStyle titulo, sub, fichaT, fichaD, fichaX;
        Texture2D fondo;

        public void MostrarCapitulo(Capitulo c, Mundo m)
        {
            cap = c;
            mundo = m;
            tCapitulo = 0;
            ficha = null;
            fichaAuto = 0;
        }

        public void MostrarFicha(Ficha f, float segundos)
        {
            if (f == null) return;
            ficha = f;
            tFicha = 0;
            duracionFicha = segundos;
        }

        void Update()
        {
            tCapitulo += Time.deltaTime;
            tFicha += Time.deltaTime;
            // fichas automáticas: a los 7 s del capítulo y después cada 14 s
            if (cap != null && cap.fichas != null && cap.fichas.Length > 0 && tCapitulo > 7f && tFicha > 14f)
            {
                MostrarFicha(mundo.FichaDe(cap.fichas[fichaAuto % cap.fichas.Length]), 11f);
                fichaAuto++;
            }
        }

        Rect Zona()
        {
            // la pared del fondo si es una sala; toda la pantalla si es una pared sola
            if (config != null && config.superficies != null && config.superficies.Length > 1)
            {
                foreach (var s in config.superficies)
                {
                    if (s.nombre != "fondo") continue;
                    float ex = Screen.width / (float)config.lienzo_ancho, ey = Screen.height / (float)config.lienzo_alto;
                    return new Rect(s.lienzo_x * ex, s.lienzo_y * ey, s.ancho_px * ex, s.alto_px * ey);
                }
            }
            return new Rect(0, 0, Screen.width, Screen.height);
        }

        void Estilos(float alto)
        {
            float k = alto / 1080f;
            GUIStyle Nuevo(int tam, FontStyle est, Color col, TextAnchor ancla) => new GUIStyle
            {
                font = fuente, fontSize = Mathf.RoundToInt(tam * k), fontStyle = est, alignment = ancla, wordWrap = true,
                normal = { textColor = col }, richText = false,
            };
            titulo = Nuevo(76, FontStyle.Bold, new Color(1f, 0.97f, 0.9f), TextAnchor.UpperLeft);
            sub = Nuevo(30, FontStyle.Normal, new Color(1f, 0.95f, 0.85f), TextAnchor.UpperLeft);
            fichaT = Nuevo(34, FontStyle.Bold, new Color(1f, 0.85f, 0.55f), TextAnchor.UpperLeft);
            fichaD = Nuevo(24, FontStyle.Italic, new Color(1f, 0.95f, 0.85f), TextAnchor.UpperLeft);
            fichaX = Nuevo(24, FontStyle.Normal, Color.white, TextAnchor.UpperLeft);
            if (!fondo)
            {
                fondo = new Texture2D(1, 1);
                fondo.SetPixel(0, 0, new Color(0.08f, 0.05f, 0.03f, 0.62f));
                fondo.Apply();
            }
        }

        static void ConSombra(Rect r, string texto, GUIStyle e, float alfa)
        {
            var c = e.normal.textColor;
            e.normal.textColor = new Color(0, 0, 0, 0.6f * alfa);
            GUI.Label(new Rect(r.x + 2, r.y + 2, r.width, r.height), texto, e);
            e.normal.textColor = new Color(c.r, c.g, c.b, alfa);
            GUI.Label(r, texto, e);
            e.normal.textColor = c;
        }

        void OnGUI()
        {
            if (!mostrarTextos || cap == null) return;
            GUI.depth = -10;                      // encima del lienzo de la sala
            Rect z = Zona();
            Estilos(z.height);
            float m = z.height * 0.05f;
            // título: entra en 1,5 s, queda 6 s y se va
            float a = Mathf.Clamp01(tCapitulo / 1.5f) * Mathf.Clamp01((9f - tCapitulo) / 1.5f);
            if (a > 0.01f)
            {
                ConSombra(new Rect(z.x + m * 1.5f, z.y + m, z.width * 0.6f, z.height * 0.15f), cap.titulo, titulo, a);
                ConSombra(new Rect(z.x + m * 1.5f, z.y + m + z.height * 0.11f, z.width * 0.45f, z.height * 0.2f), cap.subtitulo, sub, a);
            }
            if (ficha != null)
            {
                float b = Mathf.Clamp01(tFicha / 0.8f) * Mathf.Clamp01((duracionFicha - tFicha) / 0.8f);
                if (b > 0.01f)
                {
                    float w = Mathf.Min(z.width * 0.3f, z.height * 0.9f), h = z.height * 0.34f;
                    var caja = new Rect(z.x + m * 1.5f, z.yMax - h - m, w, h);
                    var previo = GUI.color;
                    GUI.color = new Color(1, 1, 1, b);
                    GUI.DrawTexture(caja, fondo);
                    GUI.color = previo;
                    float p = h * 0.08f;
                    ConSombra(new Rect(caja.x + p, caja.y + p, w - 2 * p, h * 0.2f), ficha.titulo, fichaT, b);
                    ConSombra(new Rect(caja.x + p, caja.y + p + h * 0.2f, w - 2 * p, h * 0.15f), ficha.dato, fichaD, b);
                    ConSombra(new Rect(caja.x + p, caja.y + p + h * 0.36f, w - 2 * p, h * 0.6f), ficha.texto, fichaX, b);
                }
            }
        }
    }
}
