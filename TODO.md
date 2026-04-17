# TODO - Jarvis OS

## Phase 0: Cloud Infrastructure (Priority: CRITICAL)
- [ ] Provision a VPS (Hetzner/DigitalOcean/Linode, Debian 12, 4GB+ RAM)
- [x] Write `infra/scripts/setup-server.sh` -- install Docker, create non-root user, configure UFW (22, 80, 443), disable root SSH
- [x] Write `infra/docker-compose.yml` -- brain + PostgreSQL 16 + Redis 7 + Nginx containers
- [x] Write `infra/docker-compose.dev.yml` -- dev overrides (exposed ports, debug env)
- [x] Write `brain/Dockerfile` -- Python 3.12, install deps, run FastAPI with uvicorn
- [x] Write `infra/nginx/jarvis.conf` -- reverse proxy to brain:8400, WebSocket upgrade (`Upgrade`, `Connection` headers), rate limiting, TLS config
- [ ] Set up Let's Encrypt with certbot for TLS certs (auto-renewal cron)
- [x] Write `infra/.env.example` -- template with all required env vars
- [x] Write `infra/scripts/deploy.sh` -- git pull, docker compose build, docker compose up -d, health check
- [x] Write `infra/scripts/backup.sh` -- pg_dump to timestamped file, optional rsync to offsite
- [x] Write `infra/scripts/restore.sh` -- restore from pg_dump backup
- [x] Configure daily backup cron (setup-server.sh adds it)
- [ ] Verify: brain container starts, health endpoint responds over HTTPS, WebSocket connects over wss://
- [ ] Point domain/subdomain (e.g., `jarvis.yourdomain.com`) to VPS IP

## Phase 1: Brain Core (Priority: CRITICAL)
- [x] Set up monorepo structure (`brain/`, `agents/`, `infra/`, `plugins/`)
- [x] Initialize Python project with venv + requirements.txt for brain
- [x] Implement `brain/src/db/database.py` -- SQLAlchemy engine factory (PostgreSQL prod, SQLite dev, auto-detected from config)
- [x] Implement `brain/src/db/repositories.py` -- repository pattern: `KnowledgeRepo`, `EpisodeRepo`, `ProcedureRepo` (abstracts DB engine)
- [x] Set up Alembic for database migrations (`brain/alembic.ini`, initial migration with all tables)
- [x] Implement `brain/src/redis_client.py` -- Redis connection with in-memory dict fallback for local dev
- [x] Implement `brain/src/cognitive/models.py` -- data classes (Memory, Episode, Procedure, Goal, Task, Message)
- [x] Implement Layer 1: Working Memory (`working_memory.py`) -- Redis-backed (prod) / in-memory (dev), per-device contexts
- [x] Implement Layer 2: Short-Term Memory (`short_term.py`) -- Redis-backed (prod) / deque (dev), 20-message buffer
- [x] Implement Layer 3: Long-Term Memory (`long_term.py`) -- PostgreSQL via repository, CRUD, confidence scoring
- [x] Implement `brain/src/cognitive/manager.py` -- orchestrator that wires layers 1-3
- [x] Set up FastAPI server (`brain/src/api/server.py`) -- REST endpoints for input/response + health check
- [x] Implement `brain/src/api/routes/health.py` -- health endpoint (DB connection, Redis ping, uptime)
- [x] Implement `brain/src/api/middleware/rate_limit.py` -- per-agent rate limiting via Redis
- [x] Implement `brain/src/api/middleware/logging.py` -- request/response structured logging
- [x] Write `brain/config/config.dev.toml` -- local dev overrides
- [x] Write tests for layers 1-3 (pytest, test SQLite DB, mock Redis)
- [x] Write `brain/tests/conftest.py` -- shared fixtures (test DB, mock Redis, FastAPI test client)
- [ ] Test locally: send input, get response, verify memory storage
- [ ] Deploy to cloud: verify brain responds to health check over HTTPS

