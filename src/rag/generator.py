"""RAG Generator component using LangChain."""

from collections.abc import AsyncGenerator

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.rag.models import RetrievedChunk


class RAGGenerator:
    """LLM generation layer for answering financial questions from SEC filings."""

    def __init__(
        self, llm_model: str = "gpt-4o-mini", temperature: float = 0.0
    ) -> None:
        """Initialize with specified LLM and temperature."""
        self.llm = ChatOpenAI(model=llm_model, temperature=temperature)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful financial analyst assistant. "
                    "Use the following context extracted from SEC 10-K "
                    "filings to answer the user's question. If the answer "
                    "is not contained in the context, say so. Always cite "
                    "your sources using the format [Document <ID>] or "
                    "[Item X] if available in the context.\n\n"
                    "Context:\n{context}",
                ),
                ("human", "{query}"),
            ]
        )

        self.chain = self.prompt | self.llm | StrOutputParser()

    def _format_context(self, context_chunks: list[RetrievedChunk]) -> str:
        """Format chunks into a single string for the prompt."""
        formatted = []
        for chunk in context_chunks:
            section = chunk.section_name or "Unknown Section"
            formatted.append(
                f"[Document {chunk.document_id} | {section}]\n{chunk.content}"
            )
        return "\n\n".join(formatted)

    async def generate_answer(
        self, query: str, context_chunks: list[RetrievedChunk]
    ) -> str:
        """Generate a complete answer based on the query and context chunks."""
        context = self._format_context(context_chunks)

        result = await self.chain.ainvoke({"query": query, "context": context})
        return str(result)

    async def astream_answer(
        self, query: str, context_chunks: list[RetrievedChunk]
    ) -> AsyncGenerator[str, None]:
        """Stream the generated answer based on the query and context chunks."""
        context = self._format_context(context_chunks)

        async for chunk in self.chain.astream({"query": query, "context": context}):
            yield chunk
