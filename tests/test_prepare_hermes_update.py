"""Offline, non-destructive tests for the update PR generator."""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_hermes_update.py"
spec = importlib.util.spec_from_file_location("prepare_hermes_update", SCRIPT)
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)
EVIDENCE = "https://github.com/ProGregoryBrunel/runtipi-custom-appstore/issues/18"


def fixture(root):
    folder = root / "apps/hermes-suite"
    (folder / "metadata").mkdir(parents=True)
    (folder / "config.json").write_text(json.dumps({
        "id": "hermes-suite", "tipi_version": 1, "version": "0.23.1",
        "description": "Hermes Agent v0.23.1 with Hermes WebUI 0.52.677. Existing metadata.",
        "untouched": "yes",
    }, indent=2) + "\n")
    (folder / "docker-compose.yml").write_text(
        "services:\n  hermes-agent:\n    image: nousresearch/hermes-agent:v0.23.1\n"
        "    volumes:\n      - hermes-agent-src-v0231:/opt/hermes\n"
        "  hermes-webui:\n    image: ghcr.io/nesquena/hermes-webui:0.52.677\n"
        "    volumes:\n      - hermes-agent-src-v0231:/home/hermeswebui/.hermes/hermes-agent:ro\n"
        "volumes:\n  hermes-agent-src-v0231:\n"
    )
    (folder / "metadata/description.md").write_text(
        "Agent `v0.23.1`, WebUI `0.52.677`.\n"
        "Agent `v0.23.1`, WebUI `0.52.677`.\n"
    )
    return folder


class GeneratorTests(unittest.TestCase):
    def test_update_both_and_versioned_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = fixture(root)
            changes, body = prep.build_update(root, "v0.23.4", "0.52.703", EVIDENCE)
            self.assertEqual(len(changes), 3)
            new_cfg = json.loads(changes[folder / "config.json"])
            self.assertEqual(new_cfg["tipi_version"], 2)
            self.assertEqual(new_cfg["version"], "0.23.4")
            self.assertEqual(new_cfg["untouched"], "yes")
            compose = changes[folder / "docker-compose.yml"]
            self.assertNotIn("hermes-agent-src-v0231", compose)
            self.assertEqual(compose.count("hermes-agent-src-v0234"), 3)
            self.assertIn("`v0.23.4`", changes[folder / "metadata/description.md"])
            self.assertIn(EVIDENCE, body)
            self.assertIn("Fusion humaine", body)
            self.assertIn("v0.23.1", (folder / "docker-compose.yml").read_text())

    def test_webui_only_keeps_agent_volume(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = fixture(root)
            changes, _ = prep.build_update(root, "v0.23.1", "0.52.703", EVIDENCE)
            self.assertEqual(changes[folder / "docker-compose.yml"].count("hermes-agent-src-v0231"), 3)
            self.assertEqual(json.loads(changes[folder / "config.json"])["tipi_version"], 2)

    def test_block_known_bad_pair(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            with self.assertRaisesRegex(prep.UpdateError, "blocked"):
                prep.build_update(root, "v0.23.3", "0.52.702", EVIDENCE)

    def test_reject_no_update_and_downgrade(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            for a, w in (("v0.23.1", "0.52.677"), ("v0.23.0", "0.52.680"), ("v0.23.4", "0.52.600")):
                with self.subTest(a=a, w=w), self.assertRaises(prep.UpdateError):
                    prep.build_update(root, a, w, EVIDENCE)

    def test_invalid_versions_and_url(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            for a, w, url in (
                ("v0.23.4-rc1", "0.52.703", EVIDENCE),
                ("v0.23.4", "exp-0.52.703", EVIDENCE),
                ("v0.23.4; rm -rf /", "0.52.703", EVIDENCE),
                ("v0.23.4", "0.52.703", "https://evil.example/issue/3"),
            ):
                with self.subTest(a=a,w=w,url=url), self.assertRaises(prep.UpdateError):
                    prep.build_update(root, a, w, url)

    def test_volume_not_expected_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = fixture(root)
            compose_path = folder / "docker-compose.yml"
            compose_path.write_text(compose_path.read_text().replace("hermes-agent-src-v0231:/opt/hermes", "wrong:/opt/hermes"))
            with self.assertRaisesRegex(prep.UpdateError, "volume"):
                prep.build_update(root, "v0.23.4", "0.52.703", EVIDENCE)

    def test_volume_cannot_be_satisfied_by_comment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = fixture(root)
            path = folder / "docker-compose.yml"
            # An old substring-based check could mistake a comment for a mount.
            source = path.read_text().replace(
                "      - hermes-agent-src-v0231:/opt/hermes\n",
                "      # - hermes-agent-src-v0231:/opt/hermes\n",
            )
            path.write_text(source)
            with self.assertRaisesRegex(prep.UpdateError, "volume"):
                prep.build_update(root, "v0.23.4", "0.52.703", EVIDENCE)

    def test_inconsistent_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = fixture(root)
            path = folder / "config.json"
            cfg = json.loads(path.read_text())
            cfg["version"] = "0.24.0"
            path.write_text(json.dumps(cfg))
            with self.assertRaisesRegex(prep.UpdateError, "mismatch"):
                prep.build_update(root, "v0.23.4", "0.52.703", EVIDENCE)

    def test_tag_and_url_regex(self):
        self.assertEqual(prep.numbers("v0.23.4", "agent"), (0,23,4))
        self.assertEqual(prep.numbers("0.52.703", "webui"), (0,52,703))
        for url in ("https://github.com/org/repo/issues/7?x=1", "http://github.com/o/r/issues/7", "https://github.com.evil.example/o/r/issues/7"):
            self.assertIsNone(prep.EVIDENCE.fullmatch(url))


if __name__ == "__main__":
    unittest.main()
