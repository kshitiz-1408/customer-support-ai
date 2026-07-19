import pytest
from unittest.mock import patch
from datetime import datetime
from pydantic import ValidationError
from fastapi.testclient import TestClient
from main import app
from models.user import UserCreate, UserUpdate, UserRead, UserInDB, UserRole
from utils.auth import hash_password, verify_password
from utils.exceptions import DuplicateEmailException, DatabaseFailureException, InvalidTokenException
from services.user_service import UserService

client = TestClient(app)


def clear_collection_by_query(collection, query: dict):
    from database.database import _should_use_mock, _load_mock_db, _save_mock_db
    if _should_use_mock():
        db = _load_mock_db()
        coll_name = collection.name
        if coll_name in db:
            original = db[coll_name]
            filtered = []
            for doc in original:
                match = True
                for k, v in query.items():
                    if doc.get(k) != v:
                        match = False
                        break
                if not match:
                    filtered.append(doc)
            db[coll_name] = filtered
            _save_mock_db(db)
    else:
        collection.delete_many(query)


def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_user_creation_password_validation_rejections():
    # Passwords missing complexity elements should raise ValidationError
    base_user = {
        "email": "test@example.com",
        "full_name": "Test User",
        "role": UserRole.USER
    }
    
    # Too short
    with pytest.raises(ValidationError):
        UserCreate(**base_user, password="Short1!")
 
    # No uppercase
    with pytest.raises(ValidationError):
        UserCreate(**base_user, password="lowercase1!")
 
    # No lowercase
    with pytest.raises(ValidationError):
        UserCreate(**base_user, password="UPPERCASE1!")
 
    # No digit
    with pytest.raises(ValidationError):
        UserCreate(**base_user, password="NoDigitsHere!")
 
    # No special char
    with pytest.raises(ValidationError):
        UserCreate(**base_user, password="NoSpecialChar123")
 
 
def test_user_create_email_normalization():
    # Email should be normalized to lowercase and trimmed
    user = UserCreate(
        email="  TeSt@ExAmPlE.cOm  ",
        full_name="Test User",
        password="ValidPassword123!",
        role=UserRole.USER
    )
    assert user.email == "test@example.com"
 
 
def test_user_creation_and_lookup_flow():
    # Test registration, retrieval, and unique constraints using UserService
    user_payload = UserCreate(
        email="unique_user@example.com",
        full_name="Unique User",
        password="ValidPassword123!",
        role=UserRole.USER
    )
    
    # Create user
    created = UserService.create_user(user_payload)
    assert created.email == "unique_user@example.com"
    assert created.full_name == "Unique User"
    assert created.password_hash != "ValidPassword123!"
    assert created.refresh_token_version == 1
    
    # Duplicate email raises DuplicateEmailException
    with pytest.raises(DuplicateEmailException):
        UserService.create_user(user_payload)
 
    # Lookup by email
    found_by_email = UserService.get_user_by_email("unique_user@example.com")
    assert found_by_email is not None
    assert found_by_email.id == created.id
    
    # Lookup by ID
    found_by_id = UserService.get_user_by_id(created.id)
    assert found_by_id is not None
    assert found_by_id.email == "unique_user@example.com"
 
 
def test_user_properties_updates():
    # Create user first
    user_payload = UserCreate(
        email="update_user@example.com",
        full_name="Original Name",
        password="ValidPassword123!",
        role=UserRole.USER
    )
    created = UserService.create_user(user_payload)
    
    # Update properties
    update_payload = UserUpdate(
        full_name="Updated Name",
        is_verified=True
    )
    updated = UserService.update_user(created.id, update_payload)
    assert updated is not None
    assert updated.full_name == "Updated Name"
    assert updated.is_verified is True
    assert updated.email == "update_user@example.com"
 
 
def test_user_account_deactivation():
    # Create user
    user_payload = UserCreate(
        email="deactivate_user@example.com",
        full_name="Deactivate User",
        password="ValidPassword123!",
        role=UserRole.USER
    )
    created = UserService.create_user(user_payload)
    
    # Deactivate (soft delete)
    success = UserService.deactivate_user(created.id)
    assert success is True
    
    # Verify inactive status
    inactive_user = UserService.get_user_by_id(created.id)
    assert inactive_user is not None
    assert inactive_user.is_active is False
    
    # Deactivating again returns False
    success_retry = UserService.deactivate_user(created.id)
    assert success_retry is False


