# My code study guide

This is a guide for my own review, not evidence that I already understand every line. Before presenting, I should open each file, explain the data entering and leaving each function, then make a small change without AI.

## Follow one request

Start with a Northwind employee submitting an answer:

1. `frontend/src/api.js` reads the selected token and sends an HTTP request with an Authorization header.
2. FastAPI matches `/diagnostic/submit` to the function in `backend/app/routes/diagnostic.py`.
3. Pydantic reads the JSON body into `SubmitIn`, which contains `AnswerIn` objects.
4. `Depends(current_membership)` asks FastAPI to check the token and find its membership before calling the route.
5. The route loads only assigned questions, validates the answers, calculates scores and builds database values.
6. A SQLite insert either creates a new row or updates the existing membership/question row.
7. `db.commit()` commits the whole batch. The API returns how many answers were saved.
8. React opens the report and fetches the saved summary and improvement suggestions.

I should be able to explain why hiding an option in React is not authorization: someone can send HTTP requests without using the page.

## File-by-file reading order

### `backend/app/models.py`

A model describes a database table. `Mapped[...]` describes the Python value type; `mapped_column` defines the actual column. A primary key identifies one row, and a foreign key points to a row in another table.

- Organization owns departments.
- User represents a person and stores a password hash.
- Membership connects a person to an organization and holds permissions there.
- Response connects an answer to a membership and question.
- `UniqueConstraint` means the database itself rejects two response rows for the same membership and question.
- `score=None` means unscored; it is different from zero.

Practice: draw Ravi as one user with two memberships. Explain why a response stores `membership_id` instead of just `user_id`.

### `backend/app/config.py` and `db.py`

Configuration loads environment values. Existing process environment values win because `setdefault` only fills a missing value. Development mode must be explicit; production refuses an unsafe secret.

The database engine connects to SQLite. `SessionLocal()` creates a database session for a unit of work. This is unrelated to a browser login session. `get_db` yields that session and closes it in `finally`, including when a request fails.

`autoflush=False` means pending Python objects are not automatically sent to the database before a query. `flush()` sends pending writes into the current transaction; `commit()` commits that transaction. Neither is the same as closing a session.

Practice: explain why counting rows before flushing or committing newly added objects can give the wrong test baseline.

### `backend/app/auth.py`

`bcrypt.gensalt()` creates random salt. `hashpw` combines that salt with the password to produce the stored hash. `checkpw` checks an entered password against the stored hash; it does not need to recover the original password.

`make_token` creates a payload with `sub` (user ID), `org` (selected organization) and `exp` (expiry). A JWT is signed, not encrypted. Do not store secrets inside its payload.

`_decode` accepts a Bearer token, verifies its signature and expiry, requires `sub` and `exp`, and checks the ID shapes. Invalid tokens produce HTTP 401.

`current_user` finds the user for login-level actions. `current_membership` requires a selected organization and looks up the pair of user ID and organization ID. Missing membership produces 403.

Practice: explain the difference between 401 (authentication failed), 403 (permission denied) and 400 (invalid request or organization not selected).

### `backend/app/routes/auth_routes.py`

Login looks up the user, verifies the password and lists memberships. Selecting an organization first queries for membership; it issues a token only after that query succeeds.

Practice: Ravi is an admin in Bluepeak but an employee in Northwind. Explain why his Northwind token cannot read a dashboard.

### `backend/app/services/questions.py`

The JSON file is the question bank. The function loops through questions and skips those for other roles or a higher seniority rank. Rank numbers express the intended order; alphabetical string comparison does not.

Practice: add a seniority level on paper and explain which map entries and questions would need review. Explain why changing the question bank may affect whether an old diagnostic counts as complete.

### `backend/app/routes/diagnostic.py`

The questions endpoint replaces scoring option objects with option text so the client does not receive point values. The submit endpoint repeats assignment checks on the server.

