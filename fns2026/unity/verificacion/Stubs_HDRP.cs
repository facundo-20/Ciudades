// SÓLO PARA COMPILAR EN LA NUBE (no va a Unity). Firmas copiadas del código fuente real de
// HDRP / Core RP 17.3.0 (rama 6000.3/staging de Unity-Technologies/Graphics) y de KlakSpout 2.0.6
// / KlakSyphon 1.0.4, únicamente de lo que usa el proyecto. Si Unity cambia una firma, este archivo
// se actualiza mirando el fuente y la compilación de prueba lo detecta.
#pragma warning disable CS0649, CS0067, CS0414
using System;
using System.Collections.Generic;
using UnityEngine;

namespace UnityEngine.Rendering
{
    public abstract class VolumeParameter
    {
        public bool overrideState { get; set; }
    }

    public class VolumeParameter<T> : VolumeParameter
    {
        public virtual T value { get; set; }
        public VolumeParameter(T value = default, bool overrideState = false) { }
        public virtual void Override(T x) { overrideState = true; value = x; }
    }

    public class BoolParameter : VolumeParameter<bool> { public enum DisplayType { Checkbox, EnumPopup } public BoolParameter(bool v, bool o = false) { } public BoolParameter(bool v, DisplayType d, bool o = false) { } }
    public class FloatParameter : VolumeParameter<float> { public FloatParameter(float v, bool o = false) { } }
    public class MinFloatParameter : FloatParameter { public MinFloatParameter(float v, float min, bool o = false) : base(v, o) { } }
    public class ClampedFloatParameter : FloatParameter { public ClampedFloatParameter(float v, float min, float max, bool o = false) : base(v, o) { } }
    public class NoInterpMinFloatParameter : VolumeParameter<float> { public NoInterpMinFloatParameter(float v, float min, bool o = false) { } }
    public class IntParameter : VolumeParameter<int> { public IntParameter(int v, bool o = false) { } }
    public class ClampedIntParameter : IntParameter { public ClampedIntParameter(int v, int min, int max, bool o = false) : base(v, o) { } }
    public class NoInterpIntParameter : VolumeParameter<int> { public NoInterpIntParameter(int v, bool o = false) { } }
    public class ColorParameter : VolumeParameter<Color> { public ColorParameter(Color v, bool o = false) { } public ColorParameter(Color v, bool hdr, bool showAlpha, bool showEyeDropper, bool o = false) { } }
    public class EnumParameter<T> : VolumeParameter<T> { public EnumParameter(T v, bool o = false) { } }
    public class AnimationCurveParameter : VolumeParameter<AnimationCurve> { public AnimationCurveParameter(AnimationCurve v, bool o = false) { } }

    public class VolumeComponent : ScriptableObject
    {
        public bool active = true;
    }

    public sealed class VolumeProfile : ScriptableObject
    {
        public List<VolumeComponent> components = new List<VolumeComponent>();
        public T Add<T>(bool overrides = false) where T : VolumeComponent => default;
        public VolumeComponent Add(Type type, bool overrides = false) => null;
        public bool TryGet<T>(out T component) where T : VolumeComponent { component = default; return false; }
    }

    public class Volume : MonoBehaviour
    {
        public bool isGlobal { get; set; }
        public float priority = 0f;
        public float weight = 1f;
        public VolumeProfile sharedProfile = null;
        public VolumeProfile profile { get; set; }
    }
}

namespace UnityEngine.Rendering.HighDefinition
{
    public enum ExposureMode { Fixed = 0, Automatic = 1, AutomaticHistogram = 4, CurveMapping = 2, UsePhysicalCamera = 3 }
    public enum TonemappingMode { None, Neutral, ACES, Custom, External }
    public enum SkyType { HDRI = 1, Procedural = 2, Gradient = 3, PhysicallyBased = 4 }
    public enum SkyAmbientMode { Static, Dynamic }
    public enum RayCastingMode { RayMarching = 1 << 0, RayTracing = 1 << 1, Mixed = RayMarching | RayTracing }
    public enum WaterSurfaceType { OceanSeaLake, River, Pool }
    public enum WaterGeometryType { Quad, Custom, InstancedQuads, Infinite }

    public sealed class ExposureModeParameter : VolumeParameter<ExposureMode> { }
    public sealed class TonemappingModeParameter : VolumeParameter<TonemappingMode> { }
    public sealed class SkyAmbientModeParameter : VolumeParameter<SkyAmbientMode> { }
    public sealed class RayCastingModeParameter : VolumeParameter<RayCastingMode> { }

    public sealed class Fog : VolumeComponent
    {
        public BoolParameter enabled;
        public MinFloatParameter maxFogDistance;
        public FloatParameter baseHeight;
        public FloatParameter maximumHeight;
        public MinFloatParameter meanFreePath;
        public BoolParameter enableVolumetricFog;
        public ColorParameter albedo;
        public MinFloatParameter depthExtent;
        public ClampedFloatParameter anisotropy;
        public ClampedIntParameter volumeSliceCount;
    }

    public sealed class Exposure : VolumeComponent
    {
        public ExposureModeParameter mode;
        public FloatParameter compensation;
        public FloatParameter limitMin;
        public FloatParameter limitMax;
    }

    public sealed partial class VolumetricClouds : VolumeComponent
    {
        public enum CloudControl { Simple, Advanced, Manual }
        public enum CloudSimpleMode { Performance, Quality }
        public enum CloudPresets { Sparse, Cloudy, Overcast, Stormy, Custom }
        public BoolParameter enable;
        public ClampedIntParameter numPrimarySteps;
        public EnumParameter<CloudControl> cloudControl;
        public EnumParameter<CloudSimpleMode> cloudSimpleMode;
        public CloudPresets cloudPreset { get; set; }
        public AnimationCurveParameter densityCurve;
        public AnimationCurveParameter erosionCurve;
        public AnimationCurveParameter ambientOcclusionCurve;
        public ClampedFloatParameter densityMultiplier;
        public ClampedFloatParameter shapeFactor;
        public MinFloatParameter shapeScale;
        public ClampedFloatParameter erosionFactor;
        public MinFloatParameter erosionScale;
        public BoolParameter shadows;
    }

