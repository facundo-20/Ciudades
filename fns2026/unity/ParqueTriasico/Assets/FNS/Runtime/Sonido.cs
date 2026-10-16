// El sonido de la sala. Todo sintetizado (pipeline/sonido/sonido_triasico.py): sin grabaciones de
// terceros. Ambiente por capítulo (loops sin costura que se funden entre sí), el volcán como fuente
// 3D en el cono, y en cada animal sus pisadas (al ritmo de su ciclo de paso) y su voz.
using System;
using UnityEngine;

namespace FNS
{
    [Serializable]
    public class SonidoEspecie
    {
        public string especie;
        public AudioClip[] voces = new AudioClip[0];
        public string peso = "medio";          // liviano / medio / pesado: qué pisadas usa
    }

    [Serializable]
    public class PisadasPeso
    {
        public string peso;
        public AudioClip[] barro = new AudioClip[0], seco = new AudioClip[0];
    }

    public class Sonido : MonoBehaviour
    {
        public AudioClip[] ambientes = new AudioClip[0];        // ambiente_<capitulo>
        public AudioClip volcan;
        public Transform volcanEn;
        public Ambiente ambiente;
        public SonidoEspecie[] especies = new SonidoEspecie[0];
        public PisadasPeso[] pisadas = new PisadasPeso[0];
        [Range(0, 1)] public float volumen = 0.9f;
        public float segundosMezcla = 3f;

        AudioSource a, b, fuenteVolcan;
        float mezcla = 1f, fundido;
        string clave = "";

        void Awake()
        {
            a = Fuente2D("ambiente_a");
            b = Fuente2D("ambiente_b");
            if (volcan && volcanEn)
            {
                fuenteVolcan = volcanEn.gameObject.AddComponent<AudioSource>();
                fuenteVolcan.clip = volcan;
                fuenteVolcan.loop = true;
                fuenteVolcan.spatialBlend = 1f;
                fuenteVolcan.rolloffMode = AudioRolloffMode.Logarithmic;
                fuenteVolcan.minDistance = 300f;            // un volcán: se oye desde lejos
                fuenteVolcan.maxDistance = 6000f;
                fuenteVolcan.dopplerLevel = 0f;
                fuenteVolcan.volume = 0f;
                fuenteVolcan.Play();
            }
            if (Arranque.Tiene("--sin-sonido")) AudioListener.volume = 0f;
        }

        AudioSource Fuente2D(string nombre)
        {
            var go = new GameObject(nombre);
            go.transform.SetParent(transform, false);
            var s = go.AddComponent<AudioSource>();
            s.loop = true;
            s.spatialBlend = 0f;
            s.playOnAwake = false;
            s.volume = 0f;
            return s;
        }

        public void CambioDeCapitulo(Capitulo c)
        {
            if (c.clave == clave) return;
            clave = c.clave;
            var clip = Array.Find(ambientes, x => x && x.name == "ambiente_" + c.clave);
            if (!clip) return;
            // el que sonaba pasa a "b" y se apaga; el nuevo entra por "a" desde un punto al azar
            (a, b) = (b, a);
            a.clip = clip;
            a.time = UnityEngine.Random.Range(0f, clip.length * 0.9f);
            a.Play();
            mezcla = 0f;
        }

        /// <summary>0 = imagen, 1 = negro: el ambiente baja (sin apagarse del todo) en el fundido.</summary>
        public void Fundido(float f) => fundido = Mathf.Clamp01(f);

        void Update()
        {
            mezcla = Mathf.MoveTowards(mezcla, 1f, Time.deltaTime / Mathf.Max(0.1f, segundosMezcla));
            float general = volumen * (1f - 0.75f * fundido);
            a.volume = general * Mathf.Sin(mezcla * Mathf.PI / 2);          // mezcla de igual potencia
            b.volume = general * Mathf.Cos(mezcla * Mathf.PI / 2);
            if (b.volume <= 0.001f && b.isPlaying) b.Stop();
            if (fuenteVolcan) fuenteVolcan.volume = volumen * (ambiente ? ambiente.Volcan : 0.5f) * (1f - 0.75f * fundido);
        }

        public SonidoEspecie De(string especie) => Array.Find(especies, x => x.especie == especie);

        public AudioClip Pisada(string peso, bool barro)
        {
            var p = Array.Find(pisadas, x => x.peso == peso) ?? (pisadas.Length > 0 ? pisadas[0] : null);
            var lista = p == null ? null : (barro ? p.barro : p.seco);
            return lista == null || lista.Length == 0 ? null : lista[UnityEngine.Random.Range(0, lista.Length)];
        }

        /// <summary>Barro donde hay agua o bosque húmedo; seco en la llanura, la ceniza y hoy.</summary>
        public bool SueloBarroso => clave == "rio" || clave == "bosque" || clave == "titulo";
    }
}
