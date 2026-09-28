#!/bin/bash
# Puente de After Effects (Mac): doble clic. Ctrl+C para cortar.
cd "$(dirname "$0")/../.."
git checkout claude/fiesta-sol-2026-immersive-ph9915 && git pull
node fns2026/ae_puente/puente_ae.mjs
