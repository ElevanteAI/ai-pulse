# AI Pulse

AI Pulse helps a company understand how well its people use AI at work, team by team.

- **Employees** sign in, pick their organization, and take a short diagnostic. Questions adapt to their job role and seniority. One open-ended answer is scored by an LLM.
- **Each employee** gets a personal report: maturity level, risks, and next steps for their role.
- **Company admins** see a dashboard of AI maturity by department and the top risks across the company.
- Some users (consultants, group-company HR) belong to **more than one organization** and choose one after login.

This codebase was started by a previous developer who has since left. It runs, but it is unfinished, and we are not confident in all of it.

## Stack

- Backend: Python, FastAPI, SQLAlchemy (SQLite by default)
- Frontend: React (Vite)
- AI: any OpenAI-compatible chat completions endpoint, or mock mode with canned responses

## Run it locally

Backend:

```bash
cd backend
pip install -r requirements.txt
python -m app.seed          # creates demo data, password for all users: pulse123
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev                 # http://localhost:5173
```

Tests:

```bash
cd backend
python -m pytest
```

## Demo accounts (password `pulse123`)

| Email | Organization(s) | Role |
|---|---|---|
| asha@northwind.test | Northwind Logistics | Admin |
| meera@bluepeak.test | Bluepeak Retail | Admin |
| ravi@consult.test | Both | Employee at Northwind, admin at Bluepeak |
| priya@northwind.test | Northwind Logistics | Employee (Support) |
| dev@northwind.test | Northwind Logistics | Employee (Engineering, lead) |

## AI mode

`AI_MODE=mock` (default) returns canned model responses from `backend/data/mock_ai_responses.json`. Like a real model, they are not always well-formed.

`AI_MODE=live` calls `LLM_API_URL` with `LLM_API_KEY` and `LLM_MODEL`.

---

# Assessment notes

## What was wrong (found in review)

| # | Problem | Impact |
|---|---|---|
| 1 | `/dashboard` trusted the `org_id` query parameter | Any admin could read another company's results. The only "isolation" test asserted the leak as correct behaviour. An unknown ID crashed with a 500. |
| 2 | `/auth/select-org` issued a token for any `org_id` | Token minting for organizations the user does not belong to. |
| 3 | Seniority compared as strings (`"lead" < "senior"`) | Leads were treated as more junior than seniors and missed their questions. This was the one failing test. |
| 4 | Department average divided summed question scores by headcount | Not an average. Non-responders dragged it down, and a person with more answers counted more. |
| 5 | Two different maturity-level definitions (`utils.py` vs `dashboard.py`) | The same score showed a different level on the report and the dashboard. |
| 6 | Resubmitting appended new responses | Repeat submissions distorted counts and risk totals. |
| 7 | LLM output was `json.loads`-ed and trusted | Fenced or chatty replies caused a 500 for the employee. Scores outside 1–5 and invented risk labels were saved. |
| 8 | Backend `Dockerfile` ran `main:app` | The module is `app.main`, so the container would not start. |
| 9 | Frontend dashboard printed raw JSON | Not usable by leadership. |

## What was fixed

Each phase is its own commit.

1. **Tenant isolation.** The dashboard returns 403 for any org other than the one in the token, then 404 if the org is missing (403 first, so IDs cannot be probed). `/auth/select-org` requires a membership. The leak test now asserts 403.
2. **Core logic.** Seniority uses an explicit rank map. Department average is the mean of each responding employee's own average. One `maturity_level` helper is shared by report and dashboard. Submitting replaces the employee's earlier answers (validated before deleting, so a bad request cannot wipe old data).
3. **AI pipeline.** `scoring.py` strips code fences and extracts JSON from surrounding prose, coerces and clamps the score to 1–5, keeps only the four allowed risk labels, defaults a missing reason, and never raises: any failure saves a neutral score of 3 with a reason saying scoring was unavailable.
4. **Client requests** (below).
5. **Custom feature**: risk remediation playbooks (below).
6. **Frontend.** Navigation bar, executive dashboard, validated diagnostic form, report with confirmed "Delete My Data", and routing that sends employees with answers straight to their report.
7. **Tests and docs.** 58 backend tests and 11 frontend tests; see "Tests".

## Client request (Northwind HR): how it was handled

1. **No small groups.** A department with fewer than 5 respondents is never shown on its own. All such departments are pooled into one "Other teams" row. If the pool itself has fewer than 5 respondents, only headcount is shown. Scores and risks from small groups are excluded from the dashboard, including the top-risk list and the company-wide maturity level, because leaving them in would let someone subtract the visible teams from the total to recover a hidden team's result.
2. **Right to delete.** `DELETE /diagnostic/me` removes all of the caller's responses. Reports and the dashboard are computed from the response rows on every request, so the data disappears everywhere immediately. Tests cover the report emptying, the admin dashboard recalculating, and a team falling back below the threshold after a deletion.

### Questions for Northwind HR

