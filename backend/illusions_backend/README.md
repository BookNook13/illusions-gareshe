# ილუზიების გარეშე — Backend (Phase 0 & 1)

Django + DRF backend for the interactive storytelling / psychological
tracking engine.

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

- `GET  /api/story/current/` — current node + available choices (creates
  a `ReaderProgress` at the `StoryNode` with `is_start=True` on first call)
- `POST /api/story/choice/` — body `{"choice_id": "<uuid>"}`, advances the
  reader and returns the new node + updated psychological profile
- `GET  /api/story/profile/` — the reader's accumulated profile + flags

## Authoring

Content is authored via `/admin/` for now (Phase 2 replaces this with the
Next.js dashboard). Exactly one `StoryNode` must have `is_start=True` —
enforced by a DB constraint.