def test_api_register_user_success():
    payload = {
        "email": "  api_user@Example.Com  ",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "  API User  "
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "api_user@example.com"
    assert data["full_name"] == "API User"
    assert data["role"] == "user"
    assert "password" not in data
    assert "password_hash" not in data
    assert "refresh_token_version" not in data
    assert "message" in data


def test_api_register_user_duplicate():
    payload = {
        "email": "dup_api_user@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Duplicate User"
    }
    response1 = client.post("/api/v1/auth/register", json=payload)
    assert response1.status_code == 201
    
    response2 = client.post("/api/v1/auth/register", json=payload)
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_api_register_user_password_mismatch():
    payload = {
        "email": "mismatch@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "DifferentPassword2@",
        "full_name": "Mismatch User"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert "passwords do not match" in response.json()["detail"]


def test_api_register_user_weak_password():
    payload = {
        "email": "weak@example.com",
        "password": "simple",
        "confirm_password": "simple",
        "full_name": "Weak User"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert "at least" in response.json()["detail"] or "String should have at least 8 characters" in response.json()["detail"]


def test_api_register_user_invalid_email():
    payload = {
        "email": "invalid-email-format",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Invalid Email"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422
    assert "value is not a valid email address" in response.json()["detail"]


def test_api_register_database_failure():
    payload = {
        "email": "db_fail@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "DB Fail User"
    }
    with patch("services.user_service.UserService.create_user", side_effect=DatabaseFailureException("Database unreachable")):
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 500
        assert response.json()["detail"] == "Database unreachable"


def test_api_login_success():
    # Register first
    reg_payload = {
        "email": "login_success@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Login Success User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_payload = {
        "email": "login_success@example.com",
        "password": "SecurePassword1!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    
    # Check that last_login was updated
    user = UserService.get_user_by_email("login_success@example.com")
    assert user.last_login is not None


def test_api_login_wrong_password():
    # Register first
    reg_payload = {
        "email": "login_wrong_pwd@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Wrong Pwd User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login with incorrect password
    login_payload = {
        "email": "login_wrong_pwd@example.com",
        "password": "IncorrectPassword2@"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_api_login_unknown_email():
    login_payload = {
        "email": "unknown_email@example.com",
        "password": "SecurePassword1!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_api_refresh_success():
    # Register and Login
    reg_payload = {
        "email": "refresh_success@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Refresh User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    
    login_payload = {
        "email": "refresh_success@example.com",
        "password": "SecurePassword1!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    refresh_payload = {
        "refresh_token": refresh_token
    }
    response = client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_api_refresh_invalid_token():
    refresh_payload = {
        "refresh_token": "invalid_or_fake_refresh_token"
    }
    response = client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == 401
    assert "invalid token" in response.json()["detail"].lower()


def test_api_refresh_revoked():
    # Register and Login
    reg_payload = {
        "email": "refresh_revoked@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Revoked User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    
    login_payload = {
        "email": "refresh_revoked@example.com",
        "password": "SecurePassword1!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    data = login_res.json()
    access_token = data["access_token"]
    refresh_token = data["refresh_token"]

    # Logout to increment token version
    logout_headers = {"Authorization": f"Bearer {access_token}"}
    logout_res = client.post("/api/v1/auth/logout", headers=logout_headers)
    assert logout_res.status_code == 200

    # Attempt to refresh with the old refresh token (should be rejected)
    refresh_payload = {
        "refresh_token": refresh_token
    }
    response = client.post("/api/v1/auth/refresh", json=refresh_payload)
    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()


def test_api_me_success():
    # Register and Login
    reg_payload = {
        "email": "me_success@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Me User"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    
    login_payload = {
        "email": "me_success@example.com",
        "password": "SecurePassword1!"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    access_token = login_res.json()["access_token"]

    # Access /me
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me_success@example.com"
    assert data["full_name"] == "Me User"
    assert "password_hash" not in data
    assert "refresh_token_version" not in data


def test_api_me_unauthorized():
    from config.config import settings
    with patch.object(settings, "APP_ENV", "production"):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401




def test_api_expired_token():
    import jwt
    import time
    from config.config import settings
    
    expired_payload = {
        "sub": "some_user_id_123",
        "email": "expired_user@example.com",
        "role": "user",
        "type": "access",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_api_route_protection_unauthorized():
    # Calling endpoints with invalid/fake Bearer token returns 401
    headers = {"Authorization": "Bearer invalid_or_fake_token"}
    assert client.post("/api/v1/chat/", headers=headers).status_code == 401
    assert client.get("/api/v1/chat/conversations", headers=headers).status_code == 401
    assert client.get("/api/v1/tickets/", headers=headers).status_code == 401


def test_get_current_user_no_credentials_production():
    from api.deps import get_current_user
    from config.config import settings
    
    with patch.object(settings, "APP_ENV", "production"):
        with pytest.raises(InvalidTokenException):
            get_current_user(credentials=None)



def test_api_cross_user_isolation_chat_and_history():
    # Register and Login User A
    client.post("/api/v1/auth/register", json={
        "email": "usera_chat@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User A"
    })
    tok_a = client.post("/api/v1/auth/login", json={"email": "usera_chat@example.com", "password": "SecurePassword1!"}).json()["access_token"]
    
    # Register and Login User B
    client.post("/api/v1/auth/register", json={
        "email": "userb_chat@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User B"
    })
    tok_b = client.post("/api/v1/auth/login", json={"email": "userb_chat@example.com", "password": "SecurePassword1!"}).json()["access_token"]

    # User A creates a conversation
    headers_a = {"Authorization": f"Bearer {tok_a}"}
    conv_res = client.post("/api/v1/chat/conversations", json={"title": "A's thread"}, headers=headers_a)
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["conversation_id"]

    # User B attempts to view history of A's thread -> 403 Forbidden
    headers_b = {"Authorization": f"Bearer {tok_b}"}
    hist_res = client.get(f"/api/v1/chat/conversations/{conv_id}/history", headers=headers_b)
    assert hist_res.status_code == 403

    # User B attempts to send a message to A's thread -> 403 Forbidden
    chat_res = client.post("/api/v1/chat/", json={"conversation_id": conv_id, "message": "hello"}, headers=headers_b)
    assert chat_res.status_code == 403


def test_api_cross_user_isolation_tickets():
    # Register and Login User A
    client.post("/api/v1/auth/register", json={
        "email": "usera_tkt@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User A"
    })
    tok_a = client.post("/api/v1/auth/login", json={"email": "usera_tkt@example.com", "password": "SecurePassword1!"}).json()["access_token"]
    
    # Register and Login User B
    client.post("/api/v1/auth/register", json={
        "email": "userb_tkt@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User B"
    })
    tok_b = client.post("/api/v1/auth/login", json={"email": "userb_tkt@example.com", "password": "SecurePassword1!"}).json()["access_token"]

    headers_a = {"Authorization": f"Bearer {tok_a}"}
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    # User A creates a ticket
    tkt_payload = {
        "customer_name": "User A",
        "customer_email": "usera_tkt@example.com",
        "subject": "Need help with login",
        "description": "I cannot access the login system."
    }
    tkt_res = client.post("/api/v1/tickets/", json=tkt_payload, headers=headers_a)
    assert tkt_res.status_code == 201
    ticket_id = tkt_res.json()["ticket_id"]

    # User B attempts to read User A's ticket -> 403
    read_res = client.get(f"/api/v1/tickets/{ticket_id}", headers=headers_b)
    assert read_res.status_code == 403

    # User B attempts to update User A's ticket -> 403
    update_res = client.put(f"/api/v1/tickets/{ticket_id}", json={"status": "resolved"}, headers=headers_b)
    assert update_res.status_code == 403

    # User B attempts to delete User A's ticket -> 403
    del_res = client.delete(f"/api/v1/tickets/{ticket_id}", headers=headers_b)
    assert del_res.status_code == 403


def test_api_legacy_ticket_fallback():
    # Charlie Brown (charlie@example.com) is in prepopulated tickets:
    # Register and Login Charlie
    client.post("/api/v1/auth/register", json={
        "email": "charlie@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Charlie Brown"
    })
    tok_charlie = client.post("/api/v1/auth/login", json={"email": "charlie@example.com", "password": "SecurePassword1!"}).json()["access_token"]
    headers_charlie = {"Authorization": f"Bearer {tok_charlie}"}

    # Prepopulated ticket ID for Charlie is TKT-0003
    # Charlie should be able to view it because email matches
    res = client.get("/api/v1/tickets/TKT-0003", headers=headers_charlie)
    assert res.status_code == 200
    assert res.json()["customer_email"] == "charlie@example.com"

    # Register and Login another user
    client.post("/api/v1/auth/register", json={
        "email": "stranger@example.com", "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Stranger"
    })
    tok_stranger = client.post("/api/v1/auth/login", json={"email": "stranger@example.com", "password": "SecurePassword1!"}).json()["access_token"]
    headers_stranger = {"Authorization": f"Bearer {tok_stranger}"}

    # Stranger should not be able to view Charlie's prepopulated ticket -> 403
    res_stranger = client.get("/api/v1/tickets/TKT-0003", headers=headers_stranger)
    assert res_stranger.status_code == 403


def test_simulation_session_recovery_flow():
    # Register and Login to get a valid refresh token
    email = "session_recovery@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Recovery User"
    })
    login_data = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword1!"}).json()
    refresh_token = login_data["refresh_token"]

    # 1. Simulate an expired access token by signing a token that expired in the past
    import jwt
    import time
    from config.config import settings
    expired_payload = {
        "sub": "some_user_id",
        "email": email,
        "role": "user",
        "type": "access",
        "iat": int(time.time()) - 7200,
        "exp": int(time.time()) - 3600
    }
    expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    # 2. Access /me with the expired token -> returns 401
    headers = {"Authorization": f"Bearer {expired_token}"}
    res_me_expired = client.get("/api/v1/auth/me", headers=headers)
    assert res_me_expired.status_code == 401
    assert "expired" in res_me_expired.json()["detail"].lower()

    # 3. Simulate frontend session recovery: call refresh with refresh token -> returns new access token
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_access_token = refresh_res.json()["access_token"]
    assert new_access_token != expired_token

    # 4. Access /me with the new access token -> returns 200 OK with correct profile
    headers_new = {"Authorization": f"Bearer {new_access_token}"}
    res_me_new = client.get("/api/v1/auth/me", headers=headers_new)
    assert res_me_new.status_code == 200
    assert res_me_new.json()["email"] == email
    assert res_me_new.json()["full_name"] == "Recovery User"


def test_api_user_profile_retrieval_and_update():
    # Register and Login
    email = "profile_test@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Initial Name"
    })
    tok = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword1!"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    # 1. GET /api/v1/users/me
    res_get = client.get("/api/v1/users/me", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["full_name"] == "Initial Name"
    assert res_get.json()["email"] == email

    # 2. PATCH /api/v1/users/me (Success)
    res_patch = client.patch("/api/v1/users/me", json={"full_name": "Updated Name"}, headers=headers)
    assert res_patch.status_code == 200
    assert res_patch.json()["full_name"] == "Updated Name"

    # 3. PATCH /api/v1/users/me (Reject invalid/empty name)
    res_patch_invalid = client.patch("/api/v1/users/me", json={"full_name": "   "}, headers=headers)
    assert res_patch_invalid.status_code == 422

    # 4. Confirm readonly attributes (email, role, created_at, password) cannot be updated via PATCH
    res_hack = client.patch("/api/v1/users/me", json={
        "email": "hacker@example.com", "role": "admin", "password_hash": "somehash"
    }, headers=headers)
    # Let's verify email & role remain unchanged.
    res_check = client.get("/api/v1/users/me", headers=headers)
    assert res_check.json()["email"] == email
    assert res_check.json()["role"] == "user"


def test_api_user_change_password():
    # Register and Login
    email = "pass_test@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Pass User"
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword1!"}).json()
    tok = login_res["access_token"]
    ref_tok = login_res["refresh_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    # 1. Reject change password with incorrect current password
    res_wrong_curr = client.post("/api/v1/users/change-password", json={
        "current_password": "WrongPassword1!",
        "new_password": "NewSecurePassword1!",
        "confirm_password": "NewSecurePassword1!"
    }, headers=headers)
    assert res_wrong_curr.status_code == 400
    assert "incorrect" in res_wrong_curr.json()["detail"].lower()

    # 2. Reject change password with weak new password
    res_weak = client.post("/api/v1/users/change-password", json={
        "current_password": "SecurePassword1!",
        "new_password": "weak",
        "confirm_password": "weak"
    }, headers=headers)
    assert res_weak.status_code == 422

    # 3. Successful change password
    res_success = client.post("/api/v1/users/change-password", json={
        "current_password": "SecurePassword1!",
        "new_password": "NewSecurePassword1!",
        "confirm_password": "NewSecurePassword1!"
    }, headers=headers)
    assert res_success.status_code == 200
    assert "success" in res_success.json()["message"].lower()

    # 4. Attempt login with old password -> should fail
    res_login_old = client.post("/api/v1/auth/login", json={"email": email, "password": "SecurePassword1!"})
    assert res_login_old.status_code == 401

    # 5. Attempt login with new password -> should succeed
    res_login_new = client.post("/api/v1/auth/login", json={"email": email, "password": "NewSecurePassword1!"})
    assert res_login_new.status_code == 200

    # 6. Verify refresh token was invalidated (version incremented)
    res_refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": ref_tok})
    assert res_refresh.status_code == 401


def test_api_conversation_message_isolation():
    # User A setup
    email_a = "usera@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_a, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User A"
    })
    tok_a = client.post("/api/v1/auth/login", json={"email": email_a, "password": "SecurePassword1!"}).json()["access_token"]
    headers_a = {"Authorization": f"Bearer {tok_a}"}

    # User B setup
    email_b = "userb@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_b, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "User B"
    })
    tok_b = client.post("/api/v1/auth/login", json={"email": email_b, "password": "SecurePassword1!"}).json()["access_token"]
    headers_b = {"Authorization": f"Bearer {tok_b}"}

    # 1. User A starts a chat -> creates conversation A
    chat_res_a = client.post("/api/v1/chat/", json={"message": "Query from User A"}, headers=headers_a)
    assert chat_res_a.status_code == 200
    conv_id_a = chat_res_a.json()["conversation_id"]

    # 2. User B starts a chat -> creates conversation B
    chat_res_b = client.post("/api/v1/chat/", json={"message": "Query from User B"}, headers=headers_b)
    assert chat_res_b.status_code == 200
    conv_id_b = chat_res_b.json()["conversation_id"]

    # 3. User B attempts to access User A's history -> 403
    history_res = client.get(f"/api/v1/chat/conversations/{conv_id_a}/history", headers=headers_b)
    assert history_res.status_code == 403

    # 4. User B attempts to list conversations -> should only get User B's own conversation(s)
    list_res = client.get("/api/v1/chat/conversations", headers=headers_b)
    assert list_res.status_code == 200
    conversations = list_res.json()
    assert len(conversations) > 0
    # Ensure none of User B's listed conversations have conversation_id_a or are associated with User A
    assert not any(c["conversation_id"] == conv_id_a for c in conversations)

    # 5. User B attempts to post chat to User A's conversation thread -> 403
    chat_hack_res = client.post("/api/v1/chat/", json={"message": "Hacking query", "conversation_id": conv_id_a}, headers=headers_b)
    assert chat_hack_res.status_code == 403

    # 6. Verify message documents in DB have user_id attached
    from database.database import get_messages_collection
    msg_a = get_messages_collection().find_one({"conversation_id": conv_id_a})
    assert msg_a is not None
    assert msg_a.get("user_id") is not None


def test_admin_user_management_rbac():
    from database.database import get_users_collection
    # 1. Setup an Admin and a Standard User
    email_admin = "admin@example.com"
    email_user = "normal@example.com"
    clear_collection_by_query(get_users_collection(), {"role": "admin"})
    clear_collection_by_query(get_users_collection(), {"email": email_user})
    
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Admin User"
    })
    
    # Direct role promotion to admin in database since standard registration defaults to user
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    admin_login_res = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    assert admin_login_res.status_code == 200
    tok_admin = admin_login_res.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {tok_admin}"}

    email_user = "normal@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Normal User"
    })
    tok_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"}).json()["access_token"]
    headers_user = {"Authorization": f"Bearer {tok_user}"}

    # Fetch User ID of Normal User
    user_doc = get_users_collection().find_one({"email": email_user})
    user_id = user_doc["_id"]

    # 2. Standard user attempts to call admin endpoints -> 403 Forbidden
    res_list_forbidden = client.get("/api/v1/admin/users", headers=headers_user)
    assert res_list_forbidden.status_code == 403

    res_detail_forbidden = client.get(f"/api/v1/admin/users/{user_id}", headers=headers_user)
    assert res_detail_forbidden.status_code == 403

    res_role_forbidden = client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "admin"}, headers=headers_user)
    assert res_role_forbidden.status_code == 403

    # 3. Admin user list check (pagination & filter)
    res_list = client.get("/api/v1/admin/users?role=user", headers=headers_admin)
    assert res_list.status_code == 200
    data = res_list.json()
    assert data["total"] >= 1
    assert any(u["email"] == email_user for u in data["users"])

    # 4. Admin detailed view
    res_detail = client.get(f"/api/v1/admin/users/{user_id}", headers=headers_admin)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["email"] == email_user
    assert "conversation_count" in detail_data
    assert "ticket_count" in detail_data

    # 5. Admin deactivates & activates standard user + audit log checks
    res_deactivate = client.patch(f"/api/v1/admin/users/{user_id}/deactivate", headers=headers_admin)
    assert res_deactivate.status_code == 200
    assert res_deactivate.json()["is_active"] is False

    res_activate = client.patch(f"/api/v1/admin/users/{user_id}/activate", headers=headers_admin)
    assert res_activate.status_code == 200
    assert res_activate.json()["is_active"] is True

    # 6. Admin promotes user role
    res_role = client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "admin"}, headers=headers_admin)
    assert res_role.status_code == 200
    assert res_role.json()["role"] == "admin"

    # 7. Self-protection checks: Admin cannot deactivate themselves, and can only demote themselves if other admins exist
    admin_doc = get_users_collection().find_one({"email": email_admin})
    admin_id = admin_doc["_id"]

    res_self_deactivate = client.patch(f"/api/v1/admin/users/{admin_id}/deactivate", headers=headers_admin)
    assert res_self_deactivate.status_code == 403

    # Demoting self succeeds since user_id (normal@example.com) is also an admin
    res_self_role = client.patch(f"/api/v1/admin/users/{admin_id}/role", json={"role": "user"}, headers=headers_admin)
    assert res_self_role.status_code == 200

    # Log in as normal@example.com (the last remaining admin)
    login_user_res = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    tok_normal_admin = login_user_res.json()["access_token"]
    headers_normal_admin = {"Authorization": f"Bearer {tok_normal_admin}"}

    # Demoting the final active admin (normal@example.com) fails
    res_demote_final = client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "user"}, headers=headers_normal_admin)
    assert res_demote_final.status_code == 403

    # 8. Check audit logs generated for target user
    res_logs = client.get(f"/api/v1/admin/users/{user_id}/audit-logs", headers=headers_normal_admin)
    assert res_logs.status_code == 200
    logs = res_logs.json()
    assert len(logs) >= 3  # account_deactivated, account_activated, role_changed
    assert any(log["action"] == "role_changed" for log in logs)


