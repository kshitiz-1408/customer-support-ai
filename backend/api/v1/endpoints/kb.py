from typing import List, Optional
import logging
from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File
from models.kb import KBArticle, KBArticleCreate, KBArticleUpdate, KBSearchResult, KBChunk, KBSearchQuery
from services.kb_service import KBService
from rag.pdf_loader import extract_chunks_from_pdf, extract_chunks_from_text
from embeddings.embedding_model import embed_chunks
from rag.rag_pipeline import vector_store, query_kb

logger = logging.getLogger("customer_support_backend")

router = APIRouter()


@router.post("/", response_model=KBArticle, status_code=status.HTTP_201_CREATED)
def create_article(article_in: KBArticleCreate):
    """Publish a new article to the knowledge base."""
    return KBService.create(article_in)


@router.get("/", response_model=List[KBArticle])
def list_articles(category: Optional[str] = Query(None, description="Filter by category")):
    """List all knowledge base articles, optionally filtered by category."""
    return KBService.get_all(category=category)


@router.get("/search", response_model=List[KBSearchResult])
def search_articles(q: str = Query("", description="Keywords search")):
    """Search articles by matching query keywords against title, content, or tags."""
    return KBService.search(query=q)


@router.get("/chunks", response_model=List[KBChunk])
def list_chunks():
    """
    List all ingested chunks in the knowledge base.
    Must be defined before path parameter routes (like /{article_id}) to prevent dynamic routing conflicts.
    """
    return KBService.get_chunks()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT, or MD) to ingest, chunk, embed, and index in FAISS.
    Must be defined before path parameter routes (like /{article_id}) to prevent dynamic routing conflicts.
    """
    filename = file.filename or "uploaded_document"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    
    if ext not in ["pdf", "txt", "md"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Only PDF (.pdf), TXT (.txt), and MD (.md) files are supported."
        )
        
    try:
        file_bytes = await file.read()
        
        if ext == "pdf":
            chunks = extract_chunks_from_pdf(file_bytes, filename)
            doc_type = "pdf"
        else:
            try:
                text_content = file_bytes.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("Failed to decode text file. Ensure it is UTF-8 encoded.")
            chunks = extract_chunks_from_text(text_content, filename, ext)
            doc_type = ext
            
        import asyncio
        
        # Calculate embeddings for the chunks
        logger.info(f"Computing embeddings for {len(chunks)} uploaded chunks...")
        texts = [c["content"] for c in chunks]
        embeddings = await asyncio.to_thread(embed_chunks, texts)
        
        # Add to FAISS vector store
        logger.info(f"Adding chunks to FAISS vector store database...")
        await asyncio.to_thread(vector_store.add_chunks, chunks, embeddings)
            
        # Save to memory KBService store for listing/tracking
        added_chunks = KBService.add_chunks(chunks)
        
        return {
            "filename": filename,
            "type": doc_type,
            "chunks_count": len(added_chunks),
            "message": f"Successfully ingested, embedded, and indexed {len(added_chunks)} chunks from '{filename}'."
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing upload: {str(e)}"
        )


@router.post("/search", status_code=status.HTTP_200_OK)
def search_knowledge_base(payload: KBSearchQuery):
    """
    Search the RAG knowledge base via semantic vector similarity.
    Returns matched chunks and companion source metadata.
    Must be defined before path parameter routes (like /{article_id}) to prevent dynamic routing conflicts.
    """
    logger.info(f"RAG search query: '{payload.query}' (top_k={payload.top_k})")
    try:
        results = query_kb(payload.query, top_k=payload.top_k)
        return results
    except Exception as e:
        logger.error(f"Error executing vector similarity search: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error performing vector similarity search: {str(e)}"
        )


@router.get("/{article_id}", response_model=KBArticle)
def get_article(article_id: int):
    """Retrieve details of a knowledge base article."""
    article = KBService.get(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID {article_id} not found"
        )
    return article


@router.put("/{article_id}", response_model=KBArticle)
def update_article(article_id: int, article_update: KBArticleUpdate):
    """Modify fields of a knowledge base article."""
    article = KBService.update(article_id, article_update)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID {article_id} not found"
        )
    return article


@router.delete("/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_article(article_id: int):
    """Remove an article from the knowledge base."""
    deleted = KBService.delete(article_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Article with ID {article_id} not found"
        )
    return None
