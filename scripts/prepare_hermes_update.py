#!/usr/bin/env python3
"""Prepare a review-only Hermes/Runtipi catalog update. No GitHub or Docker writes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = Path("apps/hermes-suite")
AGENT = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
WEBUI = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
EVIDENCE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/[1-9]\d*$", re.ASCII)
IMAGES = {
    "agent": re.compile(r"(?m)^(\s*image:\s*nousresearch/hermes-agent:)(v\d+\.\d+\.\d+)(\s*)$"),
    "webui": re.compile(r"(?m)^(\s*image:\s*ghcr\.io/nesquena/hermes-webui:)(\d+\.\d+\.\d+)(\s*)$"),
}
# Release pair currently held due to reported session compatibility problems.
# Do not remove without documented compatibility evidence and review.
BLOCKED_PAIRS = {("v0.23.3", "0.52.702")}
# WebUI <=0.52.724 imports an Agent-internal retirement API removed in v0.23.3.
# See nesquena/hermes-webui#9213. Fix #9218 is not in stable v0.52.724.
# This is a fail-closed floor for confirmed affected versions, not approval of
# newer WebUI versions; the manual compatibility review remains mandatory.
SESSION_DELETE_AGENT_MIN = (0, 23, 3)
SESSION_DELETE_WEBUI_MAX = (0, 52, 724)


class UpdateError(ValueError):
    """Fail closed without modifying any catalog files."""


def numbers(tag: str, kind: str) -> tuple[int, int, int]:
    match = (AGENT if kind == "agent" else WEBUI).fullmatch(tag)
    if not match:
        raise UpdateError(f"Invalid {kind} stable tag: {tag!r}")
    return tuple(int(x) for x in match.groups())


def single_replace(pattern: re.Pattern, content: str, old: str, new: str, label: str) -> str:
    hits = list(pattern.finditer(content))
    if len(hits) != 1 or hits[0].group(2) != old:
        raise UpdateError(f"Unexpected {label} pin: aborting")
    match = hits[0]
    return content[:match.start(2)] + new + content[match.end(2):]


def build_update(root: Path, agent: str, webui: str, evidence: str) -> tuple[dict[Path, str], str]:
    agent_numbers = numbers(agent, "agent")
    webui_numbers = numbers(webui, "webui")
    if not EVIDENCE.fullmatch(evidence):
        raise UpdateError("Compatibility evidence must be a GitHub issue or PR URL")
    if agent_numbers >= SESSION_DELETE_AGENT_MIN and webui_numbers <= SESSION_DELETE_WEBUI_MAX:
        raise UpdateError(
            "Update blocked: Agent v0.23.3+ with WebUI <=0.52.724 has a known "
            "session deletion regression (nesquena/hermes-webui#9213); review a "
            "stable WebUI release including fix #9218 before proposing the pair"
        )
    if (agent, webui) in BLOCKED_PAIRS:
        raise UpdateError("This release pair is blocked following a compatibility report")

    config_file = root / APP / "config.json"
    compose_file = root / APP / "docker-compose.yml"
    metadata_file = root / APP / "metadata/description.md"
    original = {p: p.read_text(encoding="utf-8") for p in (config_file, compose_file, metadata_file)}
    cfg = json.loads(original[config_file])
    if not isinstance(cfg, dict) or cfg.get("id") != "hermes-suite":
        raise UpdateError("Unexpected Runtipi app configuration")
    tipi = cfg.get("tipi_version")
    if type(tipi) is not int or tipi < 1:
        raise UpdateError("Invalid tipi_version")

    current = {}
    compose = original[compose_file]
    for kind, pattern in IMAGES.items():
        hits = list(pattern.finditer(compose))
        if len(hits) != 1:
            raise UpdateError(f"Expected exactly one {kind} image pin")
        current[kind] = hits[0].group(2)
        numbers(current[kind], kind)

    if cfg.get("version") != current["agent"].removeprefix("v"):
        raise UpdateError("config.json agent version mismatch")
    if numbers(agent, "agent") < numbers(current["agent"], "agent"):
        raise UpdateError("Agent downgrade forbidden")
    if numbers(webui, "webui") < numbers(current["webui"], "webui"):
        raise UpdateError("WebUI downgrade forbidden")
    if agent == current["agent"] and webui == current["webui"]:
        raise UpdateError("No update: both versions are unchanged")

    old_volume = "hermes-agent-src-v" + current["agent"][1:].replace(".", "")
    new_volume = "hermes-agent-src-v" + agent[1:].replace(".", "")
    # Require whole Compose lines, not substrings hidden in comments or other mounts.
    volume = re.escape(old_volume)
    expected_lines = (
        rf"^[ \t]*-[ \t]+{volume}:/opt/hermes[ \t]*$",
        rf"^[ \t]*-[ \t]+{volume}:/home/hermeswebui/\.hermes/hermes-agent:ro[ \t]*$",
        rf"^[ \t]+{volume}:[ \t]*$",
    )
    if compose.count(old_volume) != 3 or any(
        len(re.findall(pattern, compose, re.MULTILINE)) != 1 for pattern in expected_lines
    ):
        raise UpdateError("Code volume does not match expected 2 mounts + declaration")

    compose = single_replace(IMAGES["agent"], compose, current["agent"], agent, "agent")
    compose = single_replace(IMAGES["webui"], compose, current["webui"], webui, "webui")
    if agent != current["agent"]:
        compose = compose.replace(old_volume, new_volume)
    if new_volume not in compose or compose.count(new_volume) != 3:
        raise UpdateError("New code volume is not defined in all three locations")

    old_desc = f"Hermes Agent {current['agent']} with Hermes WebUI {current['webui']}"
    new_desc = f"Hermes Agent {agent} with Hermes WebUI {webui}"
    if cfg.get("description", "").count(old_desc) != 1:
        raise UpdateError("Unexpected config.json description")
    cfg["description"] = cfg["description"].replace(old_desc, new_desc)
    cfg["version"] = agent[1:]
    cfg["tipi_version"] = tipi + 1
    config = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"

    metadata = original[metadata_file]
    for older, newer in ((current["agent"], agent), (current["webui"], webui)):
        if metadata.count(f"`{older}`") < 2:
            raise UpdateError("Unexpected metadata description; aborting")
        metadata = metadata.replace(f"`{older}`", f"`{newer}`")

    changes = {
        config_file: config,
        compose_file: compose,
        metadata_file: metadata,
    }
    changes = {file: new for file, new in changes.items() if new != original[file]}
    if config_file not in changes or compose_file not in changes or metadata_file not in changes:
        raise UpdateError("Unexpected incomplete patch")

    body = "\n".join([
        "## Hermes Suite : proposition de mise à jour (BROUILLON)",
        "",
        "| | Actuel | Proposé |",
        "|---|---|---|",
        f"| Agent | `{current['agent']}` | `{agent}` |",
        f"| WebUI | `{current['webui']}` | `{webui}` |",
        f"| `tipi_version` | `{tipi}` | `{tipi + 1}` |",
        f"| Volume code | `{old_volume}` | `{new_volume}` |",
        "",
        f"Revue de compatibilité déclarée : {evidence}",
        "",
        "**Cette PR est un brouillon.** Son ouverture n'atteste ni d'une compatibilité",
        "réellement testée, ni de la disponibilité des sauvegardes de production.",
        "Le workflow contrôle les releases et manifests d'images avant de l'ouvrir.",
        "",
        "### Obligatoire avant fusion",
        "- [ ] Confirmer le comportement Agent + WebUI : sessions, API, Telegram, skills.",
        "- [ ] Vérifier la cohérence du Compose généré et des overrides privés du VPS.",
        "- [ ] Résoudre les permissions Runtipi 4.12.0 (app-data réouvert par Runtipi).",
        "- [ ] Vérifier une sauvegarde récente et une stratégie de restauration, volume de code compris.",
        "- [ ] Valider le plan de retour arrière, sans supprimer les volumes précédents.",
        "- [ ] Fusion humaine uniquement ; installation Runtipi uniquement à la demande.",
        "",
    ])
    return changes, body


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True, help="Agent image tag, e.g. v0.23.4")
    parser.add_argument("--webui", required=True, help="WebUI image tag, e.g. 0.52.703")
    parser.add_argument("--evidence", required=True, help="GitHub review issue or PR URL")
    parser.add_argument("--root", type=Path, default=ROOT, help="Catalog root (tests only)")
    parser.add_argument("--apply", action="store_true", help="Write only 3 known app catalog files")
    parser.add_argument("--body-file", type=Path, help="Write PR body on --apply")
    args = parser.parse_args()
    changes, body = build_update(args.root, args.agent, args.webui, args.evidence)
    if args.apply:
        for file, content in changes.items():
            file.write_text(content, encoding="utf-8")
        if args.body_file:
            args.body_file.write_text(body, encoding="utf-8")
        print(f"Updated {len(changes)} app catalog files; no GitHub or Docker action performed")
    else:
        print("Dry run: proposal is valid; no files modified")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (UpdateError, OSError, json.JSONDecodeError) as exc:
        print(f"ABORT: {exc}", file=sys.stderr)
        sys.exit(1)
