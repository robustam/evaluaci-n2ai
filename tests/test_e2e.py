from agent.core import procesar_solicitud

def test_flujo_estandar():
    r = procesar_solicitud("PED-001")
    assert r["ok"] is True
    assert r["accion"] == "aprobar_estandar"
    assert r["reembolso"]["monto"] > 0

def test_flujo_fuera_de_plazo():
    r = procesar_solicitud("PED-015")
    assert r["accion"] == "escalar"
    assert "plazo" in r["razon"].lower()

def test_flujo_alto_valor():
    r = procesar_solicitud("PED-022")
    assert r["accion"] == "solicitar_aprobacion"

def test_pedido_inexistente():
    r = procesar_solicitud("PED-999")
    assert r["ok"] is False