def test_admin_ticket_management_rbac():
    # 1. Setup Admin and Standard User
    email_admin = "admin_tkt@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Ticket Admin"
    })
    from database.database import get_users_collection, get_tickets_collection
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    admin_login_res = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    tok_admin = admin_login_res.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {tok_admin}"}

    email_user = "normal_tkt@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Normal Ticket Customer"
    })
    tok_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"}).json()["access_token"]
    headers_user = {"Authorization": f"Bearer {tok_user}"}

    # 2. Create a customer ticket
    res_tkt = client.post("/api/v1/tickets/", json={
        "customer_name": "Normal Ticket Customer",
        "customer_email": email_user,
        "subject": "Billing issue with invoice 22",
        "description": "My card was charged twice on billing date.",
        "priority": "medium",
        "category": "billing"
    }, headers=headers_user)
    assert res_tkt.status_code == 201
    tkt_data = res_tkt.json()
    tkt_id = tkt_data["ticket_id"]
    tkt_int_id = tkt_data["id"]

    # 3. Standard user attempts to call admin ticket endpoints -> 403 Forbidden
    assert client.get("/api/v1/admin/tickets", headers=headers_user).status_code == 403
    assert client.get("/api/v1/admin/tickets/metrics", headers=headers_user).status_code == 403
    assert client.get(f"/api/v1/admin/tickets/{tkt_id}", headers=headers_user).status_code == 403
    assert client.patch(f"/api/v1/admin/tickets/{tkt_id}/assign", json={"assigned_agent": email_admin}, headers=headers_user).status_code == 403

    # 4. Admin accesses list, metrics, and details
    assert client.get("/api/v1/admin/tickets", headers=headers_admin).status_code == 200
    
    res_metrics = client.get("/api/v1/admin/tickets/metrics", headers=headers_admin)
    assert res_metrics.status_code == 200
    assert res_metrics.json()["open_tickets"] >= 1

    res_details = client.get(f"/api/v1/admin/tickets/{tkt_id}", headers=headers_admin)
    assert res_details.status_code == 200
    assert res_details.json()["ticket"]["ticket_id"] == tkt_id

    # 5. Admin updates status, priority, assignment
    res_assign = client.patch(f"/api/v1/admin/tickets/{tkt_id}/assign", json={"assigned_agent": email_admin}, headers=headers_admin)
    assert res_assign.status_code == 200
    assert res_assign.json()["assigned_agent"] == email_admin

    res_status = client.patch(f"/api/v1/admin/tickets/{tkt_id}/status", json={"status": "in_progress"}, headers=headers_admin)
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "in_progress"

    res_priority = client.patch(f"/api/v1/admin/tickets/{tkt_id}/priority", json={"priority": "high"}, headers=headers_admin)
    assert res_priority.status_code == 200
    assert res_priority.json()["priority"] == "high"

    # 6. Admin adds an internal note
    res_note = client.post(f"/api/v1/admin/tickets/{tkt_id}/notes", json={"content": "Verified double charge on Stripe logs."}, headers=headers_admin)
    assert res_note.status_code == 200
    assert res_note.json()["content"] == "Verified double charge on Stripe logs."

    # 7. Check details has notes and history logs
    res_details_after = client.get(f"/api/v1/admin/tickets/{tkt_id}", headers=headers_admin)
    details_data = res_details_after.json()
    assert len(details_data["notes"]) == 1
    assert len(details_data["history"]) >= 4  # ticket_assigned, ticket_status_changed, ticket_priority_changed, ticket_note_added


