# AI Pulse

**AI Pulse** is a multi-organization AI literacy and workplace AI usage assessment platform. Employees complete role-specific diagnostics, receive personal maturity reports and actionable improvement suggestions, while administrators see privacy-aware department insights.

Built with **FastAPI, SQLAlchemy and SQLite** on the backend and **React + Vite** on the frontend.

> **Project status:** Assessment implementation and pilot prototype, not a production-ready enterprise deployment. See [Current limitations](#current-limitations) before using real employee data.

## Key features

- **Multi-organization access:** Users can belong to multiple organizations with different roles and permissions.
- **Role-based diagnostics:** Question assignments depend on job role and seniority.
- **AI-assisted scoring:** Open-ended answers can be scored using a mock or configured live model, with validation and safe fallback behavior.
- **Personal reports:** Employees can review maturity scores, risk indicators and three practical improvement suggestions.
- **Privacy-aware dashboards:** Small groups are hidden unless at least five employees have completed the diagnostic.
- **Data deletion:** Employees can remove their diagnostic responses for the selected organization.
- **Testing and developer tooling:** Backend and frontend tests, a browser smoke test, CI checks and guarded demo seeding.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Frontend | React, Vite, CSS |
| Backend | Python, FastAPI, SQLAlchemy |
| Database | SQLite |
| Authentication | JWT, bcrypt password hashing |
| AI integration | Mock responses or OpenAI-compatible chat endpoint |
| Quality checks | pytest, Node.js test runner, GitHub Actions, browser smoke test |
| Containerization | Docker (configuration provided; local execution not verified) |

## Quickstart from a clean checkout

Use Python 3.12+ and Node.js 22. GitHub Actions checks Python 3.12 and Node 22; local checks also ran on Python 3.13 and Node 25.

```
git clone https://github.com/avi4rag/ai-pulse.git
cd ai-pulse
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
Copy-Item backend/.env.example backend/.env
cd frontend
npm ci
cd ..
python scripts/manage.py seed
python scripts/manage.py backend
```

On Linux/macOS, activate with `source .venv/bin/activate` and copy the environment file with `cp backend/.env.example backend/.env`. If PowerShell blocks activation, use `.venv\Scripts\python.exe` in place of `python` instead of changing the machine's execution policy.

Open a second terminal in the repository root:

```
python scripts/manage.py frontend
```

Open [http://localhost:5173](http://localhost:5173/). Backend API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs). The frontend defaults to [http://localhost:8000](http://localhost:8000/); set `VITE_API_URL` in the frontend process environment before starting or building if the API runs elsewhere.

The seed command **deletes and recreates local demo tables**. It requires `DEV_MODE=true` and a relative SQLite database path of `./aipulse.db` or `./test.db`. **Never run it against real data.**

## Demo accounts (password `pulse123`)

| **Email** | **Organization(s)** | **Role** |
| --- | --- | --- |
| [asha@northwind.test](mailto:asha@northwind.test) | Northwind Logistics | Admin |
| [meera@bluepeak.test](mailto:meera@bluepeak.test) | Bluepeak Retail | Admin |
| [ravi@consult.test](mailto:ravi@consult.test) | Both | Employee at Northwind, admin at Bluepeak |
| [priya@northwind.test](mailto:priya@northwind.test) | Northwind Logistics | Employee (Support) |
| [dev@northwind.test](mailto:dev@northwind.test) | Northwind Logistics | Employee (Engineering, lead) |

These are **local demo credentials only**. Do not use this password in production.

The seed also includes `neha@northwind.test` (Northwind Sales), whose completed diagnostic is used to demonstrate data deletion and the five-person privacy threshold. Sales initially has five completed diagnostics; smaller or incomplete departments illustrate hidden dashboard groups.

## Run and test

Run these from the repository root with the Python environment active:

```
python scripts/manage.py test
python scripts/manage.py build
cd frontend
npm test
npm audit --audit-level=moderate
cd ..
```

`python scripts/manage.py test` runs `python -m pytest` inside `backend`. The Node tests use Node's built-in test runner and add no testing library. CI runs backend tests, frontend tests, an npm advisory check and the frontend production build on pushes and pull requests.

A real browser smoke test is available after installing dependencies and building:

```
node scripts/browser-smoke.mjs
```

It requires Chrome/Chromium, Node 22+, Python dependencies and free ports 8000, 5173 and 9223. On Windows it finds Chrome at its usual Program Files location. Set `CHROME_PATH` for another installation; set `PYTHON` if the Python executable has a different path. The script seeds a separate temporary database, starts its own servers and headless browser, and stops those processes when finished. It does not reset the normal demo database. Screenshots and the temporary profile remain in the printed temporary directory.

Local validation: 90 backend tests, 12 frontend tests and the production build passed. The browser test passed login, privacy states, required answers, submission, three suggestions, refresh persistence, deletion cancellation/confirmation, immediate group hiding, mobile overflow and expired-session logout. The original suite had 7 passing tests and one failing seniority test. The corrected tenant tests first failed on the original vulnerabilities before passing with the fix.

Existing deprecation warnings come from the datetime default and test-client dependencies. They are not hidden or treated as proof of failure. Live LLM calls were mocked. The Docker daemon was unavailable locally, so I did not run the container image.

## How I understand the backend

1. Login checks the password and returns a signed JWT with the user's ID and an expiry. It also lists that user's organization memberships.
2. Selecting an organization checks membership and issues another token containing the selected organization ID.
3. Protected routes look up the membership matching both token IDs. The membership supplies the role, department, job role and seniority. A role in one company does not grant permissions in another.
4. Questions come from JSON. Job role and an explicit seniority rank determine which questions are assigned. Ordinary employees have a common open question; senior managers also have a manager-specific open question.
5. Fixed answer choices have fixed scores. Open answers go through the scoring service and an AI reply validator before being saved.
6. Answers belong to a membership, not just a user. A database constraint permits one answer per membership and question. SQLite upsert replaces it on resubmit.
7. Personal reports are computed from that membership's answers. Dashboard results use completed people in the token's organization and enforce the privacy threshold before returning scores or risks.

For a file-by-file study guide and debugging exercises, see [docs/EXPLAINING_THE_CODE.md](https://github.com/avi4rag/ai-pulse/blob/main/docs/EXPLAINING_THE_CODE.md).

## What I found wrong and fixed

| **Problem I found**                                                | **What changed**                                                                                                  |
| ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| An admin could change a dashboard URL to read another company      | The dashboard uses only the authenticated membership's organization; the URL parameter is ignored                 |
| The cross-org test checked the admin's own organization            | It now requests another organization and checks that only the selected organization's results return              |
| Organization selection did not check membership                    | Nonmembers receive 403 before a token is issued                                                                   |
| A signing secret was tracked and passwords used unsalted SHA-256   | `.env` is untracked, production secret checks are enforced and bcrypt adds a random salt to every password        |
| Wildcard CORS, an incorrect Docker entrypoint and unsafe seeding   | Explicit configurable origins, `app.main:app`, selective image copies, a non-root user and a guarded local seed   |
| Headcount distorted averages and maturity scales disagreed         | Average each scored person first, then average those people equally; use one shared scale                         |
| Seniority used alphabetic order                                    | An explicit map orders junior, mid, senior, lead                                                                  |
| Repeat submits duplicated answers and accepted unrelated questions | Unique membership/question pairs, atomic replacement and server-side assignment validation                        |
| AI output was parsed without validation or recovery                | Validate scores, reasons and flags; retry once; save unscored on failure                                          |
| Small groups and their risk flags were visible                     | Require five completers for a department or anonymous combined group; exclude hidden groups from risks and counts |
| Employees could not delete their data                              | Membership-scoped deletion updates reports and dashboards from remaining rows immediately                         |
| Screens dumped JSON and lost session state                         | Plain-CSS screens with progress, suggestions, confirmation, loading/errors, refresh persistence and logout        |

I chose these maturity thresholds because the underlying answers use whole-number scores from 1 to 5: below 2 is Beginner, below 3 is Exploring, below 4 is Practitioner, otherwise Leader. Both reports and dashboards use the unrounded average to choose the level. Rounding is only for display.

The dashboard averages only completed respondents. Within a respondent, `score=None` is excluded. A completed respondent with no valid scores counts toward completion but does not contribute a numeric average. No numeric scores means `average_score=null` and `Not assessed`.

## AI scoring and failure handling

`AI_MODE=mock` is the default. It selects deterministic canned scoring replies from `backend/data/mock_ai_responses.json`, including intentionally invalid examples. `AI_MODE=live` uses `LLM_API_URL`, `LLM_API_KEY` and `LLM_MODEL` with an OpenAI-compatible chat endpoint. Never commit provider credentials.

The validator strips surrounding code fences and requires a JSON object with an integer score from 1 to 5. Booleans, floats, number words and out-of-range values are rejected. Missing reasons receive a default. Flags are limited to `customer_data_shared`, `confidential_data_shared`, `unreviewed_output` and `policy_unaware`; unknown flags are removed. Invalid output or HTTP/timeout failures get one retry. Two failed attempts save an unscored answer with no risk flags, not a zero. Each live request has a 15-second timeout.

System instructions and JSON employee data are separate messages. This reduces prompt injection risk; it does not guarantee that a model will follow the rules. The original scoring call still sends the employee's open answer to the configured provider in live mode. I would confirm provider retention and approved data handling before enabling it.

## How I handled the client request

I define **completed** as having a nonempty answer to every question currently assigned to that membership's job role and seniority. Answered and scored are separate: an AI failure does not make a submitted answer disappear. Changing the question bank or a person's role can change completion under this definition.

A department needs at least five completers to be visible. Smaller departments are combined under `Other teams` only if that combined group has at least five completers. Otherwise the API returns only a generic hidden placeholder. It does not return hidden department names, headcounts, completion counts, scores or risks. Top risks count flag occurrences from visible groups only; they are not counts of unique employees.

`DELETE /reports/me` removes all responses for the caller's **selected organization membership**. It does not delete their account or data in another organization. Reports and dashboards are computed from remaining rows, so the next dashboard request immediately hides a department if it falls below five. An already-open browser screen must refresh to fetch the new result; there is no push notification system. Suggestions are regenerated and return an empty list after deletion.

Questions I would ask Northwind:

- Should deletion cover only the selected organization, or every organization the person belongs to?
- What retention is allowed at the external AI provider, and how should provider-side deletion work?
- What should happen to backups, logs, exports and already-downloaded reports after a deletion?
- Is completion based on today's assigned questions or a saved version of the diagnostic?
- Is five the agreed threshold for every risk breakdown, and do they need extra protection against comparing results before and after one person's change?
- Should small departments be grouped at all, and who may administer memberships and department changes?

A threshold alone does not prove anonymity. Historical comparisons, repeated queries and outside knowledge can reveal more than a single dashboard response. Those risks need a client-approved privacy design before rollout.

## My own feature: personal improvement suggestions

A maturity label tells someone where they are, but does not tell them what to try next. I chose three short actions that help the employee improve their own AI habits.

`POST /reports/me/suggestions` reuses the LLM transport. It sends only the caller's role, seniority, assigned question IDs, scores, allowed flags and fixed answer choices. It does not send names, emails, organization names, membership IDs, other users' data, raw open text or model reasons. I deliberately exclude free text because an employee may type identifying information into it. The feature still uses the diagnostic's scored evidence without forwarding that text again.

Mock mode has canned role/risk suggestions. Live output must be exactly three objects with a title and one-sentence action. Validation caps titles at 60 characters and actions at 240, normalizes text, and rejects links, markup and some obvious unsafe instructions. It retries once and falls back to the existing static role advice. This is a conservative content check, not a complete safety classifier. Suggestions should be reviewed before acting on them.

Suggestions are regenerated rather than stored. After deletion there are no answers to use, and the endpoint returns no suggestions without contacting the provider.

## Configuration, secrets and Docker

`backend/.env.example` explicitly enables local development. The application refuses a missing, short or known development secret unless `DEV_MODE=true`. Production must explicitly set `DEV_MODE=false`, a unique random secret of at least 32 characters, the intended `DATABASE_URL`, approved `CORS_ORIGINS`, and provider settings if live AI is enabled. Environment variables take precedence over `.env` values. Separate multiple origins with commas; `*` is rejected.

Generate a new signing secret locally:

```
python -c "import secrets; print(secrets.token_hex(32))"
```

The old key **remains in Git history**. I kept the existing history and did not rewrite or squash it. The owner must rotate any exposed signing key and provider credential in each deployed environment. Changing the signing key invalidates existing tokens. Untracking a file does not make the leaked value safe again.

Existing SHA-256 hashes are not accepted by bcrypt verification. Development users can reseed; real users need a planned password reset. The new unique response constraint applies to fresh schemas. `create_all` does not migrate an existing database. Before upgrading real data, back it up and write/review a migration that resolves old duplicates and adds the constraint. Do not run the demo seed as a production migration.

The image copies only requirements, app code and data, excludes environment files with `.dockerignore`, runs as an unprivileged user, and starts `app.main:app`:

```
docker build -t ai-pulse backend
docker run --rm -p 8000:8000 --env-file backend/.env ai-pulse
```

That command is a local smoke setup. A production container needs production environment settings, persistent storage, HTTPS termination and operational controls. Docker execution was not verified here because the daemon was not running.

## Current limitations

A clean install exposed existing Vite/esbuild advisories, including a high-severity Windows development-tooling issue. I updated the existing Vite dependency from 5.4.11 to patched 6.4.4, which the current React plugin supports, and regenerated the lockfile. I chose this smaller upgrade instead of forcing the newest major. See the [maintainer advisory](https://github.com/vitejs/launch-editor/security/advisories/GHSA-587h-7wmj-h5pm) and [Vite migration guidance](https://v6.vite.dev/guide/migration). The updated dependency graph reports zero known npm vulnerabilities at validation time. A new development-server CORS test fails on the old Vite version and passes on the patched version. The npm advisory scan is a useful check, not a complete dependency or application audit.

- Alembic migrations and a production data-upgrade plan. Fresh SQLite schemas work; existing schemas need a reviewed migration.
- Postgres and a multi-worker database strategy. The upsert currently targets SQLite, which is the assessment database.
- httpOnly cookie authentication. Tokens remain in localStorage, so XSS can expose them. Logout clears local state but does not revoke a stolen token server-side.
- Rate limiting, enterprise SSO, password reset flows, token revocation, managed secrets and a full audit trail.
- Production hosting, HTTPS, monitoring, backups/retention enforcement and provider contracts.
- A full dependency/security audit, model-quality evaluation and comprehensive accessibility testing. Passing functional tests is not a production security certification.
- Push updates for open dashboards, long-running AI jobs, and caching. Live AI can delay requests and uses a synchronous transport.

## How I used AI tools

I used Codex as a development assistant while working through the project task by task. My workflow was to identify a problem, describe the expected behavior and write down my proposed approach. I then used AI to explore possible solutions, clarify implementation details, troubleshoot errors and help with code and tests before moving on to the next task.

AI assisted with repository inspection, implementation, test creation and running checks. That assistance does not mean I personally wrote or reviewed every generated line. I am reviewing the code, using the [code explanation guide](docs/EXPLAINING_THE_CODE.md), and practising explaining and modifying it independently for the assessment.

AI also made mistakes. In one privacy test, Codex accessed a SQLAlchemy membership object after its session had closed. Because the object's attributes had expired on commit, the test raised `DetachedInstanceError`. The fix was to capture the integer ID while the session was still open. Another test counted rows before committing its setup data while autoflush was disabled. Both issues and their corrections are documented in [AI_NOTES.md](AI_NOTES.md).

I only describe code as personally reviewed once I have actually checked it. The purpose of using AI here was to support problem-solving and learning, not to replace understanding of the implementation.

## Demo recording checklist

1. Run `python scripts/manage.py test`, then `npm test` from `frontend`, and `python scripts/manage.py build` from the root. Show the green CI checks too.
2. Seed the demo, start both servers, and sign in as Asha. Show Sales with five completions and `Other teams` with `Not enough responses`, without hidden counts.
3. Use `/docs` or the authorization tests to show that changing `org_id` cannot switch the dashboard's organization, that an employee gets 403, and that forged/expired tokens get rejected.
4. Sign in as Ravi and show his different permissions in Northwind and Bluepeak.
5. Sign in as an employee and try submitting an incomplete diagnostic. Fill every answer, show progress, submit, inspect the report and its three actions, then refresh to show session persistence.
6. Explain the score validator with the ten canned replies: fenced JSON, score 7, score `four`, missing reason and unknown flags. Show the parametrized tests and the unscored fallback.
7. Show the explicit seniority rank, shared maturity function, equal-person average test, and database uniqueness/resubmit test.
8. Reseed if needed, sign in as Neha (`neha@northwind.test`), open My report, cancel deletion once, then confirm. Show the empty report. Sign in as Asha again and show Sales disappears when completions drop to four.
9. Show `.env.example`, `.gitignore`, the seed guard, Dockerfile and `AI_NOTES.md`. Do not display a real secret on screen.
10. Show a narrow/mobile layout, logout and an error state. Explain the production limitations and client questions rather than claiming everything is production-ready.
