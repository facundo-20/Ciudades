// Arma el Parque Triásico entero en Unity, sin tocar nada a mano:
//
//   Menú FNS 2026 → Construir todo              (en el editor abierto)
//   Unity -batchmode -quit -projectPath <ParqueTriasico> -executeMethod FNS.Editor.Constructor.DesdeConsola
//         [-fnsCompilar]                         (además deja el ejecutable en ../Builds/<plataforma>/)
//
// Lee todo de ../Datos (lo generan exportar_mundo.py, valle_real.py, texturas_suelo.py, flora_lod.py
// y pipeline/rig_fauna.py) y de los GLB de la experiencia web. Pasos:
//   1. HDRP: asset, agua, nubes, niebla volumétrica, trazado de rayos (Windows), espacio lineal.
//   2. Modelos: flora con sus 3 niveles, fauna con esqueleto y animaciones (Animator por especie).
//   3. Suelo: capas de Terrain con mapa de máscara HDRP (las CC0 escaneadas si están en la PC).
//   4. Terrenos: Triásico (fino 512 m + lejano 8 km con el volcán) y hoy (el Valle de la Luna real).
//   5. Escena: sol, volumen, río, volcán, ceniza, sala inmersiva, director, sensores, salida Spout/Syphon.
// Al final escribe ../Builds/informe_constructor.txt con lo que hizo y lo que faltó.

using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Text;
using GaussianSplatting.Runtime;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.HighDefinition;

namespace FNS.Editor
{
    public static class Constructor
    {
        const string Raiz = "Assets/FNS";
        const string Escena = Raiz + "/Escenas/ParqueTriasico.unity";
        static string Proyecto => Directory.GetParent(Application.dataPath).FullName;
        static string Datos => Path.Combine(Proyecto, "Datos");
        static string Fns => Path.GetFullPath(Path.Combine(Proyecto, "..", ".."));
        static string Builds => Path.GetFullPath(Path.Combine(Proyecto, "..", "Builds"));
        static readonly StringBuilder informe = new StringBuilder();

        static void Anotar(string t)
        {
            informe.AppendLine(t);
            Debug.Log("[FNS constructor] " + t);
        }

        [MenuItem("FNS 2026/Construir todo")]
        public static void ConstruirTodo() => Construir(false);

        [MenuItem("FNS 2026/Construir todo y compilar el ejecutable")]
        public static void ConstruirYCompilar() => Construir(true);

        /// <summary>Para -executeMethod: sale con código 0 si todo anduvo, 1 si no.</summary>
        public static void DesdeConsola()
        {
            bool compilar = Environment.GetCommandLineArgs().Contains("-fnsCompilar");
            int codigo = 0;
            try { if (!Construir(compilar)) codigo = 1; }
            catch (Exception e) { Anotar("ERROR: " + e); codigo = 1; }
            GuardarInforme();
            EditorApplication.Exit(codigo);
        }

        static bool Construir(bool compilar)
        {
            informe.Clear();
            Anotar($"Parque Triásico · {DateTime.Now:yyyy-MM-dd HH:mm} · Unity {Application.unityVersion} · {EditorUserBuildSettings.activeBuildTarget}");
            Carpetas();
            ConfigurarProyecto();
            var mundo = CopiarDatos();
            var flora = PrepararFlora();
            var fauna = PrepararFauna(mundo);
            var capas = PrepararSuelos();
            var splats = PrepararSplats();
            ArmarEscena(mundo, flora, fauna, capas, splats);
            bool ok = true;
            if (compilar) ok = Compilar();
            GuardarInforme();
            return ok;
        }

        static void Carpetas()
        {
            foreach (var c in new[] { "Render", "Datos", "Modelos/flora", "Modelos/fauna", "Modelos/lugares", "Materiales", "Suelo",
                                      "Terrenos", "Mallas", "Prefabs", "Animacion", "Escenas", "Texturas", "Splats", "Sonido" })
                Directory.CreateDirectory(Path.Combine(Proyecto, Raiz, c));
            AssetDatabase.Refresh();
        }

        // ------------------------------------------------------------------------------------------
        // 1. proyecto y HDRP
        // ------------------------------------------------------------------------------------------

        static void ConfigurarProyecto()
        {
            PlayerSettings.colorSpace = ColorSpace.Linear;                 // HDRP lo exige
            PlayerSettings.productName = "Parque Triasico";
            PlayerSettings.companyName = "FNS 2026 San Juan";
            PlayerSettings.fullScreenMode = FullScreenMode.FullScreenWindow;
            PlayerSettings.defaultIsNativeResolution = true;
            PlayerSettings.runInBackground = true;
            PlayerSettings.visibleInBackground = true;
            PlayerSettings.resizableWindow = true;
            bool windows = EditorUserBuildSettings.activeBuildTarget == BuildTarget.StandaloneWindows64;
            if (windows)
            {
                // DX12: hace falta para el trazado de rayos de las RTX
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                PlayerSettings.SetGraphicsAPIs(BuildTarget.StandaloneWindows64, new[] { GraphicsDeviceType.Direct3D12, GraphicsDeviceType.Direct3D11 });
            }
            // teclado y mouse con el Input Manager clásico (el paquete nuevo no hace falta acá)
            var ps = AssetDatabase.LoadAllAssetsAtPath("ProjectSettings/ProjectSettings.asset").FirstOrDefault();
            if (ps)
            {
                var so = new SerializedObject(ps);
                var p = so.FindProperty("activeInputHandler");
                if (p != null && p.intValue == 1) { p.intValue = 2; so.ApplyModifiedProperties(); Anotar("entrada: Input Manager + Input System"); }
            }

            string ruta = Raiz + "/Render/HDRP_ParqueTriasico.asset";
            var asset = AssetDatabase.LoadAssetAtPath<HDRenderPipelineAsset>(ruta);
            if (!asset)
            {
                asset = ScriptableObject.CreateInstance<HDRenderPipelineAsset>();
                AssetDatabase.CreateAsset(asset, ruta);
            }
            var s = asset.currentPlatformRenderPipelineSettings;
            s.supportWater = true;
            s.supportVolumetricClouds = true;
            s.supportVolumetrics = true;
            s.supportSSGI = true;
            s.supportSSR = true;
            s.supportSSAO = true;
            s.supportDecals = true;
            s.supportMotionVectors = true;
            s.supportRayTracing = windows;            // M4: todo en pantalla (SSGI, SSR)
            s.colorBufferFormat = RenderPipelineSettings.ColorBufferFormat.R16G16B16A16;
            s.hdShadowInitParams.maxDirectionalShadowMapResolution = 4096;
            asset.currentPlatformRenderPipelineSettings = s;
            EditorUtility.SetDirty(asset);
            GraphicsSettings.defaultRenderPipeline = asset;
            int previo = QualitySettings.GetQualityLevel();
            for (int i = 0; i < QualitySettings.names.Length; i++)
            {
                QualitySettings.SetQualityLevel(i, false);
                QualitySettings.renderPipeline = asset;
            }
            QualitySettings.SetQualityLevel(previo, false);
            AssetDatabase.SaveAssets();
            Anotar($"HDRP listo (agua, nubes, niebla volumétrica, SSGI{(windows ? ", trazado de rayos en DX12" : "")})");
        }

        // ------------------------------------------------------------------------------------------
        // datos
        // ------------------------------------------------------------------------------------------

        static Mundo CopiarDatos()
        {
            foreach (var f in new[] { "mundo.json", "flora_triasico.json", "flora_hoy.json" })
            {
                string src = Path.Combine(Datos, f);
                if (File.Exists(src)) File.Copy(src, Path.Combine(Proyecto, Raiz, "Datos", f), true);
            }
            AssetDatabase.Refresh();
            var json = AssetDatabase.LoadAssetAtPath<TextAsset>(Raiz + "/Datos/mundo.json");
            if (!json) throw new Exception("Falta Datos/mundo.json (correr exportar_mundo.py)");
            var mundo = JsonUtility.FromJson<Mundo>(json.text);
            Anotar($"mundo: {mundo.capitulos.Length} capítulos, {mundo.terrenos.Length} terrenos, {mundo.fauna.Length} animales");
            return mundo;
        }

        static byte[] Gunzip(string ruta)
        {
            using var f = File.OpenRead(ruta);
            using var gz = new GZipStream(f, CompressionMode.Decompress);
            using var m = new MemoryStream();
            gz.CopyTo(m);
            return m.ToArray();
        }

        static string Copiar(string origen, string destinoEnAssets)
        {
            if (!File.Exists(origen)) return null;
            string abs = Path.Combine(Proyecto, destinoEnAssets);
            Directory.CreateDirectory(Path.GetDirectoryName(abs));
            if (!File.Exists(abs) || new FileInfo(abs).Length != new FileInfo(origen).Length) File.Copy(origen, abs, true);
            return destinoEnAssets;
        }

        // ------------------------------------------------------------------------------------------
        // materiales HDRP
        // ------------------------------------------------------------------------------------------

