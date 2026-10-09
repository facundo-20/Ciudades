// Pruebas de la parte del Parque Triásico que no depende de Unity. Corre en la nube con dotnet.
using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using FNS;

static class Pruebas
{
    static int fallas, pasadas;

    static void Ver(bool ok, string que)
    {
        if (ok) pasadas++; else fallas++;
        Console.WriteLine((ok ? "  ok    " : "  FALLA ") + que);
    }

    static int Main(string[] args)
    {
        string datos = args.Length > 0 ? args[0] : "../../ParqueTriasico/Datos";

        Console.WriteLine("OSC");
        var m = OscCodec.Codificar("/wall/touch/3/x", 0.25f);
        var lista = new List<OscMensaje>();
        OscCodec.Decodificar(m, 0, m.Length, lista);
        Ver(lista.Count == 1 && lista[0].direccion == "/wall/touch/3/x" && Math.Abs(lista[0].Numero() - 0.25f) < 1e-6, "float ida y vuelta");
        var m2 = OscCodec.Codificar("/gesto/salto", "hola", 7, true);
        lista.Clear();
        OscCodec.Decodificar(m2, 0, m2.Length, lista);
        Ver(lista[0].valores.Length == 3 && (string)lista[0].valores[0] == "hola" && (int)lista[0].valores[1] == 7 && (bool)lista[0].valores[2], "texto, entero y T");
        // bundle con dos mensajes (así manda TD varios valores juntos)
        var b = new List<byte>(Encoding.ASCII.GetBytes("#bundle\0"));
        b.AddRange(new byte[8]);
        foreach (var x in new[] { OscCodec.Codificar("/body/x", 0.8f), OscCodec.Codificar("/body/present", 1) })
        {
            var n = BitConverter.GetBytes(x.Length); Array.Reverse(n);
            b.AddRange(n); b.AddRange(x);
        }
        lista.Clear();
        OscCodec.Decodificar(b.ToArray(), 0, b.Count, lista);
        Ver(lista.Count == 2 && lista[1].direccion == "/body/present", "bundle con dos mensajes");

        Console.WriteLine("Sensores (misma lógica que puente.mjs)");
        var e = new EstadoSensores();
        var toques = new List<Toque>();
        e.Recibir("/wall/touch/0/x", new object[] { 0.3f }, 0);
        e.Recibir("/wall/touch/0/y", new object[] { 0.7f }, 0);
        e.Recibir("/wall/touch/0/active", new object[] { 1 }, 0);
        e.Leer(0.1, toques, out bool presente, out float cx);
        Ver(toques.Count == 1 && toques[0].nuevo && Math.Abs(toques[0].u - 0.3f) < 1e-6 && presente, "toque nuevo en la pared → hay alguien");
        e.Leer(0.2, toques, out presente, out cx);
        Ver(toques.Count == 1 && !toques[0].nuevo, "el segundo cuadro ya no es 'nuevo'");
        e.Leer(2.0, toques, out presente, out cx);
        Ver(toques.Count == 0 && !presente, "tracker callado 1,5 s → sin dedos fantasma");
        e.Recibir("/gesto/brazos_arriba", new object[0], 3);
        Ver(e.TomarGesto(out var g) && g == "brazos_arriba", "gesto");
        double prox = 0;
        var sim = new EstadoSensores();
        for (double t = 0; t < 41; t += 0.05) sim.Simular(t, true, ref prox);
        int gestos = 0;
        while (sim.TomarGesto(out _)) gestos++;
        Ver(gestos == 1, "visitante simulado: un gesto a los 40 s");

        Console.WriteLine("OSC real por UDP (receptor en hilos)");
        using (var rx = new OscReceptor(new[] { 17001, 17010 }))
        using (var udp = new UdpClient())
        {
            var p1 = OscCodec.Codificar("/body/x", 0.42f);
            var p2 = OscCodec.Codificar("/touch/down", 1);
            udp.Send(p1, p1.Length, "127.0.0.1", 17001);
            udp.Send(p2, p2.Length, "127.0.0.1", 17010);
            var vistos = new List<string>();
            for (int i = 0; i < 100 && vistos.Count < 2; i++)
            {
                while (rx.TomarMensaje(out var mm)) vistos.Add(mm.direccion);
                Thread.Sleep(10);
            }
            Ver(vistos.Contains("/body/x") && vistos.Contains("/touch/down"), $"llegaron por los dos puertos ({string.Join(", ", vistos)})");
        }

        Console.WriteLine("Alturas (predictor de exportar_mundo.py, comparado con Python)");
        string ruta = Path.Combine(datos, "triasico_cerca.r16d.gz");
        if (File.Exists(ruta))
        {
            byte[] crudo;
            using (var f = File.OpenRead(ruta)) using (var gz = new GZipStream(f, CompressionMode.Decompress)) using (var ms = new MemoryStream()) { gz.CopyTo(ms); crudo = ms.ToArray(); }
            var h = Alturas.Decodificar(crudo, 2049);
            // valores que dio Python con la función de altura (exportar_mundo.altura): ver la prueba del 09/10
            const float hmin = -6.9308f, hmax = 23.3139f;
            float A(int i, int j) => hmin + h[j, i] * (hmax - hmin);
            Ver(Math.Abs(A(400, 1000) - 15.579f) < 0.002f, $"x=-126, z=-6 → {A(400, 1000):0.000} m (Python 15,579)");
            Ver(Math.Abs(A(1024, 1024) - (-0.58f)) < 0.002f, $"x=30, z=0 → {A(1024, 1024):0.000} m (Python -0,580)");
            Ver(Math.Abs(A(1500, 300) - 16.153f) < 0.002f, $"x=149, z=-181 → {A(1500, 300):0.000} m (Python 16,153)");
        }
        else Ver(false, "no encuentro " + ruta);

        Console.WriteLine($"\n{pasadas} pasadas, {fallas} fallas");
        return fallas == 0 ? 0 : 1;
    }
}
