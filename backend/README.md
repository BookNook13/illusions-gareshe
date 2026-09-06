# ILUSIEBIS GAReshe — Backend

"Stories that reveal the reader." Django + DRF backend for a
multi-story, replay-capable interactive literature platform with a
transparent, evidence-linked psychological interpretation layer.

## Setup

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit DJANGO_SECRET_KEY and DATABASE_URL
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Auth

JWT via `rest_framework_simplejwt`.

- `POST /api/auth/token/` — body `{"username": "...", "password": "..."}` → `{access, refresh}`
- `POST /api/auth/token/refresh/` — body `{"refresh": "..."}` → `{access}`

Send `Authorization: Bearer <access>` on all `/api/story/` requests.

## Story API

All endpoints operate on a `Story`'s currently *published* `StoryVersion`
— publishing a new version supersedes the old one for new sessions while
existing `ReadingSession`s keep their original version untouched.

- `GET  /api/stories/` — library / discovery (published stories only)
- `GET  /api/stories/<story_id>/session/` — current node of the reader's
  latest run (creates run #1 at the version's `root_node` on first call)
- `POST /api/stories/<story_id>/session/choice/` — body
  `{"choice_id": "<uuid>"}`; advances the run and returns the new node +
  updated psychological profile
- `GET  /api/stories/<story_id>/session/profile/` — the latest run's
  accumulated tag scores + flags
- `GET  /api/stories/<story_id>/session/reflection/` — end-of-story
  reflection for the latest completed run (generated + cached on first
  request; errors if the run hasn't reached an ending)
- `POST /api/stories/<story_id>/replay/` — starts a new run
  (`run_number` + 1) of the same published version
- `GET  /api/stories/<story_id>/compare/?a=1&b=2` — diffs two runs:
  divergent choices + side-by-side psychological profiles

Every psychological claim is backed by an `Interpretation` row linking
back to the exact `ReaderChoice` that produced it — there is no
unexplained scoring.

## Testing

python manage.py test story -v 2

20 tests cover: story-graph validation (unreachable nodes, unintended
dead ends), choice integrity (no self-loops, no cross-version edges),
the full reading loop (session creation, choice submission, flag
gating, completion), reflection generation, replay + run comparison,
authentication enforcement, and the consistent error-response shape.

CI (`.github/workflows/ci.yml`) runs this same suite against a real
Postgres service container on every push, checks for missing
migrations, and runs `manage.py check --deploy`.

## Running with Docker

docker compose up --build

This runs Postgres + the Django app (via gunicorn) together, applying
migrations on container start. Requires a `.env` file in this directory
first (see `.env.example`).

## Production hardening

`config/settings.py` gates a set of security settings on `DEBUG=False`:
HSTS, secure cookies, `X-Content-Type-Options`, referrer policy, and
(opt-in via `DJANGO_SECURE_SSL_REDIRECT`) HTTPS redirection. Verify any
production environment with:

python manage.py check --deploy

Other production pieces included:
- **Structured JSON logging** (`LOGGING` in settings.py) — human-readable
  in dev, JSON lines in production for easy log aggregation.
- **Consistent error responses** — every API error returns
  `{"error": {"code": ..., "message": ..., "detail": ...}}`; unhandled
  5xxs are logged server-side with a correlation `incident_id` and never
  leak internals to the client (`config/exception_handler.py`).
- **`/healthz/`** — dependency-free liveness/readiness check that
  verifies actual DB connectivity, for load balancers and orchestrators.
- **Sentry hook** — inert unless `SENTRY_DSN` is set; enabling real error
  monitoring later is a config change, not a code change.
- **WhiteNoise** — serves compressed, cache-busted static files directly
  from the Django process, no separate static file server needed yet.

Not yet built (deliberately deferred until there's an actual async
workload to justify them, per the product spec's own
"avoid premature abstraction" guidance): Celery, Redis, S3 storage,
the AI analysis layer beyond the deterministic reflection summarizer,
and the Next.js authoring dashboard.

## Authoring

Content is authored via `/admin/` for now (a dedicated Next.js dashboard
is a later phase). Workflow:

1. Create a `Story` (draft status).
2. Create a `StoryVersion` under it, author `StoryNode`s and `Choice`s.
3. Set the version's `root_node`.
4. Run "Validate story graph" (admin action on `StoryVersion`) to catch
   unreachable nodes or unintended dead ends before publishing.
5. Run "Publish selected versions" (admin action) — this is irreversible
   for that version; fix content by creating a new version instead.
6. Set the `Story.status` to `published` once you're ready for readers.
