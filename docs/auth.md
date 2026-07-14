# Authentication & User Management Documentation

This document describes the design, implementation, and interfaces for the user management and authentication system in the Customer Support AI platform.

## 1. Registration Endpoint

* **URL:** `/api/v1/auth/register`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Response Status (Success):** `201 Created`

### Request Body
The request payload must be a JSON object containing the following fields:

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `email` | string | Yes | The user's email address. Will be trimmed and converted to lowercase automatically. |
| `password` | string | Yes | The user's desired password. Must meet password policy requirements. Minimum length is 8 characters. |
| `confirm_password` | string | Yes | The confirmation of the user's password. Must match `password` exactly. |
| `full_name` | string | Yes | The user's full name. Minimum length is 2 characters, maximum is 100 characters. |

#### Password Policy Requirements
To ensure account security, the chosen password must meet the following criteria:
1. At least **8 characters** in length.
2. Contains at least **one uppercase letter** (A-Z).
3. Contains at least **one lowercase letter** (a-z).
4. Contains at least **one digit** (0-9).
5. Contains at least **one special character** (e.g., `!@#$%^&*()_+-=[]{}|;':",./<>?~`).

---

## 2. Login Endpoint

* **URL:** `/api/v1/auth/login`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Response Status (Success):** `200 OK`

### Request Body
```json
{
  "email": "user@example.com",
  "password": "SecurePassword1!"
}
```

### Response Body
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 3. Token Refresh Endpoint

* **URL:** `/api/v1/auth/refresh`
* **Method:** `POST`
* **Content-Type:** `application/json`
* **Response Status (Success):** `200 OK`

### Request Body
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Response Body
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

---

## 4. Logout Endpoint

* **URL:** `/api/v1/auth/logout`
* **Method:** `POST`
* **Headers:** `Authorization: Bearer <access_token>`
* **Response Status (Success):** `200 OK`

### Response Body
```json
{
  "message": "Logged out successfully"
}
```

*Note: Logging out increments the user's `refresh_token_version` in the database, instantly invalidating all outstanding refresh tokens associated with that user.*

---

## 5. Current User Profile Endpoint

* **URL:** `/api/v1/auth/me`
* **Method:** `GET`
* **Headers:** `Authorization: Bearer <access_token>`
* **Response Status (Success):** `200 OK`

### Response Body
```json
{
  "id": "60c72b2f9b1d8b2c88888888",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "user",
  "is_active": true,
  "is_verified": false,
  "created_at": "2026-07-13T18:00:00Z",
  "updated_at": "2026-07-13T18:05:00Z",
  "last_login": "2026-07-13T18:05:00Z"
}
```

---

## 6. Response Formats & Error Handling

### HTTP Status Codes

#### 200 OK
Successful login, refresh, logout, or retrieval of user profile.

#### 201 Created
Successful registration of new user.

#### 400 Bad Request
Occurs on password mismatches or validation errors:
```json
{
  "detail": "passwords do not match"
}
```

#### 401 Unauthorized
Returned for invalid, expired, or revoked tokens, or incorrect credentials:
* **Missing/Invalid credentials**: `{"detail": "Incorrect email or password"}`
* **Expired token**: `{"detail": "Token has expired"}`
* **Invalid or malformed token**: `{"detail": "Invalid token"}`

#### 403 Forbidden
Returned when authorization credentials are not provided (e.g. missing Authorization header) or when a deactivated user attempts an action:
* **Missing header**: `{"detail": "Not authenticated"}`
* **Inactive account**: `{"detail": "Inactive user account"}`

#### 409 Conflict
Occurs when the email is already registered during user creation:
```json
{
  "detail": "User with email 'user@example.com' already exists."
}
```

#### 422 Unprocessable Entity
Occurs when required request fields are missing or formats are invalid (e.g., malformed email or password strength failure).

---

## 7. Security Specifications
* **Token Expiration**: Access tokens are configured to expire after **15 minutes**; refresh tokens expire after **7 days**.
* **Stateless Refresh Token Invalidation**: Logout requests increment the user's `refresh_token_version` count in MongoDB. When a refresh request is received, the version stored in the token payload is compared against the database. If they don't match (meaning a logout or password change occurred), the token is rejected as invalid/revoked.
* **Password Salting & Hashing**: Done securely via `bcrypt` through PyJWT and PassLib context handlers.