        static Material Lit(string nombre, Texture color, Texture normal, Texture mascara, Color tinte, bool dobleCara,
                            bool triplanar = false, float metrosPorVuelta = 20f, bool transparente = false)
        {
            string ruta = $"{Raiz}/Materiales/{nombre}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (!m)
            {
                m = new Material(Shader.Find("HDRP/Lit"));
                AssetDatabase.CreateAsset(m, ruta);
            }
            m.SetTexture("_BaseColorMap", color);
            m.SetColor("_BaseColor", tinte);
            if (normal) { m.SetTexture("_NormalMap", normal); m.SetFloat("_NormalScale", 1f); }
            if (mascara)
            {
                m.SetTexture("_MaskMap", mascara);
                m.SetFloat("_SmoothnessRemapMin", 0f);
                m.SetFloat("_SmoothnessRemapMax", 1f);
                m.SetFloat("_AORemapMin", 0f);
                m.SetFloat("_AORemapMax", 1f);
            }
            m.SetFloat("_DoubleSidedEnable", dobleCara ? 1f : 0f);
            m.SetFloat("_DoubleSidedNormalMode", 1f);            // espejo: las hojas iluminadas de los dos lados
            if (triplanar)
            {
                m.SetFloat("_UVBase", 5f);                       // UVBaseMapping.Triplanar
                m.SetFloat("_TexWorldScale", 1f / metrosPorVuelta);
            }
            if (transparente) HDMaterial.SetSurfaceType(m, true);
            m.enableInstancing = true;
            HDMaterial.ValidateMaterial(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        /// <summary>Lee una textura aunque no sea legible (las que importa glTFast no lo son).</summary>
        static Color32[] Pixeles(Texture t, int w, int h, bool lineal)
        {
            var rt = RenderTexture.GetTemporary(w, h, 0, RenderTextureFormat.ARGB32, lineal ? RenderTextureReadWrite.Linear : RenderTextureReadWrite.sRGB);
            Graphics.Blit(t, rt);
            var previa = RenderTexture.active;
            RenderTexture.active = rt;
            var lectura = new Texture2D(w, h, TextureFormat.RGBA32, false, lineal);
            lectura.ReadPixels(new Rect(0, 0, w, h), 0, 0);
            lectura.Apply();
            RenderTexture.active = previa;
            RenderTexture.ReleaseTemporary(rt);
            var px = lectura.GetPixels32();
            UnityEngine.Object.DestroyImmediate(lectura);
            return px;
        }

        /// <summary>Mapa de máscara de HDRP: R metal, G oclusión, B detalle/altura, A lisura.</summary>
        static Texture2D Mascara(string rutaAsset, int w, int h, Func<int, (float metal, float ao, float alto, float lisura)> f)
        {
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false, true);
            var px = new Color32[w * h];
            for (int i = 0; i < px.Length; i++)
            {
                var (me, ao, al, li) = f(i);
                px[i] = new Color32((byte)(me * 255), (byte)(ao * 255), (byte)(al * 255), (byte)(li * 255));
            }
            t.SetPixels32(px);
            t.Apply();
            File.WriteAllBytes(Path.Combine(Proyecto, rutaAsset), t.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(t);
            AssetDatabase.ImportAsset(rutaAsset);
            var imp = (TextureImporter)AssetImporter.GetAtPath(rutaAsset);
            imp.sRGBTexture = false;
            imp.mipmapEnabled = true;
            imp.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(rutaAsset);
        }

        static Material MaterialDeGltf(string rutaGlb)
        {
            return AssetDatabase.LoadAllAssetsAtPath(rutaGlb).OfType<Material>().FirstOrDefault();
        }

        /// <summary>HDRP/Lit con las texturas que trae un GLB de Meshy (color, normal, metal-rugosidad).</summary>
        static Material LitDesdeGltf(string nombre, string rutaGlb, bool dobleCara)
        {
            var g = MaterialDeGltf(rutaGlb);
            if (!g) return null;
            Texture col = g.HasProperty("baseColorTexture") ? g.GetTexture("baseColorTexture") : null;
            Texture nor = g.HasProperty("normalTexture") ? g.GetTexture("normalTexture") : null;
            Texture mr = g.HasProperty("metallicRoughnessTexture") ? g.GetTexture("metallicRoughnessTexture") : null;
            Texture2D masc = null;
            if (mr)
            {
                int w = Mathf.Min(mr.width, 2048), h = Mathf.Min(mr.height, 2048);
                var px = Pixeles(mr, w, h, true);
                // glTF: G = rugosidad, B = metal
                masc = Mascara($"{Raiz}/Texturas/{nombre}_mascara.png", w, h, i => (px[i].b / 255f, 1f, 0f, 1f - px[i].g / 255f));
            }
            return Lit(nombre, col, nor, masc, Color.white, dobleCara);
        }

        // ------------------------------------------------------------------------------------------
        // 2. flora
        // ------------------------------------------------------------------------------------------

        static readonly (string nombre, float meceo, bool sombra, float[] hasta)[] Plantas =
        {
            ("helecho", 2.5f, false, new[] { 25f, 45f, 70f }),
            ("neocalamites", 1.8f, true, new[] { 35f, 90f, 160f }),
            ("dicroidium", 1.0f, true, new[] { 45f, 160f, 900f }),
            ("conifera", 0.6f, true, new[] { 50f, 180f, 1100f }),
            ("tronco_caido", 0f, true, new[] { 40f, 90f, 160f }),
            ("roca_arenisca", 0f, true, new[] { 40f, 90f, 200f }),
        };

        static List<EspecieFlora> PrepararFlora()
        {
            var lista = new List<EspecieFlora>();
            foreach (var (nombre, meceo, sombra, hasta) in Plantas)
            {
                string glb = Copiar(Path.Combine(Fns, "experiencia", "public", "assets", nombre + ".glb"), $"{Raiz}/Modelos/flora/{nombre}.glb");
                var lods = new List<string> { glb };
                foreach (var n in new[] { "lod1", "lod2" })
                    lods.Add(Copiar(Path.Combine(Datos, "lod", $"{nombre}_{n}.glb"), $"{Raiz}/Modelos/flora/{nombre}_{n}.glb"));
                AssetDatabase.Refresh();
                if (glb == null) { Anotar($"flora {nombre}: FALTA el GLB"); continue; }
                var mallas = lods.Where(x => x != null).Select(x => AssetDatabase.LoadAllAssetsAtPath(x).OfType<Mesh>().FirstOrDefault())
                                 .Where(x => x).ToArray();
                // el material es una copia del de glTFast (su shader graph de HDRP) con instanciado
                var g = MaterialDeGltf(glb);
                Material mat = null;
                if (g)
                {
                    string ruta = $"{Raiz}/Materiales/flora_{nombre}.mat";
                    AssetDatabase.DeleteAsset(ruta);
                    mat = new Material(g) { enableInstancing = true };
                    AssetDatabase.CreateAsset(mat, ruta);
                }
                lista.Add(new EspecieFlora { nombre = nombre, lods = mallas, material = mat, hasta = hasta, meceo = meceo, sombra = sombra });
                Anotar($"flora {nombre}: {mallas.Length} niveles de detalle{(mat ? "" : " · SIN material")}");
            }
            return lista;
        }

        // ------------------------------------------------------------------------------------------
        // 3. fauna con esqueleto
        // ------------------------------------------------------------------------------------------

        [Serializable]
        class InformeRig { public string especie; public float velocidad_caminar_m_s; public string[] animaciones; public string texturas; public string tipo; public float ciclo_s; }

        static List<ModeloAnimal> PrepararFauna(Mundo mundo)
        {
            var lista = new List<ModeloAnimal>();
            // Datos/fauna: los de la web · Datos/fauna_pc: los de Meshy de la PC (más detalle), que ganan
            // y pueden traer especies nuevas
            var especies = new[] { "fauna", "fauna_pc" }.Select(c => Path.Combine(Datos, c)).Where(Directory.Exists)
                                .SelectMany(Directory.GetDirectories).Select(Path.GetFileName).Distinct().OrderBy(x => x).ToList();
            if (especies.Count == 0) { Anotar("fauna: falta Datos/fauna (correr pipeline/rig_fauna.py)"); return lista; }
            foreach (var esp in especies)
            {
                string dir = Path.Combine(Datos, "fauna", esp);
                string fuente = Directory.Exists(Path.Combine(Datos, "fauna_pc", esp)) ? Path.Combine(Datos, "fauna_pc", esp) : dir;
                if (!File.Exists(Path.Combine(fuente, esp + ".json"))) { Anotar($"fauna {esp}: falta {esp}.json"); continue; }
                var rig = JsonUtility.FromJson<InformeRig>(File.ReadAllText(Path.Combine(fuente, esp + ".json")));
                string fbx = Copiar(Path.Combine(fuente, esp + ".fbx"), $"{Raiz}/Modelos/fauna/{esp}/{esp}.fbx");
                // texturas: el GLB original de Meshy que indica el informe del rig (relativo a fns2026/),
                // o el de la web si no hay
                string glbTex = null;
                if (!string.IsNullOrEmpty(rig.texturas))
                    glbTex = Copiar(Path.Combine(Fns, rig.texturas.Replace('/', Path.DirectorySeparatorChar)), $"{Raiz}/Modelos/fauna/{esp}/{esp}_texturas.glb");
                glbTex ??= Copiar(Path.Combine(Fns, "experiencia", "public", "modelos", esp + ".glb"), $"{Raiz}/Modelos/fauna/{esp}/{esp}_texturas.glb");
                AssetDatabase.Refresh();
                if (fbx == null) { Anotar($"fauna {esp}: falta el FBX"); continue; }

                var imp = (ModelImporter)AssetImporter.GetAtPath(fbx);
                imp.animationType = ModelImporterAnimationType.Generic;
                imp.importAnimation = true;
                imp.materialImportMode = ModelImporterMaterialImportMode.None;
                imp.bakeAxisConversion = true;
                imp.SaveAndReimport();
                var clips = imp.defaultClipAnimations;
                foreach (var c in clips)
                {
                    c.name = c.takeName.Contains("|") ? c.takeName.Substring(c.takeName.LastIndexOf('|') + 1) : c.takeName;
                    c.loopTime = true;
                }
                imp.clipAnimations = clips;
                imp.SaveAndReimport();

                var animaciones = AssetDatabase.LoadAllAssetsAtPath(fbx).OfType<AnimationClip>().Where(c => !c.name.StartsWith("__preview__")).ToArray();
                string rutaCtrl = $"{Raiz}/Animacion/{esp}.controller";
                AssetDatabase.DeleteAsset(rutaCtrl);
                var ctrl = AnimatorController.CreateAnimatorControllerAtPath(rutaCtrl);
                var sm = ctrl.layers[0].stateMachine;
                foreach (var clip in animaciones)
                {
                    var st = sm.AddState(clip.name);
                    st.motion = clip;
                    if (clip.name == "quieto") sm.defaultState = st;
                }

                var mat = glbTex != null ? LitDesdeGltf("piel_" + esp, glbTex, true) : null;
                var modelo = AssetDatabase.LoadAssetAtPath<GameObject>(fbx);
                var go = (GameObject)PrefabUtility.InstantiatePrefab(modelo);
                if (!go.TryGetComponent<Animator>(out var anim)) anim = go.AddComponent<Animator>();
                anim.runtimeAnimatorController = ctrl;
                anim.applyRootMotion = false;
                anim.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
                foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    if (mat) r.sharedMaterial = mat;
                    r.updateWhenOffscreen = false;
                }
                if (!go.TryGetComponent<Animal>(out _)) go.AddComponent<Animal>();
                string rutaPrefab = $"{Raiz}/Prefabs/{esp}.prefab";
                var prefab = PrefabUtility.SaveAsPrefabAsset(go, rutaPrefab);
                UnityEngine.Object.DestroyImmediate(go);
                lista.Add(new ModeloAnimal
                {
                    especie = esp, prefab = prefab, velocidad = rig.velocidad_caminar_m_s,
                    ciclo = rig.ciclo_s > 0 ? rig.ciclo_s : 1f, patas = rig.tipo == "cuadrupedo" ? 4 : 2,
                });
                Anotar($"fauna {esp}: {animaciones.Length} animaciones ({string.Join(", ", animaciones.Select(a => a.name))}), " +
                       $"camina a {rig.velocidad_caminar_m_s:0.00} m/s{(fuente != dir ? " · modelo de la PC" : "")}{(mat ? "" : " · SIN texturas")}");
            }
            return lista;
        }

        // ------------------------------------------------------------------------------------------
        // 3b. Gaussian splats horneados (pipeline/splats → Datos/splats/<capitulo>.ply + .json)
        // ------------------------------------------------------------------------------------------

        [Serializable]
        class RegionSplat
        {
            public string capitulo;
            public float[] desde_blender, hasta_blender;
            public float radio_m = 45f;
            // opcional, para splats de capturas reales (fotos/video): dónde va en Unity
            public float[] posicion, rotacion, escala;
        }

        class SplatPreparado { public string nombre; public GaussianSplatAsset asset; public RegionSplat region; }

        const BindingFlags Privado = BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public;

        static List<SplatPreparado> PrepararSplats()
        {
            var lista = new List<SplatPreparado>();
            string carpeta = Path.Combine(Datos, "splats");
            if (!Directory.Exists(carpeta)) { Anotar("splats: no hay (opcional: pipeline/splats/ENTRENAR_SPLATS)"); return lista; }
            // el creador de assets del paquete es una ventana del editor sin API pública: se usa por
            // reflexión, con los mismos pasos que su botón "Create Asset"
            var tCreador = Type.GetType("GaussianSplatting.Editor.GaussianSplatAssetCreator, GaussianSplattingEditor");
            if (tCreador == null) { Anotar("splats: falta el paquete org.nesnausk.gaussian-splatting"); return lista; }
            string salida = Raiz + "/Splats";
            foreach (var archivo in Directory.GetFiles(carpeta).Where(f => f.EndsWith(".ply") || f.EndsWith(".spz")).OrderBy(f => f))
            {
                string nombre = Path.GetFileNameWithoutExtension(archivo);
                string rutaAsset = $"{salida}/{nombre}.asset";
                string absAsset = Path.Combine(Proyecto, rutaAsset);
                // crearlo tarda (comprime y agrupa los armónicos): sólo si el .ply es más nuevo
                if (!File.Exists(absAsset) || File.GetLastWriteTimeUtc(absAsset) < File.GetLastWriteTimeUtc(archivo))
                {
                    var creador = ScriptableObject.CreateInstance(tCreador);
                    try
                    {
                        tCreador.GetField("m_InputFile", Privado).SetValue(creador, archivo);
                        tCreador.GetField("m_OutputFolder", Privado).SetValue(creador, salida);
                        tCreador.GetField("m_ImportCameras", Privado).SetValue(creador, false);
                        var fCalidad = tCreador.GetField("m_Quality", Privado);
                        fCalidad.SetValue(creador, Enum.Parse(fCalidad.FieldType, "High"));   // ~3× más chico, 58 dB
                        tCreador.GetMethod("ApplyQualityLevel", Privado).Invoke(creador, null);
                        tCreador.GetMethod("CreateAsset", Privado).Invoke(creador, null);
                        var error = tCreador.GetField("m_ErrorMessage", Privado).GetValue(creador) as string;
                        if (!string.IsNullOrEmpty(error)) { Anotar($"splat {nombre}: ERROR {error}"); continue; }
                    }
                    finally { UnityEngine.Object.DestroyImmediate(creador); }
                }
                var asset = AssetDatabase.LoadAssetAtPath<GaussianSplatAsset>(rutaAsset);
                if (!asset) { Anotar($"splat {nombre}: no se creó el asset"); continue; }
                string rutaJson = Path.Combine(carpeta, nombre + ".json");
                var region = File.Exists(rutaJson) ? JsonUtility.FromJson<RegionSplat>(File.ReadAllText(rutaJson)) : new RegionSplat();
                if (string.IsNullOrEmpty(region.capitulo)) region.capitulo = nombre;
                lista.Add(new SplatPreparado { nombre = nombre, asset = asset, region = region });
                Anotar($"splat {nombre}: capítulo {region.capitulo}, radio {region.radio_m:0} m, {new FileInfo(archivo).Length / 1048576} MB de .ply");
            }
            return lista;
        }

        /// <summary>Blender (z arriba, mano derecha) → Unity (y arriba, mano izquierda): (x, y, z) → (x, z, y).</summary>
        static Vector3 DeBlender(float[] p) => p == null || p.Length < 3 ? Vector3.zero : new Vector3(p[0], p[2], p[1]);

        static void ArmarSplats(List<SplatPreparado> splats, Transform raiz, Splats sistema)
        {
            if (splats.Count == 0) return;
            var raizSplats = new GameObject("Splats").transform;
            raizSplats.SetParent(raiz, false);
            var lista = new List<SplatCapitulo>();
            foreach (var sp in splats)
            {
                var go = new GameObject("Splat_" + sp.nombre);
                go.transform.SetParent(raizSplats, false);
                var r = sp.region;
                if (r.posicion != null && r.posicion.Length == 3)
                {
                    // captura real: viene ubicada a mano (Unity)
                    go.transform.localPosition = new Vector3(r.posicion[0], r.posicion[1], r.posicion[2]);
                    // rotación: cuaternión (x, y, z, w) de importar_en_blender.py --exportar, o ángulos de Euler
                    if (r.rotacion != null && r.rotacion.Length == 4) go.transform.localRotation = new Quaternion(r.rotacion[0], r.rotacion[1], r.rotacion[2], r.rotacion[3]);
                    else if (r.rotacion != null && r.rotacion.Length == 3) go.transform.localEulerAngles = new Vector3(r.rotacion[0], r.rotacion[1], r.rotacion[2]);
                    if (r.escala != null && r.escala.Length == 3) go.transform.localScale = new Vector3(r.escala[0], r.escala[1], r.escala[2]);
                }
                else
                {
                    // horneado de Blender: el mismo mundo, sólo cambian los ejes. Rotar -90° en X y
                    // espejar Y lleva (x, y, z) de Blender a (x, z, y) de Unity
                    go.transform.localRotation = Quaternion.Euler(-90f, 0f, 0f);
                    go.transform.localScale = new Vector3(1f, -1f, 1f);
                }
                var gs = go.AddComponent<GaussianSplatRenderer>();
                gs.m_Asset = sp.asset;
                go.SetActive(false);
                lista.Add(new SplatCapitulo
                {
                    capitulo = r.capitulo, splat = gs, radio = r.radio_m,
                    desde = DeBlender(r.desde_blender), hasta = DeBlender(r.hasta_blender),
                });
            }
            sistema.capitulos = lista.ToArray();

            // el pase de HDRP que los dibuja: después del posproceso (los splats ya traen el look de
            // Cycles; antes, la exposición automática de HDRP los quemaba o los apagaba)
            var tPase = Type.GetType("GaussianSplatting.Runtime.GaussianSplatHDRPPass, GaussianSplatting");
            if (tPase == null) { Anotar("splats: no encuentro GaussianSplatHDRPPass (¿falta GS_ENABLE_HDRP?)"); return; }
            var volumen = new GameObject("Splats_pase_HDRP").AddComponent<CustomPassVolume>();
            volumen.isGlobal = true;
            volumen.injectionPoint = CustomPassInjectionPoint.AfterPostProcess;
            volumen.AddPassOfType(tPase);
            Anotar($"splats: {lista.Count} en la escena ({string.Join(", ", lista.Select(x => x.capitulo))})");
        }

        // ------------------------------------------------------------------------------------------
        // 3c. sonido (pipeline/sonido/sonido_triasico.py → Datos/sonido/*.ogg)
        // ------------------------------------------------------------------------------------------

        // qué pisadas usa cada especie (por su peso)
        static readonly Dictionary<string, string> PesoEspecie = new Dictionary<string, string>
        {
            { "eoraptor", "liviano" }, { "eodromaeus", "liviano" }, { "pisanosaurus", "liviano" }, { "panphagia", "liviano" },
            { "hyperodapedon", "liviano" }, { "exaeretodon", "medio" }, { "chromogisaurus", "medio" }, { "sanjuansaurus", "medio" },
            { "herrerasaurus", "pesado" }, { "ischigualastia", "pesado" }, { "saurosuchus", "pesado" },
        };

        static void ArmarSonido(GameObject sistemas, Director director, Fauna fauna, Ambiente ambiente, Transform carro)
        {
            // el oído de la sala: a la altura de los ojos (sin él Unity no suena)
            var oido = new GameObject("Oido");
            oido.transform.SetParent(carro, false);
            oido.transform.localPosition = new Vector3(0, 1.6f, 0);
            oido.AddComponent<AudioListener>();

            string carpeta = Path.Combine(Datos, "sonido");
            if (!Directory.Exists(carpeta)) { Anotar("sonido: falta Datos/sonido (correr pipeline/sonido/sonido_triasico.py)"); return; }
            var clips = new Dictionary<string, AudioClip>();
            foreach (var archivo in Directory.GetFiles(carpeta, "*.ogg"))
            {
                string nombre = Path.GetFileNameWithoutExtension(archivo);
                string ruta = Copiar(archivo, $"{Raiz}/Sonido/{nombre}.ogg");
                AssetDatabase.ImportAsset(ruta);
                var imp = (AudioImporter)AssetImporter.GetAtPath(ruta);
                var cfg = imp.defaultSampleSettings;
                bool largo = nombre.StartsWith("ambiente_") || nombre == "volcan";
                // los loops largos se leen del disco de a poco; los cortos, ya descomprimidos (sin demora)
                cfg.loadType = largo ? AudioClipLoadType.Streaming : AudioClipLoadType.DecompressOnLoad;
                cfg.compressionFormat = AudioCompressionFormat.Vorbis;
                cfg.quality = 0.7f;
                imp.defaultSampleSettings = cfg;
                imp.SaveAndReimport();
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(ruta);
                if (clip) clips[nombre] = clip;
            }
            var son = sistemas.AddComponent<Sonido>();
            son.ambiente = ambiente;
            son.ambientes = clips.Where(kv => kv.Key.StartsWith("ambiente_")).Select(kv => kv.Value).ToArray();
            clips.TryGetValue("volcan", out son.volcan);
            son.volcanEn = ambiente.columnaVolcan ? ambiente.columnaVolcan.transform : null;
            son.especies = PesoEspecie.Select(kv => new SonidoEspecie
            {
                especie = kv.Key, peso = kv.Value,
                voces = clips.Where(c => c.Key.StartsWith($"voz_{kv.Key}_")).OrderBy(c => c.Key).Select(c => c.Value).ToArray(),
            }).ToArray();
            son.pisadas = new[] { "liviano", "medio", "pesado" }.Select(p => new PisadasPeso
            {
                peso = p,
                barro = clips.Where(c => c.Key.StartsWith($"pisada_{p}_barro_")).Select(c => c.Value).ToArray(),
                seco = clips.Where(c => c.Key.StartsWith($"pisada_{p}_seco_")).Select(c => c.Value).ToArray(),
            }).ToArray();
            director.sonido = son;
            fauna.sonido = son;
            Anotar($"sonido: {clips.Count} clips ({son.ambientes.Length} ambientes, {son.especies.Count(e => e.voces.Length > 0)} especies con voz)");
        }

        // ------------------------------------------------------------------------------------------
        // 4. suelos y terrenos
        // ------------------------------------------------------------------------------------------

        [Serializable] class CapaInfo { public string nombre; public float mundo_m; }
        [Serializable] class IndiceCapas { public CapaInfo[] capas; }
        [Serializable] class ValleReal { public Paleta paleta_albedo_lineal; }
        [Serializable] class Paleta { public float[] arcilla_gris, arcilla_clara, estratos, ripio; }

        // de qué carpeta CC0 de Poly Haven sale cada capa (bajar_texturas_cc0.py) y con qué tinte
        static readonly Dictionary<string, (string rol, Color tinte)> Cc0 = new Dictionary<string, (string, Color)>
        {
            { "barro", ("barro", Color.white) }, { "barro_humedo", ("barro", new Color(0.55f, 0.5f, 0.45f)) },
            { "arena", ("arena", Color.white) }, { "hojarasca", ("hojarasca", Color.white) },
            { "loma", ("roca", new Color(1.1f, 0.78f, 0.62f)) }, { "basalto", ("roca", new Color(0.35f, 0.34f, 0.33f)) },
            { "arcilla_gris", ("arcilla", Color.white) }, { "arcilla_clara", ("arcilla", new Color(1.12f, 1.1f, 1.05f)) },
            { "estratos", ("roca", new Color(1.15f, 0.62f, 0.45f)) },
        };

        static Dictionary<string, TerrainLayer> PrepararSuelos()
        {
            var capas = new Dictionary<string, TerrainLayer>();
            string dirSuelo = Path.Combine(Datos, "suelo");
            var paleta = File.Exists(Path.Combine(Datos, "valle_real.json"))
                ? JsonUtility.FromJson<ValleReal>(File.ReadAllText(Path.Combine(Datos, "valle_real.json"))).paleta_albedo_lineal : null;
            foreach (var archivo in Directory.GetFiles(dirSuelo, "*_color.jpg"))
            {
                string nombre = Path.GetFileName(archivo).Replace("_color.jpg", "");
                float metros = 3f;
                string col = archivo, nor = Path.Combine(dirSuelo, nombre + "_normal.jpg"), hra = Path.Combine(dirSuelo, nombre + "_hra.jpg");
                string rug = null, desplaz = null;
                Color tinte = Color.white;
                // ¿hay escaneadas CC0 en la PC? (escenas/hiperreal/texturas_cc0/<rol>/)
                if (Cc0.TryGetValue(nombre, out var cc))
                {
                    string d = Path.Combine(Fns, "escenas", "hiperreal", "texturas_cc0", cc.rol);
                    string c2 = new[] { "color.jpg", "color.png" }.Select(x => Path.Combine(d, x)).FirstOrDefault(File.Exists);
                    if (c2 != null)
                    {
                        col = c2;
                        nor = new[] { "normal.jpg", "normal.png" }.Select(x => Path.Combine(d, x)).FirstOrDefault(File.Exists) ?? nor;
                        rug = new[] { "rugosidad.jpg", "rugosidad.png" }.Select(x => Path.Combine(d, x)).FirstOrDefault(File.Exists);
                        desplaz = new[] { "desplaz.jpg", "desplaz.png" }.Select(x => Path.Combine(d, x)).FirstOrDefault(File.Exists);
                        tinte = cc.tinte;
                        metros = 2.5f;
                        Anotar($"suelo {nombre}: textura ESCANEADA CC0 ({cc.rol})");
                    }
                }
                // cuántos metros cubre una vuelta de la textura procedural (capas.json de texturas_suelo.py)
                string idx = Path.Combine(dirSuelo, "capas.json");
                if (rug == null && File.Exists(idx))
                {
                    var info = Array.Find(JsonUtility.FromJson<IndiceCapas>(File.ReadAllText(idx)).capas ?? new CapaInfo[0], c => c.nombre == nombre);
                    if (info != null && info.mundo_m > 0) metros = info.mundo_m;
                }
                string dest = $"{Raiz}/Suelo/{nombre}";
                string aCol = Copiar(col, $"{dest}/{nombre}_color{Path.GetExtension(col)}");
                string aNor = Copiar(nor, $"{dest}/{nombre}_normal{Path.GetExtension(nor)}");
                string aHra = rug == null ? Copiar(hra, $"{dest}/{nombre}_hra.jpg") : null;
                string aRug = rug != null ? Copiar(rug, $"{dest}/{nombre}_rugosidad{Path.GetExtension(rug)}") : null;
                string aDes = desplaz != null ? Copiar(desplaz, $"{dest}/{nombre}_desplaz{Path.GetExtension(desplaz)}") : null;
                AssetDatabase.Refresh();
                Importar(aCol, TextureImporterType.Default, true, false);
                Importar(aNor, TextureImporterType.NormalMap, false, false);
                foreach (var x in new[] { aHra, aRug, aDes }) if (x != null) Importar(x, TextureImporterType.Default, false, true);

                // máscara HDRP: R metal 0, G oclusión, B altura (mezcla por altura), A lisura
                Texture2D masc;
                if (aHra != null)
                {
                    var t = AssetDatabase.LoadAssetAtPath<Texture2D>(aHra);
                    var px = t.GetPixels32();
                    masc = Mascara($"{dest}/{nombre}_mascara.png", t.width, t.height, i => (0f, px[i].g / 255f, px[i].r / 255f, 1f - px[i].b / 255f));
                }
                else
                {
                    var tr = AssetDatabase.LoadAssetAtPath<Texture2D>(aRug);
                    var pr = tr.GetPixels32();
                    Color32[] pd = aDes != null ? AssetDatabase.LoadAssetAtPath<Texture2D>(aDes).GetPixels32() : null;
                    bool igual = pd != null && pd.Length == pr.Length;
                    masc = Mascara($"{dest}/{nombre}_mascara.png", tr.width, tr.height, i => (0f, 1f, igual ? pd[i].r / 255f : 0.5f, 1f - pr[i].r / 255f));
                }
                // las capas de hoy toman el color real medido en el satélite (si está)
                var objetivo = paleta == null ? null : nombre switch
                {
                    "arcilla_gris" => paleta.arcilla_gris, "arcilla_clara" => paleta.arcilla_clara,
                    "estratos" => paleta.estratos, "ripio" => paleta.ripio, _ => null,
                };
                var texCol = AssetDatabase.LoadAssetAtPath<Texture2D>(aCol);
                if (objetivo != null && texCol)
                {
                    Color media = ColorMedio(texCol);
                    tinte = new Color(Mathf.Clamp(objetivo[0] / Mathf.Max(0.02f, media.r), 0.3f, 2f),
                                      Mathf.Clamp(objetivo[1] / Mathf.Max(0.02f, media.g), 0.3f, 2f),
                                      Mathf.Clamp(objetivo[2] / Mathf.Max(0.02f, media.b), 0.3f, 2f));
                }
                string rutaCapa = $"{dest}/{nombre}.terrainlayer";
                var capa = AssetDatabase.LoadAssetAtPath<TerrainLayer>(rutaCapa);
                if (!capa) { capa = new TerrainLayer(); AssetDatabase.CreateAsset(capa, rutaCapa); }
                capa.diffuseTexture = texCol;
                capa.normalMapTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(aNor);
                capa.maskMapTexture = masc;
                capa.tileSize = new Vector2(metros, metros);
                capa.normalScale = 1f;
                capa.diffuseRemapMin = Vector4.zero;
                capa.diffuseRemapMax = new Vector4(tinte.r, tinte.g, tinte.b, 1f);
                capa.maskMapRemapMin = Vector4.zero;
                capa.maskMapRemapMax = Vector4.one;
                EditorUtility.SetDirty(capa);
                capas[nombre] = capa;
            }
            AssetDatabase.SaveAssets();
            Anotar($"suelo: {capas.Count} capas ({string.Join(", ", capas.Keys)})");
            return capas;
        }

        static void Importar(string ruta, TextureImporterType tipo, bool srgb, bool legible)
        {
            if (ruta == null) return;
            var imp = (TextureImporter)AssetImporter.GetAtPath(ruta);
            imp.textureType = tipo;
            imp.sRGBTexture = srgb;
            imp.isReadable = legible;
            imp.mipmapEnabled = true;
            imp.anisoLevel = 8;
            imp.maxTextureSize = 4096;
            imp.SaveAndReimport();
        }

        /// <summary>Color medio de una textura, en lineal (para igualarlo al albedo del satélite).</summary>
        static Color ColorMedio(Texture2D t)
        {
            var px = Pixeles(t, 64, 64, false);
            double r = 0, g = 0, b = 0;
            foreach (var p in px) { r += Mathf.GammaToLinearSpace(p.r / 255f); g += Mathf.GammaToLinearSpace(p.g / 255f); b += Mathf.GammaToLinearSpace(p.b / 255f); }
            return new Color((float)(r / px.Length), (float)(g / px.Length), (float)(b / px.Length));
        }

        static Material MaterialTerreno(bool mezclaPorAltura)
        {
            string ruta = $"{Raiz}/Materiales/terreno_{(mezclaPorAltura ? "altura" : "simple")}.mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(ruta);
            if (!m) { m = new Material(Shader.Find("HDRP/TerrainLit")); AssetDatabase.CreateAsset(m, ruta); }
            // la mezcla por altura (la arena se mete en las grietas, las piedras asoman) sólo va con ≤ 4 capas
            m.SetFloat("_EnableHeightBlend", mezclaPorAltura ? 1f : 0f);
            m.SetFloat("_HeightTransition", 0.25f);
            HDMaterial.ValidateMaterial(m);
            EditorUtility.SetDirty(m);
            return m;
        }

        static Terrain CrearTerreno(Terreno t, Dictionary<string, TerrainLayer> capas, Transform padre)
        {
            string rutaAlt = Path.Combine(Datos, t.alturas.Replace('/', Path.DirectorySeparatorChar));
            if (!File.Exists(rutaAlt)) { Anotar($"terreno {t.nombre}: FALTA {t.alturas}"); return null; }
            var td = new TerrainData { heightmapResolution = t.res };
            td.size = new Vector3(t.lado, Mathf.Max(1f, t.hmax - t.hmin), t.lado);
            td.SetHeights(0, 0, Alturas.Decodificar(Gunzip(rutaAlt), t.res));

            var lista = t.capas.Select(c => capas.TryGetValue(c, out var l) ? l : null).ToArray();
            if (lista.All(x => x))
            {
                td.terrainLayers = lista;
                // las capas vienen en PNG RGBA de 4 en 4; la resolución de alphamap tiene que ser potencia de 2
                int res = Mathf.ClosestPowerOfTwo(t.capas_res - 1 > 0 ? t.capas_res - 1 : t.capas_res);
                res = Mathf.Clamp(res, 16, 2048);
                td.alphamapResolution = res;
                int L = lista.Length;
                var am = new float[res, res, L];
                for (int k = 0; k < t.capas_png.Length; k++)
                {
                    var png = new Texture2D(2, 2, TextureFormat.RGBA32, false, true);
                    png.LoadImage(File.ReadAllBytes(Path.Combine(Datos, t.capas_png[k].Replace('/', Path.DirectorySeparatorChar))));
                    var px = png.GetPixels32();
                    int w = png.width;
                    for (int j = 0; j < res; j++)
                        for (int i = 0; i < res; i++)
                        {
                            var p = px[(j * (png.height - 1) / (res - 1)) * w + i * (w - 1) / (res - 1)];
                            for (int c = 0; c < 4 && k * 4 + c < L; c++)
                                am[j, i, k * 4 + c] = c == 0 ? p.r / 255f : c == 1 ? p.g / 255f : c == 2 ? p.b / 255f : p.a / 255f;
                        }
                    UnityEngine.Object.DestroyImmediate(png);
                }
                for (int j = 0; j < res; j++)
                    for (int i = 0; i < res; i++)
                    {
                        float s = 0;
                        for (int c = 0; c < L; c++) s += am[j, i, c];
                        if (s < 1e-4f) { am[j, i, 0] = 1; continue; }
                        for (int c = 0; c < L; c++) am[j, i, c] /= s;
                    }
                td.SetAlphamaps(0, 0, am);
            }
            else Anotar($"terreno {t.nombre}: faltan capas de suelo ({string.Join(", ", t.capas)})");
            string ruta = $"{Raiz}/Terrenos/{t.nombre}.asset";
            AssetDatabase.DeleteAsset(ruta);
            AssetDatabase.CreateAsset(td, ruta);
            var go = Terrain.CreateTerrainGameObject(td);
            go.name = "terreno_" + t.nombre;
            go.transform.SetParent(padre, false);
            go.transform.position = new Vector3(t.x0, t.hmin, t.z0);
            var ter = go.GetComponent<Terrain>();
            bool cerca = t.cual == "cerca";
            ter.materialTemplate = MaterialTerreno(t.capas.Length <= 4);
            ter.heightmapPixelError = cerca ? 2f : 5f;
            ter.basemapDistance = cerca ? 400f : 3000f;
            ter.drawInstanced = true;
            ter.allowAutoConnect = false;
            ter.groupingID = cerca ? 1 : 2;
            ter.treeDistance = 0;
            ter.detailObjectDistance = 0;
            Anotar($"terreno {t.nombre}: {t.lado:0} m a {t.lado / (t.res - 1):0.##} m por muestra, alturas {t.hmin:0.#} a {t.hmax:0.#}");
            return ter;
        }

        [Serializable] class MallaJson { public float[] vertices; public float[] uv; public int[] triangulos; }

        static Mesh MallaDesdeJson(string nombre, string rutaGz)
        {
            if (!File.Exists(rutaGz)) return null;
            var d = JsonUtility.FromJson<MallaJson>(Encoding.UTF8.GetString(Gunzip(rutaGz)));
            int n = d.vertices.Length / 3;
            var v = new Vector3[n];
            for (int i = 0; i < n; i++) v[i] = new Vector3(d.vertices[3 * i], d.vertices[3 * i + 1], d.vertices[3 * i + 2]);
            var m = new Mesh { name = nombre, indexFormat = n > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
            m.vertices = v;
            if (d.uv != null && d.uv.Length == 2 * n)
            {
                var uv = new Vector2[n];
                for (int i = 0; i < n; i++) uv[i] = new Vector2(d.uv[2 * i], d.uv[2 * i + 1]);
                m.uv = uv;
            }
            m.triangles = d.triangulos;
            m.RecalculateNormals();
            m.RecalculateTangents();
            m.RecalculateBounds();
            string ruta = $"{Raiz}/Mallas/{nombre}.asset";
            AssetDatabase.DeleteAsset(ruta);
            AssetDatabase.CreateAsset(m, ruta);
            return m;
        }

        // ------------------------------------------------------------------------------------------
        // 5. escena
        // ------------------------------------------------------------------------------------------

        static void ArmarEscena(Mundo mundo, List<EspecieFlora> flora, List<ModeloAnimal> fauna, Dictionary<string, TerrainLayer> capas,
                                List<SplatPreparado> splats)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var raizTri = new GameObject("Era_Triasico");
            var raizHoy = new GameObject("Era_Hoy");

            var suelosTri = new List<Terrain>();
            var suelosHoy = new List<Terrain>();
            // el fino primero: Director.Suelo toma el primero que cubre el punto
            foreach (var t in mundo.terrenos.OrderBy(x => x.cual == "cerca" ? 0 : 1))
            {
                var ter = CrearTerreno(t, capas, t.era == "hoy" ? raizHoy.transform : raizTri.transform);
                if (ter) (t.era == "hoy" ? suelosHoy : suelosTri).Add(ter);
            }

            // el paredón de las Barrancas Coloradas: malla con estratos horizontales (triplanar)
            var paredon = MallaDesdeJson("paredon", Path.Combine(Datos, "valle", "paredon.json.gz"));
            if (paredon && capas.TryGetValue("estratos", out var est))
            {
                var mat = Lit("paredon_estratos", est.diffuseTexture, est.normalMapTexture, est.maskMapTexture,
                              new Color(est.diffuseRemapMax.x, est.diffuseRemapMax.y, est.diffuseRemapMax.z), true, true, 18f);
                var go = new GameObject("paredon_barrancas_coloradas", typeof(MeshFilter), typeof(MeshRenderer));
                go.transform.SetParent(raizHoy.transform, false);
                go.GetComponent<MeshFilter>().sharedMesh = paredon;
                go.GetComponent<MeshRenderer>().sharedMaterial = mat;
                go.isStatic = true;
                Anotar($"paredón: {paredon.vertexCount:N0} vértices");
            }
            LugaresDeHoy(raizHoy.transform, suelosHoy, capas);

            // sol
            var solGo = new GameObject("Sol");
            var sol = solGo.AddComponent<Light>();
            sol.type = LightType.Directional;
            sol.shadows = LightShadows.Soft;
            sol.intensity = 120000f;
            if (!solGo.TryGetComponent<HDAdditionalLightData>(out var hdSol)) hdSol = solGo.AddComponent<HDAdditionalLightData>();
            hdSol.angularDiameter = 0.53f;
            hdSol.SetShadowResolution(4096);

            // volumen global con todo el aire y el color
            var perfil = PerfilVolumen();
            var volGo = new GameObject("Volumen");
            var vol = volGo.AddComponent<Volume>();
            vol.isGlobal = true;
            vol.sharedProfile = perfil;

            // el río (sistema de agua de HDRP): sólo en el Triásico
            WaterSurface rio = null;
            {
                var go = new GameObject("Rio");
                go.transform.SetParent(raizTri.transform, false);
                go.transform.position = new Vector3(-43f, mundo.nivel_agua, 0f);
                go.transform.localScale = new Vector3(366f, 1f, 512f);
                rio = go.AddComponent<WaterSurface>();
                rio.surfaceType = WaterSurfaceType.River;
                rio.geometryType = WaterGeometryType.Quad;
                rio.timeMultiplier = 1f;
                // río de llanura cargado de barro: turbio, pardo verdoso, se ve poco el fondo
                rio.refractionColor = new Color(0.36f, 0.33f, 0.2f);
                rio.scatteringColor = new Color(0.22f, 0.2f, 0.11f);
                rio.absorptionDistance = 0.8f;
                rio.maxRefractionDistance = 0.6f;
                rio.largeWindSpeed = 8f;
                rio.largeCurrentSpeedValue = 2.5f;
                rio.largeOrientationValue = 90f;
                rio.ripplesWindSpeed = 5f;
                rio.caustics = false;
                rio.startSmoothness = 0.93f;
                rio.endSmoothness = 0.8f;
            }

            // sala, cámaras y sistemas
            var carro = new GameObject("Sala").transform;
            var camGo = new GameObject("camara_plantilla", typeof(Camera));
            camGo.transform.SetParent(carro, false);
            var cam = camGo.GetComponent<Camera>();
            cam.nearClipPlane = 0.05f;
            cam.farClipPlane = 12000f;
            var hdCam = camGo.AddComponent<HDAdditionalCameraData>();
            hdCam.antialiasing = HDAdditionalCameraData.AntialiasingMode.TemporalAntialiasing;
            hdCam.TAAQuality = HDAdditionalCameraData.TAAQualityLevel.High;
            camGo.tag = "MainCamera";

            var sistemas = new GameObject("FNS");
            var sensores = sistemas.AddComponent<Sensores>();
            var sala = carro.gameObject.AddComponent<Sala>();
            sala.plantilla = cam;
            sala.sensores = sensores;
            var ambiente = sistemas.AddComponent<Ambiente>();
            var interfaz = sistemas.AddComponent<Interfaz>();
            var director = sistemas.AddComponent<Director>();
            var faunaC = sistemas.AddComponent<Fauna>();
            var calidad = sistemas.AddComponent<Calidad>();
            var arranque = sistemas.AddComponent<Arranque>();
            var capturas = sistemas.AddComponent<Capturas>();

            director.mundoJson = AssetDatabase.LoadAssetAtPath<TextAsset>(Raiz + "/Datos/mundo.json");
            director.carro = carro;
            director.sala = sala;
            director.sensores = sensores;
            director.ambiente = ambiente;
            director.fauna = faunaC;
            director.interfaz = interfaz;
            director.suelosTriasico = suelosTri.ToArray();
            director.suelosHoy = suelosHoy.ToArray();
            faunaC.director = director;
            faunaC.modelos = fauna.ToArray();
            ambiente.sol = sol;
            ambiente.volumen = vol;
            ambiente.eraTriasico = raizTri;
            ambiente.eraHoy = raizHoy;
            ambiente.rio = rio;
            ambiente.seguir = carro;
            calidad.volumen = vol;
            arranque.sensores = sensores;
            arranque.sala = sala;
            arranque.interfaz = interfaz;
            arranque.calidad = calidad;
            capturas.director = director;
            capturas.calidad = calidad;

            // vegetación por era
            var vegs = new List<Vegetacion>();
            foreach (var (era, raiz) in new[] { ("triasico", raizTri), ("hoy", raizHoy) })
            {
                var datos = AssetDatabase.LoadAssetAtPath<TextAsset>($"{Raiz}/Datos/flora_{era}.json");
                if (!datos) continue;
                var go = new GameObject("Vegetacion_" + era);
                go.transform.SetParent(raiz.transform, false);
                var v = go.AddComponent<Vegetacion>();
                v.datos = datos;
                v.especies = flora.ToArray();
                v.centro = carro;
                vegs.Add(v);
            }
            calidad.vegetacion = vegs.ToArray();

            var splatsC = sistemas.AddComponent<Splats>();
            splatsC.vegetaciones = vegs.ToArray();
            director.splats = splatsC;
            ArmarSplats(splats, raizTri.transform, splatsC);

            Volcan(mundo, raizTri.transform, ambiente);
            ArmarSonido(sistemas, director, faunaC, ambiente, carro);
            Ceniza(ambiente);
            SalidaVideo(sistemas, arranque);

            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(), Escena);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(Escena, true) };
            AssetDatabase.SaveAssets();
            Anotar("escena guardada: " + Escena);
        }

