# Workflow and Specification: Issue 18 — Observability (Logging & Tracing)

**Milestone**: M5: CI/CD, Observability & Containerized Deployment  
**GitHub Issue**: #18  
**Branch**: `feature/issue-18-observability`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-18-observability
```

---

## 2. Development

### 2.1 Centralized Logging Configuration (`src/api/logging.py`)
Implementar una configuración de logging estandarizada para garantizar visibilidad en producción.
- **Formato**: JSON formatter o un log estructurado claro que incluya el timestamp, nivel, nombre del logger y mensaje.
- **Configuración**: Se llamará a esta configuración al arrancar la app.

### 2.2 FastAPI Middleware para Request/Response (`src/api/main.py`)
Interceptar todas las peticiones a la API para registrar telemetría básica:
- **Datos a loguear**: Método HTTP, path, código de estado HTTP y tiempo de procesamiento (latencia).
- **Inyección**: Configurar el setup del logger centralizado en el evento `lifespan` de FastAPI.

### 2.3 Documentación de Tracing de LangSmith
El código base de Langchain ya soporta LangSmith de manera nativa. Se debe confirmar su funcionamiento y asegurarse de que el `docker-compose.yml` u otras variables documenten el uso de `LANGCHAIN_TRACING_V2` y `LANGCHAIN_API_KEY`.

---

## 3. Testing Local

Asegurar que los requests emiten logs con el formato adecuado y capturan la latencia.

### Ejecución de comandos:

```bash
# Correr tests para asegurar que no rompimos nada
pytest tests/unit/ -v

# Levantar servidor
uvicorn src.api.main:app --reload

# Pegarle al servidor y revisar los logs de salida (deberían mostrar la latencia)
curl -X GET http://localhost:8000/health
```

---

## 4. Push to GitHub and Close

```bash
# Commit changes
git add src/api/ docs/issue_18_observability.md
git commit -m "feat(observability): add structured logging and request latency middleware (#18)"

# Push branch
git push -u origin feature/issue-18-observability

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(observability): add structured logging and middleware (#18)" \
  --body "Closes #18.
- Added centralized logging configuration.
- Implemented FastAPI middleware to log request latency and status codes.
- Prepared observability foundations for production."
```

---

## Closing Criteria

- [ ] `logging.py` creado e inicializado correctamente en `main.py`.
- [ ] Middleware de FastAPI registrando latencia de las peticiones.
- [ ] Tests unitarios locales pasando con éxito (`make check`).
- [ ] PR abierto referenciando `Closes #18`.
