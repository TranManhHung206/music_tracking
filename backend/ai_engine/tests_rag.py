"""
Unit tests toan dien cho he thong RAG Codebase (Knowledge Harness).
Kiem thu Ingestion AST, Idempotent Stores, Hybrid Search RRF k=60, Citation Validator va API Views.
"""

from pathlib import Path
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from .services.rag.schemas import (
    CodeChunk,
    ChunkMetadata,
    SourceType,
    SearchHit,
)
from .services.rag.ingestion.python_chunker import PythonASTChunker
from .services.rag.ingestion.doc_chunker import MarkdownDocChunker
from .services.rag.vectorstore.chroma_store import ChromaStore
from .services.rag.vectorstore.bm25_store import BM25Store
from .services.rag.retrieval.hybrid_retriever import rrf, HybridRetriever
from .services.rag.retrieval.reranker import TermSemanticReranker
from .services.rag.grounding.prompt_builder import (
    GroundingPromptBuilder,
    ESCAPE_HATCH_PHRASE,
)
from .services.rag.grounding.citation_validator import CitationValidator
from .services.rag.tools.search_codebase import search_codebase, SEARCH_CODEBASE_TOOL_SPEC

User = get_user_model()


class PythonASTChunkerTestCase(TestCase):
    """Kiem thu AST Chunker cho ma nguon Python."""

    def setUp(self):
        self.chunker = PythonASTChunker()

    def test_chunk_class_and_methods(self):
        code = '''"""Module docstring."""

class SessionManager:
    """Quan ly phien."""
    def __init__(self, sid: str):
        self.sid = sid

    def refresh_token(self) -> str:
        return "token_123"

def standalone_helper():
    return 42
'''
        chunks = self.chunker.chunk_code(code, "test/session.py", "users")
        self.assertGreater(len(chunks), 0)

        symbols = [c.metadata.symbol for c in chunks if c.metadata.symbol]
        self.assertTrue(any("SessionManager" in s for s in symbols))
        self.assertTrue(any("standalone_helper" in s for s in symbols))

        for c in chunks:
            self.assertEqual(c.metadata.path, "test/session.py")
            self.assertGreaterEqual(c.metadata.line_start, 1)
            self.assertGreaterEqual(c.metadata.line_end, c.metadata.line_start)


class MarkdownDocChunkerTestCase(TestCase):
    """Kiem thu Markdown Chunker theo tieu de phan cap."""

    def setUp(self):
        self.chunker = MarkdownDocChunker()

    def test_chunk_markdown_headings(self):
        md_text = """# He thong Tracking

Gioi thieu tong quan ve he thong tracking.

## API Endpoints

Danh sach cac endpoint API.

```python
# Khong duoc cat ngang code block
def api_call():
    pass
```

### Chi tiet Endpoint
Thong so chi tiet.
"""
        chunks = self.chunker.chunk_text(md_text, "docs/api.md")
        self.assertGreater(len(chunks), 0)

        headings = [c.metadata.heading_path for c in chunks if c.metadata.heading_path]
        self.assertTrue(any("API Endpoints" in h for h in headings))


class IdempotentStoresTestCase(TestCase):
    """Kiem thu tinh chat Idempotent (chay lai khong trung lap) tren Vector va BM25 Store."""

    def setUp(self):
        self.chroma = ChromaStore(is_memory=True, collection_name="test_idempotent_col")
        self.bm25 = BM25Store()

    def test_upsert_idempotent(self):
        meta1 = ChunkMetadata(
            doc_id="doc1",
            chunk_id="doc1:0",
            path="backend/test.py",
            source_type=SourceType.CODE.value,
            symbol="test_func",
            line_start=1,
            line_end=10,
        )
        chunk1 = CodeChunk(text="def test_func(): return True", metadata=meta1)

        # Nap lan 1
        self.chroma.upsert_file_idempotent("backend/test.py", [chunk1])
        self.bm25.upsert_file_idempotent("backend/test.py", [chunk1])

        self.assertEqual(self.chroma.count(), 1)
        self.assertEqual(self.bm25.count(), 1)

        # Nap lai lan 2 voi cung file path
        meta2 = ChunkMetadata(
            doc_id="doc1",
            chunk_id="doc1:0",
            path="backend/test.py",
            source_type=SourceType.CODE.value,
            symbol="test_func_updated",
            line_start=1,
            line_end=12,
        )
        chunk2 = CodeChunk(text="def test_func_updated(): return False", metadata=meta2)

        self.chroma.upsert_file_idempotent("backend/test.py", [chunk2])
        self.bm25.upsert_file_idempotent("backend/test.py", [chunk2])

        # So luong van phai giu nguyen la 1, khong bi nhan ban
        self.assertEqual(self.chroma.count(), 1)
        self.assertEqual(self.bm25.count(), 1)


