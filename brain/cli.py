"""Text-based CLI for testing the brain. Connects via REST API."""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx


async def main(brain_url: str, device_id: str) -> None:
    print(f"Jarvis Brain CLI -- connecting to {brain_url}")
    print(f"Device: {device_id}")
    print("Type 'quit' to exit, 'status' for brain status.\n")

    async with httpx.AsyncClient(base_url=brain_url, timeout=30.0) as client:
        # Health check
        try:
            resp = await client.get("/health")
            data = resp.json()
            print(f"Brain v{data.get('version', '?')} -- {data.get('status', '?')} (uptime: {data.get('uptime_seconds', 0)}s)")
            brain_info = data.get("brain", {})
            if brain_info:
                print(f"  Knowledge: {brain_info.get('knowledge_entries', 0)}, Devices: {brain_info.get('active_devices', [])}")
            print()
        except Exception as e:
            print(f"Could not connect to brain: {e}")
            return

        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not text:
                continue
            if text.lower() == "quit":
                print("Bye.")
                break
            if text.lower() == "status":
                resp = await client.get("/health")
                print(f"Status: {resp.json()}\n")
                continue

            try:
                resp = await client.post(
                    "/api/v1/input",
                    json={"device_id": device_id, "text": text},
                )
                data = resp.json()
                ctx = data.get("context", {})

                # Show retrieved context summary
                knowledge = ctx.get("relevant_knowledge", [])
                associations = ctx.get("associations", [])
                routine = ctx.get("matched_routine")

                if knowledge:
                    print(f"  [Brain knows: {', '.join(k['content'][:50] for k in knowledge[:3])}]")
                if associations:
                    print(f"  [Associated: {', '.join(a['name'] for a in associations[:3])}]")
                if routine:
                    print(f"  [Routine matched: {routine['name']}]")

                print(f"Jarvis: (context retrieved, {len(knowledge)} facts, {len(associations)} associations)")
                print()
            except Exception as e:
                print(f"Error: {e}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jarvis Brain CLI")
    parser.add_argument("--url", default="http://localhost:8400", help="Brain server URL")
    parser.add_argument("--device", default="cli-test", help="Device ID")
    args = parser.parse_args()

    asyncio.run(main(args.url, args.device))
