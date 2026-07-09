import logging
import os
import json
from typing import List, Dict, Any, Optional
from pymongo import MongoClient
from config.config import settings

logger = logging.getLogger("customer_support_backend")

db_client: MongoClient = None
db_connected: bool = False

# File-backed mock database for graceful fallback when remote MongoDB Atlas is offline or blocked
MOCK_DB_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
    "knowledge_base", 
    "mock_mongo.json"
)

import threading
_mock_db_lock = threading.Lock()

def _load_mock_db() -> Dict[str, List[Dict[str, Any]]]:
    with _mock_db_lock:
        if not os.path.exists(MOCK_DB_FILE):
            return {"conversations": [], "messages": [], "tickets": [], "counters": [{"_id": "ticket_id", "seq": 3}]}
        try:
            with open(MOCK_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading mock db: {e}")
            return {"conversations": [], "messages": [], "tickets": [], "counters": [{"_id": "ticket_id", "seq": 3}]}

def _save_mock_db(db_data: Dict[str, List[Dict[str, Any]]]):
    with _mock_db_lock:
        try:
            os.makedirs(os.path.dirname(MOCK_DB_FILE), exist_ok=True)
            with open(MOCK_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save mock db to file: {e}")


class MockCollection:
    def __init__(self, name: str):
        self.name = name

    def create_index(self, keys, unique=False):
        pass

    def insert_one(self, doc: Dict[str, Any]):
        db = _load_mock_db()
        # Make a copy to avoid in-memory mutations affecting file
        doc_copy = dict(doc)
        if self.name not in db:
            db[self.name] = []
        db[self.name].append(doc_copy)
        _save_mock_db(db)
        return doc

    def insert_many(self, docs: List[Dict[str, Any]]):
        db = _load_mock_db()
        if self.name not in db:
            db[self.name] = []
        for doc in docs:
            db[self.name].append(dict(doc))
        _save_mock_db(db)
        return docs

    def count_documents(self, query: Dict[str, Any]) -> int:
        db = _load_mock_db()
        if self.name not in db:
            return 0
        count = 0
        for doc in db[self.name]:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                count += 1
        return count

    def find_one(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None, sort: Optional[List[tuple]] = None) -> Optional[Dict[str, Any]]:
        db = _load_mock_db()
        if self.name not in db:
            return None
        results = []
        for doc in db[self.name]:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(doc)
        
        if not results:
            return None
            
        if sort:
            for field, order in reversed(sort):
                results.sort(key=lambda x: x.get(field, ""), reverse=(order == -1))
                
        doc = results[0]
        # Handle projection
        if projection:
            doc = {k: v for k, v in doc.items() if projection.get(k, 1) != 0}
        return dict(doc)

    def find(self, query: Dict[str, Any], projection: Optional[Dict[str, Any]] = None):
        db = _load_mock_db()
        if self.name not in db:
            results = []
        else:
            results = []
            for doc in db[self.name]:
                match = True
                for k, v in query.items():
                    if doc.get(k) != v:
                        match = False
                        break
                if match:
                    results.append(doc)
                
        class Cursor:
            def __init__(self, data):
                self.data = data
            def __iter__(self):
                return iter(self.data)
            def sort(self, field, order=1):
                # order can be a string, a list of tuples, or an int
                if isinstance(field, list):
                    for f, o in reversed(field):
                        self.data.sort(key=lambda x: x.get(f, ""), reverse=(o == -1))
                else:
                    self.data.sort(key=lambda x: x.get(field, ""), reverse=(order == -1))
                return self
            def limit(self, count):
                self.data = self.data[:count]
                return self
            def __len__(self):
                return len(self.data)
                
        return Cursor(results)

    def find_one_and_update(self, query: Dict[str, Any], update: Dict[str, Any], upsert=False, return_document=False):
        db = _load_mock_db()
        if self.name not in db:
            db[self.name] = []
            
        match_idx = -1
        for idx, doc in enumerate(db[self.name]):
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                match_idx = idx
                break
                
        if match_idx == -1:
            if upsert:
                new_doc = dict(query)
                if "$set" in update:
                    new_doc.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        new_doc[k] = new_doc.get(k, 0) + v
                db[self.name].append(new_doc)
                _save_mock_db(db)
                return new_doc
            return None
            
        doc = db[self.name][match_idx]
        old_doc = dict(doc)
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        db[self.name][match_idx] = doc
        _save_mock_db(db)
        return doc if return_document else old_doc

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert=False):
        self.find_one_and_update(query, update, upsert=upsert)

    def delete_one(self, query: Dict[str, Any]):
        db = _load_mock_db()
        if self.name not in db:
            db[self.name] = []
        match_idx = -1
        for idx, doc in enumerate(db[self.name]):
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                match_idx = idx
                break
                
        class DeleteResult:
            def __init__(self, count):
                self.deleted_count = count
                
        if match_idx != -1:
            db[self.name].pop(match_idx)
            _save_mock_db(db)
            return DeleteResult(1)
        return DeleteResult(0)


def connect_db():
    """Initialize MongoClient pool and verify connectivity."""
    global db_client, db_connected
    if not settings.MONGODB_URI:
        logger.error("MONGODB_URI environment configuration is missing. Falling back to Mock DB.")
        db_connected = False
        return
        
    try:
        import time
        start_time = time.perf_counter()
        
        # Prevent logging password credentials: only log host information
        masked_uri = settings.MONGODB_URI
        if "@" in masked_uri:
            parts = masked_uri.split("@")
            prefix = parts[0].split("://")
            scheme = prefix[0]
            masked_uri = f"{scheme}://****:****@{parts[1]}"
            
        logger.info({
            "event": "mongodb_connection_started",
            "uri": masked_uri
        })
        
        # Initialize client with connection pooling and configured timeouts
        db_client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS
        )
        # Perform lightweight check to verify connection
        db_client.admin.command('ping')
        
        db_connected = True
        
        # Create indexes
        db_client[settings.MONGODB_DB_NAME]["conversations"].create_index("conversation_id", unique=True)
        db_client[settings.MONGODB_DB_NAME]["conversations"].create_index("session_id")
        db_client[settings.MONGODB_DB_NAME]["conversations"].create_index("user_id")
        db_client[settings.MONGODB_DB_NAME]["messages"].create_index("conversation_id")
        db_client[settings.MONGODB_DB_NAME]["messages"].create_index("created_at")
        
        # Ticket indexes
        db_client[settings.MONGODB_DB_NAME]["tickets"].create_index("id", unique=True)
        db_client[settings.MONGODB_DB_NAME]["tickets"].create_index("ticket_id", unique=True)
        db_client[settings.MONGODB_DB_NAME]["tickets"].create_index("status")
        db_client[settings.MONGODB_DB_NAME]["tickets"].create_index("created_at")
        
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info({
            "event": "mongodb_connected",
            "duration_ms": duration_ms
        })
    except Exception as e:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        logger.error({
            "event": "mongodb_connection_failed",
            "exception_type": type(e).__name__,
            "error_detail": str(e),
            "duration_ms": duration_ms
        })
        db_connected = False