def test_api_registration_ignores_client_role():
    # Register with client role field in body
    res = client.post("/api/v1/auth/register", json={
        "email": "injected_role@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Injected Role User",
        "role": "admin"
    })
    assert res.status_code == 201
    
    from database.database import get_users_collection
    doc = get_users_collection().find_one({"email": "injected_role@example.com"})
    assert doc["role"] == "user" or doc["role"] == UserRole.USER


def test_admin_bootstrap_lifecycle():
    from database.database import get_users_collection
    # Delete admin@example.com to verify bootstrap triggers
    clear_collection_by_query(get_users_collection(), {"email": "admin@example.com"})
    
    with TestClient(app) as local_client:
        admin = UserService.get_user_by_email("admin@example.com")
        assert admin is not None
        assert admin.role == UserRole.ADMIN


def test_promote_script():
    email = "promote_script_user@example.com"
    # Delete if exists
    from database.database import get_users_collection
    clear_collection_by_query(get_users_collection(), {"email": email})
    
    client.post("/api/v1/auth/register", json={
        "email": email, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Script Promoted"
    })
    
    import subprocess
    import sys
    from pathlib import Path
    import os
    
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "promote_user.py"
    
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    
    res = subprocess.run(
        [sys.executable, str(script_path), email],
        capture_output=True,
        text=True,
        env=env
    )
    assert res.returncode == 0
    assert "promoted to administrator" in res.stdout.lower() or "is already" in res.stdout.lower()
    
    doc = get_users_collection().find_one({"email": email})
    assert doc["role"] == "admin" or doc["role"] == UserRole.ADMIN


