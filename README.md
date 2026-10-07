# Ledger: LLM Cost Tracker and Advisor

A full-stack tool that tells you what an LLM prompt will cost across OpenAI, Anthropic, and Groq models, logs your usage, and uses an AI advisor to point out where you might be overspending.

## The problem

Teams using LLMs often do not know what they are spending until the bill arrives. Checking spend programmatically through the providers is also harder than it looks: OpenAI and Anthropic only expose cost data through organization-level Admin API keys, and Groq exposes no usage API at all. Most individual developers cannot get that access.

## The approach

Instead of asking a provider what you spent, this project calculates cost directly from token counts, using each provider's most accessible method:

| Provider | How tokens are counted | Key required | Accuracy |
|---|---|---|---|
| OpenAI | `tiktoken`, run locally | None | Exact |
| Anthropic | `/v1/messages/count_tokens` endpoint | A regular API key (not an Admin key) | Exact |
| Groq / Llama | `tiktoken` with a similar BPE encoding | None | Approximate, labeled in the API and UI |

No prompt content is routed through this service on its way to a provider. An earlier version was designed as a request proxy, and was rejected before it was built because it would expose private prompts to a third party and make the service a single point of failure for the user's own app.

## Features

- **Live cost playground:** paste a prompt and see a ranked, animated cost leaderboard across all supported models. Works with no login for OpenAI and Groq models.
- **Context window checks:** models that cannot fit the prompt are flagged instead of showing a misleading price.
- **Accounts and encrypted key storage:** JWT authentication, bcrypt password hashing, and provider keys encrypted at rest with Fernet.
- **Usage history and AI advisor:** a deterministic pattern-finder aggregates your logged spend, then an LLM recommender (Groq) writes a short suggestion constrained to reason only from those numbers.
- **MCP server:** the same data and advisor are available to MCP clients such as Claude Desktop, authenticated with a per-user API key.

## Architecture

```
Browser
   |
Next.js frontend (Vercel)
   |  HTTPS + JWT
FastAPI backend (Docker, Render)
   |-- Tokenizers: tiktoken (OpenAI, Groq approx), Anthropic count_tokens
   |-- Pricing table + cost calculation
   |-- Pattern-finder (deterministic) -> Recommender (Groq LLM)
   |-- Fernet encryption for stored provider keys
   |
PostgreSQL (Neon)

MCP server (FastMCP) -> same database, authenticated by API key
```

## Tech stack

- **Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL (Neon), `tiktoken`, `httpx`, Groq SDK, FastMCP
- **Security:** JWT (python-jose), bcrypt (passlib), Fernet (cryptography)
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Infrastructure:** Docker, Render, Vercel, GitHub Actions
- **Testing:** pytest, `unittest.mock`, FastAPI TestClient

## Project structure

```
llm-cost-tracker/
  .github/workflows/ci.yml
  backend/
    app/
      agents/          pattern_finder.py, recommender.py
      routers/         auth.py, keys.py, usage_log.py, advisor.py, api_keys.py
      tokenizers/      openai_tokenizer.py, anthropic_tokenizer.py, groq_tokenizer.py
      config.py, database.py, models.py, schemas.py, security.py, pricing.py, mcp_server.py
    tests/
    Dockerfile
    main.py
    requirements.txt
  frontend/
    app/, components/, hooks/, lib/
```

## API overview

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/signup` | None | Create an account (password needs 8+ chars, upper, lower, number, symbol) |
| POST | `/auth/login` | None | Returns a JWT |
| GET | `/auth/me` | JWT | Current user |
| GET / POST / DELETE | `/keys` | JWT | List, add, or remove connected provider keys (raw keys are never returned) |
| POST | `/usage/log` | JWT | Count tokens, calculate cost, and log usage |
| GET | `/advisor` | JWT | Usage patterns plus an AI recommendation |
| POST | `/api-keys` | JWT | Generate an MCP API key (shown once) |

Interactive docs are available at `/docs` on the running backend.

## MCP tools

- `get_usage_summary(api_key, days)`: total spend and a per-provider breakdown
- `get_cost_advice(api_key)`: the same advisor recommendation as the dashboard

Generate an API key from the dashboard, then pass it to the tool.

## Running locally

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

Create `backend/.env`:

```
DATABASE_URL=sqlite:///./dev.db
ENCRYPTION_KEY=<generated, see below>
JWT_SECRET=<generated, see below>
JWT_EXPIRE_MINUTES=60
GROQ_API_KEY=<your Groq key>
```

Generate the two secrets:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run it:

```bash
uvicorn main:app --reload --port 8000
```

For production, use a Postgres connection string in `DATABASE_URL`. Never commit `.env`.

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
```

Then open http://localhost:3000. Add `http://localhost:3000` to the CORS allowlist in `backend/main.py` if it is not already there (it is by default).

### Tests

```bash
cd backend
python -m pytest tests/ -v
```

External calls (Groq, Anthropic, tiktoken's one-time encoding download) are mocked, so the suite runs without network access or real keys.

## Deployment

- **Backend:** Docker image deployed on Render with the root directory set to `backend`. Required environment variables: `DATABASE_URL`, `ENCRYPTION_KEY`, `JWT_SECRET`, `GROQ_API_KEY`.
- **Frontend:** Vercel with the root directory set to `frontend` and `NEXT_PUBLIC_API_URL` pointing at the backend.
- **CI:** GitHub Actions runs the full pytest suite on every push and pull request.
- **CORS:** the backend allowlists exact origins. Vercel also generates per-deployment preview URLs that differ from the stable production domain, so test against the production URL or add the preview origin.

## Design decisions

- **Deterministic first, LLM second.** The advisor never calculates anything itself. Cost and aggregation are plain code, and the LLM only writes commentary about numbers it was given.
- **Honest approximation.** Groq has no token-counting endpoint and Llama has no official offline tokenizer, so Groq counts are an estimate and the API returns `approximate: true`, which the UI shows as a badge.
- **Encrypt, do not hash, provider keys.** Passwords and MCP API keys are hashed because they only need verification. Provider keys must be recoverable to call the provider, so they are encrypted.
- **Connection resilience.** The SQLAlchemy engine uses `pool_pre_ping` and `pool_recycle` to survive Neon closing idle connections.

## Known limitations

- The pricing table in `pricing.py` is maintained by hand and needs updating when providers change prices.
- Groq token counts are approximate, typically within a modest margin for English text.
- While signed in, every playground calculation is logged as usage, so the history reflects pricing experiments as well as real usage.
- MCP API key verification compares against every stored key hash, which is fine at small scale but needs a prefix-indexed lookup to scale.
- Rotating `ENCRYPTION_KEY` makes existing stored provider keys undecryptable. There is no key versioning yet.
- Schema creation uses `create_all()`. A production setup should move to Alembic migrations.
- No rate limiting or retry and backoff on outbound provider calls yet.
- Free-tier hosting means cold starts after idle periods.

## Possible next steps

- Alembic migrations and encryption key versioning
- Indexed MCP key lookup
- Rate limiting and retries for provider calls
- Separating real usage logging from playground pricing
- Automated pricing table updates

## Author

Meeran Ahmed. [GitHub](https://github.com/Meeran039)
