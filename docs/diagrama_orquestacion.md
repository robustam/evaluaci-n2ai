# Diagrama de orquestación — TechStore Returns

Fuente Mermaid. Para incluirlo en el informe: pegar el bloque en https://mermaid.live, exportar a PNG o SVG e insertar la imagen en la sección 3.

```mermaid
flowchart TD
    U[Usuario en Streamlit<br/>ingresa ID de pedido] --> P[procesar_solicitud]
    P --> C[consultar_pedido<br/>pedido + historial del cliente]
    C --> V[validar_politica<br/>plazo de 30 días]
    V --> E[construir_estado]
    E --> PL{Planner determinista<br/>decidir_accion · 6 reglas}

    PL -- "1. No elegible" --> ESC[escalar]
    PL -- "2. Monto > $100.000" --> SA[solicitar_aprobacion]
    PL -- "3. ≥ 3 devoluciones en 90 días" --> FR[escalar_fraude]
    PL -- "4. Recurrente y monto < $50.000" --> AP[aprobar_preferente]
    PL -- "5. Falta comprobante o descripción" --> SI[solicitar_info]
    PL -- "6. Caso estándar" --> AE[aprobar_estandar]

    AE --> R1[calcular_reembolso]
    AP --> R1
    R1 --> R2[generar_etiqueta]
    R2 --> R3[actualizar_crm]
    R3 --> R4[notificar_cliente]

    ESC --> E1[actualizar_crm]
    FR --> E1
    SA --> E1
    E1 --> E2[notificar_cliente]

    SI --> S1[notificar_cliente]

    R4 --> G[guardar_decision<br/>memoria de largo plazo · SQLite]
    E2 --> G
    S1 --> G
    G --> T[Respuesta con traza en la interfaz]

    CH[(Chroma<br/>políticas y casos previos)] -. "buscar_casos_similares<br/>(RAG, ver nota)" .-> P
```

**Nota para el equipo:** la línea punteada indica la recuperación semántica. Debe reflejar exactamente dónde se usa en el código. Si `buscar_casos_similares` no forma parte del flujo `procesar_solicitud`, o solo lo usa el `AgentExecutor`, hay que dibujarlo en ese lugar y no en la posición actual.
