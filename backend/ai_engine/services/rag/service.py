"""
Dich vu Codebase RAG cap cao (Service Layer).
Dieu phoi Ingestion, Thac truy xuat Cascade, Goi LLM kem Grounding va Citation Validator.
"""

import time
import hashlib
import logging
import os
from django.conf import settings
from django.core.cache import cache

from .config import get_rag_config
from .schemas import RAGQueryResponse, CitationItem
from .ingestion.pipeline import IngestionPipeline
from .vectorstore.chroma_store import ChromaStore
from .vectorstore.bm25_store import BM25Store
from .retrieval.cascade import RetrievalCascade, PipelineMode
from .grounding.prompt_builder import GroundingPromptBuilder, ESCAPE_HATCH_PHRASE
from .grounding.citation_validator import CitationValidator

logger = logging.getLogger(__name__)


class CodebaseRAGService:
    """Service quan ly toan bo chu trinh RAG Codebase."""

    def __init__(self):
        self.config = get_rag_config()
        self.chroma_store = ChromaStore()
        self.bm25_store = BM25Store()
        self.bm25_store.load()

        self.cascade = RetrievalCascade(self.chroma_store, self.bm25_store)
        self.prompt_builder = GroundingPromptBuilder()
        self.citation_validator = CitationValidator(self.config.workspace_root)

    def is_indexed(self) -> bool:
        """Kiem tra xem he thong da duoc danh chi muc chua."""
        return self.chroma_store.count() > 0 or self.bm25_store.count() > 0

    def index_codebase(self, force: bool = False) -> dict:
        """Quet toan bo codebase va nap vao ChromaStore va BM25Store."""
        start_time = time.time()
        pipeline = IngestionPipeline(self.config.workspace_root)
        chunks = pipeline.run()

        if not chunks:
            return {"status": "empty", "chunks_count": 0, "duration_s": 0.0}

        if force:
            self.chroma_store.clear()
            self.bm25_store.clear()

        # Nap vao ChromaStore va BM25Store
        self.chroma_store.upsert_chunks(chunks)
        self.bm25_store.upsert_chunks(chunks)
        self.bm25_store.persist()

        duration = round(time.time() - start_time, 2)

        # Xoa cache cac truy van cu khi co index moi
        self._invalidate_query_cache()

        logger.info("Da index thanh cong %d chunks trong %.2f giay.", len(chunks), duration)
        return {
            "status": "success",
            "chunks_count": len(chunks),
            "chroma_count": self.chroma_store.count(),
            "bm25_count": self.bm25_store.count(),
            "duration_s": duration,
        }

    def ensure_indexed(self) -> None:
        """Tu dong index neu chua co du lieu."""
        if not self.is_indexed():
            self.index_codebase()

    def query(
        self,
        query_text: str,
        mode: PipelineMode = PipelineMode.FULL_CASCADE,
        final_k: int = 5,
        use_cache: bool = True,
    ) -> RAGQueryResponse:
        """Hoi dap thong tin codebase dua tren Thac truy xuat va Grounding."""
        start_time = time.time()
        self.ensure_indexed()

        # 1. Kiem tra Redis Cache
        cache_key = f"codebase_rag_query:{hashlib.sha256((query_text + mode.value).encode()).hexdigest()}"
        if use_cache:
            cached_data = cache.get(cache_key)
            if cached_data:
                cached_data["latency_ms"] = round((time.time() - start_time) * 1000, 2)
                return RAGQueryResponse(**cached_data)

        # 2. Thuc thi Thac truy xuat (Retrieval Cascade)
        hits = self.cascade.run(query=query_text, mode=mode, final_k=final_k)

        if not hits:
            latency = round((time.time() - start_time) * 1000, 2)
            return RAGQueryResponse(
                query=query_text,
                answer=ESCAPE_HATCH_PHRASE,
                citations=[],
                verification={"is_escape_hatch": True, "all_valid": True},
                latency_ms=latency,
                retrieved_chunks_count=0,
            )

        # 3. Lap rap Grounding Prompt
        messages = self.prompt_builder.build_messages(query_text, hits)

        # 4. Goi LLM sinh cau tra loi bám nguồn
        raw_answer = self._generate_answer(messages)

        # 5. Kiem dinh trich dan nguon
        citations, verification_metrics = self.citation_validator.validate(raw_answer, hits)

        latency = round((time.time() - start_time) * 1000, 2)
        response = RAGQueryResponse(
            query=query_text,
            answer=raw_answer,
            citations=citations,
            verification=verification_metrics,
            latency_ms=latency,
            retrieved_chunks_count=len(hits),
        )

        # 6. Luu cache Redis
        if use_cache:
            cache.set(cache_key, response.model_dump(), timeout=self.config.cache_ttl_seconds)

        return response

    def _generate_answer(self, messages: list[dict[str, str]]) -> str:
        """Goi Groq hoac fallback sang Gemini / Local Heuristic."""
        # 1. Thu goi Groq LLM
        groq_api_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
        if groq_api_key:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            models_to_try = [
                getattr(settings, "AI_MODEL_GROQ", "openai/gpt-oss-120b"),
                getattr(settings, "AI_MODEL_GROQ_BACKUP", "openai/gpt-oss-20b"),
                "llama-3.1-8b-instant",
            ]
            for model_name in models_to_try:
                try:
                    completion = client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=800,
                    )
                    content = completion.choices[0].message.content or ""
                    if content.strip():
                        return content.strip()
                except Exception as e:
                    logger.warning("Groq model %s gap su co: %s", model_name, e)

        # 2. Thu goi Gemini LLM neu Groq gap loi
        gemini_api_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
        if gemini_api_key:
            for gemini_model in ["gemini-2.5-flash", "gemini-1.5-flash"]:
                try:
                    from google import genai
                    client = genai.Client(api_key=gemini_api_key)
                    prompt_text = "\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in messages])
                    res = client.models.generate_content(
                        model=gemini_model,
                        contents=prompt_text,
                    )
                    if res and res.text and res.text.strip():
                        return res.text.strip()
                except Exception as e:
                    logger.warning("Gemini model %s gap su co: %s", gemini_model, e)

        # 3. Fallback sang Escape Hatch neu khong co LLM ket noi
        return ESCAPE_HATCH_PHRASE

    def _invalidate_query_cache(self) -> None:
        """Xoa toan bo cache truy van cu (ho tro ca Redis va locallock)."""
        try:
            # Thu xoa qua pattern neu backend la Redis
            if hasattr(cache, "delete_pattern"):
                cache.delete_pattern("codebase_rag_query:*")
        except Exception:
            pass


_service_singleton: CodebaseRAGService | None = None


def get_rag_service() -> CodebaseRAGService:
    """Tra ve singleton cua CodebaseRAGService."""
    global _service_singleton
    if _service_singleton is None:
        _service_singleton = CodebaseRAGService()
    return _service_singleton
