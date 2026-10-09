// OSC mínimo para los sensores del stand, sin paquetes externos: el mismo protocolo que ya
// hablan el tracker (lidarwall) y TouchDesigner. Es una copia fiel de oscDecodificar() de
// experiencia/server/puente.mjs, así la web y Unity entienden exactamente los mismos mensajes.
//
// Tipos: i (int32), f (float32), s (texto), T/F (verdadero/falso) y bundles (#bundle).
// La recepción corre en hilos aparte (uno por puerto) y deja los mensajes en una cola; el hilo
// principal de Unity los toma cuadro a cuadro con TomarMensaje(). Nada de Unity acá adentro: se
// prueba con dotnet en la nube (ver Pruebas/).

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;

namespace FNS
{
    public struct OscMensaje
    {
        public string direccion;
        public object[] valores;

        public float Numero(int i = 0, float siNo = 0f)
        {
            if (valores == null || i >= valores.Length) return siNo;
            switch (valores[i])
            {
                case int n: return n;
                case float f: return f;
                case bool b: return b ? 1f : 0f;
                case string s: return float.TryParse(s, System.Globalization.NumberStyles.Float,
                    System.Globalization.CultureInfo.InvariantCulture, out var v) ? v : siNo;
            }
            return siNo;
        }
    }

    public static class OscCodec
    {
        static int Leer32(byte[] b, int i) => (b[i] << 24) | (b[i + 1] << 16) | (b[i + 2] << 8) | b[i + 3];

        static string Cadena(byte[] b, ref int i, int fin)
        {
            int cero = Array.IndexOf(b, (byte)0, i, fin - i);
            if (cero < 0) throw new FormatException("OSC: cadena sin terminar");
            string s = Encoding.UTF8.GetString(b, i, cero - i);
            i = (cero / 4 + 1) * 4;               // las cadenas se rellenan a múltiplos de 4
            return s;
        }

        /// <summary>Decodifica un paquete (mensaje o bundle) y agrega los mensajes a la lista.</summary>
        public static void Decodificar(byte[] b, int inicio, int largo, List<OscMensaje> salida)
        {
            int fin = inicio + largo;
            if (largo >= 8 && Encoding.ASCII.GetString(b, inicio, 7) == "#bundle")
            {
                int i = inicio + 16;              // "#bundle\0" + 8 bytes de marca de tiempo
                while (i + 4 <= fin)
                {
                    int n = Leer32(b, i);
                    if (n <= 0 || i + 4 + n > fin) break;
                    Decodificar(b, i + 4, n, salida);
                    i += 4 + n;
                }
                return;
            }
            // Cadena() avanza con índices absolutos: se trabaja sobre una copia que empieza en 0
            byte[] m = b;
            int j = 0;
            if (inicio != 0) { m = new byte[largo]; Buffer.BlockCopy(b, inicio, m, 0, largo); }
            string dir = Cadena(m, ref j, largo);
            string tipos = j < largo ? Cadena(m, ref j, largo) : ",";
            var vals = new List<object>();
            for (int k = 1; k < tipos.Length; k++)
            {
                char t = tipos[k];
                if (t == 'i') { vals.Add(Leer32(m, j)); j += 4; }
                else if (t == 'f')
                {
                    int raw = Leer32(m, j); j += 4;
                    vals.Add(BitConverter.ToSingle(BitConverter.GetBytes(raw), 0));
                }
                else if (t == 's') vals.Add(Cadena(m, ref j, largo));
                else if (t == 'T') vals.Add(true);
                else if (t == 'F') vals.Add(false);
                else break;                       // tipo desconocido: el resto no se puede leer
            }
            salida.Add(new OscMensaje { direccion = dir, valores = vals.ToArray() });
        }

        static void Rellenar(List<byte> b) { do b.Add(0); while (b.Count % 4 != 0); }

        /// <summary>Codifica un mensaje (para las pruebas y para reenviar a TD si hace falta).</summary>
        public static byte[] Codificar(string dir, params object[] vals)
        {
            var b = new List<byte>(Encoding.UTF8.GetBytes(dir));
            Rellenar(b);
            var tipos = new StringBuilder(",");
            var datos = new List<byte>();
            foreach (var v in vals)
            {
                switch (v)
                {
                    case string s: tipos.Append('s'); datos.AddRange(Encoding.UTF8.GetBytes(s)); Rellenar(datos); break;
                    case int n: tipos.Append('i'); datos.AddRange(GrandeAlFinal(BitConverter.GetBytes(n))); break;
                    case bool x: tipos.Append(x ? 'T' : 'F'); break;
                    default: tipos.Append('f'); datos.AddRange(GrandeAlFinal(BitConverter.GetBytes(Convert.ToSingle(v)))); break;
                }
            }
            b.AddRange(Encoding.ASCII.GetBytes(tipos.ToString()));
            Rellenar(b);
            b.AddRange(datos);
            return b.ToArray();
        }

        static byte[] GrandeAlFinal(byte[] x) { if (BitConverter.IsLittleEndian) Array.Reverse(x); return x; }
    }

    /// <summary>Escucha OSC por UDP en uno o más puertos (7001 tracker, 10000 cuerpo/TD).</summary>
    public sealed class OscReceptor : IDisposable
    {
        readonly ConcurrentQueue<OscMensaje> cola = new ConcurrentQueue<OscMensaje>();
        readonly List<UdpClient> clientes = new List<UdpClient>();
        readonly List<Thread> hilos = new List<Thread>();
        volatile bool vivo = true;
        public readonly List<string> errores = new List<string>();
        public int recibidos;

        public OscReceptor(IEnumerable<int> puertos)
        {
            foreach (int puerto in puertos)
            {
                try
                {
                    // reutilizar la dirección: TD o el puente de Node pueden estar escuchando el mismo
                    // puerto en la misma máquina (en Windows el que llega último recibe)
                    var c = new UdpClient { ExclusiveAddressUse = false };
                    c.Client.SetSocketOption(SocketOptionLevel.Socket, SocketOptionName.ReuseAddress, true);
                    c.Client.Bind(new IPEndPoint(IPAddress.Any, puerto));
                    clientes.Add(c);
                    var h = new Thread(() => Escuchar(c)) { IsBackground = true, Name = $"OSC {puerto}" };
                    hilos.Add(h);
                    h.Start();
                }
                catch (Exception e)
                {
                    errores.Add($"OSC :{puerto} → {e.Message}");
                }
            }
        }

        void Escuchar(UdpClient c)
        {
            var desde = new IPEndPoint(IPAddress.Any, 0);
            var lote = new List<OscMensaje>();
            while (vivo)
            {
                try
                {
                    byte[] b = c.Receive(ref desde);
                    lote.Clear();
                    OscCodec.Decodificar(b, 0, b.Length, lote);
                    foreach (var m in lote) cola.Enqueue(m);
                    Interlocked.Increment(ref recibidos);
                }
                catch (SocketException) { if (!vivo) return; }
                catch (ObjectDisposedException) { return; }
                catch (Exception) { /* paquete roto: se ignora, igual que en el puente de Node */ }
            }
        }

        public bool TomarMensaje(out OscMensaje m) => cola.TryDequeue(out m);

        public void Dispose()
        {
            vivo = false;
            foreach (var c in clientes) { try { c.Close(); } catch { } }
            clientes.Clear();
        }
    }
}
