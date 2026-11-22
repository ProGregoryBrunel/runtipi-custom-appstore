#!/usr/bin/env python3
"""Run inside the ephemeral WebUI container after both services are healthy.

No real user data, credentials, providers or messaging adapters are involved.
Session creation uses the active Agent's own persistence API, not a mocked DB.
"""

from __future__ import annotations

import importlib
import importlib.util
import sqlite3
import tempfile
import urllib.error
import urllib.request
from pathlib import Path


def assert_http(url: str, expected: int = 200) -> None:
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    if status != expected:
        raise AssertionError(f"{url}: HTTP {status}, expected {expected}")
    print(f"HTTP check passed: {url} ({status})", flush=True)


class StoreWriter:
    def __init__(self, home: Path):
        from persistence_assembly import open_persistence, profile_scope

        self.home = home
        self.handle = open_persistence(profile_scope(home=home))
        self.epoch = self.handle.runtime.begin_epoch(instance_id="hermes-compat-ci")

    def session(self, sid: str) -> None:
        from persistence.conversation.sessions import NewSession

        self.handle.sessions.create(NewSession(session_id=sid, source="cli"))

    def terminal(self, sid: str) -> None:
        record, _ = self.handle.admissions.admit(
            epoch=self.epoch, principal_id="hermes-compat-ci",
            session_id=sid, request_id=f"req-{sid}",
            payload={"text": "synthetic compatibility test"},
        )
        claimed = self.handle.admissions.claim(epoch=self.epoch, session_id=sid)
        if claimed.admission_id != record.admission_id:
            raise AssertionError("Claimed a different admission")
        self.handle.admissions.settle(
            epoch=self.epoch, admission_id=claimed.admission_id,
            generation=claimed.generation, outcome="completed",
            result={"final_response": "synthetic answer"},
        )

    def close(self) -> None:
        from persistence_assembly import close_stores_under

        self.handle.close()
        close_stores_under(self.home)


class LegacyWriter:
    def __init__(self, home: Path):
        from hermes_state import SessionDB

        self.home = home
        self.rt = importlib.import_module("hermes_state_runtime")
        self.db = SessionDB(db_path=home / "state.db")
        self.epoch = self.rt.begin_runtime_epoch(self.db, instance_id="hermes-compat-ci")

    def session(self, sid: str) -> None:
        self.db.create_session(sid, "cli")

    def terminal(self, sid: str) -> None:
        record = self.rt.admit_session_input(
            self.db, epoch=self.epoch, principal_id="hermes-compat-ci",
            session_id=sid, request_id=f"req-{sid}",
            payload={"text": "synthetic compatibility test"},
        )
        claimed = self.rt.claim_session_input(self.db, epoch=self.epoch, session_id=sid)
        if claimed["admission_id"] != record["admission_id"]:
            raise AssertionError("Claimed a different admission")
        self.rt.settle_session_input(
            self.db, epoch=self.epoch,
            admission_id=claimed["admission_id"], generation=claimed["generation"],
            outcome="completed", result={"final_response": "synthetic answer"},
        )

    def close(self) -> None:
        self.db.close()


def verify_session_retirement() -> None:
    import api.models as models
    import api.profiles as profiles

    if not callable(getattr(models, "delete_cli_session", None)):
        raise AssertionError("WebUI session deletion API is unavailable")

    with tempfile.TemporaryDirectory(prefix="hermes-compat-ci-") as folder:
        home = Path(folder).resolve()
        if importlib.util.find_spec("persistence_assembly"):
            writer = StoreWriter(home)
        elif importlib.util.find_spec("hermes_state_runtime"):
            writer = LegacyWriter(home)
        else:
            raise AssertionError("No supported Agent runtime ledger producer; cannot certify this pair")

        sid = "synthetic-session-to-retire"
        other = "synthetic-bystander"
        try:
            writer.session(sid)
            writer.session(other)
            writer.terminal(sid)
        finally:
            writer.close()

        db = home / "state.db"
        with sqlite3.connect(str(db)) as conn:
            actual = conn.execute(
                "SELECT COUNT(*) FROM session_admissions WHERE target_session_id = ?",
                (sid,),
            ).fetchone()[0]
        if actual == 0:
            raise AssertionError("The synthetic session has no runtime ledger rows")

        original = profiles.get_active_hermes_home
        try:
            profiles.get_active_hermes_home = lambda: home
            result = models.delete_cli_session(sid)
        finally:
            profiles.get_active_hermes_home = original

        if result is not True:
            raise AssertionError("WebUI refused deletion of a completed gateway session")
        with sqlite3.connect(str(db)) as conn:
            remaining = {
                row[0] for row in conn.execute("SELECT id FROM sessions")
            }
        if sid in remaining or other not in remaining:
            raise AssertionError("Session deletion did not preserve the correct state")
        print("Completed gateway session deletion: PASS", flush=True)


def main() -> None:
    # Both checks run from WebUI on its isolated Compose network.
    assert_http("http://127.0.0.1:8787/health")
    assert_http("http://hermes-agent:8642/health")
    # Password auth must actually be enabled. API must reject anonymous sessions.
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/api/sessions", timeout=8) as response:
            status = response.status
    except urllib.error.HTTPError as exc:
        status = exc.code
    if status not in (401, 403):
        raise AssertionError(f"Unauthenticated WebUI sessions returned HTTP {status}")
    print("WebUI authentication gate: PASS", flush=True)
    verify_session_retirement()
    print("HERMES_PAIR_COMPATIBILITY: PASS", flush=True)


if __name__ == "__main__":
    main()
