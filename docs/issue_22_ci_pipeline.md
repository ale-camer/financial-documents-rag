# Issue 22: GitHub Actions CI pipeline (lint + test + type-check)

## Objetivo
Asegurar que el pipeline de Integración Continua (CI) pase de forma exitosa en GitHub Actions. Actualmente, el flujo falla en la etapa de `make check` debido a errores de linting (`ruff`) y falta de tipado estricto (`mypy`) que introdujimos en tareas anteriores.

## Tareas

### 1. Preparación y Branching
```bash
git checkout -b feature/issue-22-ci
```

### 2. Correcciones Automáticas (Ruff)
- **Acción**: Ejecutar el auto-formateador para arreglar imports y sintaxis.
- **Implementación**:
  - Correremos `make format`. Esto acomodará automáticamente los imports en `src/api/dependencies.py` y arreglará modos redundantes en `tests/evaluation/test_rag_quality.py`.

### 3. Correcciones Manuales de Tipado y Linting
- **Acción**: Resolver errores strictos de Mypy y líneas largas (E501).
- **Implementación**:
  - En `src/api/main.py`: Tipar la firma de `log_requests(request: Request, call_next: Callable) -> Response`. También se ajustarán las líneas que superan los 88 caracteres.
  - En `src/api/schemas.py`: Romper en múltiples líneas los ejemplos largos de `json_schema_extra` para cumplir el E501.
  - En `tests/evaluation/test_rag_quality.py`: Añadir la firma `-> None` a todos los tests e importar y aplicar `AsyncMock` o `MagicMock` al parámetro `mock_get_rag_pipeline`.

### 4. Testing Local y Git
```bash
# 1. Correr todas las validaciones estrictas (lint + tipos)
make format
make check

# 2. Correr los unit tests
make test

# 3. Si todo da OK, subir los cambios
git add .
git commit -m "ci: fix linting and type errors to unblock github actions pipeline"
git push origin feature/issue-22-ci

# 4. Merge a develop y cierre del issue
git checkout develop
git merge feature/issue-22-ci
git branch -d feature/issue-22-ci
git push origin develop
gh issue close 22
```
