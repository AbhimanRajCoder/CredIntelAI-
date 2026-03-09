"""
Pinecone Cloud Vector Store for Intelli-Credit.
Replaces ChromaDB for robust, cloud-native semantic search.
"""

import logging
import os
import time
from typing import List, Optional, Dict, Any

from pinecone import Pinecone, ServerlessSpec
from langchain_huggingface import HuggingFaceEmbeddings

from app.config import get_settings

logger = logging.getLogger(__name__)


class PineconeStore:
    """Pinecone vector storage service with local HuggingFace embeddings."""

    def __init__(self):
        self.settings = get_settings()
        self._pc: Optional[Pinecone] = None
        self._index = None
        self._embeddings = None

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """Lazy-initialize embeddings model."""
        if self._embeddings is None:
            logger.info(f"Loading embedding model: {self.settings.EMBEDDING_MODEL}...")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True}
            )
        return self._embeddings

    @property
    def pc(self) -> Pinecone:
        """Lazy-initialize Pinecone client."""
        if self._pc is None:
            if not self.settings.PINECONE_API_KEY:
                logger.error("PINECONE_API_KEY not set in environment.")
                raise ValueError("Missing PINECONE_API_KEY")
                
            self._pc = Pinecone(api_key=self.settings.PINECONE_API_KEY)
            logger.info("Pinecone client initialized")
        return self._pc

    @property
    def index(self):
        """Get or create the Pinecone index with serverless configuration."""
        if self._index is None:
            index_name = self.settings.PINECONE_INDEX_NAME
            
            # Check if index exists, if not create it
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if index_name not in existing_indexes:
                logger.info(f"Creating new Pinecone index: {index_name}")
                self.pc.create_index(
                    name=index_name,
                    dimension=384,  # dimension for all-MiniLM-L6-v2
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region=self.settings.PINECONE_ENVIRONMENT
                    )
                )
                # Wait for index to be ready
                while not self.pc.describe_index(index_name).status['ready']:
                    time.sleep(1)
            
            self._index = self.pc.Index(index_name)
            logger.info(f"Pinecone index '{index_name}' ready")
        return self._index

    def add_documents(
        self,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        analysis_id: Optional[str] = None,
    ) -> None:
        """Add documents by generating embeddings and upserting to Pinecone."""
        if not documents:
            return

        # Generate IDs if not provided
        if ids is None:
            prefix = analysis_id or "doc"
            ids = [f"{prefix}_chunk_{int(time.time())}_{i}" for i in range(len(documents))]

        # Add analysis_id to metadata
        if metadatas is None:
            metadatas = [{}] * len(documents)
            
        # Clear None values and ensure string-friendliness for Pinecone metadata
        cleaned_metadatas = []
        for meta in metadatas:
            m = {str(k): str(v) for k, v in meta.items() if v is not None}
            if analysis_id:
                m["analysis_id"] = str(analysis_id)
            cleaned_metadatas.append(m)

        # Generate embeddings
        logger.info(f"Generating embeddings for {len(documents)} snippets...")
        vectors = self.embeddings.embed_documents(documents)

        # Build Pinecone vectors (id, vector, metadata)
        upsert_data = []
        for i in range(len(documents)):
            # Store the actual text in metadata so we can retrieve it
            meta = cleaned_metadatas[i]
            meta["text"] = documents[i] 
            upsert_data.append((ids[i], vectors[i], meta))

        # Batch upsert
        batch_size = 100
        for i in range(0, len(upsert_data), batch_size):
            batch = upsert_data[i : i + batch_size]
            self.index.upsert(vectors=batch)

        logger.info(f"Successfully upserted {len(documents)} vectors to Pinecone")

    def query(
        self,
        query_text: str,
        n_results: int = 5,
        analysis_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query Pinecone for semantic matches."""
        # Generate query vector
        query_vector = self.embeddings.embed_query(query_text)

        # Build filter
        filter_dict = {}
        if analysis_id:
            filter_dict["analysis_id"] = {"$eq": str(analysis_id)}

        # Perform query
        results = self.index.query(
            vector=query_vector,
            top_k=n_results,
            filter=filter_dict if filter_dict else None,
            include_metadata=True
        )

        # Reformat into Chroma-like structure for backward compatibility
        formatted = {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
            "documents": [[]]
        }

        for match in results.matches:
            formatted["ids"][0].append(match.id)
            formatted["distances"][0].append(1 - match.score) # Cosine distance
            formatted["metadatas"][0].append(match.metadata)
            formatted["documents"][0].append(match.metadata.get("text", ""))

        return formatted

    def store_extracted_text(
        self,
        text: str,
        analysis_id: str,
        chunk_size: int = 1000,
        overlap: int = 200,
        page_metadata: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """Chunk and store document text."""
        chunks = self._chunk_text(text, chunk_size, overlap)
        if not chunks:
            return 0

        ids = [f"{analysis_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []

        for i in range(len(chunks)):
            meta = {
                "analysis_id": analysis_id,
                "chunk_index": i,
                "type": "narrative",
            }
            if page_metadata and i < len(page_metadata):
                for key in ("type", "page_num", "section", "year"):
                    if key in page_metadata[i]:
                        meta[key] = str(page_metadata[i][key])
            metadatas.append(meta)

        self.add_documents(
            documents=chunks,
            metadatas=metadatas,
            ids=ids,
            analysis_id=analysis_id,
        )
        return len(chunks)

    def store_structured_chunks(self, chunks: List[Dict[str, Any]], analysis_id: str) -> int:
        """Store structured financial chunks."""
        if not chunks:
            return 0

        docs, metas, ids = [], [], []
        for i, chunk in enumerate(chunks):
            text = chunk.get("text", "").strip()
            if not text: continue
            
            docs.append(text)
            ids.append(f"{analysis_id}_struct_{i}")
            metas.append({
                "type": str(chunk.get("type", "narrative")),
                "page_num": str(chunk.get("page_num", "")),
                "section": str(chunk.get("section", "")),
                "year": str(chunk.get("year", "")),
            })

        self.add_documents(docs, metas, ids, analysis_id)
        return len(docs)

    def query_by_metadata(
        self,
        query_text: str,
        analysis_id: str,
        n_results: int = 5,
        section: Optional[str] = None,
        chunk_type: Optional[str] = None,
        year: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Targeted RAG query."""
        query_vector = self.embeddings.embed_query(query_text)
        
        filter_dict = {"analysis_id": {"$eq": str(analysis_id)}}
        if section: filter_dict["section"] = {"$eq": str(section)}
        if chunk_type: filter_dict["type"] = {"$eq": str(chunk_type)}
        if year: filter_dict["year"] = {"$eq": str(year)}

        results = self.index.query(
            vector=query_vector,
            top_k=n_results,
            filter=filter_dict,
            include_metadata=True
        )

        formatted = {"ids": [[]], "distances": [[]], "metadatas": [[]], "documents": [[]]}
        for match in results.matches:
            formatted["ids"][0].append(match.id)
            formatted["metadatas"][0].append(match.metadata)
            formatted["documents"][0].append(match.metadata.get("text", ""))
        
        return formatted

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        if not text: return []
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            if chunk.strip(): chunks.append(chunk.strip())
            start = end - overlap
        return chunks

    def delete_analysis_data(self, analysis_id: str) -> None:
        """Clear vectors for a session."""
        try:
            self.index.delete(filter={"analysis_id": {"$eq": str(analysis_id)}})
            logger.info(f"Cleared Pinecone data for session {analysis_id}")
        except Exception as e:
            logger.error(f"Failed to delete session data: {e}")


# Singleton
_pinecone_store: Optional[PineconeStore] = None

def get_pinecone_store() -> PineconeStore:
    global _pinecone_store
    if _pinecone_store is None:
        _pinecone_store = PineconeStore()
    return _pinecone_store
