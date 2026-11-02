# Glossary – Sessions 13 and 14 (English → Spanish)

| Term | Spanish | Definition |
|---|---|---|
| Quality Gate | Umbral de calidad | Set of conditions (bugs, coverage, duplication...) that new code must meet in SonarCloud. |
| Code smell | Mal olor de código | Maintainability issue that is not a bug but makes code harder to change. |
| Security hotspot | Punto sensible de seguridad | Code that needs human review to decide whether it is a vulnerability. |
| Regression test | Prueba de regresión | Test that reproduces a fixed bug so it cannot come back unnoticed. |
| Mutant | Mutante | Copy of the code with one small deliberate change (`<` → `<=`, `True` → `False`). |
| Killed / survived mutant | Mutante muerto / sobreviviente | A mutant is killed when at least one test fails; it survives when all tests pass. |
| Equivalent mutant | Mutante equivalente | Mutant that behaves exactly like the original, so no test can kill it. |
| Mutation score | Puntaje de mutación | Killed mutants / tested mutants. It measures how well tests detect faults. |
| Boundary value | Valor de frontera | Input at the edge of a condition (SpO2 = 90 when the rule is `< 90`). |
| JWT (JSON Web Token) | Token web JSON | Signed token with claims (`sub`, `exp`, `rol`) used for stateless authentication. |
| Claim | Afirmación / reclamo | A key-value fact inside a JWT payload. |
| Bearer token | Token portador | Token sent in `Authorization: Bearer <token>`; whoever holds it is authenticated. |
| Authentication vs. authorization | Autenticación vs. autorización | *Who are you?* (401) vs. *what are you allowed to do?* (403). |
| RBAC | Control de acceso basado en roles | Permissions are granted to roles, and users get roles. |
| BOLA | Autorización rota a nivel de objeto | Accessing another user's object by changing an id (OWASP API1). |
| Mass assignment | Asignación masiva | Client sets fields it should not control (e.g. `rol`) by adding them to the body. |
| Salt | Sal | Random value added to a password before hashing, so equal passwords get different hashes. |
| Key derivation function (scrypt) | Función de derivación de claves | Slow, memory-hard hash designed for passwords. |
| Brute force / lockout | Fuerza bruta / bloqueo | Guessing passwords repeatedly / blocking an account after N failures. |
| OAuth 2.0 | OAuth 2.0 | Authorization framework where a client obtains access tokens from an authorization server. |
| SAST | Análisis estático de seguridad | Finding vulnerabilities in source code without running it (CodeQL, SonarCloud). |
| CodeQL | CodeQL | GitHub's SAST engine that queries code as a database. |
| Dependabot | Dependabot | GitHub bot that opens PRs to update vulnerable or outdated dependencies. |
| DevSecOps | DevSecOps | Practice of integrating security checks into every stage of the CI/CD pipeline. |
| Least privilege | Mínimo privilegio | Give each user, token or workflow only the permissions it needs. |
