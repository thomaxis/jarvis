# Changelog

All notable changes to Jarvis OS will be documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added
- Initialized git repo on `dev` branch with `.gitignore`
- Monorepo folder structure: `brain/`, `agents/`, `infra/`, `plugins/` with Python packages
- Brain config system (`brain/src/config.py`) with TOML loading and dev overrides
- Structured logging (`brain/src/logger.py`) via structlog
- Cognitive data models (`brain/src/cognitive/models.py`): Knowledge, Episode, Procedure, Goal, Task, Message, DeviceContext with enums
- SQLAlchemy async database layer (`brain/src/db/database.py`) with KnowledgeTable, EpisodeTable, ProcedureTable, ArchiveTable
- Repository pattern (`brain/src/db/repositories.py`): KnowledgeRepo, EpisodeRepo, ProcedureRepo
- Redis client (`brain/src/redis_client.py`) with InMemoryRedis fallback for local dev
- Layer 1: Working Memory (`working_memory.py`) -- Redis-backed per-device contexts, goals, cross-device tasks
- Layer 2: Short-Term Memory (`short_term.py`) -- Redis-backed 20-message buffer, corrections, device tracking
- Layer 3: Long-Term Memory (`long_term.py`) -- PostgreSQL-backed knowledge with contradiction resolution and confidence scoring
- Brain Manager (`manager.py`) -- orchestrator wiring layers 1-3 with process_input/process_response pipeline
- FastAPI server (`brain/src/api/server.py`) with lifespan, CORS, health and input routes
- Health endpoint (`/health`) -- reports version, uptime, Redis status, brain status
- Input endpoint (`POST /api/v1/input`) -- processes user text through cognitive pipeline
- Response endpoint (`POST /api/v1/response`) -- stores assistant response and extracted facts
- Config files: `config.toml` (production) and `config.dev.toml` (SQLite, no Redis)
- `brain/requirements.txt` with pinned dependencies
- `brain/src/__version__.py` tracking version 0.0.0
- Test suite: 22 tests covering all 3 layers + API endpoints (all passing)
- Alembic migrations setup with initial schema (knowledge, episodes, procedures, archive tables)
- Rate limiting middleware (`rate_limit.py`) -- per-IP, 120 req/min, Redis-backed, skips /health
- Request logging middleware (`logging.py`) -- structured logs with method, path, status, duration
- Layer 4: Associative Memory (`associations.py`) -- NetworkX graph, spreading activation, co-occurrence edges, decay
- Layer 5: Episodic Memory (`episodic.py`) -- autobiographical event recording with time-of-day tagging
- Layer 6: Procedural Memory (`procedural.py`) -- routine lifecycle (suggested > confirmed > active), trigger matching
- Layer 7: Personality Memory (`personality.py`) -- JSON profile, per-device style, corrections tracking
- Layer 8: Semantic Memory (`semantic.py`) -- ChromaDB vector search with graceful fallback if not installed
- Layer 9: Consolidation Engine (`consolidation.py`) -- decay, dedup, rescoring, association cleanup
- Layer 10: Retrieval Pipeline (`retrieval.py`) -- full 10-layer context assembly with spreading activation
- Brain Manager upgraded to orchestrate all 10 layers with save_state() and consolidate()
- Added networkx==3.4.2 to requirements
- Test suite expanded to 41 tests (19 new for layers 4-10)
- Conversation Engine: ChatEngine (`chat.py`) with Claude/OpenAI async integration and structured JSON parsing
- Prompt Builder (`prompt_builder.py`) assembles system prompt from full 10-layer context
- Intent Detection (`intent.py`) with regex-based action/question/command/memory/conversation classification
- Entity Extraction: apps, URLs, file paths, time expressions
- Persona rules (`persona.py`): banned phrase filtering, verbosity trimming, context-aware greetings
- Test suite expanded to 56 tests (15 new for conversation engine)
- LLM-powered fact extractor (`extractor.py`) with extraction prompt and JSON parsing
- Memory decay module (`decay.py`) with importance scoring formula and archival to archive table
- APScheduler integration (`scheduler.py`) for consolidation (6h) and decay (24h) cron jobs
- Scheduler wired into FastAPI lifespan (auto-start/stop)
- Brain CLI (`brain/cli.py`) for testing brain remotely via REST API
- Default persona config (`brain/config/persona.toml`)
- WebSocket handler (`brain/src/api/websocket/handler.py`) with ConnectionManager and agent lifecycle
- WebSocket event dispatcher (`events.py`) handling user_input, action_result, context_update
- WebSocket `/ws` endpoint wired into FastAPI server
- Brain saves state (graph + personality) on shutdown
- Shared agent layer: BaseAgent, BrainConnection (WebSocket + REST fallback), data models
- BrainConnection with auto-reconnect (exponential backoff up to 60s)
- Windows Agent with 6 action modules: apps, files, system, browser, terminal, clipboard
- Action safety system: destructive actions require user confirmation
- Windows agent supports text-only mode (`--text-only`) and full WebSocket mode
- Agent config template (`config.toml.example`) and `requirements.txt`
- JWT authentication for agents (`brain/src/api/auth/jwt.py`) with token creation and verification
- Per-device permission system (`permissions.py`) with platform-based and capability-based access control
- Agent registration endpoint (`POST /api/v1/agent/register`) returns signed JWT
- Agent status endpoint (`GET /api/v1/agent/status`) shows online devices
- JWT verification integrated into WebSocket handler (enforced in production, skipped in debug)
- Device router (`brain/src/orchestration/device_router.py`) for action routing to correct agent
- Agent `--register` flag connects to brain REST API and retrieves JWT token
- Voice engine: STT via faster-whisper with file and byte transcription
- Voice engine: TTS via Piper (local) or ElevenLabs (cloud) with WAV/MP3 playback
- Voice engine: Wake word detection via Porcupine with fallback to push-to-talk
- Audio device management utilities (list devices, get defaults)
- Test suite expanded to 65 tests (9 new for JWT auth, permissions, agent endpoints)
- Task Manager (`task_manager.py`) with subtask creation, dependency tracking, parent auto-completion
- Workflow Executor (`workflow_executor.py`) dispatches multi-step routines to device agents
- Cloud infrastructure: Dockerfile, docker-compose.yml (brain + PostgreSQL 16 + Redis 7)
- Docker Compose dev overrides (exposed ports, debug mode)
- Nginx config with TLS, WebSocket upgrade, rate limiting, security headers
- Server setup script (Docker, UFW, fail2ban, certbot, non-root user)
- Deploy script (git pull, rebuild, restart, health check)
- Backup/restore scripts for PostgreSQL with daily cron
- .env.example template for server environment
- Test suite expanded to 72 tests (7 new for task orchestration)
- Voice mode wired into Windows agent main loop (wake word > record > transcribe > send > speak response)
- Windows system tray (`ui/tray.py`) with pystray: connection status icon, text mode toggle, quit
- macOS agent with osascript-based actions: apps, files, system (volume/lock/power), terminal
- Linux agent with xdg-open/amixer/systemctl/pkill actions: apps, files, system, terminal
- Both agents share the BaseAgent/BrainConnection pattern from agents/shared/
- Offline cache (`agents/shared/offline.py`): knowledge caching, command queuing, queue flush on reconnect
- Plugin system (`plugins/base.py`): JarvisPlugin interface + PluginManager for loading/unloading
- Spotify plugin as reference implementation with play/pause/next/previous/search actions
- Brain admin CLI (`brain/admin.py`): status, memories, consolidate, forget, export, revoke commands
- Plugin system wired into BrainManager with load_plugin() and shutdown()
- Predictive suggestions engine (`predictions.py`): time-based routine triggers, context-aware greetings
- Desktop overlay (`ui/overlay.py`): transparent floating tkinter window for Jarvis responses
- README.md with architecture overview, quick start, and project structure
- Test suite expanded to 82 tests (10 new for plugins + predictions)

