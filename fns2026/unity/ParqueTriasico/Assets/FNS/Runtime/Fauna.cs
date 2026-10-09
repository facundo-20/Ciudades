// La fauna viva: los animales de Meshy con el esqueleto y los ciclos de rig_fauna.py (caminar,
// quieto, pastar u olfatear). Cada especie vive en su zona (los mismos lugares que en Blender) y
// en cada capítulo hay un ENCUENTRO: una manada o un animal cruza delante del visitante, por
// adentro de la sala, a escala real, como en la referencia del cubo inmersivo.
//
// Velocidad de paseo = la del informe del rig (sale del largo de la pata): los pies no patinan.

using System;
using System.Collections.Generic;
using UnityEngine;

namespace FNS
{
    [Serializable]
    public class ModeloAnimal
    {
        public string especie;
        public GameObject prefab;              // con Animator (estados caminar / quieto / pastar u olfatear)
        public float velocidad = 1f;           // m/s del ciclo de caminar
    }

    public class Fauna : MonoBehaviour
    {
        public Director director;
        public ModeloAnimal[] modelos;
        public float radioActivo = 220f;       // más lejos de la sala, los animales se congelan (ahorra CPU)

        readonly List<Animal> residentes = new List<Animal>();
        readonly List<Animal> deEncuentro = new List<Animal>();

        // quién protagoniza cada capítulo (sólo especies de Ischigualasto, 231 Ma: nada de pterosaurios
        // ni de dinosaurios de otras épocas, aunque estén en la referencia)
        static readonly Dictionary<string, (string especie, int cuantos)[]> Elenco = new Dictionary<string, (string, int)[]>
        {
            // si una especie no tiene modelo (p. ej. faltan los de Meshy de la PC), se saltea sola
            { "rio", new[] { ("hyperodapedon", 3), ("pisanosaurus", 2), ("exaeretodon", 1) } },
            { "bosque", new[] { ("chromogisaurus", 2), ("panphagia", 2), ("eodromaeus", 1), ("herrerasaurus", 1) } },
            { "llanura", new[] { ("ischigualastia", 3), ("sanjuansaurus", 1), ("saurosuchus", 1) } },
            { "ceniza", new[] { ("ischigualastia", 2) } },
        };

        void Start()
        {
            foreach (var lugar in director.Mundo.fauna)
            {
                var m = Modelo(lugar.especie);
                if (m == null) continue;
                var pos = new Vector3(lugar.pos[0], lugar.pos[1], lugar.pos[2]);
                var a = Crear(m, pos, Quaternion.Euler(0, lugar.giro, 0));
                a.hogar = pos;
                residentes.Add(a);
            }
        }

        ModeloAnimal Modelo(string especie) => Array.Find(modelos, x => x.especie == especie && x.prefab);

        Animal Crear(ModeloAnimal m, Vector3 pos, Quaternion rot)
        {
            var go = Instantiate(m.prefab, pos, rot, transform);
            go.name = m.especie;
            // TryGetComponent y no '??': en el editor un componente que falta no es null de C#
            if (!go.TryGetComponent<Animal>(out var a)) a = go.AddComponent<Animal>();
            a.especie = m.especie;
            a.velocidad = m.velocidad;
            a.director = director;
            a.Iniciar();
            return a;
        }

        public void CambioDeCapitulo(Capitulo c)
        {
            foreach (var a in deEncuentro) if (a) Destroy(a.gameObject);
            deEncuentro.Clear();
            // hoy no hay animales vivos: sólo el paisaje (los fósiles quedaron en la roca)
            foreach (var a in residentes) if (a) a.gameObject.SetActive(!c.EsHoy);
        }

        /// <summary>Una manada cruza delante de la sala, de un costado al otro, a 2,5–4 m del
        /// visitante: sobre el piso LED y frente a las paredes.</summary>
        public void Encuentro(Capitulo c, Transform sala, bool forzado)
        {
            if (!Elenco.TryGetValue(c.clave, out var elenco)) return;
            if (!forzado && deEncuentro.Count > 0) return;
            int lado = UnityEngine.Random.value < 0.5f ? 1 : -1;
            float demora = 0f;
            foreach (var (especie, cuantos) in elenco)
            {
                var m = Modelo(especie);
                if (m == null) continue;
                for (int i = 0; i < cuantos; i++)
                {
                    float z = 2.5f + i * 1.3f + UnityEngine.Random.Range(-0.3f, 0.3f);
                    Vector3 desde = sala.TransformPoint(new Vector3(12f * lado, 0, z));
                    Vector3 medio = sala.TransformPoint(new Vector3(0, 0, z + UnityEngine.Random.Range(-0.6f, 0.6f)));
                    Vector3 hasta = sala.TransformPoint(new Vector3(-14f * lado, 0, z + 1.5f));
                    var a = Crear(m, desde, Quaternion.LookRotation(medio - desde));
                    a.Recorrer(new[] { desde, medio, hasta }, demora + i * 1.1f);
                    deEncuentro.Add(a);
                }
                demora += cuantos * 1.1f + 2.5f;
            }
        }

