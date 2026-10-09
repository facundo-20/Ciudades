// --capturas CARPETA: recorre los seis capítulos, espera que la imagen se asiente (exposición
// automática, nubes y niebla temporales, TAA) y guarda un PNG de cada uno al 30 % del recorrido.
// Al final escribe informe.json (placa, calidad, cuadros por segundo de cada capítulo) y cierra.
// Lo usa CONSTRUIR_Y_PROBAR.bat para mandar las capturas a la nube y revisarlas desde ahí.

using System.Collections;
using System.IO;
using System.Text;
using UnityEngine;

namespace FNS
{
    public class Capturas : MonoBehaviour
    {
        public Director director;
        public Calidad calidad;
        public float asentar = 7f;

        IEnumerator Start()
        {
            string carpeta = Arranque.Texto("--capturas");
            if (string.IsNullOrEmpty(carpeta)) yield break;
            Directory.CreateDirectory(carpeta);
            director.automatico = false;
            var informe = new StringBuilder("{\n");
            informe.Append($"  \"placa\": \"{SystemInfo.graphicsDeviceName}\",\n  \"calidad\": \"{calidad.Nivel}\",\n");
            informe.Append($"  \"resolucion\": \"{Screen.width}x{Screen.height}\",\n  \"capitulos\": [\n");
            int n = director.Mundo.capitulos.Length;
            for (int i = 0; i < n; i++)
            {
                director.Ir(i);
                yield return new WaitForSeconds(director.fundido * 4f + 0.5f);
                float t0 = Time.realtimeSinceStartup;
                int c0 = Time.frameCount;
                yield return new WaitForSeconds(asentar);
                float fps = (Time.frameCount - c0) / Mathf.Max(0.01f, Time.realtimeSinceStartup - t0);
                string nombre = $"{i}_{director.Actual.clave}.png";
                ScreenCapture.CaptureScreenshot(Path.Combine(carpeta, nombre));
                yield return null;
                yield return null;
                informe.Append($"    {{\"capitulo\": \"{director.Actual.clave}\", \"fps\": {fps:0.0}, \"archivo\": \"{nombre}\"}}{(i < n - 1 ? "," : "")}\n");
            }
            informe.Append("  ]\n}\n");
            File.WriteAllText(Path.Combine(carpeta, "informe.json"), informe.ToString());
            yield return new WaitForSeconds(1f);
            Application.Quit();
        }
    }
}
