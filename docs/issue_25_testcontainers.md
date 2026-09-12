# Issue 25: Test Suite con Docker-based Fixtures (Testcontainers)

## Objetivo
Lograr que los tests de integración que requieren una base de datos PostgreSQL con pgvector corran automáticamente en cualquier entorno, utilizando `testcontainers` para levantar instancias de Docker efímeras durante la ejecución del test suite. Esto evitará que los tests se salteen (SKIPPED) cuando no haya una base local levantada y garantizará un ambiente inmaculado.

## Tareas

### 1. Preparación y Branching
```bash
git checkout -b feature/issue-25-testcontainers
```

### 2. Actualización de Dependencias
- **Acción**: Instalar `testcontainers`.
- **Implementación**: Agregar `"testcontainers[postgres]>=4.0.0"` a la lista de dependencias `dev` en `pyproject.toml`. Luego correr `make install`.

### 3. Configurar Fixture en `conftest.py`
- **Acción**: Crear `tests/integration/conftest.py`.
- **Implementación**:
  - Crear un fixture autouse con scope de "session" o "module".
  - Instanciar `PostgresContainer("pgvector/pgvector:pg16")` y hacer `.start()`.
  - Sobrescribir las variables de entorno (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, etc.) para que nuestra aplicación (`_build_default_connection_string`) apunte directamente al testcontainer.
  - Ejecutar las migraciones (`MigrationRunner.apply_all()`) dentro del contenedor usando esta nueva conexión temporal.
  - Al hacer `yield`, devolver el control a los tests, y usar un bloque `finally` o similar para frenar el contenedor (`.stop()`).

### 4. Limpiar los Tests Actuales
- **Acción**: Quitar los decoradores de `skipif` en los tests de integración.
- **Implementación**: 
  - En `tests/integration/storage/test_vector_store_integration.py` y `tests/integration/indexing/test_pipeline_integration.py`, remover la función `_is_db_reachable()` y el decorador `@db_required`. 
  - Al estar garantizado el testcontainer, ya no es necesario saltear (SKIP) las pruebas.

### 5. Verificación
```bash
make format
make check
# Los tests de integración que antes daban SKIPPED ahora deberán decir PASSED
make test 
```

### 6. Cierre
```bash
git add pyproject.toml tests/integration/
git commit -m "test: add testcontainers for pgvector integration tests"
git push origin feature/issue-25-testcontainers
git checkout develop
git merge feature/issue-25-testcontainers
git branch -d feature/issue-25-testcontainers
git push origin develop
gh issue close 25
```
