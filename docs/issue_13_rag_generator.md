# Workflow and Specification: Issue 13 — RAG Generation Pipeline with LangChain

**Milestone**: M3: Hybrid Retrieval & RAG Generation Pipeline  
**GitHub Issue**: #13  
**Branch**: `feature/issue-13-rag-generator`  

---

## 1. Start the Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/issue-13-rag-generator
```

---

## 2. Development

### 2.1 RAG Generator Component (`src/rag/generator.py`)
Implement the LLM generation layer using LangChain 0.3 and `ChatOpenAI` (`gpt-4o-mini`).

- **Initialization**:
  - `class RAGGenerator:`
  - `__init__(self, llm_model: str = "gpt-4o-mini", temperature: float = 0.0)`
  - Initialize the `ChatOpenAI` instance with the specified model and temperature.

- **Prompt Template**:
  - Create a robust system prompt directing the LLM to answer the user's financial question using *only* the provided context (SEC 10-K filings).
  - The prompt must instruct the LLM to include citations (e.g., `[Item 7]`, `[Doc <ID>]`) mapping back to the provided chunks.

- **Methods**:
  - `async def generate_answer(self, query: str, context_chunks: list[RetrievedChunk]) -> str:`
    - Format the `context_chunks` into a single string to be injected into the prompt.
    - Execute the LCEL chain (`prompt | llm | StrOutputParser()`).
    - Return the generated string.
  - `async def astream_answer(self, query: str, context_chunks: list[RetrievedChunk]) -> AsyncGenerator[str, None]:`
    - Use LangChain's `.astream()` method on the chain.
    - Yield chunks of the generated string as they arrive for streaming responses.

### 2.2 RAG Chain Orchestration (`src/rag/chain.py` or `src/rag/pipeline.py`)
Create a facade/orchestrator that ties retrieval and generation together.

- **Initialization**:
  - `class RAGPipeline:`
  - `__init__(self, retriever: HybridRetriever, generator: RAGGenerator)`

- **Methods**:
  - `async def ask(self, query: str, filters: dict | None = None) -> dict:`
    - Await retrieval: `chunks = await self.retriever.retrieve(query, filters=filters)`
    - Await generation: `answer = await self.generator.generate_answer(query, chunks)`
    - Return a dictionary with the `answer` and `source_documents` (the chunks).

---

## 3. Testing (`tests/unit/rag/test_generator.py`)

### 3.1 Unit Testing

| Test | Verifies |
|---|---|
| `test_generator_initialization` | Verifies `ChatOpenAI` is correctly initialized with `gpt-4o-mini`. |
| `test_generate_answer_success` | Verifies the LCEL chain runs and returns a valid string (using a mock LLM). |
| `test_astream_answer_success` | Verifies that `astream_answer` correctly yields string chunks from the LLM. |
| `test_rag_pipeline_ask` | Verifies the orchestrator correctly pipes retrieved chunks into the generator and returns the final structure. |

### Execution commands:

```bash
# Run unit tests
pytest tests/unit/rag/ -v
```

---

## 4. Code Quality

```bash
make format      # Auto-format with ruff
make lint        # ruff linter
make type-check  # strict mypy
make check       # lint + type-check combined
```

---

## 5. Push to GitHub and Close

```bash
# Commit changes
git add src/ tests/ docs/issue_13_rag_generator.md
git commit -m "feat(rag): implement generation pipeline with langchain and gpt-4o-mini (#13)"

# Push branch
git push -u origin feature/issue-13-rag-generator

# Create Pull Request
gh pr create \
  --base develop \
  --title "feat(rag): implement generation pipeline with langchain and gpt-4o-mini (#13)" \
  --body "Closes #13.
- Implemented \`RAGGenerator\` using LangChain 0.3 LCEL.
- Configured \`ChatOpenAI\` with \`gpt-4o-mini\`.
- Added support for both synchronous (wait-for-full) and streaming (\`astream\`) responses.
- Implemented \`RAGPipeline\` to orchestrate retrieval (HybridRetriever) and generation.
- Added unit tests with mocked LLM calls."
```

---

## Closing Criteria

- [ ] `RAGGenerator` is implemented using LangChain 0.3.
- [ ] LLM model defaults to `gpt-4o-mini`.
- [ ] Prompt template instructs the model to use only provided context and cite sources.
- [ ] Streaming is supported via `.astream()`.
- [ ] Pipeline correctly orchestrates retrieval + generation.
- [ ] Unit tests pass with `ChatOpenAI` mocked.
- [ ] `make check` passes with no warnings.
- [ ] PR opened against `develop` referencing `Closes #13`.