        static VolumeProfile PerfilVolumen()
        {
            string ruta = Raiz + "/Render/Perfil_ParqueTriasico.asset";
            AssetDatabase.DeleteAsset(ruta);
            var p = ScriptableObject.CreateInstance<VolumeProfile>();
            AssetDatabase.CreateAsset(p, ruta);
            T Agregar<T>() where T : VolumeComponent
            {
                var c = p.Add<T>(false);
                c.name = typeof(T).Name;
                AssetDatabase.AddObjectToAsset(c, p);
                return c;
            }
            var ve = Agregar<VisualEnvironment>();
            ve.skyType.Override((int)SkyType.PhysicallyBased);
            ve.skyAmbientMode.Override(SkyAmbientMode.Dynamic);
            Agregar<PhysicallyBasedSky>();
            var nubes = Agregar<VolumetricClouds>();
            nubes.enable.Override(true);
            nubes.cloudControl.Override(VolumetricClouds.CloudControl.Simple);
            nubes.cloudSimpleMode.Override(VolumetricClouds.CloudSimpleMode.Quality);
            nubes.shadows.Override(true);
            var fog = Agregar<Fog>();
            fog.enabled.Override(true);
            fog.enableVolumetricFog.Override(true);
            fog.meanFreePath.Override(600f);
            fog.baseHeight.Override(0f);
            fog.maximumHeight.Override(300f);
            fog.maxFogDistance.Override(9000f);
            fog.anisotropy.Override(0.55f);
            fog.depthExtent.Override(140f);
            fog.volumeSliceCount.Override(80);
            fog.albedo.Override(Color.white);
            var ex = Agregar<Exposure>();
            ex.mode.Override(ExposureMode.AutomaticHistogram);
            ex.limitMin.Override(5f);
            ex.limitMax.Override(16f);
            ex.compensation.Override(0f);
            Agregar<Tonemapping>().mode.Override(TonemappingMode.ACES);
            var bloom = Agregar<Bloom>();
            bloom.intensity.Override(0.12f);
            bloom.scatter.Override(0.6f);
            Agregar<GlobalIllumination>().enable.Override(true);
            Agregar<ScreenSpaceReflection>().enabled.Override(true);
            var ao = Agregar<ScreenSpaceAmbientOcclusion>();
            ao.intensity.Override(1.1f);
            ao.radius.Override(1.5f);
            var cs = Agregar<ContactShadows>();
            cs.enable.Override(true);
            cs.length.Override(0.25f);
            var sh = Agregar<HDShadowSettings>();
            sh.maxShadowDistance.Override(350f);
            var ca = Agregar<ColorAdjustments>();
            ca.postExposure.Override(0f);
            ca.saturation.Override(16f);
            ca.contrast.Override(14f);
            Agregar<WhiteBalance>().temperature.Override(-6f);
            var grano = Agregar<FilmGrain>();
            grano.intensity.Override(0.08f);
            var vi = Agregar<Vignette>();
            vi.intensity.Override(0.12f);
            Agregar<MotionBlur>().intensity.Override(0.25f);
            EditorUtility.SetDirty(p);
            AssetDatabase.SaveAssets();
            return p;
        }

