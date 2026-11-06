"""Genera las evidencias del proyecto (IE5, IE6, IE7) en la carpeta evidence/.

Uso (desde la raíz del proyecto, con .venv activo):
    python -m scripts.generar_evidencias

Produce:
    evidence/escenarios.md          tabla + traza de cada escenario (decisión, razón, tools ejecutadas)
    evidence/escenarios.json        lo mismo, en formato máquina
    evidence/rag_output.md          búsqueda semántica (requiere haber ejecutado scripts.index_politicas)
    evidence/pytest_output.txt      salida completa de pytest -v -rs
    evidence/pytest_junit.xml       resultado de pytest en XML
    evidence/resumen_evidencias.md  resumen para pegar en el informe

El script termina con código 1 si falta algún escenario, si algún escenario no
produce la decisión esperada, si pytest falla, si hay tests saltados o si la
recuperación semántica (RAG) no está indexada.

No usa Gemini: el flujo procesar_solicitud es determinista y funciona sin internet.
"""
import contextlib
import io
import json
import platform
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EVID = RAIZ / "evidence"

from config.settings import CHROMA_DIR  # noqa: E402
from tests import helpers  # noqa: E402

NUM_ESCENARIOS_ESPERADOS = 6
NOMBRES_TOOLS = ("consultar_pedido", "validar_politica", "calcular_reembolso",
                 "generar_etiqueta", "actualizar_crm", "notificar_cliente", "guardar_decision")


def reiniciar_bd() -> None:
    """Recrea techstore.db desde los CSV (borra también el historial)."""
    if not (RAIZ / "data" / "pedidos.csv").exists():
        subprocess.run([sys.executable, "scripts/generate_mock_data.py"], cwd=RAIZ, check=True, capture_output=True)
    subprocess.run([sys.executable, "-m", "scripts.seed_data"], cwd=RAIZ, check=True, capture_output=True)


class Trazador:
    """Envuelve una tool y anota cada vez que el agente la ejecuta (traza real, no supuesta)."""

    def __init__(self, nombre, objetivo, bitacora):
        self.nombre, self.objetivo, self.bitacora = nombre, objetivo, bitacora

    def invoke(self, args):
        self.bitacora.append(self.nombre)
        return self.objetivo.invoke(args)


def ejecutar(pedido_id: str) -> dict:
    """Ejecuta procesar_solicitud y devuelve resultado + tools usadas + notificaciones."""
    import agent.core as core

    bitacora: list[str] = []
    originales = {n: getattr(core, n) for n in NOMBRES_TOOLS}
    for n, obj in originales.items():
        if n == "guardar_decision":
            def envoltorio(*a, _f=obj, _n=n, **k):
                bitacora.append(_n)
                return _f(*a, **k)
            setattr(core, n, envoltorio)
        else:
            setattr(core, n, Trazador(n, obj, bitacora))
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            r = core.procesar_solicitud(pedido_id)
    finally:
        for n, obj in originales.items():
            setattr(core, n, obj)
    r = dict(r)
    r["tools_ejecutadas"] = bitacora
    r["notificaciones"] = [l.strip() for l in buf.getvalue().splitlines() if l.startswith("[NOTIF]")]
    return r


def escenarios() -> list[dict]:
    par = helpers.par_cliente_recurrente()
    if par is None:
        raise RuntimeError("No hay cliente con dos pedidos válidos para el escenario de memoria (revisa los datos mock).")
    fr = helpers.pedido_fraude()
    if fr is None:
        raise RuntimeError("No hay pedido de fraude válido para el escenario 5 (revisa los datos mock).")
    esc = [
        {"nombre": "1. Caso estándar", "pedidos": ["PED-001"], "esperado": ["aprobar_estandar"], "ie": "IE1, IE2, IE3"},
        {"nombre": "2. Fuera de plazo (escalamiento)", "pedidos": ["PED-015"], "esperado": ["escalar"], "ie": "IE5, IE7"},
        {"nombre": "3. Alto valor (solicitud de aprobación)", "pedidos": ["PED-022"],
         "esperado": ["solicitar_aprobacion"], "ie": "IE5, IE7"},
        {"nombre": f"4. Memoria de largo plazo (cliente {par[0]})", "pedidos": [par[1], par[2]],
         "esperado": ["aprobar_estandar", "aprobar_preferente"], "ie": "IE3, IE4, IE5"},
        {"nombre": "5. Sospecha de fraude", "pedidos": [fr], "esperado": ["escalar_fraude"], "ie": "IE5, IE7"},
        {"nombre": "6. Falta información", "pedidos": ["__SIN_MOTIVO__"], "esperado": ["solicitar_info"], "ie": "IE5"},
    ]
    assert len(esc) == NUM_ESCENARIOS_ESPERADOS
    return esc


