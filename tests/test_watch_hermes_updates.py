"""Tests hors réseau du moniteur Hermes."""

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/watch_hermes_updates.py"
spec = importlib.util.spec_from_file_location("watch_hermes_updates", SCRIPT)
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


class WatchHermesTests(unittest.TestCase):
    def test_version_strictly_stable(self):
        self.assertEqual(watch.version("v0.23.3"), (0, 23, 3))
        self.assertEqual(watch.version("0.52.702"), (0, 52, 702))
        for tag in ("exp-v0.52.702", "v0.23.3+canary.1", "v0.23.3-rc1"):
            self.assertIsNone(watch.version(tag))

    def test_read_pins_and_volume_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "apps/hermes-suite"
            path.mkdir(parents=True)
            (path / "config.json").write_text('{"tipi_version":1,"version":"0.23.1"}')
            (path / "docker-compose.yml").write_text(
                "services:\n  hermes-agent:\n    image: nousresearch/hermes-agent:v0.23.1\n"
                "  hermes-webui:\n    image: ghcr.io/nesquena/hermes-webui:0.52.677\n"
            )
            self.assertEqual(watch.read_pins(root), {"Agent": "v0.23.1", "WebUI": "0.52.677"})

    def test_digest_pins(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "apps/hermes-suite"
            folder.mkdir(parents=True)
            (folder / "config.json").write_text('{"version":"0.23.3","tipi_version":2}')
            (folder / "docker-compose.yml").write_text(
                "services:\\n  hermes-agent:\\n    image: nousresearch/hermes-agent:v0.23.3@sha256:"
                + "a"*64 + "\\n  hermes-webui:\\n    image: ghcr.io/nesquena/hermes-webui:0.52.725@sha256:"
                + "b"*64 + "\\n"
            )
            self.assertEqual(watch.read_pins(root), {"Agent": "v0.23.3", "WebUI": "0.52.725"})

    def test_latest_rejects_prerelease_and_experimental(self):
        fake = {
            "/repos/nesquena/hermes-webui/releases/latest": {
                "tag_name": "exp-v0.52.704", "draft": False, "prerelease": False
            },
            "/repos/nesquena/hermes-webui/releases?per_page=100&page=1": [
                {"tag_name": "v0.52.704+canary.1", "draft": False, "prerelease": True},
                {"tag_name": "v0.52.703", "draft": False, "prerelease": False},
                {"tag_name": "v0.52.702", "draft": False, "prerelease": False},
            ],
        }
        with patch.object(watch, "request_json", side_effect=lambda path, token: fake[path]):
            self.assertEqual(watch.latest_stable("nesquena/hermes-webui", None)["tag_name"], "v0.52.703")

    def test_issue_is_idempotent(self):
        body = watch.MARKER + "\n" + "<!-- versions:Agent=v0.23.3;WebUI=v0.52.702 -->"
        with patch.object(watch, "request_json", return_value=[{"number": 7, "body": body}]) as fetch:
            self.assertIn("aucune écriture", watch.publish_issue("Owner/repo", body, "token"))
            self.assertEqual(fetch.call_count, 1)

    def test_fails_closed_on_bad_image_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "apps/hermes-suite"
            path.mkdir(parents=True)
            (path / "config.json").write_text('{"tipi_version":1,"version":"0.23.1"}')
            (path / "docker-compose.yml").write_text("services: {}\n")
            with self.assertRaises(RuntimeError):
                watch.read_pins(root)


if __name__ == "__main__":
    unittest.main()
