#!/usr/bin/env bash
# Fuerza el directorio de trabajo y PYTHONPATH a la raíz del repo (donde está api.py).
# Render puede ejecutar desde otro path; este script lo corrige.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
exec python -m uvicorn api:app --host 0.0.0.0 --port "${PORT:-8000}"
