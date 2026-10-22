# Operations: monitoring, alerting, CI and backups

How to tell when something is broken, how to get told automatically, and what to do when CI fails.
For the system itself, see the [README](README.md).

## 1. How do I know something is broken?

Three layers, meant to be used together:

| Layer | What it tells you | Where |
|---|---|---|
| **Docker healthchecks** | which container is not answering (`web`, `api`, `db`) | `docker ps`: the STATUS column should say `healthy` |
| **The admin dashboard** | database or storage down, **the answer model failing**, a stale search index | admin → Overview ("Things to look after" and "System status") |
| **Uptime Kuma** (optional) | the site is down, **and sends you a message** (Discord, Telegram, email) | `docker compose --profile monitor up -d` |

The first two need someone to look. If you want the system to message *you*, set up the third layer.

## 2. When the answer model breaks

Visitors never see an error. They get a "I could not write a summary, here are the matching parts of the site" reply
instead (mode `fallback`). You find out from:

- **The dashboard**: a red badge **"Answer model failing N times"** and a to-do item "The answer model failed N time(s) in
  the last 24 hours". It counts questions that matched the site well but could not be answered by the model, and only when
  `GEMINI_API_KEY` is set (without a key the fallback is the intended behaviour, not a failure).
- **The log**: `docker logs portfolio-api 2>&1 | grep portfolio.llm`, which gives lines such as
  `gemini model gemini-2.5-flash-lite returned 404: This model ... is no longer available to new users`.

Common causes:

| Log says | Cause | Fix |
|---|---|---|
| `returned 404 ... no longer available` | Google retired that model | set `GEMINI_MODEL_CHEAP` / `GEMINI_MODEL_SMART` in `.env` to a model that works, then `docker compose up -d api` |
| `returned 429` | quota used up | wait, or raise the quota in Google AI Studio |
| `returned 400` / `403` | wrong or revoked key | create a new key and set `GEMINI_API_KEY` |
| `returned 5xx`, or a timeout | Google is having problems | wait; the site keeps working in fallback mode |

To list the models your key can call (the key is not printed):

```bash
docker exec portfolio-api python -c "import httpx; from app.config import get_settings as g; s=g(); r=httpx.get('https://generativelanguage.googleapis.com/v1beta/models?pageSize=200', headers={'x-goog-api-key': s.gemini_api_key}); print([m['name'].split('/')[1] for m in r.json().get('models',[]) if 'generateContent' in m.get('supportedGenerationMethods',[]) and 'flash' in m['name']])"
```

## 3. Alerts when the site goes down (Uptime Kuma)

```bash
docker compose --profile monitor up -d
```

Open http://localhost:3001 (change the port with `MONITOR_PORT` in `.env`), create the admin account on first visit, then
add HTTP monitors:

| Name | URL | Passes when | What it tells you |
|---|---|---|---|
| Website | `https://<SITE_DOMAIN>/robots.txt` | 200 | the web server (Next.js) is alive |
| API | `https://<SITE_DOMAIN>/api/health/live` | 200 | the API process is alive |
| Database and files | `https://<SITE_DOMAIN>/api/health` | 200 (a failure returns 503) | PostgreSQL and object storage answer |
| Back office | `https://<ADMIN_DOMAIN>/login` | 200 | the admin pages open |

To check from inside the Docker network instead, use `http://web:3000/robots.txt` and `http://api:8000/api/health`.

Add a notification channel under Settings → Notifications:

- **Discord**: create a webhook in the channel (channel settings → Integrations → Webhooks) and paste its URL.
- **Telegram**: create a bot with @BotFather to get a token, then enter the chat ID.
- **Email (SMTP)**: enter the host, user and password of your mail provider.

Turn on "Default enabled" so every monitor uses it, and press **Test** to make sure the message arrives.

**Limitations to know about**

- Uptime Kuma runs on the same machine as the site. If the whole machine goes down, nobody sends the alert. Add one
  **external** monitor as well (for example UptimeRobot or Better Stack on a free plan) pointed at
  `https://<SITE_DOMAIN>/api/health`.
- It is published on `127.0.0.1` only. Before exposing it through a domain, put it behind the proxy with its own password.

## 4. CI (GitHub Actions)

File: `.github/workflows/ci.yml`. It runs on every push to `main` and on every pull request:

| Job | Checks |
|---|---|
| **api** | the whole `pytest` suite (against a throwaway PostgreSQL with pgvector), and that the committed admin stylesheet matches the templates |
| **web** | `api-types.ts` matches `openapi.json`, `tsc`, `next build`, and `npm audit` (high severity and above) |
| **images** | the `api` and `web` Docker images build |

When CI fails:

- **"The committed admin stylesheet matches the templates"**: a class was added or changed in a template (or in
  `api/css/input.css`) without rebuilding the CSS. Run `api/scripts/build_css.sh` (Git Bash / Linux / macOS) or
  `api\scripts\build_css.ps1` (PowerShell) and commit `api/app/static/admin.css`.
- **"api-types.ts matches openapi.json"**: an API schema changed. Run `python -m scripts.export_openapi` in `api/`, then
  `npm run api:types` in `web/`, and commit both generated files.
- **npm audit**: a high-severity vulnerability in a package that runs in production. Upgrade that package.

To require a green CI before merging, enable branch protection once under GitHub → Settings → Branches.

---

## 5. Backups and deployment

Backups, restore and the server procedure are in [DEPLOY.md](DEPLOY.md). In short: `sh ops/backup.sh` every night from
cron, `sh ops/verify-backup.sh` after setting it up and now and then (it restores into a throw-away database and
compares row counts), and `sh ops/restore.sh <backup>` to recover. Keep a copy of the backups on another machine.
