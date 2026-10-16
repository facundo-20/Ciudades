# Origen de este paquete

Copia sin cambios de `package/` de https://github.com/aras-p/UnityGaussianSplatting, versión
**v1.1.1** (commit 9310dce438da726244ace17eaf6f768826435fa4, 9/4/2025). Licencia MIT (`LICENSE.md`),
© Aras Pranckevičius.

Va embebido en el proyecto (y no como paquete de git) para que Unity no necesite git para
abrirlo y para que quede fijo en la versión verificada contra HDRP 17.3 (Unity 6.3): el pase
`GaussianSplatHDRPPass` usa `CustomPass.Setup/Execute(CustomPassContext)/Cleanup`,
`RTHandles.Alloc(Vector2, …, DepthBits, GraphicsFormat, …)` y `CustomPassContext.cameraColorBuffer /
cameraDepthBuffer`, que siguen iguales en 6000.3.

Lo usa `Assets/FNS/Runtime/Splats.cs` y lo arma `Assets/FNS/Editor/Constructor.cs` (`PrepararSplats`).
