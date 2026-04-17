# AI Session State
Last updated: 2026-04-17 17:40

## What I was working on
JWT auth, agent registration, device routing, voice engine (Phase 5 + 6 completion).

## What I completed
- [x] JWT auth module: create/verify tokens, extract from Bearer header
- [x] Per-device permissions: platform-based defaults + custom capabilities
- [x] Agent registration endpoint (POST /api/v1/agent/register)
- [x] Agent status endpoint (GET /api/v1/agent/status)
- [x] JWT verification in WebSocket handler (production mode)
- [x] Device router for action routing to correct agent
- [x] Agent --register flag for client-side registration
- [x] STT via faster-whisper (file + bytes)
- [x] TTS via Piper (local) and ElevenLabs (cloud)
- [x] Wake word detection via Porcupine
- [x] Audio device utilities
- [x] 65 tests all passing

## What's in progress
Nothing.

## What's next
- Wire voice into Windows agent main loop (voice mode)
- End-to-end testing (brain + agent running together)
- Phase 7: Task Orchestration (task_manager.py, workflow_executor.py)
- Phase 0: Cloud Infrastructure (Docker, Nginx, deploy scripts)

## Files created
- brain/src/api/auth/__init__.py, jwt.py, permissions.py
- brain/src/api/routes/agents.py
- brain/src/orchestration/device_router.py
- brain/tests/test_auth.py
- agents/windows/voice/__init__.py, stt.py, tts.py, listener.py, audio_utils.py

## Files modified
- brain/src/api/server.py (agents router, jwt_secret to WS)
- brain/src/api/websocket/handler.py (JWT verification)
- agents/windows/agent.py (--register flow)
- TODO.md, CHANGELOG.md

## Current branch
dev

## Notes for the next agent
- 65 tests green: `PYTHONPATH=. brain/venv/Scripts/python -m pytest brain/tests/ -v`
- Git: https://github.com/thomaxis/jarvis.git, 7 commits on dev
- Voice deps (faster-whisper, pyaudio, pvporcupine, piper, elevenlabs) are NOT installed. They import dynamically and gracefully disable.
- JWT auth is skipped in debug mode (config.general.debug = true). Enforced when debug = false.
- The voice modules are implemented but not yet wired into the agent main loop.
