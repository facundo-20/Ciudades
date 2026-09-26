# Buenos Aires Real 3D: link para cualquier computadora

Esta carpeta (`publicar`) es el visor listo para subir a internet. **No tiene tu token adentro**: cada navegador lo pide una vez y lo guarda solo en ese navegador.

## Opción A: Netlify Drop (la más rápida, gratis)
1. Entrá a https://app.netlify.com/drop e iniciá sesión (podés usar tu cuenta de Google o GitHub).
2. Arrastrá **esta carpeta `publicar`** a la página.
3. En unos segundos te da un link tipo `https://nombre-al-azar.netlify.app`. En *Site configuration > Change site name* podés ponerle `ba-real-3d` o lo que quieras.

## Opción B: GitHub Pages (gratis, si ya tenés GitHub)
1. Creá un repositorio público, subí `index.html`.
2. Settings > Pages > Branch `main` / root > Save. El link queda `https://TU_USUARIO.github.io/NOMBRE_REPO/`.

## Muy importante: protegé el token
En https://ion.cesium.com/tokens abrí tu token, y en **Allowed URLs** agregá el link que te dio Netlify o GitHub (y `http://localhost:8091` para tu PC). Así, aunque alguien vea el token, no le sirve en otra página.

## En cada computadora
- Abrí el link, pegá el token de Cesium ion **una sola vez** (queda guardado en ese navegador) y listo.
- Funciona igual que en tu PC: tomas 1–6, `L` o "Libre 🖱" para moverte con el mouse, WASD/Q/E, Grabar (.webm), Modo LED, pantalla completa.
- Necesita internet y una placa de video decente; en notebooks chicas bajá el detalle agregando `?detalle=16` al final del link.

## Límites
- Cesium ion Community: gratis, 1.000 cargas de mapa por mes, **uso no comercial**. Para usarlo en eventos pagos conviene el plan comercial de Cesium o la API directa de Google.
- Nunca subas `token.local.js` (queda solo en `ba_real`, fuera de esta carpeta).
