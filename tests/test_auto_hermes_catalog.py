"""Unit tests for automatic candidate selection. No GitHub/network/Docker access."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import auto_hermes_catalog as auto
from test_prepare_hermes_update import fixture


BASELINE = {"Agent": "v0.23.1", "WebUI": "0.52.677"}


def releases(agent: str, webui: str) -> dict:
    return {
        "Agent": {
            "tag_name": agent,
            "html_url": "https://github.com/NousResearch/hermes-agent/releases/tag/" + agent,
        },
        "WebUI": {
            "tag_name": "v" + webui,
            "html_url": "https://github.com/nesquena/hermes-webui/releases/tag/v" + webui,
        },
    }


class SelectCandidateTests(unittest.TestCase):
    def check(self, release_agent, release_webui):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture(root)
            return auto.choose(root, BASELINE, releases(release_agent, release_webui))

    def test_no_version_change(self):
        result = self.check("v0.23.1", "0.52.677")
        self.assertFalse(result["eligible"])

    def test_known_incompatible_versions_are_blocked(self):
        for agent, webui in (
            ("v0.23.3", "0.52.724"),
            ("v0.23.3", "0.52.702"),
        ):
            with self.subTest(agent=agent, webui=webui):
                result = self.check(agent, webui)
                self.assertFalse(result["eligible"])
                self.assertIn("Compatibility guard", result["reason"])

    def test_candidate_above_guard_is_eligible_for_runtime_tests(self):
        # Synthetic version; eligibility does not certify compatibility.
        result = self.check("v0.23.3", "0.52.725")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["agent_tag"], "v0.23.3")
        self.assertEqual(result["webui_tag"], "0.52.725")

    def test_only_new_webui_preserves_agent_code_version(self):
        result = self.check("v0.23.1", "0.52.725")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["agent_tag"], "v0.23.1")

    def test_no_downgrade_if_a_release_api_returns_older_version(self):
        result = self.check("v0.23.0", "0.52.725")
        self.assertTrue(result["eligible"])
        self.assertEqual(result["agent_tag"], "v0.23.1")

    def test_unstable_tag_fails_closed(self):
        with self.assertRaises(ValueError):
            self.check("v0.23.3-rc1", "0.52.725")


if __name__ == "__main__":
    unittest.main()