def test_final_administrator_demotion_fails():
    # Set up exactly one admin in system
    from database.database import get_users_collection
    clear_collection_by_query(get_users_collection(), {"role": "admin"})
    
    email_admin = "last_admin@example.com"
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Last Admin"
    })
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    admin_login_res = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    tok_admin = admin_login_res.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {tok_admin}"}
    
    # Attempt to demote self (or last admin) -> should fail
    admin_doc = get_users_collection().find_one({"email": email_admin})
    admin_id = str(admin_doc["_id"])
    
    res_demote = client.patch(f"/api/v1/admin/users/{admin_id}/role", json={"role": "user"}, headers=headers_admin)
    assert res_demote.status_code == 403


def test_reset_admin_password_script():
    from database.database import get_users_collection
    # Setup admin@example.com in system
    clear_collection_by_query(get_users_collection(), {"email": "admin@example.com"})
    
    client.post("/api/v1/auth/register", json={
        "email": "admin@example.com",
        "password": "SecurePassword1!",
        "confirm_password": "SecurePassword1!",
        "full_name": "Bootstrap Admin"
    })
    get_users_collection().update_one({"email": "admin@example.com"}, {"$set": {"role": "admin"}})
    
    # Old password login works initially
    res_login_old = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "SecurePassword1!"})
    assert res_login_old.status_code == 200
    
    # Execute reset password script
    import subprocess
    import sys
    from pathlib import Path
    import os
    
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "reset_admin_password.py"
    
    env = os.environ.copy()
    env["APP_ENV"] = "test"
    
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        env=env
    )
    assert res.returncode == 0
    assert "administrator password reset successful" in res.stdout.lower()
    
    # Extract the new password from the script's terminal output
    new_pwd = None
    lines = res.stdout.splitlines()
    for i, line in enumerate(lines):
        if "new password:" in line.lower() and i + 1 < len(lines):
            new_pwd = lines[i+1].strip()
            break
            
    assert new_pwd is not None
    assert len(new_pwd) >= 16
    
    # Verify old password login is rejected
    res_login_old_rejected = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "SecurePassword1!"})
    assert res_login_old_rejected.status_code == 401
    
    # Verify new password login is accepted
    res_login_new = client.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": new_pwd})
    assert res_login_new.status_code == 200


