# AI implementation notes

## Job 1: Tenant isolation

Scoped dashboard reads to the authenticated membership and checked membership before organization selection. Regression tests first failed on both original vulnerabilities. The pre-existing lead-manager test remains failing until job 3.

My mistake: I initially tried reading README.md from the workspace parent directory. The Git repository was actually in its ai-pulse subfolder. Those commands failed without changing files. I corrected the working directory before reviewing the code.

## Job 2: Secrets and passwords

Untracked backend/.env, added a development template, required a strong production secret, added salted bcrypt passwords, configurable CORS, a non-root Docker image, and a development/local-database seed guard. All eight new security tests pass; full suite: 16 passed and the existing seniority failure remains. Rotate the old signing key manually; it remains in history. Existing SHA-256 accounts need password resets or a development reseed.

My mistake: my first patch tried deleting and adding the same path in one operation, which the patch tool rejected. No partial edits were applied; I reapplied it as an update.

## Job 3: Scoring and question assignment

Averaged each respondent before departments, shared the <2/<3/<4 maturity scale, ranked seniority explicitly, enforced assigned questions, and used a unique constraint plus SQLite upsert to replace answers. Tests cover unequal answer counts, unassessed groups, thresholds, invalid batches, role/seniority restrictions and database uniqueness. Full suite: 29 passed. Existing databases need a planned migration before using the new constraint; development databases can be reseeded. No new implementation mistake found in this job.

## Job 4: AI validation

Validated all ten canned replies, stripped code fences, required integer scores 1–5 (excluding booleans), filtered flags, defaulted reasons and retried once before saving unscored answers. Separated system instructions from JSON employee data and bounded live requests to 15 seconds per attempt. Tests cover malformed shapes, retries, HTTP/timeout failures, prompt separation and unscored persistence. Prompt separation reduces injection risk; it does not prove model obedience. No new implementation mistake found.

## Job 5: Small-group privacy

Defined completion as a nonempty answer to every currently assigned question, including unscored open answers. Only completers contribute scores and risks. Departments need five completers; smaller departments combine anonymously only if Other teams reaches five, otherwise return just a hidden placeholder without names or counts. Seed now has five completed Sales members and small incomplete departments. Updated earlier tests for this intentional seed change.

My mistake: a privacy test accessed an expired SQLAlchemy object after its session closed, causing DetachedInstanceError. I saved its integer ID before closing the session and reran the suite.

## Job 6: Right to delete

Added DELETE /reports/me scoped to the authenticated membership. Reports and dashboards are computed from remaining rows immediately; repeated deletion is harmless. Tests verify five-to-four suppression, empty reports, authentication, other-user preservation and the caller's other organization remaining unchanged.

My mistake: the cross-organization test counted rows before committing its setup. With autoflush disabled, that excluded the two new rows. I moved the baseline count after commit.

## Job 7: Personal improvement suggestions

Added POST /reports/me/suggestions with three validated actions, mock and live support, one retry and existing role advice as fallback. Sends only the caller's role, seniority, question IDs, scores, allowed flags and fixed answer choices. Raw open text and reasons are excluded to avoid forwarding embedded identifiers. Suggestions regenerate, so deletion leaves no stored copy and subsequent requests return none. Frontend display follows in job 9. Full suite: 80 passed; live calls are mocked.

My mistake: adding a final full stop after a 240-character cap could produce 241 characters. I reduced the pre-punctuation cap and tightened the test. The content filter is conservative basic validation, not a guarantee against every unsafe model suggestion.

## Job 8: Developer experience

Added a Python command runner for backend/frontend/test/build/seed, clean-checkout environment setup, and GitHub Actions for Python tests plus npm ci/build. Added employee/admin, multi-org permissions, expired/forged/missing/malformed claim coverage; malformed signed IDs now return authorization errors. Validation: 90 backend tests pass; npm ci and production build pass. The first build hit a Windows sandbox ancestor-directory access restriction; rerunning with approved filesystem access passed without changing build code. Docker image execution has not been verified locally. No new implementation mistake found.

## Job 9: Frontend

Replaced JSON output with a responsive dashboard, hidden-group states, visible-only summary counts and risk signals. Added persistent validated session metadata, logout/401 cleanup, diagnostic progress and required answers, reports with private suggestions, deletion confirmation, and loading/error/retry states. Added 11 built-in Node API/session tests and a dependency-free headless Chrome smoke script using an isolated temporary database. Validation: 90 backend tests, 11 frontend tests and production build pass. Browser smoke passed login, admin privacy, incomplete-submit prevention, submission, suggestions, refresh persistence, cancel/confirm deletion, five-to-four hiding, mobile overflow and session expiry. Inspected desktop and mobile screenshots.

My mistakes: a single write command exceeded Windows' command-length limit before running, so I split the writes. The first browser selector expected a button label without its decorative arrow; I changed it to match the label prefix and reran successfully. The Docker CLI exists but its daemon is not running, so container execution remains unverified.

## Job 10: Assessment documentation

Rewrote the README in first-person draft form with setup, architecture, fixes, privacy/completion decisions, client questions, personal suggestions, operational limits, secret rotation, migration/reset requirements, AI usage and a real SQLAlchemy test mistake. Added a file-by-file study guide and debugging exercises rather than claiming the student already reviewed generated code. A clean source archive passed template copy, demo seed, 90 backend tests, npm ci, 11 frontend tests and build. A full runtime/provider/container security review remains outside these checks.

The clean npm install exposed two existing tooling vulnerabilities (one high, one moderate). I inspected the npm report and maintainer guidance instead of applying npm audit fix --force. A separate follow-up security branch will update Vite to a compatible patched release. No new documentation mistake found.

## Follow-up: Development dependency security

The clean-install advisory scan exposed vulnerable existing Vite 5.4.11/esbuild tooling. Verified maintainer guidance and plugin compatibility, then upgraded only the existing Vite dependency to patched 6.4.4 and regenerated its lockfile. Added npm audit to CI and a real development-server CORS regression: it failed against the old version because an arbitrary Origin received Access-Control-Allow-Origin: *, and passes on the patched version. The updated npm audit reports zero known vulnerabilities. Validation: 90 backend tests, 12 frontend tests, production build and the complete isolated browser smoke pass. Rechecked the patched lockfile with a fresh install in the clean archive.

My mistakes: the first attempt to copy the regression test into the old clean archive used a frontend-relative path while already inside frontend; it failed without copying, and I corrected it to an absolute path. A documentation patch matched only part of a long line and was rejected before changes; I corrected the replacement. No forced audit upgrade or new direct frontend library was used.

## Demo deployment publication

The existing Dockerfile commit seeds demo data before startup and reads PORT with an 8000 fallback. Published it through a PR explicitly targeting avi4rag/ai-pulse:main, preserving the fork's newer README changes. Demo hosting requires DEV_MODE=true and the guarded local SQLite URL; every container restart reseeds the demo database. Container execution remains unverified because the Docker daemon was unavailable.

My mistake: I previously reported that deploy-demo was pushed without clearly explaining that the fork's main branch did not contain it yet. I checked both repositories and found no existing deploy-demo PR in either; the change was on a branch of the fork, not merged into upstream. This PR corrects the missing integration into the fork's main branch.
