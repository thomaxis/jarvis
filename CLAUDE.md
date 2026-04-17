# Jarvis OS - Personal AI Ecosystem

> A private AI ecosystem that runs across all your devices. One brain, multiple bodies. Not an app. A personal AI operating system with real cognition.

**MANDATORY: Read [RULES.md](RULES.md) before writing any code.** Every code change must update CHANGELOG.md and TODO.md. No exceptions.

## WHAT IS JARVIS OS

A distributed AI assistant system inspired by JARVIS. One central brain runs on a cloud server (always on, always reachable). Lightweight agents run on every device you own. They share memory, context, and tasks in real time. Start something on your phone, finish it on your PC. Jarvis knows you across every device because it's the same brain.

**Architecture in one sentence:** A FastAPI brain server hosted in the cloud, with thin agents on Windows, macOS, Linux, and mobile that connect to it over the internet.

**The loop on every device:** Listen > Send to Brain > Brain thinks (with full memory) > Brain responds > Agent acts locally > Brain learns

**What makes this different:**
- The brain lives in the cloud. Always on, always reachable. No need for your PC to be running.
- Agents are thin clients. They handle voice I/O and local OS actions. The thinking happens on the brain.
- You can talk to Jarvis on your phone at 3am and it responds instantly. Your PC can be off.
- You sit at your desk, the Windows agent connects, and Jarvis remembers what you said on your phone earlier. Same brain.

## CORE PRINCIPLES

1. **The brain is the product.** Everything else (voice, UI, agents, OS control) is a delivery mechanism. If the brain is weak, the entire system fails.
2. **Cloud brain, private data.** The brain server runs on YOUR cloud server (VPS you control). You own the box, you own the data. It's not a SaaS -- it's your personal infrastructure. Always on, always reachable from any device.
3. **One brain, many bodies.** Every device agent connects to the same cloud brain. Memory is never duplicated. Context is never lost between devices or sessions.
4. **Cognitive, not storage.** This is not a database with a chat interface. Memories are linked by meaning, scored by importance, decay over time, and consolidate like a real brain.
5. **Private.** This is not published to app stores. It's your personal system. You control the server, you own the data, nobody else has access.
6. **Modular.** Swap the LLM, change the TTS, add a new device agent, build a plugin -- nothing breaks.
7. **Always on.** The brain server never sleeps. Consolidation runs on schedule. Agents connect and disconnect freely. The brain is ready the moment any device reaches out.

## SYSTEM ARCHITECTURE

```
                      ☁️  CLOUD SERVER (VPS)
                 ┌────────────────────────────────┐
                 │       CENTRAL BRAIN            │
                 │      (FastAPI + Docker)        │         
                 │                                │
                 │   ┌────────────────────────┐   │
                 │   │    Cognitive Engine    │   │
                 │   │  (10-Layer Brain)      │   │
                 │   └────────────────────────┘   │
                 │   ┌────────────────────────┐   │
                 │   │   Reasoning (LLM API)  │   │
                 │   └────────────────────────┘   │
                 │   ┌────────────────────────┐   │
                 │   │  Task Orchestration    │   │
                 │   └────────────────────────┘   │
                 │   ┌────────────────────────┐   │
                 │   │  Device Coordinator    │   │
                 │   └────────────────────────┘   │
                 │   ┌────────────────────────┐   │
                 │   │  PostgreSQL + Redis    │   │
                 │   └────────────────────────┘   │
                 │   ┌────────────────────────┐   │
                 │   │  Nginx (reverse proxy) │   │
                 │   └────────────────────────┘   │
                 └────────────────┬───────────────┘
                                  │
                     wss:// + HTTPS (encrypted)
                                  │
          ┌────────────┬──────────┼───────────┬─────────────┐
          │            │          │           │             │
   ┌──────┴──────┐ ┌───┴───┐ ┌────┴────┐ ┌────┴────┐ ┌──────┴──────┐
   │  Windows    │ │ macOS │ │  Linux  │ │   iOS   │ │  Android    │
   │  Agent      │ │ Agent │ │  Agent  │ │  Agent  │ │  Agent      │
   │  (PRIMARY)  │ │       │ │         │ │         │ │             │
   │             │ │       │ │         │ │         │ │             │
   │ - OS ctrl   │ │ - OS  │ │ - Term  │ │ - Voice │ │ - Voice     │
   │ - Voice     │ │ - App │ │ - File  │ │ - Notif │ │ - Notif     │
   │ - Apps      │ │ - Auto│ │ - Svc   │ │ - Remot │ │ - Remote    │
   │ - Files     │ │       │ │         │ │   cmd   │ │   cmd       │
   └─────────────┘ └───────┘ └─────────┘ └─────────┘ └─────────────┘
        Home           Home      Home/       Anywhere     Anywhere
        LAN            LAN       Server
```

### How It Flows

