# Rules for AI Coding on Jarvis OS

> Every AI assistant (Claude, GPT, Copilot, or any other) working on this codebase MUST follow these rules. No exceptions. Read this file before writing a single line of code.

---

## 0. TOKEN ECONOMY (READ FIRST -- MOST IMPORTANT RULE)

### Shut up and work.

Every token you spend talking is a token NOT spent coding. Tokens cost money. Context windows are finite. Respect both.

**Response rules:**
- **Do NOT explain what you're about to do.** Just do it.
- **Do NOT summarize what you just did.** The diff speaks for itself.
- **Do NOT list options or ask "would you like me to..."** -- pick the best one and do it. Ask only if genuinely ambiguous.
- **Do NOT narrate your thought process.** No "Let me think about this..." or "First, I'll need to..."
- **Do NOT repeat the user's question back to them.** They know what they asked.
- **Do NOT write long explanations unless the user explicitly asks for one.**
- **Do NOT pad responses with filler.** No "Great question!", "Sure!", "Absolutely!", "Here's what I'll do:"
- **Do NOT list every file you changed at the end.** Save that for `.ai-sessions/current.md`.

**Ideal response patterns:**
- User asks to implement something: Write the code. Say "Done." or nothing.
- User asks to fix a bug: Fix it. Say what was wrong in one sentence.
- User asks a question: Answer in 1-3 sentences. Not a paragraph.
- User asks for a plan: Bullet points. No prose.

**Token budget priorities (in order):**
1. Writing code and tests
2. Reading files to understand context
3. Updating CHANGELOG/TODO/session handoff
4. Communicating with the user (LAST priority -- minimize this)

**What wastes tokens:**
- Restating the task before starting
- Explaining obvious code
- Summarizing after every change
- Asking permission for non-destructive actions
- Showing "here's the plan" before every small task
- Long conversational responses when a one-liner works

**Rule of thumb:** If your text response (not code) is longer than 5 lines, you're probably wasting tokens. Cut it down.

---

## 1. SCOPE AND FOCUS

### This project only
- You are working on **Jarvis OS** and NOTHING else.
- Do NOT read, modify, reference, or interact with files outside the `jarvis/` (or `jarvis-os/`) project directory.
- Do NOT apply patterns, configs, or conventions from other projects the user may have. This project has its own rules.
- If the user mentions another project, that is a SEPARATE context. Do not mix them.
- Do NOT copy code, configs, or structure from other repos unless the user explicitly tells you to.

### Stay in your lane
- Only work on what was asked. Don't wander into other files "while you're at it."
- If you notice something broken in a file you weren't asked to touch, mention it to the user. Don't fix it silently.
- If a task requires changes outside this repo (server config, DNS, external service), tell the user what needs to be done. Don't attempt it.

---

## 2. MANDATORY FILE UPDATES

Every coding session that changes code MUST also update these files:

### CHANGELOG.md
- Add an entry under `[Unreleased]` for every change you make
- Use the correct category: `Added`, `Changed`, `Fixed`, `Removed`, `Security`, `Deprecated`
- One bullet per logical change, not per file
- Be specific: "Implemented Layer 4 associative memory with NetworkX graph" not "updated memory system"
- When a version is released, move `[Unreleased]` items into a versioned section with a date

### TODO.md
- Check off completed items: `- [ ]` becomes `- [x]`
- Add new items if you discover work that needs to be done
- If a task turns out to be unnecessary, remove it with a note in the commit message
- Never leave a phase with all items checked without marking it complete in the header
- Add sub-tasks if an item turns out to be bigger than expected

### CLAUDE.md
- Update if architecture decisions change (new tech, removed service, changed data flow)
- Update if schemas change (new columns, renamed tables, changed data types)
- Update if the project structure changes (new folders, moved files, renamed modules)
- Do NOT update for routine code changes that follow the existing architecture

**Failure to update these files is a bug. Treat it the same as forgetting to write a test.**

---

## 3. GIT RULES (CRITICAL)

### Identity
- **NEVER commit under the AI assistant's name.** No `Co-Authored-By: Claude`, no `Co-Authored-By: GPT`, no AI attribution in commits.
- All commits are made under the **user's git identity** (whatever `git config user.name` and `git config user.email` return). Do not modify git config.
- Do NOT set, change, or override `user.name`, `user.email`, or any git config. Use whatever is already configured.
- The user is the author of all code. The AI is a tool, not a co-author.

