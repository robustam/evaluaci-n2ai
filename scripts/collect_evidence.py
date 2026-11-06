"""Corre todos los escenarios y guarda evidencias para el informe."""
import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVID = RAIZ / "evidence"
EVID.mkdir(exist_ok=True)

def correr(cmd, salida):
    print(f"\n>> {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=RAIZ,
                       capture_output=True, text=True)
    texto = r.stdout + r.stderr
    (EVID / salida).write_text(texto, encoding="utf-8")
    print(texto[-600:])
    return r.returncode

# 1. Suite de tests → evidence/pytest_output.txt
correr("pytest tests/ -v", "pytest_output.txt")

# 2. Escenarios → evidence/escenarios.json
from agent.core import procesar_solicitud
escenarios = {}
for pid in ["PED-001", "PED-015", "PED-022"]:
    r = procesar_solicitud(pid)
    escenarios[pid] = {
        "accion": r["accion"],
        "razon": r["razon"],
        "reembolso": r.get("reembolso"),
        "etiqueta": r.get("etiqueta"),
    }
(EVID / "escenarios.json").write_text(
    json.dumps(escenarios, indent=2, ensure_ascii=False),
    encoding="utf-8",
)
print(json.dumps(escenarios, indent=2, ensure_ascii=False))

# 3. Reproducibilidad: clona en limpio y corre tests
print("\n=== Prueba de reproducibilidad (README desde cero) ===")
correr(
    "rm -rf /tmp/test-fresh && "
    "git clone $(git config --get remote.origin.url) /tmp/test-fresh && "
    "cd /tmp/test-fresh && "
    "python -m venv .venv && . .venv/bin/activate && "
    "pip install -q -r requirements.txt && "
    "python scripts/generate_mock_data.py && "
    "python -m scripts.seed_data && "
    "python -m scripts.index_politicas && "
    "pytest tests/ -q",
    "reproducibilidad.txt",
)
print("\n Evidencias guardadas en evidence/")
