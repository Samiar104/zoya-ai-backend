# ZOYA AI Backend — Phase 1 (AI Brain)

The complete FastAPI backend for **ZOYA AI**, an Android personal assistant.
Phase 1 only: the backend. The website (Phase 3) and the Android app
(Phase 5) connect to this API in later phases.

- **Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite (default) / PostgreSQL
- **Auth:** JWT (never expires) + static API key (never expires)
- **Realtime:** WebSockets for devices and chat
- **Brain:** intent understanding, user memory, emotion detection, two
  modes (`assistant` / `companion`), character profile
- **Voice:** pluggable STT/TTS — Phase 1 ships an honest stub
- **Ops:** health checks, logging, rate limiting, backups, Docker, systemd

> **Honest note on 24/7 hosting:** this code is ready to deploy (systemd
> auto-restart, Docker `restart: unless-stopped`, health checks, log
> rotation). But 24/7 uptime needs a real server/VPS — this VM is for
> development and testing. Deploy with the instructions below.

## Quick start

```bash
cd backend
cp .env.example .env        # edit SECRET_KEY for production
./run.sh                    # or: uvicorn app.main:app --host 0.0.0.0 --port 8000
```

First start generates the static API key and saves it to `.env`
(`ZOYA_API_KEY`). The first registered user becomes the admin.

Interactive docs: http://localhost:8000/docs — Health: http://localhost:8000/health

## Project structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, rate limit, startup
│   ├── core/
│   │   ├── config.py           # settings + character profile + API-key generation
│   │   ├── security.py         # JWT (no expiry) + API key auth
│   │   ├── database.py         # SQLAlchemy engine/session
│   │   ├── logging.py          # stdout + rotating file logs
│   │   └── ratelimit.py        # per-IP sliding-window rate limiting
│   ├── models/                 # User, Device, Command, Conversation, Feature, UserMemory
│   ├── schemas/                # Pydantic request/response models
│   ├── routers/                # auth, devices, commands, features, voice,
│   │                           # health, backup, chat (+WebSockets),
│   │                           # conversation (emotion/memory), character
│   ├── services/
│   │   ├── conversation.py     # ZOYA's brain: intent + memory + emotion + modes
│   │   ├── emotion.py          # emotion detection (8 emotions, confidence)
│   │   ├── memory.py           # long-term user memory (preferences/facts/moods)
│   │   ├── dispatcher.py       # command delivery over WebSocket
│   │   ├── plugins.py          # feature registry (built-ins seeded)
│   │   └── voice_engine.py     # STT/TTS interface + stub engine
│   └── ws/manager.py           # WebSocket connection manager
├── tests/                      # pytest suite (39 tests, all passing)
├── scripts/backup_now.sh       # cron backup helper
├── Dockerfile                  # container image
├── docker-compose.yml          # backend (+ optional PostgreSQL)
├── zoya-backend.service        # systemd unit (auto-restart)
├── nginx.conf.example          # reverse proxy + TLS + WebSocket
├── requirements.txt
├── .env.example
└── README.md
```

## API list

Base URL: `http://localhost:8000`. Auth: `Authorization: Bearer <JWT>` for
user endpoints; `X-API-Key: <static key>` for device endpoints.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| GET | `/` | — | Service info |
| GET | `/health` | — | Liveness: status, uptime, DB |
| GET | `/health/ready` | — | Readiness probe |
| POST | `/auth/register` | — | Create account (first = admin) |
| POST | `/auth/login` | — | Login → JWT (never expires) |
| GET | `/auth/me` | JWT | Current user |
| GET | `/auth/api-key-info` | JWT+admin | Show static API key |
| POST | `/auth/rotate-api-key` | JWT+admin | Rotate the static API key |
| GET | `/character` | — | ZOYA's character profile + avatar |
| POST | `/devices/register` | API key | Register/re-register a device |
| GET | `/devices` | JWT | List devices |
| GET | `/devices/{id}` | JWT | One device |
| POST | `/devices/heartbeat` | API key | Device heartbeat |
| GET | `/devices/{id}/pending-commands` | API key | Queued commands |
| DELETE | `/devices/{id}` | JWT | Remove a device |
| POST | `/commands` | JWT | Queue a command (tap/swipe/scroll/open_app/close_app/back/home/play_pause/next/previous/volume/search/call/message/camera/custom) |
| GET | `/commands` | JWT | List (filter by device/status) |
| GET | `/commands/{id}` | JWT | One command |
| POST | `/commands/{id}/result` | JWT | Report outcome |
| POST | `/commands/{id}/cancel` | JWT | Cancel a queued command |
| POST | `/chat/sessions` | JWT | New session (language, mode) |
| GET | `/chat/sessions` | JWT | List sessions |
| GET | `/chat/sessions/{id}/messages` | JWT | History |
| POST | `/chat/message` | JWT | Send message → reply (+emotion, intent) |
| POST | `/conversation/analyze-emotion` | JWT | Detect emotion from text |
| GET | `/conversation/memory` | JWT | What ZOYA remembers |
| POST | `/conversation/memory` | JWT | Teach ZOYA something |
| DELETE | `/conversation/memory/{id}` | JWT | Make ZOYA forget one item |
| GET | `/features` | JWT | List feature modules |
| POST | `/features` | JWT | Register a feature |
| GET/PATCH | `/features/{name}` | JWT | Get / update a feature |
| POST | `/features/{name}/enable` | JWT | Enable a feature |
| POST | `/features/{name}/disable` | JWT | Disable a feature |
| DELETE | `/features/{name}` | JWT | Remove a feature |
| GET | `/voice/status` | JWT | Voice engine status |
| POST | `/voice/stt` | JWT | Speech-to-text (stub: 501) |
| POST | `/voice/tts` | JWT | Text-to-speech (stub: 501) |
| POST | `/backup/create` | JWT | Create a DB backup |
| GET | `/backup/list` | JWT | List backups |
| GET | `/backup/download/{file}` | JWT | Download a backup |
| POST | `/backup/restore` | JWT | Restore (restart required) |
| WS | `/ws/chat` | — | Live chat channel |
| WS | `/ws/device/{device_id}?api_key=...` | API key | Device channel (commands in, results out) |