def correr_escenarios() -> list[dict]:
    salida = []
    for e in escenarios():
        reiniciar_bd()  # cada escenario parte sin historial
        pasos = []
        for pid in e["pedidos"]:
            try:
                if pid == "__SIN_MOTIVO__":
                    pid = helpers.insertar_pedido_sin_motivo("PED-EVID-01")
                resultado = ejecutar(pid)
            except Exception as exc:  # un pedido roto no debe impedir generar el resto de la evidencia
                resultado = {"ok": False, "pedido_id": pid, "error": f"excepción: {exc}"}
            pasos.append(resultado)
        obtenidas = [p.get("accion", "error") for p in pasos]
        ok = all(p.get("ok") for p in pasos) and obtenidas == e["esperado"]
        salida.append({**e, "pasos": pasos, "obtenido": obtenidas, "ok": ok})
    reiniciar_bd()
    return salida


def escribir_escenarios(res: list[dict]) -> None:
    (EVID / "escenarios.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    L = ["# Evidencia de escenarios del agente TechStore Returns\n",
         f"Generado: {datetime.now():%Y-%m-%d %H:%M} · Python {platform.python_version()}\n",
         "| Escenario | Pedido(s) | Acción esperada | Acción obtenida | Resultado | Indicadores |",
         "|---|---|---|---|---|---|"]
    for e in res:
        ids = ", ".join(p.get("pedido_id", "?") for p in e["pasos"])
        L.append(f"| {e['nombre']} | {ids} | {' → '.join(e['esperado'])} | "
                 f"{' → '.join(e['obtenido'])} | {'✅' if e['ok'] else '❌'} | {e['ie']} |")
    for e in res:
        L.append(f"\n## {e['nombre']}\n")
        for p in e["pasos"]:
            if not p.get("ok"):
                L.append(f"- **Error en pedido {p.get('pedido_id', '?')}:** {p.get('error')}")
                continue
            ped = p.get("pedido") or {}
            L += [f"**Pedido {p['pedido_id']}** · cliente {ped.get('cliente_id', '?')} · {ped.get('producto', '?')} · "
                  f"${ped.get('monto', 0):,.0f} · devoluciones previas 90d: {ped.get('devoluciones_previas_90d', '?')} · "
                  f"historial recuperado: {len(ped.get('historial_cliente', []))}",
                  f"- Validación: {p.get('validacion', {}).get('razon', '?')} "
                  f"({p.get('validacion', {}).get('dias_desde_compra', '?')} días)",
                  f"- **Decisión: `{p.get('accion')}`** — {p.get('razon', '')}",
                  f"- Tools ejecutadas (en orden): {' → '.join(p.get('tools_ejecutadas', []))}"]
            if p.get("reembolso"):
                L.append(f"- Reembolso: ${p['reembolso']['monto']:,.0f} {p['reembolso']['moneda']} · "
                         f"etiqueta {p['etiqueta']['codigo']}")
            for n in p.get("notificaciones", []):
                L.append(f"- {n}")
            L.append("")
    (EVID / "escenarios.md").write_text("\n".join(L), encoding="utf-8")


