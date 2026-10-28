# AI Pulse: work plan

How I prioritised about 15 hours on an inherited codebase I don't trust. Findings are numbered V1–V24 in [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md).

## Guiding order

1. **Stop data leaving its tenant.** Nothing else matters if Northwind can read Bluepeak (V1–V4).
2. **Make the numbers true.** A dashboard that is confidently wrong is worse than no dashboard (V6–V9, V15).
3. **Make the AI safe to rely on.** Validate everything the model says, and never let it invent a label about a person (V10, V11, V14).
4. **Do what the client asked**, and write down what I'd still ask them (V12, V13).
5. **Make it easy for the next person.** One-command setup, tests that prove the above, CI (V16, V17, V24).
6. **One feature of my own**, small and sharp.
7. Polish only after all of that.

## Branches

Each branch is cut from `main`, tested, and merged back with `--no-ff`, so `git log --graph` shows one unit of work per branch. Every fix comes with a test that fails on the original code.

| Branch | Covers | Proof |
|---|---|---|
| `docs/audit-and-plan` | This plan and the audit | Repro script output in the audit |
| `fix/auth-and-secrets` | V2, V3, V4, V5, V17, V18 | `tests/test_auth.py` |
| `fix/tenant-isolation` | V1, V19 | `tests/test_isolation.py` |
| `fix/diagnostic-integrity` | V6, V9 | `tests/test_diagnostic.py`, existing failing test now passes |
| `fix/ai-scoring` | V10, V11, V14 | `tests/test_scoring.py`: every canned mock response, plus an injection case |
| `fix/dashboard-metrics` | V7, V8, V15 | `tests/test_dashboard.py` with hand-computed expected numbers |
| `feat/client-min-group-size` | Client request #1 (V12) | Tests for merging, hiding and the subtraction attack |
| `feat/client-right-to-delete` | Client request #2 (V13) | Test that deletion removes the person from the dashboard immediately |
| `feat/policy-reality-check` | My feature | Tests plus UI |
| `feat/frontend-ux` | Real dashboard, report, delete button, error handling | Manual walkthrough + build |
| `chore/dev-experience` | V16, V24: Docker, compose, CI, Makefile-style scripts | CI green, `docker compose up` |
| `docs/submission-readme` | Final README | n/a |

## Deliberately not doing (and why)

- **Rewriting git history to purge the leaked secret.** The brief says keep history, and rotating the key is the real fix anyway.
- **Moving to Postgres or adding migrations (Alembic).** SQLite is fine for a pilot. I'd add Alembic before the first schema change in production; it's on the roadmap.
- **SSO / SAML.** Enterprises will ask for it, but it's a product decision with integration work per client.
- **Login rate limiting, httpOnly cookies, token revocation (V20–V22).** Real, but lower risk than everything above, and better solved at the infrastructure layer.
- **Making the AI scoring "smarter".** The problem wasn't intelligence, it was trust. I spent the time on validation and failure handling instead.

## Feature candidates (my own idea)

I considered these and picked one. Criteria: useful to leadership *or* employees, small enough to finish properly, uses data we already collect, and doesn't weaken anonymity.

| Idea | Who it helps | Why / why not |
|---|---|---|
| **Policy reality check** (chosen) | Leadership + employees | Compares what people *say* about the AI policy with how they *actually* handle data. "70% say they follow the policy; 3 in 10 of them are still pasting customer data." That's the one number a CISO or HR head would act on. Built entirely from existing answers, and it respects the minimum group size. Employees get a private, specific nudge when their own answers don't line up. |
| Contest an AI score | Employees | Builds trust in the AI, but invites gaming (people contest only low scores) and needs a review workflow that conflicts with anonymity. |
| Per-question next steps | Employees | Replaces the generic role-based list with advice tied to the person's weakest answer. Useful but incremental, so it's a good follow-up. |
| Trend over time | Leadership | Needs repeated diagnostics and versioned results. Valuable after a second round, but there's no data to show it yet. |
| Team action plan export (PDF/CSV) | Leadership | Plumbing more than insight. |
| Manager-scoped dashboards | Managers | Needs a reporting-line model, and it makes small-group problems worse. |

## Roadmap after this submission

1. Injection and regression eval set for the live model: around 50 labelled answers, run in CI against `AI_MODE=live` nightly. Alert if agreement with the human labels drops.
2. Alembic migrations + Postgres.
3. SSO (OIDC) per organization, and SCIM for joiners and leavers.
4. Audit log of admin dashboard views and data deletions (counts only, no content).
5. Configurable minimum group size per org (never below 5), and suppression applied to every future breakdown (seniority, role), not just department.
6. Retention policy: automatically delete raw open-text answers after N days, keeping only scores.
