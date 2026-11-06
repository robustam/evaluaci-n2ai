# Agente TechStore Returns: automatización de devoluciones con IA

**Evaluación Parcial N°2 · ISY0101 Ingeniería de Soluciones con IA**
**Integrantes:** Lorena Ledezma Sánchez · [Nombre integrante 2]
**Docente:** [Nombre docente] · **Fecha:** 6 de noviembre de 2026
**Repositorio:** [URL de GitHub]

> Notas de uso de este borrador: los corchetes `[ ]` indican datos que el equipo debe completar o verificar antes de entregar. Nada entre corchetes debe quedar en la versión final.

---

## 1. Resumen ejecutivo

TechStore Returns es un agente que automatiza el proceso de devoluciones de una tienda de tecnología simulada. Recibe un ID de pedido, consulta la base de datos, valida la política de 30 días, recupera el historial del cliente y casos similares, decide con seis reglas priorizadas y ejecuta las acciones correspondientes (reembolso, etiqueta, CRM y notificación) o escala el caso con justificación. Se implementó con Python, LangChain, Gemini Flash, SQLite, Chroma y Streamlit. En las pruebas, los 6 escenarios definidos produjeron la decisión esperada y la suite automatizada registró [N] tests aprobados, [F] fallidos y [S] saltados (sección 6).

## 2. Contexto organizacional y requerimiento

El área de postventa de TechStore recibe solicitudes de devolución que hoy se revisan manualmente. El requerimiento es un agente que resuelva los casos estándar sin intervención, aplique la política de forma consistente, recuerde a los clientes entre sesiones y derive a una persona los casos de riesgo (fuera de plazo, monto alto, posible fraude).

**Alcance:** no procesa pagos reales, no se conecta a couriers reales, no maneja reclamos legales y no reemplaza al humano, lo asiste. Los datos son ficticios (40 pedidos y 15 clientes generados con semilla fija).

## 3. Arquitectura y orquestación (IE1, IE2, IE8)

El flujo principal sigue esta secuencia: el usuario ingresa un ID de pedido en Streamlit, `procesar_solicitud` llama a `consultar_pedido` (que incluye la memoria del cliente), `validar_politica` y `construir_estado`. Luego el planner determinista (`decidir_accion`) evalúa seis reglas y elige una de tres ramas: aprobar (calcular el reembolso, generar la etiqueta, actualizar el CRM y notificar), escalar o solicitar aprobación (actualizar el CRM y notificar), o solicitar información (notificar). Finalmente, `guardar_decision` registra la decisión en la memoria de largo plazo y la interfaz muestra la respuesta con su traza.

[Insertar imagen del diagrama de `docs/diagrama_orquestacion.md`, con la figura numerada y citada en el texto.]

Además, el proyecto incluye un `AgentExecutor` creado con `crear_agente`, que usa Gemini Flash para elegir por sí mismo entre las siete tools. Este enfoque sigue el patrón de razonamiento y acción descrito por Yao et al. (2023). [VERIFICAR: describir en qué caso se usa el `AgentExecutor` y mostrar una ejecución real en la evidencia.]

El flujo principal es híbrido: las tools se invocan en secuencia fija y el planner decide, lo que deja una traza reproducible; el LLM se reserva para razonamiento abierto. Las tools del proyecto son:

| Tool | Entrada → Salida | Tipo |
|---|---|---|
| `consultar_pedido` | pedido_id → dict (pedido + historial) | Consulta |
| `validar_politica` | pedido_id → {elegible, razon, dias} | Consulta/validación |
| `calcular_reembolso` | pedido_id, tipo → {monto, moneda} | Cálculo |
| `generar_etiqueta` | pedido_id → {codigo, url} | Escritura (mock) |
| `actualizar_crm` | pedido_id, estado → {ok} | Escritura (SQLite) |
| `notificar_cliente` | cliente_id, mensaje → {ok} | Escritura (mock) |
| `buscar_casos_similares` | texto → list[dict] | Consulta semántica (RAG) |

**Dependencias.** El archivo `requirements.txt` usa rangos de versión compatibles (por ejemplo, `langchain>=0.3,<1.0`). Las versiones exactas instaladas durante las pruebas se registran en `requirements-lock.txt` [VERIFICAR: generar con `pip freeze` y adjuntar al repositorio]. El repositorio incluye un README con instalación paso a paso.

