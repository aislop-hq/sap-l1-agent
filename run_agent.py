"""CLI entry point for the SAP L1 Support Agent.

Usage:
    python run_agent.py --host sap-dev-01 --sid DEV --nr 00 --alert "WP02 not responding"

Demo mode:
    DEMO_MODE=true python run_agent.py --host mock --sid DEV --nr 00 --alert "WP02 not responding"

Scenario shortcut:
    DEMO_MODE=true python run_agent.py --scenario 1
"""

from __future__ import annotations

import argparse
import logging
import os
import uuid
import sys

# Suppress Langfuse auth warnings before any @observe imports
from config import settings
if not settings.langfuse_public_key or not settings.langfuse_secret_key:
    # Set dummy keys + disabled flag so the SDK doesn't print auth warnings
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-stub")
    os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-stub")
    os.environ.setdefault("LANGFUSE_HOST", "http://localhost:0")
    os.environ["LANGFUSE_ENABLED"] = "false"
    # Suppress OpenTelemetry exporter noise when Langfuse is disabled
    logging.getLogger("opentelemetry").setLevel(logging.CRITICAL)

from langgraph.types import Command  # noqa: E402
from rich.console import Console  # noqa: E402

from langfuse_init import init_langfuse  # noqa: E402
from graph.graph import compiled_graph  # noqa: E402
from tools.ssh_tools import set_scenario  # noqa: E402

console = Console()

DEMO_SCENARIOS = {
    "1": {"host": "mock", "sid": "DEV", "nr": "00", "alert": "WP02 not responding"},
    "2": {"host": "mock", "sid": "DEV", "nr": "00", "alert": "filesystem critical on sap-dev-01"},
    "3": {"host": "mock", "sid": "DEV", "nr": "00", "alert": "TIME_OUT dump in dev_w0"},
    "4": {"host": "mock", "sid": "DEV", "nr": "00", "alert": "instance not responding"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="SAP Basis L1 Support Agent")
    parser.add_argument("--host", help="SAP host to diagnose")
    parser.add_argument("--sid", help="SAP System ID")
    parser.add_argument("--nr", default="00", help="SAP instance number (default: 00)")
    parser.add_argument("--alert", help="Alert description")
    parser.add_argument(
        "--scenario", choices=["1", "2", "3", "4"],
        help="Demo scenario shortcut (1=Hung WP, 2=Filesystem, 3=ABAP Dump, 4=Instance Down)",
    )
    args = parser.parse_args()

    # Resolve scenario shortcut
    if args.scenario:
        s = DEMO_SCENARIOS[args.scenario]
        args.host = args.host or s["host"]
        args.sid = args.sid or s["sid"]
        args.nr = args.nr if args.nr != "00" else s["nr"]
        args.alert = args.alert or s["alert"]

    if not args.host or not args.sid or not args.alert:
        parser.error("--host, --sid, and --alert are required (or use --scenario)")

    # Configure logging and tracing
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(message)s",
    )
    init_langfuse()

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # Set mock scenario before graph runs
    set_scenario(args.alert)

    initial_state = {
        "host": args.host,
        "sid": args.sid,
        "instance_nr": args.nr,
        "alert": args.alert,
        "thread_id": thread_id,
        "messages": [],
    }

    console.print(f"\n[bold blue]SAP L1 Agent[/bold blue] — thread {thread_id}")
    console.print(f"  Host: {args.host}  SID: {args.sid}  NR: {args.nr}")
    console.print(f"  Alert: {args.alert}")
    if settings.demo_mode:
        console.print("  [dim]DEMO_MODE=true (using mock outputs)[/dim]")
    console.print()

    # Run the graph — it will pause at interrupt() if approval is needed
    result = compiled_graph.invoke(initial_state, config)

    # Check if the graph paused at the approval gate
    state = compiled_graph.get_state(config)
    while state.next:
        # Graph is paused — prompt for approval
        console.print()
        try:
            answer = console.input("[bold yellow]Approve? [yes/no]: [/bold yellow]").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "no"
            console.print("\n[dim]Interrupted — treating as 'no'[/dim]")

        decision = "yes" if answer in ("yes", "y") else "no"

        # Resume the graph with the operator's decision
        result = compiled_graph.invoke(Command(resume=decision), config)
        state = compiled_graph.get_state(config)

    console.print("\n[bold blue]Agent complete.[/bold blue]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted by user.[/dim]")
        sys.exit(130)