- Is the threshold of 5 counted on **respondents** (what we did) or on department headcount?
- Prefer "Other teams" pooling (current) or hiding small teams entirely? Pooling still reveals the pool's size.
- Hiding small teams' risks also hides real risks from leadership. Is that acceptable, or should risks be shown at company level only once total respondents are high enough?
- Free-text answers are sent to the LLM provider. Is that covered by your data-processing agreement, and should employees see a notice before submitting?
- Should deletion also cover backups, logs and the LLM provider's copies? The app deletes only its own database rows.
- Should a deleted employee be blocked from, or reminded about, retaking the diagnostic?
- When AI scoring fails we record a neutral 3. Would you rather exclude those answers from averages?
- Administrators without a department are not counted in headcount. Is that right?

## Custom feature: remediation playbooks

**Problem:** the dashboard listed risk labels but gave leadership nothing to do about them.
**Solution:** each risk label has a playbook (`backend/app/services/playbooks.py`). Admins click a risk to get an action card with guardrails, tooling policy and team guidance (`GET /playbooks/{risk}`, admin only). Employees get matching fix tips on their report.
**Why this one:** it turns the product from reporting into action, it is small and self-contained (one data file and one route), and a new risk or a wording change is a one-place edit. The text is generic starter guidance and should be reviewed by the client's legal and HR teams before being treated as policy.

## Tests

`cd backend && python -m pytest` runs 58 tests covering:

- cross-tenant blocking (403s on dashboard and `select-org`, employee vs admin, multi-org user scoping);
- privacy grouping, including the 4-vs-5 boundary and risk suppression;
- deletion cascade to the report and dashboard;
- malformed AI output, both in the scoring unit tests and through `/diagnostic/submit` (junk text, fenced JSON, bad scores, invented flags, timeouts);
- password hashing, login lockout, audit logging, the production secret check and CORS.

`cd frontend && npm test` runs 11 component tests (diagnostic validation, report and delete confirmation, dashboard privacy badge and playbook card, session restore).

## Hardening added after the first pass

These were originally listed as "left alone" and have since been addressed:

- **Passwords** use salted PBKDF2-SHA256 (600,000 iterations, constant-time compare). Hashes from the old unsalted scheme no longer verify, so existing databases must be reseeded or users reset.
- **`SECRET_KEY`**: with `APP_ENV=production` the app refuses to start on the built-in dev secret.
- **CORS** is limited to `CORS_ORIGINS` (default `http://localhost:5173`) instead of every origin.
- **Rate limiting**: 5 failed sign-ins per IP and email within 15 minutes returns 429. The limiter is in memory, so it is per process; use a shared store if you run several workers.
- **Audit log** (`audit_log` table) records dashboard views, playbook views and employee data deletions, with user, organization and time.
- **Seed script** refuses to run against a database that already has users unless you pass `--reset`.
- **Sessions** survive a page refresh. The saved token is checked on load and cleared if it is no longer valid.
- **Frontend tests**: `cd frontend && npm test` (Vitest + Testing Library, 11 tests).
- **`backend/.env` was tracked in git.** It is now untracked and ignored; use `backend/.env.example` as the template. The old file is still in git history, so rotate the `SECRET_KEY` and any API key that was ever committed.

## Still deliberately left alone

- **Password reset** needs an email provider and a decision on the flow, so it is not built.
- **The token stays in `localStorage`**. Moving to an httpOnly cookie also needs CSRF protection and is a design decision.
- **SQLite** is still the default. `DATABASE_URL` accepts other databases, but only SQLite has been tested.
- The audit log has no viewer yet; it can only be read from the database.

## How I used AI tools

I used Claude Code throughout, as a pair-programmer working in this repository.

- **What it did well:** reading the codebase to find the bugs listed above, writing fixes, and writing the tests and docs for each phase. I gave it one phase at a time, and each phase ended with a test run and its own commit.
- **How I checked it:** every backend change was run against the test suite. For the security-sensitive pieces (tenant isolation, small-group suppression, deletion), the tests assert the blocked or hidden outcome rather than just "returns 200".
- **What I did not check:** the UI has component tests and builds, but was not exercised in a real browser. `AI_MODE=live` was never run against a real model, so real model output formats are untested. The Dockerfile fix was not built. Treat the playbook text and the neutral fallback score of 3 as decisions to confirm.

### One place the AI got it wrong

When fixing duplicate submissions, the AI added a regression test and reported the work as done. The test compared the admin dashboard before and after a second submit. I later checked it by removing the fix: **the test still passed**. The dashboard averages per employee, so duplicate rows do not change what it shows, and the test could never fail. The fix itself was correct, but the test gave false confidence.

I rewrote the test to count the stored rows for that employee, then re-ran it with the fix removed to confirm that it fails (it does) and with the fix in place to confirm that it passes. The lesson I took from it: for each important test, break the code on purpose and see whether the test notices.

Smaller slips of the same kind were caught in review: a first test assumed the seed data had no respondents (it did), a config rewrite silently dropped the dev-server port, and a scripted edit corrupted a character in `App.jsx`.
