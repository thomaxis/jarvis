"""Linux Agent -- connects to cloud brain and executes Linux-specific actions."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

import tomli

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from agents.shared.base_agent import BaseAgent
from agents.shared.models import ActionRequest, ActionResult
from agents.linux.actions import apps, files, system, terminal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("jarvis.linux")


class LinuxAgent(BaseAgent):
    def get_capabilities(self) -> list[str]:
        return ["os_control", "apps", "files", "browser", "terminal", "system"]

    async def execute_action(self, action: ActionRequest) -> ActionResult:
        action_type = action.type
        target = action.target
        params = action.params
        success, details = False, "Unknown action"

        if action_type == "open_app":
            success, details = apps.open_app(target)
        elif action_type == "close_app":
            success, details = apps.close_app(target)
        elif action_type == "open_url":
            try:
                subprocess.Popen(["xdg-open", target if target.startswith("http") else f"https://{target}"],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                success, details = True, f"Opened {target}"
            except Exception as e:
                success, details = False, str(e)
        elif action_type == "volume":
            success, details = system.set_volume(target)
        elif action_type == "system_power":
            if target == "lock":
                success, details = system.lock_screen()
            elif target == "shutdown":
                success, details = system.shutdown()
            elif target == "restart":
                success, details = system.restart()
            elif target == "sleep":
                success, details = system.suspend()
        elif action_type == "file_op":
            op = params.get("operation", "open")
            if op == "open":
                success, details = files.open_file(target)
            elif op == "open_folder":
                success, details = files.open_folder(target)
        elif action_type == "terminal":
            success, details = terminal.run_command(target)

        status = "success" if success else "failure"
        log.info("Action %s: %s -> %s", action_type, target, status)
        return ActionResult(action.action_id, status, details)


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.toml"
    if config_path.exists():
        with open(config_path, "rb") as f:
            raw = tomli.load(f)
            agent = raw.get("agent", {})
            brain = raw.get("brain", {})
            return {
                "device_id": agent.get("device_id", "linux-main"),
                "platform": agent.get("platform", "linux"),
                "brain_ws_url": brain.get("url", "ws://localhost:8400/ws"),
                "brain_rest_url": brain.get("rest_url", "http://localhost:8400"),
                "token": os.environ.get(brain.get("token_env", "JARVIS_AGENT_TOKEN"), ""),
            }
    return {
        "device_id": os.environ.get("JARVIS_DEVICE_ID", "linux-main"),
        "platform": "linux",
        "brain_ws_url": os.environ.get("JARVIS_BRAIN_WS", "ws://localhost:8400/ws"),
        "brain_rest_url": os.environ.get("JARVIS_BRAIN_REST", "http://localhost:8400"),
        "token": os.environ.get("JARVIS_AGENT_TOKEN", ""),
    }


async def text_mode(agent: LinuxAgent) -> None:
    print(f"Jarvis Linux Agent ({agent.device_id})")
    print("Connecting to brain...")
    connect_task = asyncio.create_task(agent.connection.connect())
    await asyncio.sleep(2)
    print("Connected.\n" if agent.connection.connected else "Connecting...\n")
    try:
        while True:
            text = await asyncio.get_event_loop().run_in_executor(None, lambda: input("You: ").strip())
            if not text:
                continue
            if text.lower() == "quit":
                break
            await agent.connection.send_input(text)
    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        await agent.connection.disconnect()
        connect_task.cancel()
        print("\nBye.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis Linux Agent")
    parser.add_argument("--text-only", action="store_true")
    args = parser.parse_args()
    config = load_config()
    agent = LinuxAgent(config)
    if args.text_only:
        asyncio.run(text_mode(agent))
    else:
        asyncio.run(agent.run())


if __name__ == "__main__":
    main()
