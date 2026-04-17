"""Brain admin CLI. View memories, force consolidation, revoke agents, export/import.
Run via: docker exec jarvis-brain python -m brain.admin <command>
Or locally: PYTHONPATH=. python brain/admin.py <command>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def cmd_status(args: argparse.Namespace) -> None:
    from brain.src.config import load_config
    from brain.src.db.database import init_db, close_db
    from brain.src.redis_client import init_redis, close_redis
    from brain.src.cognitive.manager import BrainManager

    config = load_config()
    await init_db(config.db_url)
    await init_redis(config.redis_url)

    brain = BrainManager()
    status = await brain.get_status()
    print(json.dumps(status, indent=2))

    await close_redis()
    await close_db()


async def cmd_memories(args: argparse.Namespace) -> None:
    from brain.src.config import load_config
    from brain.src.db.database import init_db, close_db
    from brain.src.redis_client import init_redis, close_redis
    from brain.src.cognitive.long_term import LongTermMemory

    config = load_config()
    await init_db(config.db_url)
    await init_redis(config.redis_url)

    ltm = LongTermMemory()
    if args.search:
        memories = await ltm.search(args.search, limit=args.limit)
    else:
        memories = await ltm.get_all(limit=args.limit)

    for m in memories:
        decay_marker = " [decaying]" if m.decay_score < 0.5 else ""
        print(f"  [{m.category.value}] {m.content} (conf:{m.confidence:.2f} imp:{m.importance:.2f}{decay_marker})")
        print(f"    id={m.id} accessed={m.access_count}x")
    print(f"\nTotal: {len(memories)} entries")

    await close_redis()
    await close_db()


async def cmd_consolidate(args: argparse.Namespace) -> None:
    from brain.src.config import load_config
    from brain.src.db.database import init_db, close_db
    from brain.src.redis_client import init_redis, close_redis
    from brain.src.cognitive.manager import BrainManager

    config = load_config()
    await init_db(config.db_url)
    await init_redis(config.redis_url)

    brain = BrainManager()
    print("Running consolidation...")
    stats = await brain.consolidate()
    print(json.dumps(stats, indent=2))

    await close_redis()
    await close_db()


async def cmd_forget(args: argparse.Namespace) -> None:
    from brain.src.config import load_config
    from brain.src.db.database import init_db, close_db
    from brain.src.redis_client import init_redis, close_redis
    from brain.src.cognitive.long_term import LongTermMemory

    config = load_config()
    await init_db(config.db_url)
    await init_redis(config.redis_url)

    ltm = LongTermMemory()
    matches = await ltm.search(args.query, limit=10)

    if not matches:
        print("No matching memories found.")
    else:
        print("Matching memories:")
        for m in matches:
            print(f"  [{m.id[:8]}] {m.content}")

        if not args.force:
            confirm = input(f"\nDelete {len(matches)} memories? [y/N] ").strip().lower()
            if confirm != "y":
                print("Aborted.")
                await close_redis()
                await close_db()
                return

        for m in matches:
            await ltm.forget(m.id)
        print(f"Deleted {len(matches)} memories.")

    await close_redis()
    await close_db()


async def cmd_export(args: argparse.Namespace) -> None:
    from brain.src.config import load_config
    from brain.src.db.database import init_db, close_db
    from brain.src.redis_client import init_redis, close_redis
    from brain.src.cognitive.long_term import LongTermMemory
    from brain.src.cognitive.episodic import EpisodicMemory

    config = load_config()
    await init_db(config.db_url)
    await init_redis(config.redis_url)

    ltm = LongTermMemory()
    episodic = EpisodicMemory()

    knowledge = await ltm.get_all(limit=10000)
    episodes = await episodic.get_recent(limit=1000)

    export_data = {
        "knowledge": [
            {"id": k.id, "content": k.content, "category": k.category.value,
             "importance": k.importance, "confidence": k.confidence, "tags": k.tags}
            for k in knowledge
        ],
        "episodes": [
            {"id": e.id, "title": e.title, "event_type": e.event_type,
             "outcome": e.outcome.value, "device": e.device, "timestamp": e.timestamp.isoformat()}
            for e in episodes
        ],
    }

    output = Path(args.output)
    output.write_text(json.dumps(export_data, indent=2))
    print(f"Exported {len(knowledge)} knowledge + {len(episodes)} episodes to {output}")

    await close_redis()
    await close_db()


async def cmd_revoke(args: argparse.Namespace) -> None:
    print(f"Token revocation for device '{args.device_id}' requires Redis blacklist.")
    print("For now, regenerate the JWT secret in .env to invalidate all tokens,")
    print("then re-register agents.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis Brain Admin CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show brain status")

    mem_parser = sub.add_parser("memories", help="List/search memories")
    mem_parser.add_argument("--search", "-s", help="Search query")
    mem_parser.add_argument("--limit", "-n", type=int, default=50)

    sub.add_parser("consolidate", help="Force memory consolidation")

    forget_parser = sub.add_parser("forget", help="Delete memories matching query")
    forget_parser.add_argument("query", help="Search query for memories to delete")
    forget_parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation")

    export_parser = sub.add_parser("export", help="Export brain to JSON")
    export_parser.add_argument("--output", "-o", default="brain_export.json")

    revoke_parser = sub.add_parser("revoke", help="Revoke agent token")
    revoke_parser.add_argument("device_id", help="Device ID to revoke")

    args = parser.parse_args()

    commands = {
        "status": cmd_status,
        "memories": cmd_memories,
        "consolidate": cmd_consolidate,
        "forget": cmd_forget,
        "export": cmd_export,
        "revoke": cmd_revoke,
    }

    asyncio.run(commands[args.command](args))


if __name__ == "__main__":
    main()
