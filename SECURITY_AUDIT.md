# Security Audit — Workout Tracker

**Date:** 2026-10-31
**Scope:** FastAPI backend (`backend/app`), SvelteKit frontend (`frontend/src`), container and deployment configuration (`Dockerfile`, `docker-compose.yml`, `scripts/`).
**Method:** Manual review of application design and code, with proof-of-concept requests against the running ASGI app. Each fix has a regression test in `backend/tests/test_security.py`.

## Summary

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| C1 | Critical | Arbitrary file read through the SPA static-file fallback | Fixed |
| C2 | Critical | Publicly known default JWT secret lets anyone forge sessions | Fixed |
| H1 | High | Google sign-in accepts ID tokens issued to other apps (account takeover) | Fixed |
| H2 | High | Any user can read any private challenge by ID (IDOR) | Fixed |
| H3 | High | Shared demo login enabled by default in production deploys | Fixed (off by default in prod) |
| M1 | Medium | OAuth redirect flow has no `state` (login CSRF) | Fixed |
| M2 | Medium | No rate limiting on login/registration or invite-code guessing | Fixed (per-instance) |
| M3 | Medium | Regex injection / ReDoS in exercise-name lookups | Fixed |
| M4 | Medium | Sessions can't be revoked; token stored in `localStorage` | Fixed |
| M5 | Medium | Cookie sessions lack CSRF defence-in-depth; `Secure` never set | Fixed |
| M6 | Medium | Unbounded, unvalidated input (leaderboard cheating, storage abuse) | Fixed |
| L1 | Low | MongoDB credentials written to logs | Fixed |
| L2 | Low | Login response/timing reveals which emails are registered | Fixed |
| L3 | Low | Weak password policy and PBKDF2 work factor | Fixed |
| L4 | Low | Missing security headers, API docs and DB name exposed, permissive CORS | Fixed |
| L5 | Low | Container runs as root; unauthenticated MongoDB bound to all interfaces | Fixed |
| L6 | Low | Race condition can add duplicate challenge participants | Fixed |
| L7 | Info | Secrets passed to Cloud Run as plain env vars | Recommendation |
| L8 | Info | Backdated workouts count toward challenges | Recommendation |

---

## Critical

### C1. Arbitrary file read via SPA fallback — `backend/app/main.py`

`serve_spa` built the path as `STATIC_DIR / full_path` and served it if it was a file. Starlette decodes `%2F`, and `pathlib` discards the base when the right-hand side is absolute, so:

```
GET /%2Fetc%2Fpasswd     -> /etc/passwd
GET /..%2Fconfig.py      -> backend/app/config.py
GET /%2Fproc%2Fself%2Fenviron -> process environment (JWT_SECRET, MONGODB_URI, GOOGLE_CLIENT_SECRET)
```

Both requests were confirmed during the audit. Reading `/proc/self/environ` exposes the JWT secret, which lets an attacker forge a session for any user and take over the database. No authentication is needed.

**Fix:** `_safe_static_file()` resolves the path and refuses anything that isn't inside `STATIC_DIR`. Requests that try to escape now fall through to `index.html`.

### C2. Hard-coded JWT secret — `config.py`, `.env.example`, `docker-compose.yml`, `scripts/deploy-gcp.sh`

The code and every deployment path fell back to a secret committed to the repo (`super-secret-workout-tracker-token-key-…`). If a deployment never overrode it, anyone could mint a valid token for any user ID with `jwt.encode({"sub": "<id>"}, "<public secret>")`.

**Fix:**
- New `ENVIRONMENT` setting. With `ENVIRONMENT=production` the app **won't start** unless `JWT_SECRET` is at least 32 characters and isn't a known published value.
- In development, a missing secret becomes a random ephemeral one. `scripts/dev.sh` generates a stable one for each dev session.
- `deploy-gcp.sh` refuses to deploy with a missing or default secret and sets `ENVIRONMENT=production`.
- **Action required:** if a production deployment ever ran on the default secret, rotate `JWT_SECRET` now. That invalidates every token that could have been forged.

## High

### H1. Google ID-token audience not enforced — `services/auth_service.py`

`verify_google_credential` called `id_token.verify_oauth2_token(..., GOOGLE_CLIENT_ID)`. When that check failed, including the `ValueError` for a **wrong audience**, it fell back to Google's `tokeninfo` endpoint and accepted whatever came back without checking `aud`. With `GOOGLE_CLIENT_ID` unset, every token went straight to the fallback. As a result, an ID token that a victim gave to *any* Google-integrated site could be replayed to `/api/auth/google/verify` to sign in as the victim. `email_verified` was never checked either.

