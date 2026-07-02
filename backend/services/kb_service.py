from datetime import datetime, timezone
from typing import List, Optional
from models.kb import KBArticle, KBArticleCreate, KBArticleUpdate, KBSearchResult


class KBService:
    # Class-level mock database
    _db: List[KBArticle] = []
    _counter: int = 0

    @classmethod
    def create(cls, article_in: KBArticleCreate) -> KBArticle:
        cls._counter += 1
        now = datetime.now(timezone.utc)
        article = KBArticle(
            id=cls._counter,
            title=article_in.title,
            content=article_in.content,
            category=article_in.category,
            tags=article_in.tags,
            created_at=now,
            updated_at=now
        )
        cls._db.append(article)
        return article

    @classmethod
    def get(cls, article_id: int) -> Optional[KBArticle]:
        for article in cls._db:
            if article.id == article_id:
                return article
        return None

    @classmethod
    def get_all(cls, category: Optional[str] = None) -> List[KBArticle]:
        if category:
            return [a for a in cls._db if a.category.lower() == category.lower()]
        return cls._db

    @classmethod
    def update(cls, article_id: int, article_update: KBArticleUpdate) -> Optional[KBArticle]:
        article = cls.get(article_id)
        if not article:
            return None
        
        update_data = article_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(article, key, value)
            
        article.updated_at = datetime.now(timezone.utc)
        return article

    @classmethod
    def delete(cls, article_id: int) -> bool:
        article = cls.get(article_id)
        if not article:
            return False
        cls._db.remove(article)
        return True

    @classmethod
    def search(cls, query: str) -> List[KBSearchResult]:
        """
        Simulates relevance score search term matching.
        """
        results = []
        if not query:
            return [KBSearchResult(article=a, score=1.0) for a in cls._db]
            
        query_terms = [t.lower() for t in query.split()]
        for article in cls._db:
            score = 0.0
            title_lower = article.title.lower()
            content_lower = article.content.lower()
            
            for term in query_terms:
                if term in title_lower:
                    score += 2.0
                if term in content_lower:
                    score += 0.5
                for tag in article.tags:
                    if term in tag.lower():
                        score += 1.0
                        
            if score > 0:
                results.append(KBSearchResult(article=article, score=score))
                
        results.sort(key=lambda x: x.score, reverse=True)
        return results


# Pre-populate articles
KBService.create(
    KBArticleCreate(
        title="How to reset your portal password",
        content="To reset your password, visit the login page and click 'Forgot Password'. You will receive an email verification code. Enter this code and enter a new password.",
        category="Account",
        tags=["password", "reset", "login", "credentials"]
    )
)
KBService.create(
    KBArticleCreate(
        title="Locating your invoice and billing history",
        content="Billing history and statements are located in Settings > Billing. Only administrators can view statements. If the portal returns a 500 error, contact billing-support@example.com.",
        category="Billing",
        tags=["invoice", "billing", "payment", "receipts"]
    )
)
KBService.create(
    KBArticleCreate(
        title="Webhooks and API Custom Integration",
        content="Our REST API supports outbound webhooks for support tickets. Setup hooks under Admin Console > Webhooks. Secure your endpoints by validating headers using your token key.",
        category="Technical",
        tags=["developer", "api", "webhooks", "integration"]
    )
)
