# Issue 19: Implementación del Endpoint de Ingesta (/api/v1/ingest)

## Objetivo
Integrar el pipeline de ingesta (descarga desde EDGAR, parseo, chunking y embedding) al endpoint `/ingest` en FastAPI, permitiendo a los usuarios indexar los últimos 10-K de una empresa a partir de su Ticker.

## Tareas

### 1. Preparación y Branching
Antes de empezar la implementación, crear la feature branch:
```bash
git checkout -b feature/issue-19-ingest
```

### 2. Resolución de Ticker a CIK
- La API de EDGAR requiere el CIK (Central Index Key) de la empresa, pero el usuario enviará el Ticker (ej. AAPL).
- **Acción**: Agregar lógica en `src/ingestion/edgar_client.py` (o en una función utilitaria) para consultar y cachear `https://www.sec.gov/files/company_tickers.json`.
- **Implementación**: Crear el método `get_cik_from_ticker(ticker: str) -> str`, que buscará el ticker y devolverá el CIK rellenado con ceros (o lanzará un error 404/400 si el ticker no es válido).

### 3. Inyección de Dependencias
- El endpoint `/ingest` necesita acceso a varias clases que actualmente no están inyectadas.
- **Acción**: Actualizar `src/api/dependencies.py`.
- **Implementación**: Añadir funciones cacheadas (`@lru_cache`) para inyectar:
  - `get_edgar_client()`
  - `get_filing_downloader()` (pasándole el cliente de EDGAR)
  - `get_indexing_pipeline()` (que instancia el `SectionAwareChunker`, `EmbeddingService` y `VectorStoreClient`).

### 4. Procesamiento en Segundo Plano (BackgroundTasks)
- La descarga desde EDGAR, el chunking y la generación de embeddings consumen bastante tiempo y no deben bloquear el request HTTP.
- **Acción**: Utilizar la clase `BackgroundTasks` nativa de FastAPI.
- **Implementación**: 
  - Crear una función asíncrona interna `run_ingestion_pipeline(ticker, cik, downloader, pipeline)` que se encargue del flujo pesado:
    1. Llama a `downloader.download_recent_10k(cik)`.
    2. Lee el HTML y lo parsea con `SECParser` y `SectionExtractor` para crear un `ParsedDocument`.
    3. Llama a `pipeline.process_document(document)` para meterlo en la DB.

### 5. Actualizar Endpoint `/ingest` en FastAPI
- **Acción**: Modificar `src/api/main.py`.
- **Implementación**:
  - Reemplazar el código temporal (stub).
  - Recibir `IngestRequest` y `BackgroundTasks`.
  - Obtener el CIK desde el ticker. Si falla, devolver HTTP 400.
  - Agregar `run_ingestion_pipeline` a las tareas de background.
  - Devolver un HTTP 202 (Accepted) inmediatamente indicando que la ingesta está en proceso.

### 6. Testing Local y Git
Para asegurar que todo funcione y pushear la rama, deberás correr:
```bash
# 1. Correr todos los tests de unidad actuales para asegurar que nada rompió
pytest tests/unit/ -v

# 2. Levantar dependencias y testear el endpoint localmente
# Podés copiar y pegar todo este bloque en una misma consola (el '&' manda a uvicorn al fondo)
docker compose up -d db
uvicorn src.api.main:app --reload &
sleep 2
curl -X POST http://localhost:8000/ingest -H "Content-Type: application/json" -d '{"ticker": "AAPL"}'
# Deberías ver el 202 Accepted. Luego frenamos uvicorn y la BD:
kill %1
docker compose down

# 3. Guardar cambios y pushear
git add .
git commit -m "feat: ingestion endpoint mapping and background tasks"
git push origin feature/issue-19-ingest

# 4. Merge a develop (si todo está OK)
git checkout develop
git merge feature/issue-19-ingest
git branch -d feature/issue-19-ingest
git push origin develop
gh issue close 19
```