        static Texture2D TexturaHumo(string nombre, int n, float borde, float semilla)
        {
            string ruta = $"{Raiz}/Texturas/{nombre}.png";
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false);
            for (int j = 0; j < n; j++)
                for (int i = 0; i < n; i++)
                {
                    float x = (i + 0.5f) / n * 2 - 1, y = (j + 0.5f) / n * 2 - 1;
                    float r = Mathf.Sqrt(x * x + y * y);
                    float ruido = 0;
                    for (int o = 0, f = 3; o < 4; o++, f *= 2) ruido += Mathf.PerlinNoise(i * f / (float)n + semilla, j * f / (float)n + semilla * 2) / (1 << o);
                    float a = Mathf.Clamp01((1 - r) / borde) * Mathf.Clamp01(ruido * 1.1f - 0.35f);
                    t.SetPixel(i, j, new Color(1, 1, 1, a));
                }
            t.Apply();
            File.WriteAllBytes(Path.Combine(Proyecto, ruta), t.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(t);
            AssetDatabase.ImportAsset(ruta);
            var imp = (TextureImporter)AssetImporter.GetAtPath(ruta);
            imp.alphaIsTransparency = true;
            imp.SaveAndReimport();
            return AssetDatabase.LoadAssetAtPath<Texture2D>(ruta);
        }

