#!/usr/bin/env python3
"""Surveille les versions stables Hermes sans modifier le catalogue Runtipi.

Python stdlib uniquement. En mode GitHub Actions, ouvre/met à jour UNE issue
pour signaler les versions candidates. Aucun déploiement ni commit automatique.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "https://api.github.com"
RELEASES = {
    "Agent": "NousResearch/hermes-agent",
    "WebUI": "nesquena/hermes-webui",
}
STABLE_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
REPO_ID = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
MARKER = "<!-- hermes-update-watch:v1 -->"
TITLE = "Veille Hermes : nouvelles versions à valider"


def version(tag: str) -> tuple[int, int, int] | None:
    match = STABLE_TAG.fullmatch(tag)
    return tuple(map(int, match.groups())) if match else None


def request_json(path: str, token: str | None, method: str = "GET", data: dict | None = None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Hermes-Runtipi-Update-Watcher/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = Request(API + path, headers=headers, method=method, data=body)
    try:
        with urlopen(req, timeout=25) as response:
            return json.load(response)
    except HTTPError as exc:
        raise RuntimeError(f"GitHub API: HTTP {exc.code} sur {path.split('?')[0]}") from exc
    except URLError as exc:
        raise RuntimeError(f"GitHub API inaccessible ({type(exc.reason).__name__})") from exc


def latest_stable(repo: str, token: str | None) -> dict:
    # /latest exclut les brouillons/prereleases mais pas forcément les tags expérimentaux.
    # On vérifie donc aussi une syntaxe de version strictement stable.
    try:
        item = request_json(f"/repos/{repo}/releases/latest", token)
        if not item.get("draft") and not item.get("prerelease") and version(item.get("tag_name", "")):
            return item
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise

    candidates = []
    for page in range(1, 4):
        items = request_json(f"/repos/{repo}/releases?per_page=100&page={page}", token)
        if not isinstance(items, list):
            raise RuntimeError(f"Format inattendu des releases pour {repo}")
        candidates.extend(
            item for item in items
            if not item.get("draft") and not item.get("prerelease")
            and version(item.get("tag_name", "")) is not None
        )
        if len(items) < 100:
            break
    if not candidates:
        raise RuntimeError(f"Aucune release stable identifiée pour {repo}")
    return max(candidates, key=lambda x: version(x["tag_name"]))


def read_pins(root: Path) -> dict[str, str]:
    config = json.loads((root / "apps/hermes-suite/config.json").read_text(encoding="utf-8"))
    compose = (root / "apps/hermes-suite/docker-compose.yml").read_text(encoding="utf-8")
    patterns = {
        "Agent": r"^\s*image:\s*nousresearch/hermes-agent:(v?\d+\.\d+\.\d+)\s*$",
        "WebUI": r"^\s*image:\s*ghcr\.io/nesquena/hermes-webui:(v?\d+\.\d+\.\d+)\s*$",
    }
    pins = {}
    for name, pattern in patterns.items():
        matches = re.findall(pattern, compose, re.MULTILINE)
        if len(matches) != 1:
            raise RuntimeError(f"Image {name} introuvable ou dupliquée dans Compose")
        pins[name] = matches[0]
    if version(pins["Agent"]) != version(str(config.get("version", ""))):
        raise RuntimeError("Incohérence entre config.json version et image Agent")
    if not isinstance(config.get("tipi_version"), int) or config["tipi_version"] < 1:
        raise RuntimeError("tipi_version invalide")
    return pins


def issue_body(pins: dict[str, str], latest: dict[str, dict]) -> str:
    tags = {name: item["tag_name"] for name, item in latest.items()}
    fingerprint = f"<!-- versions:Agent={tags['Agent']};WebUI={tags['WebUI']} -->"
    rows = []
    for name in ("Agent", "WebUI"):
        is_new = version(tags[name]) > version(pins[name])
        url = latest[name].get("html_url") or f"https://github.com/{RELEASES[name]}/releases/tag/{tags[name]}"
        rows.append(f"| {name} | `{pins[name]}` | [`{tags[name]}`]({url}) | {'À examiner' if is_new else 'Aucune nouvelle version'} |")
    return "\n".join([
        MARKER,
        fingerprint,
        "## Versions amont détectées",
        "",
        "| Composant | Version du catalogue | Dernière stable GitHub | État |",
        "|---|---|---|---|",
        *rows,
        "",
        "**Aucune mise à jour automatique n'a été effectuée.** Cette issue est une alerte, pas une approbation de compatibilité.",
        "",
        "### Vérifications humaines avant publication dans Runtipi",
        "",
        "- Vérifier la compatibilité réelle entre les deux versions (sessions, WebUI, plugins, gateway, Telegram).",
        "- Vérifier l'existence des tags d'images Docker et leurs plateformes, puis contrôler les notes de sécurité.",
        "- Vérifier la sauvegarde et la restauration possible des données avant intervention sur le VPS.",
        "- Si l'image Agent change, renommer le volume `hermes-agent-src-vXXXX` dans ses deux montages ET sa déclaration.",
        "- Préparer une PR avec tags épinglés et `tipi_version` incrémenté ; ne fusionner qu'après validation.",
        "- La correction durable des permissions Runtipi 4.12.0 reste un chantier distinct.",
        "",
        "Cette issue est maintenue par le workflow de veille. Utiliser les commentaires pour les notes humaines.",
    ])


def publish_issue(repo: str, body: str, token: str) -> str:
    if not REPO_ID.fullmatch(repo):
        raise RuntimeError("GITHUB_REPOSITORY invalide")
    matches = []
    for page in range(1, 4):
        issues = request_json(f"/repos/{repo}/issues?state=open&per_page=100&page={page}", token)
        matches.extend(
            x for x in issues
            if "pull_request" not in x and MARKER in (x.get("body") or "")
        )
        if len(issues) < 100:
            break
    if len(matches) > 1:
        raise RuntimeError("Plusieurs issues de veille actives : correction manuelle nécessaire")
    if matches:
        existing = matches[0]
        if (existing.get("body") or "") == body:
            return "Issue déjà à jour (aucune écriture)"
        request_json(f"/repos/{repo}/issues/{existing['number']}", token, method="PATCH", data={"body": body})
        return f"Issue #{existing['number']} actualisée"
    result = request_json(f"/repos/{repo}/issues", token, method="POST", data={"title": TITLE, "body": body})
    return f"Issue #{result['number']} créée"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish-issue", action="store_true", help="Créer/actualiser une issue GitHub")
    args = parser.parse_args()
    token = os.getenv("GITHUB_TOKEN")
    pins = read_pins(ROOT)
    latest = {name: latest_stable(repo, token) for name, repo in RELEASES.items()}
    for name in ("Agent", "WebUI"):
        print(f"{name}: catalogue={pins[name]} stable={latest[name]['tag_name']}")

    if not any(version(latest[name]["tag_name"]) > version(pins[name]) for name in RELEASES):
        print("Catalogue à jour selon les releases stables GitHub : aucune issue créée")
        return 0

    body = issue_body(pins, latest)
    if args.publish_issue:
        if not token:
            raise RuntimeError("GITHUB_TOKEN est nécessaire pour publier une issue")
        repo = os.getenv("GITHUB_REPOSITORY", "")
        print(publish_issue(repo, body, token))
    else:
        print("\n--- PRÉVISUALISATION (aucune écriture) ---\n")
        print(body)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        sys.exit(1)
