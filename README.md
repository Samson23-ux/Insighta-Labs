# Insighta Labs+ — Backend

Central API server for the Insighta Labs+ Profile Intelligence System. Serves as the single source of truth for authentication, user management, profile data, and access control across all interfaces.

**Live API:** [https://perpetual-illumination-production-af59.up.railway.app](https://perpetual-illumination-production-af59.up.railway.app)

**Related repositories:**
- CLI: [https://github.com/Samson23-ux/Insighta-Labs-Cli](https://github.com/Samson23-ux/Insighta-Labs-Cli) — terminal interface with GitHub OAuth + PKCE
- Web Portal: _[link to be added]_ — browser-based interface for non-technical users

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT INTERFACES                       │
│                                                              │
│   ┌─────────────────┐          ┌───────────────────────┐    │
│   │   Insighta CLI  │          │  Insighta Web Portal  │    │
│   │  (OAuth + PKCE) │          │   (Browser OAuth +    │    │
│   │  Local tokens   │          │    HTTP-only cookies)  │    │
│   └────────┬────────┘          └──────────┬────────────┘    │
└────────────┼──────────────────────────────┼─────────────────┘
             │                              │
             │   HTTPS + Bearer token       │   HTTPS + Cookies
             │                              │
             ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (this repo)                      │
│                                                              │
│   ┌──────────────┐   ┌──────────────┐   ┌───────────────┐   │
│   │  Auth Layer  │   │ Profile APIs │   │  Rate Limiter │   │
│   │  /auth/*     │   │  /api/*      │   │  + Logger     │   │
│   └──────┬───────┘   └──────┬───────┘   └───────────────┘   │
│          │                  │                                 │
│   ┌──────▼──────────────────▼──────────────────────────┐    │
│   │                    Database (PostgreSQL)             │    │
│   │          users table · profiles table               │    │
│   └─────────────────────────────────────────────────────┘    │
│                                                              │
│   ┌──────────────────────────────────────────────────────┐   │
│   │               External APIs (Stage 1)                │   │
│   │   Genderize.io · Agify.io · Nationalize.io           │   │
│   └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
     ┌───────────────┐
     │  GitHub OAuth │
     │  (token       │
     │   exchange)   │
     └───────────────┘
```

**Design principles:**
- The backend is the single source of truth — no interface contains business logic
- All authentication, authorization, and data access go through this API
- CLI and Web Portal differ only in how they carry auth (Bearer token vs. HTTP-only cookies)

---

## Authentication Flow

### CLI Flow (PKCE)

The CLI cannot safely store a client secret, so it uses **PKCE** (Proof Key for Code Exchange). The backend participates in the exchange without ever trusting a pre-shared secret.

```
1. CLI generates locally:
   state         = cryptographically random nonce
   code_verifier = cryptographically random string (never sent to GitHub)
   code_challenge = base64url(SHA-256(code_verifier))

2. CLI opens browser to GitHub OAuth:
   https://github.com/login/oauth/authorize
     ?client_id=<CLIENT_ID>
     &redirect_uri=http://localhost:<port>/callback
     &scope=read:user,user:email
     &state=<state>
     &code_challenge=<code_challenge>
     &code_challenge_method=S256

3. User authenticates. GitHub redirects to:
   http://localhost:<port>/callback?code=<code>&state=<state>

4. CLI validates state, then calls backend:
   POST /auth/github/callback
   { code, code_verifier }

5. Backend:
   a. Sends { client_id, code, code_verifier, redirect_uri } to GitHub's token endpoint
   b. GitHub verifies: SHA-256(code_verifier) == code_challenge stored at auth time
   c. GitHub issues access token
   d. Backend fetches user info from GitHub API
   e. Upserts user in database
   f. Issues: access_token (JWT, 3 min) + refresh_token (JWT, 5 min)
   g. Returns tokens in response body

6. CLI stores tokens at ~/.insighta/credentials.json
   Subsequent requests: Authorization: Bearer <access_token>
```

**Why PKCE is secure:** Even if the authorization code is intercepted, an attacker cannot exchange it without the `code_verifier`, which only the legitimate CLI instance ever possessed.

---

### Web Flow (Browser)

The browser flow does not use PKCE. The backend acts as a confidential OAuth client using the `client_secret`.

```
1. User clicks "Continue with GitHub"
   Browser navigates to: GET /auth/github
   Backend generates state, stores in server-side session, redirects to GitHub

2. User authenticates. GitHub redirects to:
   GET /auth/github/callback?code=<code>&state=<state>

3. Backend:
   a. Validates state against session
   b. Exchanges code + client_secret with GitHub
   c. Fetches user info, upserts user in database
   d. Issues access_token + refresh_token
   e. Sets as HTTP-only cookies:
      Set-Cookie: access_token=<jwt>; HttpOnly; Secure(for prod); SameSite=Strict
      Set-Cookie: refresh_token=<token>; HttpOnly; Secure(for prod); SameSite=Strict
   f. Redirects to web portal /dashboard

4. All subsequent browser requests carry cookies automatically
   Tokens are never accessible from JavaScript
```

---

## Token Handling

### Issuance

| Token | Format | Expiry | Storage |
|---|---|---|---|
| Access token | JWT (signed HS256) | 3 minutes | CLI: credentials file · Web: HTTP-only cookie |
| Refresh token | JWT, hashed in DB | 5 minutes | CLI: credentials file · Web: HTTP-only cookie |

### Rotation

Every call to `POST /auth/refresh` invalidates the submitted refresh token immediately and issues a new token pair. A token can only be used once.

```
POST /auth/refresh
  → validate refresh token against hashed value in DB
  → if valid:
      mark old refresh token as used
      issue new access_token + refresh_token
      return { access_token, refresh_token }
  → if invalid or expired:
      return 401 Unauthorized
```

### FastAPI Dependency Behaviour

Every protected endpoint passes through a dependency that:

1. Extracts the token (from `Authorization: Bearer` header or cookie, depending on client)
2. Verifies the JWT signature and expiry
3. If expired: attempts to find a valid refresh token (web portal only — transparent refresh)
4. Attaches the decoded user to the request context
5. Proceeds or returns `401`

---

## Role Enforcement

Roles are enforced via a dependency applied to all `/api/*` routes.

### Role Definitions

| Role | Permissions |
|---|---|
| `admin` | Full access: create profiles, delete profiles, read, search, export |
| `analyst` | Read-only: list, get, search, export |

Default role on registration: `analyst`

### `is_active` Check

If a user's `is_active` field is `false`, the auth dependency returns `403 Forbidden` on all `/api/*` requests regardless of role. This is checked immediately after token validation, before any role check.

### Route Permission Map

| Method | Endpoint | Min Role |
|---|---|---|
| GET | `/api/profiles` | analyst |
| GET | `/api/profiles/:id` | analyst |
| GET | `/api/profiles/search` | analyst |
| GET | `/api/profiles/export` | analyst |
| POST | `/api/profiles` | admin |
| DELETE | `/api/profiles/:id` | admin |

---

## Natural Language Parsing

Natural languages are parsed and converted to their underlying filter which are used to query the database for specific profiles.

### Processing Steps

- The received query words are normalized to remove `s` suffix from words and also exclude unsupported keywords
- Each normalized keyword is mapped against its filter, identified by the keyword's class (gender, age_group, etc.)
- The mapped keywords are then used to filter the profiles in the database to return only profiles that meet the requirements
- A QueryError exception is raised when invalid keywords are detected or when the keywords are arranged in a way that go against the rules

### Supported Keywords and Their Mapped Filters

#### Gender

- **Keywords**: `male`, `female`
- **Example**: gender=male

#### Age Groups

- **Keywords**: `child`, `teenager`, `adult`, `senior`, `young`
- **Example**: age_group=adult
- **Note**: The keyword `young` maps to ages 16-24 (e.g., age >= 16 and age <= 24)

#### Range Operators

- **Keywords**: `above`, `below`, `equal`, `minimum`, `maximum`, `between`
- **Operator Mappings**:
  - `above`: >
  - `below`: <
  - `equal`: =
  - `minimum`: >=
  - `maximum`: <=
  - `between`: >= and <=

#### Logical Operators

- **Keywords**: `or`, `and`

#### Country Names

- Full country names (e.g., "United States", "Nigeria")

### Example Queries

- `"young male"` → Males aged 16-24
- `"female above 30"` → Females 30 and above
- `"adults or senior"` → Adults or seniors
- `"males between 25 and 60"` → Males aged 25-60
- `"females from United States"` → Females from the US

### Rules

- ISO country codes (alpha_2 and alpha_3) are not supported
- Age values should be passed as positive integers. Floating point numbers and words are not supported
- When different values are passed for the same field (gender, age_group, etc.), the second value takes precedence over the first. An exception to this is when the two values are passed as operands to the `or` logical operator
- When range keywords are used, they should come before the age value (e.g., "male above 20" and not "male 20 and above")

### Limitations

- No support for name queries
- Only support for English words
- No support for country ISO code
- No normalization for words with `es` suffix
- No identification of age values when written as words
- No filter mapping for probability fields (min_gender_probability, min_country_probability) and support for float

---

## API Reference

### API Versioning

All `/api/*` endpoints require the header:

```
X-API-Version: 1
```

Requests missing this header receive:

```json
{
  "status": "error",
  "message": "API version header required"
}
```
**Status:** `400 Bad Request`

---

## Environment Variables

Create a `.env` file and copy the environment template fixing replacing the values with your database URLs ([link to file](./.env.example))

## Running Locally

## Prerequisites

- Python 3.10+
- PostgreSQL 12+
- pip (Python package manager)

```bash
git clone https://github.com/Samson23-ux/Insighta-Labs.git
cd Insighta-Labs

# Create virtual environment

# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Run migrations
alembic upgrade head

# Run seed scripts
python -m app.scripts.seed_db
python -m app.scripts.create_admin

# Start the server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

Interactive docs: `http://localhost:8000/docs`

---

## Testing

```bash
# Run all tests
pytest

# Run a specific file
pytest tests/test_auth.py
```

### CI/CD

GitHub Actions runs on every PR to `main`:
- Linting (`ruff` or `flake8`)
- Runs tests (`pytest`)

---

## Troubleshooting 🔧

### Database Connection Issues

**Problem**: `could not connect to server`

**Solution**:
- Verify PostgreSQL is running: `pg_isready`
- Check database URL in `.env`
- Ensure database and user exist: `psql -l -U postgres`

### Migration Issues

**Problem**: Migration fails to apply

**Solution**:
```bash
# Check alembic version
alembic current

# Downgrade to previous version
alembic downgrade -1

# Review migration files in alembic/versions/
```

### Virtual Environment Issues

**Problem**: `ModuleNotFoundError` after installing dependencies

**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