class HybridRetrieverRRFTestCase(TestCase):
    """Kiem thu thuat toan RRF k=60 theo Slide 36 SE373."""

    def test_rrf_agreement_elevates_chunk(self):
        c1 = CodeChunk(
            text="chunk 1",
            metadata=ChunkMetadata(doc_id="d1", chunk_id="c_G3_1", path="p1.py"),
        )
        c2 = CodeChunk(
            text="chunk 2",
            metadata=ChunkMetadata(doc_id="d2", chunk_id="c_G2_2", path="p2.py"),
        )
        c3 = CodeChunk(
            text="chunk 3",
            metadata=ChunkMetadata(doc_id="d3", chunk_id="c_G3_3", path="p3.py"),
        )

        h1 = SearchHit(chunk=c1)
        h2 = SearchHit(chunk=c2)
        h3 = SearchHit(chunk=c3)

        # Vector list: c1 (hang 1), c2 (hang 2), c3 (hang 3)
        vec_list = [h1, h2, h3]
        # BM25 list: c3 (hang 1), c2 (hang 2)
        bm25_list = [h3, h2]

        merged = rrf([vec_list, bm25_list], k=60, top_n=3)
        # Chunk c_G3_3 xuat hien o ca hai danh sach voi thu hang cao phai dung dau
        self.assertEqual(merged[0].chunk.metadata.chunk_id, "c_G3_3")


class CitationValidatorTestCase(TestCase):
    """Kiem thu bo kiem dinh trich dan nguon vat ly."""

    def setUp(self):
        self.validator = CitationValidator()

    def test_escape_hatch_detection(self):
        answer = f"Toi rat tiec. {ESCAPE_HATCH_PHRASE}"
        citations, metrics = self.validator.validate(answer, [])
        self.assertTrue(metrics["is_escape_hatch"])
        self.assertTrue(metrics["all_valid"])

    def test_valid_physical_file_citation(self):
        # Su dung README.md thuc te co tren dia
        meta = ChunkMetadata(
            doc_id="doc_readme",
            chunk_id="doc_readme:0",
            path="README.md",
            source_type=SourceType.DOC.value,
            line_start=1,
            line_end=10,
        )
        hit = SearchHit(chunk=CodeChunk(text="Music Tracking Project", metadata=meta))

        answer = "Du an la he thong theo doi am nhac [S1]."
        citations, metrics = self.validator.validate(answer, [hit])

        self.assertEqual(len(citations), 1)
        self.assertEqual(citations[0].citation_id, "S1")
        self.assertEqual(metrics["citation_existence_rate"], 1.0)
        self.assertEqual(metrics["citation_accuracy"], 1.0)
        self.assertTrue(metrics["all_valid"])

    def test_hallucinated_citation_rejected(self):
        # Model bia ra nhan S99 khong co trong context
        answer = "Thong tin nay lay tu nguon ao [S99]."
        citations, metrics = self.validator.validate(answer, [])
        self.assertEqual(len(citations), 0)
        self.assertEqual(metrics["citation_existence_rate"], 0.0)


class CodebaseRAGAPITestCase(TestCase):
    """Kiem thu API endpoints /api/ai/codebase/query/ va /api/ai/codebase/index/."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="rag_test_user", password="secure_pass_123")
        self.client.force_authenticate(user=self.user)

    def test_query_endpoint_validation(self):
        response = self.client.post("/api/ai/codebase/query/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_endpoint_authenticated(self):
        payload = {
            "query": "Cơ chế mã hóa token Fernet hoạt động thế nào?",
            "mode": "full_cascade",
            "top_k": 3,
            "use_cache": False,
        }
        response = self.client.post("/api/ai/codebase/query/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("answer", response.data)
        self.assertIn("citations", response.data)
        self.assertIn("verification", response.data)
        self.assertIn("latency_ms", response.data)
