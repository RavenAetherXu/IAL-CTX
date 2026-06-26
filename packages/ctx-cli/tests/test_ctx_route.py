import json
import os
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CTX_ROUTE = ROOT / "bin" / "ctx-route"


class CtxRouteTests(unittest.TestCase):
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

    def claim_route(
        self,
        base,
        route_id,
        *,
        device_id="lingxiaodian",
        agent_id="lingxiaodian:codex",
        instance_id=None,
        lease_seconds=None,
    ):
        args = ["claim", route_id, "--device-id", device_id, "--agent-id", agent_id]
        if instance_id:
            args.extend(["--instance-id", instance_id])
        if lease_seconds is not None:
            args.extend(["--lease-seconds", str(lease_seconds)])
        return json.loads(self.run_route(base, *args).stdout)

    def start_route(self, base, route_id, claim, *, agent_id="lingxiaodian:codex", instance_id=None):
        args = ["start", route_id, "--agent-id", agent_id]
        if instance_id:
            args.extend(["--instance-id", instance_id])
        if claim.get("lease_id"):
            args.extend(["--lease-id", claim["lease_id"]])
        return self.run_route(base, *args)

    def reply_route(self, base, route_id, claim, reply, *, agent_id="lingxiaodian:codex", instance_id=None):
        args = ["reply", route_id, "--reply-file", "-", "--agent-id", agent_id]
        if instance_id:
            args.extend(["--instance-id", instance_id])
        if claim.get("lease_id"):
            args.extend(["--lease-id", claim["lease_id"]])
        return self.run_route(base, *args, input_obj=reply)

    def expire_running_lease(self, base, route_id):
        path = base / "routes" / "running" / f"{route_id}.json"
        route = json.loads(path.read_text(encoding="utf-8"))
        route["lease"]["expires_at"] = "2000-01-01T00:00:00Z"
        path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

    def register_pi_profile(self, base, *, agent_key="test-device/pi", agent_id="test-device:pi", device_id="test-device"):
        profile = {
            "schema": "ctx-agent-profile-v1",
            "agent_key": agent_key,
            "agent_id": agent_id,
            "device_id": device_id,
            "engine": {"name": "pi", "version": "1.0.0"},
            "kind": "executor",
            "capabilities": ["os.linux", "runtime.pi", "ctx.route"],
            "constraints_supported": ["read_only_first", "no_secrets"],
            "transports": ["transport.local"],
            "availability": "test",
            "audit_profile": {
                "result_link_kind": "ctx-pi-reply-v1",
                "expects_thread_id": False,
                "ephemeral_session": True,
            },
            "secret_capabilities": [],
            "red_lines": ["metadata_first", "no_secret_values"],
        }
        self.run_route(base, "agent-register", "--profile-file", "-", input_obj=profile)
        return profile

    def register_codex_profile(self, base, *, agent_key="lingxiaodian/codex-test", agent_id="lingxiaodian:codex", device_id="lingxiaodian"):
        profile = {
            "schema": "ctx-agent-profile-v1",
            "agent_key": agent_key,
            "agent_id": agent_id,
            "device_id": device_id,
            "engine": {"name": "codex", "version": "1.0.0", "model": "gpt-test"},
            "kind": "executor",
            "capabilities": ["os.linux", "runtime.codex", "ctx.route"],
            "constraints_supported": ["read_only_first", "no_secrets"],
            "transports": ["transport.local"],
            "availability": "test",
            "audit_profile": {
                "result_link_kind": "ctx-codex-result",
                "expects_thread_id": True,
                "ephemeral_session": False,
                "thread_field": "codex_thread",
                "thread_id_field": "id",
                "thread_model_field": "model",
                "thread_id_output_field": "codex_thread_id",
                "thread_model_output_field": "codex_thread_model",
            },
            "secret_capabilities": [],
            "red_lines": ["metadata_first", "no_secret_values"],
        }
        self.run_route(base, "agent-register", "--profile-file", "-", input_obj=profile)
        return profile

    def register_neutral_executor_profile(self, base):
        profile = {
            "schema": "ctx-agent-profile-v1",
            "agent_key": "test-device/nova",
            "agent_id": "test-device:nova",
            "device_id": "test-device",
            "engine": {"name": "nova", "version": "1.0.0", "model": "nova-test"},
            "kind": "executor",
            "capabilities": ["os.linux", "runtime.shell", "ctx.route"],
            "constraints_supported": ["read_only_first", "no_secrets"],
            "transports": ["transport.local"],
            "availability": "test",
            "audit_profile": {
                "result_link_kind": "ctx-nova-result",
                "expects_thread_id": True,
                "ephemeral_session": False,
                "thread_field": "nova_session",
                "thread_id_field": "id",
                "thread_model_field": "model",
                "thread_id_output_field": "nova_thread_id",
                "thread_model_output_field": "nova_thread_model",
            },
            "secret_capabilities": [],
            "red_lines": ["metadata_first", "no_secret_values"],
        }
        self.run_route(base, "agent-register", "--profile-file", "-", input_obj=profile)
        return profile

    def register_frp_probe_profile(self, base):
        profile = {
            "schema": "ctx-agent-profile-v1",
            "agent_key": "huaguoshan/frp-probe",
            "agent_id": "huaguoshan-macos:frp-local-native",
            "device_id": "huaguoshan-macos",
            "engine": {"name": "shell", "version": "fixed-probe"},
            "kind": "probe",
            "capabilities": ["os.macos", "runtime.shell", "probe.read-only", "net.frp", "ctx.smoke"],
            "constraints_supported": ["read_only_first", "no_secrets"],
            "transports": ["frp-reverse-ssh:127.0.0.1:6022"],
            "availability": "test",
            "audit_profile": {
                "result_link_kind": "frp-command",
                "expects_thread_id": False,
                "ephemeral_session": True,
            },
            "secret_capabilities": [],
            "red_lines": [],
        }
        self.run_route(base, "agent-register", "--profile-file", "-", input_obj=profile)
        return profile

    def strip_claim_audit_snapshot(self, base, route_id):
        for state_dir in ("running", "done", "queued", "planned"):
            path = base / "routes" / state_dir / f"{route_id}.json"
            if path.exists():
                route = json.loads(path.read_text(encoding="utf-8"))
                route.pop("audit_profile_snapshot", None)
                route.pop("claim_audit_profile", None)
                lease = route.get("lease") if isinstance(route.get("lease"), dict) else {}
                lease.pop("audit_profile_snapshot", None)
                lease.pop("claim_audit_profile", None)
                lease.pop("agent_profile", None)
                path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")
                return
        self.fail(f"route not found for audit snapshot stripping: {route_id}")

    def test_lifecycle_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            created = self.run_route(
                base,
                "create",
                "--route-id",
                "route_test_0001",
                "--target-site",
                "lingxiaodian",
                "--target-agent",
                "codex",
                "--title-original",
                "test route",
                "--capability",
                "linux,codex",
            )
            self.assertEqual(json.loads(created.stdout)["status"], "queued")
            claim = self.claim_route(base, "route_test_0001", instance_id="instance-test-1")
            self.start_route(base, "route_test_0001", claim, instance_id="instance-test-1")
            reply = {
                "route_id": "route_test_0001",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_test_0001", claim, reply, instance_id="instance-test-1")
            self.run_route(base, "verify", "route_test_0001", "--verdict", "accepted", "--summary", "accepted")
            shown = self.run_route(base, "show", "route_test_0001")
            route = json.loads(shown.stdout)
            self.assertEqual(route["status"], "verified")
            self.assertEqual(route["trace_id"], "route_test_0001")
            self.assertEqual(route["lane_id"], "route_test_0001")
            self.assertEqual(route["lease"]["claim_instance_id"], "instance-test-1")
            self.assertEqual(route["events"][1]["instance_id"], "instance-test-1")
            self.assertEqual(route["events"][2]["instance_id"], "instance-test-1")
            self.assertEqual([event["type"] for event in route["events"]], [
                "route_created",
                "route_claimed",
                "action_started",
                "result_replied",
                "verification_completed",
            ])

    def test_reply_before_start_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_test_0002", "--target-site", "lingxiaodian", "--title-original", "test")
            reply = {"route_id": "route_test_0002", "status": "replied"}
            result = self.run_route(base, "reply", "route_test_0002", "--reply-file", "-", input_obj=reply, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("cannot receive reply", result.stderr)

    def test_doctor_flags_missing_claim_instance_after_rollout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_no_instance", "--target-site", "lingxiaodian", "--title-original", "test")
            self.run_route(base, "claim", "route_no_instance", "--device-id", "lingxiaodian", "--agent-id", "lingxiaodian:codex")
            report = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--claim-instance-required-after",
                "2000-01-01T00:00:00Z",
            ).stdout)
            missing = [item for item in report["issues"] if item["kind"] == "missing_claim_instance_id"]
            self.assertEqual(report["health"], "warn")
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0]["route_id"], "route_no_instance")

            self.run_route(base, "create", "--route-id", "route_with_instance", "--target-site", "lingxiaodian", "--title-original", "test")
            self.claim_route(base, "route_with_instance", instance_id="instance-ok")
            with_instance = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--claim-instance-required-after",
                "2000-01-01T00:00:00Z",
            ).stdout)
            missing_ids = {
                item["route_id"]
                for item in with_instance["issues"]
                if item["kind"] == "missing_claim_instance_id"
            }
            self.assertIn("route_no_instance", missing_ids)
            self.assertNotIn("route_with_instance", missing_ids)

    def test_policy_can_require_claim_instance_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--claim-instance-required",
                "true",
                "--updated-by",
                "test",
            ).stdout)
            self.assertTrue(policy["claim_instance_required"])
            self.run_route(base, "create", "--route-id", "route_requires_instance", "--target-site", "lingxiaodian", "--title-original", "test")
            missing = self.run_route(
                base,
                "claim",
                "route_requires_instance",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                check=False,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("missing required claim instance_id", missing.stderr)
            self.claim_route(base, "route_requires_instance", instance_id="instance-ok")
            route = json.loads(self.run_route(base, "show", "route_requires_instance").stdout)
            self.assertEqual(route["lease"]["claim_instance_id"], "instance-ok")

    def test_policy_and_doctor_expose_lane_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-active-routes-per-lane",
                "3",
                "--max-pending-routes-per-lane",
                "7",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["max_active_routes_per_lane"], 3)
            self.assertEqual(policy["max_pending_routes_per_lane"], 7)
            doctor = json.loads(self.run_route(base, "doctor", "--json").stdout)
            self.assertEqual(doctor["policy"]["max_active_routes_per_lane"], 3)
            self.assertEqual(doctor["policy"]["max_pending_routes_per_lane"], 7)
            self.assertTrue(doctor["policy"]["circuit_breaker_enabled"])
            self.assertEqual(doctor["policy"]["circuit_breaker_max_active_routes"], 4)
            self.assertEqual(doctor["policy"]["circuit_breaker_max_pending_routes"], 40)
            self.assertEqual(doctor["circuit_breaker"]["state"], "closed")

    def test_claim_allow_missing_instance_for_legacy_drills(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "policy", "--claim-instance-required", "true")
            self.run_route(base, "create", "--route-id", "route_legacy", "--target-site", "lingxiaodian", "--title-original", "legacy")
            self.run_route(
                base,
                "claim",
                "route_legacy",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--allow-missing-instance",
            )
            route = json.loads(self.run_route(base, "show", "route_legacy").stdout)
            self.assertIsNone(route["lease"]["claim_instance_id"])

    def test_agent_instance_filename_is_windows_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance:windows",
            )
            paths = list((base / "devices" / "agent-instances").glob("*.json"))
            self.assertEqual(len(paths), 1)
            self.assertNotIn(":", paths[0].name)
            self.assertIn("lingxiaodian_codex", paths[0].name)

    def test_claim_rejects_agent_process_with_stale_loaded_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "policy", "--claim-agent-code-current-required", "true")
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-stale-code",
                "--state",
                "active",
                "--started-at",
                "2026-06-14T07:00:00Z",
                "--tool-path",
                "/tmp/ctx-lingxiao-agent",
                "--tool-sha256",
                "b" * 64,
                "--tool-mtime",
                "2026-06-14T08:00:00Z",
                "--loaded-tool-sha256",
                "a" * 64,
                "--loaded-tool-mtime",
                "2026-06-14T07:00:00Z",
            )
            self.run_route(base, "create", "--route-id", "route_stale_code", "--target-site", "lingxiaodian", "--title-original", "stale code")
            blocked = self.run_route(
                base,
                "claim",
                "route_stale_code",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-stale-code",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("route not claimable", blocked.stderr)
            self.assertIn("loaded code differs", blocked.stderr)

    def test_release_requires_matching_claim_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_release", "--target-site", "lingxiaodian", "--title-original", "release")
            claim = self.claim_route(base, "route_release", instance_id="instance-owner")
            wrong = self.run_route(
                base,
                "release",
                "route_release",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-other",
                "--lease-id",
                claim["lease_id"],
                "--reason",
                "test wrong owner",
                check=False,
            )
            self.assertNotEqual(wrong.returncode, 0)
            self.assertIn("does not own", wrong.stderr)
            self.run_route(
                base,
                "release",
                "route_release",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-owner",
                "--lease-id",
                claim["lease_id"],
                "--reason",
                "test owner release",
            )
            route = json.loads(self.run_route(base, "show", "route_release").stdout)
            self.assertEqual(route["status"], "queued")
            self.assertIsNone(route["lease"])
            self.assertEqual(route["retry_count"], 1)
            self.assertEqual(route["events"][-1]["type"], "route_released")

    def test_start_and_reply_require_current_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_lease_guard", "--target-site", "lingxiaodian", "--title-original", "lease")
            claim = self.claim_route(base, "route_lease_guard", instance_id="instance-owner")
            wrong_start = self.run_route(
                base,
                "start",
                "route_lease_guard",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-owner",
                "--lease-id",
                "lease_wrong",
                check=False,
            )
            self.assertNotEqual(wrong_start.returncode, 0)
            self.assertIn("lease_id mismatch", wrong_start.stderr)

            self.start_route(base, "route_lease_guard", claim, instance_id="instance-owner")
            reply = {
                "route_id": "route_lease_guard",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            wrong_reply_lease = self.run_route(
                base,
                "reply",
                "route_lease_guard",
                "--reply-file",
                "-",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-owner",
                "--lease-id",
                "lease_wrong",
                input_obj=reply,
                check=False,
            )
            self.assertNotEqual(wrong_reply_lease.returncode, 0)
            self.assertIn("lease_id mismatch", wrong_reply_lease.stderr)

            wrong_reply_instance = self.run_route(
                base,
                "reply",
                "route_lease_guard",
                "--reply-file",
                "-",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-other",
                "--lease-id",
                claim["lease_id"],
                input_obj=reply,
                check=False,
            )
            self.assertNotEqual(wrong_reply_instance.returncode, 0)
            self.assertIn("instance_id does not own", wrong_reply_instance.stderr)
            self.reply_route(base, "route_lease_guard", claim, reply, instance_id="instance-owner")

    def test_claim_pins_registered_audit_profile_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_pi_profile(base)
            self.run_route(
                base,
                "device-upsert",
                "--profile-file",
                "-",
                input_obj={
                    "device_id": "test-device",
                    "health": "up",
                    "last_seen": "2026-06-23T00:00:00Z",
                    "agents": ["test-device/pi"],
                },
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_pinned_audit_profile",
                "--target-site",
                "test-device",
                "--target-agent",
                "capability",
                "--title-original",
                "pin audit profile",
                "--capability",
                "os.linux,runtime.pi,ctx.route",
            )
            claim = self.claim_route(
                base,
                "route_pinned_audit_profile",
                device_id="test-device",
                agent_id="test-device:pi",
                instance_id="instance-pinned-audit",
            )
            self.start_route(
                base,
                "route_pinned_audit_profile",
                claim,
                agent_id="test-device:pi",
                instance_id="instance-pinned-audit",
            )
            reply = {
                "schema": "ctx-pi-reply-v1",
                "route_id": "route_pinned_audit_profile",
                "status": "replied",
                "executed_by": "test-device:pi",
                "summary": "ok",
                "evidence": [{"kind": "unit-test"}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(
                base,
                "route_pinned_audit_profile",
                claim,
                reply,
                agent_id="test-device:pi",
                instance_id="instance-pinned-audit",
            )
            self.run_route(base, "verify", "route_pinned_audit_profile", "--verdict", "accepted", "--summary", "accepted")
            route = json.loads(self.run_route(base, "show", "route_pinned_audit_profile").stdout)
            self.assertEqual(route["lease"]["agent_key"], "test-device/pi")
            self.assertEqual(route["lease"]["audit_profile_snapshot"]["result_link_kind"], "ctx-pi-reply-v1")
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            issue_kinds = {issue["kind"] for issue in report["issues"]}
            self.assertNotIn("missing_audit_profile_snapshot", issue_kinds)
            self.assertNotIn("live_audit_profile_unpinned", issue_kinds)
            self.assertNotIn("missing_expected_result_link_kind", issue_kinds)
            self.assertEqual(report["health"], "ok")

    def test_claim_pins_audit_profile_with_legacy_capability_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_frp_probe_profile(base)
            self.run_route(
                base,
                "device-upsert",
                "--profile-file",
                "-",
                input_obj={
                    "device_id": "huaguoshan-macos",
                    "health": "up",
                    "last_seen": "2026-06-23T00:00:00Z",
                    "agents": ["frp-local-native"],
                },
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_legacy_frp_alias_audit",
                "--target-site",
                "huaguoshan-macos",
                "--target-agent",
                "frp-local-native",
                "--title-original",
                "legacy frp alias audit",
                "--capability",
                "macos,frp-reverse-ssh,read-only-probe,ctx-l2-smoke",
                "--constraint",
                "read_only_first,no_secrets",
            )
            claim = self.claim_route(
                base,
                "route_legacy_frp_alias_audit",
                device_id="huaguoshan-macos",
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id="instance-frp-alias-audit",
            )
            route = json.loads(self.run_route(base, "show", "route_legacy_frp_alias_audit").stdout)
            lease = route["lease"]
            self.assertEqual(claim["lease_id"], lease["lease_id"])
            self.assertEqual(lease["agent_key"], "huaguoshan/frp-probe")
            self.assertEqual(lease["audit_profile_snapshot"]["result_link_kind"], "frp-command")
            self.assertFalse(lease["audit_profile_snapshot"]["expects_thread_id"])
            self.assertEqual(lease["agent_profile_agent_id"], "huaguoshan-macos:frp-local-native")
            self.start_route(
                base,
                "route_legacy_frp_alias_audit",
                claim,
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id="instance-frp-alias-audit",
            )
            self.reply_route(
                base,
                "route_legacy_frp_alias_audit",
                claim,
                {
                    "route_id": "route_legacy_frp_alias_audit",
                    "status": "replied",
                    "executed_by": "huaguoshan-macos:frp-local-native",
                    "summary": "fixed probe completed",
                    "evidence": [{"kind": "frp-command", "value": "hostname", "exit_code": 0}],
                    "artifacts": [],
                    "secret_events": [],
                    "residual_risk": "fixed read-only probe",
                    "next_action": "verify",
                },
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id="instance-frp-alias-audit",
            )
            self.run_route(
                base,
                "verify",
                "route_legacy_frp_alias_audit",
                "--verified-by",
                "test:verifier",
                "--verdict",
                "accepted",
                "--summary",
                "accepted",
            )
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            route_issue_kinds = {
                item["kind"]
                for item in report["issues"]
                if item.get("route_id") == "route_legacy_frp_alias_audit"
            }
            self.assertNotIn("missing_expected_result_link_kind", route_issue_kinds)

    def test_legacy_route_without_audit_snapshot_still_reports_compatibly(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_pi_profile(base)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_legacy_unpinned_audit",
                "--target-site",
                "test-device",
                "--target-agent",
                "capability",
                "--title-original",
                "legacy unpinned audit",
                "--capability",
                "os.linux,runtime.pi,ctx.route",
            )
            claim = self.claim_route(
                base,
                "route_legacy_unpinned_audit",
                device_id="test-device",
                agent_id="test-device:pi",
                instance_id="instance-legacy-audit",
            )
            self.start_route(
                base,
                "route_legacy_unpinned_audit",
                claim,
                agent_id="test-device:pi",
                instance_id="instance-legacy-audit",
            )
            reply = {
                "schema": "ctx-pi-reply-v1",
                "route_id": "route_legacy_unpinned_audit",
                "status": "replied",
                "executed_by": "test-device:pi",
                "summary": "ok",
                "evidence": [{"kind": "unit-test"}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(
                base,
                "route_legacy_unpinned_audit",
                claim,
                reply,
                agent_id="test-device:pi",
                instance_id="instance-legacy-audit",
            )
            self.run_route(base, "verify", "route_legacy_unpinned_audit", "--verdict", "accepted", "--summary", "accepted")
            self.strip_claim_audit_snapshot(base, "route_legacy_unpinned_audit")
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            issues = [issue for issue in report["issues"] if issue.get("route_id") == "route_legacy_unpinned_audit"]
            self.assertIn("missing_audit_profile_snapshot", {issue["kind"] for issue in issues})

    def test_reply_schema_requires_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_test_0003", "--target-site", "lingxiaodian", "--title-original", "test")
            claim = self.claim_route(base, "route_test_0003")
            self.start_route(base, "route_test_0003", claim)
            reply = {
                "route_id": "route_test_0003",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "missing evidence",
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            result = self.run_route(base, "reply", "route_test_0003", "--reply-file", "-", input_obj=reply, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("reply missing required list field: evidence", result.stderr)

    def test_secret_shaped_route_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = self.run_route(
                base,
                "create",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "to" + "ken = should-not-write",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("secret-shaped", result.stderr)

    def test_device_upsert_merges_list_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = {
                "device_id": "huaguoshan-macos",
                "agents": ["local-native"],
                "capabilities": ["macos", "read-only-probe"],
                "transports": ["frp-return-link"],
                "red_lines": ["read_only_first"],
                "health": "up",
            }
            second = {
                "device_id": "huaguoshan-macos",
                "agents": ["codex"],
                "capabilities": ["codex", "codex-cli"],
                "transports": ["ssh-to-lingxiaodian"],
                "red_lines": ["no_unrestricted_remote_shell"],
                "health": "up",
            }
            self.run_route(base, "device-upsert", "--profile-file", "-", input_obj=first)
            self.run_route(base, "device-upsert", "--profile-file", "-", input_obj=second)
            shown = self.run_route(base, "devices", "--json")
            profile = json.loads(shown.stdout)[0]
            self.assertEqual(profile["agents"], ["local-native", "codex"])
            self.assertIn("read-only-probe", profile["capabilities"])
            self.assertIn("codex-cli", profile["capabilities"])

    def test_reply_to_inherits_trace_and_trace_lists_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_parent",
                "--target-site",
                "huaguoshan-macos",
                "--target-agent",
                "codex",
                "--title-original",
                "parent",
                "--trace-id",
                "trace_e2e",
                "--work-chat-id",
                "work_chat_alpha",
                "--context-id",
                "ctx_alpha",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_child",
                "--target-site",
                "lingxiaodian",
                "--target-agent",
                "codex",
                "--title-original",
                "child",
                "--reply-to",
                "route_parent",
            )
            child = json.loads(self.run_route(base, "show", "route_child").stdout)
            self.assertEqual(child["trace_id"], "trace_e2e")
            self.assertEqual(child["lane_id"], "work_chat_alpha")
            self.assertEqual(child["work_chat_id"], "work_chat_alpha")
            self.assertEqual(child["context_id"], "ctx_alpha")
            trace = json.loads(self.run_route(base, "trace", "route_parent", "--json").stdout)
            self.assertEqual(trace["trace_id"], "trace_e2e")
            self.assertEqual([route["route_id"] for route in trace["routes"]], ["route_parent", "route_child"])
            self.assertEqual([route["lane_id"] for route in trace["routes"]], ["work_chat_alpha", "work_chat_alpha"])

    def test_reply_to_rejects_conflicting_explicit_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_parent",
                "--target-site",
                "huaguoshan-macos",
                "--title-original",
                "parent",
                "--trace-id",
                "trace_parent",
            )
            result = self.run_route(
                base,
                "create",
                "--route-id",
                "route_child",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "child",
                "--reply-to",
                "route_parent",
                "--trace-id",
                "trace_other",
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("trace_id conflict", result.stderr)

    def test_reply_to_rejects_conflicting_lane_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_parent",
                "--target-site",
                "huaguoshan-macos",
                "--title-original",
                "parent",
                "--lane-id",
                "lane_parent",
                "--work-chat-id",
                "chat_parent",
                "--context-id",
                "ctx_parent",
            )
            lane_result = self.run_route(
                base,
                "create",
                "--route-id",
                "route_child_lane",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "child lane",
                "--reply-to",
                "route_parent",
                "--lane-id",
                "lane_other",
                check=False,
            )
            self.assertNotEqual(lane_result.returncode, 0)
            self.assertIn("lane_id conflict", lane_result.stderr)

            chat_result = self.run_route(
                base,
                "create",
                "--route-id",
                "route_child_chat",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "child chat",
                "--reply-to",
                "route_parent",
                "--work-chat-id",
                "chat_other",
                check=False,
            )
            self.assertNotEqual(chat_result.returncode, 0)
            self.assertIn("work_chat_id conflict", chat_result.stderr)

            context_result = self.run_route(
                base,
                "create",
                "--route-id",
                "route_child_context",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "child context",
                "--reply-to",
                "route_parent",
                "--context-id",
                "ctx_other",
                check=False,
            )
            self.assertNotEqual(context_result.returncode, 0)
            self.assertIn("context_id conflict", context_result.stderr)

    def test_trace_flags_cross_trace_reply_link_without_merging(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_parent",
                "--target-site",
                "huaguoshan-macos",
                "--title-original",
                "parent",
                "--trace-id",
                "trace_parent",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_child",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "child",
                "--trace-id",
                "trace_other",
            )
            child_path = base / "routes" / "queued" / "route_child.json"
            child = json.loads(child_path.read_text())
            child["reply_to"] = "route_parent"
            child_path.write_text(json.dumps(child), encoding="utf-8")
            trace = json.loads(self.run_route(base, "trace", "route_parent", "--json").stdout)
            self.assertEqual([route["route_id"] for route in trace["routes"]], ["route_parent"])
            self.assertEqual(trace["warnings"][0]["kind"], "cross_trace_reply_to")
            self.assertEqual(trace["warnings"][0]["route_id"], "route_child")

    def test_list_filters_by_lane_scope_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_scope_alpha",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "alpha",
                "--trace-id",
                "trace_alpha",
                "--lane-id",
                "lane_alpha",
                "--work-chat-id",
                "chat_alpha",
                "--context-id",
                "ctx_alpha",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_scope_beta",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "beta",
                "--trace-id",
                "trace_beta",
                "--lane-id",
                "lane_beta",
                "--work-chat-id",
                "chat_beta",
                "--context-id",
                "ctx_beta",
            )
            by_lane = json.loads(self.run_route(base, "list", "--json", "--lane-id", "lane_alpha").stdout)
            self.assertEqual([route["route_id"] for route in by_lane], ["route_scope_alpha"])
            by_chat = json.loads(self.run_route(base, "list", "--json", "--work-chat-id", "chat_beta").stdout)
            self.assertEqual([route["route_id"] for route in by_chat], ["route_scope_beta"])
            by_context = json.loads(self.run_route(base, "list", "--json", "--context-id", "ctx_alpha").stdout)
            self.assertEqual([route["route_id"] for route in by_context], ["route_scope_alpha"])
            by_trace = json.loads(self.run_route(base, "list", "--json", "--trace-id", "trace_beta").stdout)
            self.assertEqual([route["route_id"] for route in by_trace], ["route_scope_beta"])

    def test_trace_task_summary_redacts_secret_shaped_task_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            task_path = base / "done" / "task_redact.json"
            task_path.parent.mkdir(parents=True)
            task_path.write_text(
                json.dumps({
                    "task_id": "task_redact",
                    "status": "success",
                    "verdict": "success",
                    "summary": "to" + "ken = should-not-render",
                    "prompt": "must not be rendered",
                }),
                encoding="utf-8",
            )
            self.run_route(base, "create", "--route-id", "route_redact", "--target-site", "lingxiaodian", "--title-original", "redact")
            claim = self.claim_route(base, "route_redact")
            self.start_route(base, "route_redact", claim)
            reply = {
                "route_id": "route_redact",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [{"kind": "ctx-codex-result", "path": str(task_path)}],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_redact", claim, reply)
            trace = json.loads(self.run_route(base, "trace", "route_redact", "--json").stdout)
            self.assertEqual(trace["tasks"][0]["summary"], "[redacted-secret-shaped]")
            self.assertNotIn("prompt", trace["tasks"][0])

    def test_doctor_detects_expired_active_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_expired", "--target-site", "lingxiaodian", "--title-original", "expired")
            claim = self.claim_route(base, "route_expired")
            self.start_route(base, "route_expired", claim)
            self.expire_running_lease(base, "route_expired")
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            kinds = {item["kind"] for item in report["issues"]}
            self.assertIn("expired_active_lease", kinds)
            self.assertEqual(report["health"], "critical")

    def test_reconcile_dry_run_and_apply_requeues_expired_active_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_reconcile", "--target-site", "lingxiaodian", "--title-original", "reconcile")
            claim = self.claim_route(base, "route_reconcile", instance_id="instance-reconcile")
            self.start_route(base, "route_reconcile", claim, instance_id="instance-reconcile")
            self.expire_running_lease(base, "route_reconcile")

            dry = json.loads(self.run_route(base, "reconcile", "--json", "--dry-run").stdout)
            self.assertTrue(dry["dry_run"])
            self.assertEqual(dry["action_count"], 1)
            self.assertEqual(dry["actions"][0]["action"], "requeue")
            still_running = json.loads(self.run_route(base, "show", "route_reconcile").stdout)
            self.assertEqual(still_running["status"], "running")

            applied = json.loads(self.run_route(base, "reconcile", "--json").stdout)
            self.assertFalse(applied["dry_run"])
            self.assertEqual(applied["action_count"], 1)
            route = json.loads(self.run_route(base, "show", "route_reconcile").stdout)
            self.assertEqual(route["status"], "queued")
            self.assertIsNone(route["lease"])
            self.assertEqual(route["retry_count"], 1)
            self.assertIn("route_requeued", [event["type"] for event in route["events"]])
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            self.assertNotIn("expired_active_lease", {item["kind"] for item in report["issues"]})

    def test_claim_preflight_reconciles_expired_active_lease_before_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "policy",
                "--max-active-routes-total",
                "1",
                "--max-active-routes-per-target",
                "1",
                "--updated-by",
                "test",
            )
            self.run_route(base, "create", "--route-id", "route_old", "--target-site", "lingxiaodian", "--title-original", "old")
            old_claim = self.claim_route(base, "route_old", instance_id="instance-old")
            self.start_route(base, "route_old", old_claim, instance_id="instance-old")
            self.expire_running_lease(base, "route_old")
            self.run_route(base, "create", "--route-id", "route_new", "--target-site", "lingxiaodian", "--title-original", "new")
            claimed = json.loads(self.run_route(
                base,
                "claim",
                "route_new",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-new",
            ).stdout)
            self.assertEqual(claimed["status"], "claimed")
            self.assertEqual(claimed["reconciled_count"], 1)
            old = json.loads(self.run_route(base, "show", "route_old").stdout)
            self.assertEqual(old["status"], "queued")

    def test_policy_capacity_limits_active_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-active-routes-total",
                "1",
                "--max-active-routes-per-target",
                "1",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["max_active_routes_total"], 1)
            self.assertEqual(policy["max_active_routes_per_target"], 1)
            self.run_route(base, "create", "--route-id", "route_cap_1", "--target-site", "lingxiaodian", "--title-original", "cap1")
            self.run_route(
                base,
                "claim",
                "route_cap_1",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-cap-1",
            )
            self.run_route(base, "create", "--route-id", "route_cap_2", "--target-site", "lingxiaodian", "--title-original", "cap2")
            blocked = self.run_route(
                base,
                "claim",
                "route_cap_2",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-cap-2",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("route capacity exceeded", blocked.stderr)

    def test_policy_capacity_limits_pending_creates(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-pending-routes-per-target",
                "1",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["max_pending_routes_per_target"], 1)
            self.run_route(base, "create", "--route-id", "route_pending_1", "--target-site", "lingxiaodian", "--title-original", "pending1")
            blocked = self.run_route(
                base,
                "create",
                "--route-id",
                "route_pending_2",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "pending2",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("max_pending_routes_per_target=1", blocked.stderr)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_pending_codex",
                "--target-site",
                "lingxiaodian",
                "--target-agent",
                "codex",
                "--title-original",
                "pending codex",
            )

    def test_circuit_breaker_manual_open_blocks_create_and_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_before_breaker",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "before breaker",
            )
            opened = json.loads(self.run_route(
                base,
                "circuit-breaker",
                "open",
                "--json",
                "--severity",
                "warn",
                "--reason",
                "manual test open",
                "--by",
                "test",
            ).stdout)
            self.assertEqual(opened["state"], "open")
            self.assertEqual(opened["severity"], "warn")

            create_blocked = self.run_route(
                base,
                "create",
                "--route-id",
                "route_after_breaker",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "after breaker",
                check=False,
            )
            self.assertNotEqual(create_blocked.returncode, 0)
            self.assertIn("circuit breaker open", create_blocked.stderr)

            claim_blocked = self.run_route(
                base,
                "claim",
                "route_before_breaker",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-breaker",
                check=False,
            )
            self.assertNotEqual(claim_blocked.returncode, 0)
            self.assertIn("route not claimable: circuit breaker open", claim_blocked.stderr)

            doctor = json.loads(self.run_route(base, "doctor", "--json").stdout)
            self.assertEqual(doctor["health"], "warn")
            self.assertIn("circuit_breaker_open", {item["kind"] for item in doctor["issues"]})

            closed = json.loads(self.run_route(
                base,
                "circuit-breaker",
                "close",
                "--json",
                "--reason",
                "manual test close",
                "--by",
                "test",
            ).stdout)
            self.assertEqual(closed["state"], "closed")
            claimed = self.claim_route(base, "route_before_breaker", instance_id="instance-breaker")
            self.assertEqual(claimed["status"], "claimed")

    def test_circuit_breaker_auto_opens_on_pending_pressure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-pending-routes-per-target",
                "10",
                "--circuit-breaker-max-pending-routes",
                "1",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["circuit_breaker_max_pending_routes"], 1)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_pending_breaker_1",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "pending breaker 1",
            )
            blocked = self.run_route(
                base,
                "create",
                "--route-id",
                "route_pending_breaker_2",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "pending breaker 2",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("circuit breaker open", blocked.stderr)
            status = json.loads(self.run_route(base, "circuit-breaker", "status", "--json").stdout)
            self.assertEqual(status["state"], "open")
            self.assertEqual(status["severity"], "warn")
            self.assertEqual(status["last_trip"]["kind"], "route_pressure_threshold")
            self.assertEqual(status["last_trip"]["pending_routes"], 1)

    def test_circuit_breaker_evaluate_opens_on_doctor_critical(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_eval_breaker", "--target-site", "lingxiaodian", "--title-original", "eval")
            claim = self.claim_route(base, "route_eval_breaker", instance_id="instance-eval")
            self.start_route(base, "route_eval_breaker", claim, instance_id="instance-eval")
            reply = {
                "route_id": "route_eval_breaker",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_eval_breaker", claim, reply, instance_id="instance-eval")
            route_path = base / "routes" / "done" / "route_eval_breaker.json"
            route = json.loads(route_path.read_text(encoding="utf-8"))
            route["updated_at"] = "2000-01-01T00:00:00Z"
            route_path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

            result = json.loads(self.run_route(
                base,
                "circuit-breaker",
                "evaluate",
                "--json",
                "--open",
            ).stdout)
            self.assertEqual(result["state"]["state"], "open")
            self.assertEqual(result["state"]["severity"], "critical")
            trip_kinds = {item["kind"] for item in result["evaluation"]["trips"]}
            self.assertIn("doctor_current_critical", trip_kinds)

    def test_policy_capacity_limits_active_claims_per_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-active-routes-total",
                "10",
                "--max-active-routes-per-target",
                "10",
                "--max-active-routes-per-lane",
                "1",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["max_active_routes_per_lane"], 1)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_active_1",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane active 1",
                "--lane-id",
                "lane_alpha",
            )
            self.run_route(
                base,
                "claim",
                "route_lane_active_1",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-lane-1",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_active_2",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane active 2",
                "--lane-id",
                "lane_alpha",
            )
            blocked = self.run_route(
                base,
                "claim",
                "route_lane_active_2",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-lane-2",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("max_active_routes_per_lane=1", blocked.stderr)

            self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_active_beta",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane beta",
                "--lane-id",
                "lane_beta",
            )
            claimed = json.loads(self.run_route(
                base,
                "claim",
                "route_lane_active_beta",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--instance-id",
                "instance-lane-beta",
            ).stdout)
            self.assertEqual(claimed["lane_id"], "lane_beta")

    def test_policy_capacity_limits_pending_creates_per_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            policy = json.loads(self.run_route(
                base,
                "policy",
                "--json",
                "--max-pending-routes-per-target",
                "10",
                "--max-pending-routes-per-lane",
                "1",
                "--updated-by",
                "test",
            ).stdout)
            self.assertEqual(policy["max_pending_routes_per_lane"], 1)
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_pending_1",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane pending 1",
                "--lane-id",
                "lane_alpha",
            )
            blocked = self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_pending_2",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane pending 2",
                "--lane-id",
                "lane_alpha",
                check=False,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("max_pending_routes_per_lane=1", blocked.stderr)
            created = json.loads(self.run_route(
                base,
                "create",
                "--route-id",
                "route_lane_pending_beta",
                "--target-site",
                "lingxiaodian",
                "--title-original",
                "lane pending beta",
                "--lane-id",
                "lane_beta",
            ).stdout)
            self.assertEqual(created["lane_id"], "lane_beta")

    def test_doctor_detects_duplicate_route_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_dupe", "--target-site", "lingxiaodian", "--title-original", "dupe")
            queued = base / "routes" / "queued" / "route_dupe.json"
            done = base / "routes" / "done" / "route_dupe.json"
            done.parent.mkdir(parents=True, exist_ok=True)
            done.write_text(queued.read_text(), encoding="utf-8")
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            kinds = {item["kind"] for item in report["issues"]}
            self.assertIn("duplicate_route_record", kinds)
            self.assertEqual(report["health"], "critical")

    def test_doctor_exposes_ctx_codex_task_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_codex_profile(base)
            task_path = base / "done" / "task_link.json"
            task_path.parent.mkdir(parents=True)
            task_path.write_text(
                json.dumps({
                    "task_id": "task_link",
                    "status": "success",
                    "verdict": "success",
                    "summary": "ok",
                    "codex_thread": {"id": "thread_123", "model": "gpt-test"},
                }),
                encoding="utf-8",
            )
            self.run_route(base, "create", "--route-id", "route_link", "--target-site", "lingxiaodian", "--title-original", "link")
            claim = self.claim_route(base, "route_link")
            self.start_route(base, "route_link", claim)
            reply = {
                "route_id": "route_link",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [{"kind": "ctx-codex-run", "task_id": "task_link", "result_path": str(task_path), "ctx_status": "success"}],
                "artifacts": [{"kind": "ctx-codex-result", "path": str(task_path)}],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_link", claim, reply)
            report = json.loads(self.run_route(base, "doctor", "--json", "--unverified-warn-seconds", "999999").stdout)
            task_links = report["task_links"]
            self.assertTrue(any(link.get("task_id") == "task_link" for link in task_links))
            self.assertTrue(any(link.get("codex_thread_id") == "thread_123" for link in task_links))
            trace = json.loads(self.run_route(base, "trace", "route_link", "--json").stdout)
            refs = trace["routes"][0]["reply"]["task_refs"]
            self.assertTrue(any(ref.get("task_id") == "task_link" for ref in refs))

    def test_doctor_uses_non_codex_audit_profile_for_task_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.register_neutral_executor_profile(base)
            task_path = base / "done" / "task_nova.json"
            task_path.parent.mkdir(parents=True)
            task_path.write_text(
                json.dumps({
                    "task_id": "task_nova",
                    "status": "success",
                    "verdict": "success",
                    "summary": "ok",
                    "nova_session": {"id": "nova_thread_123", "model": "nova-test"},
                }),
                encoding="utf-8",
            )
            self.run_route(
                base,
                "create",
                "--route-id",
                "route_nova",
                "--target-site",
                "test-device",
                "--target-agent",
                "nova",
                "--title-original",
                "neutral executor link",
                "--capability",
                "runtime.shell",
            )
            claim = self.claim_route(base, "route_nova", device_id="test-device", agent_id="test-device:nova")
            self.start_route(base, "route_nova", claim, agent_id="test-device:nova")
            reply = {
                "route_id": "route_nova",
                "status": "replied",
                "executed_by": "test-device:nova",
                "summary": "ok",
                "evidence": [{"kind": "ctx-nova-result", "task_id": "task_nova", "result_path": str(task_path), "ctx_status": "success"}],
                "artifacts": [{"kind": "ctx-nova-result", "path": str(task_path)}],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_nova", claim, reply, agent_id="test-device:nova")
            report = json.loads(self.run_route(base, "doctor", "--json", "--unverified-warn-seconds", "999999").stdout)
            task_links = report["task_links"]
            self.assertTrue(any(link.get("task_id") == "task_nova" for link in task_links))
            self.assertTrue(any(link.get("nova_thread_id") == "nova_thread_123" for link in task_links))
            issue_kinds = {item["kind"] for item in report["issues"]}
            self.assertNotIn("missing_expected_result_link_kind", issue_kinds)
            self.assertNotIn("missing_expected_thread_id", issue_kinds)

    def test_dashboard_text_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_dash", "--target-site", "lingxiaodian", "--title-original", "dash")
            result = self.run_route(base, "dashboard")
            self.assertIn("CTX Route Doctor", result.stdout)
            self.assertIn("queued", result.stdout)

    def test_doctor_transport_probe_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            try:
                port = listener.getsockname()[1]
                report = json.loads(self.run_route(
                    base,
                    "doctor",
                    "--json",
                    "--transport-probe",
                    f"test-link=127.0.0.1:{port}",
                    "--transport-probe-timeout",
                    "0.2",
                ).stdout)
            finally:
                listener.close()
            self.assertTrue(report["transport_probes"][0]["ok"])
            self.assertNotIn("transport_probe_down", {item["kind"] for item in report["issues"]})

    def test_doctor_transport_probe_down(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            reserved = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            reserved.bind(("127.0.0.1", 0))
            port = reserved.getsockname()[1]
            reserved.close()
            report = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--transport-probe",
                f"test-link=127.0.0.1:{port}",
                "--transport-probe-timeout",
                "0.2",
            ).stdout)
            self.assertFalse(report["transport_probes"][0]["ok"])
            self.assertIn("transport_probe_down", {item["kind"] for item in report["issues"]})
            self.assertEqual(report["health"], "warn")

    def test_agent_heartbeat_duplicate_and_stale_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "instance-a",
                "--pid",
                "1001",
                "--hostname",
                "hua",
                "--started-at",
                "2026-06-14T00:00:00Z",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "instance-b",
                "--pid",
                "1002",
                "--hostname",
                "hua",
                "--started-at",
                "2026-06-14T00:00:01Z",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "profile-only",
                "--pid",
                "1003",
                "--hostname",
                "hua",
                "--started-at",
                "2026-06-14T00:00:02Z",
                "--state",
                "profile",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "stopped-once",
                "--pid",
                "1004",
                "--hostname",
                "hua",
                "--started-at",
                "2026-06-14T00:00:03Z",
                "--state",
                "stopped",
            )
            report = json.loads(self.run_route(base, "doctor", "--json", "--agent-stale-seconds", "999999").stdout)
            kinds = {item["kind"] for item in report["issues"]}
            self.assertEqual(report["agent_instance_count"], 4)
            self.assertIn("duplicate_active_agent_instances", kinds)
            duplicates = [item for item in report["issues"] if item["kind"] == "duplicate_active_agent_instances"]
            self.assertEqual(duplicates[0]["active_instance_count"], 2)
            self.assertTrue(any(item["agent_id"] == "huaguoshan-macos:local-native" for item in report["issues"]))
            states = {item["instance_id"]: item["state"] for item in report["agent_instances"]}
            self.assertEqual(states["profile-only"], "profile")
            self.assertEqual(states["stopped-once"], "stopped")

            instance_file = next((base / "devices" / "agent-instances").glob("*instance-a*.json"))
            instance = json.loads(instance_file.read_text())
            instance["last_seen"] = "2026-06-14T00:00:00Z"
            instance_file.write_text(json.dumps(instance), encoding="utf-8")
            instance_b_file = next((base / "devices" / "agent-instances").glob("*instance-b*.json"))
            instance_b = json.loads(instance_b_file.read_text())
            instance_b["started_at"] = "2026-06-13T23:59:00Z"
            instance_b_file.write_text(json.dumps(instance_b), encoding="utf-8")
            stale = json.loads(self.run_route(base, "doctor", "--json", "--agent-stale-seconds", "1").stdout)
            self.assertIn("stale_agent_instance", {item["kind"] for item in stale["issues"]})
            stale_ids = {item.get("instance_id") for item in stale["issues"] if item["kind"] == "stale_agent_instance"}
            self.assertNotIn("profile-only", stale_ids)
            self.assertNotIn("stopped-once", stale_ids)

    def test_agent_heartbeat_metrics_are_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            metrics = {
                "schema": "ctx-agent-route-metrics-v1",
                "call_count": 2,
                "failed_call_count": 0,
                "total_elapsed_ms": 123,
                "max_elapsed_ms": 100,
                "recent": [
                    {"operation": "device-upsert", "elapsed_ms": 23, "ok": True, "attempts": 1},
                    {"operation": "list", "elapsed_ms": 100, "ok": True, "attempts": 1},
                ],
            }
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "instance-metrics",
                "--state",
                "stopped",
                "--metrics-json",
                json.dumps(metrics),
            )
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            instance = report["agent_instances"][0]
            self.assertFalse(report["metric_events_loaded"])
            self.assertEqual(report["metric_event_count"], 0)
            self.assertEqual(instance["metrics"]["schema"], "ctx-agent-route-metrics-v1")
            self.assertEqual(instance["metrics"]["max_elapsed_ms"], 100)
            self.assertEqual(instance["metrics"]["recent"][1]["operation"], "list")
            metric_files = list((base / "metrics" / "route-calls").glob("*.json"))
            self.assertEqual(len(metric_files), 2)
            self.assertNotIn("agent_route_call_latency_high", {item["kind"] for item in report["issues"]})

            full_report = json.loads(self.run_route(base, "doctor", "--json", "--include-metric-events").stdout)
            self.assertTrue(full_report["metric_events_loaded"])
            self.assertEqual(full_report["metric_event_count"], 2)

            threshold_report = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--agent-latency-warn-ms",
                "50",
            ).stdout)
            self.assertFalse(threshold_report["metric_events_loaded"])
            self.assertEqual(threshold_report["metric_event_count"], 0)
            latency_issues = [
                item
                for item in threshold_report["issues"]
                if item["kind"] == "agent_route_call_latency_high"
            ]
            self.assertEqual(threshold_report["health"], "warn")
            self.assertEqual(len(latency_issues), 1)
            self.assertEqual(latency_issues[0]["max_elapsed_ms"], 100)
            self.assertEqual(latency_issues[0]["threshold_ms"], 50)
            self.assertEqual(latency_issues[0]["state"], "stopped")
            self.assertEqual(latency_issues[0]["max_operation"], "list")
            self.assertEqual(latency_issues[0]["max_attempts"], 1)
            windowed = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--agent-latency-warn-ms",
                "50",
                "--agent-latency-observed-after",
                "2026-06-14T00:00:00Z",
            ).stdout)
            self.assertTrue(windowed["metric_events_loaded"])
            self.assertEqual(windowed["metric_event_count"], 2)
            self.assertEqual(windowed["health"], "ok")
            self.assertNotIn("agent_route_call_latency_high", {item["kind"] for item in windowed["issues"]})

    def test_agent_heartbeat_code_fingerprint_and_rollout_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "instance-code",
                "--state",
                "stopped",
                "--tool-path",
                "/home/example/ctx-l2-tools/ctx-mac-agent",
                "--tool-sha256",
                "a" * 64,
                "--tool-mtime",
                "2026-06-14T04:00:00Z",
            )
            report = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--agent-code-required-after",
                "2000-01-01T00:00:00Z",
            ).stdout)
            instance = report["agent_instances"][0]
            self.assertEqual(instance["agent_code"]["sha256"], "a" * 64)
            self.assertNotIn("missing_agent_code_fingerprint", {item["kind"] for item in report["issues"]})

            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "instance-no-code",
                "--state",
                "active",
            )
            missing = json.loads(self.run_route(
                base,
                "doctor",
                "--json",
                "--agent-code-required-after",
                "2000-01-01T00:00:00Z",
            ).stdout)
            missing_issues = [
                item
                for item in missing["issues"]
                if item["kind"] == "missing_agent_code_fingerprint"
            ]
            self.assertEqual(missing["health"], "warn")
            self.assertEqual(len(missing_issues), 1)
            self.assertEqual(missing_issues[0]["instance_id"], "instance-no-code")
            self.assertEqual(missing_issues[0]["scope"], "current")

    def test_doctor_flags_agent_process_predating_tool_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "active-old-process",
                "--state",
                "active",
                "--started-at",
                "2026-06-14T07:35:33Z",
                "--tool-path",
                "/home/example/ctx-l2-tools/ctx-mac-agent",
                "--tool-sha256",
                "b" * 64,
                "--tool-mtime",
                "2026-06-14T08:10:15Z",
                "--loaded-tool-sha256",
                "a" * 64,
                "--loaded-tool-mtime",
                "2026-06-14T07:30:00Z",
            )
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            by_kind = {item["kind"]: item for item in report["issues"]}
            self.assertEqual(report["health"], "warn")
            self.assertEqual(by_kind["agent_process_predates_tool_code"]["scope"], "current")
            self.assertEqual(by_kind["agent_process_predates_tool_code"]["instance_id"], "active-old-process")
            self.assertEqual(by_kind["agent_loaded_code_differs_from_tool_file"]["scope"], "current")
            self.assertEqual(by_kind["agent_loaded_code_differs_from_tool_file"]["loaded_sha256"], "a" * 64)

    def test_stopped_agent_process_predating_tool_code_is_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "stopped-old-process",
                "--state",
                "stopped",
                "--started-at",
                "2026-06-14T07:35:33Z",
                "--tool-path",
                "/home/example/ctx-l2-tools/ctx-mac-agent",
                "--tool-sha256",
                "b" * 64,
                "--tool-mtime",
                "2026-06-14T08:10:15Z",
                "--loaded-tool-sha256",
                "a" * 64,
                "--loaded-tool-mtime",
                "2026-06-14T07:30:00Z",
            )
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            process_issues = [
                item for item in report["issues"]
                if item["kind"] == "agent_process_predates_tool_code"
            ]
            self.assertEqual(report["health"], "ok")
            self.assertEqual(len(process_issues), 1)
            self.assertEqual(process_issues[0]["scope"], "history")

    def test_newer_active_agent_supersedes_unretired_old_instance(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "old-active",
                "--state",
                "active",
                "--started-at",
                "2099-06-14T08:00:00Z",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:local-native",
                "--instance-id",
                "new-active",
                "--state",
                "active",
                "--started-at",
                "2099-06-14T08:05:00Z",
            )
            for path in (base / "devices" / "agent-instances").glob("*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("instance_id") == "old-active":
                    data["last_seen"] = "2099-06-14T08:04:00Z"
                if data.get("instance_id") == "new-active":
                    data["last_seen"] = "2099-06-14T08:06:00Z"
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            report = json.loads(self.run_route(base, "doctor", "--json").stdout)
            current_kinds = {
                item["kind"]
                for item in report["issues"]
                if item.get("scope") == "current"
            }
            superseded = [
                item for item in report["issues"]
                if item["kind"] == "superseded_agent_instance"
            ]
            self.assertEqual(report["health"], "ok")
            self.assertNotIn("duplicate_active_agent_instances", current_kinds)
            self.assertEqual(len(superseded), 1)
            self.assertEqual(superseded[0]["instance_id"], "old-active")
            self.assertEqual(superseded[0]["superseded_by"], "new-active")

    def test_expire_and_verify_stale_queued_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_stale", "--target-site", "huaguoshan-macos", "--title-original", "stale")
            self.run_route(base, "expire", "route_stale", "--reason", "test expiry")
            expired = json.loads(self.run_route(base, "show", "route_stale").stdout)
            self.assertEqual(expired["status"], "expired")
            self.assertEqual(expired["events"][-1]["type"], "route_expired")
            accepted = self.run_route(
                base,
                "verify",
                "route_stale",
                "--verdict",
                "accepted",
                "--summary",
                "expiry accepted",
                check=False,
            )
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn("cannot be accepted without a successful replied result", accepted.stderr)
            self.run_route(base, "verify", "route_stale", "--verdict", "rejected", "--summary", "expiry rejected")
            rejected = json.loads(self.run_route(base, "show", "route_stale").stdout)
            self.assertEqual(rejected["status"], "rejected")
            self.assertEqual(rejected["verification"]["verdict"], "rejected")

    def test_failed_reply_cannot_be_accepted_as_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_failed_verify", "--target-site", "lingxiaodian", "--title-original", "failed")
            claim = self.claim_route(base, "route_failed_verify", instance_id="instance-failed")
            self.start_route(base, "route_failed_verify", claim, instance_id="instance-failed")
            reply = {
                "route_id": "route_failed_verify",
                "status": "failed",
                "executed_by": "lingxiaodian:codex",
                "summary": "failed",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "failed",
                "next_action": "verify",
            }
            self.reply_route(base, "route_failed_verify", claim, reply, instance_id="instance-failed")
            accepted = self.run_route(
                base,
                "verify",
                "route_failed_verify",
                "--verdict",
                "accepted",
                "--summary",
                "should not verify",
                check=False,
            )
            self.assertNotEqual(accepted.returncode, 0)
            self.assertIn("cannot be accepted without a successful replied result", accepted.stderr)
            self.run_route(base, "verify", "route_failed_verify", "--verdict", "needs_followup", "--summary", "needs followup")
            route = json.loads(self.run_route(base, "show", "route_failed_verify").stdout)
            self.assertEqual(route["status"], "blocked")
            self.assertEqual(route["verification"]["verdict"], "needs_followup")

    def test_doctor_and_reconcile_strict_fail_on_unverified_terminal_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_unverified", "--target-site", "lingxiaodian", "--title-original", "unverified")
            claim = self.claim_route(base, "route_unverified", instance_id="instance-unverified")
            self.start_route(base, "route_unverified", claim, instance_id="instance-unverified")
            reply = {
                "route_id": "route_unverified",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_unverified", claim, reply, instance_id="instance-unverified")
            route_path = base / "routes" / "done" / "route_unverified.json"
            route = json.loads(route_path.read_text(encoding="utf-8"))
            route["updated_at"] = "2000-01-01T00:00:00Z"
            route_path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

            doctor = self.run_route(base, "doctor", "--json", "--strict", check=False)
            self.assertEqual(doctor.returncode, 2)
            doctor_report = json.loads(doctor.stdout)
            self.assertEqual(doctor_report["health"], "critical")
            self.assertIn("unverified_terminal_route", {item["kind"] for item in doctor_report["issues"]})

            reconcile = self.run_route(base, "reconcile", "--json", "--dry-run", "--strict", check=False)
            self.assertEqual(reconcile.returncode, 2)
            reconcile_report = json.loads(reconcile.stdout)
            self.assertIn("unverified_terminal_route", {item["kind"] for item in reconcile_report["observations"]})

    def test_reconcile_can_close_unverified_terminal_route_without_accepting(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_reconcile_verify", "--target-site", "lingxiaodian", "--title-original", "verify")
            claim = self.claim_route(base, "route_reconcile_verify", instance_id="instance-reconcile-verify")
            self.start_route(base, "route_reconcile_verify", claim, instance_id="instance-reconcile-verify")
            reply = {
                "route_id": "route_reconcile_verify",
                "status": "replied",
                "executed_by": "lingxiaodian:codex",
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(base, "route_reconcile_verify", claim, reply, instance_id="instance-reconcile-verify")
            route_path = base / "routes" / "done" / "route_reconcile_verify.json"
            route = json.loads(route_path.read_text(encoding="utf-8"))
            route["updated_at"] = "2000-01-01T00:00:00Z"
            route_path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

            dry = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--dry-run",
                "--terminal-verdict",
                "needs_followup",
            ).stdout)
            self.assertEqual(dry["action_count"], 1)
            self.assertEqual(dry["actions"][0]["action"], "verify_terminal")
            self.assertEqual(dry["actions"][0]["to_status"], "blocked")

            applied = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--terminal-verdict",
                "needs_followup",
                "--audit-run-id",
                "audit-terminal-test",
            ).stdout)
            self.assertEqual(applied["action_count"], 1)
            audit_path = Path(applied["actions"][0]["audit_path"])
            self.assertTrue(audit_path.exists())
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["audit_run_id"], "audit-terminal-test")
            self.assertEqual(audit["action"]["action"], "verify_terminal")
            self.assertEqual(audit["route_before"]["status"], "replied")
            route = json.loads(self.run_route(base, "show", "route_reconcile_verify").stdout)
            self.assertEqual(route["status"], "blocked")
            self.assertEqual(route["verification"]["verdict"], "needs_followup")
            self.assertIn("verification_completed", [event["type"] for event in route["events"]])

    def test_reconcile_can_reclassify_invalid_verified_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_invalid_verified", "--target-site", "lingxiaodian", "--title-original", "invalid")
            queued = base / "routes" / "queued" / "route_invalid_verified.json"
            done = base / "routes" / "done" / "route_invalid_verified.json"
            done.parent.mkdir(parents=True, exist_ok=True)
            route = json.loads(queued.read_text(encoding="utf-8"))
            route["status"] = "verified"
            route["updated_at"] = "2000-01-01T00:00:00Z"
            route["verification"] = {
                "verified_at": "2000-01-01T00:00:00Z",
                "verified_by": "test",
                "verdict": "accepted",
                "summary": "legacy invalid acceptance",
            }
            done.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")
            queued.unlink()

            doctor = json.loads(self.run_route(base, "doctor", "--json").stdout)
            self.assertIn("verified_without_successful_reply", {item["kind"] for item in doctor["issues"]})
            dry = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--dry-run",
                "--invalid-verified-verdict",
                "rejected",
            ).stdout)
            self.assertEqual(dry["action_count"], 1)
            self.assertEqual(dry["actions"][0]["action"], "reclassify_invalid_verified")
            self.assertEqual(dry["actions"][0]["to_status"], "rejected")

            applied = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--invalid-verified-verdict",
                "rejected",
                "--audit-run-id",
                "audit-invalid-verified-test",
            ).stdout)
            audit_path = Path(applied["actions"][0]["audit_path"])
            self.assertTrue(audit_path.exists())
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["audit_run_id"], "audit-invalid-verified-test")
            self.assertEqual(audit["action"]["action"], "reclassify_invalid_verified")
            self.assertEqual(audit["route_before"]["status"], "verified")
            route = json.loads(self.run_route(base, "show", "route_invalid_verified").stdout)
            self.assertEqual(route["status"], "rejected")
            self.assertEqual(route["verification"]["verdict"], "rejected")
            self.assertEqual(route["verification_history"][0]["verification"]["verdict"], "accepted")
            self.assertIn("verification_reclassified", [event["type"] for event in route["events"]])

    def test_reconcile_can_expire_stale_queued_route_with_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_stale_queued", "--target-site", "lingxiaodian", "--title-original", "stale queued")
            route_path = base / "routes" / "queued" / "route_stale_queued.json"
            route = json.loads(route_path.read_text(encoding="utf-8"))
            route["created_at"] = "2000-01-01T00:00:00Z"
            route["updated_at"] = "2000-01-01T00:00:00Z"
            route_path.write_text(json.dumps(route, ensure_ascii=False, indent=2), encoding="utf-8")

            default = json.loads(self.run_route(base, "reconcile", "--json", "--dry-run").stdout)
            self.assertEqual(default["action_count"], 0)
            self.assertEqual(default["observations"][0]["kind"], "stale_queued_route")

            dry = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--dry-run",
                "--stale-queued-action",
                "expire",
            ).stdout)
            self.assertEqual(dry["action_count"], 1)
            self.assertEqual(dry["actions"][0]["action"], "expire_stale_queued")
            self.assertEqual(dry["actions"][0]["to_status"], "expired")

            applied = json.loads(self.run_route(
                base,
                "reconcile",
                "--json",
                "--stale-queued-action",
                "expire",
                "--audit-run-id",
                "audit-stale-queued-test",
            ).stdout)
            self.assertEqual(applied["action_count"], 1)
            audit_path = Path(applied["actions"][0]["audit_path"])
            self.assertTrue(audit_path.exists())
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertEqual(audit["audit_run_id"], "audit-stale-queued-test")
            self.assertEqual(audit["route_before"]["status"], "queued")
            route = json.loads(self.run_route(base, "show", "route_stale_queued").stdout)
            self.assertEqual(route["status"], "expired")
            self.assertEqual(route["events"][-1]["type"], "route_expired")

    def test_requeue_requires_expired_active_lease(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.run_route(base, "create", "--route-id", "route_requeue", "--target-site", "lingxiaodian", "--title-original", "requeue")
            self.run_route(
                base,
                "claim",
                "route_requeue",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:codex",
                "--lease-seconds",
                "600",
            )
            result = self.run_route(base, "requeue", "route_requeue", "--reason", "not expired", check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("lease has not expired", result.stderr)
            self.run_route(base, "requeue", "route_requeue", "--reason", "human reviewed", "--force")
            route = json.loads(self.run_route(base, "show", "route_requeue").stdout)
            self.assertEqual(route["status"], "queued")
            self.assertEqual(route["retry_count"], 1)
            self.assertIsNone(route["lease"])

    def test_drill_covers_failures_and_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            drill_base = base / "drill-ledger"
            report = json.loads(self.run_route(
                base,
                "drill",
                "--json",
                "--strict",
                "--base",
                str(drill_base),
                "--transport-probe-timeout",
                "0.2",
            ).stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["failed_check_count"], 0)
            self.assertEqual(report["final_doctor"]["health"], "ok")
            check_names = {item["name"] for item in report["checks"]}
            self.assertIn("expired_active_lease_detected", check_names)
            self.assertIn("duplicate_route_record_detected", check_names)
            self.assertIn("ctx_codex_thread_mapping_visible", check_names)
            self.assertIn("transport_probe_reports_ok_and_down", check_names)
            self.assertTrue((drill_base / "routes" / "done" / "route_drill_happy.json").exists())

    def test_stability_create_report_and_auto_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            created = json.loads(self.run_route(
                base,
                "stability-create",
                "--json",
                "--batch-id",
                "batch_test",
                "--trace-id",
                "trace_batch_test",
                "--work-chat-id",
                "chat_batch_test",
                "--context-id",
                "ctx_batch_test",
                "--count",
                "2",
                "--target-site",
                "lingxiaodian",
                "--target-agent",
                "local-native",
                "--probe",
                "",
            ).stdout)
            self.assertEqual(created["count"], 2)
            self.assertEqual(created["trace_id"], "trace_batch_test")
            self.assertEqual(created["lane_id"], "chat_batch_test")
            self.assertEqual(created["work_chat_id"], "chat_batch_test")
            self.assertEqual(created["context_id"], "ctx_batch_test")
            route_ids = [item["route_id"] for item in created["routes"]]
            self.assertEqual({item["lane_id"] for item in created["routes"]}, {"chat_batch_test"})
            instance_ids = []
            for index, route_id in enumerate(route_ids, start=1):
                instance_id = f"instance-{index}"
                instance_ids.append(instance_id)
                route_created_at = json.loads(self.run_route(base, "show", route_id).stdout)["created_at"]
                metrics = {
                    "schema": "ctx-agent-route-metrics-v1",
                    "call_count": 4,
                    "failed_call_count": 0,
                    "total_elapsed_ms": 80,
                    "max_elapsed_ms": 3000,
                    "recent": [
                        {
                            "operation": "reply",
                            "elapsed_ms": 30,
                            "ok": True,
                            "attempts": 1,
                            "observed_at": route_created_at,
                        }
                    ],
                }
                self.run_route(
                    base,
                    "agent-heartbeat",
                    "--device-id",
                    "lingxiaodian",
                    "--agent-id",
                    "lingxiaodian:local-native",
                    "--instance-id",
                    instance_id,
                    "--state",
                    "stopped",
                    "--tool-path",
                    "/tmp/ctx-agent",
                    "--tool-sha256",
                    "b" * 64,
                    "--tool-mtime",
                    "2026-06-14T00:00:00Z",
                    "--metrics-json",
                    json.dumps(metrics),
                )
                claim = self.claim_route(
                    base,
                    route_id,
                    device_id="lingxiaodian",
                    agent_id="lingxiaodian:local-native",
                    instance_id=instance_id,
                )
                self.start_route(
                    base,
                    route_id,
                    claim,
                    agent_id="lingxiaodian:local-native",
                    instance_id=instance_id,
                )
                reply = {
                    "route_id": route_id,
                    "status": "replied",
                    "executed_by": "lingxiaodian:local-native",
                    "summary": "stability route completed",
                    "evidence": [{"kind": "synthetic-stability", "index": index}],
                    "artifacts": [],
                    "secret_events": [],
                    "residual_risk": "synthetic isolated ledger only",
                    "next_action": "verify",
                }
                self.reply_route(
                    base,
                    route_id,
                    claim,
                    reply,
                    agent_id="lingxiaodian:local-native",
                    instance_id=instance_id,
                )

            pending_report = json.loads(self.run_route(
                base,
                "stability-report",
                "--json",
                "--trace-id",
                "trace_batch_test",
                "--agent-latency-warn-ms",
                "1000",
            ).stdout)
            self.assertFalse(pending_report["ok"])
            gate_check = [
                check for check in pending_report["checks"]
                if check["name"] == "all_routes_replied_or_verified"
            ][0]
            self.assertFalse(gate_check["ok"])
            self.assertEqual(gate_check["replied_or_verified"], 0)

            report = json.loads(self.run_route(
                base,
                "stability-report",
                "--json",
                "--trace-id",
                "trace_batch_test",
                "--auto-verify",
                "--agent-latency-warn-ms",
                "1000",
            ).stdout)
            self.assertTrue(report["ok"])
            self.assertEqual(report["failed_check_count"], 0)
            self.assertEqual(len(report["verification_results"]), 2)
            self.assertEqual({route["status"] for route in report["routes"]}, {"verified"})
            self.assertEqual({route["trace_id"] for route in report["routes"]}, {"trace_batch_test"})
            self.assertEqual({route["lane_id"] for route in report["routes"]}, {"chat_batch_test"})
            self.assertEqual({route["work_chat_id"] for route in report["routes"]}, {"chat_batch_test"})
            self.assertEqual({route["context_id"] for route in report["routes"]}, {"ctx_batch_test"})
            self.assertEqual({route["agent_code_sha256"] for route in report["routes"]}, {"b" * 64})
            self.assertEqual({route["route_call_max_elapsed_ms"] for route in report["routes"]}, {30})
            self.assertEqual({route["route_call_max_operation"] for route in report["routes"]}, {"reply"})
            self.assertEqual({route["route_call_max_attempts"] for route in report["routes"]}, {1})
            self.assertEqual({route["route_call_latency_scope"] for route in report["routes"]}, {"metric_ledger_since"})
            self.assertTrue(all(route["route_call_metric_event_id"] for route in report["routes"]))
            self.assertTrue(all(route["route_call_metric_path"] for route in report["routes"]))
            self.assertTrue(all(check["ok"] for check in report["checks"]))

            stale_metrics = {
                "schema": "ctx-agent-route-metrics-v1",
                "call_count": 5,
                "failed_call_count": 0,
                "total_elapsed_ms": 100,
                "max_elapsed_ms": 3000,
                "recent": [
                    {
                        "operation": "list",
                        "elapsed_ms": 20,
                        "ok": True,
                        "attempts": 1,
                        "observed_at": "2099-01-01T00:00:00Z",
                    }
                ],
            }
            for instance_id in instance_ids:
                self.run_route(
                    base,
                    "agent-heartbeat",
                    "--device-id",
                    "lingxiaodian",
                    "--agent-id",
                    "lingxiaodian:local-native",
                    "--instance-id",
                    instance_id,
                    "--state",
                    "stopped",
                    "--tool-path",
                    "/tmp/ctx-agent",
                    "--tool-sha256",
                    "b" * 64,
                    "--tool-mtime",
                    "2026-06-14T00:00:00Z",
                    "--metrics-json",
                    json.dumps(stale_metrics),
                )
            preserved_latency = json.loads(self.run_route(
                base,
                "stability-report",
                "--json",
                "--trace-id",
                "trace_batch_test",
                "--agent-latency-warn-ms",
                "1000",
            ).stdout)
            latency_check = [
                check for check in preserved_latency["checks"]
                if check["name"] == "route_call_latency_within_threshold"
            ][0]
            self.assertTrue(preserved_latency["ok"])
            self.assertTrue(latency_check["ok"])
            self.assertEqual(len(latency_check["missing_evidence"]), 0)
            self.assertEqual({route["route_call_max_elapsed_ms"] for route in preserved_latency["routes"]}, {30})
            self.assertEqual({route["route_call_latency_scope"] for route in preserved_latency["routes"]}, {"metric_ledger_since"})

    def test_stability_report_does_not_auto_accept_failed_reply(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            route_id = "route_failed_reply"
            instance_id = "instance-failed-reply"
            self.run_route(
                base,
                "create",
                "--route-id",
                route_id,
                "--trace-id",
                "trace_failed_reply",
                "--target-site",
                "huaguoshan-macos",
                "--target-agent",
                "frp-local-native",
                "--title-original",
                "failed reply should not auto accept",
                "--capability",
                "macos",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "huaguoshan-macos",
                "--agent-id",
                "huaguoshan-macos:frp-local-native",
                "--instance-id",
                instance_id,
                "--state",
                "stopped",
                "--tool-path",
                "/tmp/ctx-huaguoshan-frp-agent",
                "--tool-sha256",
                "c" * 64,
                "--tool-mtime",
                "2026-06-14T00:00:00Z",
            )
            claim = self.claim_route(
                base,
                route_id,
                device_id="huaguoshan-macos",
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id=instance_id,
            )
            self.start_route(
                base,
                route_id,
                claim,
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id=instance_id,
            )
            reply = {
                "route_id": route_id,
                "status": "failed",
                "executed_by": "huaguoshan-macos:frp-local-native",
                "summary": "frp mac-basic-status failed: failed_command=hostname exit=124",
                "evidence": [{"kind": "frp-command", "exit_code": 124, "stderr_excerpt": "TimeoutExpired"}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "no public SSH ledger path was used",
                "next_action": "verify",
            }
            self.reply_route(
                base,
                route_id,
                claim,
                reply,
                agent_id="huaguoshan-macos:frp-local-native",
                instance_id=instance_id,
            )
            report = json.loads(self.run_route(
                base,
                "stability-report",
                "--json",
                "--trace-id",
                "trace_failed_reply",
                "--auto-verify",
                "--non-replied-verdict",
                "needs_followup",
            ).stdout)
            self.assertFalse(report["ok"])
            self.assertEqual(report["verification_results"][0]["verdict"], "needs_followup")
            self.assertEqual(report["verification_results"][0]["status"], "blocked")
            failed_check = [
                check for check in report["checks"]
                if check["name"] == "all_routes_replied_or_verified"
            ][0]
            self.assertFalse(failed_check["ok"])
            self.assertEqual(failed_check["failed_reply_statuses"][0]["reply_status"], "failed")
            self.assertEqual(report["routes"][0]["status"], "blocked")
            self.assertEqual(report["routes"][0]["reply_status"], "failed")

    def test_stability_report_fails_when_circuit_breaker_is_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            route_id = "route_stability_breaker"
            trace_id = "trace_stability_breaker"
            instance_id = "instance-stability-breaker"
            self.run_route(
                base,
                "create",
                "--route-id",
                route_id,
                "--trace-id",
                trace_id,
                "--target-site",
                "lingxiaodian",
                "--target-agent",
                "local-native",
                "--title-original",
                "stability breaker",
            )
            self.run_route(
                base,
                "agent-heartbeat",
                "--device-id",
                "lingxiaodian",
                "--agent-id",
                "lingxiaodian:local-native",
                "--instance-id",
                instance_id,
                "--state",
                "stopped",
                "--tool-path",
                "/tmp/ctx-agent",
                "--tool-sha256",
                "d" * 64,
                "--tool-mtime",
                "2026-06-14T00:00:00Z",
            )
            claim = self.claim_route(
                base,
                route_id,
                device_id="lingxiaodian",
                agent_id="lingxiaodian:local-native",
                instance_id=instance_id,
            )
            self.start_route(
                base,
                route_id,
                claim,
                agent_id="lingxiaodian:local-native",
                instance_id=instance_id,
            )
            reply = {
                "route_id": route_id,
                "status": "replied",
                "executed_by": "lingxiaodian:local-native",
                "summary": "ok",
                "evidence": [{"kind": "test"}],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }
            self.reply_route(
                base,
                route_id,
                claim,
                reply,
                agent_id="lingxiaodian:local-native",
                instance_id=instance_id,
            )
            self.run_route(base, "verify", route_id, "--verdict", "accepted", "--summary", "accepted")
            self.run_route(
                base,
                "circuit-breaker",
                "open",
                "--reason",
                "stability gate test",
                "--severity",
                "warn",
            )

            report = json.loads(self.run_route(
                base,
                "stability-report",
                "--json",
                "--trace-id",
                trace_id,
            ).stdout)
            self.assertFalse(report["ok"])
            circuit_check = [
                check for check in report["checks"]
                if check["name"] == "circuit_breaker_closed"
            ][0]
            self.assertFalse(circuit_check["ok"])
            self.assertEqual(circuit_check["state"], "open")


if __name__ == "__main__":
    unittest.main()