### Planning Phase - 2026-04-17

#### Added
- Initial CLAUDE.md with full system architecture
- Cognitive brain architecture (10-layer memory system)
- Distributed system design: Central Brain + Device Agents
- Communication protocol spec (WebSocket + REST fallback)
- Task orchestration engine design
- Security model (JWT auth, per-device permissions)
- Offline mode specification
- Project folder structure for monorepo
- RULES.md for AI coding guidelines
- TODO.md with phased development plan
- CHANGELOG.md

#### Architecture Evolution (Design Phase)

**v0.1 - Single Windows App**
- Started as a single Python app running on Windows
- 5-layer memory system (short-term, long-term, semantic, episodic, working memory manager)
- Voice + system control + conversation in one process
- All memory stored locally in SQLite + ChromaDB

**v0.2 - Cognitive Brain Upgrade**
- Expanded memory from 5 layers to 10-layer cognitive architecture
- Added: Associative Memory (NetworkX concept graph)
- Added: Procedural Memory (learned routines from repeated patterns)
- Added: Personality Memory (tone, style, conversational continuity)
- Added: Memory Consolidation (background "sleep" process)
- Added: Brain Retrieval System (think-before-speaking pipeline)
- Added: Importance scoring with frequency, recency, task relevance, user emphasis
- Added: Memory decay and archival system
- Renamed "memory_engine" to "brain" throughout

