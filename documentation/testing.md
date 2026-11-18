# Testing

## Suites

| Suite | Command | Covers |
|---|---|---|
| Backend unit/integration (65 tests) | `cd backend && pytest` | Models and constraints; project/requirement CRUD, search, pagination; full workflow through the API (all 5 checkpoints, correction loop, docs, zip); revision and rejection routing; edited requirements flowing downstream; cancellation and conflicts; second domain (inventory); analytics; auth/RBAC; rate limiting; path traversal; prompt wrapping; LLM client (mock HTTP transport); agent retries with a fake LLM; static checks; JUnit parsing; sandbox timeout handling; Docker command hardening |
| Lint | `cd backend && ruff check .` | pyflakes, pycodestyle, import order, bugbear, pyupgrade |
| Migrations | `cd backend && alembic upgrade head && alembic check` | Migrations apply and match the models |
| Frontend build | `cd frontend && npm run build` | Compiles all pages |
| End-to-end (Playwright) | `cd frontend && npm run test:e2e` | Starts a fresh backend and the Vite dev server, then runs the full leave-management demo in Chromium (create → 5 approvals → correction → docs → zip download → analytics → reload persistence, with no console errors) plus project search/edit and revision request |

Set `E2E_SCREENSHOTS=/some/folder` to save a screenshot of every demo step.

## Test isolation

- Each backend test gets its own temporary SQLite file and storage folder. Workflows run inline in mock mode with the sandbox disabled, so results are deterministic and need no network.
- E2E tests use `backend/.e2e/` (recreated on every run) and separate ports (8011/5181), so they never touch your real data.

## Testing generated code (inside the platform)

1. **Static checks** (always run, never execute code): every `.py` file is parsed with `ast`, Ruff runs with rules `E9,F63,F7,F82` (syntax errors and undefined names), and the presence of test files is checked.
2. **pytest in the Docker sandbox**, only after the *test execution* checkpoint is approved. Results are read from the JUnit XML report.
3. Any failed or errored check, or a critical review issue, triggers **controlled correction** (at most two). Each iteration's results are stored separately (`test_results.iteration`).
4. If Docker is unavailable, the suite is recorded as **skipped**, and the UI, test report and final report all say so.
