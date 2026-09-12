# Issue 23: Multi-stage build for production image

## Objetivo
Optimizar la imagen de Docker para el entorno de producción. El objetivo es reducir sustancialmente el tamaño final de la imagen, mejorar los tiempos de compilación, aislar las dependencias de build, y aumentar la seguridad corriendo la aplicación con un usuario sin privilegios.

## Tareas

### 1. Preparación y Branching
```bash
# Nota: Si ya estás en la rama correcta (ej. feature/issue-22-cdci y vas a empaquetarlo ahí, podés ignorar este paso, o crear una rama nueva)
git checkout -b feature/issue-23-docker
```

### 2. Crear archivo `.dockerignore`
- **Acción**: Prevenir que el contexto de Docker se contamine con archivos pesados e irrelevantes.
- **Implementación**: Crearemos un `.dockerignore` excluyendo `.venv`, `.git`, carpetas de caché (`__pycache__`, `.mypy_cache`, `.pytest_cache`), y variables de entorno (`.env`).

### 3. Refactorizar el `Dockerfile` a Multi-stage
- **Acción**: Implementar el patrón Multi-stage.
- **Implementación**:
  - **Stage 1 (`builder`)**: Usará `python:3.11-slim`, creará un entorno virtual en `/opt/venv`, instalará utilidades de build si fueran necesarias, e instalará todas las dependencias del `pyproject.toml`.
  - **Stage 2 (`production`)**: Usará una imagen limpia de `python:3.11-slim`, creará un usuario sin permisos de root (ej. `appuser`), copiará el entorno virtual compilado desde el *builder* (`COPY --from=builder /opt/venv /opt/venv`), y establecerá el `CMD` y `EXPOSE`.

### 4. Construcción y Verificación
```bash
# 1. Construir la imagen nueva
docker build -t financial-rag:latest .

# 2. Correr los contenedores usando el compose y ver si levanta exitosamente
docker compose up -d db
# Nota: docker-compose.yml ya tiene 'build: .' así que podemos forzar un build:
docker compose up -d --build

# 3. Finalizar
docker compose down
```

### 5. Push y Cierre
```bash
git add Dockerfile .dockerignore
git commit -m "feat: implement multi-stage docker build and unprivileged user"
git push origin feature/issue-23-docker
git checkout develop
git merge feature/issue-23-docker
git branch -d feature/issue-23-docker
git push origin develop
gh issue close 23
```
