# Issue 21: Refinar Schemas y Finalizar Documentación OpenAPI

## Objetivo
Mejorar la documentación generada automáticamente en `/docs` (Swagger UI) por FastAPI. Se busca enriquecer los modelos Pydantic con ejemplos de uso, tipar estrictamente las respuestas restantes y agrupar lógicamente los endpoints mediante etiquetas (tags) para ofrecer un contrato de API claro y profesional.

## Tareas

### 1. Preparación y Branching
```bash
git checkout -b feature/issue-21-openapi
```

### 2. Mejoras en Modelos Pydantic (`src/api/schemas.py`)
- **Acción**: Ampliar y crear nuevos schemas para cubrir todo el contrato.
- **Implementación**:
  - Modificar `QueryRequest` e `IngestRequest` agregando `json_schema_extra={"examples": [...]}` para que Swagger muestre ejemplos reales de carga útil (payload).
  - Crear `HealthResponse` (`status: str`).
  - Crear `IngestResponse` (`status: str`, `message: str`).

### 3. Configuración de Metadatos de FastAPI (`src/api/main.py`)
- **Acción**: Definir agrupaciones (tags) con descripciones para la API.
- **Implementación**:
  - Definir la variable `tags_metadata` detallando cada grupo ("System", "RAG Queries", "Ingestion").
  - Pasar `openapi_tags=tags_metadata` al inicializar `app = FastAPI(...)`.

### 4. Actualización de Decoradores de Endpoints (`src/api/main.py`)
- **Acción**: Aplicar los tags y los nuevos response models a cada ruta.
- **Implementación**:
  - `@app.get("/health", tags=["System"], response_model=HealthResponse)`
  - `@app.post("/query", tags=["RAG Queries"], response_model=QueryResponse)`
  - `@app.post("/ingest", tags=["Ingestion"], response_model=IngestResponse, status_code=202)`

### 5. Testing Local y Git
```bash
# 1. Correr tests para asegurar que no se rompieron las validaciones
pytest tests/unit/ -v

# 2. Levantar el proyecto para inspeccionar el /docs manualmente
docker compose up -d db
uvicorn src.api.main:app --reload &
sleep 2

# >> EN ESTE PUNTO PODÉS ABRIR TU NAVEGADOR EN: http://localhost:8000/docs <<
# Una vez revisado, frenamos los procesos:
kill %1
docker compose down

# 3. Commitear y pushear
git add .
git commit -m "docs: refine pydantic schemas and openapi metadata"
git push origin feature/issue-21-openapi

# 4. Merge a develop
git checkout develop
git merge feature/issue-21-openapi
git branch -d feature/issue-21-openapi
git push origin develop
gh issue close 21
```
