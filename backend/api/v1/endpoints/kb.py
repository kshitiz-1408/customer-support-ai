from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from models.kb import KBArticle, KBArticleCreate, KBArticleUpdate, KBSearchResult
from services.kb_service import KBService

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
