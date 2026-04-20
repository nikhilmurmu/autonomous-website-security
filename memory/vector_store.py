"""
ChromaDB vector store for storing and retrieving past security fixes.
"""
import json
import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from loguru import logger
from config.settings import MEMORY_DIR

class FixMemoryStore:
    def __init__(self, collection_name: str = "security_fixes"):
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=str(MEMORY_DIR),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Use sentence-transformers for embeddings (local, no API calls)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB collection '{collection_name}' ready with {self.collection.count()} documents")
    
    def store_fix(self, issue_summary: str, fix_plan: Dict[str, Any], metadata: Optional[Dict] = None):
        """
        Store a fix plan with its issue summary as the searchable text.
        """
        # Generate a unique ID based on timestamp and hash
        import hashlib
        import time
        doc_id = hashlib.md5(f"{issue_summary}{time.time()}".encode()).hexdigest()[:16]
        
        # Prepare metadata
        meta = metadata or {}
        meta["timestamp"] = time.time()
        
        # Store the full fix plan as JSON string in metadata (ChromaDB has size limits, but fine for now)
        meta["fix_plan_json"] = json.dumps(fix_plan)
        
        self.collection.add(
            documents=[issue_summary],
            metadatas=[meta],
            ids=[doc_id]
        )
        logger.info(f"Stored fix in memory with ID: {doc_id}")
        return doc_id
    
    def find_similar_fixes(self, issue_summary: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        Search for similar past issues and return their fix plans.
        """
        if self.collection.count() == 0:
            logger.info("Memory is empty, no similar fixes found.")
            return []
        
        results = self.collection.query(
            query_texts=[issue_summary],
            n_results=min(n_results, self.collection.count())
        )
        
        similar_fixes = []
        if results['ids'] and results['ids'][0]:
            for i, doc_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                distance = results['distances'][0][i] if results['distances'] else None
                fix_plan = json.loads(metadata.get("fix_plan_json", "{}"))
                similar_fixes.append({
                    "id": doc_id,
                    "issue_summary": results['documents'][0][i],
                    "fix_plan": fix_plan,
                    "similarity_score": 1 - distance if distance else None,
                    "timestamp": metadata.get("timestamp")
                })
        
        logger.info(f"Found {len(similar_fixes)} similar past fixes")
        return similar_fixes
    
    def clear(self):
        """Delete all documents (for testing)."""
        self.client.delete_collection(self.collection_name)
        self.collection = self.client.create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_fn
        )
        logger.info("Memory cleared")

# Singleton instance
_memory_store = None

def get_memory_store() -> FixMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = FixMemoryStore()
    return _memory_store