        void Update()
        {
            var sala = director.carro.position;
            foreach (var a in residentes)
                if (a && a.gameObject.activeSelf) a.Activo = (a.transform.position - sala).sqrMagnitude < radioActivo * radioActivo;
            for (int i = deEncuentro.Count - 1; i >= 0; i--)
                if (!deEncuentro[i]) deEncuentro.RemoveAt(i);
        }
    }

    public class Animal : MonoBehaviour
    {
        public string especie;
        public float velocidad = 1f;
        public Director director;
        public Vector3 hogar;
        public bool Activo { get; set; } = true;

        enum Modo { Quieto, Pastar, Caminar, Recorrido, Mirar }
        Modo modo = Modo.Quieto;
        Animator animador;
        string estadoActual;
        float reloj, espera;
        Vector3 destino;
        Vector3[] ruta;
        int tramo;
        Vector3 mirarA;
        string estadoQuieto;

        public void Iniciar()
        {
            animador = GetComponentInChildren<Animator>();
            estadoQuieto = Tiene("pastar") ? "pastar" : "olfatear";
            espera = UnityEngine.Random.Range(2f, 8f);
            Poner(UnityEngine.Random.value < 0.5f ? "quieto" : estadoQuieto, UnityEngine.Random.value);
            if (!GetComponentInChildren<Collider>())
            {
                // para que el toque del sensor lo encuentre: una caja del tamaño del cuerpo
                var b = new Bounds(transform.position, Vector3.zero);
                foreach (var r in GetComponentsInChildren<Renderer>()) b.Encapsulate(r.bounds);
                var caja = gameObject.AddComponent<BoxCollider>();
                caja.center = transform.InverseTransformPoint(b.center);
                caja.size = b.size;
            }
        }

        bool Tiene(string estado) => animador && animador.HasState(0, Animator.StringToHash(estado));

        void Poner(string estado, float desde = 0f)
        {
            if (!animador || estadoActual == estado || !Tiene(estado)) return;
            estadoActual = estado;
            animador.CrossFadeInFixedTime(estado, 0.35f, 0, desde);
        }

        public void Recorrer(Vector3[] puntos, float demora)
        {
            ruta = puntos;
            tramo = 1;
            modo = Modo.Recorrido;
            espera = demora;
            Poner("quieto");
        }

        public void Acariciar(Vector3 visitante)
        {
            if (modo == Modo.Recorrido) return;     // los de la manada siguen de largo
            mirarA = visitante;
            modo = Modo.Mirar;
            reloj = 0;
            Poner("quieto");
        }

        void Update()
        {
            if (!Activo) { if (animador) animador.enabled = false; return; }
            if (animador && !animador.enabled) animador.enabled = true;
            float dt = Time.deltaTime;
            reloj += dt;
            switch (modo)
            {
                case Modo.Quieto:
                case Modo.Pastar:
                    if (reloj > espera)
                    {
                        // un paseo corto alrededor de su lugar, sin meterse al agua
                        for (int i = 0; i < 12; i++)
                        {
                            var p = hogar + new Vector3(UnityEngine.Random.Range(-12f, 12f), 0, UnityEngine.Random.Range(-12f, 12f));
                            p.y = director.Suelo(p, false);
                            if (p.y > director.Mundo.nivel_agua + 0.15f) { destino = p; break; }
                        }
                        modo = Modo.Caminar;
                        reloj = 0;
                        Poner("caminar");
                    }
                    break;
                case Modo.Caminar:
                    if (Avanzar(destino, velocidad, dt) || reloj > 25f)
                    {
                        modo = UnityEngine.Random.value < 0.6f ? Modo.Pastar : Modo.Quieto;
                        espera = UnityEngine.Random.Range(4f, 12f);
                        reloj = 0;
                        Poner(modo == Modo.Pastar ? estadoQuieto : "quieto");
                    }
                    break;
                case Modo.Recorrido:
                    if (reloj < espera) break;
                    Poner("caminar");
                    if (Avanzar(ruta[tramo], velocidad * 1.15f, dt))
                    {
                        tramo++;
                        if (tramo >= ruta.Length) { Destroy(gameObject); return; }
                    }
                    break;
                case Modo.Mirar:
                    Girar(mirarA - transform.position, dt * 1.5f);
                    if (reloj > 4f) { modo = Modo.Quieto; reloj = 0; espera = 3f; }
                    break;
            }
            if (animador) animador.speed = 1f;
        }

        bool Avanzar(Vector3 a, float v, float dt)
        {
            Vector3 d = a - transform.position;
            d.y = 0;
            if (d.magnitude < 0.6f) return true;
            Girar(d, dt * 2f);
            // camina hacia donde mira (gira mientras avanza, como un animal y no como un carrito)
            float alineado = Mathf.Clamp01(Vector3.Dot(transform.forward, d.normalized));
            var p = transform.position + transform.forward * v * alineado * dt;
            p.y = director.Suelo(p, false);
            transform.position = p;
            return false;
        }

        void Girar(Vector3 hacia, float k)
        {
            hacia.y = 0;
            if (hacia.sqrMagnitude < 1e-4f) return;
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(hacia.normalized), Mathf.Clamp01(k));
        }
    }
}
