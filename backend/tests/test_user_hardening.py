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






