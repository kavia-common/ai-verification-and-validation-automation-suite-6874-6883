# V&V Backend API (Flask)

Backend for the AI-enabled Verification & Validation automation suite.
Provides REST endpoints for:
- SRS creation
- Test case generation (LLM-backed, mock by default)
- Script generation (pytest + Playwright)
- Test execution and results reporting

Docs: once running, visit /docs for Swagger UI.

Quickstart
- Python 3.11+
- Create and activate a virtualenv
- pip install -r requirements.txt
- Run: python run.py (defaults to Flask dev server on 127.0.0.1:5000)

CORS
- The API explicitly allows the frontend at http://localhost:3000 by default.
- You can override via REACT_APP_FRONTEND_URL.

Environment variables
- REACT_APP_FRONTEND_URL: Frontend origin for CORS (default http://localhost:3000)
- DATA_DIR: Base data directory (default ./data)
- DATABASE_URL: Optional; if set (e.g., Postgres), used as the DB connection string
- LLM_PROVIDER: Provider name (default mock)
- LLM_MOCK: Set true/false; mock is default and deterministic
- LLM_API_KEY: Optional key for real LLM providers

Database behavior
- If DATABASE_URL is set, it is used as-is (supports Postgres via psycopg2-binary).
- If not set, the app falls back to a local SQLite file at {DATA_DIR}/app.db.
- Tables are created on startup if they do not exist.

Notes
- Execution uses pytest; Playwright is installed via requirements. Ensure any browser dependencies are satisfied in your environment if running real UI tests.
