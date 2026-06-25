import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CTX_ROUTE = ROOT / "bin" / "ctx-route"


class CompatSkewTests(unittest.TestCase):
    def run_route(self, base, *args, input_obj=None, check=True):
        env = {**os.environ, "CTX_BASE": str(base)}
        data = json.dumps(input_obj) if input_obj is not None else None
        result = subprocess.run(
            [sys.executable, str(CTX_ROUTE), *args],
            input=data,
            text=True,
            capture_output=True,
            env=env,
        )
        if check and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        return result

    def create_route(self, base, route_id, *, target_agent="capability", capabilities=None):
        args = [
            "create",
            "--route-id",
            route_id,
            "--target-site",
            "friend-linux",
            "--target-agent",
            target_agent,
            "--title-original",
            route_id,
        ]
        if capabilities:
            args.extend(["--capability", ",".join(capabilities)])
        return self.run_route(base, *args)

    def claim_route(self, base, route_id):
        return json.loads(self.run_route(
            base,
            "claim",
            route_id,
            "--device-id",
            "friend-linux",
            "--agent-id",
            "friend-linux:echo",
            "--instance-id",
            "friend-echo-1",
        ).stdout)

    def register_echo_profile(self, base):
        profile = {
            "schema": "ctx-agent-profile-v1",
            "agent_key": "friend/echo",
            "agent_id": "friend-linux:echo",
            "device_id": "friend-linux",
            "engine": {"name": "echo", "version": "0.1.0", "model": "local"},
            "kind": "executor",
            "capabilities": ["os.linux", "runtime.shell", "runtime.codex", "ctx.smoke", "ctx.route"],
            "constraints_supported": ["read_only_first", "no_secrets"],
            "transports": ["transport.local"],
            "audit_profile": {
                "result_link_kind": "strict",
                "expects_thread_id": False,
                "ephemeral_session": True,
            },
            "secret_capabilities": [],
            "red_lines": ["no_secret_values"],
        }
        self.run_route(base, "agent-register", "--profile-file", "-", input_obj=profile)
        return profile

    def upsert_friend_device(self, base):
        seen = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        self.run_route(
            base,
            "device-upsert",
            "--profile-file",
            "-",
            input_obj={
                "device_id": "friend-linux",
                "health": "up",
                "last_seen": seen,
                "agents": ["friend/echo"],
                "capabilities": ["os.linux", "runtime.shell", "ctx.smoke"],
                "links": ["transport.local"],
            },
        )

    def test_lease_graceful_fallback_for_old_clients_and_wrong_lease_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.create_route(base, "route_old_client")
            claim = self.claim_route(base, "route_old_client")
            self.assertTrue(claim["lease_id"].startswith("lease_"))

            # Old clients did not pass --lease-id. They must still pass by
            # agent_id + instance ownership instead of failing hard.
            self.run_route(
                base,
                "start",
                "route_old_client",
                "--agent-id",
                "friend-linux:echo",
                "--instance-id",
                "friend-echo-1",
            )
            reply = {
                "route_id": "route_old_client",
                "status": "replied",
                "executed_by": "friend-linux:echo",
                "summary": "old client reply ok",
                "evidence": [{"kind": "compat"}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.run_route(
                base,
                "reply",
                "route_old_client",
                "--reply-file",
                "-",
                "--agent-id",
                "friend-linux:echo",
                "--instance-id",
                "friend-echo-1",
                input_obj=reply,
            )

            self.create_route(base, "route_wrong_lease")
            self.claim_route(base, "route_wrong_lease")
            wrong = self.run_route(
                base,
                "start",
                "route_wrong_lease",
                "--agent-id",
                "friend-linux:echo",
                "--instance-id",
                "friend-echo-1",
                "--lease-id",
                "lease_wrong",
                check=False,
            )
            self.assertNotEqual(wrong.returncode, 0)
            self.assertIn("lease_id mismatch", wrong.stderr)

    def test_unknown_capability_is_loud_unroutable(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_echo_profile(base)
            self.create_route(base, "route_unknown_capability", capabilities=["capability.unknown"])
            result = self.run_route(base, "match", "route_unknown_capability", check=False)
            self.assertEqual(result.returncode, 2)
            report = json.loads(result.stdout)
            self.assertIn("unknown capability token", report["unroutable_reason"])
            self.assertEqual(report["eligible_agents"], [])

    def test_capability_target_and_named_target_both_match_registered_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_echo_profile(base)
            for route_id, target_agent in (
                ("route_capability_target", "capability"),
                ("route_named_target", "codex"),
            ):
                self.create_route(base, route_id, target_agent=target_agent, capabilities=["os.linux"])
                report = json.loads(self.run_route(base, "match", route_id).stdout)
                self.assertEqual(
                    [(item["agent_key"], item["agent_id"]) for item in report["eligible_agents"]],
                    [("friend/echo", "friend-linux:echo")],
                )

    def test_friend_node_minimal_smoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.upsert_friend_device(base)
            self.register_echo_profile(base)
            self.create_route(base, "route_friend_smoke", capabilities=["os.linux", "runtime.shell", "ctx.smoke"])
            match = json.loads(self.run_route(base, "match", "route_friend_smoke").stdout)
            self.assertEqual(match["eligible_agents"][0]["agent_key"], "friend/echo")
            claim = self.claim_route(base, "route_friend_smoke")
            self.run_route(
                base,
                "start",
                "route_friend_smoke",
                "--agent-id",
                "friend-linux:echo",
                "--instance-id",
                "friend-echo-1",
            )
            reply = {
                "route_id": "route_friend_smoke",
                "status": "replied",
                "executed_by": "friend-linux:echo",
                "summary": "friend smoke ok",
                "evidence": [{"kind": "smoke", "lease_id": claim["lease_id"]}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "temporary isolated ledger only",
                "next_action": "verify",
            }
            self.run_route(
                base,
                "reply",
                "route_friend_smoke",
                "--reply-file",
                "-",
                "--agent-id",
                "friend-linux:echo",
                "--instance-id",
                "friend-echo-1",
                input_obj=reply,
            )
            self.run_route(
                base,
                "verify",
                "route_friend_smoke",
                "--verified-by",
                "friend-smoke-test",
                "--verdict",
                "accepted",
                "--summary",
                "accepted",
            )
            doctor = json.loads(self.run_route(base, "doctor", "--json").stdout)
            self.assertEqual(doctor["health"], "ok")
            self.assertEqual(doctor["status_counts"], {"verified": 1})
            self.assertEqual(doctor["current_issue_counts"], {})


if __name__ == "__main__":
    unittest.main()
