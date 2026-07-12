import logging
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer
from config.config import settings

logger = logging.getLogger("customer_support_backend")

# Global singleton model cache
_model: SentenceTransformer = None


def get_model() -> SentenceTransformer:
    """
    Lazily loads and caches the SentenceTransformer model instance.
    Prevents blocking application startup.
    """
    global _model
    import os
    if _model is None:
        model_name = settings.EMBEDDING_MODEL_NAME
        cache_dir = os.environ.get("HF_HOME", "default cache")
        logger.info(f"Loading SentenceTransformer model lazily: '{model_name}' (cache: '{cache_dir}')...")
        try:
            _model = SentenceTransformer(model_name)
            logger.info(f"SentenceTransformer model '{model_name}' loaded successfully.")
        except Exception as e:
            logger.critical(f"Failed to initialize embedding model '{model_name}': {str(e)}", exc_info=True)
            raise RuntimeError(f"Error loading embedding model: {str(e)}")
    return _model


def embed_chunks(texts: List[str]) -> np.ndarray:
    """
    Encodes a list of text chunk strings into high-dimensional vectors.
    Returns:
        np.ndarray: float32 matrix of shape (num_texts, embedding_dim) with L2-normalized unit vectors.
    """
    if not texts:
        logger.warning("Empty text list passed to embed_chunks. Returning empty array.")
        return np.empty((0, 384), dtype=np.float32)
        
    logger.info(f"Encoding {len(texts)} text chunks into embeddings...")
    try:
        model = get_model()
        # normalize_embeddings=True scales vectors to unit length (L2 norm = 1.0)
        embeddings = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        return embeddings.astype(np.float32)
    except Exception as e:
        logger.error(f"Error generating chunk embeddings: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to encode text chunks: {str(e)}")


def embed_query(query: str) -> np.ndarray:
    """
    Encodes a user query string into a high-dimensional vector.
    Returns:
        np.ndarray: float32 vector of shape (embedding_dim,) normalized to unit length.
    """
    if not query or not query.strip():
        logger.error("Query is empty or whitespace.")
        raise ValueError("Query string cannot be empty.")
        
    logger.info("Encoding query string into embedding...")
    try:
        model = get_model()
        embedding = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
        return embedding.astype(np.float32)
    except Exception as e:
        logger.error(f"Error generating query embedding: {str(e)}", exc_info=True)
        raise RuntimeError(f"Failed to encode query string: {str(e)}")