    public partial class PhysicallyBasedSky : VolumeComponent
    {
        public ClampedFloatParameter aerosolDensity;
        public ColorParameter aerosolTint;
    }

    public sealed class VisualEnvironment : VolumeComponent
    {
        public NoInterpIntParameter skyType;
        public SkyAmbientModeParameter skyAmbientMode;
    }

    public sealed class ColorAdjustments : VolumeComponent
    {
        public FloatParameter postExposure;
        public ClampedFloatParameter contrast;
        public ClampedFloatParameter saturation;
    }

    public sealed class WhiteBalance : VolumeComponent { public ClampedFloatParameter temperature; }
    public sealed class Tonemapping : VolumeComponent { public TonemappingModeParameter mode; }
    public sealed class Bloom : VolumeComponent { public ClampedFloatParameter intensity; public ClampedFloatParameter scatter; }
    public sealed class GlobalIllumination : VolumeComponent { public BoolParameter enable; public RayCastingModeParameter tracing; }
    public sealed class ScreenSpaceReflection : VolumeComponent { public BoolParameter enabled; public RayCastingModeParameter tracing; }
    public sealed class ScreenSpaceAmbientOcclusion : VolumeComponent { public BoolParameter rayTracing; public ClampedFloatParameter intensity; public ClampedFloatParameter radius; }
    public class ContactShadows : VolumeComponent { public BoolParameter enable; public ClampedFloatParameter length; }
    public class HDShadowSettings : VolumeComponent { public NoInterpMinFloatParameter maxShadowDistance; }
    public sealed class FilmGrain : VolumeComponent { public ClampedFloatParameter intensity; }
    public sealed class Vignette : VolumeComponent { public ClampedFloatParameter intensity; }
    public sealed class MotionBlur : VolumeComponent { public MinFloatParameter intensity; }

    public struct HDShadowInitParameters { public int maxDirectionalShadowMapResolution; }

    public struct RenderPipelineSettings
    {
        public enum ColorBufferFormat { R11G11B10 = 74, R16G16B16A16 = 48 }
        public bool supportSSR, supportSSAO, supportSSGI, supportVolumetrics, supportVolumetricClouds, supportWater,
                    supportDecals, supportMotionVectors, supportRayTracing;
        public ColorBufferFormat colorBufferFormat;
        public HDShadowInitParameters hdShadowInitParams;
    }

    public partial class HDRenderPipelineAsset : RenderPipelineAsset
    {
        public override RenderPipeline CreatePipeline() => null;   // en 2021 era public; en Unity 6, protected (sólo importa para el stub)
        public RenderPipelineSettings currentPlatformRenderPipelineSettings { get; set; }
    }

    public partial class HDAdditionalLightData : MonoBehaviour
    {
        public float angularDiameter { get; set; }
        public void SetShadowResolution(int resolution) { }
    }

    public partial class HDAdditionalCameraData : MonoBehaviour
    {
        public enum AntialiasingMode { None, FastApproximateAntialiasing, TemporalAntialiasing, SubpixelMorphologicalAntiAliasing }
        public enum TAAQualityLevel { Low, Medium, High }
        public AntialiasingMode antialiasing = AntialiasingMode.None;
        public TAAQualityLevel TAAQuality = TAAQualityLevel.Medium;
        public bool allowDynamicResolution = false;
        public bool allowDeepLearningSuperSampling = true;
    }

    public partial class WaterSurface : MonoBehaviour
    {
        public WaterSurfaceType surfaceType = WaterSurfaceType.OceanSeaLake;
        public WaterGeometryType geometryType = WaterGeometryType.Infinite;
        public float timeMultiplier = 1.0f;
        public float startSmoothness = 0.95f;
        public float endSmoothness = 0.85f;
        public Color refractionColor;
        public float maxRefractionDistance = 1.0f;
        public float absorptionDistance = 5.0f;
        public Color scatteringColor;
        public bool caustics = true;
        public float largeWindSpeed = 30.0f;
        public float largeOrientationValue = 0.0f;
        public float ripplesWindSpeed = 8.0f;
        public float largeCurrentSpeedValue = 0.0f;
    }

    public partial class DecalProjector : MonoBehaviour
    {
        public Material material { get; set; }
        public Vector2 uvScale { get; set; }
        public Vector3 size { get; set; }
        public float fadeFactor { get; set; }
    }

    public static partial class HDMaterial
    {
        public static bool ValidateMaterial(Material material) => true;
        public static void SetSurfaceType(Material material, bool transparent) { }
    }
}

namespace Klak.Spout
{
    public enum CaptureMethod { GameView, Camera, Texture }
    public sealed class SpoutResources : ScriptableObject { }
    public sealed partial class SpoutSender : MonoBehaviour
    {
        public string spoutName { get; set; }
        public CaptureMethod captureMethod { get; set; }
        public void SetResources(SpoutResources resources) { }
    }
}

namespace Klak.Syphon
{
    public enum CaptureMethod { GameView, Camera, Texture }
    public sealed class SyphonResources : ScriptableObject { }
    public sealed class SyphonServer : MonoBehaviour
    {
        public string ServerName { get; set; }
        public CaptureMethod CaptureMethod { get; set; }
        public SyphonResources Resources { get; set; }
    }
}
