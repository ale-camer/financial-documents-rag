# Workflow and Specification: Issue 17 — Containerized Deployment & Dockerization

**Milestone**: M5: CI/CD, Observability & Containerized Deployment  
**GitHub Issue**: #17  
**Branch**: `feature/issue-17-dockerization`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-17-dockerization
```

---

## 2. Development

### 2.1 Dockerfile para la API (`Dockerfile`)
Crear el archivo `Dockerfile` en la raíz del proyecto para empaquetar el servicio de FastAPI.

- **Base Image**: `python:3.11-slim` (para un tamaño reducido).
- **Environment**:
  - `PYTHONUNBUFFERED=1`
  - `PYTHONDONTWRITEBYTECODE=1`
- **Pasos**:
  1. Setear el directorio de trabajo a `/app`.
  2. Instalar dependencias del sistema necesarias si las hubiera.
  3. Copiar `pyproject.toml` (y si tuviéramos un lock file también).
  4. Instalar las dependencias de Python (por ej: `pip install .`).
  5. Copiar el código fuente (`src/`).
  6. Exponer el puerto `8000`.
  7. Configurar el comando de inicio: `["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`.

### 2.2 Actualizar Docker Compose (`docker-compose.yml`)
Modificar el archivo `docker-compose.yml` existente para integrar el contenedor de la API con la base de datos de PostgreSQL (pgvector).

- **Servicio `api`**:
  - `build: .`
  - `container_name`: `financial_rag_api`
  - `ports`: `"8000:8000"`
  - `environment`: Leer desde un archivo `.env` o inyectar las variables de entorno necesarias (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT`, y `OPENAI_API_KEY`).
  - `depends_on`:
    - `db`: con la condición `condition: service_healthy` (asegura que PostgreSQL esté recibiendo conexiones antes de intentar iniciar FastAPI).
- Modificar el healthcheck o las configuraciones de la base de datos si fuera necesario para ajustarse a este requerimiento.

---

## 3. Testing Local

Verificar que la imagen se construye correctamente y que los contenedores arrancan y se comunican entre sí.

### Ejecución de comandos:

```bash
# Construir la imagen
docker compose build

# Levantar todos los servicios en background
docker compose up -d

# Verificar el estado y que no haya errores en los logs
docker compose ps
docker compose logs api

# Pegarle al endpoint de health
curl -X GET http://localhost:8000/health

# Bajar el entorno
docker compose down
```

---

## 4. Push to GitHub and Close

```bash
# Commit changes
git add Dockerfile docker-compose.yml docs/issue_17_dockerization.md
git commit -m "feat(ops): add dockerfile and integrate api into docker-compose (#17)"

# Push branch
git push -u origin feature/issue-17-dockerization

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(ops): add docker container for fastapi service (#17)" \
  --body "Closes #17.
- Added \`Dockerfile\` using Python 3.11 slim image.
- Updated \`docker-compose.yml\` to include the \`api\` service.
- Configured \`depends_on\` so the API waits for pgvector to be healthy before starting."
```

---

## Closing Criteria

- [ ] Archivo `Dockerfile` implementado y optimizado.
- [ ] Servicio `api` agregado exitosamente a `docker-compose.yml`.
- [ ] Conexión probada entre el contenedor de la API y el de la DB usando `docker compose up`.
- [ ] PR abierto referenciando `Closes #17`.
