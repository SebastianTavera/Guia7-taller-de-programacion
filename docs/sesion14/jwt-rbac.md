# JWT Authentication and Role-Based Access Control

## Design

| Piece | Implementation |
|---|---|
| Password storage | Salted **scrypt** (n=2^14, r=8, p=1) from the standard library, verified with `hmac.compare_digest` ([passwords.py](../../vitreo/security/passwords.py)) |
| Token | **JWT HS256** with `sub`, `rol`, `iat`, `exp` (30 min) and `iss` claims ([tokens.py](../../vitreo/security/tokens.py)) |
| Validation | Signature, pinned algorithm (`algorithms=["HS256"]`), expiration, issuer and all claims required |
| Secret | `JWT_SECRET` from the environment, at least 32 characters; the app refuses to start in production without it |
| Authentication | `HTTPBearer` dependency `get_current_user` ([deps.py](../../vitreo/api/deps.py)) |
| Authorization | `require_roles(*roles)` dependency, applied per endpoint or per router |
| Roles | `ADMIN`, `MEDICO`, `ENFERMERIA`, `RECEPCION` (from the semester project requirements) |

The role used for authorization is **read from the database on every request**, not from the token.
Deactivating a user or changing their role takes effect immediately, and a forged `rol` claim is
useless (`test_role_comes_from_database_not_from_token`).

## The three test endpoints

| Endpoint | Who | Expected |
|---|---|---|
| `POST /api/v1/auth/login` | public | 200 + token; 401 generic message; 429 after 5 failures |
| `GET /api/v1/admin/usuarios` (ADMIN endpoint) | ADMIN | 200 for ADMIN, 403 for other roles, 401 without token |
| `GET /api/v1/auth/me` (USER endpoint) | any authenticated role | 200 with the user profile, 401 without a valid token |

## Permission matrix

| Resource | ADMIN | MEDICO | ENFERMERIA | RECEPCION |
|---|---|---|---|---|
| Users, reports | ✅ | ❌ | ❌ | ❌ |
| Register patients | ✅ | ❌ | ❌ | ✅ |
| Read patients and doctors | ✅ | ✅ | ✅ | ✅ |
| Schedule, cancel, reschedule appointments | ✅ | ❌ | ❌ | ✅ |
| Change appointment status | ✅ | own only | ❌ | ✅ |
| Read appointments | ✅ | own only | ✅ | ✅ |
| Register triage | ✅ | ❌ | ✅ | ❌ |
| ER queue | ✅ | ✅ | ✅ | ❌ |
| Mark triage as attended | ❌ | ✅ | ✅ | ❌ |

## Demo (Swagger UI or curl)

```bash
# 1. Login
curl -s -X POST localhost:8000/api/v1/auth/login -H "Content-Type: application/json" \
  -d '{"correo":"recepcion@vitreo.local","password":"<SEED_PASSWORD>"}'
# 2. USER endpoint -> 200
curl -s localhost:8000/api/v1/auth/me -H "Authorization: Bearer <token>"
# 3. ADMIN endpoint with a RECEPCION token -> 403
curl -s localhost:8000/api/v1/admin/usuarios -H "Authorization: Bearer <token>"
# 4. Same endpoint with the admin token -> 200
```

## Tests

[tests/test_auth_api.py](../../tests/test_auth_api.py) and [tests/unit/test_security_core.py](../../tests/unit/test_security_core.py)
cover login, generic errors, lockout, expired, tampered, `alg: none`, wrong issuer, missing claims,
deactivated users and the 401/403/200 matrix.

## Screenshots (`docs/evidencias/sesion14/`)

- `jwt-login.png`: login response with the token.
- `jwt-user-200.png`: `/auth/me` with the token.
- `jwt-admin-403.png` and `jwt-admin-200.png`: ADMIN endpoint with RECEPCION and ADMIN tokens.
- `jwt-401.png`: any endpoint without a token.
