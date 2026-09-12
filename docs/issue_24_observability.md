# Issue 24: Prometheus metrics and structured JSON logging

## Objetivo
Mejorar la observabilidad de la aplicación en producción. Se implementarán logs estructurados en formato JSON (para facilitar su ingesta en sistemas como ELK o Datadog) y se expondrán métricas de Prometheus para monitorear el uso de los endpoints, tiempos de respuesta y salud del servicio.

## Tareas

### 1. Preparación y Branching
```bash
git checkout -b feature/issue-24-observability
```

### 2. Actualización de Dependencias
- **Acción**: Agregar las librerías necesarias al `pyproject.toml`.
- **Implementación**: Sumar `python-json-logger>=2.0.0` (para formateo JSON en el módulo estándar de logging) y `prometheus-fastapi-instrumentator>=7.0.0` (para exponer métricas `/metrics` en FastAPI).
```bash
# Tras modificar pyproject.toml
make install
```

### 3. Configuración de JSON Logging
- **Acción**: Modificar `src/api/logging.py`.
- **Implementación**: Reemplazar el string de formato estándar por la clase `pythonjsonlogger.jsonlogger.JsonFormatter` dentro de la configuración `dictConfig` para que todas las salidas del stream sean JSON estructurados.

### 4. Instrumentación de Prometheus
- **Acción**: Modificar `src/api/main.py`.
- **Implementación**: Inicializar `Instrumentator().instrument(app).expose(app)` en la inicialización de FastAPI. Esto inyectará automáticamente un endpoint `/metrics` en la aplicación y registrará requests y latencias en formato Prometheus.

### 5. Testing Local y Formateo
```bash
# 1. Asegurar que no hay errores de tipo o formato introducidos
make format
make check

# 2. Correr los unit tests
make test
```

### 6. Git y Cierre
```bash
git add pyproject.toml src/api/logging.py src/api/main.py
git commit -m "feat: add prometheus metrics and structured json logging"
git push origin feature/issue-24-observability
git checkout develop
git merge feature/issue-24-observability
git branch -d feature/issue-24-observability
git push origin develop
gh issue close 24
```