def evidencia_rag() -> tuple[bool, str]:
    if not CHROMA_DIR.exists():
        (EVID / "rag_output.md").write_text(
            "# RAG\nNO INDEXADO: ejecuta `python -m scripts.index_politicas` y vuelve a generar la evidencia.\n",
            encoding="utf-8")
        return False, "no indexado (falta ejecutar scripts.index_politicas)"
    try:
        from agent.tools.buscar_casos import buscar_casos_similares
        L = ["# Evidencia de recuperación semántica (Chroma)\n"]
        for q in ["quiero devolver audífonos defectuosos", "cuántos días tengo para devolver",
                  "cliente que devuelve muchas veces"]:
            L.append(f"## Consulta: «{q}»")
            for x in buscar_casos_similares.invoke({"texto": q}):
                L.append(f"- **{x['tipo']}**: {x['texto'][:140].replace(chr(10), ' ')}")
            L.append("")
        (EVID / "rag_output.md").write_text("\n".join(L), encoding="utf-8")
        return True, "ok"
    except Exception as exc:  # noqa: BLE001
        (EVID / "rag_output.md").write_text(f"# RAG\nError: {exc}\n", encoding="utf-8")
        return False, f"error: {exc}"


def resumen_pytest(texto: str) -> tuple[dict, str]:
    """Lee la línea final de pytest, p. ej. '== 40 passed, 2 skipped in 3.1s =='."""
    cuenta = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    linea = next((l for l in reversed(texto.splitlines())
                  if re.search(r"\b(passed|failed|errors?|skipped)\b", l) and " in " in l), "")
    for n, clave in re.findall(r"(\d+) (passed|failed|errors?|skipped)", linea):
        cuenta["error" if clave.startswith("error") else clave] = int(n)
    return cuenta, linea.strip("= ").strip() or "(sin resumen)"


def correr_pytest() -> tuple[int, dict, str, list[str]]:
    p = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v", "-rs", "--tb=short",
                        f"--junitxml={EVID / 'pytest_junit.xml'}"], cwd=RAIZ, capture_output=True, text=True)
    texto = p.stdout + p.stderr
    (EVID / "pytest_output.txt").write_text(texto, encoding="utf-8")
    cuenta, ultima = resumen_pytest(texto)
    saltados = [l.strip() for l in texto.splitlines() if l.startswith("SKIPPED")]
    return p.returncode, cuenta, ultima, saltados


def main() -> None:
    EVID.mkdir(exist_ok=True)
    print("▶ Escenarios...")
    res = correr_escenarios()
    escribir_escenarios(res)
    print("▶ RAG...")
    rag_ok, rag_txt = evidencia_rag()
    print("▶ pytest...")
    code, cuenta, ultima, saltados = correr_pytest()

    ok = sum(e["ok"] for e in res)
    exito = (ok == len(res) == NUM_ESCENARIOS_ESPERADOS and code == 0
             and cuenta["skipped"] == 0 and rag_ok)

    L = ["# Resumen de evidencias\n",
         f"- Fecha: {datetime.now():%Y-%m-%d %H:%M} · Python {platform.python_version()} · {platform.system()}",
         f"- Escenarios correctos: **{ok}/{len(res)}** (detalle en `escenarios.md`)",
         f"- pytest: **{ultima}** (código de salida {code}; detalle en `pytest_output.txt`)",
         f"- Tests: aprobados {cuenta['passed']} · fallidos {cuenta['failed'] + cuenta['error']} · "
         f"saltados {cuenta['skipped']}",
         f"- Recuperación semántica (RAG): {rag_txt}",
         f"- Resultado global: {'APROBADO' if exito else 'INCOMPLETO / REVISAR'}",
         "", "## Acciones por escenario"]
    L += [f"- {e['nombre']}: {' → '.join(e['obtenido'])} {'✅' if e['ok'] else '❌'}" for e in res]
    if saltados:
        L += ["", "## Tests saltados (deben justificarse en el informe)"] + [f"- {s}" for s in saltados]
    (EVID / "resumen_evidencias.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    sys.exit(0 if exito else 1)


if __name__ == "__main__":
    main()