## ZOYA's brain (Phase 1)

The brain (`app/services/conversation.py`, `emotion.py`, `memory.py`) is a
**transparent rule-based engine** — every rule is readable in the code.
It is not a large language model, and the API never pretends otherwise.

- **Intent understanding:** greeting, help, time, open_app, play_media,
  call, message, reminder, how_are_you, ask_name, share_feeling, chat.
  Entities (app name, contact, media) are extracted from the message.
- **Memory:** preferences, facts, topics and mood history are stored per
  user (`user_memory` table) and used in replies — e.g. ZOYA remembers
  your name and your likes, and checks in if you were sad last time.
- **Emotion:** 8 emotions — happy, sad, stressed, angry, tired, lonely,
  excited, neutral — each with a confidence score, detected from text
  (Hindi/Urdu/Punjabi/English, Devanagari + Roman) and optionally from
  voice metadata (energy/pitch/rate). The reply adapts: comfort when sad,
  gentle humour when stressed, celebration when happy.
- **Modes:** `assistant` (productive, efficient) and `companion` (warm,
  caring, playful, affectionate — asks how you feel, remembers personal
  details). Switch per session; the mode is stored on the session.
- **Character:** `GET /character` returns ZOYA's profile — name, tagline,
  description, backstory, traits, voice character, `avatar_url`
  (`zoya-character.png` by default), languages and modes. Configure via
  `ZOYA_*` settings in `.env`.

**Upgrade path:** implement an LLM brain behind the same `ZoyaBrain`
interface (`understand()` + `reply()`) and set `LLM_PROVIDER` /
`LLM_API_KEY`. No router changes needed. Same for emotion (swap in a
trained classifier behind `detect_emotion()`) and voice (below).

## Voice (honest stub)

Phase 1 ships a **stub** voice engine: `/voice/stt` and `/voice/tts`
return HTTP 501 with setup instructions. No engine is installed, so the
backend does not pretend to hear audio.

To enable real voice:
- **STT:** `pip install faster-whisper`, set `VOICE_ENGINE=whisper`, and
  implement `WhisperEngine.transcribe()` in `app/services/voice_engine.py`.
- **TTS:** install Piper (`pip install piper-tts`), set
  `VOICE_ENGINE=piper`, and implement `PiperEngine.synthesize()`.

The interface is one class with two methods — routers need no changes.

## Security & key lifecycle

- **API key never expires** (project requirement). It is generated once,
  stored in `.env` (never in source code), sent as `X-API-Key`. Rotate it
  with `POST /auth/rotate-api-key` (admin) and update devices.
- **JWTs never expire** (no `exp` claim). Revocation: deactivate the user
  (`is_active=false` in the DB) or rotate `SECRET_KEY` (invalidates all
  tokens). Trade-off: a leaked token stays valid until revoked — keep
  tokens on the device only, use HTTPS in production.
- **Passwords:** bcrypt-hashed, never stored in plain text.
- **Secrets:** only via environment / `.env`. Never put keys in the APK —
  the app uses the API key at runtime from secure storage (Phase 5).
- **Sensitive actions** (e.g. sending a WhatsApp message) require user
  confirmation in the app (Phase 5/6). The backend never executes
  arbitrary code: the feature registry stores metadata only.
- **CORS** is restricted by `ALLOWED_ORIGINS`. **Rate limiting** defaults
  to 120 req/min per IP. Run behind HTTPS (nginx example included).

## Deployment (24/7)

**systemd (recommended on a VPS):**
```bash
sudo useradd -r -s /bin/false zoya
sudo mkdir -p /opt/zoya && sudo cp -r backend /opt/zoya/backend
sudo cp backend/zoya-backend.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now zoya-backend
```
Auto-restart on crash (`Restart=always`), logs via `journalctl -u zoya-backend`.

**Docker:**
```bash
docker compose up -d --build
```

**PostgreSQL:** set `DATABASE_URL=postgresql+psycopg2://...` in `.env`
and install `psycopg2-binary` (add to requirements).

**Backups:** `POST /backup/create` or cron `scripts/backup_now.sh`
(daily 03:00). Retention via `BACKUP_RETENTION_DAYS`. Restore with
`POST /backup/restore`, then restart the server.

**Logs:** stdout + rotating `logs/zoya.log` (1 MB × 5). Log rotation on
the server: `logrotate` or the built-in rotation.

## Testing

```bash
.venv/bin/python -m pytest tests/ -q
# 39 passed (health, auth, devices, commands, features, websockets,
# backup, brain/emotion/memory/character, voice stub)
```

Live test evidence: see `TEST-REPORT.md` (real curl + WebSocket session
against a running server).

## What Phase 2 (website) needs from this backend

- Base URL + API docs (`/docs`, OpenAPI at `/openapi.json`).
- Admin login (JWT) for the dashboard; the static API key for
  device-status widgets.
- Endpoints the Control Center will use: `/health`, `/devices`,
  `/commands`, `/features`, `/conversation/memory`, `/backup/*`,
  `/character`, `/ws/chat` for live logs/chat.
- The **AI Feature Builder** (Phase 8) will POST new feature specs to
  `/features` and read build/test progress — the approval gate lives in
  the website, not in this backend.
