// La luz y el aire de cada capítulo, con HDRP: sol físico, cielo físico (dispersión de Rayleigh y
// Mie), nubes volumétricas, niebla volumétrica (los rayos de sol entre las copas), agua con
// corriente, la columna del volcán y la ceniza que cae. Todo se mezcla de un capítulo al otro
// en ~3 s, igual que en la web.
//
// Color "vívido" como la referencia del cubo inmersivo: más saturación y contraste que la versión
// de cine, pero con la luz física (el sol a 120.000 lux, la exposición automática como un ojo).

using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace FNS
{
    public class Ambiente : MonoBehaviour
    {
        public Light sol;
        public Volume volumen;
        public GameObject eraTriasico, eraHoy;
        public WaterSurface rio;
        public ParticleSystem columnaVolcan, cenizaCae, polvoPisada;
        public Light brilloVolcan;
        public DecalProjector cenizaSuelo;
        public Transform seguir;                        // la sala: la ceniza y el calco la acompañan
        [Range(0, 1)] public float vivido = 1f;         // 0 = cine, 1 = como la referencia del cubo

        Fog fog;
        Exposure exposicion;
        VolumetricClouds nubes;
        PhysicallyBasedSky cielo;
        ColorAdjustments color;
        WhiteBalance balance;

        // valores que se persiguen suavemente
        Vector3 haciaSol = new Vector3(0.3f, 0.6f, 0.3f), haciaSolObj;
        float recorrido = 600, recorridoObj = 600;
        float ceniza, cenizaObj, volcan, volcanObj, compensacion, compensacionObj, fundido;
        Color albedoNiebla = Color.white, albedoObj = Color.white;
        bool fundidoClaro;

        void Awake()
        {
            var p = volumen.profile;              // copia de ejecución: no toca el asset
            p.TryGet(out fog);
            p.TryGet(out exposicion);
            p.TryGet(out nubes);
            p.TryGet(out cielo);
            p.TryGet(out color);
            p.TryGet(out balance);
        }

        public void PonerEra(bool hoy)
        {
            if (eraTriasico) eraTriasico.SetActive(!hoy);
            if (eraHoy) eraHoy.SetActive(hoy);
            if (rio) rio.gameObject.SetActive(!hoy);
        }

        public void Capitulo(Capitulo c, bool inmediato)
        {
            haciaSolObj = new Vector3(c.hacia_sol[0], c.hacia_sol[1], c.hacia_sol[2]).normalized;
            recorridoObj = Mathf.Clamp(c.bruma_recorrido_m, 70f, 6000f);
            cenizaObj = c.ceniza;
            volcanObj = c.volcan;
            // la exposición de Blender era para un render fijo; con exposición automática basta la mitad
            compensacionObj = c.exposicion * 0.5f;
            albedoObj = c.ceniza > 0.5f ? new Color(0.62f, 0.58f, 0.54f) : (c.EsHoy ? new Color(1f, 0.97f, 0.92f) : new Color(0.93f, 0.95f, 0.97f));
            if (nubes)
            {
                // el Triásico de Ischigualasto: clima monzónico, nubes de tormenta de temporada;
                // hoy: el cielo seco y limpio de San Juan
                nubes.cloudPreset = c.ceniza > 0.5f ? VolumetricClouds.CloudPresets.Stormy
                                  : c.EsHoy ? VolumetricClouds.CloudPresets.Sparse
                                  : c.clave == "titulo" ? VolumetricClouds.CloudPresets.Sparse
                                  : VolumetricClouds.CloudPresets.Cloudy;
                // el preset escribe los valores pero no los marca como propios del volumen: sin esto,
                // al mezclar volúmenes ganan los del perfil por defecto de HDRP
                foreach (var prm in new VolumeParameter[] { nubes.densityMultiplier, nubes.shapeFactor, nubes.shapeScale,
                         nubes.erosionFactor, nubes.erosionScale, nubes.densityCurve, nubes.erosionCurve, nubes.ambientOcclusionCurve })
                    prm.overrideState = true;
            }
            if (cielo)
            {
                // más aerosoles con humedad y ceniza; el aire del desierto de hoy es transparente
                cielo.aerosolDensity.Override(c.EsHoy ? 0.002f : 0.01f + 0.05f * c.ceniza);
                cielo.aerosolTint.Override(c.ceniza > 0.5f ? new Color(0.7f, 0.62f, 0.55f) : new Color(0.9f, 0.9f, 0.9f));
            }
            if (inmediato)
            {
                haciaSol = haciaSolObj; recorrido = recorridoObj; ceniza = cenizaObj; volcan = volcanObj;
                compensacion = compensacionObj; albedoNiebla = albedoObj;
            }
        }

        public void Fundido(float f, bool claro)
        {
            fundido = f;
            fundidoClaro = claro;
        }

        public void Pisada(Vector3 punto, Vector3 normal)
        {
            if (!polvoPisada) return;
            polvoPisada.transform.SetPositionAndRotation(punto + normal * 0.05f, Quaternion.LookRotation(normal));
            polvoPisada.Emit(60);
        }

        void Update()
        {
            float a = 1f - Mathf.Exp(-Time.deltaTime / 1.2f);
            haciaSol = Vector3.Slerp(haciaSol, haciaSolObj, a);
            recorrido = Mathf.Lerp(recorrido, recorridoObj, a);
            ceniza = Mathf.Lerp(ceniza, cenizaObj, a * 0.6f);
            volcan = Mathf.Lerp(volcan, volcanObj, a * 0.8f);
            compensacion = Mathf.Lerp(compensacion, compensacionObj, a);
            albedoNiebla = Color.Lerp(albedoNiebla, albedoObj, a);

            if (sol)
            {
                sol.transform.rotation = Quaternion.LookRotation(-haciaSol, Vector3.up);
                // con ceniza el sol se vela: menos luz directa, más difusa (la pone la niebla)
                sol.intensity = 120000f * (1f - 0.7f * ceniza);
            }
            if (fog)
            {
                fog.meanFreePath.Override(recorrido);
                fog.albedo.Override(albedoNiebla);
            }
            if (exposicion)
            {
                exposicion.compensation.Override(compensacion);
            }
            if (color)
            {
                // fundido: a negro entre capítulos; de la ceniza a hoy, a gris claro (la ceniza lo tapa todo)
                color.postExposure.Override(fundidoClaro ? fundido * 2.5f : -fundido * 9f);
                color.saturation.Override(Mathf.Lerp(4f, 16f, vivido) - 30f * ceniza - (fundidoClaro ? 60f * fundido : 0f));
                color.contrast.Override(Mathf.Lerp(6f, 14f, vivido));
            }
            if (balance) balance.temperature.Override(Mathf.Lerp(0f, -6f, vivido) + 8f * ceniza);

            if (columnaVolcan)
            {
                var em = columnaVolcan.emission;
                em.rateOverTimeMultiplier = 3f * volcan;
                if (volcan > 0.05f && !columnaVolcan.isPlaying) columnaVolcan.Play();
                if (volcan <= 0.05f && columnaVolcan.isPlaying) columnaVolcan.Stop();
            }
            if (brilloVolcan) brilloVolcan.intensity = 4e7f * volcan * (0.8f + 0.2f * Mathf.PerlinNoise(Time.time * 0.7f, 0));
            if (cenizaCae)
            {
                var em = cenizaCae.emission;
                em.rateOverTimeMultiplier = 4000f * ceniza;
                if (seguir) cenizaCae.transform.position = seguir.position + Vector3.up * 22f + seguir.forward * 10f;
            }
            if (cenizaSuelo)
            {
                cenizaSuelo.fadeFactor = Mathf.Clamp01(ceniza * 1.2f);
                if (seguir) cenizaSuelo.transform.position = new Vector3(seguir.position.x, seguir.position.y + 20f, seguir.position.z);
            }
        }
    }
}