## 4. Memoria y recuperación de contexto (IE3, IE4)

**Corto plazo:** `ConversationBufferMemory` de LangChain, guardada en `st.session_state`, mantiene la conversación mientras dura la sesión. Su funcionamiento se verifica en `tests/test_memoria.py`.

**Largo plazo:** la tabla `historial_cliente` en SQLite. Cada decisión se guarda con `guardar_decision`, y `consultar_pedido` la recupera. De este modo, el agente reconoce a clientes recurrentes y cuenta devoluciones previas.

**Semántica:** Chroma con embeddings `all-MiniLM-L6-v2`, que son representaciones vectoriales de oraciones como las descritas por Reimers y Gurevych (2019). Hay dos colecciones: políticas (un fragmento por sección) y casos previos. `buscar_casos_similares` devuelve los 2 casos y las 2 políticas más cercanas por significado. Este uso de recuperación antes de generar la respuesta corresponde al enfoque de Lewis et al. (2020). [VERIFICAR: indicar en qué paso de `procesar_solicitud` se invoca la recuperación semántica y cómo se refleja en `tools_ejecutadas`.]

## 5. Planificación y toma de decisiones (IE5)

El planner evalúa las reglas de arriba hacia abajo y se detiene en la primera que se cumple:

| # | Condición | Acción |
|---|---|---|
| 1 | No elegible (fuera de plazo) | escalar |
| 2 | Monto > $100.000 | solicitar_aprobacion |
| 3 | ≥ 3 devoluciones en 90 días | escalar_fraude |
| 4 | Cliente recurrente y monto < $50.000 | aprobar_preferente |
| 5 | Falta comprobante o descripción | solicitar_info |
| 6 | Caso estándar | aprobar_estandar |

**Justificación del orden de prioridad:** las reglas de riesgo van primero porque una aprobación automática es irreversible desde el punto de vista del negocio: se devuelve dinero y se genera una etiqueta. Si la regla 6 (caso estándar) se evaluara primero, un pedido fuera de plazo, de alto valor o con indicios de fraude se aprobaría sin pasar por la revisión humana, y las reglas 1 a 3 nunca se activarían. Ordenar por riesgo garantiza que los casos más sensibles sean revisados antes de cualquier acción, mientras que las reglas de trato amable (4 y 6) solo aplican a casos que ya superaron las verificaciones de riesgo.

## 6. Resultados y evidencias (IE5, IE7)

Los escenarios se ejecutaron con `python -m scripts.generar_evidencias` (carpeta `evidence/`) y las pruebas con `pytest tests/ -v`. La salida completa está en `evidence/pytest_output.txt`.

| Escenario | Pedido(s) | Decisión obtenida | Tools ejecutadas |
|---|---|---|---|
| Estándar | PED-001 | aprobar_estandar | 7 pasos, reembolso $25.000 |
| Fuera de plazo (45 días) | PED-015 | escalar | consulta, validación, CRM, notificación |
| Alto valor ($250.000) | PED-022 | solicitar_aprobacion | sin reembolso ni etiqueta |
| Memoria (cliente [C-XXX]) | [PED-XXX] → [PED-XXX] | aprobar_estandar → aprobar_preferente | el 2.º pedido recupera historial |
| Posible fraude | [PED-XXX] | escalar_fraude | cliente con [N] devoluciones |
| Falta información | pedido sin motivo | solicitar_info | solo notificación |

[VERIFICAR: copiar los IDs y cifras exactas desde `evidence/escenarios.md`. La tabla debe coincidir con la evidencia generada.]

El caso de memoria demuestra la adaptación: el mismo tipo de pedido recibe una decisión distinta porque el agente recordó la decisión anterior.

**Pruebas automatizadas:** [N] tests aprobados, [F] fallidos y [S] saltados. Los tests saltados corresponden a [justificar cada uno o indicar "ninguno"]. Evidencia en `evidence/pytest_output.txt` y `evidence/pytest_junit.xml`.

[Insertar capturas: 01_caso_estandar, 02_fuera_plazo, 03_alto_valor.]

## 7. Justificación de componentes (IE2, IE9)

