import os
import logging
from typing import List, Dict, Any
from config.config import settings
from rag.pdf_loader import extract_chunks_from_pdf, extract_chunks_from_text
from embeddings.embedding_model import embed_chunks, embed_query
from vectorstore.vector_store import LocalVectorStore

logger = logging.getLogger("customer_support_backend")

# Global singleton VectorStore instance (automatically loads persisted files on init)
vector_store = LocalVectorStore(dimension=384)


def initialize_rag_pipeline(force_rebuild: bool = False) -> None:
    """
    Scans the configured knowledge base folder, processes document files,
    embeds document segments, and indexes them into the local FAISS index.
    Saves updates to disk.
    """
    logger.info("Initializing RAG ingestion pipeline...")
    
    # Check if index already has populated vectors and we aren't forcing a rebuild
    if vector_store._index.ntotal > 0 and not force_rebuild:
        logger.info(f"RAG pipeline initialized: active FAISS index loaded from disk ({vector_store._index.ntotal} vectors).")
        return
        
    # Resolve absolute path to the project root (three levels up from backend/rag/rag_pipeline.py)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kb_dir = os.path.join(project_root, "knowledge_base")
    
    if not os.path.exists(kb_dir):
        logger.warning(f"Knowledge base directory '{kb_dir}' missing. Creating empty directory.")
        os.makedirs(kb_dir, exist_ok=True)
        return
        
    logger.info(f"Rebuilding RAG index from files under folder: '{kb_dir}'...")
    
    # Collect all support files
    all_chunks = []
    
    for filename in os.listdir(kb_dir):
        file_path = os.path.join(kb_dir, filename)
        
        # Skip directories or index database files themselves
        if os.path.isdir(file_path) or filename in [
            os.path.basename(settings.VECTOR_INDEX_PATH),
            os.path.basename(settings.VECTOR_METADATA_PATH)
        ]:
            continue
            
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in ["pdf", "txt", "md"]:
            logger.debug(f"Skipping file '{filename}' with unsupported extension.")
            continue
            
        try:
            if ext == "pdf":
                with open(file_path, "rb") as f:
                    file_bytes = f.read()
                file_chunks = extract_chunks_from_pdf(file_bytes, filename)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
                file_chunks = extract_chunks_from_text(text_content, filename, ext)
                
            all_chunks.extend(file_chunks)
            logger.info(f"Parsed {len(file_chunks)} chunks from '{filename}'.")
            
        except Exception as e:
            logger.error(f"Error parsing file '{filename}' during RAG indexing: {str(e)}")
            continue
            
    if not all_chunks:
        logger.warning("No documentation files found or no chunks could be extracted. FAISS index left empty.")
        return
        
    logger.info(f"Generating semantic vector embeddings for {len(all_chunks)} chunks...")
    try:
        # Extract plain texts
        texts = [chunk["content"] for chunk in all_chunks]
        
        # Compute high-dimensional numerical vectors (normalized unit lengths)
        embeddings = embed_chunks(texts)
        
        # Re-initialize index cleanly to prevent duplicate appends on force rebuild
        vector_store.clear()
        
        # Store index and mappings
        vector_store.add_chunks(all_chunks, embeddings)
        logger.info(f"Ingested RAG pipeline complete. Total indexed chunks: {vector_store._index.ntotal}")
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings or index chunks during pipeline build: {str(e)}", exc_info=True)


def query_kb(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Translates user query string into a vector, queries the FAISS vector store,
    and returns similarity matches as search results.
    """
    if not query or not query.strip():
        logger.warning("Empty search query received in query_kb.")
        return []
        
    try:
        # Convert search query into unit vector
        query_vector = embed_query(query)
        
        # similarity matching top_k
        results = vector_store.search(query_vector, top_k=top_k)
        return results
    except Exception as e:
        logger.error(f"Error executing similarity search in RAG query_kb: {str(e)}", exc_info=True)
        return []
