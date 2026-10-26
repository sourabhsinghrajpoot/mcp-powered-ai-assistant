# MCP-Powered AI Assistant

A modular starter application with a FastAPI backend, Next.js chat UI, persistent conversations, document text extraction, real OpenAI-compatible chat completions, and a bundled MCP server. The backend sends chat history to the configured provider using HTTPX; API credentials remain on the backend. The bundled MCP server runs over the official MCP Python SDK's stdio transport; `/api/mcp/tools` discovers its tools at runtime and `/api/mcp/execute` invokes them over MCP.

## Current scope

Working foundations: email/password registration and login with Argon2 password hashing and JWTs; per-user conversation and document ownership; SQLite development persistence; PDF, DOCX, Markdown, and TXT text extraction; basic in-document keyword search; OpenAI-compatible LLM chat; and MCP `get_current_time` and `calculate` tools. The chat UI loads the most recent conversation, sends messages to the backend, and displays provider errors rather than inventing model responses. Register accounts with the documented API. Integrations such as GitHub, hosted web search, custom APIs, database natural-language queries, migrations, audit UI, and OAuth are not implemented in this starter and must not be considered enabled.

## Requirements

- Python 3.12+ (3.11 may work)
- Node.js 20+
- Optional: Docker Compose
- An API key and model name for an OpenAI-compatible chat-completions endpoint to receive actual AI responses

## Run locally

From the repository root in PowerShell:

```powershell
Copy-Item backend/.env.example backend/.env -Force
python -m venv backend/.venv
backend\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

Before sending chat messages, edit `backend/.env` and set:

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-provider-api-key
LLM_MODEL=your-provider-model-name
```

These are backend-only settings. `LLM_BASE_URL` is the provider API base URL (ending in `/v1` for OpenAI); the backend appends `/chat/completions`. The same variables work with providers that implement the OpenAI chat-completions API. Keep `LLM_API_KEY` private; it is never included in frontend code or API responses. The checked-in example keeps the LLM values blank, so chat returns a clear configuration error until a provider is set. The backend loads `backend/.env` by file path, regardless of the directory from which Uvicorn is started. `.env` files are excluded by the repository's `.gitignore`.

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Register the first user (OAuth2 form encoding):

```powershell
Invoke-RestMethod http://localhost:8000/api/auth/register -Method Post -ContentType 'application/x-www-form-urlencoded' -Body @{username='you@example.com';password='choose-a-long-password'}
```

Sign in from the UI. API docs are at http://localhost:8000/docs. Set `JWT_SECRET` to a long random value before using beyond local development. To manually verify a live provider call after configuring `backend/.env`, create a conversation and send a chat request with a bearer token:

```powershell
$token = (Invoke-RestMethod http://localhost:8000/api/auth/login -Method Post -ContentType 'application/x-www-form-urlencoded' -Body @{username='you@example.com';password='your-password'}).access_token
$conversation = Invoke-RestMethod http://localhost:8000/api/conversations -Method Post -Headers @{Authorization="Bearer $token"}
Invoke-RestMethod http://localhost:8000/api/chat -Method Post -Headers @{Authorization="Bearer $token"} -ContentType 'application/json' -Body (@{conversation_id=$conversation.id;message='Reply with a short greeting.'} | ConvertTo-Json)
```

This live request incurs whatever usage charges your provider applies; the automated tests use a mocked provider and do not make paid calls.

## MCP tools

Install backend requirements before using MCP endpoints. The server is launched as a local child process with stdio. Try:

```powershell
Invoke-RestMethod http://localhost:8000/api/mcp/tools
```

For execution, provide a bearer token and JSON body such as `{"name":"calculate","arguments":{"operation":"add","a":25,"b":35}}` to `POST /api/mcp/execute`; the result is returned by an actual stdio MCP tool call. The backend only permits the two bundled tool names and reports invalid tool arguments as a client error. Do not expose the MCP endpoint to untrusted networks without adding stronger per-role policy, rate limits, and audit records. Arbitrary MCP server registration is deliberately not implemented; accepting user-controlled commands or URLs would be unsafe.

## Documents and persistence

Upload `file` as multipart form data to `POST /api/documents/upload` with a bearer token. Files are limited to 8 MiB and only supported extensions are accepted; parsed text is stored in the database under the uploading user's ID. Search with `POST /api/documents/{id}/search?q=term`. SQLite database defaults to `backend/assistant.db` when started from the repository root. This starter creates development tables on startup; production deployments should add Alembic migrations, PostgreSQL, backups, and operational monitoring.

## Docker

Create `backend/.env` from the example, then run `docker compose up --build`. The sample compose setup is for local development and mounts source directories. Set production secrets through the hosting platform, use managed PostgreSQL, terminate TLS at a trusted proxy, and configure `CORS_ORIGINS` and the frontend API URL for the deployment domains.

## API summary

- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `POST /api/conversations`, `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`
- `POST /api/chat`
- `POST /api/documents/upload`, `GET /api/documents`, `POST /api/documents/{id}/search`, `DELETE /api/documents/{id}`
- `GET /api/mcp/tools`, `POST /api/mcp/execute`
- `GET /api/health`

## Security and limitations

Passwords are hashed, tokens are signed, and resource ownership is checked. CORS origins are configurable; upload type/size and tool names are restricted. This is a functional development baseline, not a production security certification. Before deployment add rate limiting, CSRF/session strategy appropriate to deployment, Alembic migrations, comprehensive audit events, database-level read-only credentials for any SQL tools, outbound destination allowlists/SSRF defenses for network integrations, streaming, retry controls, stronger LLM tool-call validation, and thorough tests. Do not configure arbitrary MCP server commands from user input.

## Tests

From the repository root, run the backend tests:

```powershell
python -m pytest backend/tests -q
```

The chat tests mock the external provider and cover missing configuration, successful responses, persisted conversation history, provider errors, and network failures. MCP tests start the bundled server through the official SDK stdio client, discover its tools, verify `25 + 35 = 60`, and check invalid arguments. No test requires live LLM credentials. The frontend can be production-build checked with `cd frontend; npm run build`.
