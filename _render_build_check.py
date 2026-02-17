# Script para comprobar que el módulo api se puede importar durante el build en Render.
# Añade la carpeta donde está este script (raíz del repo) a sys.path.
import os
import sys

_repo_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _repo_root)

import api  # noqa: E402
print("Import api OK")
