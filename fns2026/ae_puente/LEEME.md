# Puente de After Effects

Deja que la sesión de Claude en la nube maneje el After Effects de tu PC. Usa la rama de git como cable: los dos lados llegan a GitHub, así que no hay que abrir puertos ni crear cuentas.

## Cómo se usa

- **Windows:** doble clic en `PUENTE_AE.bat`, con After Effects instalado.
- **Mac:** doble clic en `PUENTE_AE_MAC.command`.

Queda corriendo; se corta con Ctrl+C.

## Qué hace

Cada 20 segundos:
1. Baja la rama.
2. Corre en After cada trabajo nuevo de `cola/`.
3. Sube el resultado a `hechos/<id>.json` y las capturas a `hechos/<id>/`.

Claude lee esos resultados, mira las capturas y manda el trabajo siguiente.

## Seguridad

- **Qué se ejecuta:** sólo los `.jsx` de `cola/` de esta rama, que únicamente pueden subir vos y la sesión de Claude.
- **Tus proyectos:** ningún trabajo cierra un proyecto sin guardar. Si hay uno abierto con cambios, el trabajo se frena y avisa.

## Si After no aparece

Indicá la ruta en la variable `AE_EXE`:
- **Windows:** `...\Support Files\AfterFX.exe`
- **Mac:** el nombre de la app, por ejemplo `Adobe After Effects 2025`