### Committing
- Write clear commit messages: `prefix: what changed` (e.g., `feat: implement associative memory with NetworkX`)
- Prefixes: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `infra:`
- One logical change per commit. Don't bundle unrelated changes.
- Never commit broken code. If it doesn't pass `pytest`, don't commit.
- Never commit debug prints, commented-out code blocks, or TODO comments that should be in TODO.md.
- Include the CHANGELOG/TODO update in the same commit as the code change, not in a separate commit.
- Always stage specific files. Never use `git add .` or `git add -A` blindly. Review what's being staged.

### Pushing
- **Always push after committing.** Every commit should be pushed to the remote. Don't leave commits local.
- Push to the correct branch (see branching rules below).
- If push fails (rejected, auth issue), tell the user immediately. Don't silently skip it.
- Never force push (`--force` or `--force-with-lease`) unless the user explicitly asks.

### Branching Strategy (VERSION BRANCHES)

This project uses **version-based branching**. Each major/minor version gets its own branch.

**Branch naming:**
```
main                    # Stable releases only. Protected. Only merge completed versions here.
dev                     # Active development. All daily work happens here.
v0                      # Major version 0 branch (pre-alpha through alpha)
v0.1.0                  # Minor version branch (first feature milestone)
v0.1.1                  # Patch branch (bugfix on v0.1.0)
v0.2.0                  # Next minor version
v1                      # Major version 1 branch (first production release)
v1.0.0                  # Initial v1 release
v1.0.1                  # Patch on v1.0.0
v1.1.0                  # Minor feature update
v2                      # Major version 2 (breaking changes)
```

**Workflow:**
1. **Daily work** happens on `dev` branch
2. When a version milestone is reached (e.g., Phase 1 complete):
   - Create a version branch: `git checkout -b v0.1.0`
   - Update CHANGELOG.md: move `[Unreleased]` to `[0.1.0] - 2026-XX-XX`
   - Tag it: `git tag v0.1.0`
   - Push branch and tag: `git push origin v0.1.0 && git push origin v0.1.0 --tags`
   - Merge into `main` if it's stable
   - Switch back to `dev` for next version's work
3. **Patches** (bugfixes on a released version):
   - Branch off the version: `git checkout -b v0.1.1 v0.1.0`
   - Fix the bug, update CHANGELOG
   - Tag it: `git tag v0.1.1`
   - Cherry-pick the fix back to `dev` if applicable
4. **Major version branches** (`v0`, `v1`, `v2`) are long-lived. They track the latest patch of that major.

**Version milestones (planned):**
| Version | Milestone |
|---------|-----------|
| `v0.1.0` | Brain core (layers 1-3) + cloud infra working |
| `v0.2.0` | Brain intelligence (layers 4-10) complete |
| `v0.3.0` | Conversation engine + Windows agent connected |
| `v0.4.0` | Voice engine working end-to-end |
| `v0.5.0` | Task orchestration + cross-device workflows |
| `v0.6.0` | macOS + Linux agents |
| `v0.7.0` | Mobile agents (iOS + Android) |
| `v1.0.0` | Full system working: brain + agents + voice + memory. Production ready. |

**Rules:**
- NEVER commit directly to `main`. Always merge from a version branch.
- NEVER delete version branches. They are permanent historical records.
- Always create the version branch BEFORE tagging. Tag lives on the branch.
- The `dev` branch is the only place for active, unreleased work.

### What NOT to do with git
- Do NOT create branches for individual features (no `feature/add-memory` style). Use version branches.
- Do NOT rebase published branches. Only rebase local unpushed commits if needed.
- Do NOT squash merge version branches into main. Keep the full history.
- Do NOT amend pushed commits.
- Do NOT use `git reset --hard` on pushed branches.
- Do NOT delete remote branches that have been tagged.

---

## 4. VERSIONING

