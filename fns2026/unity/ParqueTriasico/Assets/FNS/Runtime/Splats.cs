// Los Gaussian splats horneados de cada capítulo (pipeline/splats): la flora con la luz de Cycles
// (rebotes, sombras suaves, hojas translúcidas), dibujada en vivo por UnityGaussianSplatting (MIT,
// Aras Pranckevičius; paquete embebido en Packages/).
//
// Cómo conviven con el resto:
//  · Se dibujan después del posproceso (ya traen el "look" de Cycles) y se tapan con lo opaco: un
//    dinosaurio delante de un helecho horneado lo tapa, y uno detrás queda tapado.
//  · El suelo es el terreno de HDRP (recibe sombras, pisadas y ceniza): del splat se podó el suelo.
//  · Donde hay splat no se dibuja la vegetación de mallas (Vegetacion.Excluir), para no repetir plantas.
//  · El fundido entre capítulos baja su opacidad (el negro del posproceso no les llega).
//  · "--sin-splats" los apaga (para comparar o si una máquina no da).
using System;
using GaussianSplatting.Runtime;
using UnityEngine;

namespace FNS
{
    [Serializable]
    public class SplatCapitulo
    {
        public string capitulo;
        public GaussianSplatRenderer splat;
        public Vector3 desde, hasta;          // el recorrido de la sala en ese capítulo (Unity)
        public float radio = 45f;             // hasta dónde llega el splat alrededor del recorrido
    }

    public class Splats : MonoBehaviour
    {
        public SplatCapitulo[] capitulos = new SplatCapitulo[0];
        public Vegetacion[] vegetaciones = new Vegetacion[0];

        SplatCapitulo actual;
        bool apagados;

        public bool Hay => capitulos.Length > 0 && !apagados;

        void Awake()
        {
            apagados = Arranque.Tiene("--sin-splats");
            foreach (var c in capitulos)
                if (c.splat) c.splat.gameObject.SetActive(false);
        }

        public void CambioDeCapitulo(Capitulo cap)
        {
            actual = null;
            foreach (var c in capitulos)
            {
                bool este = !apagados && c.splat && c.capitulo == cap.clave;
                if (c.splat) c.splat.gameObject.SetActive(este);
                if (este) actual = c;
            }
            foreach (var v in vegetaciones)
            {
                if (!v) continue;
                if (actual != null) v.Excluir(actual.desde, actual.hasta, actual.radio);
                else v.SinExcluir();
            }
        }

        /// <summary>0 = imagen, 1 = negro (o blanco de ceniza): el splat se desvanece igual.</summary>
        public void Fundido(float f)
        {
            if (actual != null && actual.splat) actual.splat.m_OpacityScale = 1f - Mathf.Clamp01(f);
        }
    }
}