def test_admin_conversation_inspection():
    from database.database import get_users_collection, get_conversations_collection, get_messages_collection
    
    # 1. Setup Admin, Regular User, and Conversation
    email_admin = "inspector_admin@example.com"
    email_user = "inspector_user@example.com"
    
    clear_collection_by_query(get_users_collection(), {"email": email_admin})
    clear_collection_by_query(get_users_collection(), {"email": email_user})
    
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Admin Inspector"
    })
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Standard User"
    })
    
    # Login Admin
    admin_login = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    tok_admin = admin_login.json()["access_token"]
    headers_admin = {"Authorization": f"Bearer {tok_admin}"}
    
    # Login Regular User
    user_login = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    tok_user = user_login.json()["access_token"]
    headers_user = {"Authorization": f"Bearer {tok_user}"}
    
    # Get user details to get user ID
    user_doc = get_users_collection().find_one({"email": email_user})
    user_id = str(user_doc["_id"])
    
    # Create conversation
    conv_id = "test_inspector_conv_123"
    clear_collection_by_query(get_conversations_collection(), {"conversation_id": conv_id})
    clear_collection_by_query(get_messages_collection(), {"conversation_id": conv_id})
    
    # Insert a conversation
    from datetime import datetime, timezone
    get_conversations_collection().insert_one({
        "conversation_id": conv_id,
        "user_id": user_id,
        "title": "Query regarding account billing",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    
    # Insert user message & assistant message
    get_messages_collection().insert_many([
        {
            "message_id": "msg_user_1",
            "conversation_id": conv_id,
            "user_id": user_id,
            "role": "user",
            "content": "Why is my invoice higher this month?",
            "intent": "billing_inquiry",
            "created_at": datetime.now(timezone.utc)
        },
        {
            "message_id": "msg_assistant_1",
            "conversation_id": conv_id,
            "user_id": user_id,
            "role": "assistant",
            "content": "It seems you had an outstanding balance from last month.",
            "agent": "billing_agent",
            "sources": [{"source": "billing_policy.pdf", "page": 2, "type": "pdf"}],
            "created_at": datetime.now(timezone.utc)
        }
    ])
    
    # 2. Assert Regular User receives 403 Forbidden
    res_list_forbidden = client.get("/api/v1/admin/conversations", headers=headers_user)
    assert res_list_forbidden.status_code == 403
    
    res_detail_forbidden = client.get(f"/api/v1/admin/conversations/{conv_id}", headers=headers_user)
    assert res_detail_forbidden.status_code == 403
    
    # 3. Assert Admin can query and filter list
    res_list = client.get(f"/api/v1/admin/conversations?email={email_user}&limit=10&page=1", headers=headers_admin)
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert data_list["total"] >= 1
    assert any(c["conversation_id"] == conv_id for c in data_list["conversations"])
    
    # Check search query
    res_search = client.get(f"/api/v1/admin/conversations?search={email_user}", headers=headers_admin)
    assert res_search.status_code == 200
    assert res_search.json()["total"] >= 1
    
    # 4. Assert Admin can get detailed view
    res_detail = client.get(f"/api/v1/admin/conversations/{conv_id}", headers=headers_admin)
    assert res_detail.status_code == 200
    data_detail = res_detail.json()
    assert data_detail["conversation_id"] == conv_id
    assert data_detail["participant"]["email"] == email_user
    assert len(data_detail["messages"]) == 2
    assert data_detail["messages"][0]["role"] == "user"
    assert data_detail["messages"][0]["intent"] == "billing_inquiry"
    assert data_detail["messages"][1]["role"] == "assistant"
    assert data_detail["messages"][1]["agent"] == "billing_agent"
    assert data_detail["messages"][1]["sources"][0]["source"] == "billing_policy.pdf"


def test_admin_knowledge_base_management():
    """
    Day 9 – Task 5: Knowledge Base Management integration tests.
    Tests: file validation, duplicate upload blocking, reindexing, pagination, search,
    deletions, and strict 403 authorization blocks.
    """
    import io
    
    # 1. Setup privilege accounts
    email_admin = "kb_admin@example.com"
    email_user = "kb_user@example.com"
    
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "KB Admin"
    })
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "KB User"
    })
    
    # Promote admin in DB
    from database.database import get_users_collection, get_knowledge_base_collection
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    # Obtain tokens
    login_admin = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    login_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    
    headers_admin = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
    headers_user = {"Authorization": f"Bearer {login_user.json()['access_token']}"}
    
    # 2. Assert Regular User receives 403 Forbidden on all KB endpoints
    assert client.get("/api/v1/admin/knowledge", headers=headers_user).status_code == 403
    assert client.get("/api/v1/admin/knowledge/some-id", headers=headers_user).status_code == 403
    assert client.delete("/api/v1/admin/knowledge/some-id", headers=headers_user).status_code == 403
    assert client.post("/api/v1/admin/knowledge/reindex/some-id", headers=headers_user).status_code == 403
    assert client.post("/api/v1/admin/knowledge/reindex-all", headers=headers_user).status_code == 403
    
    # 3. Assert Admin can upload valid text file
    file_payload = {"file": ("test_kb_doc.txt", io.BytesIO(b"Hello world from integration tests chunk 1. This is some support info."), "text/plain")}
    res_upload = client.post("/api/v1/admin/knowledge/upload", files=file_payload, headers=headers_admin)
    assert res_upload.status_code == 201
    doc_data = res_upload.json()
    assert doc_data["filename"] == "test_kb_doc.txt"
    assert doc_data["file_type"] == "txt"
    assert doc_data["embedding_status"] == "completed"
    
    doc_id = doc_data["document_id"]
    
    # 4. Assert duplicate uploads return 409 Conflict
    res_dup = client.post("/api/v1/admin/knowledge/upload", files=file_payload, headers=headers_admin)
    assert res_dup.status_code == 409
    
    # 5. Assert list filtering and search
    res_list = client.get(f"/api/v1/admin/knowledge?search=test_kb", headers=headers_admin)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1
    assert any(d["document_id"] == doc_id for d in res_list.json()["documents"])
    
    # Check detail view
    res_detail = client.get(f"/api/v1/admin/knowledge/{doc_id}", headers=headers_admin)
    assert res_detail.status_code == 200
    assert res_detail.json()["filename"] == "test_kb_doc.txt"
    
    # 6. Assert single and total re-indexing
    res_reindex_single = client.post(f"/api/v1/admin/knowledge/reindex/{doc_id}", headers=headers_admin)
    assert res_reindex_single.status_code == 200
    
    res_reindex_all = client.post("/api/v1/admin/knowledge/reindex-all", headers=headers_admin)
    assert res_reindex_all.status_code == 200
    
    # 7. Assert delete successfully synchronizes everything
    res_delete = client.delete(f"/api/v1/admin/knowledge/{doc_id}", headers=headers_admin)
    assert res_delete.status_code == 200
    
    # Check that it was deleted
    res_detail_gone = client.get(f"/api/v1/admin/knowledge/{doc_id}", headers=headers_admin)
    assert res_detail_gone.status_code == 404


