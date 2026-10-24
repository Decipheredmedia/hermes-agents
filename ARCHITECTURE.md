# Instagram agent platform: Stage 1

This is a staged, minimal working system added alongside Hermes Agent; it does not extend or alter
Hermes core. Stage 1 supports structured content drafts, local planning, manual approvals, and a
mock scheduling flow.

## Architecture and boundaries

- `agents/` holds eleven reusable Markdown skill definitions. Profile audits and comment/reply
  drafts are supporting, on-demand tasks rather than mandatory pipeline steps.
- `orchestrator/` coordinates trend research → planning → hook extraction → content critique →
  caption/Reel draft → grid plan → required human approval → mock schedule. Audience feedback is
  summarized for the next planning cycle.
- `backend/` provides a FastAPI API, SQLAlchemy persistence (SQLite by default; a PostgreSQL URL may
  be supplied), a configurable Ollama client, and a mock-only Instagram adapter.
- `dashboard/` is a small static admin UI. `n8n/content-pipeline.json` demonstrates the handoff.

Local inference, draft generation, planning, and the dashboard may run without Instagram access.
The sample planner and integration are deliberately deterministic/mocked until an operator supplies
their own inference server and authorized information sources. Trend sources require their own API
keys or authorization.

No live Instagram publishing, DM, comment-reading, or comment-sending path is implemented. The
mock scheduler rejects every item not explicitly marked approved. Real Instagram API work is
deferred until an eligible Business account, Meta App review, permitted scopes, and authorized
credentials are supplied. Never use scraping or unofficial endpoints.

## Deliberately deferred to Stage 2

- Real Meta Graph API OAuth, token lifecycle, permission checks, rate-limit/retry behavior, and
  supported publishing/insights calls. Current integration methods are mock-only stubs.
- Polished dashboard styling, authentication, multi-user access control, and production deployment
  hardening. Bind the sample services to localhost; do not expose them directly to the internet.
- Analytics attribution beyond explicitly marked mock data; no growth, revenue, or reach is inferred.
- Authorized external trend-source connectors and verified account analytics.
- Production scheduling, duplicate-job handling across workers, and timezone-aware publishing.

## Local development

1. Create a local `.env` from `.env.example`, or copy `config.yaml.example` to `config.yaml` and
   fill in only local values. All values begin blank; both local files are ignored by git, and
   `.env` must remain private.
2. From the repository root, in a shell without Hermes activation, create a separate backend
   environment with `python -m venv backend/.venv` (use a fresh destination). Install dependencies
   with `backend/.venv/bin/python -m pip install -r backend/requirements.txt`. Do not install these
   requirements into a PM-managed Hermes environment.
3. Run `backend/.venv/bin/python -m uvicorn backend.app.main:app --reload --env-file .env`
   from the repository root.
4. Open `http://127.0.0.1:8000/docs`; serve `dashboard/` with
   `python -m http.server 8080 --directory dashboard` for the dashboard.
5. Set `OLLAMA_HOST` and `OLLAMA_MODEL` to a local authorized Ollama instance/model when using
   inference. The model name is not fixed in code.
6. For containers, copy `.env.example` to `.env` and use `docker compose up --build`. Services bind
   to loopback by default. Import the workflow with
   `docker compose exec instagram-n8n n8n import:workflow --input=/files/content-pipeline.json`,
   then activate it in n8n. After setting `OLLAMA_MODEL` in `.env`, pull it with
   `docker compose exec instagram-ollama ollama pull "$OLLAMA_MODEL"`. Approve the draft in the
   dashboard before resuming the waiting execution's generated approval webhook URL; the mock
   schedule endpoint remains approval-guarded.

Tests use fake data and mocked Instagram responses; they never require Meta credentials or contact
Instagram. In the separate backend environment above, run from the repository root:

```bash
backend/.venv/bin/python -m pip install -r backend/requirements-test.txt
HERMES_PYTHON="$PWD/backend/.venv/bin/python" scripts/run_tests.sh tests/instagram_platform/ --confcutdir=tests/instagram_platform/
```

The canonical runner clears credentials and isolates test processes. `--confcutdir` limits fixture
loading to this standalone platform suite, whose API fixture uses a temporary SQLite database;
the parent Hermes fixtures import unrelated core dependencies. Keep the normal Hermes fixture
configuration when testing Hermes itself. `httpx2` is intentional: current Starlette `TestClient`
uses it through FastAPI. On Windows, use `backend/.venv/Scripts/python.exe` and run the test
command in Bash.
