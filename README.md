# TechStore Returns — Agente de devoluciones con IA

Agente que automatiza devoluciones de una tienda de tecnología simulada: consulta el pedido, valida la política de 30 días, recupera el historial del cliente y casos similares, decide con seis reglas priorizadas y ejecuta la acción correspondiente (reembolso, etiqueta, CRM y notificación) o escala el caso.

Asignatura ISY0101 · Evaluación Parcial N°2 · DUOC UC

## Stack

Python 3.10+ · LangChain 0.3 · Gemini Flash (nivel gratuito) · SQLite · Chroma · Streamlit · pytest

## Requisitos previos

- Python 3.10 o superior
- Git
- Una API key gratuita de Google AI Studio (https://aistudio.google.com/apikey)

## Instalación paso a paso

1. Clonar el repositorio y entrar a la carpeta:

   ```bash
   git clone <URL-DEL-REPOSITORIO>
   cd techstore-returns-agent
   ```

2. Crear y activar el entorno virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Mac/Linux
   .venv\Scripts\activate             # Windows (CMD)
   ```

3. Instalar dependencias (usa versiones fijadas en `requirements.txt`):

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Configurar la API key. Copiar el archivo de ejemplo y pegar la clave real. **No subir `.env` a GitHub.**

   ```bash
   cp .env.example .env               # Windows: copy .env.example .env
   ```

   Contenido de `.env`:

   ```
   GOOGLE_API_KEY=tu_api_key_aqui
   LLM_MODEL=gemini-3.8-flash
   ```

5. Verificar la conexión con Gemini:

   ```bash
   python scripts/verify_llm.py
   ```

   Debe imprimir `Hola desde Gemini`. Si aparece un error 404 o NOT_FOUND, revisar los modelos vigentes en https://ai.google.dev/gemini-api/docs/models y cambiar solo `LLM_MODEL` en `.env`.

6. Generar datos ficticios y cargarlos en la base de datos:

   ```bash
   python scripts/generate_mock_data.py
   python -m scripts.seed_data
   ```

7. Indexar las políticas y casos previos en Chroma (necesario para la recuperación semántica):

   ```bash
   python -m scripts.index_politicas
   ```

## Ejecución

Interfaz en vivo:

```bash
streamlit run <archivo-principal-de-streamlit>.py
```

Evidencias y pruebas (no requiere internet, el flujo principal es determinista):

```bash
python -m scripts.generar_evidencias   # genera la carpeta evidence/
pytest tests/ -v                        # solo las pruebas
```

Resultados esperados: `evidence/escenarios.md` con los 6 escenarios, `evidence/pytest_output.txt` con la salida de pytest y `evidence/resumen_evidencias.md` con el resumen. El script termina con código 0 solo si todos los escenarios cumplen lo esperado, pytest pasa sin tests saltados y la recuperación semántica está indexada.

## Estructura del proyecto

```
agent/            núcleo del agente: procesar_solicitud, planner, tools y memoria
config/           configuración (umbrales, rutas, variables de entorno)
data/             datos ficticios generados (CSV y base SQLite; no se versionan)
docs/             diagrama de orquestación y documentación técnica
evidence/         evidencias generadas por scripts.generar_evidencias
scripts/          utilidades: datos mock, carga de BD, indexación, verificación LLM, evidencias
tests/            pruebas unitarias, de planner, de memoria y end-to-end
requirements.txt  dependencias
```

## Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `pip` no se reconoce | El entorno virtual no está activo | Activar `.venv` y usar `python -m pip` |
| Error de ejecución de scripts en PowerShell | Política de Windows | Usar CMD o `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `git status` muestra `.env` | Falta `.gitignore` o el archivo se subió antes | Verificar `.gitignore`; si la clave se subió, revocarla en AI Studio |
| Modelo no encontrado (404) | Google retiró o renombró el modelo | Cambiar `LLM_MODEL` en `.env` |
| Tests de RAG saltados | Chroma no está indexado | Ejecutar `python -m scripts.index_politicas` |

## Autores

[Nombre integrante 1] · [Nombre integrante 2]
