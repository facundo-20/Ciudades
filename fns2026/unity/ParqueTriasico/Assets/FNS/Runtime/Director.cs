// El guion en vivo: seis capítulos sobre el mismo mundo (los de Blender y la web). La sala entera
// (piso + paredes) es un "carro" que viaja por el Triásico: el piso LED muestra el suelo que se
// pisa, las paredes lo que rodea. En cada capítulo pasa un encuentro: un animal o una manada
// cruza al lado del visitante, a escala real.
//
// Del Triásico a hoy se pasa por la lluvia de ceniza: la bruma lo tapa todo, se cambia de mundo
// y aparece el Valle de la Luna real (relieve de Copernicus, color de Sentinel-2).

using System;
using UnityEngine;

namespace FNS
{
    public class Director : MonoBehaviour
    {
        public TextAsset mundoJson;
        public Transform carro;                  // la sala: su piso es el y = 0 local
        public Sala sala;
        public Sensores sensores;
        public Ambiente ambiente;
        public Fauna fauna;
        public Interfaz interfaz;
        public Terrain[] suelosTriasico, suelosHoy;
        public float alturaOjo = 1.6f;
        public bool automatico = true;
        [Tooltip("Segundos de fundido a negro entre capítulos (el de la ceniza a hoy es más largo)")]
        public float fundido = 0.7f;

        public Mundo Mundo { get; private set; }
        public int Indice { get; private set; }
        public Capitulo Actual => Mundo.capitulos[Indice];
        public float Progreso => Mathf.Clamp01(t / Mathf.Max(1f, Actual.duracion));

        float t;
        int pedido = -1;              // capítulo al que se va cuando termine el fundido
        float fundidoEstado;          // 0 = imagen, 1 = negro
        bool encuentroHecho;
        Vector3 posSuave;
        Quaternion rotSuave;
        bool primero = true;

        void Awake()
        {
            Mundo = JsonUtility.FromJson<Mundo>(mundoJson.text);
            int arranque = Arranque.Entero("--capitulo", 0);
            Indice = Mathf.Clamp(arranque, 0, Mundo.capitulos.Length - 1);
            automatico = !Arranque.Tiene("--sin-auto");
        }

        void Start() => EntrarEn(Indice);

        public void Ir(int i)
        {
            int n = Mundo.capitulos.Length;
            pedido = ((i % n) + n) % n;
        }

        public void Siguiente() => Ir(Indice + 1);
        public void Anterior() => Ir(Indice - 1);

        void EntrarEn(int i)
        {
            Indice = i;
            t = 0;
            encuentroHecho = false;
            var cap = Actual;
            bool hoy = cap.EsHoy;
            ambiente.PonerEra(hoy);
            ambiente.Capitulo(cap, inmediato: primero);
            fauna.CambioDeCapitulo(cap);
            interfaz.MostrarCapitulo(cap, Mundo);
            primero = false;
            Colocar(0f, true);
        }

        void Update()
        {
            while (sensores.TomarGesto(out var g))
            {
                if (g == "siguiente") Siguiente();
                else if (g == "anterior") Anterior();
                else if (g == "textos") interfaz.mostrarTextos = !interfaz.mostrarTextos;
                else if (g.StartsWith("capitulo_") && int.TryParse(g.Substring(9), out int k)) Ir(k);
                else if (g == "salto") fauna.Encuentro(Actual, carro, true);
            }
            float dt = Time.deltaTime;
            t += dt;
            if (automatico && pedido < 0 && t > Actual.duracion) Siguiente();

            // fundido: baja a negro, cambia de capítulo y vuelve. De la ceniza a hoy, más lento
            float dur = pedido >= 0 && Actual.clave == "ceniza" ? fundido * 3.5f : fundido;
            if (pedido >= 0)
            {
                fundidoEstado = Mathf.MoveTowards(fundidoEstado, 1f, dt / dur);
                if (fundidoEstado >= 1f)
                {
                    int i = pedido;
                    pedido = -1;
                    EntrarEn(i);
                }
            }
            else fundidoEstado = Mathf.MoveTowards(fundidoEstado, 0f, dt / (dur * 1.4f));
            ambiente.Fundido(fundidoEstado, Actual.clave == "ceniza" || Actual.EsHoy);

            Colocar(dt, false);

            // el encuentro del capítulo: a un cuarto del recorrido, o antes si alguien está en la sala
            if (!encuentroHecho && (Progreso > 0.22f || (sensores.CuerpoPresente && Progreso > 0.08f)))
            {
                encuentroHecho = true;
                fauna.Encuentro(Actual, carro, false);
            }

            foreach (var toque in sensores.Toques)
                if (toque.nuevo) Tocar(toque);
        }

        /// <summary>El carro (la sala) sobre el recorrido del capítulo: ojo a la altura de la cámara de
        /// Blender, piso de la sala nunca bajo tierra, mirando hacia el punto del capítulo.</summary>
        void Colocar(float dt, bool saltar)
        {
            var cap = Actual;
            float k = Progreso;
            float e = k * k * (3 - 2 * k);
            Vector3 desde = V(cap.desde), hasta = V(cap.hasta), mira = V(cap.mira);
            Vector3 ojo = Vector3.Lerp(desde, hasta, e);
            float suelo = Suelo(ojo, cap.EsHoy);
            float pisoY = Mathf.Max(ojo.y - alturaOjo, suelo);
            Vector3 pos = new Vector3(ojo.x, pisoY, ojo.z);
            Vector3 dir = mira - ojo;
            dir.y = 0;
            if (dir.sqrMagnitude < 1e-4f) dir = Vector3.forward;
            Quaternion rot = Quaternion.LookRotation(dir.normalized, Vector3.up);
            if (saltar) { posSuave = pos; rotSuave = rot; }
            else
            {
                float a = 1f - Mathf.Exp(-dt * 1.5f);
                posSuave = Vector3.Lerp(posSuave, pos, a);
                rotSuave = Quaternion.Slerp(rotSuave, rot, a);
            }
            carro.SetPositionAndRotation(posSuave, rotSuave);
        }

        public float Suelo(Vector3 p, bool hoy)
        {
            var lista = hoy ? suelosHoy : suelosTriasico;
            float mejor = float.NegativeInfinity;
            if (lista == null) return 0f;
            foreach (var ter in lista)
            {
                if (!ter || !ter.isActiveAndEnabled) continue;
                var tp = ter.transform.position;
                var tam = ter.terrainData.size;
                if (p.x < tp.x || p.z < tp.z || p.x > tp.x + tam.x || p.z > tp.z + tam.z) continue;
                // el terreno fino manda: el primero de la lista que cubre el punto
                return ter.SampleHeight(p) + tp.y;
            }
            return float.IsNegativeInfinity(mejor) ? 0f : mejor;
        }

        void Tocar(Toque toque)
        {
            var cam = sala.Principal;
            if (!cam) return;
            // u, v del sensor de la pared: (0,0) arriba a la izquierda; el viewport de Unity, abajo
            Ray rayo = cam.ViewportPointToRay(new Vector3(toque.u, 1f - toque.v, 0));
            if (Physics.Raycast(rayo, out var golpe, 150f))
            {
                var animal = golpe.collider.GetComponentInParent<Animal>();
                if (animal)
                {
                    animal.Acariciar(cam.transform.position);
                    interfaz.MostrarFicha(Mundo.FichaDe(animal.especie), 11f);
                    return;
                }
                ambiente.Pisada(golpe.point, golpe.normal);
            }
        }

        static Vector3 V(float[] a) => a != null && a.Length >= 3 ? new Vector3(a[0], a[1], a[2]) : Vector3.zero;
    }
}
