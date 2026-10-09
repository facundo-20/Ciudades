// Los datos del mundo tal como los deja exportar_mundo.py (Datos/mundo.json). Los nombres de los
// campos son los del JSON: JsonUtility los llena sin traducir nada. Una sola versión del guion,
// las cámaras y las fichas para Blender, la web y Unity.

using System;

namespace FNS
{
    [Serializable]
    public class Mundo
    {
        public float nivel_agua;
        public float[] volcan;
        public Terreno[] terrenos;
        public Capitulo[] capitulos;
        public LugarFauna[] fauna;
        public Especie[] especies;
        public Ficha[] fichas;

        public Ficha FichaDe(string clave)
        {
            if (fichas != null) foreach (var f in fichas) if (f.clave == clave) return f;
            return null;
        }

        public Especie EspecieDe(string clave)
        {
            if (especies != null) foreach (var e in especies) if (e.clave == clave) return e;
            return null;
        }
    }

    [Serializable]
    public class Terreno
    {
        public string nombre, era, cual, alturas;
        public float x0, z0, lado, hmin, hmax;
        public int res, capas_res;
        public string[] capas, capas_png;
    }

    [Serializable]
    public class Capitulo
    {
        public string clave, titulo, subtitulo, era;
        public float duracion;
        public string[] fichas;
        public float[] desde, hasta, mira, hacia_sol;
        public float sol_elevacion, sol_azimut, bruma_recorrido_m, ceniza, volcan, exposicion, foco_m, diafragma;

        public bool EsHoy => era == "hoy";
    }

    [Serializable]
    public class LugarFauna
    {
        public string especie;
        public float[] pos;
        public float giro;
    }

    [Serializable]
    public class Especie
    {
        public string clave;
        public float largo, velocidad;
        public string[] zonas;
    }

    [Serializable]
    public class Ficha
    {
        public string clave, titulo, dato, texto;
    }

    [Serializable]
    public class FloraEra
    {
        public FloraEspecie[] especies;
    }

    [Serializable]
    public class FloraEspecie
    {
        public string nombre;
        public float[] datos;     // x, y, z, giro (°), escala, inclinación (rad) por planta
        public const int Paso = 6;
        public int Cantidad => datos == null ? 0 : datos.Length / Paso;
    }

    public static class Alturas
    {
        /// <summary>Deshace el predictor plano de exportar_mundo.py (codificar_predictor): cada
        /// muestra es residuo + izquierda + arriba - diagonal, en aritmética de 16 bits. Devuelve
        /// alturas normalizadas 0..1 en [z, x], lo que pide TerrainData.SetHeights.</summary>
        public static float[,] Decodificar(byte[] crudo, int res)
        {
            if (crudo.Length < res * res * 2) throw new ArgumentException($"alturas: faltan datos ({crudo.Length} bytes para {res}²)");
            var a = new ushort[res * res];
            var h = new float[res, res];
            for (int j = 0; j < res; j++)
            {
                for (int i = 0; i < res; i++)
                {
                    int k = j * res + i;
                    ushort r = (ushort)(crudo[2 * k] | (crudo[2 * k + 1] << 8));
                    int izq = i > 0 ? a[k - 1] : 0;
                    int arr = j > 0 ? a[k - res] : 0;
                    int diag = i > 0 && j > 0 ? a[k - res - 1] : 0;
                    ushort v = unchecked((ushort)(r + izq + arr - diag));
                    a[k] = v;
                    h[j, i] = v / 65535f;
                }
            }
            return h;
        }
    }
}
