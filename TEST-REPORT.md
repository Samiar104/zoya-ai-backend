# ZOYA AI Backend — Phase 1 Test Report

Date: 2026-11-16. All tests were run against the real code in this repo.

## 1. Automated tests (pytest)

Command: `.venv/bin/python -m pytest tests/ -q`

Result: **39 passed** (final run, after the ConfigDict cleanup and the
brain fixes). Coverage by file:

- `test_health.py` — root, `/health`, `/health/ready`
- `test_auth.py` — register, login, duplicate rejection, wrong password,
  `/me` auth, JWT has **no `exp` claim** (never-expire requirement),
  API-key info (admin only, `expires: never`)
- `test_devices.py` — register with API key, reject without key, list,
  heartbeat, unknown device 404
- `test_commands.py` — queue (offline device stays `queued`), unknown
  device 404, invalid type 422, result + cancel, filtered list
- `test_features.py` — built-ins seeded, create/enable/disable/delete,
  duplicate rejected
- `test_websocket.py` — chat WS reply, device WS rejects bad API key
  (1008), device WS connect + heartbeat
- `test_backup.py` — create/list/download, restore 404, auth required
- `test_brain.py` — emotion (sad/happy/neutral), character profile,
  memory add/list, chat reply includes emotion + recalls stored name,
  sad message → comforting companion reply, invalid mode 400,
  voice status stub, STT stub → 501

One failure was found and fixed during the run: the device-WS auth test
expected the disconnect on `receive_text`, but Starlette raises it on
connect — the server behaviour (close 1008) was correct; the test was
corrected.

## 2. Live server test (uvicorn + curl + WebSocket)

Server started with `./run.sh` equivalent:
`uvicorn app.main:app --host 127.0.0.1 --port 8000`.
First start generated the static API key and saved it to `.env`.

### Health
```
GET /health
{"status":"ok","app":"ZOYA AI Backend","version":"1.0.0","environment":"development","uptime_seconds":25.9,"database":"ok"}
```

### Auth
```
POST /auth/register {"username":"zoya_admin",...}
{"id":1,"username":"zoya_admin","is_active":true,"is_admin":true}
POST /auth/login -> token acquired (172 chars, JWT, no exp claim)
GET /auth/me -> same user
```

### Character
```
GET /character
{"name":"ZOYA","tagline":"Your AI friend, assistant and companion.",
 "personality_traits":["friendly","witty","supportive","curious","patient","playful"],
 "voice_character":"Natural human-like female voice, warm and expressive, medium pitch, calm pace",
 "avatar_url":"zoya-character.png","languages":["hi","ur","pa","en"],
 "modes":["assistant","companion"]}
```

### Emotion
```
POST /conversation/analyze-emotion {"text":"I am really sad today, I feel like crying"}
{"emotion":"sad","confidence":0.95,"label":"उदास"}
```

### Brain — memory + companion mode + emotion-adaptive reply
```
POST /chat/sessions {"language":"hi","mode":"companion"} -> session id 1
POST /chat/message "mera naam Ayaan hai, mujhe cricket pasand hai"
  -> (first run) "आपने अभी अपना नाम नहीं बताया..."  <-- BUG FOUND, see §4
POST /chat/message "what is my name?"
  -> {"reply":"आपका नाम ayaan है — मैं याद रखती हूँ।","intent":"ask_name",...}
POST /chat/message "I am really sad today"
  -> {"reply":"अरे जान, उदास मत हो — मैं तुम्हारे साथ हूँ। जो भी दिल में है, मुझे बता दो। हम मिलकर ठीक कर लेंगे।",
      "intent":"share_feeling","emotion":"sad","emotion_confidence":0.95}
GET /conversation/memory -> preferences (likes cricket), fact (name=ayaan),
  topics (cricket), moods (sad:0.95, neutral:0.50)
```

### Devices & commands
```
POST /devices/register (X-API-Key) {"device_id":"pixel-test-001",...} -> device id 1
POST /commands {"device_id":1,"command_type":"open_app","payload":{"app":"youtube"}}
  -> {"id":1,"command_type":"open_app","status":"queued"}   (device offline)
GET /commands/1 -> same, status queued
```

### Features / voice / backup
```
POST /features {"name":"teaching_mode",...} -> created, enabled=true
POST /features/teaching_mode/disable -> enabled=false
GET /voice/status -> {"engine":"stub","stt_available":false,"tts_available":false,...}
POST /backup/create -> {"filename":"zoya-backup-20261116-115811.db","size_bytes":102400}
```

### WebSockets (python `websockets` client)
```
CHAT WS reply: reply | "नमस्ते जान! मैं ज़ोया — तुम्हारी अपनी। ..." | emotion: neutral  -> PASS
DEVICE WS: connected + heartbeat + result sent  -> PASS
```

## 3. Issues found live and fixed

1. **Learn-before-reply ordering** — the brain answered using memory
   from *before* the current message, so "mera naam Ayaan hai" got
   "you haven't told me your name". Fixed: `send_message` now learns
   from the message and rebuilds context *before* generating the reply.
2. **Introduce vs ask-name** — "mera naam X hai" (statement) was
   misclassified as asking the name. Fixed: new `introduce` intent;
   `ask_name` now only matches questions ("what is my name?",
   "mera naam kya hai"). Verified live: "mera naam Bilal hai" →
   "याद रख लिया — bilal! आपसे मिलकर अच्छा लगा।", then "what is my name?"
   → "आपका नाम bilal है — मैं याद रखती हूँ।"
3. **Preference extraction** captured "cricket pasand" instead of
   "cricket". Fixed by stripping trailing filler words. Verified live:
   `likes_football = "football"`.
4. **Pydantic deprecation** — `class Config: from_attributes` replaced
   with `ConfigDict` in all schemas.

Re-test after fixes: new companion session, introduce + recall + memory
list all correct; both WebSocket channels pass. Full pytest suite
re-run: **39 passed**.

## 4. Known honest limits (not bugs)

- Voice STT/TTS are stubs returning 501 until faster-whisper/Piper are
  installed (README "Voice").
- The brain is rule-based, not an LLM (README "ZOYA's brain").
- Rate limiting is in-memory (single worker); use Redis for multi-worker.
- WebSocket manager is process-local; use Redis pub/sub for multi-worker.
- 24/7 uptime needs a real server/VPS; this VM was only for dev/test.
