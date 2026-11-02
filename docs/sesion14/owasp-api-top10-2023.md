# OWASP API Security Top 10 (2023) – Implemented Controls

The 2023 edition of the OWASP Top 10 is the **API Security Top 10**, which fits Vitreo because it is
a REST API. Vitreo implements **12 controls covering 8 of the 10 categories**. The other two
(API7 and API10) do not apply, because the API neither fetches URLs nor consumes third-party APIs.

| # | OWASP 2023 risk | Control implemented in Vitreo | Code evidence | Test evidence |
|---|---|---|---|---|
| 1 | **API1** Broken Object Level Authorization | A doctor only reads and updates **their own** appointments. Other doctors' appointments return 404, not 403, so ids cannot be enumerated, and the `medico_id` filter is overridden for MEDICO users. | `_cita_visible`, `listar` in [citas.py](../../vitreo/api/routers/citas.py) | `test_doctors_only_see_their_own_appointments` |
| 2 | **API2** Broken Authentication | Passwords hashed with salted **scrypt** and compared in constant time; a dummy hash is checked for unknown emails, so timing does not reveal valid accounts; the same generic error is returned for every failure. | [passwords.py](../../vitreo/security/passwords.py), `login` in [auth.py](../../vitreo/api/routers/auth.py) | `test_wrong_password_and_unknown_email_get_the_same_generic_401` |
| 3 | **API2** Broken Authentication | **JWT** with a pinned algorithm (rejects `alg: none`), 30-minute expiration, issuer and required claims; the secret comes from the environment (≥ 32 chars, mandatory in production). | [tokens.py](../../vitreo/security/tokens.py), [config.py](../../vitreo/config.py) | `test_unsigned_alg_none_token_is_rejected`, `test_expired_token_is_rejected`, `test_production_requires_a_strong_jwt_secret` |
| 4 | **API2 / API4** Brute force | **Account lockout**: 5 failed logins in 5 minutes return `429` with `Retry-After`. | [rate_limit.py](../../vitreo/security/rate_limit.py) | `test_account_is_locked_after_five_failed_attempts` |
| 5 | **API3** Broken Object Property Level Authorization | Every input schema uses `extra="forbid"`, which blocks **mass assignment** (`rol`, `activo`, `nivel_esi`, `id`...); output schemas never include `contrasena_hash`; the ESI level is always computed by the server. | `InputModel` and `UsuarioOut` in [schemas.py](../../vitreo/schemas.py) | `test_mass_assignment_of_extra_fields_is_rejected`, `test_triage_permissions_and_validation` |
| 6 | **API4** Unrestricted Resource Consumption | 64 KB request **body limit** (413), **pagination** capped at 100, `max_length` on every string (the password is capped at 128 chars before hashing), and the lockout state is bounded in memory. | `security_middleware` in [main.py](../../vitreo/api/main.py), `Query(le=100)` in routers | `test_oversized_or_invalid_body_length_is_rejected`, `test_expired_accounts_are_forgotten_to_bound_memory` |
| 7 | **API5** Broken Function Level Authorization | **RBAC** with `require_roles(...)` on every sensitive endpoint; the role is read from the database, not from the token. | `require_roles`, `get_current_user` in [deps.py](../../vitreo/api/deps.py) | `test_admin_endpoint_allows_admin_and_forbids_every_other_role`, `test_role_comes_from_database_not_from_token` |
| 8 | **API6** Unrestricted Access to Sensitive Business Flows | Booking is restricted to staff roles, and the **agenda rejects overlapping slots** for the same doctor or office, so nobody can hoard or double-book appointments. | `_verificar_disponibilidad` in [citas.py](../../vitreo/api/routers/citas.py) | `test_overlapping_appointments_for_doctor_or_office_are_409` |
| 9 | **API8** Security Misconfiguration | **Security headers** (CSP, `X-Frame-Options`, `nosniff`, `no-store`, HSTS in production), CORS **allowlist** with explicit methods and headers, and generic 500/409 errors that never leak stack traces or SQL. | `SECURITY_HEADERS` and `create_app` in [main.py](../../vitreo/api/main.py), [errors.py](../../vitreo/api/errors.py) | `test_security_headers_are_sent`, `test_unexpected_errors_hide_internal_details`, `test_database_constraint_errors_become_409_without_sql_details` |
| 10 | **API8** Security Misconfiguration | **Input validation** with strict types, ranges and patterns (vital signs, blood type, document, email, future dates). Validation errors never echo the rejected input. | [schemas.py](../../vitreo/schemas.py), `validation_exception_handler` in [errors.py](../../vitreo/api/errors.py) | `test_invalid_patient_data_is_422`, `test_weak_password_is_rejected` |
| 11 | **API9** Improper Inventory Management | Versioned routes (`/api/v1`), a documented OpenAPI contract, and **docs disabled in production**. | `create_app` in [main.py](../../vitreo/api/main.py) | `test_production_disables_api_docs_and_adds_hsts` |
| 12 | **API9** Dependency inventory | **Dependabot** for pip and GitHub Actions, exact version pins, and **CodeQL** `security-extended` on every push. | [dependabot.yml](../../.github/dependabot.yml), [codeql.yml](../../.github/workflows/codeql.yml) | Dependabot PRs, CodeQL alerts tab |

Not applicable: **API7 SSRF** (no endpoint receives or fetches URLs) and **API10 Unsafe Consumption
of APIs** (Vitreo does not call external APIs).

Audit trail (non-functional requirement 6): successful and failed logins and critical triage alerts
(ESI 1–2) are logged on the `vitreo.audit` and `vitreo.alerts` loggers, using ids only and never
user input, which avoids log injection.

## Reference

OWASP Foundation. (2023). *OWASP API Security Top 10 – 2023*. https://owasp.org/API-Security/editions/2023/en/0x11-t10/
