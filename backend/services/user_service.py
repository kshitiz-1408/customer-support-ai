import logging
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from database.database import get_users_collection
from models.user import UserCreate, UserUpdate, UserInDB
from utils.auth import hash_password
from utils.exceptions import DuplicateEmailException, DatabaseFailureException
from utils.resilience import retry_mongodb_read

logger = logging.getLogger("customer_support_backend")

class UserService:
    @classmethod
    def create_user(cls, user_create: UserCreate) -> UserInDB:
        """
        Creates a new user record in MongoDB.
        Enforces email uniqueness and hashes the password securely.
        """
        email_normalized = user_create.email.strip().lower()
        
        # Check uniqueness beforehand (works on mock and actual DB)
        existing = cls.get_user_by_email(email_normalized)
        if existing:
            raise DuplicateEmailException(f"User with email '{email_normalized}' already exists.")
            
        try:
            coll = get_users_collection()
            now = datetime.now(timezone.utc)
            user_id = str(ObjectId())
            
            user_doc = {
                "_id": user_id,
                "email": email_normalized,
                "password_hash": hash_password(user_create.password),
                "full_name": user_create.full_name.strip(),
                "role": user_create.role,
                "is_active": user_create.is_active,
                "is_verified": user_create.is_verified,
                "created_at": now,
                "updated_at": now,
                "last_login": None,
                "refresh_token_version": 1
            }
            
            coll.insert_one(user_doc)
            logger.info(f"User created successfully: ID={user_id}, Email={email_normalized}")
            return UserInDB(**user_doc)
            
        except DuplicateEmailException as de_exc:
            raise de_exc
        except Exception as e:
            logger.error(f"Failed to create user in DB: {str(e)}", exc_info=True)
            raise DatabaseFailureException(f"Error persisting user record to datastore: {str(e)}")

    @classmethod
    def get_user_by_email(cls, email: str) -> Optional[UserInDB]:
        """Retrieves a user document by their normalized email address."""
        email_normalized = email.strip().lower()
        try:
            coll = get_users_collection()
            
            doc = retry_mongodb_read(coll.find_one, {"email": email_normalized})
            if not doc:
                return None
            return UserInDB(**doc)
        except Exception as e:
            logger.error(f"Error reading user by email '{email_normalized}': {str(e)}")
            raise DatabaseFailureException(f"Error retrieving user from datastore: {str(e)}")

    @classmethod
    def get_user_by_id(cls, user_id: str) -> Optional[UserInDB]:
        """Retrieves a user document by their stringified ObjectId."""
        try:
            coll = get_users_collection()
            
            doc = retry_mongodb_read(coll.find_one, {"_id": user_id})
            if not doc:
                return None
            return UserInDB(**doc)
        except Exception as e:
            logger.error(f"Error reading user by ID '{user_id}': {str(e)}")
            raise DatabaseFailureException(f"Error retrieving user from datastore: {str(e)}")

    @classmethod
    def update_user(cls, user_id: str, user_update: UserUpdate) -> Optional[UserInDB]:
        """Updates specific fields on a user record."""
        try:
            coll = get_users_collection()
            
            # Fetch current state
            existing = cls.get_user_by_id(user_id)
            if not existing:
                return None
                
            update_data = user_update.model_dump(exclude_unset=True)
            if not update_data:
                return existing
                
            # If email is changing, enforce uniqueness
            if "email" in update_data and update_data["email"] != existing.email:
                email_normalized = update_data["email"]
                if cls.get_user_by_email(email_normalized):
                    raise DuplicateEmailException(f"User with email '{email_normalized}' already exists.")
                    
            now = datetime.now(timezone.utc)
            update_data["updated_at"] = now
            
            # Perform update
            coll.update_one({"_id": user_id}, {"$set": update_data})
            
            # Return updated document
            return cls.get_user_by_id(user_id)
        except DuplicateEmailException as de_exc:
            raise de_exc
        except Exception as e:
            logger.error(f"Error updating user '{user_id}': {str(e)}")
            raise DatabaseFailureException(f"Error updating user record in datastore: {str(e)}")

    @classmethod
    def deactivate_user(cls, user_id: str) -> bool:
        """Deactivates a user account (soft delete)."""
        try:
            coll = get_users_collection()
            existing = cls.get_user_by_id(user_id)
            if not existing or not existing.is_active:
                return False
                
            now = datetime.now(timezone.utc)
            coll.update_one(
                {"_id": user_id},
                {"$set": {"is_active": False, "updated_at": now}}
            )
            logger.info(f"User '{user_id}' deactivated successfully.")
            return True
        except Exception as e:
            logger.error(f"Error deactivating user '{user_id}': {str(e)}")
            raise DatabaseFailureException(f"Error deactivating user in datastore: {str(e)}")

    @classmethod
    def change_password(cls, user_id: str, new_password_hash: str) -> Optional[UserInDB]:
        """Secures password change and increments the refresh_token_version."""
        try:
            coll = get_users_collection()
            existing = cls.get_user_by_id(user_id)
            if not existing:
                return None
            
            now = datetime.now(timezone.utc)
            new_version = existing.refresh_token_version + 1
            
            coll.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "password_hash": new_password_hash,
                        "refresh_token_version": new_version,
                        "updated_at": now
                    }
                }
            )
            logger.info(f"Password changed and refresh tokens invalidated for user '{user_id}'. New version: {new_version}")
            return cls.get_user_by_id(user_id)
        except Exception as e:
            logger.error(f"Error changing password for user '{user_id}': {str(e)}")
            raise DatabaseFailureException(f"Error changing password in datastore: {str(e)}")

