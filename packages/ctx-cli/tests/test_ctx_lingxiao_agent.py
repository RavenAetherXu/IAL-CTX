import importlib.util
from importlib.machinery import SourceFileLoader
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "bin" / "ctx-lingxiao-agent"
MAC_AGENT = ROOT / "bin" / "ctx-mac-agent"
MAC_CODEX_AGENT = ROOT / "bin" / "ctx-mac-codex-agent"
HGS_FRP_AGENT = ROOT / "bin" / "ctx-huaguoshan-frp-agent"
HGS_PI_BRIDGE = ROOT / "bin" / "ctx-huaguoshan-pi-bridge"
LX_WORKER = ROOT / "bin" / "ctx-lx-worker"


def load_agent():
    loader = SourceFileLoader("ctx_lingxiao_agent", str(AGENT))
    spec = importlib.util.spec_from_loader("ctx_lingxiao_agent", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_mac_agent():
    loader = SourceFileLoader("ctx_mac_agent", str(MAC_AGENT))
    spec = importlib.util.spec_from_loader("ctx_mac_agent", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_mac_codex_agent():
    loader = SourceFileLoader("ctx_mac_codex_agent", str(MAC_CODEX_AGENT))
    spec = importlib.util.spec_from_loader("ctx_mac_codex_agent", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_hgs_frp_agent():
    loader = SourceFileLoader("ctx_huaguoshan_frp_agent", str(HGS_FRP_AGENT))
    spec = importlib.util.spec_from_loader("ctx_huaguoshan_frp_agent", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_hgs_pi_bridge():
    loader = SourceFileLoader("ctx_huaguoshan_pi_bridge", str(HGS_PI_BRIDGE))
    spec = importlib.util.spec_from_loader("ctx_huaguoshan_pi_bridge", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_lx_worker():
    loader = SourceFileLoader("ctx_lx_worker", str(LX_WORKER))
    spec = importlib.util.spec_from_loader("ctx_lx_worker", loader)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LingxiaoAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = load_agent()

    def eligible_route(self):
        return {
            "route_id": "route_test",
            "status": "queued",
            "target_site": "lingxiaodian",
            "target_agent": "codex",
            "task_kind": "inspect",
            "approval_required": False,
            "secret_capabilities": [],
            "required_capabilities": ["os.linux", "runtime.codex"],
            "constraints": ["read_only_first", "no_secrets"],
            "cwd": "/tmp",
            "title_original": "inspect",
        }

    def test_eligible_route(self):
        ok, reason = self.agent.route_eligible(self.eligible_route())
        self.assertTrue(ok, reason)

    def test_approval_required_rejected(self):
        route = self.eligible_route()
        route["approval_required"] = True
        ok, reason = self.agent.route_eligible(route)
        self.assertFalse(ok)
        self.assertIn("approval", reason)

    def test_operate_rejected(self):
        # Per CTX-CORE-BASELINE: task_kind safety gating lives at the EXECUTOR adapter,
        # not the neutral central claimant (which routes purely by capability).
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_op", "status": "queued",
            "target_site": "huaguoshan-macos", "target_agent": "codex",
            "task_kind": "operate", "approval_required": False, "secret_capabilities": [],
            "required_capabilities": ["read-only-inspect"],
            "constraints": ["read_only_first", "no_secrets"],
            "cwd": "/tmp",
        }
        ok, reason = mac_codex.route_eligible(route)
        self.assertFalse(ok)
        self.assertIn("task_kind", reason)

    def test_audit_handoff_route_allowed(self):
        route = self.eligible_route()
        route["task_kind"] = "audit_handoff"
        route["required_capabilities"] = ["ctx.route"]
        ok, reason = self.agent.route_eligible(route)
        self.assertTrue(ok, reason)

    def test_sensitive_cwd_rejected(self):
        # Per CTX-CORE-BASELINE: cwd safety lives at the EXECUTOR adapter (it runs code),
        # not the central claimant.
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_cwd", "status": "queued",
            "target_site": "huaguoshan-macos", "target_agent": "codex",
            "task_kind": "inspect", "approval_required": False, "secret_capabilities": [],
            "required_capabilities": ["read-only-inspect"],
            "constraints": ["read_only_first", "no_secrets"],
            "cwd": str(Path.home() / ".ssh"),
        }
        ok, reason = mac_codex.route_eligible(route)
        self.assertFalse(ok)
        self.assertIn("blocked cwd", reason)

    def test_lingxiao_task_contains_ctx_identity(self):
        route = self.eligible_route()
        route.update({
            "trace_id": "trace_alpha",
            "lane_id": "lane_alpha",
            "work_chat_id": "chat_alpha",
            "context_id": "ctx_alpha",
        })
        task = self.agent.route_task(route)
        self.assertIn("CTX-CALL-IDENTITY:", task)
        self.assertIn("CTX-EXECUTOR: lingxiaodian:codex", task)
        self.assertIn("CTX-SESSION-VISIBILITY: persisted", task)
        self.assertIn('"lane_id": "lane_alpha"', task)
        self.assertIn('"work_chat_id": "chat_alpha"', task)
        self.assertIn('"context_id": "ctx_alpha"', task)

    def test_lingxiao_timeout_summary_does_not_echo_prompt(self):
        summary = self.agent.summarize_ctx_codex_result(
            "timeout",
            {"summary": "Handle this CTX L2 route as Lingxiaodian local Codex."},
            {"stdout_tail": "\n".join([
                "task_id: task_test_timeout",
                "status: timeout",
                "exit_code: 1",
                "review reached final checks but timed out before closeout",
                "---",
                "Handle this CTX L2 route as Lingxiaodian local Codex.",
            ])},
            180,
        )
        self.assertIn("ctx-codex timed out", summary)
        self.assertIn("180s", summary)
        self.assertIn("task_id: task_test_timeout", summary)
        self.assertIn("status: timeout", summary)
        self.assertNotIn("review reached final checks", summary)
        self.assertNotIn("Handle this CTX L2 route", summary)

    def test_lingxiao_agent_heartbeat_has_instance_identity(self):
        original_run_json = self.agent.run_json
        calls = []

        def fake_run_json(args, input_obj=None, timeout=30):
            calls.append(args)
            return {"ok": True}

        self.agent.run_json = fake_run_json
        try:
            self.agent.agent_heartbeat()
        finally:
            self.agent.run_json = original_run_json
        heartbeat = calls[0]
        self.assertEqual(heartbeat[0], "agent-heartbeat")
        self.assertIn("--instance-id", heartbeat)
        self.assertIn("--pid", heartbeat)
        self.assertIn("--state", heartbeat)
        self.assertIn("active", heartbeat)
        self.assertIn("--metrics-json", heartbeat)
        self.assertIn("--tool-sha256", heartbeat)
        self.assertIn("--tool-mtime", heartbeat)
        self.assertIn("--loaded-tool-sha256", heartbeat)
        self.assertIn("--loaded-tool-mtime", heartbeat)
        self.assertIn("lingxiaodian-ctx-codex-claimant", heartbeat)

    def test_lingxiao_once_retires_instance(self):
        original_run_json = self.agent.run_json
        calls = []

        def fake_run_json(args, input_obj=None, timeout=30):
            calls.append(args)
            if args and args[0] == "list":
                return []
            return {"ok": True}

        self.agent.run_json = fake_run_json
        try:
            self.agent.run_once(type("Args", (), {"timeout": 120})())
        finally:
            self.agent.run_json = original_run_json
        heartbeat_states = [
            call[call.index("--state") + 1]
            for call in calls
            if call and call[0] == "agent-heartbeat" and "--state" in call
        ]
        self.assertEqual(heartbeat_states, ["active", "stopped"])

    def test_lingxiao_agent_skips_claim_race(self):
        original_run_json = self.agent.run_json
        original_run_ctx_codex = self.agent.run_ctx_codex

        def fake_run_json(args, input_obj=None, timeout=30):
            if args and args[0] == "claim":
                raise RuntimeError("route not claimable: route_test status=claimed")
            return {}

        def fail_run_ctx_codex(route, timeout):
            raise AssertionError("ctx-codex should not run after claim race")

        self.agent.run_json = fake_run_json
        self.agent.run_ctx_codex = fail_run_ctx_codex
        try:
            self.assertFalse(self.agent.process_route(self.eligible_route(), 120))
        finally:
            self.agent.run_json = original_run_json
            self.agent.run_ctx_codex = original_run_ctx_codex

    def test_lingxiao_process_route_passes_instance_id(self):
        original_run_json = self.agent.run_json
        original_run_ctx_codex = self.agent.run_ctx_codex
        calls = []

        def fake_run_json(args, input_obj=None, timeout=30):
            calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-lingxiao-test"}
            if args and args[0] == "show":
                return {"route_id": "route_test", "status": "running"}
            return {}

        def fake_run_ctx_codex(route, timeout):
            return {
                "route_id": route["route_id"],
                "status": "replied",
                "executed_by": self.agent.AGENT_ID,
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }

        self.agent.run_json = fake_run_json
        self.agent.run_ctx_codex = fake_run_ctx_codex
        try:
            self.assertTrue(self.agent.process_route(self.eligible_route(), 120))
        finally:
            self.agent.run_json = original_run_json
            self.agent.run_ctx_codex = original_run_ctx_codex
        claim = next(call for call in calls if call and call[0] == "claim")
        start = next(call for call in calls if call and call[0] == "start")
        reply = next(call for call in calls if call and call[0] == "reply")
        self.assertEqual(claim[claim.index("--instance-id") + 1], self.agent.INSTANCE_ID)
        self.assertEqual(start[start.index("--instance-id") + 1], self.agent.INSTANCE_ID)
        self.assertEqual(start[start.index("--lease-id") + 1], "lease-lingxiao-test")
        self.assertEqual(reply[reply.index("--lease-id") + 1], "lease-lingxiao-test")

    def test_lingxiao_skips_late_reply_after_cancel(self):
        original_run_json = self.agent.run_json
        original_run_ctx_codex = self.agent.run_ctx_codex
        calls = []

        def fake_run_json(args, input_obj=None, timeout=30):
            calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-lingxiao-test"}
            if args and args[0] == "show":
                return {"route_id": "route_test", "status": "cancelled"}
            if args and args[0] == "reply":
                raise AssertionError("late reply should not be written to cancelled route")
            return {}

        def fake_run_ctx_codex(route, timeout):
            return {
                "route_id": route["route_id"],
                "status": "replied",
                "executed_by": self.agent.AGENT_ID,
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }

        self.agent.run_json = fake_run_json
        self.agent.run_ctx_codex = fake_run_ctx_codex
        try:
            self.assertFalse(self.agent.process_route(self.eligible_route(), 120))
        finally:
            self.agent.run_json = original_run_json
            self.agent.run_ctx_codex = original_run_ctx_codex
        self.assertTrue(any(call and call[0] == "show" for call in calls))
        self.assertFalse(any(call and call[0] == "reply" for call in calls))

    def test_lingxiao_skips_reply_status_race(self):
        original_run_json = self.agent.run_json
        original_run_ctx_codex = self.agent.run_ctx_codex

        def fake_run_json(args, input_obj=None, timeout=30):
            if args and args[0] == "claim":
                return {"lease_id": "lease-lingxiao-test"}
            if args and args[0] == "show":
                return {"route_id": "route_test", "status": "running"}
            if args and args[0] == "reply":
                raise RuntimeError("route cannot receive reply from status=cancelled")
            return {}

        def fake_run_ctx_codex(route, timeout):
            return {
                "route_id": route["route_id"],
                "status": "replied",
                "executed_by": self.agent.AGENT_ID,
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }

        self.agent.run_json = fake_run_json
        self.agent.run_ctx_codex = fake_run_ctx_codex
        try:
            self.assertFalse(self.agent.process_route(self.eligible_route(), 120))
        finally:
            self.agent.run_json = original_run_json
            self.agent.run_ctx_codex = original_run_ctx_codex

    def test_claim_race_helper_matches_start_status_error(self):
        self.assertTrue(self.agent.is_claim_race_error(RuntimeError("route cannot start from status=replied")))

    def test_mac_agent_uses_dev_null_ssh_config(self):
        mac_agent = load_mac_agent()
        self.assertEqual(mac_agent.SSH_CONFIG, "/dev/null")

    def test_mac_agent_quotes_remote_ssh_arguments(self):
        mac_agent = load_mac_agent()
        original_run = mac_agent.subprocess.run
        captured = []

        class Result:
            returncode = 0
            stdout = "{}"
            stderr = ""

        def fake_run(cmd, input=None, text=None, capture_output=None, timeout=None):
            captured.append(cmd)
            return Result()

        mac_agent.subprocess.run = fake_run
        try:
            mac_agent.ssh_json(["agent-heartbeat", "--metrics-json", "{\"recent\":[{\"operation\":\"list\"}]}"])
        finally:
            mac_agent.subprocess.run = original_run
        remote_command = captured[0][-1]
        self.assertIsInstance(remote_command, str)
        self.assertIn("agent-heartbeat", remote_command)
        self.assertIn("--metrics-json", remote_command)
        self.assertNotEqual(captured[0][-3], "agent-heartbeat")

    def test_mac_agents_classify_transient_ssh_errors(self):
        mac_agent = load_mac_agent()
        mac_codex = load_mac_codex_agent()
        self.assertTrue(mac_agent.is_transient_ssh_error("ssh: connect to host 203.0.113.10 port 22: Operation timed out"))
        self.assertTrue(mac_codex.is_transient_ssh_error("kex_exchange_identification: Connection closed by remote host"))
        self.assertFalse(mac_agent.is_transient_ssh_error("route not claimable: route_x status=claimed"))
        self.assertFalse(mac_codex.is_transient_ssh_error("route cannot start from status=replied"))

    def test_huaguoshan_frp_agent_defaults_to_reverse_ssh(self):
        frp_agent = load_hgs_frp_agent()
        self.assertEqual(frp_agent.FRP_SSH_HOST, "127.0.0.1")
        self.assertEqual(frp_agent.FRP_SSH_PORT, "6022")
        profile = frp_agent.device_profile()
        self.assertIn("frp-reverse-ssh:127.0.0.1:6022", profile["transports"])
        self.assertIn("no_public_ssh_ledger_path", profile["red_lines"])
        self.assertNotIn("203.0.113.10", str(profile))

    def test_huaguoshan_frp_agent_claims_locally_and_probes_over_frp(self):
        frp_agent = load_hgs_frp_agent()
        route = {
            "route_id": "route_hgs_frp",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "target_agent": "local-native",
            "required_capabilities": ["macos", "read-only-probe"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": False,
            "secret_capabilities": [],
            "probe": "mac-basic-status",
        }
        original_run_json = frp_agent.run_json
        original_frp_command = frp_agent.frp_command
        route_calls = []
        frp_calls = []

        def fake_run_json(args, input_obj=None, timeout=30):
            route_calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-frp-test"}
            if args and args[0] == "show":
                return {"route_id": route["route_id"], "status": "running"}
            return {}

        def fake_frp_command(args, timeout=10):
            frp_calls.append(args)
            stdout = {
                ("hostname",): "example-mac.local",
                ("uname", "-a"): "Darwin example-mac.local",
                ("whoami",): "ctx",
                ("date", "-u", "+%Y-%m-%dT%H:%M:%SZ"): "2026-06-14T09:00:00Z",
            }.get(tuple(args), "")
            return {
                "command": ["ssh", "-F", "/dev/null", "-p", "6022", "ctx@127.0.0.1", *args],
                "remote_args": args,
                "exit_code": 0,
                "elapsed_ms": 10,
                "stdout": stdout,
                "stderr": "",
                "observed_at": "2026-06-14T09:00:00Z",
            }

        frp_agent.run_json = fake_run_json
        frp_agent.frp_command = fake_frp_command
        try:
            self.assertTrue(frp_agent.process_route(route))
        finally:
            frp_agent.run_json = original_run_json
            frp_agent.frp_command = original_frp_command
        self.assertEqual([call[0] for call in route_calls], ["claim", "start", "show", "reply"])
        start = next(call for call in route_calls if call and call[0] == "start")
        reply = next(call for call in route_calls if call and call[0] == "reply")
        self.assertEqual(start[start.index("--lease-id") + 1], "lease-frp-test")
        self.assertEqual(reply[reply.index("--lease-id") + 1], "lease-frp-test")
        self.assertEqual(frp_calls, [
            ["hostname"],
            ["uname", "-a"],
            ["whoami"],
            ["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
        ])
        self.assertNotIn("203.0.113.10", str(route_calls) + str(frp_calls))

    def test_huaguoshan_frp_agent_failed_probe_becomes_reply_evidence(self):
        frp_agent = load_hgs_frp_agent()
        original_frp_command = frp_agent.frp_command
        calls = []

        def fake_frp_command(args, timeout=10):
            calls.append(args)
            return {
                "command": ["ssh", "-F", "/dev/null", "-p", "6022", "ctx@127.0.0.1", *args],
                "remote_args": args,
                "exit_code": 255,
                "elapsed_ms": 12,
                "stdout": "",
                "stderr": "ssh: connect to host 127.0.0.1 port 6022: Connection refused",
                "observed_at": "2026-06-14T09:20:00Z",
            }

        frp_agent.frp_command = fake_frp_command
        try:
            reply = frp_agent.mac_basic_status({"route_id": "route_hgs_frp_down"})
        finally:
            frp_agent.frp_command = original_frp_command
        self.assertEqual(calls, [["hostname"]])
        self.assertEqual(reply["status"], "failed")
        self.assertIn("frp mac-basic-status failed", reply["summary"])
        self.assertEqual(len(reply["evidence"]), 1)
        self.assertEqual(reply["evidence"][0]["transport"], "frp-reverse-ssh:127.0.0.1:6022")
        self.assertIn("Connection refused", reply["evidence"][0]["stderr_excerpt"])
        self.assertIn("no public SSH ledger path", reply["residual_risk"])

    def test_pi_bridge_envelope_preserves_lane_scope(self):
        bridge = load_hgs_pi_bridge()
        envelope = bridge.build_envelope({
            "route_id": "route_pi_scope",
            "trace_id": "trace_pi_scope",
            "lane_id": "lane_pi_scope",
            "work_chat_id": "chat_pi_scope",
            "context_id": "ctx_pi_scope",
            "origin_site": "lingxiaodian",
            "origin_agent": "codex",
            "instructions": "inspect",
            "constraints": ["read_only_first"],
        })
        self.assertEqual(envelope["trace_id"], "trace_pi_scope")
        self.assertEqual(envelope["lane_id"], "lane_pi_scope")
        self.assertEqual(envelope["work_chat_id"], "chat_pi_scope")
        self.assertEqual(envelope["context_id"], "ctx_pi_scope")

    def test_lx_worker_create_on_ingest_preserves_lane_scope(self):
        worker = load_lx_worker()
        calls = []
        original_status = worker.route_status
        original_route_cmd = worker.route_cmd

        def fake_status(_rid):
            return None

        def fake_route_cmd(args, stdin=None, timeout=40):
            calls.append(args)
            return {"ok": True}

        try:
            worker.route_status = fake_status
            worker.route_cmd = fake_route_cmd
            worker.ensure_route({
                "route_id": "route_lx_scope",
                "trace_id": "trace_lx_scope",
                "lane_id": "lane_lx_scope",
                "work_chat_id": "chat_lx_scope",
                "context_id": "ctx_lx_scope",
                "origin": "huaguoshan:pi",
                "target": "lingxiaodian:fable",
                "prompt": "inspect",
            })
        finally:
            worker.route_status = original_status
            worker.route_cmd = original_route_cmd

        self.assertEqual(calls[0][0], "create")
        self.assertIn("--trace-id", calls[0])
        self.assertIn("trace_lx_scope", calls[0])
        self.assertIn("--lane-id", calls[0])
        self.assertIn("lane_lx_scope", calls[0])
        self.assertIn("--work-chat-id", calls[0])
        self.assertIn("chat_lx_scope", calls[0])
        self.assertIn("--context-id", calls[0])
        self.assertIn("ctx_lx_scope", calls[0])

    def test_huaguoshan_frp_command_timeout_becomes_command_result(self):
        frp_agent = load_hgs_frp_agent()
        original_run = frp_agent.subprocess.run

        def fake_run(cmd, text=None, capture_output=None, timeout=None):
            raise frp_agent.subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

        frp_agent.subprocess.run = fake_run
        try:
            result = frp_agent.frp_command(["hostname"], timeout=1)
        finally:
            frp_agent.subprocess.run = original_run
        self.assertEqual(result["exit_code"], 124)
        self.assertIn("TimeoutExpired", result["stderr"])
        self.assertEqual(result["remote_args"], ["hostname"])
        self.assertNotIn("203.0.113.10", str(result))

    def test_mac_agent_heartbeat_has_instance_identity(self):
        mac_agent = load_mac_agent()
        original_ssh_json = mac_agent.ssh_json
        calls = []

        def fake_ssh_json(args, input_obj=None):
            calls.append(args)
            return {"ok": True}

        mac_agent.ssh_json = fake_ssh_json
        try:
            mac_agent.agent_heartbeat()
        finally:
            mac_agent.ssh_json = original_ssh_json
        heartbeat = calls[0]
        self.assertEqual(heartbeat[0], "agent-heartbeat")
        self.assertIn("--instance-id", heartbeat)
        self.assertIn("--pid", heartbeat)
        self.assertIn("--state", heartbeat)
        self.assertIn("active", heartbeat)
        self.assertIn("--metrics-json", heartbeat)
        self.assertIn("--tool-sha256", heartbeat)
        self.assertIn("--tool-mtime", heartbeat)
        self.assertIn("--loaded-tool-sha256", heartbeat)
        self.assertIn("--loaded-tool-mtime", heartbeat)
        self.assertIn("huaguoshan-fixed-read-only-claimant", heartbeat)

    def test_mac_agent_once_retires_instance(self):
        mac_agent = load_mac_agent()
        original_ssh_json = mac_agent.ssh_json
        calls = []

        def fake_ssh_json(args, input_obj=None):
            calls.append(args)
            if args and args[0] == "list":
                return []
            return {"ok": True}

        mac_agent.ssh_json = fake_ssh_json
        try:
            mac_agent.run_once()
        finally:
            mac_agent.ssh_json = original_ssh_json
        heartbeat_states = [
            call[call.index("--state") + 1]
            for call in calls
            if call and call[0] == "agent-heartbeat" and "--state" in call
        ]
        self.assertEqual(heartbeat_states, ["active", "stopped"])

    def test_mac_agent_once_honors_max_routes(self):
        mac_agent = load_mac_agent()
        original_ssh_json = mac_agent.ssh_json
        original_process_route = mac_agent.process_route
        routes = [
            {"route_id": "route_one", "status": "queued", "target_site": "huaguoshan-macos"},
            {"route_id": "route_two", "status": "queued", "target_site": "huaguoshan-macos"},
            {"route_id": "route_three", "status": "queued", "target_site": "huaguoshan-macos"},
        ]
        processed = []

        def fake_ssh_json(args, input_obj=None):
            if args and args[0] == "list":
                return routes
            return {"ok": True}

        def fake_process_route(route):
            processed.append(route["route_id"])
            return True

        mac_agent.ssh_json = fake_ssh_json
        mac_agent.process_route = fake_process_route
        try:
            mac_agent.run_once(max_routes=2)
        finally:
            mac_agent.ssh_json = original_ssh_json
            mac_agent.process_route = original_process_route
        self.assertEqual(processed, ["route_one", "route_two"])

    def test_mac_agent_rejects_approval_required(self):
        mac_agent = load_mac_agent()
        route = {
            "route_id": "route_mac",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "required_capabilities": ["macos", "read-only-probe"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": True,
            "secret_capabilities": [],
            "probe": "mac-basic-status",
        }
        self.assertFalse(mac_agent.route_eligible(route))

    def test_mac_agent_skips_claim_race(self):
        mac_agent = load_mac_agent()
        route = {
            "route_id": "route_mac",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "required_capabilities": ["macos", "read-only-probe"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": False,
            "secret_capabilities": [],
            "probe": "mac-basic-status",
        }
        original_ssh_json = mac_agent.ssh_json

        def fake_ssh_json(args, input_obj=None):
            if args and args[0] == "claim":
                raise RuntimeError("route not claimable: route_mac status=claimed")
            return {}

        mac_agent.ssh_json = fake_ssh_json
        try:
            self.assertFalse(mac_agent.process_route(route))
        finally:
            mac_agent.ssh_json = original_ssh_json

    def test_mac_agent_process_route_passes_instance_id(self):
        mac_agent = load_mac_agent()
        route = {
            "route_id": "route_mac",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "required_capabilities": ["macos", "read-only-probe"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": False,
            "secret_capabilities": [],
            "probe": "mac-basic-status",
        }
        original_ssh_json = mac_agent.ssh_json
        original_mac_basic_status = mac_agent.mac_basic_status
        calls = []

        def fake_ssh_json(args, input_obj=None):
            calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-mac-test"}
            return {}

        def fake_mac_basic_status(route):
            return {
                "route_id": route["route_id"],
                "status": "replied",
                "executed_by": mac_agent.AGENT_ID,
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }

        mac_agent.ssh_json = fake_ssh_json
        mac_agent.mac_basic_status = fake_mac_basic_status
        try:
            self.assertTrue(mac_agent.process_route(route))
        finally:
            mac_agent.ssh_json = original_ssh_json
            mac_agent.mac_basic_status = original_mac_basic_status
        claim = next(call for call in calls if call and call[0] == "claim")
        start = next(call for call in calls if call and call[0] == "start")
        reply = next(call for call in calls if call and call[0] == "reply")
        self.assertEqual(claim[claim.index("--instance-id") + 1], mac_agent.INSTANCE_ID)
        self.assertEqual(start[start.index("--instance-id") + 1], mac_agent.INSTANCE_ID)
        self.assertEqual(start[start.index("--lease-id") + 1], "lease-mac-test")
        self.assertEqual(reply[reply.index("--lease-id") + 1], "lease-mac-test")

    def test_mac_agent_releases_own_claim_after_start_timeout(self):
        mac_agent = load_mac_agent()
        route = {
            "route_id": "route_mac",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "required_capabilities": ["macos", "read-only-probe"],
            "constraints": ["read_only_first", "no_secrets"],
            "approval_required": False,
            "secret_capabilities": [],
            "probe": "mac-basic-status",
        }
        original_ssh_json = mac_agent.ssh_json
        original_mac_basic_status = mac_agent.mac_basic_status
        calls = []

        def fake_ssh_json(args, input_obj=None):
            calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-mac-release-test"}
            if args and args[0] == "start":
                raise RuntimeError("ssh: connect to host 203.0.113.10 port 22: Operation timed out")
            if args and args[0] == "show":
                return {
                    "route_id": route["route_id"],
                    "status": "claimed",
                    "lease": {
                        "lease_id": "lease-mac-release-test",
                        "claimed_by": mac_agent.AGENT_ID,
                        "claim_instance_id": mac_agent.INSTANCE_ID,
                    },
                }
            return {}

        def fail_mac_basic_status(route):
            raise AssertionError("probe should not run after unrecovered start failure")

        mac_agent.ssh_json = fake_ssh_json
        mac_agent.mac_basic_status = fail_mac_basic_status
        try:
            self.assertFalse(mac_agent.process_route(route))
        finally:
            mac_agent.ssh_json = original_ssh_json
            mac_agent.mac_basic_status = original_mac_basic_status
        release = next(call for call in calls if call and call[0] == "release")
        self.assertEqual(release[1], "route_mac")
        self.assertEqual(release[release.index("--instance-id") + 1], mac_agent.INSTANCE_ID)
        self.assertEqual(release[release.index("--lease-id") + 1], "lease-mac-release-test")

    def test_mac_codex_agent_accepts_safe_review_route(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "target_agent": "codex",
            "task_kind": "review",
            "approval_required": False,
            "secret_capabilities": [],
            "required_capabilities": ["macos", "codex", "codex-cli"],
            "constraints": ["read_only_first", "no_secrets", "no_file_mutation"],
            "cwd": "/tmp",
        }
        ok, reason = mac_codex.route_eligible(route)
        self.assertTrue(ok, reason)

    def test_mac_codex_agent_rejects_local_native_target(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "target_agent": "local-native",
            "task_kind": "review",
            "approval_required": False,
            "secret_capabilities": [],
            "required_capabilities": ["macos"],
            "constraints": ["read_only_first", "no_secrets"],
            "cwd": "/tmp",
        }
        ok, reason = mac_codex.route_eligible(route)
        self.assertFalse(ok)
        self.assertIn("target_agent", reason)

    def test_mac_codex_command_is_read_only_ephemeral(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "cwd": "/tmp",
        }
        cmd = mac_codex.codex_command(route, Path("/tmp/out.txt"))
        self.assertIn("--sandbox", cmd)
        self.assertIn("read-only", cmd)
        self.assertIn("--ephemeral", cmd)

    def test_mac_codex_task_contains_ctx_identity(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "trace_id": "trace_mac",
            "lane_id": "lane_mac",
            "work_chat_id": "chat_mac",
            "context_id": "ctx_mac",
            "origin_site": "lingxiaodian",
            "origin_agent": "codex",
            "target_site": "huaguoshan-macos",
            "target_agent": "codex",
            "task_kind": "review",
            "constraints": ["read_only_first", "no_secrets"],
            "instructions": "review",
        }
        task = mac_codex.route_task(route)
        self.assertIn("CTX-CALL-IDENTITY:", task)
        self.assertIn("CTX-EXECUTOR: huaguoshan-macos:codex", task)
        self.assertIn("CTX-SESSION-VISIBILITY: ephemeral", task)
        self.assertIn('"lane_id": "lane_mac"', task)
        self.assertIn('"work_chat_id": "chat_mac"', task)
        self.assertIn('"context_id": "ctx_mac"', task)

    def test_mac_codex_agent_heartbeat_has_instance_identity(self):
        mac_codex = load_mac_codex_agent()
        original_ssh_json = mac_codex.ssh_json
        calls = []

        def fake_ssh_json(args, input_obj=None, timeout=45):
            calls.append(args)
            return {"ok": True}

        mac_codex.ssh_json = fake_ssh_json
        try:
            mac_codex.agent_heartbeat()
        finally:
            mac_codex.ssh_json = original_ssh_json
        heartbeat = calls[0]
        self.assertEqual(heartbeat[0], "agent-heartbeat")
        self.assertIn("--instance-id", heartbeat)
        self.assertIn("--pid", heartbeat)
        self.assertIn("--state", heartbeat)
        self.assertIn("active", heartbeat)
        self.assertIn("--metrics-json", heartbeat)
        self.assertIn("--tool-sha256", heartbeat)
        self.assertIn("--tool-mtime", heartbeat)
        self.assertIn("--loaded-tool-sha256", heartbeat)
        self.assertIn("--loaded-tool-mtime", heartbeat)
        self.assertIn("huaguoshan-manual-first-codex-claimant", heartbeat)

    def test_mac_codex_agent_once_retires_instance(self):
        mac_codex = load_mac_codex_agent()
        original_ssh_json = mac_codex.ssh_json
        calls = []

        def fake_ssh_json(args, input_obj=None, timeout=45):
            calls.append(args)
            if args and args[0] == "list":
                return []
            return {"ok": True}

        mac_codex.ssh_json = fake_ssh_json
        try:
            mac_codex.run_once(type("Args", (), {"timeout": 300})())
        finally:
            mac_codex.ssh_json = original_ssh_json
        heartbeat_states = [
            call[call.index("--state") + 1]
            for call in calls
            if call and call[0] == "agent-heartbeat" and "--state" in call
        ]
        self.assertEqual(heartbeat_states, ["active", "stopped"])

    def test_mac_codex_agent_skips_claim_race(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "target_agent": "codex",
            "task_kind": "review",
            "approval_required": False,
            "secret_capabilities": [],
            "required_capabilities": ["macos", "codex", "codex-cli"],
            "constraints": ["read_only_first", "no_secrets", "no_file_mutation"],
            "cwd": "/tmp",
        }
        original_ssh_json = mac_codex.ssh_json
        original_run_codex = mac_codex.run_codex

        def fake_ssh_json(args, input_obj=None, timeout=45):
            if args and args[0] == "claim":
                raise RuntimeError("route not claimable: route_mac_codex status=claimed")
            return {}

        def fail_run_codex(route, timeout):
            raise AssertionError("Codex should not run after claim race")

        mac_codex.ssh_json = fake_ssh_json
        mac_codex.run_codex = fail_run_codex
        try:
            self.assertFalse(mac_codex.process_route(route, 300))
        finally:
            mac_codex.ssh_json = original_ssh_json
            mac_codex.run_codex = original_run_codex

    def test_mac_codex_agent_process_route_passes_instance_id(self):
        mac_codex = load_mac_codex_agent()
        route = {
            "route_id": "route_mac_codex",
            "status": "queued",
            "target_site": "huaguoshan-macos",
            "target_agent": "codex",
            "task_kind": "review",
            "approval_required": False,
            "secret_capabilities": [],
            "required_capabilities": ["macos", "codex", "codex-cli"],
            "constraints": ["read_only_first", "no_secrets", "no_file_mutation"],
            "cwd": "/tmp",
        }
        original_ssh_json = mac_codex.ssh_json
        original_run_codex = mac_codex.run_codex
        calls = []

        def fake_ssh_json(args, input_obj=None, timeout=45):
            calls.append(args)
            if args and args[0] == "claim":
                return {"lease_id": "lease-mac-codex-test"}
            return {}

        def fake_run_codex(route, timeout):
            return {
                "route_id": route["route_id"],
                "status": "replied",
                "executed_by": mac_codex.AGENT_ID,
                "summary": "ok",
                "evidence": [],
                "artifacts": [],
                "secret_events": [],
                "residual_risk": "none",
                "next_action": "verify",
            }

        mac_codex.ssh_json = fake_ssh_json
        mac_codex.run_codex = fake_run_codex
        try:
            self.assertTrue(mac_codex.process_route(route, 300))
        finally:
            mac_codex.ssh_json = original_ssh_json
            mac_codex.run_codex = original_run_codex
        claim = next(call for call in calls if call and call[0] == "claim")
        start = next(call for call in calls if call and call[0] == "start")
        reply = next(call for call in calls if call and call[0] == "reply")
        self.assertEqual(claim[claim.index("--instance-id") + 1], mac_codex.INSTANCE_ID)
        self.assertEqual(start[start.index("--instance-id") + 1], mac_codex.INSTANCE_ID)
        self.assertEqual(start[start.index("--lease-id") + 1], "lease-mac-codex-test")
        self.assertEqual(reply[reply.index("--lease-id") + 1], "lease-mac-codex-test")


if __name__ == "__main__":
    unittest.main()