| Componente | Requerimiento que cubre | Justificación |
|---|---|---|
| LangChain | Orquestar tools, memoria y agente | Ofrece abstracciones probadas para tools, memoria y agentes, y una integración directa con Gemini y Chroma. Evita reimplementar el ciclo de herramientas, lo que reduce el riesgo de errores y facilita sustituir el modelo más adelante. Se fijó la versión 0.3 porque las versiones 1.x cambian las rutas de `AgentExecutor` y `ConversationBufferMemory`. |
| Gemini Flash | Razonamiento abierto del agente | Tiene nivel gratuito suficiente para una demo académica, con respuestas rápidas. El modelo se configura con la variable `LLM_MODEL`, lo que permite cambiarlo sin tocar el código si Google renueva sus modelos. |
| SQLite | Datos del pedido y memoria de largo plazo | Es un archivo local sin servidor, suficiente para 40 pedidos y 15 clientes. Permite reproducir el proyecto en cualquier equipo con una sola instalación. Para producción se requeriría una base de datos con servidor, por lo que el diseño de acceso a datos debe mantenerse separado. |
| Chroma + embeddings locales | Recuperación semántica de políticas y casos | La búsqueda por significado encuentra casos como «audífonos defectuosos» aunque no coincidan las palabras exactas. Los embeddings locales evitan costos y dependencias de red para la indexación. |
| Planner determinista | Decisiones trazables y auditables | Con reglas explícitas, cada decisión puede explicarse y repetirse con los mismos datos. Un LLM podría responder distinto en cada ejecución, lo que dificultaría la auditoría de casos de alto monto o fraude. El LLM se usa solo para razonamiento abierto. |
| Streamlit | Demo en vivo | Permite construir una interfaz funcional en Python puro, donde el evaluador puede ingresar un pedido y ver la traza de decisiones en tiempo real. |

**Escalabilidad y compatibilidad [VERIFICAR, completar con lo implementado]:** el diseño separa las tools, el planner y la memoria en módulos independientes. Por eso, cambiar la base de datos o el modelo afecta solo a una capa. Las limitaciones actuales son [enumerar, por ejemplo: SQLite no soporta escritura concurrente masiva; el planner no aprende de casos nuevos].

## 8. Conclusiones y reflexiones individuales

*Sección obligatoria sin apoyo de IA. Cada integrante redacta la suya: qué aprendió, qué parte construyó y qué cambiaría.*

**Lorena Ledezma Sánchez:** [Redactar individualmente.]

**[Nombre integrante 2]:** [Redactar individualmente.]

## 9. Declaración de uso de IA

| Herramienta | Uso | Validado por |
|---|---|---|
| Gemini Flash | Motor LLM del agente | Equipo completo |
| Claude (Anthropic, 2026) | Estructura del informe y código de pruebas y evidencias | [Nombre del integrante que revisó] |
| [Otra, si aplica] | [Uso] | [Nombre] |

Las conclusiones, reflexiones individuales y justificaciones técnicas fueron redactadas por el equipo sin asistencia de IA. [Confirmar que esto sea cierto antes de firmar.]

## Referencias

Anthropic. (2026). *Claude* [Modelo de lenguaje]. https://claude.ai

Chroma. (s. f.). *Chroma documentation*. https://docs.trychroma.com/

Google. (s. f.). *Gemini API documentation*. https://ai.google.dev/gemini-api/docs

LangChain. (s. f.). *LangChain documentation*. https://python.langchain.com/

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Küttler, H., Lewis, M., Yih, W., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). Retrieval-augmented generation for knowledge-intensive NLP tasks. *Advances in Neural Information Processing Systems, 33*, 9459–9474. https://arxiv.org/abs/2005.11401

pytest-dev. (s. f.). *pytest documentation*. https://docs.pytest.org/

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *Proceedings of EMNLP-IJCNLP 2019*, 3982–3992. https://doi.org/10.18653/v1/D19-1410

SQLite Consortium. (s. f.). *SQLite documentation*. https://www.sqlite.org/docs.html

Streamlit. (s. f.). *Streamlit documentation*. https://docs.streamlit.io/

Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2023). ReAct: Synergizing reasoning and acting in language models. *International Conference on Learning Representations*. https://arxiv.org/abs/2210.03629
