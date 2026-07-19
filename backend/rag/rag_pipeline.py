import os
import logging
from typing import List, Dict, Any
from config.config import settings
from rag.pdf_loader import extract_chunks_from_pdf, extract_chunks_from_text, extract_chunks_from_docx
from embeddings.embedding_model import embed_chunks, embed_query
from vectorstore.vector_store import LocalVectorStore

logger = logging.getLogger("customer_support_backend")

# Global singleton VectorStore instance (automatically loads persisted files on init)
vector_store = LocalVectorStore(dimension=384)


def sync_kb_db_with_files(kb_dir: str, current_manifest: dict):
    """
    Synchronizes MongoDB knowledge_base collection with physical documents in knowledge_base directory.
    Calculates exact chunk count for each file dynamically based on vector store metadata mappings.
    """
    try:
        from database.database import get_knowledge_base_collection
        from datetime import datetime, timezone
        import uuid

        kb_coll = get_knowledge_base_collection()
        physical_files = set()

        if os.path.exists(kb_dir):
            for filename in os.listdir(kb_dir):
                file_path = os.path.join(kb_dir, filename)
                if os.path.isdir(file_path) or filename in [
                    os.path.basename(settings.VECTOR_INDEX_PATH),
                    os.path.basename(settings.VECTOR_METADATA_PATH)
                ]:
                    continue
                ext = filename.split(".")[-1].lower() if "." in filename else ""
                if ext not in ["pdf", "txt", "md", "docx"]:
                    continue

                physical_files.add(filename)

                # Count active chunks in vector store
                file_chunks_count = 0
                for vid, metadata in vector_store._metadata_store.items():
                    if metadata.get("metadata", {}).get("source") == filename:
                        file_chunks_count += 1

                stat = os.stat(file_path)
                existing = kb_coll.find_one({"filename": filename})
                
                if existing:
                    kb_coll.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "chunk_count": file_chunks_count,
                            "embedding_status": "completed" if file_chunks_count > 0 else "failed",
                            "indexed_status": "completed" if file_chunks_count > 0 else "failed",
                            "file_size": stat.st_size,
                            "last_indexed": datetime.now(timezone.utc)
                        }}
                    )
                else:
                    now = datetime.now(timezone.utc)
                    kb_coll.insert_one({
                        "_id": str(uuid.uuid4()),
                        "filename": filename,
                        "upload_date": now,
                        "file_type": ext,
                        "file_size": stat.st_size,
                        "uploaded_by": "system",
                        "chunk_count": file_chunks_count,
                        "embedding_status": "completed" if file_chunks_count > 0 else "failed",
                        "indexed_status": "completed" if file_chunks_count > 0 else "failed",
                        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                        "last_indexed": now
                    })

        # Remove database references to documents no longer present on filesystem
        db_docs = list(kb_coll.find({}))
        for doc in db_docs:
            if doc["filename"] not in physical_files:
                kb_coll.delete_one({"_id": doc["_id"]})
                
    except Exception as e:
        logger.error(f"Error syncing knowledge base metadata collection: {str(e)}", exc_info=True)