**Fix:**
- Library validation failures (`ValueError`) are final.
- The fallback runs only when the library itself can't run (for example, a certificate fetch fails), and it checks `aud == GOOGLE_CLIENT_ID` and `iss`.
- Google sign-in is rejected when no client ID is configured.
- `email_verified` must be true on both the ID-token and OAuth-code paths.
- An email already linked to a different `google_id` is rejected instead of being silently merged.

### H2. Challenge IDOR — `routers/challenges.py`

`GET /api/challenges/{id}` returned any challenge to any authenticated user: invite code, participant names and avatars, activity timestamps. Private challenges are meant to be reachable only through the invite code, and ObjectIds are partly predictable (they start with a timestamp).

**Fix:** only the creator and participants can view a challenge. Everyone else gets `404`, so IDs can't be probed.

### H3. Shared demo account in production — `config.py`, `deploy-gcp.sh`, `docker-compose.yml`

`ALLOW_DEV_LOGIN` defaulted to `true` everywhere, including the Cloud Run deploy. Every visitor shares one account, so anyone can read, change or delete its data, join challenges as it, and see what other visitors logged.

**Fix:** it now defaults to off when `ENVIRONMENT=production` (and in `deploy-gcp.sh`), with a warning if it's explicitly turned on. The shared demo account can't be deleted, and logging out of it doesn't revoke everyone else's demo session.
**Note:** if the public demo on your live site is intentional, set `ALLOW_DEV_LOGIN=true` explicitly.

## Medium

### M1. OAuth login CSRF — `routers/auth.py`
The authorization-code flow sent no `state`. An attacker could make a victim's browser finish the flow with the attacker's code, signing the victim into the attacker's account (where anything they log becomes visible to the attacker). **Fix:** a random `state` is stored in a short-lived HttpOnly cookie scoped to `/api/auth/google` and checked with `compare_digest` on the callback. The unneeded `access_type=offline` scope was also removed.

### M2. No rate limiting — new `utils/security.py`
Unlimited attempts against `/login` made password guessing practical. The invite code (6 characters, about 10⁹ combinations) is the only protection on a private challenge. **Fix:** a sliding-window limiter (10 requests/min by default) on login (per IP *and* per email), register, Google verify, demo login and challenge join (per user and per IP). `TRUST_PROXY_HEADERS=true` (set by the deploy script) takes the client IP from the right-most `X-Forwarded-For` entry.
*Limitation:* the limiter's state is per process. For strict limits across Cloud Run instances, move it to Redis or Memorystore.

### M3. Regex injection — `routers/exercises.py`, `routers/challenges.py`
User-supplied exercise names were inserted into `$regex` without escaping. `.*` matched every exercise, an invalid pattern such as `(` caused a 500, and crafted patterns could burn database CPU (ReDoS). **Fix:** `exact_name_regex()` applies `re.escape`.

### M4. Session lifecycle — `auth_service.py`, `auth_dep.py`, `frontend/src/lib/api.ts`
- Logout only cleared the cookie, so a stolen token stayed valid for 14 days. **Fix:** tokens carry a `ver` claim matched against `users.token_version`. Logout increments it, which revokes all of that user's sessions. The default lifetime is now 7 days, and `exp`/`sub` are required.
- The frontend kept the JWT in `localStorage`, where any XSS could read it. **Fix:** the SPA relies on the existing HttpOnly cookie, and old stored tokens are removed. `access_token` is still returned in API responses for non-browser clients.

### M5. CSRF and cookie flags — `auth_dep.py`, `utils/security.py`
Cookies were always `Secure=False`, and cookie-authenticated writes relied only on `SameSite=Lax`. **Fix:**
- Cookie-authenticated `POST/PUT/DELETE` requests must send `X-Requested-With`. Cross-site forms can't set that header, and cross-origin `fetch` needs a CORS preflight that only allowed origins pass.
- `Secure` is set automatically when `FRONTEND_URL` is `https://`.
- Bearer-token clients are unaffected.

### M6. Input validation — `models/*.py`, `routers/auth.py`
There were no bounds anywhere. Negative or enormous reps let anyone top a challenge leaderboard or skew stats. Unbounded lists and strings let one request store megabytes. `theme`, `weight_unit`, `period`, `unit` and `type` took any string. **Fix:**
- Reps, weight, duration and targets have `ge`/`le` bounds.
- Strings and lists have `max_length`.
- Enumerated fields use `Literal` types.
- Challenges are capped at 366 days.

## Low

