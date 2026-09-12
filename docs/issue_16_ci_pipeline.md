# Workflow and Specification: Issue 16 — Continuous Integration (GitHub Actions)

**Milestone**: M5: CI/CD, Observability & Containerized Deployment  
**GitHub Issue**: #16  
**Branch**: `feature/issue-16-ci-pipeline`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-16-ci-pipeline
```

---

## 2. Development

### 2.1 GitHub Actions Workflow (`.github/workflows/ci.yml`)
Configurar el pipeline automatizado para ejecutar las validaciones cada vez que se sube código o se crea un Pull Request.

- **Directorios**: Crear la carpeta `.github/workflows/` si no existe.
- **Definición del Workflow**: Crear el archivo `ci.yml`.
  - **Triggers**: `push` y `pull_request` a las ramas `main` y `develop`.
  - **Jobs**:
    - `test-and-lint`:
      - OS: `ubuntu-latest`.
      - Steps:
        1. `actions/checkout@v4`: Clonar el repositorio.
        2. `actions/setup-python@v4`: Instalar Python 3.11+.
        3. Configurar caché para pip.
        4. Ejecutar la instalación (`make install`).
        5. Correr comprobaciones de formato, tipado y linting (`make check`).
        6. Ejecutar tests unitarios (`pytest tests/unit/ -v`).
  - **Variables de Entorno**: Inyectar una variable dummy `OPENAI_API_KEY=dummy` para que el cliente de OpenAI no falle en los tests durante el CI.

---

## 3. Testing Local

Asegurar que los mismos comandos definidos en el workflow corren exitosamente en local.

### Ejecución de comandos:

```bash
# Validar pruebas
pytest tests/unit/ -v

# Validar calidad de código y tipado
make check
```

---

## 4. Push to GitHub and Close

```bash
# Commit changes
git add .github/workflows/ci.yml docs/issue_16_ci_pipeline.md
git commit -m "ci: implement github actions workflow for tests and linting (#16)"

# Push branch
git push -u origin feature/issue-16-ci-pipeline

# Create Pull Request
gh pr create \
  --base develop \
  --title "ci: implement github actions workflow for tests and linting (#16)" \
  --body "Closes #16.
- Added \`.github/workflows/ci.yml\` for automated CI checks.
- Pipeline executes \`make check\` (formatting, linting, type-checking) and unit tests via pytest.
- Setup for Python caching."
```

---

## Closing Criteria

- [ ] Directorio `.github/workflows/` creado correctamente.
- [ ] Workflow `ci.yml` configurado con todos los pasos (checkout, setup-python, install, test, check).
- [ ] Validación superada localmente al correr `make check` y `pytest`.
- [ ] PR abierto en `develop` referenciando `Closes #16`.