def test_admin_analytics_dashboard():
    """
    Day 9 - Task 6: Analytics Dashboard integration tests.
    Tests authorization access restrictions and validates schema payloads
    for overview, usage, AI, and system health endpoints.
    """
    email_admin = "analytics_admin@example.com"
    email_user = "analytics_user@example.com"
    
    from database.database import get_users_collection
    clear_collection_by_query(get_users_collection(), {"email": email_admin})
    clear_collection_by_query(get_users_collection(), {"email": email_user})
    
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Analytics Admin"
    })
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Analytics User"
    })
    
    # Logins
    login_admin = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    login_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    
    headers_admin = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
    headers_user = {"Authorization": f"Bearer {login_user.json()['access_token']}"}
    
    # 1. Assert regular user gets 403 Forbidden
    assert client.get("/api/v1/admin/analytics/overview", headers=headers_user).status_code == 403
    assert client.get("/api/v1/admin/analytics/usage", headers=headers_user).status_code == 403
    assert client.get("/api/v1/admin/analytics/ai", headers=headers_user).status_code == 403
    assert client.get("/api/v1/admin/analytics/system", headers=headers_user).status_code == 403
    
    # 2. Assert admin overview retrieves correctly
    res_overview = client.get("/api/v1/admin/analytics/overview", headers=headers_admin)
    assert res_overview.status_code == 200
    data_overview = res_overview.json()
    assert "total_users" in data_overview
    assert "active_users" in data_overview
    assert "total_conversations" in data_overview
    assert "total_messages" in data_overview
    assert "total_tickets" in data_overview
    assert "open_tickets" in data_overview
    assert "closed_tickets" in data_overview
    assert "total_documents" in data_overview
    assert "total_administrators" in data_overview
    assert data_overview["total_users"] >= 2
    assert data_overview["total_administrators"] >= 1
    
    # 3. Assert admin usage endpoint
    res_usage = client.get("/api/v1/admin/analytics/usage?range=7d", headers=headers_admin)
    assert res_usage.status_code == 200
    data_usage = res_usage.json()
    assert "conversations_per_day" in data_usage
    assert "messages_per_day" in data_usage
    assert "new_users_per_day" in data_usage
    assert "tickets_per_day" in data_usage
    
    # Try custom ranges
    res_usage_custom = client.get("/api/v1/admin/analytics/usage?range=30d", headers=headers_admin)
    assert res_usage_custom.status_code == 200
    
    # 4. Assert admin AI stats
    res_ai = client.get("/api/v1/admin/analytics/ai", headers=headers_admin)
    assert res_ai.status_code == 200
    data_ai = res_ai.json()
    assert "average_ai_response_time" in data_ai
    assert "average_confidence_score" in data_ai
    assert "intent_distribution" in data_ai
    assert "agent_routing_distribution" in data_ai
    assert "rag_retrieval_count" in data_ai
    assert "gemini_request_count" in data_ai
    assert "failed_ai_requests" in data_ai
    assert "ai_success_rate" in data_ai
    
    # 5. Assert admin system status
    res_sys = client.get("/api/v1/admin/analytics/system", headers=headers_admin)
    assert res_sys.status_code == 200
    data_sys = res_sys.json()
    assert "database_status" in data_sys
    assert "vector_index_status" in data_sys
    assert "total_embeddings" in data_sys
    assert "startup_time" in data_sys
    assert "api_uptime" in data_sys