def initialize_rag_pipeline(force_rebuild: bool = False) -> None:
    """
    Scans the configured knowledge base folder, processes document files,
    embeds document segments, and indexes them into the local FAISS index.
    Saves updates to disk.
    """
    logger.info("Initializing RAG ingestion pipeline...")
    
    # Resolve absolute path to the project root (three levels up from backend/rag/rag_pipeline.py)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    kb_dir = os.path.join(project_root, "knowledge_base")
    
    # Build current files manifest to detect modifications
    current_manifest = {}
    if os.path.exists(kb_dir):
        for filename in os.listdir(kb_dir):
            file_path = os.path.join(kb_dir, filename)
            if os.path.isdir(file_path):
                continue
            if filename in [
                os.path.basename(settings.VECTOR_INDEX_PATH),
                os.path.basename(settings.VECTOR_METADATA_PATH)
            ]:
                continue
            ext = filename.split(".")[-1].lower() if "." in filename else ""
            if ext not in ["pdf", "txt", "md", "docx"]:
                continue
            try:
                stat = os.stat(file_path)
                current_manifest[filename] = {
                    "mtime": stat.st_mtime,
                    "size": stat.st_size
                }
            except Exception as e:
                logger.warning(f"Failed to stat knowledge base file '{filename}': {str(e)}")

    # Check if index already has populated vectors and we aren't forcing a rebuild
    has_vectors = vector_store._index.ntotal > 0
    saved_manifest = vector_store._metadata_store.get("__manifest__", {})
    manifests_match = (current_manifest == saved_manifest)
    
    if has_vectors and not force_rebuild and manifests_match:
        logger.info(f"RAG pipeline initialized: active FAISS index loaded from disk ({vector_store._index.ntotal} vectors). File manifest matches, skipping rebuild.")
        sync_kb_db_with_files(kb_dir, current_manifest)
        return
        
    if not force_rebuild and not manifests_match:
        logger.info("Knowledge base file modifications detected or manifest missing. Rebuilding vector store index...")
        
    if not os.path.exists(kb_dir):
        logger.warning(f"Knowledge base directory '{kb_dir}' missing. Creating empty directory.")
        os.makedirs(kb_dir, exist_ok=True)
        sync_kb_db_with_files(kb_dir, current_manifest)
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
        if ext not in ["pdf", "txt", "md", "docx"]:
            logger.debug(f"Skipping file '{filename}' with unsupported extension.")
            continue
            
        try:
            if ext == "pdf":
                with open(file_path, "rb") as f:
                     file_bytes = f.read()
                file_chunks = extract_chunks_from_pdf(file_bytes, filename)
            elif ext == "docx":
                with open(file_path, "rb") as f:
                     file_bytes = f.read()
                file_chunks = extract_chunks_from_docx(file_bytes, filename)
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
        # Ensure we clear memory
        vector_store.clear()
        with vector_store._lock:
            vector_store._metadata_store["__manifest__"] = current_manifest
            vector_store.save_to_disk()
        sync_kb_db_with_files(kb_dir, current_manifest)
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
        
        # Record manifest inside metadata store and re-save to disk
        with vector_store._lock:
            vector_store._metadata_store["__manifest__"] = current_manifest
            vector_store.save_to_disk()
            
        logger.info(f"Ingested RAG pipeline complete. Total indexed chunks: {vector_store._index.ntotal}")
        
    except Exception as e:
        logger.error(f"Failed to generate embeddings or index chunks during pipeline build: {str(e)}", exc_info=True)
        
    sync_kb_db_with_files(kb_dir, current_manifest)


def query_kb(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Translates user query string into a vector, queries the FAISS vector store,
    and returns similarity matches as search results.
    """
    import time
    start_time = time.perf_counter()
    logger.info({
        "event": "rag_retrieval_started",
        "top_k": top_k
    })
    
    if not query or not query.strip():
        logger.warning({
            "event": "rag_retrieval_completed",
            "top_k": top_k,
            "retrieval_count": 0,
            "duration_ms": 0,
            "detail": "empty query"
        })
        return []
        
    try:
        from utils.tracing import pipeline_tracker_var
        tracker = pipeline_tracker_var.get()

        # Convert search query into unit vector
        embed_start = time.perf_counter()
        query_vector = embed_query(query)
        embedding_generation_ms = (time.perf_counter() - embed_start) * 1000.0
        
        # similarity matching top_k
        search_start = time.perf_counter()
        results = vector_store.search(query_vector, top_k=top_k)
        faiss_search_ms = (time.perf_counter() - search_start) * 1000.0
        
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        if tracker:
            tracker.embedding_generation_ms = embedding_generation_ms
            tracker.faiss_search_ms = faiss_search_ms
            tracker.rag_retrieval_total_ms = duration_ms
            
        source_names = list(set(r.get("metadata", {}).get("source", "unknown") for r in results))
        
        logger.info({
            "event": "rag_retrieval_completed",
            "top_k": top_k,
            "retrieval_count": len(results),
            "sources": source_names,
            "duration_ms": int(duration_ms)
        })
        return results
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        logger.error({
            "event": "rag_retrieval_failed",
            "exception_type": type(e).__name__,
            "error_detail": str(e),
            "duration_ms": int(duration_ms)
        })
        return []