def close_db():
    """Close MongoDB connection pool cleanly."""
    global db_client, db_connected
    if db_client:
        logger.info({"event": "mongodb_close_started"})
        db_client.close()
        db_client = None
        db_connected = False
        logger.info({"event": "mongodb_closed"})

def get_db():
    """Retrieve the shared database instance."""
    global db_client
    if db_client is None:
        if not settings.MONGODB_URI:
            raise RuntimeError("MONGODB_URI is not configured in settings.")
        db_client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            socketTimeoutMS=settings.MONGODB_SOCKET_TIMEOUT_MS
        )
    return db_client[settings.MONGODB_DB_NAME]

def get_tickets_collection():
    """Retrieve the collection storing support tickets."""
    if not db_connected:
        return MockCollection("tickets")
    return get_db()["tickets"]

def get_chat_history_collection():
    """Retrieve the collection storing chat session memory logs."""
    if not db_connected:
        return MockCollection("chat_history")
    return get_db()["chat_history"]

def get_counters_collection():
    """Retrieve the collection managing auto-incrementing sequential sequence counters."""
    if not db_connected:
        return MockCollection("counters")
    return get_db()["counters"]

def get_conversations_collection():
    """Retrieve the collection storing conversations."""
    if not db_connected:
        return MockCollection("conversations")
    return get_db()["conversations"]

def get_messages_collection():
    """Retrieve the collection storing conversation messages."""
    if not db_connected:
        return MockCollection("messages")
    return get_db()["messages"]
