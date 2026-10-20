"""
Vector Store Wrapper su dung ChromaDB.
Ho tro che do Persistent tren dia va In-Memory, cai dat Upsert Idempotent.
"""

import hashlib
import logging
from typing import Any
import chromadb
from chromadb.utils import embedding_functions
from ..schemas import CodeChunk, ChunkMetadata, SearchHit
from ..config import get_rag_config

logger = logging.getLogger(__name__)


class ChromaStore:
    """Lop dieu phoi Vector Database ChromaDB voi co che Idempotent."""

    def __init__(
        self,
        persist_dir: str | None = None,
        collection_name: str | None = None,
        is_memory: bool = False,
    ):
        config = get_rag_config()
        self.collection_name = collection_name or config.collection_name

        if is_memory:
            self.client = chromadb.EphemeralClient()
        else:
            dir_path = str(persist_dir or config.chroma_persist_dir)
            self.client = chromadb.PersistentClient(path=dir_path)

        # Su dung local ONNX embedding mac dinh cua Chroma (0 token cost, offline)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn,
            metadata={"description": "Music Tracking Codebase & Docs Vector Store"},
        )

    def upsert_file_idempotent(self, path: str, chunks: list[CodeChunk]) -> None:
        """Xoa toan bo chunk cu cua file theo doc_id truoc khi nap chunk moi."""
        doc_id = hashlib.sha1(path.encode("utf-8")).hexdigest()[:12]

        try:
            # Xoa toan bo chunk cu
            self.collection.delete(where={"doc_id": doc_id})
        except Exception:
            pass

        if not chunks:
            return

        docs: list[str] = []
        metas: list[dict[str, Any]] = []
        ids: list[str] = []

        for i, chunk in enumerate(chunks):
            chunk.metadata.doc_id = doc_id
            chunk.metadata.chunk_id = f"{doc_id}:{i}"
            chunk.metadata.path = path

            doc, meta, c_id = chunk.to_chroma_format()
            docs.append(doc)
            metas.append(meta)
            ids.append(c_id)

        self.collection.add(documents=docs, metadatas=metas, ids=ids)

    def upsert_chunks(self, chunks: list[CodeChunk]) -> None:
        """Nap danh sach nhieu chunk (nhom theo file de upsert idempotent)."""
        if not chunks:
            return

        # Nhom theo duong dan file
        file_chunks_map: dict[str, list[CodeChunk]] = {}
        for c in chunks:
            file_chunks_map.setdefault(c.metadata.path, []).append(c)

        for path, file_chunks in file_chunks_map.items():
            self.upsert_file_idempotent(path, file_chunks)

    def search_dense(
        self, query: str, top_k: int = 50, filters: dict[str, Any] | None = None
    ) -> list[SearchHit]:
        """Truy xuat dense vector embeddings tu ChromaDB."""
        if self.collection.count() == 0:
            return []

        clean_filter = None
        if filters:
            conditions = [{k: {"$eq": v}} for k, v in filters.items()]
            clean_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count()),
                where=clean_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning("Loi truy van Chroma dense search: %s", e)
            return []

        hits: list[SearchHit] = []
        if not results or not results["documents"] or not results["documents"][0]:
            return hits

        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else []
        distances = results["distances"][0] if results.get("distances") else []

        for doc, meta_dict, dist in zip(docs, metas, distances):
            meta = ChunkMetadata(
                doc_id=meta_dict.get("doc_id", ""),
                chunk_id=meta_dict.get("chunk_id", ""),
                path=meta_dict.get("path", ""),
                source_type=meta_dict.get("source_type", "code"),
                symbol=meta_dict.get("symbol") or None,
                line_start=int(meta_dict.get("line_start", 1)),
                line_end=int(meta_dict.get("line_end", 1)),
                heading_path=meta_dict.get("heading_path") or None,
                status=meta_dict.get("status", "active"),
                app_name=meta_dict.get("app_name") or None,
            )
            chunk = CodeChunk(text=doc, metadata=meta)
            # Chuyen khoang cach thanh diem tuong dong (similarity = 1 / (1 + distance))
            similarity = 1.0 / (1.0 + float(dist)) if dist is not None else 0.0
            hits.append(SearchHit(chunk=chunk, dense_score=similarity))

        return hits

    def count(self) -> int:
        """Tra ve tong so chunk trong collection."""
        return self.collection.count()

    def clear(self) -> None:
        """Xoa toan bo du lieu trong collection."""
        try:
            self.client.delete_collection(name=self.collection_name)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_fn,
            )
        except Exception:
            pass