def test_admin_audit_logging():
    """
    Day 9 - Task 7: Audit Logging system integration tests.
    Verifies that security-sensitive operations (login, failed login, role changes, etc.)
    trigger automatic append-only logs, standard users are denied,
    and admin logs querying supports pagination, global search, and granular filters.
    """
    email_admin = "audit_admin@example.com"
    email_user = "audit_user@example.com"
    
    from database.database import get_users_collection, get_audit_logs_collection
    clear_collection_by_query(get_users_collection(), {"email": email_admin})
    clear_collection_by_query(get_users_collection(), {"email": email_user})
    
    clear_collection_by_query(get_audit_logs_collection(), {})

    # Register admin
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Audit Admin"
    })
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    # Register user
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Audit User"
    })

    # 2. Check failed login creates a failed login log
    client.post("/api/v1/auth/login", json={"email": email_user, "password": "WrongPassword!"})
    
    # Login admin & user successfully
    login_admin = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    login_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    
    headers_admin = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
    headers_user = {"Authorization": f"Bearer {login_user.json()['access_token']}"}

    # 3. Standard user should not access logs
    res_list_user = client.get("/api/v1/admin/audit", headers=headers_user)
    assert res_list_user.status_code == 403

    # 4. Admin accesses list and checks login & failed login logs
    res_list_admin = client.get("/api/v1/admin/audit", headers=headers_admin)
    assert res_list_admin.status_code == 200
    data_list = res_list_admin.json()
    assert "total" in data_list
    assert "logs" in data_list
    
    # Verify events
    actions = [l["action"] for l in data_list["logs"]]
    assert "login_failed" in actions
    assert "login" in actions

    # Verify IP and User Agent are logged
    failed_log = next(l for l in data_list["logs"] if l["action"] == "login_failed")
    assert "status" in failed_log
    assert failed_log["status"] == "failed"
    assert "additional_metadata" in failed_log
    assert failed_log["additional_metadata"].get("reason") == "invalid_password"

    # 5. Verify detail spec details view
    audit_id = failed_log["_id"]
    res_detail_user = client.get(f"/api/v1/admin/audit/{audit_id}", headers=headers_user)
    assert res_detail_user.status_code == 403

    res_detail_admin = client.get(f"/api/v1/admin/audit/{audit_id}", headers=headers_admin)
    assert res_detail_admin.status_code == 200
    detail_data = res_detail_admin.json()
    assert detail_data["_id"] == audit_id
    assert detail_data["action"] == "login_failed"
    assert "timestamp" in detail_data

    # 6. Verify role promotions / demotions trigger logs
    user_id = login_user.json().get("user_id")
    if not user_id:
        u_doc = get_users_collection().find_one({"email": email_user})
        user_id = u_doc["_id"] if u_doc else email_user
        
    client.patch(f"/api/v1/admin/users/{user_id}/role", json={"role": "admin"}, headers=headers_admin)
    
    # Retrieve logs again to check role change log
    res_list_new = client.get("/api/v1/admin/audit", headers=headers_admin)
    new_actions = [l["action"] for l in res_list_new.json()["logs"]]
    assert "role_changed" in new_actions

    # 7. Verify Pagination works
    res_pag = client.get("/api/v1/admin/audit?page=1&limit=2", headers=headers_admin)
    assert len(res_pag.json()["logs"]) <= 2

    # 8. Verify search query param
    res_search = client.get(f"/api/v1/admin/audit?search={email_admin}", headers=headers_admin)
    assert res_search.status_code == 200

    # 9. Verify Action filter
    res_filter = client.get("/api/v1/admin/audit?action=login", headers=headers_admin)
    for l in res_filter.json()["logs"]:
        assert l["action"] == "login"


def test_admin_system_monitoring():
    """
    Day 9 - Task 8: System Monitoring endpoints integration tests.
    Verifies that system monitoring routes require admin credentials (RBAC check),
    and check for complete schemas returned to admins.
    """
    email_admin = "monitoring_admin@example.com"
    email_user = "monitoring_user@example.com"
    
    from database.database import get_users_collection
    clear_collection_by_query(get_users_collection(), {"email": email_admin})
    clear_collection_by_query(get_users_collection(), {"email": email_user})

    # Register admin
    client.post("/api/v1/auth/register", json={
        "email": email_admin, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Monitoring Admin"
    })
    get_users_collection().update_one({"email": email_admin}, {"$set": {"role": "admin"}})
    
    # Register user
    client.post("/api/v1/auth/register", json={
        "email": email_user, "password": "SecurePassword1!", "confirm_password": "SecurePassword1!", "full_name": "Monitoring User"
    })

    # Login admin & user successfully
    login_admin = client.post("/api/v1/auth/login", json={"email": email_admin, "password": "SecurePassword1!"})
    login_user = client.post("/api/v1/auth/login", json={"email": email_user, "password": "SecurePassword1!"})
    
    headers_admin = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}
    headers_user = {"Authorization": f"Bearer {login_user.json()['access_token']}"}

    # 1. Standard user receives 403 Forbidden
    for endpoint in ["health", "performance", "services"]:
        res = client.get(f"/api/v1/admin/system/{endpoint}", headers=headers_user)
        assert res.status_code == 403

    # 2. Admin receives 200 OK
    # Health endpoint
    res_health = client.get("/api/v1/admin/system/health", headers=headers_admin)
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert "overall_status" in data_health
    assert "backend_status" in data_health
    assert "database_status" in data_health
    assert "gemini_status" in data_health
    assert "uptime" in data_health

    # Performance endpoint
    res_perf = client.get("/api/v1/admin/system/performance", headers=headers_admin)
    assert res_perf.status_code == 200
    data_perf = res_perf.json()
    assert "average_response_time" in data_perf
    assert "requests_per_minute" in data_perf
    assert "active_users" in data_perf
    assert "memory_usage" in data_perf
    assert "cpu_usage" in data_perf
    assert "database_latency" in data_perf

    # Services endpoint
    res_services = client.get("/api/v1/admin/system/services", headers=headers_admin)
    assert res_services.status_code == 200
    data_services = res_services.json()
    for service_name in ["mongodb", "gemini", "embeddings", "vector_store", "background_services"]:
        assert service_name in data_services
        service_info = data_services[service_name]
        assert "status" in service_info
        assert "last_check" in service_info
        assert "response_time" in service_info















