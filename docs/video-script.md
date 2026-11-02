# Video script (English, about 2:30)

Target length: 1–3 minutes. Screen recording plus voice. Rehearse once with a timer.

| Time | Screen | What to say |
|---|---|---|
| 0:00–0:15 | README with badges | "Hi, we are [names]. This is Vitreo, our semester project: an API for medical appointments and emergency triage. In this lab we focused on DevSecOps: code quality and API security." |
| 0:15–0:45 | SonarCloud dashboard, Quality Gate *Passed* | "First, SonarCloud. It analyzes every push from GitHub Actions. We fixed the critical issues it reported, added a regression test for each one, and the Quality Gate is now passing with [X]% coverage." |
| 0:45–1:15 | CI job summary with the mutation score, then `test_triage_domain.py` | "Coverage only tells you that code was executed. Mutation testing tells you whether the tests would catch a bug. mutmut created 177 mutants of our triage rules and security code. Our score is [X]%. The pipeline fails if it drops below 50%. A surviving mutant showed us that our login limiter never freed memory, so we added a test for it." |
| 1:15–1:50 | Swagger: login → `/auth/me` 200 → `/admin/usuarios` 403 with the receptionist token → 200 with the admin token | "Now security. We log in and get a JWT that expires in 30 minutes. Any authenticated user can call `/me`. The admin endpoint returns 403 for a receptionist and 200 for an admin. We have four roles, and the role is checked against the database on every request." |
| 1:50–2:20 | `owasp-api-top10-2023.md` table | "We mapped twelve controls to the OWASP API Security Top 10 2023: object-level authorization so doctors only see their own appointments, scrypt password hashing, account lockout, mass-assignment protection, request size limits and security headers." |
| 2:20–2:40 | Security tab: CodeQL 0 alerts, Dependabot PR | "Finally, CodeQL scans every push with zero critical alerts, and Dependabot keeps our dependencies updated." |
| 2:40–3:00 | AI log | "About the AI assistant: one suggestion was [describe it]. It was wrong because [reason], and we fixed it by [fix]. Thanks for watching!" |