Follow [Semantic Versioning](https://semver.org/):
- `MAJOR.MINOR.PATCH` (e.g., `0.3.1`)
- **MAJOR:** Breaking changes to the brain API, agent protocol, or data format
- **MINOR:** New features, new memory layers, new agent capabilities
- **PATCH:** Bug fixes, performance improvements, refactors

Current version: `0.0.0` (pre-alpha, nothing built yet)

Rules:
- We stay at `0.x.x` until the brain + one agent is fully functional end-to-end
- `1.0.0` = brain server + Windows agent + voice + memory all working together
- Every version bump gets a CHANGELOG section with a date
- Every version bump gets a git tag AND a version branch
- Version string must be updated in `brain/src/__version__.py` (create this file)

---

## 5. CODE STYLE

### Python
- Python 3.12+ features allowed (type hints, match statements, etc.)
- Use type hints on all function signatures. No untyped public functions.
- Use dataclasses or Pydantic models for data structures. No raw dicts for domain objects.
- Use `async/await` for I/O-bound operations (API calls, DB queries, WebSocket)
- Use `pathlib.Path` for all file paths, never string concatenation
- Imports: stdlib first, then third-party, then local. Separated by blank lines.
- Max line length: 120 characters
- Use f-strings, not `.format()` or `%`
- Docstrings on classes and non-obvious functions only. Skip obvious ones.

### Naming
- Files: `snake_case.py`
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: prefix with `_`

### Error Handling
- Catch specific exceptions, never bare `except:`
- Log errors with context (what was being attempted, what input caused it)
- Brain server must never crash from a single bad request. Catch, log, return error response.
- Agent must never crash from a single failed action. Catch, report to brain, continue.

### Testing
- Tests go in `tests/` mirroring the source structure
- Use `pytest` for all tests
- Test file naming: `test_<module>.py`
- Every cognitive layer must have unit tests
- API endpoints must have integration tests
- Don't mock the database in integration tests. Use a test SQLite DB.
- Run tests before every commit: `pytest tests/`

---

## 6. ARCHITECTURE RULES

### Brain Server
- The brain is the single source of truth for all memory. Agents NEVER store persistent memory.
- All cognitive layers are independent modules. They communicate through the `manager.py` orchestrator.
- No layer should directly import another layer. Go through the manager.
- The brain server must be stateless between HTTP requests. Ephemeral state (working memory, short-term) lives in Redis. Persistent state lives in PostgreSQL/ChromaDB/files.
- API endpoints are thin. Business logic lives in the cognitive and conversation modules, not in route handlers.
- Never expose internal brain state directly in API responses. Always go through a response model.
- Use the repository pattern for all database access. Never write raw SQL in cognitive layer code.

### Agents
- Agents are thin clients. They do NOT contain business logic.
- An agent's job: capture input, send to cloud brain, execute returned actions, report results.
- Voice (STT/TTS) runs on the agent, not the brain. This keeps latency low.
- Agents connect to the cloud brain via `wss://` (encrypted). Never use `ws://` over the internet.
- Every agent action must be reversible or confirmable for destructive operations.
- Agent code must work offline gracefully (cache + queue pattern).

### Database
- PostgreSQL for production (cloud server). SQLite for local development only.
- All SQL through SQLAlchemy ORM, never raw SQL strings.
- Migrations: use Alembic. Never modify the schema by hand. Never run raw DDL in production.
- Every table must have `created_at` and `updated_at` timestamps.
- IDs: use UUIDs (uuid4), not auto-increment integers.
- Repository pattern: `KnowledgeRepo`, `EpisodeRepo`, `ProcedureRepo` abstract the DB engine. Cognitive layers call repositories, never SQLAlchemy directly.
- Redis: use for ephemeral state (working memory, short-term, agent presence, rate limits). Never store persistent data in Redis.

### Communication
- Brain <-> Agent: WebSocket primary (wss://), REST fallback (https://)
- Every WebSocket message must have an `event` field and a `device_id` field
- Every REST request must include the JWT token in the `Authorization` header
- Never trust agent input. Validate everything on the brain side.
- Nginx handles TLS termination. Brain server receives plain HTTP/WS internally.

### Cloud Infrastructure
- All infrastructure config lives in `infra/`. Docker Compose, Nginx configs, deploy scripts.
- Never hardcode IPs, domains, or ports. Use environment variables and config files.
- Never commit `.env` files. Only commit `.env.example` with placeholder values.
- Database credentials, API keys, JWT secrets = environment variables only.
- PostgreSQL and Redis must NOT be exposed to the internet. Docker internal network only.
- Nginx is the only container with ports 80/443 mapped to the host.
- All deploy scripts must be idempotent (safe to run multiple times).
- Backups: daily pg_dump via cron. Script must handle failures gracefully (log, don't crash).
- Let's Encrypt certs auto-renew. Never use self-signed certs in production.

---

## 7. SECURITY RULES

- API keys (Anthropic, OpenAI, ElevenLabs) go in environment variables. NEVER in code, config files, or commits.
- JWT secrets go in environment variables.
- Never log API keys, tokens, or passwords. Not even partially.
- Never commit `.env` files, `*.db` files, `*.json` brain data, or `semantic/` ChromaDB data.
- Agent JWT tokens are device-specific. One compromised device does not compromise others.
- Destructive OS actions (delete files, shutdown, kill process) always require user confirmation.
- Never execute arbitrary shell commands from LLM output without validation against an allowed-actions list.
- Never `eval()` or `exec()` anything from user input or LLM responses.

---

## 8. FILE MANAGEMENT

### What goes in `.gitignore`:
```
# Brain data (runtime generated, never committed)
brain/data/
*.db
*.db-journal
brain/semantic/
brain/personality.json
brain/associations.graphml
brain/short_term_recovery.json
brain/summaries/
brain/backups/

# Environment and secrets
.env
*.env
!.env.example

# Agent device configs (contain URLs and tokens)
agents/*/config.toml

# Python
__pycache__/
*.pyc
*.pyo
venv/
.venv/
*.egg-info/
dist/
build/
.pytest_cache/
.mypy_cache/

# Logs
logs/
*.log

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# SSL certs (auto-generated)
infra/nginx/ssl/
```

### What MUST be committed:
- All source code (`src/`, `agents/`)
- Test files (`tests/`)
- Config templates (`config.toml.example`, `.env.example`)
- Requirements files (`requirements.txt`)
- Documentation (`CLAUDE.md`, `CHANGELOG.md`, `TODO.md`, `RULES.md`, `README.md`)
- Infrastructure (`infra/docker-compose.yml`, `infra/nginx/*.conf`, `infra/scripts/*.sh`)
- Dockerfiles
- Alembic configs and migration files
- AI skills/prompts (`ai-skills/` if applicable)

### Repo organization
- Keep the root clean. Only project-level files at root (`README.md`, `CLAUDE.md`, `CHANGELOG.md`, `TODO.md`, `RULES.md`, `.gitignore`)
- Source code lives under `brain/src/`, `agents/*/`, etc. Never dump code at root.
- One `requirements.txt` per deployable unit (`brain/`, each agent)
- Test files mirror source structure inside `tests/`
- No orphan files. Every file belongs to a module or directory with a clear purpose.

---

## 9. DEPENDENCY RULES

- Pin exact versions in `requirements.txt` (e.g., `fastapi==0.115.0` not `fastapi>=0.100`)
- Minimize dependencies. Don't add a library for something you can write in 20 lines.
- Every new dependency must be justified. "It's popular" is not a justification.
- Separate requirements files per project: `brain/requirements.txt`, `agents/windows/requirements.txt`
- Check for security vulnerabilities before adding a new dependency.

---

## 10. WHAT NOT TO DO

- Do NOT work on files outside this project. Ever.
- Do NOT add features not in CLAUDE.md or TODO.md without discussing first
- Do NOT refactor working code unless the refactor is the task
- Do NOT add "nice to have" abstractions, utility wrappers, or helper classes unless they're used in 3+ places
- Do NOT add comments that restate the code. Only comment on WHY, never WHAT.
- Do NOT create empty placeholder files "for later"
- Do NOT use print() for logging. Use the project logger.
- Do NOT hardcode values that should be in config (ports, paths, model names, thresholds)
- Do NOT ignore type checker warnings. Fix them.
- Do NOT write overly defensive code. Trust internal module boundaries. Validate at system edges (API endpoints, agent input).
- Do NOT add backwards-compatibility shims. This is pre-v1. Break things freely.
- Do NOT commit under an AI identity. All commits belong to the user.
- Do NOT leave uncommitted/unpushed changes at the end of a session. Commit and push everything.

---

## 11. SESSION CONTINUITY (CRITICAL -- READ THIS)

AI agents run out of context, credits, or get disconnected. When that happens, ALL progress in the agent's "head" is lost forever. This is unacceptable. Every AI agent working on this project MUST save its state to disk so the next agent (or the same agent in a new session) can pick up exactly where the last one left off.

### The Handoff Directory

All session state is saved to `.ai-sessions/` in the project root. This folder is the AI's persistent brain between sessions.

```
.ai-sessions/
  current.md              # The active session file (always exists during work)
  history/
    2026-04-17_session1.md
    2026-04-17_session2.md
    2026-04-18_session1.md
```

### When to save (MANDATORY)

1. **At the START of every session:** Read `.ai-sessions/current.md` if it exists. This is the previous agent's handoff. Resume from where they left off.
2. **Every time you complete a significant step:** Update `current.md` with what you just did.
3. **When you sense context is getting long:** Save immediately. Don't wait until you're cut off.
4. **Before ANY large operation** (big refactor, multi-file change): Save first. If it fails halfway, the next agent knows what was attempted.
5. **At the END of every session:** Save final state. This is non-negotiable.
6. **If the user says "save" or "checkpoint":** Save immediately.

### What to save in `current.md`

```markdown
# AI Session State
Last updated: 2026-04-17 23:45

## What I was working on
[Clear description of the current task. What was asked, what's the goal.]

## What I completed
- [x] Implemented working_memory.py with Redis backend
- [x] Added unit tests for working memory
- [x] Updated CHANGELOG.md

## What's in progress (NOT DONE YET)
- [ ] short_term.py -- started, Redis integration half-done. File exists but `flush_to_episodic()` is not implemented yet.
- [ ] manager.py -- not started

## What's next (planned but not started)
- [ ] Wire layers 1-3 into manager.py
- [ ] Set up FastAPI server with health endpoint
- [ ] Deploy to cloud and test

## Key decisions made this session
- Chose to use Redis hashes for working memory instead of simple keys (faster per-device access)
- Decided DeviceContext needs a `last_activity` timestamp for timeout detection

## Problems / blockers
- ChromaDB 0.5.x has a breaking change with the embedding function API. Need to pin 0.4.x or adapt.
- The user's git remote isn't set up yet. Couldn't push.

## Files I modified
- brain/src/cognitive/working_memory.py (CREATED)
- brain/src/cognitive/models.py (MODIFIED -- added DeviceContext class)
- brain/tests/test_cognitive/test_working_memory.py (CREATED)
- CHANGELOG.md (UPDATED)
- TODO.md (UPDATED)

## Current branch
dev

## Notes for the next agent
- The Redis fallback (in-memory dict) is implemented but not tested. Write tests for it.
- User prefers short responses. Don't over-explain.
- User's git name is already configured. Don't touch git config.
```

### Rules for the handoff file

- **Be specific.** "Working on memory" is useless. "Implementing `flush_to_episodic()` in `short_term.py`, line 47, needs to call `EpisodeRepo.create()`" is useful.
- **List every file you touched.** The next agent needs to know what changed.
- **Include the current branch.** The next agent needs to know where to commit.
- **Note blockers.** If something is broken or blocked, say exactly what and why.
- **Note user preferences** you learned during the session (response style, decisions they made).
- **Don't dump code.** The handoff is context, not a code backup. The code is in the files.
- **Keep it under 200 lines.** If it's longer, you're including too much detail. Summarize.

### Session history

When starting a new session, move the existing `current.md` to `history/` with a timestamp:
```
mv .ai-sessions/current.md .ai-sessions/history/2026-04-17_session2.md
```
Then create a fresh `current.md` for the new session. The history is there if you need to look back further.

### Reading previous sessions

At the start of a session, the AI agent MUST:
1. Read `.ai-sessions/current.md` (the last handoff)
2. Briefly scan the last 2-3 files in `.ai-sessions/history/` if the current.md references them
3. Read `TODO.md` to understand overall progress
4. Read `CHANGELOG.md` recent entries to see what changed last
5. Then start working. Don't re-read CLAUDE.md unless the task requires architectural context.

### Emergency save

If you realize you're running low on context or the conversation is getting very long:
1. STOP what you're doing mid-task
2. Save `current.md` immediately with EXACT progress (what line you're on, what's half-done)
3. Tell the user: "I'm saving my progress now. A new session can pick up from here."
4. Commit and push any code changes that are in a working state
5. If code is half-written and broken, note that in `current.md` but do NOT commit broken code

### The `.ai-sessions/` folder

- **IS committed to git.** This is intentional. The handoff files are part of the project.
- **Is NOT in .gitignore.** Repeat: do NOT add this to .gitignore.
- **History files older than 30 days** can be deleted by the user. The AI should not auto-delete them.

---

## 12. CONSISTENCY RULES

### Code consistency
- Follow the patterns already established in the codebase. If existing code uses `async def`, new code uses `async def`. If existing repos use a certain import style, follow it.
- Before writing a new utility function, check if one already exists. Search the codebase.
- If a pattern is used in 2+ places, the third usage should match exactly. Don't invent a new way.
- Config keys, environment variable names, and API response shapes must be consistent across the entire project. If one endpoint returns `{"status": "ok"}`, all endpoints return `{"status": "ok"}`, not `{"success": true}`.

### Naming consistency
- If the codebase calls it "knowledge," don't start calling it "memory" or "facts" in new code. Pick one term per concept and stick with it everywhere.
- Database table names, column names, API field names, and Python class attributes for the same concept must all use the same word. `device_id` everywhere, not `device_id` in the DB and `agent_id` in the API.
- File names must match what they contain. `episodic.py` contains the `EpisodicMemory` class. Don't put episodic logic in `utils.py`.

### Behavioral consistency
- If a feature works a certain way in one context, it must work the same way in every context. If corrections propagate in short-term memory, they propagate in long-term memory too.
- Error handling patterns must be the same across all modules. Don't use exceptions in one module and return codes in another.
- Logging format must be identical across all modules. Same structure, same severity levels, same context fields.

### Cross-session consistency
- Read the previous session's handoff before starting. Don't contradict decisions made in previous sessions unless the user explicitly asks to change direction.
- Don't rename things that a previous agent named unless there's a concrete reason (not just preference).
- Don't restructure files or directories that a previous agent created unless the task specifically calls for it.
- If a previous session left something half-done, finish it the way it was started. Don't rewrite it from scratch unless it's broken.

---

## 13. WHEN YOU'RE STUCK

1. Read `.ai-sessions/current.md` first -- a previous agent may have solved this already
2. Read the relevant section of CLAUDE.md
3. Check TODO.md for context on what's been done and what's planned
4. Check CHANGELOG.md for recent changes that might affect your work
5. Check `.ai-sessions/history/` for notes from older sessions
6. If the architecture needs to change, update CLAUDE.md BEFORE writing code
7. If you discover a new task, add it to TODO.md BEFORE starting it
8. If something is ambiguous, ask the user. Don't guess on architectural decisions.

---

## 14. SESSION COMPLETION CHECKLIST

Before finishing any coding session, verify ALL of these:

### Code Quality
- [ ] Code works (tested manually or with pytest)
- [ ] No API keys, tokens, or secrets in the code
- [ ] No raw dicts where a dataclass/model should be used
- [ ] No bare `except:` blocks
- [ ] No `print()` statements (use logger)
- [ ] No hardcoded config values
- [ ] Type hints on all public function signatures
- [ ] Tests written for new functionality
- [ ] Naming and patterns consistent with existing code

### Documentation
- [ ] CHANGELOG.md updated with what changed
- [ ] TODO.md updated (items checked off, new items added)
- [ ] CLAUDE.md updated if architecture changed

### Git
- [ ] Commit message follows the format: `prefix: description`
- [ ] Committed under the user's git identity (NOT an AI name)
- [ ] Pushed to the correct branch
- [ ] No uncommitted or unpushed changes left behind
- [ ] No files outside this project were modified

### Session Continuity
- [ ] `.ai-sessions/current.md` saved with full session state
- [ ] Previous `current.md` moved to `history/` (if this is a new session)
- [ ] All in-progress work described clearly enough for the next agent to continue
- [ ] Blockers and problems documented
- [ ] Files modified listed in the handoff
