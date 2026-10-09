// Calidad según la máquina. HDRP escala casi todo: la OMEN con RTX va al máximo (iluminación global
// y reflejos por trazado de rayos si la placa lo soporta), la M4 en "media" (todo en pantalla:
// SSGI, reflejos de pantalla, nubes con menos pasos).
//
//   maxima  trazado de rayos (RTGI + reflejos + sombras de contacto), nubes y niebla finas, DLSS si hay NVIDIA
//   alta    SSGI + SSR + niebla volumétrica media (la que va por defecto)
//   media   sin SSGI, nubes y niebla livianas, vegetación más corta (Mac M4, notebooks)

using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace FNS
{
    public class Calidad : MonoBehaviour
    {
        public Volume volumen;
        public Vegetacion[] vegetacion;
        public string Nivel { get; private set; } = "alta";
        public string Placa { get; private set; }

        public void Aplicar(string nivel, Sala sala)
        {
            Placa = SystemInfo.graphicsDeviceName;
            bool rtx = SystemInfo.supportsRayTracing;
            if (nivel == "maxima" && !rtx) nivel = "alta";          // sin trazado de rayos, alta es lo máximo
            Nivel = nivel;
            var p = volumen.profile;
            p.TryGet(out GlobalIllumination gi);
            p.TryGet(out ScreenSpaceReflection ssr);
            p.TryGet(out Fog fog);
            p.TryGet(out VolumetricClouds nubes);
            p.TryGet(out ContactShadows contacto);
            p.TryGet(out ScreenSpaceAmbientOcclusion ao);

            bool max = nivel == "maxima", media = nivel == "media";
            if (gi)
            {
                gi.enable.Override(!media);
                gi.tracing.Override(max ? RayCastingMode.RayTracing : RayCastingMode.RayMarching);
            }
            if (ssr) ssr.tracing.Override(max ? RayCastingMode.RayTracing : RayCastingMode.RayMarching);
            if (ao) ao.rayTracing.Override(max);
            if (fog)
            {
                fog.volumeSliceCount.Override(media ? 48 : max ? 128 : 80);
                fog.depthExtent.Override(media ? 80f : max ? 220f : 140f);
            }
            if (nubes)
            {
                nubes.numPrimarySteps.Override(media ? 32 : max ? 128 : 64);
                nubes.cloudSimpleMode.Override(media ? VolumetricClouds.CloudSimpleMode.Performance : VolumetricClouds.CloudSimpleMode.Quality);
                nubes.shadows.Override(!media);
            }
            if (contacto) contacto.enable.Override(!media);
            foreach (var v in vegetacion) if (v) v.factorDistancia = media ? 0.6f : max ? 1.3f : 1f;

            foreach (var cam in sala.Camaras)
            {
                if (!cam.TryGetComponent<HDAdditionalCameraData>(out var hd)) continue;
                hd.antialiasing = HDAdditionalCameraData.AntialiasingMode.TemporalAntialiasing;
                hd.TAAQuality = media ? HDAdditionalCameraData.TAAQualityLevel.Medium : HDAdditionalCameraData.TAAQualityLevel.High;
                // DLSS: sólo con NVIDIA y si el asset de HDRP lo tiene habilitado (lo deja el constructor)
                hd.allowDynamicResolution = max && Placa.Contains("NVIDIA");
                hd.allowDeepLearningSuperSampling = max && Placa.Contains("NVIDIA");
            }
            Debug.Log($"[FNS] calidad {Nivel} · {Placa} · trazado de rayos: {(rtx ? "sí" : "no")}");
        }
    }
}