        static ParticleSystem Particulas(string nombre, Transform padre, Material mat)
        {
            var go = new GameObject(nombre);
            go.transform.SetParent(padre, false);
            var ps = go.AddComponent<ParticleSystem>();
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = mat;
            return ps;
        }

        static void Volcan(Mundo mundo, Transform raiz, Ambiente amb)
        {
            var humo = TexturaHumo("humo", 256, 0.45f, 3.1f);
            var mat = Lit("humo_volcan", humo, null, null, new Color(0.42f, 0.39f, 0.36f), true, false, 20f, true);
            var crater = new Vector3(mundo.volcan[0], mundo.volcan[1], mundo.volcan[2]);
            var ps = Particulas("columna_volcan", raiz, mat);
            ps.transform.position = crater;
            ps.transform.rotation = Quaternion.Euler(-90f, 0, 0);
            var main = ps.main;
            main.startLifetime = 70f;
            main.startSpeed = new ParticleSystem.MinMaxCurve(10f, 18f);
            main.startSize = new ParticleSystem.MinMaxCurve(90f, 180f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
            main.maxParticles = 600;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.prewarm = true;
            var em = ps.emission;
            em.rateOverTime = 3f;
            var sh = ps.shape;
            sh.shapeType = ParticleSystemShapeType.Cone;
            sh.angle = 8f;
            sh.radius = 60f;
            // el viento de altura inclina la pluma (como en Blender: 16°)
            var vel = ps.velocityOverLifetime;
            vel.enabled = true;
            vel.space = ParticleSystemSimulationSpace.World;
            vel.x = new ParticleSystem.MinMaxCurve(6f, 9f);
            vel.y = new ParticleSystem.MinMaxCurve(0f, 0f);
            vel.z = new ParticleSystem.MinMaxCurve(0f, 0f);
            var tam = ps.sizeOverLifetime;
            tam.enabled = true;
            tam.size = new ParticleSystem.MinMaxCurve(1f, AnimationCurve.Linear(0, 0.6f, 1, 3.2f));
            var col = ps.colorOverLifetime;
            col.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(new Color(0.35f, 0.32f, 0.3f), 0), new GradientColorKey(new Color(0.6f, 0.57f, 0.53f), 1) },
                      new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(0.85f, 0.1f), new GradientAlphaKey(0.6f, 0.7f), new GradientAlphaKey(0, 1) });
            col.color = g;
            var rot = ps.rotationOverLifetime;
            rot.enabled = true;
            rot.z = new ParticleSystem.MinMaxCurve(-0.05f, 0.05f);
            amb.columnaVolcan = ps;

            var brillo = new GameObject("brillo_volcan").AddComponent<Light>();
            brillo.transform.SetParent(raiz, false);
            brillo.transform.position = crater + Vector3.up * 30f;
            brillo.type = LightType.Point;
            brillo.color = new Color(1f, 0.45f, 0.15f);
            brillo.range = 4000f;
            if (!brillo.TryGetComponent<HDAdditionalLightData>(out _)) brillo.gameObject.AddComponent<HDAdditionalLightData>();
            amb.brilloVolcan = brillo;
        }

        static void Ceniza(Ambiente amb)
        {
            var punto = TexturaHumo("copo", 32, 0.9f, 7.7f);
            var mat = Lit("ceniza_copo", punto, null, null, new Color(0.62f, 0.6f, 0.57f), true, false, 20f, true);
            var ps = Particulas("ceniza_cae", null, mat);
            var main = ps.main;
            main.startLifetime = 14f;
            main.startSpeed = 0f;
            main.startSize = new ParticleSystem.MinMaxCurve(0.015f, 0.05f);
            main.maxParticles = 60000;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.gravityModifier = 0.04f;
            var em = ps.emission;
            em.rateOverTime = 0f;
            var sh = ps.shape;
            sh.shapeType = ParticleSystemShapeType.Box;
            sh.scale = new Vector3(70f, 1f, 70f);
            var ruido = ps.noise;
            ruido.enabled = true;
            ruido.strength = 0.6f;
            ruido.frequency = 0.3f;
            amb.cenizaCae = ps;

            var polvo = TexturaHumo("polvo", 64, 0.6f, 1.3f);
            var matPolvo = Lit("polvo_pisada", polvo, null, null, new Color(0.55f, 0.45f, 0.35f), true, false, 20f, true);
            var pp = Particulas("polvo_pisada", null, matPolvo);
            var m2 = pp.main;
            m2.startLifetime = 2.5f;
            m2.startSpeed = new ParticleSystem.MinMaxCurve(0.4f, 1.6f);
            m2.startSize = new ParticleSystem.MinMaxCurve(0.2f, 0.7f);
            m2.loop = false;
            m2.playOnAwake = false;
            var e2 = pp.emission;
            e2.rateOverTime = 0f;
            var s2 = pp.shape;
            s2.shapeType = ParticleSystemShapeType.Hemisphere;
            s2.radius = 0.4f;
            amb.polvoPisada = pp;

            // calco de ceniza sobre el suelo alrededor de la sala (se espesa en el capítulo de la ceniza)
            var tc = TexturaHumo("ceniza_suelo", 512, 0.02f, 4.4f);
            var md = new Material(Shader.Find("HDRP/Decal"));
            md.SetTexture("_BaseColorMap", tc);
            md.SetColor("_BaseColor", new Color(0.55f, 0.53f, 0.5f, 1f));
            HDMaterial.ValidateMaterial(md);
            AssetDatabase.CreateAsset(md, $"{Raiz}/Materiales/ceniza_suelo.mat");
            var dgo = new GameObject("ceniza_suelo");
            dgo.transform.rotation = Quaternion.Euler(90f, 0f, 0f);
            var dp = dgo.AddComponent<DecalProjector>();
            dp.material = md;
            dp.size = new Vector3(240f, 240f, 60f);
            dp.uvScale = new Vector2(60f, 60f);
            dp.fadeFactor = 0f;
            amb.cenizaSuelo = dp;
        }

        [Serializable] class InfoHunyuan { public bool textura; }

        static void LugaresDeHoy(Transform raiz, List<Terrain> suelos, Dictionary<string, TerrainLayer> capas)
        {
            // los modelos de los lugares, si están en esta máquina: de Meshy (correr_todo.py) o de
            // Hunyuan3D-2 (pipeline/hunyuan/hunyuan_lote.py, desde fotos propias).
            // UBICACIÓN APROXIMADA: no hay coordenadas públicas de cada formación; van a la vista del recorrido.
            // largo: la medida mayor real (pipeline/lista_modelos.json); capa: la roca de su material
            var lugares = new (string nombre, string[] rutas, Vector3 pos, float giro, float largo, string capa)[]
            {
                ("el_hongo", new[] { Path.Combine(Fns, "modelos", "el_hongo", "el_hongo_alto.glb") }, new Vector3(-236f, 0, -175f), 30f, 6f, "arcilla_gris"),
                ("el_submarino", new[] { Path.Combine(Fns, "modelos", "el_submarino", "el_submarino_alto.glb"), Path.Combine(Fns, "modelos_mac", "result.glb") },
                 new Vector3(-101f, 0, -125f), 120f, 25f, "arcilla_clara"),
            };
            foreach (var (nombre, rutas, pos, giro, largo, capa) in lugares)
            {
                string src = rutas.FirstOrDefault(File.Exists);
                if (src == null) { Anotar($"hoy: {nombre} no está en esta máquina (se saltea)"); continue; }
                string a = Copiar(src, $"{Raiz}/Modelos/lugares/{nombre}.glb");
                AssetDatabase.Refresh();
                var modelo = AssetDatabase.LoadAssetAtPath<GameObject>(a);
                if (!modelo) continue;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(modelo);
                go.transform.SetParent(raiz, false);
                go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.Euler(0, giro, 0));
                go.transform.localScale = Vector3.one;

                // a su tamaño real: Hunyuan entrega todo normalizado (~1 m) y Meshy, a ojo
                var rends = go.GetComponentsInChildren<Renderer>();
                if (rends.Length > 0)
                {
                    var b = rends[0].bounds;
                    foreach (var r in rends) b.Encapsulate(r.bounds);
                    float mayor = Mathf.Max(b.size.x, b.size.y, b.size.z);
                    if (mayor > 1e-3f) go.transform.localScale = Vector3.one * (largo / mayor);
                }

                // sin textura (Hunyuan sólo forma): la roca triplanar con estratos, como el paredón
                string infoRuta = Path.Combine(Path.GetDirectoryName(src), nombre + "_hunyuan.json");
                bool sinTextura = File.Exists(infoRuta) && !JsonUtility.FromJson<InfoHunyuan>(File.ReadAllText(infoRuta)).textura;
                if (sinTextura && (capas.TryGetValue(capa, out var cp) || capas.TryGetValue("estratos", out cp)))
                {
                    var mat = Lit($"roca_{nombre}", cp.diffuseTexture, cp.normalMapTexture, cp.maskMapTexture,
                                  new Color(cp.diffuseRemapMax.x, cp.diffuseRemapMax.y, cp.diffuseRemapMax.z), true, true, 6f);
                    foreach (var r in go.GetComponentsInChildren<Renderer>())
                        r.sharedMaterials = Enumerable.Repeat(mat, Mathf.Max(1, r.sharedMaterials.Length)).ToArray();
                }

                // apoyado en el terreno real, hundido 30 cm (no flota)
                var p = pos;
                foreach (var t in suelos)
                {
                    var tp = t.transform.position; var tam = t.terrainData.size;
                    if (p.x >= tp.x && p.z >= tp.z && p.x <= tp.x + tam.x && p.z <= tp.z + tam.z) { p.y = t.SampleHeight(p) + tp.y - 0.3f; break; }
                }
                var bs = go.GetComponentsInChildren<Renderer>().Select(r => r.bounds).DefaultIfEmpty(new Bounds()).Aggregate((x, y) => { x.Encapsulate(y); return x; });
                go.transform.position = p - new Vector3(bs.center.x, bs.min.y, bs.center.z);
                go.isStatic = true;
                Anotar($"hoy: {nombre} puesto ({largo:0} m{(sinTextura ? ", roca triplanar" : "")}, ubicación aproximada)");
            }
        }

        static void SalidaVideo(GameObject sistemas, Arranque arranque)
        {
            var go = new GameObject("Salida_Video");
            go.transform.SetParent(sistemas.transform, false);
#if FNS_SPOUT && UNITY_STANDALONE_WIN
            var s = go.AddComponent<Klak.Spout.SpoutSender>();
            s.spoutName = "ParqueTriasico";
            s.captureMethod = Klak.Spout.CaptureMethod.GameView;
            s.SetResources(AssetDatabase.LoadAssetAtPath<Klak.Spout.SpoutResources>("Packages/jp.keijiro.klak.spout/Editor/SpoutResources.asset"));
            s.enabled = false;
            arranque.salidaVideo = s;
            Anotar("salida: Spout (se prende con --spout NOMBRE)");
#elif FNS_SYPHON && UNITY_STANDALONE_OSX
            var s = go.AddComponent<Klak.Syphon.SyphonServer>();
            s.ServerName = "ParqueTriasico";
            s.CaptureMethod = Klak.Syphon.CaptureMethod.GameView;
            s.Resources = AssetDatabase.LoadAssetAtPath<Klak.Syphon.SyphonResources>("Packages/jp.keijiro.klak.syphon/Internal/SyphonResources.asset");
            s.enabled = false;
            arranque.salidaVideo = s;
            Anotar("salida: Syphon (se prende con --syphon NOMBRE)");
#else
            Anotar("salida: directo a pantalla (sin Spout/Syphon en esta plataforma)");
#endif
        }

        // ------------------------------------------------------------------------------------------
        // compilar
        // ------------------------------------------------------------------------------------------

        static bool Compilar()
        {
            bool windows = EditorUserBuildSettings.activeBuildTarget == BuildTarget.StandaloneWindows64;
            string destino = windows ? Path.Combine(Builds, "Windows", "ParqueTriasico.exe") : Path.Combine(Builds, "Mac", "ParqueTriasico.app");
            Directory.CreateDirectory(Path.GetDirectoryName(destino));
            var r = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { Escena },
                locationPathName = destino,
                target = EditorUserBuildSettings.activeBuildTarget,
                options = BuildOptions.None,
            });
            bool ok = r.summary.result == BuildResult.Succeeded;
            Anotar(ok ? $"EJECUTABLE: {destino} ({r.summary.totalSize / 1048576} MB, {r.summary.totalTime.TotalMinutes:0} min)"
                      : $"FALLÓ la compilación: {r.summary.result} · {r.summary.totalErrors} errores");
            return ok;
        }

        static void GuardarInforme()
        {
            try
            {
                Directory.CreateDirectory(Builds);
                File.WriteAllText(Path.Combine(Builds, "informe_constructor.txt"), informe.ToString());
            }
            catch (Exception e) { Debug.LogWarning("no pude guardar el informe: " + e.Message); }
        }
    }
}
