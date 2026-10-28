# Recording walkthrough (about 5 minutes)

A suggested order for the screen recording. Reseed first so the numbers match: `cd backend && python -m app.seed`.

| Time | Show | Say |
|---|---|---|
| 0:00 | `git log --graph --oneline` | Original history kept; one branch per fix, each with tests, then the second-pass commits on `review/skills-second-pass`. |
| 0:20 | `docs/SECURITY_AUDIT.md` summary table | 26 findings, reproduced before fixing, plus V27–V33 from reviewing my own fixes. The worst three: cross-tenant dashboard, committed signing key, AI inventing labels like "probably_lying". |
| 1:00 | `python -m pytest -q` (95 pass). Optionally run `tests/test_isolation.py` against the original `dashboard.py` to show 4 failures | Proof, not claims. |
| 1:40 | Sign in as **asha@northwind.test** → dashboard | Sales/Support shown; Engineering + HR pooled into "Other teams"; overall = sum of shown groups. |
| 2:20 | Policy reality check card + "Policy gap" column | My feature: "10 of 16 say they follow the policy, 3 of them still risky". Training, not another policy email. |
| 2:50 | Sign in as **meera@bluepeak.test** | Only 2 respondents → no scores, no risks at all. Small teams are listed by name only, so the page doesn't show who took part. |
| 3:10 | Sign in as **neha@northwind.test** → report | Private policy evidence; what the AI said and which model; mock labelled as demo. |
| 3:40 | Sign in as **vikram@northwind.test** → Delete my data → back to Asha's dashboard | Sales drops to 4 and disappears immediately. Client request 2 + request 1 working together. |
| 4:00 | `python -m app.eval` | Say it's mock mode, so the score numbers mean nothing. The real result: the injection screen catches 2 of 6 attempts and wrongly excludes 2 of 24 genuine answers. Live model not run. |
| 4:30 | README "What I deliberately left" + questions for Northwind | Key rotation, differencing over time (measured: 4.08 vs a real 4.00), live AI evaluation not run, Docker and GitHub Actions unverified. |