- **L1 – Credentials in logs** (`database.py`): the full `MONGODB_URI`, including the Atlas password, was logged at startup. It's now redacted.
- **L2 – User enumeration** (`auth_service.py`): login said "created with Google Sign-In" for Google accounts and returned faster for unknown emails. There's now one generic message, and a dummy hash equalises timing. (Registration still says "already exists"; removing that needs email verification, see below.)
- **L3 – Password storage**: the minimum length is now 8 (was 6). PBKDF2 iterations go from 100k to 600k (OWASP 2023), in a versioned hash format. Legacy hashes still verify and are upgraded on next login. Hashing runs in a worker thread so it doesn't block the event loop.
- **L4 – Hardening** (`main.py`):
  - Added `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `COOP`, HSTS (on HTTPS) and `Cache-Control: no-store` on `/api/*`.
  - `/docs` and `/openapi.json` are off in production.
  - `/api/health` no longer reveals the database name.
  - CORS uses explicit methods and headers, and localhost origins are dropped in production.
- **L5 – Containers**: the image runs as an unprivileged `appuser`. In `docker-compose.yml`, MongoDB (which has no auth) is published only on `127.0.0.1`.
- **L6 – Join race**: the participant `$push` is now conditional on the user not already being a member.

## Recommendations (not yet implemented)

### Security
1. **Secret Manager (L7).** `deploy-gcp.sh` passes `JWT_SECRET`, `MONGODB_URI` and `GOOGLE_CLIENT_SECRET` as plain env vars, which anyone with Viewer access to the Cloud Run service can read. Use `gcloud secrets create` and `--set-secrets`.
2. **Challenge integrity (L8).** Workouts can be logged with any past date (`quick-log`'s `date`, `POST /workouts`'s `date`) and still count toward a challenge. Count only workouts *created* after the participant joined (`created_at >= joined_at`), or limit how far back entries can be dated.
3. **Content-Security-Policy.** Turn on SvelteKit's `kit.csp` (hash/nonce mode) and allow `accounts.google.com`, the avatar hosts and `'self'`. This needs the inline theme script in `app.html` to be hashed.
4. **Email verification and password reset** for email/password accounts. This also lets the "already exists" enumeration be removed.
5. **Shared rate-limit store** (Redis) and alerting on repeated `401`/`429`.
6. **Stop storing participant emails** in `challenges.participants`. They're never shown and duplicate PII.
7. **Per-visitor demo sandboxes** (a throwaway account per demo login, cleaned up by a TTL index) instead of one shared demo account, if you want a public demo.
8. **Dependency hygiene.** `python-jose` sees little maintenance and pulls in `ecdsa`, which has an unfixed side-channel issue (harmless for HS256, but avoidable). Consider moving to `PyJWT`. Add `pip-audit` and `npm audit` to CI, and enable Dependabot.
9. **Audit logging** of sign-ins, logouts, account deletion and challenge deletion.

### Features
1. **Account management UI.** The backend now has `GET /api/auth/me/export` (full data export) and `DELETE /api/auth/me` (account and data deletion, GDPR-style), and `api.ts` has `exportMyData()` and `deleteAccount()`. A settings page needs to expose them.
2. **"Sign out everywhere"** is already the logout behaviour. Show it in the UI, and revoke sessions automatically after a password change.
3. **Time-zone-aware days.** "Today", streaks, daily goals and challenge days are all computed in UTC, so evening workouts in the Americas land on "tomorrow". Store the user's IANA time zone in preferences and compute day boundaries in it.
4. **Challenge ownership transfer.** When the creator leaves, the challenge keeps their `creator_id`, so they can still delete it for everyone. Transfer ownership to the next participant, or block leaving until it's transferred.
5. **Performance.** Challenge leaderboards and stats run one query per participant and scan every workout in Python. Use a MongoDB aggregation pipeline (`$match` → `$unwind` → `$group`) and paginate `/api/stats/prs`.
6. **Workout editing in the UI.** `PUT /api/workouts/{id}` exists but the frontend doesn't use it.
7. **Goal units.** `seconds` goals currently sum reps. Use `duration_seconds` for duration goals, the same way challenges do.

## Testing

```bash
cd backend && uv run pytest
```

`tests/test_security.py` covers path traversal, the CSRF header, token revocation, rejection of forged tokens, the production config guard, generic login errors, rate limiting, legacy password hashes, Google audience and `email_verified` checks, OAuth `state`, challenge access control, regex escaping, input bounds, export/delete and security headers. `tests/conftest.py` resets the rate limiters between tests.
