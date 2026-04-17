# Jarvis OS

A private, distributed AI assistant ecosystem. One brain, multiple bodies.

## What is this?

A central AI brain runs on a cloud server. Lightweight agents run on every device you own (Windows, macOS, Linux, mobile). They share memory, context, and tasks in real time. Start something on your phone, finish it on your PC.

## Architecture

```
            Cloud Brain (FastAPI + PostgreSQL + Redis)
                        |
               wss:// encrypted
                        |
    ┌──────────┬────────┼────────┬──────────┐
    Windows    macOS    Linux    iOS     Android
    Agent      Agent    Agent   Agent    Agent
```

## Quick Start

### Brain (local dev)
```bash
cd brain
python -m venv venv
venv/Scripts/activate          # Windows
pip install -r requirements.txt

# Start brain server (SQLite, no Redis, port 8400)
PYTHONPATH=.. python -m brain.src.api.server
```

### Windows Agent
```bash
cd agents/windows
pip install -r requirements.txt

# Register with brain
python agent.py --register

# Text mode
python agent.py --text-only

# Voice mode (requires faster-whisper, pyaudio)
python agent.py
```

### Brain CLI
```bash
python brain/cli.py --url http://localhost:8400
```

### Admin CLI
```bash
python brain/admin.py status
python brain/admin.py memories --search "chrome"
python brain/admin.py consolidate
python brain/admin.py export --output brain.json
python brain/admin.py forget "old fact" --force
```

### Tests
```bash
PYTHONPATH=. python -m pytest brain/tests/ -v
```

## Production Deploy
```bash
# On VPS (Debian 12)
sudo bash infra/scripts/setup-server.sh
cp infra/.env.example .env  # fill in secrets
docker compose -f infra/docker-compose.yml up -d
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Brain API | FastAPI + WebSockets |
| Database | PostgreSQL 16 (prod) / SQLite (dev) |
| Cache | Redis 7 |
| LLM | Claude API (primary) / OpenAI (fallback) |
| Vector DB | ChromaDB |
| Graph | NetworkX |
| Voice STT | faster-whisper |
| Voice TTS | Piper (local) / ElevenLabs (cloud) |
| Wake Word | Porcupine |
| Agents | Python (desktop) / Swift & Kotlin (mobile) |

## Cognitive Architecture

10-layer memory system:

1. **Working Memory** -- active context per device (Redis)
2. **Short-Term Memory** -- recent 20 messages (Redis)
3. **Long-Term Memory** -- persistent knowledge (PostgreSQL)
4. **Associative Memory** -- concept graph (NetworkX)
5. **Episodic Memory** -- event history (PostgreSQL)
6. **Procedural Memory** -- learned routines (PostgreSQL)
7. **Personality Memory** -- interaction style (JSON)
8. **Semantic Memory** -- vector search (ChromaDB)
9. **Consolidation** -- background memory maintenance
10. **Retrieval Pipeline** -- context assembly for LLM

## Project Structure

```
jarvis/
  brain/           Central brain server
    src/
      api/         FastAPI server, WebSocket, auth, middleware
      cognitive/   10 memory layers + extractor + decay + predictions
      conversation/ LLM integration, intent, persona
      orchestration/ Task manager, device router, workflows
      db/          Database + repositories + migrations
    tests/         72 tests
    config/        TOML configs
    admin.py       Admin CLI
    cli.py         Test CLI
  agents/
    shared/        Base agent, connection, offline cache
    windows/       Windows agent + actions + voice + UI
    macos/         macOS agent + actions
    linux/         Linux agent + actions
  plugins/         Plugin system + Spotify reference
  infra/           Docker, Nginx, deploy scripts
```
