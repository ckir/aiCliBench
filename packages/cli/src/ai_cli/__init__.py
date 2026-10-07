"""Developer/operator CLI (stdlib argparse; no framework needed for this slice)."""

from __future__ import annotations

import argparse
import json
import sys

from ai_plugin_example import ExamplePlugin


def _list_tools() -> int:
    plugin = ExamplePlugin()
    payload = [
        {
            "name": spec.name,
            "description": spec.description,
            "effect": str(spec.effect.value),
            "input_schema": spec.input_schema,
        }
        for spec in plugin.tools()
    ]
    print(json.dumps({"plugin": plugin.metadata.name, "tools": payload}, indent=2))
    return 0


def _health() -> int:
    print(json.dumps({"status": "ok", "service": "ai-cli"}))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai", description="AI monorepo operator CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health", help="Print CLI health")
    sub.add_parser("tools", help="List example plugin tools")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "health":
        sys.exit(_health())
    if args.command == "tools":
        sys.exit(_list_tools())
    parser.error(f"unknown command {args.command!r}")