1. User speaks to any device agent (home, office, on the go -- doesn't matter)
2. Agent does STT locally (fast, no network latency for transcription)
3. Agent sends the text + device context to the Cloud Brain via encrypted WebSocket
4. Brain runs the full retrieval pipeline (all 10 memory layers)
5. Brain calls Claude API with enriched context
6. Brain parses the response: text + actions + facts to store
7. Brain routes actions to the correct device agent(s)
8. Agent executes actions locally and streams results back
9. Brain updates memory in PostgreSQL + ChromaDB
10. Agent plays TTS response

### Cross-Device Example
```
User on phone (at coffee shop): "Remind me to open the investor deck when I get to my PC"
  → Brain stores a pending task: "open investor deck" triggered by "Windows agent comes online"

User gets home, opens PC, Windows agent connects to cloud brain:
  → Brain detects Windows agent online
  → Brain recalls the pending task
  → Jarvis on PC: "You asked me to open the investor deck. Opening it now."
  → Windows agent opens the file
```

### Why Cloud (Not Local)

The original design ran the brain on the user's primary PC. This had problems:
- **PC must be on** for Jarvis to work. Phone agent is dead if your PC is sleeping.
- **LAN only** without VPN tunneling. Mobile agents can't reach the brain outside the house.
- **Single point of failure.** PC reboots, crashes, or runs out of RAM = brain goes down.
- **No consolidation at night.** Memory consolidation can't run if the machine is off.

Cloud brain fixes all of this:
- **Always on.** 24/7 uptime. Consolidation runs on schedule. Agents connect whenever.
- **Reachable from anywhere.** Phone works at the coffee shop, on the train, at the office.
- **Dedicated resources.** Brain gets its own CPU/RAM. Doesn't compete with your games or builds.
- **Proper database.** PostgreSQL instead of SQLite. Better for concurrent agent connections.
- **Backups.** Automated daily backups of the brain database. Your memories are safe.

You still own the server. It's a VPS you rent and control. Not a third-party SaaS.

## TECH STACK

### Central Brain (Cloud Server)
| Layer | Technology | Why |
|-------|-----------|-----|
| Runtime | Python 3.12+ | Best AI/ML ecosystem |
| API Framework | FastAPI + WebSockets | Async, fast, typed. WebSockets for real-time agent communication |
| LLM | Claude API (Anthropic) | Primary reasoning. Fallback: OpenAI GPT-4o |
| Database | PostgreSQL 16 | Production-grade. Handles concurrent agent connections. Proper backups. |
| Vector DB | ChromaDB (embedded) | Semantic memory. Runs in the same container as the brain |
| Association Graph | NetworkX | Concept linking. Persisted to disk as GraphML |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local embeddings on the server, ~80MB model |
| Cache/Realtime | Redis 7 | Agent presence tracking, pub/sub for multi-agent events, session cache, rate limiting |
| Scheduling | APScheduler | Consolidation cron, decay, routine triggers |
| Auth | JWT (PyJWT) | Agent authentication. Each device gets a signed token |
| Reverse Proxy | Nginx | TLS termination, WebSocket upgrade, rate limiting, static files |
| Containerization | Docker + Docker Compose | Brain + PostgreSQL + Redis + Nginx in one stack |
| SSL | Let's Encrypt (certbot) | Free TLS certs, auto-renewal. All traffic encrypted. |
| Process Manager | Supervisor or systemd | Auto-restart brain if it crashes |
| Backups | pg_dump cron + rsync | Daily PostgreSQL backups. Optional offsite sync. |

### Cloud Server Requirements
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB (embeddings model + ChromaDB in memory) |
| Disk | 40 GB SSD | 80 GB SSD |
| OS | Debian 12 / Ubuntu 24.04 | Debian 12 |
| Provider | Any VPS | Hetzner, DigitalOcean, Linode, OVH (cheap, reliable) |
| Cost | ~$10-20/mo | ~$20-40/mo |

### Local Development
For development, the brain can still run locally without Docker:
- SQLite instead of PostgreSQL (auto-detected from config)
- No Nginx (FastAPI serves directly)
- No Redis (in-memory fallback)
- Same code, same API, just different config

### Device Agents
| Platform | Language | Key Libraries |
|----------|----------|---------------|
| Windows (PRIMARY) | Python | pyautogui, pywinauto, subprocess, ctypes, pystray |
| macOS | Python | pyobjc, subprocess, osascript wrappers |
| Linux | Python | subprocess, dbus, xdotool wrappers |
| iOS | Swift (native app) | Speech framework, URLSession/WebSocket, local notifications |
| Android | Kotlin (native app) | SpeechRecognizer, OkHttp/WebSocket, notifications |

### Voice (On Every Agent)
| Component | Technology | Where |
|-----------|-----------|-------|
| STT | faster-whisper | Runs on-device (no network needed for transcription) |
| TTS (local) | Piper | Runs on-device, zero cost |
| TTS (cloud) | ElevenLabs API | Opt-in, routed through brain for API key management |
| Wake Word | Porcupine (Picovoice) | Runs on-device, always-on, low CPU |
| Mobile STT | Native OS APIs | iOS Speech framework / Android SpeechRecognizer |
| Mobile TTS | Native OS APIs | iOS AVSpeechSynthesizer / Android TextToSpeech |

## THE BRAIN (COGNITIVE ARCHITECTURE)

The brain lives on the cloud server. All 10 layers run there. Agents never store memory locally (except short-term cache for offline mode). The cloud server is the single source of truth.

**Storage split:**
- **PostgreSQL:** Long-term knowledge, episodes, procedures (structured, queryable, backed up)
- **ChromaDB:** Semantic embeddings (vector search, runs embedded in the brain process)
- **Redis:** Working memory, short-term memory, agent presence, real-time state (fast, ephemeral)
- **Disk files:** Association graph (GraphML), personality profile (JSON), session summaries (JSON)

In local dev mode, PostgreSQL is replaced by SQLite and Redis is replaced by in-memory dicts. The code abstracts this behind repository interfaces.

---

### Layer 1: Working Memory (The Conscious Mind)

**What:** What Jarvis is actively thinking about right now. The scratchpad.
**Storage:** Redis (production) or in-memory Python object (local dev). Ephemeral. Rebuilt if the brain restarts.
**Speed:** Instant. Always loaded. No PostgreSQL queries.
**Scope:** Per-device (each agent has its own working memory slot) + global (cross-device goals).

**Contains:**
- Current conversation topic (per device)
- Active task stack (multi-step tasks in progress)
- Active goals (what the user is trying to accomplish)
- Unresolved questions (things Jarvis needs to ask or clarify)
- Recent context window (last 5 messages per device)
- Pending actions (queued but not yet executed)
- Cross-device pending tasks (set on one device, triggered on another)

```python
class WorkingMemory:
    # Per-device state
    device_contexts: dict[str, DeviceContext]  # keyed by device_id

    # Global state
    active_goals: list[Goal]
    paused_goals: list[Goal]
    cross_device_tasks: list[PendingTask]      # "do X when Y agent connects"
    focus_entity: str | None

class DeviceContext:
    device_id: str
    context_window: list[Message]              # Last 5 messages on this device
    current_topic: str
    unresolved: list[str]
    pending_actions: list[Action]
```

**Behavior:**
- Hard cap: 7 active items per device (like human cognitive load). Overflow pushes to short-term.
- Cross-device tasks persist until triggered or explicitly cancelled.
- When user switches devices, working memory for the previous device is preserved (not cleared).

---

### Layer 2: Short-Term Memory (The Recent Mind)

**What:** Recent events from the last 30 minutes across ALL devices.
**Storage:** Redis (production) or in-memory (local dev). Auto-pruned. Survives brain process restarts in production (Redis persists).

**Tracks:**
- Last 20 messages per device (user + Jarvis)
- Recent apps opened/closed (from device agents)
- Recent commands executed (across all devices)
- Recent corrections ("Actually use Firefox instead")
- Active device list (which agents are online right now)

**Behavior:**
- Corrections propagate immediately: if user corrects on phone, desktop agent reflects it next interaction
- When buffer exceeds limits, oldest items get summarized by consolidation and pushed to episodic memory
- Crash recovery: brain periodically writes short-term state to `brain/short_term_recovery.json`

---

### Layer 3: Long-Term Memory (The Knowledge Brain)

**What:** Persistent facts about the user. Personality-level recall. Survives restarts.
**Storage:** PostgreSQL (`knowledge` table) on the cloud server. SQLite in local dev.

**Schema:**
```sql
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    category TEXT NOT NULL,         -- preference, habit, personal, correction, style, device_specific
    importance REAL DEFAULT 0.5,
    confidence REAL DEFAULT 0.8,
    access_count INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_accessed TIMESTAMP,
    source_device TEXT,             -- Which device this was learned from
    source_session TEXT,
    decay_score REAL DEFAULT 1.0,
    tags TEXT,                      -- JSON array for graph linking
    previous_values TEXT            -- JSON: history of contradictions resolved
);
```

**Examples:**
- "User prefers Chrome over Edge" (category: preference, confidence: 0.95)
- "User works late, usually 10pm-2am" (category: habit, confidence: 0.8)
- "User's main project folder is ~/Projects/acme on Windows" (category: device_specific)
- "User prefers short responses" (category: style, confidence: 0.9)

**Behavior:**
- Auto-extraction from conversations (LLM-powered fact extraction)
- Confidence increases with repetition, decreases with contradictions
- Decay: unused memories (30+ days) lose decay_score. Below 0.1 = archived to `archive` table (same DB, separate table)
- Contradiction resolution: new info updates old entries. Old value kept in `previous_values` for context.

---

### Layer 4: Associative Memory (The Connection Web)

**What:** Concepts linked by meaning and co-occurrence. When you think "design," your brain activates Photoshop, Figma, Behance, portfolio, client work. Jarvis does the same.
**Storage:** NetworkX graph, persisted to `brain/associations.graphml`
**This is NOT keyword matching. This is concept association.**

**Node types:** `app`, `person`, `project`, `topic`, `action`, `location`, `time`, `device`

**Edge properties:**
```python
{
    "weight": 0.85,           # Strength (0-1), increases with co-occurrence
    "co_occurrences": 12,
    "last_seen": "...",
    "context": "work"         # In what context they're linked
}
```

**Example:**
```
User: "Open my design stuff"
1. Parse "design" as topic node
2. Traverse graph from "design":
   - Photoshop (0.92) + linked to "windows" device
   - Figma (0.78) + linked to "browser"
   - ~/Projects/portfolio (0.55) + linked to "windows" device
3. Route to Windows agent: open Photoshop, open Figma in browser
4. Ask: "Want me to open your portfolio folder too?"
```

**Cross-device associations:**
- Nodes can be linked to specific devices: "Xcode" is associated with "macOS agent"
- "Open my dev environment" on a Mac triggers different apps than on Windows (VS Code vs Xcode)
- The graph knows which apps exist on which device

---

### Layer 5: Episodic Memory (Experiences)

**What:** Specific events Jarvis has lived through. Autobiographical memory.
**Storage:** PostgreSQL `episodes` table (SQLite in local dev)

**Schema:**
```sql
CREATE TABLE episodes (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,       -- task, error, workflow, conversation, decision
    title TEXT,
    description TEXT,
    actions TEXT,                   -- JSON array of actions taken
    outcome TEXT,                   -- success, failure, partial, cancelled
    duration_seconds INTEGER,
    timestamp TIMESTAMP,
    day_of_week TEXT,
    time_of_day TEXT,               -- morning, afternoon, evening, night
    device TEXT,                    -- Which device this happened on
    context TEXT,
    learned TEXT,                   -- What Jarvis learned
    importance REAL DEFAULT 0.5,
    linked_episode_ids TEXT         -- JSON array of related episodes
);
```

**Cross-device behavior:**
- Episodes track which device they occurred on
- "Continue what we did yesterday" searches all devices' episodes
- Multi-device episodes are linked: "Started investor deck on phone (notes), continued on PC (Canva)"

---

### Layer 6: Procedural Memory (Learned Routines)

**What:** Repeated action sequences Jarvis learned from observation. Muscle memory.
**Storage:** PostgreSQL `procedures` table (SQLite in local dev)

**Schema:**
```sql
CREATE TABLE procedures (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    trigger_description TEXT,
    steps TEXT NOT NULL,               -- JSON: ordered actions with device targets
    times_executed INTEGER DEFAULT 0,
    times_detected INTEGER DEFAULT 0,
    detection_threshold INTEGER DEFAULT 3,
    status TEXT DEFAULT 'suggested',   -- suggested, confirmed, active, disabled
    created_at TIMESTAMP,
    last_executed TIMESTAMP,
    success_rate REAL DEFAULT 1.0,
    trigger_type TEXT,                 -- verbal, time_based, context_based, device_event, manual
    trigger_conditions TEXT,           -- JSON: time, day, device, preceding actions
    target_devices TEXT                -- JSON: which devices this routine runs on
);
```

**Cross-device routines:**
```json
{
    "name": "morning_routine",
    "steps": [
        {"device": "windows", "action": "open_app", "target": "Chrome"},
        {"device": "windows", "action": "open_app", "target": "Slack"},
        {"device": "windows", "action": "open_app", "target": "VS Code"},
        {"device": "android", "action": "notification", "message": "Morning routine started on PC"}
    ],
    "trigger_type": "verbal",
    "trigger_conditions": {"phrase": "morning setup"}
}
```

**Behavior:**
1. **Detection:** Jarvis notices repeated patterns across 3+ occurrences
2. **Suggestion:** "You've done this 3 mornings in a row. Want me to save it as a routine?"
3. **Confirmation:** User approves. Procedure becomes `active`.
4. **Execution:** "Morning. Run the usual?" -- one word triggers the full sequence across devices.
5. **Evolution:** If the user modifies the sequence, Jarvis asks to update the routine.

---

### Layer 7: Personality Memory (Conversational Continuity)

**What:** How the user likes to interact. Communication style, tone, patterns.
**Storage:** JSON file (`brain/personality.json`)

```json
{
    "tone_preference": "direct",
    "verbosity": "concise",
    "humor": true,
    "formality": "casual",
    "preferred_response_length": "short",
    "frustration_indicators": ["repeating commands", "saying 'just do it'"],
    "interaction_patterns": {
        "morning": "brief, wants efficiency",
        "evening": "more relaxed, open to chat",
        "when_debugging": "facts only, no filler"
    },
    "corrections_history": [
        {"what": "stop saying 'certainly'", "when": "2026-01-15"},
        {"what": "don't explain, just do it", "when": "2026-02-03"}
    ],
    "per_device_style": {
        "phone": "extra concise, user is usually on the go",
        "desktop": "normal length, user has full attention"
    }
}
```

**Per-device adaptation:** Responses on mobile are shorter by default. Desktop gets more detail. This is automatic based on which agent is talking.

---

### Layer 8: Semantic Memory (Vector Search)

**What:** Meaning-based memory using embeddings. Connects to everything else.
**Storage:** ChromaDB (`brain/semantic/`)

**What gets embedded:**
- Conversation summaries
- Episode narratives
- Long-term knowledge entries
- Procedure descriptions

**Deduplication:** Before embedding, check cosine similarity > 0.92 against existing entries. Update instead of duplicate.

---

### Layer 9: Memory Consolidation (The Sleep Process)

**What:** Background process that mimics brain consolidation. Processes raw experiences into structured knowledge.

**Schedule:**
- After every session ends (immediate)
- Every 6 hours (deep consolidation)
- On brain server startup (catch-up)

**What it does:**
1. **Summarize sessions** across all devices into 2-3 sentence summaries
2. **Extract facts** from conversations using LLM
3. **Detect patterns** in episodic memory for procedural candidates
4. **Strengthen associations** between co-occurring concepts
5. **Decay** old unused memories
6. **Deduplicate** similar knowledge entries
7. **Resolve contradictions** (keep newest, archive old with reference)
8. **Re-score importance** using: `0.3*frequency + 0.3*recency + 0.2*task_relevance + 0.2*user_emphasis`

---

### Layer 10: Brain Retrieval System (Think Before Speaking)

Before EVERY response, the brain runs this pipeline:

```
1. Agent sends user input + device context
2. Parse intent + entities
3. Check working memory (follow-up? active goal?)
4. Check short-term (recent context across all devices)
5. Search long-term knowledge (relevant facts)
6. Search semantic memory (similar past discussions)
7. Activate association graph (linked concepts)
8. Search episodic memory (past experiences)
9. Check procedural memory (learned routine match?)
10. Load personality profile (how to respond + device-specific style)
11. Rank all retrieved memories by relevance + importance
12. Select top N (max_context_memories, default 10)
13. Build system prompt with context
14. Call Claude API
15. Parse response: text + actions + facts
16. Route actions to correct device agent(s)
17. Update memories with what happened
```

---

### Memory Privacy and Control

- **View:** `jarvis show memories` / `jarvis what do you know about me?`
- **Edit:** `jarvis update memory <id> "new content"`
- **Delete:** `jarvis forget <query>` (fuzzy match, with confirmation)
- **Wipe:** `jarvis reset brain` (double confirmation)
- **Pause:** `jarvis stop remembering` (session-only mode)
- **Export:** `jarvis export brain` (full JSON dump)
- **Import:** `jarvis import brain <path>`

## COMMUNICATION PROTOCOL

### Brain <-> Agent Protocol

Agents communicate with the brain over WebSocket (primary) with REST fallback.

**WebSocket events (Agent -> Brain):**
```json
{"event": "agent_connect", "device_id": "windows-main", "platform": "windows", "capabilities": ["os_control", "voice", "apps", "files"]}
{"event": "user_input", "device_id": "windows-main", "text": "Open Chrome", "audio_duration": 1.2}
{"event": "action_result", "device_id": "windows-main", "action_id": "abc123", "status": "success", "details": "Chrome opened"}
{"event": "context_update", "device_id": "windows-main", "active_app": "VS Code", "active_file": "main.py"}
{"event": "agent_disconnect", "device_id": "windows-main"}
```

**WebSocket events (Brain -> Agent):**
```json
{"event": "response", "text": "Opening Chrome for you.", "tts": true}
{"event": "execute_action", "action_id": "abc123", "type": "open_app", "target": "chrome"}
{"event": "execute_workflow", "procedure_id": "morning_routine", "steps": [...]}
{"event": "request_context", "what": "active_window"}
{"event": "notification", "message": "Your PC task is ready", "priority": "normal"}
```

**REST API fallback (for mobile agents with spotty connections):**
```
POST /api/v1/input          # Send user input
GET  /api/v1/response/{id}  # Poll for response
POST /api/v1/action-result  # Report action completion
GET  /api/v1/context        # Get current brain context
GET  /api/v1/memory         # Query memories
POST /api/v1/agent/register # Register a new device agent
GET  /api/v1/agent/status   # Check which agents are online
```

**Authentication:**
- Each agent gets a JWT token on first registration
- Token is stored locally on the device
- Brain validates token on every request
- Tokens can be revoked from the brain's admin CLI

**Network:**
- Brain runs on a cloud VPS, accessible from anywhere over the internet
- All traffic encrypted via TLS (Nginx terminates SSL, Let's Encrypt certs)
- WebSocket connections use `wss://` (encrypted), REST uses `https://`
- Nginx handles rate limiting, connection limits, and request size limits
- Optional: restrict access to specific IPs via Nginx allowlist or Cloudflare Access

## TASK ORCHESTRATION ENGINE

For complex multi-step, multi-device requests.

**How it works:**
1. User says: "Prepare my presentation for tomorrow's meeting"
2. Brain breaks it down into sub-tasks:
   - Find the latest version of the presentation (search files on Windows agent)
   - Check calendar for meeting details (if calendar plugin is installed)
   - Open the file in the appropriate app
   - Set a reminder for 30 minutes before
3. Brain dispatches sub-tasks to the right agents
4. Tracks progress, handles failures, reports status

**Task schema:**
```python
class Task:
    id: str
    parent_id: str | None          # For sub-tasks
    description: str
    status: str                    # pending, dispatched, in_progress, completed, failed
    target_device: str | None      # None = brain decides
    actions: list[Action]
    dependencies: list[str]        # Task IDs that must complete first
    created_at: datetime
    completed_at: datetime | None
    result: str | None
```

## ACTION ENGINE

### What Agents Can Do (by platform)

| Action | Windows | macOS | Linux | iOS | Android |
|--------|---------|-------|-------|-----|---------|
| Open/close apps | Y | Y | Y | Limited | Limited |
| File operations | Y | Y | Y | - | - |
| Browser control | Y | Y | Y | Open URL | Open URL |
| Volume/brightness | Y | Y | Y | - | - |
| Lock/sleep/shutdown | Y | Y | Y | - | - |
| Clipboard | Y | Y | Y | - | - |
| Run terminal commands | Y | Y | Y | - | - |
| Send notifications | Y | Y | Y | Y | Y |
| Set reminders | Y | Y | Y | Y | Y |
| Type text | Y | Y | Y | - | - |
| Screenshot | Y | Y | Y | - | - |

### Brain-Powered Actions
- **Routine recall:** "Do my morning routine" -- procedural memory fires, routes steps to correct devices
- **Contextual inference:** "Open my project" -- episodic + association graph resolves which project, on which device
- **Cross-device routing:** "Play music" -- brain knows Spotify is on Windows, routes there even if asked from phone
- **Predictive:** "It's Monday 9am. Want me to start your work setup?" -- time-based procedural trigger
- **Error recall:** "That thing crashed again" -- episodic memory finds the last fix

### Safety
- Destructive actions require confirmation (configurable per-action in `config/actions.toml`)
- All actions logged in episodic memory
- Per-device permission system: mobile agents have fewer permissions by default

## CONVERSATION ENGINE

### How Jarvis Talks
- Natural, direct, slightly witty. Like a sharp colleague who knows you.
- Adapts using personality memory: serious when troubleshooting, casual when chatting, concise on mobile.
- Uses brain context: "Morning -- want me to start the usual?" not "What can I help you with?"
- Never says "certainly," "of course," "I'd be happy to." Just does it.
- Per-device verbosity: phone = shorter, desktop = normal.

### LLM Integration
- System prompt = Jarvis persona + retrieved brain context + user personality + available actions + active device
- Structured output:
```json
{
    "response": "Opening Chrome for you.",
    "actions": [{"type": "open_app", "target": "chrome", "device": "windows-main"}],
    "facts_extracted": [{"content": "user wants Chrome", "category": "preference", "confidence": 0.7}],
    "associations": [["morning", "chrome"]],
    "tone": "casual"
}
```

## VOICE ENGINE

STT and TTS run on-device (on the agents), not on the brain server. This keeps voice latency low.

### Desktop Agents (Windows/macOS/Linux)
| Component | Tech |
|-----------|------|
| STT | faster-whisper (local, no network) |
| TTS (local) | Piper (fast, free) |
| TTS (cloud) | ElevenLabs (opt-in, brain manages API key) |
| Wake Word | Porcupine (always-on, low CPU) |

### Mobile Agents
| Component | Tech |
|-----------|------|
| STT | Native OS API (iOS Speech / Android SpeechRecognizer) |
| TTS | Native OS API (iOS AVSpeech / Android TTS) |
| Wake Word | Push-to-talk button (always-on wake word drains mobile battery) |

## PROJECT STRUCTURE

```
jarvis-os/
  brain/                              # ── CENTRAL BRAIN SERVER ──
    src/
      api/
        server.py                     # FastAPI app, WebSocket + REST endpoints
        routes/
          input.py                    # User input endpoint
          memory.py                   # Memory query/edit endpoints
          agents.py                   # Agent registration, status, commands
          tasks.py                    # Task orchestration endpoints
          admin.py                    # Brain admin (view state, force consolidation)
          health.py                   # Health check endpoint for monitoring
        websocket/
          handler.py                  # WebSocket connection manager
          events.py                   # Event dispatcher (input, action_result, context)
        auth/
          jwt.py                      # Agent JWT auth
          permissions.py              # Per-device permission checks
        middleware/
          rate_limit.py               # Per-agent rate limiting (via Redis)
          logging.py                  # Request/response logging
      cognitive/
        manager.py                    # Brain orchestrator -- routes to all layers
        working_memory.py             # Layer 1: conscious mind (Redis-backed)
        short_term.py                 # Layer 2: recent events (Redis-backed)
        long_term.py                  # Layer 3: knowledge DB (PostgreSQL)
        associations.py               # Layer 4: concept graph (NetworkX)
        episodic.py                   # Layer 5: experiences (PostgreSQL)
        procedural.py                 # Layer 6: learned routines (PostgreSQL)
        personality.py                # Layer 7: user style profile (JSON on disk)
        semantic.py                   # Layer 8: vector search (ChromaDB)
        consolidation.py              # Layer 9: background "sleep" process
        retrieval.py                  # Layer 10: think-before-speaking pipeline
        extractor.py                  # LLM-powered fact extraction
        decay.py                      # Importance scoring + decay
        models.py                     # Data classes: Memory, Episode, Procedure, Goal, Task
      conversation/
        chat.py                       # LLM calls, prompt assembly, response parsing
        persona.py                    # Jarvis personality rules
        intent.py                     # Intent detection, entity extraction
        prompt_builder.py             # Builds system prompt with brain context
      orchestration/
        task_manager.py               # Multi-step task breakdown and tracking
        device_router.py              # Routes actions to the correct agent
        workflow_executor.py          # Executes procedural routines across devices
      db/
        database.py                   # SQLAlchemy engine + session factory
        repositories.py               # Repository pattern: KnowledgeRepo, EpisodeRepo, ProcedureRepo
        migrations/                   # Alembic migrations
      redis_client.py                 # Redis connection + helpers (with in-memory fallback for dev)
      config.py                       # Config loader (TOML)
      logger.py                       # Structured logging
      scheduler.py                    # APScheduler for consolidation, decay, routine triggers
    data/                             # Brain data on disk (auto-created at runtime)
      associations.graphml            # NetworkX graph persisted to disk
      personality.json                # User interaction profile
      semantic/                       # ChromaDB storage
      summaries/                      # Session summaries (JSON)
      backups/                        # Local backup staging directory
    config/
      config.toml                     # Brain configuration
      config.dev.toml                 # Local dev overrides (SQLite, no Redis, no TLS)
      persona.toml                    # Jarvis personality defaults
      actions.toml                    # Allowed/blocked actions per device
    tests/
      test_cognitive/
        test_working_memory.py
        test_long_term.py
        test_associations.py
        test_episodic.py
        test_procedural.py
        test_consolidation.py
        test_retrieval.py
      test_api.py
      test_orchestration.py
      conftest.py                     # Shared fixtures: test DB, mock Redis, test client
    requirements.txt
    Dockerfile                        # Brain container image
    alembic.ini                       # Alembic migration config

  infra/                              # ── CLOUD INFRASTRUCTURE ──
    docker-compose.yml                # Full stack: brain + PostgreSQL + Redis + Nginx
    docker-compose.dev.yml            # Dev overrides (ports exposed, debug mode)
    nginx/
      jarvis.conf                     # Nginx site config: TLS, WebSocket upgrade, proxy_pass
      ssl/                            # Let's Encrypt certs (auto-generated, gitignored)
    scripts/
      setup-server.sh                 # First-time VPS setup: install Docker, create user, firewall
      deploy.sh                       # Pull latest, rebuild, restart containers
      backup.sh                       # pg_dump + rsync to backup location
      restore.sh                      # Restore from backup
      renew-certs.sh                  # Let's Encrypt cert renewal
    .env.example                      # Template for server environment variables

  agents/                             # ── DEVICE AGENTS ──
    shared/                           # Shared agent code (Python)
      base_agent.py                   # Abstract base: connect, send, receive, execute
      connection.py                   # WebSocket client + REST fallback
      voice.py                        # STT + TTS abstraction
      models.py                       # Shared data models

    windows/                          # Windows Agent (PRIMARY)
      agent.py                        # Main entry point
      actions/
        apps.py                       # Open/close/switch applications
        files.py                      # File operations
        system.py                     # Volume, brightness, lock, shutdown
        browser.py                    # Browser automation
        terminal.py                   # PowerShell/CMD execution
        clipboard.py                  # Clipboard read/write
      voice/
        listener.py                   # Mic capture + wake word
        stt.py                        # faster-whisper
        tts.py                        # Piper / ElevenLabs
      ui/
        tray.py                       # System tray icon
        overlay.py                    # Optional floating overlay
      config.toml
      requirements.txt

    macos/                            # macOS Agent
      agent.py
      actions/
        apps.py                       # osascript, pyobjc
        files.py
        system.py                     # brightness, volume via osascript
        terminal.py
      voice/
        listener.py
        stt.py
        tts.py
      config.toml
      requirements.txt

    linux/                            # Linux Agent
      agent.py
      actions/
        apps.py                       # xdg-open, wmctrl
        files.py
        system.py                     # amixer, xrandr, systemctl
        terminal.py
      voice/
        listener.py
        stt.py
        tts.py
      config.toml
      requirements.txt

    mobile/                           # Mobile Agents
      ios/                            # Swift / Xcode project
        JarvisAgent/
          AppDelegate.swift
          JarvisClient.swift          # WebSocket + REST connection to brain
          VoiceManager.swift          # Native STT + TTS
          NotificationManager.swift
          Views/
            MainView.swift            # Chat-style UI + push-to-talk
            SettingsView.swift
        JarvisAgent.xcodeproj/

      android/                        # Kotlin / Android Studio project
        app/
          src/main/
            java/.../jarvis/
              MainActivity.kt
              JarvisClient.kt         # WebSocket + REST connection
              VoiceManager.kt         # Native STT + TTS
              NotificationManager.kt
            res/
              layout/
                activity_main.xml     # Chat UI + push-to-talk

  plugins/                            # Optional extensions
    spotify/                          # Spotify control
    calendar/                         # Calendar integration
    email/                            # Email check/send
    smart_home/                       # Home automation (Hue, etc.)
    screenshot_reader/                # OCR + screen understanding

  docs/
    architecture.md                   # System design overview
    setup.md                          # Installation guide
    protocol.md                       # Agent <-> Brain communication spec

  docker-compose.yml                  # Optional: brain + Redis + Postgres
  README.md
```

## CONFIGURATION

### Brain Config -- Production (`brain/config/config.toml`)
```toml
[general]
name = "Jarvis"
language = "en"
debug = false

[server]
host = "0.0.0.0"                   # Nginx sits in front, so 0.0.0.0 is fine
port = 8400
allowed_origins = ["*"]            # Lock down to your domains in production
jwt_secret_env = "JARVIS_JWT_SECRET"

[llm]
provider = "anthropic"
model = "claude-sonnet-4-20250514"
api_key_env = "ANTHROPIC_API_KEY"
fallback_provider = "openai"
fallback_model = "gpt-4o"
temperature = 0.7
max_tokens = 1024

[brain]
enabled = true
auto_extract = true
ask_before_storing = false
decay_enabled = true
decay_threshold_days = 30
consolidation_interval_hours = 6
max_context_memories = 10
association_decay_days = 60
procedure_detection_threshold = 3
working_memory_capacity = 7

[database]
type = "postgresql"
url_env = "DATABASE_URL"           # e.g. postgresql://jarvis:password@localhost:5432/jarvis

[redis]
enabled = true
url_env = "REDIS_URL"              # e.g. redis://localhost:6379/0
```

### Brain Config -- Local Dev (`brain/config/config.dev.toml`)
```toml
[general]
debug = true

[database]
type = "sqlite"
sqlite_path = "data/knowledge.db"

[redis]
enabled = false                    # Falls back to in-memory dicts
```

### Agent Config (per-device, e.g. `agents/windows/config.toml`)
```toml
[agent]
device_id = "windows-main"
device_name = "Desktop PC"
platform = "windows"

[brain]
url = "wss://jarvis.yourdomain.com/ws"          # Cloud brain, encrypted
rest_url = "https://jarvis.yourdomain.com/api/v1"
token_env = "JARVIS_AGENT_TOKEN"

[voice]
enabled = true
wake_word = "jarvis"
stt_model = "base.en"
tts_engine = "piper"
tts_voice = "en_US-lessac-medium"
input_device = "default"
output_device = "default"
silence_threshold = 500

[ui]
tray_icon = true
overlay = false
```

### Server Environment Variables (`.env` on the VPS)
```bash
# Database
DATABASE_URL=postgresql://jarvis:your_secure_password@postgres:5432/jarvis
REDIS_URL=redis://redis:6379/0

# Auth
JARVIS_JWT_SECRET=your_long_random_secret_here

# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...            # Optional fallback

# TTS (optional cloud)
ELEVENLABS_API_KEY=...           # Only if cloud TTS is enabled

# Server
DOMAIN=jarvis.yourdomain.com
LETSENCRYPT_EMAIL=you@email.com
```

## ENVIRONMENT

### Cloud Server (Brain)
- **OS:** Debian 12 or Ubuntu 24.04
- **Runtime:** Python 3.12+ inside Docker container
- **Database:** PostgreSQL 16 (Docker container)
- **Cache:** Redis 7 (Docker container)
- **Proxy:** Nginx (Docker container or host-installed)
- **SSL:** Let's Encrypt via certbot (auto-renewal cron)
- **Firewall:** UFW -- ports 22 (SSH), 80 (HTTP redirect), 443 (HTTPS/WSS) only
- **Access:** SSH key auth, root disabled
- **Domain:** Point a subdomain (e.g., `jarvis.yourdomain.com`) to the VPS IP

### Local Dev (Brain)
- **Python 3.12+** with venv
- **SQLite** instead of PostgreSQL (auto-detected from config)
- **No Redis** (in-memory fallback)
- **No Docker required** for dev
- **No Nginx** (FastAPI serves directly on localhost:8400)

### Device Agents
- **Desktop agents:** Python 3.12+, run on user's machines
- **Mobile agents:** Native apps (Swift for iOS, Kotlin for Android). Sideloaded or TestFlight.
- **All agents connect to the cloud brain** via `wss://` and `https://`
- **API keys:** Only the brain server has LLM API keys. Agents never need them.

## COMMANDS

```bash
# ── Local Dev (Brain on your machine) ──
cd brain
python -m venv venv
venv/Scripts/activate              # Windows: Scripts, macOS/Linux: bin
pip install -r requirements.txt

python -m src.api.server                        # Start brain (SQLite, no Redis)
python -m src.api.server --config config/config.dev.toml
python -m src.cognitive.manager --show           # View all memories
python -m src.cognitive.manager --show-graph     # Association graph stats
python -m src.cognitive.manager --show-routines  # Learned routines
python -m src.cognitive.manager --consolidate    # Force consolidation
python -m src.cognitive.manager --export         # Full brain export
python -m src.cognitive.manager --reset          # Wipe (double confirmation)

# ── Production Deploy (Cloud VPS) ──
ssh user@your-vps-ip
cd /opt/jarvis
bash infra/scripts/setup-server.sh              # First time: installs Docker, firewall, etc.
cp infra/.env.example .env                      # Fill in your API keys and secrets
docker compose -f infra/docker-compose.yml up -d  # Start brain + Postgres + Redis + Nginx
docker compose logs -f brain                     # Watch brain logs

# Deploy updates:
bash infra/scripts/deploy.sh                    # Pull, rebuild, restart

# Backups:
bash infra/scripts/backup.sh                    # Manual pg_dump + file backup
# Cron runs this daily automatically (setup-server.sh configures it)

# ── Windows Agent ──
cd agents/windows
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt

python agent.py --register                       # First-time: register with cloud brain, get JWT
python agent.py                                  # Start with voice
python agent.py --text-only                      # Text mode

# ── macOS / Linux Agent ──
cd agents/macos   # or agents/linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python agent.py --register
python agent.py

# ── Database Migrations ──
cd brain
alembic upgrade head                             # Apply all migrations
alembic revision --autogenerate -m "description" # Create new migration
```

## DEVELOPMENT PRIORITIES

Build in this order. Each phase must work before the next starts.

### Phase 0: Cloud Infrastructure (Week 1) -- NEW, HIGH PRIORITY
Set up the VPS. Install Docker. Write docker-compose.yml with PostgreSQL + Redis + Nginx + brain container. Configure TLS with Let's Encrypt. Write setup, deploy, and backup scripts. Verify the brain server starts and responds to health checks from the internet.

### Phase 1: Brain Core (Week 1-2)
Build the brain server with layers 1-3 (working memory in Redis, short-term in Redis, long-term in PostgreSQL). REST API only (no WebSocket yet). Alembic migrations for the DB schema. Repository pattern for data access. Test with curl/httpie against the cloud server.

### Phase 2: Brain Intelligence (Week 2-3)
Add layers 4-8 (associations, episodic, procedural, personality, semantic). Add the consolidation process (layer 9) and retrieval pipeline (layer 10). Test with a text-based CLI that talks to the cloud brain.

### Phase 3: Windows Agent (Week 3-4)
Build the Windows agent with OS control (apps, files, system). Connect it to the cloud brain via encrypted WebSocket. Verify the brain routes actions to the agent and the agent executes them. Text-only mode first.

### Phase 4: Voice (Week 4-5)
Add STT + TTS + wake word to the Windows agent. End-to-end: speak > transcribe > send to cloud brain > respond > speak.

### Phase 5: Task Orchestration (Week 5-6)
Multi-step task breakdown. Cross-device task routing (even if only one agent is connected). Procedural routines that execute as workflows.

### Phase 6: Additional Agents (Week 6-8)
macOS agent, Linux agent. Same Python base, platform-specific action handlers.

### Phase 7: Mobile (Week 8-10)
iOS and Android agents. Native apps. Push-to-talk, notifications, remote commands. Simpler than desktop agents (no OS control, voice + notifications focus).

### Phase 8: Polish (Ongoing)
Plugins, offline mode, screen understanding, predictive suggestions. UI improvements. Stability. Monitoring and alerting for the cloud server.

## OFFLINE MODE

When an agent can't reach the cloud brain (no internet, server down):
- Agent caches the last personality profile and top 20 knowledge entries locally (synced on each connect)
- Agent can still do STT + TTS locally (these never depend on the brain)
- Simple commands (open app, volume, etc.) execute locally without brain
- Complex commands get queued locally and replayed when connection resumes
- No new memories are stored until reconnected (then the queue flushes to brain)
- Agent shows a "disconnected" indicator in the UI (system tray icon change)

## SECURITY

- **TLS everywhere.** All agent-to-brain traffic over `wss://` and `https://`. Nginx terminates TLS with Let's Encrypt certs. No unencrypted traffic.
- **JWT auth** for every agent connection. Tokens issued on registration, stored per-device.
- **Token revocation** via brain admin CLI: `docker exec jarvis-brain python -m src.api.server --revoke-agent <device_id>`
- **Firewall (UFW).** Only ports 22 (SSH), 80 (redirect to 443), 443 (HTTPS/WSS) open. Brain port 8400 is internal only (Nginx proxies to it).
- **Action permissions** per device. Mobile agents can't delete files or run terminal commands by default.
- **Rate limiting.** Nginx rate limits by IP. Redis tracks per-agent request rates. Prevents abuse if a token is compromised.
- **SSH key auth only.** Password auth disabled on the VPS. Root login disabled.
- **No API keys on agents.** LLM keys live only on the cloud server. Agents never see them.
- **Database not exposed.** PostgreSQL and Redis listen on Docker internal network only. Not reachable from the internet.
- **Backups encrypted.** pg_dump backups can optionally be encrypted with GPG before offsite sync.

## AI WRITING RULES

Never use: "Furthermore", "Additionally", "Moreover", "leverage", "utilize", "streamline", "cutting-edge", "delve", "comprehensive", "innovative". No em dashes. Vary sentence length. Be specific. Reference actual data.