The first loop validates and prepares the whole batch. If any item is invalid, no upsert has run. The second loop performs the writes. `on_conflict_do_update` tells SQLite to replace answer, score, reason and flags if the unique key already exists.

Practice: submit the same question twice in one body versus sending a valid body twice. The first is rejected; the second replaces the answer. Explain why a Python check alone would not reliably prevent simultaneous duplicate inserts.

### `backend/app/services/llm.py` and `scoring.py`

The wrapper chooses mock replies or sends an HTTP request. The prompt's system message contains instructions; employee JSON is in a separate user message. This separation helps but does not prove injection is impossible.

The validator first handles text formatting and JSON parsing, then checks the object shape, score type/range, flag types and allowed labels. `type(score) is int` intentionally excludes booleans: in Python, `isinstance(True, int)` would be true.

The scoring function tries twice. It returns as soon as validation succeeds. After both attempts fail, it returns the unscored result. Transport errors are handled at this boundary too.

Practice: predict what happens for score 7, score 4.0, score true, no reason, and an unknown flag. Find each case in the tests.

### `backend/app/utils.py` and `routes/dashboard.py`

`maturity_level` is shared by reports and the dashboard. It receives the unrounded average.

`department_statistics` first checks whether each person answered all assigned questions. It calculates each completed person's average from valid scores, then averages those person averages. It also collects risk occurrences from those completed answers.

The route checks admin permission and reads only `m.org_id`. It releases a department's statistics only if five people completed. Smaller groups are combined and checked again. Hidden output contains only a generic name and `hidden=True`; the UI cannot accidentally display counts it never receives.

Practice: person A has scores 1 and 1; person B has four scores of 5. Their equally weighted average is `(1 + 5) / 2 = 3`, not the average of all six answers. Now explain which people count if one has an unscored open answer.

### `backend/app/routes/reports.py` and `services/suggestions.py`

The report filters by the current membership. Deletion uses the same filter and commits before returning. No report table or dashboard cache exists to invalidate.

Suggestions deliberately build a new limited payload rather than serializing the user or membership object. Fixed multiple-choice text is allowed; raw open text and model reasons are excluded. The validator requires three safe-looking bounded items, or the endpoint falls back to static role guidance after two failed attempts. A content filter cannot guarantee every model response is sensible.

Practice: explain why deletion in Northwind does not delete Ravi's Bluepeak data. Explain why suggestions return no actions after deletion without calling the provider.

### Frontend files

- `App.jsx` owns the current session and screen. State changes cause React to render the matching page.
- `api.js` sends tokens, parses JSON, handles errors and clears expired sessions. localStorage persists across refresh but has XSS risks.
- `Login.jsx` and `OrgPicker.jsx` handle sign-in and membership selection with pending/error states.
- `Diagnostic.jsx` keeps answers in an object keyed by question ID. It counts nonempty answers and submits only when every assigned question is answered.
- `Report.jsx` fetches the report and suggestions, then provides cancellation/confirmation for deletion.
- `Dashboard.jsx` renders visible groups and a hidden placeholder, with no hidden counts in its summary cards.
- `styles.css` controls layout and uses media queries to change spacing and columns on narrow screens.

`useState` stores component values between renders. `useEffect` performs work such as fetching data after rendering. The AbortController cleanup cancels a page's fetch when the page unmounts or retries, helping prevent stale results from updating it.

Practice: disconnect the backend and explain how the error reaches the page. Refresh a signed-in page and follow where the token, session metadata and page selection come from.

## How to debug without AI

1. Reproduce one problem with a specific account, organization, URL and request body.
2. Read the browser Network tab: request headers/body, response status and response JSON.
3. Find the matching route, then trace its dependencies before the route body.
4. Add a small failing test for the observed behavior. Read fixtures to know which data exists.
5. Change the smallest responsible function and rerun that test, then the full suite.
6. Read the diff and explain every changed expression before committing.

Never print a real password, token or signing key while debugging or recording. Use synthetic examples and avoid resetting a database until its path and purpose are clear.