**v0.3 - Distributed Ecosystem**
- Transformed from single app to distributed system
- Central Brain: FastAPI server hosting all 10 cognitive layers
- Device Agents: thin clients on Windows, macOS, Linux, iOS, Android
- WebSocket + REST communication protocol between brain and agents
- Cross-device working memory (tasks set on one device, triggered on another)
- Cross-device procedural routines (morning routine spans multiple devices)
- Task Orchestration Engine for multi-step, multi-device workflows
- Device Coordinator for routing actions to correct agents
- JWT authentication per device agent
- Offline mode with local cache and command queuing
- Per-device personality adaptation (shorter responses on mobile)
- Agent registration system
- Network security: local-only by default, optional Tailscale/WireGuard

**v0.4 - Cloud Backend**
- Brain server moved from local machine to cloud VPS (always on, always reachable)
- Replaced SQLite with PostgreSQL 16 as primary database for production
- Redis 7 now required in production for working memory, short-term memory, agent presence, rate limiting
- Added full Docker Compose stack: brain + PostgreSQL + Redis + Nginx
- Added Nginx reverse proxy with TLS termination (Let's Encrypt auto-renewal)
- All agent-to-brain traffic now encrypted (wss:// and https://)
- Added `infra/` directory with server setup, deploy, backup, and restore scripts
- Added Alembic for database migrations
- Added repository pattern for data access (abstracts SQLite vs PostgreSQL)
- Added Redis client with in-memory fallback for local development
- Added `config.dev.toml` for local dev overrides (SQLite, no Redis, no TLS)
- Added rate limiting middleware (Nginx + Redis per-agent tracking)
- Added health check endpoint for monitoring
- Added `.env.example` template for server environment variables
- Firewall: only ports 22, 80, 443 exposed. Brain port 8400 internal only.
- PostgreSQL and Redis not exposed to internet (Docker internal network only)
- Daily automated backups via pg_dump cron
- Removed Tailscale/WireGuard requirement (TLS over public internet is sufficient)
- Updated all agent configs to point to cloud brain (wss:// URLs)
- Added Phase 0 (Cloud Infrastructure) to development priorities
- Cloud server requirements documented: 2-4 vCPU, 4-8GB RAM, Debian 12
- Estimated cost: $10-40/mo depending on provider
- Local dev mode preserved: SQLite + in-memory Redis fallback, no Docker needed

**v0.5 - Git & Project Governance**
- Added Rule 0: Scope and Focus -- AI must only work on Jarvis OS, never touch other projects
- Added Rule 2: Git Rules -- comprehensive git workflow for AI assistants
- Established version-based branching strategy: `main`, `dev`, `v0.1.0`, `v0.2.0`, etc.
- All commits must be under the user's git identity, never under AI names
- No `Co-Authored-By` AI attribution in commits
- Always push after committing. No orphaned local commits.
- Always stage specific files, never `git add .` blindly
- Never commit directly to `main`. Always merge from version branches.
- Version branches are permanent and never deleted
- Defined version milestones: v0.1.0 through v1.0.0
- Added `infra:` commit prefix for infrastructure changes
- Expanded session completion checklist: verify push, verify branch, verify no cross-project contamination
- Expanded `.gitignore` with IDE files, OS files, mypy cache, SSL certs
- Added repo organization rules: clean root, source under proper directories, no orphan files
- Added `brain/src/__version__.py` requirement for version tracking in code

**v0.6 - Session Continuity & Consistency**
- Added Rule 10: Session Continuity -- AI agents MUST save progress to `.ai-sessions/current.md` before running out of context/credits
- Added `.ai-sessions/` directory as the AI's persistent brain between sessions
- Session handoff files include: current task, completed steps, in-progress work, blockers, files modified, decisions made, notes for next agent
- Session history preserved in `.ai-sessions/history/` with timestamped filenames
- AI agents must read previous session handoff at the START of every new session
- Emergency save protocol: if context is running low, stop and save immediately
- `.ai-sessions/` is committed to git (NOT in .gitignore) -- handoff files are part of the project
- Added Rule 11: Consistency Rules
- Code consistency: follow existing patterns, search before writing duplicates
- Naming consistency: one term per concept across DB, API, and code (`device_id` everywhere, not mixed with `agent_id`)
- Behavioral consistency: same error handling, logging format, and feature behavior across all modules
- Cross-session consistency: don't contradict previous agents' decisions, don't rename or restructure without reason, finish half-done work as it was started
- Expanded session checklist to 4 categories: Code Quality, Documentation, Git, Session Continuity
- When stuck, check `.ai-sessions/` before CLAUDE.md -- a previous agent may have solved it

**v0.7 - Token Economy (Current)**
- Added Rule 0: Token Economy -- "Shut up and work." AI must minimize text output and maximize code output
- No explaining before doing, no summarizing after doing, no narrating thought process
- Token budget priority: code > reading files > updating docs > talking to user
- Response targets: "Done." for implementations, one sentence for fixes, 1-3 sentences for questions
- If text response exceeds 5 lines, it's probably wasting tokens
- All rules renumbered (0-14) to accommodate new Rule 0 at top priority position