## Phase 2: Brain Intelligence (Priority: CRITICAL)
- [x] Implement Layer 4: Associative Memory (`associations.py`) -- NetworkX graph, co-occurrence edges, traversal
- [x] Implement Layer 5: Episodic Memory (`episodic.py`) -- PostgreSQL episodes table, event logging
- [x] Implement Layer 6: Procedural Memory (`procedural.py`) -- pattern detection, routine lifecycle (suggested > confirmed > active)
- [x] Implement Layer 7: Personality Memory (`personality.py`) -- JSON profile on disk, tone adaptation, corrections tracking
- [x] Implement Layer 8: Semantic Memory (`semantic.py`) -- ChromaDB embeddings, similarity search, deduplication
- [x] Implement Layer 9: Consolidation (`consolidation.py`) -- session summarization, fact extraction, decay, dedup, contradiction resolution
- [x] Implement Layer 10: Retrieval Pipeline (`retrieval.py`) -- query all layers, rank, select top N, build context
- [x] Implement `extractor.py` -- LLM-powered fact extraction from conversations
- [x] Implement `decay.py` -- importance scoring formula, decay processing, archival to `archive` table
- [x] Set up APScheduler for consolidation cron (every 6 hours + session end)
- [x] Wire all 10 layers into `manager.py`
- [x] Build text-based CLI for testing brain remotely (connects to cloud brain)
- [x] Write Alembic migration for episodes + procedures tables
- [x] Write tests for layers 4-10
- [ ] Deploy and verify on cloud server

## Phase 3: Conversation Engine (Priority: HIGH)
- [x] Implement `brain/src/conversation/chat.py` -- multi-provider LLM integration (Groq, OpenRouter, Gemini, HuggingFace, OpenAI, Anthropic)
- [x] Implement `brain/src/conversation/prompt_builder.py` -- assemble system prompt with brain context
- [x] Implement `brain/src/conversation/intent.py` -- intent detection, entity extraction
- [x] Implement `brain/src/conversation/persona.py` -- Jarvis personality rules, tone logic
- [x] Create `brain/config/persona.toml` -- default personality settings
- [ ] End-to-end test: text input > brain retrieval > LLM call > response with memory update

