import os
import json
import logging
import threading
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from config.config import settings

logger = logging.getLogger("customer_support_backend")


class LocalVectorStore:
    """
    Manages a local FAISS CPU Index with companion JSON metadata mapping.
    Uses Inner Product (IndexFlatIP) search strategy, which is mathematically
    equivalent to Cosine Similarity when input vectors are L2-normalized.
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._lock = threading.RLock()
        
        # Resolve absolute paths relative to project root (three levels up from backend/vectorstore/vector_store.py)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.index_path = os.path.join(project_root, settings.VECTOR_INDEX_PATH)
        self.metadata_path = os.path.join(project_root, settings.VECTOR_METADATA_PATH)
        
        # Initialize empty defaults
        self._index: faiss.Index = faiss.IndexFlatIP(self.dimension)
        # Maps vector indices (int) to chunk dict payloads
        self._metadata_store: Dict[str, Dict[str, Any]] = {}
        
        # Try loading index automatically on initialization
        self.load_from_disk()

    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        """
        Adds vector embeddings to the FAISS index and records the corresponding metadata.
        Saves updates to disk.
        """
        with self._lock:
            if not chunks:
                logger.warning("No chunks passed to add_chunks. Skipping execution.")
                return
                
            if embeddings.shape[0] != len(chunks):
                logger.error(f"Dimension mismatch: Received {embeddings.shape[0]} embeddings for {len(chunks)} chunks.")
                raise ValueError("The number of embeddings must match the number of document chunks.")
                
            if embeddings.shape[1] != self.dimension:
                logger.error(f"Embedding dimension mismatch: Expected {self.dimension}, got {embeddings.shape[1]}")
                raise ValueError(f"Embedding vectors must have dimension size {self.dimension}.")
                
            # Ensure float32 formatting
            embeddings_f32 = embeddings.astype(np.float32)
            
            # Calculate current index start pointer
            start_id = self._index.ntotal
            
            # Add to FAISS index
            self._index.add(embeddings_f32)
            
            # Record companion metadata maps (using strings for JSON compatibility keys)
            for idx, chunk in enumerate(chunks):
                vector_id = str(start_id + idx)
                self._metadata_store[vector_id] = {
                    "content": chunk["content"],
                    "metadata": chunk.get("metadata", {})
                }
                
            logger.info(f"Added {len(chunks)} vectors to the index. Total vectors: {self._index.ntotal}")
            self.save_to_disk()

    def search(self, query_vector: np.ndarray, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Searches the FAISS index for the top-k nearest chunks to the query vector.
        Returns list of chunks containing content, metadata, and similarity score.
        """
        with self._lock:
            if self._index.ntotal == 0:
                logger.warning("Query received but index is empty. Returning empty list.")
                return []
                
            # Ensure query vector is shape (1, dimension)
            if query_vector.ndim == 1:
                query_vector = np.expand_dims(query_vector, axis=0)
                
            if query_vector.shape[1] != self.dimension:
                logger.error(f"Query vector dimension mismatch: Expected {self.dimension}, got {query_vector.shape[1]}")
                raise ValueError(f"Query vector dimension must match index dimension: {self.dimension}")
                
            # Format query array as float32
            query_f32 = query_vector.astype(np.float32)
            
            # Execute FAISS search
            # IndexFlatIP returns similarity scores in distances, and mapping ids in indices
            distances, indices = self._index.search(query_f32, top_k)
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                # FAISS returns -1 index if not enough vectors populate the database
                if idx == -1:
                    continue
                    
                str_idx = str(idx)
                if str_idx in self._metadata_store:
                    chunk_data = self._metadata_store[str_idx]
                    results.append({
                        "content": chunk_data["content"],
                        "metadata": chunk_data["metadata"],
                        "score": float(dist)
                    })
                else:
                    logger.warning(f"Vector index ID {idx} matched in FAISS but missing from metadata store.")
                    
            logger.info(f"Found {len(results)} matches for vector query.")
            return results

    def clear(self) -> None:
        """
        Resets the FAISS index and metadata store in-memory.
        """
        with self._lock:
            logger.info("Clearing in-memory FAISS index and metadata store.")
            self._index = faiss.IndexFlatIP(self.dimension)
            self._metadata_store = {}

    def save_to_disk(self) -> None:
        """
        Serializes the active FAISS index binary and json metadata mapper to settings paths.
        """
        with self._lock:
            try:
                # Create base directories if missing
                index_dir = os.path.dirname(self.index_path)
                if index_dir:
                    os.makedirs(index_dir, exist_ok=True)
                    
                # Write FAISS index
                faiss.write_index(self._index, self.index_path)
                
                # Write metadata json mapping
                with open(self.metadata_path, "w", encoding="utf-8") as f:
                    json.dump(self._metadata_store, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"Successfully saved FAISS index and metadata to disk.")
            except Exception as e:
                logger.error(f"Error saving FAISS index to disk: {str(e)}", exc_info=True)
                raise RuntimeError(f"Failed to persist index files to disk: {str(e)}")

    def load_from_disk(self) -> None:
        """
        Deserializes index binary and companion metadata map from disk.
        Gracefully falls back to empty initialized state on corrupt or missing indexes.
        """
        with self._lock:
            # If files are missing, initialize fresh
            if not os.path.exists(self.index_path) or not os.path.exists(self.metadata_path):
                logger.info("Local persisted index or metadata files missing. Initializing empty FAISS index.")
                self._index = faiss.IndexFlatIP(self.dimension)
                self._metadata_store = {}
                return
                
            try:
                # Read index binary
                loaded_index = faiss.read_index(self.index_path)
                
                # Validate loaded dimension matches configured model output
                if loaded_index.d != self.dimension:
                    logger.error(f"Persisted index dimension mismatch: Loaded index has d={loaded_index.d}, expected {self.dimension}.")
                    raise ValueError("Persisted index dimension size mismatch.")
                    
                # Read JSON metadata
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    loaded_metadata = json.load(f)
                    
                # Sanity check matching vector totals
                if len(loaded_metadata) != loaded_index.ntotal:
                    logger.warning(f"Count mismatch: Metadata has {len(loaded_metadata)} keys, Index has {loaded_index.ntotal} vectors. Index might be corrupted.")
                    
                self._index = loaded_index
                self._metadata_store = loaded_metadata
                logger.info(f"Successfully loaded persisted FAISS index containing {self._index.ntotal} vectors.")
                
            except Exception as e:
                logger.critical(f"Failed to load persisted FAISS index: {str(e)}", exc_info=True)
                # Fallback to empty initialized state
                self._index = faiss.IndexFlatIP(self.dimension)
                self._metadata_store = {}
