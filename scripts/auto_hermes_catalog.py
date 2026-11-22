#!/usr/bin/env python3
"""Select a stable Hermes Agent/WebUI candidate, never changing the catalog.

The CI publisher calls --recheck before the only write step: stale test results
must not be published if the upstream pair or current catalog has changed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_hermes_update as prepare
import watch_hermes_updates as watch

REVIEW_NOTE = (
    "https://github.com/ProGregoryBrunel/runtipi-custom-appstore/issues/7"
)


def choose(root: Path, pins: dict, latest: dict) -> dict:
    selected = {}
    for name in ("Agent", "WebUI"):
        tag = latest[name]["tag_name"]
        new = watch.version(tag)
        old = watch.version(pins[name])
        if new is None or old is None:
            raise ValueError(f"Non-stable tag for {name}")
        # Never downgrade a component just because another one has a new release.
        selected[name] = tag if new > old else pins[name]
    selected["Agent"] = "v" + selected["Agent"].lstrip("v")
    selected["WebUI"] = selected["WebUI"].lstrip("v")
    if (
        watch.version(selected["Agent"]) == watch.version(pins["Agent"])
        and watch.version(selected["WebUI"]) == watch.version(pins["WebUI"])
    ):
        return {"eligible": False, "reason": "Already at stable releases"}
    try:
        prepare.build_update(
            root, selected["Agent"], selected["WebUI"], REVIEW_NOTE
        )
    except prepare.UpdateError as exc:
        return {"eligible": False, "reason": f"Compatibility guard: {exc}"}
    return {
        "eligible": True,
        "agent_tag": selected["Agent"],
        "webui_tag": selected["WebUI"],
        "agent_release": latest["Agent"]["html_url"],
        "webui_release": latest["WebUI"]["html_url"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", type=Path)
    parser.add_argument("--recheck", action="store_true")
    parser.add_argument("--agent")
    parser.add_argument("--webui")
    args = parser.parse_args()

    pins = watch.read_pins(ROOT)
    latest = {
        name: watch.latest_stable(repo, None)
        for name, repo in watch.RELEASES.items()
    }
    result = choose(ROOT, pins, latest)
    if args.recheck:
        if not result["eligible"]:
            raise SystemExit(f"Publish blocked on recheck: {result['reason']}")
        if (result["agent_tag"], result["webui_tag"]) != (
            args.agent, args.webui
        ):
            raise SystemExit("Publish blocked: candidate drift after verification")
        print("Candidate still matches latest stable releases and current catalog")
        return

    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.output:
        args.output.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
    if args.github_output:
        values = {
            "eligible": str(result["eligible"]).lower(),
            "agent": result.get("agent_tag", ""),
            "webui": result.get("webui_tag", ""),
        }
        with args.github_output.open("a", encoding="utf-8") as out:
            for key, value in values.items():
                print(f"{key}={value}", file=out)


if __name__ == "__main__":
    main()
