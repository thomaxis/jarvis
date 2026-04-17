"""Windows Agent -- main entry point. Connects to cloud brain and executes actions."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

import tomli

# Add project root to path
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_PROJECT_ROOT))

from agents.shared.base_agent import BaseAgent
from agents.shared.models import ActionRequest, ActionResult
from agents.windows.actions import apps, browser, clipboard, files, system, terminal
from agents.windows.safety import request_confirmation, requires_confirmation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis.windows")


class WindowsAgent(BaseAgent):
    def get_capabilities(self) -> list[str]:
        return ["os_control", "apps", "files", "browser", "terminal", "clipboard", "system"]

    async def execute_action(self, action: ActionRequest) -> ActionResult:
        action_type = action.type
        target = action.target
        params = action.params

        # Safety check
        if requires_confirmation(action_type, target):
            approved = await request_confirmation(action_type, target)
            if not approved:
                return ActionResult(action.action_id, "cancelled", "User declined")

        success, details = False, "Unknown action"

        if action_type == "open_app":
            success, details = apps.open_app(target)
        elif action_type == "close_app":
            success, details = apps.close_app(target)
        elif action_type == "open_url":
            success, details = browser.open_url(target)
        elif action_type == "search":
            success, details = browser.search_web(target, params.get("engine", "google"))
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
                success, details = system.sleep_screen()
        elif action_type == "file_op":
            op = params.get("operation", "open")
            if op == "open":
                success, details = files.open_file(target)
            elif op == "open_folder":
                success, details = files.open_folder(target)
            elif op == "create":
                success, details = files.create_file(target, params.get("content", ""))
        elif action_type == "terminal":
            success, details = terminal.run_command(target, params.get("shell", "powershell"))
        elif action_type == "clipboard":
            op = params.get("operation", "read")
            if op == "read":
                success, details = clipboard.read_clipboard()
            elif op == "write":
                success, details = clipboard.write_clipboard(target)
        elif action_type == "screenshot":
            success, details = False, "Screenshot not yet implemented"
        else:
            details = f"Unknown action type: {action_type}"

        status = "success" if success else "failure"
        log.info("Action %s: %s -> %s", action_type, target, status)
        return ActionResult(action.action_id, status, details)


def load_config() -> dict:
    """Load agent config from config.toml or environment."""
    config_path = Path(__file__).parent / "config.toml"
    config: dict = {}

    if config_path.exists():
        with open(config_path, "rb") as f:
            raw = tomli.load(f)
            agent = raw.get("agent", {})
            brain = raw.get("brain", {})
            config = {
                "device_id": agent.get("device_id", "windows-main"),
                "platform": agent.get("platform", "windows"),
                "brain_ws_url": brain.get("url", "ws://localhost:8400/ws"),
                "brain_rest_url": brain.get("rest_url", "http://localhost:8400"),
                "token": os.environ.get(brain.get("token_env", "JARVIS_AGENT_TOKEN"), ""),
            }
    else:
        config = {
            "device_id": os.environ.get("JARVIS_DEVICE_ID", "windows-main"),
            "platform": "windows",
            "brain_ws_url": os.environ.get("JARVIS_BRAIN_WS", "ws://localhost:8400/ws"),
            "brain_rest_url": os.environ.get("JARVIS_BRAIN_REST", "http://localhost:8400"),
            "token": os.environ.get("JARVIS_AGENT_TOKEN", ""),
        }

    return config


async def register_agent(config: dict) -> None:
    """Register this agent with the brain and get a JWT token."""
    import httpx

    rest_url = config.get("brain_rest_url", "http://localhost:8400")
    device_id = config.get("device_id", "windows-main")
    platform = config.get("platform", "windows")

    print(f"Registering agent '{device_id}' with brain at {rest_url}...")

    try:
        async with httpx.AsyncClient(base_url=rest_url, timeout=10.0) as client:
            resp = await client.post("/api/v1/agent/register", json={
                "device_id": device_id,
                "platform": platform,
                "device_name": f"{platform} agent",
                "capabilities": ["os_control", "apps", "files", "browser", "terminal", "clipboard", "system"],
            })

            if resp.status_code == 200:
                data = resp.json()
                token = data.get("token", "")
                print(f"Registered. Token:\n\n{token}\n")
                print("Save this token. Set it as JARVIS_AGENT_TOKEN environment variable,")
                print("or add it to your config.toml under [brain] token_env.")
            else:
                print(f"Registration failed: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Could not connect to brain: {e}")


async def text_mode(agent: WindowsAgent) -> None:
    """Interactive text mode for testing without voice."""
    print(f"Jarvis Windows Agent ({agent.device_id})")
    print("Connecting to brain...")

    # Run connection in background
    connect_task = asyncio.create_task(agent.connection.connect())

    # Wait a bit for connection
    await asyncio.sleep(2)

    if agent.connection.connected:
        print("Connected. Type 'quit' to exit.\n")
    else:
        print("Not connected yet (will keep trying in background).\n")

    try:
        while True:
            text = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("You: ").strip()
            )
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


async def voice_mode(agent: WindowsAgent, config: dict) -> None:
    """Full voice mode: wake word > listen > transcribe > send > respond > speak."""
    from agents.windows.voice.stt import SpeechToText
    from agents.windows.voice.tts import TextToSpeech
    from agents.windows.voice.listener import VoiceListener

    voice_cfg = config.get("voice", {})
    stt = SpeechToText(model_size=voice_cfg.get("stt_model", "base.en"))
    tts = TextToSpeech(
        engine=voice_cfg.get("tts_engine", "piper"),
        voice=voice_cfg.get("tts_voice", "en_US-lessac-medium"),
    )
    listener = VoiceListener(
        wake_word=voice_cfg.get("wake_word", "jarvis"),
        silence_threshold=voice_cfg.get("silence_threshold", 500),
    )

    # Initialize voice components
    stt_ok = stt.initialize()
    tts_ok = tts.initialize()
    listener_ok = listener.initialize()

    if not stt_ok:
        log.error("STT failed to initialize. Falling back to text mode.")
        await text_mode(agent)
        return

    print(f"Jarvis Windows Agent ({agent.device_id}) - Voice Mode")
    print(f"  STT: {'ready' if stt_ok else 'disabled'}")
    print(f"  TTS: {'ready' if tts_ok else 'disabled'}")
    print(f"  Wake word: {'ready' if listener_ok and listener._porcupine else 'push-to-talk'}")
    print("Connecting to brain...")

    # Store TTS ref on agent for response playback
    agent._tts = tts if tts_ok else None

    # Override message handler to speak responses
    original_handler = agent._handle_message

    async def voice_message_handler(message: dict) -> None:
        await original_handler(message)
        event = message.get("event", "")
        if event == "response" and tts_ok:
            text = message.get("text", "")
            if text:
                tts.speak(text)

    agent.connection._on_message = voice_message_handler

    connect_task = asyncio.create_task(agent.connection.connect())
    await asyncio.sleep(2)

    if agent.connection.connected:
        print("Connected. Listening...\n")
    else:
        print("Not connected yet (will keep trying).\n")

    try:
        while True:
            if listener_ok and listener._porcupine:
                # Wake word mode
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: listener.listen_for_wake_word(lambda: None)
                )
            else:
                # Push-to-talk: wait for Enter
                await asyncio.get_event_loop().run_in_executor(
                    None, lambda: input("[Press Enter to speak] ")
                )

            # Record audio
            wav_path = await asyncio.get_event_loop().run_in_executor(
                None, listener.record_until_silence
            )

            if not wav_path:
                continue

            # Transcribe
            text = stt.transcribe(wav_path)
            if not text:
                continue

            print(f"You: {text}")
            await agent.connection.send_input(text)

            # Clean up temp file
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        listener.cleanup()
        await agent.connection.disconnect()
        connect_task.cancel()
        print("\nBye.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jarvis Windows Agent")
    parser.add_argument("--text-only", action="store_true", help="Text mode (no voice)")
    parser.add_argument("--register", action="store_true", help="Register with brain and get JWT")
    args = parser.parse_args()

    config = load_config()
    agent = WindowsAgent(config)

    if args.register:
        asyncio.run(register_agent(config))
        return

    if args.text_only:
        asyncio.run(text_mode(agent))
    else:
        asyncio.run(voice_mode(agent, config))


if __name__ == "__main__":
    main()
