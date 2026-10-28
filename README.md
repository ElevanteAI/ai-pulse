# AI Pulse

AI Pulse measures practical, safe AI adoption by role. Employees complete a role-aware diagnostic and receive a private report; organization admins see only privacy-safe trends.

## What changed

The inherited prototype ran, but was not safe to give to a client. This branch fixes the highest-risk issues:

- **Tenant isolation:** organization membership is verified before a scoped token is issued. The dashboard gets its organization from that token, never a browser-supplied ID.
- **Northwind privacy:** a department needs at least five completed diagnostics to appear. Small departments are combined as `Other teams` only when that combined group also reaches five; risk trends use the same rule.
- **Right to delete:** `DELETE /reports/me` hard-deletes the selected employee's answers and assessments. Dashboard calculations use current data, so the removal is immediate.
- **Assessment integrity:** a submission must contain every assigned question exactly once. Reports and dashboards use only the latest completed assessment.
- **Correctness:** seniority is an explicit rank, role-inappropriate questions are rejected, and all maturity labels share one implementation.
- **AI guardrails:** only schema-valid model output is stored: integer scores 1–5 and approved risk flags. Provider/model failures save nothing.
- **Configuration security:** real `.env` files are ignored and removed from Git. Production rejects the default JWT secret; CORS is allow-listed and live AI settings are checked at startup.
- **Usable & Captivating UI:** a minimalist luxury **Beige and Navy Blue** corporate aesthetic with persistent `← Back` navigation, interactive option cards, progress tracking, credential autofill chips, and explicit erasure modals.
- **Original Feature (Pulse Practice):** connects diagnostic weaknesses to **in-platform interactive practice sandboxes** evaluated by live AI mentoring, supplemented with bonus authoritative deep-dive links.

## Northwind's request

Both requested changes are implemented.

1. Department score and risk data are hidden below the five-completed-person threshold. `Other teams` is only returned when it is itself large enough to be anonymous.
2. **Delete my diagnostic data** permanently removes a user's answers and report in their selected organization, and immediately removes their dashboard contribution.

Confirm before production: whether legal retention overrides hard deletion; whether a minimal deletion audit record is permitted; whether five is correct in every jurisdiction; and exactly which leadership roles may see aggregated data.

## Original feature: Pulse Practice (In-Platform Sprints & Live AI Review)

A generic recommender merely offers disconnected external links that employees rarely click. Pulse Practice keeps learning **directly on the platform**:
**Diagnostic Evidence ➔ In-Platform Interactive Sandbox ➔ Live AI Mentoring Review ➔ Bonus Authority Deep Dive.**

- **The Problem It Solves:** Diagnostic tests show employees *where* they stand, but leave them wondering *how* to improve safely without context switching.
- **How It Works:**
  - Evaluates specific low scores ($\le 3$) and critical risk flags (`customer_data_shared`, `unreviewed_output`, `policy_unaware`) across roles.
  - Generates a tailored **In-Platform Practice Sandbox** for each identified gap (e.g. Redacting raw customer PII, writing unit test edge cases for AI code, or refactoring vague prompts).
  - **Live AI Evaluation:** Employees submit their solution directly on the platform; live AI reviews their attempt and awards a *"Practice Completed ✅"* score.
  - **Bonus Authority Resources:** Pairs every challenge with an external deep-dive guide from OWASP, Google Cloud, GitHub Docs, Anthropic, or NIST as an optional bonus.

## Run locally

Prerequisites: Python 3.12+ and Node.js 20+.

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. `python -m app.seed` deletes and recreates the local database; it is demo-only.

### AI modes

Tests use safe, deterministic `AI_MODE=mock`. For a local Groq demonstration, keep credentials only in untracked `backend/.env`:

```env
AI_MODE=live
LLM_API_URL=https://api.groq.com/openai/v1/chat/completions
LLM_API_KEY=your-local-groq-key
LLM_MODEL=openai/gpt-oss-20b
```

Never commit or put this key in frontend code. A live provider must not receive enterprise data until client data-processing approval, provider retention terms, data region, and prompt-redaction rules are agreed.

## Demo accounts

All seeded accounts use password `pulse123`.

| Email | Organization(s) | Role |
|---|---|---|
| asha@northwind.test | Northwind Logistics | Admin |
| meera@bluepeak.test | Bluepeak Retail | Admin |
| ravi@consult.test | Both | Northwind employee; Bluepeak admin |
| priya@northwind.test | Northwind Logistics | Support employee |
| dev@northwind.test | Northwind Logistics | Engineering lead |

## Verify

```bash
cd backend && python -m pytest -q
cd frontend && npm run build
```

Tests cover tenant isolation, organization selection, role-question enforcement, seniority, small-group suppression, deletion, and malformed AI output.

## Deliberately left for a production rollout

- Replace SQLite and `create_all()` with managed PostgreSQL and Alembic migrations.
- Migrate inherited SHA-256 passwords to Argon2id/bcrypt.
- Add SSO/SAML, MFA, login rate limits, secure HTTP-only sessions, audit logs, monitoring, backup, encryption/key management, accessibility and independent security testing.
- Version question banks and establish formal assessment/retention policies.

## AI-tool disclosure

AI tools were used to map the codebase, generate test ideas, and review edge cases. Every change was read and tested. One rejected AI suggestion was to label the sparse inherited demo answers as complete assessments simply to populate the dashboard; that would misrepresent the product, so completion is instead enforced by validated full submission.
