# Issue 20: Framework de Evaluación de Calidad RAG

## Objetivo
Implementar un entorno de evaluación sistemático para medir la calidad y precisión de las respuestas generadas por el pipeline RAG, integrándolo con LangSmith para tener trazabilidad de los experimentos.

## Tareas

### 1. Preparación y Branching
Crear la rama para aislar los cambios:
```bash
git checkout -b feature/issue-20-evaluation
```

### 2. Dataset de Evaluación (Ground Truth)
- **Acción**: Generar un conjunto de datos estático para medir el rendimiento del modelo.
- **Implementación**: Crear el archivo `tests/evaluation/dataset.json` con preguntas predefinidas, contextos de referencia y las respuestas esperadas (`ground_truth`). Esto actuará como la vara de medir para nuestro RAG.

### 3. Pipeline de Evaluación
- **Acción**: Implementar un script que orqueste la evaluación.
- **Implementación**: Crear `scripts/evaluate_rag.py`. 
  - Leerá el dataset de prueba.
  - Consumirá nuestra clase `RAGPipeline` para generar las respuestas.
  - Usará el método `evaluate` de la SDK de LangSmith para correr evaluadores LLM-as-a-judge (Fidelidad de la respuesta, Relevancia, y Precisión del Contexto).

### 4. Integración Continua (Pytest)
- **Acción**: Crear un test que valide los umbrales de calidad.
- **Implementación**: Añadir `tests/evaluation/test_rag_quality.py`. Si bien la evaluación exhaustiva se hace con el script, este test verificará de forma ligera que el generador no alucine (usando aserciones de métricas base).

### 5. Testing Local y Git
Para correr las evaluaciones y cerrar el issue:
```bash
# 1. Levantar dependencias (DB) e ingestar un documento (si hace falta)
docker compose up -d db

# 2. Ejecutar la evaluación manual (Asegurate de tener exportadas tus claves)
python scripts/evaluate_rag.py

# 3. Guardar cambios y subir la rama
git add .
git commit -m "test: implement rag quality evaluation framework"
git push origin feature/issue-20-evaluation

# 4. Merge a develop (Una vez chequeado el dashboard en LangSmith)
git checkout develop
git merge feature/issue-20-evaluation
git branch -d feature/issue-20-evaluation
git push origin develop
gh issue close 20
```