## Phase 4: Windows Agent (Priority: HIGH)
- [x] Set up `agents/shared/` -- base agent class, WebSocket client, voice abstraction
- [x] Implement `agents/shared/connection.py` -- encrypted WebSocket (wss://) with auto-reconnect + REST fallback
- [x] Set up `agents/windows/` project with venv + requirements.txt
- [x] Implement agent registration flow (`--register` flag, connects to cloud brain, gets JWT)
- [x] Implement Windows actions: `apps.py` (open/close/switch apps)
- [x] Implement Windows actions: `files.py` (file operations)
- [x] Implement Windows actions: `system.py` (volume, brightness, lock, shutdown)
- [x] Implement Windows actions: `browser.py` (open URLs, search)
- [x] Implement Windows actions: `terminal.py` (PowerShell/CMD execution)
- [x] Implement Windows actions: `clipboard.py` (read/write)
- [x] Implement `agents/windows/agent.py` -- main loop: connect to cloud brain, receive actions, execute
- [x] Implement action safety checks (`safety.py` -- confirmation for destructive actions)
- [x] Create `agents/windows/config.toml` (with wss:// cloud brain URL)
- [ ] Test: send command from cloud brain, verify Windows agent executes it

## Phase 5: WebSocket Protocol (Priority: HIGH)
- [x] Implement brain-side WebSocket handler (`brain/src/api/websocket/handler.py`)
- [x] Implement event dispatcher (`brain/src/api/websocket/events.py`)
- [x] Implement JWT auth middleware for WebSocket connections
- [x] Implement agent presence tracking in Redis (online/offline, last seen, capabilities)
- [x] Implement device routing (`brain/src/orchestration/device_router.py`)
- [ ] Verify Nginx correctly upgrades HTTP to WebSocket (wss://)
- [ ] Test: agent connects over internet, sends input, brain responds, agent executes action
- [ ] Test: cross-device task (set on one "device", trigger on another)

## Phase 6: Voice (Priority: MEDIUM)
- [x] Implement STT: `agents/windows/voice/stt.py` (faster-whisper)
- [x] Implement TTS: `agents/windows/voice/tts.py` (Piper local + ElevenLabs cloud option)
- [x] Implement wake word: `agents/windows/voice/listener.py` (Porcupine)
- [x] Implement audio device management (`audio_utils.py`)
- [x] Wire voice into Windows agent main loop
- [x] End-to-end test: speak > transcribe > send to cloud brain > respond > speak
- [x] Voice in GUI app: mic button, Ctrl+Space, Google STT, Windows TTS
- [x] Native C# WPF desktop app (`agents/windows-app/`): .NET 9, XAML, Windows Speech API, native WebSocket

## Phase 7: Task Orchestration (Priority: MEDIUM)
- [x] Implement `brain/src/orchestration/task_manager.py` -- task breakdown, dependency tracking
- [x] Implement `brain/src/orchestration/workflow_executor.py` -- execute procedural routines across devices
- [x] Implement multi-step task status tracking (pending > dispatched > in_progress > completed/failed)
- [ ] Test: complex request broken into sub-tasks, routed to agent, results tracked

## Phase 8: UI (Priority: LOW)
- [x] Implement Windows system tray (`agents/windows/ui/tray.py`) -- icon, menu, connection status indicator
- [x] Optional: floating overlay for desktop (`agents/windows/ui/overlay.py`)
- [x] Brain admin CLI (runs via `docker exec`) -- view memories, force consolidation, revoke agents
- [x] Full GUI desktop app (`agents/windows/app.py`) -- chat window, tray icon, WebSocket, action execution

## Phase 9: Additional Desktop Agents (Priority: LOW)
- [x] Implement macOS agent (`agents/macos/`) -- osascript, pyobjc for OS control
- [x] Implement Linux agent (`agents/linux/`) -- xdg-open, dbus, xdotool, systemctl
- [ ] Test: same cloud brain, multiple agents from different machines, actions route correctly

## Phase 10: Mobile Agents (Priority: LOW)
- [ ] iOS agent (Swift) -- WebSocket client (wss://), native STT/TTS, push-to-talk UI, notifications
- [ ] Android agent (Kotlin) -- WebSocket client (wss://), native STT/TTS, push-to-talk UI, notifications
- [ ] Test: voice input on phone over cellular, brain responds, action executes on PC at home

## Phase 11: Polish and Extras (Priority: BACKLOG)
- [x] Offline mode -- local cache of top memories, command queuing, queue flush on reconnect, disconnected indicator
- [x] Plugin system -- define plugin interface, build Spotify plugin as reference
- [x] Spotify plugin -- real Spotify Web API (OAuth PKCE, search, play, pause, skip, volume, now playing)
- [x] Plugin auto-setup -- AI detects unconfigured plugins, asks user for credentials, saves config automatically
- [x] Plugin config persistence -- JSON config per plugin in brain/data/plugins/
- [ ] Screen understanding -- screenshot + OCR for context awareness
- [x] Predictive suggestions -- time-based procedural triggers ("It's 9am Monday...")
- [x] Memory export/import CLI (via brain admin)
- [ ] Per-device action permissions config
- [ ] Cloud server monitoring (uptime checks, disk alerts, memory usage)
- [ ] Log rotation on cloud server
- [ ] Optional GPG encryption for backups

## Decisions Made
- [x] ~~SQLite vs PostgreSQL~~ -- PostgreSQL for production (cloud server), SQLite for local dev only
- [x] ~~Redis: needed for v1?~~ -- Yes, required in production for working memory, short-term, agent presence, rate limiting
- [x] ~~TLS: Tailscale or public?~~ -- Public internet with Let's Encrypt TLS. No VPN needed.
- [x] ~~Brain location: local or cloud?~~ -- Cloud VPS. Always on, reachable from anywhere. $10-40/mo.

## Decisions Still Open
- [ ] VPS provider: Hetzner vs DigitalOcean vs Linode vs OVH?
- [ ] Domain: use existing domain subdomain or register new one?
- [ ] Mobile distribution: TestFlight for iOS, APK sideload for Android?
- [ ] Wake word: Porcupine (proprietary, free tier) vs custom model?
- [ ] TTS default: Piper quality good enough? Or push ElevenLabs as default?
- [ ] Supervisor vs systemd for brain process management inside Docker?
