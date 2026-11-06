"""Fixtures compartidas: deja la base de datos limpia antes de las pruebas."""
import subprocess
import sys
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parent.parent

@pytest.fixture(scope="session", autouse=True)
def base_de_datos_limpia():
    """Recrea techstore.db desde los CSV para que los tests sean repetibles."""
    subprocess.run(
        [sys.executable, "-m", "scripts.seed_data"],
        cwd=RAIZ, check=True
    )
