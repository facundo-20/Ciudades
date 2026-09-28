import { defineConfig } from 'vite';

// base relativa: el build (dist/) anda servido desde cualquier carpeta, desde el puente de Node
// o abierto en el Web Render TOP de TouchDesigner
export default defineConfig({
  base: './',
  build: { target: 'es2022', chunkSizeWarningLimit: 1200 },
  server: { port: 5173 },
});
